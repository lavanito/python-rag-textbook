"""
Tests for Chapter 4 — Embeddings and semantic search.

The arithmetic is tested with small hand-made vectors, so these tests need
no model. Once the worked example has been run and its embeddings saved
(data/embeddings/all-MiniLM-L6-v2.npz), the saved file is checked too.
"""

import math

import numpy as np
import pytest

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import load_questions, top_three_hits
from ragbook.ch04_semantic_search import (
    EMBEDDING_FILE,
    MODEL_NAME,
    SemanticIndex,
    cosine_similarities,
    cosine_similarity,
    dot_product,
    load_embeddings,
    save_embeddings,
    vector_length,
)


def test_dot_product():
    assert dot_product([1, 2, 3], [4, 5, 6]) == 32


def test_vector_length():
    assert vector_length([3, 4]) == 5.0


def test_cosine_similarity_runs_from_minus_one_to_one():
    assert math.isclose(cosine_similarity([1, 0], [2, 0]), 1.0)
    assert math.isclose(cosine_similarity([1, 0], [0, 3]), 0.0, abs_tol=1e-12)
    assert math.isclose(cosine_similarity([1, 0], [-1, 0]), -1.0)


def test_cosine_similarity_ignores_length():
    assert math.isclose(cosine_similarity([1, 2], [10, 20]), 1.0)


def test_numpy_version_matches_hand_version():
    passages = [[0.2, 0.9, -0.1], [1.0, 0.0, 0.5], [-0.3, 0.4, 0.8]]
    question = [0.5, 0.5, 0.1]
    by_numpy = cosine_similarities(passages, question)
    for row, value in zip(passages, by_numpy):
        assert math.isclose(cosine_similarity(row, question), value)


def test_rank_puts_closest_direction_first():
    passages = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    vectors = [[0, 1], [1, 0.1], [1, 1]]
    index = SemanticIndex(passages, vectors, lambda question: np.array([1, 0]))
    assert [p["id"] for p in index.rank("any question", how_many=3)] == ["b", "c", "a"]


def test_rank_keeps_corpus_order_for_equal_scores():
    passages = [{"id": "a"}, {"id": "b"}]
    index = SemanticIndex(passages, [[1, 0], [2, 0]], lambda question: np.array([1, 0]))
    assert [p["id"] for p in index.rank("any question", how_many=2)] == ["a", "b"]


def test_save_and_load_embeddings_round_trip(tmp_path):
    file_path = tmp_path / "test.npz"
    save_embeddings(file_path, ["x", "y"], [[1, 2], [3, 4]])
    loaded = load_embeddings(file_path)
    assert list(loaded) == ["x", "y"]
    assert loaded["y"].tolist() == [3.0, 4.0]
    assert str(np.load(file_path)["model_name"]) == MODEL_NAME


needs_saved_embeddings = pytest.mark.skipif(
    not EMBEDDING_FILE.exists(),
    reason="run python -m ragbook.ch04_semantic_search once to save the embeddings",
)


@needs_saved_embeddings
def test_saved_embeddings_cover_corpus_and_questions():
    saved = load_embeddings()
    for passage in load_corpus():
        assert saved[passage["id"]].shape == (384,)
    for question in load_questions():
        assert question["id"] in saved
    assert str(np.load(EMBEDDING_FILE)["model_name"]) == MODEL_NAME


def saved_semantic_index():
    """A SemanticIndex that reads saved embeddings instead of running the model."""
    saved = load_embeddings()
    passages = load_corpus()
    question_ids = {question["question"]: question["id"] for question in load_questions()}
    return SemanticIndex(passages, [saved[p["id"]] for p in passages],
                         lambda question: saved[question_ids[question]])


@needs_saved_embeddings
def test_semantic_search_finds_a_gold_passage_for_32_of_32():
    index = saved_semantic_index()
    assert top_three_hits(index.rank, load_questions()) == 32


@needs_saved_embeddings
def test_semantic_search_finds_the_bm25_misses():
    # Semantic search finds the two BM25 misses (q2-04, q2-30) and misses none.
    # Before the gold lists were revised (26 Oct) it missed q2-24 and q2-31.
    index = saved_semantic_index()
    missed = []
    for question in load_questions():
        found = [p["id"] for p in index.rank(question["question"])]
        if not any(gold in found for gold in question["gold_passages"]):
            missed.append(question["id"])
    assert missed == []


@needs_saved_embeddings
def test_deflator_example_ranking():
    index = saved_semantic_index()
    ranked = [p["id"] for p in index.rank("What is the GDP deflator?")]
    assert ranked == ["esa10-8.89", "bea-ch2-gnp", "una14-ch1-deflator"]
