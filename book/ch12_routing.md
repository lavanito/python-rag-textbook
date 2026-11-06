# Chapter 12 — Routing questions

## 12.1 What this chapter builds

Chapters 3 to 11 answer one kind of question: a definition, answered from quoted passages. The bank has other kinds: a figure for one year, a growth split, a comparison of two economies, a "what if". Each needs a different part of the system, and some need no language model at all.

A router reads a question and gives it two labels before anything else runs:

1. **A class:** what kind of question it is, Q1 to Q8, AMB (too vague) or OUT (out of scope).
2. **A route:** how it is answered, from R1 (no AI) to R6 (an agent loop), or clarify, or escalate.

This chapter builds two routers and scores them on the same questions: keyword rules (12.3) and a small language model (12.4). It then combines them (12.5). The code is in `ragbook/ch12_routing.py`.

Each question is routed alone. The demonstrator keeps no memory of earlier questions, so a follow-up such as "what does that mean?" cannot be answered, and a user cannot narrow a question in steps. The one exchange it supports is "clarify": a vague question gets three sharper questions, each complete in itself, and the user picks one (Lavan, 6 November 2026).

## 12.2 Classes and routes

### 12.2.1 Principles

The routes form a routing ladder, cheapest first. The rule: send each question to the lowest route that can answer it.

| Route | How the question is answered | Cost |
| --- | --- | --- |
| R1 | No AI: copy a series' published title from a list | Free |
| R2 | Code computes the answer from the data | Free |
| R3 | A cached answer, built once and served again | Near-free |
| R4 | Retrieval: quoted passages, reported by the language model (Chapters 3–11) | Low |
| R4+R2 | Retrieval for the explanation, code for the figure | Low |
| R5>R2 | A small model reads the inputs from the question; code computes | Low |
| R6 | An agent loop: the model plans several steps within a step budget | High |
| clarify | Offer three sharper questions: living standards, growth or productivity | Low |
| escalate | Refuse, with the reason | — |

R3 is how the demonstrator serves answers already built offline, so no question is labelled R3. "Discovery without generation", search results shown without a written answer, is R4 with the last step left out; it is not R1, because a search ranks passages and can be wrong.

Each class has a usual route:

| Class | Kind of question | Usual route |
| --- | --- | --- |
| Q1 | Lookup: one value, or a series' exact name | R2 (R1 for a series name) |
| Q2 | Definition | R4 |
| Q3 | Compute, such as what drove growth | R2 |
| Q4 | Vintage: how an estimate changed between releases | R2, or R4+R2 if it asks why |
| Q5 | Two or more economies compared | R2, or R4+R2 if it asks why |
| Q6 | A definition and a figure | R4+R2 |
| Q7 | Scenario: what if one input were different | R5>R2 |
| Q8 | Several steps, each depending on the last | R6 |
| AMB | Too vague: no measure or year | clarify |
| OUT | Judgement, policy advice, forecast, or outside the data | escalate |

### 12.2.2 The two question sets

- **The bank: 56 questions.** 33 definition questions (Q2: q2-01 to q2-32, and q5-04, relabelled Q2 on 3 November 2026) and 23 of other classes. Retrieval in Chapters 3–11 is still measured on q2-01 to q2-32 only. The rules in 12.3 were written with the bank in view.
- **The test set: 32 questions.** Lavan Mahadeva wrote them on 3 November 2026, after the rules were written and without seeing them, and labelled their classes; the routes follow from the classes by the usual pairs. They are in `data/question_bank/routing_test_5_november.jsonl` and are never edited to suit a router.

| Class | Bank | Test set |
| --- | --- | --- |
| Q1 | 3 | 2 |
| Q2 | 33 | 15 |
| Q3 | 2 | 1 |
| Q4 | 2 | 1 |
| Q5 | 4 | 2 |
| Q6 | 3 | 1 |
| Q7 | 1 | 2 |
| Q8 | 1 | 2 |
| AMB | 3 | 1 |
| OUT | 4 | 5 |

A router is right on a question when it gives both the labelled class and the labelled route.

## 12.3 Keyword rules

### 12.3.1 Principles

A keyword rule tests the question's text for a word, a phrase or a pattern, such as a year after 2030 with "will". The rules are tried in a fixed order and the first that matches decides. Refusals come first, so a forecast is escalated before any rule looks for a figure. A question that matches no rule goes to retrieval (Q2, R4), unless most of its words appear nowhere in the corpus.

Rules cost nothing to run and give the same answer every time. Each can be read and argued with. They match only the wording their author thought of.

### 12.3.2 Code

`ragbook/ch12_routing.py`, the word lists and the functions `economies_named` and `route_question`:

```python
# The six economies, by every name the bank uses.
ECONOMIES = {
    "United States": ["united states", "us"],
    "euro area": ["euro area"],
    "United Kingdom": ["united kingdom", "uk"],
    "China": ["china"],
    "India": ["india"],
    "Japan": ["japan"],
}

# Word lists, one per rule. Each is written out so a reader can argue with it.
FORECAST = re.compile(r"\bwill\b.*\b20[3-9][0-9]\b")
ADVICE = re.compile(r"\bshould\b.*\b(cut|raise|interest rates?|taxes?|policy)\b")
JUDGEMENT = ["sustainable", "fair", "good for"]
SCENARIO = ["what if", "suppose", "had been"]
VAGUE = ["doing better", "catching up", "falling behind", "fallen behind"]
VINTAGE = ["vintage", "revised", "new icp results", "changed between"]
DRIVERS = ["drove", "came from", "explains"]
WHY = ["why", "depend", "hard to compare", "differ"]
SERIES_CODE = re.compile(r"\b[A-Z]{2}\.[A-Z0-9.]*[A-Z0-9]\b")
YEAR = re.compile(r"\b(19|20)[0-9]{2}\b")

# A question whose topic words are mostly missing from the corpus is outside it.
OUTSIDE_SHARE = 0.5
```

```python
def economies_named(question):
    """
    Return the economies a question names, in the order of ECONOMIES.

    Names are matched as whole words, so "us" does not match "because".

    Example:
        economies_named("Is China catching up with the United States?")
        returns ["United States", "China"]
    """
    text = " " + " ".join(split_into_words(question)) + " "
    found = []
    for economy, names in ECONOMIES.items():
        if any(" " + name + " " in text for name in names):
            found.append(economy)
    return found
```

```python
def route_question(question, known_words, titles):
    """
    Give a question a class and a route with keyword rules.

    The rules are tried in order and the first that matches decides. The
    order puts refusals first, then the cheapest routes: a question that
    asks for a forecast is escalated before any rule looks for a figure.
    Returns the class, the route and the name of the rule that decided.

    Example:
        route_question("What will China's GDP be in 2030?", words, titles)
        returns ("OUT", "escalate", "forecast")
    """
    text = question.lower()
    words = topic_words(question)
    economies = economies_named(question)
    if FORECAST.search(text):
        return "OUT", "escalate", "forecast"
    if ADVICE.search(text):
        return "OUT", "escalate", "policy advice"
    if contains_any(question, JUDGEMENT):
        return "OUT", "escalate", "judgement"
    code = SERIES_CODE.search(question)
    if code and code.group() in titles and "name" in text:
        return "Q1", "R1", "series name"
    if contains_any(question, SCENARIO):
        return "Q7", "R5>R2", "scenario"
    if contains_any(question, VAGUE) and not YEAR.search(question):
        return "AMB", "clarify", "too vague"
    if " now " in f" {text} " and " ago" in text:
        return "Q8", "R6", "two dates and an explanation"
    if contains_any(question, VINTAGE) and economies:
        route = "R4+R2" if text.startswith("why") else "R2"
        return "Q4", route, "vintage"
    if len(economies) >= 2:
        route = "R4+R2" if contains_any(question, WHY) else "R2"
        return "Q5", route, "two economies"
    if economies and text.startswith("what is"):
        return "Q6", "R4+R2", "definition and a figure"
    if economies and contains_any(question, DRIVERS + ["how much of"]):
        return "Q3", "R2", "compute"
    if economies and YEAR.search(question):
        return "Q1", "R2", "value lookup"
    if words and sum(word in known_words for word in words) / len(words) < OUTSIDE_SHARE:
        return "OUT", "escalate", "outside the corpus"
    return "Q2", "R4", "definition (default)"
```

### 12.3.3 Annotations

- **Order matters.** The check for words outside the corpus is the last rule. Placed first, it escalated three bank questions whose words are mostly codes or economy names (amb-03, q6-01, q1-03).
- **"Should" alone is not advice.** "Should annual price and volume indices be chained?" is a definition question, so the advice rule also needs a policy word.
- **R1 needs a known code.** The series-name rule fires only for one of the 17 World Bank codes in `data/series/wdi_titles.csv`, whose titles were copied from the World Bank's own data service.

### 12.3.4 Results

| Questions | Class right | Route right | Both right |
| --- | --- | --- | --- |
| Bank (56) | 56 | 56 | 56 |
| Test set (32) | 19 | 20 | 19 |

- **56 of 56 on the bank is a training score.** The rules were written while reading those questions.
- **19 of 32 on the test set is the real score.** The 13 misses:
    - Economies outside the six are not recognised, so t-03 and t-09 (Switzerland) were not escalated; "Irish" in t-21 was not recognised.
    - The corpus check refused two definition questions (t-17 on financial assets, t-19 on gross and net investment) and passed one out-of-scope question (t-08).
    - "If pre-2008 trends had continued" (t-02) matches none of the scenario phrases.
    - "From 2022 to 2026" (t-31) is a forecast, but the forecast rule needs "will" (first wording; moved to 2024 on 6 November, 12.5.6).
    - A series code inside a link (t-32) is missed, because the rule needs the word "name".
    - "During its lost decade" (t-28) gives no two dates.
    - Naming the UK and the US made a definition question (t-05) a comparison.
    - A year and an economy made t-04 (a 2026 poll) and t-26 (spending components) value lookups.

## 12.4 A small model as router

### 12.4.1 Principles

A language model can route wording that no rule was written for. Routing is a narrow task: read one question, reply with two labels. A small local model can do it in a few seconds.

The model gets four things:

- **The labels:** each class and route, in one line.
- **The limits of the data:** six economies plus the 21 euro area members, 2000 to 2025, and no exports, imports or spending components other than household consumption.
- **The 17 series codes,** for R1.
- **Eleven examples:** one bank question for each class, plus one R1 question, given as earlier turns of the conversation. None is in the test set, and the bank score leaves them out.

The settings are Chapter 11's with temperature 0, so the same question gives the same reply, and a limit of 20 tokens.

### 12.4.2 Code

`ragbook/ch12_routing.py`, the functions `router_messages`, `read_router_reply` and `route_with_model`:

```python
ROUTER_SETTINGS = dict(SETTINGS, temperature=0, num_predict=20)
```

```python
ROUTER_REPLY = re.compile(r"\b(Q[1-8]|AMB|OUT)\b\s+(R4\+R2|R5>R2|R[1-6]|clarify|escalate)\b")
```

```python
def router_messages(question, examples, titles):
    """
    Build the messages that ask the model to route one question.

    The instructions name the classes, the routes and the limits of the
    data; the examples are pairs of a bank question and its labels, given
    as earlier turns of the conversation.

    Example:
        router_messages("What is GDI?", [], titles)[-1]
        returns {"role": "user", "content": "What is GDI?"}
    """
    codes = ", ".join(titles)
    messages = [{"role": "system", "content": ROUTER_INSTRUCTIONS.format(codes=codes)}]
    for example in examples:
        messages.append({"role": "user", "content": example["question"]})
        messages.append({"role": "assistant", "content": f"{example['class']} {example['route']}"})
    messages.append({"role": "user", "content": question})
    return messages
```

```python
def read_router_reply(reply):
    """
    Read the class and route from the model's reply.

    A reply with no recognisable class and route gives ("none", "none"),
    which counts as wrong.

    Example:
        read_router_reply("Q6 R4+R2") returns ("Q6", "R4+R2")
    """
    found = ROUTER_REPLY.search(reply)
    if found is None:
        return "none", "none"
    return found.group(1), found.group(2)
```

```python
def route_with_model(questions, examples, titles, ask=ask_model_with_details, test_set=""):
    """
    Ask the model to route each question; keep the reply, tokens and seconds.

    Example:
        route_with_model(questions, examples, titles)[0]["found_class"]
        returns "Q2"
    """
    records = []
    for question in questions:
        messages = router_messages(question["question"], examples, titles)
        reply = ask(messages, options=ROUTER_SETTINGS)
        found_class, found_route = read_router_reply(reply["answer"])
        records.append({
            "test_set": test_set, "id": question["id"], "question": question["question"],
            "class": question["class"], "route": question["route"],
            "reply": reply["answer"], "found_class": found_class, "found_route": found_route,
            "class_right": found_class == question["class"],
            "route_right": found_route == question["route"],
            "prompt_tokens": reply["prompt_tokens"], "reply_tokens": reply["reply_tokens"],
            "seconds": reply["seconds"],
        })
    return records
```

### 12.4.3 Annotations

- **The reply is read, not trusted.** `read_router_reply` looks for a class followed by a route. A reply without one counts as wrong; none of the 77 replies lacked one.
- **The model can pair labels badly.** It replied "Q2 clarify" once and "Q2 R4+R2" four times: a class with a route that does not belong to it.

### 12.4.4 Results

Lavan ran the model on 5 November 2026: 77 replies (45 bank questions and the 32 test questions) in 3.3 minutes, 2.6 seconds each.

| Questions | Class right | Route right | Both right |
| --- | --- | --- | --- |
| Bank, examples left out (45) | 39 | 39 | 37 |
| Test set (32) | 17 | 17 | 15 |
| Second test set (16), run 6 Nov | 7 | 7 | 6 |

- **The model scores lower than the rules on the test set: 15 against 19.**
- **They miss mostly different questions.** The rules are right and the model wrong on 10; the model right and the rules wrong on 6; both wrong on 7. At least one is right on 25.
- **The model escalates too often.** It refused two definition questions (t-01, t-12) and read "how do you calculate…" and "how do economists determine…" as compute (t-14, t-16, t-20).
- **The model is better at spotting what is out of scope.** It escalated the poll (t-04), the question on GDP per head and quality of life (t-08) and the China–Switzerland question (t-09), and kept t-17 and t-19 as definitions.
- **Both missed seven:** t-02, t-03, t-21, t-26, t-28, t-31 and t-32. Most are about the limits of the data.
- **On the second test set the model and the rules tie: 6 of 16 each.** Lavan ran the model on the 16 new questions on 6 November 2026 (`--model-second`, 72 seconds). It missed the three questions past the ragged edge (u-03, u-04, u-13), called u-14's "what would … have grown if" a compute question, and escalated u-16 instead of clarifying. Rules first, then the model, also gives 6.

## 12.5 Rules first, the model for the rest

### 12.5.1 Principles

The routing ladder suggests an order: the cheap, certain router first, the model only where it is unsure. Here the rules are taken as unsure when they decide only because nothing else matched: the default (Q2, R4) and "outside the corpus". This choice was fixed on 5 November 2026 before the combined score was computed.

### 12.5.2 Code

`ragbook/ch12_routing.py`, the list `FALL_BACK_RULES` and the function `combine`:

```python
FALL_BACK_RULES = ["definition (default)", "outside the corpus"]
```

```python
def combine(rule_records, model_records):
    """
    Take the rules' answer when a specific rule matched, else the model's.

    Both lists are routings of the same questions. Each combined record
    says which router decided.

    Example:
        combine(rule_records, model_records)[0]["decided_by"]
        returns "rules"
    """
    model_by_id = {record["id"]: record for record in model_records}
    combined = []
    for record in rule_records:
        if record["rule"] in FALL_BACK_RULES:
            chosen = dict(model_by_id[record["id"]], decided_by="model")
        else:
            chosen = dict(record, decided_by="rules")
        combined.append(chosen)
    return combined
```

### 12.5.3 Results

| Router | Test set, both right (of 32) |
| --- | --- |
| Keyword rules | 19 |
| Small model | 15 |
| Rules first, then the model | 16 |

- **Combining them lowered the score.** The model decided 21 of the 32 questions.
- **The default was a good guess.** 15 of the 32 test questions are definitions, so "Q2, R4" was right on most of the questions the rules could not place. The model replaced several of those right answers with its own errors (t-01, t-12, t-14, t-16, t-20) and gained three (t-08, t-17, t-19).
- **A different way of combining them could score higher.** One example: let the model decide only when it says OUT. But that idea came from reading these results, so its score would be a training score too.

### 12.5.4 Second round: revised rules

The seven questions both routers missed point to six checks the rules lacked. They were added on 5 November 2026, after reading the misses, in front of the first-round rules:

- **A series code anywhere, a link included:** R1 if it is one of the 17, out of scope if not.
- **An economy not in the data,** such as Switzerland: out of scope.
- **"If … had":** a scenario.
- **A year after 2025, the last year of the data:** out of scope.
- **Ireland or "Irish" with a year:** a value lookup, since Ireland is a euro area member in the data.
- **"Components" with an economy:** compute.

`ragbook/ch12_routing.py`, the word lists and the function `route_question_revised`:

```python
LAST_YEAR = 2025
OTHER_ECONOMIES = [
    "switzerland", "singapore", "australia", "canada", "norway", "sweden",
    "denmark", "korea", "brazil", "mexico", "russia", "indonesia", "turkey",
    "saudi arabia", "argentina", "south africa", "us states", "50 states",
]
EURO_MEMBER_NAMES = ["ireland", "irish"]
CONDITIONAL = re.compile(r"\bif\b.*\bhad\b")
ANY_CODE = re.compile(r"[A-Z]{2}\.[A-Z0-9.]*[A-Z0-9]")
```

```python
def route_question_revised(question, known_words, titles):
    """
    The keyword rules with six checks added in front of them.

    A series code anywhere in the question, a link included, decides first:
    R1 if the code is one of the 17, out of scope if not. Then an economy
    not in the data, a conditional "if ... had", a year after the data end,
    a euro area member with a year, and "components" with an economy.
    Anything else goes to route_question.

    Example:
        route_question_revised("https://data.worldbank.org/indicator/SP.POP.TOTL", words, titles)
        returns ("Q1", "R1", "series code")
    """
    text = question.lower()
    words_in_text = " " + " ".join(split_into_words(question)) + " "
    code = ANY_CODE.search(question)
    if code:
        if code.group() in titles:
            return "Q1", "R1", "series code"
        return "OUT", "escalate", "series not in the data"
    if any(" " + name + " " in words_in_text for name in OTHER_ECONOMIES):
        return "OUT", "escalate", "economy not in the data"
    if CONDITIONAL.search(text):
        return "Q7", "R5>R2", "scenario (if ... had)"
    years = [int(year) for year in re.findall(r"\b(?:19|20)[0-9]{2}\b", question)]
    if years and max(years) > LAST_YEAR:
        return "OUT", "escalate", "beyond the data"
    if any(" " + name + " " in words_in_text for name in EURO_MEMBER_NAMES) and years:
        return "Q1", "R2", "value lookup (euro area member)"
    if "components" in text and economies_named(question):
        return "Q3", "R2", "compute (components)"
    return route_question(question, known_words, titles)
```

| Router | Bank, both right (of 56) | Test set, both right (of 32) |
| --- | --- | --- |
| First-round rules | 56 | 19 |
| Revised rules | 56 | 26, a training score |

- **26 of 32 is not a fair score.** The checks were written after reading these misses, so the test set is now training data for them. A fair score needs new questions.
- **The bank score did not change.** None of the six checks fires wrongly on the 56 bank questions.
- **Six misses remain.** t-05 (the UK and the US in a definition question), t-08 and t-17, t-19 (the corpus check), t-28 ("lost decade" gives no years), and t-31. For t-31, "2022 to 2026" is now escalated as beyond the data; the label says multi-step (Q8, R6). This is the first wording; see 12.5.6.
- **The list of other economies is short.** It names 18 places; a question about Chile still passes it.
- **The fair score is 6 of 16.** Lavan wrote 16 more questions on 6 November 2026, after the revised rules, without seeing them (`data/question_bank/routing_test_6_november.jsonl`). Scored once, unchanged, the revised rules route 6 of 16 as labelled, the same as the first-round rules. Two of the 16 ask about years beyond the data (u-03, Japan to 2025; u-13, Ireland's revisions to 2025) and are labelled for escalation; the revised rules miss both, because they check one last year, 2025, for every economy and every release. The main misses: "USA" and "euroarea" are not in the economy names; "if we had to use" fires the new "if … had" scenario check; "What is … of Japan" reads as a definition and a figure.

### 12.5.5 What an escalated question gets

A question routed to "escalate" gets a reason and a message. The build spec listed four reasons: judgement, policy advice, forecast, outside the corpus. A year after 2025 is not a forecast, since the figure may already be published elsewhere; Switzerland is not outside the corpus, since the World Bank publishes it. Both are gaps in this data set, a matter of completeness, so on 6 November 2026 Lavan added two reasons: **beyond the data** and **economy not in the data**. Their messages say what is missing and what the data contain. A code not among the 17 series gets a third, **series not in the data**.

`ragbook/ch12_routing.py`, the reasons, the messages and the function `escalation_message`:

```python
# The reason a user is given for each rule that escalates. "Beyond the data"
# and "economy not in the data" were added by Lavan Mahadeva on 6 November 2026:
# both are gaps in this data set (completeness), not questions the system
# refuses on principle, so the message says what is missing and what the data contain.
ESCALATION_REASONS = {
    "forecast": "forecast",
    "policy advice": "policy advice",
    "judgement": "judgement",
    "outside the corpus": "outside the corpus",
    "beyond the data": "beyond the data",
    "economy not in the data": "economy not in the data",
    "series not in the data": "series not in the data",
}

ESCALATION_MESSAGES = {
    "forecast": "This asks for a forecast. Only published figures are reported here.",
    "policy advice": "This asks for policy advice, which is not given here.",
    "judgement": "This asks for a judgement, which is left to a person.",
    "outside the corpus": "The manuals and data used here do not cover this question.",
    "beyond the data": ("The data here end in {last_year}, so later years are not "
                        "available. The latest year in the data is {last_year}."),
    "economy not in the data": "This economy is not in the data used here. The data cover {economies}.",
    "series not in the data": ("This series is not in the data used here. The {count} series "
                        "in the data are listed in data/series/wdi_titles.csv."),
}

ECONOMIES_IN_DATA = ("the United States, the euro area and its 21 members, the United "
                  "Kingdom, China, India and Japan")
```

```python
def escalation_message(rule, titles):
    """
    Return the reason and the message for a question a rule escalated.

    Example:
        escalation_message("beyond the data", titles)
        returns ("beyond the data", "The data here end in 2025, so later years
        are not available. The latest year in the data is 2025.")
    """
    reason = ESCALATION_REASONS[rule]
    message = ESCALATION_MESSAGES[reason].format(
        last_year=LAST_YEAR, economies=ECONOMIES_IN_DATA, count=len(titles))
    return reason, message
```

- **The message does not yet give the nearest figure.** "The latest year in the data is 2025" could carry the 2025 value with its source, vintage and DQR; that needs the model class, so it waits for the app build.

### 12.5.6 Third round: the ragged edge

The data do not end in the same year everywhere. The last year with every input for real NNI per head is 2024 for the United States, Japan and China (household consumption ends there) and 2025 for the United Kingdom, India, the euro area and Ireland. In the March 2024 archive edition it is 2022, and the euro area members are not in it. This uneven end is the **ragged edge**.

The second-round rules checked one last year, 2025, for every economy and edition, so they passed questions about Japan to 2025 or Ireland's revisions to 2025. On 6 November 2026 Lavan asked for a last year for each economy and edition. A script, `tools/build_last_year.py`, runs the model's own loader and decomposition class and writes `data/series/last_year.csv`; no year is typed.

The last year also differs by measure: hours worked end in 2023, and published NNI ends in 2021. The rule does not check the measure. In practice, statistical producers often nowcast the missing years with a model such as a Kalman filter and mark the filled values as estimated; this book escalates them instead, except NNI after 2021, which is filled and flagged "estimated" (Chapter 13).

`ragbook/ch12_routing.py`, the names, the file and the functions `load_last_years`, `beyond_the_edge` and `beyond_the_edge_message`. `route_question_ragged` is `route_question_revised` with its year check replaced by `beyond_the_edge`.

```python
# The last year of real NNI per head differs by economy and by WDI edition
# (Lavan Mahadeva, 6 November 2026). Written by tools/build_last_year.py from
# the nni-model code; a blank last year means the economy is not in that edition.
LAST_YEAR_FILE = Path(__file__).parent.parent / "data" / "series" / "last_year.csv"

# Names for the economies in last_year.csv. Used by the ragged-edge check only.
ECONOMY_NAMES = {
    "USA": ["united states", "us", "usa"],
    "EA21": ["euro area", "euroarea", "eurozone"],
    "GBR": ["united kingdom", "uk", "britain", "british"],
    "CHN": ["china", "chinese"],
    "IND": ["india", "indian"],
    "JPN": ["japan", "japanese"],
    "IRL": ["ireland", "irish"],
}
DISPLAY_NAMES = {"USA": "the United States", "EA21": "the euro area", "GBR": "the United Kingdom",
                 "CHN": "China", "IND": "India", "JPN": "Japan", "IRL": "Ireland"}
REVISION_WORDS = ["revision", "revised", "vintage", "changed between", "icp"]
```

```python
def load_last_years(file_path=LAST_YEAR_FILE):
    """
    Read the last year of the data for each economy and edition.

    Example:
        load_last_years()[("JPN", "latest")] returns 2024
        load_last_years()[("IRL", "archive")] returns None
    """
    last_years = {}
    with open(file_path, encoding="utf-8") as file:
        for row in csv.DictReader(file):
            year = int(row["last_year"]) if row["last_year"] else None
            last_years[(row["economy"], row["edition"])] = year
    return last_years
```

```python
def beyond_the_edge(question, last_years):
    """
    Find the first economy whose data end before a year the question names.

    A question about revisions is checked against both editions. A question
    that names no economy is checked against the latest year of any economy.
    Returns (economy, edition, last year), or None if every year is covered.

    Example:
        beyond_the_edge("Japan's growth from 2010 to 2025?", last_years)
        returns ("JPN", "latest", 2024)
    """
    words_in_text = " " + " ".join(split_into_words(question)) + " "
    years = [int(year) for year in re.findall(r"\b(?:19|20)[0-9]{2}\b", question)]
    if not years:
        return None
    named = [economy for economy, names in ECONOMY_NAMES.items()
             if any(" " + name + " " in words_in_text for name in names)]
    editions = ["latest"]
    if contains_any(question, REVISION_WORDS):
        editions.append("archive")
    if not named:
        latest = max(year for (economy, edition), year in last_years.items()
                     if edition == "latest" and year is not None)
        return ("", "latest", latest) if max(years) > latest else None
    for economy in named:
        for edition in editions:
            last = last_years[(economy, edition)]
            if last is None or max(years) > last:
                return economy, edition, last
    return None
```

```python
def beyond_the_edge_message(edge):
    """
    Say which data end where, for a question escalated as beyond the data.

    Example:
        beyond_the_edge_message(("JPN", "latest", 2024))
        returns "The data here for Japan end in 2024, so later years are not available."
    """
    economy, edition, last = edge
    if last is None:
        return (f"The {edition} edition used here has no data for {DISPLAY_NAMES[economy]}, "
                f"so its figures cannot be compared across editions.")
    name = DISPLAY_NAMES.get(economy, "any economy")
    if edition == "archive":
        return (f"The archive edition used here ends in {last} for {name}, "
                f"so revisions after {last} cannot be compared.")
    return f"The data here for {name} end in {last}, so later years are not available."
```

**Changes to the test sets, 6 November 2026 (Lavan).** Two questions asked about years past the edge without meaning to: t-26 (US spending components, "2022 to 2025") and t-31 (euro area NNI, "2022 to 2026"). Their dates were moved to 2024, inside the data, and their labels kept. One, u-04 (Japan "2010 to 2025"), was relabelled OUT/escalate. The first wording is kept in each question's note. The model's saved replies answer the first wording of t-26 and t-31.

| Router | Bank (56) | First test set (32) | Second test set (16) |
| --- | --- | --- | --- |
| First-round rules (12.3) | 56 | 19 | 6 |
| Revised rules (12.5.4) | 56 | 26 | 6 |
| Ragged-edge rules (12.5.6) | 56 | 26 | 9 |

- **Fair scores: 19 of 32 and 6 of 16 for the first-round rules, and 6 of 16 for the revised rules.** Each set was written before the rules it scores. Every other number is a training score.
- **The ragged edge adds three on the second set:** u-03, u-04 and u-13, the three questions about years past the edge.
- **A fair score for the ragged-edge rules needs a third set of new questions. Lavan decided on 6 November 2026 to stop the rule rounds here.**

What would a test set twice the size show: the same order of routers, or a different one?

## 12.6 Tests, glossary and links

### 12.6.1 Tests

The file `tests/test_ch12_routing.py` has 25 tests. None needs the model; three read the saved replies from the two laptop runs. Run them with `python -m pytest tests/test_ch12_routing.py -v`.

| Test | What it proves |
| --- | --- |
| Titles | 17 series titles are read; one is checked word for word |
| Economies | Names are matched as whole words: "us" is not found in "because" |
| Refusals | Forecast, policy advice and judgement are escalated first; "should" alone is not advice |
| Series name | R1 only for a code in the list |
| Vague | "Falling behind" is AMB without a year and Q5 with one |
| Outside the corpus | Escalated only when no other rule matches |
| Bank score | 56 of 56 |
| Test set file | 32 questions, 5 of them OUT |
| Test set score | The rules' first score: 19 of 32 |
| Labels | Every class and route in both sets is an agreed code |
| Examples | The 11 examples cover every class and are not in the test set |
| Messages | Instructions, then examples as earlier turns, then the question |
| Reply reader | Class and route are read from a reply; a reply without them gives "none" |
| Settings | Temperature 0, 20 tokens, seed 42 |
| Stand-in model | The pipeline with a stand-in that always replies "Q2 R4" |
| Saved replies | 77 replies; the scores in 12.4.4; the seven questions both routers miss |
| Combined | The model decides 21; 16 of 32 |
| Revised rules | A series code in a link is R1; an unknown code, another economy or a year after 2025 is escalated; "Irish" with a year is a lookup; everything else goes to the first-round rules |
| Revised scores | 56 of 56 on the bank; 26 of 32 on the test set; the six misses |
| Escalation messages | Every rule that escalates has a reason and a message; "beyond the data" names 2025; "economy not in the data" lists the economies in the data |
| Second test set | 16 questions: 6 of 16 with either set of rules |
| Last years | Japan 2024 and the UK 2025 in the latest edition; the US 2022 and Ireland absent in the archive |
| Ragged edge | Japan to 2025 is past the edge, the UK to 2025 is not; a revision question about Ireland is checked against the archive; the message names the economy and year |
| Ragged-edge scores | 56 of 56; 26 of 32; 9 of 16 |

### 12.6.2 Glossary

| Term | Meaning |
| --- | --- |
| Router | Code that gives a question a class and a route before it is answered |
| Class | What kind of question it is: Q1 to Q8, AMB or OUT |
| Route | How a question is answered: R1 to R6, clarify or escalate |
| Routing ladder | The routes ordered from cheapest and most certain to most costly |
| Cached answer | An answer built once and served again unchanged until its sources change (R3) |
| Keyword rule | A test of a question's text for a word, phrase or pattern |
| Test set | Questions written after the router and kept unchanged, used only to score it |
| Training score | A score on the questions a router was built from; it overstates the score on new questions |
| Fall-back rule | A rule that decides only because no other rule matched |

### 12.6.3 Links

- Lavan Mahadeva, *Making Data AI-Ready: A Layered Framework*, section 20.2, "The Six-Tier Routing Ladder"
- [World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation): the source of the 17 series titles
- [Ollama API: chat](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion): the request the model router sends
- Chapter 11 (settings and saving replies); Chapter 14 (checking answers); Appendix A (fine-tuning a router)
