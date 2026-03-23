---
name: obsidian
description: Interact with Obsidian vault "Leo Knowledge" using the GitHub repo as primary source. Search, read, create, append notes. Changes are synced to GitHub and iCloud for multi-device access.
argument-hint: [command] [options]
---

# Obsidian Vault Integration

The vault is managed via GitHub repository. All changes are made to the repo first, then synced to iCloud for other devices.

## Primary Vault Path (GitHub Repo)
```
/Users/leonardoaraujo/work/leo-obsidian-vault
```

## GitHub Repository
```
https://github.com/leonardoaraujosantos/leo-obsidian-vault.git
```

## iCloud Path (for syncing to other devices)
```
/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge
```

---

## Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Repo    │────▶│    iCloud       │────▶│  Other Devices  │
│  (Primary)      │     │  (Sync Target)  │     │  (iPhone, iPad) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**IMPORTANT:** Always make changes to the GitHub repo first, then sync.

---

## Reading Notes

Use standard file tools to read from the vault:

```bash
# Read a specific file
Read: /Users/leonardoaraujo/work/leo-obsidian-vault/Programming/Python/Python.md

# Search for files by pattern
Glob: /Users/leonardoaraujo/work/leo-obsidian-vault/**/*.md

# Search for content
Grep: pattern="kubernetes" path="/Users/leonardoaraujo/work/leo-obsidian-vault"
```

---

## Writing/Creating Notes

Use Write or Edit tools to modify files:

```bash
# Create new file
Write: /Users/leonardoaraujo/work/leo-obsidian-vault/Programming/NewNote.md

# Edit existing file
Edit: /Users/leonardoaraujo/work/leo-obsidian-vault/Programming/Python/Python.md
```

---

## Syncing Changes

### After making any changes, ALWAYS run this sync command:

```bash
# 1. Commit and push to GitHub
cd /Users/leonardoaraujo/work/leo-obsidian-vault && \
git add -A && \
git commit -m "Update vault" && \
git push && \

# 2. Sync to iCloud (for other devices)
rsync -av --delete \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='.obsidian/workspace.json' \
  --exclude='.obsidian/workspace-mobile.json' \
  --exclude='.smart-env/' \
  --exclude='.trash/' \
  /Users/leonardoaraujo/work/leo-obsidian-vault/ \
  "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/"
```

### Quick Sync Command (one-liner):
```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && git add -A && git commit -m "Update vault" && git push && rsync -av --delete --exclude='.git/' --exclude='.DS_Store' --exclude='.obsidian/workspace.json' --exclude='.obsidian/workspace-mobile.json' --exclude='.smart-env/' --exclude='.trash/' /Users/leonardoaraujo/work/leo-obsidian-vault/ "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/"
```

---

## Common Operations

### Search for Notes
```bash
# By filename
Glob: /Users/leonardoaraujo/work/leo-obsidian-vault/**/*docker*.md

# By content
Grep: pattern="kubernetes" path="/Users/leonardoaraujo/work/leo-obsidian-vault"
```

### List Files in Folder
```bash
Bash: ls /Users/leonardoaraujo/work/leo-obsidian-vault/Programming/
```

### List All Folders
```bash
Bash: find /Users/leonardoaraujo/work/leo-obsidian-vault -type d -maxdepth 2 | head -30
```

### Count Files
```bash
Bash: find /Users/leonardoaraujo/work/leo-obsidian-vault -name "*.md" | wc -l
```

### Find Orphan Notes (no incoming links)
```bash
# Get all markdown files
Bash: find /Users/leonardoaraujo/work/leo-obsidian-vault -name "*.md" -exec basename {} .md \; | sort > /tmp/all_notes.txt

# Get all linked notes
Grep: pattern="\[\[" path="/Users/leonardoaraujo/work/leo-obsidian-vault" output_mode="content"
```

---

## Vault Structure

| Folder | Content |
|--------|---------|
| Programming | Languages, frameworks, web dev |
| ML Artificial Intelligence | AI/ML, deep learning |
| Infrastructure | Docker, Kubernetes, Terraform |
| Databases | SQL, NoSQL, data modeling |
| Blockchain | Crypto, DeFi, smart contracts |
| Engineering | Electronics, power, control |
| Robotics | ROS, motion planning, embedded |
| Cybersecurity | Security, pentesting |
| Mathematics | Math topics |
| Physics | Physics notes |
| Biology | Bio, bioinformatics |
| Finances | Markets, trading, DeFi |
| Game Development | Unity, Unreal |
| People | Personal info, family |
| Amini | Amini project notes |
| Cyberdyne | Cyberdyne project notes |

---

## Daily Notes

Daily notes are stored in: `Journal/Daily/YYYY-MM/YYYY-MM-DD.md`

```bash
# Read today's daily note
Read: /Users/leonardoaraujo/work/leo-obsidian-vault/Journal/Daily/$(date +%Y-%m)/$(date +%Y-%m-%d).md

# Create/append to daily note
# Use Write or Edit tool
```

---

## Usage Examples

When user asks:
- "Search for Docker notes" → Use Grep or Glob
- "What's in my Python notes?" → Use Read tool
- "Add a note about React hooks" → Use Write tool, then sync
- "List my notes on Kubernetes" → Use Glob pattern matching
- "Sync my vault" → Run the sync command
- "Push changes to GitHub" → Run git add, commit, push

---

## Important Reminders

1. **Always use the repo path:** `/Users/leonardoaraujo/work/leo-obsidian-vault`
2. **After changes:** Run the sync command to push to GitHub and iCloud
3. **File format:** All notes are Markdown (.md) with wiki-style links `[[Note Name]]`
4. **Frontmatter:** Many notes have YAML frontmatter with tags and metadata
