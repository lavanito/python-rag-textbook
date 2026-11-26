"""
Test: no new sentence in the book makes code or a model the actor (gate B3s).

What this checks
    Code and the models (language, embedding, reranking, NNI) are means, never
    the subject of an action verb (Lavan, 24 Nov 2026). The book had 31 such
    phrases on 24 November 2026; they are recorded in
    data/review/means_as_actor_book.csv and are fixed in the readability edit.
    This test fails if a book file has one that is not in the record. When a
    sentence is fixed, delete its row, so the record stays the list still to fix.
    The same pattern is used for the page text (tests/test_page_text.py).

Chapter: none (gate B3s). Runs on every change.
"""

import csv
from collections import Counter
from pathlib import Path

from tests.test_page_text import means_as_actor

ROOT = Path(__file__).parent.parent
RECORD = ROOT / "data" / "review" / "means_as_actor_book.csv"


def found_in_book():
    found = Counter()
    for path in sorted((ROOT / "book").glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            for phrase in means_as_actor(line):
                found[(f"book/{path.name}", phrase)] += 1
    return found


def recorded():
    with open(RECORD, encoding="utf-8", newline="") as file:
        return Counter((row["file"], row["phrase"]) for row in csv.DictReader(file))


def test_no_new_means_as_actor_in_the_book():
    new = found_in_book() - recorded()
    assert not new, f"New sentences make code or a model the actor: {sorted(new)}"


def test_record_lists_only_what_is_still_there():
    fixed = recorded() - found_in_book()
    assert not fixed, f"Fixed in the book; delete these rows from the record: {sorted(fixed)}"
