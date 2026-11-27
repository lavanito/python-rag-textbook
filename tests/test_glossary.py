"""
Test: the page's glossary is built from the approved records and linked by fixed rules.

What this checks
    app/data/glossary.json equals a rebuild from data/glossary.csv
    (tools/build_glossary.py); every term is approved and written by the
    vertical domain expert; each preferred label and each linked form belongs
    to one term only; no acronym is used in a definition without being
    defined, in the glossary or in the same definition; and app/js/glossary.js
    links the first use of each term only, the longest form first, acronyms
    in their exact case and whole words only.

Chapter: none (demonstrator, gate A5; decision 2a, 27 November 2026).
"""

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_glossary", ROOT / "tools" / "build_glossary.py")
glossary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glossary)

# Acronyms spelled out in the definition that uses them, or names of places and labels.
DEFINED_IN_PLACE = {"AI", "AMB", "OUT", "BM", "IRI", "PROV-O", "SQL", "US", "UK", "USA", "Q1", "Q8", "R1", "R6"}


def test_stored_file_equals_the_rebuilt_file():
    stored = json.loads(glossary.OUT.read_text(encoding="utf-8"))
    assert stored == json.loads(json.dumps(glossary.build(), ensure_ascii=False))


def test_every_term_is_approved_and_written_by_the_vertical_domain_expert():
    rows = glossary.load()
    assert len(rows) == 144
    for row in rows:
        assert row["approved"], row["term"]
        assert row["written_by"] == "vertical domain expert", row["term"]
        assert row["definition"] == row["definition"].strip(), row["term"]


def test_one_term_per_label_and_per_linked_form():
    terms = glossary.build()["terms"]
    labels = [t["preferred_label"].lower() for t in terms]
    assert len(labels) == len(set(labels))
    forms = [f.lower() for t in terms for f in t["link_forms"]]
    assert len(forms) == len(set(forms))


def test_decisions_of_27_november():
    """Triple, with triplet its alias (decision 2); entity, not thing (3); question type (4)."""
    by_label = {t["preferred_label"]: t for t in glossary.build()["terms"]}
    assert "triplet" in by_label["Triple"]["alternative_labels"] and "Triplet" not in by_label
    assert "thing" in by_label["Entity"]["alternative_labels"]
    assert "class of a question" in by_label["Question type"]["alternative_labels"]


def test_no_undefined_acronym():
    terms = glossary.build()["terms"]
    known = {name for t in terms for name in [t["preferred_label"], *t["alternative_labels"]]}
    known |= {name + "s" for name in known}
    for t in terms:
        for token in re.findall(r"\b[A-Z][A-Z0-9-]*[A-Z0-9]\b", t["definition"]):
            assert token in known or token in DEFINED_IN_PLACE, (t["term"], token)


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
def test_first_use_per_section_is_linked():
    script = """
    require(process.argv[1]);
    const terms = [{id: "rag", link_forms: ["RAG"]}, {id: "governed-rag", link_forms: ["Governed RAG"]},
                   {id: "dqr", link_forms: ["DQR", "data quality rating"]}, {id: "passage", link_forms: ["Passage"]},
                   {id: "ppp", link_forms: ["PPP"]}];
    const m = globalThis.glossaryCode.compile(terms);
    const run = (text) => globalThis.glossaryCode.linkText(text, m, new Set())
      .filter((p) => p.id).map((p) => p.id + ":" + p.text);
    console.log(JSON.stringify([
      run("Governed RAG is a kind of RAG; RAG again."),
      run("The Data Quality Rating and the DQR; dqr is not linked."),
      run("Passages, then a passage."),
      run("PPPs, not PPP-based or PPPX."),
    ]));
    """
    found = subprocess.run([NODE, "-e", script, str(ROOT / "app" / "js" / "glossary.js")],
                           capture_output=True, text=True, check=True).stdout
    assert json.loads(found) == [
        ["governed-rag:Governed RAG", "rag:RAG"],
        ["dqr:Data Quality Rating"],
        ["passage:Passages"],
        ["ppp:PPPs"],
    ]
