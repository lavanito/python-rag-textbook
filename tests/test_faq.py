"""
Test: the page's questions and answers match data/faq.csv.

What this checks
    tools/build_faq.py rebuilds app/data/faq.json; the stored file must
    equal the rebuilt one. Every answer was written by the vertical domain
    expert and carries no draft mark.

Chapter: none (demonstrator, gate A5). Runs on every change.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_faq", ROOT / "tools" / "build_faq.py")
faq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(faq)


def test_stored_faq_equals_the_rebuilt_faq():
    assert json.loads(faq.OUT.read_text(encoding="utf-8")) == faq.build()


def test_every_answer_is_the_vertical_domain_experts_and_final():
    for item in faq.build()["questions"]:
        assert item["written_by"] == "vertical domain expert"
        assert "draft" not in item["answer"].lower()
