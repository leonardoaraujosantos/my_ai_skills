# Skills Overview

Complete table of every skill in this repository. Each skill name links to its detailed section (usage, installation, files) in the [README](../README.md). This table is kept in sync with the skill directories by CI (`scripts/validate_skills.py`).

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| [android-tools](../README.md#android-tools) | Android emulator/adb/logcat recipes, ANR & Gradle build triage | Android SDK (`adb`, `emulator`, `avdmanager`) |
| [api-client](../README.md#api-client) | HTTP client with saved request collections & environments (a CLI Postman) | None |
| [app-showcase](../README.md#app-showcase) | Build a pitch deck or screenshot-driven manual from a live app | `playwright`, `gws` |
| [bookmarks](../README.md#bookmarks) | Save URLs to Obsidian vault | `requests`, `beautifulsoup4` |
| [code-review](../README.md#code-review) | Review code for architecture, security & test coverage | None |
| [cognitive-complexity](../README.md#cognitive-complexity) | Measure & rank Cognitive Complexity to target refactors | `complexipy`, `gocognit`, `eslint-plugin-sonarjs`, `clang-tidy`, `solhint`, `scc` |
| [convert-to-md](../README.md#convert-to-md) | Convert PDF/PPTX to Markdown | `pymupdf`, `python-pptx` |
| [coolify](../README.md#coolify) | Manage Coolify deployments & env vars via API | None |
| [csv-tools](../README.md#csv-tools) | CSV manipulation & conversion | None |
| [datasheet](../README.md#datasheet) | Digest component datasheets into structured part cards; compare parts | None |
| [dep-audit](../README.md#dep-audit) | Multi-ecosystem dependency vulnerability & outdated audit with upgrade plan | Per-ecosystem: `npm`, `pip-audit`, `govulncheck`, `cargo-audit` |
| [docker-tools](../README.md#docker-tools) | Docker/Compose debugging & maintenance recipes | `docker` CLI |
| [elevenlabs](../README.md#elevenlabs) | TTS, SFX, voice conversion, music & audio isolation | `ELEVENLABS_API_KEY` env var |
| [email-triage](../README.md#email-triage) | Gmail inbox triage: classify, summarize, draft replies, batch archive | `@googleworkspace/cli` (npm) |
| [eng-calc](../README.md#eng-calc) | EE + mechanical calculators: dividers, E-series, filters, AWG, thermal, beams, bolts | None |
| [finance](../README.md#finance) | Personal finance from bank/card CSV exports: ledger, rules, reports | None |
| [flashcards](../README.md#flashcards) | Flashcards from study notes for Anki or Obsidian | None (optional: `genanki`) |
| [generate-image](../README.md#generate-image) | AI media studio: images, video, music, TTS, analysis | `GEMINI_API_KEY` env var |
| [github](../README.md#github) | Resilient GitHub REST access when api.github.com is blocked | `gh`, `curl`, `jq` |
| [gws](../README.md#gws) | Google Workspace CLI integration | `@googleworkspace/cli` (npm) |
| [image-tools](../README.md#image-tools) | Image manipulation | `Pillow` |
| [ios-simulator](../README.md#ios-simulator) | Drive the iOS Simulator via `xcrun simctl`: apps, push, permissions, screenshots | Xcode |
| [journal](../README.md#journal) | Daily journaling to Obsidian | None |
| [json-tools](../README.md#json-tools) | JSON manipulation & queries | None (optional: `pyyaml`) |
| [kicad-tools](../README.md#kicad-tools) | KiCad CLI: ERC/DRC checks, BOM/netlist, gerbers & fab outputs | `kicad-cli` (KiCad 8/9) |
| [latex-tools](../README.md#latex-tools) | Compile, scaffold & debug LaTeX; IEEE/report/TikZ templates | `latexmk` (MacTeX) or `tectonic` |
| [lit-review](../README.md#lit-review) | Systematic literature review: matrix, contradictions, cited survey note | None |
| [markitdown-hook](../README.md#markitdown-hook) | Auto-convert PDF/Office docs to Markdown on Read (token saver) | `markitdown[all]` (auto-installed) |
| [mcp-client](../README.md#mcp-client) | Test, explore & manage MCP servers | `mcp` (pip) |
| [mermaid](../README.md#mermaid) | Create cross-platform Mermaid diagrams | None |
| [mobile-device-testing](../README.md#mobile-device-testing) | Tests on real devices & device farms: XCUITest on hardware, Maestro, Firebase Test Lab | Xcode / Android SDK (optional: maestro, gcloud) |
| [mobile-profiling](../README.md#mobile-profiling) | CLI profiling: Instruments/xctrace (iOS), Perfetto/Macrobenchmark (Android) | Xcode / Android SDK+NDK |
| [mobile-publish](../README.md#mobile-publish) | App Store & Google Play release pipelines, TestFlight/tracks, review playbooks | Xcode / Android SDK (optional: fastlane, bundletool) |
| [notebooklm](../README.md#notebooklm) | Full Google NotebookLM API: notebooks, sources, artifacts | `notebooklm-py` (pip) |
| [obsidian](../README.md#obsidian) | Obsidian vault management | Obsidian CLI |
| [openspec](../README.md#openspec) | Spec-driven development with OpenSpec | `openspec` CLI (Node ≥ 20) |
| [openspec-baseline](../README.md#openspec-baseline) | Onboard a brownfield codebase onto OpenSpec + CI | `openspec` CLI |
| [payments](../README.md#payments) | Payment/subscription dev & debugging for Stripe, iOS StoreKit, Play Billing | None (optional: Stripe CLI, Stripe MCP) |
| [pdf-tools](../README.md#pdf-tools) | PDF manipulation | `pypdf` |
| [pentest](../README.md#pentest) | Authorized defensive security testing — 41 vuln/recon playbooks + Shannon | Per-playbook CLI tools (curl, ffuf, nuclei…); Docker for Shannon |
| [pg-client](../README.md#pg-client) | PostgreSQL client with graph & RLS support | `psycopg2` |
| [release-notes](../README.md#release-notes) | Changelog / release notes from git history between refs | `gh` (fallback: github skill) |
| [rf-tools](../README.md#rf-tools) | RF calculators: link budget, VSWR, Friis NF, matching, microstrip, attenuators | None |
| [spice](../README.md#spice) | ngspice batch simulation: AC/tran/DC/op, circuit templates, CSV + ASCII plots | `ngspice` |
| [study-this](../README.md#study-this) | Process study references & manage Obsidian study notes | `@googleworkspace/cli` (npm), `yt-dlp` |
| [sync-skills](../README.md#sync-skills) | Sync skills to GitHub repo | None |
| [transcribe](../README.md#transcribe) | Local Whisper speech-to-text for audio/video (txt/srt/vtt/json/md) | `ffmpeg` + a Whisper backend |
| [video-tools](../README.md#video-tools) | Video manipulation with ffmpeg: trim, compress, GIF, merge | `ffmpeg` |
| [visual-explainer](../README.md#visual-explainer) | Generate self-contained HTML diagrams, slide decks & dashboards | None (optional: `surf-cli` for AI images) |
| [weekly-review](../README.md#weekly-review) | Weekly review note from journal, calendar, tasks & git activity | journal, gws & obsidian skills |
| [xcode-tools](../README.md#xcode-tools) | xcodebuild/xcresult/signing/symbolication/devicectl recipes | Xcode |
| [youtube-playlist](../README.md#youtube-playlist) | YouTube playlist & CC extraction | `yt-dlp`, `youtube-transcript-api` |
