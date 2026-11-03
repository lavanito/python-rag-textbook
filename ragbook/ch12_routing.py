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
    Chapter 3 (QUESTION_FILE). Python's csv, re and pathlib modules.

Run the worked example
    python -m ragbook.ch12_routing
        Routes the bank and prints the questions the rules route wrongly.
        Needs no model.
"""
import csv
import re
from pathlib import Path

from ragbook.ch01_python_basics import load_passages, split_into_words
from ragbook.ch02_minimal_pipeline import load_corpus, topic_words
from ragbook.ch03_keyword_search import QUESTION_FILE

TITLE_FILE = Path(__file__).parent.parent / "data" / "series" / "wdi_titles.csv"

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


def main():
    questions = load_passages(QUESTION_FILE)
    records = route_bank(questions, corpus_words(load_corpus()), load_titles())
    counts = count_right(records)
    print(f"12.3  {counts['questions']} questions: class right {counts['class']}, "
          f"route right {counts['route']}, both {counts['both']}")
    for record in records:
        if not (record["class_right"] and record["route_right"]):
            print(f"  {record['id']}: labelled {record['class']} {record['route']}, "
                  f"rules gave {record['found_class']} {record['found_route']} "
                  f"({record['rule']})")


if __name__ == "__main__":
    main()
