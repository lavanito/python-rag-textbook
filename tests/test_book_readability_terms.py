"""
Test: the record of terms to change in the readability edit is complete and current (gate B3s).

What this checks
    tools/readability_terms.py lists every use, in the book's prose, of a
    term replaced by a decision since the chapters were signed off (triplet,
    thing, class of a question, locked block, hits at, by meaning, lookup,
    with content). The uses are recorded in
    data/review/terms_for_readability_edit.csv (57 on 28 November 2026).
    This test fails if the book has a use that is not in the record, and if
    the record has a row whose use has gone: delete the row when the sentence
    is fixed, so the record stays the list still to fix.

Chapter: none (gate B3s). Runs on every change.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import readability_terms  # noqa: E402


def test_no_new_use_of_a_replaced_term():
    new = readability_terms.found() - readability_terms.recorded()
    assert not new, f"New uses of a replaced term; use the glossary's term: {sorted(new)}"


def test_record_lists_only_what_is_still_there():
    fixed = readability_terms.recorded() - readability_terms.found()
    assert not fixed, f"Fixed in the book; delete these rows from the record: {sorted(fixed)}"


def test_every_row_names_its_replacement_and_decision():
    import csv
    with open(readability_terms.RECORD, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows
    assert all(row["replaced_by"] and row["decision"] for row in rows)
