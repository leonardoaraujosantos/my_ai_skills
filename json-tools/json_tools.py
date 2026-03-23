#!/usr/bin/env python3
"""
JSON Tools - Manipulate JSON files from the command line.

Usage:
    python json_tools.py <command> <file> [options]

Commands:
    info        Show JSON info (structure, size, keys)
    format      Pretty print / format JSON
    minify      Minify JSON (remove whitespace)
    validate    Validate JSON syntax
    keys        List all keys (with paths)
    query       Query JSON with path (e.g., "data.users[0].name")
    get         Get value at path
    set         Set value at path
    delete      Delete key at path
    diff        Compare two JSON files
    merge       Merge multiple JSON files
    to-csv      Convert JSON array to CSV
    to-yaml     Convert to YAML
    flatten     Flatten nested structure
    unflatten   Unflatten to nested structure

Options:
    -o, --output <file>     Output file
    -p, --path <path>       JSON path (e.g., "data.items[0]")
    -v, --value <value>     Value to set
    -i, --indent <n>        Indentation spaces (default: 2)
    --sort-keys             Sort keys alphabetically
    --compact               Compact output for arrays

Examples:
    python json_tools.py info data.json
    python json_tools.py format data.json -o pretty.json
    python json_tools.py query data.json -p "users[0].name"
    python json_tools.py keys data.json
    python json_tools.py diff file1.json file2.json
    python json_tools.py merge a.json b.json -o combined.json
    python json_tools.py to-csv data.json -o data.csv
    python json_tools.py set data.json -p "config.debug" -v true
"""

import sys
import json
import re
import csv
from pathlib import Path


def format_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_type_name(value):
    """Get human-readable type name."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return f"array[{len(value)}]"
    elif isinstance(value, dict):
        return f"object{{{len(value)}}}"
    return type(value).__name__


def count_elements(data, counts=None):
    """Count elements by type recursively."""
    if counts is None:
        counts = {'objects': 0, 'arrays': 0, 'strings': 0, 'numbers': 0, 'booleans': 0, 'nulls': 0}

    if isinstance(data, dict):
        counts['objects'] += 1
        for v in data.values():
            count_elements(v, counts)
    elif isinstance(data, list):
        counts['arrays'] += 1
        for item in data:
            count_elements(item, counts)
    elif isinstance(data, str):
        counts['strings'] += 1
    elif isinstance(data, bool):
        counts['booleans'] += 1
    elif isinstance(data, (int, float)):
        counts['numbers'] += 1
    elif data is None:
        counts['nulls'] += 1

    return counts


def parse_path(path_str):
    """Parse JSON path string into list of keys/indices."""
    parts = []
    # Handle dot notation and bracket notation
    tokens = re.findall(r'([^.\[\]]+)|\[(\d+)\]|\[([\'"])(.*?)\3\]', path_str)

    for token in tokens:
        if token[0]:  # Regular key
            parts.append(token[0])
        elif token[1]:  # Array index
            parts.append(int(token[1]))
        elif token[3]:  # Quoted key
            parts.append(token[3])

    return parts


def get_at_path(data, path_str):
    """Get value at JSON path."""
    if not path_str:
        return data

    parts = parse_path(path_str)
    current = data

    for part in parts:
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                raise KeyError(f"Key not found: {part}")
        elif isinstance(current, list):
            if isinstance(part, int) and 0 <= part < len(current):
                current = current[part]
            else:
                raise IndexError(f"Index out of range: {part}")
        else:
            raise TypeError(f"Cannot index into {type(current).__name__}")

    return current


def set_at_path(data, path_str, value):
    """Set value at JSON path."""
    parts = parse_path(path_str)

    if not parts:
        return value

    current = data
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                # Create intermediate dict or list
                next_part = parts[parts.index(part) + 1]
                current[part] = [] if isinstance(next_part, int) else {}
            current = current[part]
        elif isinstance(current, list):
            while len(current) <= part:
                current.append({})
            current = current[part]

    last_part = parts[-1]
    if isinstance(current, dict):
        current[last_part] = value
    elif isinstance(current, list):
        while len(current) <= last_part:
            current.append(None)
        current[last_part] = value

    return data


def delete_at_path(data, path_str):
    """Delete key at JSON path."""
    parts = parse_path(path_str)

    if not parts:
        return None

    current = data
    for part in parts[:-1]:
        if isinstance(current, dict):
            current = current.get(part, {})
        elif isinstance(current, list):
            current = current[part] if 0 <= part < len(current) else {}

    last_part = parts[-1]
    if isinstance(current, dict) and last_part in current:
        del current[last_part]
    elif isinstance(current, list) and 0 <= last_part < len(current):
        del current[last_part]

    return data


def flatten_json(data, parent_key='', sep='.'):
    """Flatten nested JSON into flat dictionary."""
    items = []

    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_json(v, new_key, sep).items())
    elif isinstance(data, list):
        for i, v in enumerate(data):
            new_key = f"{parent_key}[{i}]"
            items.extend(flatten_json(v, new_key, sep).items())
    else:
        items.append((parent_key, data))

    return dict(items)


def unflatten_json(data, sep='.'):
    """Unflatten flat dictionary into nested JSON."""
    result = {}

    for key, value in data.items():
        parts = parse_path(key)
        current = result

        for i, part in enumerate(parts[:-1]):
            next_part = parts[i + 1]

            if isinstance(part, int):
                while len(current) <= part:
                    current.append({} if not isinstance(next_part, int) else [])
                if current[part] is None or (isinstance(current[part], dict) and not current[part]):
                    current[part] = [] if isinstance(next_part, int) else {}
                current = current[part]
            else:
                if part not in current:
                    current[part] = [] if isinstance(next_part, int) else {}
                current = current[part]

        last_part = parts[-1]
        if isinstance(last_part, int):
            while len(current) <= last_part:
                current.append(None)
            current[last_part] = value
        else:
            current[last_part] = value

    return result


def get_all_keys(data, prefix=''):
    """Get all keys with their paths."""
    keys = []

    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{prefix}.{k}" if prefix else k
            keys.append((path, get_type_name(v)))
            keys.extend(get_all_keys(v, path))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            path = f"{prefix}[{i}]"
            keys.append((path, get_type_name(v)))
            keys.extend(get_all_keys(v, path))

    return keys


def json_diff(obj1, obj2, path=''):
    """Compare two JSON objects and return differences."""
    diffs = []

    if type(obj1) != type(obj2):
        diffs.append(('type_change', path, get_type_name(obj1), get_type_name(obj2)))
        return diffs

    if isinstance(obj1, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        for key in all_keys:
            new_path = f"{path}.{key}" if path else key
            if key not in obj1:
                diffs.append(('added', new_path, None, obj2[key]))
            elif key not in obj2:
                diffs.append(('removed', new_path, obj1[key], None))
            else:
                diffs.extend(json_diff(obj1[key], obj2[key], new_path))

    elif isinstance(obj1, list):
        max_len = max(len(obj1), len(obj2))
        for i in range(max_len):
            new_path = f"{path}[{i}]"
            if i >= len(obj1):
                diffs.append(('added', new_path, None, obj2[i]))
            elif i >= len(obj2):
                diffs.append(('removed', new_path, obj1[i], None))
            else:
                diffs.extend(json_diff(obj1[i], obj2[i], new_path))

    else:
        if obj1 != obj2:
            diffs.append(('changed', path, obj1, obj2))

    return diffs


def load_json(filepath):
    """Load JSON from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return None
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return None


def cmd_info(filepath):
    """Show JSON information."""
    path = Path(filepath)
    data = load_json(filepath)
    if data is None:
        return

    print(f"File:       {path.name}")
    print(f"Size:       {format_size(path.stat().st_size)}")
    print(f"Root Type:  {get_type_name(data)}")

    counts = count_elements(data)
    print(f"\nElement Counts:")
    print(f"  Objects:  {counts['objects']}")
    print(f"  Arrays:   {counts['arrays']}")
    print(f"  Strings:  {counts['strings']}")
    print(f"  Numbers:  {counts['numbers']}")
    print(f"  Booleans: {counts['booleans']}")
    print(f"  Nulls:    {counts['nulls']}")

    if isinstance(data, dict):
        print(f"\nTop-level Keys ({len(data)}):")
        for key in list(data.keys())[:10]:
            print(f"  {key}: {get_type_name(data[key])}")
        if len(data) > 10:
            print(f"  ... and {len(data) - 10} more")
    elif isinstance(data, list):
        print(f"\nArray Length: {len(data)}")
        if data:
            print(f"First Element Type: {get_type_name(data[0])}")


def cmd_format(filepath, output, indent=2, sort_keys=False):
    """Pretty print JSON."""
    data = load_json(filepath)
    if data is None:
        return

    formatted = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)

    if output:
        Path(output).write_text(formatted, encoding='utf-8')
        print(f"Formatted JSON saved to: {output}")
    else:
        print(formatted)


def cmd_minify(filepath, output):
    """Minify JSON."""
    data = load_json(filepath)
    if data is None:
        return

    minified = json.dumps(data, separators=(',', ':'), ensure_ascii=False)

    if output:
        Path(output).write_text(minified, encoding='utf-8')
        original_size = Path(filepath).stat().st_size
        new_size = len(minified.encode('utf-8'))
        print(f"Minified: {format_size(original_size)} -> {format_size(new_size)}")
        print(f"Saved to: {output}")
    else:
        print(minified)


def cmd_validate(filepath):
    """Validate JSON syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"Valid JSON: {filepath}")
        return True
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {filepath}")
        print(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")
        return False
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return False


def cmd_keys(filepath, max_depth=None):
    """List all keys."""
    data = load_json(filepath)
    if data is None:
        return

    keys = get_all_keys(data)

    print(f"Keys in {filepath}:\n")
    for path, type_name in keys[:100]:  # Limit output
        depth = path.count('.') + path.count('[')
        if max_depth is None or depth <= max_depth:
            print(f"  {path}: {type_name}")

    if len(keys) > 100:
        print(f"\n  ... and {len(keys) - 100} more keys")


def cmd_query(filepath, path):
    """Query JSON at path."""
    data = load_json(filepath)
    if data is None:
        return

    try:
        result = get_at_path(data, path)
        if isinstance(result, (dict, list)):
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error: {e}")


def cmd_set(filepath, path, value, output):
    """Set value at path."""
    data = load_json(filepath)
    if data is None:
        return

    # Parse value as JSON if possible
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    set_at_path(data, path, parsed_value)

    output = output or filepath
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Set {path} = {json.dumps(parsed_value)}")
    print(f"Saved to: {output}")


def cmd_delete(filepath, path, output):
    """Delete key at path."""
    data = load_json(filepath)
    if data is None:
        return

    delete_at_path(data, path)

    output = output or filepath
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Deleted: {path}")
    print(f"Saved to: {output}")


def cmd_diff(file1, file2):
    """Compare two JSON files."""
    data1 = load_json(file1)
    data2 = load_json(file2)

    if data1 is None or data2 is None:
        return

    diffs = json_diff(data1, data2)

    if not diffs:
        print("Files are identical")
        return

    print(f"Differences between {file1} and {file2}:\n")

    for diff_type, path, old_val, new_val in diffs:
        if diff_type == 'added':
            print(f"  + {path}: {json.dumps(new_val)}")
        elif diff_type == 'removed':
            print(f"  - {path}: {json.dumps(old_val)}")
        elif diff_type == 'changed':
            print(f"  ~ {path}: {json.dumps(old_val)} -> {json.dumps(new_val)}")
        elif diff_type == 'type_change':
            print(f"  ! {path}: type changed from {old_val} to {new_val}")

    print(f"\nTotal: {len(diffs)} difference(s)")


def cmd_merge(files, output):
    """Merge multiple JSON files."""
    if len(files) < 2:
        print("Error: Need at least 2 files to merge")
        return

    result = {}

    for filepath in files:
        data = load_json(filepath)
        if data is None:
            return

        if isinstance(data, dict):
            result.update(data)
        elif isinstance(data, list):
            if isinstance(result, dict) and not result:
                result = []
            if isinstance(result, list):
                result.extend(data)
            else:
                print(f"Warning: Cannot merge array into object, skipping {filepath}")

    output = output or "merged.json"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Merged {len(files)} files to: {output}")


def cmd_to_csv(filepath, output):
    """Convert JSON array to CSV."""
    data = load_json(filepath)
    if data is None:
        return

    if not isinstance(data, list):
        print("Error: JSON must be an array of objects for CSV conversion")
        return

    if not data:
        print("Error: Empty array")
        return

    # Get all unique keys
    all_keys = set()
    for item in data:
        if isinstance(item, dict):
            all_keys.update(item.keys())

    fieldnames = sorted(all_keys)

    output = output or Path(filepath).stem + ".csv"

    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            if isinstance(item, dict):
                # Convert complex values to JSON strings
                row = {}
                for k, v in item.items():
                    if isinstance(v, (dict, list)):
                        row[k] = json.dumps(v)
                    else:
                        row[k] = v
                writer.writerow(row)

    print(f"Converted {len(data)} rows to: {output}")


def cmd_to_yaml(filepath, output):
    """Convert to YAML."""
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML not installed. Run: pip install pyyaml")
        return

    data = load_json(filepath)
    if data is None:
        return

    yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    output = output or Path(filepath).stem + ".yaml"
    Path(output).write_text(yaml_str, encoding='utf-8')

    print(f"Converted to YAML: {output}")


def cmd_flatten(filepath, output):
    """Flatten nested JSON."""
    data = load_json(filepath)
    if data is None:
        return

    flattened = flatten_json(data)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(flattened, f, indent=2, ensure_ascii=False)
        print(f"Flattened to: {output}")
    else:
        print(json.dumps(flattened, indent=2, ensure_ascii=False))


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Parse arguments
    files = []
    output = None
    path = None
    value = None
    indent = 2
    sort_keys = False

    i = 0
    while i < len(args):
        if args[i] in ['-o', '--output'] and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif args[i] in ['-p', '--path'] and i + 1 < len(args):
            path = args[i + 1]
            i += 2
        elif args[i] in ['-v', '--value'] and i + 1 < len(args):
            value = args[i + 1]
            i += 2
        elif args[i] in ['-i', '--indent'] and i + 1 < len(args):
            indent = int(args[i + 1])
            i += 2
        elif args[i] == '--sort-keys':
            sort_keys = True
            i += 1
        elif not args[i].startswith('-'):
            files.append(args[i])
            i += 1
        else:
            i += 1

    # Execute command
    if cmd == 'info':
        if files:
            cmd_info(files[0])
        else:
            print("Error: JSON file required")

    elif cmd == 'format':
        if files:
            cmd_format(files[0], output, indent, sort_keys)
        else:
            print("Error: JSON file required")

    elif cmd == 'minify':
        if files:
            cmd_minify(files[0], output)
        else:
            print("Error: JSON file required")

    elif cmd == 'validate':
        if files:
            cmd_validate(files[0])
        else:
            print("Error: JSON file required")

    elif cmd == 'keys':
        if files:
            cmd_keys(files[0])
        else:
            print("Error: JSON file required")

    elif cmd in ['query', 'get']:
        if files and path:
            cmd_query(files[0], path)
        else:
            print("Error: JSON file and path required")

    elif cmd == 'set':
        if files and path and value is not None:
            cmd_set(files[0], path, value, output)
        else:
            print("Error: JSON file, path, and value required")

    elif cmd == 'delete':
        if files and path:
            cmd_delete(files[0], path, output)
        else:
            print("Error: JSON file and path required")

    elif cmd == 'diff':
        if len(files) >= 2:
            cmd_diff(files[0], files[1])
        else:
            print("Error: Two JSON files required")

    elif cmd == 'merge':
        cmd_merge(files, output)

    elif cmd == 'to-csv':
        if files:
            cmd_to_csv(files[0], output)
        else:
            print("Error: JSON file required")

    elif cmd == 'to-yaml':
        if files:
            cmd_to_yaml(files[0], output)
        else:
            print("Error: JSON file required")

    elif cmd == 'flatten':
        if files:
            cmd_flatten(files[0], output)
        else:
            print("Error: JSON file required")

    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
