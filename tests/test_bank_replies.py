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


def test_every_commercial_explanation_with_content_is_judged():
    import csv
    path = ROOT / "data" / "answers" / "a5_judgements_commercial.csv"
    judged = {row["id"] for row in csv.DictReader(open(path, encoding="utf-8"))}
    shown = {r["id"] for r in BUILT["replies"]
             if r["modes"]["commercial"]["explanation"]["status"] in ("passed", "passed on retry", "corrected")
             and "No explanation is available" not in (r["modes"]["commercial"]["explanation"].get("model_text")
                                                       or r["modes"]["commercial"]["explanation"]["text"])
             and r["modes"]["commercial"]["evidence"] != r["modes"]["non-commercial"]["evidence"]}
    assert shown == judged


def test_judgement_reasons_are_final():
    """Reasons are written by the vertical domain expert: none may carry a draft mark (Lavan, 24 Nov)."""
    import csv
    for name in ("a5_judgements.csv", "a5_judgements_commercial.csv"):
        with open(ROOT / "data" / "answers" / name, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                assert row["reason"].strip() and not row["reason"].lower().startswith("draft")


def test_corrected_explanation_keeps_the_model_text_and_a_fault_judgement():
    import csv
    with open(ROOT / "data" / "answers" / "a5_judgements_commercial.csv", encoding="utf-8") as f:
        faults = {row["id"] for row in csv.DictReader(f) if row["judgement"] == "fault"}
    for reply in BUILT["replies"]:
        for mode in reply["modes"].values():
            if mode["explanation"]["status"] == "corrected":
                assert mode["explanation"]["text"].startswith(replies.CORRECTED_HEADING)
                assert mode["explanation"]["model_text"]
                assert reply["id"] in faults


def test_comparison_line_on_every_reply_that_compares_economies():
    for reply in BUILT["replies"]:
        mode = reply["modes"]["non-commercial"]
        if reply["class"] in replies.COMPARING_CLASSES and reply["built"]:
            assert replies.COMPARISON_LINE in mode["locked"]
        for option in mode.get("options", []):
            assert replies.COMPARISON_LINE in option["locked"]
