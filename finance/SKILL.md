---
name: finance
description: Personal finance tracking from bank/card CSV exports — normalize statements into a local ledger, categorize spending by rules, and generate monthly reports. Use when the user says "import my bank statement", "categorize my spending", "monthly spending report", "where did my money go", or "finance report".
argument-hint: <command> [file.csv|month] [options]
---

# Finance

## Script Location

```bash
FIN="$HOME/.claude/skills/finance/scripts/finance.py"
```

## Storage

All data stays in `~/.claude/skills/finance/data/` (override with `--data-dir` or `FINANCE_DATA_DIR`): `profiles.json` (per-bank CSV column mappings), `rules.json` (categorization rules), `ledger.csv` (normalized ledger; ids are hashes of date+description+amount for dedup).

## Commands

| Command | Description |
|---------|-------------|
| `profile-add <name> --date-col X --desc-col Y --amount-col Z` | Save a bank's CSV mapping (columns by header name or 0-based index) |
| `profile-list` | List saved profiles |
| `import <file.csv> -p <profile> [--account name]` | Normalize into the ledger; dedup; auto-apply rules |
| `rules-add "<pattern>" <category> [--regex]` | Case-insensitive substring (or regex) rule on description |
| `rules-list` / `rules-delete <pattern>` | Manage rules |
| `categorize [--month YYYY-MM] [--force]` | Apply rules, then list remaining uncategorized transactions |
| `set-category <id> <category>` | One-off category assignment (id prefix ok) |
| `report [--month YYYY-MM \| --from D --to D] [--markdown]` | Income/expenses/net, spend by category with %, top merchants, vs previous month |
| `list [--month] [--category] [--uncategorized]` | Filtered transaction listing |

### profile-add options

`--date-format "%d/%m/%Y"` (strptime), `--decimal-comma` (1.234,56), `--invert` (bank exports expenses as positive), `--currency BRL`, `--encoding latin-1`, `--delimiter ";"`.

## Examples

```bash
# US-style bank (Date,Description,Amount; expenses negative)
python3 "$FIN" profile-add chase --date-col Date --desc-col Description --amount-col Amount

# Brazilian Nubank card export (DD/MM/YYYY, decimal comma, expenses positive)
python3 "$FIN" profile-add nubank --date-col data --desc-col descrição --amount-col valor \
  --date-format "%d/%m/%Y" --decimal-comma --invert --currency BRL --delimiter ";"

python3 "$FIN" import ~/Downloads/statement.csv -p nubank
python3 "$FIN" rules-add "uber" transport
python3 "$FIN" categorize --month 2026-07
python3 "$FIN" report --month 2026-07 --markdown
```

## Typical Workflow

1. **Import**: `import <file.csv> -p <profile>` (create the profile first if it's a new bank — inspect the CSV header to map columns).
2. **Categorize**: run `categorize`; for each uncategorized transaction, propose a category to the user. With confirmation, add recurring merchants as rules (`rules-add`) and use `set-category` for one-offs.
3. **Report**: `report --month YYYY-MM` and summarize the highlights (biggest categories, deltas vs previous month).
4. **Optionally save**: `report --month YYYY-MM --markdown` and store the note in the Obsidian vault via the obsidian skill, e.g. `Finance/2026-07.md`.

## Privacy

All transaction data stays local in the data dir. Never send transaction data, merchant names, or amounts to external services or web tools.
