"""Regression tests for bookmarks index + search.

Bugs fixed:
  * update_index() used an unescaped-pipe regex, inserting the new row *inside*
    the separator line and corrupting the Markdown table on every add.
  * search_bookmarks() lowercased the whole file before parsing and title-cased
    results, mangling URLs (case-sensitive paths) and titles ("iPhone"→"Iphone").
"""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "bookmarks.py"
spec = importlib.util.spec_from_file_location("bookmarks", MODULE)
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)


@pytest.fixture
def vault(tmp_path, monkeypatch):
    bdir = tmp_path / "Resources" / "Bookmarks"
    monkeypatch.setattr(bm, "OBSIDIAN_VAULT", tmp_path)
    monkeypatch.setattr(bm, "BOOKMARKS_DIR", bdir)
    monkeypatch.setattr(bm, "BOOKMARKS_INDEX", bdir / "_index.md")
    return tmp_path


def test_index_table_stays_valid_after_multiple_adds(vault):
    bm.update_index("First", "https://a.example/One", "News", "2026-07-06")
    bm.update_index("Second", "https://b.example/Two", "Tech", "2026-07-07")
    text = bm.BOOKMARKS_INDEX.read_text()

    # Separator row must remain a single, intact line.
    assert "|------|-------|----------|" in text
    lines = [l for l in text.splitlines() if l.startswith("|")]
    # header + separator + 2 data rows, every row well-formed (4 pipes)
    assert len(lines) == 4
    for l in lines:
        assert l.count("|") == 4
    assert "First" in text and "Second" in text


def test_search_preserves_case(vault, capsys):
    bm.ensure_dirs()
    note = bm.BOOKMARKS_DIR / "note.md"
    note.write_text("---\nurl: https://Example.com/iPhone\n---\n# My iPhone Review\n\nkubernetes\n")
    bm.search_bookmarks("kubernetes")
    out = capsys.readouterr().out
    assert "https://Example.com/iPhone" in out   # URL casing intact
    assert "My iPhone Review" in out              # title not re-cased to "Iphone"
