"""
Tests for the knowledge graph: data/knowledge_graph/.

What this checks
    Every fact (triplet) uses a relation the ontology declares, links things
    of the kinds that relation allows, points only at passages that exist,
    and records its evidence. Every passage's manual is a declared manual.

Why it matters
    The graph widens searches and moves answers between manuals. A fact that
    points at a missing passage, or links the wrong kinds of thing, would
    send retrieval to the wrong evidence.
"""

import csv
import json
from pathlib import Path

from ragbook.ch01_python_basics import load_passages

DATA = Path(__file__).parent.parent / "data"
SCHEMA = json.loads((DATA / "knowledge_graph" / "schema.json").read_text(encoding="utf-8"))
with open(DATA / "knowledge_graph" / "entities.csv", encoding="utf-8") as file:
    ENTITIES = list(csv.DictReader(file))
with open(DATA / "knowledge_graph" / "triples.csv", encoding="utf-8") as file:
    TRIPLES = list(csv.DictReader(file))
PASSAGES = load_passages(DATA / "corpus" / "passages.jsonl")

KIND = {row["id"]: row["type"] for row in ENTITIES}
for passage in PASSAGES:
    KIND[passage["id"]] = "Passage"


def test_entity_ids_are_unique_and_kinds_are_declared():
    ids = [row["id"] for row in ENTITIES]
    assert len(ids) == len(set(ids))
    for row in ENTITIES:
        assert row["type"] in SCHEMA["entity_types"], row["id"]


def test_every_triple_uses_a_declared_relation():
    for triple in TRIPLES:
        assert triple["relation"] in SCHEMA["relations"], triple


def allowed(kinds):
    """A relation names one kind, or a list of kinds, for its subject and its object."""
    return kinds if isinstance(kinds, list) else [kinds]


def test_subject_and_object_have_the_kinds_the_relation_allows():
    for triple in TRIPLES:
        rule = SCHEMA["relations"][triple["relation"]]
        assert KIND.get(triple["subject"]) in allowed(rule["subject"]), triple
        assert KIND.get(triple["object"]) in allowed(rule["object"]), triple


def test_every_triple_has_evidence_that_exists():
    for triple in TRIPLES:
        evidence = triple["evidence"]
        assert evidence == "author" or evidence in KIND and KIND[evidence] == "Passage", triple


def test_every_passage_comes_from_a_declared_manual():
    for passage in PASSAGES:
        assert KIND.get(passage["source_code"]) == "Manual", passage["id"]


def test_no_triple_is_repeated():
    keys = [(t["subject"], t["relation"], t["object"]) for t in TRIPLES]
    assert len(keys) == len(set(keys))


def test_every_measure_in_the_nni_model_is_an_indicator():
    # The catalogue of measures (the horizontal domain expert, 16 November 2026): each of the
    # NNI model's measures is a thing in the graph, so a question can be read
    # against it. Two ids differ from the measure's name, because a concept
    # already has that id.
    from ragbook.ch13_model_tool import MEASURES
    renamed = {"population": "population_total", "gni": "gni_total"}
    for measure in MEASURES:
        assert KIND.get(renamed.get(measure, measure)) == "Indicator", measure


def test_only_whole_measure_definitions_are_defined_in():
    # A measure is defined_in a passage only when the passage defines the whole
    # measure (the horizontal domain expert, 16 November 2026).
    defined = {(t["subject"], t["object"]) for t in TRIPLES
               if t["relation"] == "defined_in" and KIND.get(t["subject"]) == "Indicator"}
    assert defined == {("gni_total", "esa10-8.94"), ("population_total", "esa10-11.05"),
                       ("average_hours", "esa10-11.27")}
