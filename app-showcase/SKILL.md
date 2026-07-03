---
name: app-showcase
description: Create a polished sales pitch/presentation (Google Slides) OR a screenshot-driven user manual (PDF) for a software product. Drives the live app with Playwright (web) or a mobile simulator to capture REAL screenshots, authenticates with supplied credentials if needed, and grounds every claim in the product's openspec/ folder (or baseline specs generated from the source code + docs). Use when the user asks to build a pitch deck, product presentation, feature comparison, onboarding/user guide, tutorial, or manual for an app they can point you at (URL, local dev command, or repo).
argument-hint: pitch|manual <app-url-or-repo> [--auth user:pass] [--mobile ios|android]
allowed-tools: Bash, Read, Write, Edit, Skill, Agent
---

# App Showcase — pitches & manuals from a running product

Turn a real, running application into a **Google Slides pitch** or a **screenshot-driven PDF manual**. The core idea: *never invent screens or features* — discover the product from its own specs/source, drive the live app to capture real screenshots, and assemble a polished artifact.

This skill has three phases. Do them in order.

```
1. DISCOVER   understand the product  → grounded, accurate content
2. CAPTURE    drive the app w/ Playwright → real screenshots (shots/)
3. ASSEMBLE   → Google Slides pitch  OR  PDF manual
```

Work in a scratch dir (use the session scratchpad if one exists). Everything below references helper scripts in this skill:

```
SKILL=~/.claude/skills/app-showcase
$SKILL/scripts/capture.py     # storyboard-driven Playwright screenshotter (+ selector probe)
$SKILL/scripts/manual_pdf.py  # JSON spec → styled HTML → PDF (chromium print)
$SKILL/scripts/slides.py      # JSON deck spec → Google Slides (create + upload images + batchUpdate)
$SKILL/references/playbook.md # methodology, selector discovery, hard-won gotchas (READ THIS)
$SKILL/references/mobile.md   # iOS Simulator / Android emulator / mobile-web capture
```

**Read `references/playbook.md` before capturing** — it holds the non-obvious lessons (auth timing, contenteditable quirks, hover-to-reveal buttons, settings-as-dialog routes, gws output quirks) that will otherwise cost you several iterations.

---

## Phase 1 — DISCOVER the product

Goal: a faithful mental model of what the product *is* and *does*, so the deck/manual is accurate and defensible.

1. **Prefer `openspec/`.** If the repo has an `openspec/` folder, read it — `specs/` is the source of truth for shipped capabilities, `changes/` (non-archived) is the roadmap, `changes/archive/` is what already shipped. This is the single best grounding source.
2. **No openspec? Generate a baseline.** Read `README.md`, `docs/`, architecture docs, and skim the source (routes, components, domain models). If the change is substantial and the user wants living specs, invoke the **`openspec`** skill to reverse-engineer baseline specs first. Otherwise just build an internal feature map from README + docs + code.
3. **Extract the story:** the one-line value prop, the top differentiators, the real feature list (shipped vs planned), and the target audience. For a **pitch**, also identify the competitor/status-quo you're arguing against. For a **manual**, identify the primary user tasks in order.
4. Write these down (a short `discovery.md`) — you'll turn them into slides/sections.

Delegate broad reading to an `Explore`/`general-purpose` agent when the repo is large; keep the conclusions, not the file dumps.

## Phase 2 — CAPTURE real screenshots

You need a way to reach the app: a **URL** (hosted or local dev server), or a command to start it (`just web`, `npm run dev`, …) — start it if needed and wait until it responds. Then drive it with `capture.py`.

**Step A — discover selectors (don't guess).** For each screen you plan to shoot, probe the DOM:
```bash
$SKILL/scripts/capture.py probe <url> [--state auth.json]
```
It prints buttons/links/aria-labels/testids/hrefs with coordinates. Use these to write reliable steps. Re-probe after auth (the authed DOM differs).

**Step B — write a storyboard JSON** describing login + each scene, then run it:
```bash
$SKILL/scripts/capture.py run storyboard.json
```
See `references/playbook.md` for the storyboard schema and every action type. Minimal shape:
```json
{
  "base": "https://app.example.com",
  "viewport": [1440, 900], "scale": 2,
  "state_file": "auth.json",
  "auth": { "url": "/login", "success_url_contains": "/app",
    "steps": [ {"fill": "input[type=email]", "value": "USER"},
               {"fill": "input[type=password]", "value": "PASS"},
               {"click": "button[type=submit]"} ] },
  "scenes": [
    { "out": "shots/home.png", "steps": [ {"goto": "/app"}, {"wait": 2500}, {"screenshot": null} ] }
  ]
}
```
- Auth runs once and saves `auth.json`; every scene reuses it.
- **View each screenshot with Read as you go** and fix the storyboard — this is iterative. Capture at `scale: 2` for crisp images.
- To demonstrate the editor/app *doing* something (typing, opening menus), script the interaction (type text, press `/`, select text to reveal toolbars). Build demo content in a *disposable/private* area and clean it up afterward.
- **Mobile:** for mobile-web/PWA set `"device": "iPhone 15"` (any Playwright device). For native iOS/Android apps, see `references/mobile.md` (Simulator/emulator + `xcrun simctl io … screenshot` / `adb exec-out screencap`, or Appium/Flutter integration driving).

**Authorization & hygiene:** only drive apps the user owns or is authorized to test. Treat supplied credentials as secrets — never hard-code them into committed files; pass via the storyboard at runtime (or env). Prefer a dev/staging environment. Create demo data in private/disposable spaces and trash it when done. Report honestly what you saw (a "coming soon" screen is "coming soon", not a shipped feature).

## Phase 3 — ASSEMBLE

### Option A — Google Slides pitch
Best when the goal is persuasion (why this product / vs a competitor).
1. **Generate custom illustrations** (optional but high-impact): use the **`generate-image`** skill for a cohesive set (one consistent style/palette, dark or light theme to match). Section heroes + a title emblem. Run several in parallel.
2. Write a **deck spec JSON** (title / cards / section+image / comparison table / closing) and build it:
   ```bash
   $SKILL/scripts/slides.py deck.json          # creates the presentation, uploads images, applies layout
   ```
   It prints the editable Google Slides URL. Requires the `gws` CLI authenticated (`gws auth status`).
3. **Verify visually**: export to PDF and Read it, then fix overflows in the spec and re-run (the script deletes and rebuilds slides so it's idempotent):
   ```bash
   gws drive files export --params '{"fileId":"<ID>","mimeType":"application/pdf"}' --output deck.pdf
   ```
   Fonts render taller than you expect — keep titles short, give text room, re-check every slide. See the slides schema + geometry notes in `references/playbook.md`.

### Option B — PDF user manual
Best when the goal is onboarding/instruction. Uses the real screenshots from Phase 2.
1. Write a **manual spec JSON**: a cover + one section per task (title, screenshot, 1–3 short paragraphs, optional "why it matters" callout) + a closing box.
2. Build and verify:
   ```bash
   $SKILL/scripts/manual_pdf.py manual.json Getting-Started.pdf
   ```
   Then Read the PDF pages to confirm layout; adjust the spec and re-run. Deliver with `SendUserFile`, and copy to `~/Downloads` if the user asks.

## Output conventions
- Match the product's brand (pull accent colors from the app; a manual is light-themed, a pitch can be dark).
- Ground every headline in a real capability; put anything unshipped under a clearly-labeled **Roadmap**.
- Keep the user in the loop on scope (how many slides/sections) if it's ambiguous — otherwise pick a sensible length (pitch 8–12 slides; manual one section per primary task).
