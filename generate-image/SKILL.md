---
name: generate-image
description: Creative AI studio — generate images (Nano Banana 2), videos (Veo 3.1), music (Lyria 3), speech (Gemini TTS), or analyze images to extract prompts for all tools. Use when user asks to generate, create, make, or analyze any media.
argument-hint: generate|video|music|tts|analyze <prompt_or_file> [options]
allowed-tools: Bash, Read, Write
---

# Gemini Creative Studio

Full AI media generation suite powered by Google Gemini API.

## Script

```bash
SKILL_DIR="$HOME/.claude/skills/generate-image"
python3 "$SKILL_DIR/generate_image.py" <command> <args>
```

---

## Commands

### 1. `generate` — Image Generation (Nano Banana 2 / Imagen 4)

```bash
python3 "$SKILL_DIR/generate_image.py" generate "<prompt>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_image.png` | Output path |
| `--size, -s` | `1024x1024` | `1024x1024`, `1536x1024`, `1024x1536` |
| `--count, -n` | `1` | 1-4 images |
| `--model, -m` | `imagen-4.0-generate-001` | Falls back to `nano-banana-pro-preview` |

```bash
python3 "$SKILL_DIR/generate_image.py" generate "A cute robot in a wasteland" -o robot.png
python3 "$SKILL_DIR/generate_image.py" generate "Character sheet, anime style robot" -o sheet.png -s 1536x1024
```

### 2. `video` — Video Generation (Veo 3.1)

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
# Text to video
python3 "$SKILL_DIR/generate_image.py" video "A small robot walks through ruins and finds a green sprout" -o scene.mp4

# Image to video (animate a still image)
python3 "$SKILL_DIR/generate_image.py" video "The robot reaches down to touch the plant" --image robot.png -o animated.mp4

# Fast generation
python3 "$SKILL_DIR/generate_image.py" video "Robot building a dome" -m veo-3.1-fast-generate-preview -o dome.mp4
```

Note: Video generation is async — the script polls until complete (up to 10 min). Be patient.

### 3. `music` — Music Generation (Lyria 3)

```bash
python3 "$SKILL_DIR/generate_image.py" music "<prompt>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_music.wav` | Output path |
| `--model, -m` | `lyria-3-clip-preview` | Also: `lyria-3-pro-preview` (longer) |
| `--duration, -d` | `30` | Duration in seconds |

```bash
# Game soundtrack
python3 "$SKILL_DIR/generate_image.py" music "Hopeful orchestral piece, 90 BPM, D major, soft piano melody with strings" -o theme.wav

# Combat music
python3 "$SKILL_DIR/generate_image.py" music "Aggressive electronic, 140 BPM, taiko drums, distorted bass" -o combat.wav

# Ambient
python3 "$SKILL_DIR/generate_image.py" music "Dark ambient, wasteland wind, distant metallic groans, desolate" -o wasteland.wav
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

**Available Voices:**
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
# Narrator voice
python3 "$SKILL_DIR/generate_image.py" tts "The world ended. A small robot found a sprout." -v Charon -o narration.wav

# Character dialogue (Yuri)
python3 "$SKILL_DIR/generate_image.py" tts "I didn't trap them. I preserved them. The difference matters." -v Fenrir -o yuri.wav

# Tutorial voice
python3 "$SKILL_DIR/generate_image.py" tts "Tap and hold to move your Commander. Drag to select units." -v Kore -o tutorial.wav
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
