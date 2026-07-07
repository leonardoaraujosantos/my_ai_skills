#!/usr/bin/env python3
"""Run analog circuit simulations with ngspice in batch mode.

Subcommands:
  run <netlist.cir>   execute the netlist, convert wrdata output to CSV, summarize
  op <netlist.cir>    DC operating point: node voltages + source currents table
  plot <out.csv>      quick ASCII plot of a CSV column vs the first column
  template <name>     copy a bundled template ('template list' shows them)

Python 3 stdlib only. Requires ngspice on PATH for 'run' and 'op'.
"""

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates"

INSTALL_HINT = (
    "error: ngspice not found on PATH.\n"
    "Install it first:  brew install ngspice   (macOS)\n"
    "                   sudo apt install ngspice   (Debian/Ubuntu)"
)

DEFAULT_ANALYSIS = {
    "op": "op",
    "ac": "ac dec 20 1 10Meg",
    "tran": "tran 10u 10m",
}


# ---------------------------------------------------------------- helpers

def die(msg):
    sys.exit(msg)


def find_ngspice():
    exe = shutil.which("ngspice")
    if not exe:
        die(INSTALL_HINT)
    return exe


def read_netlist(path_str):
    path = Path(path_str)
    if not path.is_file():
        die(f"error: netlist not found: {path}")
    return path, path.read_text()


def run_ngspice(netlist: Path):
    """Run ngspice -b in the netlist's directory; return combined output."""
    exe = find_ngspice()
    proc = subprocess.run(
        [exe, "-b", netlist.name],
        cwd=netlist.parent,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = proc.stdout + proc.stderr
    if proc.returncode != 0:
        die(f"ngspice failed (exit {proc.returncode}):\n{out}")
    return out


# ------------------------------------------------------- netlist analysis

CONTROL_RE = re.compile(r"^\s*\.control\b.*?^\s*\.endc\b", re.M | re.S | re.I)
WRDATA_RE = re.compile(r"^\s*wrdata\s+(\S+)((?:[ \t]+\S+)*)", re.M | re.I)


def get_control_block(text):
    m = CONTROL_RE.search(text)
    return m.group(0) if m else None


def get_wrdata(text):
    """Return (filename, [vector names]) from the first wrdata line, or None."""
    m = WRDATA_RE.search(text)
    if not m:
        return None
    return m.group(1), m.group(2).split()


def infer_xname(control_text):
    for pat, name in ((r"^\s*ac\s", "frequency"), (r"^\s*tran\s", "time"),
                      (r"^\s*dc\s", "sweep"), (r"^\s*op\b", "op")):
        if re.search(pat, control_text, re.M | re.I):
            return name
    return "x"


def ac_probes(probes):
    """For AC analysis, turn v(node) probes into vdb/vp so data is real-valued."""
    out = []
    for p in probes:
        m = re.fullmatch(r"[vV]\((.+)\)", p)
        if m:
            out += [f"vdb({m.group(1)})", f"vp({m.group(1)})"]
        else:
            out.append(p)
    return out


def build_control(analysis, probes, wrdata_file):
    kind = analysis.split()[0].lower()
    line = DEFAULT_ANALYSIS.get(analysis, analysis)
    if kind == "dc" and len(analysis.split()) < 5:
        die("error: dc analysis needs arguments, e.g. --analysis 'dc V1 0 5 0.1'")
    vecs = ac_probes(probes) if kind == "ac" else probes
    body = [".control", "set wr_vecnames", "set wr_singlescale", line]
    if kind == "op":
        body.append("print all")
    body += [f"wrdata {wrdata_file} {' '.join(vecs)}", "quit", ".endc"]
    return "\n".join(body)


def inject_control(text, control):
    """Insert a .control block before the final .end (or append one)."""
    m = re.search(r"^\s*\.end\s*$", text, re.M | re.I)
    if m:
        return text[:m.start()] + control + "\n" + text[m.start():]
    return text.rstrip() + "\n" + control + "\n.end\n"


# ------------------------------------------------------- wrdata -> CSV

def _floats(tokens):
    try:
        return [float(t) for t in tokens]
    except ValueError:
        return None


def parse_wrdata(path: Path, vec_names, xname):
    """Parse an ngspice wrdata file into (header, rows of floats).

    Handles three layouts: a header line (set wr_vecnames), one scale column
    (set wr_singlescale), or the default repeated-scale pairs.
    """
    lines = [ln.split() for ln in path.read_text().splitlines() if ln.strip()]
    if not lines:
        die(f"error: wrdata output {path} is empty")
    header = None
    if _floats(lines[0]) is None:
        header = lines[0]
        lines = lines[1:]
    rows = [_floats(t) for t in lines]
    if any(r is None for r in rows):
        die(f"error: non-numeric data in {path}")
    if header:
        return header, rows
    return _label_columns(rows, vec_names, xname)


def _label_columns(rows, vec_names, xname):
    """Name headerless wrdata columns; drop repeated scale columns."""
    ncol, n = len(rows[0]), len(vec_names)
    if n and ncol == 2 * n:  # (scale, value) per vector
        keep = [0] + [2 * i + 1 for i in range(n)]
        return ([xname] + vec_names, [[r[i] for i in keep] for r in rows])
    if n and ncol == 3 * n:  # complex: (scale, re, im) per vector
        header = [xname]
        for v in vec_names:
            header += [f"{v}.re", f"{v}.im", f"{v}.mag"]
        out = []
        for r in rows:
            row = [r[0]]
            for i in range(n):
                re_, im_ = r[3 * i + 1], r[3 * i + 2]
                row += [re_, im_, math.hypot(re_, im_)]
            out.append(row)
        return header, out
    if n and ncol == n + 1:
        return [xname] + vec_names, rows
    return [xname] + [f"c{i}" for i in range(1, ncol)], rows


def write_csv(path: Path, header, rows):
    with path.open("w") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(f"{v:.6g}" for v in r) + "\n")


def print_summary(header, rows, csv_path):
    print(f"wrote {csv_path}  ({len(rows)} points, {len(header)} columns)")
    print(f"{'column':<20} {'min':>14} {'max':>14}")
    for i, name in enumerate(header):
        col = [r[i] for r in rows]
        print(f"{name:<20} {min(col):>14.6g} {max(col):>14.6g}")


# ------------------------------------------------------------ cmd: run

def cmd_run(args):
    netlist, text = read_netlist(args.netlist)
    control = get_control_block(text)
    if control:
        _run_existing_control(netlist, text, control, args)
    else:
        _run_injected_control(netlist, text, args)


def _run_existing_control(netlist, text, control, args):
    wr = get_wrdata(control)
    output = run_ngspice(netlist)
    if not wr:
        print("netlist has a .control block without wrdata; ngspice output:\n")
        print(output.strip())
        return
    wr_file, vecs = wr
    raw = netlist.parent / wr_file
    if not raw.is_file():
        die(f"error: ngspice did not produce {raw}\n{output}")
    _finish(raw, vecs, infer_xname(control), netlist, args.output)


def _run_injected_control(netlist, text, args):
    probes = [p for chunk in args.probe for p in chunk.split(",") if p]
    with tempfile.TemporaryDirectory(dir=netlist.parent) as tmp:
        wr_file = "spice_run.out"
        control = build_control(args.analysis, probes, wr_file)
        tmp_net = Path(tmp) / netlist.name
        tmp_net.write_text(inject_control(text, control))
        print(f"no .control block found; injecting: {args.analysis} "
              f"-> wrdata {' '.join(probes)}")
        output = run_ngspice(tmp_net)
        raw = Path(tmp) / wr_file
        if not raw.is_file():
            die(f"error: ngspice did not produce data\n{output}")
        _finish(raw, probes, infer_xname(control), netlist, args.output)


def _finish(raw, vecs, xname, netlist, out_opt):
    header, rows = parse_wrdata(raw, vecs, xname)
    csv_path = Path(out_opt) if out_opt else netlist.with_suffix(".csv")
    write_csv(csv_path, header, rows)
    print_summary(header, rows, csv_path)


# ------------------------------------------------------------- cmd: op

OP_VALUE_RE = re.compile(r"^\s*(\S+)\s*=\s*([-+0-9.eE]+)\s*$", re.M)


def cmd_op(args):
    netlist, text = read_netlist(args.netlist)
    stripped = CONTROL_RE.sub("", text)  # replace any existing control block
    control = ".control\nop\nprint all\nquit\n.endc"
    with tempfile.TemporaryDirectory(dir=netlist.parent) as tmp:
        tmp_net = Path(tmp) / netlist.name
        tmp_net.write_text(inject_control(stripped, control))
        output = run_ngspice(tmp_net)
    pairs = OP_VALUE_RE.findall(output)
    if not pairs:
        die(f"error: no operating-point values found in ngspice output:\n{output}")
    volts = [(k, v) for k, v in pairs if "#branch" not in k]
    amps = [(k, v) for k, v in pairs if "#branch" in k]
    print("Node voltages")
    for k, v in volts:
        print(f"  {k:<18} {float(v):>14.6g} V")
    if amps:
        print("Source currents")
        for k, v in amps:
            print(f"  {k:<18} {float(v):>14.6g} A")


# ----------------------------------------------------------- cmd: plot

def read_csv(path_str):
    path = Path(path_str)
    if not path.is_file():
        die(f"error: CSV not found: {path}")
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    header = lines[0].split(",")
    rows = [[float(v) for v in ln.split(",")] for ln in lines[1:]]
    if not rows:
        die(f"error: no data rows in {path}")
    return header, rows


def pick_column(header, name):
    if name in header:
        return header.index(name)
    die(f"error: column '{name}' not in {header}")


def cmd_plot(args):
    header, rows = read_csv(args.csv)
    if args.db:
        yi, ylabel = pick_column(header, args.db), f"dB({args.db})"
    else:
        yi = pick_column(header, args.col) if args.col else 1
        ylabel = header[yi]
    pts = []
    for r in rows:
        x, y = r[0], r[yi]
        if args.db:
            if abs(y) == 0:
                continue
            y = 20 * math.log10(abs(y))
        if args.log_x:
            if x <= 0:
                continue
            x = math.log10(x)
        pts.append((x, y))
    if not pts:
        die("error: no plottable points (log of non-positive values?)")
    xlabel = header[0] + (" (log10)" if args.log_x else "")
    ascii_plot(pts, xlabel, ylabel)


def ascii_plot(pts, xlabel, ylabel, width=60, height=20):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    xspan = (xmax - xmin) or 1.0
    yspan = (ymax - ymin) or 1.0
    grid = [[" "] * width for _ in range(height)]
    for x, y in pts:
        col = round((x - xmin) / xspan * (width - 1))
        row = round((ymax - y) / yspan * (height - 1))
        grid[row][col] = "*"
    print(f"{ylabel} vs {xlabel}")
    for i, line in enumerate(grid):
        label = ""
        if i == 0:
            label = f"{ymax:.4g}"
        elif i == height - 1:
            label = f"{ymin:.4g}"
        print(f"{label:>10} |{''.join(line)}|")
    print(f"{'':>10} +{'-' * width}+")
    print(f"{'':>10}  {xmin:<.4g}{xmax:>{width - 6}.4g}")


# ------------------------------------------------------- cmd: template

def template_desc(path: Path):
    first = path.read_text().splitlines()[0]
    return first.lstrip("* ").split("--", 1)[-1].strip()


def cmd_template(args):
    if args.name == "list":
        for t in sorted(TEMPLATE_DIR.glob("*.cir")):
            print(f"{t.stem:<20} {template_desc(t)}")
        return
    src = TEMPLATE_DIR / (args.name if args.name.endswith(".cir")
                          else args.name + ".cir")
    if not src.is_file():
        names = ", ".join(t.stem for t in sorted(TEMPLATE_DIR.glob("*.cir")))
        die(f"error: unknown template '{args.name}'. Available: {names}")
    dest = Path(args.output) if args.output else Path.cwd() / src.name
    if dest.exists():
        die(f"error: {dest} already exists; pass -o to choose another path")
    shutil.copy(src, dest)
    print(f"copied {src.name} -> {dest}")


# ----------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="spice_run.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run a netlist and convert wrdata output to CSV")
    p.add_argument("netlist")
    p.add_argument("-o", "--output", help="CSV output path (default: <netlist>.csv)")
    p.add_argument("--analysis", default="tran",
                   help="analysis when no .control block exists: op | ac | tran | "
                        "'dc V1 0 5 0.1' | any full ngspice analysis line")
    p.add_argument("--probe", action="append", default=[],
                   help="node to record, e.g. v(out); repeat or comma-separate")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("op", help="DC operating point table")
    p.add_argument("netlist")
    p.set_defaults(func=cmd_op)

    p = sub.add_parser("plot", help="ASCII plot of a CSV column vs the first column")
    p.add_argument("csv")
    p.add_argument("--col", help="column name to plot (default: second column)")
    p.add_argument("--db", help="plot 20*log10(|column|) of this column")
    p.add_argument("--log-x", action="store_true", help="log10 the x axis")
    p.set_defaults(func=cmd_plot)

    p = sub.add_parser("template", help="copy a bundled template ('list' to show)")
    p.add_argument("name")
    p.add_argument("-o", "--output", help="destination path")
    p.set_defaults(func=cmd_template)

    args = ap.parse_args()
    if args.cmd == "run" and not args.probe:
        args.probe = ["v(out)"]
    args.func(args)


if __name__ == "__main__":
    main()
