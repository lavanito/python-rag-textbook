"""
Tests for the concept map: data/ontology/.

What this checks
    Every fact (triple) uses a relation the ontology declares, links things
    of the kinds that relation allows, points only at passages that exist,
    and records its evidence. Every passage's manual is a declared manual.

Why it matters
    The map widens searches and moves answers between manuals. A fact that
    points at a missing passage, or links the wrong kinds of thing, would
    send retrieval to the wrong evidence.
"""

import csv
import json
from pathlib import Path

from ragbook.ch01_python_basics import load_passages

DATA = Path(__file__).parent.parent / "data"
SCHEMA = json.loads((DATA / "ontology" / "schema.json").read_text(encoding="utf-8"))
with open(DATA / "ontology" / "entities.csv", encoding="utf-8") as file:
    ENTITIES = list(csv.DictReader(file))
with open(DATA / "ontology" / "triples.csv", encoding="utf-8") as file:
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


def test_subject_and_object_have_the_kinds_the_relation_allows():
    for triple in TRIPLES:
        rule = SCHEMA["relations"][triple["relation"]]
        assert KIND.get(triple["subject"]) == rule["subject"], triple
        assert KIND.get(triple["object"]) == rule["object"], triple


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
