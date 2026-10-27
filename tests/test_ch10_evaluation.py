"""
Tests for Chapter 10: ragbook/ch10_evaluation.py.

What this checks
    Each measure gives the value worked out by hand on small examples, stays
    between 0 and 1, and agrees with Chapter 5's hits_at where the two
    overlap. The earlier gold lists (26 October 2026 and before) and the
    gold-only lists are rebuilt without changing the bank.
    The results of 10.6 to 10.8 are held as figures.

Why it matters
    A measure with a wrong denominator still returns a number between 0 and
    1 and looks plausible. Only hand-worked cases catch it.

Chapter: 10. Runs on every change; needs no model and no internet.
"""

import pytest

from ragbook.ch03_keyword_search import load_questions
from ragbook.ch05_hybrid_search import hits_at
from ragbook.ch10_evaluation import (
    ADDED_26_OCTOBER, EMBEDDING_FILE_26_OCTOBER, SCORE_FILE_26_OCTOBER, average_precision,
    build_searches, compare_by_question, earlier_gold_lists, f1, gold_lists_of_26_october,
    gold_only, measure_question, measure_search, precision_at, recall_at, reciprocal_rank,
    sign_test,
)

QUESTIONS = load_questions()
QUESTIONS_26_OCTOBER = gold_lists_of_26_october(QUESTIONS)


def test_precision_and_recall_by_hand():
    assert precision_at(["a", "x", "b"], ["a", "b"]) == pytest.approx(2 / 3)
    assert recall_at(["a", "x", "b"], ["a", "b"]) == 1.0
    assert recall_at(["a", "x", "y"], ["a", "b", "c", "d"]) == 0.25
    assert precision_at(["x", "y", "z", "a"], ["a"]) == 0.0


def test_recall_at_three_cannot_reach_one_with_more_than_three_gold_passages():
    gold = ["a", "b", "c", "d"]
    assert recall_at(["a", "b", "c"], gold) == 0.75
    assert precision_at(["a", "b", "c"], gold) == 1.0


def test_f1_by_hand():
    assert f1(1.0, 0.5) == pytest.approx(2 / 3)
    assert f1(0.5, 0.5) == 0.5
    assert f1(0.0, 0.0) == 0.0
    assert f1(1.0, 0.0) == 0.0


def test_reciprocal_rank_by_hand():
    assert reciprocal_rank(["a", "x"], ["a"]) == 1.0
    assert reciprocal_rank(["x", "a", "b"], ["a", "b"]) == 0.5
    assert reciprocal_rank(["x", "y", "z", "a"], ["a"], depth=3) == 0.0


def test_average_precision_by_hand():
    assert average_precision(["a", "x", "b"], ["a", "b"]) == pytest.approx((1 + 2 / 3) / 2)
    assert average_precision(["x", "a"], ["a", "b"]) == pytest.approx(0.5 / 2)
    assert average_precision(["a", "b"], ["a", "b"]) == 1.0
    assert average_precision(["x", "y"], ["a"]) == 0.0


def test_order_changes_average_precision_but_not_precision():
    gold = ["a", "b"]
    early = ["a", "b", "x"]
    late = ["x", "a", "b"]
    assert precision_at(early, gold) == precision_at(late, gold)
    assert average_precision(early, gold) > average_precision(late, gold)


def test_measures_stay_between_zero_and_one():
    for found in (["a", "x", "b"], ["x", "y", "z"], ["a", "b", "c"]):
        for value in measure_question(found, ["a", "b", "c"]).values():
            assert 0.0 <= value <= 1.0


def test_sign_test_by_hand():
    assert sign_test(8, 1) == pytest.approx(20 / 512)
    assert sign_test(3, 2) == 1.0
    assert sign_test(0, 0) == 1.0
    assert sign_test(5, 0) == pytest.approx(2 / 32)


def test_compare_by_question_counts_ties():
    a = {"q1": {"ap": 1.0}, "q2": {"ap": 0.5}, "q3": {"ap": 0.2}}
    b = {"q1": {"ap": 0.5}, "q2": {"ap": 0.5}, "q3": {"ap": 0.4}}
    assert compare_by_question(a, b) == (["q1"], ["q3"], 1)


def test_earlier_gold_lists_leave_the_bank_unchanged():
    before = [list(question["gold_passages"]) for question in QUESTIONS]
    earlier = earlier_gold_lists(QUESTIONS_26_OCTOBER)
    gold_only(QUESTIONS)
    assert [question["gold_passages"] for question in QUESTIONS] == before
    by_id = {question["id"]: question for question in earlier}
    for question_id, added in ADDED_26_OCTOBER.items():
        for passage_id in added:
            assert passage_id not in by_id[question_id]["gold_passages"]
    assert by_id["q2-31"]["gold_passages"] == ["esa10-11.27"]


def test_the_27_october_revision_rebuilds_the_26_october_lists():
    by_id = {question["id"]: question for question in QUESTIONS_26_OCTOBER}
    assert by_id["q2-03"]["question"] == "Is depletion of natural resources a cost of production?"
    assert by_id["q2-03"]["gold_passages"] == ["sna08-12.26", "sna25-A4.59"]
    assert sum(len(question["gold_passages"]) for question in QUESTIONS_26_OCTOBER) == 71
    assert sum(len(question["gold_passages"]) for question in QUESTIONS) == 58
    assert sum(len(question["gold_passages"]) for question in gold_only(QUESTIONS)) == 53


@pytest.fixture(scope="module")
def searches():
    return build_searches()[0]


@pytest.fixture(scope="module")
def results(searches):
    found = {}
    for label, rank_function in searches.items():
        found[label] = measure_search(rank_function, QUESTIONS)
    return found


def test_mrr_counts_the_same_first_places_as_hits_at_one(searches, results):
    for label, rank_function in searches.items():
        by_question = results[label][1]
        first_place = sum(1 for measures in by_question.values() if measures["rr"] == 1.0)
        assert first_place == hits_at(rank_function, QUESTIONS, 1), label


def test_recall_above_zero_counts_the_same_questions_as_hits_at_three(searches, results):
    for label, rank_function in searches.items():
        by_question = results[label][1]
        found = sum(1 for measures in by_question.values() if measures["recall"] > 0)
        assert found == hits_at(rank_function, QUESTIONS, 3), label


EXPECTED = {
    # search: (P@3, R@3, F1@3, MRR, MAP) on the gold lists of 27 October 2026,
    # supporting passages counted, two decimals
    "BM25": (0.38, 0.71, 0.47, 0.85, 0.74),
    "BM25 + query expansion": (0.38, 0.72, 0.48, 0.75, 0.66),
    "Semantic search": (0.39, 0.74, 0.48, 0.74, 0.62),
    "Hybrid search": (0.39, 0.74, 0.49, 0.88, 0.74),
    "Hybrid search + query expansion": (0.43, 0.81, 0.54, 0.84, 0.72),
    "Filtered, non-commercial": (0.42, 0.78, 0.52, 0.83, 0.70),
    "Reranked, pool of 10": (0.42, 0.76, 0.52, 0.85, 0.72),
}

EXPECTED_GOLD_ONLY = {
    "BM25": (0.34, 0.71, 0.45, 0.81, 0.70),
    "BM25 + query expansion": (0.33, 0.71, 0.44, 0.71, 0.63),
    "Semantic search": (0.34, 0.71, 0.44, 0.71, 0.61),
    "Hybrid search": (0.34, 0.73, 0.45, 0.82, 0.71),
    "Hybrid search + query expansion": (0.39, 0.79, 0.50, 0.79, 0.69),
    "Filtered, non-commercial": (0.38, 0.76, 0.49, 0.78, 0.68),
    "Reranked, pool of 10": (0.36, 0.74, 0.47, 0.76, 0.65),
}

EXPECTED_26_OCTOBER = {
    "BM25": (0.43, 0.69, 0.50, 0.88, 0.73),
    "BM25 + query expansion": (0.43, 0.70, 0.51, 0.81, 0.69),
    "Semantic search": (0.45, 0.71, 0.52, 0.79, 0.66),
    "Hybrid search": (0.44, 0.70, 0.51, 0.90, 0.73),
    "Hybrid search + query expansion": (0.50, 0.78, 0.58, 0.89, 0.74),
    "Filtered, non-commercial": (0.48, 0.76, 0.56, 0.91, 0.74),
    "Reranked, pool of 10": (0.47, 0.74, 0.54, 0.91, 0.72),
}

EXPECTED_BEFORE_26_OCTOBER = {
    "BM25": (0.41, 0.70, 0.49, 0.85, 0.70),
    "BM25 + query expansion": (0.41, 0.71, 0.49, 0.79, 0.67),
    "Semantic search": (0.41, 0.67, 0.48, 0.75, 0.64),
    "Hybrid search": (0.40, 0.68, 0.47, 0.86, 0.70),
    "Hybrid search + query expansion": (0.47, 0.77, 0.56, 0.84, 0.71),
    "Filtered, non-commercial": (0.45, 0.75, 0.53, 0.86, 0.71),
    "Reranked, pool of 10": (0.43, 0.73, 0.51, 0.83, 0.67),
}


def rounded(means):
    return tuple(round(means[name], 2) for name in ["precision", "recall", "f1", "rr", "ap"])


def test_results_on_gold_lists_of_27_october(results):
    for label, expected in EXPECTED.items():
        assert rounded(results[label][0]) == expected, label


def test_results_on_gold_only(searches):
    stricter = gold_only(QUESTIONS)
    for label, expected in EXPECTED_GOLD_ONLY.items():
        assert rounded(measure_search(searches[label], stricter)[0]) == expected, label


@pytest.fixture(scope="module")
def searches_26_october():
    return build_searches(questions=QUESTIONS_26_OCTOBER, embedding_file=EMBEDDING_FILE_26_OCTOBER,
                          score_file=SCORE_FILE_26_OCTOBER)[0]


def test_results_on_gold_lists_of_26_october(searches_26_october):
    for label, expected in EXPECTED_26_OCTOBER.items():
        assert rounded(measure_search(searches_26_october[label], QUESTIONS_26_OCTOBER)[0]) == expected, label


def test_results_on_gold_lists_before_26_october(searches_26_october):
    earlier = earlier_gold_lists(QUESTIONS_26_OCTOBER)
    for label, expected in EXPECTED_BEFORE_26_OCTOBER.items():
        assert rounded(measure_search(searches_26_october[label], earlier)[0]) == expected, label


def test_commercial_use():
    searches = build_searches("commercial")[0]
    means = measure_search(searches["Filtered, commercial"], QUESTIONS)[0]
    assert rounded(means) == (0.30, 0.52, 0.37, 0.63, 0.48)


def test_query_expansion_on_bm25_question_by_question(results):
    with_expansion = results["BM25 + query expansion"][1]
    without = results["BM25"][1]
    lost_first = [q for q in without if without[q]["rr"] == 1.0 and with_expansion[q]["rr"] < 1.0]
    assert lost_first == ["q2-06", "q2-08", "q2-11", "q2-17", "q2-25"]
    assert compare_by_question(with_expansion, without) == (
        ["q2-04", "q2-05", "q2-14", "q2-18", "q2-21", "q2-23", "q2-30"],
        ["q2-06", "q2-08", "q2-09", "q2-11", "q2-12", "q2-15", "q2-17", "q2-20", "q2-24",
         "q2-25", "q2-29"],
        14,
    )


def test_no_comparison_is_clear_on_32_questions(results):
    # Clear would mean a sign-test probability below 0.05.
    pairs = [("BM25 + query expansion", "BM25", (7, 11), 0.48),
             ("Hybrid search", "BM25", (9, 6), 0.61),
             ("Hybrid search + query expansion", "Hybrid search", (8, 9), 1.0),
             ("Reranked, pool of 10", "Filtered, non-commercial", (7, 7), 1.0)]
    for a, b, expected, probability in pairs:
        better, worse, ties = compare_by_question(results[a][1], results[b][1])
        assert (len(better), len(worse)) == expected, (a, b)
        assert round(sign_test(len(better), len(worse)), 2) == probability, (a, b)
        assert sign_test(len(better), len(worse)) > 0.05
