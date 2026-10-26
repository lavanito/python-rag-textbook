"""
Chapter 10 — Is the retriever any good?

What this file does
    Measures how well each search in Chapters 3 to 9 finds the gold passages
    of the 32 definition questions. Five measures: precision, recall and F1
    at three places, reciprocal rank, and average precision. Query expansion
    is measured on its own, on BM25, as well as inside hybrid search. The
    chapter then shows how much the figures depend on the gold lists, using
    the revision of 26 October 2026, and counts the questions on which one
    search beats another.

Inputs
    The corpus (data/corpus/passages.jsonl), the question bank
    (data/question_bank/questions.jsonl), the saved embeddings
    (data/embeddings/all-MiniLM-L6-v2.npz), the knowledge graph and the saved
    reranker scores (data/reranker/ms-marco-MiniLM-L6-v2.npz).

Outputs
    A table of the five measures for each search, the same table on the
    gold lists before 26 October 2026, and question-by-question comparisons.

Used by
    Chapter 11 (prompts and settings) and Chapter 14 (checking answers).

Uses
    Chapter 2 (load_corpus); Chapter 3 (load_questions); Chapter 4
    (load_embeddings); Chapter 5 (build_indexes, expand_question,
    saved_question_embedder); Chapter 8 (FilteredSearch); Chapter 9
    (RerankedSearch, saved_scorer, load_scores). Python's math module.

Run the worked example
    python -m ragbook.ch10_evaluation
        Reads the saved files, so it needs no model and no internet.
"""

import math

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import load_questions
from ragbook.ch04_semantic_search import load_embeddings
from ragbook.ch05_hybrid_search import build_indexes, expand_question, saved_question_embedder
from ragbook.ch08_filters import FilteredSearch
from ragbook.ch09_reranking import RerankedSearch, load_scores, saved_scorer

TOP = 3      # the places precision, recall and F1 look at: the passages an answer uses
DEPTH = 10   # the places reciprocal rank and average precision look at


# ---------------------------------------------------------------------------
# 10.3  Precision, recall and F1
# ---------------------------------------------------------------------------

def precision_at(found_ids, gold_ids, places=TOP):
    """
    The share of the first `places` passages that are gold.

    Example:
        precision_at(["a", "x", "b"], ["a", "b"], 3)
        returns 0.667 (two of three)
    """
    first = found_ids[:places]
    gold_found = 0
    for passage_id in first:
        if passage_id in gold_ids:
            gold_found = gold_found + 1
    return gold_found / places


def recall_at(found_ids, gold_ids, places=TOP):
    """
    The share of the gold passages found in the first `places` passages.

    Example:
        recall_at(["a", "x", "y"], ["a", "b"], 3)
        returns 0.5 (one of two)
    """
    first = found_ids[:places]
    gold_found = 0
    for gold_id in gold_ids:
        if gold_id in first:
            gold_found = gold_found + 1
    return gold_found / len(gold_ids)


def f1(precision, recall):
    """
    The harmonic mean of precision and recall: high only when both are high.

    Example:
        f1(1.0, 0.5)
        returns 0.667
        f1(0.0, 0.0)
        returns 0.0
    """
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# 10.4  Reciprocal rank
# ---------------------------------------------------------------------------

def reciprocal_rank(found_ids, gold_ids, depth=DEPTH):
    """
    1 divided by the place of the first gold passage; 0 if none is in the
    first `depth` places.

    Example:
        reciprocal_rank(["x", "a", "b"], ["a", "b"])
        returns 0.5 (first gold passage in second place)
    """
    for place, passage_id in enumerate(found_ids[:depth], start=1):
        if passage_id in gold_ids:
            return 1 / place
    return 0.0


# ---------------------------------------------------------------------------
# 10.5  Average precision
# ---------------------------------------------------------------------------

def average_precision(found_ids, gold_ids, depth=DEPTH):
    """
    The precision at the place of each gold passage found, added up and
    divided by the number of gold passages. A gold passage not found in the
    first `depth` places adds 0.

    Example:
        average_precision(["a", "x", "b"], ["a", "b"])
        returns (1/1 + 2/3) / 2 = 0.833
    """
    total = 0.0
    gold_found = 0
    for place, passage_id in enumerate(found_ids[:depth], start=1):
        if passage_id in gold_ids:
            gold_found = gold_found + 1
            total = total + gold_found / place
    return total / len(gold_ids)


# ---------------------------------------------------------------------------
# 10.6  Measuring every search
# ---------------------------------------------------------------------------

def measure_question(found_ids, gold_ids, places=TOP, depth=DEPTH):
    """
    The five measures for one question, as a dictionary.

    Example:
        measure_question(["a", "x", "b"], ["a", "b"])
        returns {"precision": 0.667, "recall": 1.0, "f1": 0.8, "rr": 1.0, "ap": 0.833}
    """
    precision = precision_at(found_ids, gold_ids, places)
    recall = recall_at(found_ids, gold_ids, places)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
        "rr": reciprocal_rank(found_ids, gold_ids, depth),
        "ap": average_precision(found_ids, gold_ids, depth),
    }


def measure_search(rank_function, questions, places=TOP, depth=DEPTH):
    """
    The five measures for every question, and their means over the questions.

    rank_function takes a question's text and returns at least `depth`
    passages. The means of reciprocal rank and average precision are the
    mean reciprocal rank (MRR) and mean average precision (MAP).

    Example:
        means, by_question = measure_search(lambda q: index.rank(q, how_many=10), questions)
        means["ap"]
        returns the MAP
    """
    by_question = {}
    for question in questions:
        found_ids = []
        for passage in rank_function(question["question"])[:depth]:
            found_ids.append(passage["id"])
        by_question[question["id"]] = measure_question(found_ids, question["gold_passages"],
                                                       places, depth)
    means = {}
    for name in ["precision", "recall", "f1", "rr", "ap"]:
        values = [measures[name] for measures in by_question.values()]
        means[name] = sum(values) / len(values)
    return means, by_question


def build_searches(use_mode="non-commercial"):
    """
    Every search from Chapters 3 to 9, as rank functions that return the
    first DEPTH passages. Query expansion appears twice: on BM25 alone, and
    inside hybrid search.

    Example:
        searches, questions = build_searches()
        searches["BM25"]("What is GDI?")
        returns ten passages
    """
    keyword_index, semantic_index, hybrid_index, questions = build_indexes()
    knowledge_graph = hybrid_index.knowledge_graph
    passages = load_corpus()
    saved = load_embeddings()
    embed_question = saved_question_embedder(questions, saved)
    filtered = FilteredSearch(passages, saved, embed_question)
    reranked = RerankedSearch(passages, saved, embed_question,
                              saved_scorer(questions, load_scores()))

    def bm25_expanded(question):
        return keyword_index.rank(expand_question(knowledge_graph, question), "bm25", how_many=DEPTH)

    searches = {
        "BM25": lambda q: keyword_index.rank(q, "bm25", how_many=DEPTH),
        "BM25 + query expansion": bm25_expanded,
        "Semantic search": lambda q: semantic_index.rank(q, how_many=DEPTH),
        "Hybrid search": lambda q: hybrid_index.rank(q, how_many=DEPTH),
        "Hybrid search + query expansion": lambda q: hybrid_index.rank(q, how_many=DEPTH, expand=True),
        "Filtered, " + use_mode: lambda q: filtered.rank(q, use_mode, how_many=DEPTH)[0],
        "Reranked, pool of 10": lambda q: reranked.rank(q, use_mode, pool_size=10, how_many=DEPTH)[0],
    }
    return searches, questions


# ---------------------------------------------------------------------------
# 10.7  How the figures depend on the gold lists
# ---------------------------------------------------------------------------

# The passages added to four gold lists on 26 October 2026. The rule used:
# a passage is gold if the expected answer can rest on it.
ADDED_26_OCTOBER = {
    "q2-15": ["esa10-10.22"],
    "q2-17": ["qna17-10.48"],
    "q2-24": ["bea-ch2-ndp-gni"],
    "q2-31": ["sna25-16.95"],
}


def earlier_gold_lists(questions, added=ADDED_26_OCTOBER):
    """
    Copies of the questions with the gold lists as they were before passages
    were added. The questions passed in are not changed.

    Example:
        earlier = earlier_gold_lists(load_questions())
        returns 32 questions; q2-31 has one gold passage instead of two
    """
    earlier = []
    for question in questions:
        copy = dict(question)
        removed = added.get(question["id"], [])
        copy["gold_passages"] = [p for p in question["gold_passages"] if p not in removed]
        earlier.append(copy)
    return earlier


# ---------------------------------------------------------------------------
# 10.8  Is one search better than another?
# ---------------------------------------------------------------------------

def compare_by_question(by_question_a, by_question_b, measure="ap"):
    """
    The questions on which search A scores higher than search B on one
    measure, the questions on which it scores lower, and the number of ties.

    Example:
        better, worse, ties = compare_by_question(a, b, "rr")
        returns two lists of question ids and a count
    """
    better = []
    worse = []
    ties = 0
    for question_id in by_question_a:
        a = by_question_a[question_id][measure]
        b = by_question_b[question_id][measure]
        if math.isclose(a, b):
            ties = ties + 1
        elif a > b:
            better.append(question_id)
        else:
            worse.append(question_id)
    return better, worse, ties


def sign_test(better, worse):
    """
    The chance of a split at least this uneven if each search were equally
    likely to win each question that is not a tie (two-sided sign test).

    Example:
        sign_test(8, 1)
        returns 0.039: a split of 8 to 1 happens about 4 times in 100 by chance
        sign_test(3, 2)
        returns 1.0
    """
    games = better + worse
    if games == 0:
        return 1.0
    fewer = min(better, worse)
    one_side = 0
    for wins in range(fewer + 1):
        one_side = one_side + math.comb(games, wins)
    return min(1.0, 2 * one_side / 2 ** games)


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

def print_table(searches, questions):
    print(f"     {'search':34} {'P@3':>5} {'R@3':>5} {'F1@3':>5} {'MRR':>5} {'MAP':>5}")
    results = {}
    for label, rank_function in searches.items():
        means, by_question = measure_search(rank_function, questions)
        results[label] = by_question
        print(f"     {label:34} {means['precision']:5.2f} {means['recall']:5.2f} "
              f"{means['f1']:5.2f} {means['rr']:5.2f} {means['ap']:5.2f}")
    return results


def main():
    print("10.3-10.5  One question: found a, x, b; gold a, b")
    print("     ", measure_question(["a", "x", "b"], ["a", "b"]))

    searches, questions = build_searches()
    print(f"\n10.6  Means over {len(questions)} definition questions (revised gold lists)")
    revised = print_table(searches, questions)

    print("\n10.7  The same, on the gold lists before 26 October 2026")
    earlier = print_table(searches, earlier_gold_lists(questions))

    print("\n10.8  Question by question, average precision")
    pairs = [("BM25 + query expansion", "BM25"),
             ("Hybrid search", "BM25"),
             ("Hybrid search + query expansion", "Hybrid search"),
             ("Reranked, pool of 10", "Filtered, non-commercial")]
    for a, b in pairs:
        better, worse, ties = compare_by_question(revised[a], revised[b])
        print(f"     {a} vs {b}: better {len(better)}, worse {len(worse)}, ties {ties},"
              f" sign test {sign_test(len(better), len(worse)):.2f}")


if __name__ == "__main__":
    main()
