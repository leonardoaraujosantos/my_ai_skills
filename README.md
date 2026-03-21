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
| [convert-to-md](#convert-to-md) | Convert PDF/PPTX to Markdown | `pymupdf`, `python-pptx` |
| [csv-tools](#csv-tools) | CSV manipulation & conversion | None |
| [gws](#gws) | Google Workspace CLI integration | `gws` (npm) |
| [image-tools](#image-tools) | Image manipulation | `Pillow` |
| [journal](#journal) | Daily journaling to Obsidian | None |
| [json-tools](#json-tools) | JSON manipulation & queries | None (optional: `pyyaml`) |
| [obsidian](#obsidian) | Obsidian vault management | Obsidian CLI |
| [pdf-tools](#pdf-tools) | PDF manipulation | `pypdf` |
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

## License

MIT License - Feel free to use, modify, and distribute these skills.
