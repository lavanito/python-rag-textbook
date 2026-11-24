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


def test_walkthrough_covers_every_task_and_row_once():
    steps = page.walkthrough()["steps"]
    assert [s["step"] for s in steps] == [1, 2, 3, 4, 5, 6]
    tasks = [m["step"] for s in steps for m in s["means"]]
    assert sorted(tasks) == sorted(page.answering_tasks())
    rows = [r["in_this_build"] for s in steps for r in s["at_full_scale"]]
    assert sorted(rows) == sorted(r["in_this_build"] for r in page.at_full_scale()["rows"])


# Code and the models are means, never actors (Lavan, 24 Nov): not the subject of
# an action verb. "Calculated using code" and "the language model's output" are fine;
# "code calculates" and "the language model writes" are not.
ACTION_VERBS = (r"writes?|wrote|explains?|answers?|reads?|checks?|decides?|chooses?|finds?|calculates?|fills?|"
                r"routes?|keeps?|says|states?|gives?|returns?|knows?|thinks?|understands?|invents?|makes?|"
                r"adds?|drops?|retries|records?|sends?|picks?|follows?|restates?|cites?|groups?|draws?|"
                r"works? out|produces?|generates?|uses?|builds?|reports?|shows?|passes|treats?|tries|"
                r"learns?|assumes?")
MEANS_AS_ACTOR = re.compile(
    r"\b(code|(?:the |a )?(?:language |embedding |reranking |NNI )?model)\s+"
    r"(?:then |also |only |never |must |can |cannot |should |will |does not |did not )?(" + ACTION_VERBS + r")\b",
    re.I)
# Matches where the subject is something else.
NOT_AN_ACTOR = ["steps that call the language model use tokens"]
PAGE_TEXT_FILES = ["method_and_caveats", "coverage_grid", "change_log", "faq", "lessons", "at_full_scale",
                   "sources", "walkthrough"]


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)


def means_as_actor(text):
    for phrase in NOT_AN_ACTOR:
        text = text.replace(phrase, "")
    return [m.group(0) for m in MEANS_AS_ACTOR.finditer(text)]


def test_means_are_never_the_actor():
    """In the front matter and in all page text, code and the models are never the
    subject of an action verb."""
    found = means_as_actor((ROOT / "book" / "front_matter.md").read_text(encoding="utf-8"))
    for name in PAGE_TEXT_FILES:
        page_data = json.loads((ROOT / "app" / "data" / f"{name}.json").read_text(encoding="utf-8"))
        for text in strings_in(page_data):
            found += means_as_actor(text)
    figures = json.loads((ROOT / "app" / "data" / "figures.json").read_text(encoding="utf-8"))
    for text in strings_in([figures["wording"], figures["definitions"]]):
        found += means_as_actor(text)
    assert found == []
    assert means_as_actor("Code calculates the figures.") == ["Code calculates"]
    assert means_as_actor("The language model then writes a reply.") == ["The language model then writes"]


def test_process_sentences_name_code_as_the_means():
    """No personification of code (Lavan, 24 Nov): code is named only as the means ("using code")."""
    for step in page.walkthrough()["steps"]:
        assert not re.match(r"^(The )?code\b", step["process"], re.I)