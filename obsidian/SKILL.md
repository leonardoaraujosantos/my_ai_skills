---
name: obsidian
description: Interact with Obsidian vault "Leo Knowledge" using the official Obsidian CLI. Search, read, create, append notes, manage tasks, and more. Use when the user asks about their notes, knowledge base, or wants to save/retrieve information.
argument-hint: [command] [options]
---

# Obsidian CLI Integration

You have access to the **official Obsidian CLI v1.12+** to interact with the user's vault.

## CLI Binary Location
```
/Applications/Obsidian.app/Contents/MacOS/Obsidian
```

## Target Vault
```
vault="Leo Knowledge"
```

## Vault Fallback Path (if CLI fails)
```
/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge
```
Use standard file tools (Read, Write, Glob, Grep) on this path if the CLI is unavailable.

## Command Syntax
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian <command> vault="Leo Knowledge" [options]
```

**Important Notes:**
- `file=<name>` resolves by name (like wikilinks)
- `path=<path>` is exact (folder/note.md)
- Quote values with spaces: `name="My Note"`
- Use `\n` for newline, `\t` for tab in content values

---

## Essential Commands

### Search & Read

**Search vault for text:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian search vault="Leo Knowledge" query="kubernetes"
```

**Search with context (shows matching lines):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian search:context vault="Leo Knowledge" query="kubernetes" limit=10
```

**Read file contents:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian read vault="Leo Knowledge" path="Programming/Python.md"
```

**Read by name (wikilink style):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian read vault="Leo Knowledge" file="Python"
```

### List & Browse

**List all files:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian files vault="Leo Knowledge"
```

**List files in folder:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian files vault="Leo Knowledge" folder="Programming"
```

**List folders:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian folders vault="Leo Knowledge"
```

**List tags:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian tags vault="Leo Knowledge" counts
```

**Vault info:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian vault vault="Leo Knowledge"
```

### Create & Write

**Create new file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian create vault="Leo Knowledge" path="Programming/NewNote.md" content="# Title\n\nContent here"
```

**Create with template:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian create vault="Leo Knowledge" name="Meeting Notes" template="Meeting"
```

**Append to file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian append vault="Leo Knowledge" path="Programming/Python.md" content="\n## New Section\n\nContent"
```

**Prepend to file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian prepend vault="Leo Knowledge" file="Python" content="Updated: 2024-02-27\n"
```

### Daily Notes

**Read daily note:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:read vault="Leo Knowledge"
```

**Append to daily note:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:append vault="Leo Knowledge" content="- [ ] New task"
```

**Get daily note path:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian daily:path vault="Leo Knowledge"
```

### Links & Backlinks

**List backlinks to a file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian backlinks vault="Leo Knowledge" file="Python"
```

**List outgoing links:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian links vault="Leo Knowledge" file="Python"
```

**Find orphan notes (no incoming links):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian orphans vault="Leo Knowledge"
```

**Find dead-end notes (no outgoing links):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian deadends vault="Leo Knowledge"
```

**Find unresolved/broken links:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian unresolved vault="Leo Knowledge" counts
```

**Find unresolved with source files:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian unresolved vault="Leo Knowledge" verbose
```

### Tasks

**List all tasks:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge"
```

**List incomplete tasks:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge" todo
```

**List completed tasks:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge" done
```

**Tasks from daily note:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian tasks vault="Leo Knowledge" daily
```

**Toggle a specific task (by file and line):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian task vault="Leo Knowledge" path="Daily/2024-01-15.md" line=10 toggle
```

**Mark task as done:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian task vault="Leo Knowledge" file="MyNote" line=5 done
```

**Mark task as todo:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian task vault="Leo Knowledge" file="MyNote" line=5 todo
```

### Properties (Frontmatter)

**List all properties in vault:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian properties vault="Leo Knowledge" counts
```

**Read property from file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian property:read vault="Leo Knowledge" file="Python" name="tags"
```

**Set property on file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian property:set vault="Leo Knowledge" file="Python" name="status" value="reviewed"
```

### File Operations

**Get file info:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian file vault="Leo Knowledge" path="Programming/Python.md"
```

**Move/rename file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian move vault="Leo Knowledge" path="old/location.md" to="new/location.md"
```

**Delete file:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian delete vault="Leo Knowledge" path="path/to/file.md"
```

**Get outline (headings):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian outline vault="Leo Knowledge" file="Python"
```

### Templates

**List templates:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian templates vault="Leo Knowledge"
```

**Read template:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian template:read vault="Leo Knowledge" name="Meeting"
```

### Other Useful Commands

**Aliases:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian aliases vault="Leo Knowledge" verbose
```

**Bookmarks:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian bookmarks vault="Leo Knowledge"
```

**Recent files:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian recents vault="Leo Knowledge"
```

**Word count:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian wordcount vault="Leo Knowledge" file="Python"
```

**Random note:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian random:read vault="Leo Knowledge"
```

### Obsidian Commands

**List all available commands (including plugins):**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian commands vault="Leo Knowledge"
```

**Filter commands by prefix:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian commands vault="Leo Knowledge" filter="editor"
```

**Execute an Obsidian command:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian command vault="Leo Knowledge" id="editor:toggle-bold"
```

### Bases (Database Feature)

**List all bases in vault:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian bases vault="Leo Knowledge"
```

**Query a base:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian base:query vault="Leo Knowledge" file="MyBase" format=json
```

**List views in a base:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian base:views vault="Leo Knowledge" file="MyBase"
```

**Create item in a base:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian base:create vault="Leo Knowledge" file="MyBase" name="New Entry" content="# New Entry\n\nContent"
```

### Themes & Snippets

**List installed themes:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian themes vault="Leo Knowledge"
```

**Set active theme:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian theme:set vault="Leo Knowledge" name="Minimal"
```

**List CSS snippets:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian snippets vault="Leo Knowledge"
```

**Enable/disable snippet:**
```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian snippet:enable vault="Leo Knowledge" name="my-snippet"
/Applications/Obsidian.app/Contents/MacOS/Obsidian snippet:disable vault="Leo Knowledge" name="my-snippet"
```

---

## Vault Backup

### Backup Vault to ZIP

**Create a timestamped backup of the entire vault:**
```bash
# Create backup directory if it doesn't exist
mkdir -p ~/Downloads/VaultBackup

# Create ZIP backup with timestamp
cd "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents" && \
zip -r ~/Downloads/VaultBackup/"Leo_Knowledge_$(date +%Y-%m-%d_%H-%M-%S).zip" "Leo Knowledge" \
-x "*.DS_Store" -x "*/.obsidian/workspace.json" -x "*/.obsidian/workspace-mobile.json"
```

**Quick backup (without timestamp):**
```bash
mkdir -p ~/Downloads/VaultBackup && \
cd "/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents" && \
zip -r ~/Downloads/VaultBackup/Leo_Knowledge_latest.zip "Leo Knowledge" \
-x "*.DS_Store" -x "*/.obsidian/workspace.json"
```

**List existing backups:**
```bash
ls -lah ~/Downloads/VaultBackup/*.zip 2>/dev/null || echo "No backups found"
```

**Get backup folder size:**
```bash
du -sh ~/Downloads/VaultBackup 2>/dev/null || echo "Backup folder does not exist"
```

**Delete old backups (keep last 5):**
```bash
cd ~/Downloads/VaultBackup && ls -t *.zip 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
```

### Backup Configuration

| Setting | Value |
|---------|-------|
| **Backup Location** | `~/Downloads/VaultBackup` |
| **Vault Path** | `/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge` |
| **Excludes** | `.DS_Store`, `workspace.json`, `workspace-mobile.json` |
| **Naming Format** | `Leo_Knowledge_YYYY-MM-DD_HH-MM-SS.zip` |

### Usage Examples

When user asks:
- "Backup my vault" → Run the timestamped backup command
- "Create a vault backup" → Run the timestamped backup command
- "Show my backups" → List existing backups
- "Clean old backups" → Delete old backups keeping last 5

---

## Vault Structure

The vault contains knowledge organized in folders:
- **Programming** - Code, languages, frameworks
- **ML Artificial Intelligence** - AI/ML notes
- **Infrastructure** - DevOps, Docker, Kubernetes
- **Databases** - Database knowledge
- **Blockchain** - Crypto, web3
- **Engineering** - Electronics, hardware, power electronics
- **Robotics** - ROS, motion planning, embedded systems, simulation
- **Cybersecurity** - Security topics
- **Mathematics** - Math topics
- **Physics** - Physics notes
- **Biology** - Bio topics
- **Finances** - Financial knowledge, DeFi
- **Game Development** - Unity, Unreal, game design
- **Being a Boss** - Leadership
- And more...

---

## Usage Examples

When user asks:
- "Search for Docker notes" → Use `search` command
- "What's in my Python notes?" → Use `read` command
- "Add a note about React hooks" → Use `create` or `append`
- "What links to my Kubernetes note?" → Use `backlinks`
- "List my incomplete tasks" → Use `tasks todo`
- "Add to today's daily note" → Use `daily:append`
- "Find broken links" → Use `unresolved` command
- "Check off that task" → Use `task toggle` or `task done`
- "What Obsidian commands are available?" → Use `commands`
- "Backup my vault" → Use the vault backup ZIP command
- "Show my backups" → List existing backups in ~/Downloads/VaultBackup

**Always use the vault option:** `vault="Leo Knowledge"`
