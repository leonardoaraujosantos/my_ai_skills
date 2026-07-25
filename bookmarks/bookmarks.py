#!/usr/bin/env python3
"""
Bookmarks - Save and manage bookmarks in Obsidian vault.

Usage:
    python bookmarks.py <command> [options]

Commands:
    add         Add a new bookmark
    list        List all bookmarks
    search      Search bookmarks by title/tag/URL
    tags        List all tags
    export      Export bookmarks to JSON/HTML

Options:
    -u, --url <url>         URL to bookmark
    -t, --title <title>     Bookmark title (auto-fetched if not provided)
    -d, --desc <desc>       Description
    --tags <tags>           Tags (comma-separated)
    -c, --category <cat>    Category/folder
    -q, --query <query>     Search query
    -o, --output <file>     Output file for export
    --format <fmt>          Export format: json, html, markdown

Examples:
    python bookmarks.py add -u "https://example.com" --tags "dev,python"
    python bookmarks.py add -u "https://article.com" -t "Great Article" -c "Reading"
    python bookmarks.py list
    python bookmarks.py list -c "Programming"
    python bookmarks.py search -q "python tutorial"
    python bookmarks.py tags
    python bookmarks.py export -o bookmarks.json

Dependencies:
    pip install requests beautifulsoup4
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configuration
OBSIDIAN_VAULT = Path("/Users/leonardoaraujo/work/leo-obsidian-vault")
BOOKMARKS_DIR = OBSIDIAN_VAULT / "Resources" / "Bookmarks"
BOOKMARKS_INDEX = BOOKMARKS_DIR / "_index.md"


def ensure_dirs():
    """Ensure bookmark directories exist."""
    BOOKMARKS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_page_info(url):
    """Fetch title and description from URL."""
    if not HAS_REQUESTS:
        return None, None

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Get title
        title = None
        if soup.title:
            title = soup.title.string
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')

        # Get description
        desc = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content')
        if not desc:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                desc = og_desc.get('content')

        return title, desc
    except Exception as e:
        print(f"Warning: Could not fetch page info: {e}")
        return None, None


def sanitize_filename(name):
    """Sanitize string for use as filename."""
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Limit length
    name = name[:100]
    return name.strip()


def get_domain(url):
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.replace('www.', '')


def create_bookmark_note(url, title, description, tags, category):
    """Create a bookmark note in Obsidian."""
    ensure_dirs()

    # Auto-fetch info if not provided
    if not title or not description:
        fetched_title, fetched_desc = fetch_page_info(url)
        title = title or fetched_title or get_domain(url)
        description = description or fetched_desc or ""

    # Prepare tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else []
    tag_list.append('bookmark')
    tag_str = ' '.join([f'#{t}' for t in tag_list if t])

    # Determine save location
    if category:
        save_dir = BOOKMARKS_DIR / category
        save_dir.mkdir(parents=True, exist_ok=True)
    else:
        save_dir = BOOKMARKS_DIR

    # Create filename
    filename = sanitize_filename(title) + ".md"
    filepath = save_dir / filename

    # Handle duplicate filenames
    counter = 1
    while filepath.exists():
        filename = f"{sanitize_filename(title)}_{counter}.md"
        filepath = save_dir / filename
        counter += 1

    # Create note content
    today = datetime.now().strftime("%Y-%m-%d")
    domain = get_domain(url)

    content = f"""---
url: {url}
domain: {domain}
saved: {today}
tags: [{', '.join(tag_list)}]
---

# {title}

{description}

**URL:** [{url}]({url})
**Saved:** {today}
**Domain:** {domain}

---

## Notes



---

{tag_str}
"""

    # Write file
    filepath.write_text(content, encoding='utf-8')

    # Update index
    update_index(title, url, category, today)

    return filepath


def update_index(title, url, category, date):
    """Update the bookmarks index file."""
    ensure_dirs()

    if not BOOKMARKS_INDEX.exists():
        index_content = """# Bookmarks Index

A collection of saved bookmarks organized by category.

---

## Recent Bookmarks

| Date | Title | Category |
|------|-------|----------|
"""
        BOOKMARKS_INDEX.write_text(index_content, encoding='utf-8')

    # Read existing content
    content = BOOKMARKS_INDEX.read_text(encoding='utf-8')

    # Find the table and add new entry
    table_pattern = r'(\| Date \| Title \| Category \|\n\|------|-------|----------\|)'
    new_row = f"\n| {date} | [{title}]({url}) | {category or 'Uncategorized'} |"

    if re.search(table_pattern, content):
        content = re.sub(table_pattern, r'\1' + new_row, content)
        BOOKMARKS_INDEX.write_text(content, encoding='utf-8')


def list_bookmarks(category=None):
    """List all bookmarks."""
    ensure_dirs()

    bookmarks = []

    # Search directory
    search_dir = BOOKMARKS_DIR / category if category else BOOKMARKS_DIR

    if not search_dir.exists():
        print(f"No bookmarks found in category: {category}")
        return

    for filepath in search_dir.rglob("*.md"):
        if filepath.name.startswith('_'):
            continue

        content = filepath.read_text(encoding='utf-8')

        # Parse frontmatter
        url_match = re.search(r'^url:\s*(.+)$', content, re.MULTILINE)
        saved_match = re.search(r'^saved:\s*(.+)$', content, re.MULTILINE)
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)

        url = url_match.group(1).strip() if url_match else "Unknown"
        saved = saved_match.group(1).strip() if saved_match else "Unknown"
        title = title_match.group(1).strip() if title_match else filepath.stem

        # Get relative category
        rel_path = filepath.relative_to(BOOKMARKS_DIR)
        cat = str(rel_path.parent) if str(rel_path.parent) != '.' else 'Uncategorized'

        bookmarks.append({
            'title': title,
            'url': url,
            'saved': saved,
            'category': cat,
            'path': str(filepath)
        })

    # Sort by date (newest first)
    bookmarks.sort(key=lambda x: x['saved'], reverse=True)

    # Print
    print(f"{'Title':<40} {'Category':<15} {'Saved':<12}")
    print("-" * 70)
    for b in bookmarks:
        title = b['title'][:38] + '..' if len(b['title']) > 40 else b['title']
        print(f"{title:<40} {b['category']:<15} {b['saved']:<12}")

    print(f"\nTotal: {len(bookmarks)} bookmarks")


def search_bookmarks(query):
    """Search bookmarks by title, URL, or tags."""
    ensure_dirs()

    query = query.lower()
    results = []

    for filepath in BOOKMARKS_DIR.rglob("*.md"):
        if filepath.name.startswith('_'):
            continue

        content = filepath.read_text(encoding='utf-8').lower()

        if query in content:
            # Parse info
            url_match = re.search(r'^url:\s*(.+)$', content, re.MULTILINE)
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)

            title = title_match.group(1).strip() if title_match else filepath.stem
            url = url_match.group(1).strip() if url_match else ""

            results.append({'title': title.title(), 'url': url, 'path': str(filepath)})

    if results:
        print(f"Found {len(results)} results for '{query}':\n")
        for r in results:
            print(f"  {r['title']}")
            print(f"  {r['url']}")
            print()
    else:
        print(f"No results found for '{query}'")


def list_tags():
    """List all tags used in bookmarks."""
    ensure_dirs()

    tags = {}

    for filepath in BOOKMARKS_DIR.rglob("*.md"):
        if filepath.name.startswith('_'):
            continue

        content = filepath.read_text(encoding='utf-8')

        # Find tags in frontmatter
        tags_match = re.search(r'^tags:\s*\[([^\]]+)\]', content, re.MULTILINE)
        if tags_match:
            tag_list = [t.strip() for t in tags_match.group(1).split(',')]
            for tag in tag_list:
                tags[tag] = tags.get(tag, 0) + 1

        # Find hashtags in content
        hashtags = re.findall(r'#(\w+)', content)
        for tag in hashtags:
            if tag != 'bookmark':
                tags[tag] = tags.get(tag, 0) + 1

    # Sort by count
    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)

    print("Tags:\n")
    for tag, count in sorted_tags:
        print(f"  #{tag}: {count}")


def export_bookmarks(output, fmt='json'):
    """Export bookmarks to file."""
    ensure_dirs()

    bookmarks = []

    for filepath in BOOKMARKS_DIR.rglob("*.md"):
        if filepath.name.startswith('_'):
            continue

        content = filepath.read_text(encoding='utf-8')

        url_match = re.search(r'^url:\s*(.+)$', content, re.MULTILINE)
        saved_match = re.search(r'^saved:\s*(.+)$', content, re.MULTILINE)
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        tags_match = re.search(r'^tags:\s*\[([^\]]+)\]', content, re.MULTILINE)

        bookmarks.append({
            'title': title_match.group(1).strip() if title_match else filepath.stem,
            'url': url_match.group(1).strip() if url_match else "",
            'saved': saved_match.group(1).strip() if saved_match else "",
            'tags': [t.strip() for t in tags_match.group(1).split(',')] if tags_match else []
        })

    if fmt == 'json':
        output_content = json.dumps(bookmarks, indent=2, ensure_ascii=False)
    elif fmt == 'html':
        lines = ['<!DOCTYPE html><html><head><title>Bookmarks</title></head><body>',
                 '<h1>Bookmarks</h1><ul>']
        for b in bookmarks:
            lines.append(f'<li><a href="{b["url"]}">{b["title"]}</a></li>')
        lines.append('</ul></body></html>')
        output_content = '\n'.join(lines)
    else:  # markdown
        lines = ['# Bookmarks\n']
        for b in bookmarks:
            lines.append(f'- [{b["title"]}]({b["url"]})')
        output_content = '\n'.join(lines)

    Path(output).write_text(output_content, encoding='utf-8')
    print(f"Exported {len(bookmarks)} bookmarks to {output}")


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Parse arguments
    url = None
    title = None
    description = None
    tags = None
    category = None
    query = None
    output = None
    fmt = 'json'

    i = 0
    while i < len(args):
        if args[i] in ['-u', '--url'] and i + 1 < len(args):
            url = args[i + 1]
            i += 2
        elif args[i] in ['-t', '--title'] and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] in ['-d', '--desc'] and i + 1 < len(args):
            description = args[i + 1]
            i += 2
        elif args[i] == '--tags' and i + 1 < len(args):
            tags = args[i + 1]
            i += 2
        elif args[i] in ['-c', '--category'] and i + 1 < len(args):
            category = args[i + 1]
            i += 2
        elif args[i] in ['-q', '--query'] and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        elif args[i] in ['-o', '--output'] and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif args[i] == '--format' and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        else:
            # Might be a URL directly
            if args[i].startswith('http'):
                url = args[i]
            i += 1

    # Execute command
    if cmd == 'add':
        if not url:
            print("Error: URL required (-u/--url)")
            return
        filepath = create_bookmark_note(url, title, description, tags, category)
        print(f"Bookmark saved: {filepath.relative_to(OBSIDIAN_VAULT)}")

    elif cmd == 'list':
        list_bookmarks(category)

    elif cmd == 'search':
        if not query:
            print("Error: Query required (-q/--query)")
            return
        search_bookmarks(query)

    elif cmd == 'tags':
        list_tags()

    elif cmd == 'export':
        if not output:
            print("Error: Output file required (-o/--output)")
            return
        export_bookmarks(output, fmt)

    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
