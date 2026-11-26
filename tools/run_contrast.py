"""Ask each bank question with no passages and no data, for the contrast panel (A5).

Laptop only (needs Ollama and qwen3:4b-instruct). Run from the repository folder:
    python tools/run_contrast.py
Build spec v3, component 12: the left side of the contrast panel is the same
question to the same local model with no retrieval and no data, shown word
for word with the date and the settings. Each of the 56 bank questions is
sent alone, as the only message, with the explanation settings (temperature
0, at most 400 tokens in the reply, context 8,192 tokens). The reply is
saved as it comes; nothing is checked or changed. The file is saved after
each question, and a question already in the file is not asked again, so
the run can be stopped and started again.

Decided by Lavan, 26 November 2026: all 56 bank questions.
"""

import sys
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch01_python_basics import load_passages                  # noqa: E402
from ragbook.ch11_prompts import ask_model_with_details, load_answers, save_answers  # noqa: E402
from ragbook.ch14_answer_checks import EXPLAIN_SETTINGS                # noqa: E402

QUESTIONS = REPO / "data" / "question_bank" / "questions.jsonl"
OUT = REPO / "data" / "answers" / "a5_contrast.jsonl"


def contrast_messages(question):
    """The messages for the contrast run: the question alone, nothing added.

    Example:
        contrast_messages("What is GDI?")
        returns [{"role": "user", "content": "What is GDI?"}]
    """
    return [{"role": "user", "content": question}]


def run(ask=ask_model_with_details, out=OUT):
    bank = load_passages(QUESTIONS)
    records = load_answers(out) if Path(out).exists() else []
    done = {r["id"] for r in records}
    for question in bank:
        if question["id"] in done:
            continue
        result = ask(contrast_messages(question["question"]), options=EXPLAIN_SETTINGS)
        records.append({"id": question["id"], "question": question["question"],
                        "settings": EXPLAIN_SETTINGS, "passages": 0, "data": "none", **result})
        save_answers(out, records)                     # saved after each question
        print(f"{question['id']} {result['reply_tokens']} tokens, "
              f"{result['seconds']:.0f} s ({len(records)} of {len(bank)})")
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
