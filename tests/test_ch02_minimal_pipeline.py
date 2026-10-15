"""
Tests for Chapter 2 — A minimal RAG pipeline.

Retrieval is tested exactly. The model's wording is never tested: a stand-in
replaces the model, and the tests check what the pipeline sends and returns.
"""

import json

from ragbook.ch02_minimal_pipeline import (
    INSTRUCTIONS,
    NO_MATCH,
    answer_question,
    ask_model,
    build_prompt,
    find_matching_passages,
    load_corpus,
    topic_words,
)

PASSAGES = load_corpus()


def test_load_corpus_reads_every_passage_with_its_source():
    assert len(PASSAGES) == 48
    for passage in PASSAGES:
        assert passage["id"] and passage["source"] and passage["reference"] and passage["text"]


def test_topic_words_drops_common_words_and_repeats():
    assert topic_words("What is the GDP deflator?") == ["gdp", "deflator"]
    assert topic_words("GNI and GNI") == ["gni"]


def test_find_matching_passages_ranks_by_shared_topic_words():
    found = find_matching_passages(PASSAGES, "How do you get from GNI to net national income?")
    assert [passage["id"] for passage in found] == ["sna08-2.144", "bea-ch2-ndp-gni", "cso-gnistar-6"]


def test_find_matching_passages_returns_at_most_how_many():
    assert len(find_matching_passages(PASSAGES, "income", how_many=2)) == 2


def test_find_matching_passages_returns_nothing_when_no_word_matches():
    assert find_matching_passages(PASSAGES, "Which restaurant in Dublin serves oysters?") == []


def test_build_prompt_puts_rules_first_and_passages_with_ids_after_the_question():
    passage = {"id": "ex-001", "source": "Example", "reference": "para 1", "text": "GDP measures output."}
    messages = build_prompt("What is GDP?", [passage])
    assert messages[0] == {"role": "system", "content": INSTRUCTIONS}
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Question: What is GDP?\n\nPassages:\n\n[ex-001] Example, para 1\nGDP measures output."


def test_answer_question_sends_only_the_matched_passages_to_the_model():
    sent = []

    def stand_in_model(messages):
        sent.append(messages)
        return "Deduct consumption of fixed capital [sna08-2.144]."

    result = answer_question("How do you get from GNI to net national income?", PASSAGES, ask=stand_in_model)
    assert len(sent) == 1
    for passage_id in result["passage_ids"]:
        assert f"[{passage_id}]" in sent[0][1]["content"]
    assert result["answer"] == "Deduct consumption of fixed capital [sna08-2.144]."


def test_answer_question_does_not_ask_the_model_when_nothing_matches():
    def model_that_must_not_be_called(messages):
        raise AssertionError("the model was asked")

    result = answer_question("Which restaurant in Dublin serves oysters?", PASSAGES, ask=model_that_must_not_be_called)
    assert result == {"question": "Which restaurant in Dublin serves oysters?", "passage_ids": [], "answer": NO_MATCH}


def test_ask_model_sends_settings_inside_options_and_reads_the_reply(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *details):
            return False

        def read(self):
            return json.dumps({"message": {"role": "assistant", "content": "An answer."}}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    reply = ask_model([{"role": "user", "content": "Hello"}])
    assert reply == "An answer."
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["body"]["options"] == {
        "temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0,
        "seed": 42, "num_ctx": 4096, "num_predict": 400,
    }
    assert captured["body"]["stream"] is False
    assert captured["body"]["model"] == "qwen3:4b-instruct"
