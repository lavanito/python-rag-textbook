"""
Terms in the book to change in the readability edit (gate B3s, for B3c).

What this tool does
    Lists every use, in the book's prose, of a term that a decision has
    replaced since the chapters were signed off. Fenced code blocks and
    inline code are skipped, because the book quotes code as it is. Each
    row names the file, the term, the words found and what replaces them.

    python tools/readability_terms.py          prints the count per term
    python tools/readability_terms.py --write  rewrites the record

    The record is data/review/terms_for_readability_edit.csv. A test fails
    on a use that is not in the record, and on a row whose use has gone
    (delete the row once the sentence is fixed), as for the 31 sentences in
    data/review/means_as_actor_book.csv.

Decisions (claude/decision-log.md)
    9e, 27 Nov: "triple" (triplet its alias); "entity" replaces "thing";
    "question type" (class of a question its alias).
    9g, 28 Nov: hit rate at k; semantic search; lookup question
    (question type Q1); "with content" in literal words.
    Glossary rule 7, 18 Nov: "template part" replaces "locked block".

Chapter: none (gate B3s).
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
RECORD = ROOT / "data" / "review" / "terms_for_readability_edit.csv"

# (term, pattern, replaced by, decision)
TERMS = [
    ("triplet", r"\btriplets?\b", "triple", "9e, decision 2"),
    ("thing", r"\b\d+ things\b|\bthings? in the (?:knowledge )?graph\b", "entity", "9e, decision 3"),
    ("class of a question", r"\bclass(?:es)? of (?:a )?questions?\b|\bquestion class(?:es)?\b", "question type", "9e, decision 4"),
    ("locked block", r"\blocked blocks?\b", "template part", "glossary rule 7"),
    ("hits at", r"\bhits at (?:\d+|k)\b", "hit rate at k", "9g"),
    ("by meaning", r"\bby meaning\b", "by semantic search", "9g"),
    ("lookup", r"\blookups?\b", "lookup question (question type Q1)", "9g"),
    ("with content", r"\bwith content\b", "explanations shown, other than the fixed sentence", "9g"),
]


def prose_lines(text):
    """The lines of a chapter outside fenced code blocks, with inline code removed."""
    inside = False
    for line in text.splitlines():
        if line.startswith("```"):
            inside = not inside
            continue
        if not inside:
            yield re.sub(r"`[^`]*`", "", line)


def found():
    """Every use in the book: (file, term, words found) with a count."""
    uses = Counter()
    for path in sorted((ROOT / "book").glob("*.md")):
        if path.name == "README.md":
            continue
        for line in prose_lines(path.read_text(encoding="utf-8")):
            for term, pattern, _, _ in TERMS:
                for match in re.finditer(pattern, line, re.I):
                    uses[(f"book/{path.name}", term, match.group(0))] += 1
    return uses


def recorded():
    with open(RECORD, encoding="utf-8", newline="") as file:
        return Counter((row["file"], row["term"], row["found"]) for row in csv.DictReader(file))


def write():
    replaced = {term: (by, decision) for term, _, by, decision in TERMS}
    with open(RECORD, "w", encoding="utf-8", newline="") as file:
        out = csv.writer(file)
        out.writerow(["file", "term", "found", "replaced_by", "decision"])
        for (name, term, words), count in sorted(found().items()):
            for _ in range(count):
                out.writerow([name, term, words, *replaced[term]])


if __name__ == "__main__":
    if "--write" in sys.argv:
        write()
    per_term = Counter()
    for (_, term, _), count in found().items():
        per_term[term] += count
    for term, _, _, _ in TERMS:
        print(f"{term}: {per_term[term]}")
