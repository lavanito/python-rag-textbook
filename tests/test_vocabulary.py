"""
Test: the controlled vocabulary's first set follows its rules.

What this checks
    data/knowledge_graph/controlled_vocabulary.csv holds the first set: the
    13 NNI model measures, the six economies and Ireland, and the input flags.
    Each term has one preferred label, a definition with its source, the two
    roles and a status. No label names two terms. Concept, series and figure
    are kept apart (lesson L3): series codes sit in the `series` column, never
    in a label, and no figure is stored. The knowledge graph's aliases for
    these terms are a copy of the vocabulary's alternative labels.

Why it matters
    Code, search and the router read these names. Written in one place, they
    cannot drift apart.

Chapter: Appendix B (planned). Runs on every change.
"""

import csv
import importlib.util
import re
from pathlib import Path

from nni_model.contracts import raw_rows
from nni_model.dqr import FLAG_CAPS

from ragbook.ch12_routing import DATA_CODES
from ragbook.ch13_model_tool import MEASURES

ROOT = Path(__file__).parent.parent
FOLDER = ROOT / "data" / "knowledge_graph"
COLUMNS = ["id", "scheme", "prefLabel", "altLabel", "hiddenLabel", "definition", "scopeNote",
           "notation", "broader", "related", "exactMatch", "series", "definitionSource",
           "writtenBy", "checkedBy", "status", "created", "modified"]
SERIES_CODE = re.compile(r"^[A-Z]{2,}(\.[A-Z0-9]+)+$")

with open(FOLDER / "controlled_vocabulary.csv", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    HEADER = reader.fieldnames
    TERMS = list(reader)
with open(FOLDER / "entities.csv", encoding="utf-8", newline="") as file:
    THINGS = {row["id"]: row for row in csv.DictReader(file)}


def labels(term):
    alternatives = [a.strip() for a in term["altLabel"].split("|") if a.strip()]
    hidden = [a.strip() for a in term["hiddenLabel"].split("|") if a.strip()]
    return [term["prefLabel"]] + alternatives + hidden


def scheme(name):
    return [t for t in TERMS if t["scheme"] == name]


def test_columns_and_line_endings():
    assert HEADER == COLUMNS
    assert (FOLDER / "controlled_vocabulary.csv").read_bytes().count(b"\r\n") == len(TERMS) + 1


def test_first_set_is_complete():
    assert len({t["id"] for t in TERMS}) == len(TERMS)
    assert {t["scheme"] for t in TERMS} == {"measure", "economy", "input_flag"}
    assert sorted(t["notation"] for t in scheme("measure")) == sorted(MEASURES)
    assert {t["id"]: t["notation"] for t in scheme("economy")} == DATA_CODES
    assert {t["notation"] for t in scheme("input_flag")} == set(FLAG_CAPS) | {"provisional", "proxy"}


def test_every_term_has_definition_source_roles_and_status():
    for t in TERMS:
        for column in ["prefLabel", "definition", "definitionSource", "created", "modified"]:
            assert t[column].strip(), (t["id"], column)
        assert t["writtenBy"] == "vertical domain expert", t["id"]
        assert t["checkedBy"] == "horizontal domain expert", t["id"]
        assert t["status"] in {"draft", "approved"}, t["id"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", t["created"]) and t["modified"] >= t["created"]


def test_no_label_is_used_twice():
    # SKOS: one term never repeats a label; across terms a shared label is a homonym.
    seen = {}
    for t in TERMS:
        names = [n.lower() for n in labels(t)]
        assert len(names) == len(set(names)), t["id"]
        for n in names:
            assert n not in seen, f"'{n}' names both {seen[n]} and {t['id']}"
            seen[n] = t["id"]


def test_concept_series_and_figure_are_kept_apart():
    assert not {"value", "year", "figure"} & set(HEADER)       # figures live in the data, not here
    known_series = {row[1] for row in raw_rows()}
    for t in TERMS:
        for name in labels(t):
            assert not SERIES_CODE.match(name), (t["id"], name)
        codes = [c.strip() for c in t["series"].split("|") if c.strip()]
        assert bool(codes) == (t["scheme"] == "measure"), t["id"]
        for code in codes:
            assert SERIES_CODE.match(code) and code in known_series, (t["id"], code)


def test_graph_aliases_are_a_copy_of_the_vocabulary():
    spec = importlib.util.spec_from_file_location(
        "sync_vocabulary_aliases", ROOT / "tools" / "sync_vocabulary_aliases.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    aliases = tool.vocabulary_aliases(FOLDER)
    for t in scheme("measure") + scheme("economy"):
        assert t["id"] in THINGS, t["id"]
        assert THINGS[t["id"]]["label"] == t["prefLabel"], t["id"]
        assert THINGS[t["id"]]["aliases"] == aliases[t["id"]], t["id"]
