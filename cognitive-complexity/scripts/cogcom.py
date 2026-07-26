#!/usr/bin/env python3
"""
cogcom.py — Cognitive Complexity analyzer (orchestrator).

Dispatches each file to the best-in-class open-source cognitive-complexity tool
for its language, normalizes the output, and reports a ranked, banded summary.
No analysis logic lives here — the actual metric is computed by the underlying
tools (SonarSource's definition in every case except the C/C++ fallback):

    Python      -> complexipy
    Go          -> gocognit
    TS/JS       -> eslint + eslint-plugin-sonarjs
    C / C++     -> clang-tidy (readability-function-cognitive-complexity)
                   fallback: lizard (CYCLOMATIC, clearly labeled)
    Solidity    -> solhint code-complexity rule (CYCLOMATIC, clearly labeled)
    SystemVerilog -> scc (per-FILE cyclomatic-style estimate, clearly labeled;
                   no open-source tool reports per-function complexity for SV)

Usage:
    cogcom.py <path> [<path>...] [--top N] [--threshold N] [--lang L] [--json]

Run scripts/setup.sh once to install the tools.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TS_DIR = SCRIPT_DIR / "ts"

# Bands per SonarSource / common linting practice.
BANDS = [
    (0, 10, "Excellent", "🟢"),
    (11, 15, "Acceptable", "🟡"),
    (16, 25, "Warning", "🟠"),
    (26, 10**9, "Critical", "🔴"),
]

EXT_LANG = {
    ".py": "python",
    ".go": "go",
    ".ts": "ts", ".tsx": "ts", ".js": "ts", ".jsx": "ts", ".mjs": "ts", ".cjs": "ts",
    ".c": "c", ".h": "cpp",
    ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".hxx": "cpp",
    ".sol": "solidity",
    ".sv": "sv", ".svh": "sv",
}

LANG_ALIASES = {"systemverilog": "sv", "sol": "solidity"}

IGNORE_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "target",
    "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache",
    ".next", ".nuxt", "coverage", "third_party", ".tox", "site-packages",
}


def band(score):
    for lo, hi, name, emoji in BANDS:
        if lo <= score <= hi:
            return name, emoji
    return "Critical", "🔴"


def collect(paths, only_lang):
    """Return {language: [files]} under the given paths, honoring ignores."""
    by_lang = defaultdict(list)
    for p in paths:
        p = Path(p)
        if p.is_file():
            lang = EXT_LANG.get(p.suffix.lower())
            if lang and (not only_lang or lang in only_lang):
                by_lang[lang].append(str(p))
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            for f in files:
                lang = EXT_LANG.get(Path(f).suffix.lower())
                if lang and (not only_lang or lang in only_lang):
                    by_lang[lang].append(os.path.join(root, f))
    return by_lang


def chunked(seq, n=400):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def have(tool):
    return shutil.which(tool) is not None


# --- per-language runners -> list of {file, function, line, score} ----------

def run_python(files):
    if not have("complexipy"):
        return [], "complexipy not installed (run setup.sh)"
    out = []
    for batch in chunked(files):
        with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as tf:
            tmp = tf.name
        try:
            subprocess.run(
                ["complexipy", *batch, "--output-format", "json", "--output", tmp, "-q"],
                capture_output=True, text=True, timeout=600,
            )
            with open(tmp) as fh:
                data = json.load(fh)
            for d in data:
                out.append({
                    "file": d.get("path") or d.get("file_name"),
                    "function": d.get("function_name"),
                    "line": (d.get("refactor_plans") or [{}])[0].get("line_start"),
                    "score": int(d["complexity"]),
                })
        except Exception as e:  # noqa: BLE001
            return out, f"complexipy error: {e}"
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return out, None


def run_go(files):
    gocognit = shutil.which("gocognit") or str(Path.home() / "go/bin/gocognit")
    if not Path(gocognit).exists():
        return [], "gocognit not installed (run setup.sh)"
    out = []
    for batch in chunked(files):
        try:
            r = subprocess.run([gocognit, "-json", *batch],
                               capture_output=True, text=True, timeout=600)
            data = json.loads(r.stdout or "[]")
            for d in data:
                pos = d.get("Pos", {})
                out.append({
                    "file": pos.get("Filename"),
                    "function": d.get("FuncName"),
                    "line": pos.get("Line"),
                    "score": int(d["Complexity"]),
                })
        except Exception as e:  # noqa: BLE001
            return out, f"gocognit error: {e}"
    return out, None


def run_ts(files):
    """Score JS/TS via the ESLint Node API runner (one long-lived process)."""
    if not (TS_DIR / "node_modules" / "eslint").exists():
        return [], "eslint toolchain not installed (run setup.sh)"
    if not have("node"):
        return [], "node not found — JS/TS skipped"
    runner = TS_DIR / "run.mjs"
    out = []
    files = [str(Path(f).resolve()) for f in files]
    for batch in chunked(files, 2000):
        try:
            r = subprocess.run(
                ["node", str(runner), json.dumps(batch)],
                capture_output=True, text=True, timeout=1800, cwd=str(TS_DIR),
            )
            for d in json.loads(r.stdout or "[]"):
                out.append({
                    "file": d["file"], "function": None,
                    "line": d.get("line"), "score": int(d["score"]),
                })
        except Exception as e:  # noqa: BLE001
            return out, f"eslint runner error: {e} :: {r.stderr[:200] if 'r' in dir() else ''}"
    return out, None


SOL_DIR = SCRIPT_DIR / "solidity"
# Threshold 1 = report every function solhint can score (it never reports
# functions whose cyclomatic complexity is exactly 1 — the rule minimum is 1
# and it only fires above the threshold).
SOLHINT_CFG = '{"rules": {"code-complexity": ["warn", 1]}}'
SOLHINT_MSG_RE = re.compile(r"cyclomatic complexity (\d+)")
SOL_FUNC_RE = re.compile(
    r"\b(?:function\s+([A-Za-z0-9_$]+)|(constructor)|(receive)|(fallback)"
    r"|modifier\s+([A-Za-z0-9_$]+))"
)


def _solhint_bin():
    local = SOL_DIR / "node_modules" / ".bin" / "solhint"
    return str(local) if local.exists() else shutil.which("solhint")


def _sol_func_name(path, line, cache):
    """Best-effort function name from the source line solhint points at."""
    if path not in cache:
        try:
            cache[path] = Path(path).read_text(errors="replace").splitlines()
        except OSError:
            cache[path] = []
    lines = cache[path]
    if line and 0 < line <= len(lines):
        m = SOL_FUNC_RE.search(lines[line - 1])
        if m:
            return next((g for g in m.groups() if g), None)
    return None


def _parse_solhint(stdout):
    """solhint --formatter json -> [{file,function,line,score}].

    Shape observed (solhint 6.x): a JSON array of
    {line,column,severity,message,ruleId,fix,filePath} entries plus a trailing
    {conclusion} element; parse errors carry no ruleId. filePath is relative
    to the subprocess cwd — we run with cwd="/" so it is the absolute path
    minus the leading separator.
    """
    recs = []
    for d in json.loads(stdout or "[]"):
        if d.get("ruleId") != "code-complexity":
            continue
        m = SOLHINT_MSG_RE.search(d.get("message", ""))
        if m:
            recs.append({"file": os.sep + d["filePath"], "function": None,
                         "line": d.get("line"), "score": int(m.group(1))})
    return recs


def run_solidity(files):
    """Score .sol files via solhint's code-complexity rule (CYCLOMATIC)."""
    solhint = _solhint_bin()
    if not solhint:
        return [], "solhint not installed (run setup.sh)"
    files = [str(Path(f).resolve()) for f in files]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        tf.write(SOLHINT_CFG)
        cfg = tf.name
    out, cache = [], {}
    try:
        for batch in chunked(files):
            # exit code 1 just means findings/parse errors — parse stdout anyway
            r = subprocess.run([solhint, "-c", cfg, "--formatter", "json", *batch],
                               capture_output=True, text=True, timeout=900, cwd=os.sep)
            for rec in _parse_solhint(r.stdout):
                rec["function"] = _sol_func_name(rec["file"], rec["line"], cache)
                out.append(rec)
    except Exception as e:  # noqa: BLE001
        return out, f"solhint error: {e}"
    finally:
        try:
            os.unlink(cfg)
        except OSError:
            pass
    return out, None


def run_sv(files):
    """Score .sv/.svh via scc — a per-FILE cyclomatic-style estimate.

    No open-source tool reports per-function/always-block complexity for
    SystemVerilog (verible-verilog-lint has no complexity rule; lizard and
    svlint don't cover it), so this is a clearly-labeled per-file proxy.
    """
    if not have("scc"):
        return [], "scc not installed (run setup.sh — e.g. brew install scc)"
    out = []
    files = [str(Path(f).resolve()) for f in files]
    for batch in chunked(files):
        try:
            r = subprocess.run(["scc", "--by-file", "--format", "json", *batch],
                               capture_output=True, text=True, timeout=600)
            for grp in json.loads(r.stdout or "[]"):
                for f in grp.get("Files", []):
                    out.append({"file": f.get("Location"), "function": "(whole file)",
                                "line": None, "score": int(f.get("Complexity", 0))})
        except Exception as e:  # noqa: BLE001
            return out, f"scc error: {e}"
    return out, None


CLANG_RE = re.compile(
    r"^(.*?):(\d+):(\d+): warning: function '([^']+)' has cognitive complexity of (\d+)"
)
CLANG_CFG = "{CheckOptions: [{key: readability-function-cognitive-complexity.Threshold, value: '0'}]}"


def _run_clang(files, std):
    out = []
    for batch in chunked(files, 60):
        r = subprocess.run(
            ["clang-tidy", *batch, "--quiet",
             "--checks=-*,readability-function-cognitive-complexity",
             f"-config={CLANG_CFG}", "--", f"-std={std}"],
            capture_output=True, text=True, timeout=1200,
        )
        for line in (r.stdout or "").splitlines():
            m = CLANG_RE.match(line)
            if m:
                out.append({
                    "file": m.group(1), "function": m.group(4),
                    "line": int(m.group(2)), "score": int(m.group(5)),
                })
    return out


def run_lizard(files, label):
    """Cyclomatic fallback (lizard). Clearly NOT cognitive complexity."""
    if not have("lizard"):
        return [], f"{label}: clang-tidy and lizard both missing (run setup.sh)"
    out = []
    for batch in chunked(files):
        r = subprocess.run(["lizard", "--csv", *batch],
                           capture_output=True, text=True, timeout=900)
        for row in (r.stdout or "").splitlines():
            cols = row.split(",")
            # lizard csv: nloc,ccn,token,param,length,location,file,name,long_name,start,end
            if len(cols) >= 8:
                try:
                    score = int(cols[1])
                except ValueError:
                    continue
                out.append({
                    "file": cols[6].strip('"'), "function": cols[7].strip('"'),
                    "line": int(cols[9]) if len(cols) > 9 and cols[9].isdigit() else None,
                    "score": score,
                })
    return out, None


def run_c_cpp(c_files, cpp_files, force_lizard):
    if force_lizard or not have("clang-tidy"):
        recs, err = run_lizard(c_files + cpp_files, "C/C++")
        return recs, "cyclomatic", err
    recs = []
    if c_files:
        recs += _run_clang(c_files, "c11")
    if cpp_files:
        recs += _run_clang(cpp_files, "c++17")
    return recs, "cognitive", None


# (language key, runner, metric label, honesty note printed when files matched)
RUNNERS = [
    ("python", run_python, "cognitive", None),
    ("go", run_go, "cognitive", None),
    ("ts", run_ts, "cognitive", None),
    ("solidity", run_solidity, "cyclomatic",
     "Solidity scored with solhint = CYCLOMATIC complexity (not cognitive); "
     "functions with complexity 1 are not reported by solhint."),
    ("sv", run_sv, "cyclomatic (per-file estimate)",
     "SystemVerilog scored with scc = per-FILE cyclomatic-style estimate "
     "(no open-source tool reports per-function complexity for SV)."),
]


def tag(recs, lang, metric):
    for r in recs:
        r["language"], r["metric"] = lang, metric
    return recs


def analyze(by_lang, force_lizard):
    """Run every applicable analyzer; return (records, warnings, metric_notes)."""
    records, warnings, notes = [], [], []
    for lang, runner, metric, note in RUNNERS:
        if not by_lang.get(lang):
            continue
        recs, err = runner(by_lang[lang])
        records += tag(recs, lang, metric)
        if err:
            warnings.append(err)
        if note and recs:
            notes.append(note)
    if by_lang.get("c") or by_lang.get("cpp"):
        recs, metric, err = run_c_cpp(by_lang.get("c", []), by_lang.get("cpp", []), force_lizard)
        records += tag(recs, "c/cpp", metric)
        if err:
            warnings.append(err)
        if metric == "cyclomatic":
            notes.append("C/C++ scored with lizard = CYCLOMATIC complexity (not cognitive). "
                         "Install clang-tidy for true cognitive scores.")
    return records, warnings, notes


# --- reporting --------------------------------------------------------------

def render(records, metric_note, top, threshold, warnings):
    shown = [r for r in records if r["score"] >= threshold]
    shown.sort(key=lambda r: r["score"], reverse=True)
    counts = defaultdict(int)
    for r in records:
        counts[band(r["score"])[0]] += 1
    total = len(records)

    print("\n  Cognitive Complexity Report")
    print("  " + "═" * 60)
    if not total:
        print("  No analyzable functions found.")
    else:
        worst = max(records, key=lambda r: r["score"])["score"]
        avg = sum(r["score"] for r in records) / total
        print(f"  Functions analyzed: {total}   avg: {avg:.1f}   worst: {worst}")
        print("  Distribution:")
        for lo, hi, name, emoji in BANDS:
            n = counts.get(name, 0)
            rng = f"{lo}-{hi}" if hi < 10**8 else f"{lo}+"
            bar = "█" * min(40, n)
            print(f"    {emoji} {name:<11} ({rng:>5}): {n:>4}  {bar}")

        print(f"\n  Top {min(top, len(shown))} most complex (threshold ≥ {threshold}):")
        print(f"    {'score':>5}  {'band':<10} {'function':<32} location")
        print("    " + "-" * 78)
        cwd = os.getcwd()
        for r in shown[:top]:
            name, emoji = band(r["score"])
            loc = r["file"] or "?"
            try:
                rel = os.path.relpath(loc, cwd)
                if not rel.startswith(".."):
                    loc = rel
            except (ValueError, TypeError):
                pass
            if r["line"]:
                loc += f":{r['line']}"
            fn = (r["function"] or "(anonymous)")[:32]
            print(f"    {r['score']:>5}  {emoji} {name:<8} {fn:<32} {loc}")
    if metric_note:
        print(f"\n  ⚠ {metric_note}")
    for w in warnings:
        print(f"  ⚠ {w}")
    print()


def main():
    ap = argparse.ArgumentParser(description="Cognitive complexity of a code folder.")
    ap.add_argument("paths", nargs="+", help="files or directories")
    ap.add_argument("--top", type=int, default=15, help="how many worst functions to list")
    ap.add_argument("--threshold", type=int, default=0, help="only list functions ≥ this score")
    ap.add_argument("--lang", help="restrict to languages "
                                   "(comma list: python,go,ts,c,cpp,solidity,sv)")
    ap.add_argument("--lizard", action="store_true", help="force lizard (cyclomatic) for C/C++")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    only = None
    if args.lang:
        only = {LANG_ALIASES.get(l.strip(), l.strip()) for l in args.lang.split(",")}
    by_lang = collect(args.paths, only)

    records, warnings, metric_notes = analyze(by_lang, args.lizard)

    if args.json:
        print(json.dumps({"records": records, "warnings": warnings}, indent=2))
        return 0

    render(records, " ".join(metric_notes), args.top, args.threshold, warnings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
