# Chapter 15 — Monitoring token cost

## 15.1 What this chapter builds

This chapter monitors token cost. Every call to a language model is paid for in tokens: on a hosted model in money, on the laptop in time. So the chapter counts the tokens and seconds each answer uses, at each step and on each route.

A **token** is the unit a language model reads and writes: a word or part of a word. **Tokens in** are what the model is sent (instructions, question, locked block, passages); **tokens out** are what it writes. Ollama reports both for every call, and Chapters 11 to 14 saved them with the seconds each call took.

The canvas, from the saved runs:

- The language model uses every token and almost all the time. For the 24 questions of Chapter 14, the model's 34 calls took 32.4 minutes and 59,674 tokens; the steps in Python took under a tenth of a second.
- Lookups, series titles, clarifying and escalation cost no tokens. They are answered by code.
- A question with figures and an explanation (route R2) cost about 3,100 tokens in and 108 seconds on the laptop.
- Retries were 13 of the 34 calls and 39 per cent of the tokens. They gave one more explanation with content (f-08).

What the chapter builds:

1. **Tokens and seconds per route** (15.2), from the saved runs.
2. **One line per step** (15.3): a file with one line for each step of each question.
3. **The user's two settings** (15.4): use mode and role, recorded on every line.
4. **The list for review** (15.5): every failed check, retry, dropped explanation and escalation, with what each retry cost.
5. **The scores already measured** (15.6), each labelled training or fair.
6. **Lessons for a production version** (15.7).

Cost is shown in tokens and laptop seconds only, with no hosted price (the horizontal domain expert, 16 November 2026). No new model run was made: the step lines are built from the saved runs (the horizontal domain expert, 16 November 2026).

## 15.2 Tokens and seconds per route

### 15.2.1 Principles

Each saved run records, for every model call, `prompt_tokens` (tokens in), `reply_tokens` (tokens out) and `seconds`. A Chapter 14 record has one call per attempt: one, or two with a retry.

The cost of a route is the sum over its questions, divided by the number of questions. A question that makes no call counts with zero, so a route of lookups costs nothing per question.

### 15.2.2 Code

```python
def model_calls(records):
    """
    Every call to the language model in a saved run, as a list of dicts
    with the question id, tokens in, tokens out and seconds. A Chapter 14
    record has one call per attempt; other chapters' records are one call
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
```

```python
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
```

```python
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
```

```python
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
```

### 15.2.3 Annotations

- `model_calls` treats every saved run the same way: a record either has attempts or is one call.
- `cost` divides by the number of questions, not calls, so retries raise the cost per question.
- `r | {...}` makes a copy of a record with only some of its attempts.

### 15.2.4 Results

By route, on the laptop (qwen3:4b-instruct). The rows for R2, R4+R2, R5>R2 and R4 with figures are the Chapter 14 run after the review (16 November 2026, 24 questions); the rows for answers from passages are Chapter 11's run (30 October 2026, 400-token limit).

| Route | What answers it | Questions | Tokens in per question | Tokens out per question | Seconds per question |
| --- | --- | --- | --- | --- | --- |
| R1 | Code copies the published series title | — | 0 | 0 | 0 |
| R2, lookup (class Q1) | Code calculates the figure; no explanation | 3 | 0 | 0 | 0 |
| R2 | Code; the model explains | 11 | 3,144 | 129 | 108.4 |
| R4+R2 | Code and passages; the model explains | 6 | 2,866 | 149 | 96.3 |
| R5>R2 | Code; the model explains | 1 | 278 | 9 | 3.4 |
| R4, Chapter 14 | Passages; the model explains | 3 | 1,597 | 169 | 56.8 |
| R4, analyst (Chapter 11) | The model answers from three passages | 32 | 779 | 307 | 69.3 |
| R4, executive (Chapter 11) | The same, at most two sentences | 32 | 772 | 80 | 30.2 |
| clarify, escalate | Code writes the message | — | 0 | 0 | 0 |
| R6 | Agent loop: not built in this demonstrator | — | — | — | — |

The trials of earlier chapters, per call:

| Saved run | Calls | Tokens in | Tokens out | Seconds |
| --- | --- | --- | --- | --- |
| Chapter 12: routing by model | 77 | 838 | 5 | 2.6 |
| Chapter 13: reading the question by model (rounds 1 and 2) | 68 | 1,031 | 46 | 12.2 |
| Chapter 13: whole reply written by the model | 14 | 347 | 88 | 21.7 |

- R2 sends the most tokens. The prompt contains the instructions, the locked block and up to five passages, and a locked block over a span lists every year (f-04, f-05).
- Tokens in and tokens out both add seconds. With almost the same tokens in, the executive's two-sentence limit cut tokens out from 307 to 80 and seconds from 69 to 30 (R4 answers). With 9 tokens out, f-05's 4,087 tokens in took 185 seconds.
- The routing rules of Chapter 12 cost no tokens. The model router sent 838 tokens per question to produce 5.
- Retries: 21 first attempts used 36,133 tokens and 26.2 minutes; 13 retries used 23,541 tokens and 6.2 minutes. A retry sends the whole first conversation again, with the reply and the problems, so it has more tokens in than the first attempt. It took less time: the model wrote fewer tokens out, and Ollama likely reused its work on the opening text it had just read (its prompt cache).

## 15.3 One line per step

### 15.3.1 Principles

A **trace** is a file with one line for each step of each question, in the order the reply is built. Each line has the question, the step, the user's settings, what the step produced, its seconds and tokens, and where the seconds were measured.

The steps for a question routed to code: route; read the question; licence filter; NNI model; locked block; evidence; each explanation attempt; status.

The trace is built from the saved Chapter 14 run, with no new laptop run. The steps with no model are run again and timed when the trace is built; the model's attempts are copied from the saved run with their tokens and seconds. A step run again must give what the run gave, and the trace records whether it does. The trace is saved in `data/traces/`, not in `logs/` (Chapter 8): it is built from committed runs, so it is committed with them.

### 15.3.2 Code

```python
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
```

```python
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
```

### 15.3.3 Annotations

- `timed` runs a function and returns its result and the seconds it took, measured with `time.perf_counter`.
- The read-question step uses the labelled parameters, as the Chapter 14 run did; it records zero seconds and says so. Reading typed questions is the demonstrator's job (decision 24).
- `same_as_saved_run` on the locked block and the evidence checks that the rebuilt steps match the run.
- The route step records the route the rules give and the route the run used.

### 15.3.4 Results

The trace of the 24 questions has 202 lines (`data/traces/ch15_traces.jsonl`). The lines for q4-01:

| Step | Output | Seconds | Tokens in | Tokens out |
| --- | --- | --- | --- | --- |
| route | Q4, R2, rule "vintage" | 0.0001 | 0 | 0 |
| read question | India, 2016, GNI per head at PPP, latest and archive | 0 | 0 | 0 |
| licence filter | 57 kept, none withheld | 0.0000 | 0 | 0 |
| NNI model | 2 figures, no problems, no escalation | 0.0000 | 0 | 0 |
| locked block | same as the saved run | 0.0001 | 0 | 0 |
| evidence | esa10-8.94, ppp23-1.13, esa10-11.05, ppp23-4.16 | 0.0003 | 0 | 0 |
| explanation, attempt 1 | failed: directions, passage talk, citations | 90.2 | 1,683 | 133 |
| explanation, attempt 2 | passed (the fixed sentence) | 16.7 | 2,111 | 9 |
| status | passed on retry | 0 | 0 | 0 |

- The locked block and the evidence are the same as in the saved run for all 24 questions.
- Over the 24 questions, the steps in Python took under a tenth of a second here; the model's 34 attempts took 1,944 seconds on the laptop. The NNI model's data load once, in about 0.02 seconds.
- The third-round routing rules (Chapter 12) gave 6 of the vertical domain expert's 10 questions a route other than the one the run used. Five went to R4, the default for definitions, because the rules did not know "USA", "Euroarea", "Chinese" or "Japanese" as economy names (f-02 to f-05, f-10); f-06 ("revised by in 2023") was escalated as beyond the data. The Chapter 14 run used the labelled routes, so its figures are right.
- The fourth-round rules (12.5.7) read the economy names from the knowledge graph and route all 10 as labelled, a training score. The trace uses the fourth round.

## 15.4 The user's two settings

### 15.4.1 Principles

A user chooses two settings. The **use mode** (non-commercial or commercial) decides which passages may be sent to the model, through Chapter 8's licence filter. The **role** (analyst or executive) decides how long an answer from passages may be, through Chapter 11's length rule. Both are kept in one dictionary, passed to each step and recorded on every line of the trace.

An unknown value stops the program with an error, rather than falling back to a default the user did not choose.

### 15.4.2 Code

```python
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
```

### 15.4.3 Results

- Commercial use changes the evidence for 13 of the 24 questions: the licence filter withholds the passages whose licence class allows only non-commercial use or quotation (Chapter 8), and the evidence takes the next passages.
- The role changes tokens out, not tokens in: 307 tokens out and 69 seconds for the analyst, 80 and 30 for the executive (Chapter 11's run). Explanations in Chapter 14 have one limit, 120 words, for both roles.

## 15.5 The list for review

### 15.5.1 Principles

The horizontal domain expert needs every problem in one plain list: each failed check of each attempt, with the problem in words; each dropped explanation; each escalation. Each attempt's row gives its tokens and seconds, so the list shows what each retry cost. The counts per check say which check fails most.

### 15.5.2 Code

```python
def review_list(saved_records):
    """
    Every problem the horizontal domain expert should see, one row each: each failed
    check of each attempt (with the problem in words), each dropped
    explanation and each escalation. Rows for an attempt give its tokens
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
```

```python
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
```

### 15.5.3 Results

The Chapter 14 run after the review gives 96 rows.

| Check | Problems | Questions |
| --- | --- | --- |
| Citations | 61 | 13 |
| Direction words | 13 | 4 |
| Remarks about the passages | 9 | 7 |
| Numbers | 2 | 1 |
| Dropped | 9 | 9 |
| Escalated | 2 | 2 |

- Citation problems are most of the list: a sentence with no id, an id not given, a sentence its passage does not support, or a miscitation.
- Retries: 13 questions were retried, for 23,541 tokens and 6.2 minutes. Four passed on retry; three of them wrote only the fixed sentence ("No explanation is available from the passages."). One retry gave an explanation with content: f-08.
- The two escalations (q5-03, f-02) are written by code and cost no tokens.

## 15.6 The scores already measured

### 15.6.1 Principles

One table gathers the scores of Chapters 8 to 14. Nothing new is measured. A **training score** comes from questions the code or rules were written or chosen while reading; a **fair score** comes from questions written before the code they score and opened once.

### 15.6.2 Results

| Chapter | Score | Result | Label |
| --- | --- | --- | --- |
| 8 | Chroma's filtered top three equal to the hand-written filter, both use modes | 32 of 32 | Training |
| 10 | Definition questions with a gold passage in the top three, filtered search | 31 of 32 | Training |
| 12 | Questions routed as labelled, bank, ragged-edge rules | 56 of 56 | Training |
| 12 | Questions routed as labelled, first test set, first-round rules | 19 of 32 | Fair |
| 12 | Questions routed as labelled, second test set, revised rules | 6 of 16 | Fair |
| 12 | Questions routed as labelled, Chapter 14 fair questions, fourth-round rules | 10 of 10 | Training |
| 13 | Parameters read right (same figures), keyword rules, new questions | 2 of 20 | Fair |
| 13 | Parameters read right (same figures), model round 2, new questions | 9 of 20 | Fair |
| 13 | Replies with no invented number (model wrote the whole reply) | 13 of 14 | Training |
| 14 | The vertical domain expert's sentences judged supported; the check agreed on 17 | 19 of 20 | Training |
| 14 | Explanations with content shown, first run, new questions | 0 of 10 | Fair |
| 14 | Explanations with content shown, after the review, the vertical domain expert's 10 | 2 of 10 | Training |

- The fair scores are lower than the training scores wherever both exist: routing 56 of 56 against 19 of 32; reading parameters 21 of 28 against 2 of 20 (keyword rules, Chapter 13).
- Retrieval scores are training scores: the searches were chosen while reading the 32 definition questions.

## 15.7 Lessons for a production version

### What worked

1. Every figure is calculated by Python from WDI and PWT data. The JavaScript version gives the same numbers for all 147 economy-years tested.
2. The locked block answered all 24 questions in the Chapter 14 run and corrected q4-02's false premise.
3. The four kinds of model mistake in Chapter 13 (wrong sign, false premise, added flags, escalation not called for; F15 to F18) cannot occur in the locked block: a tested function writes each of those lines.
4. The checks dropped all 28 faulty explanations and showed none.
5. The vertical domain expert judged 19 of 20 cited sentences supported; the word-overlap check agreed on 17.
6. Routing: 56 of 56 bank questions (training); 19 of 32 new questions in the first fair test.
7. Definition questions: a correct passage in the top three for 31 of 32.
8. The licence filter in the vector database kept the same passages as the hand-written filter on all 32 questions.
9. Every score is labelled training or fair; fair tests were frozen in a commit before the questions were opened.
10. After the review, two explanations with content passed (f-07, f-08), training scores.
11. Only the steps that call the language model use tokens: the explanation and, for definition questions, the answer extracted from passages. Lookups, series titles, clarifying and escalation are answered by code at no cost in tokens, and the steps in Python took under a tenth of a second for 24 questions.

### What a production version needs

1. A better reader for typed questions. Keyword rules found the right figures for 2 of 20 new questions, the small model for 9 of 20, and the routing rules sent 6 of the vertical domain expert's 10 questions to a route other than the labelled one: five because the rules did not know names such as USA and Japanese, one because a year of revision was read as a year of data. The demonstrator reads questions against a catalogue of measures in the knowledge graph (decision 25), which a production team keeps instead of a bank of questions.
2. A larger model asked for sentence and id as separate fields.
3. Counts of both kinds of check error: good replies dropped and bad replies shown.
4. A check that a reply answers the question (f-09).
5. A named person who sets and reviews the size bands.
6. New questions from real users, scored before any rule changes.
7. More data and passages (a passage defining PPP; the production boundary for unpaid work at home).
8. Review in a form the expert can read quickly.
9. A token and time limit for each route. On the laptop, an R2 question with an explanation took about 3,100 tokens in and 108 seconds; a retry added about 1,800 tokens and 29 seconds, and gave real content only once out of 13 retries.

## Tests

`tests/test_ch15_token_cost.py`, 19 tests; with the earlier chapters, 335 pass. No language model is called. They check:

- tokens and seconds are counted from every saved run, retries counted apart, and the Chapter 14 run totals 34 calls and 32.4 minutes;
- lookups cost no tokens;
- the executive's answers have fewer than half the analyst's tokens out;
- unknown settings stop with an error;
- the trace has one line per step, the steps with no model reproduce the saved locked blocks and evidence, and only the model uses tokens;
- commercial use changes the evidence;
- the review list counts dropped explanations, and every attempt row gives its tokens;
- every score is labelled training or fair.

## Glossary additions

- **Token:** the unit a language model reads and writes: a word or part of a word.
- **Tokens in:** the tokens sent to the model in one call (Ollama's `prompt_eval_count`, saved as `prompt_tokens`).
- **Tokens out:** the tokens the model writes in one call (Ollama's `eval_count`, saved as `reply_tokens`).
- **Token cost:** the tokens a step or a route uses per question; on a hosted model it is paid in money, on the laptop in time.
- **Trace:** a file with one line for each step of each question, with its output, seconds and tokens.
- **Step line:** one line of a trace.
- **User settings:** the use mode and the role, chosen by the user and recorded on every step line.
- **Review list:** every failed check, retry, dropped explanation and escalation, one row each, for the horizontal domain expert.
- **Training score:** a score on questions the code or rules were written or chosen while reading.
- **Fair score:** a score on questions written before the code they score and opened once.

## Links

- Code: `ragbook/ch15_token_cost.py`; tests: `tests/test_ch15_token_cost.py`
- Trace: `data/traces/ch15_traces.jsonl`
- Saved runs: `data/answers/ch11_answers.jsonl`, `data/answers/ch12_router_replies.jsonl`, `data/answers/ch13_parameter_replies_second.jsonl`, `data/answers/ch13_replies.jsonl`, `data/answers/ch14_explanations_review.jsonl`
- Repository: [github.com/lavanito/python-rag-textbook](https://github.com/lavanito/python-rag-textbook), branch `ch15-token-cost`
- [Ollama API: the counts each reply returns](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Python `time.perf_counter`](https://docs.python.org/3/library/time.html#time.perf_counter)
- [JSON Lines](https://jsonlines.org/)
