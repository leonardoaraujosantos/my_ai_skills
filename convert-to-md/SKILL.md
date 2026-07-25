---
name: convert-to-md
description: Convert PDF or PowerPoint (PPTX) files to Markdown format. Use this skill when the user wants to convert documents to Markdown, extract text from PDFs, or turn presentations into readable text.
argument-hint: <file_path> [--pages 1-10] [--slides 1-10] [--no-images]
---

# Document to Markdown Converter

Converts PDF and PowerPoint (PPTX) files to Markdown format with image extraction.

## Scripts Location

The converter scripts are bundled with this skill:
- `~/.claude/skills/convert-to-md/scripts/pdf_to_markdown.py`
- `~/.claude/skills/convert-to-md/scripts/pptx_to_markdown.py`

## Dependencies

Required: `pip install pymupdf python-pptx`

## Usage

### PDF files
```bash
python ~/.claude/skills/convert-to-md/scripts/pdf_to_markdown.py "<file.pdf>" [options]
```
Options: `-o <output>`, `--pages <range>`, `--no-images`

### PowerPoint files
```bash
python ~/.claude/skills/convert-to-md/scripts/pptx_to_markdown.py "<file.pptx>" [options]
```
Options: `-o <output>`, `--slides <range>`, `--no-images`

## Instructions

When user provides `$ARGUMENTS`:

1. Detect file type by extension (`.pdf` or `.pptx`)
2. Run the appropriate script from `~/.claude/skills/convert-to-md/scripts/`
3. Report: output path, size, pages/slides converted, images extracted
