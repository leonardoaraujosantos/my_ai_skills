---
name: image-tools
description: Manipulate images - resize, compress, convert, rotate, crop, watermark. Use when working with image files.
argument-hint: <command> <image> [options]
---

# Image Tools

## Dependencies

```bash
pip install Pillow
```

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/image-tools"
```

## Commands

```bash
python3 "$SKILL_DIR/image_tools.py" <command> <image> [options]
```

| Command | Description |
|---------|-------------|
| `info` | Show image info (size, format, EXIF) |
| `resize` | Resize image |
| `compress` | Compress/reduce file size |
| `convert` | Convert to different format |
| `rotate` | Rotate by angle |
| `flip` | Flip horizontal/vertical |
| `crop` | Crop region |
| `thumbnail` | Create thumbnail |
| `grayscale` | Convert to grayscale |
| `watermark` | Add text watermark |

## Options

| Option | Description |
|--------|-------------|
| `-w, --width <px>` | Width in pixels |
| `-h, --height <px>` | Height in pixels |
| `-q, --quality <1-100>` | JPEG quality (default: 85) |
| `-a, --angle <degrees>` | Rotation angle |
| `-t, --text <text>` | Watermark text |
| `-o, --output <file>` | Output file |
| `--keep-aspect` | Keep aspect ratio (default) |
| `--horizontal/--vertical` | Flip direction |

## Examples

```bash
# View info
python3 "$SKILL_DIR/image_tools.py" info photo.jpg

# Resize (keep aspect ratio)
python3 "$SKILL_DIR/image_tools.py" resize photo.jpg -w 800 -o small.jpg

# Resize exact dimensions
python3 "$SKILL_DIR/image_tools.py" resize photo.jpg -w 800 -h 600 --no-aspect -o exact.jpg

# Compress JPEG
python3 "$SKILL_DIR/image_tools.py" compress photo.jpg -q 70 -o compressed.jpg

# Convert PNG to JPEG
python3 "$SKILL_DIR/image_tools.py" convert image.png -o image.jpg

# Create thumbnail
python3 "$SKILL_DIR/image_tools.py" thumbnail photo.jpg -w 150 -h 150

# Rotate 90 degrees
python3 "$SKILL_DIR/image_tools.py" rotate photo.jpg -a 90 -o rotated.jpg

# Add watermark
python3 "$SKILL_DIR/image_tools.py" watermark photo.jpg -t "Copyright 2024" -o marked.jpg

# Grayscale
python3 "$SKILL_DIR/image_tools.py" grayscale photo.jpg -o bw.jpg

# Crop (left, top, right, bottom)
python3 "$SKILL_DIR/image_tools.py" crop photo.jpg --crop 100 100 500 400 -o cropped.jpg
```
