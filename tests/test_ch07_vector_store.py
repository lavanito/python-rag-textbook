"""Tests for Chapter 7 — Vector databases."""

import numpy as np
import pytest

from ragbook.ch07_vector_store import (
    METADATA_FIELDS,
    build_corpus_store,
    compare_with_exact,
    exact_search,
    graph_search,
    measure_graph_search,
    navigable_graph,
    nearest_neighbour_graph,
    open_store,
    random_embeddings,
    recall,
    search_store,
    time_exact_search,
)


# 7.2 Exact search

def test_random_embeddings_are_unit_length_and_repeatable():
    rows = random_embeddings(200)
    assert rows.shape == (200, 384)
    assert np.allclose(np.linalg.norm(rows, axis=1), 1, atol=1e-5)
    assert np.array_equal(rows, random_embeddings(200))
    assert not np.array_equal(rows, random_embeddings(200, seed=1))


def test_exact_search_example():
    vectors = np.array([[1, 0], [0, 1], [0.8, 0.6]])
    assert exact_search(vectors, np.array([1, 0]), 2) == [0, 2]


def test_time_exact_search_returns_one_time_per_size():
    results = time_exact_search([100, 200], queries=2)
    assert [size for size, _ in results] == [100, 200]
    assert all(milliseconds > 0 for _, milliseconds in results)


# 7.3 Near-neighbour graphs

def test_nearest_neighbour_graph_excludes_the_row_itself():
    vectors = random_embeddings(50)
    graph = nearest_neighbour_graph(vectors, neighbours=5)
    assert all(len(links) == 5 and row not in links for row, links in enumerate(graph))
    assert graph[0] == [row for row in exact_search(vectors, vectors[0], 6) if row != 0]


def test_navigable_graph_links_both_ways():
    graph = navigable_graph(random_embeddings(50), neighbours=5)
    for row, links in enumerate(graph):
        for other in links:
            assert row in graph[other]
    assert len(graph[1]) >= 1 and 0 in graph[1]


def test_graph_search_walks_along_a_chain():
    # Eight points round a quarter circle, each linked to the next.
    angles = np.linspace(0, np.pi / 2, 8)
    vectors = np.column_stack([np.cos(angles), np.sin(angles)])
    graph = [[1]] + [[row - 1, row + 1] for row in range(1, 7)] + [[6]]
    rows, comparisons = graph_search(graph, vectors, vectors[7], how_many=2, candidates=2)
    assert rows == [7, 6]
    assert comparisons == 8


def test_recall():
    assert recall([1, 2, 9], [1, 2, 3]) == pytest.approx(2 / 3)


def test_graph_built_as_rows_arrive_finds_neighbours_the_other_misses():
    rows = random_embeddings(5_100)
    vectors, queries = rows[:5_000], rows[5_000:]
    islands = measure_graph_search(nearest_neighbour_graph(vectors), vectors, queries, (10,))
    navigable = measure_graph_search(navigable_graph(vectors), vectors, queries, (10, 50))
    assert islands[0][1] < 0.02
    assert navigable[0][1] > 0.98 and navigable[0][2] < 300
    assert navigable[1][1] == 1.0 and navigable[1][2] < 350


# 7.5 and 7.6 Chroma

@pytest.fixture(scope="module")
def corpus_store(tmp_path_factory):
    client = open_store(tmp_path_factory.mktemp("chroma"))
    return client, *build_corpus_store(client)


def test_store_holds_every_passage_with_its_metadata(corpus_store):
    client, collection, semantic_index, questions = corpus_store
    assert collection.count() == 48
    stored = collection.get(ids=["sna08-2.144"])
    assert set(METADATA_FIELDS) <= set(stored["metadatas"][0])
    assert stored["metadatas"][0]["source_code"] == "SNA08"


def test_search_store_example(corpus_store):
    client, collection, semantic_index, questions = corpus_store
    question = "What is consumption of fixed capital?"
    results = search_store(collection, semantic_index.embed_question(question))
    assert [result["id"] for result in results] == ["esa10-3.139", "sna08-2.144", "sna25-A4.59"]
    assert results[0]["similarity"] == pytest.approx(0.816, abs=0.001)
    assert results[0]["reference"] == "para. 3.139 (first part)"


def test_chroma_agrees_with_exact_search(corpus_store):
    client, collection, semantic_index, questions = corpus_store
    assert compare_with_exact(collection, semantic_index, questions) == (32, [])


def test_store_is_kept_on_disk(tmp_path):
    client = open_store(tmp_path)
    build_corpus_store(client)
    reopened = open_store(tmp_path)
    assert reopened.get_collection("corpus").count() == 48
