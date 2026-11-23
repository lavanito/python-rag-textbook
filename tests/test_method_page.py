"""
Test: the "Method and caveats" page data match the data they count.

What this checks
    tools/build_method_page.py rebuilds app/data/method_and_caveats.json from
    the corpus, the question bank, the saved rerun, the judgements and the
    NNI model. The stored file must equal the rebuilt one, so no number on
    the page is typed by hand or left stale (lessons L5 and L9; gate B3s).

Chapter: none (demonstrator, gate A5). Runs on every change.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_method_page", ROOT / "tools" / "build_method_page.py")
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)


def test_stored_page_equals_the_rebuilt_page():
    stored = json.loads(page.OUT.read_text(encoding="utf-8"))
    assert stored == json.loads(json.dumps(page.build()))


def test_counts_add_up():
    c = page.build()["counts"]
    assert sum(c["passages_by_licence"].values()) == c["passages"]
    assert sum(c["questions_by_route"].values()) == c["questions"]
    assert c["measures_exact"] + c["measures_proxy"] + c["measures_no_figure"] == c["measures"]
    e = c["explanations"]
    assert e["lookup"] + e["shown_with_content"] + e["shown_fixed_sentence"] + e["dropped"] == e["questions"]
    assert e["judged_good"] + e["judged_fault"] == e["shown_with_content"]


def test_every_caveat_has_a_title_and_at_most_three_sentences():
    for caveat in page.build()["caveats"]:
        assert caveat["title"] and caveat["text"]
        assert caveat["text"].count(". ") <= 3, caveat["title"]
