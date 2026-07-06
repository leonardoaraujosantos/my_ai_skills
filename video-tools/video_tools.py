#!/usr/bin/env python3
"""video-tools: ffmpeg/ffprobe wrapper for common video operations.

Requires ffmpeg and ffprobe on PATH (macOS: brew install ffmpeg).
Python 3 stdlib only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

AUDIO_CODECS = {
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    ".m4a": ["-c:a", "aac", "-b:a", "192k"],
    ".wav": ["-c:a", "pcm_s16le"],
}


def die(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def require_tool(name):
    path = shutil.which(name)
    if not path:
        die(f"'{name}' not found on PATH. Install it with: brew install ffmpeg")
    return path


def check_input(path):
    if not os.path.isfile(path):
        die(f"input file not found: {path}")


def check_output(path, overwrite):
    if os.path.exists(path) and not overwrite:
        die(f"output file already exists: {path} (use --overwrite/-y to replace it)")
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        die(f"output directory does not exist: {parent}")


def run_ffmpeg(args, verbose, ffmpeg_args):
    """Run ffmpeg with the given arguments (after the binary name)."""
    cmd = [require_tool("ffmpeg"), "-hide_banner", "-y"] + ffmpeg_args
    if verbose:
        print("+ " + " ".join(cmd), file=sys.stderr)
        result = subprocess.run(cmd)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        die(f"ffmpeg failed with exit code {result.returncode}")


def parse_timestamp(value):
    """Accept seconds ('75', '75.5') or clock time ('1:15', '00:01:15.5'). Return seconds."""
    parts = value.split(":")
    if len(parts) > 3:
        die(f"invalid timestamp: {value}")
    try:
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
        return seconds
    except ValueError:
        die(f"invalid timestamp: {value}")


def probe(path):
    check_input(path)
    ffprobe = require_tool("ffprobe")
    cmd = [ffprobe, "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        die(f"ffprobe failed to read: {path}")
    return json.loads(result.stdout)


def find_stream(data, kind):
    for stream in data.get("streams", []):
        if stream.get("codec_type") == kind:
            return stream
    return None


def format_duration(seconds):
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"


def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024


def parse_fps(rate):
    try:
        num, _, den = rate.partition("/")
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def cmd_info(args):
    data = probe(args.file)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))
    print(f"File:       {args.file}")
    print(f"Container:  {fmt.get('format_long_name', fmt.get('format_name', 'unknown'))}")
    print(f"Duration:   {format_duration(duration)} ({duration:.2f}s)")
    print(f"Size:       {format_size(int(fmt.get('size', 0)))}")
    print(f"Bitrate:    {int(fmt.get('bit_rate', 0)) // 1000} kb/s")

    video = find_stream(data, "video")
    if video:
        fps = parse_fps(video.get("avg_frame_rate", "0/1"))
        print(f"Video:      {video.get('codec_name', '?')} "
              f"{video.get('width', '?')}x{video.get('height', '?')} @ {fps:.2f} fps")
    else:
        print("Video:      none")

    audio = find_stream(data, "audio")
    if audio:
        print(f"Audio:      {audio.get('codec_name', '?')}, "
              f"{audio.get('channels', '?')} channel(s), "
              f"{audio.get('sample_rate', '?')} Hz")
    else:
        print("Audio:      none")


def cmd_trim(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    if args.end and args.duration:
        die("use either -e/--end or -d/--duration, not both")
    if not args.end and not args.duration:
        die("trim requires -e/--end or -d/--duration")

    start = parse_timestamp(args.start)
    if args.duration:
        duration = parse_timestamp(args.duration)
    else:
        duration = parse_timestamp(args.end) - start
        if duration <= 0:
            die("end time must be after start time")

    ffargs = ["-ss", f"{start:.3f}", "-i", args.file, "-t", f"{duration:.3f}"]
    if args.reencode:
        ffargs += ["-c:v", "libx264", "-c:a", "aac"]
    else:
        ffargs += ["-c", "copy"]
    ffargs.append(args.output)
    run_ffmpeg(args, args.verbose, ffargs)
    print(f"Trimmed -> {args.output}")


def cmd_compress(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    ffargs = ["-i", args.file, "-c:v", "libx264",
              "-crf", str(args.crf), "-preset", args.preset]
    if args.width:
        ffargs += ["-vf", f"scale={args.width}:-2"]
    ffargs += ["-c:a", "aac", "-b:a", "128k", args.output]
    run_ffmpeg(args, args.verbose, ffargs)
    print(f"Compressed -> {args.output}")


def cmd_convert(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    if not os.path.splitext(args.output)[1]:
        die("output file must have an extension (e.g. out.mp4, out.webm)")
    run_ffmpeg(args, args.verbose, ["-i", args.file, args.output])
    print(f"Converted -> {args.output}")


def cmd_extract_audio(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    ext = os.path.splitext(args.output)[1].lower()
    codec = AUDIO_CODECS.get(ext)
    if not codec:
        die(f"unsupported audio extension '{ext}' (supported: {', '.join(AUDIO_CODECS)})")
    run_ffmpeg(args, args.verbose, ["-i", args.file, "-vn"] + codec + [args.output])
    print(f"Audio extracted -> {args.output}")


def trim_input_args(args):
    """Optional -ss/-t input arguments shared by gif."""
    ffargs = []
    if args.start:
        ffargs += ["-ss", f"{parse_timestamp(args.start):.3f}"]
    if args.end:
        end = parse_timestamp(args.end)
        start = parse_timestamp(args.start) if args.start else 0.0
        if end <= start:
            die("end time must be after start time")
        ffargs += ["-t", f"{end - start:.3f}"]
    return ffargs


def cmd_gif(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    base = f"fps={args.fps},scale={args.width}:-1:flags=lanczos"
    pre = trim_input_args(args)
    with tempfile.TemporaryDirectory() as tmp:
        palette = os.path.join(tmp, "palette.png")
        run_ffmpeg(args, args.verbose,
                   pre + ["-i", args.file, "-vf", f"{base},palettegen", palette])
        run_ffmpeg(args, args.verbose,
                   pre + ["-i", args.file, "-i", palette,
                          "-lavfi", f"{base}[x];[x][1:v]paletteuse", args.output])
    print(f"GIF created -> {args.output}")


def cmd_thumbnail(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    ffargs = ["-ss", f"{parse_timestamp(args.time):.3f}", "-i", args.file,
              "-frames:v", "1", "-q:v", "2", args.output]
    run_ffmpeg(args, args.verbose, ffargs)
    print(f"Thumbnail -> {args.output}")


def cmd_resize(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    height = args.height if args.height else -2
    ffargs = ["-i", args.file, "-vf", f"scale={args.width}:{height}",
              "-c:v", "libx264", "-c:a", "copy", args.output]
    run_ffmpeg(args, args.verbose, ffargs)
    print(f"Resized -> {args.output}")


def cmd_mute(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    run_ffmpeg(args, args.verbose,
               ["-i", args.file, "-an", "-c:v", "copy", args.output])
    print(f"Audio removed -> {args.output}")


def atempo_chain(factor):
    """atempo only accepts 0.5-2.0; chain filters for factors outside that range."""
    stages = []
    while factor > 2.0:
        stages.append("atempo=2.0")
        factor /= 2.0
    while factor < 0.5:
        stages.append("atempo=0.5")
        factor /= 0.5
    stages.append(f"atempo={factor:.6g}")
    return ",".join(stages)


def cmd_speed(args):
    check_input(args.file)
    check_output(args.output, args.overwrite)
    if args.factor <= 0:
        die("--factor must be greater than 0")
    has_audio = find_stream(probe(args.file), "audio") is not None
    ffargs = ["-i", args.file, "-vf", f"setpts=PTS/{args.factor:.6g}"]
    if has_audio:
        ffargs += ["-af", atempo_chain(args.factor)]
    else:
        ffargs += ["-an"]
    ffargs.append(args.output)
    run_ffmpeg(args, args.verbose, ffargs)
    print(f"Speed x{args.factor:g} -> {args.output}")


def cmd_merge(args):
    if len(args.files) < 2:
        die("merge requires at least two input files")
    for path in args.files:
        check_input(path)
    check_output(args.output, args.overwrite)
    print("Note: merge uses stream copy; all inputs must share the same "
          "codecs, resolution, and frame rate.", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        list_file = os.path.join(tmp, "concat.txt")
        with open(list_file, "w") as fh:
            for path in args.files:
                escaped = os.path.abspath(path).replace("'", "'\\''")
                fh.write(f"file '{escaped}'\n")
        run_ffmpeg(args, args.verbose,
                   ["-f", "concat", "-safe", "0", "-i", list_file,
                    "-c", "copy", args.output])
    print(f"Merged {len(args.files)} files -> {args.output}")


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--verbose", action="store_true",
                        help="print the underlying ffmpeg command")
    common.add_argument("-y", "--overwrite", action="store_true",
                        help="overwrite the output file if it exists")

    parser = argparse.ArgumentParser(
        prog="video_tools.py",
        description="ffmpeg/ffprobe wrapper for common video operations")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", parents=[common], help="show video file summary")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("trim", parents=[common], help="cut a section of a video")
    p.add_argument("file")
    p.add_argument("-s", "--start", default="0", help="start time (default 0)")
    p.add_argument("-e", "--end", help="end time")
    p.add_argument("-d", "--duration", help="duration instead of end time")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--reencode", action="store_true",
                   help="re-encode for frame-accurate cuts (slower)")
    p.set_defaults(func=cmd_trim)

    p = sub.add_parser("compress", parents=[common],
                       help="compress with libx264 + aac")
    p.add_argument("file")
    p.add_argument("--crf", type=int, default=28,
                   help="quality, lower is better (default 28)")
    p.add_argument("--preset", default="medium",
                   help="x264 preset (default medium)")
    p.add_argument("--width", type=int, help="also downscale to this width")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_compress)

    p = sub.add_parser("convert", parents=[common],
                       help="convert container/codec by output extension")
    p.add_argument("file")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("extract-audio", parents=[common],
                       help="extract audio track (mp3/m4a/wav)")
    p.add_argument("file")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_extract_audio)

    p = sub.add_parser("gif", parents=[common],
                       help="create a high-quality GIF (two-pass palette)")
    p.add_argument("file")
    p.add_argument("--fps", type=int, default=12, help="GIF frame rate (default 12)")
    p.add_argument("--width", type=int, default=480, help="GIF width (default 480)")
    p.add_argument("-s", "--start", help="start time")
    p.add_argument("-e", "--end", help="end time")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_gif)

    p = sub.add_parser("thumbnail", parents=[common],
                       help="extract a single frame as an image")
    p.add_argument("file")
    p.add_argument("-t", "--time", default="0", help="timestamp (default 0)")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_thumbnail)

    p = sub.add_parser("resize", parents=[common], help="resize video")
    p.add_argument("file")
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int,
                   help="target height (default: keep aspect ratio)")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_resize)

    p = sub.add_parser("mute", parents=[common], help="remove audio track")
    p.add_argument("file")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_mute)

    p = sub.add_parser("speed", parents=[common],
                       help="change playback speed (video + audio)")
    p.add_argument("file")
    p.add_argument("--factor", type=float, required=True,
                   help="speed multiplier, e.g. 2.0 or 0.5")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_speed)

    p = sub.add_parser("merge", parents=[common],
                       help="concatenate videos with matching codecs")
    p.add_argument("files", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_merge)

    return parser


def main():
    require_tool("ffmpeg")
    require_tool("ffprobe")
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
