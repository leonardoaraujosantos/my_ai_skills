#!/usr/bin/env python3
"""Storyboard-driven Playwright screenshotter for app-showcase.

Two commands:

  capture.py probe <url> [--state auth.json] [--device "iPhone 15"]
      Print interactive elements (buttons/links/aria/testid/href) with coordinates,
      so you can write reliable selectors. Re-run AFTER auth (authed DOM differs).

  capture.py run <storyboard.json>
      Run the storyboard: authenticate once (saving storage state), then play each
      scene and write its screenshot.

Storyboard schema (JSON):
{
  "base": "https://app.example.com",       # prepended to relative goto paths
  "viewport": [1440, 900],                  # CSS pixels
  "scale": 2,                               # device_scale_factor (2 = crisp/retina)
  "device": "iPhone 15" | null,             # Playwright device descriptor (mobile web)
  "headless": true,
  "state_file": "auth.json",                # where login state is saved/reused
  "auth": {                                 # optional; skip if the app needs no login
     "url": "/login",
     "success_url_contains": "/app",        # wait until URL contains this after submit
     "steps": [ <action>, ... ]             # actions to fill+submit the login form
  },
  "scenes": [
     { "out": "shots/home.png", "steps": [ <action>, ... ] }
  ]
}

Actions (each is a one-key dict unless noted):
  {"goto": "/path"}                 navigate (relative to base)
  {"goto_abs": "https://..."}       navigate to an absolute URL
  {"click": "sel", "force": false}  click (force=true clicks opacity-0/hover-revealed items)
  {"hover": "sel"}                  hover (reveals hover-only buttons; hover BEFORE force-click)
  {"fill": "sel", "value": "..."}   set an <input>/<textarea> value
  {"type": "text", "delay": 12}     type at the caret (contenteditable/inputs)
  {"press": "Enter"}                a key press (e.g. "Enter", "Escape", "Backspace", "End", "Control+A")
  {"repeat_press": "Backspace", "n": 30}   press a key N times (clearing fields)
  {"select_text": "sel", "frac": 0.8}      drag-select across an element to reveal an inline toolbar
  {"wait": 1500}                    wait ms
  {"wait_url": "**/app**"}          wait until URL matches glob
  {"mouse": [x, y]}                 click at CSS coordinates (last resort)
  {"eval": "js expression"}         run JS in the page (returns are printed)
  {"screenshot": "path" | null}     capture (null → use the scene's "out"); full page if {"full": true}
"""
import sys, json
from playwright.sync_api import sync_playwright


def _context(b, sb):
    kw = {"viewport": {"width": sb.get("viewport", [1440, 900])[0],
                        "height": sb.get("viewport", [1440, 900])[1]},
          "device_scale_factor": sb.get("scale", 2)}
    dev = sb.get("device")
    if dev:
        # merge Playwright device descriptor (mobile web / touch / UA)
        return b.new_context(**{**b._playwright.devices[dev]})
    return b.new_context(**kw)


def do_action(pg, a, scene_out=None):
    if "goto" in a:            pg.goto(a["goto"], wait_until=a.get("until", "networkidle"))
    elif "goto_abs" in a:      pg.goto(a["goto_abs"], wait_until=a.get("until", "networkidle"))
    elif "click" in a:         pg.click(a["click"], force=a.get("force", False), timeout=a.get("timeout", 15000))
    elif "hover" in a:         pg.hover(a["hover"], timeout=a.get("timeout", 10000))
    elif "fill" in a:          pg.fill(a["fill"], a["value"])
    elif "type" in a:          pg.keyboard.type(a["type"], delay=a.get("delay", 12))
    elif "press" in a:         pg.keyboard.press(a["press"])
    elif "repeat_press" in a:
        for _ in range(int(a.get("n", 1))): pg.keyboard.press(a["repeat_press"])
    elif "select_text" in a:
        el = pg.get_by_text(a["select_text"], exact=a.get("exact", False)).first if a.get("by_text") \
            else pg.locator(a["select_text"]).first
        box = el.bounding_box()
        y = box["y"] + box["height"] / 2
        pg.mouse.move(box["x"] + 4, y); pg.mouse.down()
        pg.mouse.move(box["x"] + box["width"] * a.get("frac", 0.8), y, steps=10); pg.mouse.up()
    elif "wait" in a:          pg.wait_for_timeout(a["wait"])
    elif "wait_url" in a:      pg.wait_for_url(a["wait_url"], timeout=a.get("timeout", 30000))
    elif "mouse" in a:         pg.mouse.click(a["mouse"][0], a["mouse"][1])
    elif "eval" in a:          print("  eval →", pg.evaluate(a["eval"]))
    elif "screenshot" in a:
        path = a["screenshot"] or scene_out
        pg.screenshot(path=path, full_page=a.get("full", False))
        print("  shot →", path)
    else:
        print("  ?? unknown action", a)


def run(sb):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=sb.get("headless", True))
        state = sb.get("state_file", "auth.json")
        auth = sb.get("auth")
        if auth:
            ctx = _context(b, sb); pg = ctx.new_page()
            pg.goto(sb["base"].rstrip("/") + auth.get("url", "/login"), wait_until="domcontentloaded")
            for a in auth["steps"]:
                do_action(pg, a)
            if auth.get("success_url_contains"):
                try:
                    pg.wait_for_url(f"**{auth['success_url_contains']}**", timeout=30000)
                except Exception as e:
                    print("  auth: success url not reached:", e, "| url:", pg.url)
            pg.wait_for_timeout(auth.get("settle", 3000))
            print("auth done, url:", pg.url)
            ctx.storage_state(path=state); ctx.close()

        # scenes reuse saved state if present
        import os
        ctx_kw = {}
        if os.path.exists(state):
            ctx_kw["storage_state"] = state
        base_ctx = _context(b, sb) if not ctx_kw else b.new_context(
            storage_state=state,
            viewport={"width": sb.get("viewport", [1440, 900])[0], "height": sb.get("viewport", [1440, 900])[1]},
            device_scale_factor=sb.get("scale", 2))
        pg = base_ctx.new_page()
        for sc in sb.get("scenes", []):
            print("scene:", sc.get("out"))
            for a in sc["steps"]:
                do_action(pg, a, scene_out=sc.get("out"))
        b.close()
    print("done")


def probe(url, state=None, device=None):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        kw = {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 2}
        if state:
            import os
            if os.path.exists(state): kw["storage_state"] = state
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(2500)
        els = pg.evaluate("""() => {
          const out=[], seen=new Set();
          for (const e of document.querySelectorAll("button,a[href],[role=button],[data-testid],h1[contenteditable],[contenteditable]")) {
            const r=e.getBoundingClientRect();
            const o={tag:e.tagName.toLowerCase(), t:(e.innerText||'').trim().slice(0,32),
                     aria:e.getAttribute('aria-label'), title:e.getAttribute('title'),
                     href:e.getAttribute('href'), tid:e.getAttribute('data-testid'),
                     ce:e.getAttribute('contenteditable'),
                     x:Math.round(r.x), y:Math.round(r.y)};
            const k=JSON.stringify(o); if(seen.has(k)) continue; seen.add(k);
            if(o.t||o.aria||o.href||o.tid||o.ce) out.push(o);
          }
          return out.slice(0,120);
        }""")
        for e in els:
            print(json.dumps(e, ensure_ascii=False))
        b.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "run":
        run(json.load(open(sys.argv[2])))
    elif cmd == "probe":
        state = None; device = None; args = sys.argv[3:]
        if "--state" in args: state = args[args.index("--state") + 1]
        if "--device" in args: device = args[args.index("--device") + 1]
        probe(sys.argv[2], state, device)
    else:
        print(__doc__); sys.exit(1)
