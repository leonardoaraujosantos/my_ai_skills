# My AI Skills

[![CI](https://github.com/leonardoaraujosantos/my_ai_skills/actions/workflows/ci.yml/badge.svg)](https://github.com/leonardoaraujosantos/my_ai_skills/actions/workflows/ci.yml)

A collection of Claude Code skills for automating common tasks. These skills extend Claude Code's capabilities with specialized tools for document conversion, data manipulation, media processing, and productivity.

## Installation

Clone this repository and copy the skills to your Claude Code skills directory:

```bash
git clone https://github.com/leonardoaraujosantos/my_ai_skills.git
cp -r my_ai_skills/* ~/.claude/skills/
```

Or symlink individual skills:

```bash
ln -s /path/to/my_ai_skills/youtube-playlist ~/.claude/skills/youtube-playlist
```

### Optional: global CLAUDE.md rules

The repo also ships a template of global rules (commit style, code quality, verification habits) at [`global/CLAUDE.md`](global/CLAUDE.md). To install it into your `~/.claude/CLAUDE.md`:

```bash
bash scripts/install_global_claude.sh              # merge — keeps rules you already have
bash scripts/install_global_claude.sh --overwrite  # replace the whole file
bash scripts/install_global_claude.sh --dry-run    # preview
```

The merge is idempotent: the template lives between `<!-- my_ai_skills:global-rules -->` markers, so re-running after a `git pull` updates that block in place without touching your own rules.

---

## Skills Overview

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| [api-client](#api-client) | HTTP client with saved request collections & environments (a CLI Postman) | None |
| [app-showcase](#app-showcase) | Build a pitch deck or screenshot-driven manual from a live app | `playwright`, `gws` |
| [bookmarks](#bookmarks) | Save URLs to Obsidian vault | `requests`, `beautifulsoup4` |
| [code-review](#code-review) | Review code for architecture, security & test coverage | None |
| [cognitive-complexity](#cognitive-complexity) | Measure & rank Cognitive Complexity to target refactors | `complexipy`, `gocognit`, `eslint-plugin-sonarjs`, `clang-tidy`, `solhint`, `scc` |
| [convert-to-md](#convert-to-md) | Convert PDF/PPTX to Markdown | `pymupdf`, `python-pptx` |
| [coolify](#coolify) | Manage Coolify deployments & env vars via API | None |
| [csv-tools](#csv-tools) | CSV manipulation & conversion | None |
| [datasheet](#datasheet) | Digest component datasheets into structured part cards; compare parts | None |
| [dep-audit](#dep-audit) | Multi-ecosystem dependency vulnerability & outdated audit with upgrade plan | Per-ecosystem: `npm`, `pip-audit`, `govulncheck`, `cargo-audit` |
| [docker-tools](#docker-tools) | Docker/Compose debugging & maintenance recipes | `docker` CLI |
| [elevenlabs](#elevenlabs) | TTS, SFX, voice conversion, music & audio isolation | `ELEVENLABS_API_KEY` env var |
| [email-triage](#email-triage) | Gmail inbox triage: classify, summarize, draft replies, batch archive | `@googleworkspace/cli` (npm) |
| [eng-calc](#eng-calc) | EE + mechanical calculators: dividers, E-series, filters, AWG, thermal, beams, bolts | None |
| [finance](#finance) | Personal finance from bank/card CSV exports: ledger, rules, reports | None |
| [flashcards](#flashcards) | Flashcards from study notes for Anki or Obsidian | None (optional: `genanki`) |
| [generate-image](#generate-image) | AI media studio: images, video, music, TTS, analysis | `GEMINI_API_KEY` env var |
| [github](#github) | Resilient GitHub REST access when api.github.com is blocked | `gh`, `curl`, `jq` |
| [gws](#gws) | Google Workspace CLI integration | `@googleworkspace/cli` (npm) |
| [image-tools](#image-tools) | Image manipulation | `Pillow` |
| [journal](#journal) | Daily journaling to Obsidian | None |
| [json-tools](#json-tools) | JSON manipulation & queries | None (optional: `pyyaml`) |
| [kicad-tools](#kicad-tools) | KiCad CLI: ERC/DRC checks, BOM/netlist, gerbers & fab outputs | `kicad-cli` (KiCad 8/9) |
| [latex-tools](#latex-tools) | Compile, scaffold & debug LaTeX; IEEE/report/TikZ templates | `latexmk` (MacTeX) or `tectonic` |
| [lit-review](#lit-review) | Systematic literature review: matrix, contradictions, cited survey note | None |
| [markitdown-hook](#markitdown-hook) | Auto-convert PDF/Office docs to Markdown on Read (token saver) | `markitdown[all]` (auto-installed) |
| [mcp-client](#mcp-client) | Test, explore & manage MCP servers | `mcp` (pip) |
| [mermaid](#mermaid) | Create cross-platform Mermaid diagrams | None |
| [notebooklm](#notebooklm) | Full Google NotebookLM API: notebooks, sources, artifacts | `notebooklm-py` (pip) |
| [obsidian](#obsidian) | Obsidian vault management | Obsidian CLI |
| [openspec](#openspec) | Spec-driven development with OpenSpec | `openspec` CLI (Node ≥ 20) |
| [openspec-baseline](#openspec-baseline) | Onboard a brownfield codebase onto OpenSpec + CI | `openspec` CLI |
| [payments](#payments) | Payment/subscription dev & debugging for Stripe, iOS StoreKit, Play Billing | None (optional: Stripe CLI, Stripe MCP) |
| [pdf-tools](#pdf-tools) | PDF manipulation | `pypdf` |
| [pentest](#pentest) | Authorized defensive security testing — 40 vuln playbooks + recon + Shannon | Per-playbook CLI tools (curl, ffuf, nuclei…); Docker for Shannon |
| [pg-client](#pg-client) | PostgreSQL client with graph & RLS support | `psycopg2` |
| [release-notes](#release-notes) | Changelog / release notes from git history between refs | `gh` (fallback: github skill) |
| [rf-tools](#rf-tools) | RF calculators: link budget, VSWR, Friis NF, matching, microstrip, attenuators | None |
| [spice](#spice) | ngspice batch simulation: AC/tran/DC/op, circuit templates, CSV + ASCII plots | `ngspice` |
| [study-this](#study-this) | Process study references & manage Obsidian study notes | `@googleworkspace/cli` (npm), `yt-dlp` |
| [sync-skills](#sync-skills) | Sync skills to GitHub repo | None |
| [transcribe](#transcribe) | Local Whisper speech-to-text for audio/video (txt/srt/vtt/json/md) | `ffmpeg` + a Whisper backend |
| [video-tools](#video-tools) | Video manipulation with ffmpeg: trim, compress, GIF, merge | `ffmpeg` |
| [visual-explainer](#visual-explainer) | Generate self-contained HTML diagrams, slide decks & dashboards | None (optional: `surf-cli` for AI images) |
| [weekly-review](#weekly-review) | Weekly review note from journal, calendar, tasks & git activity | journal, gws & obsidian skills |
| [youtube-playlist](#youtube-playlist) | YouTube playlist & CC extraction | `yt-dlp`, `youtube-transcript-api` |

---

## api-client

A CLI Postman: ad-hoc HTTP requests, saved request collections, and named environments with `{{var}}` substitution. Python stdlib only — no dependencies. Complements `pg-client` (databases) and `mcp-client` (MCP servers).

### Usage

```bash
API="$HOME/.claude/skills/api-client/scripts/api_client.py"

# Quick requests
python3 "$API" r https://api.example.com/search -q q=widgets -q limit=5
python3 "$API" r https://api.example.com/items -d '{"name": "widget", "qty": 3}'   # auto-POST
python3 "$API" r https://api.example.com/me --auth env:API_TOKEN

# Environments + saved requests
python3 "$API" env-set dev base_url=http://localhost:3000 token=dev-secret
python3 "$API" save get-user '{{base_url}}/users/{{id}}' --auth 'bearer:{{token}}' --collection users
python3 "$API" run get-user -e dev --var id=42

# Recent requests (Authorization values redacted in history)
python3 "$API" history -n 10
```

Tokens in environments are stored plaintext (chmod 600) — prefer `--auth env:VAR` so secrets stay in your shell.

### Files

```
api-client/
├── SKILL.md
└── scripts/api_client.py
```

---

## app-showcase

Build a polished sales pitch (Google Slides) or a screenshot-driven user manual (PDF) from a live app. Drives the app with Playwright (web) or a mobile simulator to capture real screenshots, and grounds every claim in the product's `openspec/` folder.

### Installation

```bash
pip install playwright && playwright install chromium
# plus the `gws` CLI (Google Workspace) for Slides/PDF export
```

### Usage

```bash
# Pitch deck from a live URL
/app-showcase pitch https://app.example.com

# Screenshot-driven manual from a local dev app
/app-showcase manual "npm run dev" --auth user:pass
```

### Files

```
app-showcase/
├── SKILL.md
├── scripts/{capture.py, slides.py, manual_pdf.py}
└── references/{playbook.md, mobile.md}
```

---

## bookmarks

Save and manage bookmarks in Obsidian vault with auto-fetched metadata.

### Installation

```bash
pip install requests beautifulsoup4
```

### Usage

```bash
SKILL="$HOME/.claude/skills/bookmarks"

# Add bookmark (auto-fetches title & description)
python3 "$SKILL/bookmarks.py" add -u "https://example.com/article"

# Add with tags and category
python3 "$SKILL/bookmarks.py" add -u "https://docs.python.org" --tags "python,docs" -c "Programming"

# List all bookmarks
python3 "$SKILL/bookmarks.py" list

# Search bookmarks
python3 "$SKILL/bookmarks.py" search -q "python tutorial"

# List all tags
python3 "$SKILL/bookmarks.py" tags

# Export to JSON
python3 "$SKILL/bookmarks.py" export -o bookmarks.json --format json
```

### Files

```
bookmarks/
├── SKILL.md
└── bookmarks.py
```

---

## code-review

Review changed code for architecture compliance, security vulnerabilities, and test coverage. Enforces Hexagonal Architecture for backend projects and MVVM for frontend projects. Detects test gaps and runs tests when possible.

### Usage

```bash
# Review a GitHub PR
/code-review https://github.com/org/repo/pull/123

# Review a branch diff
/code-review feature-branch

# Review staged + unstaged changes (no argument)
/code-review

# Backend-only review
/code-review --backend

# Frontend-only review
/code-review --frontend

# Security-focused review only
/code-review --security-only

# Test coverage review only
/code-review --tests-only
```

### Review Output

Each finding follows a structured format with severity levels:

- **CRITICAL** -- Must fix before merge (security vulnerabilities, data loss risk)
- **MAJOR** -- Should fix before merge (architecture violations, missing error handling)
- **MINOR** -- Nice to fix (style issues, naming)
- **NIT** -- Optional (cosmetic suggestions)

The review ends with a summary including verdict (APPROVE / REQUEST CHANGES / NEEDS DISCUSSION), architecture compliance, security assessment, test coverage gaps, and top priorities.

### Architecture Rules

- **Backend (Hexagonal):** Strict separation of domain, ports, and adapters. Domain must not import infrastructure. Dependency direction always inward.
- **Frontend (MVVM):** Clean separation between View, ViewModel, and Model. No API calls or business logic in components.

### Files

```
code-review/
└── SKILL.md
```

---

## cognitive-complexity

Measure Cognitive Complexity (the SonarSource metric) of C/C++, Python, Go, TypeScript/JavaScript, Solidity, or SystemVerilog code and report a ranked, banded list of the most complex functions to target for refactoring. Wraps installed open-source analyzers — it does not re-implement the metric, and it labels honestly when a language's best available tool reports a different metric: Solidity uses solhint's per-function **cyclomatic** complexity; SystemVerilog uses scc's per-**file** cyclomatic estimate (no open-source tool provides per-function SV complexity — Verible's 60 lint rules include none).

### Installation

```bash
# Python/Go handled by the skill's setup; TS/JS uses a bundled toolchain
bash "$HOME/.claude/skills/cognitive-complexity/scripts/setup.sh"
```

### Usage

```bash
SKILL="$HOME/.claude/skills/cognitive-complexity"

# Rank the most complex functions in a folder
python3 "$SKILL/scripts/cogcom.py" src/ --top 20

# Filter by language and threshold, JSON output
python3 "$SKILL/scripts/cogcom.py" . --lang python,go --threshold 15 --json
```

### Files

```
cognitive-complexity/
├── SKILL.md
└── scripts/{cogcom.py, setup.sh, ts/}
```

---

## convert-to-md

Convert PDF and PowerPoint files to Markdown format with image extraction.

### Installation

```bash
pip install pymupdf python-pptx
```

### Usage

```bash
# Convert PDF
python ~/.claude/skills/convert-to-md/scripts/pdf_to_markdown.py document.pdf

# Convert PPTX
python ~/.claude/skills/convert-to-md/scripts/pptx_to_markdown.py presentation.pptx

# Options
--pages 1-10    # PDF: convert specific pages
--slides 1-10   # PPTX: convert specific slides
--no-images     # Skip image extraction
-o output.md    # Custom output path
```

### Files

```
convert-to-md/
├── SKILL.md
└── scripts/
    ├── pdf_to_markdown.py
    └── pptx_to_markdown.py
```

---

## coolify

Manage Coolify applications, deployments, environment variables, and services through the Coolify API.

### Installation

Set the required environment variables:

```bash
export COOLIFY_URL="https://coolify.example.com"
export COOLIFY_TOKEN="your-api-token"
```

The CLI tool uses only Python stdlib (no pip dependencies needed).

### Usage

```bash
COOLIFY="COOLIFY_URL=$COOLIFY_URL COOLIFY_TOKEN=$COOLIFY_TOKEN python3 ~/.claude/skills/coolify/coolify_cli.py"

# List applications
$COOLIFY apps

# Show application details
$COOLIFY app <app-uuid>

# List environment variables
$COOLIFY app-envs <app-uuid>

# Set / update an environment variable
$COOLIFY app-env-set <app-uuid> MY_KEY "my-value"

# Set a JSON env var (use --literal to prevent brace interpolation)
$COOLIFY app-env-set <app-uuid> MCP_CONFIG '{"name":"agent","url":"https://..."}' --literal

# Delete an environment variable
$COOLIFY app-env-delete <app-uuid> <env-uuid>

# Trigger deployment
$COOLIFY deploy <app-uuid>

# Force redeploy (no cache)
$COOLIFY deploy <app-uuid> --force

# List recent deployments
$COOLIFY deployments <app-uuid> --limit 5

# View application logs
$COOLIFY logs <app-uuid> --lines 100

# List services / servers / resources / teams
$COOLIFY services
$COOLIFY servers
$COOLIFY resources
$COOLIFY teams
```

### Files

```
coolify/
├── SKILL.md
└── coolify_cli.py
```

---

## csv-tools

Manipulate CSV files - view, filter, sort, convert to JSON/Markdown.

### Usage

```bash
SKILL="$HOME/.claude/skills/csv-tools"

# View CSV info
python3 "$SKILL/csv_tools.py" info data.csv

# Show first/last rows
python3 "$SKILL/csv_tools.py" head data.csv -n 20
python3 "$SKILL/csv_tools.py" tail data.csv -n 10

# Filter rows
python3 "$SKILL/csv_tools.py" filter data.csv -w "status == 'active'"
python3 "$SKILL/csv_tools.py" filter data.csv -w "age > 30"

# Select columns
python3 "$SKILL/csv_tools.py" select data.csv -c "name,email,phone"

# Sort
python3 "$SKILL/csv_tools.py" sort data.csv -s "created_at" --desc

# Statistics
python3 "$SKILL/csv_tools.py" stats data.csv

# Convert to JSON
python3 "$SKILL/csv_tools.py" to-json data.csv -o data.json

# Convert to Markdown table
python3 "$SKILL/csv_tools.py" to-markdown data.csv -o table.md
```

### Files

```
csv-tools/
├── SKILL.md
└── csv_tools.py
```

---

## datasheet

Digest component datasheets into a structured, reusable "part card": absolute maximum ratings, recommended operating conditions, key electrical characteristics *with test conditions*, pinout, application notes, and gotchas — every value copied exactly (min/typ/max discipline, page citations, `⚠ verify` markers instead of guesses). Compare mode produces a worst-case side-by-side table with a "choose X if / choose Y if" verdict. Part cards save to the vault under `Engineering/Parts/`.

### Usage

```bash
/datasheet ~/Downloads/lm317.pdf --save
/datasheet TPS7A47                      # finds the official PDF by part number
/datasheet TPS7A47 compare LT3045       # side-by-side on worst-case specs
```

### Files

```
datasheet/
└── SKILL.md
```

---

## dep-audit

Multi-ecosystem dependency audit: scan for vulnerable and outdated packages and produce a prioritized upgrade plan. Detects ecosystems by manifest/lockfile (npm/pnpm/yarn, Python, Go, Rust, Ruby, PHP) and drives the native scanners (`npm audit`, `pip-audit`, `govulncheck`, `cargo audit`). Reports and plans only — never runs `npm audit fix` or upgrades without approval; missing scanners are reported as "not scanned", never silently skipped.

### Usage

```bash
/dep-audit                        # audit the current project
/dep-audit apps/api --prod-only   # production dependencies only
/dep-audit --fix-plan             # ordered upgrade plan: security first, then minors, then majors
```

### Files

```
dep-audit/
└── SKILL.md
```

---

## docker-tools

Opinionated Docker/Compose debugging and maintenance recipes: container status overview, a step-by-step unhealthy/restarting-container diagnosis workflow (health-check log, exit code, OOMKilled, restart count, exec-in), logs, exec & copy, staged safe disk cleanup (volumes last and always confirmed), compose lifecycle, networking, and image management. Local/host-level counterpart to the coolify skill.

### Usage

Ask things like "why is my container unhealthy?", "clean up docker disk usage", or "rebuild just the api service" — the skill drives the installed `docker` / `docker compose` CLI with show-before-destroy safety rules.

### Files

```
docker-tools/
└── SKILL.md
```

---

## elevenlabs

Full audio generation suite powered by the ElevenLabs API: text-to-speech, sound effects, speech-to-speech voice conversion, music composition, and audio isolation (background-noise removal).

### Installation

No pip dependencies — the CLI uses only the Python stdlib. It only needs an API key:

```bash
export ELEVENLABS_API_KEY="your-elevenlabs-api-key"
```

The skill reads the key from `os.environ`; nothing is hardcoded.

### Usage

```bash
SKILL_DIR="$HOME/.claude/skills/elevenlabs"

# Text-to-Speech
python3 "$SKILL_DIR/elevenlabs_cli.py" tts "Hello world" -o speech.mp3 -v JBFqnCBsd6RMkjVDRZzb

# Sound effects
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "footsteps on gravel, rain" -o sfx.mp3

# Speech-to-Speech (voice conversion)
python3 "$SKILL_DIR/elevenlabs_cli.py" sts input.mp3 -v <voice_id> -o converted.mp3

# Music composition
python3 "$SKILL_DIR/elevenlabs_cli.py" music "lo-fi hip hop, 80 BPM, mellow" -o track.mp3

# Audio isolation (strip background noise)
python3 "$SKILL_DIR/elevenlabs_cli.py" isolate noisy.mp3 -o clean.mp3

# List available voices / models
python3 "$SKILL_DIR/elevenlabs_cli.py" voices
python3 "$SKILL_DIR/elevenlabs_cli.py" models
```

> Note: the API key must include the scopes for the operations you use (e.g. `text_to_speech`). A narrowly-scoped key still works for TTS/SFX even if it lacks `user_read`.

### Files

```
elevenlabs/
├── SKILL.md
└── elevenlabs_cli.py
```

---

## email-triage

Inbox triage over the gws CLI: fetch recent Gmail, classify threads into 🔴 action / 🟡 reply / 📰 newsletter / 📥 FYI buckets, and present a triage report. With explicit confirmation it drafts replies (prefers Gmail drafts over sending), adds action items as Google Tasks, and batch-archives bulk mail.

Safety rules: never sends without showing the draft and getting approval, never deletes email (archive only, after listing affected messages), `--dry-run` = zero mutations, and email content is treated as untrusted data (prompt-injection guard).

### Usage

```bash
/email-triage                     # last 2 days
/email-triage --days 7 --dry-run
/email-triage --focus "sender or topic"
```

### Files

```
email-triage/
└── SKILL.md
```

---

## eng-calc

Everyday electrical + mechanical engineering calculators. All formulas verified against hand calculations. SI suffixes (k, M, m, u, n, p) accepted everywhere.

**Electrical**: `divider` (with best E24/E96 pair synthesis), `eseries`, `rc`/`rl`/`lc`, `led`, `ohm`, `awg` (AWG 0000–40 table), `tolerance` (worst-case + RSS), `thermal` (junction temp through a RθJC/RθCS/RθSA chain), `battery` (incl. duty-cycle phases).
**Mechanical**: `beam` (4 loading cases, `--rect` section helper), `bolt` (metric M3–M20, grades 8.8/10.9/12.9), `gear`.

### Usage

```bash
SKILL="$HOME/.claude/skills/eng-calc"

python3 "$SKILL/eng_calc.py" divider --vin 12 --vout 3.3 --rtotal 10k --series E24
python3 "$SKILL/eng_calc.py" rc --r 10k --c 100n          # fc = 159.2 Hz
python3 "$SKILL/eng_calc.py" awg 24
python3 "$SKILL/eng_calc.py" thermal --p 2.5 --ta 40 --rth 3.1,0.5,4.2 --tjmax 125
python3 "$SKILL/eng_calc.py" beam --case cantilever-end --l 0.5 --e 200e9 --i 8.3e-9 --p 100
python3 "$SKILL/eng_calc.py" bolt --size M6 --grade 8.8
```

### Files

```
eng-calc/
├── SKILL.md
└── eng_calc.py
```

---

## finance

Personal finance tracking from bank/card CSV exports: normalize statements into a local ledger, categorize spending by rules, and generate monthly reports. Handles per-bank CSV quirks via profiles (column mapping, date format, decimal comma, `--invert` for banks that export expenses as positive — e.g. Nubank exports). All data stays local.

### Usage

```bash
FIN="$HOME/.claude/skills/finance/scripts/finance.py"

# One-time: map your bank's CSV columns
python3 "$FIN" profile-add nubank --date-col data --desc-col descrição --amount-col valor \
  --date-format "%d/%m/%Y" --decimal-comma --invert --currency BRL --delimiter ";"

# Monthly loop: import → categorize → report
python3 "$FIN" import ~/Downloads/statement.csv -p nubank
python3 "$FIN" rules-add "uber" transport
python3 "$FIN" categorize --month 2026-07
python3 "$FIN" report --month 2026-07 --markdown   # Obsidian-ready note
```

### Files

```
finance/
├── SKILL.md
└── scripts/finance.py
```

---

## flashcards

Generate spaced-repetition flashcards from study notes: Claude authors atomic Q/A and cloze cards from a note or topic (following authoring guidelines in the skill), then the script packages them for Anki (`.apkg` via optional `genanki`, or importable TSV) or the Obsidian spaced-repetition plugin. Closes the loop that study-this opens: capture → study → consolidate → retain.

### Usage

```bash
SKILL="$HOME/.claude/skills/flashcards"

# Claude writes cards.md in the documented format, then:
python3 "$SKILL/flashcards.py" validate cards.md
python3 "$SKILL/flashcards.py" convert cards.md --format apkg --deck "Networking" -o networking.apkg
python3 "$SKILL/flashcards.py" convert cards.md --format obsidian   # Question::Answer lines for the vault
python3 "$SKILL/flashcards.py" stats cards.md
```

### Files

```
flashcards/
├── SKILL.md
└── flashcards.py
```

---

## generate-image

Full AI media generation suite powered by Google Gemini API. Generate images, videos, music, speech, or analyze images to extract prompts for all tools.

Requires the `GEMINI_API_KEY` environment variable to be set.

### Models

| Command | Model | Description |
|---------|-------|-------------|
| `generate` | Nano Banana 2 / Imagen 4 | Image generation |
| `video` | Veo 3.1 | Video generation (text-to-video and image-to-video) |
| `music` | Lyria 3 | Music generation |
| `tts` | Gemini TTS | Text-to-speech with multiple voices |
| `analyze` | Gemini | Image analysis and prompt extraction |

### Usage

```bash
SKILL_DIR="$HOME/.claude/skills/generate-image"
```

#### 1. `generate` -- Image Generation (Nano Banana 2 / Imagen 4)

```bash
# Generate an image
python3 "$SKILL_DIR/generate_image.py" generate "A cute robot in a wasteland" -o robot.png

# Custom size (1024x1024, 1536x1024, 1024x1536)
python3 "$SKILL_DIR/generate_image.py" generate "Character sheet, anime style robot" -o sheet.png -s 1536x1024

# Generate multiple images (1-4)
python3 "$SKILL_DIR/generate_image.py" generate "Landscape variations" -n 4

# Options: --output/-o, --size/-s, --count/-n, --model/-m
```

#### 2. `video` -- Video Generation (Veo 3.1)

```bash
# Text to video
python3 "$SKILL_DIR/generate_image.py" video "A small robot walks through ruins and finds a green sprout" -o scene.mp4

# Image to video (animate a still image)
python3 "$SKILL_DIR/generate_image.py" video "The robot reaches down to touch the plant" --image robot.png -o animated.mp4

# Fast generation with alternate model
python3 "$SKILL_DIR/generate_image.py" video "Robot building a dome" -m veo-3.1-fast-generate-preview -o dome.mp4

# Options: --output/-o, --model/-m, --duration/-d (5s/8s/10s), --image/-i
```

Video generation is async -- the script polls until complete (up to 10 min).

#### 3. `music` -- Music Generation (Lyria 3)

```bash
# Game soundtrack
python3 "$SKILL_DIR/generate_image.py" music "Hopeful orchestral piece, 90 BPM, D major, soft piano melody with strings" -o theme.wav

# Combat music
python3 "$SKILL_DIR/generate_image.py" music "Aggressive electronic, 140 BPM, taiko drums, distorted bass" -o combat.wav

# Ambient
python3 "$SKILL_DIR/generate_image.py" music "Dark ambient, wasteland wind, distant metallic groans, desolate" -o wasteland.wav

# Options: --output/-o, --model/-m (lyria-3-clip-preview, lyria-3-pro-preview), --duration/-d (seconds)
```

#### 4. `tts` -- Text-to-Speech (Gemini TTS)

```bash
# Narrator voice
python3 "$SKILL_DIR/generate_image.py" tts "The world ended. A small robot found a sprout." -v Charon -o narration.wav

# Character dialogue
python3 "$SKILL_DIR/generate_image.py" tts "I didn't trap them. I preserved them." -v Fenrir -o yuri.wav

# Tutorial voice
python3 "$SKILL_DIR/generate_image.py" tts "Tap and hold to move your Commander." -v Kore -o tutorial.wav

# Options: --output/-o, --model/-m, --voice/-v
```

Available voices: Zephyr (bright), Puck (playful), Charon (deep), Kore (calm, default), Fenrir (bold), Leda (warm), Orus (professional), Aoede (expressive), Io (youthful), Elara (gentle).

#### 5. `analyze` -- Image Analysis to Prompts

```bash
# Full analysis -- prompts for every tool (image, video, music, sfx, voice)
python3 "$SKILL_DIR/generate_image.py" analyze concept_art.png

# Just video prompt (for Veo 3.1)
python3 "$SKILL_DIR/generate_image.py" analyze scene.png -t video

# Save analysis to file
python3 "$SKILL_DIR/generate_image.py" analyze character.png -t all -o prompts.md

# Options: --target/-t (all/image/video/music/sfx/voice), --output/-o
```

### Full Creative Pipeline Example

```bash
SKILL_DIR="$HOME/.claude/skills/generate-image"

# 1. Generate concept art
python3 "$SKILL_DIR/generate_image.py" generate "Cute robot finding a sprout in wasteland, anime style" -o concept.png

# 2. Analyze it to get prompts for everything
python3 "$SKILL_DIR/generate_image.py" analyze concept.png -t all -o prompts.md

# 3. Generate video from the image
python3 "$SKILL_DIR/generate_image.py" video "Robot reaches down to touch plant, camera slowly orbits" --image concept.png -o scene.mp4

# 4. Generate matching music
python3 "$SKILL_DIR/generate_image.py" music "Gentle piano, hopeful, 80 BPM, D major" -o soundtrack.wav

# 5. Generate narration
python3 "$SKILL_DIR/generate_image.py" tts "In the silence of the wasteland, a small robot found hope." -v Elara -o narration.wav
```

### Files

```
generate-image/
├── SKILL.md
└── generate_image.py
```

---

## github

Resilient GitHub access (issues, PRs, REST API) that survives local network blocks of `api.github.com`. Use when `gh` commands hang or time out, or to diagnose whether GitHub is actually down vs blocked locally.

### Usage

```bash
SKILL="$HOME/.claude/skills/github"

# Diagnose reachability and pin a working IP if needed
bash "$SKILL/ghx.sh" doctor

# Call the REST API through the resilient path
bash "$SKILL/ghx.sh" api "repos/OWNER/REPO/issues?state=open"
```

### Files

```
github/
├── SKILL.md
└── ghx.sh
```

---

## gws

Interact with Google Workspace (Gmail, Calendar, Drive, Sheets, Docs, Tasks) using the gws CLI.

### Installation

```bash
npm install -g @googleworkspace/cli   # provides the `gws` binary
gws auth login
```

> Note: install the official `@googleworkspace/cli` package. The bare npm name `gws` is an unrelated package (an E2E testing tool) and will NOT provide the Google Workspace commands.

### Usage

```bash
# Gmail
gws gmail +triage --format table          # Check inbox
gws gmail +send --to "x@y.com" --subject "Hi" --body "Hello"

# Calendar
gws calendar +agenda --format table       # Today's agenda
gws calendar +agenda --days 7             # Week ahead

# Drive
gws drive files list --format table       # List files
gws drive +upload --file "./doc.pdf"      # Upload file

# Sheets
gws sheets +read --spreadsheet "ID" --range "Sheet1!A1:C10"
gws sheets +append --spreadsheet "ID" --range "A:C" --values '[["a","b","c"]]'

# Tasks
gws tasks tasks list --format table       # List tasks
gws tasks tasks insert --params '{"tasklist": "@default"}' --json '{"title": "New task"}'
```

### Files

```
gws/
└── SKILL.md
```

---

## image-tools

Manipulate images - resize, compress, convert, rotate, crop, watermark.

### Installation

```bash
pip install Pillow
```

### Usage

```bash
SKILL="$HOME/.claude/skills/image-tools"

# View image info
python3 "$SKILL/image_tools.py" info photo.jpg

# Resize (keeps aspect ratio)
python3 "$SKILL/image_tools.py" resize photo.jpg -w 800 -o small.jpg

# Compress JPEG
python3 "$SKILL/image_tools.py" compress photo.jpg -q 70 -o compressed.jpg

# Convert format
python3 "$SKILL/image_tools.py" convert image.png -o image.jpg

# Create thumbnail
python3 "$SKILL/image_tools.py" thumbnail photo.jpg -w 150 -h 150

# Rotate
python3 "$SKILL/image_tools.py" rotate photo.jpg -a 90 -o rotated.jpg

# Add watermark
python3 "$SKILL/image_tools.py" watermark photo.jpg -t "Copyright 2024" -o marked.jpg

# Grayscale
python3 "$SKILL/image_tools.py" grayscale photo.jpg -o bw.jpg

# Crop (left, top, right, bottom)
python3 "$SKILL/image_tools.py" crop photo.jpg --crop 100 100 500 400 -o cropped.jpg
```

### Files

```
image-tools/
├── SKILL.md
└── image_tools.py
```

---

## journal

Daily journaling with templates saved to Obsidian vault.

### Usage

```bash
SKILL="$HOME/.claude/skills/journal"

# View/create today's entry
python3 "$SKILL/journal.py" today

# Add a quick note
python3 "$SKILL/journal.py" add -t "Had a great meeting with the team"

# Add with mood and energy
python3 "$SKILL/journal.py" add -t "Feeling productive" -m great -e 5

# Add to gratitude section
python3 "$SKILL/journal.py" add -t "Grateful for sunny weather" -s gratitude

# Add morning reflection
python3 "$SKILL/journal.py" add -t "Planning to focus on project X" -s morning

# View this week
python3 "$SKILL/journal.py" week

# View month
python3 "$SKILL/journal.py" month

# Search entries
python3 "$SKILL/journal.py" search -q "project meeting"

# View stats
python3 "$SKILL/journal.py" stats

# Get writing prompts
python3 "$SKILL/journal.py" prompts
```

### Template Sections

Each daily entry includes:
- **Morning** - Start of day thoughts
- **Tasks & Goals** - Today's todos
- **Journal** - Main journaling area
- **Gratitude** - 3 things grateful for
- **Evening Reflection** - End of day review

### Files

```
journal/
├── SKILL.md
└── journal.py
```

---

## json-tools

Manipulate JSON - format, validate, query, diff, merge, convert.

### Usage

```bash
SKILL="$HOME/.claude/skills/json-tools"

# View JSON info
python3 "$SKILL/json_tools.py" info data.json

# Pretty print
python3 "$SKILL/json_tools.py" format data.json -o pretty.json

# Minify
python3 "$SKILL/json_tools.py" minify data.json -o min.json

# Validate syntax
python3 "$SKILL/json_tools.py" validate data.json

# List all keys
python3 "$SKILL/json_tools.py" keys data.json

# Query specific path
python3 "$SKILL/json_tools.py" query data.json -p "users[0].email"

# Set value
python3 "$SKILL/json_tools.py" set config.json -p "debug" -v "true"

# Delete key
python3 "$SKILL/json_tools.py" delete data.json -p "temp_field"

# Compare two files
python3 "$SKILL/json_tools.py" diff old.json new.json

# Merge files
python3 "$SKILL/json_tools.py" merge a.json b.json -o combined.json

# Convert to CSV (array of objects)
python3 "$SKILL/json_tools.py" to-csv users.json -o users.csv

# Convert to YAML
python3 "$SKILL/json_tools.py" to-yaml config.json -o config.yaml

# Flatten nested JSON
python3 "$SKILL/json_tools.py" flatten nested.json -o flat.json
```

### Path Syntax

```
name              # top-level key
data.users        # nested key
users[0]          # array index
data.users[0].name # combined
```

### Files

```
json-tools/
├── SKILL.md
└── json_tools.py
```

---

## kicad-tools

Drive KiCad from the command line via `kicad-cli`: ERC/DRC design checks with parsed JSON reports (grouped by severity, explained in plain language), schematic exports (PDF/SVG/netlist/BOM), PCB fab outputs (gerbers, drill, pick-and-place, a "standard fab package" zip recipe with checklist), and board renders. Read-only on project files; flags are confirmed with `--help` at runtime since they vary across KiCad 7/8/9.

### Usage

```bash
/kicad-tools board.kicad_pcb drc        # run DRC, explain violations
/kicad-tools sch.kicad_sch bom
/kicad-tools project.kicad_pro gerbers  # full fab package
```

### Files

```
kicad-tools/
└── SKILL.md
```

---

## latex-tools

Compile, scaffold, and debug LaTeX documents: the `latexmk` compile-fix loop (with an error→fix table for the common failures), ready-to-compile templates, BibTeX hygiene (Crossref/arXiv fetching, key conventions), and siunitx/math snippets for EE/RF notation. All four templates compile cleanly with MacTeX (TeX Live 2025).

### Installation

```bash
brew install tectonic        # minimal single binary — or MacTeX for the full distribution
```

### Usage

```bash
/latex-tools compile paper.tex
/latex-tools new ieee-paper          # also: report, letter, tikz-examples
/latex-tools fix paper.tex           # first-error-first log diagnosis
```

### Files

```
latex-tools/
├── SKILL.md
└── templates/{ieee-paper.tex, refs.bib, report.tex, letter.tex, tikz-examples.tex}
```

---

## lit-review

Systematic literature review: scope the question, gather papers (local PDF folders, or paper search via the Firecrawl research tools with arXiv/Semantic Scholar fallback, plus one-hop citation snowballing), extract each paper into a fixed schema saved as a vault note under `Papers/`, build a literature matrix, surface agreements and contradictions (both sides cited — never averaged away), and synthesize a fully-cited survey note to `Literature Reviews/<topic>.md`. Every claim traces to a specific paper; unread/paywalled papers are listed as "Not reviewed", never cited blind.

### Usage

```bash
/lit-review "sub-GHz LPWAN interference mitigation" --depth thorough
/lit-review ~/papers/beamforming/          # folder of PDFs
/lit-review <arxiv-urls...> --no-save
```

### Files

```
lit-review/
└── SKILL.md
```

---

## mcp-client

Test, explore, and manage MCP (Model Context Protocol) servers. Verify connectivity, list tools/resources/prompts, execute tools, benchmark performance, manage auth tokens, and register servers. Supports stdio, SSE, and Streamable HTTP transports.

### Installation

```bash
pip install mcp
```

### Usage

```bash
MCP_CLIENT="$HOME/.claude/skills/mcp-client/scripts/mcp_client.py"

# Register a server
python3 "$MCP_CLIENT" register my-kg -t http -u http://localhost:8000/mcp

# Save auth token
python3 "$MCP_CLIENT" token-set my-kg "sk-abc123" --type bearer

# Full exploration (lists tools, resources, resource templates, prompts)
python3 "$MCP_CLIENT" explore -s my-kg

# List tools
python3 "$MCP_CLIENT" tools -s my-kg --json

# Call a tool (JSON args)
python3 "$MCP_CLIENT" call query '{"query": "test"}' -s my-kg

# Call a tool (key=value args)
python3 "$MCP_CLIENT" call add 'a=2,b=3' -t stdio --cmd python3 --args server.py

# Get tool schema
python3 "$MCP_CLIENT" schema query -s my-kg

# Read a resource
python3 "$MCP_CLIENT" resource "file:///path/to/resource" -s my-kg

# Get a prompt
python3 "$MCP_CLIENT" prompt my-prompt -s my-kg

# Health check with latency metrics
python3 "$MCP_CLIENT" health -s my-kg --json

# Benchmark tool response time (10 iterations)
python3 "$MCP_CLIENT" benchmark query '{"q": "test"}' -s my-kg -n 10

# Manage servers
python3 "$MCP_CLIENT" servers
python3 "$MCP_CLIENT" unregister my-kg

# Manage tokens
python3 "$MCP_CLIENT" token-list
python3 "$MCP_CLIENT" token-delete my-kg
```

### Connection Options

Every command accepts either a named (registered) server or inline connection flags:

```bash
# Named server
python3 "$MCP_CLIENT" explore -s my-server

# Inline stdio
python3 "$MCP_CLIENT" explore -t stdio --cmd mcp --args run server.py

# Inline SSE
python3 "$MCP_CLIENT" explore -t sse -u http://localhost:8000/sse

# Inline Streamable HTTP
python3 "$MCP_CLIENT" explore -t http -u http://localhost:8000/mcp
```

### Files

```
mcp-client/
├── SKILL.md
├── servers.json
└── scripts/
    └── mcp_client.py
```

---

## markitdown-hook

Install a harness-level `PreToolUse(Read)` hook that auto-converts binary documents (PDF, DOCX, PPTX, XLSX, EPub) to Markdown **before** Claude reads them — saving tokens. `Read` renders PDF pages as images at high token cost; the hook intercepts the read, converts the file locally with `markitdown`, and redirects Claude to a sibling `.converted.md`. Complements the on-demand `convert-to-md` / `pdf-tools` skills by making conversion automatic on every read.

### Installation

```bash
bash ~/.claude/skills/markitdown-hook/scripts/install.sh
# then restart Claude Code and run /hooks to confirm
```

Idempotent. Creates a pinned `markitdown[all]` venv (Python 3.10–3.13), copies the hook to `~/.claude/hooks/`, and safe-merges a `PreToolUse(Read)` entry into `~/.claude/settings.json`.

### Notes

- Documents only — images/audio are left on normal `Read`. Cached, size-guarded (>50 MB skipped), never clobbers user files, and skips sensitive paths (`.ssh`, `.aws`, `.env`, …).
- Dragged/pasted files bypass the hook (Claude Code attaches them before any hook runs) — ask "read `<path>`" for those.
- Treats converted text as untrusted data, not instructions (prompt-injection aware).

---

## mermaid

Create Mermaid diagrams that render correctly across Obsidian, GitHub, and Notion. Enforces cross-platform compatibility rules and avoids common rendering bugs.

### Usage

```bash
# Create a diagram by describing what you need
/mermaid flowchart showing user authentication flow

# Fix broken Mermaid blocks in a file
/mermaid fix path/to/file.md
```

### Key Rules

- Always quote labels with special characters: `A["My Label"]`
- Never use `<br/>` in labels (breaks Obsidian)
- Never put standalone (unconnected) nodes inside subgraphs
- Use ASCII-only for node IDs (accented chars OK in quoted labels)
- Max 50 nodes / 100 edges per diagram for reliable rendering
- Avoid emojis for cross-platform compatibility

### Supported Diagram Types

| Type | Compatibility |
|------|---------------|
| `graph` / `flowchart` | Obsidian, GitHub, Notion |
| `sequenceDiagram` | Obsidian, GitHub, Notion |
| `classDiagram` | Obsidian, GitHub, Notion |
| `stateDiagram-v2` | Obsidian, GitHub, Notion |
| `erDiagram` | Obsidian, GitHub, Notion |
| `gantt` | Obsidian, GitHub, Notion |
| `pie` | Obsidian, GitHub, Notion |
| `gitGraph` | Obsidian, GitHub, Notion |
| `mindmap` | Obsidian (v1.4+), GitHub, Notion |
| `timeline` | Obsidian (v1.4+), GitHub, Notion |

### Fix Mode

When invoked with `/mermaid fix <file>`, the skill scans all Mermaid blocks in the file and automatically fixes common issues: unquoted labels, `<br/>` tags, standalone subgraph nodes, accented node IDs, and more.

### Files

```
mermaid/
└── SKILL.md
```

---

## notebooklm

Complete programmatic access to Google NotebookLM — including capabilities not exposed in the web UI. Create notebooks, add sources (URLs, YouTube, PDFs, audio, video, images), chat with content, generate all artifact types (podcast, video, slide deck, report, quiz, flashcards, mind map, data table, infographic), and download results in multiple formats.

The skill drives the `notebooklm` CLI provided by the `notebooklm-py` Python package.

### Installation

**From PyPI (recommended):**

```bash
pip install notebooklm-py
```

**From GitHub (pin to the latest release tag — NOT `main`):**

```bash
LATEST_TAG=$(curl -s https://api.github.com/repos/teng-lin/notebooklm-py/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
pip install "git+https://github.com/teng-lin/notebooklm-py@${LATEST_TAG}"
```

> Requires Python 3.10+. Do NOT install from the `main` branch — it may contain unreleased/unstable changes. Use PyPI or a specific release tag.

Verify the CLI:

```bash
notebooklm --version
```

### Authentication

NotebookLM uses Google OAuth via the browser:

```bash
notebooklm login          # Opens a browser for Google sign-in
notebooklm auth check     # Diagnose auth state
notebooklm list           # Verify it works (returns your notebooks)
```

If commands fail with auth errors, re-run `notebooklm login`.

#### CI / multiple accounts / parallel agents

| Variable | Purpose |
|----------|---------|
| `NOTEBOOKLM_HOME` | Custom config directory (default: `~/.notebooklm`). Use a unique dir per parallel agent. |
| `NOTEBOOKLM_AUTH_JSON` | Inline auth JSON (`storage_state.json` contents) — no file writes; ideal for CI secrets. |

### Usage

```bash
# Notebooks
notebooklm create "Research: AI safety"
notebooklm list

# Add sources
notebooklm source add "https://example.com/article"
notebooklm source add ./paper.pdf
notebooklm source add "https://youtube.com/watch?v=VIDEO_ID"

# Chat
notebooklm ask "Summarize the key arguments"

# Generate artifacts
notebooklm generate audio "Focus on practical takeaways"
notebooklm generate report --format briefing-doc
notebooklm generate mind-map

# Download
notebooklm download audio ./podcast.mp3
notebooklm download report ./report.md
```

See the skill's `SKILL.md` for the full command reference, autonomy rules, and subagent patterns for long-running generation.

### Files

```
notebooklm/
└── SKILL.md
```

---

## obsidian

Interact with Obsidian vault using the official Obsidian CLI.

### Configuration

Update the vault name in `SKILL.md` to match your vault:

```bash
vault="Your Vault Name"
```

### Usage

```bash
CLI="/Applications/Obsidian.app/Contents/MacOS/Obsidian"

# Search
$CLI search vault="$OBSIDIAN_VAULT_NAME" query="kubernetes"

# Read
$CLI read vault="$OBSIDIAN_VAULT_NAME" file="Python"

# Create
$CLI create vault="$OBSIDIAN_VAULT_NAME" path="Notes/NewNote.md" content="# Title\n\nContent"

# Append
$CLI append vault="$OBSIDIAN_VAULT_NAME" file="Python" content="\n## New Section"

# Daily notes
$CLI daily:read vault="$OBSIDIAN_VAULT_NAME"
$CLI daily:append vault="$OBSIDIAN_VAULT_NAME" content="- [ ] New task"

# Tasks
$CLI tasks vault="$OBSIDIAN_VAULT_NAME" todo
$CLI task vault="$OBSIDIAN_VAULT_NAME" file="Note" line=5 toggle

# Backlinks
$CLI backlinks vault="$OBSIDIAN_VAULT_NAME" file="Python"
```

### Files

```
obsidian/
└── SKILL.md
```

---

## openspec

Spec-driven development with OpenSpec. Discuss a feature then spec it before coding (proposal / specs / design / tasks), implement against the artifacts, validate, and archive so living specs stay in the repo.

### Installation

```bash
# Requires Node ≥ 20.19
npm install -g openspec   # verify with: openspec --version
```

### Usage

```bash
# Triggered conversationally or via the slash command
/openspec propose <change-name>
/openspec validate <change-name>
/openspec archive <change-name>
```

### Files

```
openspec/
└── SKILL.md
```

---

## openspec-baseline

Onboard an existing (brownfield) codebase onto OpenSpec end-to-end: initialize `openspec/`, reverse-engineer capability-scoped baseline specs from the current implementation, add an `openspec-validate` CI job, and open a PR.

### Usage

```bash
# Run on a project with no openspec/ directory yet
/openspec-baseline

# Skip opening the PR
/openspec-baseline no-pr
```

### Files

```
openspec-baseline/
└── SKILL.md
```

---

## payments

Cross-platform payment and subscription development/debugging playbooks for the three payment stacks: **Stripe** (web — CLI webhook loop, `stripe trigger`, test cards, test clocks, subscription lifecycle events), **Apple StoreKit 2 / App Store Connect** (`.storekit` Xcode testing, `SKTestSession` CI automation, sandbox renewal-rate tables, App Store Server API/Notifications V2, "products not loading" decision tree), and **Google Play Billing** (Billing Library 8/9, license-tester accelerated renewals, the 3-day acknowledgment refund trap, RTDN, `subscriptionsv2` verification, `BillingResponseCode` table). A cross-platform architecture reference maps all three event vocabularies onto one subscription lifecycle and defines the server-side entitlements source-of-truth pattern.

Complements (does not duplicate) the official Stripe skills plugin (`claude plugin install stripe@claude-plugins-official`) and Stripe MCP (`claude mcp add --transport http stripe https://mcp.stripe.com/`) — this skill focuses on testing/debugging and the iOS/Android layers Stripe doesn't cover.

### Usage

```bash
# Debug a platform-specific issue
/payments ios products not loading
/payments android purchase refunded after 3 days
/payments stripe webhook signature fails locally

# Design/review the cross-platform backend
/payments architecture
```

### Files

```
payments/
├── SKILL.md
└── references/
    ├── stripe.md
    ├── ios-storekit.md
    ├── android-play-billing.md
    └── architecture.md
```

---

## pdf-tools

Manipulate PDFs - merge, split, extract pages, rotate, compress, extract text/images.

### Installation

```bash
pip install pypdf
pip install pypdf[image]  # For image extraction
```

### Usage

```bash
SKILL="$HOME/.claude/skills/pdf-tools"

# View PDF info
python3 "$SKILL/pdf_tools.py" info document.pdf

# Merge PDFs
python3 "$SKILL/pdf_tools.py" merge file1.pdf file2.pdf file3.pdf -o combined.pdf

# Split into pages
python3 "$SKILL/pdf_tools.py" split document.pdf -o pages/

# Extract pages 1-5
python3 "$SKILL/pdf_tools.py" extract document.pdf -p 1-5 -o extract.pdf

# Extract specific pages
python3 "$SKILL/pdf_tools.py" extract document.pdf -p "1,3,5,10-15" -o selected.pdf

# Rotate 90 degrees
python3 "$SKILL/pdf_tools.py" rotate document.pdf -a 90 -o rotated.pdf

# Compress PDF
python3 "$SKILL/pdf_tools.py" compress large.pdf -o smaller.pdf

# Extract text
python3 "$SKILL/pdf_tools.py" text document.pdf -o content.txt

# Extract images
python3 "$SKILL/pdf_tools.py" images document.pdf -o images/

# Encrypt with password
python3 "$SKILL/pdf_tools.py" encrypt document.pdf --password secret -o protected.pdf

# Decrypt
python3 "$SKILL/pdf_tools.py" decrypt protected.pdf --password secret -o unlocked.pdf
```

### Files

```
pdf-tools/
├── SKILL.md
└── pdf_tools.py
```

---

## pentest

Authorized **defensive** security testing for web apps, APIs, cloud, and CI/CD. A scope-gated orchestrator (`SKILL.md`) over **41 vulnerability/recon playbooks**, with an optional [Shannon](https://github.com/KeygraphHQ/shannon) autonomous-pentester (MCP) integration. Adapted from the [vakaobr/claude-code-ai-development-workflow](https://github.com/vakaobr/claude-code-ai-development-workflow) security library.

Supports **black-box** (only a backend or web URL — no source, often no creds), **gray-box**, and **white-box** engagements. For black-box, declare `engagement_type: black_box` in the scope file and the skill starts at the `blackbox-recon` runbook: it classifies web-vs-API, fingerprints the stack from responses, discovers endpoints/parameters, maps the auth surface (self-registering test accounts only if authorized), and writes the inventory the hunters consume — then states its coverage blind spots honestly.

> ⚠️ **Authorization required.** Every run reads `security-scope.yaml` and **refuses to emit test traffic** if it is missing or contains only placeholder assets. Test only systems you own or are explicitly authorized to test. Production defaults to passive-only.

### What's inside

- **`SKILL.md`** — orchestrator: authorization gate, recon→hunter dispatch map, cross-skill chains, "No Exploit, No Report" standard.
- **`hunters/*.md`** — flattened playbooks incl. `blackbox-recon` (from-URL black-box runbook), `idor`, `bola-bfla`, `sqli`, `xss`, `dom-xss`, `ssrf`, `ssrf-cloud-metadata`, `jwt`, `oauth-oidc`, `ssti`, `xxe`, `command-injection`, `path-traversal`, `deserialization`, `csrf`, `cors-misconfig`, `clickjacking`, `open-redirect`, `graphql`, `mass-assignment`, `excessive-data-exposure`, `rate-limit`, `business-logic`, `crypto-flaw`, `aws-iam`, `s3-misconfig`, `container`, `gitlab-cicd`, `secrets-in-code`, `subdomain-takeover`, plus recon (`web-check-recon`, passive/active web recon, `api-recon`, `auth-flow-mapper`, `attack-surface-mapper`).
- **`security-scope.yaml`** — rules-of-engagement template (authorized assets, testing levels, technique restrictions).
- **`_shared/`** — finding schema, tool profiles (5 allowlists; aggressive tools like sqlmap/metasploit/hydra/nikto are forbidden by design), validation checklist.
- **`recon/web-check/`** — self-hosted [web-check](https://github.com/lissy93/web-check) container + scripts for a fast first-pass.
- **`shannon/shannon-mcp-wrapper.sh`** — launches Shannon as an MCP server, reading your Claude Code OAuth token dynamically (no API key management). Staging/localhost only.
- **`scripts/validate-skills.sh`** — structural validator (sections, scope reference, forbidden-tool catch). Currently 40 playbooks, 0 errors.

### Usage

```bash
# 1. Copy the template into your target project and populate it with real assets
cp ~/.claude/skills/pentest/security-scope.yaml ./security-scope.yaml

# 2. Ask Claude, e.g.:
#    "pentest the staging API at api.staging.internal — it's in security-scope.yaml"
# Findings append to ./security-findings/SECURITY_AUDIT.md
```

---

## pg-client

Full-featured PostgreSQL client for querying, inspecting, mutating, and graph-querying databases. Supports local, remote, and Supabase connections with saved profiles. Includes Apache AGE graph query support and RLS policy inspection.

### Installation

```bash
pip install psycopg2
```

### Usage

```bash
PG_CLIENT="$HOME/.claude/skills/pg-client/scripts/pg_client.py"

# Save connection profiles
python3 "$PG_CLIENT" profile-add local "postgresql://user:pass@localhost:5432/mydb"
python3 "$PG_CLIENT" profile-add supabase "postgresql://postgres.xxxx:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres" --supabase

# List tables
python3 "$PG_CLIENT" tables -p local

# Describe a table (columns, types, constraints, indexes, FKs, row count)
python3 "$PG_CLIENT" describe users -p supabase

# Run a query
python3 "$PG_CLIENT" query "SELECT * FROM users LIMIT 10" -p local
python3 "$PG_CLIENT" q "SELECT count(*) FROM orders" -p local -f json

# Run from a .sql file
python3 "$PG_CLIENT" query report.sql -p local

# Insert/Update with transaction safety
python3 "$PG_CLIENT" exec "INSERT INTO users (name, email) VALUES ('Leo', 'leo@example.com')" -p local
python3 "$PG_CLIENT" exec "UPDATE users SET active=true WHERE id=1 RETURNING *" -p local --returning

# Explain a query
python3 "$PG_CLIENT" explain "SELECT * FROM orders WHERE total > 100" -p local

# Search across text columns
python3 "$PG_CLIENT" search users "john" -p local

# Random sample
python3 "$PG_CLIENT" sample orders -p local -n 5

# Dump table (CSV, JSON, or INSERT statements)
python3 "$PG_CLIENT" dump users -p local -f csv
python3 "$PG_CLIENT" dump users -p local -f json -n 100

# ER Diagram generation (Mermaid)
python3 "$PG_CLIENT" erd -p local
python3 "$PG_CLIENT" erd -p local -o ./diagrams/
python3 "$PG_CLIENT" erd -p local --tables "users,orders,products"

# Database health
python3 "$PG_CLIENT" size -p local
python3 "$PG_CLIENT" activity -p supabase
python3 "$PG_CLIENT" vacuum -p local
python3 "$PG_CLIENT" slow -p local

# RLS policies (Supabase)
python3 "$PG_CLIENT" rls -p supabase
python3 "$PG_CLIENT" rls --table profiles -p supabase

# Apache AGE graph queries
python3 "$PG_CLIENT" graphs -p local
python3 "$PG_CLIENT" graph-schema my_graph -p local
python3 "$PG_CLIENT" graph my_graph "MATCH (n) RETURN n LIMIT 10" -p local
python3 "$PG_CLIENT" graph my_graph "MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name LIMIT 20" -p local
```

### Output Formats

`-f table` (default), `-f json`, `-f csv`, `-f vertical`

### Connection Options

Every command accepts `-p <profile>`, `--dsn <connection_string>`, or the `DATABASE_URL` / `PG_DSN` environment variable.

### Files

```
pg-client/
├── SKILL.md
├── profiles.json
└── scripts/
    └── pg_client.py
```

---

## release-notes

Generate a changelog / release notes from git history between two refs: resolves the range (last tag → HEAD by default), gathers commits and merged PRs (via `gh`, falling back to the github skill's `ghx.sh` when the API is blocked), categorizes changes (Breaking / Added / Fixed / Changed / Performance / Docs), writes Keep-a-Changelog markdown, and suggests a semver bump. Can prepend to CHANGELOG.md or create a **draft** GitHub release — never publishes or pushes tags without approval.

### Usage

```bash
/release-notes                                   # since the last tag
/release-notes v1.2.0 v1.3.0                     # between two refs
/release-notes --tag v2.0.0 --audience developers
```

### Files

```
release-notes/
└── SKILL.md
```

---

## rf-tools

RF/microwave engineering calculators — every command verified against textbook reference values. SI suffixes accepted on frequencies and distances.

Commands: `fspl`, `linkbudget` (with sensitivity margin), `vswr` (VSWR ↔ return loss ↔ |Γ| ↔ mismatch loss), `db` (dBm ↔ W ↔ V rms ↔ dBµV), `friis` (cascaded noise figure + noise floor), `match` (L-network synthesis), `microstrip` (Hammerstad-Jensen synthesis/analysis), `wavelength`, `attenuator` (pi/tee with E24 picks), `skin`.

### Usage

```bash
SKILL="$HOME/.claude/skills/rf-tools"

python3 "$SKILL/rf_tools.py" fspl -f 2.4G -d 100m                     # 80.05 dB
python3 "$SKILL/rf_tools.py" linkbudget --ptx 20 --gtx 2 --grx 2 -f 2.4G -d 100m --losses 2 --sens -90
python3 "$SKILL/rf_tools.py" vswr 2.0                                 # RL 9.54 dB, |Γ| 0.333
python3 "$SKILL/rf_tools.py" friis --stage 15,1 --stage=-7,7 --bw 1M  # NF 1.42 dB
python3 "$SKILL/rf_tools.py" microstrip -z 50 --er 4.4 -h 1.6mm       # W = 3.06 mm
python3 "$SKILL/rf_tools.py" attenuator -a 3 --topology pi
```

### Files

```
rf-tools/
├── SKILL.md
└── rf_tools.py
```

---

## spice

Run analog circuit simulations with ngspice in batch mode: AC/transient/DC sweeps and operating points from your netlists or bundled templates, results parsed to CSV with a stdlib ASCII plotter (log-x Bode rolloffs, transient shapes) — no GUI needed. Templates: RC lowpass, divider, series RLC, diode rectifier, MOSFET switch, ideal-op-amp inverting amp — each simulated and checked against theory (e.g. RC −3 dB measured at 159.14 Hz vs 159.15 Hz expected).

### Installation

```bash
brew install ngspice
```

### Usage

```bash
SPICE="$HOME/.claude/skills/spice/scripts/spice_run.py"

python3 "$SPICE" template list
python3 "$SPICE" template rc_lowpass -o my_filter.cir   # edit values, then:
python3 "$SPICE" run my_filter.cir -o out.csv
python3 "$SPICE" plot out.csv --log-x --db vdb_out
python3 "$SPICE" op divider.cir                          # node voltages table
```

### Files

```
spice/
├── SKILL.md
├── scripts/spice_run.py
└── templates/{rc_lowpass, divider, rlc_resonant, diode_rectifier, mosfet_switch, opamp_inverting}.cir
```

---

## study-this

Process study references (YouTube videos, PDFs, websites), create Obsidian vault notes under "Things to Study", add Google Tasks, and consolidate learnings back into the vault. Two modes: **Study** (add new references) and **Consolidate** (merge learnings into existing vault notes).

### Usage

#### Study Mode -- Adding New References

```bash
# Add a YouTube video to study
/study-this https://youtube.com/watch?v=abc123

# Add multiple references with priority
/study-this https://youtube.com/watch?v=abc123 https://docs.example.com/guide --priority high

# Add with a specific category
/study-this https://example.com/article --category "AI"
```

What it does:
1. Fetches metadata from each URL (YouTube metadata, page titles, etc.)
2. Searches the Obsidian vault for existing knowledge on the topic
3. Creates a study note in `Things to Study/` with references, summaries, and action items
4. Adds a Google Task to the "Learn and Try" list
5. Syncs the vault to GitHub and iCloud

#### Consolidate Mode -- Merging Learnings Back

```bash
# Consolidate a specific study topic
/study-this consolidate React Server Components

# Or when you finish studying
# "I finished studying the Remotion tutorial, consolidate it"
```

What it does:
1. Reads the study note and extracts key points and notes
2. Searches the vault for related knowledge notes
3. Updates existing notes with new learnings or creates new knowledge notes
4. Marks the study note as `status: consolidated`
5. Completes the Google Task
6. Syncs the vault

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--priority` | Priority level: high, medium, low | medium |
| `--category` | Category: Programming, AI, Engineering, etc. | Auto-detected |

### Files

```
study-this/
└── SKILL.md
```

---

## sync-skills

Automatically sync skills from `~/.claude/skills/` to this GitHub repository.

### Usage

```bash
# Sync all skills
/sync-skills

# Sync specific skill
/sync-skills --skill youtube-playlist

# Custom commit message
/sync-skills --message "Add new feature"

# Preview changes (dry run)
/sync-skills --dry-run

# List available skills
/sync-skills --list
```

### Files

```
sync-skills/
├── SKILL.md
└── sync_skills.py
```

---

## transcribe

Local speech-to-text for audio and video files. Auto-detects an installed Whisper backend (mlx-whisper → faster-whisper → openai-whisper → whisper.cpp); video/non-WAV input is converted to 16 kHz mono WAV via ffmpeg first. Outputs txt, srt, vtt, json, or Obsidian-ready markdown (with YAML frontmatter).

### Installation

```bash
brew install ffmpeg
pip install mlx-whisper      # recommended on Apple Silicon (or: faster-whisper / openai-whisper)
```

### Usage

```bash
SKILL="$HOME/.claude/skills/transcribe"

# Transcript to meeting.txt
python3 "$SKILL/transcribe.py" meeting.m4a

# Portuguese voice memo → markdown note with timestamps
python3 "$SKILL/transcribe.py" memo.m4a --lang pt --format md --timestamps

# Video → subtitles, best quality
python3 "$SKILL/transcribe.py" lecture.mp4 --format srt --model large-v3-turbo
```

Pipelines: yt-dlp download → transcribe (videos without CC), and transcribe `--format md` → study-this/obsidian vault notes.

### Files

```
transcribe/
├── SKILL.md
└── transcribe.py
```

---

## video-tools

Manipulate videos with ffmpeg: inspect metadata, trim, compress, convert, extract audio, GIFs, thumbnails, resize, mute, change speed, merge clips. Never overwrites outputs unless `-y` is passed. Complements generate-image (post-process Veo output) and elevenlabs (clean extracted audio).

### Installation

```bash
brew install ffmpeg
```

### Usage

```bash
SKILL="$HOME/.claude/skills/video-tools"

python3 "$SKILL/video_tools.py" info clip.mp4
python3 "$SKILL/video_tools.py" trim clip.mp4 -s 0:30 -d 10 -o cut.mp4
python3 "$SKILL/video_tools.py" compress clip.mp4 --crf 28 --width 1280 -o small.mp4
python3 "$SKILL/video_tools.py" extract-audio clip.mp4 -o audio.mp3
python3 "$SKILL/video_tools.py" gif clip.mp4 --fps 12 --width 480 -s 1 -e 4 -o demo.gif
python3 "$SKILL/video_tools.py" thumbnail clip.mp4 -t 5 -o thumb.jpg
python3 "$SKILL/video_tools.py" merge a.mp4 b.mp4 -o full.mp4
```

### Files

```
video-tools/
├── SKILL.md
└── video_tools.py
```

---

## visual-explainer

Generate beautiful, self-contained HTML pages that visually explain systems, code changes, plans, and data — Mermaid diagrams with zoom/pan, KPI dashboards, comparison tables, and magazine-quality slide decks, with anti-AI-slop guardrails. By [nicobailon](https://github.com/nicobailon/visual-explainer). Pairs naturally with the Artifact workflow and is useful for architecture overviews, diff reviews, and presentation decks.

### Usage

Ask for any visual explanation — "make a diagram of this architecture", "turn this into a slide deck", "render this as a styled HTML table". The skill triggers proactively on complex tables (4+ rows or 3+ columns).

### Notes

- Output is a single self-contained `.html` file (inlined CSS/JS) — viewable in any browser.
- `references/` holds CSS patterns, library notes, and slide patterns; `templates/` holds reference HTML; `scripts/share.sh` deploys to Vercel for a public URL.

---

## weekly-review

Aggregate the week's activity — journal entries (journal skill), calendar meetings and tasks (gws), git commits across `~/work` repos, and Obsidian notes touched — and synthesize a weekly review note saved to the vault at `Weekly Reviews/YYYY-Www.md`. Sections: summary, wins, challenges, learnings, meetings, shipped/git activity, mood & energy, open loops, and a proposed next-week focus. Missing sources are skipped and reported, never fabricated.

### Usage

```bash
/weekly-review                # current week
/weekly-review last           # previous week
/weekly-review 2026-W26 --no-save
```

### Files

```
weekly-review/
└── SKILL.md
```

---

## youtube-playlist

Extract video URLs from YouTube playlists, video metadata, and closed captions (CC) from individual videos.

### Installation

```bash
brew install yt-dlp
pip install youtube-transcript-api
```

### Usage

#### Video Metadata

```bash
python youtube_metadata.py "https://youtube.com/watch?v=VIDEO_ID"
python youtube_metadata.py "https://youtube.com/watch?v=VIDEO_ID" --format json
python youtube_metadata.py "https://youtube.com/watch?v=VIDEO_ID" --full
```

Output includes: title, channel, duration, views, likes, upload date, CC availability, chapters.

#### Closed Captions (CC)

```bash
# Extract transcript
python youtube_cc.py "https://youtube.com/watch?v=VIDEO_ID"

# Specific language
python youtube_cc.py "https://youtube.com/watch?v=VIDEO_ID" --lang pt

# With timestamps
python youtube_cc.py "https://youtube.com/watch?v=VIDEO_ID" --timestamps

# JSON format
python youtube_cc.py "https://youtube.com/watch?v=VIDEO_ID" --format json

# List available languages
python youtube_cc.py "https://youtube.com/watch?v=VIDEO_ID" --list-langs
```

#### Playlist Extraction

```bash
# Extract URLs
python youtube_playlist.py "https://youtube.com/playlist?list=PLxxx"

# With titles (markdown)
python youtube_playlist.py "https://youtube.com/playlist?list=PLxxx" --format markdown

# Limit videos
python youtube_playlist.py "https://youtube.com/playlist?list=PLxxx" --limit 10

# Save to Obsidian
python youtube_playlist.py "https://youtube.com/playlist?list=PLxxx" --save --category "Programming"
```

### Files

```
youtube-playlist/
├── SKILL.md
├── youtube_cc.py          # CC/transcript extraction
├── youtube_metadata.py    # Video metadata extraction
└── youtube_playlist.py    # Playlist URL extraction
```

### Language Codes

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish |
| `pt` | Portuguese |
| `fr` | French |
| `de` | German |
| `ja` | Japanese |
| `ko` | Korean |
| `zh-Hans` | Chinese (Simplified) |

---

## Creating New Skills

Skills are Markdown files with YAML frontmatter placed in `~/.claude/skills/<skill-name>/SKILL.md`.

### Basic Structure

```markdown
---
name: my-skill
description: Brief description of what the skill does
argument-hint: <required> [optional]
---

# Skill Title

## Dependencies

List required tools/packages.

## Usage

Document commands and options.

## Examples

Show common use cases.
```

### Best Practices

1. **Keep SKILL.md lean** - Move complex logic to external scripts to reduce token usage
2. **Use Python scripts** - For complex operations, create standalone `.py` files
3. **Document dependencies** - List all required packages with install commands
4. **Include examples** - Show common usage patterns
5. **Handle errors** - Scripts should report clear error messages

---

## Updating Skills

After modifying skills locally, sync them back to this repository using the `sync-skills` skill:

```bash
# Recommended: Use the sync-skills skill
/sync-skills

# Or sync a specific skill
/sync-skills --skill youtube-playlist --message "Fix bug in CC extraction"

# Preview changes first
/sync-skills --dry-run
```

### Manual Sync (Alternative)

```bash
cp -r ~/.claude/skills/* /path/to/my_ai_skills/
cd /path/to/my_ai_skills
git add . && git commit -m "Update skills" && git push
```

---

## CLAUDE.md Configuration

Claude Code uses `CLAUDE.md` files to define rules, preferences, and project-specific instructions. These files are automatically read at the start of each session.

> This repo ships a ready-made global rules template — see [Optional: global CLAUDE.md rules](#optional-global-claudemd-rules) above, or browse [`global/CLAUDE.md`](global/CLAUDE.md).

### File Locations

| Location | Scope | Purpose |
|----------|-------|---------|
| `~/.claude/CLAUDE.md` | **Global** | Rules that apply to ALL projects |
| `<project>/CLAUDE.md` | **Project** | Rules specific to one project |
| `<project>/<folder>/CLAUDE.md` | **Folder** | Rules for a specific folder |

Files are merged, with more specific locations taking precedence.

### Example: Global CLAUDE.md

Create `~/.claude/CLAUDE.md` for rules that apply everywhere:

```markdown
# Global Rules

## Git Commits
- Do NOT include "Co-Authored-By: Claude" or any AI mentions in commits
- Write commit messages as if written by the developer
- Keep messages concise and technical

## Code Style
- Follow existing project conventions
- Add comments only when logic is not self-evident
- Prefer simple solutions over clever ones

## Communication
- Be concise and direct
- Avoid unnecessary filler words
```

### Example: Project CLAUDE.md

Create `<project>/CLAUDE.md` for project-specific rules:

```markdown
# Project Rules

## Stack
- Python 3.11+
- FastAPI for APIs
- PostgreSQL database

## Conventions
- Use snake_case for Python files and functions
- Use PascalCase for classes
- All API endpoints must have docstrings

## Testing
- Run `pytest` before committing
- Maintain >80% code coverage

## Do NOT
- Modify files in /config/production/
- Commit .env files
- Use print() for logging (use logger instead)
```

### Common Use Cases

#### Prevent AI Mentions in Commits
```markdown
## Git
- Never include "Claude", "AI", "Co-Authored-By" in commit messages
- Write commits from developer's perspective
```

#### Enforce Code Standards
```markdown
## Code Standards
- Use type hints for all function parameters
- Maximum line length: 100 characters
- All functions must have docstrings
```

#### Project-Specific Commands
```markdown
## Commands
- Build: `npm run build`
- Test: `npm test`
- Lint: `npm run lint`
- Deploy: `./scripts/deploy.sh`
```

#### Protect Sensitive Files
```markdown
## Do NOT Modify
- .env, .env.* files
- config/secrets.json
- Any file in /production/
```

#### Define Preferred Libraries
```markdown
## Libraries
- HTTP requests: use `httpx` (not requests)
- Date handling: use `pendulum` (not datetime)
- Testing: use `pytest` (not unittest)
```

### Tips

1. **Keep it concise** - Claude reads this every session, so shorter is better
2. **Be specific** - "Use snake_case" is better than "follow Python conventions"
3. **Use headers** - Organize rules into clear sections
4. **Update regularly** - Add new rules as patterns emerge
5. **Use negative rules** - "Do NOT..." is often clearer than positive rules

### Viewing Active Rules

To see what CLAUDE.md files are active in your current session:

```bash
# Global rules
cat ~/.claude/CLAUDE.md

# Project rules (if any)
cat ./CLAUDE.md
```

---

## Hooks

Hooks are shell commands or scripts that execute automatically in response to Claude Code events. They enable automation, validation, and custom workflows.

### Available Hook Events

| Event | When It Fires |
|-------|---------------|
| `PreToolUse` | Before a tool executes (can block it) |
| `PostToolUse` | After a tool succeeds |
| `SessionStart` | When a session begins or resumes |
| `SessionEnd` | When a session terminates |
| `Notification` | When Claude needs attention |
| `PermissionRequest` | When a permission dialog appears |
| `Stop` | When Claude finishes responding |
| `PreCompact` | Before context compaction |
| `PostCompact` | After context compaction |
| `TaskCompleted` | When a task is marked complete |

### Hook Configuration

Hooks are configured in `settings.json`:

| Location | Scope |
|----------|-------|
| `~/.claude/settings.json` | Global (all projects) |
| `.claude/settings.json` | Project (can be committed) |
| `.claude/settings.local.json` | Project (gitignored) |

### Basic Hook Structure

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/validate.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook Types

| Type | Description |
|------|-------------|
| `command` | Execute a shell script |
| `http` | POST to an HTTP endpoint |
| `prompt` | Single-turn Claude evaluation |
| `agent` | Multi-turn subagent verification |

### Exit Codes

| Code | Behavior |
|------|----------|
| `0` | Success - action proceeds |
| `2` | Block - action is prevented |
| Other | Warning - action proceeds |

### Example: Block Dangerous Commands

Create `.claude/hooks/block-destructive.sh`:

```bash
#!/bin/bash
COMMAND=$(cat | jq -r '.tool_input.command')

if echo "$COMMAND" | grep -qE 'rm -rf|drop table|truncate'; then
  echo "Destructive command blocked" >&2
  exit 2
fi

exit 0
```

Configure in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-destructive.sh"
          }
        ]
      }
    ]
  }
}
```

### Example: Auto-Format After Edits

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs prettier --write 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

### Example: Desktop Notifications (macOS)

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude needs attention\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

### Example: Run Tests Before Task Completion

```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "npm test || exit 2"
          }
        ]
      }
    ]
  }
}
```

### Matcher Patterns

Matchers use regex to filter when hooks fire:

| Event | Matches Against | Examples |
|-------|-----------------|----------|
| Tool events | Tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| SessionStart | Session source | `startup`, `resume`, `compact` |
| Notification | Notification type | `permission_prompt` |

### Environment Variables

Available in hook scripts:

| Variable | Description |
|----------|-------------|
| `$CLAUDE_PROJECT_DIR` | Project root directory |
| `$CLAUDE_PLUGIN_ROOT` | Plugin directory (if applicable) |

### Managing Hooks

```bash
# View all configured hooks
/hooks

# Disable all hooks
# Add to settings.json:
{
  "disableAllHooks": true
}
```

---

## Slash Commands

Claude Code provides built-in slash commands for common operations.

### Essential Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help and available commands |
| `/clear` | Clear conversation history (aliases: `/reset`, `/new`) |
| `/compact` | Compact conversation to free context |
| `/exit` | Exit Claude Code (alias: `/quit`) |

### Context & Usage

| Command | Description |
|---------|-------------|
| `/context` | Visualize current context usage |
| `/cost` | Show token usage statistics |
| `/usage` | Show plan usage limits |
| `/stats` | Visualize usage and session history |

### Configuration

| Command | Description |
|---------|-------------|
| `/config` | Open settings interface (alias: `/settings`) |
| `/model [name]` | Select or change AI model |
| `/permissions` | View/update tool permissions |
| `/hooks` | View hook configurations |
| `/memory` | Edit CLAUDE.md memory files |
| `/theme` | Change color theme |

### Session Management

| Command | Description |
|---------|-------------|
| `/resume [session]` | Resume previous conversation (alias: `/continue`) |
| `/export [filename]` | Export conversation as text |
| `/copy [N]` | Copy last response to clipboard |
| `/rename [name]` | Rename current session |
| `/branch [name]` | Create conversation branch (alias: `/fork`) |
| `/rewind` | Rewind to previous state (alias: `/checkpoint`) |

### Development

| Command | Description |
|---------|-------------|
| `/diff` | Open interactive diff viewer |
| `/pr-comments [PR]` | Fetch GitHub PR comments |
| `/security-review` | Analyze changes for vulnerabilities |
| `/plan` | Enter plan mode |
| `/tasks` | List background tasks |

### Tools & Integrations

| Command | Description |
|---------|-------------|
| `/mcp` | Manage MCP server connections |
| `/ide` | Manage IDE integrations |
| `/skills` | List available skills |
| `/plugin` | Manage Claude Code plugins |
| `/doctor` | Diagnose installation issues |

### Modes

| Command | Description |
|---------|-------------|
| `/vim` | Toggle Vim editing mode |
| `/voice` | Toggle voice dictation |
| `/fast [on\|off]` | Toggle fast mode |
| `/sandbox` | Toggle sandbox mode |
| `/effort [level]` | Set effort level (low/medium/high/max/auto) |

### Other

| Command | Description |
|---------|-------------|
| `/feedback` | Submit feedback (alias: `/bug`) |
| `/login` | Sign in to Anthropic account |
| `/logout` | Sign out |
| `/upgrade` | Open upgrade page |
| `/desktop` | Continue in Claude Code Desktop |
| `/btw <question>` | Ask side question without adding to history |
| `/add-dir <path>` | Add new working directory |

### Tips

1. Type `/` to see all available commands
2. Commands are context-aware (some only appear when relevant)
3. MCP prompts appear as `/mcp__<server>__<prompt>`
4. Skills appear as `/<skill-name>` commands

---

## License

MIT License — see [LICENSE](LICENSE). Feel free to use, modify, and distribute
these skills. Some skills are adapted from third parties and retain their
original licenses/attribution (noted in `LICENSE`).
