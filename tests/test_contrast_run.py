"""The contrast run sends each bank question alone and can be restarted (A5, component 12)."""

import json

from tools import run_contrast


def fake_ask(messages, options):
    return {"answer": "reply to " + messages[0]["content"], "prompt_tokens": 10,
            "reply_tokens": 5, "seconds": 1.0, "done_reason": "stop"}


def test_question_sent_alone():
    assert run_contrast.contrast_messages("What is GDI?") == [{"role": "user", "content": "What is GDI?"}]


def test_run_saves_every_bank_question_and_restarts(tmp_path):
    out = tmp_path / "contrast.jsonl"
    asked = []

    def counting_ask(messages, options):
        asked.append(messages[0]["content"])
        assert options["temperature"] == 0 and options["num_ctx"] == 8192
        return fake_ask(messages, options)

    records = run_contrast.run(counting_ask, out)
    assert len(records) == 56 and len(asked) == 56
    saved = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert all(r["answer"] == "reply to " + r["question"] for r in saved)
    assert all(r["passages"] == 0 and r["data"] == "none" and "date" in r for r in saved)
    run_contrast.run(counting_ask, out)             # nothing left to ask
    assert len(asked) == 56
