"""
Tests for Chapter 13 (calling the NNI model as a tool).

They check properties, never wording: the parts add up to the total, values
match the model's own data, ratings match the model's own rule, and flags
and messages appear where they should.
"""
import json

from nni_model import dqr

from ragbook.ch01_python_basics import load_passages
from ragbook.ch12_routing import ECONOMIES, load_last_years
from ragbook.ch13_model_tool import (ECONOMY_CODES, MEASURES, PARAMETER_EXAMPLES,
                                     PARAMETER_FILE, PARAMETER_SCHEMA, SERIES, TOOL, call_model,
                                     fields_right, load_edition, model_questions, plan_calls,
                                     read_model_reply, read_parameters_with_model,
                                     read_with_rules, resolve_year, score_parameters, show)


def test_the_six_economies_match_the_router():
    assert set(ECONOMY_CODES) == set(ECONOMIES)


def test_a_value_lookup_returns_the_models_own_value():
    reply = call_model("United Kingdom", 2024, "gni_per_head_ppp")
    expected = load_edition("latest").get("GBR", SERIES["gni_per_head_ppp"], 2024)
    assert reply.value == expected
    assert reply.unit and reply.source and reply.edition
    assert reply.message is None


def test_the_rating_follows_the_models_rule():
    reply = call_model("India", 2022, "population")
    expected = dqr.rate("P2", "IND", inputs=["population"])
    assert (reply.dqr_band, reply.dqr_reason) == (expected.name, expected.reason)
    assert reply.shown == f"{reply.value:.0f}"     # a count: no decimal places


def test_the_parts_add_up_to_the_total():
    for economy in ECONOMY_CODES:
        reply = call_model(economy, 2015, "nni_growth")
        parts = reply.parts["C1a"] + reply.parts["C2"] + reply.parts["C4"]
        assert abs(parts - reply.value) < 1e-9, economy


def test_years_after_2021_are_flagged_estimated_and_at_most_medium():
    reply = call_model("Japan", 2024, "nni_growth")
    assert any(flag.startswith("estimated") for flag in reply.flags)
    assert reply.dqr_band in ("Medium", "Low")


def test_a_break_is_flagged_and_rated_low():
    reply = call_model("India", 2022, "nni_growth")
    assert any(flag.startswith("break") for flag in reply.flags)
    assert reply.dqr_band == "Low"


def test_a_euro_area_member_is_rated_as_the_euro_area():
    # Assumption agreed by Lavan, 6 November 2026: members follow one standard.
    for measure in ["population", "gni_per_head_ppp"]:
        member = call_model("IRL", 2024, measure)
        euro_area = call_model("euro area", 2024, measure)
        assert member.value is not None
        assert member.dqr_band == euro_area.dqr_band
        assert member.dqr_reason.endswith(euro_area.dqr_reason)


def test_the_two_editions_give_different_values_for_the_same_year():
    latest = call_model("India", 2016, "gni_per_head_ppp", "latest")
    archive = call_model("India", 2016, "gni_per_head_ppp", "archive")
    assert latest.edition != archive.edition
    assert latest.value != archive.value


def test_missing_values_give_a_message_not_a_number():
    for args in [("Switzerland", 2024, "population"),      # economy not in the data
                 ("Japan", 2030, "nni_growth"),             # beyond the data
                 ("India", 2024, "exports")]:               # measure not in the model
        reply = call_model(*args)
        assert reply.value is None and reply.shown is None
        assert reply.message, args


def test_the_tool_description_lists_every_measure_and_economy():
    parameters = TOOL["function"]["parameters"]
    assert parameters["properties"]["measure"]["enum"] == list(MEASURES)
    assert set(ECONOMY_CODES) <= set(parameters["properties"]["economy"]["enum"])
    assert set(parameters["required"]) == {"economy", "year", "measure"}


def test_the_euro_area_has_gni_per_head_at_ppp():
    # Built by the model from its 21 members (agreed by Lavan, 6 November 2026).
    reply = call_model("euro area", 2024, "gni_per_head_ppp")
    assert reply.value is not None and reply.dqr_band


def test_counts_have_no_decimal_places_at_any_band():
    # Lavan, 7 November 2026: population is shown as a whole number.
    high = call_model("IRL", 2024, "population")
    assert high.dqr_band == "High" and "." not in high.shown
    assert show(1234.6, dqr.LOW, count=True) == "about 1235"
    assert show(2.4567, dqr.HIGH) == "2.5"            # other values keep the rule


# 13.4  Reading the parameters. Stand-in tests: no language model is run.

EXPECTED = {row["id"]: row for row in load_passages(PARAMETER_FILE)}
LAST_YEARS = load_last_years()


def test_every_question_routed_to_code_has_expected_parameters():
    ids = [question["id"] for question in model_questions()]
    assert len(ids) == 28
    assert set(ids) == set(EXPECTED)


def test_the_examples_are_not_scored_questions():
    asked = {question["question"] for question in model_questions()}
    assert not asked & {example for example, _ in PARAMETER_EXAMPLES}


def test_the_reply_shape_offers_every_measure():
    choices = PARAMETER_SCHEMA["properties"]["measures"]["items"]["enum"]
    assert choices == list(MEASURES) + ["other"]


def test_the_rules_read_a_relative_year():
    found = read_with_rules("What drove growth in real NNI per head in Japan last year?")
    assert found["economies"] == ["JPN"] and found["years"] == ["latest"]


def test_a_reply_that_is_not_json_counts_as_wrong():
    assert read_model_reply("Japan, 2024") is None
    assert not any(fields_right(None, EXPECTED["q1-01"]).values())


def test_a_stand_in_model_that_copies_the_expected_answers_scores_28():
    def stand_in(messages, schema):
        question = messages[-1]["content"]
        row = next(EXPECTED[q["id"]] for q in model_questions() if q["question"] == question)
        reply = {name: row[name] for name in ["economies", "years", "measures", "editions", "change"]}
        return {"answer": json.dumps(reply), "prompt_tokens": 0, "reply_tokens": 0, "seconds": 0}

    questions = model_questions()
    replies = {r["id"]: r for r in read_parameters_with_model(questions, ask=stand_in)}
    records = score_parameters(questions, EXPECTED, lambda q: read_model_reply(replies[q["id"]]["reply"]))
    assert sum(r["all_right"] for r in records) == 28


def test_latest_comes_from_the_ragged_edge():
    assert resolve_year("latest-5", 2024) == 2019
    calls, problems = plan_calls(EXPECTED["q3-01"], LAST_YEARS)
    assert calls == [("JPN", LAST_YEARS[("JPN", "latest")], "nni_growth", "latest")] and not problems


def test_a_span_of_twenty_years_gives_twenty_years_of_growth_each():
    calls, _ = plan_calls(EXPECTED["t-22"], LAST_YEARS)
    assert len(calls) == 2 * 20


def test_a_year_beyond_the_data_gives_a_problem_not_a_call():
    parameters = dict(EXPECTED["q1-01"], economies=["JPN"], years=["2025"])
    calls, problems = plan_calls(parameters, LAST_YEARS)
    assert calls == [] and problems


def test_a_measure_not_in_the_model_gives_a_problem():
    calls, problems = plan_calls(EXPECTED["t-24"], LAST_YEARS)
    assert calls == [] and problems


def test_a_member_without_its_own_last_year_uses_the_euro_areas():
    # The archive edition has no euro area, so Germany's 2016 revision cannot be compared.
    parameters = dict(EXPECTED["q4-01"], economies=["DEU"])
    calls, problems = plan_calls(parameters, LAST_YEARS)
    assert [c for c in calls if c[3] == "archive"] == [] and problems
    assert [c for c in calls if c[3] == "latest"] == [("DEU", 2016, "gni_per_head_ppp", "latest")]
