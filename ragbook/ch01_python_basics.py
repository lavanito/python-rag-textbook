"""
Chapter 1 — The Python you need

What this file does
    Holds the small text-handling functions every later chapter uses:
    cleaning text, splitting it into words, storing a passage as a record,
    finding passages that contain a word, formatting passages for a prompt,
    and saving and loading passages from a file.

Inputs
    Plain text, and passage records (Python dictionaries).

Outputs
    Cleaned text, lists of words, passage records, formatted text blocks,
    and files in the JSON Lines format (one passage per line).

Used by
    Chapter 2 onwards.

Uses
    Python's standard library only (json, string, pathlib).

Run the worked example
    python -m ragbook.ch01_python_basics
"""

import json
import string
from pathlib import Path


# ---------------------------------------------------------------------------
# 1.2  Cleaning text
# ---------------------------------------------------------------------------

def clean_text(text):
    """
    Remove extra spaces, tabs and line breaks from a piece of text.

    Text copied from a PDF often has line breaks in the middle of sentences
    and runs of spaces. This joins it back into one tidy line.

    Example:
        clean_text("  Gross domestic\\n   product  ")
        returns "Gross domestic product"
    """
    # split() with no argument splits on any run of spaces, tabs or line
    # breaks, and drops empty pieces at the start and end.
    pieces = text.split()

    # Put the pieces back together with exactly one space between them.
    cleaned = " ".join(pieces)
    return cleaned


# ---------------------------------------------------------------------------
# 1.3  Lists: splitting text into words
# ---------------------------------------------------------------------------

def split_into_words(text):
    """
    Turn a piece of text into a list of lower-case words, without punctuation.

    Keyword search (Chapter 3) compares lists like this one.

    Example:
        split_into_words("GDP, at market prices.")
        returns ["gdp", "at", "market", "prices"]
    """
    # Step 1: lower case, so "GDP" and "gdp" count as the same word.
    lower_text = text.lower()

    # Step 2: replace every punctuation mark with a space.
    # string.punctuation is a ready-made string of all punctuation marks.
    without_punctuation = ""
    for character in lower_text:
        if character in string.punctuation:
            without_punctuation = without_punctuation + " "
        else:
            without_punctuation = without_punctuation + character

    # Step 3: split on spaces into a list of words.
    words = without_punctuation.split()
    return words


# ---------------------------------------------------------------------------
# 1.4  Dictionaries: a passage as a record
# ---------------------------------------------------------------------------

def make_passage(passage_id, source, reference, text):
    """
    Store one passage and the facts about it in a dictionary.

    Every passage in the book is a record like this. The source and the
    reference travel with the text, so an answer can always say where its
    evidence came from.

    Example:
        make_passage("ex-001", "Example", "para 1", "  GDP measures output. ")
        returns {"id": "ex-001", "source": "Example",
                 "reference": "para 1", "text": "GDP measures output."}
    """
    passage = {
        "id": passage_id,
        "source": source,
        "reference": reference,
        "text": clean_text(text),
    }
    return passage


# ---------------------------------------------------------------------------
# 1.5  Loops and conditions: finding passages that contain a word
# ---------------------------------------------------------------------------

def find_passages_containing(passages, word):
    """
    Return the passages whose text contains a given word.

    The match is on whole words, ignoring case and punctuation:
    "income" matches "Income," but not "incomes".

    Example:
        With passages about "gross domestic product" and "national income",
        find_passages_containing(passages, "income")
        returns only the passage about national income.
    """
    wanted_word = word.lower()
    matches = []
    for passage in passages:
        words_in_passage = split_into_words(passage["text"])
        if wanted_word in words_in_passage:
            matches.append(passage)
    return matches


# ---------------------------------------------------------------------------
# 1.6  f-strings and join: formatting passages for a prompt
# ---------------------------------------------------------------------------

def format_passage(passage):
    """
    Turn one passage record into a short labelled block of text.

    A language model reads text, not dictionaries. This block shows the
    model the source and reference beside the words, so it can cite them.

    Example:
        format_passage({"id": "ex-001", "source": "Example",
                        "reference": "para 1", "text": "GDP measures output."})
        returns
            "[ex-001] Example, para 1\\nGDP measures output."
    """
    heading_line = f"[{passage['id']}] {passage['source']}, {passage['reference']}"
    block = heading_line + "\n" + passage["text"]
    return block


def format_passages(passages):
    """
    Turn a list of passages into one block of text, blank line between each.

    Example:
        Two passages give
            "[ex-001] ...\\n...\\n\\n[ex-002] ...\\n..."
    """
    blocks = []
    for passage in passages:
        blocks.append(format_passage(passage))
    # "\n\n" puts one empty line between consecutive blocks.
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# 1.7  Files: saving and loading passages
# ---------------------------------------------------------------------------

def save_passages(passages, file_path):
    """
    Write passages to a file, one passage per line, in JSON format.

    This layout is called JSON Lines. Each line can be read on its own,
    and the file can be opened in any text editor.

    Example:
        save_passages([passage_1, passage_2], "passages.jsonl")
        writes a file with two lines.
    """
    file_path = Path(file_path)
    lines = []
    for passage in passages:
        # ensure_ascii=False keeps characters such as "é" readable in the file.
        lines.append(json.dumps(passage, ensure_ascii=False))
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_passages(file_path):
    """
    Read passages from a JSON Lines file into a list of dictionaries.

    Blank lines are skipped. The order of passages in the file is kept.

    Example:
        load_passages("passages.jsonl")
        returns [passage_1, passage_2]
    """
    file_path = Path(file_path)
    passages = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "":
            continue
        passages.append(json.loads(line))
    return passages


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

# Sample sentences written for this chapter. They are NOT quotations from any
# manual; the real quoted corpus is introduced in Chapter 2.
SAMPLE_FILE = Path(__file__).parent.parent / "data" / "examples" / "ch01_sample_passages.jsonl"


def main():
    print("1.2  Cleaning text")
    messy = "  Gross domestic\n   product  "
    print("    before:", repr(messy))
    print("    after: ", repr(clean_text(messy)))

    print("\n1.3  Splitting into words")
    print("   ", split_into_words("GDP, at market prices."))

    print("\n1.7  Loading the sample passages")
    passages = load_passages(SAMPLE_FILE)
    print(f"    loaded {len(passages)} passages")

    print("\n1.5  Passages containing 'income'")
    for passage in find_passages_containing(passages, "income"):
        print("   ", passage["id"])

    print("\n1.6  Formatted for a prompt")
    print(format_passages(passages[:2]))


if __name__ == "__main__":
    main()
