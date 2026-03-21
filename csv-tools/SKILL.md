---
name: csv-tools
description: Manipulate CSV files - view, filter, sort, convert to JSON/Markdown, get statistics. Use when working with CSV data files.
argument-hint: <command> <file.csv> [options]
---

# CSV Tools

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/csv-tools"
```

## Commands

```bash
python3 "$SKILL_DIR/csv_tools.py" <command> <file.csv> [options]
```

| Command | Description |
|---------|-------------|
| `info` | Show file info (rows, columns, types) |
| `head` | Show first N rows |
| `tail` | Show last N rows |
| `columns` | List column names |
| `stats` | Statistics for numeric columns |
| `filter` | Filter rows by condition |
| `select` | Select specific columns |
| `sort` | Sort by column |
| `to-json` | Convert to JSON |
| `to-markdown` | Convert to Markdown table |

## Options

| Option | Description |
|--------|-------------|
| `-n, --rows <n>` | Number of rows (head/tail) |
| `-c, --columns <cols>` | Column names (comma-separated) |
| `-w, --where <cond>` | Filter condition |
| `-s, --sort <col>` | Sort column |
| `--desc` | Sort descending |
| `-o, --output <file>` | Output file |
| `--no-header` | CSV has no header |

## Filter Operators

`==`, `!=`, `>`, `<`, `>=`, `<=`, `contains`

## Examples

```bash
# View info
python3 "$SKILL_DIR/csv_tools.py" info data.csv

# First 20 rows
python3 "$SKILL_DIR/csv_tools.py" head data.csv -n 20

# Filter rows
python3 "$SKILL_DIR/csv_tools.py" filter data.csv -w "status == 'active'"
python3 "$SKILL_DIR/csv_tools.py" filter data.csv -w "age > 30"
python3 "$SKILL_DIR/csv_tools.py" filter data.csv -w "name contains 'John'"

# Select columns
python3 "$SKILL_DIR/csv_tools.py" select data.csv -c "name,email,phone"

# Sort
python3 "$SKILL_DIR/csv_tools.py" sort data.csv -s "date" --desc

# Convert
python3 "$SKILL_DIR/csv_tools.py" to-json data.csv -o data.json
python3 "$SKILL_DIR/csv_tools.py" to-markdown data.csv

# Statistics
python3 "$SKILL_DIR/csv_tools.py" stats sales.csv
```
