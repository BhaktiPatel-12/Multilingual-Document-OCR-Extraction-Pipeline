import json
import re
import os
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_JSON = "output/json/input.json"
DEFAULT_TXT = "output/txt/input.txt"
DEFAULT_PDF = "output/txt/searchable_output.pdf"

PAGE_SIZE = A4
LEFT_MARGIN = 16 * mm
RIGHT_MARGIN = 16 * mm
TOP_MARGIN = 15 * mm
BOTTOM_MARGIN = 15 * mm


# ============================================================
# FONT SETUP
# ============================================================

def find_font():
    """
    Find a Unicode font available on Windows/Linux/macOS.

    Noto Sans is preferred because it supports multilingual text.
    DejaVu Sans is used as a fallback.
    """
    candidates = [
        # Windows - Noto
        r"C:\Windows\Fonts\NotoSans-Regular.ttf",
        r"C:\Windows\Fonts\NotoSansGujarati-Regular.ttf",
        r"C:\Windows\Fonts\NotoSansDevanagari-Regular.ttf",

        # Windows - common fallback
        r"C:\Windows\Fonts\DejaVuSans.ttf",

        # Linux
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        # macOS
        "/Library/Fonts/NotoSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


FONT_PATH = find_font()

if FONT_PATH:
    pdfmetrics.registerFont(TTFont("OCRUnicode", FONT_PATH))
    BASE_FONT = "OCRUnicode"
else:
    print(
        "WARNING: No Unicode font was found. "
        "Install Noto Sans or DejaVu Sans for Hindi/Gujarati support."
    )
    BASE_FONT = "Helvetica"


# ============================================================
# INPUT HELPERS
# ============================================================

def load_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()


def get_page_text(page):
    """
    Prefer the final/fused OCR text from the JSON.
    """
    text = page.get("text")

    if text and isinstance(text, str):
        return text.strip()

    lines = page.get("lines", [])
    texts = []

    for line in lines:
        value = line.get("text", "")
        if value:
            texts.append(value)

    return "\n".join(texts).strip()


def get_pages(data, txt_text):
    """
    Build page list from JSON.

    If JSON contains pages, use those.
    Otherwise use TXT separated by page markers.
    """
    pages = data.get("pages", [])

    if pages:
        result = []

        for page in pages:
            result.append({
                "page_number": page.get("page_number", len(result) + 1),
                "language": page.get("language", "unknown"),
                "text": get_page_text(page),
            })

        return result

    # TXT fallback
    chunks = re.split(
        r"={10,}\s*PAGE\s+(\d+)\s*={10,}",
        txt_text,
        flags=re.IGNORECASE,
    )

    result = []

    if len(chunks) > 1:
        # chunks format:
        # ["", "1", "\ntext\n", "2", "\ntext\n", ...]
        i = 1
        while i < len(chunks):
            page_no = int(chunks[i])
            text = chunks[i + 1]
            text = re.sub(r"={10,}\s*END OF DOCUMENT\s*={10,}", "", text)
            result.append({
                "page_number": page_no,
                "language": "unknown",
                "text": text.strip(),
            })
            i += 2

    if result:
        return result

    return [{
        "page_number": 1,
        "language": "unknown",
        "text": txt_text.strip(),
    }]


# ============================================================
# MARKDOWN / OCR PARSING
# ============================================================

def clean_inline_markdown(text):
    """
    Remove Markdown formatting while keeping the actual OCR text.
    """
    text = text.replace("<br>", "\n")
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = text.replace("\\|", "|")
    return text.strip()


def is_separator_row(line):
    """
    Detect Markdown table separator:
    | :--- | :---: | --- |
    """
    stripped = line.strip()
    if "|" not in stripped:
        return False

    cells = [c.strip() for c in stripped.strip("|").split("|")]

    if not cells:
        return False

    return all(
        re.fullmatch(r":?-{2,}:?", cell) is not None
        for cell in cells
    )


def parse_table_row(line):
    """
    Convert:
        | A | B | C |
    into:
        ["A", "B", "C"]
    """
    stripped = line.strip()

    if stripped.startswith("|"):
        stripped = stripped[1:]

    if stripped.endswith("|"):
        stripped = stripped[:-1]

    cells = [clean_inline_markdown(c.strip()) for c in stripped.split("|")]

    return cells


def parse_markdown_table(lines, start):
    """
    Parse a Markdown table beginning at lines[start].

    Returns:
        table_data, next_index
    """
    table_lines = []
    i = start

    while i < len(lines):
        line = lines[i].strip()

        if "|" not in line:
            break

        table_lines.append(line)
        i += 1

    if len(table_lines) < 2:
        return None, start

    rows = [parse_table_row(line) for line in table_lines]

    # Remove separator rows
    rows = [
        row for row, original in zip(rows, table_lines)
        if not is_separator_row(original)
    ]

    if not rows:
        return None, start

    max_cols = max(len(row) for row in rows)

    for row in rows:
        while len(row) < max_cols:
            row.append("")

    return rows, i


def make_paragraph(text, style):
    """
    Escape text safely for ReportLab Paragraph.
    """
    from xml.sax.saxutils import escape

    text = clean_inline_markdown(text)
    text = escape(text)

    # Preserve explicit line breaks
    text = text.replace("\n", "<br/>")

    return Paragraph(text, style)


# ============================================================
# PDF STYLES
# ============================================================

def create_styles():
    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "OCRTitle",
        parent=styles["Title"],
        fontName=BASE_FONT,
        fontSize=22,
        leading=27,
        alignment=TA_CENTER,
        spaceAfter=10,
    )

    heading = ParagraphStyle(
        "OCRHeading",
        parent=styles["Heading1"],
        fontName=BASE_FONT,
        fontSize=16,
        leading=20,
        alignment=TA_LEFT,
        spaceBefore=8,
        spaceAfter=6,
    )

    body = ParagraphStyle(
        "OCRBody",
        parent=styles["BodyText"],
        fontName=BASE_FONT,
        fontSize=10.5,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=5,
    )

    table_header = ParagraphStyle(
        "OCRTableHeader",
        parent=body,
        fontName=BASE_FONT,
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
    )

    table_body = ParagraphStyle(
        "OCRTableBody",
        parent=body,
        fontName=BASE_FONT,
        fontSize=8.5,
        leading=11,
        alignment=TA_LEFT,
    )

    return {
        "title": title,
        "heading": heading,
        "body": body,
        "table_header": table_header,
        "table_body": table_body,
    }


# ============================================================
# TABLE WIDTH CALCULATION
# ============================================================

def calculate_column_widths(rows, available_width):
    """
    Allocate table width according to content while keeping it
    inside the page.
    """
    if not rows:
        return []

    n = max(len(row) for row in rows)

    weights = []

    for col in range(n):
        max_len = 1

        for row in rows:
            if col < len(row):
                value = str(row[col])
                max_len = max(max_len, min(len(value), 45))

        weights.append(max_len)

    total = sum(weights)

    if total == 0:
        return [available_width / n] * n

    widths = [
        available_width * weight / total
        for weight in weights
    ]

    # Keep very narrow columns readable.
    minimum = 15 * mm

    if n > 1:
        widths = [max(width, minimum) for width in widths]

    total_width = sum(widths)

    if total_width > available_width:
        scale = available_width / total_width
        widths = [width * scale for width in widths]

    return widths


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================

def add_page_number(canvas, doc):
    canvas.saveState()

    canvas.setFont(BASE_FONT, 8)
    canvas.drawCentredString(
        PAGE_SIZE[0] / 2,
        7 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# BUILD PAGE CONTENT
# ============================================================

def build_page_story(page_text, page_number, styles, available_width):
    story = []

    lines = page_text.splitlines()
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        # Empty line
        if not line:
            story.append(Spacer(1, 3))
            i += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"-{3,}", line):
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Markdown table
        if "|" in line:
            table_data, next_index = parse_markdown_table(lines, i)

            if table_data:
                formatted_rows = []

                for row_index, row in enumerate(table_data):
                    row_style = (
                        styles["table_header"]
                        if row_index == 0
                        else styles["table_body"]
                    )

                    formatted_rows.append([
                        make_paragraph(cell, row_style)
                        for cell in row
                    ])

                widths = calculate_column_widths(
                    table_data,
                    available_width,
                )

                table = Table(
                    formatted_rows,
                    colWidths=widths,
                    repeatRows=1,
                    hAlign="LEFT",
                )

                table.setStyle(
                    TableStyle([
                        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ])
                )

                story.append(Spacer(1, 4))
                story.append(table)
                story.append(Spacer(1, 7))

                i = next_index
                continue

        # Markdown heading
        if re.match(r"^#{1,6}\s+", line):
            heading_text = re.sub(r"^#{1,6}\s+", "", line)
            story.append(
                make_paragraph(
                    heading_text,
                    styles["heading"],
                )
            )
            i += 1
            continue

        # Bold-only heading
        if re.fullmatch(r"\*\*.*\*\*", line):
            heading_text = clean_inline_markdown(line)

            story.append(
                make_paragraph(
                    heading_text,
                    styles["heading"],
                )
            )

            i += 1
            continue

        # Normal text
        story.append(
            make_paragraph(
                line,
                styles["body"],
            )
        )

        i += 1

    return story


# ============================================================
# CREATE SEARCHABLE TEXT PDF
# ============================================================

def create_searchable_pdf(json_path, txt_path, output_pdf):
    json_path = Path(json_path)
    txt_path = Path(txt_path)
    output_pdf = Path(output_pdf)

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    if not txt_path.exists():
        raise FileNotFoundError(f"TXT file not found: {txt_path}")

    print("=" * 70)
    print("OCR SEARCHABLE PDF GENERATOR")
    print("=" * 70)

    print(f"JSON input : {json_path}")
    print(f"TXT input  : {txt_path}")
    print(f"PDF output : {output_pdf}")
    print(f"Font       : {BASE_FONT}")
    print()

    data = load_json(json_path)
    txt_text = load_txt(txt_path)

    pages = get_pages(data, txt_text)

    if not pages:
        raise ValueError("No OCR pages/text were found.")

    document_meta = data.get("document", {})

    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=PAGE_SIZE,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="OCR Searchable Document",
        author="Multilingual Document OCR Extraction Pipeline",
        subject="Machine-readable and selectable OCR PDF",
    )

    styles = create_styles()

    available_width = (
        PAGE_SIZE[0]
        - LEFT_MARGIN
        - RIGHT_MARGIN
    )

    story = []

    # --------------------------------------------------------
    # Document title / metadata
    # --------------------------------------------------------

    first_page = pages[0]

    first_lines = first_page["text"].splitlines()

    # Don't add a duplicate title here. The OCR content itself
    # contains the document title.
    # Metadata remains in the PDF document properties.

    # --------------------------------------------------------
    # OCR pages
    # --------------------------------------------------------

    for index, page in enumerate(pages):
        page_number = page["page_number"]
        page_text = page["text"]

        if index > 0:
            story.append(PageBreak())

        page_story = build_page_story(
            page_text,
            page_number,
            styles,
            available_width,
        )

        story.extend(page_story)

    # --------------------------------------------------------
    # Build PDF
    # --------------------------------------------------------

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    print()
    print("SUCCESS")
    print(f"Created: {output_pdf.resolve()}")
    print(f"Pages  : {len(pages)}")
    print()
    print("The generated PDF contains real PDF text objects.")
    print("Text can be selected, copied and searched with Ctrl+F.")
    print()
    print("IMPORTANT:")
    print(
        "This version reconstructs the document from OCR text/JSON. "
        "It does NOT overlay text on the original scanned PDF because "
        "the original PDF and OCR bounding boxes were not supplied."
    )
    print("=" * 70)


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSON
    txt_file = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TXT
    output_file = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PDF

    create_searchable_pdf(
        json_file,
        txt_file,
        output_file,
    )
