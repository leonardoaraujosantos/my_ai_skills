---
name: weekly-review
description: Aggregate the week's activity (journal entries, calendar meetings, tasks, git commits, Obsidian notes) and synthesize a weekly review note saved to the Obsidian vault. Use when the user says "weekly review", "review my week", "what did I do this week", or "prepare my week".
argument-hint: [week: current|last|YYYY-Www] [--no-save]
---

# Weekly Review

Orchestrator skill: gather the week's activity from the **journal**, **gws**,
and **obsidian** skills plus local git repos, then synthesize a single weekly
review note into the Obsidian vault.

This skill has no scripts of its own — follow the steps below at runtime,
invoking the tools those skills already provide.

## Configuration

Reuses the config of the `journal` and `obsidian` skills:

```bash
export OBSIDIAN_VAULT="$HOME/path/to/your-vault"   # local git repo of the vault
export OBSIDIAN_VAULT_NAME="YourVault"             # vault name the Obsidian CLI expects
CLI="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
JOURNAL="$HOME/.claude/skills/journal/journal.py"
```

If `OBSIDIAN_VAULT` is unset, the journal skill defaults to `~/obsidian-vault`.

---

## Step 1 — Resolve the target week

Argument: `current` (default), `last`, or an ISO week like `2026-W27`.
Compute the ISO week id and the Monday–Sunday date range:

```bash
python3 -c '
import sys, datetime
arg = sys.argv[1] if len(sys.argv) > 1 else "current"
today = datetime.date.today()
if arg == "current":
    monday = today - datetime.timedelta(days=today.weekday())
elif arg == "last":
    monday = today - datetime.timedelta(days=today.weekday() + 7)
else:  # YYYY-Www
    year, week = arg.split("-W")
    monday = datetime.date.fromisocalendar(int(year), int(week), 1)
sunday = monday + datetime.timedelta(days=6)
y, w, _ = monday.isocalendar()
print(f"WEEK_ID={y}-W{w:02d}")
print(f"MONDAY={monday.isoformat()}")
print(f"SUNDAY={sunday.isoformat()}")
' current
```

Use `MONDAY` / `SUNDAY` in every range below and `WEEK_ID` as the note name.

## Step 2 — Gather data

Collect from each source below. **Tolerate missing sources**: if a CLI is not
installed, not authenticated, or returns an error, skip it, continue with the
rest, and record the gap so the note can say "no data" for that section.

### Journal (moods, energy, entries)

```bash
python3 "$JOURNAL" week    # entries overview — CURRENT week only
python3 "$JOURNAL" stats   # streak + mood distribution (all-time)
```

`week` always shows the current calendar week (it takes no date option). For
`last` or an explicit `YYYY-Www`, read the daily files for the range directly:

```bash
# One file per day, may not exist:
# $OBSIDIAN_VAULT/Journal/Daily/YYYY-MM/YYYY-MM-DD.md
```

Extract `mood:` and `energy:` from each file's frontmatter and the text under
`## Journal`, `## Gratitude`, and `## Evening Reflection`.

### Calendar (meetings attended)

For the current week starting today:

```bash
gws calendar +agenda --days 7 --format table
```

`+agenda` looks forward from today, so for `last`, an explicit week, or to
cover days already past this week, query the range directly (`--params` is
passed to the Google Calendar API):

```bash
gws calendar events list --params '{"calendarId": "primary", "timeMin": "<MONDAY>T00:00:00Z", "timeMax": "<SUNDAY>T23:59:59Z", "singleEvents": true, "orderBy": "startTime"}' --format table
```

If the range query fails, fall back to `+agenda` and note that only upcoming
events were visible.

### Tasks (completed vs still open)

```bash
gws tasks tasks list --params '{"tasklist": "@default"}' --format table
```

This lists open tasks. To also see completed ones, best-effort: add
`"showCompleted": true, "showHidden": true` to the params (Google Tasks API
options); if the command rejects them, report open tasks only and say
completed-task data was unavailable. If there are multiple task lists
(`gws tasks tasklists list --format table`), iterate them.

### Git activity (per repo under ~/work)

```bash
for d in "$HOME/work"/*/; do
  [ -d "$d/.git" ] || continue
  log=$(git -C "$d" log --since="<MONDAY> 00:00" --until="<SUNDAY> 23:59" \
        --author="$(git -C "$d" config user.name)" --oneline 2>/dev/null)
  [ -n "$log" ] && printf '### %s\n%s\n' "$(basename "$d")" "$log"
done
```

Summarize per repo: number of commits and the main themes (group related
commit messages, don't paste the raw log into the note).

### Obsidian notes touched this week

```bash
# Notes modified in the range (excluding journal dailies, already covered)
find "$OBSIDIAN_VAULT" -name "*.md" \
  -not -path "*/.git/*" -not -path "*/.obsidian/*" -not -path "*/.trash/*" \
  -not -path "*/Journal/Daily/*" \
  -newermt "<MONDAY> 00:00:00" ! -newermt "<SUNDAY> 23:59:59" 2>/dev/null
```

If `find -newermt` is unavailable, best-effort fallback: in the vault repo,
`git -C "$OBSIDIAN_VAULT" log --since --until --name-only` for changed `.md`
files, or the Obsidian CLI `"$CLI" recents vault="$OBSIDIAN_VAULT_NAME"`
(recency only, not range-filtered — say so if used).

## Step 3 — Synthesize the review note

Write the note with exactly these sections, in this order:

1. **Summary** — 3–5 sentence narrative of the week.
2. **Wins** — from journal entries, completed tasks, shipped commits.
3. **Challenges** — from journal reflections, bad-mood days, stalled work.
4. **Learnings** — insights from journal + notes created/modified.
5. **Meetings & Collaboration** — from the calendar data.
6. **Shipped / Git activity** — per-repo bullet list.
7. **Mood & Energy** — from journal frontmatter (e.g. daily mood line, average energy).
8. **Open loops** — uncompleted tasks and unfinished threads.
9. **Focus for next week** — 3–5 proposed priorities; **ask the user to confirm or edit these before saving**.

Frontmatter for the note:

```yaml
---
week: <WEEK_ID>
date-range: <MONDAY> to <SUNDAY>
tags: [weekly-review]
---
```

## Step 4 — Save to the vault

Skip this step entirely if `--no-save` was passed (just show the note).

1. Target path: `$OBSIDIAN_VAULT/Weekly Reviews/<WEEK_ID>.md`
   (e.g. `Weekly Reviews/2026-W27.md`).
2. **If the file already exists, show a diff-level summary and ask the user
   before overwriting or appending.** Never silently replace it.
3. Write the note with the Write/Edit tool on the repo vault — this is the
   obsidian skill's documented pattern for creating notes (repo first, then
   sync). Create the `Weekly Reviews/` folder if missing.
4. Offer to sync: run `/obsidian push` (or `/obsidian sync`) so the note
   reaches GitHub and iCloud. Do not sync without asking.
5. Show the final note content to the user.

## Rules

- **Never fabricate data.** A source that failed or returned nothing gets an
  explicit "no data" line in its section — do not invent meetings, moods, or
  commits.
- Ask before overwriting an existing weekly note (Step 4.2).
- Write the note in the **same language the user's journal entries use**
  (inspect the gathered entries; default to English only if there are none).
- Confirm the "Focus for next week" items with the user before saving.
- Keep the note self-contained: summarize, link with `[[wikilinks]]` to
  daily notes (`[[YYYY-MM-DD]]`) where useful, don't paste raw command output.

## Sources consulted

| Data source | Exact command |
|---|---|
| Journal entries (current week) | `python3 "$HOME/.claude/skills/journal/journal.py" week` |
| Journal stats | `python3 "$HOME/.claude/skills/journal/journal.py" stats` |
| Journal entries (arbitrary week) | Read `$OBSIDIAN_VAULT/Journal/Daily/YYYY-MM/YYYY-MM-DD.md` per day |
| Calendar (current week) | `gws calendar +agenda --days 7 --format table` |
| Calendar (date range) | `gws calendar events list --params '{"calendarId": "primary", "timeMin": "...", "timeMax": "..."}'` |
| Tasks | `gws tasks tasks list --params '{"tasklist": "@default"}' --format table` |
| Git activity | `git -C <repo> log --since=<MONDAY> --until=<SUNDAY> --author="$(git -C <repo> config user.name)" --oneline` per repo under `~/work` |
| Vault notes touched | `find "$OBSIDIAN_VAULT" -name "*.md" -newermt <MONDAY> ! -newermt <SUNDAY>` (with excludes) |
| Save note | Write tool → `$OBSIDIAN_VAULT/Weekly Reviews/<WEEK_ID>.md`, then `/obsidian push` |
