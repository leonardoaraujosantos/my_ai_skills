#!/usr/bin/env python3
"""
YouTube Playlist Extractor
Extracts video URLs and metadata from YouTube playlists using yt-dlp.

Usage:
    python youtube_playlist.py <playlist_url> [options]

Options:
    --format <fmt>      Output format: urls, titles, markdown, csv, json (default: urls)
    --limit <n>         Limit to first N videos
    --save              Save to Obsidian vault
    --category <cat>    Obsidian category (default: Uncategorized)
    --name <name>       Custom note name (default: playlist title)
    --help              Show this help message

Examples:
    python youtube_playlist.py https://youtube.com/playlist?list=PLxxx
    python youtube_playlist.py https://youtube.com/playlist?list=PLxxx --format markdown
    python youtube_playlist.py https://youtube.com/playlist?list=PLxxx --save --category "Programming"
"""

import sys
import os
import json
import subprocess
import re
from datetime import datetime

# Constants
OBSIDIAN_VAULT = "/Users/leonardoaraujo/work/leo-obsidian-vault"
PLAYLISTS_BASE = f"{OBSIDIAN_VAULT}/Resources/YouTube Playlists"


def check_ytdlp():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_playlist_data(url, limit=None):
    """Extract playlist metadata using yt-dlp."""
    cmd = ["yt-dlp", "--flat-playlist", "-J", url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        entries = data.get("entries", [])
        if limit:
            entries = entries[:limit]

        return {
            "success": True,
            "title": data.get("title", "Untitled Playlist"),
            "channel": data.get("channel") or data.get("uploader", "Unknown"),
            "description": data.get("description", ""),
            "url": url,
            "video_count": len(entries),
            "videos": [
                {
                    "title": v.get("title", "Untitled"),
                    "id": v.get("id", ""),
                    "url": f"https://www.youtube.com/watch?v={v.get('id', '')}",
                    "duration": v.get("duration_string", "N/A"),
                    "channel": v.get("channel") or v.get("uploader", "")
                }
                for v in entries if v
            ]
        }
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"yt-dlp error: {e.stderr}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse yt-dlp output"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_output(data, fmt="urls"):
    """Format playlist data based on requested format."""
    if not data.get("success"):
        return f"ERROR: {data.get('error', 'Unknown error')}"

    videos = data["videos"]

    if fmt == "urls":
        return "\n".join(v["url"] for v in videos)

    elif fmt == "titles":
        return "\n".join(f"{v['title']}: {v['url']}" for v in videos)

    elif fmt == "markdown":
        return "\n".join(f"- [{v['title']}]({v['url']})" for v in videos)

    elif fmt == "csv":
        lines = ['"Title","Channel","Duration","URL"']
        for v in videos:
            lines.append(f'"{v["title"]}","{v["channel"]}","{v["duration"]}","{v["url"]}"')
        return "\n".join(lines)

    elif fmt == "json":
        return json.dumps(data, indent=2)

    else:
        return "\n".join(v["url"] for v in videos)


def sanitize_filename(name):
    """Remove invalid filename characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def save_to_obsidian(data, category="Uncategorized", custom_name=None):
    """Save playlist to Obsidian vault."""
    if not data.get("success"):
        return {"success": False, "error": data.get("error")}

    # Prepare paths
    category_path = os.path.join(PLAYLISTS_BASE, category)
    os.makedirs(category_path, exist_ok=True)

    note_name = sanitize_filename(custom_name or data["title"])
    note_path = os.path.join(category_path, f"{note_name}.md")

    # Build markdown table
    table_rows = []
    for i, v in enumerate(data["videos"], 1):
        table_rows.append(f"| {i} | {v['title']} | {v['duration']} | [Watch]({v['url']}) |")

    # Build URL list for Notebook LM
    url_list = "\n".join(v["url"] for v in data["videos"])

    # Generate note content
    today = datetime.now().strftime("%Y-%m-%d")
    category_tag = category.lower().replace(" ", "-")

    content = f"""# {data['title']}

{data['description']}

**Source:** {data['channel']}
**Playlist URL:** {data['url']}
**Total Videos:** {data['video_count']}
**Extracted:** {today}
**Related:** [[{category}]]

---

## Videos

| # | Title | Duration | Link |
|---|-------|----------|------|
{chr(10).join(table_rows)}

---

## Notes

- Key takeaways from this playlist

---

## For Notebook LM

Copy these URLs:
```
{url_list}
```

#youtube #playlist #{category_tag}
"""

    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": note_path,
            "relative_path": f"Resources/YouTube Playlists/{category}/{note_name}.md",
            "video_count": data["video_count"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def print_help():
    """Print help message."""
    print(__doc__)


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv:
        print_help()
        sys.exit(0 if '--help' in sys.argv else 1)

    if not check_ytdlp():
        print("ERROR: yt-dlp not installed. Run: brew install yt-dlp")
        sys.exit(1)

    url = sys.argv[1]

    # Parse arguments
    fmt = "urls"
    limit = None
    save = False
    category = "Uncategorized"
    custom_name = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--format' and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i] == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == '--save':
            save = True
            i += 1
        elif args[i] == '--category' and i + 1 < len(args):
            category = args[i + 1]
            i += 2
        elif args[i] == '--name' and i + 1 < len(args):
            custom_name = args[i + 1]
            i += 2
        else:
            i += 1

    # Extract playlist data
    data = extract_playlist_data(url, limit)

    if not data.get("success"):
        print(f"ERROR: {data.get('error')}")
        sys.exit(1)

    if save:
        result = save_to_obsidian(data, category, custom_name)
        if result["success"]:
            print(f"Saved to: {result['relative_path']}")
            print(f"Videos: {result['video_count']}")
        else:
            print(f"ERROR: {result['error']}")
            sys.exit(1)
    else:
        print(format_output(data, fmt))


if __name__ == "__main__":
    main()
