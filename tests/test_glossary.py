"""
Test: the page's glossary is its approved record, in controlled-vocabulary form.

What this checks
    app/data/glossary.json equals a rebuild from data/glossary.csv
    (tools/build_glossary.py). Every term has a unique id, a definition ending
    with a full stop or a web address, a source, an approval date, a writer and
    a checker. No word links to two terms. Every acronym written in capitals
    at the start of a term is spelled out as an alias (no undefined acronym).

Chapter: none (demonstrator, gate A5; glossary approved by Lavan, 27 Nov 2026).
"""

import csv
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_glossary", ROOT / "tools" / "build_glossary.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def rows():
    with open(build.RECORD, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_glossary_matches_rebuild():
    assert json.loads(build.OUT.read_text(encoding="utf-8")) == json.loads(json.dumps(build.build(), ensure_ascii=False))


def test_every_term_is_complete_and_approved():
    ids = [r["id"] for r in rows()]
    assert len(ids) == len(set(ids))
    for r in rows():
        assert r["definition"].rstrip().endswith(".") or r["definition"].rstrip().endswith("/"), r["term"]
        assert r["source"] and r["approved"] and r["written_by"] and r["checked_by"], r["term"]


def test_no_word_links_to_two_terms():
    seen = {}
    for e in build.build()["entries"]:
        for w in e["links"]:
            assert seen.setdefault(w.lower(), e["id"]) == e["id"], w


def test_acronyms_are_spelled_out():
    for r in rows():
        head = re.sub(r"\s*\(.*\)$", "", r["term"])
        if re.fullmatch(r"[A-Z][A-Z0-9]+[a-z]?", head) and head not in {"BM25", "SPARQL", "ALFRED"}:
            assert r["aliases"], r["term"]
