"""
Chapter 6 — Chunking

What this file does
    Gets the text out of a PDF, repairs the faults that PDF extraction
    leaves behind, and (in later sections) splits the text into chunks:
    passages small enough to embed and retrieve.

Inputs
    data/sources/mccarthy_2013_ch18.pdf: Chapter 18 of World Bank (2013),
    Measuring the Real Size of the World Economy (CC BY 3.0 IGO; see
    data/sources/README.md).

Outputs
    The text of each page; one cleaned text for the whole document; a count
    of each repair made.

Used by
    Chapter 7 (vector databases).

Uses
    pypdf, to read PDF files. Python's re and pathlib modules.

Run the worked example
    python -m ragbook.ch06_chunking
"""

import re
from pathlib import Path

from pypdf import PdfReader

SOURCES_FOLDER = Path(__file__).parent.parent / "data" / "sources"
EXAMPLE_PDF = SOURCES_FOLDER / "mccarthy_2013_ch18.pdf"


# ---------------------------------------------------------------------------
# 6.2  Getting text out of a PDF
# ---------------------------------------------------------------------------

def read_pdf_pages(pdf_path):
    """
    Return the text of each page of a PDF, as a list of strings.

    A PDF stores where each character is drawn on the page, not sentences or
    paragraphs. pypdf rebuilds lines of text from those positions. Running
    headers, page numbers, broken words and table cells all come out as
    ordinary text; section 6.3 repairs them.

    A page with no text (a blank page, or a scanned image) gives "".

    Example:
        read_pdf_pages(EXAMPLE_PDF)[0][:20]
        returns "Extrapolating PPPs a"
    """
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text is None:
            text = ""
        pages.append(text)
    return pages


# ---------------------------------------------------------------------------
# 6.3  Cleaning the text
# ---------------------------------------------------------------------------

def remove_running_header(page_text):
    """
    Remove the page number and running header from the top of a page.

    In the example PDF every page after the first starts with its page
    number. Usually the number is a line of its own and the header is the
    next line; on a few pages the number and the header share one line.
    The header text itself cannot be matched exactly, because the small
    capital letters it is printed in come out differently on different
    pages ("econo My", "Econo My").

    Rule: if the first line starts with a number, remove it; if that line
    was only the number, remove the next line too.

    Example:
        remove_running_header("474\\nMeasuring the real size\\nText.")
        returns "Text."
    """
    lines = page_text.split("\n")
    first_line = lines[0].strip()
    if not re.match(r"\d+", first_line):
        return page_text
    if first_line.isdigit():
        return "\n".join(lines[2:])
    return "\n".join(lines[1:])


# Two characters named by their Unicode code numbers (written in hexadecimal).
# Codes E000 to F8FF are kept for each font's private symbols; 202F is the
# narrow no-break space.
PRIVATE_SYMBOLS = "[" + chr(0xE000) + "-" + chr(0xF8FF) + "]"
NARROW_NO_BREAK_SPACE = chr(0x202F)

# Each repair: what it fixes, the pattern to find, and what replaces it.
# They run in this order.
REPAIRS = [
    ("word broken by a hyphen at the end of a line", r"(\w) ?-\n(\w)", r"\1\2"),
    ("capital T split from the rest of its word", r"\bT\s(?=[a-z])", "T"),
    ("space before a full stop, comma, colon, semicolon or bracket", r" +([.,;:)])", r"\1"),
    ("doubled bullet mark", r"••", "•"),
    ("piece of a large bracket drawn from a font's private symbols", PRIVATE_SYMBOLS, ""),
    ("narrow no-break space", NARROW_NO_BREAK_SPACE, " "),
    ("two or more spaces", r" {2,}", " "),
    ("space at the start or end of a line", r" +\n *|\n +", "\n"),
    ("empty line", r"\n{2,}", "\n"),
]


def repair_text(text):
    """
    Apply each repair in REPAIRS to the text, in order.

    Returns the repaired text and a dictionary giving how many times each
    repair was made, so the effect of every rule can be checked.

    The hyphen rule also joins a word that really has a hyphen if the line
    happens to break there ("time-\\nseries" becomes "timeseries"). Section
    6.3.3 counts how often that happens in the example.

    Example:
        repair_text("the esti -\\nmates of the ICP .")[0]
        returns "the estimates of the ICP."
    """
    counts = {}
    for description, pattern, replacement in REPAIRS:
        text, how_many = re.subn(pattern, replacement, text)
        counts[description] = how_many
    return text, counts


def clean_pdf_text(pages):
    """
    Turn the pages of a PDF into one cleaned text.

    Removes the running header from every page except the first (the first
    page's top line is the chapter title, which is real text). Leaves out
    empty pages. Joins the pages with a line break, then repairs the whole
    text, so a word broken across two pages is joined too.

    Returns the cleaned text and the repair counts from repair_text.

    Example:
        clean_pdf_text(["Title\\nA long esti -", "2\\nHeader\\nmate."])[0]
        returns "Title\\nA long estimate."
    """
    kept = []
    for page_number, page_text in enumerate(pages, start=1):
        if page_number > 1:
            page_text = remove_running_header(page_text)
        if page_text.strip() == "":
            continue
        kept.append(page_text)
    joined = "\n".join(kept)
    return repair_text(joined)


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------

def main():
    pages = read_pdf_pages(EXAMPLE_PDF)
    empty = sum(1 for page_text in pages if page_text.strip() == "")
    words_before = sum(len(page_text.split()) for page_text in pages)
    print(f"Pages: {len(pages)} ({empty} with no text)")
    print(f"Words as extracted: {words_before:,}")

    text, counts = clean_pdf_text(pages)
    print(f"Words after cleaning: {len(text.split()):,}")
    print()
    print("Repairs made:")
    for description, how_many in counts.items():
        print(f"  {how_many:4}  {description}")
    print()
    print("Start of the cleaned text:")
    print(text[:300])


if __name__ == "__main__":
    main()
