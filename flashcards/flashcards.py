#!/usr/bin/env python3
"""Convert study-note flashcards (intermediate markdown) to Anki/Obsidian formats.

Core is stdlib-only. `genanki` (pip install genanki) is optional and only
needed for .apkg output; without it, apkg requests fall back to TSV.
"""

import argparse
import hashlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

CLOZE_RE = re.compile(r"\{\{c\d+::(.+?)(?:::[^}]*)?\}\}")
YES_NO_STARTERS = (
    "is ", "are ", "was ", "were ", "do ", "does ", "did ", "can ", "could ",
    "will ", "would ", "has ", "have ", "had ", "should ", "shall ", "am ",
)


@dataclass
class Card:
    question: str = ""
    answer: str = ""
    tags: list = field(default_factory=list)
    line: int = 0

    @property
    def is_cloze(self):
        return bool(CLOZE_RE.search(self.question))


class Parser:
    """Line-oriented parser for the intermediate cards format."""

    def __init__(self):
        self.deck = "Flashcards"
        self.cards = []
        self._card = None
        self._buffer = None  # "q" | "a" | None

    def feed(self, lineno, line):
        s = line.strip()
        if s.startswith("# Deck:"):
            self.deck = s[len("# Deck:"):].strip() or self.deck
            self._buffer = None
        elif s == "## Card":
            self._start_card(lineno)
        elif self._card is None:
            return
        elif s.startswith("Q:"):
            self._card.question = s[2:].strip()
            self._buffer = "q"
        elif s.startswith("A:"):
            self._card.answer = s[2:].strip()
            self._buffer = "a"
        elif s.startswith("Tags:"):
            self._card.tags = [t.strip() for t in s[5:].split(",") if t.strip()]
            self._buffer = None
        elif s:
            self._continue(s)

    def _start_card(self, lineno):
        self._card = Card(line=lineno)
        self.cards.append(self._card)
        self._buffer = None

    def _continue(self, text):
        if self._buffer == "q":
            self._card.question += "\n" + text
        elif self._buffer == "a":
            self._card.answer += "\n" + text


def parse_cards(path):
    parser = Parser()
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            parser.feed(lineno, line)
    return parser.deck, parser.cards


# ---------------------------------------------------------------- converters

def _oneline(text):
    return text.replace("\t", " ").replace("\n", "<br>")


def to_tsv(cards):
    rows = []
    for card in cards:
        tags = " ".join(t.replace(" ", "-") for t in card.tags)
        rows.append(f"{_oneline(card.question)}\t{_oneline(card.answer)}\t{tags}")
    return "\n".join(rows) + "\n"


def to_obsidian(cards, deck):
    topic = deck.strip().replace(" ", "-")
    lines = [f"#flashcards/{topic}", ""]
    for card in cards:
        if card.is_cloze:
            text = CLOZE_RE.sub(lambda m: f"=={m.group(1)}==", card.question)
            lines.append(_oneline(text))
        else:
            lines.append(f"{_oneline(card.question)}::{_oneline(card.answer)}")
        lines.append("")
    return "\n".join(lines)


def _stable_id(name):
    return int(hashlib.sha1(name.encode("utf-8")).hexdigest()[:8], 16)


def to_apkg(cards, deck, out_path):
    """Write an .apkg via genanki. Returns False if genanki is missing."""
    try:
        import genanki
    except ImportError:
        return False

    basic = genanki.Model(
        _stable_id("flashcards-basic"), "Flashcards Basic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
        }],
    )
    cloze = genanki.Model(
        _stable_id("flashcards-cloze"), "Flashcards Cloze",
        fields=[{"name": "Text"}, {"name": "Extra"}],
        templates=[{
            "name": "Cloze",
            "qfmt": "{{cloze:Text}}",
            "afmt": "{{cloze:Text}}<br>{{Extra}}",
        }],
        model_type=genanki.Model.CLOZE,
    )
    anki_deck = genanki.Deck(_stable_id(deck), deck)
    for card in cards:
        tags = [t.replace(" ", "-") for t in card.tags]
        if card.is_cloze:
            note = genanki.Note(model=cloze, fields=[_oneline(card.question), _oneline(card.answer)], tags=tags)
        else:
            note = genanki.Note(model=basic, fields=[_oneline(card.question), _oneline(card.answer)], tags=tags)
        anki_deck.add_note(note)
    genanki.Package(anki_deck).write_to_file(str(out_path))
    return True


# ------------------------------------------------------------------ commands

def cmd_convert(args):
    deck, cards = parse_cards(args.file)
    if args.deck:
        deck = args.deck
    if not cards:
        sys.exit(f"error: no cards found in {args.file}")

    fmt = args.format
    if fmt == "apkg":
        out = Path(args.output or Path(args.file).with_suffix(".apkg"))
        if to_apkg(cards, deck, out):
            print(f"Wrote {len(cards)} cards to {out} (deck: {deck})")
            return
        print("warning: genanki not installed (pip install genanki); "
              "falling back to TSV for Anki File > Import", file=sys.stderr)
        fmt = "tsv"

    content = to_tsv(cards) if fmt == "tsv" else to_obsidian(cards, deck)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Wrote {len(cards)} cards to {args.output} (format: {fmt}, deck: {deck})")
    else:
        sys.stdout.write(content)


def _validate_card(card, index, seen_fronts):
    issues = []
    front = card.question.strip()
    label = f"card {index} (line {card.line})"
    if not front:
        issues.append(f"{label}: empty front")
        return issues
    if not card.answer.strip() and not card.is_cloze:
        issues.append(f"{label}: empty back")
    key = front.lower()
    if key in seen_fronts:
        issues.append(f"{label}: duplicate front (same as card {seen_fronts[key]})")
    else:
        seen_fronts[key] = index
    if len(card.answer.split()) > 60:
        issues.append(f"{label}: answer too long ({len(card.answer.split())} words > 60)")
    if front.lower().startswith(YES_NO_STARTERS):
        issues.append(f"{label}: yes/no question — rephrase as why/how/what")
    return issues


def cmd_validate(args):
    _, cards = parse_cards(args.file)
    seen = {}
    issues = []
    for i, card in enumerate(cards, 1):
        issues.extend(_validate_card(card, i, seen))
    print(f"{len(cards)} cards checked")
    for issue in issues:
        print(f"  WARN {issue}")
    if issues:
        sys.exit(1)
    print("OK: no issues found")


def cmd_stats(args):
    deck, cards = parse_cards(args.file)
    cloze = sum(1 for c in cards if c.is_cloze)
    tag_counts = Counter(t for c in cards for t in c.tags)
    print(f"Deck:  {deck}")
    print(f"Cards: {len(cards)} ({cloze} cloze, {len(cards) - cloze} basic)")
    print("Tags:")
    for tag, count in tag_counts.most_common():
        print(f"  {tag}: {count}")
    if not tag_counts:
        print("  (none)")


def main():
    ap = argparse.ArgumentParser(
        prog="flashcards.py",
        description="Package flashcards (intermediate markdown) for Anki or Obsidian.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    conv = sub.add_parser("convert", help="Convert cards file to apkg/tsv/obsidian")
    conv.add_argument("file", help="Cards markdown file")
    conv.add_argument("--format", required=True, choices=["apkg", "tsv", "obsidian"])
    conv.add_argument("--deck", help="Deck name (overrides '# Deck:' header)")
    conv.add_argument("-o", "--output", help="Output file (default: stdout; apkg: <file>.apkg)")
    conv.set_defaults(func=cmd_convert)

    val = sub.add_parser("validate", help="Lint the cards file")
    val.add_argument("file", help="Cards markdown file")
    val.set_defaults(func=cmd_validate)

    st = sub.add_parser("stats", help="Card, cloze, and per-tag counts")
    st.add_argument("file", help="Cards markdown file")
    st.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
