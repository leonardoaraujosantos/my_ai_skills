"""Regression tests for csv-tools filter operator parsing.

Bug: the regex tried `>` before `>=`, so `age >= 30` parsed as op `>` with
value `= 30`, float() threw, and every row was silently dropped.
"""

import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "csv_tools.py"
spec = importlib.util.spec_from_file_location("csv_tools", MODULE)
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)

CSV = "name,age\nalice,30\nbob,25\ncarol,40\n"


def _filter(tmp_path, condition, capsys):
    f = tmp_path / "t.csv"
    f.write_text(CSV)
    ct.cmd_filter(str(f), condition)
    return capsys.readouterr().out


def test_gte_includes_boundary(tmp_path, capsys):
    out = _filter(tmp_path, "age >= 30", capsys)
    assert "alice" in out and "carol" in out and "bob" not in out
    assert "2 rows matched" in out


def test_lte_includes_boundary(tmp_path, capsys):
    out = _filter(tmp_path, "age <= 30", capsys)
    assert "alice" in out and "bob" in out and "carol" not in out


def test_gt_strict(tmp_path, capsys):
    out = _filter(tmp_path, "age > 30", capsys)
    assert "carol" in out and "alice" not in out


def test_eq_string(tmp_path, capsys):
    out = _filter(tmp_path, "name == alice", capsys)
    assert "alice" in out and "1 rows matched" in out


def test_contains(tmp_path, capsys):
    out = _filter(tmp_path, "name contains ar", capsys)  # carol
    assert "carol" in out and "alice" not in out
