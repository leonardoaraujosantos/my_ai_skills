---
name: generate-image
description: Creative AI studio — generate images (OpenAI gpt-image-1 / dall-e-3 by default; or Google Imagen 4 / Nano Banana 2), videos (Veo 3.1), music (Lyria 3), speech (Gemini TTS), or analyze images to extract prompts. Use when user asks to generate, create, make, or analyze any media.
argument-hint: generate|video|music|tts|analyze <prompt_or_file> [options]
allowed-tools: Bash, Read, Write
---

# Creative AI Studio (OpenAI + Gemini)

Full AI media generation suite.

- **Image generation**: OpenAI (default) — `gpt-image-1`, `dall-e-3`, `dall-e-2` —
  or Google — Imagen 4 / Nano Banana 2.
- **Video / Music / TTS / Analyze**: Google Gemini (Veo 3.1, Lyria 3, Gemini TTS).

## API keys

Set these environment variables (e.g. in `~/.claude/settings.json` under `"env"`):

| Variable | Required for |
|---|---|
| `OPENAI_API_KEY` | `generate` with `--provider openai` (default) |
| `GEMINI_API_KEY` | `generate --provider gemini`, `video`, `music`, `tts`, `analyze` |

⚠️ **Never** hard-code keys in this script. They are read from `os.environ` only.

## Script

```bash
SKILL_DIR="$HOME/.claude/skills/generate-image"
python3 "$SKILL_DIR/generate_image.py" <command> <args>
```

---

## Commands

### 1. `generate` — Image Generation

```bash
python3 "$SKILL_DIR/generate_image.py" generate "<prompt>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_image.png` | Output path |
| `--size, -s` | `1024x1024` | See per-model lists below |
| `--count, -n` | `1` | 1–4 (DALL-E 3 forces n=1) |
| `--provider, -p` | `openai` | `openai` or `gemini` |
| `--model, -m` | depends on provider | OpenAI: `gpt-image-1` (default), `dall-e-3`, `dall-e-2`. Gemini: `imagen-4.0-generate-001` (default with Nano-Banana 2 fallback) |
| `--quality` | `medium` (gpt-image-1) / `standard` (dall-e-3) | OpenAI only |
| `--style` | `vivid` | DALL-E 3 only (`vivid` or `natural`) |

#### OpenAI sizes per model

| Model | Sizes | Quality | Style | Best for |
|---|---|---|---|---|
| `gpt-image-1` | 1024×1024, 1024×1536, 1536×1024 | `low` / `medium` / `high` | n/a | Newest; best at text inside images |
| `dall-e-3` | 1024×1024, 1024×1792, 1792×1024 | `standard` / `hd` | `vivid` / `natural` | Photorealistic |
| `dall-e-2` | 256×256, 512×512, 1024×1024 | n/a | n/a | Cheap legacy |

#### Examples

```bash
# OpenAI (default) — gpt-image-1 at medium quality
python3 "$SKILL_DIR/generate_image.py" generate "A cute robot in a wasteland" -o robot.png

# DALL-E 3 photorealistic, 16:9 HD
python3 "$SKILL_DIR/generate_image.py" generate \
    "Aerial photo of Bridgetown at sunset with telecom towers" \
    -m dall-e-3 -s 1792x1024 --quality hd --style natural -o cover.png

# gpt-image-1 high quality with text in image
python3 "$SKILL_DIR/generate_image.py" generate \
    "Sign that says 'Police Station - 21m mast' in clean technical style" \
    -m gpt-image-1 --quality high -o sign.png

# Switch to Gemini
python3 "$SKILL_DIR/generate_image.py" generate \
    "Anime-style robot finding a sprout, vibrant colors" \
    --provider gemini -m imagen-4.0-generate-001 -o robot_anime.png

# Generate 4 variations (only OpenAI gpt-image-1 / dall-e-2 / Gemini support n>1)
python3 "$SKILL_DIR/generate_image.py" generate \
    "Antenna sector pattern diagram, isometric 3D" -n 4 -o variants.png
```

### 2. `video` — Video Generation (Veo 3.1, Gemini)

```bash
python3 "$SKILL_DIR/generate_image.py" video "<prompt>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_video.mp4` | Output path |
| `--model, -m` | `veo-3.1-generate-preview` | Also: `veo-3.1-fast-generate-preview`, `veo-3.0-generate-001` |
| `--duration, -d` | `8s` | `5s`, `8s`, `10s` |
| `--image, -i` | None | Reference image for image-to-video |

```bash
# Text → video
python3 "$SKILL_DIR/generate_image.py" video \
    "A small robot walks through ruins and finds a green sprout" -o scene.mp4

# Image → video (animate a still image)
python3 "$SKILL_DIR/generate_image.py" video \
    "The robot reaches down to touch the plant" --image robot.png -o animated.mp4

# Fast generation
python3 "$SKILL_DIR/generate_image.py" video \
    "Robot building a dome" -m veo-3.1-fast-generate-preview -o dome.mp4
```

Note: video generation is async — the script polls until complete (up to 10 min).

### 3. `music` — Music Generation (Lyria 3, Gemini)

```bash
python3 "$SKILL_DIR/generate_image.py" music "<prompt>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_music.wav` | Output path |
| `--model, -m` | `lyria-3-clip-preview` | Also: `lyria-3-pro-preview` (longer) |
| `--duration, -d` | `30` | Duration in seconds |

```bash
python3 "$SKILL_DIR/generate_image.py" music \
    "Hopeful orchestral piece, 90 BPM, D major, soft piano with strings" -o theme.wav
python3 "$SKILL_DIR/generate_image.py" music \
    "Aggressive electronic, 140 BPM, taiko drums, distorted bass" -o combat.wav
python3 "$SKILL_DIR/generate_image.py" music \
    "Dark ambient, wasteland wind, distant metallic groans" -o wasteland.wav
```

### 4. `tts` — Text-to-Speech (Gemini TTS)

```bash
python3 "$SKILL_DIR/generate_image.py" tts "<text>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_speech.wav` | Output path |
| `--model, -m` | `gemini-2.5-flash-preview-tts` | Also: `gemini-2.5-pro-preview-tts` |
| `--voice, -v` | `Kore` | See voice list below |

**Available voices**

| Voice | Character |
|-------|-----------|
| `Zephyr` | Bright, energetic |
| `Puck` | Upbeat, playful |
| `Charon` | Deep, authoritative |
| `Kore` | Calm, clear (default) |
| `Fenrir` | Bold, strong |
| `Leda` | Warm, nurturing |
| `Orus` | Confident, professional |
| `Aoede` | Musical, expressive |
| `Io` | Youthful, curious |
| `Elara` | Gentle, soothing |

```bash
python3 "$SKILL_DIR/generate_image.py" tts \
    "The world ended. A small robot found a sprout." -v Charon -o narration.wav
python3 "$SKILL_DIR/generate_image.py" tts \
    "Tap and hold to move your Commander. Drag to select units." -v Kore -o tutorial.wav
```

### 5. `analyze` — Image Analysis → Prompts for All Tools

```bash
python3 "$SKILL_DIR/generate_image.py" analyze <image_path> [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--target, -t` | `all` | `all`, `image`, `video`, `music`, `sfx`, `voice` |
| `--output, -o` | stdout | Save to markdown file |

```bash
# Full analysis — prompts for every tool
python3 "$SKILL_DIR/generate_image.py" analyze concept_art.png

# Just video prompt (for Veo 3.1)
python3 "$SKILL_DIR/generate_image.py" analyze scene.png -t video

# Save to file
python3 "$SKILL_DIR/generate_image.py" analyze character.png -t all -o prompts.md
```

---

## Full Creative Pipeline Example

```bash
SKILL_DIR="$HOME/.claude/skills/generate-image"

# 1. Generate concept art with OpenAI gpt-image-1
python3 "$SKILL_DIR/generate_image.py" generate \
    "Cute robot finding a sprout in wasteland, anime style" \
    --quality high -o concept.png

# 2. Analyze it to extract prompts for every other tool (Gemini)
python3 "$SKILL_DIR/generate_image.py" analyze concept.png -t all -o prompts.md

# 3. Animate the image (Gemini Veo 3.1)
python3 "$SKILL_DIR/generate_image.py" video \
    "Robot reaches down to touch the plant, camera slowly orbits" \
    --image concept.png -o scene.mp4

# 4. Matching music (Gemini Lyria 3)
python3 "$SKILL_DIR/generate_image.py" music \
    "Gentle piano, hopeful, 80 BPM, D major" -o soundtrack.wav

# 5. Narration (Gemini TTS)
python3 "$SKILL_DIR/generate_image.py" tts \
    "In the silence of the wasteland, a small robot found hope." \
    -v Elara -o narration.wav
```
