"""
Test: the code shown in the book is the code that is tested.

What this checks
    Every Python code block in a signed-off chapter (book/chNN_*.md) must
    appear, character for character, in the matching code file
    (ragbook/chNN_*.py).

Why it matters
    The book shows code to read; the tests check the code that runs.
    If the two drift apart, the reader is shown untested code.

How it works
    1. For each chapter file in book/, find the code file with the same name.
    2. Pull out every block that starts with ```python and ends with ```.
    3. Check that each block is found, unchanged, inside the code file.

Chapter: front matter (repository rules). Runs on every change.
"""

from pathlib import Path

BOOK_FOLDER = Path(__file__).parent.parent / "book"
CODE_FOLDER = Path(__file__).parent.parent / "ragbook"


def python_blocks(markdown_text):
    """
    Return the contents of every ```python block in a Markdown text.

    Example:
        "Intro\\n```python\\nx = 1\\n```\\nEnd"
        gives ["x = 1"]
    """
    blocks = []
    inside_block = False
    current_lines = []
    for line in markdown_text.splitlines():
        if not inside_block and line.strip() == "```python":
            inside_block = True
            current_lines = []
        elif inside_block and line.strip() == "```":
            inside_block = False
            blocks.append("\n".join(current_lines))
        elif inside_block:
            current_lines.append(line)
    return blocks


def blocks_missing_from_code(book_folder, code_folder):
    """
    List every book code block that is not an exact copy of its code file.

    Each problem is described as "<chapter file>: block <n> not found".
    """
    problems = []
    for chapter_file in sorted(book_folder.glob("ch*.md")):
        code_file = code_folder / (chapter_file.stem + ".py")
        if not code_file.exists():
            problems.append(f"{chapter_file.name}: no code file {code_file.name}")
            continue
        code_text = code_file.read_text(encoding="utf-8")
        markdown_text = chapter_file.read_text(encoding="utf-8")
        block_number = 0
        for block in python_blocks(markdown_text):
            block_number = block_number + 1
            if block not in code_text:
                problems.append(f"{chapter_file.name}: block {block_number} not found in {code_file.name}")
    return problems


def test_every_book_code_block_is_in_its_code_file():
    problems = blocks_missing_from_code(BOOK_FOLDER, CODE_FOLDER)
    assert problems == [], "Book and code differ:\n" + "\n".join(problems)


def test_the_check_catches_an_edited_block(tmp_path):
    """Check the checker: a block changed in the book must be caught."""
    book = tmp_path / "book"
    code = tmp_path / "ragbook"
    book.mkdir()
    code.mkdir()
    (code / "ch01_demo.py").write_text("def add(a, b):\n    return a + b\n")
    (book / "ch01_demo.md").write_text(
        "Good:\n```python\ndef add(a, b):\n    return a + b\n```\n"
        "Edited:\n```python\ndef add(a, b):\n    return a - b\n```\n"
    )
    assert blocks_missing_from_code(book, code) == ["ch01_demo.md: block 2 not found in ch01_demo.py"]
