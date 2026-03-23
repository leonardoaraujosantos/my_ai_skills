---
name: study-this
description: Process study references (YouTube, PDFs, websites), create an Obsidian vault note under "Things to Study", and add a Google Task to "Learn and Try". Use when the user says "let's study this", "add this to study", or shares links/resources they want to learn.
argument-hint: <urls or references> [--priority high|medium|low] [--category <cat>]
---

# Study This

Process references (YouTube videos, PDFs, websites) into structured study notes and tasks.

## Workflow

When the user provides references to study, follow these steps **in order**:

### Step 1: Extract URLs from the user's message

Parse all URLs from the message. Classify each as:
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

From the collected metadata, determine a concise, descriptive topic name that covers all the provided references. If the references are about different topics, create separate notes for each topic.

### Step 4: Create the Obsidian study note

Write the note to: `/Users/leonardoaraujo/work/leo-obsidian-vault/Things to Study/<Topic Name>.md`

**Before creating**, check if a note on the same topic already exists in that folder. If it does, **append** the new references to the existing note instead of creating a duplicate.

Use this template:

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

### Step 5: Add Google Task to "Learn and Try"

Create a task in the "Learn and Try" task list (ID: `ZjF1bU9sdlFzS3NhMi1jWg`):

```bash
gws tasks tasks insert --params '{"tasklist": "ZjF1bU9sdlFzS3NhMi1jWg"}' --json '{"title": "Study: <Topic Name>", "notes": "<list of URLs, one per line>"}'
```

### Step 6: Sync vault to GitHub and iCloud

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

### Step 7: Confirm to the user

Show a summary:
- Note created/updated in vault
- Google Task added
- List of references processed with titles

---

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--priority` | Priority level: high, medium, low | medium |
| `--category` | Category: Programming, AI, Engineering, etc. | Auto-detected |

---

## Examples

**User says:**
> Let's study this: https://www.youtube.com/watch?v=abc123 https://example.com/article

**Skill will:**
1. Fetch YouTube metadata for `abc123`
2. Fetch webpage title/content for the article
3. Create vault note with both references
4. Add Google Task "Study: <topic>"
5. Sync vault
6. Confirm

**User says:**
> /study-this https://arxiv.org/pdf/1234.5678 --priority high --category AI

**Skill will:**
1. Fetch/read the PDF
2. Create vault note with high priority under AI category
3. Add Google Task
4. Sync and confirm
