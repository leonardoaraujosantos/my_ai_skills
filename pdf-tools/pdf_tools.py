#!/usr/bin/env python3
"""
PDF Tools - Manipulate PDF files from the command line.

Usage:
    python pdf_tools.py <command> <file(s)> [options]

Commands:
    info        Show PDF information (pages, metadata)
    merge       Merge multiple PDFs into one
    split       Split PDF into individual pages
    extract     Extract specific pages
    rotate      Rotate pages
    compress    Compress PDF (reduce file size)
    text        Extract text from PDF
    images      Extract images from PDF
    metadata    Show/edit metadata
    encrypt     Add password protection
    decrypt     Remove password protection
    create      Create PDF from Markdown file (requires pandoc)

Options:
    -o, --output <file>     Output file
    -p, --pages <range>     Page range (e.g., "1-5", "1,3,5", "1-3,7-9")
    -a, --angle <degrees>   Rotation angle (90, 180, 270)
    --password <pwd>        Password for encryption/decryption
    -q, --quality <level>   Compression quality (low, medium, high)

Examples:
    python pdf_tools.py info document.pdf
    python pdf_tools.py merge file1.pdf file2.pdf -o combined.pdf
    python pdf_tools.py split document.pdf -o pages/
    python pdf_tools.py extract document.pdf -p 1-5 -o extract.pdf
    python pdf_tools.py rotate document.pdf -a 90 -o rotated.pdf
    python pdf_tools.py text document.pdf -o text.txt
    python pdf_tools.py compress document.pdf -o smaller.pdf

Dependencies:
    pip install pypdf
    pip install pypdf[image]  # For image extraction
"""

import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False


def check_dependency():
    """Check if pypdf is installed."""
    if not HAS_PYPDF:
        print("Error: pypdf not installed. Run: pip install pypdf")
        sys.exit(1)


def parse_page_range(page_str, total_pages):
    """Parse page range string into list of page numbers (0-indexed)."""
    pages = []
    parts = page_str.split(',')

    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            start = int(start) - 1  # Convert to 0-indexed
            end = int(end) - 1
            pages.extend(range(start, min(end + 1, total_pages)))
        else:
            page = int(part) - 1
            if 0 <= page < total_pages:
                pages.append(page)

    return sorted(set(pages))


def format_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def cmd_info(pdf_path):
    """Show PDF information."""
    check_dependency()

    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: File not found: {pdf_path}")
        return

    reader = PdfReader(pdf_path)

    print(f"File:       {path.name}")
    print(f"Size:       {format_size(path.stat().st_size)}")
    print(f"Pages:      {len(reader.pages)}")

    # Page dimensions (first page)
    if reader.pages:
        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        # Convert points to inches (72 points per inch)
        print(f"Page Size:  {width:.0f} x {height:.0f} pts ({width/72:.1f}\" x {height/72:.1f}\")")

    # Metadata
    meta = reader.metadata
    if meta:
        print("\nMetadata:")
        if meta.title:
            print(f"  Title:    {meta.title}")
        if meta.author:
            print(f"  Author:   {meta.author}")
        if meta.subject:
            print(f"  Subject:  {meta.subject}")
        if meta.creator:
            print(f"  Creator:  {meta.creator}")
        if meta.producer:
            print(f"  Producer: {meta.producer}")

    # Check encryption
    if reader.is_encrypted:
        print("\nEncrypted:  Yes")
    else:
        print("\nEncrypted:  No")


def cmd_merge(pdf_files, output):
    """Merge multiple PDFs."""
    check_dependency()

    if len(pdf_files) < 2:
        print("Error: Need at least 2 PDF files to merge")
        return

    writer = PdfWriter()

    for pdf in pdf_files:
        if not Path(pdf).exists():
            print(f"Error: File not found: {pdf}")
            return
        print(f"Adding: {pdf}")
        reader = PdfReader(pdf)
        for page in reader.pages:
            writer.add_page(page)

    output = output or "merged.pdf"
    with open(output, 'wb') as f:
        writer.write(f)

    print(f"\nMerged {len(pdf_files)} files into: {output}")


def cmd_split(pdf_path, output_dir):
    """Split PDF into individual pages."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    reader = PdfReader(pdf_path)
    output_dir = Path(output_dir or "pages")
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(pdf_path).stem

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = output_dir / f"{base_name}_page_{i+1:03d}.pdf"
        with open(output_path, 'wb') as f:
            writer.write(f)
        print(f"Created: {output_path}")

    print(f"\nSplit into {len(reader.pages)} pages in: {output_dir}")


def cmd_extract(pdf_path, pages, output):
    """Extract specific pages."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    if not pages:
        print("Error: Page range required (-p/--pages)")
        return

    reader = PdfReader(pdf_path)
    page_nums = parse_page_range(pages, len(reader.pages))

    if not page_nums:
        print("Error: No valid pages in range")
        return

    writer = PdfWriter()
    for page_num in page_nums:
        writer.add_page(reader.pages[page_num])

    output = output or f"{Path(pdf_path).stem}_extracted.pdf"
    with open(output, 'wb') as f:
        writer.write(f)

    print(f"Extracted pages {pages} to: {output}")


def cmd_rotate(pdf_path, angle, output, pages=None):
    """Rotate pages."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    if angle not in [90, 180, 270, -90, -180, -270]:
        print("Error: Angle must be 90, 180, or 270 degrees")
        return

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    if pages:
        page_nums = set(parse_page_range(pages, len(reader.pages)))
    else:
        page_nums = set(range(len(reader.pages)))

    for i, page in enumerate(reader.pages):
        if i in page_nums:
            page.rotate(angle)
        writer.add_page(page)

    output = output or f"{Path(pdf_path).stem}_rotated.pdf"
    with open(output, 'wb') as f:
        writer.write(f)

    print(f"Rotated {len(page_nums)} page(s) by {angle}° to: {output}")


def cmd_text(pdf_path, output=None):
    """Extract text from PDF."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    reader = PdfReader(pdf_path)
    text_content = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            text_content.append(f"--- Page {i+1} ---\n{text}\n")

    full_text = "\n".join(text_content)

    if output:
        Path(output).write_text(full_text, encoding='utf-8')
        print(f"Extracted text to: {output}")
    else:
        print(full_text)


def cmd_compress(pdf_path, output, quality='medium'):
    """Compress PDF."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Compress content streams
    for page in writer.pages:
        page.compress_content_streams()

    output = output or f"{Path(pdf_path).stem}_compressed.pdf"
    with open(output, 'wb') as f:
        writer.write(f)

    original_size = Path(pdf_path).stat().st_size
    new_size = Path(output).stat().st_size
    reduction = (1 - new_size / original_size) * 100

    print(f"Original:   {format_size(original_size)}")
    print(f"Compressed: {format_size(new_size)}")
    print(f"Reduction:  {reduction:.1f}%")
    print(f"Saved to:   {output}")


def cmd_images(pdf_path, output_dir):
    """Extract images from PDF."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    try:
        from PIL import Image
        import io
    except ImportError:
        print("Error: Pillow required for image extraction. Run: pip install Pillow")
        return

    reader = PdfReader(pdf_path)
    output_dir = Path(output_dir or "images")
    output_dir.mkdir(parents=True, exist_ok=True)

    image_count = 0

    for page_num, page in enumerate(reader.pages):
        if '/XObject' in page['/Resources']:
            xobjects = page['/Resources']['/XObject'].get_object()

            for obj_name in xobjects:
                obj = xobjects[obj_name]
                if obj['/Subtype'] == '/Image':
                    image_count += 1

                    # Get image data
                    if '/Filter' in obj:
                        if obj['/Filter'] == '/DCTDecode':
                            ext = 'jpg'
                        elif obj['/Filter'] == '/FlateDecode':
                            ext = 'png'
                        else:
                            ext = 'png'
                    else:
                        ext = 'png'

                    output_path = output_dir / f"image_{page_num+1}_{image_count:03d}.{ext}"

                    try:
                        data = obj.get_data()
                        with open(output_path, 'wb') as f:
                            f.write(data)
                        print(f"Extracted: {output_path}")
                    except Exception as e:
                        print(f"Could not extract image {image_count}: {e}")

    if image_count == 0:
        print("No images found in PDF")
    else:
        print(f"\nExtracted {image_count} image(s) to: {output_dir}")


def cmd_encrypt(pdf_path, password, output):
    """Encrypt PDF with password."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    if not password:
        print("Error: Password required (--password)")
        return

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password)

    output = output or f"{Path(pdf_path).stem}_encrypted.pdf"
    with open(output, 'wb') as f:
        writer.write(f)

    print(f"Encrypted PDF saved to: {output}")


def cmd_decrypt(pdf_path, password, output):
    """Decrypt PDF."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    if not password:
        print("Error: Password required (--password)")
        return

    reader = PdfReader(pdf_path)

    if reader.is_encrypted:
        reader.decrypt(password)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    output = output or f"{Path(pdf_path).stem}_decrypted.pdf"
    with open(output, 'wb') as f:
        writer.write(f)

    print(f"Decrypted PDF saved to: {output}")


def cmd_metadata(pdf_path):
    """Show PDF metadata."""
    check_dependency()

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return

    reader = PdfReader(pdf_path)
    meta = reader.metadata

    if meta:
        print("PDF Metadata:")
        print("-" * 40)
        for key in meta:
            value = meta[key]
            if value:
                # Clean up key name
                clean_key = key.replace('/', '').replace('dc:', '').replace('pdf:', '')
                print(f"{clean_key}: {value}")
    else:
        print("No metadata found")


def cmd_create(md_path, output=None):
    """Create PDF from Markdown file.

    Tries pandoc first (best quality with LaTeX tables and formatting).
    Falls back to fpdf2 if pandoc is not available.
    """
    import shutil
    import subprocess

    md_path = Path(md_path)
    if not md_path.exists():
        print(f"Error: File not found: {md_path}")
        return

    if output is None:
        output = str(md_path.with_suffix('.pdf'))

    # Try pandoc first (best quality)
    if shutil.which('pandoc'):
        try:
            cmd = [
                'pandoc', str(md_path), '-o', output,
                '-V', 'geometry:margin=2cm',
                '-V', 'fontsize=11pt',
                '-V', 'colorlinks=true',
                '-V', 'linkcolor=blue',
                '-V', 'urlcolor=blue',
            ]
            # Use pdflatex if available for best table rendering
            if shutil.which('pdflatex'):
                cmd.extend(['--pdf-engine=pdflatex'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                size = Path(output).stat().st_size
                print(f"Created: {output} ({size / 1024:.1f} KB) [pandoc]")
                return
            else:
                print(f"Pandoc warning: {result.stderr.strip()}, trying fallback...")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Pandoc failed, trying fallback...")

    # Fallback: fpdf2 (pure Python, no external deps beyond pip)
    try:
        from fpdf import FPDF
    except ImportError:
        print("Error: Neither pandoc nor fpdf2 available.")
        print("Install one of:")
        print("  brew install pandoc       # Best quality (LaTeX tables)")
        print("  pip install fpdf2         # Pure Python fallback")
        return

    content = md_path.read_text(encoding='utf-8')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Try to use a Unicode-capable font
    try:
        pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
        default_font = 'DejaVu'
    except Exception:
        default_font = 'Helvetica'

    pdf.set_font(default_font, size=11)

    for line in content.split('\n'):
        stripped = line.strip()

        # Skip YAML frontmatter
        if stripped == '---':
            continue

        # Headers
        if stripped.startswith('# ') and not stripped.startswith('##'):
            pdf.set_font(default_font, 'B', 18)
            pdf.cell(0, 12, stripped[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)
            pdf.set_font(default_font, size=11)
        elif stripped.startswith('## '):
            pdf.set_font(default_font, 'B', 15)
            pdf.cell(0, 10, stripped[3:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
            pdf.set_font(default_font, size=11)
        elif stripped.startswith('### '):
            pdf.set_font(default_font, 'B', 13)
            pdf.cell(0, 9, stripped[4:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            pdf.set_font(default_font, size=11)
        elif stripped.startswith('- **') or stripped.startswith('* **'):
            # Bold list items
            pdf.cell(5)
            text = stripped[2:] if stripped.startswith('- ') else stripped[2:]
            pdf.multi_cell(0, 6, f"  {text}")
            pdf.ln(1)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            pdf.cell(5)
            pdf.multi_cell(0, 6, f"  {stripped}")
            pdf.ln(1)
        elif stripped.startswith('```'):
            # Code block markers — skip
            continue
        elif stripped.startswith('|') and '|' in stripped[1:]:
            # Table row — render as fixed-width text
            pdf.set_font('Courier', size=8)
            pdf.cell(0, 5, stripped, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(default_font, size=11)
        elif stripped == '':
            pdf.ln(3)
        elif stripped == '\\newpage':
            pdf.add_page()
        else:
            pdf.multi_cell(0, 6, stripped)
            pdf.ln(1)

    pdf.output(output)
    size = Path(output).stat().st_size
    print(f"Created: {output} ({size / 1024:.1f} KB) [fpdf2]")


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Parse arguments
    files = []
    output = None
    pages = None
    angle = None
    password = None
    quality = 'medium'

    i = 0
    while i < len(args):
        if args[i] in ['-o', '--output'] and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif args[i] in ['-p', '--pages'] and i + 1 < len(args):
            pages = args[i + 1]
            i += 2
        elif args[i] in ['-a', '--angle'] and i + 1 < len(args):
            angle = int(args[i + 1])
            i += 2
        elif args[i] == '--password' and i + 1 < len(args):
            password = args[i + 1]
            i += 2
        elif args[i] in ['-q', '--quality'] and i + 1 < len(args):
            quality = args[i + 1]
            i += 2
        elif not args[i].startswith('-'):
            files.append(args[i])
            i += 1
        else:
            i += 1

    # Execute command
    if cmd == 'info':
        if files:
            cmd_info(files[0])
        else:
            print("Error: PDF file required")

    elif cmd == 'merge':
        cmd_merge(files, output)

    elif cmd == 'split':
        if files:
            cmd_split(files[0], output)
        else:
            print("Error: PDF file required")

    elif cmd == 'extract':
        if files:
            cmd_extract(files[0], pages, output)
        else:
            print("Error: PDF file required")

    elif cmd == 'rotate':
        if files and angle:
            cmd_rotate(files[0], angle, output, pages)
        else:
            print("Error: PDF file and angle required")

    elif cmd == 'text':
        if files:
            cmd_text(files[0], output)
        else:
            print("Error: PDF file required")

    elif cmd == 'compress':
        if files:
            cmd_compress(files[0], output, quality)
        else:
            print("Error: PDF file required")

    elif cmd == 'images':
        if files:
            cmd_images(files[0], output)
        else:
            print("Error: PDF file required")

    elif cmd == 'encrypt':
        if files:
            cmd_encrypt(files[0], password, output)
        else:
            print("Error: PDF file required")

    elif cmd == 'decrypt':
        if files:
            cmd_decrypt(files[0], password, output)
        else:
            print("Error: PDF file required")

    elif cmd == 'metadata':
        if files:
            cmd_metadata(files[0])
        else:
            print("Error: PDF file required")

    elif cmd == 'create':
        if files:
            cmd_create(files[0], output)
        else:
            print("Error: Markdown file required")

    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
