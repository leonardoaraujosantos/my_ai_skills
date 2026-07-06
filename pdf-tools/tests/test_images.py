"""Regression test for pdf-tools image extraction.

Bug: FlateDecode images were written by dumping the raw decoded stream bytes to
a .png, producing unopenable files. The fix uses pypdf's page.images API, which
reconstructs a real image. Extracted files must open as valid images.
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("fitz")
pytest.importorskip("PIL")
import fitz  # noqa: E402
from PIL import Image  # noqa: E402

MODULE = Path(__file__).resolve().parents[1] / "pdf_tools.py"
spec = importlib.util.spec_from_file_location("pdf_tools", MODULE)
pt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pt)


def _make_pdf_with_image(tmp_path):
    png = tmp_path / "src.png"
    Image.new("RGB", (16, 16), (12, 200, 60)).save(png)
    pdf = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    page.insert_image(fitz.Rect(0, 0, 16, 16), filename=str(png))
    doc.save(str(pdf))
    doc.close()
    return pdf


def test_extracted_images_are_valid(tmp_path, capsys):
    pdf = _make_pdf_with_image(tmp_path)
    outdir = tmp_path / "imgs"
    pt.cmd_images(str(pdf), str(outdir))

    files = list(outdir.glob("*"))
    assert files, "no images extracted"
    for f in files:
        # Must open and verify as a real image, not corrupt bytes.
        with Image.open(f) as im:
            im.verify()
