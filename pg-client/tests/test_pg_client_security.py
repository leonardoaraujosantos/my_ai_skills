"""Regression tests for pg-client security hardening.

Covers:
  * `query` is forced read-only at the DB level (mutations must use `exec`).
  * Apache AGE graph names are validated before interpolation.
  * Cypher bodies are dollar-quoted with a tag that cannot be terminated by
    the body content (e.g. a query containing `$$`).
  * profiles.json is written with owner-only (0600) permissions.
"""

import importlib.util
import stat
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "pg_client.py"
spec = importlib.util.spec_from_file_location("pg_client", MODULE)
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)


# ── graph-name validation ───────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["g", "my_graph", "_g1", "Graph2"])
def test_safe_graph_name_accepts_identifiers(name):
    assert pg._safe_graph_name(name) == name


@pytest.mark.parametrize("name", [
    "g'); DROP TABLE users;--",
    "a b",
    "1graph",
    "graph-name",
    "",
    "x$$y",
])
def test_safe_graph_name_rejects_injection(name):
    with pytest.raises(SystemExit):
        pg._safe_graph_name(name)


# ── cypher dollar-quoting ───────────────────────────────────────────────────

def test_cypher_literal_wraps_and_is_balanced():
    wrapped = pg._cypher_literal("MATCH (n) RETURN n")
    tag = wrapped.split(" ", 1)[0]
    assert wrapped.startswith(tag) and wrapped.endswith(tag)


def test_cypher_literal_tag_absent_from_body():
    # A body containing `$$` must not be able to terminate the quoting.
    body = "MATCH (n) WHERE n.x = '$$ injected' RETURN n"
    wrapped = pg._cypher_literal(body)
    tag = wrapped.split(" ", 1)[0]
    assert tag not in body
    assert wrapped.count(tag) == 2


# ── read-only query enforcement ─────────────────────────────────────────────

class _FakeCursor:
    def __init__(self):
        self.description = [("n",)]
        self.rowcount = 1
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def execute(self, sql, params=None):
        self.executed = sql
    def fetchall(self):
        return [(1,)]


class _FakeConn:
    def __init__(self):
        self.session = None
    def set_session(self, readonly=None, autocommit=None):
        self.session = {"readonly": readonly, "autocommit": autocommit}
    def cursor(self):
        return _FakeCursor()


def test_query_forces_readonly_session(monkeypatch):
    fake = _FakeConn()

    @contextmanager
    def fake_get_conn(_args):
        yield fake

    monkeypatch.setattr(pg, "get_conn", fake_get_conn)
    args = SimpleNamespace(sql="SELECT 1", limit=None, format="table")
    pg.cmd_query(args)

    assert fake.session == {"readonly": True, "autocommit": True}


# ── profile file permissions ────────────────────────────────────────────────

def test_save_profiles_is_owner_only(monkeypatch, tmp_path):
    target = tmp_path / "profiles.json"
    monkeypatch.setattr(pg, "PROFILES_FILE", target)
    pg.save_profiles({"p": {"dsn": "postgres://u:secret@h/db"}})
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o600
