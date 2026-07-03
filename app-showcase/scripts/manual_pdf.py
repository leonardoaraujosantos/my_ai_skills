#!/usr/bin/env python3
"""Build a screenshot-driven user manual PDF from a JSON spec.

Usage:  manual_pdf.py spec.json output.pdf

Spec schema:
{
  "eyebrow": "ACME · PRODUCT",              # small uppercase label on the cover
  "title": "Product\nGetting Started",      # cover title (\n allowed)
  "subtitle": "A hands-on tour ...",
  "meta": "Acme · User Guide · 2026 · Screenshots from the live app",
  "accent": "#F2B705",                      # brand accent (bars, callouts, numbers)
  "ink": "#0f172a",                         # heading color
  "shots_dir": "shots",                     # dir holding the screenshots (abs or rel to cwd)
  "sections": [
    { "title": "Sign in", "image": "login.png",
      "paras": ["Open <b>app...</b> and sign in.", "..."],   # inline HTML allowed (<b>,<i>,<span class=kbd>)
      "tip": "Why it matters: ..." }                          # optional highlighted callout
  ],
  "closing": {                              # optional dark summary box
    "title": "Built for X",
    "box_title": "What runs under every page",
    "items": ["<b>Data sovereignty.</b> ...", "<b>Audit.</b> ..."],
    "footer_left": "Acme — Getting Started",
    "footer_right": "Tagline here"
  }
}

Notes: numbers are auto-assigned per section. Images are constrained to page width.
Requires Playwright (chromium) for PDF rendering.
"""
import sys, os, json, html
from playwright.sync_api import sync_playwright


def build_html(spec, base_dir):
    accent = spec.get("accent", "#F2B705")
    ink = spec.get("ink", "#0f172a")
    shots = spec.get("shots_dir", "shots")
    if not os.path.isabs(shots):
        shots = os.path.join(base_dir, shots)

    def img_src(name):
        p = name if os.path.isabs(name) else os.path.join(shots, name)
        return "file://" + p

    secs = spec.get("sections", [])
    toc = "".join(
        f'<div><span class="n">{i+1:02d}</span>{html.escape(s["title"])}</div>'
        for i, s in enumerate(secs))

    steps = ""
    for i, s in enumerate(secs):
        ps = "".join(f"<p>{p}</p>" for p in s.get("paras", []))
        tip = (f'<div class="tip"><span class="tiplabel">Why it matters</span>{s["tip"]}</div>'
               if s.get("tip") else "")
        fig = (f'<figure><img src="{img_src(s["image"])}"/></figure>'
               if s.get("image") else "")
        steps += f"""
        <section class="step">
          <div class="stephead"><span class="num">{i+1:02d}</span><h2>{html.escape(s['title'])}</h2></div>
          <div class="body">{ps}{tip}</div>{fig}
        </section>"""

    closing = ""
    c = spec.get("closing")
    if c:
        items = "".join(f"<li>{it}</li>" for it in c.get("items", []))
        closing = f"""
        <div class="closing">
          <div class="stephead"><span class="num">&#9733;</span><h2>{html.escape(c.get('title',''))}</h2></div>
          <div class="govbox"><h3>{html.escape(c.get('box_title',''))}</h3><ul>{items}</ul></div>
          <div class="footer"><span>{html.escape(c.get('footer_left',''))}</span><span>{html.escape(c.get('footer_right',''))}</span></div>
        </div>"""

    title_html = html.escape(spec.get("title", "User Guide")).replace("\n", "<br/>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 16mm 15mm 18mm 15mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; color:#1e2530; margin:0; line-height:1.5; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
h1,h2,h3 {{ color:{ink}; letter-spacing:-0.01em; }}
a {{ color:{accent}; }}
.kbd {{ font-family:ui-monospace,Menlo,monospace; background:#f1f5f9; border:1px solid #e2e8f0; border-radius:4px; padding:0 5px; font-size:.9em; }}
.cover {{ height:247mm; display:flex; flex-direction:column; justify-content:center; page-break-after:always; padding:0 6mm; }}
.brandbar {{ width:64px; height:8px; background:{accent}; border-radius:4px; margin-bottom:26px; }}
.eyebrow {{ text-transform:uppercase; letter-spacing:.18em; font-size:12px; font-weight:700; color:{accent}; margin:0 0 14px; filter:brightness(.8); }}
.cover h1 {{ font-size:52px; line-height:1.03; margin:0 0 14px; font-weight:800; }}
.cover .sub {{ font-size:20px; color:#475569; margin:0 0 40px; max-width:150mm; }}
.cover .meta {{ font-size:13px; color:#64748b; border-top:1px solid #e2e8f0; padding-top:16px; }}
.toc {{ margin-top:30px; columns:2; column-gap:26px; font-size:13px; color:#334155; }}
.toc div {{ margin:3px 0; break-inside:avoid; }}
.toc .n {{ color:{accent}; font-weight:700; display:inline-block; width:22px; filter:brightness(.8); }}
.step {{ page-break-inside:avoid; margin:0 0 20px; padding-top:6px; }}
.stephead {{ display:flex; align-items:center; gap:12px; border-bottom:2px solid {accent}; padding-bottom:8px; margin-bottom:12px; }}
.num {{ font-size:15px; font-weight:800; color:#fff; background:{ink}; border-radius:7px; padding:5px 9px; }}
.step h2 {{ font-size:22px; margin:0; font-weight:700; }}
.body p {{ margin:0 0 9px; font-size:13.5px; color:#334155; }}
.tip {{ background:#FFF8E6; border-left:4px solid {accent}; border-radius:0 8px 8px 0; padding:9px 13px; font-size:12.5px; color:#5b4b16; margin:10px 0 4px; }}
.tiplabel {{ display:block; text-transform:uppercase; letter-spacing:.12em; font-size:10px; font-weight:800; color:{accent}; filter:brightness(.8); margin-bottom:3px; }}
figure {{ margin:12px 0 0; break-inside:avoid; }}
figure img {{ width:100%; border:1px solid #e2e8f0; border-radius:10px; box-shadow:0 2px 10px rgba(15,23,42,.08); }}
.closing {{ page-break-before:always; padding-top:8px; }}
.govbox {{ background:{ink}; color:#e2e8f0; border-radius:14px; padding:22px 26px; }}
.govbox h3 {{ color:#fff; margin:0 0 12px; font-size:19px; }}
.govbox ul {{ margin:0; padding-left:18px; }}
.govbox li {{ margin:7px 0; font-size:13.5px; color:#cbd5e1; }}
.govbox b {{ color:#67e8f9; }}
.footer {{ margin-top:26px; border-top:1px solid #e2e8f0; padding-top:12px; font-size:11px; color:#94a3b8; display:flex; justify-content:space-between; }}
</style></head><body>
<div class="cover">
  <div class="brandbar"></div>
  <p class="eyebrow">{html.escape(spec.get('eyebrow',''))}</p>
  <h1>{title_html}</h1>
  <p class="sub">{html.escape(spec.get('subtitle',''))}</p>
  <div class="toc">{toc}</div>
  <div class="meta">{html.escape(spec.get('meta',''))}</div>
</div>
{steps}
{closing}
</body></html>"""


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    spec_path, out_pdf = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path))
    base_dir = os.path.dirname(os.path.abspath(spec_path))
    html_doc = build_html(spec, base_dir)
    html_path = os.path.splitext(os.path.abspath(out_pdf))[0] + ".html"
    open(html_path, "w").write(html_doc)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.goto("file://" + html_path, wait_until="networkidle")
        pg.wait_for_timeout(1500)
        pg.pdf(path=out_pdf, format="A4", print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        b.close()
    print("PDF written:", out_pdf, os.path.getsize(out_pdf), "bytes")


if __name__ == "__main__":
    main()
