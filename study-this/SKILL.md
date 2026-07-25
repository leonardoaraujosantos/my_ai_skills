---
name: study-this
description: "Process study references (YouTube, PDFs, websites), create Obsidian vault notes under 'Things to Study', add Google Tasks, and consolidate learnings back into the vault. Use when: user says 'let's study this' / 'add this to study' with links, OR 'consolidate' / 'I finished studying' to merge learnings into existing vault notes."
argument-hint: <urls or references> [--priority high|medium|low] [--category <cat>] OR consolidate [topic]
---

# Study This

Two modes: **Study** (add new references) and **Consolidate** (merge learnings back into vault).

---

## Mode 1: Study — Adding New References

Triggered by: `/study-this <urls>`, "let's study this", "add this to study"

### Step 1: Extract URLs from the user's message

Parse all URLs. Classify each as:
- **YouTube** — contains `youtube.com/watch`, `youtu.be/`, or `youtube.com/playlist`
- **PDF** — ends in `.pdf` or user mentions it's a PDF
- **Website** — everything else (articles, docs, blog posts, etc.)

### Step 2: Fetch metadata for each reference

**YouTube videos:**
```bash
python3 "$HOME/.claude/skills/youtube-playlist/youtube_metadata.py" "<url>" --format json
```

**YouTube playlists:**
```bash
python3 "$HOME/.claude/skills/youtube-playlist/youtube_playlist.py" "<url>" --format json --limit 20
```

**Websites:**
Use the WebFetch tool to get the page content and extract title + description.

**PDFs:**
If it's a local file, use the Read tool. If it's a remote URL, use WebFetch to download it, then read.

### Step 3: Determine a study topic name

From the collected metadata, determine a concise, descriptive topic name. If references cover different topics, create separate notes.

### Step 4: Search the vault for existing knowledge

**IMPORTANT:** Before creating the study note, search the vault for existing notes about this topic.

```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian search vault="Leo Knowledge" query="<topic keywords>" 2>&1 | grep -v "^2026\|installer\|Loading\|asar"
```

Also search with Grep for broader matches:
```bash
Grep: pattern="<topic keyword>" path="/Users/leonardoaraujo/work/leo-obsidian-vault" glob="*.md"
```

**Exclude** results from `Things to Study/` folder — we want knowledge notes, not other study notes.

If existing notes are found:
1. Read the most relevant ones (up to 3-4 notes)
2. Add a **"## Existing Knowledge in Vault"** section to the study note listing what you already have, with wiki-links `[[Note Name]]`
3. Briefly summarize what each existing note covers so the user knows what's new vs. what they already have

### Step 5: Create the Obsidian study note

Write to: `/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study/<Topic Name>.md`

**Before creating**, check if a note on the same topic already exists in `Things to Study/`. If it does, **append** the new references instead of creating a duplicate.

Template:

```markdown
---
status: pending
priority: <priority - default: medium>
category: <category - infer from content, e.g. Programming, AI, Engineering, etc.>
source: <YouTube, Website, PDF, Mixed>
date_added: <today's date YYYY-MM-DD>
---

# <Topic Name>

## Why Study This

<Brief explanation of why this is worth studying, inferred from the content>

## Existing Knowledge in Vault

<If existing notes were found, list them here with summaries. If none found, write "No existing notes found on this topic — this is a new area.">

- [[Note Name]] — <what it covers, e.g. "Covers Docker basics, commands, and Dockerfile structure">
- [[Another Note]] — <summary>

## References

### <N>. <Reference Title>
- **Type:** YouTube Video | Website | PDF
- **Source:** <channel name or website domain>
- **Duration:** <if video>
- **URL:** <url>
- **Published:** <date if available>
- **Summary:** <brief summary from description/content>

<repeat for each reference>

## Key Points

## Notes

## Action Items
- [ ] <action item per reference, e.g. "Watch video X (duration)" or "Read article Y">
- [ ] Take notes
- [ ] Practice/Apply
```

### Step 6: Add Google Task to "Learn and Try"

```bash
gws tasks tasks insert --params '{"tasklist": "ZjF1bU9sdlFzS3NhMi1jWg"}' --json '{"title": "Study: <Topic Name>", "notes": "<list of URLs, one per line>"}'
```

### Step 7: Sync vault to GitHub and iCloud

```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && \
git add "Things to Study/" && \
git commit -m "Add study note: <Topic Name>" && \
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

### Step 8: Confirm to the user

Show a summary:
- Note created/updated in vault
- Existing vault knowledge found (if any)
- Google Task added
- List of references processed with titles

---

## Mode 2: Consolidate — Merging Learnings Back Into Vault

Triggered by: `/study-this consolidate [topic]`, "consolidate this study", "I finished studying X", or when a study note has `status: consolidated`

The goal is to take what was learned from the study references and **enrich existing vault knowledge notes** or **create new knowledge notes** in the appropriate vault folder.

### Step 1: Identify the study note to consolidate

If the user specifies a topic, find the matching note in `Things to Study/`.
If not specified, list study notes with `status: pending` or `status: in_progress` and ask which one.

```bash
ls "/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study/"
```

Read the study note to understand the topic, references, and any notes the user has added.

### Step 2: Extract learnings from the study note

Read the study note fully. The key content to consolidate comes from:
- **Key Points** section (user-written insights)
- **Notes** section (user-written notes)
- **Action Items** that are completed (checked off)
- The reference summaries and any CC/transcripts if available

If the Key Points and Notes sections are empty, ask the user what they learned or if they want you to extract key points from the reference materials (e.g., fetch YouTube CC, re-read the articles).

### Step 3: Find target vault notes to update

Search the vault (excluding `Things to Study/`) for notes related to the topic:

```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian search vault="Leo Knowledge" query="<topic keywords>" 2>&1 | grep -v "^2026\|installer\|Loading\|asar\|Things to Study"
```

Also use Grep for broader coverage:
```bash
Grep: pattern="<topic keyword>" path="/Users/leonardoaraujo/work/leo-obsidian-vault" glob="*.md"
```

Filter out `Things to Study/` results.

Read the most relevant notes to understand their current content and structure.

### Step 4: Update or create knowledge notes

**If matching vault notes exist:**
1. Read each relevant note
2. Identify what's **new** from the study (not already covered)
3. Append new learnings to the appropriate section of the existing note
4. Keep the existing note's style and structure — don't reorganize it
5. Add the study references as sources at the bottom if the note has a Resources/References section

**If no matching vault notes exist:**
1. Determine the correct vault folder based on category:
   - Programming → `/Programming/<subfolder>/`
   - AI/ML → `/ML Artificial Intelligence/`
   - Infrastructure → `/Infrastructure/`
   - Engineering → `/Engineering/`
   - Blockchain → `/Blockchain/`
   - etc.
2. Create a new knowledge note with the learnings
3. Use the standard vault note style (look at existing notes in that folder for reference)

### Step 5: Update the study note status

Change the study note's frontmatter:
```yaml
status: consolidated
date_consolidated: <today's date YYYY-MM-DD>
```

### Step 6: Update Google Task

Find and complete the corresponding task in "Learn and Try":

```bash
gws tasks tasks list --params '{"tasklist": "ZjF1bU9sdlFzS3NhMi1jWg"}' --format json
```

Find the task matching "Study: <Topic Name>" and mark it complete:

```bash
gws tasks tasks update --params '{"tasklist": "ZjF1bU9sdlFzS3NhMi1jWg", "task": "<TASK_ID>"}' --json '{"status": "completed"}'
```

### Step 7: Sync vault

```bash
cd /Users/leonardoaraujo/work/leo-obsidian-vault && \
git add -A && \
git commit -m "Consolidate study: <Topic Name>" && \
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

### Step 8: Confirm to the user

Show a summary:
- Which vault notes were updated (with what was added)
- Any new notes created (with location)
- Study note marked as consolidated
- Google Task completed

---

## Vault Folder Reference

| Category | Vault Path |
|----------|-----------|
| Programming | `/Programming/<Language or Framework>/` |
| AI / ML | `/ML Artificial Intelligence/` |
| Infrastructure | `/Infrastructure/` |
| Databases | `/Databases/` |
| Blockchain | `/Blockchain/` |
| Engineering | `/Engineering/` |
| Robotics | `/Robotics/` |
| Cybersecurity | `/Cybersecurity/` |
| Mathematics | `/Mathematics/` |
| Physics | `/Physics/` |
| Finances | `/Finances/` |
| Game Development | `/Game Development/` |
| Geospatial | `/Geospatial/` |

---

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--priority` | Priority level: high, medium, low | medium |
| `--category` | Category: Programming, AI, Engineering, etc. | Auto-detected |

---

## Examples

### Study mode

**User:** "Let's study this: https://youtube.com/watch?v=abc123"
1. Fetch metadata → topic is "React Server Components"
2. Search vault → finds `Programming/Frontend/Frontend.md` mentions RSC briefly
3. Create study note with "Existing Knowledge" section linking to Frontend note
4. Add Google Task
5. Sync & confirm

### Consolidate mode

**User:** "/study-this consolidate React Server Components"
1. Read study note → has Key Points and Notes filled in
2. Search vault → finds `Programming/Frontend/Frontend.md`
3. Read Frontend.md → has a small RSC section
4. Append new learnings (streaming, suspense boundaries, etc.) to Frontend.md
5. Mark study note as `status: consolidated`
6. Complete Google Task
7. Sync & confirm

**User:** "I finished studying the Remotion tutorial, consolidate it"
1. Find `Things to Study/Remotion Tutorial.md`
2. Extract learnings
3. No existing Remotion note outside Things to Study → create `/Programming/Frontend/Remotion.md`
4. Mark as consolidated, complete task, sync
