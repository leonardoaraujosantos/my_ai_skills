---
name: youtube-playlist
description: Extract video URLs from YouTube playlists for use with Notebook LM or other tools. Also extracts closed captions (CC) from individual YouTube videos. Use when the user wants to extract videos from a playlist, get playlist URLs, extract video transcripts/captions, or prepare content for AI-powered study materials.
argument-hint: <url> [--cc] [--lang <code>] [--timestamps] [--format json|text|markdown] [--save] [--category "Topic"] [--name "Note Name"]
---

# YouTube Playlist & CC Extractor

## Scripts Location

```bash
SKILL_DIR="$HOME/.claude/skills/youtube-playlist"
```

## Dependencies

```bash
brew install yt-dlp && pip install youtube-transcript-api
```

---

## Video Metadata

Extract video info (title, channel, views, duration, CC availability, chapters).

```bash
python3 "$SKILL_DIR/youtube_metadata.py" <url> [options]
```

| Option | Description |
|--------|-------------|
| `--format <fmt>` | text, json, markdown |
| `--full` | Include chapters, channel stats, etc. |

---

## CC Extraction (Single Videos)

Use when URL contains `watch?v=` or `youtu.be/` (without `list=`).

```bash
python3 "$SKILL_DIR/youtube_cc.py" <url> [options]
```

| Option | Description |
|--------|-------------|
| `--lang <code>` | Language: en, es, pt, fr, de, ja, ko, zh-Hans |
| `--timestamps` | Include timestamps |
| `--format <fmt>` | text, json, markdown |
| `--list-langs` | List available languages |

---

## Playlist Extraction

Use when URL contains `playlist?list=` or `list=`.

```bash
python3 "$SKILL_DIR/youtube_playlist.py" <url> [options]
```

| Option | Description |
|--------|-------------|
| `--format <fmt>` | urls, titles, markdown, csv, json |
| `--limit <n>` | Limit to first N videos |
| `--save` | Save to Obsidian vault |
| `--category <cat>` | Obsidian category |
| `--name <name>` | Custom note name |

---

## Examples

```bash
# Video metadata
python3 "$SKILL_DIR/youtube_metadata.py" "https://youtube.com/watch?v=xxx"
python3 "$SKILL_DIR/youtube_metadata.py" "https://youtube.com/watch?v=xxx" --format json --full

# CC extraction
python3 "$SKILL_DIR/youtube_cc.py" "https://youtube.com/watch?v=xxx"
python3 "$SKILL_DIR/youtube_cc.py" "https://youtube.com/watch?v=xxx" --lang pt --timestamps

# Playlist extraction
python3 "$SKILL_DIR/youtube_playlist.py" "https://youtube.com/playlist?list=xxx"
python3 "$SKILL_DIR/youtube_playlist.py" "https://youtube.com/playlist?list=xxx" --format markdown

# Save to Obsidian
python3 "$SKILL_DIR/youtube_playlist.py" "https://youtube.com/playlist?list=xxx" --save --category "Programming"
```

## Categories

Programming | ML Artificial Intelligence | Blockchain | Engineering | Mathematics | Physics | Uncategorized
