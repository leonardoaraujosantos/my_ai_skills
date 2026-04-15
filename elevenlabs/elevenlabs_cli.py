#!/usr/bin/env python3
"""
ElevenLabs Audio Studio — Text-to-speech, sound effects, speech-to-speech, and audio isolation.
Uses ElevenLabs API with multilingual v2, sound effects v2, and STS models.
"""

import argparse
import sys
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
BASE_URL = "https://api.elevenlabs.io/v1"


# ─── Helpers ───────────────────────────────────────────────────────────────────

def api_request(url: str, payload: dict, timeout: int = 120) -> bytes:
    """POST JSON, return raw bytes (audio)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"API error {e.code}: {body}")


def api_get_json(url: str, timeout: int = 30) -> dict:
    """GET JSON response."""
    req = urllib.request.Request(
        url,
        headers={"xi-api-key": API_KEY},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"API error {e.code}: {body}")


def api_post_multipart(url: str, fields: dict, files: dict, timeout: int = 120) -> bytes:
    """POST multipart/form-data, return raw bytes."""
    boundary = "----ElevenLabsBoundary9876543210"
    body = b""

    for key, val in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{val}\r\n".encode()

    for key, (filename, data, content_type) in files.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += data + b"\r\n"

    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "xi-api-key": API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"API error {e.code}: {err_body}")


def save_audio(data: bytes, output: str) -> str:
    """Save audio bytes to file."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def format_size(n: int) -> str:
    """Human-readable file size."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    else:
        return f"{n / (1024 * 1024):.1f} MB"


# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_tts(args):
    """Text-to-Speech."""
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    voice_id = args.voice
    model_id = args.model
    output = args.output

    # Read text from argument or stdin
    text = args.text
    if text == "-":
        text = sys.stdin.read().strip()

    if not text:
        print("Error: No text provided.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating speech...")
    print(f"  Voice: {voice_id}")
    print(f"  Model: {model_id}")
    print(f"  Format: {args.format}")
    print(f"  Text: {text[:80]}{'...' if len(text) > 80 else ''}")

    payload = {
        "text": text,
        "model_id": model_id,
        "output_format": args.format,
    }

    # Add voice settings if specified
    settings = {}
    if args.stability is not None:
        settings["stability"] = args.stability
    if args.similarity is not None:
        settings["similarity_boost"] = args.similarity
    if args.style is not None:
        settings["style"] = args.style
    if args.speed is not None:
        settings["speed"] = args.speed
    if settings:
        payload["voice_settings"] = settings

    if args.language:
        payload["language_code"] = args.language

    url = f"{BASE_URL}/text-to-speech/{voice_id}?output_format={args.format}"
    audio_data = api_request(url, payload)

    saved = save_audio(audio_data, output)
    print(f"\n  Saved: {saved} ({format_size(len(audio_data))})")
    print(f"\nDone!")


def cmd_sfx(args):
    """Sound Effects Generation."""
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    text = args.text
    output = args.output

    print(f"Generating sound effect...")
    print(f"  Prompt: {text[:80]}{'...' if len(text) > 80 else ''}")
    if args.duration:
        print(f"  Duration: {args.duration}s")
    print(f"  Format: {args.format}")

    payload = {
        "text": text,
    }
    if args.duration:
        payload["duration_seconds"] = args.duration
    if args.influence is not None:
        payload["prompt_influence"] = args.influence
    if args.loop:
        payload["loop"] = True

    url = f"{BASE_URL}/sound-generation?output_format={args.format}"
    audio_data = api_request(url, payload)

    saved = save_audio(audio_data, output)
    print(f"\n  Saved: {saved} ({format_size(len(audio_data))})")
    print(f"\nDone!")


def cmd_sts(args):
    """Speech-to-Speech (Voice Conversion)."""
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    voice_id = args.voice
    input_path = Path(args.input)
    output = args.output

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Converting speech...")
    print(f"  Input: {input_path}")
    print(f"  Voice: {voice_id}")
    print(f"  Model: {args.model}")

    audio_data = input_path.read_bytes()
    ext = input_path.suffix.lower()
    content_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
    }.get(ext, "audio/mpeg")

    fields = {
        "model_id": args.model,
    }
    if args.remove_noise:
        fields["remove_background_noise"] = "true"

    files = {
        "audio": (input_path.name, audio_data, content_type),
    }

    url = f"{BASE_URL}/speech-to-speech/{voice_id}?output_format={args.format}"
    result_data = api_post_multipart(url, fields, files)

    saved = save_audio(result_data, output)
    print(f"\n  Saved: {saved} ({format_size(len(result_data))})")
    print(f"\nDone!")


def cmd_isolate(args):
    """Audio Isolation (remove background noise)."""
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    output = args.output

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Isolating audio...")
    print(f"  Input: {input_path}")

    audio_data = input_path.read_bytes()
    ext = input_path.suffix.lower()
    content_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
    }.get(ext, "audio/mpeg")

    files = {"audio": (input_path.name, audio_data, content_type)}

    url = f"{BASE_URL}/audio-isolation"
    result_data = api_post_multipart(url, {}, files)

    saved = save_audio(result_data, output)
    print(f"\n  Saved: {saved} ({format_size(len(result_data))})")
    print(f"\nDone!")


def cmd_voices(args):
    """List available voices."""
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    params = f"page_size={args.limit}&include_total_count=true"
    if args.search:
        params += f"&search={urllib.request.quote(args.search)}"
    if args.category:
        params += f"&category={args.category}"

    url = f"https://api.elevenlabs.io/v2/voices?{params}"
    data = api_get_json(url)

    voices = data.get("voices", [])
    total = data.get("total_count", len(voices))

    print(f"Voices ({len(voices)} of {total}):\n")
    print(f"{'Voice ID':<28} {'Name':<25} {'Category':<12} {'Labels'}")
    print("-" * 90)

    for v in voices:
        vid = v.get("voice_id", "")
        name = v.get("name", "")
        cat = v.get("category", "")
        labels = v.get("labels", {})
        label_str = ", ".join(f"{k}: {val}" for k, val in labels.items()) if labels else ""
        print(f"{vid:<28} {name:<25} {cat:<12} {label_str}")

    if args.json:
        print(f"\n--- JSON ---")
        print(json.dumps(voices, indent=2))


def cmd_music(args):
    """Music Composition."""
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    output = args.output
    duration_ms = int(args.duration * 1000)

    # If --plan is provided, read JSON composition plan from file
    if args.plan:
        plan_path = Path(args.plan)
        if not plan_path.exists():
            print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
            sys.exit(1)
        plan = json.loads(plan_path.read_text())
        print(f"Composing music from plan...")
        print(f"  Plan: {plan_path}")
        print(f"  Sections: {len(plan.get('sections', []))}")
        payload = {
            "composition_plan": plan,
            "model_id": "music_v1",
            "respect_sections_durations": args.strict_duration,
        }
    else:
        # Simple prompt mode
        prompt = args.prompt
        if not prompt:
            print("Error: Provide a prompt or --plan <file.json>", file=sys.stderr)
            sys.exit(1)
        print(f"Composing music...")
        print(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"  Duration: {args.duration}s")
        print(f"  Instrumental: {args.instrumental}")
        payload = {
            "prompt": prompt,
            "music_length_ms": duration_ms,
            "model_id": "music_v1",
            "force_instrumental": args.instrumental,
        }

    if args.seed is not None:
        payload["seed"] = args.seed

    url = f"{BASE_URL}/music?output_format={args.format}"
    # Music generation can take longer
    audio_data = api_request(url, payload, timeout=300)

    saved = save_audio(audio_data, output)
    print(f"\n  Saved: {saved} ({format_size(len(audio_data))})")
    print(f"\nDone!")


def cmd_models(args):
    """List known models (hardcoded — models API requires elevated permissions)."""
    models = [
        ("eleven_multilingual_v2", "Multilingual v2 (TTS)", "29 languages"),
        ("eleven_turbo_v2_5", "Turbo v2.5 (TTS, fast)", "32 languages"),
        ("eleven_english_sts_v2", "English STS v2", "English"),
        ("eleven_multilingual_sts_v2", "Multilingual STS v2", "29 languages"),
        ("music_v1", "Music v1 (Composition)", "Instrumental + vocals"),
    ]
    print(f"Known Models:\n")
    print(f"{'Model ID':<40} {'Name':<30} {'Languages'}")
    print("-" * 85)
    for mid, name, langs in models:
        print(f"{mid:<40} {name:<30} {langs}")


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ElevenLabs Audio Studio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- tts ---
    p_tts = sub.add_parser("tts", help="Text-to-Speech")
    p_tts.add_argument("text", help="Text to speak (or '-' for stdin)")
    p_tts.add_argument("-o", "--output", default="./generated_speech.mp3", help="Output file path")
    p_tts.add_argument("-v", "--voice", default="JBFqnCBsd6RMkjVDRZzb", help="Voice ID (default: George)")
    p_tts.add_argument("-m", "--model", default="eleven_multilingual_v2", help="Model ID")
    p_tts.add_argument("-f", "--format", default="mp3_44100_128", help="Output format")
    p_tts.add_argument("--language", help="Language code (ISO 639-1, e.g., en, pt, es)")
    p_tts.add_argument("--stability", type=float, help="Voice stability (0.0-1.0)")
    p_tts.add_argument("--similarity", type=float, help="Similarity boost (0.0-1.0)")
    p_tts.add_argument("--style", type=float, help="Style exaggeration (0.0-1.0)")
    p_tts.add_argument("--speed", type=float, help="Speaking speed (0.5-2.0)")
    p_tts.set_defaults(func=cmd_tts)

    # --- sfx ---
    p_sfx = sub.add_parser("sfx", help="Sound Effects Generation")
    p_sfx.add_argument("text", help="Description of the sound effect")
    p_sfx.add_argument("-o", "--output", default="./generated_sfx.mp3", help="Output file path")
    p_sfx.add_argument("-d", "--duration", type=float, help="Duration in seconds (0.5-30)")
    p_sfx.add_argument("-f", "--format", default="mp3_44100_128", help="Output format")
    p_sfx.add_argument("--influence", type=float, help="Prompt influence (0.0-1.0, default 0.3)")
    p_sfx.add_argument("--loop", action="store_true", help="Generate loopable sound")
    p_sfx.set_defaults(func=cmd_sfx)

    # --- sts ---
    p_sts = sub.add_parser("sts", help="Speech-to-Speech (Voice Conversion)")
    p_sts.add_argument("input", help="Input audio file path")
    p_sts.add_argument("-o", "--output", default="./converted_speech.mp3", help="Output file path")
    p_sts.add_argument("-v", "--voice", default="JBFqnCBsd6RMkjVDRZzb", help="Target voice ID")
    p_sts.add_argument("-m", "--model", default="eleven_english_sts_v2", help="Model ID")
    p_sts.add_argument("-f", "--format", default="mp3_44100_128", help="Output format")
    p_sts.add_argument("--remove-noise", action="store_true", help="Remove background noise")
    p_sts.set_defaults(func=cmd_sts)

    # --- music ---
    p_music = sub.add_parser("music", help="Music Composition")
    p_music.add_argument("prompt", nargs="?", default=None, help="Text prompt for music generation")
    p_music.add_argument("-o", "--output", default="./generated_music.mp3", help="Output file path")
    p_music.add_argument("-d", "--duration", type=float, default=30, help="Duration in seconds (3-600)")
    p_music.add_argument("-f", "--format", default="mp3_44100_128", help="Output format")
    p_music.add_argument("--plan", help="Path to JSON composition plan file (overrides prompt)")
    p_music.add_argument("--instrumental", action="store_true", help="Force instrumental (no vocals)")
    p_music.add_argument("--seed", type=int, help="Random seed for reproducibility")
    p_music.add_argument("--strict-duration", action="store_true", default=True, help="Strictly respect section durations in plan")
    p_music.set_defaults(func=cmd_music)

    # --- isolate ---
    p_iso = sub.add_parser("isolate", help="Audio Isolation (remove background noise)")
    p_iso.add_argument("input", help="Input audio file path")
    p_iso.add_argument("-o", "--output", default="./isolated_audio.mp3", help="Output file path")
    p_iso.set_defaults(func=cmd_isolate)

    # --- voices ---
    p_voices = sub.add_parser("voices", help="List available voices")
    p_voices.add_argument("-s", "--search", help="Search by name/description")
    p_voices.add_argument("-c", "--category", choices=["premade", "cloned", "generated", "professional"], help="Filter by category")
    p_voices.add_argument("-l", "--limit", type=int, default=25, help="Max results (default 25)")
    p_voices.add_argument("--json", action="store_true", help="Output full JSON")
    p_voices.set_defaults(func=cmd_voices)

    # --- models ---
    p_models = sub.add_parser("models", help="List available models")
    p_models.set_defaults(func=cmd_models)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
