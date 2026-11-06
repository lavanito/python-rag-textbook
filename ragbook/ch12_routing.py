"""
Chapter 12 — Routing questions

What this file does
    Gives each question a class (what kind of question it is) and a route
    (how it is answered), using keyword rules, and scores the rules against
    the labels in the question bank. The routes follow the routing ladder,
    cheapest first: R1 no AI, R2 code, R4 retrieval, R5 small model, R6
    agent loop, plus clarify and escalate. The rules are tried in a fixed
    order and the first that matches decides.

Inputs
    The question bank (data/question_bank/questions.jsonl), the corpus
    (data/corpus/passages.jsonl) and the series titles
    (data/series/wdi_titles.csv).

Outputs
    For each question: the class and route the rules give, and the rule
    that decided. Counts of questions routed as labelled.

Used by
    Chapter 13 (model as a tool) and the demonstrator's router.

Uses
    Chapter 1 (load_passages); Chapter 2 (load_corpus, topic_words);
    Chapter 3 (QUESTION_FILE); Chapter 11 (SETTINGS,
    ask_model_with_details, save_answers, load_answers). Python's csv,
    re, sys, urllib and pathlib modules. For 12.4, Ollama running locally
    with qwen3:4b-instruct.

Run the worked example
    python -m ragbook.ch12_routing --model
        Asks the model to route the 56 bank questions and the 32 test
        questions, and saves the replies to
        data/answers/ch12_router_replies.jsonl. Needs Ollama running.
    python -m ragbook.ch12_routing
        Scores the keyword rules, and the saved model replies if there are
        any, on the bank and on the test set. Needs no model.
"""
import csv
import re
import sys
import urllib.error
from pathlib import Path

from ragbook.ch01_python_basics import load_passages, split_into_words
from ragbook.ch02_minimal_pipeline import load_corpus, topic_words
from ragbook.ch03_keyword_search import QUESTION_FILE
from ragbook.ch11_prompts import (
    ANSWER_FOLDER, SETTINGS, ask_model_with_details, load_answers, save_answers,
)

TITLE_FILE = Path(__file__).parent.parent / "data" / "series" / "wdi_titles.csv"
TEST_FILE = QUESTION_FILE.parent / "routing_test_5_november.jsonl"
ROUTER_FILE = ANSWER_FOLDER / "ch12_router_replies.jsonl"

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


def load_titles(file_path=TITLE_FILE):
    """
    Read the published title of each series in the model's data.

    Example:
        load_titles()["SP.POP.TOTL"] returns "Population, total"
    """
    with open(file_path, encoding="utf-8") as file:
        return {row["code"]: row["title"] for row in csv.DictReader(file)}


def corpus_words(passages):
    """
    Return the set of topic words found anywhere in the corpus.

    Example:
        "deflator" in corpus_words(load_corpus()) returns True
    """
    words = set()
    for passage in passages:
        words.update(topic_words(passage["text"]))
    return words


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


def contains_any(question, phrases):
    """
    Say whether a question contains any of the phrases, ignoring case.

    Example:
        contains_any("What drove growth?", ["drove"]) returns True
    """
    text = question.lower()
    return any(phrase in text for phrase in phrases)


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


def route_bank(questions, known_words, titles):
    """
    Route every question and record whether the rules agree with its labels.

    Example:
        route_bank(questions, words, titles)[0]["class_right"] returns True
    """
    records = []
    for question in questions:
        found_class, found_route, rule = route_question(question["question"], known_words, titles)
        records.append({
            "id": question["id"], "question": question["question"],
            "class": question["class"], "route": question["route"],
            "found_class": found_class, "found_route": found_route, "rule": rule,
            "class_right": found_class == question["class"],
            "route_right": found_route == question["route"],
        })
    return records


def count_right(records):
    """
    Count the questions given the labelled class, the labelled route, and both.

    Example:
        count_right(records) returns {"questions": 56, "class": ..., "route": ..., "both": ...}
    """
    return {
        "questions": len(records),
        "class": sum(record["class_right"] for record in records),
        "route": sum(record["route_right"] for record in records),
        "both": sum(record["class_right"] and record["route_right"] for record in records),
    }


# ---------------------------------------------------------------------------
# 12.5.4  Second round: rules revised after reading the test-set misses
# ---------------------------------------------------------------------------

# Added on 5 November 2026 after the first score on the test set, so scores
# with these rules on that set are training scores.
LAST_YEAR = 2025
OTHER_ECONOMIES = [
    "switzerland", "singapore", "australia", "canada", "norway", "sweden",
    "denmark", "korea", "brazil", "mexico", "russia", "indonesia", "turkey",
    "saudi arabia", "argentina", "south africa", "us states", "50 states",
]
EURO_MEMBER_NAMES = ["ireland", "irish"]
CONDITIONAL = re.compile(r"\bif\b.*\bhad\b")
ANY_CODE = re.compile(r"[A-Z]{2}\.[A-Z0-9.]*[A-Z0-9]")


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


def route_bank_revised(questions, known_words, titles):
    """
    route_bank with the revised rules.

    Example:
        count_right(route_bank_revised(questions, words, titles))
    """
    records = []
    for question in questions:
        found_class, found_route, rule = route_question_revised(question["question"], known_words, titles)
        records.append({
            "id": question["id"], "question": question["question"],
            "class": question["class"], "route": question["route"],
            "found_class": found_class, "found_route": found_route, "rule": rule,
            "class_right": found_class == question["class"],
            "route_right": found_route == question["route"],
        })
    return records


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


# ---------------------------------------------------------------------------
# 12.5.6  Third round: the ragged edge
# ---------------------------------------------------------------------------

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


def route_question_ragged(question, known_words, titles, last_years):
    """
    The revised rules with the year check replaced by the ragged edge.

    Everything else is as in route_question_revised: a series code, an
    economy not in the data and "if ... had" are checked first; then a year
    after the last year for the economy and edition the question asks about.

    Example:
        route_question_ragged("Japan's growth from 2010 to 2025?", words, titles, last_years)
        returns ("OUT", "escalate", "beyond the data")
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
    if beyond_the_edge(question, last_years):
        return "OUT", "escalate", "beyond the data"
    years = re.findall(r"\b(?:19|20)[0-9]{2}\b", question)
    if any(" " + name + " " in words_in_text for name in EURO_MEMBER_NAMES) and years:
        return "Q1", "R2", "value lookup (euro area member)"
    if "components" in text and economies_named(question):
        return "Q3", "R2", "compute (components)"
    return route_question(question, known_words, titles)


def route_bank_ragged(questions, known_words, titles, last_years):
    """
    route_bank with the third-round rules.

    Example:
        count_right(route_bank_ragged(questions, words, titles, last_years))
    """
    records = []
    for question in questions:
        found_class, found_route, rule = route_question_ragged(
            question["question"], known_words, titles, last_years)
        records.append({
            "id": question["id"], "question": question["question"],
            "class": question["class"], "route": question["route"],
            "found_class": found_class, "found_route": found_route, "rule": rule,
            "class_right": found_class == question["class"],
            "route_right": found_route == question["route"],
        })
    return records


# ---------------------------------------------------------------------------
# 12.4  A small model as router
# ---------------------------------------------------------------------------

CLASSES = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "AMB", "OUT"]
ROUTES = ["R1", "R2", "R4", "R4+R2", "R5>R2", "R6", "clarify", "escalate"]

# One bank question for each class, shown to the model as an example. None
# is in the test set.
EXAMPLE_IDS = ["q1-02", "q1-03", "q2-13", "q3-01", "q4-01", "q5-01", "q6-01",
               "q7-01", "q8-01", "amb-03", "out-03"]

ROUTER_INSTRUCTIONS = """You route questions about national accounts statistics.
Give each question one class and one route.

Classes:
Q1 lookup: one value for one economy and year, or the exact name of a data series
Q2 definition: what a term means or how it is measured
Q3 compute: a calculation from the data, such as what drove growth
Q4 vintage: how an estimate changed between data releases
Q5 multi-country: two or more economies compared
Q6 mixed: a definition and a figure
Q7 scenario: what if one input had been different
Q8 multi-step: several steps, each depending on the last
AMB too vague: no measure or year, so sharper questions must be offered first
OUT out of scope: a judgement, policy advice, a forecast, or outside the data

Routes:
R1 no AI: copy the published title of one of these series: {codes}
R2 code computes the answer from the data
R4 retrieval: quoted passages from the manuals
R4+R2 retrieval and code
R5>R2 a small model extracts the inputs, then code computes
R6 agent loop
clarify: offer sharper questions
escalate: refuse with the reason

The data cover the United States, the euro area and its 21 members, the
United Kingdom, China, India and Japan, for 2000 to 2025. Exports, imports
and spending components other than household consumption are not in the data.

Reply with the class and the route only, separated by a space, for example: Q2 R4"""

# The router needs a short reply and the same reply every time.
ROUTER_SETTINGS = dict(SETTINGS, temperature=0, num_predict=20)

ROUTER_REPLY = re.compile(r"\b(Q[1-8]|AMB|OUT)\b\s+(R4\+R2|R5>R2|R[1-6]|clarify|escalate)\b")


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


def run_model_router(bank, test, titles, ask=ask_model_with_details):
    """
    Route the bank and the test set with the model and save the replies.

    The example questions are left out of the bank's count, since the model
    is shown their labels.

    Example:
        run_model_router(bank, test, titles)
    """
    examples = [question for question in bank if question["id"] in EXAMPLE_IDS]
    rest = [question for question in bank if question["id"] not in EXAMPLE_IDS]
    records = route_with_model(rest, examples, titles, ask, "bank")
    records += route_with_model(test, examples, titles, ask, "test")
    save_answers(ROUTER_FILE, records)
    return records


# ---------------------------------------------------------------------------
# 12.5  Rules first, the model for the rest
# ---------------------------------------------------------------------------

# The rules that decide only because nothing else matched. A question that
# reaches one of these goes to the model instead (decided 5 November 2026,
# before the combined score was computed).
FALL_BACK_RULES = ["definition (default)", "outside the corpus"]


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


def report(label, records):
    counts = count_right(records)
    print(f"{label}: {counts['questions']} questions, class right {counts['class']}, "
          f"route right {counts['route']}, both {counts['both']}")
    for record in records:
        if not (record["class_right"] and record["route_right"]):
            print(f"      {record['id']}: labelled {record['class']} {record['route']}, "
                  f"gave {record['found_class']} {record['found_route']}")


def main():
    bank = load_passages(QUESTION_FILE)
    test = load_passages(TEST_FILE)
    titles = load_titles()
    words = corpus_words(load_corpus())
    report("12.3  Rules on the bank", route_bank(bank, words, titles))
    report("12.3  Rules on the test set", route_bank(test, words, titles))
    if "--model" in sys.argv:
        try:
            run_model_router(bank, test, titles)
        except urllib.error.URLError as error:
            print(f"Could not reach Ollama ({error.reason}). Start Ollama and run again.")
            return
    if ROUTER_FILE.exists():
        records = load_answers(ROUTER_FILE)
        report("12.4  Model on the bank (examples left out)",
               [r for r in records if r["test_set"] == "bank"])
        report("12.4  Model on the test set", [r for r in records if r["test_set"] == "test"])
        seconds = sum(r["seconds"] for r in records)
        print(f"      {len(records)} replies in {seconds / 60:.1f} minutes")
        combined = combine(route_bank(test, words, titles),
                           [r for r in records if r["test_set"] == "test"])
        report("12.5  Rules first, then the model, on the test set", combined)
        by_model = sum(r["decided_by"] == "model" for r in combined)
        print(f"      the model decided {by_model} of {len(combined)}")
    report("12.5.4  Revised rules on the bank", route_bank_revised(bank, words, titles))
    report("12.5.4  Revised rules on the test set (a training score)",
           route_bank_revised(test, words, titles))


if __name__ == "__main__":
    main()
