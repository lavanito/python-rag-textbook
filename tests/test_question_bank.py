"""
Tests for the question bank: data/question_bank/questions.jsonl.

What this checks
    Every question has a class and a route from the agreed lists, every
    passage it names as an answer exists in the corpus, every question the
    manuals must answer names at least one such passage, and every passage
    in the corpus answers at least one question.

Why it matters
    The question bank is the ground truth for measuring retrieval (Chapter 10)
    and routing (Chapter 12). A question pointing at a passage that does not
    exist would make those scores meaningless. A passage no question uses is
    either a gap in the bank or a passage the corpus does not need.
"""

from pathlib import Path

from ragbook.ch01_python_basics import load_passages

DATA_FOLDER = Path(__file__).parent.parent / "data"
PASSAGES = load_passages(DATA_FOLDER / "corpus" / "passages.jsonl")
QUESTIONS = load_passages(DATA_FOLDER / "question_bank" / "questions.jsonl")

# AMB: too vague to answer as asked; the system must offer sharper questions first.
ALLOWED_CLASSES = {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "AMB", "OUT"}
ALLOWED_ROUTES = {"R2", "R4", "R4+R2", "R5>R2", "R6", "clarify", "escalate"}
# Classes answered from the manuals: each question must name its passages.
RETRIEVAL_CLASSES = {"Q2", "Q6"}


def test_ids_are_unique():
    ids = [question["id"] for question in QUESTIONS]
    assert len(ids) == len(set(ids))


def test_class_and_route_use_agreed_labels():
    for question in QUESTIONS:
        assert question["class"] in ALLOWED_CLASSES, question["id"]
        assert question["route"] in ALLOWED_ROUTES, question["id"]


def test_every_gold_passage_exists():
    corpus_ids = {passage["id"] for passage in PASSAGES}
    for question in QUESTIONS:
        for passage_id in question["gold_passages"]:
            assert passage_id in corpus_ids, f"{question['id']} names unknown passage {passage_id}"


def test_retrieval_questions_name_their_passages():
    for question in QUESTIONS:
        if question["class"] in RETRIEVAL_CLASSES:
            assert len(question["gold_passages"]) > 0, question["id"]


def test_every_passage_answers_some_question():
    used = set()
    for question in QUESTIONS:
        for passage_id in question["gold_passages"]:
            used.add(passage_id)
    unused = [passage["id"] for passage in PASSAGES if passage["id"] not in used]
    assert unused == [], f"passages no question uses: {unused}"


def test_every_class_has_a_question():
    classes = {question["class"] for question in QUESTIONS}
    assert classes == ALLOWED_CLASSES
