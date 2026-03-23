#!/usr/bin/env python3
"""
YouTube CC/Transcript Extractor
Extracts closed captions from YouTube videos.

Usage:
    python youtube_cc.py <video_url> [options]

Options:
    --lang <code>       Language code (default: en)
    --timestamps        Include timestamps in output
    --format <fmt>      Output format: text, json, markdown (default: text)
    --list-langs        List available languages for the video
    --help              Show this help message

Examples:
    python youtube_cc.py https://www.youtube.com/watch?v=VIDEO_ID
    python youtube_cc.py https://www.youtube.com/watch?v=VIDEO_ID --lang pt
    python youtube_cc.py https://www.youtube.com/watch?v=VIDEO_ID --timestamps
    python youtube_cc.py https://www.youtube.com/watch?v=VIDEO_ID --format json
    python youtube_cc.py https://www.youtube.com/watch?v=VIDEO_ID --list-langs
"""

import sys
import re
import json

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )
    # NoTranscriptAvailable may not exist in older versions
    try:
        from youtube_transcript_api._errors import NoTranscriptAvailable
    except ImportError:
        NoTranscriptAvailable = NoTranscriptFound
except ImportError:
    print("ERROR: youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
    sys.exit(1)


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


def list_available_languages(video_id):
    """List all available transcript languages for a video."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        result = {"video_id": video_id, "manual": [], "auto_generated": []}

        for transcript in transcript_list:
            info = {
                "language": transcript.language,
                "code": transcript.language_code,
                "is_translatable": transcript.is_translatable
            }
            if transcript.is_generated:
                result["auto_generated"].append(info)
            else:
                result["manual"].append(info)

        return {"success": True, **result}

    except TranscriptsDisabled:
        return {"success": False, "error": "Transcripts are disabled for this video", "cc_available": False}
    except VideoUnavailable:
        return {"success": False, "error": "Video is unavailable"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_transcript(video_id, language_code='en', include_timestamps=False):
    """
    Get transcript for a video.

    Returns:
        dict with keys: success, transcript, language, is_generated, error
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        is_generated = False
        actual_language = language_code

        # First, try to get manual transcript
        try:
            transcript = transcript_list.find_manually_created_transcript([language_code])
            is_generated = False
        except NoTranscriptFound:
            pass

        # If no manual, try auto-generated
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript([language_code])
                is_generated = True
            except NoTranscriptFound:
                pass

        # If still not found, try translation
        if not transcript:
            try:
                for t in transcript_list:
                    if t.is_translatable:
                        transcript = t.translate(language_code)
                        is_generated = t.is_generated
                        actual_language = f"{t.language_code} -> {language_code} (translated)"
                        break
            except Exception:
                pass

        # Last resort: get any available transcript
        if not transcript:
            try:
                for t in transcript_list:
                    transcript = t
                    is_generated = t.is_generated
                    actual_language = t.language_code
                    break
            except Exception:
                pass

        if not transcript:
            return {
                "success": False,
                "error": f"No transcript available in '{language_code}' or translatable to it",
                "cc_available": False
            }

        # Fetch the transcript data
        transcript_data = transcript.fetch()

        # Handle both dict and object access (API version compatibility)
        def get_entry_data(entry):
            if isinstance(entry, dict):
                return entry.get("text", ""), entry.get("start", 0), entry.get("duration", 0)
            else:
                return getattr(entry, "text", ""), getattr(entry, "start", 0), getattr(entry, "duration", 0)

        if include_timestamps:
            entries = []
            for entry in transcript_data:
                text, start, duration = get_entry_data(entry)
                entries.append({"start": start, "duration": duration, "text": text})
        else:
            entries = [get_entry_data(entry)[0] for entry in transcript_data]

        return {
            "success": True,
            "video_id": video_id,
            "transcript": entries,
            "language": actual_language,
            "is_generated": is_generated,
            "entry_count": len(transcript_data)
        }

    except TranscriptsDisabled:
        return {"success": False, "error": "Transcripts are disabled for this video", "cc_available": False}
    except NoTranscriptAvailable:
        return {"success": False, "error": "No transcripts available for this video", "cc_available": False}
    except VideoUnavailable:
        return {"success": False, "error": "Video is unavailable"}
    except Exception as e:
        if "429" in str(e):
            return {"success": False, "error": "Rate limited by YouTube. Please wait and try again."}
        return {"success": False, "error": str(e)}


def format_output(result, output_format='text'):
    """Format the output based on requested format."""
    if not result.get("success"):
        if output_format == 'json':
            return json.dumps(result, indent=2)
        return f"ERROR: {result.get('error', 'Unknown error')}"

    transcript = result["transcript"]

    if output_format == 'json':
        return json.dumps(result, indent=2)

    elif output_format == 'markdown':
        lines = [f"# Transcript\n", f"**Language:** {result['language']}\n"]
        if isinstance(transcript[0], dict):  # Has timestamps
            for entry in transcript:
                minutes = int(entry["start"] // 60)
                seconds = int(entry["start"] % 60)
                lines.append(f"**[{minutes:02d}:{seconds:02d}]** {entry['text']}\n")
        else:
            lines.append("\n".join(transcript))
        return "\n".join(lines)

    else:  # text format
        if isinstance(transcript[0], dict):  # Has timestamps
            lines = []
            for entry in transcript:
                minutes = int(entry["start"] // 60)
                seconds = int(entry["start"] % 60)
                lines.append(f"[{minutes:02d}:{seconds:02d}] {entry['text']}")
            return "\n".join(lines)
        else:
            return " ".join(transcript)


def print_help():
    """Print help message."""
    print(__doc__)


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv:
        print_help()
        sys.exit(0 if '--help' in sys.argv else 1)

    url = sys.argv[1]
    video_id = extract_video_id(url)

    if not video_id:
        print(json.dumps({"success": False, "error": "Invalid YouTube URL"}))
        sys.exit(1)

    # Parse arguments
    lang = 'en'
    timestamps = False
    output_format = 'text'
    list_langs = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--lang' and i + 1 < len(args):
            lang = args[i + 1]
            i += 2
        elif args[i] == '--timestamps':
            timestamps = True
            i += 1
        elif args[i] == '--format' and i + 1 < len(args):
            output_format = args[i + 1]
            i += 2
        elif args[i] == '--list-langs':
            list_langs = True
            i += 1
        else:
            i += 1

    if list_langs:
        result = list_available_languages(video_id)
        print(json.dumps(result, indent=2))
    else:
        result = get_transcript(video_id, lang, timestamps)
        print(format_output(result, output_format))


if __name__ == "__main__":
    main()
