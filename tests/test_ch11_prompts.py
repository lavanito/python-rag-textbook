"""
Tests for Chapter 11: ragbook/ch11_prompts.py.

What this checks
    Each passage is labelled with its edition, and with its scope only when
    it has a scope note. The context keeps passages in rank order within the
    word budget. The messages carry the role's length rule. Settings trials
    change only what they name. Citations are counted correctly, including
    several ids in one bracket and ids the model was not given. Where the
    saved replies exist (data/answers/), they are checked too.

Why it matters
    The counts in 11.5 are the chapter's evidence. If cited_ids missed an id
    or the sentence count were wrong, the chapter would misreport how often
    the model cites its passages.

Chapter: 11. Runs on every change; needs no model and no internet.
"""

import json

import pytest

from ragbook import ch11_prompts
from ragbook.ch11_prompts import (
    ANSWERS_FILE, INSTRUCTIONS, ROLE_LENGTH, SETTINGS, SETTINGS_FILE, answer_bank,
    ask_model_with_details, assemble_context, build_messages, build_search, check_citations,
    cited_ids, distinct_replies, format_evidence, load_answers, run_trials, save_answers,
    scope_named, sentences, setting_trials, summarise, word_count,
)

SEARCH, QUESTIONS, PASSAGES = build_search()
BY_ID = {passage["id"]: passage for passage in PASSAGES}


def fake_passage(passage_id, words):
    return {"id": passage_id, "source": "S", "reference": "r", "edition": "e",
            "scope": "international standard", "scope_note": "", "text": " ".join(["w"] * words)}


def stand_in(messages, options):
    """A model that cites the first passage label it sees and reports fixed counts."""
    first_id = messages[1]["content"].split("[", 1)[1].split("]", 1)[0]
    return {"answer": f"An answer [{first_id}].", "prompt_tokens": 100, "reply_tokens": 10,
            "seconds": 2.0, "done_reason": "stop"}


# 11.2  Assembling the context

def test_every_passage_has_an_edition():
    for passage in PASSAGES:
        assert passage["edition"].strip() != ""


def test_scope_line_only_with_a_scope_note():
    with_note = format_evidence(BY_ID["cso-gnistar-1"])
    without_note = format_evidence(BY_ID["sna08-2.144"])
    assert "Scope: national practice: Ireland." in with_note
    assert "Scope:" not in without_note
    assert without_note.splitlines()[1] == "Edition: 2008 SNA (2009)"
    assert without_note.endswith(BY_ID["sna08-2.144"]["text"])


def test_context_keeps_rank_order_within_budget():
    ranked = [fake_passage("a-1", 300), fake_passage("b-2", 250), fake_passage("c-3", 100),
              fake_passage("d-4", 10)]
    kept, left_out = assemble_context(ranked, how_many=3, word_budget=600)
    assert [p["id"] for p in kept] == ["a-1", "b-2", "d-4"]
    assert [p["id"] for p in left_out] == ["c-3"]


def test_first_passage_always_kept():
    kept, left_out = assemble_context([fake_passage("a-1", 900), fake_passage("b-2", 10)],
                                      how_many=3, word_budget=600)
    assert [p["id"] for p in kept] == ["a-1"]
    assert [p["id"] for p in left_out] == ["b-2"]


def test_three_bank_contexts_fit_the_budget():
    for question in QUESTIONS:
        ranked, withheld = SEARCH.rank(question["question"], "non-commercial", how_many=10)
        kept, left_out = assemble_context(ranked)
        assert len(kept) == 3
        assert sum(len(p["text"].split()) for p in kept) <= 600


# 11.3  The instructions

def test_messages_carry_the_role_rule():
    kept = [BY_ID["cso-gnistar-1"]]
    for role, rule in ROLE_LENGTH.items():
        messages = build_messages("What is modified GNI?", kept, role)
        assert [m["role"] for m in messages] == ["system", "user"]
        assert messages[0]["content"] == INSTRUCTIONS + " " + rule
        assert messages[1]["content"].startswith("Question: What is modified GNI?\n\nPassages:\n\n")
        assert "[cso-gnistar-1]" in messages[1]["content"]


def test_word_count():
    assert word_count([{"role": "user", "content": "What is GDP?"},
                       {"role": "system", "content": "Be brief."}]) == 5


# 11.4  The settings

def test_trials_change_only_what_they_name():
    trials = setting_trials()
    assert len(trials) == 20
    assert len({label for label, changes in trials}) == 20
    records = run_trials(build_messages("Q?", [BY_ID["sna08-2.144"]]), ask=stand_in)
    assert records[0]["options"] == SETTINGS
    hot = [r for r in records if r["label"] == "temperature 1.5, seed 3"][0]["options"]
    assert hot["temperature"] == 1.5 and hot["seed"] == 3
    assert {k: v for k, v in hot.items() if k not in ("temperature", "seed")} == \
        {k: v for k, v in SETTINGS.items() if k not in ("temperature", "seed")}
    assert SETTINGS["temperature"] == 0.7 and SETTINGS["seed"] == 42


def test_distinct_replies():
    assert distinct_replies([{"answer": "A"}, {"answer": "A"}, {"answer": "B"}]) == 2


class FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_details_read_from_ollama_reply(monkeypatch):
    body = {"message": {"content": "GNI is ... [esa10-8.94]."}, "prompt_eval_count": 512,
            "eval_count": 85, "total_duration": 41_200_000_000, "done_reason": "stop"}
    monkeypatch.setattr(ch11_prompts.urllib.request, "urlopen", lambda request, timeout: FakeResponse(body))
    reply = ask_model_with_details([{"role": "user", "content": "x"}])
    assert reply == {"answer": "GNI is ... [esa10-8.94].", "prompt_tokens": 512,
                     "reply_tokens": 85, "seconds": 41.2, "done_reason": "stop"}


# 11.5  Counting citations

def test_cited_ids():
    text = ("GNI is income [esa10-8.94]. NNI deducts CFC [sna08-2.144; esa10-8.94]. "
            "Depreciation [sna25-A4.59, bea-ch2-ndp-gni]. See [1] and [the table].")
    assert cited_ids(text) == ["esa10-8.94", "sna08-2.144", "sna25-A4.59", "bea-ch2-ndp-gni"]


def test_sentences():
    assert sentences("GDP is output [a-1]. GNI adds income [b-2].  ") == \
        ["GDP is output [a-1].", "GNI adds income [b-2]."]
    assert sentences("GDP is output. [a-1] GNI adds income. [b-2][c-3] Done.") == \
        ["GDP is output. [a-1]", "GNI adds income. [b-2][c-3]", "Done."]


def test_check_citations():
    check = check_citations("GNI is income [esa10-8.94]. It is large. NNI [sna08-2.144].",
                            ["esa10-8.94"])
    assert check == {"cited": ["esa10-8.94", "sna08-2.144"], "not_given": ["sna08-2.144"],
                     "uncited_sentences": 1}


def test_scope_named():
    irish = [BY_ID["cso-gnistar-1"]]
    assert scope_named("Modified GNI removes globalisation effects [cso-gnistar-1].", irish) == ["cso-gnistar-1"]
    assert scope_named("In Irish practice (CSO), modified GNI ... [cso-gnistar-1].", irish) == []
    assert scope_named("Used in practice [bea-ch2-gnp].", [BY_ID["bea-ch2-gnp"]]) == ["bea-ch2-gnp"]
    assert scope_named("Any wording [esa10-8.94].", [BY_ID["esa10-8.94"]]) == []
    assert scope_named("Any wording [ppp23-1.13].", [BY_ID["ppp23-1.13"]]) == []
    assert scope_named("Any wording [ppp23-4.16].", [BY_ID["ppp23-4.16"]]) == ["ppp23-4.16"]


def test_answer_bank_with_a_stand_in():
    records = answer_bank(QUESTIONS, SEARCH, role="executive", ask=stand_in)
    assert len(records) == 32
    for record, question in zip(records, QUESTIONS):
        assert record["id"] == question["id"] and record["role"] == "executive"
        assert len(record["passage_ids"]) == 3
        assert check_citations(record["answer"], record["passage_ids"])["not_given"] == []
    commercial = answer_bank(QUESTIONS, SEARCH, use_mode="commercial", ask=stand_in)
    for record in commercial:
        assert all(BY_ID[i]["licence_class"] == "open" for i in record["passage_ids"])


def test_summarise():
    records = [
        {"answer": "A [esa10-8.94].", "passage_ids": ["esa10-8.94"], "done_reason": "stop",
         "seconds": 10.0, "reply_tokens": 20},
        {"answer": "B. C. D [x-9].", "passage_ids": ["esa10-8.94"], "done_reason": "length",
         "seconds": 20.0, "reply_tokens": 40},
        {"answer": "GNI* removes IP [cso-gnistar-1].", "passage_ids": ["cso-gnistar-1"],
         "done_reason": "stop", "seconds": 30.0, "reply_tokens": 60},
    ]
    counts = summarise(records, BY_ID)
    assert counts == {"answers": 3, "no_citation": 0, "not_given": 1, "uncited_sentences": 1,
                      "scope_unnamed": 1, "over_two_sentences": 1, "cut_off": 1,
                      "mean_seconds": 20.0, "mean_reply_tokens": 40}


def test_save_and_load(tmp_path):
    records = [{"id": "q2-01", "answer": "A [esa10-3.139]."}]
    save_answers(tmp_path / "a.jsonl", records)
    loaded = load_answers(tmp_path / "a.jsonl")
    assert loaded[0]["model"] == "qwen3:4b-instruct"
    assert loaded[0]["id"] == "q2-01" and loaded[0]["answer"] == "A [esa10-3.139]."
    assert len(loaded[0]["date"]) == 10


# Saved replies, once the laptop run is in the repository

@pytest.mark.skipif(not SETTINGS_FILE.exists(), reason="no saved settings trials yet")
def test_saved_settings_trials():
    records = load_answers(SETTINGS_FILE)
    assert [r["label"] for r in records] == [label for label, changes in setting_trials()]
    by_label = {r["label"]: r for r in records}
    # The first reply differs; later replies with the same prompt and settings repeat.
    assert by_label["seed 42, run 1"]["answer"] != by_label["seed 42, run 2"]["answer"]
    assert by_label["seed 42, run 2"]["answer"] == by_label["stop at a blank line"]["answer"]
    for temperature, different in ((0, 1), (0.7, 5), (1.5, 5)):
        group = [r for r in records if r["label"].startswith(f"temperature {temperature},")]
        assert distinct_replies(group) == different
    limited = by_label["reply limit 40 tokens"]
    assert limited["reply_tokens"] == 40 and limited["done_reason"] == "length"
    assert cited_ids(limited["answer"]) == []
    penalised = by_label["repeat penalty 1.5"]
    assert penalised["reply_tokens"] == 400 and penalised["done_reason"] == "length"


@pytest.mark.skipif(not ANSWERS_FILE.exists(), reason="no saved answers yet")
def test_saved_answers():
    records = load_answers(ANSWERS_FILE)
    assert len(records) == 64
    assert [r["role"] for r in records] == ["analyst"] * 32 + ["executive"] * 32
    analyst = summarise(records[:32], BY_ID)
    executive = summarise(records[32:], BY_ID)
    assert analyst == {"answers": 32, "no_citation": 0, "not_given": 1, "uncited_sentences": 29,
                       "scope_unnamed": 2, "over_two_sentences": 32, "cut_off": 6,
                       "mean_seconds": 69.3, "mean_reply_tokens": 307}
    assert executive == {"answers": 32, "no_citation": 0, "not_given": 0, "uncited_sentences": 5,
                         "scope_unnamed": 2, "over_two_sentences": 0, "cut_off": 0,
                         "mean_seconds": 30.2, "mean_reply_tokens": 80}
    # The same prompt and settings as the second settings trial give the same reply.
    if SETTINGS_FILE.exists():
        assert records[0]["answer"] == load_answers(SETTINGS_FILE)[1]["answer"]
