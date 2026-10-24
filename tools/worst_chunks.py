"""
Show the recursive chunks of one PDF that pass the embedding model's
word-piece limit, so the cause can be seen (Chapter 6, 6.8).

Usage (on a computer with the Chapter 4 model):
    python tools/worst_chunks.py FILE SMALLEST LARGEST [HOW_MANY]

For each chunk over the limit it prints the number of words and word
pieces, the longest word, the share of characters that are letters, and
the first 160 characters. The output is for checking only; it is not
committed and the book reports counts only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragbook.ch04_semantic_search import load_model
from ragbook.ch06_chunking import (
    clean_pdf_text,
    count_word_pieces,
    count_words,
    find_heading_lines,
    read_pdf_pages,
    recursive_chunks,
)


def letter_share(text):
    """Return the share of non-space characters that are letters."""
    characters = [c for c in text if not c.isspace()]
    if not characters:
        return 0.0
    return sum(1 for c in characters if c.isalpha()) / len(characters)


def show_worst(pdf_path, smallest, largest, how_many=5):
    pages = read_pdf_pages(pdf_path)
    text, _ = clean_pdf_text(pages)
    heading_lines = find_heading_lines(pdf_path, smallest, largest)
    chunks = recursive_chunks(text, heading_lines)

    model = load_model()
    pieces = count_word_pieces(model, chunks)
    over = [(p, i) for i, p in enumerate(pieces) if p > model.max_seq_length]
    over.sort(reverse=True)

    print(f"== {Path(pdf_path).name}: {len(over)} of {len(chunks)} recursive chunks over "
          f"{model.max_seq_length} word pieces; the {min(how_many, len(over))} largest:")
    for p, i in over[:how_many]:
        chunk = chunks[i]
        longest = max(chunk.split(), key=len)
        print()
        print(f"Chunk {i}: {count_words(chunk)} words, {p} word pieces, "
              f"letters {letter_share(chunk):.0%} of characters")
        print(f"  Longest word ({len(longest)} characters): {longest[:60]!r}")
        print(f"  Starts: {chunk[:160]!r}")


if __name__ == "__main__":
    how_many = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    show_worst(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), how_many)
