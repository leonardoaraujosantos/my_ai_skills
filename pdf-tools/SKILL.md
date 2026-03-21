---
name: pdf-tools
description: Manipulate PDFs - merge, split, extract pages, rotate, compress, extract text/images. Use when working with PDF files.
argument-hint: <command> <file> [options]
---

# PDF Tools

## Dependencies

```bash
pip install pypdf
pip install pypdf[image]  # For image extraction
```

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/pdf-tools"
```

## Commands

```bash
python3 "$SKILL_DIR/pdf_tools.py" <command> <file> [options]
```

| Command | Description |
|---------|-------------|
| `info` | Show PDF info (pages, metadata, size) |
| `merge` | Merge multiple PDFs |
| `split` | Split into individual pages |
| `extract` | Extract specific pages |
| `rotate` | Rotate pages |
| `compress` | Compress PDF |
| `text` | Extract text |
| `images` | Extract images |
| `metadata` | Show metadata |
| `encrypt` | Add password protection |
| `decrypt` | Remove password |

## Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output file/directory |
| `-p, --pages <range>` | Page range (e.g., "1-5", "1,3,5") |
| `-a, --angle <deg>` | Rotation angle (90, 180, 270) |
| `--password <pwd>` | Password for encrypt/decrypt |

## Examples

```bash
# View PDF info
python3 "$SKILL_DIR/pdf_tools.py" info document.pdf

# Merge PDFs
python3 "$SKILL_DIR/pdf_tools.py" merge file1.pdf file2.pdf file3.pdf -o combined.pdf

# Split into pages
python3 "$SKILL_DIR/pdf_tools.py" split document.pdf -o pages/

# Extract pages 1-5
python3 "$SKILL_DIR/pdf_tools.py" extract document.pdf -p 1-5 -o extract.pdf

# Extract specific pages
python3 "$SKILL_DIR/pdf_tools.py" extract document.pdf -p "1,3,5,10-15" -o selected.pdf

# Rotate 90 degrees
python3 "$SKILL_DIR/pdf_tools.py" rotate document.pdf -a 90 -o rotated.pdf

# Compress PDF
python3 "$SKILL_DIR/pdf_tools.py" compress large.pdf -o smaller.pdf

# Extract text
python3 "$SKILL_DIR/pdf_tools.py" text document.pdf -o content.txt

# Extract images
python3 "$SKILL_DIR/pdf_tools.py" images document.pdf -o images/

# Encrypt with password
python3 "$SKILL_DIR/pdf_tools.py" encrypt document.pdf --password secret -o protected.pdf

# Decrypt
python3 "$SKILL_DIR/pdf_tools.py" decrypt protected.pdf --password secret -o unlocked.pdf
```
