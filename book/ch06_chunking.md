# Chapter 6 — Chunking

## 6.1 What this chapter builds

Chapters 2–5 searched 56 passages that were cut by hand, each under 200 words. A working retrieval system starts from whole documents, so code must cut them into **chunks**: passages small enough to embed and retrieve.

This chapter turns a 34-page PDF into chunks and compares five ways of cutting it.

1. **Getting text out of a PDF** (6.2): pypdf reads the text of each page.
2. **Cleaning the text** (6.3): code removes the page numbers, running headers and the first page's footer, and applies twelve repair rules, each counted. One rule keeps the ends of paragraphs.
3. **Fixed-size chunks, with and without overlap** (6.4): every chunk has the same number of words; with overlap, each chunk repeats the end of the one before.
4. **Paragraph chunks** (6.5): a chunk is one paragraph, or several short ones.
5. **Header chunks** (6.6): a chunk is one section, cut at its heading.
6. **Recursive chunking** (6.7): cut at headings, then paragraphs, then sentences, until every chunk fits a size limit.

Section 6.8 compares the five methods on the same text: how many chunks each makes, their sizes, and how many exceed the 256 word-piece limit of the embedding model all-MiniLM-L6-v2 (Chapter 4, 4.4.1).

### 6.1.1 The example text

The example is Paul McCarthy, "Extrapolating PPPs and Comparing ICP Benchmark Results", Chapter 18 of World Bank (2013), *Measuring the Real Size of the World Economy* (6.9.3). It is stored in full as `data/sources/mccarthy_2013_ch18.pdf`.

- **Licence.** The book is published under Creative Commons Attribution 3.0 (CC BY 3.0), which allows the whole chapter to be stored, cut and shown with attribution. The manuals in the corpus allow only short quotations (Chapter 2), so their chunks cannot be stored here.
- **Subject.** The chapter explains why a country's growth measured by its own national accounts differs from the change implied by two sets of purchasing power parities (PPPs). The app answers the same kind of question (Chapter 12).
- **Layout.** It has the faults most PDFs have: a page number and running header on every page, a footer on the first page, tables, equations and notes printed away from the sentences they explain. Section 6.2 shows each one.

The same code can cut the manuals on the reader's own computer, from copies the reader holds. Section 6.8 reports the counts for the manuals, not their text.

**Code file:** `ragbook/ch06_chunking.py`

**Uses:** pypdf 5.9.0, a Python library that reads PDF files (added to `requirements.txt`); Python's `re` and `pathlib` modules. From Chapter 4, only load_model, to count word pieces (6.8).

## 6.2 Getting text out of a PDF

### 6.2.1 Principles

A PDF stores instructions to draw each character at a position on a page. It does not store words, lines, paragraphs, or which text is a heading.

A program that reads a PDF rebuilds lines from the positions of the characters and guesses where spaces fall from the gaps between them. Anything printed on the page comes out as text: page numbers, running headers, table cells, pieces of equations.

The example PDF shows the common faults. Each row quotes the text as pypdf extracts it.

| Fault | As extracted | Cause |
| --- | --- | --- |
| Page number and **running header** at the top of every page after the first | "474" then "Measuring the real size of the World econo My" | The header is printed in small capital letters; extraction splits words where the letter size changes |
| Footer on the first page | "18", "Paul Mccarthy", "CHAPTER", "473" as the page's last four lines | The chapter number, author and page number are printed at the foot of the chapter's first page |
| Word broken by a hyphen at the end of a line | "esti -" then "mates" | The typesetter split the word to fit the line |
| Large first letter of the chapter (a **drop capital**) | "T" on its own line, then "he International Comparison Program" | The first letter is printed larger, in its own place |
| Capital T split from its word | "T esting" | The gap printed after a capital T is read as a space |
| Space before punctuation | "ICP ." | The same kind of gap, after a capital P |
| Doubled bullet | "••" | The bullet is drawn twice |
| Table | "Goods 80 1.00 1.00 80 20 1.00 1.00 20" | Columns become a run of numbers; the table's title comes after the table |
| Equation | Bracket pieces, then "pt _ pt−2" | Symbols and subscripts lose their positions; large brackets are drawn from a font's private symbols |
| Notes | Notes 4 and 5 printed after Annex D | The notes are printed at the end, away from the sentences that refer to them |
| Blank page | "" | The PDF ends with an empty page |

Every printed line ends with a line break, and no blank line marks where a paragraph ends. One mark survives: a line inside a paragraph ends with a space, and the last line of a paragraph does not. Section 6.3 keeps that mark.

The chapter uses **pypdf**, a library written only in Python with a permissive open-source licence (BSD). It needs no other program. Other libraries keep more of the page layout, such as table columns; running text is all this chapter needs.

### 6.2.2 Code

`ragbook/ch06_chunking.py`, function `read_pdf_pages`

```python
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
```

### 6.2.3 Annotations

- `PdfReader(pdf_path)` opens the file. `reader.pages` holds its pages in order.
- `page.extract_text()` rebuilds the lines of one page. It can return nothing for a page with no text; the function turns that into an empty string, so every page gives a string.
- One string per page, not one for the whole file: the running header sits at the top of each page, so section 6.3 removes it page by page.
- A scanned page holds a picture of text, not characters, so it gives "". Reading a scan needs optical character recognition, which this book does not cover.

On the example PDF:

| Measure | Value |
| --- | --- |
| Pages | 34 (printed pages 473–505, then one blank page) |
| Pages with no text | 1 |
| Words as extracted | 17,384 |

Words are counted by splitting the text at spaces and line breaks, so "esti -" counts as two.

## 6.3 Cleaning the text

### 6.3.1 Principles

Cleaning removes text the author did not write and repairs text that extraction broke. Every repair is a rule whose uses are counted, so a rule that changes text it should not is found and reported, not hidden.

The work is done in two steps.

1. **Page by page:** remove the footer from the first page, and the page number and running header from the top of every other page.
2. **Whole text:** join the pages, then apply twelve repair rules in a fixed order. Joining first means a word broken across two pages is repaired too.

The running header cannot be found by matching its text, because its small capitals come out differently on different pages ("econo My" on page 474, "Econo My" on page 504). Its position can: every page after the first starts with its page number. The rule removes that line, and the next line too when the number stands alone.

The first page has no running header but has a footer: the chapter number (18), the author's name, the word CHAPTER and the page number (473). They come out as the page's last four lines, in the middle of the paragraph that runs on to page 474. The rule removes the last four lines when the last one is a number.

Each repair rule is a **regular expression**: a pattern that describes text to find, such as "a letter, an optional space, a hyphen, a line break, a letter". Python's `re` module finds each match and replaces it.

One rule marks rather than repairs. A printed line inside a paragraph ends with a space; the last line of a paragraph, a heading or a table row does not. The rule puts an empty line after every line with no space at its end, so the cleaned text marks paragraphs as most text files do: an empty line between them, single line breaks inside them.

Two rules find nothing in the example; they were added when the code was run on the manuals (6.8). A table of contents joins each title to its page number with a row of dots, which comes out as one "word" of up to 171 characters. Some tables in the 2008 SNA use a font that pypdf cannot turn into letters, so it gives the font's codes for each character instead ("/g38/g82/g81", "#23#23"). Both are removed.

Three faults are left unrepaired: tables, equations and notes. No short rule fixes them, and a retriever can still match their numbers and names. The line breaks inside a paragraph stay; the chunking methods replace them with spaces (6.4–6.7).

### 6.3.2 Code

`ragbook/ch06_chunking.py`, function `remove_running_header`

```python
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
```

`ragbook/ch06_chunking.py`, function `remove_first_page_footer`

```python
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
```

The repair rules and the function that applies them:

```python
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
    ("dot leader: four or more dots, as in a table of contents", r"\.{4,}", " "),
    ("word holding font codes instead of letters, such as /g38 or #23", r"\S*(?:/g\d+|#\d\d)\S*", ""),
    ("two or more spaces", r" {2,}", " "),
    ("space at the start or end of a line", r" +\n *|\n +", "\n"),
    ("two or more empty lines in a row", r"\n{3,}", "\n\n"),
]
```

```python
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
```

`ragbook/ch06_chunking.py`, function `clean_pdf_text`

```python
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
```

### 6.3.3 Annotations

- `re.match(r"\d+", first_line)` asks whether the line starts with one or more digits. `first_line.isdigit()` asks whether it is nothing but digits.
- In a pattern, `\w` is any letter or digit, `\n` a line break, `\s` any space or line break, `\b` the edge of a word. `(\w)` captures what it matches, and `\1` puts it back in the replacement.
- `(?=[a-z])` checks the next character without removing it: the T rule removes the space only when a small letter follows, so "T esting" becomes "Testing" and the drop capital "T", line break, "he" becomes "The".
- `(?<=[^ \n])` checks the character before without removing it: here, anything but a space or a line break. So the paragraph rule acts only on a line that ends with some other character.
- `PRIVATE_SYMBOLS` is a pattern for any character with a code from E000 to F8FF, the block Unicode keeps for each font's private symbols. Here they are the pieces of large brackets in equations; as text they mean nothing. `chr(0x202F)` is the character with code 202F; `0x` marks a number written in hexadecimal.
- `re.subn` returns the new text and the number of replacements, which is how every rule is counted.
- The order matters. The hyphen rule and the T rule run before the paragraph rule, so "esti-" and the drop capital "T" are joined to the next line first. The paragraph rule runs before the rule that removes spaces at line ends, which would remove the mark it reads. The rule for empty lines runs last, after the bracket pieces it would leave are gone.

On the example PDF the page step removes 313 words of page numbers, running headers and the first page's footer. The repair rules make these changes:

| Repair | Times made |
| --- | --- |
| Word broken by a hyphen at the end of a line | 83 |
| Capital T split from the rest of its word | 16 |
| Line with no space at its end: a paragraph ends, so add an empty line | 519 |
| Space before a full stop, comma, colon, semicolon or bracket | 74 |
| Doubled bullet mark | 27 |
| Piece of a large bracket from a font's private symbols | 244 |
| Narrow no-break space | 177 |
| Dot leader: four or more dots, as in a table of contents | 0 |
| Word holding font codes instead of letters, such as /g38 or #23 | 0 |
| Two or more spaces | 593 |
| Space at the start or end of a line | 1,153 |
| Two or more empty lines in a row | 58 |

The text falls from 17,384 words to 16,634, in 425 paragraphs.

**Known fault.** One of the 83 hyphen repairs joins a word that has a real hyphen: "PPP-based", broken at the end of a line, becomes "PPPbased". The other 82 are words the typesetter split. A rule that kept the hyphen after capital letters would fix this case and could break others; with one error in 83 the rule stays as it is, and a test records the fault.

## 6.4 Fixed-size chunks, with and without overlap

### 6.4.1 Principles

**Fixed-size chunking** gives every chunk the same number of words. A chunk ends where the count runs out, even in the middle of a sentence.

The method needs nothing from the document but its words, so it works on any text. Its fault is the cut: a sentence split between two chunks is whole in neither, and one chunk can hold the end of one subject and the start of the next.

**Overlap** reduces the damage. Each chunk starts some words before the previous one ended, so the words around every cut appear in two chunks. The cost is more chunks, and the same words stored and embedded twice.

Every method in this chapter uses the same limit, 90 words, so section 6.8 compares like with like. The limit must keep each chunk within the embedding model's 256 word pieces (Chapter 4); 6.8 shows how 90 was chosen. The overlap is 18 words, a fifth of a chunk.

The limit is counted in words, not word pieces, because words can be counted without the model.

### 6.4.2 Code

`ragbook/ch06_chunking.py`, the names `CHUNK_WORDS` and `OVERLAP_WORDS` and the functions `count_words` and `fixed_size_chunks`

```python
CHUNK_WORDS = 90     # the most words in a chunk, for every method in this chapter
OVERLAP_WORDS = 18   # words a fixed-size chunk repeats from the end of the one before
```

```python
def count_words(text):
    """
    Return the number of words in a text, split at spaces and line breaks.

    Example:
        count_words("Real GDP\\nper head")
        returns 4
    """
    return len(text.split())
```

```python
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
```

### 6.4.3 Annotations

- `step` is how far each chunk starts after the one before: 90 words without overlap (chunks start at words 0, 90, 180…), 72 with an overlap of 18 (0, 72, 144…).
- `range(0, len(words), step)` gives those starting positions. `words[start:start + size]` takes up to `size` words; at the end of the text it takes what is left.
- `break` stops once a chunk reaches the end of the text. Without it, overlap would add a last chunk holding only words already in the one before.
- An overlap as large as the chunk would never move forward, so the function refuses it (`raise ValueError`).

On the cleaned example (16,634 words), fixed-size chunking gives 185 chunks; with overlap, 231. Only the last chunk is shorter than 90 words (74 words in both).

The first cut falls inside a sentence: chunk 1 ends "…the annual (or quarterly) time series data" and chunk 2 starts "that are available." With overlap, chunk 2 starts 18 words earlier, at "the evolution of an economy over time", so the clause cut in two is whole in it.

## 6.5 Paragraph chunks

### 6.5.1 Principles

An author typically puts one point in a paragraph. **Paragraph chunking** cuts where the author did, so no chunk splits a sentence and most chunks hold one point.

Paragraphs vary in length. A heading, a table cell or a short paragraph is too small to retrieve on its own, so short paragraphs that follow each other are **packed** into one chunk, up to 90 words. A paragraph longer than 90 words stays whole as a chunk of its own, over the limit; section 6.7 deals with it.

The cleaned text marks paragraphs with an empty line (6.3), so finding them takes one split.

### 6.5.2 Code

`ragbook/ch06_chunking.py`, the functions `split_paragraphs`, `pack` and `paragraph_chunks`

```python
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
```

```python
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
```

```python
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
```

### 6.5.3 Annotations

- `" ".join(block.split())` splits a paragraph at every space and line break, then joins the words with single spaces: the printed lines become one line.
- `pack` keeps a list of the pieces in the current chunk and a running count of their words. Before adding a piece it checks whether the count would pass `size`; if so, it closes the chunk first.
- `if current and …` stops `pack` closing an empty chunk when the first piece is already too long.
- After the loop, the last chunk is still open; the final `if current:` closes it.
- `pack` is written once and used again in 6.7, for sentences as well as paragraphs. `joiner` says what goes between the pieces: an empty line between paragraphs, a space between sentences.

The example has 425 paragraphs. Packed, they give 158 chunks, from 1 word to 279. 65 paragraphs are longer than 90 words, so 65 chunks are over the limit.

71 paragraphs have three words or fewer. Most are headings ("Constant PPPs"), table cells ("GDP, year t") or notes under tables ("Source: IMF 2011."); packing joins them to the text around them. One is an error: the line "constant price value = current value/" ends without a space, so the rule in 6.3 ends a paragraph there and leaves "deflator." alone.

## 6.6 Header chunks

### 6.6.1 Principles

A heading names what its section is about. **Header chunking** makes each section one chunk, from its heading to the next, so every chunk carries the name of its subject.

The extracted text does not say which lines are headings (6.2). The PDF does record the size each piece of text is printed in, and headings are printed larger than the body. In the example:

| Text | Size (points) |
| --- | --- |
| Body text | 10 |
| Annex subsections ("General") | 12 |
| Sections and annex labels ("Constant PPPs", "ANNEX A") | 15 |
| Chapter title | 18 |

So a line printed at 12 to 18 points is a heading line. Other documents use other sizes, so count the characters printed at each size in a new document before choosing the range. The size printed most is the body text.

A heading can run over two lines ("International Comparisons in" / "World Development Indicators"), and an annex has a label above its title. Lines of heading that follow each other form one heading.

Sections have no size limit, which is the method's fault: a long section is one long chunk.

### 6.6.2 Code

`ragbook/ch06_chunking.py`, the functions `font_sizes`, `find_heading_lines`, `split_sections` and `header_chunks`

```python
def font_sizes(pdf_path):
    """
    Count how many characters a PDF prints at each size, largest count
    first.

    The size printed most is the body text. Larger sizes are candidates for
    headings; check them by looking at the text printed in each (6.6).

    Example:
        font_sizes(EXAMPLE_PDF)[0]
        returns (10.0, 89714): body text, 10 points

    Sizes of 0 or 1 come from text that is scaled in another way, mostly in
    tables; they are not real sizes.
    """
    characters = {}

    def note_piece(text, page_matrix, text_matrix, font, font_size):
        if font is None or text.strip() == "":
            return
        size = round(font_size * text_matrix[0], 1)
        characters[size] = characters.get(size, 0) + len(text.strip())

    for page in PdfReader(pdf_path).pages:
        page.extract_text(visitor_text=note_piece)
    return sorted(characters.items(), key=lambda pair: -pair[1])
```

```python
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
```

```python
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
```

```python
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
```

### 6.6.3 Annotations

- `page.extract_text(visitor_text=note_piece)` reads the page as before, and also calls `note_piece` for every piece of text, with its font and size. `note_piece` is defined inside `find_heading_lines`, so it can add to that function's `heading_lines`.
- pypdf passes five things to `note_piece`; only the text, the text's matrix and the font size are used. The matrix holds where and how large the text is drawn; its first number is the scale.
- `round(…, 1)` keeps one decimal place, so a size of 14.9999 counts as 15. font_sizes adds up the characters at each size and sorts the sizes, largest count first; the minus sign in the sort key reverses the order.
- `set(heading_lines)` makes looking up a line fast. A paragraph counts as a heading only if all its lines are heading lines, so a body sentence that happens to contain a heading's words is not one.
- `split_sections` collects heading paragraphs in `heading_parts` and body paragraphs in `body`. A heading that arrives after some body text closes the section before it.
- `split_sections` returns the heading and the body apart, because recursive chunking (6.7) needs them apart; `header_chunks` joins them.

On the example, 37 lines are printed in heading sizes. They make 24 sections, from 85 words to 2,638. The longest section is "Consistency between Time and Space"; the next, the chapter title and the opening text under it, has 1,349. Word counts include the heading.

Two faults:

- "NOTES" and "REFERENCES" are printed at 8 points, smaller than body text, so they are not found. The notes and references join the last section, Annex D's "Conclusion".
- Annex D's authors' names are printed at 12 points, so they become part of the annex's heading.

## 6.7 Recursive chunking

### 6.7.1 Principles

**Recursive chunking** combines the three methods before it. It cuts at the largest boundary that gives chunks within the limit, and goes to a smaller boundary only where it must:

1. Each section (6.6) that fits in 90 words is one chunk.
2. A longer section is cut into paragraphs, packed as in 6.5.
3. A paragraph longer than 90 words is cut into sentences, packed the same way.
4. A sentence longer than 90 words is cut into fixed-size pieces (6.4).

So every chunk fits, and a cut falls inside a sentence only when one sentence is longer than a whole chunk.

Each chunk also starts with its section's heading. A chunk from the middle of "The Balassa-Samuelson Effect" then names its subject, so a question that names the subject can match it. Chapter 10 measures whether that helps. The heading's words count towards the 90.

The sentence rule is rough: a sentence ends at a full stop, question mark or exclamation mark followed by a space and a capital letter, an opening bracket or an opening quotation mark. "e.g., the" is not cut; "U.S. Census" would be. For chunking a wrong cut costs little, because the pieces are packed back together.

### 6.7.2 Code

`ragbook/ch06_chunking.py`, the function `split_sentences`, the name `CUTS` and the functions `cut_to_fit` and `recursive_chunks`

```python
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
```

```python
# The ways of cutting a text, from largest pieces to smallest, and what is
# put between pieces when they are packed back into chunks.
CUTS = [
    (split_paragraphs, "\n\n"),
    (split_sentences, " "),
]
```

```python
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
```

```python
def recursive_chunks(text, heading_lines, size=CHUNK_WORDS):
    """
    Cut a cleaned text at headings, then paragraphs, then sentences, then
    words, until every chunk has at most `size` words.

    Each chunk starts with its section's heading (6.6), so a chunk from
    the middle of a section still names its subject. The heading's words
    count towards `size`. A heading longer than a third of `size` is not
    repeated: it stays at the start of the section's text, which is cut
    like any other. (In a document whose heading sizes are also used for
    other text, many lines can run together into one long "heading".)

    Example:
        recursive_chunks("Prices\\n\\na b.\\n\\nc d.", ["Prices"], size=3)
        returns ["Prices\\n\\na b.", "Prices\\n\\nc d."]
    """
    chunks = []
    for heading, body in split_sections(text, heading_lines):
        if heading == "":
            chunks.extend(cut_to_fit(body, size))
        elif count_words(heading) > size // 3:
            chunks.extend(cut_to_fit(heading + "\n\n" + body, size))
        else:
            for piece in cut_to_fit(body, size - count_words(heading)):
                chunks.append(heading + "\n\n" + piece)
    return chunks
```

### 6.7.3 Annotations

- `(?<=[.?!])` checks that the character before the space ends a sentence; `\s+` is the space, which is removed; `(?=[A-Z(“])` checks the next character without removing it. `re.split` cuts the paragraph at each match.
- `CUTS` lists each way of cutting with its `joiner` (6.5). A list makes the order visible and lets a reader add a way, such as cutting at line breaks.
- In `cut_to_fit`, `cuts[0]` is the way to try now and `cuts[1:]` the ways left. Each time the function calls itself the list is one shorter, so it always stops.
- `pack` returns chunks that fit, and chunks of a single piece that does not; `cut_to_fit` returns the first kind unchanged and cuts the second kind further.
- `recursive_chunks` cuts the body to fit `size` minus the heading's words, then puts the heading in front of each piece. A heading of more than 30 words (a third of 90) is not repeated; without this rule a 90-word heading would leave no room for text, and the 2025 SNA, whose heading size is also used on its contents pages, has such headings.

On the example, recursive chunking gives 278 chunks, from 8 words to 90; the median is 71. One piece of text is cut by the last step: a run of Annex B's equations, 103 words with no full stop, which the sentence rule reads as one sentence. A test checks that the chunks, without their headings, hold every word of the text in its order.

Repeating the headings adds 1,562 words: 18,196 words in all, against 16,634 in the text. Three chunks have fewer than 15 words, one of them "deflator." from the false paragraph end (6.5).

## 6.8 Comparing the methods

### 6.8.1 Principles

The five methods are run on the same cleaned text with the same limit, 90 words. Three questions decide between them:

1. Does every chunk fit the embedding model? A chunk longer than 256 word pieces is cut off without warning (Chapter 4), so its end is never searched.
2. Does a chunk hold one subject? A chunk cut mid-sentence, or one that runs across two sections, is harder to match to a question.
3. How much text is stored? Overlap and repeated headings add words to embed and store.

Word pieces are counted with the model's own **tokenizer**, the part of the model that cuts text into word pieces. This needs the model, so it runs only where the model is installed.

### 6.8.2 Code

`ragbook/ch06_chunking.py`, the functions `chunk_sizes`, `all_methods` and `count_word_pieces`

```python
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
```

```python
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
```

```python
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
```

### 6.8.3 Annotations

- `sizes[len(sizes) // 2]` is the middle value of the sorted sizes; `//` divides and drops the remainder.
- `model.tokenizer(chunk)` returns the chunk's word pieces as numbers under `"input_ids"`, with a marker added at the start and one at the end; the limit of 256 counts them.
- The worked example (`python -m ragbook.ch06_chunking`) prints the table below. With `--word-pieces` it loads the model with Chapter 4's `load_model` and adds the word-piece count.

### 6.8.4 Results

On the example (16,634 words). Word pieces were counted on the author's laptop with python -m ragbook.ch06_chunking --word-pieces:

| Method | Chunks | Words stored | Smallest (words) | Median (words) | Largest (words) | Over 90 words | Over 256 word pieces | Largest (word pieces) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed size | 185 | 16,634 | 74 | 90 | 90 | 0 | 0 | 241 |
| Fixed size with overlap | 231 | 20,774 | 74 | 90 | 90 | 0 | 0 | 247 |
| Paragraph | 158 | 16,634 | 1 | 84 | 279 | 65 | 17 | 341 |
| Header | 24 | 16,634 | 85 | 473 | 2,638 | 23 | 22 | 3,424 |
| Recursive | 278 | 18,196 | 8 | 71 | 90 | 0 | 0 | 243 |

- Fixed size fits both limits and stores each word once, but cuts sentences.
- Overlap keeps the words around each cut together, at the cost of 25% more words to embed.
- Paragraph chunks never cut a sentence, but 65 are over the word limit and 17 over the model's.
- Header chunks keep whole subjects, but 23 of 24 are over the limit; the longest is 29 times it.
- Recursive chunks fit the limit, cut inside a sentence only once, and carry their heading, for 9% more words.

### 6.8.5 Choosing the limit

A first draft of this chapter used 150 words. Counted with all-MiniLM-L6-v2's tokenizer on the author's laptop (`python -m ragbook.ch06_chunking --word-pieces`), every method then had chunks over 256 word pieces:

| Method (150 words) | Chunks over 256 word pieces | Largest chunk (word pieces) |
| --- | --- | --- |
| Fixed size | 7 of 111 | 365 |
| Fixed size with overlap | 8 of 139 | 337 |
| Paragraph | 22 of 123 | 341 |
| Header | 22 of 24 | 3,424 |
| Recursive | 5 of 167 | 359 |

The worst chunk had 2.4 word pieces per word. Recursive chunking was then run at six limits:

| Limit (words) | Chunks | Over 256 word pieces | Largest chunk (word pieces) |
| --- | --- | --- | --- |
| 80 | 317 | 0 | 226 |
| 90 | 278 | 0 | 243 |
| 100 | 246 | 1 | 260 |
| 110 | 225 | 1 | 271 |
| 120 | 208 | 2 | 279 |
| 130 | 192 | 2 | 302 |

90 words is the largest limit at which no recursive chunk passes the model's limit, so the chapter uses 90. A test records the choice.

### 6.8.6 Why words are a poor measure

At 150 words, the five recursive chunks over 256 word pieces were three tables and two parts of the reference list:

| Section | Content | Words | Word pieces |
| --- | --- | --- | --- |
| Assumptions about Countries with Similar Economic Structures | Table of spending shares by country and year | 149 | 359 |
| Comparing ICP Benchmark Results | Table of PPPs and real expenditure | 147 | 331 |
| Comparing ICP Benchmark Results | Table column headings and figures | 105 | 261 |
| Conclusion (Annex D) | Reference list | 146 | 269 |
| Conclusion (Annex D) | Reference list | 148 | 296 |

The tokenizer holds common English words whole, but cuts numbers ("51.6"), abbreviations ("HFCE"), names and web addresses into several pieces each. Tables and reference lists are full of them; prose has few. The reference list sits in Annex D's "Conclusion" because "REFERENCES" is printed too small to be found as a heading (6.6).

So a word limit that suits prose can fail on tables. For a new document, count word pieces, not only words.

## 6.9 Tests, glossary and links

### 6.9.1 Tests

The file `tests/test_ch06_chunking.py` holds 33 tests. Small examples test each function; tests on the example PDF fix the figures reported in this chapter. None needs the embedding model. Run them with `python -m pytest tests/test_ch06_chunking.py -v`.

| Test | What it proves |
| --- | --- |
| Example PDF is the published file | Its SHA-256 fingerprint matches the one recorded when the file was added, so every figure in this chapter comes from the same file |
| Page counts | 34 pages, the last empty; 17,384 words as extracted |
| Running header, number on its own line | The number and the next line go |
| Running header, number and header on one line | That one line goes |
| Running header, other pages | A page that does not start with a number is unchanged |
| Repair examples | "esti -" + "mates" becomes "estimates"; "T esting" becomes "Testing" |
| First-page footer | The last four lines go when the last is a number |
| Words joined across pages | A word broken at the foot of one page is joined to the next |
| Paragraph end | A line with no space at its end is followed by an empty line |
| No running headers left | No trace of the headers; 16,634 words; 83 hyphen and 16 T repairs |
| Known fault: "PPPbased" | The one wrong hyphen join is recorded |
| Bracket pieces removed | No private-use characters, narrow no-break spaces or runs of empty lines; 244 bracket pieces |
| Paragraph across a page and the footer | The paragraph from page 473 runs on to page 474; 519 paragraph ends; 425 paragraphs |
| Word count | Words are counted at spaces and line breaks |
| Fixed size, no overlap | "a b c d e" in twos gives "a b", "c d", "e" |
| Fixed size, with overlap | Each chunk repeats the last word of the one before; a short text gives one chunk |
| Overlap as large as the chunk | Refused |
| Paragraphs | Split at empty lines, each made one line |
| Packing | Short pieces are joined up to the limit; a long piece stays alone |
| Paragraph chunks | Short paragraphs are packed, separated by an empty line |
| Font sizes | Body text 10 points; 806, 110 and 53 characters at 15, 12 and 18 points |
| Heading lines | 37 lines; the first three; "Conclusion" twice |
| Sections and header chunks | Text before the first heading stands alone; two headings in a row form one; a two-line heading is one |
| Header chunks on the example | 24 sections; three headings checked |
| Sentences | Cut after "rose." but not after "e.g.," |
| Cutting to fit | Paragraphs first, then sentences, then words |
| Recursive chunks repeat the heading | Each chunk starts with its section's heading |
| Recursive chunks on the example | None over 90 words; without headings, every word of the text in order |
| Chunk sizes | Count, smallest, median and largest |
| Chunk limit | 90 words, the largest that kept every recursive chunk within 256 word pieces (6.8.5) |
| Comparison on the example | The chunk counts and largest sizes in 6.8.4 |
| Dot leaders and font codes | A row of dots becomes a space; a word of font codes ("/g38", "#23") is removed |
| Long heading not repeated | A heading longer than a third of the limit is cut with the text, so every chunk still fits |

### 6.9.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Chunk | A passage cut from a document, small enough to embed and retrieve |
| Chunking | Cutting documents into chunks |
| Running header | A line printed at the top of every page, such as the book or chapter title |
| Drop capital | A large first letter of a chapter, printed in its own place |
| Private-use characters | Unicode codes E000 to F8FF, which each font may use for its own symbols |
| Fixed-size chunking | Giving every chunk the same number of words, wherever the count ends |
| Overlap | Words a chunk repeats from the end of the chunk before |
| Paragraph chunking | Cutting where paragraphs end |
| Packing | Joining short pieces of text, in order, into one chunk up to the limit |
| Point | The unit of type size, 1/72 of an inch |
| Heading line | A line printed in a heading size |
| Header chunking | Making each section one chunk, from its heading to the next |
| Recursive chunking | Cutting at headings, then paragraphs, then sentences, then words, until every chunk fits the limit |
| Recursive function | A function that calls itself, each time on a smaller problem |
| Tokenizer | The part of a model that cuts text into word pieces |

### 6.9.3 Links

- [McCarthy, P. (2013), "Extrapolating PPPs and Comparing ICP Benchmark Results", Chapter 18 of World Bank, *Measuring the Real Size of the World Economy* (DOI 10.1596/978-0-8213-9728-2)](https://doi.org/10.1596/978-0-8213-9728-2)
- [The example PDF and its licence on GitHub](https://github.com/lavanito/python-rag-textbook/tree/main/data/sources)
- [pypdf documentation](https://pypdf.readthedocs.io/)
- [all-MiniLM-L6-v2 model card (Hugging Face)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Python `re` module](https://docs.python.org/3/library/re.html)
- [Unicode: private-use characters](https://www.unicode.org/faq/private_use.html)
- [Chapter 6 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch06_chunking.py)
