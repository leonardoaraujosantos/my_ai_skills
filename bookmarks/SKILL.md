---
name: bookmarks
description: Save and manage bookmarks in Obsidian vault. Automatically fetches page title and description. Use when you want to save URLs for later.
argument-hint: <command> [options]
---

# Bookmarks

Save URLs to Obsidian vault with auto-fetched metadata.

## Dependencies

```bash
pip install requests beautifulsoup4
```

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/bookmarks"
```

## Vault Location

```
~/work/leo-obsidian-vault/Resources/Bookmarks/
```

## Commands

```bash
python3 "$SKILL_DIR/bookmarks.py" <command> [options]
```

| Command | Description |
|---------|-------------|
| `add` | Add a new bookmark |
| `list` | List all bookmarks |
| `search` | Search by title/tag/URL |
| `tags` | List all tags |
| `export` | Export to JSON/HTML/MD |

## Options

| Option | Description |
|--------|-------------|
| `-u, --url <url>` | URL to bookmark |
| `-t, --title <title>` | Custom title (auto-fetched if omitted) |
| `-d, --desc <desc>` | Description |
| `--tags <tags>` | Tags (comma-separated) |
| `-c, --category <cat>` | Category folder |
| `-q, --query <query>` | Search query |
| `-o, --output <file>` | Export file |
| `--format <fmt>` | json, html, markdown |

## Examples

```bash
# Add bookmark (auto-fetches title)
python3 "$SKILL_DIR/bookmarks.py" add -u "https://example.com/article"

# Add with tags and category
python3 "$SKILL_DIR/bookmarks.py" add -u "https://docs.python.org" --tags "python,docs" -c "Programming"

# Add with custom title
python3 "$SKILL_DIR/bookmarks.py" add -u "https://site.com" -t "My Favorite Site" --tags "favorite"

# List all bookmarks
python3 "$SKILL_DIR/bookmarks.py" list

# List by category
python3 "$SKILL_DIR/bookmarks.py" list -c "Programming"

# Search bookmarks
python3 "$SKILL_DIR/bookmarks.py" search -q "python tutorial"

# List all tags
python3 "$SKILL_DIR/bookmarks.py" tags

# Export to JSON
python3 "$SKILL_DIR/bookmarks.py" export -o bookmarks.json --format json
```

## Note Format

Each bookmark creates a note with:
- Frontmatter (url, domain, saved date, tags)
- Title and description
- Space for personal notes
- Hashtags for easy searching

---

## Syncing Changes

After adding bookmarks, sync to GitHub and iCloud:

```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && git add -A && git commit -m "Add bookmark" && git push && rsync -av --delete --exclude='.git/' --exclude='.DS_Store' --exclude='.obsidian/workspace.json' --exclude='.obsidian/workspace-mobile.json' --exclude='.smart-env/' --exclude='.trash/' /Users/leonardoaraujo/work/leo-obsidian-vault/ "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/"
```
