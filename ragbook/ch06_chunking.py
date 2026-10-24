"""
Chapter 6 — Chunking

What this file does
    Gets the text out of a PDF, repairs the faults that PDF extraction
    leaves behind, and cuts the text into chunks: passages small enough to
    embed and retrieve. Compares five ways of cutting: fixed size, fixed
    size with overlap, paragraph, header and recursive.

Inputs
    data/sources/mccarthy_2013_ch18.pdf: Chapter 18 of World Bank (2013),
    Measuring the Real Size of the World Economy (CC BY 3.0 IGO; see
    data/sources/README.md).

Outputs
    The text of each page; one cleaned text for the whole document; a count
    of each repair made; the lines printed in heading sizes; lists of
    chunks; a table comparing the methods.

Used by
    Chapter 7 (vector databases).

Uses
    pypdf, to read PDF files. Python's re and pathlib modules.
    Chapter 4 (load_model), only to count word pieces.

Run the worked example
    python -m ragbook.ch06_chunking
    python -m ragbook.ch06_chunking --word-pieces
    The second also counts word pieces with the embedding model, so it
    needs the model (Chapter 4).
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


def remove_first_page_footer(page_text):
    """
    Remove the chapter number, author's name, the word CHAPTER and the page
    number from the bottom of a chapter's first page.

    The book prints these four items at the foot of each chapter's first
    page, in large type. They come out as the last four lines of the page,
    in the middle of the paragraph that runs on to the next page.

    Rule: if the last line is only a number, remove it and the three lines
    above it.

    Example:
        remove_first_page_footer("Text \\n18\\nPaul Mccarthy\\nCHAPTER\\n473")
        returns "Text "
    """
    lines = page_text.split("\n")
    if not lines[-1].strip().isdigit():
        return page_text
    return "\n".join(lines[:-4])


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
    ("line with no space at its end: a paragraph ends, so add an empty line", r"(?<=[^ \n])\n", "\n\n"),
    ("space before a full stop, comma, colon, semicolon or bracket", r" +([.,;:)])", r"\1"),
    ("doubled bullet mark", r"••", "•"),
    ("piece of a large bracket drawn from a font's private symbols", PRIVATE_SYMBOLS, ""),
    ("narrow no-break space", NARROW_NO_BREAK_SPACE, " "),
    ("two or more spaces", r" {2,}", " "),
    ("space at the start or end of a line", r" +\n *|\n +", "\n"),
    ("two or more empty lines in a row", r"\n{3,}", "\n\n"),
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

    Removes the footer from the first page and the running header from
    every other page (the first page's top line is the chapter title, which
    is real text). Leaves out empty pages. Joins the pages with a line
    break, then repairs the whole text, so a word broken across two pages is
    joined too.

    In the result a single line break separates the lines of a paragraph,
    and an empty line separates paragraphs.

    Returns the cleaned text and the repair counts from repair_text.

    Example:
        clean_pdf_text(["Title\\nA long esti -", "2\\nHeader\\nmate."])[0]
        returns "Title\\n\\nA long estimate."
    """
    kept = []
    for page_number, page_text in enumerate(pages, start=1):
        if page_number == 1:
            page_text = remove_first_page_footer(page_text)
        else:
            page_text = remove_running_header(page_text)
        if page_text.strip() == "":
            continue
        kept.append(page_text)
    joined = "\n".join(kept)
    return repair_text(joined)


# ---------------------------------------------------------------------------
# 6.4  Fixed-size chunks, with and without overlap
# ---------------------------------------------------------------------------

CHUNK_WORDS = 150    # the most words in a chunk, for every method in this chapter
OVERLAP_WORDS = 30   # words a fixed-size chunk repeats from the end of the one before


def count_words(text):
    """
    Return the number of words in a text, split at spaces and line breaks.

    Example:
        count_words("Real GDP\\nper head")
        returns 4
    """
    return len(text.split())


def fixed_size_chunks(text, size=CHUNK_WORDS, overlap=0):
    """
    Cut a text into chunks of `size` words; the last chunk may be shorter.

    With overlap, each chunk starts `overlap` words before the previous
    chunk ended, so the words around every cut appear in two chunks.

    Line breaks and paragraphs are ignored: the words of each chunk are
    joined with single spaces.

    Example:
        fixed_size_chunks("a b c d e", size=2, overlap=1)
        returns ["a b", "b c", "c d", "d e"]
    """
    if not 0 <= overlap < size:
        raise ValueError("overlap must be at least 0 and less than size")
    words = text.split()
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return chunks


# ---------------------------------------------------------------------------
# 6.5  Paragraph chunks
# ---------------------------------------------------------------------------

def split_paragraphs(text):
    """
    Return the paragraphs of a cleaned text, each as one line.

    clean_pdf_text (6.3) puts an empty line between paragraphs. The line
    breaks inside a paragraph are where the printed lines ended; they are
    replaced by spaces.

    Example:
        split_paragraphs("One\\nline.\\n\\nTwo.")
        returns ["One line.", "Two."]
    """
    paragraphs = []
    for block in text.split("\n\n"):
        paragraph = " ".join(block.split())
        if paragraph != "":
            paragraphs.append(paragraph)
    return paragraphs


def pack(pieces, size=CHUNK_WORDS, joiner=" "):
    """
    Join pieces of text, in order, into chunks of at most `size` words.

    A piece joins the current chunk if the chunk stays within `size`;
    otherwise the current chunk is closed and the piece starts a new one.
    A piece longer than `size` becomes a chunk on its own and stays too
    long; recursive chunking (6.7) cuts it further.

    `joiner` is put between the pieces of a chunk.

    Example:
        pack(["a b", "c", "d e f"], size=3)
        returns ["a b c", "d e f"]
    """
    chunks = []
    current = []
    current_words = 0
    for piece in pieces:
        piece_words = count_words(piece)
        if current and current_words + piece_words > size:
            chunks.append(joiner.join(current))
            current = []
            current_words = 0
        current.append(piece)
        current_words += piece_words
    if current:
        chunks.append(joiner.join(current))
    return chunks


def paragraph_chunks(text, size=CHUNK_WORDS):
    """
    Cut a cleaned text into chunks of whole paragraphs: one paragraph, or
    several short ones in a row, up to `size` words.

    Paragraphs in the same chunk are separated by an empty line.

    Example:
        paragraph_chunks("a b\\n\\nc\\n\\nd e f", size=3)
        returns ["a b\\n\\nc", "d e f"]
    """
    return pack(split_paragraphs(text), size, joiner="\n\n")


# ---------------------------------------------------------------------------
# 6.6  Header chunks
# ---------------------------------------------------------------------------

def find_heading_lines(pdf_path, smallest=12, largest=18):
    """
    Return the lines of a PDF printed in heading sizes, in reading order.

    The extracted text has lost its fonts, but pypdf can report the font
    size of each piece of text as it reads a page: it calls note_piece
    once for each piece. The printed size is the font size multiplied by
    the scale stored with the text (text_matrix[0]).

    In the example PDF, body text is 10 points; headings are 12 points
    (annex subsections), 15 (sections and annex labels) or 18 (the
    chapter title). Sizes differ between documents, so check them first.

    Example:
        find_heading_lines(EXAMPLE_PDF)[2]
        returns "Estimating PPPs for Nonbenchmark Years"
    """
    heading_lines = []

    def note_piece(text, page_matrix, text_matrix, font, font_size):
        if font is None or text.strip() == "":
            return
        size = round(font_size * text_matrix[0], 1)
        if smallest <= size <= largest:
            heading_lines.append(text.strip())

    for page in PdfReader(pdf_path).pages:
        page.extract_text(visitor_text=note_piece)
    return heading_lines


def split_sections(text, heading_lines):
    """
    Cut a cleaned text into sections, each a pair: (heading, body).

    A paragraph is a heading if every one of its lines is in
    heading_lines. A heading that comes straight after another heading
    (such as "ANNEX A" and the annex's title) joins it in one heading.
    Text before the first heading has the heading "".

    Each paragraph of the body becomes one line; paragraphs are separated
    by an empty line, as in paragraph_chunks.

    Example:
        split_sections("Intro.\\n\\nPrices\\n\\nText.", ["Prices"])
        returns [("", "Intro."), ("Prices", "Text.")]
    """
    headings = set(heading_lines)
    sections = []
    heading_parts = []
    body = []
    for block in text.split("\n\n"):
        if block.strip() == "":
            continue
        lines = block.split("\n")
        is_heading = all(line in headings for line in lines)
        if is_heading and body:
            sections.append((" ".join(heading_parts), "\n\n".join(body)))
            heading_parts = []
            body = []
        if is_heading:
            heading_parts.append(" ".join(lines))
        else:
            body.append(" ".join(lines))
    if heading_parts or body:
        sections.append((" ".join(heading_parts), "\n\n".join(body)))
    return sections


def header_chunks(text, heading_lines):
    """
    Cut a cleaned text into sections: each chunk is a heading and the text
    that follows it, up to the next heading. Sections have no size limit.

    Example:
        header_chunks("Intro.\\n\\nPrices\\n\\nText.", ["Prices"])
        returns ["Intro.", "Prices\\n\\nText."]
    """
    chunks = []
    for heading, body in split_sections(text, heading_lines):
        if heading == "":
            chunks.append(body)
        else:
            chunks.append(heading + "\n\n" + body)
    return chunks


# ---------------------------------------------------------------------------
# 6.7  Recursive chunking
# ---------------------------------------------------------------------------

def split_sentences(paragraph):
    """
    Cut a paragraph into sentences.

    A sentence ends at a full stop, question mark or exclamation mark that
    is followed by a space and then a capital letter, an opening bracket or
    an opening quotation mark. An abbreviation followed by a capital, such
    as "U.S. Census", is cut wrongly; for chunking that does little harm.

    Example:
        split_sentences("GDP rose. It fell (later).")
        returns ["GDP rose.", "It fell (later)."]
    """
    return re.split(r"(?<=[.?!])\s+(?=[A-Z(“])", paragraph)


# The ways of cutting a text, from largest pieces to smallest, and what is
# put between pieces when they are packed back into chunks.
CUTS = [
    (split_paragraphs, "\n\n"),
    (split_sentences, " "),
]


def cut_to_fit(text, size=CHUNK_WORDS, cuts=CUTS):
    """
    Cut a text into chunks of at most `size` words, using the largest
    pieces that fit.

    If the text fits, it is one chunk. If not, it is cut with the first
    way in `cuts` and the pieces are packed (6.5). Any chunk still too long
    is a single piece that did not fit; the function calls itself on it,
    with the remaining ways of cutting. When none are left, the text is
    cut into fixed-size chunks (6.4).

    A function that calls itself is called recursive, hence the name of
    the method.

    Example:
        cut_to_fit("a b c.\\n\\nd e. F g h i.", size=3)
        returns ["a b c.", "d e.", "F g h", "i."]
    """
    if count_words(text) <= size:
        return [text]
    if not cuts:
        return fixed_size_chunks(text, size)
    cut, joiner = cuts[0]
    chunks = []
    for chunk in pack(cut(text), size, joiner):
        chunks.extend(cut_to_fit(chunk, size, cuts[1:]))
    return chunks


def recursive_chunks(text, heading_lines, size=CHUNK_WORDS):
    """
    Cut a cleaned text at headings, then paragraphs, then sentences, then
    words, until every chunk has at most `size` words.

    Each chunk starts with its section's heading (6.6), so a chunk from
    the middle of a section still names its subject. The heading's words
    count towards `size`.

    Example:
        recursive_chunks("Prices\\n\\na b.\\n\\nc d.", ["Prices"], size=3)
        returns ["Prices\\n\\na b.", "Prices\\n\\nc d."]
    """
    chunks = []
    for heading, body in split_sections(text, heading_lines):
        if heading == "":
            chunks.extend(cut_to_fit(body, size))
            continue
        for piece in cut_to_fit(body, size - count_words(heading)):
            chunks.append(heading + "\n\n" + piece)
    return chunks


# ---------------------------------------------------------------------------
# 6.8  Comparing the methods
# ---------------------------------------------------------------------------

def chunk_sizes(chunks):
    """
    Describe a list of chunks: how many, and the smallest, middle (median)
    and largest number of words.

    Example:
        chunk_sizes(["a", "b c", "d e f"])
        returns {"chunks": 3, "smallest": 1, "median": 2, "largest": 3}
    """
    sizes = sorted(count_words(chunk) for chunk in chunks)
    return {
        "chunks": len(sizes),
        "smallest": sizes[0],
        "median": sizes[len(sizes) // 2],
        "largest": sizes[-1],
    }


def all_methods(text, heading_lines):
    """
    Cut the same text with every method in this chapter.

    Returns a dictionary from the method's name to its list of chunks.
    """
    return {
        "fixed size": fixed_size_chunks(text),
        "fixed size with overlap": fixed_size_chunks(text, overlap=OVERLAP_WORDS),
        "paragraph": paragraph_chunks(text),
        "header": header_chunks(text, heading_lines),
        "recursive": recursive_chunks(text, heading_lines),
    }


def count_word_pieces(model, chunks):
    """
    Return the number of word pieces the embedding model reads in each
    chunk, including the two markers it adds at the start and end.

    The model reads at most model.max_seq_length pieces (256 for
    all-MiniLM-L6-v2, Chapter 4); the rest of a longer chunk is ignored.

    Example:
        count_word_pieces(load_model(), ["What is GDP?", "Real GDP"])
        returns two numbers, one for each chunk
    """
    counts = []
    for chunk in chunks:
        counts.append(len(model.tokenizer(chunk)["input_ids"]))
    return counts


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------

def main(word_pieces=False):
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

    heading_lines = find_heading_lines(EXAMPLE_PDF)
    print(f"Lines in heading sizes: {len(heading_lines)}")
    print()

    model = None
    if word_pieces:
        from ragbook.ch04_semantic_search import load_model

        model = load_model()

    print(f"{'Method':25} {'Chunks':>6} {'Smallest':>8} {'Median':>6} {'Largest':>7}  Over 256 pieces")
    for name, chunks in all_methods(text, heading_lines).items():
        sizes = chunk_sizes(chunks)
        line = (
            f"{name:25} {sizes['chunks']:6} {sizes['smallest']:8} "
            f"{sizes['median']:6} {sizes['largest']:7}"
        )
        if model is not None:
            pieces = count_word_pieces(model, chunks)
            over = sum(1 for how_many in pieces if how_many > model.max_seq_length)
            line += f"  {over} (largest {max(pieces)})"
        print(line)
    if model is None:
        print("(Word pieces not counted: run with --word-pieces on a computer with the model.)")


if __name__ == "__main__":
    import sys

    main(word_pieces="--word-pieces" in sys.argv)
