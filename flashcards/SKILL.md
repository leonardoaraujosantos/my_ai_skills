---
name: flashcards
description: Generate spaced-repetition flashcards from study notes and package them for Anki (.apkg/.tsv) or Obsidian (spaced-repetition plugin). Use when the user says "make flashcards from X", "create Anki cards", "turn this note into flashcards", or wants to review study material with spaced repetition.
argument-hint: <note-or-topic> [--deck name] [--format apkg|tsv|obsidian]
---

# Flashcards

Turn study material into spaced-repetition flashcards. Claude authors the cards; the script packages them.

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/flashcards"
```

## Workflow

1. **Read the source.** An Obsidian note (typically under `Things to Study` — see the `obsidian` and `study-this` skills), a local file, or a topic the user names.
2. **Write a cards file** in the intermediate format below (e.g. to the scratchpad), following the authoring guidelines.
3. **Validate**: `python3 "$SKILL_DIR/flashcards.py" validate cards.md` — fix warnings.
4. **Convert** to the format the user wants (default: ask, or `apkg` for Anki users).
5. **Deliver**: save `.apkg`/`.tsv` wherever the user wants; `obsidian` output can be appended back into the vault note (obsidian-spaced-repetition plugin picks it up).

## Card-Authoring Guidelines

- **Atomic**: one fact per card. Split compound facts.
- **Front is a genuine question** — not a fill-in-the-blank copy of the note's sentence.
- **Avoid yes/no questions**; prefer "why / how / what happens if".
- **Cloze deletions** for lists and definitions: `Q: TCP handshake: {{c1::SYN}}, {{c2::SYN-ACK}}, {{c3::ACK}}` (`A:` optional for cloze).
- **10–30 cards per note**; answers under ~60 words.
- **Tag every card** with the topic.

## Intermediate Format

```markdown
# Deck: Topic Name

## Card
Q: question text (multi-line ok)
A: answer text
Tags: tag1, tag2

## Card
Q: A process has {{c1::code, data, and stack}} segments in memory.
Tags: os
```

## Commands

```bash
# Convert (formats: apkg | tsv | obsidian)
python3 "$SKILL_DIR/flashcards.py" convert cards.md --format apkg --deck "Networking" -o networking.apkg
python3 "$SKILL_DIR/flashcards.py" convert cards.md --format tsv -o cards.tsv
python3 "$SKILL_DIR/flashcards.py" convert cards.md --format obsidian   # stdout; append to vault note

# Lint: empty fronts/backs, duplicate fronts, long answers, yes/no questions
python3 "$SKILL_DIR/flashcards.py" validate cards.md

# Counts: cards, cloze, per-tag
python3 "$SKILL_DIR/flashcards.py" stats cards.md
```

## Output Formats

| Format | Notes |
|--------|-------|
| `apkg` | Anki package. Requires `genanki` (`pip install genanki`); without it the script warns and falls back to TSV. |
| `tsv` | Tab-separated `front / back / tags` for Anki File > Import. |
| `obsidian` | `#flashcards/<topic>` header + `Question::Answer` lines; cloze becomes `==highlight==` (obsidian-spaced-repetition plugin). |
