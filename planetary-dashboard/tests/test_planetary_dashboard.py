"""Tests for the planetary-dashboard CLI: catalog integrity, filters, scaffold, probe classification."""

import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "planetary_dashboard.py"
spec = importlib.util.spec_from_file_location("planetary_dashboard", MODULE)
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)

REQUIRED = {"id", "name", "category", "auth", "browser", "url", "probe", "refresh", "limits", "license", "used_in"}


def test_catalog_entries_are_complete_and_unique():
    sources = pd.load_catalog()
    assert len(sources) >= 40
    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids))
    for s in sources:
        missing = REQUIRED - s.keys()
        assert not missing, f"{s['id']} missing {missing}"
        assert s["probe"].startswith("https://"), s["id"]


def test_server_only_keys_are_never_marked_browser_safe():
    # Only the ion token and the Google Maps key may reach the browser.
    browser_keys = {"key:CESIUM_ION_TOKEN", "key:GOOGLE_MAPS_API_KEY"}
    for s in pd.load_catalog():
        if s["auth"].startswith("key:") and s["browser"]:
            assert s["auth"] in browser_keys, s["id"]


def test_filters():
    sources = pd.load_catalog()
    keyless = pd.filter_sources(sources, keyless=True)
    assert keyless and all(pd.is_keyless(s) for s in keyless)
    assert not any(s["id"] == "nasa-firms" for s in keyless)
    assert any(s["id"] == "opensky" for s in keyless)  # optional key still counts as keyless
    space = pd.filter_sources(sources, category="space")
    assert {s["id"] for s in space} == {"celestrak", "launch-library-2"}
    assert all(s["browser"] for s in pd.filter_sources(sources, browser=True))
    assert [s["id"] for s in pd.filter_sources(sources, ids={"overpass"})] == ["overpass"]


def test_slugify():
    assert pd.slugify("Atlas Ops 2!") == "atlas-ops-2"
    assert pd.slugify("!!!") == "planetary-dashboard"


def test_scaffold_copies_starter_and_substitutes_names(tmp_path, capsys):
    dest = tmp_path / "atlas"
    assert pd.main(["scaffold", str(dest), "--name", "Atlas Ops"]) == 0
    pkg = json.loads((dest / "package.json").read_text())
    assert pkg["name"] == "atlas-ops"
    html = (dest / "index.html").read_text()
    assert "<title>Atlas Ops</title>" in html
    for rel in ("src/main.js", "server/proxies.js", "src/core/layerManager.js", "scripts/copy-cesium.mjs", ".gitignore"):
        assert (dest / rel).exists(), rel
    leftovers = [p for p in dest.rglob("*") if p.is_file() and "__APP_" in p.read_text(errors="ignore")]
    assert not leftovers, leftovers


def test_scaffold_refuses_non_empty_dir(tmp_path, capsys):
    (tmp_path / "x.txt").write_text("keep me")
    assert pd.main(["scaffold", str(tmp_path)]) == 1
    assert (tmp_path / "x.txt").read_text() == "keep me"


class _Resp:
    def __init__(self, status):
        self.status = status

    def read(self, n=-1):
        return b""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (_Resp(206), "up"),
        (urllib.error.HTTPError("u", 403, "Forbidden", {}, None), "gated"),
        (urllib.error.HTTPError("u", 429, "Too Many", {}, None), "throttled"),
        (urllib.error.HTTPError("u", 500, "Boom", {}, None), "down"),
        (urllib.error.URLError("dns"), "down"),
    ],
)
def test_probe_classification(monkeypatch, outcome, expected):
    def fake_urlopen(req, timeout):
        assert req.get_header("Range") == "bytes=0-1023"
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(pd.urllib.request, "urlopen", fake_urlopen)
    result = pd.probe_one({"id": "x", "url": "https://example.org", "probe": "https://example.org/p"}, timeout=1)
    assert result["status"] == expected


def test_probe_skips_templated_urls():
    assert pd.probe_one({"id": "x", "url": "https://a/{z}/{x}", "probe": ""}, timeout=1)["status"] == "skipped"
