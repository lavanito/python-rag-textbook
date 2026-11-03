"""
Tests for Chapter 12: keyword routing.

None needs the model. The rules were written with the bank in view, so the
count on the bank is a training score, not a test of new questions.
"""
from ragbook.ch01_python_basics import load_passages
from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import QUESTION_FILE
from ragbook.ch12_routing import (
    count_right, corpus_words, economies_named, load_titles, route_bank, route_question,
)

QUESTIONS = load_passages(QUESTION_FILE)
WORDS = corpus_words(load_corpus())
TITLES = load_titles()


def route(question):
    return route_question(question, WORDS, TITLES)


def test_titles():
    assert len(TITLES) == 17
    assert TITLES["NY.GNP.PCAP.PP.CD"] == "GNI per capita, PPP (current international $)"


def test_economies_are_whole_words():
    assert economies_named("Is China catching up with the United States?") == ["United States", "China"]
    assert economies_named("Can US and euro area growth be compared?") == ["United States", "euro area"]
    assert economies_named("Why is this so, because of prices?") == []


def test_refusals_come_first():
    assert route("What will China's GDP be in 2030?") == ("OUT", "escalate", "forecast")
    assert route("Should the Bank of England cut interest rates?") == ("OUT", "escalate", "policy advice")
    assert route("Is the euro area's growth sustainable?") == ("OUT", "escalate", "judgement")
    # "Should" alone is not advice: this is a definition question.
    assert route("Should annual price and volume indices be chained?")[:2] == ("Q2", "R4")


def test_series_name_is_r1_only_for_a_known_code():
    assert route("What is the exact name of the World Bank series SP.POP.TOTL?") == ("Q1", "R1", "series name")
    assert route("What is the exact name of the World Bank series XX.NOT.REAL?")[1] != "R1"


def test_vague_unless_a_year_is_given():
    assert route("Is the UK falling behind?")[:2] == ("AMB", "clarify")
    assert route("Has the United Kingdom fallen behind the United States since 2007?")[:2] == ("Q5", "R2")


def test_outside_the_corpus_only_when_no_other_rule_matches():
    assert route("What is the best restaurant in Dublin?") == ("OUT", "escalate", "outside the corpus")
    assert route("What is double deflation?") == ("Q2", "R4", "definition (default)")


def test_bank_score():
    records = route_bank(QUESTIONS, WORDS, TITLES)
    # Every question is routed as labelled. q5-04 was relabelled Q2, R4 on
    # 3 November 2026; as Q5 it was the one miss, since it names no economy.
    assert count_right(records) == {"questions": 56, "class": 56, "route": 56, "both": 56}
