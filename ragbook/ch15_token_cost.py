"""
Chapter 15 — Monitoring token cost

What this file does
    Counts the tokens and seconds each answer uses, at each step and on
    each route. Every call to a language model is paid for in tokens: on a
    hosted model in money, on the laptop in time. The functions here read
    the saved model runs of Chapters 11 to 14, add up tokens in, tokens out
    and seconds by route, write one line to a file for each step of each
    question, and list every failed check, retry and dropped explanation
    for the domain expert, with what each retry cost.

Inputs
    The saved runs in data/answers/ (each model call has prompt_tokens,
    reply_tokens and seconds, recorded on the laptop), the question bank,
    the fair test of Chapter 14, the corpus, the knowledge graph and the
    NNI model. No language model is called.

Outputs
    A table of tokens and seconds per route; data/traces/ch15_traces.jsonl
    with one line per step; a review list with counts per check; one table
    of the scores measured in Chapters 10 to 14, each labelled training or
    fair.

Used by
    The demonstrator's "At full scale" panel and its lessons for a
    production version.

Uses
    Chapter 1 (load_passages); Chapter 2 (load_corpus); Chapter 3
    (QUESTION_FILE); Chapter 8 (USE_MODES, licence_filter); Chapter 11
    (ANSWER_FOLDER, ROLE_LENGTH, load_answers); Chapter 12
    (route_question_graph, load_economies, corpus_words, load_titles, load_last_years);
    Chapter 13 (PARAMETER_FILE, load_edition); Chapter 14 (fetch,
    locked_block, evidence_for, the checks and the saved runs). Decisions:
    the domain expert, 16 November 2026 (claude/ch15-decisions.md in the
    project): cost in tokens and laptop seconds only, no hosted price; the
    step lines are built from the saved runs, with no new laptop run.

Run the worked example
    python -m ragbook.ch15_token_cost
        Prints the cost tables, writes data/traces/ch15_traces.jsonl,
        prints the review list and the score table. Needs no language model.
"""
import json
import time
from pathlib import Path

from ragbook.ch01_python_basics import load_passages
from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import QUESTION_FILE
from ragbook.ch08_filters import USE_MODES, licence_filter
from ragbook.ch11_prompts import ANSWER_FOLDER, ROLE_LENGTH, load_answers
from ragbook.ch12_routing import (corpus_words, load_economies, load_last_years, load_titles,
                                  route_question_graph)
from ragbook.ch13_model_tool import PARAMETER_FILE, load_edition
from ragbook.ch14_answer_checks import (FAIR_TEST_FILE, REVIEW_FILE, evidence_for, fetch,
                                        load_definitions, load_graph, locked_block)

TRACE_FILE = Path(__file__).parent.parent / "data" / "traces" / "ch15_traces.jsonl"
LAPTOP_RUN = "laptop, saved run"
TIMED_HERE = "timed when the trace is built"


# ---------------------------------------------------------------------------
# 15.2  Tokens and seconds per route
# ---------------------------------------------------------------------------

def model_calls(records):
    """
    Every call to the language model in a saved run, as a list of dicts
    with the question id, tokens in, tokens out and seconds. A Chapter 14
    record holds one call per attempt; other chapters' records are one call
    each.

    Example:
        model_calls(load_answers(REVIEW_FILE))[0]
        returns {"id": "q6-01", "tokens_in": 1506, "tokens_out": 9, "seconds": 60.5...}
    """
    calls = []
    for record in records:
        attempts = record["attempts"] if "attempts" in record else [record]
        for attempt in attempts:
            calls.append({"id": record["id"], "tokens_in": attempt["prompt_tokens"],
                          "tokens_out": attempt["reply_tokens"], "seconds": attempt["seconds"]})
    return calls


def cost(calls, questions):
    """
    Tokens in, tokens out and seconds for a set of model calls: the totals
    and the averages per question. Questions with no call (lookups) count
    in the averages, because they are answered at no cost in tokens.

    Example:
        cost([{"id": "a", "tokens_in": 800, "tokens_out": 200, "seconds": 50.0}], 2)
        returns {"questions": 2, "calls": 1, "tokens_in": 800, "tokens_out": 200,
                 "seconds": 50.0, "in_per_question": 400.0, "out_per_question": 100.0,
                 "seconds_per_question": 25.0}
    """
    tokens_in = sum(c["tokens_in"] for c in calls)
    tokens_out = sum(c["tokens_out"] for c in calls)
    seconds = sum(c["seconds"] for c in calls)
    per = max(questions, 1)
    return {"questions": questions, "calls": len(calls), "tokens_in": tokens_in,
            "tokens_out": tokens_out, "seconds": seconds, "in_per_question": tokens_in / per,
            "out_per_question": tokens_out / per, "seconds_per_question": seconds / per}


# Routes that call no language model: the answer is copied, calculated or
# written from a fixed template.
NO_MODEL = {"R1": "copies the published series title",
            "R2 lookup": "code calculates the figure; lookups get no explanation",
            "clarify": "code offers sharper questions",
            "escalate": "code writes the reason"}


def questions_by_id():
    """The bank and the fair test of Chapter 14, by id, with route and class."""
    rows = load_passages(QUESTION_FILE) + load_passages(FAIR_TEST_FILE)
    return {q["id"]: q for q in rows}


def route_of(question):
    """
    The route a question is costed under: R2 lookups (class Q1) apart from
    R2 questions that get an explanation.

    Example:
        route_of({"route": "R2", "class": "Q1"}) returns "R2 lookup"
    """
    if question["route"] == "R2" and question["class"] == "Q1":
        return "R2 lookup"
    return question["route"]


def cost_by_route(records, questions):
    """
    Tokens and seconds for each route in one saved run: the records are
    grouped by the route of their question.
    """
    groups = {}
    for record in records:
        groups.setdefault(route_of(questions[record["id"]]), []).append(record)
    return {route: cost(model_calls(group), len(group)) for route, group in groups.items()}


# The saved runs, with the step each one measured (all on the laptop, with
# qwen3:4b-instruct).
RUNS = [
    ("ch11_answers.jsonl", "Chapter 11: answers from passages, analyst and executive"),
    ("ch12_router_replies.jsonl", "Chapter 12: routing by model (trial; the rules route at no cost)"),
    ("ch13_parameter_replies_second.jsonl", "Chapter 13: reading the question by model (rounds 1 and 2)"),
    ("ch13_replies.jsonl", "Chapter 13: whole reply written by model (replaced in Chapter 14)"),
    ("ch14_explanations_review.jsonl", "Chapter 14: explanations with checks, after the review"),
]


def cost_of_runs(runs=RUNS, folder=ANSWER_FOLDER):
    """Tokens and seconds for each saved run, per record (one record is one
    call, except in Chapter 14, where a record is a question)."""
    rows = []
    for file_name, step in runs:
        records = load_answers(folder / file_name)
        rows.append(dict(cost(model_calls(records), len(records)), step=step))
    return rows


def cost_by_role(records):
    """
    Chapter 11's answers grouped by role: the role sets the length rule
    (ROLE_LENGTH), so it changes tokens out and seconds.
    """
    return {role: cost(model_calls([r for r in records if r["role"] == role]),
                       sum(r["role"] == role for r in records))
            for role in ROLE_LENGTH}


def retry_cost(records):
    """
    What retries added in a Chapter 14 run: tokens and seconds of first
    attempts, and of second attempts. A retry sends the first conversation
    again, with the reply and the problems, so it has more tokens in.
    """
    first = [r | {"attempts": r["attempts"][:1]} for r in records if r["attempts"]]
    second = [r | {"attempts": r["attempts"][1:]} for r in records if len(r["attempts"]) > 1]
    return {"first": cost(model_calls(first), len(first)),
            "retry": cost(model_calls(second), len(second))}


# ---------------------------------------------------------------------------
# 15.4  The user's two settings
# ---------------------------------------------------------------------------

def user_settings(use_mode="non-commercial", role="analyst"):
    """
    The two settings a user chooses, in one dictionary. The use mode
    decides which passages may be sent to the model (Chapter 8's licence
    filter); the role decides how long a reply from passages may be
    (Chapter 11). An unknown value raises an error rather than falling
    back to a default.

    Example:
        user_settings("commercial", "executive")
        returns {"use_mode": "commercial", "role": "executive"}
    """
    if use_mode not in USE_MODES:
        raise ValueError(f"Unknown use mode {use_mode!r}: choose from {sorted(USE_MODES)}")
    if role not in ROLE_LENGTH:
        raise ValueError(f"Unknown role {role!r}: choose from {sorted(ROLE_LENGTH)}")
    return {"use_mode": use_mode, "role": role}


# ---------------------------------------------------------------------------
# 15.3  One line per step
# ---------------------------------------------------------------------------

def timed(function, *arguments, **keywords):
    """
    Run a function and return its result and the seconds it took.

    Example:
        timed(sum, [1, 2, 3]) returns (6, 0.000001...)
    """
    start = time.perf_counter()
    result = function(*arguments, **keywords)
    return result, time.perf_counter() - start


def step_line(question_id, step, settings, outputs, seconds, timed_on,
              tokens_in=0, tokens_out=0):
    """
    One line of the trace: the question, the step, the user's settings,
    what the step produced, its seconds and tokens, and where the seconds
    were measured.
    """
    return {"question_id": question_id, "step": step, "settings": settings, "outputs": outputs,
            "seconds": round(seconds, 4), "tokens_in": tokens_in, "tokens_out": tokens_out,
            "timed_on": timed_on}


def failed_checks(checks):
    """
    The names of the checks that found a problem.

    Example:
        failed_checks({"numbers": ["140"], "directions": [], "citations": []})
        returns ["numbers"]
    """
    return [name for name, found in checks.items() if found]


def trace_question(question, parameters, saved, settings, context):
    """
    The trace of one question: one line per step, in the order the reply
    is built. The steps with no model are run again and timed here; the
    model's attempts are copied from the saved laptop run, with their
    tokens and seconds.
    """
    qid, text = question["id"], question["question"]
    lines = []
    found, seconds = timed(route_question_graph, text, context["known_words"],
                           context["titles"], context["last_years"], context["economies"])
    lines.append(step_line(qid, "route", settings,
                           {"class": found[0], "route": found[1], "rule": found[2],
                            "route_used": question["route"]}, seconds, TIMED_HERE))
    lines.append(step_line(qid, "read question", settings,
                           {k: parameters[k] for k in ("economies", "years", "measures", "editions")},
                           0.0, "labelled parameters (Chapter 13); no reading step was run"))
    (kept, withheld), seconds = timed(licence_filter, context["corpus"], settings["use_mode"])
    lines.append(step_line(qid, "licence filter", settings,
                           {"kept": len(kept), "withheld": [w["id"] for w in withheld]},
                           seconds, TIMED_HERE))
    (groups, problems, _, escalated), seconds = timed(fetch, parameters, context["last_years"])
    lines.append(step_line(qid, "NNI model", settings,
                           {"figures": sum(len(g) for g in groups.values()), "problems": problems,
                            "escalate": escalated}, seconds, TIMED_HERE))
    locked, seconds = timed(locked_block, text, parameters, context["last_years"],
                            context["definitions"])
    lines.append(step_line(qid, "locked block", settings,
                           {"measures": locked["measures"], "premise": locked["premise"],
                            "same_as_saved_run": locked["text"] == saved["locked"]["text"]},
                           seconds, TIMED_HERE + " (includes the NNI model again)"))
    (evidence, _, _), seconds = timed(evidence_for, text, locked, question["route"],
                                      question["class"], context["corpus"], context["graph"],
                                      context["definitions"], settings["use_mode"])
    lines.append(step_line(qid, "evidence", settings, {"ids": [p["id"] for p in evidence],
                                                       "same_as_saved_run": [p["id"] for p in evidence]
                                                       == saved["evidence"]},
                           seconds, TIMED_HERE))
    for number, attempt in enumerate(saved["attempts"], start=1):
        lines.append(step_line(qid, f"explanation, attempt {number}", settings,
                               {"failed_checks": failed_checks(attempt["checks"])},
                               attempt["seconds"], LAPTOP_RUN, attempt["prompt_tokens"],
                               attempt["reply_tokens"]))
    lines.append(step_line(qid, "status", settings, {"status": saved["status"]}, 0.0, TIMED_HERE))
    return lines


def trace_context():
    """
    Everything the steps need, loaded once, and the seconds it took to load
    the NNI model's two editions of the data. Each step's seconds leave out
    that load, which happens once, before the first question.
    """
    corpus = load_corpus()
    load_edition.cache_clear()
    _, data_seconds = timed(lambda: [load_edition(e) for e in ("latest", "archive")])
    return {"corpus": corpus, "known_words": corpus_words(corpus), "titles": load_titles(),
            "last_years": load_last_years(), "definitions": load_definitions(),
            "graph": load_graph(), "economies": load_economies(), "data_seconds": data_seconds}


def trace_run(saved_records, settings, context=None):
    """
    The trace of every question in a saved Chapter 14 run, one line per
    step. Parameters come from the bank's labels and the fair test.
    """
    context = context or trace_context()
    questions = questions_by_id()
    parameters = {row["id"]: row for row in load_passages(PARAMETER_FILE)}
    parameters.update({row["id"]: row for row in load_passages(FAIR_TEST_FILE)})
    lines = []
    for saved in saved_records:
        lines += trace_question(questions[saved["id"]], parameters[saved["id"]], saved,
                                settings, context)
    return lines


def save_trace(lines, file_path=TRACE_FILE):
    """Write the trace as JSON Lines, one step per line, as it was built."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


def seconds_by_step(lines):
    """
    Total seconds and tokens for each step over all questions, in the order
    the steps first appear.
    """
    totals = {}
    for line in lines:
        step = line["step"].split(",")[0]
        total = totals.setdefault(step, {"lines": 0, "seconds": 0.0, "tokens_in": 0,
                                         "tokens_out": 0, "timed_on": line["timed_on"]})
        total["lines"] += 1
        total["seconds"] += line["seconds"]
        total["tokens_in"] += line["tokens_in"]
        total["tokens_out"] += line["tokens_out"]
    return totals


# ---------------------------------------------------------------------------
# 15.5  The list for review
# ---------------------------------------------------------------------------

def review_list(saved_records):
    """
    Every problem the domain expert should see, one row each: each failed
    check of each attempt (with the problem in words), each dropped
    explanation and each escalation. Rows for an attempt carry its tokens
    and seconds, so a retry shows what it cost.
    """
    rows = []
    for record in saved_records:
        for number, attempt in enumerate(record["attempts"], start=1):
            for check, problems in attempt["checks"].items():
                for problem in problems:
                    rows.append({"question_id": record["id"], "attempt": number, "check": check,
                                 "problem": problem,
                                 "tokens": attempt["prompt_tokens"] + attempt["reply_tokens"],
                                 "seconds": attempt["seconds"]})
        if record["status"] == "dropped":
            rows.append({"question_id": record["id"], "attempt": None, "check": "dropped",
                         "problem": "explanation dropped after the retry", "tokens": 0, "seconds": 0})
        if record["locked"]["escalate"]:
            rows.append({"question_id": record["id"], "attempt": None, "check": "escalated",
                         "problem": "passed to an analyst", "tokens": 0, "seconds": 0})
    return rows


def count_by_check(rows):
    """
    How many problems each check found, and on how many questions.

    Example:
        count_by_check([{"question_id": "a", "check": "numbers"},
                        {"question_id": "a", "check": "numbers"}])
        returns {"numbers": {"problems": 2, "questions": 1}}
    """
    counts = {}
    for row in rows:
        entry = counts.setdefault(row["check"], {"problems": 0, "questions": set()})
        entry["problems"] += 1
        entry["questions"].add(row["question_id"])
    return {check: {"problems": e["problems"], "questions": len(e["questions"])}
            for check, e in counts.items()}


# ---------------------------------------------------------------------------
# 15.6  The scores already measured
# ---------------------------------------------------------------------------

# Each score as reported in its chapter. "training" means the code or rules
# were written or chosen while reading those questions; "fair" means the
# questions were written before the code they score and opened once.
SCORES = [
    ("10", "Definition questions with a gold passage in the top three, filtered search",
     "31 of 32", "training"),
    ("8", "Chroma's filtered top three equal to the hand-written filter, both use modes",
     "32 of 32", "training"),
    ("12", "Questions routed as labelled, bank, ragged-edge rules", "56 of 56", "training"),
    ("12", "Questions routed as labelled, first test set, first-round rules", "19 of 32", "fair"),
    ("12", "Questions routed as labelled, second test set, revised rules", "6 of 16", "fair"),
    ("12", "Questions routed as labelled, Chapter 14 fair questions, fourth-round rules",
     "10 of 10", "training"),
    ("13", "Parameters read right (same figures), keyword rules, new questions", "2 of 20", "fair"),
    ("13", "Parameters read right (same figures), model round 2, new questions", "9 of 20", "fair"),
    ("13", "Replies with no invented number (model wrote the whole reply)", "13 of 14", "training"),
    ("14", "The domain expert's sentences judged supported; the check agreed on 17",
     "19 of 20", "training"),
    ("14", "Explanations with content shown, first run, new questions", "0 of 10", "fair"),
    ("14", "Explanations with content shown, after the review, the domain expert's 10",
     "2 of 10", "training"),
]


def score_table(scores=SCORES):
    """The scores as rows, each with its chapter and label."""
    return [{"chapter": c, "score": s, "result": r, "label": label} for c, s, r, label in scores]


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------

def main():
    print("15.2  Tokens and seconds per record, by saved run (laptop)")
    for row in cost_of_runs():
        print(f"      {row['step']}: {row['calls']} calls; "
              f"{row['in_per_question']:,.0f} in, {row['out_per_question']:,.0f} out, "
              f"{row['seconds_per_question']:.1f} seconds per record")

    review = load_answers(REVIEW_FILE)
    questions = questions_by_id()
    print("15.2  By route, Chapter 14 run after the review")
    for route, row in sorted(cost_by_route(review, questions).items()):
        print(f"      {route}: {row['questions']} questions; {row['in_per_question']:,.0f} in, "
              f"{row['out_per_question']:,.0f} out, {row['seconds_per_question']:.1f} seconds")
    for route, what in NO_MODEL.items():
        print(f"      {route}: no model call ({what})")

    retries = retry_cost(review)
    print(f"15.2  First attempts {retries['first']['calls']}: "
          f"{retries['first']['tokens_in'] + retries['first']['tokens_out']:,} tokens, "
          f"{retries['first']['seconds'] / 60:.1f} minutes; retries {retries['retry']['calls']}: "
          f"{retries['retry']['tokens_in'] + retries['retry']['tokens_out']:,} tokens, "
          f"{retries['retry']['seconds'] / 60:.1f} minutes")

    print("15.4  Chapter 11 answers by role")
    for role, row in cost_by_role(load_answers(ANSWER_FOLDER / "ch11_answers.jsonl")).items():
        print(f"      {role}: {row['out_per_question']:.0f} tokens out, "
              f"{row['seconds_per_question']:.1f} seconds per answer")

    context = trace_context()
    print(f"15.3  The NNI model's data loaded once in {context['data_seconds']:.2f} seconds")
    for use_mode in USE_MODES:
        lines = trace_run(review, user_settings(use_mode), context)
        evidence = [line for line in lines if line["step"] == "evidence"]
        changed = sum(not line["outputs"]["same_as_saved_run"] for line in evidence)
        print(f"15.4  {use_mode}: evidence different from the saved run for {changed} of "
              f"{len(evidence)} questions")
    lines = trace_run(review, user_settings(), context)
    save_trace(lines)
    print(f"15.3  {len(lines)} lines written to {TRACE_FILE.name}")
    for step, total in seconds_by_step(lines).items():
        print(f"      {step}: {total['lines']} lines, {total['seconds']:.3f} seconds, "
              f"{total['tokens_in'] + total['tokens_out']:,} tokens ({total['timed_on']})")
    routes = [line for line in lines if line["step"] == "route"]
    differ = [line["question_id"] for line in routes
              if line["outputs"]["route"] != line["outputs"]["route_used"]]
    locked = [line for line in lines if line["step"] == "locked block"]
    print(f"      routes by rules differ from the route used: {len(differ)} ({', '.join(differ)})")
    print(f"      locked blocks the same as the saved run: "
          f"{sum(line['outputs']['same_as_saved_run'] for line in locked)} of {len(locked)}")

    rows = review_list(review)
    print(f"15.5  Review list: {len(rows)} rows")
    for check, count in sorted(count_by_check(rows).items()):
        print(f"      {check}: {count['problems']} problems on {count['questions']} questions")

    print("15.6  Scores already measured")
    for row in score_table():
        print(f"      Chapter {row['chapter']}: {row['score']}: {row['result']} ({row['label']})")


if __name__ == "__main__":
    main()
