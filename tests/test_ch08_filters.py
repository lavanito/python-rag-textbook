"""
Tests for Chapter 8: ragbook/ch08_filters.py.

What this checks
    The licence filter keeps only the licence classes a use mode allows.
    The edition filter keeps the SNA edition a question names, or the latest
    edition on a topic when it names none, and never touches other sources.
    Every withheld passage is recorded with a reason. Chroma, given the same
    filters as a "where" condition, returns what exact search returns.

Why it matters
    A withheld passage must never reach the model. If the filters let one
    through, an answer could quote text the use mode does not permit, or mix
    two editions without saying so.

Chapter: 8. Runs on every change; needs no model and no internet.
"""

import json

import pytest

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import load_questions
from ragbook.ch04_semantic_search import load_embeddings
from ragbook.ch05_hybrid_search import saved_question_embedder
from ragbook.ch07_vector_store import open_store, store_passages
from ragbook.ch08_filters import (
    USE_MODES, FilteredSearch, add_filter_fields, chroma_filter, compare_with_filtered_exact,
    edition_filter, editions_named, filter_passages, licence_filter, reachable, record_withheld,
    search_store_filtered,
)

PASSAGES = load_corpus()
QUESTIONS = load_questions()
SAVED = load_embeddings()


def test_non_commercial_use_keeps_every_passage():
    kept, withheld = licence_filter(PASSAGES, "non-commercial")
    assert len(kept) == len(PASSAGES) and withheld == []


def test_commercial_use_keeps_only_open_passages():
    kept, withheld = licence_filter(PASSAGES, "commercial")
    assert {passage["licence_class"] for passage in kept} == {"open"}
    assert (len(kept), len(withheld)) == (41, 15)
    assert all(record["filter"] == "licence" and record["reason"] for record in withheld)


def test_editions_named():
    assert editions_named("What did the 2008 SNA call depreciation?") == ["SNA08"]
    assert editions_named("Compare the SNA 2008 and the 2025 SNA") == ["SNA08", "SNA25"]
    assert editions_named("What is net national income?") == []


def test_latest_edition_withholds_only_older_passages_with_a_newer_one_on_the_topic():
    kept, withheld = edition_filter(PASSAGES, "What is net national income?")
    assert [record["id"] for record in withheld] == ["sna08-2.144", "sna08-12.26"]
    # 2008 SNA 15.187 has no 2025 SNA passage on its topic, so it stays.
    assert "sna08-15.187" in [passage["id"] for passage in kept]


def test_named_edition_withholds_the_other_edition_only():
    kept, withheld = edition_filter(PASSAGES, "How did the 2008 SNA define net national income?")
    assert {record["id"].split("-")[0] for record in withheld} == {"sna25"}
    kept_sources = {passage["source_code"] for passage in kept}
    assert "SNA25" not in kept_sources and {"SNA08", "ESA10", "BEA"} <= kept_sources


def test_both_filters_never_keep_a_withheld_passage():
    for use_mode in USE_MODES:
        for question in QUESTIONS:
            kept, withheld = filter_passages(PASSAGES, question["question"], use_mode)
            kept_ids = {passage["id"] for passage in kept}
            withheld_ids = {record["id"] for record in withheld}
            assert kept_ids.isdisjoint(withheld_ids)
            assert len(kept_ids) + len(withheld_ids) == len(PASSAGES)


def test_log_has_one_line_per_withheld_passage(tmp_path):
    log_file = tmp_path / "withheld.jsonl"
    kept, withheld = filter_passages(PASSAGES, "What is net national income?", "commercial")
    record_withheld("What is net national income?", "commercial", withheld, log_file)
    record_withheld("What is net national income?", "commercial", withheld, log_file)
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2 * len(withheld)
    assert set(lines[0]) == {"time", "use_mode", "question", "id", "filter", "reason"}


def test_filtered_search_never_returns_a_withheld_passage():
    search = FilteredSearch(PASSAGES, SAVED, saved_question_embedder(QUESTIONS, SAVED))
    for question in QUESTIONS:
        results, withheld = search.rank(question["question"], "commercial", how_many=10)
        withheld_ids = {record["id"] for record in withheld}
        assert all(result["id"] not in withheld_ids for result in results)


def test_six_questions_cannot_be_reached_in_commercial_use():
    kept_ids = {question["id"] for question in reachable(QUESTIONS, PASSAGES, "commercial")}
    lost = sorted({question["id"] for question in QUESTIONS} - kept_ids)
    assert lost == ["q2-03", "q2-16", "q2-18", "q2-19", "q2-24", "q2-32"]


def test_chroma_filter_examples():
    assert chroma_filter("commercial", []) == {"licence_class": {"$in": ["open"]}}
    withheld = [{"id": "sna08-2.144", "filter": "edition", "reason": "r"},
                {"id": "qna17-12.1", "filter": "licence", "reason": "r"}]
    assert chroma_filter("non-commercial", withheld)["$and"][1] == {"passage_id": {"$nin": ["sna08-2.144"]}}


@pytest.fixture(scope="module")
def filtered_store(tmp_path_factory):
    client = open_store(tmp_path_factory.mktemp("chroma"))
    collection = store_passages(client, PASSAGES, SAVED, name="corpus_filtered")
    add_filter_fields(collection, PASSAGES)
    return collection


def test_chroma_returns_only_allowed_licence_classes(filtered_store):
    results = search_store_filtered(filtered_store, SAVED["q2-17"], chroma_filter("commercial", []), 10)
    assert {result["licence_class"] for result in results} == {"open"}


def test_chroma_agrees_with_filtered_exact_search(filtered_store):
    for use_mode in USE_MODES:
        same, different = compare_with_filtered_exact(filtered_store, PASSAGES, SAVED, QUESTIONS, use_mode)
        assert (same, different) == (len(QUESTIONS), [])
