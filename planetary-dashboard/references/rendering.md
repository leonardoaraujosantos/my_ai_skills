# Rendering: Cesium and MapLibre recipes that look good and stay fast

## Part A: CesiumJS

### A1. Viewer baseline
```js
const viewer = new Cesium.Viewer(el, {
  animation:false, timeline:false, baseLayerPicker:false, geocoder:false, homeButton:false,
  sceneModePicker:false, navigationHelpButton:false, fullscreenButton:false, infoBox:false,
  selectionIndicator:false, baseLayer:false, msaaSamples:4, requestRenderMode:true,
  maximumRenderTimeChange: Infinity, creditContainer: myCreditsDiv,
});
viewer.targetFrameRate = 60;
viewer.scene.globe.enableLighting = true;          // day/night terminator for free
viewer.scene.skyAtmosphere.brightnessShift = -0.08; // slightly moodier
```
- **Keyless imagery.** Use `new Cesium.UrlTemplateImageryProvider({url: ESRI_URL, credit: 'Powered by Esri'})`. After two tile failures, fall back to `OpenStreetMapImageryProvider`.
- **Keyless terrain.** `await Cesium.CesiumTerrainProvider.fromUrl('https://terrain.reearth.land/cesium-mesh/ellipsoid')`, falling back to `EllipsoidTerrainProvider`.
- **Photoreal upgrade.** Use `Cesium.createGooglePhotorealistic3DTileset({key})`, or the ion asset `2275207` when you have an ion token. **Hide the globe** (`globe.show = false`) while tiles are shown. Set `cacheBytes` to about 1.5 GB for smooth flying.
- **Ctrl+wheel pinch.** Add `CameraEventType.WHEEL` with the CTRL modifier to the zoom event types. Scale pixel-mode deltas ×8 and clamp them to 120 px, so trackpad pinch works.

### A2. Render governor: keep an idle globe at about 0 % CPU
- Leave `requestRenderMode = true` in place. Keep a `Set` of named **holds**, for example `tracked-entity`, `style-anim`, `camera-orbit`, `flights`, `detection` and `cockpit`.
- While any hold exists, render continuously. When the last hold is released, render one settling frame and go idle again.
- When `document.hidden`, set `useDefaultRenderLoop = false`.
- Layers call `requestRender('layer-tick:<id>')` after each data update.
- For debugging, keep a ring buffer of the last 16 governor transitions.

### A3. Choosing primitives, from cheapest to most flexible
| Count | Use | Notes |
|---|---|---|
| > 5k points | `PointPrimitiveCollection` / `BillboardCollection` | Update positions in place and never recreate. Starlink "dense" loads 1,500 per frame chunk |
| 100–5k interactive icons | `BillboardCollection` + a parallel `LabelCollection` | Put a per-class SVG silhouette into a texture atlas |
| < 1k rich objects | `Entity` in a `CustomDataSource` | Upsert by id, then sweep ids that are gone (a single `reconcileEntities()` helper) |
| Dense grids and heatmaps | **One canvas → `SingleTileImageryProvider`** | Draw one pixel per cell with alpha scaled by value. This is "far cleaner than 2,500 rectangles" (GS coverage, aurora) |
| Raster analysis result | PNG + `X-Bbox` header → `SingleTileImageryProvider({rectangle})` | Keep track of what is installed by id, so the same URL is never re-added |
| Polygons and lines on terrain | `classificationType: TERRAIN` / `clampToGround` | Prevents z-fighting |
| Buildings | `Cesium3DTileset` (OSM Buildings / Google) + `Cesium3DTileStyle` | Tint per feature. Re-style with `makeStyleDirty()` |

- **Bulk adds.** Add entities in batches of 5,000 inside `entities.suspendEvents()` / `resumeEvents()`, scheduled with `requestIdleCallback` (use `setTimeout` on Safari). Make the job cancellable. This keeps about 47k features responsive.
- **Clustering.** Set `dataSource.clustering = {enabled:true, pixelRange:80, minimumClusterSize:5}`. Draw the cluster discs on canvas and cache them per count bucket. Clicking a cluster flies to its members.
- **Distance fades.** Use `translucencyByDistance: new NearFarScalar(1e6,1,1.5e7,0)` for labels, and `scaleByDistance` together with `disableDepthTestDistance` for callouts.

### A4. Moving things (aircraft, ships, satellites, transit)
- **Render in the past and interpolate** (GEV flights). Draw each contact **30 s behind real time**, placed between the two fixes on either side of that moment along a constant-rate-turn arc.
  - Once the last fix is passed, coast forward for 60–300 s. Keep 5 fixes of history.
  - Run the fleet tick at about 80 ms and limit course slew to 60°/s.
  - Contacts glide smoothly even though the feed only updates every 10–30 s.
- **Evict missing contacts.** Drop a contact after N missed polls, or after 1 missed poll if it looks landed (below 150 m and slower than 23 m/s). After an *incomplete* snapshot, keep missing contacts for a while instead of dropping them.
- **Show staleness honestly.** Dim a contact whose extrapolation window has run out, for example to 45 % alpha, or once dead reckoning exceeds 60 s (KZ). Never draw it as live.
- **Satellites.** Propagate TLEs with `satellite.js` SGP4 in the browser once per second, or better, drive them from the Cesium clock with `SampledPositionProperty` / `CallbackProperty` rather than setting positions from a Svelte `$effect`.
  - Footprint radius: cos θ = R/(R+h).
  - Orbit path: 180 steps.
  - Pass prediction: 24 h horizon, 30 s coarse step, 5 s fine step. A pass is visible when the satellite is sunlit and the sun is at or below −6° for the observer.
- **Heading-correct icons.** Set `rotation = -(heading - camera.heading)` with `alignedAxis: Cartesian3.ZERO`. Set `camera.percentageChanged = 0.05` to throttle updates.
- **3D model swap.** Below about 800 km, swap glyphs for per-class glTF models (airliner, turboprop, bizjet, helicopter, UAV, …).
  - Cap the model count: 150 in proximity mode (add within 150 km, keep within 185 km), 350 in "all" mode, 60 in the cockpit.
  - Clamp the pixel size of a tracked model to 40–200 px.
  - Precompress `.glb` files with brotli/gzip; KZ went from 139 kB to 10 kB. Merge parts to about 10 draw calls.

### A5. Tracking and camera
- **Click to track.** A click only counts if the pointer moved 6 px or less in total. Deselecting on empty space also requires the click to last 400 ms or less. Clicks on trails do nothing.
  - Lock with `viewer.trackedEntity`, a minimum range of 150 m and no zoom inertia.
  - Keep a render hold while tracking.
  - Escape releases the lock without moving the camera.
- **Trails.** Seed trails from a history backfill (OpenSky `/tracks`, adsb.lol traces, AIS track store) and cap them at 400 points. Use constant alpha: 0.85 in front of scene geometry, dimmer behind it.
- **Focus de-emphasis.** While tracking, fade competing contacts to a 0.25 alpha floor (attack 300 ms, release 600 ms).
- **Tilt and north-up.** Oblique pitch is −35° and straight-down is −89°; animate between them over 650 ms. Pick the pivot with `pickPosition` → `globe.pick` → `pickEllipsoid`, or use the tracked entity. Any pointer-down or wheel event cancels the animation.
- **Reset to globe.** Fly to 18,000 km over the current sub-camera point at heading 0, pitch −90°. Exit cockpit or tracking first. Add a watchdog, and make the reset idempotent.
- **Use the view centre, not the bbox centre, when tilted.** A tilted view's bbox reaches the horizon (GS `viewCentre`). Regional queries should use the ground point under the centre of the canvas.
- **Displayed altitude is MSL.** Apply EGM96 `h = H + N` (`egm96-universal`, loaded lazily), cached per 0.01° cell.
- **Ground clamping on photoreal mesh.** Sample the mesh and accept it only if it lies within −15/+80 m of a DEM prior. This rejects cranes and bridges.

### A6. Sensor looks (post-processing)
Build each look as a `PostProcessStage` fragment shader, crossfaded over 500 ms:

| Look | Recipe |
|---|---|
| CRT | pixelation, barrel distortion, jitter, chromatic aberration, Bayer dither, shadow mask |
| NVG | P43 green phosphor, gain, tube vignette, honeycomb, scanlines, timestamp + reticle |
| FLIR | luminance → white-hot/black-hot or an Ironbow palette, bloom |
| Noir | contrast, grain, vignette, 15 % sepia |
| Anime | cel shading + edges |
| Snow | 5 particle layers + frost |
| Hologram / glass (KZ) | colours read from CSS tokens so they follow the brand |

- Hold continuous rendering only for shaders that use `time`.
- Bloom: map strength through a smoothstep onto contrast, brightness, sigma and step size.
- Sharpen: an unsharp mask.
- Scope/keyhole mask: a 2D canvas above the globe with feathered edges.

### A7. Detection overlay ("everything in view gets a box")
Draw screen-space brackets and IDs on a 2D canvas above the globe.
- **Density modes:** OFF / SPARSE / BALANCED / DENSE, with density snapping to 0/25/50/75/100.
- **Budgets:** a cohort of 256 (max 900), a collision budget of about 96, and occluder refresh every 100 ms.
- **Label arbiter:** a 32 px spatial hash with quotas per layer (elastic or weighted). Fade in 150 ms, fade out 300 ms, minimum lifetime 2.5 s, cooldown 1.2 s. This stops labels from flickering.
- **Accessibility:** mirror what the canvas shows into a visually-hidden "Visible map targets" list.

### A8. Weather and fields
- **Wind streamlines.** Decode a GRIB2 u/v field on the server, resample it to 1°, and ship it as a binary grid.
  - Advect about 7,200 particles on the GPU (1,200 on narrow screens), 12 km above the surface.
  - Fall back to a 2D canvas when the GPU path isn't available.
  - Fade trails with `destination-out`.
- **Observed radar, clouds and lightning.** Put them on one shared playback clock. Use frame-gap tolerances (30 min for radar, 3 h for global IR). When a frame is missing, keep the last good one and say so.
- **Cyclones.** Draw a point, the track and the forecast cone, and attach the geometry only when the advisory numbers match.
- **FIRMS LOD by altitude.**
  - Above 9,000 km: 2° heat cells.
  - Above 3,000 km: 1° cells.
  - Closer in: glow sprites.
  - Use ±10 % hysteresis between levels.

## Part B: MapLibre GL (KZ recipes)

### B1. Terrain, sky and a real sun
```js
map.addSource('dem', { type: 'raster-dem', tiles: [TERRARIUM], encoding: 'terrarium', tileSize: 256, maxzoom: 15 });
map.setTerrain({ source: 'dem', exaggeration: 1.6 });
map.addLayer({ id: 'hillshade', type: 'hillshade', source: 'dem',
  paint: { 'hillshade-illumination-direction': sun.azimuth, 'hillshade-method': 'igor' } });
map.setSky(skyFor(sun)); map.setLight(lightFor(sun));
```
- Compute the sun position with the NOAA algorithm. For legibility, clamp its rendered altitude to 6–75°. Keep a light intensity floor of 0.38 so night views never go black.
- **Colour relief.** Use the `["elevation"]` expression, stretched to the elevation range of the current window.
- **Index contours** that fade with zoom.
- **Fake ground shadows.** Add a flat fill under each building, translated with `fill-translate` interpolated by zoom.

### B2. Buildings that look expensive
- `fill-extrusion` with `fill-extrusion-vertical-gradient` and a height-ramp colour.
- **Roof cap.** A second extrusion with `base = height − 0.3` in a lighter tone.
- **Hologram crown.** `base = height − 0.6` with a glow colour.
- **Edge glow.** Two passes: a wide, blurred line, then a thin sharp line.
- **Lidar photons (ICESat-2).** Draw each photon as a tiny fill-extrusion square with per-feature `base` and `top`.

### B3. Beyond the style spec
- **Underground (drill cores, traces, a deck floor).** Use `CustomLayerInterface` raw WebGL, because fill-extrusion cannot go below zero. The cutaway view turns terrain off, makes the satellite layer translucent and hides the hillshade.
- **glTF in MapLibre.** Render three.js inside MapLibre's GL context. Call `renderer.resetState()` before and after each draw, and scale with `meterInMercatorCoordinateUnits()`.
- **Imagery drapes.** Use an `image` source with four corner coordinates, e.g. Sentinel-2 band-ratio PNGs.
- **Swipe compare.** Use a second map and sync the cameras with a re-entrancy flag. Split with CSS `clip-path: inset()` on both maps.
- **Flow particles.** Update a GeoJSON source with `setData` inside requestAnimationFrame, capped at about 30 fps. Show a still frame when reduced motion is on, and stop when the tab is hidden.

### B4. Data delivery
- **Small layers:** GeoJSON with 5-decimal coordinates, `-simplify` applied, and only the web fields.
- **Anything above a few MB:** PMTiles (tippecanoe from the GeoPackage). Serve it through a range-capable static route with ETag. Never ship a 16 MB GeoJSON.
- **Keyless basemaps:** CARTO GL styles or Esri raster. Self-host Protomaps PMTiles for sovereign or offline deployments.
