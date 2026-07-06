"""Regression test for journal --tags.

Bug: --tags was parsed and passed to cmd_add but never used. It now renders as
inline hashtags in the entry.
"""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "journal.py"
spec = importlib.util.spec_from_file_location("journal", MODULE)
jn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jn)


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setattr(jn, "OBSIDIAN_VAULT", tmp_path)
    monkeypatch.setattr(jn, "JOURNAL_DIR", tmp_path / "Journal")
    monkeypatch.setattr(jn, "DAILY_DIR", tmp_path / "Journal" / "Daily")
    return tmp_path


def test_tags_render_as_hashtags(vault):
    jn.cmd_add("Learned about vector databases", tags="ml,databases", date="2026-07-06")
    path = jn.get_journal_path("2026-07-06")
    text = path.read_text()
    assert "#ml" in text and "#databases" in text


def test_no_tags_adds_no_hashtag_line(vault):
    jn.cmd_add("Plain entry", date="2026-07-06")
    text = jn.get_journal_path("2026-07-06").read_text()
    # With tags the entry is "...Plain entry\n#tag...". Without tags, no hashtag
    # line should immediately follow the entry text.
    assert "Plain entry\n#" not in text
