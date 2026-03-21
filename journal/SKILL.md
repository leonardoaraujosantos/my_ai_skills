---
name: journal
description: Daily journaling with templates to Obsidian vault. Track moods, energy, gratitude, and reflections. Use for personal journaling and daily notes.
argument-hint: <command> [options]
---

# Journal

Daily journaling with templates saved to Obsidian.

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/journal"
```

## Vault Location

```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/Journal/Daily/YYYY-MM/
```

## Commands

```bash
python3 "$SKILL_DIR/journal.py" <command> [options]
```

| Command | Description |
|---------|-------------|
| `today` | Show/create today's entry |
| `add` | Add entry to journal |
| `week` | Show this week's entries |
| `month` | Show this month's entries |
| `search` | Search journal entries |
| `stats` | Show journaling statistics |
| `prompts` | Show writing prompts |

## Options

| Option | Description |
|--------|-------------|
| `-t, --text <text>` | Text to add |
| `-m, --mood <mood>` | great, good, okay, bad, terrible |
| `-e, --energy <1-5>` | Energy level |
| `-s, --section <sec>` | morning, afternoon, evening, gratitude, reflection |
| `--tags <tags>` | Tags (comma-separated) |
| `-d, --date <date>` | Specific date (YYYY-MM-DD) |
| `-q, --query <query>` | Search query |

## Examples

```bash
# View/create today's entry
python3 "$SKILL_DIR/journal.py" today

# Add a quick note
python3 "$SKILL_DIR/journal.py" add -t "Had a great meeting with the team"

# Add with mood and energy
python3 "$SKILL_DIR/journal.py" add -t "Feeling productive" -m great -e 5

# Add to gratitude section
python3 "$SKILL_DIR/journal.py" add -t "Grateful for sunny weather" -s gratitude

# Add morning reflection
python3 "$SKILL_DIR/journal.py" add -t "Planning to focus on project X" -s morning

# View this week
python3 "$SKILL_DIR/journal.py" week

# View month
python3 "$SKILL_DIR/journal.py" month

# Search entries
python3 "$SKILL_DIR/journal.py" search -q "project meeting"

# View stats
python3 "$SKILL_DIR/journal.py" stats

# Get writing prompts
python3 "$SKILL_DIR/journal.py" prompts
```

## Template Sections

Each daily entry includes:
- **Morning** - Start of day thoughts
- **Tasks & Goals** - Today's todos
- **Journal** - Main journaling area
- **Gratitude** - 3 things grateful for
- **Evening Reflection** - End of day review
