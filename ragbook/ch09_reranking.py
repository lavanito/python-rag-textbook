"""
Chapter 9 — Reranking

What this file does
    Searches in two stages. The first stage is Chapter 8's filtered hybrid
    search: quick, and it returns a pool of candidate passages, more than
    the answer needs. The second stage, the reranker, reads the question and
    each candidate passage together and gives each pair a relevance score;
    the pool is then sorted by that score. The reranker is a small
    cross-encoder that runs on the computer's main processor (CPU). The
    chapter measures first place, top three and top ten against Chapter 8.

Inputs
    The corpus (data/corpus/passages.jsonl), the question bank
    (data/question_bank/questions.jsonl), the saved embeddings
    (data/embeddings/all-MiniLM-L6-v2.npz) and the knowledge graph.

Outputs
    Reranked lists of passages; the reranker's score for every pair of
    definition question and passage, saved to
    data/reranker/ms-marco-MiniLM-L6-v2.npz, so later chapters and the
    tests can use the scores without running the model.

Used by
    Chapter 10 (measuring retrieval) and Chapter 11 (prompts and settings).

Uses
    Chapter 2 (load_corpus); Chapter 3 (load_questions); Chapter 4
    (load_embeddings); Chapter 5 (hits_at, saved_question_embedder);
    Chapter 8 (FilteredSearch). Python's sys and time modules; numpy; the
    sentence-transformers library and the ms-marco-MiniLM-L6-v2 model
    (section 9.3).

Run the worked example
    python -m ragbook.ch09_reranking --score
        Loads the model, scores every pair and saves the scores. The first
        run downloads the model (about 90 MB) from Hugging Face.
    python -m ragbook.ch09_reranking
        Reads the saved scores, so it needs no model and no internet.
"""

import sys
import time
from pathlib import Path

import numpy as np

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import load_questions
from ragbook.ch04_semantic_search import load_embeddings
from ragbook.ch05_hybrid_search import hits_at, saved_question_embedder
from ragbook.ch08_filters import FilteredSearch

RERANKER_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"
SCORE_FILE = Path(__file__).parent.parent / "data" / "reranker" / "ms-marco-MiniLM-L6-v2.npz"


# ---------------------------------------------------------------------------
# 9.3  The cross-encoder
# ---------------------------------------------------------------------------

def load_reranker(model_name=RERANKER_NAME):
    """
    Load the cross-encoder on the computer's main processor (CPU).

    The first call downloads the model from Hugging Face and keeps a copy;
    later calls use the copy and need no internet connection.

    Example:
        reranker = load_reranker()
    """
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device="cpu")


def model_scorer(reranker):
    """
    A function that scores a list of passages against one question with the
    model.

    Each score is the model's raw output for the pair: any number, positive
    or negative; the larger, the more relevant the model judges the passage.
    Only the order of the scores matters.

    Example:
        score_passages = model_scorer(load_reranker())
        score_passages("What is GDP?", passages[:2])
        returns two numbers, one per passage
    """
    import torch

    def score_passages(question, passages):
        pairs = []
        for passage in passages:
            pairs.append((question, passage["text"]))
        scores = reranker.predict(pairs, activation_fn=torch.nn.Identity(),
                                  show_progress_bar=False)
        return [float(score) for score in scores]

    return score_passages


# ---------------------------------------------------------------------------
# 9.4  Saving the scores, so the model runs once
# ---------------------------------------------------------------------------

def score_everything(score_passages, questions, passages):
    """
    Score every pair of question and passage, and time the work.

    Returns a table of scores (one row per question, one column per passage)
    and the seconds taken.

    Example:
        scores, seconds = score_everything(score_passages, questions, passages)
        scores.shape
        returns (32, 57)
    """
    rows = []
    start = time.perf_counter()
    for question in questions:
        rows.append(score_passages(question["question"], passages))
    seconds = time.perf_counter() - start
    return np.array(rows, dtype=np.float32), seconds


def save_scores(file_path, question_ids, passage_ids, scores, seconds, model_name=RERANKER_NAME):
    """
    Save the table of scores, the ids of its rows and columns, the model name
    and the seconds the scoring took, in one numpy file.

    Example:
        save_scores(SCORE_FILE, ["q2-01"], ["sna08-2.144"], [[3.2]], 0.05)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(file_path, question_ids=np.array(question_ids), passage_ids=np.array(passage_ids),
             scores=np.asarray(scores, dtype=np.float32), seconds=np.array(seconds),
             model_name=np.array(model_name))


def load_scores(file_path=SCORE_FILE):
    """
    Read saved scores back as a dictionary: question id -> passage id -> score.

    Example:
        load_scores()["q2-01"]["sna08-2.144"]
        returns one number
    """
    saved = np.load(file_path)
    scores = {}
    for question_id, row in zip(saved["question_ids"], saved["scores"]):
        scores[str(question_id)] = {}
        for passage_id, score in zip(saved["passage_ids"], row):
            scores[str(question_id)][str(passage_id)] = float(score)
    return scores


def scoring_time(file_path=SCORE_FILE):
    """
    The seconds the saved scoring took, and the number of pairs scored.

    Example:
        seconds, pairs = scoring_time(SCORE_FILE)
    """
    saved = np.load(file_path)
    return float(saved["seconds"]), int(saved["scores"].size)


def saved_scorer(questions, scores):
    """
    A function that returns a bank question's saved scores, so the chapter
    runs without the model. Questions outside the bank are refused.

    Example:
        score_passages = saved_scorer(load_questions(), load_scores())
        score_passages("What is consumption of fixed capital?", passages[:2])
        returns the two saved scores
    """
    ids_by_text = {}
    for question in questions:
        ids_by_text[question["question"]] = question["id"]

    def score_passages(question, passages):
        if question not in ids_by_text:
            raise KeyError(f"No saved scores for: {question} (load the model as in 9.3)")
        row = scores[ids_by_text[question]]
        found = []
        for passage in passages:
            found.append(row[passage["id"]])
        return found

    return score_passages


# ---------------------------------------------------------------------------
# 9.5  Reranking the pool
# ---------------------------------------------------------------------------

def rerank(question, pool, score_passages, how_many=3):
    """
    Sort a pool of passages by the reranker's score, highest first, and keep
    the first `how_many`.

    Passages with equal scores keep their order in the pool.

    Example:
        scores = {"a": 0.1, "b": 2.0, "c": 0.5}
        rerank("q", [{"id": "a"}, {"id": "b"}, {"id": "c"}],
               lambda q, ps: [scores[p["id"]] for p in ps])
        returns the passages in the order b, c, a
    """
    scores = score_passages(question, pool)
    pairs = []
    for place, (passage, score) in enumerate(zip(pool, scores)):
        pairs.append((-score, place, passage))
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    reranked = []
    for negative_score, place, passage in pairs[:how_many]:
        reranked.append(passage)
    return reranked


class RerankedSearch:
    """
    Chapter 8's filtered hybrid search, then the reranker on its pool.

    pool_size is how many passages the first stage passes to the reranker.
    The reranker can only reorder the pool: a gold passage outside it cannot
    be found.

    Example:
        search = RerankedSearch(load_corpus(), load_embeddings(), embed_question, score_passages)
        results, withheld = search.rank("What is consumption of fixed capital?", "non-commercial")
    """

    def __init__(self, passages, saved, embed_question, score_passages):
        self.first_stage = FilteredSearch(passages, saved, embed_question)
        self.score_passages = score_passages

    def rank(self, question, use_mode, pool_size=10, how_many=3):
        pool, withheld = self.first_stage.rank(question, use_mode, how_many=pool_size)
        return rerank(question, pool, self.score_passages, how_many=how_many), withheld


# ---------------------------------------------------------------------------
# 9.6  Measuring
# ---------------------------------------------------------------------------

def compare_first_places(questions, first_stage_rank, reranked_rank):
    """
    The questions whose first passage is gold before reranking but not after
    (lost), and the reverse (gained).

    Example:
        lost, gained = compare_first_places(questions, before, after)
        returns two lists of question ids
    """
    lost = []
    gained = []
    for question in questions:
        gold = set(question["gold_passages"])
        before = first_stage_rank(question["question"])[0]["id"] in gold
        after = reranked_rank(question["question"])[0]["id"] in gold
        if before and not after:
            lost.append(question["id"])
        if after and not before:
            gained.append(question["id"])
    return lost, gained


def build_searches(score_file=SCORE_FILE):
    """
    Build the first-stage search and the reranked search from the saved files.

    Example:
        first_stage, reranked, questions = build_searches()
    """
    passages = load_corpus()
    questions = load_questions()
    saved = load_embeddings()
    embed_question = saved_question_embedder(questions, saved)
    score_passages = saved_scorer(questions, load_scores(score_file))
    first_stage = FilteredSearch(passages, saved, embed_question)
    reranked = RerankedSearch(passages, saved, embed_question, score_passages)
    return first_stage, reranked, questions


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

def score_and_save():
    """Run the model on every pair of definition question and passage, and save the scores."""
    passages = load_corpus()
    questions = load_questions()
    print(f"9.3  Loading {RERANKER_NAME} (the first run downloads it)")
    score_passages = model_scorer(load_reranker())
    print(f"9.4  Scoring {len(questions)} questions x {len(passages)} passages")
    scores, seconds = score_everything(score_passages, questions, passages)
    save_scores(SCORE_FILE, [question["id"] for question in questions],
                [passage["id"] for passage in passages], scores, seconds)
    print(f"     {scores.size} pairs in {seconds:.1f} seconds; saved to "
          f"{SCORE_FILE.relative_to(SCORE_FILE.parent.parent.parent)}")


def main():
    if "--score" in sys.argv:
        score_and_save()
    if not SCORE_FILE.exists():
        print(f"No saved scores at {SCORE_FILE}. Run: python -m ragbook.ch09_reranking --score")
        return
    first_stage, reranked, questions = build_searches(SCORE_FILE)
    use_mode = "non-commercial"

    example = questions[0]["question"]
    print(f"\n9.5  {example}")
    pool, withheld = first_stage.rank(example, use_mode, how_many=10)
    scores = reranked.score_passages(example, pool)
    print("     first stage   reranker score   passage")
    for place, (passage, score) in enumerate(zip(pool, scores), start=1):
        print(f"     {place:>11}   {score:>14.2f}   {passage['id']}")

    print(f"\n9.6  Hits at 1, 3, 10 ({len(questions)} definition questions, {use_mode})")
    counts = [hits_at(lambda q: first_stage.rank(q, use_mode, how_many=10)[0], questions, depth)
              for depth in (1, 3, 10)]
    print(f"     first stage only (Chapter 8)   {counts[0]:>3} {counts[1]:>3} {counts[2]:>3}")
    for pool_size in (5, 10, 20):
        counts = [hits_at(lambda q: reranked.rank(q, use_mode, pool_size, how_many=10)[0],
                          questions, depth) for depth in (1, 3, 10)]
        ceiling = hits_at(lambda q: first_stage.rank(q, use_mode, how_many=pool_size)[0],
                          questions, pool_size)
        print(f"     reranked, pool of {pool_size:>2}           {counts[0]:>3} {counts[1]:>3} {counts[2]:>3}"
              f"   (ceiling {ceiling})")

    lost, gained = compare_first_places(
        questions,
        lambda q: first_stage.rank(q, use_mode, how_many=10)[0],
        lambda q: reranked.rank(q, use_mode, pool_size=10)[0])
    print(f"     first place, pool of 10: gained {gained}, lost {lost}")

    seconds, pairs = scoring_time(SCORE_FILE)
    print(f"\n9.7  Cost: {pairs} pairs in {seconds:.1f} s, {1000 * seconds / pairs:.0f} ms a pair;"
          f" a pool of 10 costs about {10 * seconds / pairs:.2f} s a question")


if __name__ == "__main__":
    main()
