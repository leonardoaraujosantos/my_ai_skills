---
name: json-tools
description: Manipulate JSON - format, validate, query, diff, merge, convert to CSV/YAML. Use when working with JSON files.
argument-hint: <command> <file> [options]
---

# JSON Tools

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/json-tools"
```

## Commands

```bash
python3 "$SKILL_DIR/json_tools.py" <command> <file> [options]
```

| Command | Description |
|---------|-------------|
| `info` | Show JSON info (structure, types, counts) |
| `format` | Pretty print JSON |
| `minify` | Minify (remove whitespace) |
| `validate` | Validate JSON syntax |
| `keys` | List all keys with paths |
| `query` | Query value at path |
| `set` | Set value at path |
| `delete` | Delete key at path |
| `diff` | Compare two JSON files |
| `merge` | Merge multiple files |
| `to-csv` | Convert array to CSV |
| `to-yaml` | Convert to YAML |
| `flatten` | Flatten nested structure |

## Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output file |
| `-p, --path <path>` | JSON path (e.g., "data.users[0].name") |
| `-v, --value <value>` | Value to set |
| `-i, --indent <n>` | Indentation (default: 2) |
| `--sort-keys` | Sort keys alphabetically |

## Path Syntax

Use dot notation and brackets:
- `name` - top-level key
- `data.users` - nested key
- `users[0]` - array index
- `data.users[0].name` - combined

## Examples

```bash
# View JSON info
python3 "$SKILL_DIR/json_tools.py" info data.json

# Pretty print
python3 "$SKILL_DIR/json_tools.py" format data.json -o pretty.json

# Minify
python3 "$SKILL_DIR/json_tools.py" minify data.json -o min.json

# Validate
python3 "$SKILL_DIR/json_tools.py" validate data.json

# List all keys
python3 "$SKILL_DIR/json_tools.py" keys data.json

# Query specific path
python3 "$SKILL_DIR/json_tools.py" query data.json -p "users[0].email"

# Set value
python3 "$SKILL_DIR/json_tools.py" set config.json -p "debug" -v "true" -o config.json

# Delete key
python3 "$SKILL_DIR/json_tools.py" delete data.json -p "temp_field" -o data.json

# Compare files
python3 "$SKILL_DIR/json_tools.py" diff old.json new.json

# Merge files
python3 "$SKILL_DIR/json_tools.py" merge a.json b.json c.json -o combined.json

# Convert to CSV
python3 "$SKILL_DIR/json_tools.py" to-csv users.json -o users.csv

# Convert to YAML (requires pyyaml)
python3 "$SKILL_DIR/json_tools.py" to-yaml config.json -o config.yaml

# Flatten nested JSON
python3 "$SKILL_DIR/json_tools.py" flatten nested.json -o flat.json
```

## Optional Dependencies

```bash
pip install pyyaml  # For YAML conversion
```
