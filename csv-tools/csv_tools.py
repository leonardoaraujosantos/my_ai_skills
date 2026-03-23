#!/usr/bin/env python3
"""
CSV Tools - Manipulate CSV files from the command line.

Usage:
    python csv_tools.py <command> <file> [options]

Commands:
    info        Show CSV info (rows, columns, types)
    head        Show first N rows (default: 10)
    tail        Show last N rows (default: 10)
    columns     List column names
    stats       Show statistics for numeric columns
    filter      Filter rows by condition
    select      Select specific columns
    sort        Sort by column(s)
    to-json     Convert to JSON
    to-markdown Convert to Markdown table
    query       Run SQL-like query on CSV

Options:
    -n, --rows <n>      Number of rows for head/tail
    -c, --columns <cols> Column names (comma-separated)
    -w, --where <cond>   Filter condition (e.g., "age > 30")
    -s, --sort <col>     Sort by column
    --desc               Sort descending
    -o, --output <file>  Output file
    --no-header          CSV has no header row

Examples:
    python csv_tools.py info data.csv
    python csv_tools.py head data.csv -n 20
    python csv_tools.py filter data.csv -w "status == 'active'"
    python csv_tools.py select data.csv -c "name,email,phone"
    python csv_tools.py to-json data.csv -o data.json
    python csv_tools.py stats data.csv
"""

import sys
import csv
import json
import re
from pathlib import Path
from collections import defaultdict


def read_csv(file_path, has_header=True):
    """Read CSV file and return headers and rows."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return [], []

    if has_header:
        return rows[0], rows[1:]
    else:
        # Generate column names
        headers = [f"col_{i}" for i in range(len(rows[0]))]
        return headers, rows


def detect_type(value):
    """Detect the type of a value."""
    if value == '' or value is None:
        return 'empty'
    try:
        int(value)
        return 'int'
    except ValueError:
        pass
    try:
        float(value)
        return 'float'
    except ValueError:
        pass
    return 'string'


def cmd_info(file_path, has_header=True):
    """Show CSV file information."""
    headers, rows = read_csv(file_path, has_header)

    # Detect column types
    col_types = defaultdict(lambda: defaultdict(int))
    for row in rows[:100]:  # Sample first 100 rows
        for i, val in enumerate(row):
            if i < len(headers):
                col_types[headers[i]][detect_type(val)] += 1

    print(f"File: {file_path}")
    print(f"Rows: {len(rows)}")
    print(f"Columns: {len(headers)}")
    print("\nColumn Info:")
    print("-" * 50)

    for i, col in enumerate(headers):
        types = col_types[col]
        main_type = max(types.items(), key=lambda x: x[1])[0] if types else 'unknown'
        empty_count = types.get('empty', 0)
        print(f"  {i+1}. {col}: {main_type}" + (f" ({empty_count} empty)" if empty_count else ""))


def cmd_head(file_path, n=10, has_header=True):
    """Show first N rows."""
    headers, rows = read_csv(file_path, has_header)
    print_table(headers, rows[:n])


def cmd_tail(file_path, n=10, has_header=True):
    """Show last N rows."""
    headers, rows = read_csv(file_path, has_header)
    print_table(headers, rows[-n:])


def cmd_columns(file_path, has_header=True):
    """List column names."""
    headers, _ = read_csv(file_path, has_header)
    for i, col in enumerate(headers):
        print(f"{i+1}. {col}")


def cmd_stats(file_path, has_header=True):
    """Show statistics for numeric columns."""
    headers, rows = read_csv(file_path, has_header)

    # Find numeric columns
    numeric_cols = {}
    for i, col in enumerate(headers):
        values = []
        for row in rows:
            if i < len(row):
                try:
                    values.append(float(row[i]))
                except (ValueError, TypeError):
                    pass
        if len(values) > len(rows) * 0.5:  # At least 50% numeric
            numeric_cols[col] = values

    if not numeric_cols:
        print("No numeric columns found.")
        return

    print(f"{'Column':<20} {'Count':>10} {'Min':>12} {'Max':>12} {'Mean':>12} {'Sum':>15}")
    print("-" * 85)

    for col, values in numeric_cols.items():
        count = len(values)
        min_val = min(values)
        max_val = max(values)
        mean_val = sum(values) / count
        sum_val = sum(values)
        print(f"{col:<20} {count:>10} {min_val:>12.2f} {max_val:>12.2f} {mean_val:>12.2f} {sum_val:>15.2f}")


def cmd_filter(file_path, condition, has_header=True, output=None):
    """Filter rows by condition."""
    headers, rows = read_csv(file_path, has_header)

    # Parse condition (simple parser for: column op value)
    cond_match = re.match(r'(\w+)\s*(==|!=|>|<|>=|<=|contains)\s*["\']?([^"\']*)["\']?', condition)
    if not cond_match:
        print(f"Invalid condition: {condition}")
        return

    col_name, op, value = cond_match.groups()

    if col_name not in headers:
        print(f"Column not found: {col_name}")
        return

    col_idx = headers.index(col_name)

    # Filter rows
    filtered = []
    for row in rows:
        if col_idx >= len(row):
            continue
        cell = row[col_idx]

        try:
            if op == '==':
                passes = cell == value
            elif op == '!=':
                passes = cell != value
            elif op == '>':
                passes = float(cell) > float(value)
            elif op == '<':
                passes = float(cell) < float(value)
            elif op == '>=':
                passes = float(cell) >= float(value)
            elif op == '<=':
                passes = float(cell) <= float(value)
            elif op == 'contains':
                passes = value.lower() in cell.lower()
            else:
                passes = False

            if passes:
                filtered.append(row)
        except (ValueError, TypeError):
            continue

    if output:
        write_csv(output, headers, filtered)
        print(f"Filtered {len(filtered)} rows to {output}")
    else:
        print_table(headers, filtered)
        print(f"\n{len(filtered)} rows matched")


def cmd_select(file_path, columns, has_header=True, output=None):
    """Select specific columns."""
    headers, rows = read_csv(file_path, has_header)

    col_names = [c.strip() for c in columns.split(',')]
    col_indices = []

    for col in col_names:
        if col in headers:
            col_indices.append(headers.index(col))
        else:
            print(f"Column not found: {col}")
            return

    new_headers = [headers[i] for i in col_indices]
    new_rows = [[row[i] if i < len(row) else '' for i in col_indices] for row in rows]

    if output:
        write_csv(output, new_headers, new_rows)
        print(f"Selected {len(col_names)} columns to {output}")
    else:
        print_table(new_headers, new_rows[:20])
        if len(new_rows) > 20:
            print(f"\n... and {len(new_rows) - 20} more rows")


def cmd_sort(file_path, sort_col, descending=False, has_header=True, output=None):
    """Sort by column."""
    headers, rows = read_csv(file_path, has_header)

    if sort_col not in headers:
        print(f"Column not found: {sort_col}")
        return

    col_idx = headers.index(sort_col)

    def sort_key(row):
        if col_idx >= len(row):
            return (1, '')
        val = row[col_idx]
        try:
            return (0, float(val))
        except (ValueError, TypeError):
            return (1, val.lower())

    sorted_rows = sorted(rows, key=sort_key, reverse=descending)

    if output:
        write_csv(output, headers, sorted_rows)
        print(f"Sorted {len(sorted_rows)} rows to {output}")
    else:
        print_table(headers, sorted_rows[:20])
        if len(sorted_rows) > 20:
            print(f"\n... and {len(sorted_rows) - 20} more rows")


def cmd_to_json(file_path, has_header=True, output=None):
    """Convert to JSON."""
    headers, rows = read_csv(file_path, has_header)

    data = []
    for row in rows:
        obj = {}
        for i, col in enumerate(headers):
            obj[col] = row[i] if i < len(row) else ''
        data.append(obj)

    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"Converted {len(data)} rows to {output}")
    else:
        print(json_str)


def cmd_to_markdown(file_path, has_header=True, output=None):
    """Convert to Markdown table."""
    headers, rows = read_csv(file_path, has_header)

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows:
        cells = [row[i] if i < len(row) else '' for i in range(len(headers))]
        cells = [c.replace("|", "\\|") for c in cells]
        lines.append("| " + " | ".join(cells) + " |")

    md = "\n".join(lines)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"Converted {len(rows)} rows to {output}")
    else:
        print(md)


def write_csv(file_path, headers, rows):
    """Write CSV file."""
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def print_table(headers, rows, max_width=30):
    """Print a formatted table."""
    if not headers:
        return

    # Calculate column widths
    widths = [min(len(h), max_width) for h in headers]
    for row in rows[:50]:  # Sample first 50 rows
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], min(len(str(cell)), max_width))

    # Print header
    header_line = " | ".join(h[:widths[i]].ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row in rows:
        cells = []
        for i in range(len(headers)):
            cell = str(row[i]) if i < len(row) else ''
            cells.append(cell[:widths[i]].ljust(widths[i]))
        print(" | ".join(cells))


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        return

    cmd = sys.argv[1]

    if cmd == '--help':
        print_help()
        return

    if len(sys.argv) < 3:
        print("Error: Please provide a CSV file")
        return

    file_path = sys.argv[2]

    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        return

    # Parse arguments
    args = sys.argv[3:]
    n = 10
    columns = None
    where = None
    sort_col = None
    descending = False
    output = None
    has_header = True

    i = 0
    while i < len(args):
        if args[i] in ['-n', '--rows'] and i + 1 < len(args):
            n = int(args[i + 1])
            i += 2
        elif args[i] in ['-c', '--columns'] and i + 1 < len(args):
            columns = args[i + 1]
            i += 2
        elif args[i] in ['-w', '--where'] and i + 1 < len(args):
            where = args[i + 1]
            i += 2
        elif args[i] in ['-s', '--sort'] and i + 1 < len(args):
            sort_col = args[i + 1]
            i += 2
        elif args[i] == '--desc':
            descending = True
            i += 1
        elif args[i] in ['-o', '--output'] and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif args[i] == '--no-header':
            has_header = False
            i += 1
        else:
            i += 1

    # Execute command
    if cmd == 'info':
        cmd_info(file_path, has_header)
    elif cmd == 'head':
        cmd_head(file_path, n, has_header)
    elif cmd == 'tail':
        cmd_tail(file_path, n, has_header)
    elif cmd == 'columns':
        cmd_columns(file_path, has_header)
    elif cmd == 'stats':
        cmd_stats(file_path, has_header)
    elif cmd == 'filter':
        if not where:
            print("Error: -w/--where condition required")
            return
        cmd_filter(file_path, where, has_header, output)
    elif cmd == 'select':
        if not columns:
            print("Error: -c/--columns required")
            return
        cmd_select(file_path, columns, has_header, output)
    elif cmd == 'sort':
        if not sort_col:
            print("Error: -s/--sort column required")
            return
        cmd_sort(file_path, sort_col, descending, has_header, output)
    elif cmd == 'to-json':
        cmd_to_json(file_path, has_header, output)
    elif cmd == 'to-markdown':
        cmd_to_markdown(file_path, has_header, output)
    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
