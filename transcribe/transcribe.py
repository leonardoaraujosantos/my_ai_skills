#!/usr/bin/env python3
"""Local speech-to-text for audio/video files.

Orchestrates optional Whisper backends (mlx-whisper, faster-whisper,
openai-whisper CLI, whisper.cpp) and formats the result as txt/srt/vtt/json/md.
Progress goes to stderr; the output file path is printed to stdout.
"""

import argparse
import datetime
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FORMAT_EXTENSIONS = {"txt": ".txt", "srt": ".srt", "vtt": ".vtt", "json": ".json", "md": ".md"}

INSTALL_GUIDE = """\
Install one of (first is best on Apple Silicon):

  pip install mlx-whisper       # Apple Silicon GPU, fastest on Mac (recommended)
  pip install faster-whisper    # CPU/CUDA, fast and accurate
  pip install openai-whisper    # reference implementation ('whisper' CLI)
  brew install whisper-cpp      # whisper.cpp ('whisper-cli', needs a ggml model file)"""


def err(msg):
    print(msg, file=sys.stderr)


def die(msg, code=1):
    err(msg)
    sys.exit(code)


def has_module(name):
    return importlib.util.find_spec(name) is not None


# ---------------------------------------------------------------- backends

def backend_available(name):
    checks = {
        "mlx": lambda: has_module("mlx_whisper"),
        "faster": lambda: has_module("faster_whisper"),
        "whisper": lambda: shutil.which("whisper") is not None,
        "whisper-cli": lambda: shutil.which("whisper-cli") is not None,
    }
    return checks[name]()


def resolve_backend(choice):
    order = ("mlx", "faster", "whisper", "whisper-cli")
    if choice != "auto":
        if not backend_available(choice):
            die(f"Error: backend '{choice}' is not installed on this machine.\n\n{INSTALL_GUIDE}")
        return choice
    for name in order:
        if backend_available(name):
            return name
    die(f"Error: no transcription backend found. {INSTALL_GUIDE}")


def mlx_repo(model):
    if "/" in model:
        return model
    if model.startswith("large-v3"):
        return f"mlx-community/whisper-{model}"
    return f"mlx-community/whisper-{model}-mlx"


def run_mlx(wav, model, lang):
    import mlx_whisper

    result = mlx_whisper.transcribe(
        wav, path_or_hf_repo=mlx_repo(model), language=lang, verbose=False
    )
    segments = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result["segments"]
    ]
    return {"segments": segments, "language": result.get("language"), "duration": None}


def run_faster(wav, model, lang):
    from faster_whisper import WhisperModel

    whisper_model = WhisperModel(model, compute_type="int8")
    seg_iter, info = whisper_model.transcribe(wav, language=lang)
    segments = [
        {"start": s.start, "end": s.end, "text": s.text.strip()} for s in seg_iter
    ]
    return {"segments": segments, "language": info.language, "duration": info.duration}


def run_whisper(wav, model, lang):
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["whisper", wav, "--model", model, "--output_format", "json",
               "--output_dir", tmp, "--verbose", "False"]
        if lang:
            cmd += ["--language", lang]
        run_command(cmd, "whisper CLI failed")
        data = json.loads((Path(tmp) / (Path(wav).stem + ".json")).read_text())
    segments = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in data["segments"]
    ]
    return {"segments": segments, "language": data.get("language"), "duration": None}


def find_ggml_model(model):
    path = Path(model).expanduser()
    if path.suffix == ".bin" and path.is_file():
        return path
    for directory in (Path.home() / ".cache" / "whisper.cpp",
                      Path.home() / "models",
                      Path("/opt/homebrew/share/whisper-cpp")):
        candidate = directory / f"ggml-{model}.bin"
        if candidate.is_file():
            return candidate
    die(f"Error: no ggml model file for '{model}'. Download one, e.g.:\n"
        f"  curl -L -o ~/.cache/whisper.cpp/ggml-{model}.bin --create-dirs \\\n"
        f"    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{model}.bin\n"
        "or pass --model /path/to/ggml-*.bin")


def run_whisper_cpp(wav, model, lang):
    model_file = find_ggml_model(model)
    with tempfile.TemporaryDirectory() as tmp:
        prefix = str(Path(tmp) / "out")
        cmd = ["whisper-cli", "-m", str(model_file), "-f", wav,
               "-oj", "-of", prefix, "-l", lang or "auto"]
        run_command(cmd, "whisper-cli failed")
        data = json.loads(Path(prefix + ".json").read_text())
    segments = [
        {"start": s["offsets"]["from"] / 1000.0,
         "end": s["offsets"]["to"] / 1000.0,
         "text": s["text"].strip()}
        for s in data["transcription"]
    ]
    language = data.get("result", {}).get("language")
    return {"segments": segments, "language": language, "duration": None}


RUNNERS = {"mlx": run_mlx, "faster": run_faster,
           "whisper": run_whisper, "whisper-cli": run_whisper_cpp}


# ------------------------------------------------------------- audio prep

def run_command(cmd, fail_msg):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"Error: {fail_msg}:\n{proc.stderr.strip()}")
    return proc


def prepare_audio(input_path, tmpdir):
    """Return a 16 kHz mono WAV path, converting via ffmpeg when needed."""
    if input_path.suffix.lower() == ".wav":
        return input_path
    if shutil.which("ffmpeg") is None:
        die("Error: ffmpeg is required to extract audio from non-WAV files.\n"
            "Install it with: brew install ffmpeg")
    wav = Path(tmpdir) / (input_path.stem + ".wav")
    err(f"Extracting audio -> 16 kHz mono WAV ({input_path.name})...")
    run_command(
        ["ffmpeg", "-y", "-i", str(input_path), "-vn",
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
        f"ffmpeg could not extract audio from '{input_path}'",
    )
    return wav


def probe_duration(path):
    if shutil.which("ffprobe") is None:
        return None
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


# ------------------------------------------------------------- formatting

def clock(seconds, ms_sep=","):
    total_ms = int(round(seconds * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{ms_sep}{ms:03d}"


def short_clock(seconds):
    return clock(seconds)[:8]


def transcript_body(result, timestamps):
    if timestamps:
        lines = [f"[{short_clock(s['start'])}] {s['text']}" for s in result["segments"]]
    else:
        lines = [s["text"] for s in result["segments"]]
    return "\n".join(lines).strip() + "\n"


def format_txt(result, meta, timestamps):
    return transcript_body(result, timestamps)


def format_srt(result, meta, timestamps):
    blocks = [
        f"{i}\n{clock(s['start'])} --> {clock(s['end'])}\n{s['text']}\n"
        for i, s in enumerate(result["segments"], start=1)
    ]
    return "\n".join(blocks)


def format_vtt(result, meta, timestamps):
    blocks = [
        f"{clock(s['start'], '.')} --> {clock(s['end'], '.')}\n{s['text']}\n"
        for s in result["segments"]
    ]
    return "WEBVTT\n\n" + "\n".join(blocks)


def format_json(result, meta, timestamps):
    payload = dict(meta)
    payload["text"] = " ".join(s["text"] for s in result["segments"]).strip()
    payload["segments"] = result["segments"]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def format_md(result, meta, timestamps):
    frontmatter = "\n".join(f"{key}: {value}" for key, value in meta.items())
    title = Path(meta["source"]).stem
    return (f"---\n{frontmatter}\n---\n\n# Transcript: {title}\n\n"
            + transcript_body(result, timestamps))


FORMATTERS = {"txt": format_txt, "srt": format_srt, "vtt": format_vtt,
              "json": format_json, "md": format_md}


def build_meta(input_path, args, backend, result):
    duration = result.get("duration") or probe_duration(input_path)
    if duration is None and result["segments"]:
        duration = result["segments"][-1]["end"]
    return {
        "source": input_path.name,
        "date": datetime.date.today().isoformat(),
        "duration": short_clock(duration or 0),
        "language": result.get("language") or "unknown",
        "model": args.model,
        "backend": backend,
    }


# ------------------------------------------------------------------ main

def build_parser():
    parser = argparse.ArgumentParser(
        prog="transcribe.py",
        description="Transcribe audio/video files locally with Whisper backends.",
    )
    parser.add_argument("input", help="audio or video file to transcribe")
    parser.add_argument("--backend", default="auto",
                        choices=["auto", "mlx", "faster", "whisper", "whisper-cli"],
                        help="transcription backend (default: auto-detect)")
    parser.add_argument("--model", default="small",
                        help="Whisper model (default: small; large-v3-turbo for quality)")
    parser.add_argument("--lang", default=None,
                        help="language code, e.g. en, pt (default: auto-detect)")
    parser.add_argument("--format", default="txt", choices=sorted(FORMAT_EXTENSIONS),
                        help="output format (default: txt)")
    parser.add_argument("-o", "--output", default=None,
                        help="output file (default: input basename + format extension)")
    parser.add_argument("--timestamps", action="store_true",
                        help="include timestamps in txt/md output")
    return parser


def main():
    args = build_parser().parse_args()
    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        die(f"Error: input file not found: {input_path}")

    backend = resolve_backend(args.backend)
    err(f"Backend: {backend} (model={args.model}, lang={args.lang or 'auto'})")

    with tempfile.TemporaryDirectory() as tmpdir:
        wav = prepare_audio(input_path, tmpdir)
        err("Transcribing...")
        result = RUNNERS[backend](str(wav), args.model, args.lang)

    if not result["segments"]:
        err("Warning: no speech detected; writing empty transcript.")

    meta = build_meta(input_path, args, backend, result)
    content = FORMATTERS[args.format](result, meta, args.timestamps)

    output = Path(args.output) if args.output else input_path.with_suffix(
        FORMAT_EXTENSIONS[args.format])
    output.write_text(content, encoding="utf-8")
    err(f"Done: {len(result['segments'])} segments, "
        f"duration {meta['duration']}, language {meta['language']}")
    print(output)


if __name__ == "__main__":
    main()
