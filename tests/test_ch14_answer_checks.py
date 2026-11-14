"""
Tests for Chapter 14: checking answers.

What this checks
    The locked block (definitions, directions, comparisons, the question's
    premise), each check on the explanation (numbers, direction words,
    words code decides, remarks about the passages, citations, support,
    miscitation), the evidence code chooses, and the retry and fall-back.
    A stand-in replaces the language model, so no Ollama is needed.

Chapter: 14. Decisions: Lavan, 13 November 2026.
"""
import csv

import pytest
from nni_model import dqr

from ragbook.ch01_python_basics import load_passages
from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch11_prompts import ANSWERS_800_FILE, load_answers
from ragbook.ch12_routing import load_last_years
from ragbook.ch13_model_tool import MEASURES, PARAMETER_FILE, ToolResult, bank_model_questions
from ragbook.ch14_answer_checks import (
    CODE_WORDS, DEMONSTRATOR_WITHHELD, DIRECTION_WORDS, EXPLANATION_HEADING, NO_EXPLANATION,
    THRESHOLDS, WITHHELD, between, check_explanation, check_sentences, comparisons,
    concepts_named, defining_passages, definition_line, direction, evidence_for, explain,
    invented_numbers, load_definitions, load_graph, load_judgements, locked_block, overlap,
    passed, premise_line, problems_in_words, recheck_passage_answers, reply_page, revision,
    support_agreement, words_found)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


@pytest.fixture(scope="module")
def by_id(corpus):
    return {p["id"]: p for p in corpus}


@pytest.fixture(scope="module")
def definitions():
    return load_definitions()


@pytest.fixture(scope="module")
def expected():
    return {row["id"]: row for row in load_passages(PARAMETER_FILE)}


@pytest.fixture(scope="module")
def bank():
    return {q["id"]: q for q in bank_model_questions()}


def result(economy, year, value, measure="gni_per_head_ppp", edition="WDI 2026-10-08", band="Medium"):
    """A stand-in ToolResult."""
    return ToolResult(economy=economy, year=year, measure=measure, edition=edition, value=value,
                      shown=str(value), unit=MEASURES[measure]["unit"], dqr_band=band,
                      dqr_reason="test")


def stand_in(*replies):
    """A stand-in for the language model that gives these replies in turn."""
    queue = list(replies)

    def ask(messages, options):
        ask.calls.append(messages)
        return {"answer": queue.pop(0), "prompt_tokens": 1, "reply_tokens": 1, "seconds": 0.1}
    ask.calls = []
    return ask


# 14.2  The locked block -----------------------------------------------------

def test_every_measure_with_figures_has_an_approved_definition(definitions, by_id):
    assert set(definitions) == set(MEASURES)
    for row in definitions.values():
        assert row["means"]
        assert all(passage_id in by_id for passage_id in row["passages"])


def test_unpaid_work_is_named_wherever_lavan_agreed(definitions):
    clause = "unpaid work at home, such as caring, cooking and cleaning, most of it done by women"
    named = {m for m, row in definitions.items() if clause in row["leaves_out"]}
    assert named == set(MEASURES) - {"population", "spending_components", "trend_gap"}


def test_definition_line_gives_meaning_what_is_left_out_and_passages(definitions):
    line = definition_line("gni", definitions)
    assert "What it means: Gross national income" in line
    assert "What it leaves out:" in line
    assert line.endswith("See esa10-8.94.")


def test_direction_uses_the_threshold_for_the_band():
    assert direction(-0.3, dqr.MEDIUM) == "same"
    assert direction(0.6, dqr.HIGH) == "up"
    assert direction(-4.9, dqr.LOW) == "same"
    assert direction(-5.0, dqr.LOW) == "down"
    assert THRESHOLDS[dqr.HIGH] < THRESHOLDS[dqr.MEDIUM] < THRESHOLDS[dqr.LOW]


def test_revision_states_the_direction_and_size():
    # q4-01: India 2016, 5710 to 5570, -2.5 log points. Rated Low, that is
    # within the threshold (5), so "about the same"; rated Medium, "revised down".
    low = revision(result("IND", 2016, 5710, edition="WDI 2024-03", band="Low"),
                   result("IND", 2016, 5570, band="Low"))
    assert low["direction"] == "same"
    assert "about -140" in low["text"]
    medium = revision(result("IND", 2016, 5710, edition="WDI 2024-03"),
                      result("IND", 2016, 5570))
    assert medium["direction"] == "down"
    assert "revised down" in medium["text"]


def test_gap_by_ratio_in_log_points_over_a_span():
    uk = [result("GBR", 2007, 35360), result("GBR", 2024, 62220)]
    us = [result("USA", 2007, 48330), result("USA", 2024, 85270)]
    item = between(uk, us)
    assert item["kind"] == "gap"
    assert item["direction"] == "same"           # 0.3 log points, below Medium's 2
    assert "73.2% of its level" in item["text"] and "73.0% of its level" in item["text"]
    assert "the gap was about the same" in item["text"]


def test_comparisons_skip_economies_in_the_older_edition():
    groups = {("CHN", "gdp_per_head_ppp", "latest"): [result("CHN", 2022, 23028, "gdp_per_head_ppp")],
              ("IND", "gdp_per_head_ppp", "latest"): [result("IND", 2022, 8941, "gdp_per_head_ppp")],
              ("CHN", "gdp_per_head_ppp", "archive"): [result("CHN", 2022, 21483, "gdp_per_head_ppp")],
              ("IND", "gdp_per_head_ppp", "archive"): [result("IND", 2022, 8400, "gdp_per_head_ppp")]}
    kinds = [item["kind"] for item in comparisons(groups)]
    assert kinds.count("revision") == 2
    assert kinds.count("level") == 1


def test_premise_line_names_a_false_premise_f16():
    rise = [{"kind": "revision", "direction": "up"}]
    assert premise_line("Why did China's GDP per head fall?", rise) == \
        "The question assumes a fall; the figures show a rise."
    assert premise_line("How did China's GDP per head change?", rise) is None


def test_fallen_behind_is_a_comparison_not_a_fall():
    found = [{"kind": "time", "direction": "up"}, {"kind": "gap", "direction": "same"}]
    assert premise_line("Has the United Kingdom fallen behind the United States?", found) is None
    gained = [{"kind": "gap", "direction": "up"}]
    assert "fell behind" in premise_line("Has the UK fallen behind the US?", gained)


def test_locked_block_for_q4_02_corrects_the_premise(bank, expected, definitions):
    locked = locked_block(bank["q4-02"]["question"], expected["q4-02"], load_last_years(), definitions)
    assert locked["text"].startswith("The question assumes a fall; the figures show a rise.")
    assert sum("revised up" in line for line in locked["comparisons"]) == 2
    assert "What it leaves out" in locked["text"]


def test_locked_block_for_q5_02_says_about_the_same(bank, expected, definitions):
    locked = locked_block(bank["q5-02"]["question"], expected["q5-02"], load_last_years(), definitions)
    assert locked["premise"] is None
    assert any("the gap was about the same" in line for line in locked["comparisons"])


# 14.3  Numbers ----------------------------------------------------------------

def test_invented_numbers_ignore_passage_ids_f15():
    assert invented_numbers("It fell by 140 [esa10-8.94].", "5710 and 5570") == ["140"]
    assert invented_numbers("See [esa10-8.94] and [sna25-A4.10].", "") == []


# 14.4  Direction words and words code decides -------------------------------

def test_direction_words_are_found():
    text = "Prices rose, output fell, the gap narrowed and India caught up; revised down."
    assert words_found(DIRECTION_WORDS, text) == ["caught up", "fell", "narrowed", "revised down", "rose"]


def test_known_misses_and_false_alarms_of_the_word_list():
    # Misses: comparisons without the listed words (14.4 lists them).
    assert words_found(DIRECTION_WORDS, "Income is more than in 2010 and above the trend.") == []
    # False alarm: a negation still contains the word.
    assert words_found(DIRECTION_WORDS, "Neither fell.") == ["fell"]


def test_words_that_code_decides_f17_f18():
    text = "The figure is estimated and a proxy. DQR Medium. Passed to an analyst."
    assert words_found(CODE_WORDS, text) == ["dqr", "estimated", "passed to an analyst", "proxy"]


# 14.5  Citations, support and miscitation -----------------------------------

def test_strict_citation_rule(by_id):
    evidence = [by_id["ppp23-1.31"]]
    problems = check_sentences("PPPs are statistical constructs [ppp23-1.31]. They are useful.", evidence)
    assert problems == ["Sentence 2 has no passage id: 'They are useful.'"]
    problems = check_sentences("PPPs are statistical constructs [esa10-11.2.7].", evidence)
    assert problems == ["Sentence 1 cites esa10-11.2.7, which you were not given."]


def test_support_is_word_overlap_with_the_passage_text_only(by_id):
    assert overlap("PPPs are statistical constructs [ppp23-1.31].", by_id["ppp23-1.31"]) == 1.0
    # The scope note says GDI is not real gross domestic income; the BEA text does not.
    assert overlap("real gross domestic income", by_id["bea-ch2-ndp-gni"]) < \
        overlap("real gross domestic income", {"text": by_id["bea-ch2-ndp-gni"]["scope_note"]})


def test_miscitation_is_found_lavan_row_7(by_id):
    sentence = ("The theory of purchasing power parity assumes that all goods are internationally "
                "tradable and that currency demand is driven solely by trade, but in reality, these "
                "assumptions do not hold. [ppp23-1.17]")
    evidence = [by_id[i] for i in ("ppp23-1.14", "ppp23-1.13", "ppp23-1.17")]
    problems = check_sentences(sentence, evidence)
    assert any("its words are in ppp23-1.13" in p for p in problems)


def test_first_sentence_must_cite_the_defining_passage(by_id):
    evidence = [by_id["sna08-15.187"], by_id["ppp23-1.13"]]
    problems = check_sentences("PPP theory needs arbitrage [ppp23-1.13].", evidence,
                               must_cite_first=["sna08-15.187"])
    assert "Sentence 1 must cite the defining passage: sna08-15.187." in problems


def test_no_explanation_passes_and_remarks_about_passages_fail(by_id):
    locked = {"text": ""}
    assert passed(check_explanation(NO_EXPLANATION, "q", locked, []))
    checks = check_explanation("The passage does not define it [ppp23-1.13].", "q", locked,
                               [by_id["ppp23-1.13"]])
    assert checks["passage_talk"] == ["passage"]


def test_chapter_11_answers_rechecked_without_a_model(corpus):
    found = recheck_passage_answers(load_answers(ANSWERS_800_FILE), corpus)
    assert len(found) == 32
    assert any("esa10-11.2.7" in p for p in found["q2-31"])
    assert found["q2-10"] == []                  # every sentence cited and supported


def test_lavans_judgements_are_kept_and_scored(corpus):
    judgements = load_judgements()
    assert len(judgements) == 20
    assert sum(row["support"] == "Supported" for row in judgements) == 19
    rows = support_agreement(judgements, load_answers(ANSWERS_800_FILE), corpus)
    failing = {row["row"] for row in rows if not row["code_passes"]}
    assert {"7", "15"} <= failing                # both miscited


# 14.6  Evidence, retry and fall-back ---------------------------------------

def test_concepts_named_finds_the_longest_name_first():
    things, triplets = load_graph()
    assert concepts_named("What are the terms of trade?", things) == ["terms_of_trade"]
    assert defining_passages(["terms_of_trade"], triplets) == (["sna08-15.187"], [])


def test_evidence_respects_the_licence_filter_and_the_cap(bank, expected, definitions, corpus):
    question = bank["q5-03"]
    locked = locked_block(question["question"], expected["q5-03"], load_last_years(), definitions)
    graph = load_graph()
    evidence, _, _ = evidence_for(question["question"], locked, question["route"], question["class"],
                                  corpus, graph, definitions)
    assert len(evidence) <= 5
    commercial, _, _ = evidence_for(question["question"], locked, question["route"], question["class"],
                                    corpus, graph, definitions, use_mode="commercial")
    assert all(p["licence_class"] == "open" for p in commercial)


def test_lookups_get_no_explanation():
    ask = stand_in()
    assert explain("q", "Q1", {"text": ""}, [], [], ask) == {"status": "lookup", "shown": None,
                                                             "attempts": []}
    assert ask.calls == []


def test_one_retry_names_the_problems_then_passes(by_id):
    evidence = [by_id["ppp23-1.31"]]
    ask = stand_in("PPPs rose by 140 [ppp23-1.31].", "PPPs are statistical constructs [ppp23-1.31].")
    outcome = explain("How precise are PPPs?", "Q3", {"text": ""}, evidence, [], ask)
    assert outcome["status"] == "passed on retry"
    retry_note = ask.calls[1][-1]["content"]
    assert "140" in retry_note and "rose" in retry_note


def test_two_failures_drop_the_explanation(by_id):
    locked = {"text": "Figures (written by code)"}
    ask = stand_in("It fell.", "It fell again.")
    outcome = explain("q", "Q3", locked, [by_id["ppp23-1.31"]], [], ask)
    assert outcome["status"] == "dropped"
    page = reply_page(locked, outcome)
    assert WITHHELD in page and DEMONSTRATOR_WITHHELD in page
    assert EXPLANATION_HEADING not in page


def test_problems_in_words_for_the_retry():
    lines = problems_in_words({"numbers": ["140"], "directions": ["fell"], "code_words": [],
                               "passage_talk": [], "citations": ["Sentence 1 has no passage id: 'x'"]})
    assert lines[0] == "It contains numbers not in the locked block: 140."
    assert lines[-1].startswith("Sentence 1")
