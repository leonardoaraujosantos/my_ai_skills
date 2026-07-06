"""Regression tests for json-tools flatten/unflatten.

Bugs fixed:
  * `unflatten` was implemented but never dispatched in main() ("Unknown command").
  * The old implementation seeded a dict and crashed on top-level arrays / mixed
    nesting.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "json_tools.py"
spec = importlib.util.spec_from_file_location("json_tools", MODULE)
jt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jt)

CASES = [
    {"a": {"b": [1, 2]}, "c": "x"},
    [10, 20, {"k": "v"}],
    {"users": [{"name": "Ann"}, {"name": "Bob"}], "n": 2},
    {"deep": {"a": {"b": {"c": [ {"d": 1} ]}}}},
]


def test_round_trip_flatten_unflatten():
    for original in CASES:
        flat = jt.flatten_json(original)
        assert jt.unflatten_json(flat) == original


def test_unflatten_top_level_array():
    flat = {"[0]": 10, "[1]": 20}
    assert jt.unflatten_json(flat) == [10, 20]


def test_unflatten_command_is_wired(tmp_path):
    flat = {"a.b[0]": 1, "a.b[1]": 2}
    f = tmp_path / "flat.json"
    f.write_text(json.dumps(flat))
    r = subprocess.run(
        [sys.executable, str(MODULE), "unflatten", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "Unknown command" not in (r.stdout + r.stderr)
    assert json.loads(r.stdout) == {"a": {"b": [1, 2]}}
