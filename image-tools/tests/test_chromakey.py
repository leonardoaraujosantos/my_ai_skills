"""Regression test for image-tools chromakey option parsing.

Bug: the option loop started at index 2 over an already-offset args list, so the
first two option tokens (e.g. `--color #ff0000`) were silently skipped and the
default green chroma was always used.
"""

import subprocess
import sys
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "image_tools.py"


def test_color_option_is_honored(tmp_path):
    src = tmp_path / "green.png"
    Image.new("RGB", (4, 4), (0, 255, 0)).save(src)
    out = tmp_path / "out.png"

    # Chroma = red. Green pixels are far from red, so they must stay OPAQUE.
    # If --color were skipped (the bug), the default green chroma would remove them.
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "chromakey", str(src),
         "--color", "#ff0000", "--tolerance", "10", "-o", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    alphas = list(Image.open(out).convert("RGBA").getdata())
    assert all(px[3] == 255 for px in alphas), "green pixels were wrongly keyed out"


def test_bad_hex_color_is_rejected(tmp_path):
    src = tmp_path / "g.png"
    Image.new("RGB", (2, 2), (0, 255, 0)).save(src)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "chromakey", str(src), "--color", "xyz"],
        capture_output=True, text=True,
    )
    assert "6-digit hex" in r.stdout
