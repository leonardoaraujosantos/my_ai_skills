# My AI Skills

A collection of Claude Code skills for automating common tasks. These skills extend Claude Code's capabilities with specialized tools for document conversion, Google Workspace integration, Obsidian note management, and YouTube content extraction.

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
| [convert-to-md](#convert-to-md) | Convert PDF/PPTX to Markdown | `pymupdf`, `python-pptx` |
| [gws](#gws) | Google Workspace CLI integration | `gws` (npm) |
| [obsidian](#obsidian) | Obsidian vault management | Obsidian CLI |
| [youtube-playlist](#youtube-playlist) | YouTube playlist & CC extraction | `yt-dlp`, `youtube-transcript-api` |

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

After modifying skills locally, sync them back to this repository:

```bash
# Copy from Claude skills to repo
cp -r ~/.claude/skills/* /path/to/my_ai_skills/

# Commit and push
cd /path/to/my_ai_skills
git add .
git commit -m "Update skills"
git push
```

---

## License

MIT License - Feel free to use, modify, and distribute these skills.
