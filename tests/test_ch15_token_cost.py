"""
Tests for Chapter 15: monitoring token cost.

What this checks
    Counting tokens and seconds from saved runs, grouping by route, the
    cost of retries, the user's two settings, the trace (one line per step,
    the steps with no model reproducing the saved run), the review list
    and the score table. No language model is called.

Chapter: 15. Decisions: the horizontal domain expert, 16 November 2026.
"""
import pytest

from ragbook.ch11_prompts import ANSWER_FOLDER, load_answers
from ragbook.ch14_answer_checks import RERUN_FILE
from ragbook.ch15_token_cost import (
    NO_MODEL, RUNS, cost, cost_by_role, cost_by_route, cost_of_runs, count_by_check,
    failed_checks, model_calls, questions_by_id, retry_cost, review_list, route_of,
    score_table, seconds_by_step, timed, trace_context, trace_run, user_settings)


@pytest.fixture(scope="module")
def review():
    return load_answers(RERUN_FILE)


@pytest.fixture(scope="module")
def lines(review):
    return trace_run(review, user_settings())


def test_model_calls_flattens_attempts():
    records = [{"id": "a", "attempts": [{"prompt_tokens": 10, "reply_tokens": 2, "seconds": 1.0},
                                        {"prompt_tokens": 15, "reply_tokens": 3, "seconds": 0.5}]},
               {"id": "b", "attempts": []},
               {"id": "c", "prompt_tokens": 7, "reply_tokens": 1, "seconds": 2.0}]
    calls = model_calls(records)
    assert [c["id"] for c in calls] == ["a", "a", "c"]
    assert sum(c["tokens_in"] for c in calls) == 32


def test_cost_counts_questions_with_no_call():
    row = cost([{"id": "a", "tokens_in": 800, "tokens_out": 200, "seconds": 50.0}], 2)
    assert row["in_per_question"] == 400.0
    assert row["seconds_per_question"] == 25.0
    assert cost([], 0)["in_per_question"] == 0


def test_every_saved_run_has_tokens_and_seconds():
    for row in cost_of_runs():
        assert row["calls"] > 0 and row["tokens_in"] > 0 and row["seconds"] > 0
    assert len(cost_of_runs()) == len(RUNS)


def test_review_run_totals(review):
    whole = cost(model_calls(review), len(review))
    assert whole["calls"] == 36
    assert round(whole["seconds"] / 60, 1) == 34.9


def test_route_of_separates_lookups():
    assert route_of({"route": "R2", "class": "Q1"}) == "R2 lookup"
    assert route_of({"route": "R2", "class": "Q3"}) == "R2"
    assert "R2 lookup" in NO_MODEL


def test_lookups_cost_no_tokens(review):
    routes = cost_by_route(review, questions_by_id())
    assert routes["R2 lookup"]["tokens_in"] == 0
    assert routes["R2 lookup"]["questions"] == 3
    assert sum(r["questions"] for r in routes.values()) == 24


def test_retries_are_counted_apart(review):
    found = retry_cost(review)
    assert found["first"]["calls"] == 21
    assert found["retry"]["calls"] == 15
    assert found["first"]["calls"] + found["retry"]["calls"] == 36


def test_executive_answers_are_shorter():
    roles = cost_by_role(load_answers(ANSWER_FOLDER / "ch11_answers.jsonl"))
    assert roles["executive"]["out_per_question"] < roles["analyst"]["out_per_question"] / 2


def test_user_settings_rejects_unknown_values():
    assert user_settings("commercial", "executive") == {"use_mode": "commercial",
                                                        "role": "executive"}
    with pytest.raises(ValueError):
        user_settings("private")
    with pytest.raises(ValueError):
        user_settings(role="minister")


def test_timed_returns_result_and_seconds():
    result, seconds = timed(sum, [1, 2, 3])
    assert result == 6 and seconds >= 0


def test_failed_checks_names_only_failures():
    assert failed_checks({"numbers": ["140"], "directions": [], "citations": []}) == ["numbers"]


def test_trace_has_one_line_per_step(lines, review):
    attempts = sum(len(r["attempts"]) for r in review)
    assert len(lines) == 7 * len(review) + attempts
    assert all(line["settings"] == {"use_mode": "non-commercial", "role": "analyst"}
               for line in lines)


def test_steps_with_no_model_reproduce_the_saved_run(lines):
    locked = [line for line in lines if line["step"] == "locked block"]
    evidence = [line for line in lines if line["step"] == "evidence"]
    assert all(line["outputs"]["same_as_saved_run"] for line in locked)
    assert all(line["outputs"]["same_as_saved_run"] for line in evidence)


def test_only_the_model_uses_tokens(lines):
    for step, total in seconds_by_step(lines).items():
        if step != "explanation":
            assert total["tokens_in"] == 0 and total["tokens_out"] == 0
    assert seconds_by_step(lines)["explanation"]["tokens_in"] > 0


def test_commercial_use_changes_the_evidence(review):
    lines = trace_run(review, user_settings("commercial"), trace_context())
    changed = [line for line in lines if line["step"] == "evidence"
               and not line["outputs"]["same_as_saved_run"]]
    assert changed
    withheld = [line for line in lines if line["step"] == "licence filter"]
    assert all(line["outputs"]["withheld"] for line in withheld)


def test_review_list_counts(review):
    rows = review_list(review)
    counts = count_by_check(rows)
    assert counts["dropped"]["questions"] == sum(r["status"] == "dropped" for r in review)
    assert all(row["tokens"] > 0 for row in rows if row["attempt"])


def test_count_by_check():
    rows = [{"question_id": "a", "check": "numbers"}, {"question_id": "a", "check": "numbers"}]
    assert count_by_check(rows) == {"numbers": {"problems": 2, "questions": 1}}


def test_every_score_is_labelled():
    assert all(row["label"] in ("training", "fair") for row in score_table())


def test_save_trace_writes_one_line_per_step(tmp_path, lines):
    from ragbook.ch15_token_cost import save_trace
    target = tmp_path / "traces" / "trace.jsonl"
    save_trace(lines[:3], target)
    assert len(target.read_text(encoding="utf-8").splitlines()) == 3
