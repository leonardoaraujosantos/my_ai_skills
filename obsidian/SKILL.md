---
name: obsidian
description: "Interact with an Obsidian vault (configured via the OBSIDIAN_VAULT / OBSIDIAN_VAULT_NAME env vars). Search, read, create, append notes. Sync between GitHub repo, iCloud, and other devices. Covers Obsidian Flavored Markdown (.md), Bases (.base), and JSON Canvas (.canvas). Use when user says 'pull from iCloud', 'sync vault', 'push vault', 'search vault', or any vault operation."
argument-hint: pull | push | sync | search <query> | [command] [options]
---

# Obsidian Vault Integration

The vault is managed via GitHub repository. All changes are made to the repo first, then synced to iCloud for other devices.

## Configuration

Set these once in your shell profile so every command below is portable:

```bash
export OBSIDIAN_VAULT="$HOME/path/to/your-vault"        # local git repo of the vault
export OBSIDIAN_VAULT_NAME="YourVault"                   # vault name the Obsidian CLI expects
export OBSIDIAN_ICLOUD="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/$OBSIDIAN_VAULT_NAME"
```

Keep `OBSIDIAN_VAULT` free of spaces (the recipes use it unquoted); the iCloud
path is always quoted since it contains spaces.

## Paths

| Location | Path |
|----------|------|
| **GitHub Repo (Primary)** | `$OBSIDIAN_VAULT` |
| **iCloud (Sync Target)** | `$OBSIDIAN_ICLOUD` |
| **GitHub URL** | your vault's git remote |

## Obsidian CLI

```bash
CLI="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
# Pass the vault to each command as: vault="$OBSIDIAN_VAULT_NAME"
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
diff -rq $OBSIDIAN_VAULT \
  "$OBSIDIAN_ICLOUD" \
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
  "$OBSIDIAN_ICLOUD/" \
  $OBSIDIAN_VAULT/
```

### 3. Commit and push to GitHub
```bash
cd $OBSIDIAN_VAULT && \
git add -A && \
git commit -m "Sync vault from iCloud: <brief description of changes>" && \
git push
```

### 4. Show the user a summary of what was pulled (new files, modified files)

---

## Push to GitHub + iCloud (Repo → GitHub → iCloud)

**Triggered by:** `/obsidian push`, "push vault", "sync to iCloud"

### 1. Safety check — do NOT delete un-pulled mobile edits

The push below uses `rsync --delete`, which removes anything present in iCloud
but not in the repo. Run this dry-run first: if it prints any `deleting …`
lines, those are mobile/iPad edits you haven't pulled yet. **STOP and run
`/obsidian pull` (or `/obsidian sync`) first** — pushing would delete them.
Only proceed to step 2 when this prints `safe to push`.

```bash
# grep -i 'deleting' matches both GNU rsync ("deleting <file>") and the macOS
# default openrsync ("<file>: deleting").
rsync -avn --delete \
  --exclude='.git/' --exclude='.DS_Store' \
  --exclude='.obsidian/workspace.json' --exclude='.obsidian/workspace-mobile.json' \
  --exclude='.smart-env/' --exclude='.trash/' \
  $OBSIDIAN_VAULT/ "$OBSIDIAN_ICLOUD/" | grep -i 'deleting' \
  && echo "!!! the files above would be DELETED from iCloud — run /obsidian pull first" \
  || echo "safe to push"
```

### 2. Commit, push, and mirror to iCloud

The commit is guarded so an empty "nothing to commit" doesn't abort the `&&`
chain and skip the rsync.

```bash
cd $OBSIDIAN_VAULT && \
git add -A && \
{ git diff --cached --quiet || git commit -m "Update vault: <brief description>"; } && \
git push && \
rsync -av --delete \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='.obsidian/workspace.json' \
  --exclude='.obsidian/workspace-mobile.json' \
  --exclude='.smart-env/' \
  --exclude='.trash/' \
  $OBSIDIAN_VAULT/ \
  "$OBSIDIAN_ICLOUD/"
```

---

## Full Sync (Bidirectional)

**Triggered by:** `/obsidian sync`, "sync my vault"

1. First run the **Pull from iCloud** steps (to get mobile edits)
2. Then run the **Push to GitHub + iCloud** steps (to push everything out)

---

## Reference files

Deep-format details live in `references/` and are read on demand — load the
relevant one only when you need it:

- [Obsidian Flavored Markdown](references/obsidian-flavored-markdown.md) — wikilinks, embeds, callouts, properties, tags, math, Mermaid, footnotes
- [Bases (.base)](references/bases.md) — schema, filters, formulas, view types, examples, YAML quoting, troubleshooting
- [JSON Canvas (.canvas)](references/canvas.md) — nodes, edges, colors, layout guidelines, validation checklist
- [Obsidian CLI Reference](references/obsidian-cli.md) — full command set (reading, writing, links, tasks, daily notes, properties, templates, health checks) plus plugin/theme development
- [Maintenance](references/maintenance.md) — storage analysis and timestamped backups

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
| **Things to Study** | Topics/videos to learn |

> The folder list above is illustrative — your vault will have its own
> top-level folders. Run `$CLI folders vault="$OBSIDIAN_VAULT_NAME"` to see them.

---


## Things to Study Folder

`$OBSIDIAN_VAULT/Things to Study/` tracks topics, videos, courses, and articles
to learn. This folder is managed primarily by the **`study-this` skill** — use
it to add references and to consolidate learnings back into the vault.

---

## Usage Examples

When user asks:
- "Pull from iCloud" / "Bring iCloud changes" → Run **Pull from iCloud** steps
- "Push vault" / "Sync to iCloud" → Run **Push** steps
- "Sync my vault" → Run **Full Sync** (pull then push)
- "Search for Docker notes" → Use CLI `search` or Grep
- "What's in my Python notes?" → Use CLI `read` or Read tool
- "Add a note about React hooks" → Use Write tool with Obsidian Flavored Markdown, then push
- "Create a Base for my reading list" → Write a `.base` YAML file per the Bases section
- "Make a mind map of this topic" → Create a `.canvas` JSON file per the Canvas section
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

1. **Primary path:** `$OBSIDIAN_VAULT`
2. **After changes:** Run sync to push to GitHub and iCloud
3. **File formats:** `.md` (Markdown), `.base` (Bases YAML), `.canvas` (Canvas JSON)
4. **Linking:** Wiki-style links `[[Note Name]]` for internal; Markdown `[text](url)` for external
5. **Frontmatter:** YAML with tags and metadata
6. **Use CLI for:** Search, backlinks, tasks, health checks, plugin development
7. **Use File tools for:** Reading/writing note content, editing `.base`/`.canvas` files

## References

- [Obsidian Flavored Markdown](https://help.obsidian.md/obsidian-flavored-markdown)
- [Callouts](https://help.obsidian.md/callouts)
- [Properties](https://help.obsidian.md/properties)
- [Bases Syntax](https://help.obsidian.md/bases/syntax)
- [Bases Functions](https://help.obsidian.md/bases/functions)
- [Bases Views](https://help.obsidian.md/bases/views)
- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)
- [Obsidian CLI](https://help.obsidian.md/cli)
