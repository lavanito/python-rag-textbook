"""
Test: code reuse runs forward only.

What this checks
    Every chapter file in the ragbook folder may import functions from
    EARLIER chapters, never from the same or LATER chapters.
    Chapter 5 may use Chapter 3. Chapter 3 may never use Chapter 5.

Why it matters
    A reader working through the book in order should never meet code
    that depends on something not yet explained.

How it works
    1. Find every chapter file, named like ch03_keyword_search.py.
    2. Read each file as Python source, without running it.
    3. List every import that points at another ragbook file.
    4. Compare chapter numbers and record any import that goes the wrong way.

Appendix files (named like appB_weaviate.py) may import any chapter,
because appendices come after all chapters. No chapter may import an
appendix.

Chapter: front matter (repository rules). Runs on every change.
"""

import ast
import re
from pathlib import Path


# The folder that holds the book's code, one file per chapter.
CODE_FOLDER = Path(__file__).parent.parent / "ragbook"

# Chapter files look like "ch03_keyword_search.py".
# The two digits after "ch" are the chapter number.
CHAPTER_NAME = re.compile(r"^ch(\d\d)_")

# Appendix files look like "appB_weaviate.py".
APPENDIX_NAME = re.compile(r"^app[A-Z]_")


def chapter_number(module_name):
    """
    Return the chapter number of a ragbook file name, or None.

    Example:
        chapter_number("ch03_keyword_search")  ->  3
        chapter_number("appB_weaviate")        ->  None
        chapter_number("helpers")              ->  None
    """
    match = CHAPTER_NAME.match(module_name)
    if match is None:
        return None
    return int(match.group(1))


def ragbook_imports(file_path):
    """
    List the ragbook files that one file imports, by module name.

    Example:
        A file containing the line
            from ragbook.ch03_keyword_search import bm25_rank
        gives
            ["ch03_keyword_search"]

    The file is read as text and parsed; it is never run.
    """
    source_text = file_path.read_text(encoding="utf-8")
    syntax_tree = ast.parse(source_text)

    imported_names = []
    for node in ast.walk(syntax_tree):
        # Form 1:  from ragbook.ch03_keyword_search import bm25_rank
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            parts = node.module.split(".")
            if parts[0] == "ragbook" and len(parts) > 1:
                imported_names.append(parts[1])
        # Form 2:  import ragbook.ch03_keyword_search
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "ragbook" and len(parts) > 1:
                    imported_names.append(parts[1])
    return imported_names


def find_wrong_way_imports(folder):
    """
    Return a list of imports that break the forward-only rule.

    Example:
        A folder holding ch03_a.py, which imports ragbook.ch05_b, gives
            ["ch03_a imports ch05_b"]
        A folder where every import points to an earlier chapter gives
            []
    """
    wrong_way = []

    for file_path in sorted(folder.glob("*.py")):
        this_name = file_path.stem
        this_chapter = chapter_number(this_name)

        # Only chapter files are restricted. Appendices may import any chapter.
        if this_chapter is None:
            continue

        for imported_name in ragbook_imports(file_path):
            if APPENDIX_NAME.match(imported_name):
                wrong_way.append(f"{this_name} imports appendix {imported_name}")
                continue

            imported_chapter = chapter_number(imported_name)
            if imported_chapter is None:
                continue  # not a chapter file, for example __init__
            if imported_chapter >= this_chapter:
                wrong_way.append(f"{this_name} imports {imported_name}")

    return wrong_way


def test_chapters_import_only_earlier_chapters():
    """Fail if any chapter imports from itself, a later chapter or an appendix."""
    wrong_way = find_wrong_way_imports(CODE_FOLDER)
    assert wrong_way == [], "Imports that go the wrong way:\n" + "\n".join(wrong_way)


def test_the_check_catches_a_backward_import(tmp_path):
    """
    Check the checker: build a small fake folder and confirm it is caught.

    ch03 importing ch01 is allowed; ch03 importing ch05 is not;
    ch03 importing an appendix is not.
    """
    (tmp_path / "ch01_basics.py").write_text("x = 1\n")
    (tmp_path / "ch03_search.py").write_text(
        "from ragbook.ch01_basics import x\n"
        "from ragbook.ch05_hybrid import y\n"
        "import ragbook.appB_weaviate\n"
    )
    (tmp_path / "ch05_hybrid.py").write_text("from ragbook.ch03_search import z\n")

    found = find_wrong_way_imports(tmp_path)

    assert found == [
        "ch03_search imports ch05_hybrid",
        "ch03_search imports appendix appB_weaviate",
    ]


def test_chapter_numbers_are_not_repeated():
    """Fail if two files claim the same chapter number."""
    seen = {}
    repeated = []
    for file_path in sorted(CODE_FOLDER.glob("ch*.py")):
        number = chapter_number(file_path.stem)
        if number is None:
            continue
        if number in seen:
            repeated.append(f"chapter {number}: {seen[number]} and {file_path.stem}")
        else:
            seen[number] = file_path.stem
    assert repeated == [], "Repeated chapter numbers:\n" + "\n".join(repeated)
