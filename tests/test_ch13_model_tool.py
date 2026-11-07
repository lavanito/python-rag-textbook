"""
Tests for Chapter 13 (calling the NNI model as a tool).

They check properties, never wording: the parts add up to the total, values
match the model's own data, ratings match the model's own rule, and flags
and messages appear where they should.
"""
from nni_model import dqr

from ragbook.ch12_routing import ECONOMIES
from ragbook.ch13_model_tool import (ECONOMY_CODES, MEASURES, SERIES, TOOL, call_model, show,
                                     load_edition)


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
