"""
Tests for Chapter 9: ragbook/ch09_reranking.py.

What this checks
    The reranker only reorders the pool it is given: it never adds a
    passage, never returns a withheld one, and keeps pool order for equal
    scores. Saved scores round-trip exactly, and unknown questions are
    refused. Where the saved scores exist (data/reranker/), they are
    checked too.

Why it matters
    A reranker that could reach outside the pool would bypass Chapter 8's
    filters. The count at the pool's depth cannot change: if it did, the
    code would be adding or dropping passages, not reordering them.

Chapter: 9. Runs on every change; needs no model and no internet.
"""

import numpy as np
import pytest

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import load_questions
from ragbook.ch04_semantic_search import load_embeddings
from ragbook.ch05_hybrid_search import hits_at, saved_question_embedder
from ragbook.ch08_filters import FilteredSearch
from ragbook.ch09_reranking import (
    SCORE_FILE, RerankedSearch, build_searches, compare_first_places, load_scores, rerank,
    save_scores, saved_scorer, score_everything, scoring_time,
)

PASSAGES = load_corpus()
QUESTIONS = load_questions()
SAVED = load_embeddings()
EMBED = saved_question_embedder(QUESTIONS, SAVED)


def scores_from(table):
    """A scorer that reads a dictionary: passage id -> score."""
    return lambda question, passages: [table[passage["id"]] for passage in passages]


def test_rerank_sorts_by_score_highest_first():
    pool = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = rerank("q", pool, scores_from({"a": 0.1, "b": 2.0, "c": 0.5}))
    assert [passage["id"] for passage in result] == ["b", "c", "a"]


def test_rerank_keeps_pool_order_for_equal_scores():
    pool = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = rerank("q", pool, scores_from({"a": 1.0, "b": 1.0, "c": 1.0}))
    assert [passage["id"] for passage in result] == ["a", "b", "c"]


def test_rerank_handles_negative_scores_and_how_many():
    pool = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = rerank("q", pool, scores_from({"a": -3.0, "b": -1.0, "c": -2.0}), how_many=2)
    assert [passage["id"] for passage in result] == ["b", "c"]


def test_score_everything_gives_one_row_per_question():
    table, seconds = score_everything(lambda q, ps: [len(q)] * len(ps), QUESTIONS[:3], PASSAGES)
    assert table.shape == (3, len(PASSAGES))
    assert seconds >= 0


def test_save_and_load_scores_round_trip(tmp_path):
    file_path = tmp_path / "scores.npz"
    save_scores(file_path, ["q1", "q2"], ["a", "b"], [[1.5, -2.0], [0.25, 3.0]], 1.25)
    scores = load_scores(file_path)
    assert scores == {"q1": {"a": 1.5, "b": -2.0}, "q2": {"a": 0.25, "b": 3.0}}
    assert scoring_time(file_path) == (1.25, 4)


def test_saved_scorer_refuses_unknown_questions():
    score_passages = saved_scorer(QUESTIONS, {})
    with pytest.raises(KeyError):
        score_passages("A question not in the bank?", PASSAGES[:1])


@pytest.fixture(scope="module")
def stand_in_scores(tmp_path_factory):
    """
    A score file made without the model: the score is the cosine similarity
    of the saved embeddings. It exercises the code, not the model.
    """
    file_path = tmp_path_factory.mktemp("reranker") / "stand_in.npz"
    table = []
    for question in QUESTIONS:
        q = SAVED[question["id"]]
        row = []
        for passage in PASSAGES:
            p = SAVED[passage["id"]]
            row.append(float(np.dot(q, p) / (np.linalg.norm(q) * np.linalg.norm(p))))
        table.append(row)
    save_scores(file_path, [q["id"] for q in QUESTIONS], [p["id"] for p in PASSAGES], table, 0.0)
    return file_path


def test_reranked_results_come_from_the_pool_and_obey_the_filters(stand_in_scores):
    first_stage, reranked, questions = build_searches(stand_in_scores)
    for use_mode in ("non-commercial", "commercial"):
        for question in questions:
            pool, withheld = first_stage.rank(question["question"], use_mode, how_many=5)
            results, withheld_again = reranked.rank(question["question"], use_mode, pool_size=5, how_many=5)
            assert sorted(p["id"] for p in results) == sorted(p["id"] for p in pool)
            assert withheld == withheld_again


def test_count_at_pool_depth_does_not_change(stand_in_scores):
    first_stage, reranked, questions = build_searches(stand_in_scores)
    for pool_size in (3, 5, 10):
        before = hits_at(lambda q: first_stage.rank(q, "non-commercial", how_many=pool_size)[0],
                         questions, pool_size)
        after = hits_at(lambda q: reranked.rank(q, "non-commercial", pool_size, how_many=pool_size)[0],
                        questions, pool_size)
        assert before == after


def test_compare_first_places_lists_changes():
    questions = [{"id": "x", "question": "x", "gold_passages": ["g"]},
                 {"id": "y", "question": "y", "gold_passages": ["g"]}]
    before = {"x": [{"id": "g"}], "y": [{"id": "n"}]}
    after = {"x": [{"id": "n"}], "y": [{"id": "g"}]}
    lost, gained = compare_first_places(questions, lambda q: before[q], lambda q: after[q])
    assert (lost, gained) == (["x"], ["y"])


needs_saved_scores = pytest.mark.skipif(
    not SCORE_FILE.exists(), reason="saved reranker scores not made yet (run with --score)")


@needs_saved_scores
def test_saved_scores_cover_every_definition_question_and_passage():
    scores = load_scores()
    assert set(scores) == {question["id"] for question in QUESTIONS}
    for row in scores.values():
        assert set(row) == {passage["id"] for passage in PASSAGES}


@pytest.fixture(scope="module")
def saved_searches():
    return build_searches(SCORE_FILE)


@needs_saved_scores
def test_reranker_does_not_beat_the_first_stage(saved_searches):
    first_stage, reranked, questions = saved_searches
    use_mode = "non-commercial"
    before = [hits_at(lambda q: first_stage.rank(q, use_mode, how_many=10)[0], questions, depth)
              for depth in (1, 3, 10)]
    assert before == [25, 30, 32]
    expected = {5: [24, 30, 31], 10: [24, 29, 32], 20: [24, 30, 32]}
    for pool_size, counts in expected.items():
        after = [hits_at(lambda q: reranked.rank(q, use_mode, pool_size, how_many=10)[0],
                         questions, depth) for depth in (1, 3, 10)]
        assert after == counts


@needs_saved_scores
def test_first_places_gained_and_lost(saved_searches):
    first_stage, reranked, questions = saved_searches
    lost, gained = compare_first_places(
        questions,
        lambda q: first_stage.rank(q, "non-commercial", how_many=10)[0],
        lambda q: reranked.rank(q, "non-commercial", pool_size=10)[0])
    assert (lost, gained) == (["q2-15", "q2-25"], ["q2-30"])


@needs_saved_scores
def test_pool_of_ten_holds_a_gold_passage_for_every_question(saved_searches):
    first_stage, reranked, questions = saved_searches
    assert hits_at(lambda q: first_stage.rank(q, "non-commercial", how_many=10)[0], questions, 10) == 32


@needs_saved_scores
def test_saved_timing_covers_every_pair():
    seconds, pairs = scoring_time(SCORE_FILE)
    assert pairs == 32 * 56
    assert seconds > 0
