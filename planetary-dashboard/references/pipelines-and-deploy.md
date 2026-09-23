# Data pipelines, provenance, context packs and sovereign deployment

This reference covers dashboards that ship curated, national-scale, or offline data in addition to (or instead of) live feeds. The patterns come mostly from KANZI (`aminitech/kanzi`), which uses GDAL, GeoPackage, manifests and MapLibre.

---

## 1. Source registry: "config over code"

Each layer is one YAML entry. Its `sources` are listed in priority order.

```yaml
- id: protected_areas
  title: Protected areas
  custodian: WDPA / UNEP-WCMC
  licence: "WDPA terms (non-commercial)"
  attribution: "UNEP-WCMC and IUCN (2026)"
  confidence: B            # A..D | unknown — shown in the UI
  geometry: polygon
  clip_layer: country_boundary
  simplify: 0.0005
  web_fields: [name, desig, iucn_cat, status_yr]
  max_snapshot_mb: 8
  style: { fill: "--series-3", opacity: 0.35 }
  country: BW
  sources:
    - { kind: arcgis, url: "https://…/FeatureServer/0", where: "ISO3='BWA'" }
    - { kind: http,   url: "https://…/wdpa_bw.zip", layer_match: "polygons" }
    - { kind: manual, path: "data/manual/wdpa_bw.gpkg" }
```

**Fetcher kinds:** `http | wfs | overpass | arcgis | hdx | sciencebase | manual | terrain`.

**Validation:** validate the registry with Pydantic. Extra per-source options are `layer_match` (a regex for the layer inside a zip, gpkg or gdb), `where` (OGR SQL), and `x_field` / `y_field` (for CSV points).

## 2. Every source has a backup

- **Fallback loop.** Try each source in order. The first one that succeeds is recorded as `live`, and any later success as `mirror`. Record every attempt in `attempts[]`.
- **Snapshots.** If every source fails, copy the committed `data/snapshots/<id>.geojson` and mark the layer `snapshot`. If there is no snapshot either, mark it `missing`.
- **Refreshing snapshots.** `refresh_snapshots` promotes the last good export into the snapshot directory, capped by `max_snapshot_mb`.
- **Offline runs.** With `OFFLINE=1`, downloads come only from the cache. Seed a fresh deployment's empty volume with the committed snapshots, so `run --offline` works on first boot.
- **HTTP cache.** Key the cache on a hash of the URL, apply a TTL, write atomically via `.part` files, check the zip magic bytes, and guard against zip-slip.

**The UI shows the status of every layer:**
- `live` pulses.
- `mirror`, `snapshot` and `missing` are each shown in their own tone.
- `degraded_layers` in the manifest drives a banner.

## 3. GDAL normalisation, one command per layer

```bash
ogr2ogr -f GPKG kanzi.gpkg src.ext -nln <id> \
  -t_srs EPSG:4326 -makevalid -skipfailures -nlt PROMOTE_TO_MULTI \
  -spat <w s e n> -spat_srs EPSG:4326 -clipdst boundary.geojson
# provenance columns stamped via SQL:
#   kz_source, kz_source_url, kz_fetched_at, kz_licence, kz_attribution, kz_confidence
ogr2ogr -f GeoJSON exports/<id>.geojson kanzi.gpkg <id> \
  -lco COORDINATE_PRECISION=5 -lco RFC7946=YES -simplify <tol> -select <web_fields>
```

- **Shell out to the GDAL CLI** rather than using the Python bindings, so there are no compiled wheels to manage.
- **The GeoPackage keeps every field. The web export keeps only `web_fields`.**
- **Large layers become vector tiles.** Anything above a few MB goes to `tippecanoe -o <id>.pmtiles -zg --drop-densest-as-needed`, not GeoJSON.
- **Rasters become COGs:** `gdal_translate -of COG -co COMPRESS=DEFLATE`. Serve them through TiTiler, or pre-render PNG drapes with a bbox.

## 4. Manifests drive the viewer

- **`layers.json`** is the slim listing: `{id, title, status, source_id, url, fetched_at, count, bbox, sha256, licence, attempts, notes}`.
- **`twin_manifest.json`** holds the terrain spec (`primary`, exaggeration), basemaps (the vector style and the raster pair for Cesium), camera presets, layers, and `degraded_layers`.
- **One manifest per stage:** `eo_`, `site3d_`, `soil_`, `flows_`, `contours_`, and so on.
- Because the frontend renders only what the manifest describes, **you swap data hosts by republishing, not by changing code.**

## 5. Earth-observation stage (keyless)

1. **Search.** Query Earth Search STAC and take the newest cloud-free scene per MGRS tile.
2. **Read.** Do windowed rasterio COG reads with `AWS_NO_SIGN_REQUEST=YES`.
3. **Mosaic.** Mosaic the scenes with radiometric matching: a linear fit on the overlap.
4. **Products.** Compute band ratios, e.g. iron oxide B04/B02, clay B11/B12, ferrous B11/B08. Output hotspots, plus PNGs with legend text and a **"screening" caveat**.
5. **Contours.** Use an adaptive interval ladder: widen the interval until the file fits its size budget (about 2.5 MB), with a Gaussian pre-smooth. For national contours, use terrarium z9 tiles, not 3.4 GB of 30 m DEM.
6. **Lidar.** ICESat-2 via OpenAltimetry, with the per-beam geoid offset removed. Building heights come from Open Buildings 2.5D.

## 6. Context packs (one folder per client or country)

```
contexts/<country>/
  README.md          what we know (table: fact, source, verified date), first twin sites
  CONSTITUTION.md    binding local constraints (data residency, classification, language)
  ROADMAP.md
  docs-index.md      every public document/dataset: status (live|gated|…), preprocess steps
  specs/NN-*.md      frontmatter {id, phase, criteria, owner, status, depends}
                     → Purpose, Context, Requirements (SHALL), Given/When/Then scenarios,
                       Done-when, Open questions
```

- **Machine view.** `preprocess/docs/registry.yaml` mirrors every `docs-index.md` together with its steps (`fetch`, `ocr:tables`, `georef:check`, …).
- **BDD from specs.** A test parses every Given/When/Then out of `specs/`. A register marks each scenario as covered, partial, or covered elsewhere (with a reason). A **coverage test fails when a spec scenario is added, removed or renamed without updating the register.** This works well with the `openspec` skill.

## 7. Sovereign / offline deployment

**Constitution order when principles conflict:** Security > Sovereignty > Evidence > Provenance > … Examples of the principles:
- "No silent AI".
- "Unknown quality shown as unknown".
- "Progressive map loading; never ship large datasets wholesale".

**Offline and sovereign measures:**
- **Self-host everything:** fonts, icons, Cesium assets (a copy script), a Protomaps/PMTiles basemap, and terrain tiles.
- **Keyless tile hosts only, enforced by a test.** The test fails on any key-gated host, and on CARTO raster URLs, which return a watermark with HTTP 200.
- **Cesium without ion:** a custom terrarium terrain provider plus imagery from the manifest. Ion and Google 3D stay optional upgrades.
- **Local LLM:** point `OPENAI_BASE_URL` at an on-prem OpenAI-compatible gateway (see the `amini-llm` skill). Voice TTS then needs a local alternative, or disclose that audio leaves the country.

**Compose topology:**
- `caddy`: TLS, and `/data/*` served from a volume. `/metrics` returns 404 publicly.
- `web`: `adapter-node`.
- `pipeline`: a one-shot job profile.
- `health --watch`: a daemon exposing `/metrics` on :9464.
- One shared data volume. **Data is a runtime input, not baked into the image.**

**Refresh schedule:** `flock`-guarded cron jobs running `docker compose run --rm pipeline <stage>`:
- news: hourly
- layers: nightly
- EO: weekly
- 3D and soil: monthly

**Coolify / PaaS:** when the platform can't override the container command, pick the mode from an environment variable in the entrypoint (`APP_TYPE=daemon`). See the `coolify` skill for deploys.

**Connector health:** probe every upstream with HEAD or a 1-byte range request. Status is one of `healthy | degraded | down | gated | skipped`. Keep the last 288 results for a heartbeat sparkline, and export `data_file_age_seconds` to Prometheus.

**Observability:**
- JSON logs to stdout, Prometheus, OpenTelemetry, and Sentry with a `tenant` tag.
- Thread a `run_id` through logs, traces and manifests.
- Alert rules for stale data files.
