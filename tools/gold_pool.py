"""
Build the gold-pool review list (Chapter 10, 10.7.6).

For each definition question, take the first three passages of each of the
seven searches in Chapter 10, keep those not already gold, and write them
out for a person to judge with the rule of 26 October 2026: a passage is
gold if the expected answer can rest on it.

Run:
    python -m tools.gold_pool            prints counts
    python -m tools.gold_pool out.json   also writes the pool as JSON
"""

import json
import sys

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch10_evaluation import build_searches

PLACES = 3


def gold_pool(searches, questions, places=PLACES):
    """
    For each question, the passages in the first `places` of any search
    that are not yet gold, with the searches that returned each one.

    Returns a list of (question, [(passage id, [search labels])]).
    """
    pool = []
    for question in questions:
        found = {}
        for label, rank_function in searches.items():
            for passage in rank_function(question["question"])[:places]:
                if passage["id"] in question["gold_passages"]:
                    continue
                found.setdefault(passage["id"], []).append(label)
        ordered = sorted(found.items(), key=lambda item: (-len(item[1]), item[0]))
        pool.append((question, ordered))
    return pool


def main():
    searches, questions = build_searches()
    texts = {passage["id"]: passage["text"] for passage in load_corpus()}
    pool = gold_pool(searches, questions)
    candidates = sum(len(found) for question, found in pool)
    print(f"{len(pool)} questions, {candidates} passages to judge")
    if len(sys.argv) > 1:
        rows = []
        for question, found in pool:
            for passage_id, labels in found:
                rows.append({"question_id": question["id"], "question": question["question"],
                             "expected": question["expected"], "passage_id": passage_id,
                             "text": texts[passage_id], "searches": labels})
        with open(sys.argv[1], "w", encoding="utf-8") as file:
            json.dump(rows, file, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
