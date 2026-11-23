"""Build the replies to the 56 bank questions for the demonstrator page (A5).

Run from the repository folder:
    python tools/build_bank_replies.py
It writes app/data/bank_replies.json: for each bank question and each use
mode (non-commercial, commercial), the reply as the page shows it, built by
the book's code from the data, the saved runs and the NNI model. A test
(tests/test_bank_replies.py) rebuilds the file and fails if it differs.

Where each reply comes from:
- 14 questions routed to code (R2): the locked block and explanation of the
  decision-20 rerun (data/answers/a5_explanations.jsonl), shown as stored.
  In commercial use, where the licence filter changes the evidence, the
  explanation comes from the commercial run
  (data/answers/a5_explanations_commercial.jsonl, written on the laptop by
  tools/run_commercial_explanations.py); until that run exists the status
  is "awaiting the commercial run".
- 33 definition questions (Q2, route R4): the passages code chooses
  (evidence_for, Chapter 14), quoted in the locked block. No explanation and
  no DQR.
- q1-03 (R1): the published series title.
- 4 escalated questions: the router's reason and Chapter 12's message.
- 3 vague questions (AMB): three sharper questions, each with its locked
  block calculated here. No explanation.
- q8-01 (R6): not built in this demonstrator (Lavan, 23 November 2026), and
  not among the suggested questions.

The wording below was drafted by Claude and approved by the vertical domain
expert on 23 November 2026. Change the wording here, not in the JSON.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch01_python_basics import load_passages                 # noqa: E402
from ragbook.ch08_filters import USE_MODES, licence_filter, load_corpus  # noqa: E402
from ragbook.ch11_prompts import load_answers                        # noqa: E402
from ragbook.ch12_routing import (ESCALATION_MESSAGES, ECONOMIES_IN_DATA, beyond_the_edge_graph,  # noqa: E402
                                  beyond_the_edge_message, corpus_words, load_economies,
                                  load_last_years, load_titles, route_question_graph)
from ragbook.ch13_model_tool import ESCALATION_NOTE, PARAMETER_FILE  # noqa: E402
from ragbook.ch14_answer_checks import (DEMONSTRATOR_ANALYST, DEMONSTRATOR_WITHHELD, EXPLANATION_HEADING, RERUN_FILE,  # noqa: E402
                                        WITHHELD, evidence_for, load_definitions, load_graph,
                                        locked_block)

DATA = REPO / "data"
OUT = REPO / "app" / "data" / "bank_replies.json"
COMMERCIAL_FILE = DATA / "answers" / "a5_explanations_commercial.jsonl"
MODES = ("non-commercial", "commercial")
assert set(MODES) == set(USE_MODES)

# The suggested questions of build spec v3 ("Ask: suggested questions"), without
# q8-01: route R6 is not built (Lavan, 23 November 2026).
SUGGESTED = ["q1-01", "q2-05", "q3-01", "q4-02", "q5-01", "q6-03", "q7-01", "amb-01", "out-03"]

# ---------------------------------------------------------------------------
# Wording drafted by Claude, approved by the vertical domain expert (23 November 2026)
# ---------------------------------------------------------------------------

PASSAGES_HEADING = "Passages (quoted from the sources)"
NO_DQR = "No DQR: this reply quotes passages only."
NO_PASSAGES = "No passage in this use mode answers this question."
SERIES_HEADING = "Series title (copied from the World Bank's list of series)"
CLARIFY_LINE = "This question is too vague to answer from the data. Pick one of these sharper questions:"
NOT_BUILT = ("This question needs several steps planned in turn (route R6). "
             "That route is not built in this demonstrator.")
DEMONSTRATOR_NOT_BUILT = ("Demonstrator note: a product would plan the steps itself, "
                          "within a limit on steps, and show each one.")
AWAITING = "awaiting the commercial run"

# Three sharper questions for each vague question: living standards, growth,
# productivity (build spec v3, 9.4). Each is answered from labelled parameters,
# with its locked block only.
SHARPER = {
    "amb-01": [
        ("living standards", "How does real NNI per head in the euro area compare with the United States in 2024?",
         {"economies": ["USA", "EA21"], "years": ["2024"], "measures": ["real_nni_per_head_ppp"]}),
        ("growth", "How does real GDP growth in the euro area compare with the United States in 2024?",
         {"economies": ["USA", "EA21"], "years": ["2024"], "measures": ["real_gdp_growth"]}),
        ("productivity", "How does GDP per hour worked in the euro area compare with the United States in 2023?",
         {"economies": ["USA", "EA21"], "years": ["2023"], "measures": ["gdp_per_hour"]}),
    ],
    "amb-02": [
        ("living standards", "How did real NNI per head in China compare with the United States in 2014 and 2024?",
         {"economies": ["USA", "CHN"], "years": ["2014", "2024"], "measures": ["real_nni_per_head_ppp"]}),
        ("growth", "How did real GDP growth in China compare with the United States in 2024?",
         {"economies": ["USA", "CHN"], "years": ["2024"], "measures": ["real_gdp_growth"]}),
        ("productivity", "How did GDP per hour worked in China compare with the United States in 2013 and 2023?",
         {"economies": ["USA", "CHN"], "years": ["2013", "2023"], "measures": ["gdp_per_hour"]}),
    ],
    "amb-03": [
        ("living standards", "How did real NNI per head in the United Kingdom compare with the United States in 2007 and 2024?",
         {"economies": ["USA", "GBR"], "years": ["2007", "2024"], "measures": ["real_nni_per_head_ppp"]}),
        ("growth", "How did real GDP growth in the United Kingdom compare with the United States in 2024?",
         {"economies": ["USA", "GBR"], "years": ["2024"], "measures": ["real_gdp_growth"]}),
        ("productivity", "How did GDP per hour worked in the United Kingdom compare with the United States in 2007 and 2023?",
         {"economies": ["USA", "GBR"], "years": ["2007", "2023"], "measures": ["gdp_per_hour"]}),
    ],
}

APPROVED_WORDING = ["PASSAGES_HEADING", "NO_DQR", "NO_PASSAGES", "SERIES_HEADING", "CLARIFY_LINE",
                 "NOT_BUILT", "DEMONSTRATOR_NOT_BUILT", "SHARPER"]


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def passage_lines(passage):
    """One quoted passage: id, source and reference; edition, licence, scope; the text.
    The scope note is ours, so it is labelled as ours (build spec v3, 3.7)."""
    scope = passage["scope"]
    if passage["scope_note"]:
        scope += f" (our note: {passage['scope_note']})"
    return (f"- [{passage['id']}] {passage['source']}, {passage['reference']}\n"
            f"  Edition: {passage['edition']} · Licence: {passage['licence_class']} · Scope: {scope}\n"
            f"  \"{passage['text']}\"")


def passage_block(evidence, undefined):
    parts = [PASSAGES_HEADING + "\n" + ("\n".join(passage_lines(p) for p in evidence) or f"- {NO_PASSAGES}")]
    parts += [f"The passages found do not define {label}." for label in undefined]
    parts.append(NO_DQR)
    return "\n\n".join(parts)


def explanation_part(record):
    """The explanation as the page shows it, from a saved record."""
    if record["status"] in ("passed", "passed on retry"):
        return {"status": record["status"], "text": f"{EXPLANATION_HEADING}\n{record['attempts'][-1]['reply']}"}
    if record["status"] == "dropped":
        return {"status": "dropped", "text": f"{WITHHELD}\n{DEMONSTRATOR_WITHHELD}"}
    return {"status": record["status"], "text": None}


def page_text(*parts):
    return "\n\n".join(p for p in parts if p)


def withheld_ids(corpus, mode):
    return [w["id"] for w in licence_filter(corpus, mode)[1]]


# ---------------------------------------------------------------------------
# Replies by route
# ---------------------------------------------------------------------------

def code_reply(question, saved, commercial, context):
    """R2 questions: the stored rerun; commercial evidence by code."""
    modes = {}
    for mode in MODES:
        record = saved
        evidence, _, _ = evidence_for(question["question"], saved["locked"], question["route"],
                                      question["class"], context["corpus"], context["graph"],
                                      context["definitions"], mode)
        ids = [p["id"] for p in evidence]
        explanation = explanation_part(record)
        if mode == "commercial" and ids != saved["evidence"] and saved["status"] != "lookup":
            record = commercial.get(question["id"])
            explanation = explanation_part(record) if record else {"status": AWAITING, "text": None}
        modes[mode] = {"locked": saved["locked"]["text"], "evidence": ids,
                       "withheld": withheld_ids(context["corpus"], mode), "explanation": explanation,
                       "page": page_text(saved["locked"]["text"], explanation["text"])}
    return modes


def passage_reply(question, context):
    """Q2 questions: the passages code chooses, quoted."""
    modes = {}
    for mode in MODES:
        evidence, _, undefined = evidence_for(question["question"], {"measures": []}, question["route"],
                                              question["class"], context["corpus"], context["graph"],
                                              context["definitions"], mode)
        locked = passage_block(evidence, undefined)
        modes[mode] = {"locked": locked, "evidence": [p["id"] for p in evidence],
                       "withheld": withheld_ids(context["corpus"], mode),
                       "explanation": {"status": "none", "text": None}, "page": locked}
    return modes


def fixed_reply(text, context):
    """The same reply in both use modes, with no passages."""
    return {mode: {"locked": text, "evidence": [], "withheld": withheld_ids(context["corpus"], mode),
                   "explanation": {"status": "none", "text": None}, "page": text} for mode in MODES}


def series_reply(question, context):
    code = next(c for c in context["titles"] if c in question["question"])
    return fixed_reply(f"{SERIES_HEADING}\n- {code}: {context['titles'][code]}", context)


def escalated_reply(question, rule, context):
    if rule == "beyond the data":
        edge = beyond_the_edge_graph(question["question"], context["last_years"], context["economies"])
        message = beyond_the_edge_message(edge)
    else:
        message = ESCALATION_MESSAGES[rule].format(economies=ECONOMIES_IN_DATA, count=len(context["titles"]))
    return fixed_reply(f"{message}\n\n{ESCALATION_NOTE}\n{DEMONSTRATOR_ANALYST}", context)


def clarify_reply(question, context):
    options = []
    for aspect, text, labels in SHARPER[question["id"]]:
        parameters = dict(labels, editions=["latest"], change=False)
        locked = locked_block(text, parameters, context["last_years"], context["definitions"])
        options.append({"aspect": aspect, "question": text, "parameters": parameters, "locked": locked["text"]})
    listing = "\n".join(f"- {o['aspect'].capitalize()}: {o['question']}" for o in options)
    reply = fixed_reply(f"{CLARIFY_LINE}\n{listing}", context)
    for mode in MODES:
        reply[mode]["options"] = options
    return reply


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

def load_context():
    corpus = load_corpus()
    return {"corpus": corpus, "known_words": corpus_words(corpus), "titles": load_titles(),
            "last_years": load_last_years(), "economies": load_economies(),
            "definitions": load_definitions(), "graph": load_graph()}


def build():
    context = load_context()
    questions = load_passages(DATA / "question_bank" / "questions.jsonl")
    saved = {r["id"]: r for r in load_answers(RERUN_FILE)}
    commercial = {r["id"]: r for r in load_answers(COMMERCIAL_FILE)} if COMMERCIAL_FILE.exists() else {}
    replies = []
    for q in questions:
        found_class, found_route, rule = route_question_graph(
            q["question"], context["known_words"], context["titles"], context["last_years"], context["economies"])
        if "R2" in q["route"]:
            modes = code_reply(q, saved[q["id"]], commercial, context)
        elif q["route"] == "R4":
            modes = passage_reply(q, context)
        elif q["route"] == "R1":
            modes = series_reply(q, context)
        elif q["route"] == "escalate":
            modes = escalated_reply(q, rule, context)
        elif q["route"] == "clarify":
            modes = clarify_reply(q, context)
        else:
            modes = fixed_reply(f"{NOT_BUILT}\n{DEMONSTRATOR_NOT_BUILT}", context)
        replies.append({"id": q["id"], "question": q["question"], "class": q["class"], "route": q["route"],
                        "router": {"class": found_class, "route": found_route, "rule": rule},
                        "built": q["route"] != "R6", "modes": modes})
    return {"note": "Written by tools/build_bank_replies.py; do not edit by hand.",
            "rerun": {"file": f"data/answers/{RERUN_FILE.name}",
                      "commercial_file": f"data/answers/{COMMERCIAL_FILE.name}",
                      "commercial_run_saved": COMMERCIAL_FILE.exists()},
            "parameters_file": f"data/question_bank/{PARAMETER_FILE.name}",
            "wording_approved": {"date": "2026-11-23", "items": APPROVED_WORDING},
            "suggested": SUGGESTED,
            "replies": replies}


def main():
    page = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(page, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    awaiting = [r["id"] for r in page["replies"] if r["modes"]["commercial"]["explanation"]["status"] == AWAITING]
    print(f"Wrote {OUT.relative_to(REPO)}: {len(page['replies'])} replies; "
          f"awaiting the commercial run: {', '.join(awaiting) or 'none'}")


if __name__ == "__main__":
    main()
