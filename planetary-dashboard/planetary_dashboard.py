#!/usr/bin/env python3
"""planetary-dashboard helper CLI (stdlib only).

Subcommands:
  scaffold <dir> [--name NAME]      copy the keyless Vite + Cesium starter into <dir>
  sources [--category C] [--keyless] [--browser] [--json]
                                    list the curated public data-source catalog
  probe [--id ID ...] [--category C] [--keyless] [--timeout S] [--json]
                                    check which sources answer right now
"""

import argparse
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
CATALOG = SKILL_DIR / "references" / "sources.json"
STARTER = SKILL_DIR / "templates" / "starter"
PLACEHOLDER_FILES = ("package.json", "index.html", "src/main.js", "server/proxies.js")
USER_AGENT = "planetary-dashboard-skill/1.0 (source probe)"


def load_catalog(path=CATALOG):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["sources"]


def is_keyless(src):
    auth = src.get("auth", "")
    return auth == "none" or auth.startswith("optional:") or auth == "mostly none"


def filter_sources(sources, category=None, keyless=False, browser=False, ids=None):
    out = []
    for s in sources:
        if ids and s["id"] not in ids:
            continue
        if category and s["category"] != category:
            continue
        if keyless and not is_keyless(s):
            continue
        if browser and not s.get("browser"):
            continue
        out.append(s)
    return out


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "planetary-dashboard"


# ---------------------------------------------------------------- scaffold
def cmd_scaffold(args):
    dest = Path(args.dir).resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} exists and is not empty", file=sys.stderr)
        return 1
    name = args.name or dest.name.replace("-", " ").title()
    slug = slugify(args.name or dest.name)
    shutil.copytree(STARTER, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("node_modules", "dist", "public", ".app-cache"))
    for rel in PLACEHOLDER_FILES:
        f = dest / rel
        if f.exists():
            f.write_text(f.read_text(encoding="utf-8").replace("__APP_NAME__", name).replace("__APP_SLUG__", slug), encoding="utf-8")
    print(f"Scaffolded '{name}' into {dest}")
    print("Next:")
    print(f"  cd {dest}")
    print("  npm install")
    print("  npm run dev        # http://localhost:4173 — works with zero keys")
    print("  npm test           # core unit tests (feed state, layer manager, share links)")
    return 0


# ---------------------------------------------------------------- sources
def cmd_sources(args):
    rows = filter_sources(load_catalog(), args.category, args.keyless, args.browser)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("no sources match")
        return 0
    cats = sorted({s["category"] for s in rows})
    for cat in cats:
        print(f"\n## {cat}")
        for s in (r for r in rows if r["category"] == cat):
            where = "browser" if s.get("browser") else "proxy"
            print(f"- {s['id']:<24} {s['name']}")
            print(f"    auth: {s['auth']:<34} fetch: {where:<8} refresh: {s.get('refresh', '')}")
            if s.get("limits"):
                print(f"    limits: {s['limits']}")
            print(f"    license: {s.get('license', '?')}   url: {s['url']}")
    print(f"\n{len(rows)} source(s). Categories: {', '.join(sorted({s['category'] for s in load_catalog()}))}")
    return 0


# ---------------------------------------------------------------- probe
def probe_one(src, timeout):
    url = src.get("probe") or src["url"]
    if not url.startswith("http") or "{" in url:
        return {"id": src["id"], "status": "skipped", "code": None, "ms": None, "detail": "no probeable URL"}
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1023"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            resp.read(1024)
        status = "up" if code < 400 else "down"
        detail = ""
    except urllib.error.HTTPError as e:
        code = e.code
        # 401/403 on a keyed endpoint means reachable but gated; 429 means reachable but throttled.
        status = "gated" if code in (401, 403) else "throttled" if code == 429 else "down"
        detail = str(e.reason)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        code = None
        status = "down"
        detail = str(getattr(e, "reason", e))
    return {"id": src["id"], "status": status, "code": code, "ms": round((time.monotonic() - t0) * 1000), "detail": detail}


def cmd_probe(args):
    rows = filter_sources(load_catalog(), args.category, args.keyless, False, set(args.id) if args.id else None)
    if not rows:
        print("no sources match", file=sys.stderr)
        return 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda s: probe_one(s, args.timeout), rows))
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            code = r["code"] if r["code"] is not None else "-"
            ms = f"{r['ms']} ms" if r["ms"] is not None else ""
            print(f"{r['status'].upper():<10} {r['id']:<24} {code!s:<5} {ms:<9} {r['detail']}")
        up = sum(r["status"] == "up" for r in results)
        print(f"\n{up}/{len(results)} up")
    return 0 if all(r["status"] in ("up", "gated", "throttled", "skipped") for r in results) else 2


def build_parser():
    p = argparse.ArgumentParser(prog="planetary_dashboard.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="copy the keyless Vite + Cesium starter")
    sc.add_argument("dir")
    sc.add_argument("--name", help="display name (default: from directory)")
    sc.set_defaults(func=cmd_scaffold)

    so = sub.add_parser("sources", help="list curated public data sources")
    so.add_argument("--category")
    so.add_argument("--keyless", action="store_true", help="only sources usable without a key")
    so.add_argument("--browser", action="store_true", help="only sources safe to call from the browser")
    so.add_argument("--json", action="store_true")
    so.set_defaults(func=cmd_sources)

    pr = sub.add_parser("probe", help="check which sources answer right now")
    pr.add_argument("--id", action="append", help="source id (repeatable)")
    pr.add_argument("--category")
    pr.add_argument("--keyless", action="store_true")
    pr.add_argument("--timeout", type=float, default=8.0)
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_probe)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
