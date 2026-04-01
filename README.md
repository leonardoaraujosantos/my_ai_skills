# My AI Skills

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

---

## Skills Overview

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| [bookmarks](#bookmarks) | Save URLs to Obsidian vault | `requests`, `beautifulsoup4` |
| [code-review](#code-review) | Review code for architecture, security & test coverage | None |
| [convert-to-md](#convert-to-md) | Convert PDF/PPTX to Markdown | `pymupdf`, `python-pptx` |
| [coolify](#coolify) | Manage Coolify deployments & env vars via API | None |
| [csv-tools](#csv-tools) | CSV manipulation & conversion | None |
| [generate-image](#generate-image) | AI media studio: images, video, music, TTS, analysis | `GEMINI_API_KEY` env var |
| [gws](#gws) | Google Workspace CLI integration | `gws` (npm) |
| [image-tools](#image-tools) | Image manipulation | `Pillow` |
| [journal](#journal) | Daily journaling to Obsidian | None |
| [json-tools](#json-tools) | JSON manipulation & queries | None (optional: `pyyaml`) |
| [mcp-client](#mcp-client) | Test, explore & manage MCP servers | `mcp` (pip) |
| [mermaid](#mermaid) | Create cross-platform Mermaid diagrams | None |
| [obsidian](#obsidian) | Obsidian vault management | Obsidian CLI |
| [pdf-tools](#pdf-tools) | PDF manipulation | `pypdf` |
| [pg-client](#pg-client) | PostgreSQL client with graph & RLS support | `psycopg2` |
| [study-this](#study-this) | Process study references & manage Obsidian study notes | `gws` (npm), `yt-dlp` |
| [sync-skills](#sync-skills) | Sync skills to GitHub repo | None |
| [youtube-playlist](#youtube-playlist) | YouTube playlist & CC extraction | `yt-dlp`, `youtube-transcript-api` |

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

## gws

Interact with Google Workspace (Gmail, Calendar, Drive, Sheets, Docs, Tasks) using the gws CLI.

### Installation

```bash
npm install -g gws
gws auth login
```

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
$CLI search vault="Leo Knowledge" query="kubernetes"

# Read
$CLI read vault="Leo Knowledge" file="Python"

# Create
$CLI create vault="Leo Knowledge" path="Notes/NewNote.md" content="# Title\n\nContent"

# Append
$CLI append vault="Leo Knowledge" file="Python" content="\n## New Section"

# Daily notes
$CLI daily:read vault="Leo Knowledge"
$CLI daily:append vault="Leo Knowledge" content="- [ ] New task"

# Tasks
$CLI tasks vault="Leo Knowledge" todo
$CLI task vault="Leo Knowledge" file="Note" line=5 toggle

# Backlinks
$CLI backlinks vault="Leo Knowledge" file="Python"
```

### Files

```
obsidian/
└── SKILL.md
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

MIT License - Feel free to use, modify, and distribute these skills.
