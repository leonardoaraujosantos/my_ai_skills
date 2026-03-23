#!/usr/bin/env python3
"""
Image Tools - Manipulate images from the command line.

Usage:
    python image_tools.py <command> <image> [options]

Commands:
    info        Show image information (size, format, mode)
    resize      Resize image
    compress    Compress image (reduce file size)
    convert     Convert to different format
    rotate      Rotate image
    flip        Flip image (horizontal/vertical)
    crop        Crop image
    thumbnail   Create thumbnail
    grayscale   Convert to grayscale
    watermark   Add text watermark

Options:
    -o, --output <file>     Output file
    -w, --width <px>        Width in pixels
    -h, --height <px>       Height in pixels
    -q, --quality <1-100>   JPEG quality (default: 85)
    -a, --angle <degrees>   Rotation angle
    -t, --text <text>       Watermark text
    --keep-aspect           Keep aspect ratio when resizing

Examples:
    python image_tools.py info photo.jpg
    python image_tools.py resize photo.jpg -w 800 -h 600 -o small.jpg
    python image_tools.py compress photo.jpg -q 70 -o compressed.jpg
    python image_tools.py convert photo.png -o photo.jpg
    python image_tools.py thumbnail photo.jpg -w 150 -h 150
    python image_tools.py watermark photo.jpg -t "Copyright 2025" -o marked.jpg

Dependencies:
    pip install Pillow
"""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ExifTags
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


def get_image_info(img_path):
    """Get detailed image information."""
    path = Path(img_path)
    file_size = path.stat().st_size

    with Image.open(img_path) as img:
        info = {
            "file": str(path.name),
            "path": str(path.absolute()),
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "file_size": file_size,
            "file_size_human": format_size(file_size),
        }

        # Get EXIF data if available
        if hasattr(img, '_getexif') and img._getexif():
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag in ['Make', 'Model', 'DateTime', 'ExposureTime', 'FNumber', 'ISOSpeedRatings']:
                        info[f"exif_{tag}"] = str(value)

    return info


def format_size(size_bytes):
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def cmd_info(img_path):
    """Show image information."""
    info = get_image_info(img_path)

    print(f"File:       {info['file']}")
    print(f"Format:     {info['format']}")
    print(f"Mode:       {info['mode']}")
    print(f"Dimensions: {info['width']} x {info['height']} px")
    print(f"File Size:  {info['file_size_human']}")

    # Print EXIF if available
    exif_keys = [k for k in info.keys() if k.startswith('exif_')]
    if exif_keys:
        print("\nEXIF Data:")
        for key in exif_keys:
            print(f"  {key.replace('exif_', '')}: {info[key]}")


def cmd_resize(img_path, width=None, height=None, keep_aspect=True, output=None, quality=85):
    """Resize image."""
    with Image.open(img_path) as img:
        orig_width, orig_height = img.size

        if keep_aspect:
            if width and not height:
                ratio = width / orig_width
                height = int(orig_height * ratio)
            elif height and not width:
                ratio = height / orig_height
                width = int(orig_width * ratio)
            elif width and height:
                # Fit within bounds while keeping aspect
                ratio = min(width / orig_width, height / orig_height)
                width = int(orig_width * ratio)
                height = int(orig_height * ratio)
        else:
            width = width or orig_width
            height = height or orig_height

        resized = img.resize((width, height), Image.Resampling.LANCZOS)

        output = output or f"resized_{Path(img_path).name}"
        save_image(resized, output, quality)
        print(f"Resized: {orig_width}x{orig_height} -> {width}x{height}")
        print(f"Saved to: {output}")


def cmd_compress(img_path, quality=70, output=None):
    """Compress image to reduce file size."""
    orig_size = Path(img_path).stat().st_size

    with Image.open(img_path) as img:
        # Convert to RGB if necessary (for JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        output = output or f"compressed_{Path(img_path).name}"
        if not output.lower().endswith(('.jpg', '.jpeg')):
            output = str(Path(output).with_suffix('.jpg'))

        img.save(output, 'JPEG', quality=quality, optimize=True)

    new_size = Path(output).stat().st_size
    reduction = (1 - new_size / orig_size) * 100

    print(f"Original:   {format_size(orig_size)}")
    print(f"Compressed: {format_size(new_size)}")
    print(f"Reduction:  {reduction:.1f}%")
    print(f"Saved to:   {output}")


def cmd_convert(img_path, output):
    """Convert image to different format."""
    with Image.open(img_path) as img:
        # Handle format-specific conversions
        out_format = Path(output).suffix.lower()

        if out_format in ['.jpg', '.jpeg'] and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        elif out_format == '.png' and img.mode == 'CMYK':
            img = img.convert('RGB')

        img.save(output)
        print(f"Converted: {Path(img_path).suffix} -> {out_format}")
        print(f"Saved to: {output}")


def cmd_rotate(img_path, angle, output=None, quality=85):
    """Rotate image."""
    with Image.open(img_path) as img:
        rotated = img.rotate(angle, expand=True, fillcolor='white')

        output = output or f"rotated_{Path(img_path).name}"
        save_image(rotated, output, quality)
        print(f"Rotated: {angle} degrees")
        print(f"Saved to: {output}")


def cmd_flip(img_path, direction='horizontal', output=None, quality=85):
    """Flip image."""
    with Image.open(img_path) as img:
        if direction == 'horizontal':
            flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:
            flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        output = output or f"flipped_{Path(img_path).name}"
        save_image(flipped, output, quality)
        print(f"Flipped: {direction}")
        print(f"Saved to: {output}")


def cmd_crop(img_path, left, top, right, bottom, output=None, quality=85):
    """Crop image."""
    with Image.open(img_path) as img:
        cropped = img.crop((left, top, right, bottom))

        output = output or f"cropped_{Path(img_path).name}"
        save_image(cropped, output, quality)
        print(f"Cropped: ({left}, {top}) to ({right}, {bottom})")
        print(f"New size: {cropped.width}x{cropped.height}")
        print(f"Saved to: {output}")


def cmd_thumbnail(img_path, width=150, height=150, output=None, quality=85):
    """Create thumbnail."""
    with Image.open(img_path) as img:
        img.thumbnail((width, height), Image.Resampling.LANCZOS)

        output = output or f"thumb_{Path(img_path).name}"
        save_image(img, output, quality)
        print(f"Thumbnail: {img.width}x{img.height}")
        print(f"Saved to: {output}")


def cmd_grayscale(img_path, output=None, quality=85):
    """Convert to grayscale."""
    with Image.open(img_path) as img:
        gray = img.convert('L')

        output = output or f"gray_{Path(img_path).name}"
        save_image(gray, output, quality)
        print(f"Converted to grayscale")
        print(f"Saved to: {output}")


def cmd_watermark(img_path, text, output=None, quality=85):
    """Add text watermark."""
    with Image.open(img_path) as img:
        # Create a copy to draw on
        watermarked = img.copy()
        draw = ImageDraw.Draw(watermarked)

        # Try to use a nice font, fall back to default
        font_size = max(20, img.width // 20)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

        # Get text size
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Position in bottom right with padding
        x = img.width - text_width - 20
        y = img.height - text_height - 20

        # Draw shadow
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 128))
        # Draw text
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 200))

        output = output or f"watermarked_{Path(img_path).name}"
        save_image(watermarked, output, quality)
        print(f"Added watermark: '{text}'")
        print(f"Saved to: {output}")


def save_image(img, output, quality=85):
    """Save image with appropriate format settings."""
    out_format = Path(output).suffix.lower()

    if out_format in ['.jpg', '.jpeg']:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.save(output, 'JPEG', quality=quality, optimize=True)
    elif out_format == '.png':
        img.save(output, 'PNG', optimize=True)
    elif out_format == '.webp':
        img.save(output, 'WEBP', quality=quality)
    else:
        img.save(output)


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        return

    cmd = sys.argv[1]

    if len(sys.argv) < 3:
        print("Error: Please provide an image file")
        return

    img_path = sys.argv[2]

    if not Path(img_path).exists():
        print(f"File not found: {img_path}")
        return

    # Parse arguments
    args = sys.argv[3:]
    width = None
    height = None
    quality = 85
    angle = 0
    text = None
    output = None
    keep_aspect = True
    direction = 'horizontal'
    crop_coords = None

    i = 0
    while i < len(args):
        if args[i] in ['-w', '--width'] and i + 1 < len(args):
            width = int(args[i + 1])
            i += 2
        elif args[i] in ['-h', '--height'] and i + 1 < len(args):
            height = int(args[i + 1])
            i += 2
        elif args[i] in ['-q', '--quality'] and i + 1 < len(args):
            quality = int(args[i + 1])
            i += 2
        elif args[i] in ['-a', '--angle'] and i + 1 < len(args):
            angle = float(args[i + 1])
            i += 2
        elif args[i] in ['-t', '--text'] and i + 1 < len(args):
            text = args[i + 1]
            i += 2
        elif args[i] in ['-o', '--output'] and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif args[i] == '--keep-aspect':
            keep_aspect = True
            i += 1
        elif args[i] == '--no-aspect':
            keep_aspect = False
            i += 1
        elif args[i] in ['--horizontal', '--h']:
            direction = 'horizontal'
            i += 1
        elif args[i] in ['--vertical', '--v']:
            direction = 'vertical'
            i += 1
        elif args[i] == '--crop' and i + 4 < len(args):
            crop_coords = (int(args[i+1]), int(args[i+2]), int(args[i+3]), int(args[i+4]))
            i += 5
        else:
            i += 1

    # Execute command
    if cmd == 'info':
        cmd_info(img_path)
    elif cmd == 'resize':
        cmd_resize(img_path, width, height, keep_aspect, output, quality)
    elif cmd == 'compress':
        cmd_compress(img_path, quality, output)
    elif cmd == 'convert':
        if not output:
            print("Error: -o/--output required for convert")
            return
        cmd_convert(img_path, output)
    elif cmd == 'rotate':
        cmd_rotate(img_path, angle, output, quality)
    elif cmd == 'flip':
        cmd_flip(img_path, direction, output, quality)
    elif cmd == 'crop':
        if not crop_coords:
            print("Error: --crop left top right bottom required")
            return
        cmd_crop(img_path, *crop_coords, output, quality)
    elif cmd == 'thumbnail':
        cmd_thumbnail(img_path, width or 150, height or 150, output, quality)
    elif cmd == 'grayscale':
        cmd_grayscale(img_path, output, quality)
    elif cmd == 'watermark':
        if not text:
            print("Error: -t/--text required for watermark")
            return
        cmd_watermark(img_path, text, output, quality)
    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
