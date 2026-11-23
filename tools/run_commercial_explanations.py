"""Run the explanations again in commercial use, where the evidence changes (A5).

Laptop only (needs Ollama and qwen3:4b-instruct). Run from the repository folder:
    python tools/run_commercial_explanations.py
In commercial use the licence filter keeps open passages only, so for some
bank questions code chooses different evidence from the decision-20 rerun
(non-commercial). For those questions, and only those, this asks for the
explanation again with the commercial evidence, with Chapter 14's checks and
one retry, and saves data/answers/a5_explanations_commercial.jsonl after
each question. The locked block is the stored one: it does not depend on
the use mode. tools/build_bank_replies.py reads the file.

Decided by Lavan, 23 November 2026 (A5: both use modes built offline).
"""

import sys
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch01_python_basics import load_passages                 # noqa: E402
from ragbook.ch08_filters import load_corpus                         # noqa: E402
from ragbook.ch11_prompts import ask_model_with_details, load_answers, save_answers  # noqa: E402
from ragbook.ch14_answer_checks import (EXPLAIN_SETTINGS, RERUN_FILE, evidence_for, explain,  # noqa: E402
                                        load_definitions, load_graph, reply_page)

OUT = REPO / "data" / "answers" / "a5_explanations_commercial.jsonl"
MODE = "commercial"


def questions_to_run():
    """The bank questions whose commercial evidence differs from the stored run,
    with the stored record and the commercial evidence."""
    corpus, graph, definitions = load_corpus(), load_graph(), load_definitions()
    bank = {q["id"]: q for q in load_passages(REPO / "data" / "question_bank" / "questions.jsonl")}
    found = []
    for saved in load_answers(RERUN_FILE):
        question = bank.get(saved["id"])
        if question is None or saved["status"] == "lookup":
            continue
        evidence, must_cite_first, undefined = evidence_for(
            question["question"], saved["locked"], question["route"], question["class"],
            corpus, graph, definitions, MODE)
        if [p["id"] for p in evidence] != saved["evidence"]:
            found.append((question, saved, evidence, must_cite_first, undefined))
    return found


def run(ask=ask_model_with_details):
    todo = questions_to_run()
    records = []
    for question, saved, evidence, must_cite_first, undefined in todo:
        result = explain(question["question"], question["class"], saved["locked"], evidence,
                         must_cite_first, ask)
        records.append({"locked": saved["locked"], "evidence": [p["id"] for p in evidence],
                        "must_cite_first": must_cite_first, "undefined": undefined,
                        "status": result["status"], "attempts": result["attempts"],
                        "page": reply_page(saved["locked"], result, undefined),
                        "id": question["id"], "use_mode": MODE, "settings": EXPLAIN_SETTINGS})
        save_answers(OUT, records)                     # saved after each question
        print(f"{question['id']} {result['status']} ({len(records)} of {len(todo)})")
    return records


def main():
    try:
        run()
    except urllib.error.HTTPError as error:
        print(f"Ollama refused the request ({error.code}): {error.read().decode()}")
    except urllib.error.URLError as error:
        print(f"Could not reach Ollama ({error.reason}). Start Ollama and run again.")


if __name__ == "__main__":
    main()
