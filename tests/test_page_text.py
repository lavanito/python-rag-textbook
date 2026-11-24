"""
Test: the page's lessons, "At full scale" table and sources match their records.

What this checks
    tools/build_page_text.py rebuilds app/data/lessons.json,
    at_full_scale.json and sources.json; each stored file must equal the
    rebuilt one. The lessons are Chapter 15.7's, item for item. Every count
    in the "At full scale" table equals the count recomputed from the data
    (lesson L9). Every corpus source has a link with two dates, and every
    data edition is CC BY 4.0.

Chapter: none (demonstrator, gate A5). Runs on every change.
"""

import importlib.util
import json
import re
from pathlib import Path

from tests.test_published_counts import recompute

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_page_text", ROOT / "tools" / "build_page_text.py")
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)


def test_stored_files_equal_the_rebuilt_files():
    for name, build in page.FILES.items():
        assert json.loads((page.OUT / name).read_text(encoding="utf-8")) == build(), name


def test_lessons_are_chapter_15s():
    lessons = page.lessons()
    assert len(lessons["what_worked"]) == 11
    assert len(lessons["what_a_production_version_needs"]) == 10


def test_counts_in_the_at_full_scale_table_match_the_data():
    totals = recompute()
    text = " ".join(r["in_this_build"] for r in page.at_full_scale()["rows"])
    expected = {"passages": "passages", "sources": "sources", "things": "things", "triplets": "triplets"}
    for word, total in expected.items():
        for number in re.findall(rf"(\d+) {word}", text):
            assert int(number) == totals[total], word
    assert re.search(rf"Question bank of {totals['bank questions']}\b", text)


def test_every_source_has_a_link_and_two_dates():
    sources = page.sources()
    assert len(sources["corpus"]) == recompute()["sources"]
    for source in sources["corpus"]:
        assert source["url"].startswith("http") and source["document_date"] and source["date_read"]
    for edition in sources["data"]:
        assert edition["licence"] == "CC BY 4.0" and edition["series"]


def test_lessons_are_written_once():
    """15.7 is the one source of truth (Lavan, 24 Nov): the front matter points to it."""
    front = (ROOT / "book" / "front_matter.md").read_text(encoding="utf-8")
    section = front.split("## Lessons for a production version", 1)[1].split("\n## ", 1)[0]
    assert "15.7" in section
    assert "### What worked" not in section and not re.search(r"^\d+\. ", section, re.M)
