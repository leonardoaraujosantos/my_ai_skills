#!/usr/bin/env python3
"""
Creative AI Studio — Generate images, videos, music, speech, and analyze media.

Image generation supports two providers:
  - OpenAI    (default): gpt-image-1, dall-e-3, dall-e-2  -> needs OPENAI_API_KEY
  - Google    (gemini):  Imagen 4 / Nano Banana 2          -> needs GEMINI_API_KEY

Video / Music / TTS / Analyze are Gemini-only -> need GEMINI_API_KEY.

API keys are read from environment variables. Do NOT hardcode keys here.
"""

import argparse
import base64
import sys
import os
import json
import time
import urllib.request
import urllib.error
import mimetypes
from pathlib import Path

# Gemini (Google)
API_KEY = os.environ.get("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = "https://api.openai.com/v1"


# ─── Helpers ───────────────────────────────────────────────────────────────────

def api_request(url: str, payload: dict, timeout: int = 120) -> dict:
    """Make a POST request to the Gemini API."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"API error {e.code}: {error_body}")


def api_get(url: str, timeout: int = 120) -> dict:
    """Make a GET request to the Gemini API."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def save_binary(data: bytes, output: str, index: int = 0, total: int = 1) -> str:
    """Save binary data to file, handling multi-output numbering."""
    output_path = Path(output)
    stem = output_path.stem
    suffix = output_path.suffix
    parent = output_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    if total == 1:
        filepath = parent / f"{stem}{suffix}"
    else:
        filepath = parent / f"{stem}_{index + 1}{suffix}"

    filepath.write_bytes(data)
    size_kb = len(data) / 1024
    print(f"  Saved: {filepath} ({size_kb:.0f} KB)")
    return str(filepath)


def api_request_openai(endpoint: str, payload: dict, timeout: int = 300) -> dict:
    """POST to OpenAI API with Bearer authentication. Reads OPENAI_API_KEY from env."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable not set. "
            "Add it to ~/.claude/settings.json under the 'env' block, or "
            "`export OPENAI_API_KEY=sk-...` in your shell."
        )
    url = f"{OPENAI_BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"OpenAI API error {e.code}: {error_body}")


# ─── IMAGE GENERATION ──────────────────────────────────────────────────────────

def cmd_generate_image(prompt: str, output: str, size: str, count: int, model: str):
    """Generate images using Imagen or Nano Banana 2 fallback."""
    aspect_map = {
        "1024x1024": "1:1", "1536x1024": "3:2", "1024x1536": "2:3",
        "1792x1024": "16:9", "1024x1792": "9:16",
    }
    aspect_ratio = aspect_map.get(size, "1:1")

    print(f"Generating image...")
    print(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"  Size: {size} ({aspect_ratio})")
    print(f"  Model: {model}")
    print()

    # Try Imagen predict endpoint first
    try:
        url = f"{BASE_URL}/models/{model}:predict?key={API_KEY}"
        data = api_request(url, {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": count, "aspectRatio": aspect_ratio},
        })
        predictions = data.get("predictions", [])
        if predictions:
            saved = []
            for i, pred in enumerate(predictions):
                img_b64 = pred.get("bytesBase64Encoded", "")
                if img_b64:
                    saved.append(save_binary(base64.b64decode(img_b64), output, i, len(predictions)))
            if saved:
                return saved
    except RuntimeError as e:
        print(f"  Imagen unavailable, using Nano Banana 2...", file=sys.stderr)

    # Fallback: Nano Banana 2
    url = f"{BASE_URL}/models/nano-banana-pro-preview:generateContent?key={API_KEY}"
    data = api_request(url, {
        "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    })

    saved = []
    idx = 0
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData", {})
            if inline.get("mimeType", "").startswith("image/"):
                saved.append(save_binary(base64.b64decode(inline["data"]), output, idx, count))
                idx += 1

    if not saved:
        # Print any text response for debugging
        for c in data.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                if "text" in p:
                    print(f"  API text: {p['text']}", file=sys.stderr)
        print("Error: No images generated.", file=sys.stderr)
        sys.exit(1)

    return saved


# ─── IMAGE GENERATION (OpenAI) ─────────────────────────────────────────────────

def cmd_generate_image_openai(prompt: str, output: str, size: str, count: int,
                              model: str, quality: str, style: str):
    """Generate images using OpenAI Images API.

    Models supported:
      - gpt-image-1 (default): newest model, best at text-in-image; sizes
        1024x1024, 1024x1536, 1536x1024; quality low|medium|high.
      - dall-e-3: photo-realistic, sizes 1024x1024, 1024x1792, 1792x1024;
        quality standard|hd; style vivid|natural; n is forced to 1.
      - dall-e-2: cheap legacy, 256x256, 512x512, 1024x1024; quality ignored.
    """
    print(f"Generating image (OpenAI)...")
    print(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"  Size: {size}")
    print(f"  Model: {model}")
    print(f"  Quality: {quality}")
    if model == "dall-e-3":
        print(f"  Style: {style}")
    print(f"  Count: {count}")
    print()

    payload = {
        "model": model,
        "prompt": prompt,
        "n": count,
        "size": size,
    }

    if model == "dall-e-3":
        # DALL-E 3 only supports n=1 per request
        if count > 1:
            print(f"  Note: dall-e-3 supports n=1 only; clamping count to 1.")
            payload["n"] = 1
        payload["quality"] = quality if quality in ("standard", "hd") else "standard"
        payload["style"] = style if style in ("vivid", "natural") else "vivid"
        payload["response_format"] = "b64_json"
    elif model == "gpt-image-1":
        payload["quality"] = quality if quality in ("low", "medium", "high") else "medium"
        # gpt-image-1 always returns b64; no response_format flag needed.
    elif model == "dall-e-2":
        payload["response_format"] = "b64_json"
    else:
        # Unknown model — pass through; OpenAI will validate.
        payload["response_format"] = "b64_json"

    try:
        data = api_request_openai("/images/generations", payload, timeout=300)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    items = data.get("data", [])
    if not items:
        print(f"Error: no images returned. Response: "
              f"{json.dumps(data, indent=2)[:500]}", file=sys.stderr)
        sys.exit(1)

    saved = []
    for i, img in enumerate(items):
        b64 = img.get("b64_json", "")
        if not b64:
            print(f"  Warning: no b64 data in response item {i}", file=sys.stderr)
            continue
        saved.append(save_binary(base64.b64decode(b64), output, i, len(items)))

    if not saved:
        print("Error: no image bytes extracted from response.", file=sys.stderr)
        sys.exit(1)

    return saved


# ─── VIDEO GENERATION ──────────────────────────────────────────────────────────

def cmd_generate_video(prompt: str, output: str, model: str, duration: str,
                       image_path: str = None):
    """Generate video using Veo 3.1 / Veo 3 / Veo 2."""
    print(f"Generating video...")
    print(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"  Model: {model}")
    print(f"  Duration: {duration}")
    if image_path:
        print(f"  Reference image: {image_path}")
    print()

    # Build request
    instance = {"prompt": prompt}

    # If reference image provided (image-to-video)
    if image_path:
        img_path = Path(image_path)
        if not img_path.exists():
            print(f"Error: Image not found: {image_path}", file=sys.stderr)
            sys.exit(1)
        img_bytes = img_path.read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        mime, _ = mimetypes.guess_type(str(img_path))
        instance["image"] = {"bytesBase64Encoded": img_b64, "mimeType": mime or "image/png"}

    url = f"{BASE_URL}/models/{model}:predictLongRunning?key={API_KEY}"
    payload = {
        "instances": [instance],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": int(duration.rstrip("s")),
        },
    }

    try:
        data = api_request(url, payload)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Get operation name for polling
    op_name = data.get("name", "")
    if not op_name:
        print(f"Error: No operation returned. Response: {json.dumps(data, indent=2)}", file=sys.stderr)
        sys.exit(1)

    print(f"  Operation started: {op_name}")
    print(f"  Polling for completion...")

    # Poll until done
    poll_url = f"{BASE_URL}/{op_name}?key={API_KEY}"
    max_wait = 600  # 10 minutes max
    elapsed = 0
    poll_interval = 10

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            status = api_get(poll_url)
        except Exception as e:
            print(f"  Poll error: {e}, retrying...", file=sys.stderr)
            continue

        done = status.get("done", False)
        if not done:
            metadata = status.get("metadata", {})
            progress = metadata.get("progressPercent", "?")
            print(f"  [{elapsed}s] Progress: {progress}%")
            continue

        # Done — extract video
        response = status.get("response", {})
        videos = response.get("generateVideoResponse", {}).get("generatedSamples", [])

        if not videos:
            # Try alternate response structure
            videos = response.get("videos", [])

        if not videos:
            error = status.get("error", {})
            if error:
                print(f"Error: {error.get('message', 'Unknown error')}", file=sys.stderr)
            else:
                print(f"Error: No videos in response. Full response: {json.dumps(status, indent=2)}", file=sys.stderr)
            sys.exit(1)

        saved = []
        for i, vid in enumerate(videos):
            # Try base64 first
            vid_b64 = vid.get("video", {}).get("bytesBase64Encoded", "")
            if not vid_b64:
                vid_b64 = vid.get("bytesBase64Encoded", "")
            if vid_b64:
                saved.append(save_binary(base64.b64decode(vid_b64), output, i, len(videos)))
                continue

            # Try URI download
            uri = vid.get("video", {}).get("uri", "")
            if not uri:
                uri = vid.get("uri", "")
            if uri:
                # Append API key if needed
                dl_url = uri if "key=" in uri else f"{uri}&key={API_KEY}" if "?" in uri else f"{uri}?key={API_KEY}"
                print(f"  Downloading video from URI...")
                try:
                    dl_req = urllib.request.Request(dl_url, method="GET")
                    with urllib.request.urlopen(dl_req, timeout=120) as dl_resp:
                        vid_bytes = dl_resp.read()
                    saved.append(save_binary(vid_bytes, output, i, len(videos)))
                except Exception as dl_err:
                    print(f"  Download error: {dl_err}", file=sys.stderr)

        if saved:
            print(f"\nDone! Generated {len(saved)} video(s)")
            return saved

        print("Error: Could not extract video data.", file=sys.stderr)
        sys.exit(1)

    print(f"Error: Timed out after {max_wait}s.", file=sys.stderr)
    sys.exit(1)


# ─── MUSIC GENERATION ──────────────────────────────────────────────────────────

def cmd_generate_music(prompt: str, output: str, model: str, duration: int):
    """Generate music using Lyria 3."""
    print(f"Generating music...")
    print(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"  Model: {model}")
    print(f"  Duration: {duration}s")
    print()

    url = f"{BASE_URL}/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
        },
    }

    try:
        data = api_request(url, payload, timeout=180)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract audio from response
    saved = []
    idx = 0
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData", {})
            mime = inline.get("mimeType", "")
            if mime.startswith("audio/"):
                audio_bytes = base64.b64decode(inline["data"])
                # Detect actual format from bytes, not just MIME
                if audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
                    ext = ".mp3"
                elif audio_bytes[:4] == b'RIFF':
                    ext = ".wav"
                elif audio_bytes[:4] == b'OggS':
                    ext = ".ogg"
                elif audio_bytes[:4] == b'fLaC':
                    ext = ".flac"
                else:
                    ext_map = {"audio/wav": ".wav", "audio/mp3": ".mp3", "audio/mpeg": ".mp3",
                               "audio/ogg": ".ogg", "audio/aac": ".aac"}
                    ext = ext_map.get(mime, ".mp3")

                out_path = Path(output)
                output_fixed = str(out_path.with_suffix(ext))
                print(f"  Detected format: {ext} (MIME: {mime})")

                saved.append(save_binary(audio_bytes, output_fixed, idx, 1))
                idx += 1

    if not saved:
        # Check for text response
        for c in data.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                if "text" in p:
                    print(f"  API text: {p['text']}", file=sys.stderr)
        print("Error: No audio generated.", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone! Generated {len(saved)} audio file(s)")
    return saved


# ─── TEXT-TO-SPEECH ────────────────────────────────────────────────────────────

def wrap_pcm_as_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    """Wrap raw PCM audio data with a proper WAV header."""
    import struct
    byte_rate = sample_rate * channels * (bits // 8)
    block_align = channels * (bits // 8)
    data_size = len(pcm_data)
    # Strip leading silence/zeros (common in Gemini TTS output)
    first_nonzero = 0
    for i, b in enumerate(pcm_data):
        if b != 0:
            # Align to sample boundary
            first_nonzero = (i // block_align) * block_align
            break
    if first_nonzero > 0 and first_nonzero < len(pcm_data) * 0.1:
        pcm_data = pcm_data[first_nonzero:]
        data_size = len(pcm_data)

    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1,  # PCM format
        channels, sample_rate, byte_rate, block_align, bits,
        b'data', data_size)
    return header + pcm_data


def cmd_tts(text: str, output: str, model: str, voice: str):
    """Generate speech using Gemini TTS models."""
    print(f"Generating speech...")
    print(f"  Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"  Model: {model}")
    print(f"  Voice: {voice}")
    print()

    url = f"{BASE_URL}/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": text}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice,
                    }
                }
            },
        },
    }

    try:
        data = api_request(url, payload, timeout=120)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    saved = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData", {})
            mime = inline.get("mimeType", "")
            if inline.get("data") and ("audio" in mime or mime == ""):
                audio_bytes = base64.b64decode(inline["data"])

                # Gemini TTS returns raw PCM — wrap with WAV header
                if not audio_bytes[:4] == b'RIFF' and not audio_bytes[:3] == b'ID3' and not audio_bytes[:2] == b'\xff\xfb':
                    print(f"  Wrapping raw PCM with WAV header (24kHz, 16-bit)...")
                    audio_bytes = wrap_pcm_as_wav(audio_bytes, sample_rate=24000, channels=1, bits=16)

                out_path = Path(output)
                if not out_path.suffix:
                    output = str(out_path.with_suffix(".wav"))
                saved.append(save_binary(audio_bytes, output, 0, 1))

    if not saved:
        for c in data.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                if "text" in p:
                    print(f"  API text: {p['text']}", file=sys.stderr)
        print("Error: No audio generated.", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone! Generated speech audio")
    return saved


# ─── IMAGE ANALYSIS ────────────────────────────────────────────────────────────

def cmd_analyze(image_path: str, target: str = "all", output_file: str = None) -> str:
    """Analyze an image and extract prompts for various AI generation tools."""
    filepath = Path(image_path)
    if not filepath.exists():
        print(f"Error: File not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    img_bytes = filepath.read_bytes()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    mime_type, _ = mimetypes.guess_type(str(filepath))
    if not mime_type:
        mime_type = "image/png"

    target_instructions = {
        "all": """Analyze this image in detail and generate prompts optimized for each of these AI tools:

## 1. IMAGE GENERATION (Nano Banana 2 / Midjourney / DALL-E)
Write a detailed text-to-image prompt that would recreate this image. Include:
- Subject description (characters, objects, scene)
- Art style (rendering, lighting, color palette)
- Composition and camera angle
- Mood and atmosphere
- Technical details (resolution hint, aspect ratio)

## 2. VIDEO GENERATION (Veo 3.1)
Write a video generation prompt that brings this image to life as a short animated clip. Include:
- Scene description and setting
- Character actions and movement
- Camera movement (pan, zoom, orbit, tracking)
- Lighting and atmosphere changes
- Duration suggestion and pacing
- Style notes (cel-shaded, cinematic, anime, etc.)

## 3. MUSIC GENERATION (Lyria 3)
Write a music generation prompt for background audio that matches this image's mood. Include:
- Genre and style
- Tempo (BPM)
- Key/scale
- Instruments
- Mood and energy level
- Duration

## 4. SOUND EFFECTS (ElevenLabs SFX)
List 3-5 specific sound effect prompts for sounds that would exist in this scene. Each should be a standalone SFX prompt.

## 5. TEXT-TO-SPEECH (Gemini TTS)
If there are characters, describe their voice and write a sample line they would say. If no characters, write a narrator description + narration for the scene.

## 6. PROMPT COMMANDS
At the end, provide ready-to-run commands using this tool:
```
generate <image_prompt> --output recreated.png
video <video_prompt> --output scene.mp4
music <music_prompt> --output soundtrack.wav
tts <narration_text> --output narration.wav
```""",

        "image": """Analyze this image and write a detailed text-to-image prompt that would recreate it in AI image generators (Nano Banana 2, Midjourney, DALL-E, Stable Diffusion). Include:
- Subject description with precise details
- Art style, rendering technique, color palette
- Composition, camera angle, framing
- Lighting setup and atmosphere
- Background and environment
- Mood and emotional tone
- Technical: suggest aspect ratio and style keywords""",

        "video": """Analyze this image and write a video generation prompt (for Veo 3.1) that brings this scene to life as a 5-8 second animated clip. Include:
- Scene description matching the image
- Character/object movement and actions
- Camera movement (specify: static, pan, zoom, orbit, dolly, tracking shot)
- Lighting transitions (time of day, shadows, effects)
- Atmosphere and particle effects
- Pacing and duration
- Art style consistency notes""",

        "music": """Analyze this image and write an AI music generation prompt (for Lyria 3 / Suno) for background music matching the mood. Include:
- Genre and sub-genre
- Tempo in BPM
- Musical key and scale
- Primary and secondary instruments
- Mood descriptors
- Structure (intro, verse, chorus, etc.)
- Duration suggestion
- Reference tracks if applicable""",

        "sfx": """Analyze this image and list 5-8 specific sound effect prompts for SFX generation. Each sound should be something that would naturally exist in this scene. For each, write:
- A standalone SFX prompt (descriptive, 1-3 sentences)
- Duration estimate
- Priority (essential vs ambient)""",

        "voice": """Analyze this image. If there are characters, describe their voice for TTS:
- Vocal qualities (pitch, tone, texture, accent)
- Speaking style (pace, emotion, delivery)
- Character personality reflected in voice
- A sample dialogue line the character might say in this scene

If no characters, describe a narrator voice and write a short narration for the scene.""",
    }

    instruction = target_instructions.get(target, target_instructions["all"])

    print(f"Analyzing image: {image_path}")
    print(f"  Target: {target}")
    print()

    url = f"{BASE_URL}/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    data = api_request(url, {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": img_b64}},
                {"text": instruction},
            ]
        }],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
    })

    candidates = data.get("candidates", [])
    if not candidates:
        print("Error: No response from API.", file=sys.stderr)
        sys.exit(1)

    text_parts = []
    for candidate in candidates:
        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                text_parts.append(part["text"])

    result = "\n".join(text_parts)

    if output_file:
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result, encoding="utf-8")
        print(f"Saved analysis to: {output_file}\n")

    print(result)
    return result


# ─── MAIN CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Creative AI Studio — Image (OpenAI / Gemini), Video, Music, Speech, Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate (g)  Generate image (OpenAI gpt-image-1 default; Gemini Imagen 4 / Nano Banana 2 via --provider gemini)
  video (v)     Generate video from text or image (Veo 3.1)
  music (m)     Generate music from text prompt (Lyria 3)
  tts (t)       Text-to-speech (Gemini TTS)
  analyze (a)   Analyze image → extract prompts for all tools

Environment variables:
  OPENAI_API_KEY   required for `generate` with --provider openai (default)
  GEMINI_API_KEY   required for `generate --provider gemini`, video, music, tts, analyze

Examples:
  # OpenAI (default)
  %(prog)s generate "A cute robot" --output robot.png
  %(prog)s generate "Photorealistic Bridgetown skyline" -m dall-e-3 -s 1792x1024 --quality hd
  %(prog)s generate "Constellation 256-QAM diagram" -m gpt-image-1 --quality high

  # Gemini
  %(prog)s generate "A cute robot, anime style" --provider gemini --output robot.png

  # Video / Music / TTS / Analyze (all Gemini)
  %(prog)s video "A robot walking through wasteland" --output scene.mp4
  %(prog)s video "Robot discovers a plant" --image ref.png --output scene.mp4
  %(prog)s music "Hopeful orchestral, 90 BPM, D major" --output theme.wav
  %(prog)s tts "Hello, I am Kiko" --voice Kore --output hello.wav
  %(prog)s analyze screenshot.png --target all
  %(prog)s analyze art.png --target video --output prompts.md
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── Generate Image ──
    p_gen = subparsers.add_parser("generate", aliases=["gen", "g"], help="Generate image")
    p_gen.add_argument("prompt", help="Text prompt")
    p_gen.add_argument("--output", "-o", default="./generated_image.png")
    p_gen.add_argument("--size", "-s", default="1024x1024",
                       help="OpenAI: 1024x1024, 1024x1536, 1536x1024 (gpt-image-1) | "
                            "1024x1024, 1024x1792, 1792x1024 (dall-e-3). "
                            "Gemini: 1024x1024, 1536x1024, 1024x1536")
    p_gen.add_argument("--count", "-n", type=int, default=1, choices=[1, 2, 3, 4])
    p_gen.add_argument("--provider", "-p", default="openai",
                       choices=["openai", "gemini"],
                       help="Image provider (default: openai)")
    p_gen.add_argument("--model", "-m", default=None,
                       help="Model to use. Defaults: openai=gpt-image-1, "
                            "gemini=imagen-4.0-generate-001. "
                            "Other OpenAI: dall-e-3, dall-e-2.")
    p_gen.add_argument("--quality", default=None,
                       help="OpenAI only. gpt-image-1: low|medium|high (default medium). "
                            "dall-e-3: standard|hd (default standard).")
    p_gen.add_argument("--style", default="vivid",
                       choices=["vivid", "natural"],
                       help="OpenAI dall-e-3 only (default: vivid).")

    # ── Generate Video ──
    p_vid = subparsers.add_parser("video", aliases=["vid", "v"], help="Generate video")
    p_vid.add_argument("prompt", help="Text prompt describing the video")
    p_vid.add_argument("--output", "-o", default="./generated_video.mp4")
    p_vid.add_argument("--model", "-m", default="veo-3.1-generate-preview",
                       help="veo-3.1-generate-preview, veo-3.1-fast-generate-preview, veo-3.0-generate-001, veo-3.0-fast-generate-001")
    p_vid.add_argument("--duration", "-d", default="8s", help="Duration: 5s, 8s (default), 10s")
    p_vid.add_argument("--image", "-i", default=None, help="Reference image for image-to-video")

    # ── Generate Music ──
    p_mus = subparsers.add_parser("music", aliases=["mus", "m"], help="Generate music")
    p_mus.add_argument("prompt", help="Text prompt describing the music")
    p_mus.add_argument("--output", "-o", default="./generated_music.wav")
    p_mus.add_argument("--model", "-m", default="lyria-3-clip-preview",
                       help="lyria-3-clip-preview (30s), lyria-3-pro-preview (longer)")
    p_mus.add_argument("--duration", "-d", type=int, default=30, help="Duration in seconds")

    # ── Text-to-Speech ──
    p_tts = subparsers.add_parser("tts", aliases=["t"], help="Text-to-speech")
    p_tts.add_argument("text", help="Text to speak")
    p_tts.add_argument("--output", "-o", default="./generated_speech.wav")
    p_tts.add_argument("--model", "-m", default="gemini-2.5-flash-preview-tts")
    p_tts.add_argument("--voice", "-v", default="Kore",
                       help="Voice: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Io, Elara, Umbriel, Algieba")

    # ── Analyze Image ──
    p_ana = subparsers.add_parser("analyze", aliases=["ana", "a"], help="Analyze image → prompts")
    p_ana.add_argument("image", help="Path to image file")
    p_ana.add_argument("--target", "-t", default="all",
                       choices=["all", "image", "video", "music", "sfx", "voice"])
    p_ana.add_argument("--output", "-o", default=None, help="Save to markdown file")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    def require_gemini_key():
        if not API_KEY:
            print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
            print("Add it to ~/.claude/settings.json under 'env', or "
                  "`export GEMINI_API_KEY=...` in your shell.", file=sys.stderr)
            sys.exit(1)

    def require_openai_key():
        if not OPENAI_API_KEY:
            print("Error: OPENAI_API_KEY environment variable not set.", file=sys.stderr)
            print("Add it to ~/.claude/settings.json under 'env', or "
                  "`export OPENAI_API_KEY=sk-...` in your shell.", file=sys.stderr)
            sys.exit(1)

    if args.command in ("generate", "gen", "g"):
        if args.provider == "openai":
            require_openai_key()
            model = args.model or "gpt-image-1"
            quality = args.quality or ("standard" if model == "dall-e-3" else "medium")
            saved = cmd_generate_image_openai(
                args.prompt, args.output, args.size, args.count,
                model, quality, args.style,
            )
        else:  # gemini
            require_gemini_key()
            model = args.model or "imagen-4.0-generate-001"
            saved = cmd_generate_image(
                args.prompt, args.output, args.size, args.count, model,
            )
        print(f"\nDone! {len(saved)} image(s) generated.")

    elif args.command in ("video", "vid", "v"):
        require_gemini_key()
        cmd_generate_video(args.prompt, args.output, args.model, args.duration, args.image)

    elif args.command in ("music", "mus", "m"):
        require_gemini_key()
        cmd_generate_music(args.prompt, args.output, args.model, args.duration)

    elif args.command in ("tts", "t"):
        require_gemini_key()
        cmd_tts(args.text, args.output, args.model, args.voice)

    elif args.command in ("analyze", "ana", "a"):
        require_gemini_key()
        cmd_analyze(args.image, args.target, args.output)


if __name__ == "__main__":
    main()
