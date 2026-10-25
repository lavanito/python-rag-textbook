"""
Chapter 8 — Filters, metadata and access rules

What this file does
    Decides, before any search, which passages a question may use. A licence
    filter keeps only the licence classes the use mode allows. An edition
    filter keeps the edition of the SNA a question asks for, or the latest
    edition when it names none. Every withheld passage is recorded with the
    reason. The same filters are then applied inside Chroma, on metadata.

Inputs
    The corpus (each passage's licence_class, source_code and topic), the
    question bank, the saved embeddings and the knowledge graph.

Outputs
    The passages a question may use; a list of withheld passages and why;
    a log file of withheld passages (one line each); hit counts in each use
    mode; Chroma results that obey the same filters.

Used by
    Chapter 11 (prompts and settings) and Chapter 14 (checking answers).

Uses
    Chapter 2 (load_corpus); Chapter 3 (KeywordIndex, load_questions);
    Chapter 4 (SemanticIndex, load_embeddings); Chapter 5 (HybridIndex,
    KnowledgeGraph, hits_at, saved_question_embedder); Chapter 7
    (open_store, store_passages). Python's json and datetime modules.

Run the worked example
    python -m ragbook.ch08_filters
    It reads the saved embeddings, so it needs no model and no internet.
"""

import datetime
import json
from pathlib import Path

import numpy as np

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import KeywordIndex, load_questions
from ragbook.ch04_semantic_search import SemanticIndex, load_embeddings
from ragbook.ch05_hybrid_search import HybridIndex, KnowledgeGraph, hits_at, saved_question_embedder
from ragbook.ch07_vector_store import open_store, store_passages

LOG_FILE = Path(__file__).parent.parent / "logs" / "withheld.jsonl"


# ---------------------------------------------------------------------------
# 8.2  The licence filter
# ---------------------------------------------------------------------------

# Which licence classes each use mode may send to the model.
USE_MODES = {
    "non-commercial": ["open", "non-commercial", "quotation only"],
    "commercial": ["open"],
}


def licence_filter(passages, use_mode):
    """
    Keep the passages whose licence class the use mode allows.

    Returns two lists: the passages kept, and one record for each passage
    withheld, giving its id and the reason.

    Example:
        kept, withheld = licence_filter(load_corpus(), "commercial")
        len(kept), len(withheld)
        returns (41, 15)
    """
    allowed = USE_MODES[use_mode]
    kept = []
    withheld = []
    for passage in passages:
        if passage["licence_class"] in allowed:
            kept.append(passage)
        else:
            reason = f"licence: '{passage['licence_class']}' is not allowed in {use_mode} use"
            withheld.append({"id": passage["id"], "filter": "licence", "reason": reason})
    return kept, withheld


# ---------------------------------------------------------------------------
# 8.3  The edition filter
# ---------------------------------------------------------------------------

# Editions of one standard, oldest first, and the names a question may use.
EDITIONS = ["SNA08", "SNA25"]
EDITION_NAMES = {
    "SNA08": ["2008 SNA", "SNA 2008"],
    "SNA25": ["2025 SNA", "SNA 2025"],
}


def editions_named(question):
    """
    The editions a question names, as source codes, oldest first.

    Example:
        editions_named("What did the 2008 SNA call depreciation?")
        returns ["SNA08"]
    """
    named = []
    for code in EDITIONS:
        for name in EDITION_NAMES[code]:
            if name.lower() in question.lower():
                named.append(code)
                break
    return named


def edition_filter(passages, question):
    """
    Keep the edition of the SNA that the question asks for.

    If the question names one or more editions, passages from the other
    editions are withheld. If it names none, a passage from an older edition
    is withheld only when a newer edition has a passage on the same topic;
    an older passage with no newer counterpart stays. Passages from other
    sources are never touched.

    Example:
        kept, withheld = edition_filter(load_corpus(), "What is net national income?")
        [record["id"] for record in withheld]
        returns ["sna08-2.144", "sna08-12.26"]
    """
    named = editions_named(question)
    newest_topics = {}
    for passage in passages:
        if passage["source_code"] in EDITIONS:
            position = EDITIONS.index(passage["source_code"])
            if position > newest_topics.get(passage["topic"], -1):
                newest_topics[passage["topic"]] = position
    kept = []
    withheld = []
    for passage in passages:
        code = passage["source_code"]
        reason = ""
        if code in EDITIONS and named and code not in named:
            reason = f"edition: the question asks for the {' and '.join(EDITION_NAMES[c][0] for c in named)}"
        elif code in EDITIONS and not named and EDITIONS.index(code) < newest_topics[passage["topic"]]:
            newer = EDITION_NAMES[EDITIONS[newest_topics[passage["topic"]]]][0]
            reason = f"edition: the {newer} has a passage on '{passage['topic']}'"
        if reason:
            withheld.append({"id": passage["id"], "filter": "edition", "reason": reason})
        else:
            kept.append(passage)
    return kept, withheld


# ---------------------------------------------------------------------------
# 8.4  Both filters, and the log
# ---------------------------------------------------------------------------

def filter_passages(passages, question, use_mode):
    """
    Apply the licence filter, then the edition filter.

    Returns the passages kept and every withheld record. A passage withheld
    by the licence filter is not checked again for its edition.

    Example:
        kept, withheld = filter_passages(load_corpus(), "What is net national income?", "commercial")
        len(kept)
        returns 41
    """
    kept, withheld_by_licence = licence_filter(passages, use_mode)
    kept, withheld_by_edition = edition_filter(kept, question)
    return kept, withheld_by_licence + withheld_by_edition


def record_withheld(question, use_mode, withheld, log_file=LOG_FILE):
    """
    Add one line to the log for each withheld passage.

    Each line is a JSON record: date and time, use mode, question, passage
    id, filter and reason. The log is appended to, never overwritten.

    Example:
        record_withheld("What is net national income?", "commercial", withheld)
    """
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    when = datetime.datetime.now().isoformat(timespec="seconds")
    with open(log_file, "a", encoding="utf-8") as file:
        for record in withheld:
            line = {"time": when, "use_mode": use_mode, "question": question}
            line.update(record)
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 8.5  Searching only what the filters allow
# ---------------------------------------------------------------------------

class FilteredSearch:
    """
    Chapter 5's hybrid search, run on the passages that pass the filters.

    The indexes are rebuilt for each question from the kept passages, so a
    withheld passage cannot appear in a ranking and does not count in the
    BM25 word statistics. At 56 passages this takes a few milliseconds.

    Example:
        search = FilteredSearch(load_corpus(), load_embeddings(), embed_question)
        results, withheld = search.rank("What is net national income?", "commercial")
    """

    def __init__(self, passages, saved, embed_question):
        self.passages = passages
        self.saved = saved
        self.embed_question = embed_question

    def rank(self, question, use_mode, how_many=3, expand=True):
        kept, withheld = filter_passages(self.passages, question, use_mode)
        vectors = [self.saved[passage["id"]] for passage in kept]
        keyword_index = KeywordIndex(kept)
        semantic_index = SemanticIndex(kept, vectors, self.embed_question)
        hybrid_index = HybridIndex(keyword_index, semantic_index, KnowledgeGraph(kept))
        return hybrid_index.rank(question, how_many=how_many, expand=expand), withheld


def reachable(questions, passages, use_mode):
    """
    The questions that keep at least one gold passage after filtering.

    A question whose gold passages are all withheld cannot be answered from
    the corpus in that use mode, however good the search.

    Example:
        len(reachable(load_questions(), load_corpus(), "commercial"))
        returns 26
    """
    kept_questions = []
    for question in questions:
        kept, withheld = filter_passages(passages, question["question"], use_mode)
        kept_ids = [passage["id"] for passage in kept]
        if any(gold_id in kept_ids for gold_id in question["gold_passages"]):
            kept_questions.append(question)
    return kept_questions


# ---------------------------------------------------------------------------
# 8.6  The same filters inside Chroma
# ---------------------------------------------------------------------------

def add_filter_fields(collection, passages):
    """
    Add the fields the filters read to each stored passage's metadata.

    Chapter 7 stored source, reference, edition, scope and licence. Chroma merges
    new fields into the metadata already stored, so nothing else changes.

    Example:
        add_filter_fields(collection, load_corpus())
    """
    collection.update(
        ids=[passage["id"] for passage in passages],
        metadatas=[{"licence_class": passage["licence_class"], "passage_id": passage["id"]}
                   for passage in passages],
    )


def chroma_filter(use_mode, withheld):
    """
    Turn the use mode and the edition filter's withheld ids into a Chroma
    "where" condition.

    The licence condition reads licence_class, so it works on any collection
    whose items carry that field. The edition condition lists the passages
    to leave out.

    Example:
        chroma_filter("commercial", [])
        returns {"licence_class": {"$in": ["open"]}}
    """
    licence = {"licence_class": {"$in": USE_MODES[use_mode]}}
    edition_ids = [record["id"] for record in withheld if record["filter"] == "edition"]
    if not edition_ids:
        return licence
    return {"$and": [licence, {"passage_id": {"$nin": edition_ids}}]}


def search_store_filtered(collection, question_vector, where, how_many=3):
    """
    Chapter 7's search, with Chroma checking the condition before it ranks.

    Example:
        search_store_filtered(collection, vector, chroma_filter("commercial", []))
        returns only passages whose licence_class is "open"
    """
    answer = collection.query(query_embeddings=[np.asarray(question_vector).tolist()],
                              n_results=how_many, where=where)
    results = []
    for passage_id, metadata, distance in zip(answer["ids"][0], answer["metadatas"][0], answer["distances"][0]):
        result = {"id": passage_id, "similarity": 1 - distance}
        result.update(metadata)
        results.append(result)
    return results


def compare_with_filtered_exact(collection, passages, saved, questions, use_mode, how_many=3):
    """
    For each question, compare Chroma's filtered top passages with an exact
    semantic ranking of the passages that pass the same filters.

    Returns the number of questions that agree and the ids of any that do not.
    """
    same = 0
    different = []
    for question in questions:
        kept, withheld = filter_passages(passages, question["question"], use_mode)
        vector = saved[question["id"]]
        index = SemanticIndex(kept, [saved[p["id"]] for p in kept], lambda text: vector)
        exact_ids = [p["id"] for p in index.rank(question["question"], how_many)]
        where = chroma_filter(use_mode, withheld)
        chroma_ids = [r["id"] for r in search_store_filtered(collection, vector, where, how_many)]
        if chroma_ids == exact_ids:
            same += 1
        else:
            different.append(question["id"])
    return same, different


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------

def main():
    passages = load_corpus()
    questions = load_questions()
    saved = load_embeddings()

    print("8.2  Licence filter: passages kept and withheld")
    for use_mode in USE_MODES:
        kept, withheld = licence_filter(passages, use_mode)
        print(f"     {use_mode:15} kept {len(kept):>2}, withheld {len(withheld):>2}")

    print("\n8.3  Edition filter")
    for text in ["How do you get from GNI to net national income?",
                 "How did the 2008 SNA get from GNI to net national income?",
                 "What is the trading gain and how is it measured?"]:
        kept, withheld = edition_filter(passages, text)
        print(f"     {text}")
        for record in withheld:
            print(f"       withheld {record['id']}: {record['reason']}")
        if not withheld:
            print("       nothing withheld")

    print("\n8.4  Both filters, recorded in the log")
    example = "How do you get from GNI to net national income?"
    kept, withheld = filter_passages(passages, example, "commercial")
    record_withheld(example, "commercial", withheld)
    print(f"     commercial: {len(withheld)} withheld, written to {LOG_FILE}")

    print(f"\n8.5  Hybrid search + query expansion, filtered (of {len(questions)} questions)")
    search = FilteredSearch(passages, saved, saved_question_embedder(questions, saved))
    print("     use mode        reachable   hits at 1, 3, 10")
    for use_mode in USE_MODES:
        counts = [hits_at(lambda q: search.rank(q, use_mode, how_many=10)[0], questions, depth)
                  for depth in (1, 3, 10)]
        print(f"     {use_mode:15} {len(reachable(questions, passages, use_mode)):>9}   "
              f"{counts[0]:>3} {counts[1]:>3} {counts[2]:>3}")

    print("\n8.6  Chroma with the same filters")
    import tempfile
    client = open_store(Path(tempfile.mkdtemp()))
    collection = store_passages(client, passages, saved, name="corpus_filtered")
    add_filter_fields(collection, passages)
    for use_mode in USE_MODES:
        same, different = compare_with_filtered_exact(collection, passages, saved, questions, use_mode)
        print(f"     {use_mode:15} same top three as exact search on {same} of {len(questions)}", different or "")


if __name__ == "__main__":
    main()
