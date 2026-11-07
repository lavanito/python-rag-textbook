"""
Tests for Chapter 13 (calling the NNI model as a tool).

They check properties, never wording: the parts add up to the total, values
match the model's own data, ratings match the model's own rule, and flags
and messages appear where they should.
"""
import json
import math

from nni_model import dqr
from nni_model.data import EURO_MEMBERS, Snapshot
from nni_model.decomposition import NNIDecomposition

from ragbook.ch01_python_basics import load_passages
from ragbook.ch11_prompts import load_answers
from ragbook.ch12_routing import ECONOMIES, load_last_years
from ragbook.ch13_model_tool import (ECONOMY_CODES, GAPS, MEASURES, PARAMETER_REPLIES, PARAMETER_EXAMPLES,
                                     PARAMETER_FILE, PARAMETER_SCHEMA, SERIES, TOOL, call_model,
                                     fields_right, load_edition, model_questions, plan_calls,
                                     read_model_reply, read_parameters_with_model,
                                     read_with_rules, resolve_year, score_parameters, show,
                                     escalate, household_ppp, trend_gap)


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
    assert choices == list(MEASURES) + list(GAPS) + ["other"]


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


def test_a_span_fetches_every_year_of_a_level():
    # q5-02 (Lavan, 7 November 2026): GNI per head at PPP every year from 2007.
    calls, _ = plan_calls(EXPECTED["q5-02"], LAST_YEARS)
    last = min(LAST_YEARS[("GBR", "latest")], LAST_YEARS[("USA", "latest")])
    assert len(calls) == 2 * (last - 2007 + 1)



# Measures added from the gap table (Lavan, 7 November 2026).

def test_real_gdp_growth_is_growth_per_head_plus_population_growth():
    s = load_edition("latest")
    for economy in ECONOMY_CODES:
        code = ECONOMY_CODES[economy]
        growth = call_model(economy, 2015, "real_gdp_growth").value
        per_head = NNIDecomposition(s, code).year(2015).c4
        population = 100 * math.log(s.get(code, "SP.POP.TOTL", 2015) / s.get(code, "SP.POP.TOTL", 2014))
        assert abs(growth - (per_head + population)) < 1e-9, economy


def test_real_nni_per_head_level_grows_as_the_decomposition_says():
    for economy in ECONOMY_CODES:
        old = call_model(economy, 2014, "real_nni_per_head_ppp").value
        new = call_model(economy, 2015, "real_nni_per_head_ppp").value
        growth = call_model(economy, 2015, "nni_growth").value
        assert abs(100 * math.log(new / old) - growth) < 1e-9, economy


def test_real_nni_per_head_in_2021_is_nni_over_household_ppp_over_population():
    s = load_edition("latest")
    level = NNIDecomposition(s, "USA").levels(2021)
    expected = (level.nni_to_gdp * s.get("USA", "NY.GDP.MKTP.CN", 2021)
                / s.get("USA", "PA.NUS.PRVT.PP", 2021) / level.population)
    assert abs(call_model("USA", 2021, "real_nni_per_head_ppp").value / expected - 1) < 1e-12


def test_the_euro_area_household_ppp_weights_members_by_consumption():
    s = load_edition("latest")
    euros = sum(s.get(m, "NE.CON.PRVT.CN", 2021) for m in EURO_MEMBERS)
    dollars = sum(s.get(m, "NE.CON.PRVT.CN", 2021) / s.get(m, "PA.NUS.PRVT.PP", 2021)
                  for m in EURO_MEMBERS)
    assert household_ppp(s, "EA21", 2021) == euros / dollars


def test_gdp_per_head_at_ppp_differs_between_editions_for_china():
    latest = call_model("China", 2016, "gdp_per_head_ppp", "latest")
    archive = call_model("China", 2016, "gdp_per_head_ppp", "archive")
    assert latest.value and archive.value and latest.value != archive.value


def test_a_steady_trend_gives_no_gap():
    s = Snapshot("steady")
    for year in range(2000, 2021):
        s.set("XXX", "NY.GDP.MKTP.KN", year, 100 * 1.02 ** (year - 2000))
        s.set("XXX", "SP.POP.TOTL", year, 1.0)
    gap, _ = trend_gap(s, "XXX", 2020)
    assert abs(gap) < 1e-9


def test_a_proxy_is_flagged_and_rated_low():
    for economy, year, measure in [("United Kingdom", 2023, "employment_rate"),
                                   ("United States", 2024, "spending_components"),
                                   ("United Kingdom", 2025, "trend_gap")]:
        reply = call_model(economy, year, measure)
        assert reply.value is not None, measure
        assert reply.dqr_band == "Low" and any(f.startswith("proxy") for f in reply.flags)


def test_a_figure_not_in_the_data_names_the_best_data_and_escalates():
    for question in ["t-24", "t-30"]:
        calls, problems = plan_calls(EXPECTED[question], LAST_YEARS)
        assert calls == [] and problems and escalate(calls, problems)


def test_an_exact_figure_is_not_escalated():
    calls, problems = plan_calls(EXPECTED["q1-01"], LAST_YEARS)
    assert calls and not escalate(calls, problems)


def test_the_saved_model_replies_score_as_reported():
    # Lavan ran qwen3:4b-instruct on 7 November 2026: 28 replies in 5.6 minutes.
    replies = {r["id"]: r for r in load_answers(PARAMETER_REPLIES)}
    assert set(replies) == set(EXPECTED)
    assert all(read_model_reply(r["reply"]) is not None for r in replies.values())
    records = score_parameters(model_questions(), EXPECTED,
                               lambda q: read_model_reply(replies[q["id"]]["reply"]))
    assert sum(r["all_right"] for r in records) == 12


def test_round_two_names_every_measure_with_a_hint():
    from ragbook.ch13_model_tool import SECOND_HINTS, parameter_messages
    system = parameter_messages("What is GDI?", version="second")[0]["content"]
    assert all(f"- {name}:" in system for name in SECOND_HINTS)
    assert "deflator mix" in system and "level" in system
    assert parameter_messages("What is GDI?")[0]["content"] != system   # round 1 kept as it was


def test_the_new_questions_use_known_labels():
    from ragbook.ch13_model_tool import NEW_QUESTION_FILE
    rows = load_passages(NEW_QUESTION_FILE)
    assert len(rows) == 20
    for row in rows:
        assert set(row["measures"]) <= set(MEASURES) | set(GAPS) | {"other"}, row["id"]
        assert all(economy_ok in ECONOMY_CODES.values() or len(economy_ok) == 3
                   for economy_ok in row["economies"]), row["id"]
        assert set(row["editions"]) <= {"latest", "archive"} and row["editions"], row["id"]


def test_round_two_scores_as_reported():
    # Lavan's run of 7 November 2026: 68 replies in 13.9 minutes.
    from ragbook.ch13_model_tool import NEW_QUESTION_FILE, SECOND_REPLIES, same_calls
    records = load_answers(SECOND_REPLIES)
    new = load_passages(NEW_QUESTION_FILE)
    new_key = {row["id"]: row for row in new}
    scores = {}
    for version, questions, key in [("second", model_questions(), EXPECTED),
                                    ("first", new, new_key), ("second", new, new_key)]:
        replies = {r["id"]: r for r in records if r["version"] == version}
        found = {q["id"]: read_model_reply(replies[q["id"]]["reply"]) for q in questions}
        strict = sum(all(fields_right(found[i], key[i]).values()) for i in found)
        loose = sum(same_calls(found[i], key[i], LAST_YEARS) for i in found)
        scores[(version, len(questions))] = (strict, loose)
    assert scores == {("second", 28): (15, 17), ("first", 20): (2, 6), ("second", 20): (6, 9)}
