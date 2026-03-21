#!/usr/bin/env python3
"""
PDF to Markdown Converter

A tool that converts PDF files to Markdown format, preserving text structure,
headings, and extracting images.
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install it with: pip install pymupdf")
    sys.exit(1)


def clean_text(text: str) -> str:
    """Clean and normalize text extracted from PDF."""
    # Remove excessive whitespace while preserving paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove trailing whitespace from lines
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    # Fix common PDF extraction artifacts
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)  # Join hyphenated words
    return text.strip()


def detect_heading(text: str, font_size: float, avg_font_size: float) -> int:
    """
    Detect if text is a heading based on font size.
    Returns heading level (1-6) or 0 if not a heading.
    """
    if not text.strip():
        return 0

    size_ratio = font_size / avg_font_size if avg_font_size > 0 else 1

    if size_ratio > 1.8:
        return 1
    elif size_ratio > 1.5:
        return 2
    elif size_ratio > 1.3:
        return 3
    elif size_ratio > 1.15:
        return 4
    return 0


def extract_images(page: fitz.Page, page_num: int, output_dir: Path) -> list[str]:
    """Extract images from a PDF page and save them."""
    images_md = []
    image_list = page.get_images()

    for img_index, img in enumerate(image_list):
        xref = img[0]
        try:
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            # Create images directory
            images_dir = output_dir / "images"
            images_dir.mkdir(exist_ok=True)

            # Save image
            image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
            image_path = images_dir / image_filename

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # Add markdown reference
            images_md.append(f"![Image {img_index + 1}](images/{image_filename})")
        except Exception as e:
            print(f"Warning: Could not extract image {img_index + 1} from page {page_num + 1}: {e}")

    return images_md


def analyze_font_sizes(doc: fitz.Document) -> float:
    """Analyze the document to find the average font size."""
    font_sizes = []

    for page_num in range(min(10, len(doc))):  # Sample first 10 pages
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            font_sizes.append(span["size"])

    if font_sizes:
        return sum(font_sizes) / len(font_sizes)
    return 12.0  # Default font size


def convert_page_to_markdown(page: fitz.Page, page_num: int, avg_font_size: float,
                              output_dir: Path, extract_imgs: bool) -> str:
    """Convert a single PDF page to Markdown."""
    markdown_parts = []

    # Extract images if requested
    if extract_imgs:
        images = extract_images(page, page_num, output_dir)
        if images:
            markdown_parts.extend(images)
            markdown_parts.append("")

    # Get text with formatting info
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if "lines" not in block:
            continue

        block_text = []
        for line in block["lines"]:
            line_text = ""
            line_font_size = 0

            for span in line["spans"]:
                text = span["text"]
                font_size = span["size"]
                flags = span["flags"]

                if text.strip():
                    line_font_size = max(line_font_size, font_size)

                    # Apply formatting based on font flags
                    is_bold = flags & 2**4  # Bold
                    is_italic = flags & 2**1  # Italic

                    if is_bold and is_italic:
                        text = f"***{text}***"
                    elif is_bold:
                        text = f"**{text}**"
                    elif is_italic:
                        text = f"*{text}*"

                    line_text += text

            if line_text.strip():
                heading_level = detect_heading(line_text, line_font_size, avg_font_size)

                if heading_level > 0:
                    # Remove any existing bold/italic from headings
                    clean_heading = re.sub(r'\*+([^*]+)\*+', r'\1', line_text)
                    line_text = "#" * heading_level + " " + clean_heading.strip()

                block_text.append(line_text)

        if block_text:
            markdown_parts.append(" ".join(block_text))

    return "\n\n".join(markdown_parts)


def pdf_to_markdown(pdf_path: str, output_path: str = None,
                    extract_images: bool = True,
                    page_range: tuple = None) -> str:
    """
    Convert a PDF file to Markdown format.

    Args:
        pdf_path: Path to the input PDF file
        output_path: Path for the output Markdown file (optional)
        extract_images: Whether to extract and include images
        page_range: Tuple of (start_page, end_page) for partial conversion (1-indexed)

    Returns:
        The generated Markdown content
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Determine output path
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = pdf_path.with_suffix('.md')

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting: {pdf_path}")
    print(f"Output: {output_path}")

    # Open PDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"Total pages: {total_pages}")

    # Determine page range
    start_page = 0
    end_page = total_pages

    if page_range:
        start_page = max(0, page_range[0] - 1)
        end_page = min(total_pages, page_range[1])

    # Analyze font sizes for heading detection
    avg_font_size = analyze_font_sizes(doc)
    print(f"Average font size: {avg_font_size:.2f}")

    # Convert pages
    markdown_content = []
    markdown_content.append(f"# {pdf_path.stem}\n")
    markdown_content.append(f"*Converted from PDF - {total_pages} pages*\n")
    markdown_content.append("---\n")

    for page_num in range(start_page, end_page):
        print(f"Processing page {page_num + 1}/{end_page}...", end='\r')

        page = doc[page_num]
        page_md = convert_page_to_markdown(
            page, page_num, avg_font_size, output_dir, extract_images
        )

        if page_md.strip():
            markdown_content.append(f"\n<!-- Page {page_num + 1} -->\n")
            markdown_content.append(page_md)

    print(f"\nProcessed {end_page - start_page} pages.")

    doc.close()

    # Join and clean content
    final_content = "\n".join(markdown_content)
    final_content = clean_text(final_content)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Markdown saved to: {output_path}")

    return final_content


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to Markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_to_markdown.py document.pdf
  python pdf_to_markdown.py document.pdf -o output.md
  python pdf_to_markdown.py document.pdf --pages 1-10
  python pdf_to_markdown.py document.pdf --no-images
        """
    )

    parser.add_argument("pdf_file", help="Path to the PDF file to convert")
    parser.add_argument("-o", "--output", help="Output Markdown file path")
    parser.add_argument("--no-images", action="store_true",
                        help="Skip image extraction")
    parser.add_argument("--pages", help="Page range to convert (e.g., '1-10')")

    args = parser.parse_args()

    # Parse page range
    page_range = None
    if args.pages:
        try:
            parts = args.pages.split('-')
            if len(parts) == 2:
                page_range = (int(parts[0]), int(parts[1]))
            else:
                page_range = (int(parts[0]), int(parts[0]))
        except ValueError:
            print(f"Invalid page range: {args.pages}")
            sys.exit(1)

    try:
        pdf_to_markdown(
            args.pdf_file,
            output_path=args.output,
            extract_images=not args.no_images,
            page_range=page_range
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
