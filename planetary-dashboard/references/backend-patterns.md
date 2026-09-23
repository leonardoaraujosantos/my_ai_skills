# Backend patterns: geospatial compute behind a globe

Use this reference when a dashboard does more than proxy public feeds, for example spectral indices, compliance checks, RF coverage, risk scoring or async jobs. These patterns come from GeoSphere (`CyberdyneCorp/geo_dashboard`, a FastAPI hexagonal backend). The paths in brackets point to the originals in that repo.

Skip this whole file if the dashboard only visualises public feeds. A thin proxy layer (`proxies.md`) is enough for that.

---

## 1. One use case, three front doors

Put each capability in exactly one place, a callable use case, and expose it three ways:

```
domain/ports/*_port.py        typing.Protocol + Spec/Result dataclasses + one error class per port
domain/services/              pure math, no I/O (verdict rules, RF formulas, EVI, …)
application/use_cases/*.py    class ComputeIndex: __init__(ports) ; async __call__(spec)
adapters/inbound/api/         FastAPI router      → use case
adapters/inbound/mcp/         FastMCP tool        → use case
adapters/inbound/agent/tools  Agents SDK function_tool → use case
adapters/outbound/            real adapter + fake twin per port
```

- **Generate the MCP and agent tool definitions from one registry.** In GeoSphere they were written separately and drifted apart: MCP had 26 tools and the agent had 39, and the size caps differed (90 vs 366 days). Add a snapshot test of the tool surface.
- **Choose adapters from environment flags**, for example `RASTER_ENGINE=cybergeopy|fake`, `STORAGE_BACKEND=memory|s3`, `JOBS_BACKEND=memory|arq`. Make each fake deterministic by seeding it from a hash of the geometry, so the UI works offline and demos are reproducible.
- **Import heavy optional dependencies lazily.** Examples are GDAL, odc-stac and itmlogic. Catch the `ImportError` in the adapter's `__init__` and raise a domain error only when a request actually needs the dependency. The app then stays importable without GDAL.
- Use a small registry or FastAPI lifespan state for dependency wiring. Avoid a 1,500-line service locator.

## 2. Size-capped sync endpoints that promote to jobs

```
POST /v1/index/compute
  area ≤ 1 deg² and days ≤ 366  → 200 {result}
  otherwise                     → 202 + Location: /v1/jobs/{id}
GET  /v1/jobs/{id}              → {status: PENDING|RUNNING|SUCCEEDED|FAILED|CANCELLED}
GET  /v1/jobs/{id}/result       → 409 if not SUCCEEDED, 410 if blob gone, else payload + presigned URL (15 min)
```

- **Queue:** arq on Redis. The only contract is the function name `run_job(job_id, tenant_id)`, and `_job_id="app:{id}"` makes enqueueing idempotent. Retry pool start-up on Redis `BusyLoadingError` (AOF replay after a restart).
- **Result location:** results live at `tenants/{tenant}/jobs/{id}/result.json` in S3/MinIO.
- **Worker settings:** `max_jobs=2`, `job_timeout=600`. The worker must set the tenant context from the payload before touching the database.
- **Heavy solvers** (CFD, FEM) run in their own images on dedicated queues and share case files through a named volume.

## 3. Streaming progress from blocking geo code (SSE)

Raster pipelines (dask, odc-stac, rasterio) block. Run them in `asyncio.to_thread` and move progress events onto the event loop:

```python
loop = asyncio.get_running_loop()
queue: asyncio.Queue = asyncio.Queue()

def progress(stage: str, msg: str) -> None:          # called from the worker thread
    loop.call_soon_threadsafe(queue.put_nowait, {"event": "progress", "stage": stage, "msg": msg})

async def run():
    try:
        result = await asyncio.to_thread(engine.compute_indices, spec, progress)
        await queue.put({"event": "result", "data": result})
    except DomainError as e:
        await queue.put({"event": "error", "message": str(e)})
    finally:
        await queue.put(None)

async def stream():
    task = asyncio.create_task(run())
    while (item := await queue.get()) is not None:
        yield f"event: {item.pop('event')}\ndata: {json.dumps(item)}\n\n"
    await task

return StreamingResponse(stream(), media_type="text/event-stream",
                         headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

`X-Accel-Buffering: no` matters. Without it, nginx or Traefik buffers the whole stream and the progress bar only updates once the job has finished.

## 4. Raster results the globe can draw without a tile server

- **PNG with a bbox header:** `POST /v1/index/preview_png` returns `image/png` plus `X-Bbox: minLng,minLat,maxLng,maxLat`. On the client, draw it with Cesium `SingleTileImageryProvider({url, rectangle})` or a MapLibre `image` source with four corner coordinates.
  - Colour each index with linear interpolation over RGB stops. Map NaN to alpha 0.
  - Take the bbox from the input GeoJSON, not from the raster, because odc picks a UTM grid.
- **Dissolved vectors for classified grids:** turn thousands of coverage cells into one MultiPolygon per quality band with shapely `unary_union`. Export the same bands as GeoJSON or KML, with KML colours in `aabbggrr` order.
- **Share band thresholds between backend and frontend.** RSRP −85/−100/−110/−120 dBm is one example. The legend, map and export must agree.
- For large or zoomable rasters, move to COGs behind TiTiler or PMTiles (see `maplibre-and-pipelines.md`).

## 5. Spectral indices over STAC

- **Chain:** STAC search with `eo:cloud_cover < N` → read bands at `resolution_m=10` with chunks `{"x":2048,"y":2048}` → SCL cloud mask → scaling → index → composite (`none | median | mean | max_value`).
- **Bands:**

  | Index | Bands |
  |---|---|
  | NDVI | red, nir |
  | EVI | blue, red, nir. EVI = 2.5·(NIR−RED)/(NIR+6·RED−7.5·BLUE+1) |
  | NDWI | green, nir |
  | NDMI | nir, swir16 |
  | NDBI | swir16, nir |

- **Stats:** min, max, mean, p10, p50, p90, plus a per-scene spatial-mean time series. The time series feeds a sparkline or chart.
- **Catalog routing:** send Sentinel-1/2/3/5P to Copernicus CDSE. It needs OAuth client credentials and S3 keys for `eodata`. Fall back to Element84 Earth Search, which needs no auth. Send Landsat and MODIS to Planetary Computer. Cache STAC searches for 1 h, keyed on a hash of collection + bbox + time + query.
- **Deforestation check (EUDR-style):** compare forest baseline (JRC 2020) with post-cutoff loss (Hansen GFC). The verdict is one of `LIKELY_COMPLIANT | NON_COMPLIANT | INCONCLUSIVE | REVIEW_REQUIRED`.

## 6. Terrain comes from the client

For physics-style endpoints such as RF path loss or line of sight, **sample the terrain profile in the browser** and POST `profile_m[]`. Use Cesium `sampleTerrainMostDetailed`, or MapLibre `queryTerrainElevation`. The backend then needs no DEM.

- **Point-to-point:** Longley-Rice ITM (`itmlogic`).
- **Area:** simplified ITU-R P.1812 (knife-edge P.526 + clutter table + P.676 gas).
- **Coverage grid:** 3GPP TR 38.901 sector pattern. Cap the grid at about 501×501.

## 7. Globe-aware agent

- **Context preamble:** the client sends its dashboard state with every chat turn: camera, enabled layers, drawn polygons, selection and open entity ids. The server prepends it as
  `<DASHBOARD_CONTEXT>{json}</DASHBOARD_CONTEXT>`. The system prompt tells the model to use those ids and to answer from the preamble when it can.
- **SSE event schema** (`POST /v1/agent/chat/stream`):
  `session{session_id}` · `token{delta}` · `tool{name, call_id, arguments_preview}` · `tool_output{call_id, output}` · `done{reply, model}` · `error{message}`.
  The UI turns `tool` events into chips and looks for `artifact_url` in `tool_output`.
- **Result-size flags:** `include_grid`, `verbose`. Tools return stats by default so large grids never enter the model's context.
- **Artifacts:** charts (matplotlib Agg PNG) and CSV exports go to blob storage and come back as HMAC-signed URLs (`?exp=&sig=`), because an `<img src>` cannot carry a bearer token.
- **External MCP:** attach external MCP servers per request (`MCPServerSse`, 15 s timeout, cached tool list). If one fails to connect, log it and skip it. Never fail the chat.
- **System prompt rules worth copying:**
  - lng/lat order.
  - ISO UTC dates.
  - Read back existing results before recomputing.
  - Confirm before starting heavy jobs.
  - Always give units.
  - Only offer follow-ups that a tool can actually deliver.
- **Model compatibility:** skip `temperature` for reasoning models that reject it. Honour `OPENAI_BASE_URL` so any OpenAI-compatible gateway works, including an on-prem one.

## 8. Tenancy, auth, caching

- **Row-level security:** enable RLS with `ENABLE` + `FORCE ROW LEVEL SECURITY` and a policy `USING (tenant_id = current_setting('app.tenant_id', true)::uuid)`. Set the tenant per transaction in an SQLAlchemy `after_begin` hook with `SELECT set_config('app.tenant_id', :tid, true)`. That is the bindable form of `SET LOCAL` and is safe with pooled connections.
- **Tenant selection:** read the active tenant from an `X-Active-Tenant` header and check membership. On failure, return a structured 403 that includes `default_tenant_id`, so the UI can recover.
- **Auth:** verify JWTs locally against JWKS. If you must call an upstream `/users/me`, cache the result by `sha256(token)` for 30 s and **coalesce concurrent verifications into one call**, because a globe polls often.
- **Caching:** wrap ports in caching decorators and set the TTL by how often the data changes:

  | Data | TTL |
  |---|---|
  | Past climate | 30 d |
  | Wikipedia | 7 d (negative results cached too) |
  | News | 1 h |
  | STAC search | 1 h |

  Prefix cache keys with the tenant. Fall back to an in-memory cache when Redis errors. Run Redis with `maxmemory` + `allkeys-lru`.
- **Rate limiting:** key on the token suffix, falling back to IP (slowapi). Default to 120/min.

## 9. Observability and tests

- **Observability:**
  - Propagate `X-Request-ID` into structlog contextvars.
  - Serve Prometheus `/metrics`, excluding health endpoints.
  - Log JSON in production.
  - Make `/readyz` actually check the database, Redis and storage.
- **Tests:**
  - Reset the singletons around every test.
  - Pin the fake engines through environment variables.
  - Use a fake auth port that still enforces the bearer header.
  - Run the lifespan explicitly with `httpx.ASGITransport`.
  - Mock HTTP with `respx` and S3 with `moto`.
  - Test MCP in-process with `fastmcp.Client(server)`.
  - Snapshot-test the tool list.
- **Compose topology:** postgres, redis, minio, api, worker (reuse the api image), and optional solver workers. Use `expose` only and let the reverse proxy (Coolify or Traefik) handle ingress.
