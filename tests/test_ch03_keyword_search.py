"""
Tests for Chapter 3 — Keyword search.

Retrieval is tested exactly: these tests fix the rankings and the counts the
chapter reports, so a change to the code or the corpus that moves them shows up.
"""

import math

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import (
    KeywordIndex,
    bm25_score,
    bm25s_rank,
    count_score,
    count_words,
    document_frequencies,
    load_questions,
    search_words,
    tf_idf_score,
    top_three_hits,
)

PASSAGES = load_corpus()
INDEX = KeywordIndex(PASSAGES)
QUESTIONS = load_questions()


def test_search_words_removes_curly_quotes_and_common_words():
    assert search_words("What is the “GDP deflator”?") == ["gdp", "deflator"]
    assert search_words("the country’s population") == ["country", "population"]


def test_search_words_keeps_repeats():
    assert search_words("GDP and GDP") == ["gdp", "gdp"]


def test_count_words():
    assert count_words(["gdp", "income", "gdp"]) == {"gdp": 2, "income": 1}


def test_count_score_adds_each_question_word_once():
    assert count_score(["gdp", "gdp", "deflator"], ["gdp", "growth", "gdp"]) == 2


def test_document_frequencies_count_passages_not_appearances():
    assert document_frequencies([["gdp", "gdp"], ["gdp", "income"]]) == {"gdp": 2, "income": 1}


def test_tf_idf_gives_nothing_to_a_word_in_every_passage():
    frequencies = {"gdp": 2, "income": 1}
    assert tf_idf_score(["gdp"], ["gdp"], frequencies, 2) == 0
    assert math.isclose(tf_idf_score(["income"], ["income"], frequencies, 2), math.log(2))


def test_bm25_repeats_count_for_less():
    frequencies = {"deflator": 1}
    once = bm25_score(["deflator"], ["deflator"], frequencies, 10, 1)
    five_times = bm25_score(["deflator"], ["deflator"] * 5, frequencies, 10, 5)
    assert five_times < 5 * once


def test_bm25_marks_down_long_passages():
    frequencies = {"deflator": 1}
    short = bm25_score(["deflator"], ["deflator", "x"], frequencies, 10, 10)
    long = bm25_score(["deflator"], ["deflator"] + ["x"] * 30, frequencies, 10, 10)
    assert long < short


def test_corpus_frequencies_quoted_in_the_chapter():
    assert INDEX.frequencies["gdp"] == 16
    assert INDEX.frequencies["deflator"] == 2


def test_bm25_ranks_the_deflator_passage_first():
    found = [p["id"] for p in INDEX.rank("What is the GDP deflator?", "bm25")]
    assert found == ["una14-ch1-deflator", "esa10-10.47", "cso-gnistar-2"]


def test_hand_built_bm25_matches_bm25s_on_every_definition_question():
    for question in QUESTIONS:
        by_hand = [p["id"] for p in INDEX.rank(question["question"], "bm25")]
        by_library = [p["id"] for p in bm25s_rank(PASSAGES, question["question"])]
        assert by_hand == by_library, question["id"]


def test_top_three_hits_reported_in_the_chapter():
    assert len(QUESTIONS) == 32
    assert top_three_hits(lambda q: INDEX.rank(q, "counts"), QUESTIONS) == 27
    assert top_three_hits(lambda q: INDEX.rank(q, "tfidf"), QUESTIONS) == 29
    assert top_three_hits(lambda q: INDEX.rank(q, "bm25"), QUESTIONS) == 30


def test_unknown_method_is_refused():
    try:
        INDEX.rank("GDP", "magic")
    except ValueError:
        return
    raise AssertionError("an unknown method was accepted")
