---
name: elevenlabs
description: Generate speech, sound effects, convert voices, and isolate audio using ElevenLabs API. Use when the user wants to create voiceovers, narration, game SFX, voice conversion, or clean up audio files.
user_invocable: false
---

# ElevenLabs Audio Studio

Full audio generation suite powered by ElevenLabs API.

## Script

```bash
SKILL_DIR="$HOME/.claude/skills/elevenlabs"
python3 "$SKILL_DIR/elevenlabs_cli.py" <command> <args>
```

---

## Commands

### 1. `tts` — Text-to-Speech

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" tts "<text>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_speech.mp3` | Output path |
| `--voice, -v` | `JBFqnCBsd6RMkjVDRZzb` | Voice ID (George) |
| `--model, -m` | `eleven_multilingual_v2` | Model ID |
| `--format, -f` | `mp3_44100_128` | `mp3_44100_128`, `mp3_22050_32`, `pcm_16000`, `pcm_24000`, `opus_48000_32` |
| `--language` | auto | ISO 639-1 code (`en`, `pt`, `es`, `fr`, `de`, `ja`, etc.) |
| `--stability` | voice default | 0.0-1.0 (lower = more expressive) |
| `--similarity` | voice default | 0.0-1.0 (higher = closer to original voice) |
| `--style` | voice default | 0.0-1.0 (style exaggeration) |
| `--speed` | 1.0 | 0.5-2.0 (speaking speed) |

```bash
# Basic narration
python3 "$SKILL_DIR/elevenlabs_cli.py" tts "The world ended. A small robot found a sprout." -o narration.mp3

# Portuguese with specific voice
python3 "$SKILL_DIR/elevenlabs_cli.py" tts "O mundo acabou. Um pequeno robô encontrou um broto." -o narration_pt.mp3 --language pt

# Slow dramatic reading
python3 "$SKILL_DIR/elevenlabs_cli.py" tts "In the silence of the wasteland..." -o dramatic.mp3 --speed 0.7 --stability 0.3

# From stdin (pipe text)
echo "Hello world" | python3 "$SKILL_DIR/elevenlabs_cli.py" tts - -o hello.mp3
```

### 2. `sfx` — Sound Effects Generation

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "<description>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_sfx.mp3` | Output path |
| `--duration, -d` | auto | Duration in seconds (0.5-30) |
| `--format, -f` | `mp3_44100_128` | Output format |
| `--influence` | 0.3 | Prompt influence (0.0-1.0) |
| `--loop` | false | Generate loopable sound |

```bash
# Game sound effects
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Laser turret firing rapid energy bolts" -o laser.mp3 -d 3
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Robot footsteps on metal floor, mechanical and chunky" -o footsteps.mp3 -d 5
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Insectoid screech, alien bug hissing aggressively" -o bug_screech.mp3 -d 2
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Energy dome shield activating with electric hum" -o dome_shield.mp3 -d 4

# Ambient loops
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Post-apocalyptic wasteland wind, distant metallic groans" -o wasteland_ambient.mp3 --loop -d 10
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Gentle rain on glass greenhouse with plant growing sounds" -o greenhouse_ambient.mp3 --loop -d 10

# UI sounds
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Futuristic UI button click, holographic interface" -o ui_click.mp3 -d 0.5
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Achievement unlocked chime, positive notification" -o achievement.mp3 -d 1.5
```

### 3. `music` — Music Composition

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" music "<prompt>" [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./generated_music.mp3` | Output path |
| `--duration, -d` | `30` | Duration in seconds (3-600) |
| `--format, -f` | `mp3_44100_128` | Output format |
| `--instrumental` | false | Force instrumental (no vocals) |
| `--plan` | none | Path to JSON composition plan (overrides prompt) |
| `--seed` | random | Seed for reproducibility |

```bash
# Simple prompt — instrumental game music
python3 "$SKILL_DIR/elevenlabs_cli.py" music "Hopeful orchestral piece with electronic elements, piano melody in D major, soft strings, gentle percussion, cinematic and emotional" -o theme.mp3 -d 60 --instrumental

# Combat music
python3 "$SKILL_DIR/elevenlabs_cli.py" music "Aggressive electronic orchestral hybrid, 140 BPM, taiko drums, distorted bass drops, staccato strings, intense battle music" -o combat.mp3 -d 45 --instrumental

# Ambient wasteland
python3 "$SKILL_DIR/elevenlabs_cli.py" music "Dark ambient soundscape, low analog synth drone, distant metallic creaks, desolate wind, post-apocalyptic, minimal and sparse" -o wasteland.mp3 -d 60 --instrumental

# With composition plan (advanced)
python3 "$SKILL_DIR/elevenlabs_cli.py" music --plan song_plan.json -o composed.mp3
```

#### Composition Plan JSON Example

```json
{
  "positive_global_styles": ["orchestral", "cinematic", "hopeful"],
  "negative_global_styles": ["heavy metal", "aggressive"],
  "sections": [
    {
      "section_name": "intro",
      "positive_local_styles": ["minimal", "piano", "ambient"],
      "negative_local_styles": ["loud", "drums"],
      "duration_ms": 15000,
      "lines": []
    },
    {
      "section_name": "build",
      "positive_local_styles": ["strings", "building", "emotional"],
      "negative_local_styles": ["harsh"],
      "duration_ms": 20000,
      "lines": []
    },
    {
      "section_name": "climax",
      "positive_local_styles": ["full orchestra", "triumphant", "brass"],
      "negative_local_styles": ["quiet"],
      "duration_ms": 25000,
      "lines": []
    }
  ]
}
```

### 4. `sts` — Speech-to-Speech (Voice Conversion)

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" sts <input_audio> [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./converted_speech.mp3` | Output path |
| `--voice, -v` | `JBFqnCBsd6RMkjVDRZzb` | Target voice ID |
| `--model, -m` | `eleven_english_sts_v2` | `eleven_english_sts_v2` or `eleven_multilingual_sts_v2` |
| `--format, -f` | `mp3_44100_128` | Output format |
| `--remove-noise` | false | Remove background noise from input |

```bash
# Convert voice to a different character
python3 "$SKILL_DIR/elevenlabs_cli.py" sts recording.mp3 -v JBFqnCBsd6RMkjVDRZzb -o converted.mp3

# Multilingual voice conversion with noise removal
python3 "$SKILL_DIR/elevenlabs_cli.py" sts noisy_recording.mp3 -m eleven_multilingual_sts_v2 --remove-noise -o clean_converted.mp3
```

### 4. `isolate` — Audio Isolation (Background Noise Removal)

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" isolate <input_audio> [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--output, -o` | `./isolated_audio.mp3` | Output path |

```bash
# Clean up a noisy recording
python3 "$SKILL_DIR/elevenlabs_cli.py" isolate noisy_audio.mp3 -o clean_audio.mp3
```

### 5. `voices` — List Available Voices

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" voices [options]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--search, -s` | none | Search by name/description |
| `--category, -c` | all | `premade`, `cloned`, `generated`, `professional` |
| `--limit, -l` | 25 | Max results |
| `--json` | false | Output full JSON details |

```bash
# List all voices
python3 "$SKILL_DIR/elevenlabs_cli.py" voices

# Search for specific voice
python3 "$SKILL_DIR/elevenlabs_cli.py" voices -s "deep male"

# Only premade voices
python3 "$SKILL_DIR/elevenlabs_cli.py" voices -c premade -l 50
```

### 6. `models` — List Available Models

```bash
python3 "$SKILL_DIR/elevenlabs_cli.py" models
```

---

## Common Voice IDs

| Voice ID | Name | Character |
|----------|------|-----------|
| `JBFqnCBsd6RMkjVDRZzb` | George | Deep, authoritative male |
| `21m00Tcm4TlvDq8ikWAM` | Rachel | Calm, clear female |
| `EXAVITQu4vr4xnSDxMaL` | Bella | Warm, nurturing female |
| `ErXwobaYiN019PkySvjV` | Antoni | Confident male |
| `MF3mGyEYCl7XYWbV9V6O` | Elli | Young, energetic female |
| `TxGEqnHWrfWFTfGW9XjX` | Josh | Young male |
| `VR6AewLTigWG4xSOukaG` | Arnold | Deep, strong male |
| `pNInz6obpgDQGcFmaJgB` | Adam | Versatile male |
| `yoZ06aMxZJJ28mfd3POQ` | Sam | Conversational male |

Use `voices` command to list all available voices with IDs.

---

## Output Formats

| Format | Quality | Use Case |
|--------|---------|----------|
| `mp3_44100_128` | High quality MP3 | Default, general use |
| `mp3_22050_32` | Low quality MP3 | Small file size, previews |
| `pcm_16000` | 16kHz PCM | Real-time streaming |
| `pcm_24000` | 24kHz PCM | Higher quality PCM |
| `pcm_44100` | 44.1kHz PCM | Studio quality raw audio |
| `opus_48000_32` | Opus codec | Web streaming |

---

## Models

| Model ID | Use Case |
|----------|----------|
| `eleven_multilingual_v2` | TTS (default, 29 languages) |
| `eleven_turbo_v2_5` | TTS (faster, lower latency) |
| `eleven_english_sts_v2` | Speech-to-Speech (English) |
| `eleven_multilingual_sts_v2` | Speech-to-Speech (multilingual) |

---

## Full Pipeline Example

```bash
SKILL_DIR="$HOME/.claude/skills/elevenlabs"

# 1. Generate narration
python3 "$SKILL_DIR/elevenlabs_cli.py" tts "The world ended. A small robot found hope." -o narration.mp3 --speed 0.8

# 2. Generate sound effects
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Post-apocalyptic wind howling through ruins" -o wind.mp3 -d 10 --loop
python3 "$SKILL_DIR/elevenlabs_cli.py" sfx "Small robot beeping and whirring cheerfully" -o robot_beep.mp3 -d 3

# 3. Convert a recording to a character voice
python3 "$SKILL_DIR/elevenlabs_cli.py" sts my_recording.mp3 -v JBFqnCBsd6RMkjVDRZzb -o character_voice.mp3

# 4. Clean up noisy audio
python3 "$SKILL_DIR/elevenlabs_cli.py" isolate noisy_field_recording.mp3 -o clean_audio.mp3
```
