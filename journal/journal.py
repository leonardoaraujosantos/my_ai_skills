#!/usr/bin/env python3
"""
Journal - Daily journaling with templates to Obsidian vault.

Usage:
    python journal.py <command> [options]

Commands:
    today       Open/create today's journal entry
    add         Add entry to today's journal
    week        Show this week's entries
    month       Show this month's entries
    search      Search journal entries
    stats       Show journaling statistics
    prompts     Show writing prompts

Options:
    -t, --text <text>       Text to add
    -m, --mood <mood>       Mood (great/good/okay/bad)
    -e, --energy <1-5>      Energy level
    --tags <tags>           Tags (comma-separated)
    -s, --section <section> Section: morning, afternoon, evening, gratitude, reflection
    -q, --query <query>     Search query
    -d, --date <YYYY-MM-DD> Specific date

Examples:
    python journal.py today
    python journal.py add -t "Had a productive meeting about the new project"
    python journal.py add -t "Feeling accomplished" -m great -e 5
    python journal.py add -t "Grateful for good weather" -s gratitude
    python journal.py week
    python journal.py search -q "project meeting"
    python journal.py stats
"""

import sys
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import random

# Configuration
OBSIDIAN_VAULT = Path("/Users/leonardoaraujo/Library/Mobile Documents/iCloud~md~obsidian/Documents/Leo Knowledge")
JOURNAL_DIR = OBSIDIAN_VAULT / "Journal"
DAILY_DIR = JOURNAL_DIR / "Daily"

# Mood emojis
MOODS = {
    'great': '😄',
    'good': '🙂',
    'okay': '😐',
    'bad': '😔',
    'terrible': '😢'
}

# Energy levels
ENERGY = {
    1: '🔋',
    2: '🔋🔋',
    3: '🔋🔋🔋',
    4: '🔋🔋🔋🔋',
    5: '🔋🔋🔋🔋🔋'
}

# Writing prompts
PROMPTS = [
    "What am I grateful for today?",
    "What's one thing I learned today?",
    "What challenged me today and how did I handle it?",
    "What made me smile today?",
    "What could I have done differently today?",
    "What am I looking forward to tomorrow?",
    "Who made a positive impact on my day?",
    "What's one thing I accomplished today?",
    "How did I take care of myself today?",
    "What's on my mind right now?",
    "What fear did I face today?",
    "What inspired me today?",
    "What conversation stood out today?",
    "How did I grow today?",
    "What would I tell my past self about today?"
]


def ensure_dirs():
    """Ensure journal directories exist."""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)


def get_journal_path(date=None):
    """Get the path for a journal entry."""
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    year_month = date.strftime("%Y-%m")
    month_dir = DAILY_DIR / year_month
    month_dir.mkdir(parents=True, exist_ok=True)

    filename = date.strftime("%Y-%m-%d") + ".md"
    return month_dir / filename


def create_journal_template(date=None):
    """Create a new journal entry with template."""
    if date is None:
        date = datetime.now()

    weekday = date.strftime("%A")
    formatted_date = date.strftime("%B %d, %Y")
    iso_date = date.strftime("%Y-%m-%d")

    # Get a random prompt
    prompt = random.choice(PROMPTS)

    template = f"""---
date: {iso_date}
weekday: {weekday}
mood:
energy:
tags: [journal, daily]
---

# {weekday}, {formatted_date}

## Morning

*How am I starting the day?*



## Tasks & Goals

- [ ]
- [ ]
- [ ]

## Journal

*{prompt}*



## Gratitude

1.
2.
3.

## Evening Reflection

*How was today overall?*



---

#journal #daily #{date.strftime('%Y-%m')}
"""
    return template


def cmd_today(date=None):
    """Open or create today's journal entry."""
    ensure_dirs()

    path = get_journal_path(date)

    if not path.exists():
        content = create_journal_template(datetime.strptime(date, "%Y-%m-%d") if date else None)
        path.write_text(content, encoding='utf-8')
        print(f"Created new journal entry: {path.relative_to(OBSIDIAN_VAULT)}")
    else:
        print(f"Journal entry exists: {path.relative_to(OBSIDIAN_VAULT)}")

    # Show the content
    content = path.read_text(encoding='utf-8')
    print("\n" + "=" * 50)
    print(content)

    return path


def cmd_add(text, mood=None, energy=None, section=None, tags=None, date=None):
    """Add entry to journal."""
    ensure_dirs()

    path = get_journal_path(date)

    # Create if doesn't exist
    if not path.exists():
        content = create_journal_template(datetime.strptime(date, "%Y-%m-%d") if date else None)
        path.write_text(content, encoding='utf-8')

    content = path.read_text(encoding='utf-8')
    now = datetime.now().strftime("%H:%M")

    # Build entry
    entry_parts = [f"\n**{now}**"]

    if mood and mood in MOODS:
        entry_parts.append(f" {MOODS[mood]}")

    if energy and 1 <= energy <= 5:
        entry_parts.append(f" {ENERGY[energy]}")

    entry_parts.append(f"\n{text}\n")

    entry = "".join(entry_parts)

    # Find section to add to
    if section:
        section_map = {
            'morning': '## Morning',
            'afternoon': '## Journal',
            'evening': '## Evening Reflection',
            'gratitude': '## Gratitude',
            'reflection': '## Evening Reflection',
            'tasks': '## Tasks & Goals',
            'journal': '## Journal'
        }
        section_header = section_map.get(section.lower(), '## Journal')

        if section_header in content:
            # Find the section and add after it
            parts = content.split(section_header)
            if len(parts) >= 2:
                # Find next section
                next_section = re.search(r'\n## ', parts[1])
                if next_section:
                    insert_pos = next_section.start()
                    parts[1] = parts[1][:insert_pos] + entry + parts[1][insert_pos:]
                else:
                    parts[1] = parts[1].rstrip() + entry + "\n"
                content = section_header.join(parts)
        else:
            # Just append to end
            content = content.rstrip() + "\n" + entry
    else:
        # Add to Journal section by default
        if '## Journal' in content:
            parts = content.split('## Journal')
            if len(parts) >= 2:
                next_section = re.search(r'\n## ', parts[1])
                if next_section:
                    insert_pos = next_section.start()
                    parts[1] = parts[1][:insert_pos] + entry + parts[1][insert_pos:]
                else:
                    parts[1] = parts[1].rstrip() + entry + "\n"
                content = '## Journal'.join(parts)
        else:
            content = content.rstrip() + "\n" + entry

    # Update mood and energy in frontmatter if provided
    if mood and mood in MOODS:
        content = re.sub(r'^mood:\s*$', f'mood: {mood}', content, flags=re.MULTILINE)

    if energy and 1 <= energy <= 5:
        content = re.sub(r'^energy:\s*$', f'energy: {energy}', content, flags=re.MULTILINE)

    path.write_text(content, encoding='utf-8')
    print(f"Added to journal: {path.relative_to(OBSIDIAN_VAULT)}")
    print(f"Entry: {text[:50]}{'...' if len(text) > 50 else ''}")


def cmd_week():
    """Show this week's entries."""
    ensure_dirs()

    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())

    print(f"Journal entries for week of {start_of_week.strftime('%B %d, %Y')}:\n")

    for i in range(7):
        date = start_of_week + timedelta(days=i)
        path = get_journal_path(date)

        weekday = date.strftime("%A")
        date_str = date.strftime("%Y-%m-%d")

        if path.exists():
            content = path.read_text(encoding='utf-8')

            # Extract mood
            mood_match = re.search(r'^mood:\s*(\w+)', content, re.MULTILINE)
            mood = mood_match.group(1) if mood_match else None
            mood_emoji = MOODS.get(mood, '  ') if mood else '  '

            # Count words (rough estimate)
            word_count = len(content.split())

            marker = "→" if date.date() == today.date() else " "
            print(f"{marker} {weekday:<10} {date_str}  {mood_emoji}  ({word_count} words)")
        else:
            marker = "→" if date.date() == today.date() else " "
            print(f"{marker} {weekday:<10} {date_str}  --  (no entry)")


def cmd_month(year_month=None):
    """Show this month's entries."""
    ensure_dirs()

    if year_month:
        year, month = year_month.split('-')
        start_date = datetime(int(year), int(month), 1)
    else:
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)

    month_dir = DAILY_DIR / start_date.strftime("%Y-%m")

    print(f"Journal entries for {start_date.strftime('%B %Y')}:\n")

    if not month_dir.exists():
        print("No entries this month.")
        return

    entries = sorted(month_dir.glob("*.md"))
    total_words = 0

    for path in entries:
        content = path.read_text(encoding='utf-8')
        date_str = path.stem

        # Extract mood
        mood_match = re.search(r'^mood:\s*(\w+)', content, re.MULTILINE)
        mood = mood_match.group(1) if mood_match else None
        mood_emoji = MOODS.get(mood, '  ') if mood else '  '

        word_count = len(content.split())
        total_words += word_count

        print(f"  {date_str}  {mood_emoji}  ({word_count} words)")

    print(f"\nTotal: {len(entries)} entries, ~{total_words} words")


def cmd_search(query):
    """Search journal entries."""
    ensure_dirs()

    query = query.lower()
    results = []

    for path in DAILY_DIR.rglob("*.md"):
        content = path.read_text(encoding='utf-8')

        if query in content.lower():
            # Find matching lines
            lines = content.split('\n')
            matches = [l.strip() for l in lines if query in l.lower() and not l.startswith('---')]

            results.append({
                'date': path.stem,
                'matches': matches[:3]  # Limit to 3 matches per file
            })

    if results:
        results.sort(key=lambda x: x['date'], reverse=True)
        print(f"Found {len(results)} entries matching '{query}':\n")

        for r in results[:10]:  # Limit to 10 results
            print(f"  {r['date']}:")
            for m in r['matches']:
                # Highlight query in match
                print(f"    ...{m[:80]}{'...' if len(m) > 80 else ''}")
            print()
    else:
        print(f"No entries found matching '{query}'")


def cmd_stats():
    """Show journaling statistics."""
    ensure_dirs()

    total_entries = 0
    total_words = 0
    mood_counts = {m: 0 for m in MOODS}
    entries_by_month = {}

    for path in DAILY_DIR.rglob("*.md"):
        total_entries += 1
        content = path.read_text(encoding='utf-8')
        total_words += len(content.split())

        # Count moods
        mood_match = re.search(r'^mood:\s*(\w+)', content, re.MULTILINE)
        if mood_match and mood_match.group(1) in MOODS:
            mood_counts[mood_match.group(1)] += 1

        # Count by month
        month = path.parent.name
        entries_by_month[month] = entries_by_month.get(month, 0) + 1

    print("Journal Statistics\n")
    print(f"Total entries:    {total_entries}")
    print(f"Total words:      ~{total_words}")
    print(f"Avg words/entry:  ~{total_words // total_entries if total_entries else 0}")

    # Streak calculation
    today = datetime.now().date()
    streak = 0
    check_date = today
    while True:
        path = get_journal_path(check_date.strftime("%Y-%m-%d"))
        if path.exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    print(f"Current streak:   {streak} days")

    print("\nMood distribution:")
    for mood, count in mood_counts.items():
        if count > 0:
            bar = '█' * (count * 2)
            print(f"  {MOODS[mood]} {mood:<8} {bar} {count}")

    print("\nEntries by month:")
    for month in sorted(entries_by_month.keys(), reverse=True)[:6]:
        count = entries_by_month[month]
        bar = '█' * count
        print(f"  {month}: {bar} {count}")


def cmd_prompts(count=5):
    """Show random writing prompts."""
    print("Writing Prompts:\n")
    selected = random.sample(PROMPTS, min(count, len(PROMPTS)))
    for i, prompt in enumerate(selected, 1):
        print(f"  {i}. {prompt}")


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Parse arguments
    text = None
    mood = None
    energy = None
    section = None
    tags = None
    date = None
    query = None

    i = 0
    while i < len(args):
        if args[i] in ['-t', '--text'] and i + 1 < len(args):
            text = args[i + 1]
            i += 2
        elif args[i] in ['-m', '--mood'] and i + 1 < len(args):
            mood = args[i + 1].lower()
            i += 2
        elif args[i] in ['-e', '--energy'] and i + 1 < len(args):
            energy = int(args[i + 1])
            i += 2
        elif args[i] in ['-s', '--section'] and i + 1 < len(args):
            section = args[i + 1]
            i += 2
        elif args[i] == '--tags' and i + 1 < len(args):
            tags = args[i + 1]
            i += 2
        elif args[i] in ['-d', '--date'] and i + 1 < len(args):
            date = args[i + 1]
            i += 2
        elif args[i] in ['-q', '--query'] and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        else:
            # Might be text directly
            if not args[i].startswith('-'):
                text = args[i]
            i += 1

    # Execute command
    if cmd == 'today':
        cmd_today(date)
    elif cmd == 'add':
        if not text:
            print("Error: Text required (-t/--text)")
            return
        cmd_add(text, mood, energy, section, tags, date)
    elif cmd == 'week':
        cmd_week()
    elif cmd == 'month':
        cmd_month(date)
    elif cmd == 'search':
        if not query:
            print("Error: Query required (-q/--query)")
            return
        cmd_search(query)
    elif cmd == 'stats':
        cmd_stats()
    elif cmd == 'prompts':
        cmd_prompts()
    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
