"""Build the trace of every bank reply, the score table and the cost table for the page (A5).

Run from the repository folder:
    python tools/build_traces.py
It writes app/data/traces.json (build spec v3, component 15):
- for each of the 56 bank questions in each use mode, one line per step in
  the order the reply is built (Chapter 15.3): route, parameters, licence
  filter, edition filter, evidence, each explanation attempt with its failed
  checks, tokens and laptop seconds from the saved run, and the status. Steps
  done with code use no tokens; their seconds are not stored, because they
  differ from run to run and every file the page loads must equal a rebuild;
- the table of all scores, each named training or fair (Chapter 15.6), with
  the score for reading typed questions in parts;
- tokens and laptop seconds per saved run (Chapter 15.2), no hosted price
  (decision 28);
- the contrast run (component 12) when data/answers/a5_contrast.jsonl exists.
Scores and saved runs keep the book's name (`name_in_book`); the page shows
the plain page-only name from data/score_names.csv once the vertical domain
expert has approved it (decision 1a, 27 Nov 2026), the book's name until then.
A test rebuilds this file and fails if it differs.
"""

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch01_python_basics import load_passages                  # noqa: E402
from ragbook.ch02_minimal_pipeline import load_corpus                  # noqa: E402
from ragbook.ch08_filters import edition_filter, licence_filter        # noqa: E402
from ragbook.ch11_prompts import load_answers                          # noqa: E402
from ragbook.ch13_model_tool import PARAMETER_FILE                     # noqa: E402
from ragbook.ch15_token_cost import cost_of_runs, failed_checks, score_table  # noqa: E402

OUT = REPO / "app" / "data" / "traces.json"
ANSWERS = REPO / "data" / "answers"
CONTRAST = ANSWERS / "a5_contrast.jsonl"
READING_SCORES = ANSWERS / "a5_reading_scores_test.json"
MODES = ["non-commercial", "commercial"]
NO_MODEL = "code; no language model"
LAPTOP = "language model on the laptop, saved run"
READ_PARTS = ["economies", "years", "editions", "measures"]
SCORE_NAMES = REPO / "data" / "score_names.csv"


def page_names():
    """(table, name in the book) -> the name shown on the page: the approved page name, else the book's."""
    with open(SCORE_NAMES, encoding="utf-8", newline="") as f:
        return {(r["table"], r["name_in_book"]): (r["page_name"] if r["approved"] else r["name_in_book"])
                for r in csv.DictReader(f)}


def named(rows, table, key, names):
    """Each row with the page's name in `key` and the book's in `name_in_book`."""
    return [dict(row, name_in_book=row[key], **{key: names[(table, row[key])]}) for row in rows]


def step(name, outputs, means=NO_MODEL, tokens_in=0, tokens_out=0, seconds=None):
    return {"step": name, "outputs": outputs, "means": means, "tokens_in": tokens_in,
            "tokens_out": tokens_out, "seconds": None if seconds is None else round(seconds, 1)}


def saved_runs():
    """The saved explanation runs by use mode and question id; commercial falls back to non-commercial."""
    non_commercial = {r["id"]: r for r in load_answers(ANSWERS / "a5_explanations.jsonl")}
    commercial = dict(non_commercial)
    commercial.update({r["id"]: r for r in load_answers(ANSWERS / "a5_explanations_commercial.jsonl")})
    return {"non-commercial": non_commercial, "commercial": commercial}


def trace(reply, mode, parameters, corpus, runs):
    data = reply["modes"][mode]
    lines = [step("route", dict(reply["router"], route_used=reply["route"]))]
    if parameters:
        lines.append(step("parameters", {k: parameters[k] for k in ("economies", "years", "measures", "editions")}))
    kept, withheld = licence_filter(corpus, mode)
    lines.append(step("licence filter", {"kept": len(kept), "withheld": [w["id"] for w in withheld]}))
    kept_edition, withheld_edition = edition_filter(kept, reply["question"])
    lines.append(step("edition filter", {"kept": len(kept_edition), "withheld": [w["id"] for w in withheld_edition]}))
    if data["evidence"]:
        lines.append(step("evidence", {"ids": data["evidence"]}))
    saved = runs[mode].get(reply["id"])
    attempts = saved["attempts"] if saved else []
    for number, attempt in enumerate(attempts, start=1):
        lines.append(step(f"explanation, attempt {number}", {"failed_checks": failed_checks(attempt["checks"])},
                          LAPTOP, attempt["prompt_tokens"], attempt["reply_tokens"], attempt["seconds"]))
    lines.append(step("status", {"status": data["explanation"]["status"]}))
    return lines


def reading_score():
    totals = json.loads(READING_SCORES.read_text(encoding="utf-8"))["totals"]["all"]
    parts = ", ".join(f"{p} {totals[p]}" for p in READ_PARTS)
    return {"chapter": "A5", "score": f"Typed questions read in parts, all parts right ({parts})",
            "result": f"{totals['all_right']} of {totals['questions']}", "label": "fair"}


def contrast():
    if not CONTRAST.exists():
        return None
    records = load_answers(CONTRAST)
    return {"model": records[0]["model"], "date": records[0]["date"], "settings": records[0]["settings"],
            "replies": {r["id"]: {"answer": r["answer"], "tokens_in": r["prompt_tokens"],
                                  "tokens_out": r["reply_tokens"], "seconds": round(r["seconds"], 1),
                                  "done_reason": r["done_reason"]} for r in records}}


def build():
    replies = json.loads((REPO / "app" / "data" / "bank_replies.json").read_text(encoding="utf-8"))["replies"]
    parameters = {p["id"]: p for p in load_passages(PARAMETER_FILE)}
    corpus, runs, names = load_corpus(), saved_runs(), page_names()
    return {
        "note": "Written by tools/build_traces.py; do not edit by hand.",
        "traces": {r["id"]: {m: trace(r, m, parameters.get(r["id"]), corpus, runs) for m in MODES}
                   for r in replies},
        "scores": named(score_table() + [reading_score()], "scores", "score", names),
        "cost": named([{k: (round(v, 1) if isinstance(v, float) else v) for k, v in row.items()}
                       for row in cost_of_runs()], "cost", "step", names),
        "contrast": contrast(),
    }


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['traces'])} questions, {len(data['scores'])} scores, "
          f"contrast {'saved' if data['contrast'] else 'not yet run'}")


if __name__ == "__main__":
    main()
