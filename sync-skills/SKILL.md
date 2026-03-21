---
name: sync-skills
description: Sync Claude Code skills to GitHub repository. Use when you want to backup skills, update the repo after creating/modifying a skill, or share skills.
argument-hint: [--skill <name>] [--message "commit message"] [--dry-run] [--list]
---

# Sync Skills to GitHub

Syncs skills from `~/.claude/skills/` to the GitHub repository.

## Repository

```
https://github.com/leonardoaraujosantos/my_ai_skills.git
```

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/sync-skills"
```

## Commands

```bash
# Sync all skills
python3 "$SKILL_DIR/sync_skills.py"

# Sync specific skill
python3 "$SKILL_DIR/sync_skills.py" --skill youtube-playlist

# Custom commit message
python3 "$SKILL_DIR/sync_skills.py" --message "Add new feature to CC extraction"

# Preview changes (dry run)
python3 "$SKILL_DIR/sync_skills.py" --dry-run

# List available skills
python3 "$SKILL_DIR/sync_skills.py" --list
```

## Options

| Option | Description |
|--------|-------------|
| `--skill <name>` | Sync only a specific skill |
| `--message <msg>` | Custom commit message |
| `--dry-run` | Preview without making changes |
| `--list` | List all available skills |

## Workflow

1. **After creating/modifying a skill**: Run `/sync-skills` to push changes
2. **To sync specific skill**: Run `/sync-skills --skill <name>`
3. **To preview changes**: Run `/sync-skills --dry-run`

## Examples

```bash
# After updating youtube-playlist skill
/sync-skills --skill youtube-playlist --message "Add timestamps feature"

# After creating a new skill
/sync-skills --message "Add new skill: my-new-skill"

# Regular backup of all skills
/sync-skills
```
