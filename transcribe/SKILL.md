---
name: transcribe
description: Local speech-to-text for audio and video files using Whisper backends (mlx-whisper, faster-whisper, openai-whisper, whisper.cpp). Outputs txt, srt, vtt, json, or Obsidian-ready markdown. Use when the user says "transcribe this audio/video/meeting/voice memo", "speech to text", or "get the transcript of this recording".
argument-hint: <audio-or-video-file> [options]
---

# Transcribe

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/transcribe"
```

## Usage

```bash
python3 "$SKILL_DIR/transcribe.py" <audio-or-video-file> [options]
```

Accepts any audio or video file. Non-WAV input is converted to 16 kHz mono WAV via ffmpeg (`brew install ffmpeg`). Progress prints to stderr; the transcript file path prints to stdout.

## Options

| Option | Description |
|--------|-------------|
| `--backend <name>` | `auto` (default), `mlx`, `faster`, `whisper`, `whisper-cli` |
| `--model <name>` | Whisper model (default: `small`; use `large-v3-turbo` for quality) |
| `--lang <code>` | Language code, e.g. `en`, `pt` (default: auto-detect) |
| `--format <fmt>` | `txt` (default), `srt`, `vtt`, `json`, `md` |
| `-o, --output <file>` | Output file (default: input basename + format extension) |
| `--timestamps` | Include timestamps in txt/md output |

## Backends (auto-detected in this order)

| Backend | Install | Notes |
|---------|---------|-------|
| `mlx` | `pip install mlx-whisper` | Apple Silicon GPU, fastest on Mac |
| `faster` | `pip install faster-whisper` | CPU/CUDA, fast and accurate |
| `whisper` | `pip install openai-whisper` | Reference implementation |
| `whisper-cli` | `brew install whisper-cpp` | Needs a ggml model file (`--model` accepts a `.bin` path) |

If none is installed the script exits 1 with an install guide (mlx-whisper recommended on Apple Silicon).

The `md` format adds YAML frontmatter (source, date, duration, language, model) — ready to drop into an Obsidian vault.

## Examples

```bash
# Basic: transcript to meeting.txt
python3 "$SKILL_DIR/transcribe.py" meeting.m4a

# Portuguese voice memo, markdown note with timestamps
python3 "$SKILL_DIR/transcribe.py" memo.m4a --lang pt --format md --timestamps

# Video to subtitles, best quality
python3 "$SKILL_DIR/transcribe.py" lecture.mp4 --format srt --model large-v3-turbo

# Force a backend and output path
python3 "$SKILL_DIR/transcribe.py" call.mp3 --backend faster -o call-transcript.txt

# JSON with segments for downstream processing
python3 "$SKILL_DIR/transcribe.py" interview.wav --format json
```

## Pipelines

- **youtube-playlist → transcribe**: download a video with yt-dlp (`yt-dlp -f bestaudio -o talk.m4a <url>`), then transcribe it — useful when a video has no closed captions.
- **transcribe → study-this / obsidian**: transcribe with `--format md`, then file the note into the vault (e.g. under 'Things to Study') and consolidate learnings from there.
