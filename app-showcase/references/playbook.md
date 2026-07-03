# App Showcase — Playbook (methodology + gotchas)

Read this before capturing. It encodes lessons that otherwise cost several iterations.

## Discovery: grounding the content

- **`openspec/specs/`** = shipped capabilities (source of truth). **`openspec/changes/`** (not archived) = roadmap. **`openspec/changes/archive/`** = already shipped. This is the best material for a feature list, a comparison table, and an honest roadmap slide.
- **No openspec?** Read `README.md`, `docs/`, ADRs/architecture docs, then skim routes/components/domain models. If the user wants durable specs, invoke the `openspec` skill to reverse-engineer a baseline first.
- Distill: value prop (1 line), 3–6 differentiators, real feature list (shipped vs planned), audience, and — for a pitch — the status-quo/competitor you argue against.
- Be honest: a "coming soon" screen is roadmap, not a shipped feature. Put unshipped items under a labeled **Roadmap**.

## Getting the app running

- Hosted URL → use directly. Local repo → start the dev server (`just web`, `npm run dev`, `pnpm dev`, …) as a background process and wait until it serves before probing.
- Confirm the login/entry route and whether auth is required.

## Selector discovery (do NOT guess selectors)

```bash
$SKILL/scripts/capture.py probe <url>                 # unauthenticated (e.g. /login)
$SKILL/scripts/capture.py probe <url> --state auth.json  # authenticated (DOM differs!)
```
Prefer, in order: `aria-label`, `data-testid`, visible text (`get_by_text`/`:has-text`), stable role. Avoid framework hash classes (`svelte-xxxx`, CSS-modules) — they change.

## Storyboard schema (capture.py run)

See the header of `scripts/capture.py` for the full action list. Skeleton:
```json
{
  "base": "https://app.example.com", "viewport": [1440,900], "scale": 2,
  "state_file": "auth.json",
  "auth": { "url": "/login", "success_url_contains": "/app", "steps": [
      {"fill":"input[type=email]","value":"USER"},
      {"fill":"input[type=password]","value":"PASS"},
      {"click":"button[type=submit]"} ] },
  "scenes": [
    {"out":"shots/home.png","steps":[{"goto":"/app"},{"wait":2500},{"screenshot":null}]},
    {"out":"shots/search.png","steps":[
       {"goto":"/app"},{"wait":1500},{"click":"button:has-text('Search')"},{"wait":1000},
       {"type":"your query","delay":40},{"wait":1500},{"screenshot":null}]}
  ]
}
```
Iterate: run → Read the PNG → fix steps. Capture at `scale: 2`.

## Gotchas (observed in the wild)

1. **Auth is async.** Clicking submit doesn't immediately navigate. Wait on the destination URL (`success_url_contains` / `wait_url`), not a fixed sleep, then settle ~3s. A button stuck on "Signing in…" means you screenshotted mid-request.
2. **Hover-revealed buttons.** "+"/action buttons are often `opacity:0` until the row/section is hovered. `hover` the container first, then `click` with `"force": true`.
3. **Create ≠ navigate.** A "New page/item" button may just add it to a list without navigating. After it, click the new item (or read its href) to open it.
4. **Titles can be `contenteditable="plaintext-only"`** (not `"true"`), so a `[contenteditable='true']` selector misses them — use `h1[contenteditable]`. Pressing Enter in such a title may NOT move to the body; click the body element explicitly to type there.
5. **Don't `Control+A` inside a rich-text body** — it can select the whole editor (title + body) and the next keystroke wipes everything. Clear a field with `End` + repeated `Backspace` instead (`{"repeat_press":"Backspace","n":40}`).
6. **Markdown shortcuts may not auto-convert.** In some editors `## ` stays literal. Use the block/slash menu: type `/`, then the block name, then Enter. Screenshot the open menu — it's a great "how to add blocks" shot.
7. **Inline toolbars** (bold/link/comment) appear on text selection — use the `select_text` action (drag-select) to reveal and capture them.
8. **"Import"/"Export"/"Settings" are often dialog routes** (e.g. `/app?settings=workspace/import`), not standalone pages. Direct-navigating `/app/import` may render blank; instead click the sidebar link, or open settings then click the section. Give SPA dialogs 3–4s to render.
9. Viewport is CSS pixels; a `scale: 2` screenshot is 2× those dimensions. `getBoundingClientRect` returns CSS pixels — compute mouse coordinates in CSS px.

## gws (Google Slides/Drive) quirks — used by slides.py

- `gws` prints a `Using keyring backend: keyring` line before JSON; parse from the first `{`. (slides.py handles this.)
- Slides object IDs must be **≥ 5 chars** (`s_0001`, not `s1`).
- `gws drive +upload <file>` takes the file as a **positional** arg (not `--file`). Make public with `permissions create {"role":"reader","type":"anyone"}`; embed as `https://drive.google.com/uc?export=download&id=<ID>`.
- `createImage` fetches the URL server-side at insert time, so the image must be public first.
- Verify visually: export to PDF (`gws drive files export … application/pdf`) and Read it. **Fonts render taller than expected** — keep titles to ~1 line, give text vertical room, and re-check every slide. `slides.py` is idempotent: pass the presentation id to delete+rebuild.

## Hygiene & authorization

- Only drive apps the user owns or is authorized to test. Prefer dev/staging.
- Treat credentials as secrets: pass them through the storyboard at runtime; don't commit them. Delete the `auth.json` state and any storyboard containing a password when done.
- Build demo content in a **private/disposable** area and trash it afterward (via the app's page/⋯ menu).

## Worked example (what a good editor-demo capture looks like)

Goal: a "here's a finished page" screenshot with varied blocks.
1. Create a page in a private section (`hover` Private → `force`-click the "+").
2. Open it (click the new sidebar item).
3. `h1[contenteditable]` → clear with End+Backspace×30 → type the title.
4. Click the first body block (`div[contenteditable='true'][data-placeholder]`).
5. For each structural block: `type "/"` → `type "Heading 2"` (or "Bulleted", "To-do", "Callout") → `press Enter` → type the text → `press Enter`.
6. Deselect (`Escape`, click empty space), screenshot.
7. Trash the demo page afterward.
