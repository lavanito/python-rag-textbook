"""
Tests for the corpus: data/corpus/passages.jsonl.

What this checks
    Every passage has the fields the book relies on, ids are unique,
    every source is listed in SOURCES.md, and the limits agreed with
    publishers are kept.

Why it matters
    Every answer the system gives cites a passage. A passage with a missing
    source or reference, or one that breaks a publisher's limit, would make
    those citations unreliable.

The check that each passage is quoted word for word from its source PDF is
run when the corpus is built, because the PDFs are not stored here.
"""

from pathlib import Path

from ragbook.ch01_python_basics import load_passages

CORPUS_FOLDER = Path(__file__).parent.parent / "data" / "corpus"
PASSAGES = load_passages(CORPUS_FOLDER / "passages.jsonl")

REQUIRED_FIELDS = {
    "id", "source", "reference", "text", "edition", "source_code",
    "topic", "components", "partial", "access", "licence",
}
ALLOWED_COMPONENTS = {"C1a", "C1b", "C2", "C3", "C4", "quality"}
ALLOWED_ACCESS = {"public", "subscriber"}


def test_every_passage_has_all_fields():
    for passage in PASSAGES:
        missing = REQUIRED_FIELDS - set(passage.keys())
        assert missing == set(), f"{passage['id']} is missing {missing}"


def test_ids_are_unique():
    ids = [passage["id"] for passage in PASSAGES]
    assert len(ids) == len(set(ids))


def test_no_field_is_empty():
    for passage in PASSAGES:
        for field in ["id", "source", "reference", "text", "licence", "topic"]:
            assert passage[field].strip() != "", f"{passage['id']} has an empty {field}"


def test_components_and_access_use_agreed_labels():
    for passage in PASSAGES:
        assert set(passage["components"]) <= ALLOWED_COMPONENTS, passage["id"]
        assert passage["access"] in ALLOWED_ACCESS, passage["id"]


def test_exactly_one_passage_is_marked_subscriber_only():
    # One passage carries a demonstration label for Chapter 8 (access rules).
    subscriber = [passage["id"] for passage in PASSAGES if passage["access"] == "subscriber"]
    assert len(subscriber) == 1


def test_every_source_code_is_listed_in_sources_file():
    sources_text = (CORPUS_FOLDER / "SOURCES.md").read_text(encoding="utf-8")
    for passage in PASSAGES:
        assert f"| {passage['source_code']} |" in sources_text, passage["source_code"]


def test_imf_quotations_stay_within_1000_words():
    # IMF fair-use terms: up to 1,000 words from any one source.
    words = 0
    for passage in PASSAGES:
        if passage["source_code"] == "QNA17":
            words = words + len(passage["text"].split())
    assert words <= 1000, f"IMF quotations total {words} words"


def test_passages_are_short():
    # One paragraph each; the longest agreed passage is under 200 words.
    for passage in PASSAGES:
        assert len(passage["text"].split()) < 200, passage["id"]
