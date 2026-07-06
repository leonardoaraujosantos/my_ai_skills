# Obsidian CLI Reference

> Config variables used below (`$OBSIDIAN_VAULT`, `$OBSIDIAN_VAULT_NAME`, `$OBSIDIAN_ICLOUD`, `$CLI`) are defined in the obsidian skill's [SKILL.md](../SKILL.md#configuration).

## CLI Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian create name="My Note" silent overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

## File Targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

## Vault Targeting

Commands target the most recently focused vault by default. Use `vault=<name>` as the first parameter:

```bash
obsidian vault="$OBSIDIAN_VAULT_NAME" search query="test"
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `silent` | Prevent files from opening in UI |
| `--copy` | Copy command output to clipboard |
| `total` | Return a count on list commands |
| `overwrite` | Allow overwriting existing files on create |

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Search vault | `$CLI search vault="$OBSIDIAN_VAULT_NAME" query="keyword"` |
| Search with context | `$CLI search:context vault="$OBSIDIAN_VAULT_NAME" query="keyword" limit=10` |
| Read file | `$CLI read vault="$OBSIDIAN_VAULT_NAME" file="NoteName"` |
| Read by path | `$CLI read vault="$OBSIDIAN_VAULT_NAME" path="Folder/Note.md"` |
| List files | `$CLI files vault="$OBSIDIAN_VAULT_NAME"` |
| List folders | `$CLI folders vault="$OBSIDIAN_VAULT_NAME"` |
| List tags | `$CLI tags vault="$OBSIDIAN_VAULT_NAME" counts` |
| Vault info | `$CLI vault vault="$OBSIDIAN_VAULT_NAME"` |
| Recent files | `$CLI recents vault="$OBSIDIAN_VAULT_NAME"` |
| Random note | `$CLI random:read vault="$OBSIDIAN_VAULT_NAME"` |

Run `obsidian help` at any time for the full, up-to-date command list.

## Reading Notes

### Using CLI (preferred for search)
```bash
# Search for content
/Applications/Obsidian.app/Contents/MacOS/Obsidian search vault="$OBSIDIAN_VAULT_NAME" query="kubernetes"

# Search with context (shows matching lines)
/Applications/Obsidian.app/Contents/MacOS/Obsidian search:context vault="$OBSIDIAN_VAULT_NAME" query="kubernetes" limit=10

# Read by name (wikilink style)
/Applications/Obsidian.app/Contents/MacOS/Obsidian read vault="$OBSIDIAN_VAULT_NAME" file="Python"

# Read by path
/Applications/Obsidian.app/Contents/MacOS/Obsidian read vault="$OBSIDIAN_VAULT_NAME" path="Programming/Python.md"
```

### Using File Tools (for editing)
```bash
# Read a specific file
Read: $OBSIDIAN_VAULT/Programming/Python/Python.md

# Search for files by pattern
Glob: $OBSIDIAN_VAULT/**/*.md

# Search for content
Grep: pattern="kubernetes" path="$OBSIDIAN_VAULT"
```

## Writing/Creating Notes

Use Write or Edit tools on the **GitHub repo**, then sync:

```bash
# Create new file
Write: $OBSIDIAN_VAULT/Programming/NewNote.md

# Edit existing file
Edit: $OBSIDIAN_VAULT/Programming/Python/Python.md
```

## Links & Backlinks

```bash
# List backlinks to a file
/Applications/Obsidian.app/Contents/MacOS/Obsidian backlinks vault="$OBSIDIAN_VAULT_NAME" file="Python"

# List outgoing links
/Applications/Obsidian.app/Contents/MacOS/Obsidian links vault="$OBSIDIAN_VAULT_NAME" file="Python"

# Get note outline (headings)
/Applications/Obsidian.app/Contents/MacOS/Obsidian outline vault="$OBSIDIAN_VAULT_NAME" file="Python"
```

## Vault Health Checks

```bash
# Orphan notes (no incoming links)
/Applications/Obsidian.app/Contents/MacOS/Obsidian orphans vault="$OBSIDIAN_VAULT_NAME"

# Dead-end notes (no outgoing links)
/Applications/Obsidian.app/Contents/MacOS/Obsidian deadends vault="$OBSIDIAN_VAULT_NAME"

# Broken/unresolved links
/Applications/Obsidian.app/Contents/MacOS/Obsidian unresolved vault="$OBSIDIAN_VAULT_NAME" verbose
/Applications/Obsidian.app/Contents/MacOS/Obsidian unresolved vault="$OBSIDIAN_VAULT_NAME" counts
```

## Tasks

```bash
# List all tasks
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="$OBSIDIAN_VAULT_NAME"

# Incomplete
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="$OBSIDIAN_VAULT_NAME" todo

# Completed
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="$OBSIDIAN_VAULT_NAME" done

# Tasks from daily note
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="$OBSIDIAN_VAULT_NAME" daily

# Toggle a task
/Applications/Obsidian.app/Contents/MacOS/Obsidian task vault="$OBSIDIAN_VAULT_NAME" file="MyNote" line=5 toggle
```

## Daily Notes

Daily notes are stored in: `Journal/Daily/YYYY-MM/YYYY-MM-DD.md`

```bash
# Read today's daily note
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:read vault="$OBSIDIAN_VAULT_NAME"

# Append to daily note
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:append vault="$OBSIDIAN_VAULT_NAME" content="- [ ] New task"

# Get daily note path
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:path vault="$OBSIDIAN_VAULT_NAME"
```

## Properties (Frontmatter) via CLI

```bash
# List all properties in vault
/Applications/Obsidian.app/Contents/MacOS/Obsidian properties vault="$OBSIDIAN_VAULT_NAME" counts

# Read property from file
/Applications/Obsidian.app/Contents/MacOS/Obsidian property:read vault="$OBSIDIAN_VAULT_NAME" file="Python" name="tags"

# Set property on file
/Applications/Obsidian.app/Contents/MacOS/Obsidian property:set vault="$OBSIDIAN_VAULT_NAME" file="Python" name="status" value="reviewed"
```

## Templates

```bash
# List templates
/Applications/Obsidian.app/Contents/MacOS/Obsidian templates vault="$OBSIDIAN_VAULT_NAME"

# Read template
/Applications/Obsidian.app/Contents/MacOS/Obsidian template:read vault="$OBSIDIAN_VAULT_NAME" name="Meeting"

# Create with template
/Applications/Obsidian.app/Contents/MacOS/Obsidian create vault="$OBSIDIAN_VAULT_NAME" name="Meeting Notes" template="Meeting"
```

## Plugin & Theme Development

When making code changes to a plugin or theme, follow this develop/test cycle:

1. **Reload** the plugin to pick up changes:
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **Check for errors** — if errors appear, fix and repeat:
   ```bash
   obsidian dev:errors
   ```
3. **Verify visually** with a screenshot or DOM inspection:
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **Check console output** for warnings/logs:
   ```bash
   obsidian dev:console level=error
   ```

### Additional Developer Commands

Run JavaScript in the app context:

```bash
obsidian eval code="app.vault.getFiles().length"
```

Inspect CSS values:

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

Toggle mobile emulation:

```bash
obsidian dev:mobile on
```

Run `obsidian help` for additional developer commands (CDP, debugger controls).

---
