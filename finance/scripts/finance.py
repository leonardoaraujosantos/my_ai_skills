#!/usr/bin/env python3
"""finance.py — personal finance tracking from bank/card CSV exports.

Normalizes bank CSVs into a local ledger, categorizes transactions by rules,
and produces spending reports. All data stays local.

Data dir (profiles.json, rules.json, ledger.csv):
  ~/.claude/skills/finance/data/  — override with --data-dir or FINANCE_DATA_DIR.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

LEDGER_FIELDS = ["date", "description", "amount", "currency", "account",
                 "category", "source_file", "id"]

# ─── Storage helpers ─────────────────────────────────────────────────────────

def die(msg, code=1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def get_data_dir(args):
    d = (args.data_dir or os.environ.get("FINANCE_DATA_DIR")
         or str(Path.home() / ".claude" / "skills" / "finance" / "data"))
    path = Path(d).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as e:
            die(f"corrupt JSON in {path}: {e}")
    return default


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def load_ledger(ddir):
    path = ddir / "ledger.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_ledger(ddir, rows):
    path = ddir / "ledger.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


# ─── Parsing helpers ─────────────────────────────────────────────────────────

def parse_amount(raw, decimal_comma=False):
    s = re.sub(r"[^\d,.\-+]", "", raw.strip())
    if decimal_comma:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"cannot parse amount {raw!r}")


def parse_date(raw, fmt):
    try:
        return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"date {raw!r} does not match format {fmt!r}")


def resolve_col(spec, header):
    """Column spec is a header name (case-insensitive) or a 0-based index."""
    if re.fullmatch(r"\d+", spec):
        idx = int(spec)
        if idx >= len(header):
            die(f"column index {idx} out of range (CSV has {len(header)} columns)")
        return idx
    lowered = [h.strip().lower() for h in header]
    key = spec.strip().lower()
    if key not in lowered:
        die(f"column '{spec}' not found in header: {header}")
    return lowered.index(key)


def validate_month(m):
    if not re.fullmatch(r"\d{4}-\d{2}", m):
        die(f"invalid month '{m}', expected YYYY-MM")
    return m


def prev_month(month):
    y, m = int(month[:4]), int(month[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def txn_id(date, desc, amount):
    return hashlib.sha1(f"{date}|{desc}|{amount:.2f}".encode()).hexdigest()[:12]


# ─── Rules ───────────────────────────────────────────────────────────────────

def rule_matches(rule, desc):
    if rule.get("regex"):
        return re.search(rule["pattern"], desc, re.IGNORECASE) is not None
    return rule["pattern"].lower() in desc.lower()


def match_category(desc, rules):
    for rule in rules:
        if rule_matches(rule, desc):
            return rule["category"]
    return None


def apply_rules(ledger, rules, force=False):
    changed = 0
    for txn in ledger:
        if txn["category"] and not force:
            continue
        cat = match_category(txn["description"], rules)
        if cat and cat != txn["category"]:
            txn["category"] = cat
            changed += 1
    return changed


# ─── Profile commands ────────────────────────────────────────────────────────

def cmd_profile_add(args):
    ddir = get_data_dir(args)
    pfile = ddir / "profiles.json"
    profiles = load_json(pfile, {})
    profiles[args.name] = {
        "date_col": args.date_col,
        "desc_col": args.desc_col,
        "amount_col": args.amount_col,
        "date_format": args.date_format,
        "decimal_comma": args.decimal_comma,
        "invert": args.invert,
        "currency": args.currency,
        "encoding": args.encoding,
        "delimiter": args.delimiter,
    }
    save_json(pfile, profiles)
    print(f"Profile '{args.name}' saved.")


def cmd_profile_list(args):
    ddir = get_data_dir(args)
    profiles = load_json(ddir / "profiles.json", {})
    if not profiles:
        print("No profiles. Add one with: profile-add <name> --date-col ... "
              "--desc-col ... --amount-col ...")
        return
    for name, p in profiles.items():
        flags = [f for f in ("decimal_comma", "invert") if p.get(f)]
        extra = f"  [{', '.join(flags)}]" if flags else ""
        print(f"{name}: date={p['date_col']} desc={p['desc_col']} "
              f"amount={p['amount_col']} fmt={p['date_format']} "
              f"{p['currency']} delim={p['delimiter']!r}{extra}")


# ─── Import ──────────────────────────────────────────────────────────────────

def read_csv_file(path, profile):
    try:
        with open(path, newline="", encoding=profile["encoding"]) as f:
            rows = list(csv.reader(f, delimiter=profile["delimiter"]))
    except (UnicodeDecodeError, OSError) as e:
        die(f"cannot read {path}: {e}")
    if len(rows) < 2:
        die(f"{path} has a header but no data rows")
    return rows[0], rows[1:]


def normalize_row(row, cols, profile, account, source):
    date = parse_date(row[cols["date"]], profile["date_format"])
    desc = row[cols["desc"]].strip()
    amount = parse_amount(row[cols["amount"]], profile["decimal_comma"])
    if profile["invert"]:
        amount = -amount
    return {
        "date": date,
        "description": desc,
        "amount": f"{amount:.2f}",
        "currency": profile["currency"],
        "account": account,
        "category": "",
        "source_file": source,
        "id": txn_id(date, desc, amount),
    }


def cmd_import(args):
    ddir = get_data_dir(args)
    profiles = load_json(ddir / "profiles.json", {})
    if args.profile not in profiles:
        die(f"profile '{args.profile}' not found. Available: "
            f"{', '.join(profiles) or '(none)'}. Use profile-add first.")
    profile = profiles[args.profile]
    path = Path(args.file)
    if not path.exists():
        die(f"file not found: {path}")

    header, raw_rows = read_csv_file(path, profile)
    cols = {k: resolve_col(profile[f"{k}_col"], header)
            for k in ("date", "desc", "amount")}
    ledger = load_ledger(ddir)
    known = {r["id"] for r in ledger}
    rules = load_json(ddir / "rules.json", [])
    account = args.account or args.profile

    imported = skipped = 0
    for lineno, row in enumerate(raw_rows, start=2):
        if not any(cell.strip() for cell in row):
            continue
        try:
            txn = normalize_row(row, cols, profile, account, path.name)
        except (ValueError, IndexError) as e:
            die(f"{path.name} line {lineno}: {e}")
        if txn["id"] in known:
            skipped += 1
            continue
        txn["category"] = match_category(txn["description"], rules) or ""
        ledger.append(txn)
        known.add(txn["id"])
        imported += 1

    save_ledger(ddir, ledger)
    uncat = sum(1 for r in ledger if not r["category"])
    print(f"Imported {imported} transaction(s), skipped {skipped} duplicate(s).")
    print(f"Uncategorized in ledger: {uncat}"
          + (" — run 'categorize' to review them." if uncat else ""))


# ─── Rules commands ──────────────────────────────────────────────────────────

def cmd_rules_add(args):
    ddir = get_data_dir(args)
    rfile = ddir / "rules.json"
    rules = load_json(rfile, [])
    if args.regex:
        try:
            re.compile(args.pattern)
        except re.error as e:
            die(f"invalid regex {args.pattern!r}: {e}")
    existing = next((r for r in rules if r["pattern"] == args.pattern), None)
    if existing:
        existing.update(category=args.category, regex=args.regex)
        verb = "updated"
    else:
        rules.append({"pattern": args.pattern, "category": args.category,
                      "regex": args.regex})
        verb = "added"
    save_json(rfile, rules)
    print(f"Rule {verb}: {args.pattern!r} -> {args.category}")


def cmd_rules_list(args):
    ddir = get_data_dir(args)
    rules = load_json(ddir / "rules.json", [])
    if not rules:
        print("No rules. Add one with: rules-add \"<pattern>\" <category>")
        return
    for r in rules:
        kind = "regex" if r.get("regex") else "substring"
        print(f"{r['pattern']!r:<40} -> {r['category']:<15} ({kind})")


def cmd_rules_delete(args):
    ddir = get_data_dir(args)
    rfile = ddir / "rules.json"
    rules = load_json(rfile, [])
    kept = [r for r in rules if r["pattern"] != args.pattern]
    if len(kept) == len(rules):
        die(f"no rule with pattern {args.pattern!r}")
    save_json(rfile, kept)
    print(f"Rule {args.pattern!r} deleted.")


# ─── Categorize ──────────────────────────────────────────────────────────────

def cmd_categorize(args):
    ddir = get_data_dir(args)
    ledger = load_ledger(ddir)
    rules = load_json(ddir / "rules.json", [])
    changed = apply_rules(ledger, rules, force=args.force)
    save_ledger(ddir, ledger)
    print(f"Categorized {changed} transaction(s) by rules.")

    remaining = [r for r in ledger if not r["category"]]
    if args.month:
        month = validate_month(args.month)
        remaining = [r for r in remaining if r["date"].startswith(month)]
    if not remaining:
        print("No uncategorized transactions remain.")
        return
    print(f"\n{len(remaining)} uncategorized transaction(s):")
    for r in sorted(remaining, key=lambda r: r["date"]):
        print(f"  {r['id']}  {r['date']}  {float(r['amount']):>10.2f}  "
              f"{r['description']}")
    print("\nAssign with: set-category <id> <category>  "
          "or add a rule: rules-add \"<pattern>\" <category>")


def cmd_set_category(args):
    ddir = get_data_dir(args)
    ledger = load_ledger(ddir)
    matches = [r for r in ledger if r["id"].startswith(args.id)]
    if not matches:
        die(f"no transaction with id '{args.id}'")
    if len(matches) > 1:
        die(f"id '{args.id}' is ambiguous ({len(matches)} matches)")
    txn = matches[0]
    txn["category"] = args.category
    save_ledger(ddir, ledger)
    print(f"Set {txn['id']} ({txn['description']}) -> {args.category}")


# ─── Report ──────────────────────────────────────────────────────────────────

def filter_period(ledger, month=None, date_from=None, date_to=None):
    rows = ledger
    if month:
        rows = [r for r in rows if r["date"].startswith(month)]
    if date_from:
        rows = [r for r in rows if r["date"] >= date_from]
    if date_to:
        rows = [r for r in rows if r["date"] <= date_to]
    return rows


def summarize(rows):
    income = expenses = 0.0
    by_cat, merchants = {}, {}
    for r in rows:
        amt = float(r["amount"])
        if amt >= 0:
            income += amt
            continue
        expenses += -amt
        cat = r["category"] or "(uncategorized)"
        by_cat[cat] = by_cat.get(cat, 0.0) - amt
        merchants[r["description"]] = merchants.get(r["description"], 0.0) - amt
    return {"income": income, "expenses": expenses, "net": income - expenses,
            "by_category": by_cat, "merchants": merchants}


def sorted_categories(summary):
    total = summary["expenses"] or 1.0
    return [(cat, amt, 100.0 * amt / total)
            for cat, amt in sorted(summary["by_category"].items(),
                                   key=lambda kv: -kv[1])]


def top_merchants(summary, n=10):
    return sorted(summary["merchants"].items(), key=lambda kv: -kv[1])[:n]


def category_deltas(cur, prev):
    cats = set(cur["by_category"]) | set(prev["by_category"])
    deltas = [(c, cur["by_category"].get(c, 0.0) - prev["by_category"].get(c, 0.0))
              for c in cats]
    return sorted((d for d in deltas if abs(d[1]) >= 0.005),
                  key=lambda kv: -abs(kv[1]))


def render_text(label, cur, prev, prev_label):
    out = [f"Finance report — {label}", "",
           f"  Income:   {cur['income']:>12.2f}",
           f"  Expenses: {cur['expenses']:>12.2f}",
           f"  Net:      {cur['net']:>12.2f}",
           "", "Spend by category:"]
    out += [f"  {c:<22} {a:>10.2f}  {p:5.1f}%" for c, a, p in sorted_categories(cur)]
    out += ["", "Top merchants:"]
    out += [f"  {m:<32} {a:>10.2f}" for m, a in top_merchants(cur)]
    if prev and prev["by_category"]:
        out += ["", f"vs {prev_label} (expense delta by category):"]
        out += [f"  {c:<22} {d:>+10.2f}" for c, d in category_deltas(cur, prev)]
    return "\n".join(out)


def render_markdown(label, cur, prev, prev_label):
    out = [f"# Finance Report — {label}", "",
           "| Metric | Amount |", "|---|---:|",
           f"| Income | {cur['income']:.2f} |",
           f"| Expenses | {cur['expenses']:.2f} |",
           f"| **Net** | **{cur['net']:.2f}** |",
           "", "## Spend by Category", "",
           "| Category | Amount | % |", "|---|---:|---:|"]
    out += [f"| {c} | {a:.2f} | {p:.1f}% |" for c, a, p in sorted_categories(cur)]
    out += ["", "## Top Merchants", "", "| Merchant | Amount |", "|---|---:|"]
    out += [f"| {m} | {a:.2f} |" for m, a in top_merchants(cur)]
    if prev and prev["by_category"]:
        out += ["", f"## vs {prev_label}", "",
                "| Category | Delta |", "|---|---:|"]
        out += [f"| {c} | {d:+.2f} |" for c, d in category_deltas(cur, prev)]
    return "\n".join(out)


def cmd_report(args):
    if args.month and (args.date_from or args.date_to):
        die("use either --month or --from/--to, not both")
    ddir = get_data_dir(args)
    ledger = load_ledger(ddir)
    month = validate_month(args.month) if args.month else None
    rows = filter_period(ledger, month, args.date_from, args.date_to)
    if not rows:
        die("no transactions in the selected period")

    label = month or f"{args.date_from or 'start'} .. {args.date_to or 'end'}"
    cur = summarize(rows)
    prev = prev_label = None
    if month:
        prev_label = prev_month(month)
        prev = summarize(filter_period(ledger, prev_label))
    render = render_markdown if args.markdown else render_text
    print(render(label, cur, prev, prev_label))


# ─── List ────────────────────────────────────────────────────────────────────

def cmd_list(args):
    ddir = get_data_dir(args)
    rows = load_ledger(ddir)
    if args.month:
        month = validate_month(args.month)
        rows = [r for r in rows if r["date"].startswith(month)]
    if args.category:
        rows = [r for r in rows if r["category"] == args.category]
    if args.uncategorized:
        rows = [r for r in rows if not r["category"]]
    if not rows:
        print("No matching transactions.")
        return
    for r in sorted(rows, key=lambda r: (r["date"], r["id"])):
        cat = r["category"] or "-"
        print(f"{r['id']}  {r['date']}  {float(r['amount']):>10.2f} "
              f"{r['currency']}  {cat:<15}  {r['description']}")
    print(f"\n{len(rows)} transaction(s).")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", help="Data directory (default: "
                        "~/.claude/skills/finance/data or $FINANCE_DATA_DIR)")

    parser = argparse.ArgumentParser(
        prog="finance.py",
        description="Personal finance tracking from bank/card CSV exports.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("profile-add", parents=[common],
                       help="Save a CSV column-mapping profile for a bank")
    p.add_argument("name")
    p.add_argument("--date-col", required=True,
                   help="Date column (header name or 0-based index)")
    p.add_argument("--desc-col", required=True, help="Description column")
    p.add_argument("--amount-col", required=True, help="Amount column")
    p.add_argument("--date-format", default="%Y-%m-%d",
                   help="strptime format (default: %%Y-%%m-%%d)")
    p.add_argument("--decimal-comma", action="store_true",
                   help="Amounts use comma as decimal separator (1.234,56)")
    p.add_argument("--invert", action="store_true",
                   help="Bank exports expenses as positive; flip signs")
    p.add_argument("--currency", default="USD")
    p.add_argument("--encoding", default="utf-8")
    p.add_argument("--delimiter", default=",")
    p.set_defaults(func=cmd_profile_add)

    p = sub.add_parser("profile-list", parents=[common], help="List profiles")
    p.set_defaults(func=cmd_profile_list)

    p = sub.add_parser("import", parents=[common],
                       help="Import a bank CSV into the ledger")
    p.add_argument("file")
    p.add_argument("-p", "--profile", required=True)
    p.add_argument("--account", help="Account label (default: profile name)")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("rules-add", parents=[common],
                       help="Add a categorization rule")
    p.add_argument("pattern")
    p.add_argument("category")
    p.add_argument("--regex", action="store_true",
                   help="Treat pattern as a regex (default: substring)")
    p.set_defaults(func=cmd_rules_add)

    p = sub.add_parser("rules-list", parents=[common], help="List rules")
    p.set_defaults(func=cmd_rules_list)

    p = sub.add_parser("rules-delete", parents=[common], help="Delete a rule")
    p.add_argument("pattern")
    p.set_defaults(func=cmd_rules_delete)

    p = sub.add_parser("categorize", parents=[common],
                       help="Apply rules, then list uncategorized transactions")
    p.add_argument("--month", help="Limit the uncategorized listing to YYYY-MM")
    p.add_argument("--force", action="store_true",
                   help="Re-apply rules to already-categorized transactions too")
    p.set_defaults(func=cmd_categorize)

    p = sub.add_parser("set-category", parents=[common],
                       help="Set the category of one transaction by id")
    p.add_argument("id", help="Transaction id (prefix accepted if unambiguous)")
    p.add_argument("category")
    p.set_defaults(func=cmd_set_category)

    p = sub.add_parser("report", parents=[common],
                       help="Income/expense report with category breakdown")
    p.add_argument("--month", help="YYYY-MM (enables previous-month comparison)")
    p.add_argument("--from", dest="date_from", help="Start date YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", help="End date YYYY-MM-DD")
    p.add_argument("--markdown", action="store_true",
                   help="Emit an Obsidian-ready markdown note")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("list", parents=[common], help="List transactions")
    p.add_argument("--month", help="YYYY-MM")
    p.add_argument("--category")
    p.add_argument("--uncategorized", action="store_true")
    p.set_defaults(func=cmd_list)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
