---
name: video-tools
description: Manipulate videos with ffmpeg - inspect metadata, trim, compress, convert formats, extract audio, make GIFs, thumbnails, resize, mute, change speed, merge clips. Use when the user wants to trim/compress/convert video, make a GIF from a video, extract audio from video, merge videos, or grab a video thumbnail. Complements the generate-image skill (post-process Veo video output) and the elevenlabs skill (extracted audio can be cleaned or voice-converted).
argument-hint: <command> <file> [options]
---

# Video Tools

Requires `ffmpeg`/`ffprobe` (macOS: `brew install ffmpeg`). The script exits with a clear message if they are missing.

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/video-tools"
```

## Commands

```bash
python3 "$SKILL_DIR/video_tools.py" <command> <file> [options]
```

| Command | Description |
|---------|-------------|
| `info` | Human summary: container, duration, size, bitrate, video/audio streams |
| `trim` | Cut a section (stream copy by default; `--reencode` for frame-accurate) |
| `compress` | Re-encode with libx264 + aac (`--crf`, `--preset`, optional `--width`) |
| `convert` | Convert by output extension (mp4, webm, mov, ...) |
| `extract-audio` | Extract audio track to mp3 / m4a / wav (codec picked by extension) |
| `gif` | High-quality GIF via two-pass palettegen/paletteuse |
| `thumbnail` | Extract a single frame as an image |
| `resize` | Resize (`--width` only preserves aspect ratio via `-2`) |
| `mute` | Strip audio (`-an`, video stream copied) |
| `speed` | Change speed (setpts + atempo, chained outside 0.5-2.0) |
| `merge` | Concatenate clips (stream copy; inputs must share codecs/resolution) |

## Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output file (required by all except `info`) |
| `-s, --start <time>` | Start time (`75`, `1:15`, or `00:01:15.5`) |
| `-e, --end <time>` | End time |
| `-d, --duration <time>` | Duration instead of end time (trim) |
| `--reencode` | Frame-accurate trim (slower) |
| `--crf <n>` | Compression quality, lower = better (default 28) |
| `--preset <name>` | x264 preset (default medium) |
| `--width <n>` / `--height <n>` | Target dimensions |
| `--fps <n>` | GIF frame rate (default 12) |
| `-t, --time <time>` | Thumbnail timestamp (default 0) |
| `--factor <f>` | Speed multiplier, e.g. 2.0 or 0.5 |
| `-y, --overwrite` | Allow overwriting an existing output file |
| `--verbose` | Print the underlying ffmpeg command |

Outputs are never overwritten unless `-y/--overwrite` is passed.

## Examples

```bash
# Inspect a file
python3 "$SKILL_DIR/video_tools.py" info clip.mp4

# Trim 10s starting at 0:30 (fast, stream copy)
python3 "$SKILL_DIR/video_tools.py" trim clip.mp4 -s 0:30 -d 10 -o cut.mp4
python3 "$SKILL_DIR/video_tools.py" trim clip.mp4 -s 0:30 -e 0:40 --reencode -o cut.mp4

# Compress / convert
python3 "$SKILL_DIR/video_tools.py" compress clip.mp4 --crf 28 --width 1280 -o small.mp4
python3 "$SKILL_DIR/video_tools.py" convert clip.mov -o clip.mp4

# Extract audio (e.g. to feed the elevenlabs skill)
python3 "$SKILL_DIR/video_tools.py" extract-audio clip.mp4 -o audio.mp3

# GIF from a range (e.g. from a Veo clip made by generate-image)
python3 "$SKILL_DIR/video_tools.py" gif clip.mp4 --fps 12 --width 480 -s 1 -e 4 -o demo.gif

# Thumbnail at 5s
python3 "$SKILL_DIR/video_tools.py" thumbnail clip.mp4 -t 5 -o thumb.jpg

# Resize, mute, speed up
python3 "$SKILL_DIR/video_tools.py" resize clip.mp4 --width 720 -o 720p.mp4
python3 "$SKILL_DIR/video_tools.py" mute clip.mp4 -o silent.mp4
python3 "$SKILL_DIR/video_tools.py" speed clip.mp4 --factor 2.0 -o fast.mp4

# Merge clips (same codecs/resolution required)
python3 "$SKILL_DIR/video_tools.py" merge a.mp4 b.mp4 c.mp4 -o full.mp4
```
