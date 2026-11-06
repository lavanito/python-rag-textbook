"""
Tests for Chapter 12: keyword routing.

None needs the model. The rules were written with the bank in view, so the
count on the bank is a training score, not a test of new questions.
"""
from ragbook.ch01_python_basics import load_passages
from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import QUESTION_FILE
from ragbook.ch12_routing import (
    CLASSES, ESCALATION_REASONS, EXAMPLE_IDS, FALL_BACK_RULES, combine, escalation_message, route_bank_revised, route_question_revised, ROUTER_FILE, ROUTER_SETTINGS, ROUTES, TEST_FILE, count_right,
    corpus_words, economies_named, load_titles, read_router_reply, route_bank, route_question,
    route_with_model, router_messages,
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


def test_held_out_score_before_any_rule_change():
    # Lavan's 32 questions of 5 November 2026, scored with the rules as they
    # stood (commit a83ba07). This records the first score; later rule changes
    # are scored separately and do not change this test's file or rules.
    held_out = load_passages(QUESTION_FILE.parent / "routing_test_5_november.jsonl")
    assert len(held_out) == 32
    assert sum(question["class"] == "OUT" for question in held_out) == 5


def test_held_out_rules_score():
    # The first score on the test set, rules unchanged (5 November 2026).
    held_out = load_passages(TEST_FILE)
    assert count_right(route_bank(held_out, WORDS, TITLES)) == {
        "questions": 32, "class": 19, "route": 20, "both": 19}


def test_labels_use_the_agreed_codes():
    for question in QUESTIONS + load_passages(TEST_FILE):
        assert question["class"] in CLASSES, question["id"]
        assert question["route"] in ROUTES, question["id"]


def test_examples_cover_every_class_and_are_not_in_the_test_set():
    examples = [question for question in QUESTIONS if question["id"] in EXAMPLE_IDS]
    assert len(examples) == len(EXAMPLE_IDS)
    assert {question["class"] for question in examples} == set(CLASSES)
    test_texts = {question["question"] for question in load_passages(TEST_FILE)}
    assert not test_texts & {question["question"] for question in examples}


def test_router_messages():
    examples = [{"question": "What is GDI?", "class": "Q2", "route": "R4"}]
    messages = router_messages("What is NDP?", examples, TITLES)
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert "SP.POP.TOTL" in messages[0]["content"]
    assert messages[2]["content"] == "Q2 R4"
    assert messages[-1]["content"] == "What is NDP?"


def test_read_router_reply():
    assert read_router_reply("Q6 R4+R2") == ("Q6", "R4+R2")
    assert read_router_reply("Class: Q7 R5>R2.") == ("Q7", "R5>R2")
    assert read_router_reply("AMB clarify") == ("AMB", "clarify")
    assert read_router_reply("I think this is a definition") == ("none", "none")


def test_router_settings():
    assert ROUTER_SETTINGS["temperature"] == 0
    assert ROUTER_SETTINGS["num_predict"] == 20
    assert ROUTER_SETTINGS["seed"] == 42


def test_model_router_with_a_stand_in():
    def stand_in(messages, options):
        return {"answer": "Q2 R4", "prompt_tokens": 900, "reply_tokens": 4,
                "seconds": 1.5, "done_reason": "stop"}
    records = route_with_model(QUESTIONS[:3], [], TITLES, stand_in, "bank")
    assert [r["found_class"] for r in records] == ["Q2", "Q2", "Q2"]
    assert all(r["class_right"] for r in records)


def test_saved_model_router_replies():
    # Lavan's laptop run of 5 November 2026: 77 replies in 3.3 minutes.
    import pytest
    if not ROUTER_FILE.exists():
        pytest.skip("no saved router replies yet")
    from ragbook.ch11_prompts import load_answers
    records = load_answers(ROUTER_FILE)
    bank = [r for r in records if r["test_set"] == "bank"]
    test = [r for r in records if r["test_set"] == "test"]
    assert (len(bank), len(test)) == (45, 32)
    assert not {r["id"] for r in bank} & set(EXAMPLE_IDS)
    assert all(r["found_class"] != "none" for r in records)
    assert count_right(bank) == {"questions": 45, "class": 39, "route": 39, "both": 37}
    assert count_right(test) == {"questions": 32, "class": 17, "route": 17, "both": 15}
    # On the test set the rules and the model miss mostly different questions.
    rules = {r["id"]: r for r in route_bank(load_passages(TEST_FILE), WORDS, TITLES)}
    right = lambda r: r["class_right"] and r["route_right"]
    both_wrong = [r["id"] for r in test if not right(r) and not right(rules[r["id"]])]
    assert both_wrong == ["t-02", "t-03", "t-21", "t-26", "t-28", "t-31", "t-32"]


def test_combined_router_on_the_test_set():
    # Rules first; the model decides only where a fall-back rule decided.
    # Rule fixed on 5 November 2026 before the score was computed.
    import pytest
    if not ROUTER_FILE.exists():
        pytest.skip("no saved router replies yet")
    from ragbook.ch11_prompts import load_answers
    assert FALL_BACK_RULES == ["definition (default)", "outside the corpus"]
    model = [r for r in load_answers(ROUTER_FILE) if r["test_set"] == "test"]
    combined = combine(route_bank(load_passages(TEST_FILE), WORDS, TITLES), model)
    assert sum(r["decided_by"] == "model" for r in combined) == 21
    assert count_right(combined) == {"questions": 32, "class": 18, "route": 17, "both": 16}


def test_revised_rules():
    def revised(question):
        return route_question_revised(question, WORDS, TITLES)
    assert revised("https://data.worldbank.org/indicator/SP.POP.TOTL") == ("Q1", "R1", "series code")
    assert revised("What does the code XX.NOT.REAL mean?")[:2] == ("OUT", "escalate")
    assert revised("How does the UK compare with Norway?")[2] == "economy not in the data"
    assert revised("What was GDP in Japan in 2027?")[2] == "beyond the data"
    assert revised("What was Irish GNI in 2010?")[:2] == ("Q1", "R2")
    # The first-round rules still decide everything else.
    assert revised("What is double deflation?") == ("Q2", "R4", "definition (default)")


def test_revised_rules_scores():
    # Second round (5 November 2026). The bank is unchanged at 56 of 56; the
    # test-set score is a training score, since the rules were revised after
    # reading its misses.
    assert count_right(route_bank_revised(QUESTIONS, WORDS, TITLES))["both"] == 56
    records = route_bank_revised(load_passages(TEST_FILE), WORDS, TITLES)
    assert count_right(records) == {"questions": 32, "class": 26, "route": 26, "both": 26}
    wrong = [r["id"] for r in records if not (r["class_right"] and r["route_right"])]
    assert wrong == ["t-05", "t-08", "t-17", "t-19", "t-28", "t-31"]


def test_escalation_messages():
    # Every rule that escalates has a reason and a message (6 November 2026).
    escalating = {r["rule"] for r in route_bank_revised(QUESTIONS + load_passages(TEST_FILE), WORDS, TITLES)
                  if r["found_route"] == "escalate"}
    assert escalating <= set(ESCALATION_REASONS)
    reason, message = escalation_message("beyond the data", TITLES)
    assert reason == "beyond the data" and "end in 2025" in message
    reason, message = escalation_message("economy not in the data", TITLES)
    assert reason == "economy not in the data" and "India and Japan" in message
    assert "17 series" in escalation_message("series not in the data", TITLES)[1]
