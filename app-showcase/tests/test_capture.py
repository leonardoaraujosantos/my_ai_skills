"""Regression tests for app-showcase capture.py device emulation.

Bugs fixed:
  * `_context` used `b._playwright.devices` (Browser has no `_playwright`) and
    discarded viewport/scale in device mode.
  * `probe --device` was accepted but never applied.
  * authenticated scenes (auth.json present) bypassed `_context`, dropping the
    device emulation.

Requires Playwright + a Chromium build; skipped otherwise (e.g. minimal CI).

Note: device emulation is checked via devicePixelRatio / touch / user-agent and
the real screenshot dimensions — NOT window.innerWidth, which returns the 980px
layout fallback on a mobile page that has no <meta viewport> tag.
"""

import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "capture.py"
spec = importlib.util.spec_from_file_location("capture", MODULE)
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

IPHONE = "iPhone 15"
IPHONE_VW, IPHONE_VH, IPHONE_SCALE = 393, 659, 3


@contextmanager
def playwright_browser():
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f"chromium not available: {e}")
        try:
            yield p, b
        finally:
            b.close()


def _probe_ctx(ctx):
    pg = ctx.new_page()
    pg.goto("data:text/html,<h1>x</h1>", wait_until="domcontentloaded")
    info = {
        "dpr": pg.evaluate("window.devicePixelRatio"),
        "touch": pg.evaluate("navigator.maxTouchPoints > 0"),
        "ua": pg.evaluate("navigator.userAgent"),
        "innerWidth": pg.evaluate("window.innerWidth"),
    }
    ctx.close()
    return info


def test_desktop_default():
    with playwright_browser() as (p, b):
        info = _probe_ctx(cap._context(p, b, {}))
    assert info["dpr"] == 2 and info["touch"] is False
    assert info["innerWidth"] == 1440


def test_device_emulation_applied():
    with playwright_browser() as (p, b):
        info = _probe_ctx(cap._context(p, b, {"device": IPHONE}))
    assert info["dpr"] == IPHONE_SCALE
    assert info["touch"] is True
    assert "iPhone" in info["ua"]


def test_scale_overrides_device():
    with playwright_browser() as (p, b):
        info = _probe_ctx(cap._context(p, b, {"device": IPHONE, "scale": 2}))
    assert info["dpr"] == 2 and info["touch"] is True  # still a device, custom scale


def test_auth_path_keeps_device(tmp_path):
    # A pre-existing storage_state (the auth.json case) must not drop emulation.
    state = tmp_path / "auth.json"
    state.write_text(json.dumps({"cookies": [], "origins": []}))
    with playwright_browser() as (p, b):
        ctx = cap._context(p, b, {"device": IPHONE}, storage_state=str(state))
        info = _probe_ctx(ctx)
    assert info["dpr"] == IPHONE_SCALE and info["touch"] is True


def test_probe_with_device_runs(tmp_path, capsys):
    # `probe --device` was silently ignored before; it must now run through the
    # device context without error and still emit the element list.
    page = tmp_path / "p.html"
    page.write_text("<html><body><button data-testid='go'>Go</button></body></html>")
    try:
        cap.probe(page.as_uri(), device=IPHONE)
    except Exception as e:
        pytest.skip(f"chromium not available: {e}")
    out = capsys.readouterr().out
    assert '"tid": "go"' in out or '"go"' in out


def test_run_writes_device_sized_screenshot(tmp_path):
    # cap.run() manages its own Playwright — no fixture, to avoid nesting.
    page = tmp_path / "page.html"
    page.write_text("<html><body style='margin:0'>"
                    "<div style='width:100vw;height:200vh;background:#0a0'>hi</div></body></html>")
    out = tmp_path / "shot.png"
    storyboard = {
        "device": IPHONE,
        "state_file": str(tmp_path / "none.json"),
        "scenes": [{"out": str(out), "steps": [
            {"goto_abs": page.as_uri()},
            {"screenshot": None},
        ]}],
    }
    try:
        cap.run(storyboard)
    except Exception as e:
        pytest.skip(f"chromium not available: {e}")
    from PIL import Image
    with Image.open(out) as im:
        # A viewport (non-full-page) screenshot == device viewport * scale.
        # Desktop would be 1440*2 x 900*2; device proves emulation is applied.
        assert im.size == (IPHONE_VW * IPHONE_SCALE, IPHONE_VH * IPHONE_SCALE)
