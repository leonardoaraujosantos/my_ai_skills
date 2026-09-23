# AI on the globe: voice agents, chat agents, analyst answers

There are three proven shapes. Pick one, or combine them:

| Shape | Transport | Where it came from | Best for |
|---|---|---|---|
| **Realtime voice agent** | Browser ⇄ OpenAI Realtime over **WebRTC**, with a short-lived client secret minted by your server | GEV (29 tools), KZ "Akili" (~40 tools) | Hands-free control and demos: "fly to Tokyo, show flights, go thermal" |
| **Chat agent with tools** | Browser → your backend, streamed with **SSE**. Agents SDK + MCP tools on the server | GS | Analysis: indices, risk, RF, portfolio questions, and artifacts such as charts and CSVs |
| **Analyst engine** | Local, deterministic: count, filter and rank over loaded records | GEV | Grounded numbers the model is not allowed to invent |

---

## 1. Non-negotiable rules

1. **The long-lived key never reaches the browser.** `/api/realtime/token` calls `/v1/realtime/client_secrets` and returns an ephemeral secret with `Cache-Control: no-store`. Keep the instructions and tool schema **on the server** too (KZ).
2. **Tools only change state that the UI already owns.** The agent calls the same functions a button would, so anything it does, the user can undo. Show the tool trace on screen.
3. **Confirm only on `ok: true`.** The system prompt must say to confirm a change only when the tool succeeded, to state the resulting state in one short sentence, and to issue all tool calls before speaking when the user asked for several changes.
4. **Never invent numbers.** Counts come from the analyst engine together with **feed provenance**. If a layer is off, the agent says so and offers to turn it on. If data is stale, the agent says "stale" in the same sentence as the count. If the data came from a fallback source, it names the fallback.
5. **Keep prompt-injection surfaces closed.** Upstream text (OSM names, news headlines, Wikipedia) goes into tool *results* as data. Never splice it into instruction text.
6. **Cost is visible and capped.** Meter `usage` from every `response.done` and price it per model. Bill unknown token modalities at the worst-case audio rate. Warn at $2 and end the session at $5 (both configurable). A corrupt stored limit falls back to the defaults and must never disable the cap.
7. **No key means still usable.** Without a key, run a typed-intent parser against the same tool registry (KZ). Show "configured: false" rather than breaking.

## 2. Voice agent recipe (GEV and KZ)

**Server**
```
GET|POST /api/realtime/token?tier=standard|mini
  → POST https://api.openai.com/v1/realtime/client_secrets
    { session: { type:'realtime', model, instructions, tools, tool_choice:'auto',
                 audio:{ input:{ noise_reduction:{type:'near_field'},
                                 turn_detection:{type:'semantic_vad', eagerness:'low',
                                                 create_response:true, interrupt_response:false}},
                         output:{ voice:'marin' } },
                 truncation:{ type:'retention_ratio', retention_ratio:0.5 } } }
  ← { value: <ephemeral secret>, expires_at }
```
- Add an opt-in per-IP throttle for this route.
- Prefer POST-only, so a cross-site `<img>` tag cannot mint tokens. GEV allows GET, which is a finding.

**Browser**
1. Get the secret and check its expiry.
2. Create an `RTCPeerConnection`, add the mic track (mono, with echo cancellation and noise suppression), and open an `oai-events` data channel.
3. POST the SDP offer to `https://api.openai.com/v1/realtime/calls` with `Authorization: Bearer <secret>`.
4. Play the remote audio through a hidden `<audio>` element.

**Input modes**
- Click the mic for open-mic mode.
- Hold **Space for 500 ms** for push-to-talk. Ignore it in text fields and when a modifier key is held. Cancel it on blur or when the page is hidden. On release, mute the track but keep the connection open so the reply still arrives.

**Tool-call loop**
- Deduplicate on `call_id` within 2.5 s.
- Only one response may be active at a time.
- If a newer command arrives, answer late tool calls from the old response with `{ok:false, superseded:true}`.
- After each tool result, send `response.create`.

**Visual grounding**
- Send a JPEG of the viewport (quality 0.74, at most 1200×900 and 200 KB) only when zoomed in closer than about 10 km.
- Keep only the latest screenshot in the conversation.
- Instruct the model: "do not invent labels that are not legible".

**Audio etiquette**
- Duck any playing radio or media while the agent listens or speaks.
- Hand the speaker to radio only after playback is confirmed.

**Ownership split**
Split the agent into seven owners: connection, turns, radio, input, cost, viewport and diagnostics. On a fatal error, tear down the session **before** showing ERROR.

**Wake word (KZ)**
Keep it opt-in and off by default. Tell users that Chrome's `SpeechRecognition` sends audio to Google.

## 3. Tool catalog for a globe (merge of GEV and KZ)

| Group | Tools |
|---|---|
| Camera | `fly_to_location{locationId|query|lat,lon, viewMode, rangeM}`, `adjust_camera_zoom{in|out, little|medium|lot}`, `zoom_to_globe`, `move_camera{orbit|pan|tilt|rotate|stop, direction, speed, once|continuous}`, `frame_overhead{target, radiusKm}`, `fly_route{label}` |
| Tracking | `track_entity{query, layerId}`, `select_nearest_aircraft{layerId, location}`, `stop_tracking`, `lock_target` |
| Layers and UI | `set_layer_visibility{layerId, enabled}`, `show_data_layers_menu`, `set_panel_open`, `set_context_mode`, `navigate_to{route}` (multi-page apps) |
| Display | `set_visual_style`, `set_hud`, `set_detection`, `set_map_stack`, `set_post_processing`, `set_sensor` |
| Context | `get_current_view_state`, `get_entity_context{scope: selected|in_view}`, `describe_view`, `read_board`, `read_insight` |
| Analysis | `analyst_query{layers, scope, filters, sortBy, limit, followUp}`, `next_satellite_pass{target, minElevationDeg}`, `run_scenario` |
| Annotation | `annotate_map{annotations[1..24]: pin|highlight|area|arrow|route|label}`, `clear_annotations` |
| Media | `control_radio`, `control_cctv`, `control_scene` |

Schema tips:
- Use enums wherever the value set is closed.
- Clamp numbers on the server as well as in the schema.
- Return `{ok, error, stage}` so the model can say *where* something failed.
- Give read tools a `limit`, and default to summaries. `include_grid` and `verbose` are opt-in (GS).

## 4. Analyst engine (grounded counting)

- **Records.** `getAnalystRecords()` on each *enabled* layer returns plain records. The engine never fetches data itself.
- **Scopes.**
  - `view`: radius = clamp(altKm × 1.6, 25, 2500) km around the ground point under the view.
  - `radius`: centred on the subject.
  - `region`: a Natural Earth or OSM admin ring, tested with point-in-polygon. **Use every ring of a multipolygon, not just the largest.**
  - `anywhere`.
- **Filters and sorting.** Filters are ANDed. A record that lacks the field is excluded. `eq` is case-insensitive. Sort numerically with id as the tie-break. Limit to 1–50. Include min and max in the summary.
- **Follow-ups.** `followUp` re-filters the previous result set in its original scope. GEV's bug was re-applying the view scope. Reset the stored result set whenever the set of enabled layers changes.
- **Provenance.** Every answer carries `coverage.feedProvenance`, whose overall value is the most severe state across the layers. It also carries a note the model must read aloud: `off`, `STALE (source, age)`, `fallback (source)`, warm-up ("enabled moments ago, counts will rise"), and viewport-bounded ("flights load by viewport").

## 5. Chat agent recipe (GS)

- **Endpoint.** `POST /v1/agent/chat/stream` with body `{message, session_id, context}`.
- **Context injection.** The client snapshots dashboard state on every send: camera and bbox, active layers with counts, selection, polygons with index summaries rounded to 3 decimals, markers, place-context summaries (truncated), and open analyses (top 20). The server prepends it as `<DASHBOARD_CONTEXT>{json}</DASHBOARD_CONTEXT>`.
- **Stream events.** `session`, `token{delta}`, `tool{name, call_id, arguments_preview}`, `tool_output{call_id, output}`, `done{reply, model}`, `error{message}`.
- **Client reading.** Use `fetch` plus `ReadableStream`, not `EventSource`, because `EventSource` cannot POST or send a bearer header. Split frames on `\n\n`, skip lines starting with `:`, and call `reader.cancel()` in `finally`.
- **Streaming UI.** Push an empty assistant message with `streaming: true`, then append each token. Render tool calls as chips, and render `artifact_url` outputs as an inline image or a download.
- **Map actions (missing in GS, so add it).** Add a `map_action` event (or a tool-output convention) such as `{type:'fly_to'|'toggle_layer'|'select'|'draw', …}`, and route it through the same viewmodel mutators the UI uses.
- **External MCP.** Attach per request (SSE, 15 s timeout, cached tool list). If one fails, skip it silently.
- **One registry.** Generate the HTTP routes, MCP tools and agent tools from the same registry (`backend-patterns.md` §1).
- **Sessions.** Keep them in a persistent store if you run more than one replica; in-memory SQLite does not survive restarts.

## 6. Annotations by voice (whiteboard)

- **Pin now, outline later.** Place the anchor pin immediately and resolve the outline progressively (`outlinePending: true`). When the outline arrives, push a silent system item into the conversation.
- **Outline resolution order.**
  1. Geocoding, or Places near the view (within 8 km).
  2. Natural Earth regions.
  3. OSM admin relations.
  4. Bundled neighbourhoods.
  5. The OSM landuse or leisure polygon that encloses the point.
  6. A street centreline buffered by 11 m.
  7. Otherwise a dashed "approximate" disc (400 m for "around").
- **Limits.** At most 24 annotations per call and 120 marks on the board. At the cap, ask the user before clearing.
- **Routes.** Use OSRM. If it fails, draw a straight line labelled "direct line (no route)".
- **Draw tool.** Build the manual draw tool on the same engine (`manual: true`), with no network requests.

## 7. Evidence-first answers (KZ target architecture)

- **Pipeline.** Plan, then retrieve (SQL, spatial and document queries), then build an evidence bundle, then call the LLM, then validate citations. The answer shape is `{answer, evidence[], confidence, limitations}`, traced with Langfuse.
- **Insight cards.** Give them typed citations that resolve to routes (a target, a dataset, a file path). The card and the spoken answer share one cursor.
- **Sovereign deployments.** Point the OpenAI-compatible client at an on-prem gateway via `OPENAI_BASE_URL`, e.g. the `amini-llm` skill's LiteLLM/Qwen gateway, and skip `temperature` for reasoning models.
