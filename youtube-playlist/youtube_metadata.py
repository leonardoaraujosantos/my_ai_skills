#!/usr/bin/env python3
"""
YouTube Video Metadata Extractor
Extracts metadata from YouTube videos using yt-dlp.

Usage:
    python youtube_metadata.py <video_url> [options]

Options:
    --format <fmt>      Output format: text, json, markdown (default: text)
    --full              Include all available metadata
    --help              Show this help message

Examples:
    python youtube_metadata.py https://www.youtube.com/watch?v=VIDEO_ID
    python youtube_metadata.py https://www.youtube.com/watch?v=VIDEO_ID --format json
    python youtube_metadata.py https://www.youtube.com/watch?v=VIDEO_ID --full
"""

import sys
import json
import subprocess
import re


def check_ytdlp():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_duration(seconds):
    """Convert seconds to HH:MM:SS format."""
    if not seconds:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_number(num):
    """Format large numbers with K, M, B suffixes."""
    if not num:
        return "N/A"
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_date(date_str):
    """Format YYYYMMDD to readable date."""
    if not date_str or len(date_str) != 8:
        return "N/A"
    try:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    except Exception:
        return date_str


def extract_metadata(url, full=False):
    """Extract video metadata using yt-dlp."""
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "error": "Invalid YouTube URL"}

    cmd = ["yt-dlp", "-J", "--no-download", url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        data = json.loads(result.stdout)

        # Core metadata
        metadata = {
            "success": True,
            "video_id": video_id,
            "title": data.get("title", "Unknown"),
            "channel": data.get("channel") or data.get("uploader", "Unknown"),
            "channel_url": data.get("channel_url") or data.get("uploader_url", ""),
            "duration": format_duration(data.get("duration")),
            "duration_seconds": data.get("duration", 0),
            "upload_date": format_date(data.get("upload_date")),
            "view_count": data.get("view_count", 0),
            "view_count_formatted": format_number(data.get("view_count")),
            "like_count": data.get("like_count", 0),
            "like_count_formatted": format_number(data.get("like_count")),
            "comment_count": data.get("comment_count", 0),
            "comment_count_formatted": format_number(data.get("comment_count")),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "categories": data.get("categories", []),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail": data.get("thumbnail", ""),
        }

        # Check for subtitles/CC availability
        subtitles = data.get("subtitles", {})
        auto_captions = data.get("automatic_captions", {})
        metadata["has_manual_cc"] = len(subtitles) > 0
        metadata["has_auto_cc"] = len(auto_captions) > 0
        metadata["cc_languages"] = list(subtitles.keys()) if subtitles else []
        metadata["auto_cc_languages"] = list(auto_captions.keys())[:10] if auto_captions else []  # Limit to 10

        if full:
            # Additional metadata for --full flag
            metadata["age_limit"] = data.get("age_limit", 0)
            metadata["is_live"] = data.get("is_live", False)
            metadata["was_live"] = data.get("was_live", False)
            metadata["availability"] = data.get("availability", "public")
            metadata["channel_id"] = data.get("channel_id", "")
            metadata["channel_follower_count"] = data.get("channel_follower_count", 0)
            metadata["channel_follower_count_formatted"] = format_number(data.get("channel_follower_count"))
            metadata["chapters"] = [
                {"title": ch.get("title", ""), "start": format_duration(ch.get("start_time", 0))}
                for ch in data.get("chapters", [])
            ] if data.get("chapters") else []

        return metadata

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Request timed out"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"yt-dlp error: {e.stderr[:200] if e.stderr else 'Unknown error'}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse yt-dlp output"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_output(metadata, fmt="text"):
    """Format metadata output."""
    if not metadata.get("success"):
        if fmt == "json":
            return json.dumps(metadata, indent=2)
        return f"ERROR: {metadata.get('error', 'Unknown error')}"

    if fmt == "json":
        return json.dumps(metadata, indent=2, ensure_ascii=False)

    elif fmt == "markdown":
        cc_status = []
        if metadata.get("has_manual_cc"):
            cc_status.append(f"Manual: {', '.join(metadata['cc_languages'][:5])}")
        if metadata.get("has_auto_cc"):
            cc_status.append(f"Auto: {', '.join(metadata['auto_cc_languages'][:5])}")
        cc_info = " | ".join(cc_status) if cc_status else "None"

        chapters = ""
        if metadata.get("chapters"):
            chapters = "\n\n## Chapters\n\n" + "\n".join(
                f"- **{ch['start']}** - {ch['title']}" for ch in metadata["chapters"]
            )

        tags = ", ".join(metadata.get("tags", [])[:10]) or "None"

        return f"""# {metadata['title']}

**Channel:** [{metadata['channel']}]({metadata['channel_url']})
**Duration:** {metadata['duration']}
**Uploaded:** {metadata['upload_date']}
**Views:** {metadata['view_count_formatted']}
**Likes:** {metadata['like_count_formatted']}
**Comments:** {metadata['comment_count_formatted']}

**URL:** {metadata['url']}
**CC Available:** {cc_info}
**Tags:** {tags}

---

## Description

{metadata['description'][:1000]}{'...' if len(metadata.get('description', '')) > 1000 else ''}
{chapters}
"""

    else:  # text format
        cc_status = []
        if metadata.get("has_manual_cc"):
            cc_status.append(f"Manual ({', '.join(metadata['cc_languages'][:3])})")
        if metadata.get("has_auto_cc"):
            cc_status.append("Auto-generated")
        cc_info = ", ".join(cc_status) if cc_status else "None"

        lines = [
            f"Title:       {metadata['title']}",
            f"Channel:     {metadata['channel']}",
            f"Duration:    {metadata['duration']}",
            f"Uploaded:    {metadata['upload_date']}",
            f"Views:       {metadata['view_count_formatted']}",
            f"Likes:       {metadata['like_count_formatted']}",
            f"Comments:    {metadata['comment_count_formatted']}",
            f"CC:          {cc_info}",
            f"URL:         {metadata['url']}",
        ]

        if metadata.get("chapters"):
            lines.append(f"Chapters:    {len(metadata['chapters'])}")

        return "\n".join(lines)


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
    fmt = "text"
    full = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--format' and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i] == '--full':
            full = True
            i += 1
        else:
            i += 1

    metadata = extract_metadata(url, full)
    print(format_output(metadata, fmt))


if __name__ == "__main__":
    main()
