# UI design: making it feel like a forbidden cockpit, and still usable

Three looks have held up in production:
- **GEV:** "Apple meets Blade Runner". Dark glass panels with cyan accents and mono kickers.
- **GS:** a design-system look. Token-driven, dark by default, with a light override.
- **KZ:** a sovereign-client look. A brand kit feeds an app token layer, with one accent colour and a separate data colour.

Choose a look deliberately. The rules below apply to all three.

---

## 1. Tokens first

```css
:root {
  --bg: #0a0a0f;  --glass: rgba(12,12,20,.72);  --glass-border: rgba(255,255,255,.08);
  --accent: #00d4ff;  --accent-dim: rgba(0,212,255,.15);  --accent-glow: rgba(0,212,255,.4);
  --text: #e8eaed;  --text-2: rgba(232,234,237,.5);  --text-3: rgba(232,234,237,.3);
  --ok: #5cffc6; --warn: #ffdc78; --err: #ff5c6e;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;  --font-sans: Inter, system-ui, sans-serif;
  --radius-panel: 16px; --radius-btn: 10px;
  --ease: cubic-bezier(.4,0,.2,1); --t-fast: 150ms; --t-smooth: 300ms;
}
```
- **Layering (KZ).** Brand-kit tokens map to app tokens (`--k-*`, `--series-1..6`, `--status-*`, `--chart-*`), and components read only the app layer. To re-skin for a new client, swap the brand kit. Component code stays the same.
- **Colour roles.**
  - Use one **accent** for interaction and focus, and never as a fill.
  - Keep a **separate data palette**, validated for colour-vision deficiency.
  - Always pair a status colour with an icon **and** a label.
- **Theme before first paint.** An inline script in `app.html` reads `?theme=` or `localStorage` and sets `data-theme` before paint, so there is no flash.
- **Tie the HUD colour to the active sensor style.** NVG is green, FLIR white, CRT amber, and the default is the accent.
- **Test the tokens.** Every `var(--x)` referenced from JS or TS must be defined somewhere. A missing token fails silently to white.

## 2. Layout map (desktop)

```
┌ title/logo (top-left) ─────── globe actions (top-centre) ─────── style/HUD mode (top-right) ┐
│ [clear layers] [share] [tilt] [north] [reset globe]                                           │
│                                                                                               │
│ LEFT STACK (x 52, 26vh)                                        RIGHT CONTEXT RAIL (w 330)     │
│  DATA LAYERS (grouped)            3D GLOBE                     DISPLAY · CCTV · WEATHER ·     │
│  SCENES / DIRECTOR                                             CONTEXT (contacts/missions)    │
│                                                                                               │
│ credits (always visible)   [ visual presets | 🎙 voice | location/search ] dock   POWER UP ⚡  │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```
- **Panel stack arbitration.**
  - Expanded panels share height, each with a floor of 96 px.
  - A later panel auto-collapses when it would get less than 50 % of its natural height.
  - The first panel never collapses.
  - Dock "wings" open on hover or focus after 140 ms, close after 420 ms, and can be pinned.
- **Floating panels (GS, KZ).** Draggable by the header, resizable, and scrollable inside. Remember each panel's position per browser. Use them for place context, entity detail, agent chat and analysis.
- **Breakpoints.**
  - ≤ 900 px: compact dock.
  - ≤ 720 px: the left stack takes the top half and the right rail the bottom half, above the credits. Globe actions move to a top-right column.
  - ≤ 520 px: logo only.
- **Credits.** The imagery credit line is **never** hidden, including in clean-view and recording modes. Provider terms require it.

## 3. Layer panel

- **Grouping.** Group layers as Movement, Cameras, Infrastructure, Events, Weather and Utilities. Generate the groups from the layer registry.
- **Row layout.** Each row has an icon, name, count (`1.2K`) and toggle. Below that, show a meta line: `<STATE> · <source> · <age> · <error> · retry Ns`.
- **Toggle labels.** Label the toggle with the **feed state**, not just on/off: `OFF | ON | LOADING | DEGRADED | STALE | PARTIAL | FALLBACK | UNAVAILABLE | KEY REQUIRED`.
- **Accessible name.** Make it name, state and key guidance, for example "Active Fires: KEY REQUIRED. Add FIRMS_MAP_KEY in Provider Settings".
- **Row body (GS).** A card body that is disabled while the layer is off. It holds filters, a one-line legend ("size = magnitude · colour = depth"), and `tooLarge`/`rateLimited` hints.
- **Legends list only what is drawn.** Tag each legend entry with a **trust label**: LIVE, REAL, MODEL, SCREENING, NOT OBSERVED or SIMULATED (KZ).
- **Global loading chip.**
  - Reveal it after 160 ms, so fast loads never flash.
  - On success, dwell 2.2 s. On failure, dwell 5 s.
  - Guidance states ("zoom in") are not faults.
- **Split-flap text** on status chips: 190 ms per character, 26 ms stagger. Never replace the text node, so screen readers announce the change only once.

## 4. The "cockpit" look, used honestly

- **Intel HUD.**
  - Decorative classification banners and a REC blink.
  - Readouts: MGRS, lat/lon, GSD/NIIRS, MSL altitude, sun elevation.
  - An AI one-line summary, refreshed every 15 s. It must include a feed-state token whenever a feed is not nominal.
  - Offer tactical, operator and minimal layouts.
  - Show the HUD automatically for the CRT, NVG and FLIR styles, with the `H` key as an override.
  - Mark the decorative parts `aria-hidden`.
- **Cockpit (inside a tracked aircraft).**
  - Speed and altitude rims, a heading tape and a UTC clock.
  - A vision cycler.
  - A CONTACTS · 250 KM window, with the banner "AVAILABLE INPUTS ONLY · NOT AN ALL-CLEAR".
  - A briefing carousel labelled "SOURCE-BACKED EVENTS · NO SYNTHETIC NEWS".
- **Honest refusal (KZ war room).** A brief that has no data returns **no numbers**. It names the data gaps and the method instead.
- **Copy.** Uppercase mono kickers ("MISSION CONTROL · FIRST LAUNCH"). Sentence case for everything else.

## 5. First-run and empty states

- **Launcher.** A non-modal launcher titled "Choose your first view" with four tiles: **Live Contacts**, **Space Missions**, **Environmental** and **Explore Manually**. The Environmental tile flies to the globe *while* it enables quakes and fires.
- **Dismissal.**
  - "Don't show again" is stored in `localStorage`.
  - Any other dismissal is stored in `sessionStorage`, so the launcher returns next session.
  - `?welcome=0|1` overrides both.
- **Deferral.** Defer the launcher while the cockpit, scene playback or recording is active.
- **Mission failure.** Keep the launcher open and show "Could not open that mission (ids). Retry or explore manually."
- **Key upsell.** A bottom-right chip reads "POWER UP · N KEYS WAITING". It opens Provider Settings, which lists each key, what it unlocks, its tier (metered or free) and where to get it.

## 6. Accessibility (enforced by tests in GEV)

- Use **one** global `:focus-visible` outline rule. No component may remove it.
- Busy controls use `aria-busy` + `aria-disabled`, never native `disabled`, so focus is not lost.
- **Escape.**
  - Collapses the nearest expanded panel that contains focus; nested panels collapse first. Focus returns to the disclosure control.
  - Surfaces (first-run, settings) trap Esc and Tab and restore focus afterwards.
  - Watch for several independent document listeners all handling one Esc press. GEV has this bug.
- **Keyboard shortcuts.** Ignore them while focus is in a form field. Document every one.
  - `1`–`7`: styles
  - `H`: HUD
  - `O`: orbit
  - `V`: clean view
  - `F`: layers panel
  - `D`: detection
  - `C`: cockpit (when tracking)
  - Q–T: points of interest
  - Hold Space for 500 ms: push-to-talk
- **Reduced motion.** Disable logo gaze and parallax, shorten the split-flap animation, flatten route banking, and show a still frame of particle flows. Any timer that waits on `transitionend` needs a fallback timer.
- **Icons.** Subset the Material Symbols font with `icon_names=`, and have a test that fails when a new icon is missing from the subset.

## 7. Charts next to a globe

- **Keep charts small and hand-built.** Use SVG sparklines, bar rows, stat tiles and capture curves. Put the geometry in pure, tested helpers, e.g. a `linearScale` that guards against a flat domain.
- **Use a library only for layout-heavy charts.** d3-sankey for lineage, d3-force for graphs.
- **Choropleths.** Use 3 stops from min to max, collapsing to 1 stop when the data is flat. Put the legend caption in the layer card.
- **Charts from an agent.** The server renders a PNG and returns a signed URL, which the chat shows inline (GS).

## 8. i18n and branding for clients (KZ)

- **Typed message keys.** Split them into per-area namespaces (`common`, `shell`, `twin`, …). Run a strict check for missing keys, orphan keys and hard-coded English.
- **Client marks as data.** Emblem, ministry lines, lockups for dark and light, and the agency seal. Render them in a fixed order.
- **Deployment-specific rules** go in a `contexts/<client>/CONSTITUTION.md`.
