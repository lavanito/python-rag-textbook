"""
Test: the replies to the 56 bank questions match the code that builds them.

What this checks
    tools/build_bank_replies.py rebuilds app/data/bank_replies.json from the
    question bank, the saved runs, the corpus and the NNI model. The stored
    file must equal the rebuilt one, so no reply is typed by hand or left
    stale (gate A5; gate B3s). Also: every bank question has a reply in both
    use modes; no reply quotes a passage its use mode withholds; the
    suggested questions are bank questions that are built.

Chapter: none (demonstrator, gate A5). Runs on every change.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


replies = load("build_bank_replies")
commercial = load("run_commercial_explanations")
BUILT = replies.build()


def test_stored_replies_equal_the_rebuilt_replies():
    stored = json.loads(replies.OUT.read_text(encoding="utf-8"))
    assert stored == json.loads(json.dumps(BUILT))


def test_every_bank_question_has_a_reply_in_both_use_modes():
    assert len(BUILT["replies"]) == 56
    for reply in BUILT["replies"]:
        assert set(reply["modes"]) == set(replies.MODES)
        for mode in reply["modes"].values():
            assert mode["page"]


def test_no_reply_uses_a_withheld_passage():
    for reply in BUILT["replies"]:
        for mode in reply["modes"].values():
            assert not set(mode["evidence"]) & set(mode["withheld"])


def test_router_agrees_with_the_bank_labels():
    for reply in BUILT["replies"]:
        assert (reply["router"]["class"], reply["router"]["route"]) == (reply["class"], reply["route"])


def test_suggested_questions_are_built():
    built = {r["id"] for r in BUILT["replies"] if r["built"]}
    assert set(replies.SUGGESTED) <= built
    assert "q8-01" not in replies.SUGGESTED


def test_commercial_run_covers_every_question_awaiting_it():
    awaiting = {r["id"] for r in BUILT["replies"]
                if r["modes"]["commercial"]["explanation"]["status"] == replies.AWAITING}
    to_run = {question["id"] for question, *_ in commercial.questions_to_run()}
    if not replies.COMMERCIAL_FILE.exists():
        assert awaiting == to_run
    else:
        assert not awaiting
