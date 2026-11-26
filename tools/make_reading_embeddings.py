"""Embed the measures' names and the questions, for reading the measure by meaning (A5).

Run by the GitHub workflow "reading embeddings" (Hugging Face cannot be reached
from Claude's workspace), or from the repository folder with
sentence-transformers installed:
    python tools/make_reading_embeddings.py
It writes, with Chapter 4's model (all-MiniLM-L6-v2) and embed_texts:
- app/data/measure_embeddings.json: one embedding per name of each measure in
  app/data/reading.json (the page compares a typed question with these);
- data/embeddings/reading_questions.json: one embedding per question in the
  bank and the four test sets, so the reading can be scored without the model.
Vectors are rounded to 6 decimal places.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch01_python_basics import load_passages        # noqa: E402
from ragbook.ch04_semantic_search import MODEL_NAME, embed_texts, load_model  # noqa: E402

READING = REPO / "app" / "data" / "reading.json"
MEASURE_OUT = REPO / "app" / "data" / "measure_embeddings.json"
QUESTION_OUT = REPO / "data" / "embeddings" / "reading_questions.json"
BANK = REPO / "data" / "question_bank"
QUESTION_FILES = ["questions.jsonl", "routing_test_5_november.jsonl", "routing_test_6_november.jsonl",
                  "parameters_test.jsonl", "ch14_fair_test.jsonl"]


def measure_texts():
    reading = json.loads(READING.read_text(encoding="utf-8"))
    return [{"measure": measure, "text": name}
            for measure, m in reading["measures"].items() for name in m["names"]]


def questions():
    found = {}
    for name in QUESTION_FILES:
        for q in load_passages(BANK / name):
            found[q["id"]] = q["question"]
    return found


def rounded(vector):
    return [round(float(x), 6) for x in vector]


def main():
    model = load_model()
    texts = measure_texts()
    vectors = embed_texts(model, [t["text"] for t in texts])
    MEASURE_OUT.write_text(json.dumps({
        "note": "Written by tools/make_reading_embeddings.py; do not edit by hand.",
        "model": MODEL_NAME, "texts": [dict(t, vector=rounded(v)) for t, v in zip(texts, vectors)]},
        ensure_ascii=False) + "\n", encoding="utf-8")
    found = questions()
    vectors = embed_texts(model, list(found.values()))
    QUESTION_OUT.write_text(json.dumps({
        "note": "Written by tools/make_reading_embeddings.py; do not edit by hand.",
        "model": MODEL_NAME, "questions": {i: rounded(v) for i, v in zip(found, vectors)}}) + "\n",
        encoding="utf-8")
    print(f"Embedded {len(texts)} measure names and {len(found)} questions")


if __name__ == "__main__":
    main()
