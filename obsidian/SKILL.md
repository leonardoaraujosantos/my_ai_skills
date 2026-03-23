---
name: obsidian
description: "Interact with Obsidian vault 'Leo Knowledge'. Search, read, create, append notes. Sync between GitHub repo, iCloud, and other devices. Use when user says 'pull from iCloud', 'sync vault', 'push vault', 'search vault', or any vault operation."
argument-hint: pull | push | sync | search <query> | [command] [options]
---

# Obsidian Vault Integration

The vault is managed via GitHub repository. All changes are made to the repo first, then synced to iCloud for other devices.

## Paths

| Location | Path |
|----------|------|
| **GitHub Repo (Primary)** | `/Users/leonardoaraujo/work/leo-obsidian-vault` |
| **iCloud (Sync Target)** | `/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge` |
| **GitHub URL** | https://github.com/leonardoaraujosantos/leo-obsidian-vault.git |

## Obsidian CLI

```bash
CLI="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
VAULT='vault="Leo Knowledge"'
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

## Top-Level Commands

These are the primary commands the user triggers with `/obsidian <command>`:

| User says | Action |
|-----------|--------|
| `/obsidian pull` | Pull iCloud changes → repo → commit → push to GitHub |
| `/obsidian push` | Commit repo changes → push to GitHub → rsync to iCloud |
| `/obsidian sync` | Full bidirectional: pull from iCloud first, then push to GitHub + iCloud |
| `/obsidian search <query>` | Search vault for content |

---

## Pull from iCloud (Mobile/iPad edits → Repo → GitHub)

**Triggered by:** `/obsidian pull`, "pull from iCloud", "bring iCloud changes"

Run these steps in order:

### 1. Check what changed
```bash
diff -rq /Users/leonardoaraujo/work/leo-obsidian-vault \
  "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge" \
  --exclude='.git' --exclude='.obsidian' --exclude='.smart-env' --exclude='.trash' --exclude='.DS_Store' 2>/dev/null | head -30
```

### 2. Pull changes from iCloud into repo
```bash
rsync -av --update \
  --exclude='.git/' \
  --exclude='.obsidian/workspace*.json' \
  --exclude='.smart-env/' \
  --exclude='.trash/' \
  --exclude='.DS_Store' \
  "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/" \
  /Users/leonardoaraujo/work/leo-obsidian-vault/
```

### 3. Commit and push to GitHub
```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && \
git add -A && \
git commit -m "Sync vault from iCloud: <brief description of changes>" && \
git push
```

### 4. Show the user a summary of what was pulled (new files, modified files)

---

## Push to GitHub + iCloud (Repo → GitHub → iCloud)

**Triggered by:** `/obsidian push`, "push vault", "sync to iCloud"

```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && \
git add -A && \
git commit -m "Update vault: <brief description>" && \
git push && \
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

---

## Full Sync (Bidirectional)

**Triggered by:** `/obsidian sync`, "sync my vault"

1. First run the **Pull from iCloud** steps (to get mobile edits)
2. Then run the **Push to GitHub + iCloud** steps (to push everything out)

---

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Search vault | `$CLI search $VAULT query="keyword"` |
| Search with context | `$CLI search:context $VAULT query="keyword" limit=10` |
| Read file | `$CLI read $VAULT file="NoteName"` |
| Read by path | `$CLI read $VAULT path="Folder/Note.md"` |
| List files | `$CLI files $VAULT` |
| List folders | `$CLI folders $VAULT` |
| List tags | `$CLI tags $VAULT counts` |
| Vault info | `$CLI vault $VAULT` |
| Recent files | `$CLI recents $VAULT` |
| Random note | `$CLI random:read $VAULT` |

---

## Reading Notes

### Using CLI (preferred for search)
```bash
# Search for content
/Applications/Obsidian.app/Contents/MacOS/Obsidian search vault="Leo Knowledge" query="kubernetes"

# Search with context (shows matching lines)
/Applications/Obsidian.app/Contents/MacOS/Obsidian search:context vault="Leo Knowledge" query="kubernetes" limit=10

# Read by name (wikilink style)
/Applications/Obsidian.app/Contents/MacOS/Obsidian read vault="Leo Knowledge" file="Python"

# Read by path
/Applications/Obsidian.app/Contents/MacOS/Obsidian read vault="Leo Knowledge" path="Programming/Python.md"
```

### Using File Tools (for editing)
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

Use Write or Edit tools on the **GitHub repo**, then sync:

```bash
# Create new file
Write: /Users/leonardoaraujo/work/leo-obsidian-vault/Programming/NewNote.md

# Edit existing file
Edit: /Users/leonardoaraujo/work/leo-obsidian-vault/Programming/Python/Python.md
```

---

## Links & Backlinks

```bash
# List backlinks to a file
/Applications/Obsidian.app/Contents/MacOS/Obsidian backlinks vault="Leo Knowledge" file="Python"

# List outgoing links
/Applications/Obsidian.app/Contents/MacOS/Obsidian links vault="Leo Knowledge" file="Python"

# Get note outline (headings)
/Applications/Obsidian.app/Contents/MacOS/Obsidian outline vault="Leo Knowledge" file="Python"
```

---

## Vault Health Checks

```bash
# Find orphan notes (no incoming links)
/Applications/Obsidian.app/Contents/MacOS/Obsidian orphans vault="Leo Knowledge"

# Find dead-end notes (no outgoing links)
/Applications/Obsidian.app/Contents/MacOS/Obsidian deadends vault="Leo Knowledge"

# Find broken/unresolved links
/Applications/Obsidian.app/Contents/MacOS/Obsidian unresolved vault="Leo Knowledge" verbose

# Find unresolved with counts
/Applications/Obsidian.app/Contents/MacOS/Obsidian unresolved vault="Leo Knowledge" counts
```

---

## Tasks

```bash
# List all tasks
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge"

# List incomplete tasks
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge" todo

# List completed tasks
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge" done

# Tasks from daily note
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge" daily

# Toggle a task
/Applications/Obsidian.app/Contents/MacOS/Obsidian task vault="Leo Knowledge" file="MyNote" line=5 toggle
```

---

## Daily Notes

Daily notes are stored in: `Journal/Daily/YYYY-MM/YYYY-MM-DD.md`

```bash
# Read today's daily note
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:read vault="Leo Knowledge"

# Append to daily note
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:append vault="Leo Knowledge" content="- [ ] New task"

# Get daily note path
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:path vault="Leo Knowledge"
```

---

## Properties (Frontmatter)

```bash
# List all properties in vault
/Applications/Obsidian.app/Contents/MacOS/Obsidian properties vault="Leo Knowledge" counts

# Read property from file
/Applications/Obsidian.app/Contents/MacOS/Obsidian property:read vault="Leo Knowledge" file="Python" name="tags"

# Set property on file
/Applications/Obsidian.app/Contents/MacOS/Obsidian property:set vault="Leo Knowledge" file="Python" name="status" value="reviewed"
```

---

## Templates

```bash
# List templates
/Applications/Obsidian.app/Contents/MacOS/Obsidian templates vault="Leo Knowledge"

# Read template
/Applications/Obsidian.app/Contents/MacOS/Obsidian template:read vault="Leo Knowledge" name="Meeting"

# Create with template
/Applications/Obsidian.app/Contents/MacOS/Obsidian create vault="Leo Knowledge" name="Meeting Notes" template="Meeting"
```

---

## Syncing Changes

### Full Sync (Repo → GitHub → iCloud)

```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && \
git add -A && \
git commit -m "Update vault" && \
git push && \
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

### Pull from iCloud (Mobile edits → Repo)

```bash
rsync -av --update \
  --exclude='.git/' \
  --exclude='.obsidian/workspace*.json' \
  --exclude='.smart-env/' \
  --exclude='.trash/' \
  "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/" \
  /Users/leonardoaraujo/work/leo-obsidian-vault/
```

### Check for Conflicts

```bash
diff -rq /Users/leonardoaraujo/work/leo-obsidian-vault \
  "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge" \
  --exclude='.git' --exclude='.obsidian' --exclude='.smart-env' --exclude='.trash' 2>/dev/null | head -20
```

---

## Storage Analysis

```bash
# Total vault size
du -sh "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge"

# Size by folder
du -sh "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge"/* | sort -hr | head -20

# Largest files
find "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge" -type f -exec du -h {} + 2>/dev/null | sort -hr | head -20

# Clean Smart Connections cache (regenerates automatically)
rm -rf "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge/.smart-env"
```

---

## Backup

```bash
# Create timestamped backup
mkdir -p ~/Downloads/VaultBackup && \
cd "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents" && \
zip -r ~/Downloads/VaultBackup/"Leo_Knowledge_$(date +%Y-%m-%d_%H-%M-%S).zip" "Leo Knowledge" \
  -x "*.DS_Store" -x "*/.obsidian/workspace*.json" -x "*/.smart-env/*"

# List backups
ls -lah ~/Downloads/VaultBackup/*.zip 2>/dev/null

# Delete old backups (keep last 5)
cd ~/Downloads/VaultBackup && ls -t *.zip 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
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
| **Things to Study** | Topics/videos to learn |

---

## Things to Study Folder

Location: `/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study/`

Used to track topics, videos, courses, and articles to study. **Managed primarily by the `/study-this` skill.**

### Status Lifecycle

| Status | Meaning |
|--------|---------|
| `pending` | Not started yet |
| `in_progress` | Currently studying |
| `consolidated` | Finished studying, learnings merged back into vault knowledge notes |

### Frontmatter fields
- **status**: `pending`, `in_progress`, `consolidated`
- **priority**: `high`, `medium`, `low`
- **category**: Programming, AI, Engineering, etc.
- **source**: YouTube, Website, PDF, Mixed
- **date_added**: when the study item was created
- **date_consolidated**: when learnings were merged back into vault (set by `/study-this consolidate`)

### Integration with `/study-this` skill

- **Adding study items:** Use `/study-this <urls>` — it fetches metadata, checks existing vault knowledge, creates the note, and adds a Google Task to "Learn and Try"
- **Consolidating:** Use `/study-this consolidate <topic>` — merges learnings from the study note back into vault knowledge notes, marks status as `consolidated`, and completes the Google Task
- **Manual creation:** Can also create notes directly here using the template below

### Template (for manual creation)
```markdown
---
status: pending
priority: medium
category:
source:
date_added: YYYY-MM-DD
---

# Topic Name

## Why Study This

## Existing Knowledge in Vault

## References

## Key Points

## Notes

## Action Items
- [ ] Watch/Read the material
- [ ] Take notes
- [ ] Practice/Apply
```

### List study items by status
```bash
# All study notes
ls "/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study/"

# Find pending items
Grep: pattern="status: pending" path="/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study" glob="*.md"

# Find consolidated items
Grep: pattern="status: consolidated" path="/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study" glob="*.md"
```

---

## Usage Examples

When user asks:
- "Pull from iCloud" / "Bring iCloud changes" → Run **Pull from iCloud** steps
- "Push vault" / "Sync to iCloud" → Run **Push** steps
- "Sync my vault" → Run **Full Sync** (pull then push)
- "Search for Docker notes" → Use CLI `search` or Grep
- "What's in my Python notes?" → Use CLI `read` or Read tool
- "Add a note about React hooks" → Use Write tool, then push
- "What links to my Kubernetes note?" → Use CLI `backlinks`
- "List my incomplete tasks" → Use CLI `tasks todo`
- "Find broken links" → Use CLI `unresolved`
- "Add to today's daily note" → Use CLI `daily:append`
- "Backup my vault" → Run the backup ZIP command
- "Check vault storage" → Run storage analysis
- "Add video to study list" → Use `/study-this` skill instead
- "What study items are pending?" → Grep for `status: pending` in Things to Study

---

## Important Reminders

1. **Primary path:** `/Users/leonardoaraujo/work/leo-obsidian-vault`
2. **After changes:** Run sync to push to GitHub and iCloud
3. **File format:** Markdown (.md) with wiki-style links `[[Note Name]]`
4. **Frontmatter:** YAML with tags and metadata
5. **Use CLI for:** Search, backlinks, tasks, health checks
6. **Use File tools for:** Reading/writing content, editing
