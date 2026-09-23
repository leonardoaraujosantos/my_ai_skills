# Feature catalog: proven recipes to pick from

Every feature here has shipped in GEV, GS or KZ. Each entry gives what it is, how to build it, the constants that make it feel right, and the traps to avoid. Build them in tiers: pick the core first, then add wow features.

---

## Tier 1: core (every dashboard)

### Layer toggles with feed state
See `architecture.md` §4–5. Each toggle row shows its state, source, age and error.

### Search that works offline first
Resolve a query in this order:
1. **Decimal coordinates.** Accept `30.2 N 97.7 W` or `-33.9, 151.2`. Reject mixes of sign and hemisphere letter, and anything out of range.
2. **Bundled city/POI presets.** NFKD-fold both sides and require an exact match.
3. **Google geocoding** if a key is set.
4. **Photon.** Bias it softly with the view centre. If the biased hit's name doesn't start with the query, retry unbiased.
5. **Nominatim** through the 1 req/s proxy queue.

Chain rules:
- 12 s total timeout.
- Cache 64 queries: hits for 5 min, answered misses for 30 s.
- Never cache failures.

Frame the result by kind: region overview, city, neighbourhood, street corridor or precise place.

### Share links (URL hash state)
- **Contents.** Serialize camera, style, map stack, layers, layer options, panels and **at most one tracked target** into `#v=2&lat=&lon=&alt=&heading=&pitch=&style=&map=&l=<tokens>&lo=<options>`.
- **Layer tokens.** Give each layer a one-character token. If any token in a payload is unknown, reject the whole layer payload; the camera still restores.
- **Writing.** Use `history.replaceState`, debounced by 500 ms. Suppress writes until the initial restore has finished.
- **Live targets are handoffs, not bookmarks.** Copy Link adds `at=<epoch>`. On restore, track the target only within its freshness window: 90 s for flights, 45 s for military, 300 s for satellites.
- **Restore lanes.** The visual, map and panel lanes can each be claimed by a newer user action. Restore must never override something the user has just changed.
- **KZ variant.** `?site=&at=lon,lat,zoom,pitch,bearing&overlay=&compare=`. Because it is URL-addressable, the same format also works for tours and tests.

### Click-to-track and entity cards
See `rendering.md` §A5. The card is protected: it never loses a collision fight, and nearby competitors dim.

### Credits and attribution lightbox
- Register static credits once. Add dynamic credits while their layer is active.
- The on-screen line is always visible.
- Put full attributions in a keyboard-accessible lightbox. Keep its text verbatim from `DATA_SOURCES.md`.

---

## Tier 2: situational awareness

### Global Context: staged modes
Entering a mode (Contacts, Space Missions) does four things:
1. Snapshots the enabled layers and any changed params.
2. Clears unrelated layers.
3. Enables the mode's dependencies.
4. Forces detection on.

Exiting replays the snapshot and honours changes the user made during the mode. Turning a dependency off by hand exits the mode. Also snapshot the **camera** if you promise "get your exact view back"; GEV forgot to.

### Contacts roster (250 km)
- **What it fuses.** Aircraft, military aircraft, vessels and mapped installations within 250 km of a subject. If nothing is in range, the search radius doubles outward, up to 16,000 km.
- **Refresh.** Every 750 ms while parked, 175 ms while the camera moves, with 250 ms of settle hysteresis.
- **Paging.** Rows page 3 at a time and rotate every 10 s.
- **Navigation.** PREVIOUS goes to the last visited contact. NEXT goes to the nearest unvisited one. FOCUS centres the current one.
- **Label.** Mark the roster "AVAILABLE INPUTS ONLY · NOT AN ALL-CLEAR". Installation counts carry "viewport feed is not a complete survey".

### Cockpit view
Enter with `C` while an aircraft is tracked. It shows instruments, a vision cycler, the contacts window and a regional brief. The brief combines three sources:
- a Nominatim reverse geocode;
- Open-Meteo weather;
- news: Google News RSS, falling back to GDELT over a 48 h window.

The brief is cached per 0.1° cell for 5 min and may be served up to 1 h stale. It is marked `partial` when a source fails.

Fly-to and reset are refused while in the cockpit: "Exit cockpit to fly to a city".

### Place-context panel (GS)
Opens on every search result or map click. It fetches seven slices in parallel:
- weather
- climate
- land surface temperature
- Wikipedia (truncated to 600 characters)
- air quality
- quakes
- news (top 5)

Each slice has its own state: `idle | loading | success | error | disabled`, where `disabled` means "key not configured". One `AbortController` per selection plus a `seq` guard keep results from arriving out of order.

### Nearest live camera handoff
- Enabling cameras with no active camera selects the nearest one. The camera flies there only if nothing else owns it, for example tracking or the cockpit.
- **Build the handoff from a tracked fire or vessel to the nearest camera properly.** GEV advertised it but never implemented it.
- **Camera frame proxy.** Registry only. If the frame fetch fails, fall back to Street View at the camera's *registered* pose, then to a synthetic SVG. Rate-limit the fallback: otherwise it becomes an open, billable Street View proxy.

### Weather timeline
- Observed radar, clouds and lightning run on one shared clock, alongside forecast wind (GFS/IFS) and cyclone cones.
- Keep the last good frame and say so: "Frame unavailable; previous observation retained".
- GS alternative: RainViewer frames at 600 ms per step with play/pause.

---

## Tier 3: analysis on the map

### Draw and analyse polygons
Drawing uses its own `ScreenSpaceEventHandler` and holds the pointer lease. Controls:
- left-click adds a vertex;
- Enter, double-click or right-click finishes;
- Esc cancels;
- Ctrl/Cmd+Z removes the last vertex.

Area uses spherical excess and perimeter uses great-circle distance. Export as GeoJSON, and persist to `localStorage` under a versioned key.

On a finished polygon, run the analyses:
- spectral index time series, streamed over SSE and shown as a sparkline;
- a PNG preview draped on the polygon;
- a compliance or deforestation verdict;
- zonal stats.

See `backend-patterns.md`.

### Terrain profiles, line of sight and RF
- **Profiles.** Sample 200 great-circle points along a line with `sampleTerrainMostDetailed`.
- **Line of sight.** Line plus the Fresnel ellipsoid: r₁ = ½√(λd). Orient it with heading −90° and pitch equal to the line-of-sight slope.
- **Coverage.** Radio-horizon rings using the 4/3-Earth model. Coverage heatmaps are drawn as a canvas imagery layer.
- **Server work.** Post the profile to the server for ITM or P.1812 path loss.

### Choropleths and risk colouring
- **Admin-2 choropleth.** 3-stop scale.
- **Risk bands.** LOW `#4ade80` · MEDIUM `#facc15` · HIGH `#fb923c` · EXTREME `#f87171`.
- **Overlay priority.** When several overlays apply, the order is flood > peril > band.

### Recent satellite imagery for a box
The user draws a box. Box rules:
- at most 1,000 km on a side;
- within ±85.05° latitude;
- must not cross the dateline;
- a single pin becomes a 10 km box.

Search the last 30 days of HLS 30 m imagery through CMR, paging 200 at a time up to 2,000 results. "Clear" means ≤ 20 % cloud. Tiles come from GIBS and thumbnails from Worldview Snapshots.

Show the result as a before/after swipe against Esri.

### Scenario and route economics (KZ)
- Snap OSM ways to a ~60 m grid and run Dijkstra on cost per tonne.
- Keep every coefficient in one `assumptions.ts` file and **show the coefficients next to each result**.

### Trust-gated rankings (KZ targets)
A ranked target counts as *trusted* only if all three hold:
- the model run is complete;
- the blind-site hit rate is at or above the threshold;
- a competent person has signed it off.

Blocked targets stay visible but unranked, with their block reasons shown.

---

## Tier 4: wow

### Scene director and cinematic tours
- **Scene document.** A versioned, strictly validated scene document:
  - limits: 5 MiB, 256 scenes, 10k shots, nesting depth 24;
  - refuse `__proto__`, `constructor` and `prototype` keys;
  - errors never echo the input values.
- **Shots.** Each shot has camera, visual, layers, duration and hold. Optional parts:
  - named ellipsoid anchors;
  - authored moves (linear or cubic-in-out, with shortest-arc heading and longitude);
  - data packs: GeoJSON, PNG or media, SHA-256 pinned and ≤ 8 MiB each;
  - interactions: card, focus, shot and layer actions.
- **Playback.** Phases run select → visual → layers → travel → settle → hold. Any pointer or wheel input stops playback and hands the camera back to the user.
- **Sharing.** Share scenes as `.gevbundle.json` with base64 assets, verified by hash. Nothing applies until the user confirms a preview.
- **KZ tours.** Tour steps are **URLs**, so the tour needs no internal hooks. Other rules:
  - the last navigation wins (nav token);
  - time on a step is measured by wall clock, so a background tab doesn't slow it;
  - the tour pauses when the user navigates.

  Site flights are pure functions of (geometry, progress 0..1), applied with `jumpTo` on each animation frame.

### Swipe compare and time slider
- **Swipe.** Two synced maps with a CSS `clip-path` divider (`rendering.md` §B3).
- **Time slider.** Filter by year and show a histogram of counts with a play step.
- **Cesium alternative.** Use the clock and a `SampledProperty` instead of re-rendering.

### Digital twin with underground
Terrain plus extruded buildings with roof caps and glow, lidar photons, Sentinel-2 drapes, and drill cores rendered below ground through a custom WebGL layer. See `rendering.md` Part B.

### Sensor styles and the detection overlay
See `rendering.md` §A6–A7. Switch styles with the keys `1`–`7`, and give each one its own HUD palette.

### Voice agent and analyst answers
See `ai-agents.md`.

### Recording mode
- Hide the panels and show a 16:9 or 9:16 safe frame. Keep the credits visible.
- A run log downloads as JSON.
- Pair it with a GIF/MP4 recorder script: CDP `Page.startScreencast` plus an ffmpeg palette.
