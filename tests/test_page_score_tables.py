"""
Test: the page's two extra score tables equal the tables printed in the book.

What this checks
    app/data/traces.json holds, from tools/build_traces.py:
    - "retrieval": definition questions with a gold passage at depths 1, 3
      and 10 in each use mode, equal to the table in Chapter 8.5.4;
    - "explanation_runs": explanations by status for each saved run, equal to
      the tables in Chapters 14.7.2 and 14.8.2, and to the rerun of
      22 November 2026 as build spec v3, component 15.3, records it.
    Each row carries a training or fair label.

Chapter: none (demonstrator, gate A5; build spec v3, components 15.2, 15.3).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRACES = json.loads((ROOT / "app" / "data" / "traces.json").read_text(encoding="utf-8"))


def printed_table(chapter_file, heading):
    """The rows of the first markdown table after `heading` in a book chapter, as lists of cells."""
    text = (ROOT / "book" / chapter_file).read_text(encoding="utf-8")
    rest = text[text.index(heading):]
    rows = []
    for line in rest.splitlines()[1:]:
        if line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
        elif rows:
            break
    return rows[2:]   # without the header and the line under it


def test_retrieval_equals_chapter_8():
    printed = {r[0]: [int(x) for x in r[1:]] for r in printed_table("ch08_filters.md", "### 8.5.4 Results")}
    for row in TRACES["retrieval"]:
        assert printed[row["use_mode"]] == [row["passages_kept"], row["answerable"],
                                            row["hits_at_1"], row["hits_at_3"], row["hits_at_10"]]
        assert row["label"] == "training"


def counts(row):
    return [row["questions"], row["lookup"], row["passed"], row["passed_on_retry"], row["dropped"], row["with_content"]]


def test_explanation_runs_equal_chapter_14():
    runs = {(r["chapter"], r["set"]): r for r in TRACES["explanation_runs"]}
    for heading, chapter in [("### 14.7.2 Results", "Chapter 14.7"), ("### 14.8.2 Results", "Chapter 14.8")]:
        printed = printed_table("ch14_answer_checks.md", heading)
        assert [int(x) for x in printed[0][1:]] == counts(runs[(chapter, "bank")])
        assert [int(x) for x in printed[1][1:]] == counts(runs[(chapter, "fair")])


def test_rerun_equals_build_spec_15_3():
    """Build spec v3, 15.3: bank 14 (lookup 2, passed 2, on retry 3, dropped 7);
    the vertical domain expert's 10 (lookup 1, passed 4, on retry 2, dropped 3); f-08 and f-09 with content."""
    runs = {(r["chapter"], r["set"]): r for r in TRACES["explanation_runs"]}
    assert counts(runs[("Chapter 15", "bank")]) == [14, 2, 2, 3, 7, 0]
    assert counts(runs[("Chapter 15", "fair")]) == [10, 1, 4, 2, 3, 2]
    assert runs[("Chapter 15", "fair")]["with_content_ids"] == ["f-08", "f-09"]


def test_only_the_first_run_on_new_questions_is_fair():
    labels = {(r["chapter"], r["set"]): r["label"] for r in TRACES["explanation_runs"]}
    assert [k for k, v in labels.items() if v == "fair"] == [("Chapter 14.7", "fair")]
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"]) for r in TRACES["explanation_runs"])
