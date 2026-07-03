#!/usr/bin/env python3
"""Build a Google Slides pitch from a JSON deck spec (via the `gws` CLI).

Usage:
  slides.py deck.json                 # create a new presentation
  slides.py deck.json <presentationId># rebuild an existing one (deletes+recreates slides)

Requires: the `gws` CLI authenticated (`gws auth status`). Prints the editable URL.

Deck spec (JSON):
{
  "title": "Deck title (shown in Drive)",
  "theme": {"bg":"0F172A","panel":"1E293B","accent":"2DD4BF","gold":"F5C451",
            "text":"F1F5F9","muted":"94A3B8","emerald":"34D399","red":"F87171","white":"FFFFFF"},
  "fonts": {"head":"Poppins","body":"Roboto"},
  "footer": "Brand · Tag",
  "images": {"hero":"/abs/or/rel/hero.png", "sec1":"..."},   # local files, uploaded+publicized
  "slides": [
    {"type":"title","kicker":"...","title":"Name","subtitle":"...","tag":"...","image":"hero"},
    {"type":"cards","kicker":"THE PROBLEM","title":"...","cards":[["Lead","Desc"],...]},   # up to 4 (2x2)
    {"type":"section","kicker":"...","title":"...","bullets":[["Lead","Desc"],...],"image":"sec1"},
    {"type":"bullets","kicker":"...","title":"...","bullets":[["Lead","Desc"],...]},       # full-width, no image
    {"type":"table","kicker":"...","title":"...","columns":["A","B","C"],
        "rows":[["r","✓","✕"],...],"highlight_col":1,"symbols":true},
    {"type":"closing","kicker":"...","title":"Two lines\\nok","subtitle":"...","cta":"...","image":"hero"}
  ]
}
Fonts render tall — keep titles short and re-check by exporting to PDF.
"""
import sys, os, json, subprocess

EMU_IN = 914400
def IN(v): return int(round(v * EMU_IN))
PAGE_W, PAGE_H = 9144000, 5143500

DEFAULT_THEME = {"bg":"0F172A","panel":"1E293B","accent":"2DD4BF","gold":"F5C451",
                 "text":"F1F5F9","muted":"94A3B8","emerald":"34D399","red":"F87171","white":"FFFFFF"}


def gws(args, json_body=None, params=None):
    cmd = ["gws"] + args
    if params is not None: cmd += ["--params", json.dumps(params)]
    if json_body is not None: cmd += ["--json", json.dumps(json_body)]
    cmd += ["--format", "json"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    i = out.find("{")
    if i < 0:
        raise RuntimeError("gws returned no JSON: " + out[:300])
    return json.loads(out[i:])


def gws_raw_json(args, json_str, params):
    """batchUpdate: pass a pre-serialized json string (can be large)."""
    cmd = ["gws"] + args + ["--params", json.dumps(params), "--json", json_str, "--format", "json"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"raw": out[:300]}


def upload_images(images, base_dir):
    urls = {}
    for key, path in (images or {}).items():
        p = path if os.path.isabs(path) else os.path.join(base_dir, path)
        up = gws(["drive", "+upload", p, "--name", f"deck-{key}-{os.path.basename(p)}"])
        fid = up["id"]
        gws(["drive", "permissions", "create"], json_body={"role":"reader","type":"anyone"},
            params={"fileId": fid})
        urls[key] = f"https://drive.google.com/uc?export=download&id={fid}"
        print("  uploaded", key, "->", fid)
    return urls


class Deck:
    def __init__(self, spec, urls):
        self.t = {**DEFAULT_THEME, **spec.get("theme", {})}
        f = spec.get("fonts", {})
        self.HEAD = f.get("head", "Poppins"); self.BODY = f.get("body", "Roboto")
        self.footer_txt = spec.get("footer", "")
        self.urls = urls
        self.reqs = []; self._n = 0

    def rgb(self, hx):
        hx = hx.lstrip("#")
        return {"red":int(hx[0:2],16)/255,"green":int(hx[2:4],16)/255,"blue":int(hx[4:6],16)/255}
    def solid(self, c, a=1.0):
        d = {"color":{"rgbColor":self.rgb(self.t.get(c, c))}}
        if a < 1.0: d["alpha"] = a
        return d
    def oid(self, p):
        self._n += 1; return f"{p}_{self._n:04d}"

    def slide(self):
        sid = self.oid("s")
        self.reqs.append({"createSlide":{"objectId":sid,"slideLayoutReference":{"predefinedLayout":"BLANK"}}})
        self.reqs.append({"updatePageProperties":{"objectId":sid,
            "pageProperties":{"pageBackgroundFill":{"solidFill":self.solid("bg")}},
            "fields":"pageBackgroundFill.solidFill.color"}})
        return sid
    def rect(self, sid, x, y, w, h, fill=None, a=1.0):
        rid = self.oid("r")
        self.reqs.append({"createShape":{"objectId":rid,"shapeType":"RECTANGLE","elementProperties":{
            "pageObjectId":sid,"size":{"width":{"magnitude":w,"unit":"EMU"},"height":{"magnitude":h,"unit":"EMU"}},
            "transform":{"scaleX":1,"scaleY":1,"translateX":x,"translateY":y,"unit":"EMU"}}}})
        props={"outline":{"propertyState":"NOT_RENDERED"}}; fields="outline.propertyState"
        if fill is not None:
            props["shapeBackgroundFill"]={"solidFill":self.solid(fill,a)}
            fields="shapeBackgroundFill.solidFill,outline.propertyState"
        self.reqs.append({"updateShapeProperties":{"objectId":rid,"shapeProperties":props,"fields":fields}})
        return rid
    def image(self, sid, key, x, y, w, h):
        iid = self.oid("img")
        self.reqs.append({"createImage":{"objectId":iid,"url":self.urls[key],"elementProperties":{
            "pageObjectId":sid,"size":{"width":{"magnitude":w,"unit":"EMU"},"height":{"magnitude":h,"unit":"EMU"}},
            "transform":{"scaleX":1,"scaleY":1,"translateX":x,"translateY":y,"unit":"EMU"}}}})
    def tb(self, sid, x, y, w, h):
        tid = self.oid("t")
        self.reqs.append({"createShape":{"objectId":tid,"shapeType":"TEXT_BOX","elementProperties":{
            "pageObjectId":sid,"size":{"width":{"magnitude":w,"unit":"EMU"},"height":{"magnitude":h,"unit":"EMU"}},
            "transform":{"scaleX":1,"scaleY":1,"translateX":x,"translateY":y,"unit":"EMU"}}}})
        return tid
    def text(self, tid, s):
        self.reqs.append({"insertText":{"objectId":tid,"insertionIndex":0,"text":s}})
    def style(self, tid, a, b, size=None, color=None, bold=None, italic=None, font=None):
        st={}; fl=[]
        if size is not None: st["fontSize"]={"magnitude":size,"unit":"PT"}; fl.append("fontSize")
        if color is not None: st["foregroundColor"]={"opaqueColor":{"rgbColor":self.rgb(self.t.get(color,color))}}; fl.append("foregroundColor")
        if bold is not None: st["bold"]=bold; fl.append("bold")
        if italic is not None: st["italic"]=italic; fl.append("italic")
        if font is not None: st["fontFamily"]=font; fl.append("fontFamily")
        rng={"type":"ALL"} if a is None else {"type":"FIXED_RANGE","startIndex":a,"endIndex":b}
        self.reqs.append({"updateTextStyle":{"objectId":tid,"textRange":rng,"style":st,"fields":",".join(fl)}})
    def para(self, tid, align=None, above=None, below=None, line=None, a=None, b=None):
        st={}; fl=[]
        if align is not None: st["alignment"]=align; fl.append("alignment")
        if above is not None: st["spaceAbove"]={"magnitude":above,"unit":"PT"}; fl.append("spaceAbove")
        if below is not None: st["spaceBelow"]={"magnitude":below,"unit":"PT"}; fl.append("spaceBelow")
        if line is not None: st["lineSpacing"]=line; fl.append("lineSpacing")
        rng={"type":"ALL"} if a is None else {"type":"FIXED_RANGE","startIndex":a,"endIndex":b}
        self.reqs.append({"updateParagraphStyle":{"objectId":tid,"textRange":rng,"style":st,"fields":",".join(fl)}})

    def kicker(self, sid, txt, x, y, w=IN(5)):
        t=self.tb(sid,x,y,w,IN(0.3)); self.text(t,txt)
        self.style(t,None,None,size=11,color="accent",bold=True,font=self.HEAD)
    def bullet(self, sid, x, y, w, lead, desc):
        t=self.tb(sid,x,y,w,IN(0.85)); body="▸  "+lead+"\n"+desc; self.text(t,body)
        n=len("▸  "+lead)
        self.style(t,0,3,size=14,color="accent",bold=True,font=self.HEAD)
        self.style(t,3,n,size=14,color="text",bold=True,font=self.HEAD)
        self.style(t,n+1,n+1+len(desc),size=11.5,color="muted",bold=False,font=self.BODY)
        self.para(t,above=0,below=3,line=110,a=0,b=n)
        self.para(t,above=2,below=10,line=112,a=n+1,b=n+1+len(desc))
    def footer(self, sid, idx, label=True):
        if label and self.footer_txt:
            t=self.tb(sid,IN(0.55),IN(5.15),IN(6),IN(0.3)); self.text(t,self.footer_txt)
            self.style(t,None,None,size=9,color="muted",font=self.HEAD)
        p=self.tb(sid,IN(8.7),IN(5.15),IN(0.9),IN(0.3)); self.text(p,f"{idx:02d}")
        self.style(p,None,None,size=9,color="accent",bold=True,font=self.HEAD); self.para(p,align="END")

    # ---- slide renderers ----
    def s_title(self, d, idx):
        s=self.slide()
        if d.get("image"): self.image(s,d["image"],IN(4.85),IN(1.15),IN(5.0),IN(3.333))
        self.rect(s,IN(0.55),IN(1.65),IN(0.09),IN(1.9),fill="accent")
        if d.get("kicker"): self.kicker(s,d["kicker"],IN(0.8),IN(1.15))
        t=self.tb(s,IN(0.75),IN(1.55),IN(4.2),IN(1.2)); self.text(t,d["title"])
        self.style(t,None,None,size=d.get("title_size",56),color="white",bold=True,font=self.HEAD)
        if d.get("subtitle"):
            su=self.tb(s,IN(0.78),IN(2.85),IN(4.0),IN(0.9)); self.text(su,d["subtitle"])
            self.style(su,None,None,size=17,color="muted",font=self.BODY); self.para(su,line=120)
        if d.get("tag"):
            tg=self.tb(s,IN(0.78),IN(3.8),IN(4.0),IN(0.6)); self.text(tg,d["tag"])
            self.style(tg,None,None,size=15,color="accent",bold=True,font=self.HEAD)
        self.footer(s,idx)
    def s_cards(self, d, idx):
        s=self.slide()
        if d.get("kicker"): self.kicker(s,d["kicker"],IN(0.6),IN(0.55))
        h=self.tb(s,IN(0.55),IN(0.85),IN(9),IN(0.8)); self.text(h,d["title"])
        self.style(h,None,None,size=30,color="white",bold=True,font=self.HEAD)
        self.rect(s,IN(0.6),IN(1.62),IN(1.1),IN(0.05),fill="accent")
        cx=[IN(0.6),IN(5.05)]; cy=[IN(2.0),IN(3.5)]
        for i,(lead,desc) in enumerate(d["cards"][:4]):
            x=cx[i%2]; y=cy[i//2]
            self.rect(s,x,y,IN(4.35),IN(1.35),fill="panel")
            self.bullet(s,x+IN(0.28),y+IN(0.2),IN(3.8),lead,desc)
        self.footer(s,idx)
    def s_section(self, d, idx):
        s=self.slide()
        if d.get("kicker"): self.kicker(s,d["kicker"],IN(0.78),IN(0.62))
        self.rect(s,IN(0.55),IN(0.98),IN(0.08),IN(1.1),fill="accent")
        h=self.tb(s,IN(0.78),IN(0.95),IN(4.6),IN(1.15)); self.text(h,d["title"])
        self.style(h,None,None,size=22,color="white",bold=True,font=self.HEAD); self.para(h,line=112)
        y=IN(2.4)
        for lead,desc in d.get("bullets",[]):
            self.bullet(s,IN(0.6),y,IN(4.4),lead,desc); y+=IN(0.9)
        if d.get("image"): self.image(s,d["image"],IN(5.0),IN(1.18),IN(4.8),IN(3.2))
        self.footer(s,idx)
    def s_bullets(self, d, idx):
        s=self.slide()
        if d.get("kicker"): self.kicker(s,d["kicker"],IN(0.6),IN(0.55))
        h=self.tb(s,IN(0.55),IN(0.9),IN(9),IN(0.9)); self.text(h,d["title"])
        self.style(h,None,None,size=26,color="white",bold=True,font=self.HEAD)
        self.rect(s,IN(0.6),IN(1.75),IN(1.1),IN(0.05),fill="accent")
        y=IN(2.15)
        for lead,desc in d.get("bullets",[]):
            self.bullet(s,IN(0.6),y,IN(8.6),lead,desc); y+=IN(0.85)
        self.footer(s,idx)
    def s_table(self, d, idx):
        s=self.slide()
        if d.get("kicker"): self.kicker(s,d["kicker"],IN(0.6),IN(0.42))
        h=self.tb(s,IN(0.55),IN(0.72),IN(9),IN(0.6)); self.text(h,d["title"])
        self.style(h,None,None,size=25,color="white",bold=True,font=self.HEAD)
        rows=[d["columns"]]+d["rows"]; nr=len(rows); nc=len(d["columns"])
        hi=d.get("highlight_col"); symbols=d.get("symbols",False)
        tid=self.oid("tbl")
        self.reqs.append({"createTable":{"objectId":tid,"elementProperties":{"pageObjectId":s,
            "size":{"width":{"magnitude":IN(9.0),"unit":"EMU"},"height":{"magnitude":IN(3.2),"unit":"EMU"}},
            "transform":{"scaleX":1,"scaleY":1,"translateX":IN(0.55),"translateY":IN(1.34),"unit":"EMU"}},
            "rows":nr,"columns":nc}})
        widths=d.get("col_widths")
        if widths:
            for ci,w in enumerate(widths):
                self.reqs.append({"updateTableColumnProperties":{"objectId":tid,"columnIndices":[ci],
                    "tableColumnProperties":{"columnWidth":{"magnitude":IN(w),"unit":"EMU"}},"fields":"columnWidth"}})
        sym_color={"✓":"text","◐":"gold","✕":"red","✗":"red"}
        for ri,row in enumerate(rows):
            for ci,cell in enumerate(row):
                self.reqs.append({"insertText":{"objectId":tid,"cellLocation":{"rowIndex":ri,"columnIndex":ci},
                    "text":str(cell),"insertionIndex":0}})
                if ri==0: col,sz,bold="bg",12,True
                elif hi is not None and ci==hi: col,sz,bold="emerald",11.5,True
                elif symbols and ci>0: col=sym_color.get(str(cell).strip(),"muted"); sz,bold=12,True
                elif ci==0: col,sz,bold="text",11,True
                else: col,sz,bold="muted",11.5,False
                self.reqs.append({"updateTextStyle":{"objectId":tid,"cellLocation":{"rowIndex":ri,"columnIndex":ci},
                    "textRange":{"type":"ALL"},"style":{"fontSize":{"magnitude":sz,"unit":"PT"},
                    "foregroundColor":{"opaqueColor":{"rgbColor":self.rgb(self.t[col])}},"bold":bold,
                    "fontFamily":(self.BODY if ci==0 and ri>0 else self.HEAD)},
                    "fields":"fontSize,foregroundColor,bold,fontFamily"}})
                align="START" if (ci==0 or not symbols) else "CENTER"
                self.reqs.append({"updateParagraphStyle":{"objectId":tid,"cellLocation":{"rowIndex":ri,"columnIndex":ci},
                    "textRange":{"type":"ALL"},"style":{"alignment":align},"fields":"alignment"}})
        def fill(ri,ci,c):
            self.reqs.append({"updateTableCellProperties":{"objectId":tid,
                "tableRange":{"location":{"rowIndex":ri,"columnIndex":ci},"rowSpan":1,"columnSpan":1},
                "tableCellProperties":{"tableCellBackgroundFill":{"solidFill":self.solid(c)}},
                "fields":"tableCellBackgroundFill.solidFill"}})
        for ci in range(nc): fill(0,ci,"accent")
        for ri in range(1,nr):
            band="bg" if ri%2 else "panel"
            for ci in range(nc): fill(ri,ci,("16352E" if hi is not None and ci==hi else band))
        self.footer(s,idx,label=False)
    def s_closing(self, d, idx):
        s=self.slide()
        if d.get("image"): self.image(s,d["image"],IN(5.4),IN(1.35),IN(4.35),IN(2.9))
        self.rect(s,IN(0.55),IN(1.35),IN(0.08),IN(1.7),fill="gold")
        if d.get("kicker"): self.kicker(s,d["kicker"],IN(0.78),IN(1.0))
        h=self.tb(s,IN(0.78),IN(1.32),IN(4.5),IN(1.8)); self.text(h,d["title"])
        self.style(h,None,None,size=d.get("title_size",25),color="white",bold=True,font=self.HEAD); self.para(h,line=118)
        if d.get("subtitle"):
            su=self.tb(s,IN(0.8),IN(3.35),IN(4.4),IN(1.1)); self.text(su,d["subtitle"])
            self.style(su,None,None,size=13,color="muted",font=self.BODY); self.para(su,line=126)
        if d.get("cta"):
            c=self.tb(s,IN(0.8),IN(4.55),IN(5.5),IN(0.45)); self.text(c,d["cta"])
            self.style(c,None,None,size=13.5,color="accent",bold=True,font=self.HEAD)
        self.footer(s,idx)

    def build(self, slides):
        r={"title":self.s_title,"cards":self.s_cards,"section":self.s_section,
           "bullets":self.s_bullets,"table":self.s_table,"closing":self.s_closing}
        for i,d in enumerate(slides,1):
            r[d["type"]](d,i)
        return self.reqs


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1]))
    base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
    pid = sys.argv[2] if len(sys.argv) > 2 else None

    if not pid:
        created = gws(["slides", "presentations", "create"], json_body={"title": spec.get("title", "Deck")})
        pid = created["presentationId"]
        print("created presentation", pid)

    urls = upload_images(spec.get("images", {}), base_dir)
    deck = Deck(spec, urls)
    reqs = deck.build(spec["slides"])

    # delete existing slides so this is idempotent, then create ours
    existing = gws(["slides","presentations","get"],
                   params={"presentationId":pid,"fields":"slides(objectId)"}).get("slides",[])
    head = [{"deleteObject":{"objectId":s["objectId"]}} for s in existing]
    body = json.dumps({"requests": head + reqs})
    print(f"applying {len(head)} deletes + {len(reqs)} requests ...")
    res = gws_raw_json(["slides","presentations","batchUpdate"], body, {"presentationId":pid})
    if "error" in res:
        print("ERROR:", json.dumps(res["error"])[:400]); sys.exit(1)
    print("URL: https://docs.google.com/presentation/d/%s/edit" % pid)


if __name__ == "__main__":
    main()
