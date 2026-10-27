"""
Tests for Chapter 5 — Hybrid search and the knowledge graph.

Fusion and phrase matching are tested on small hand-made examples. The
knowledge-graph tests read data/knowledge_graph/. The measured results read the saved
embeddings, so no test runs the model.
"""

import pytest

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import search_words
from ragbook.ch04_semantic_search import EMBEDDING_FILE
from ragbook.ch05_hybrid_search import (
    KnowledgeGraph,
    build_indexes,
    concept_trail,
    expand_question,
    hits_at,
    passages_by_manual,
    phrase_positions,
    reciprocal_rank_fusion,
)

A, B, C = {"id": "a"}, {"id": "b"}, {"id": "c"}


def ids(passages):
    return [passage["id"] for passage in passages]


def test_rrf_rewards_agreement():
    # a: 1/61 + 1/63; b: 1/62 + 1/61; c: 1/63 + 1/62
    assert ids(reciprocal_rank_fusion([[A, B, C], [B, C, A]])) == ["b", "a", "c"]


def test_rrf_counts_a_passage_missing_from_one_ranking():
    # Keyword search leaves out passages scoring zero; they still count from the other ranking.
    assert ids(reciprocal_rank_fusion([[A], [B, A]], how_many=2)) == ["a", "b"]


def test_rrf_keeps_first_met_order_for_equal_totals():
    assert ids(reciprocal_rank_fusion([[A, B], [B, A]], how_many=2)) == ["a", "b"]


def test_phrase_positions_cleans_the_phrase_like_the_words():
    words = search_words("How do you get from GNI to net national income?")
    assert words == ["gni", "net", "national", "income"]
    assert phrase_positions("national income", words) == [(2, 4)]
    assert phrase_positions("the", words) == []


@pytest.fixture(scope="module")
def knowledge_graph():
    return KnowledgeGraph(load_corpus())


def test_label_note_in_brackets_is_dropped(knowledge_graph):
    assert knowledge_graph.names("bea_gdi") == ["gross domestic income", "GDI", "income-side GDP"]


def test_longer_name_wins(knowledge_graph):
    assert knowledge_graph.concepts_in("What is net national income?") == ["nni"]
    assert knowledge_graph.concepts_in("How do you get from GNI to net national income?") == ["gni", "nni"]


def test_label_with_bracket_note_is_found(knowledge_graph):
    question = "What is real gross domestic income, and how does it lead to real gross national income?"
    assert "real_gdi" in knowledge_graph.concepts_in(question)


def test_no_two_unrelated_concepts_share_a_cleaned_name(knowledge_graph):
    # "GNI*" once cleaned to "gni" and made every GNI question match modified GNI too.
    same_pairs = set()
    for other_id in knowledge_graph.entities:
        for linked_id, note in knowledge_graph.linked(other_id, "same_as"):
            same_pairs.add(frozenset([other_id, linked_id]))
    owner = {}
    for concept_id, entity in knowledge_graph.entities.items():
        if entity["type"] != "Concept":
            continue
        for name in knowledge_graph.names(concept_id):
            key = tuple(search_words(name))
            if key in owner and owner[key] != concept_id:
                assert frozenset([owner[key], concept_id]) in same_pairs, (name, owner[key], concept_id)
            owner[key] = concept_id


def test_two_way_relations_are_followed_from_either_end(knowledge_graph):
    assert [other for other, note in knowledge_graph.linked("depreciation_2025", "same_as")] == \
        ["consumption_of_fixed_capital"]
    assert [other for other, note in knowledge_graph.linked("consumption_of_fixed_capital", "same_as")] == \
        ["depreciation_2025"]


def test_query_expansion_adds_full_names(knowledge_graph):
    expanded = expand_question(knowledge_graph, "What is the difference between GDP and GNI?")
    assert "gross national income" in expanded
    assert expand_question(knowledge_graph, "At what levels can countries' economies be compared?") == \
        "At what levels can countries' economies be compared?"


def test_query_expansion_follows_same_as(knowledge_graph):
    assert "depreciation" in expand_question(knowledge_graph, "What is consumption of fixed capital?")


def test_passages_grouped_by_manual_definitions_first(knowledge_graph):
    assert passages_by_manual(knowledge_graph, "nni") == {
        "SNA08": [("sna08-2.144", "defined_in")],
        "SNA25": [("sna25-3.145", "defined_in")],
        "ESA10": [("esa10-8.94", "discussed_in")],
    }


def test_trail_crosses_manuals_and_flags_differences(knowledge_graph):
    trail = concept_trail(knowledge_graph, "bea_gdi")
    assert [(concept_id, relation) for concept_id, relation, note, grouped in trail] == \
        [("bea_gdi", "asked"), ("real_gdi", "differs_from")]
    assert trail[1][3] == {"ESA10": [("esa10-10.47", "discussed_in")]}


def test_hits_at_counts_within_depth():
    questions = [{"question": "q", "gold_passages": ["b"]}]
    assert hits_at(lambda question: [A, B], questions, depth=1) == 0
    assert hits_at(lambda question: [A, B], questions, depth=2) == 1


needs_saved_embeddings = pytest.mark.skipif(
    not EMBEDDING_FILE.exists(),
    reason="run python -m ragbook.ch04_semantic_search once to save the embeddings",
)


@needs_saved_embeddings
def test_measured_hits_at_depths_1_3_10():
    keyword_index, semantic_index, hybrid_index, questions = build_indexes()
    everything = len(keyword_index.passages)
    results = {
        "bm25": lambda q: keyword_index.rank(q, "bm25", how_many=everything),
        "semantic": lambda q: semantic_index.rank(q, how_many=everything),
        "hybrid": lambda q: hybrid_index.rank(q, how_many=10),
        "expanded": lambda q: hybrid_index.rank(q, how_many=10, expand=True),
    }
    counts = {name: [hits_at(f, questions, depth) for depth in (1, 3, 10)] for name, f in results.items()}
    assert counts == {
        "bm25": [25, 29, 31],
        "semantic": [17, 32, 32],
        "hybrid": [26, 30, 32],
        "expanded": [23, 31, 32],
    }


@needs_saved_embeddings
def test_which_questions_each_hybrid_misses_in_the_top_three():
    keyword_index, semantic_index, hybrid_index, questions = build_indexes()

    def misses(expand):
        missed = []
        for question in questions:
            found = ids(hybrid_index.rank(question["question"], expand=expand))
            if not any(gold in found for gold in question["gold_passages"]):
                missed.append(question["id"])
        return missed

    assert misses(expand=False) == ["q2-04", "q2-30"]
    assert misses(expand=True) == ["q2-30"]


@needs_saved_embeddings
def test_gdp_gni_example_ranking():
    keyword_index, semantic_index, hybrid_index, questions = build_indexes()
    question = "What is the difference between GDP and GNI?"
    assert ids(hybrid_index.rank(question)) == ["cso-gnistar-6", "cso-gnistar-3", "cso-gnistar-1"]
    assert ids(hybrid_index.rank(question, expand=True)) == ["cso-gnistar-6", "bea-ch2-ndp-gni", "bea-ch2-gnp"]
