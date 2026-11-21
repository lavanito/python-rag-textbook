"""
Test: every count the book and the READMEs publish matches the data.

What this checks
    The totals are recomputed from the data files: passages, sources, bank
    questions, knowledge graph things, triplets, relations and kinds, and
    controlled vocabulary terms. Then:
    1. every statement in CURRENT_TOTALS is found in its file, with the
       recomputed number;
    2. every "<number> things", "triplets", "relations" or "kinds" in any
       text file equals the recomputed total, because these words are only
       used for the whole graph.

Why it matters
    A count typed once goes stale when the data change (lesson L9, from
    Agri Map Navigator: 1,260 providers on one page, 1,195 on another).

Chapter: front matter (repository rules). Runs on every change.
"""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
WORDS = {"six": 6, "ten": 10, "twelve": 12}


def read_jsonl(path):
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def recompute():
    """Every published total, counted from the data files."""
    passages = read_jsonl(DATA / "corpus" / "passages.jsonl")
    schema = json.loads((DATA / "knowledge_graph" / "schema.json").read_text(encoding="utf-8"))
    return {
        "passages": len(passages),
        "sources": len({p["source_code"] for p in passages}),
        "bank questions": len(read_jsonl(DATA / "question_bank" / "questions.jsonl")),
        "things": len(read_csv(DATA / "knowledge_graph" / "entities.csv")),
        "triplets": len(read_csv(DATA / "knowledge_graph" / "triples.csv")),
        "relations": len(schema["relations"]),
        "kinds": len(schema["entity_types"]),
        "vocabulary terms": len(read_csv(DATA / "knowledge_graph" / "controlled_vocabulary.csv")),
    }


# Statements of a current total: (file, pattern with one number, which total).
CURRENT_TOTALS = [
    ("book/ch02_minimal_pipeline.md", r"`data/corpus/passages\.jsonl`, (\d+) passages", "passages"),
    ("book/ch02_minimal_pipeline.md", r"quoted word for word from (\w+) manuals", "sources"),
    ("book/ch02_minimal_pipeline.md", r"The corpus loads (\d+) passages", "passages"),
    ("book/ch03_keyword_search.md", r"is in 2 of the (\d+) passages", "passages"),
    ("book/ch07_vector_store.md", r"the collection contains (\d+) passages", "passages"),
    ("book/ch08_filters.md", r"Keeps all (\d+) passages", "passages"),
    ("book/ch08_filters.md", r"Commercial use keeps 41 of the (\d+) passages", "passages"),
    ("book/ch12_routing.md", r"The bank: (\d+) questions", "bank questions"),
    ("book/ch05_hybrid_search.md", r"`entities\.csv` lists (\d+) things", "things"),
    ("book/ch05_hybrid_search.md", r"With (\d+) triplets", "triplets"),
    ("data/knowledge_graph/README.md", r"eight input flags \((\d+) terms\)", "vocabulary terms"),
]

GRAPH_WORDS = re.compile(r"\b(\d+|six|ten|twelve) (things|triplets|relations|kinds)\b")


def number(text):
    return WORDS[text] if text in WORDS else int(text)


def text_files():
    files = sorted((ROOT / "book").glob("*.md")) + [ROOT / "README.md"]
    files += sorted(DATA.glob("*.md")) + sorted(DATA.glob("*/README.md"))
    return files


def test_current_totals_match_the_data():
    totals = recompute()
    for file_name, pattern, total in CURRENT_TOTALS:
        text = (ROOT / file_name).read_text(encoding="utf-8")
        found = re.findall(pattern, text)
        assert found, f"{file_name}: statement not found: {pattern}"
        for value in found:
            assert number(value) == totals[total], f"{file_name}: {value} {total}, data has {totals[total]}"


def test_every_graph_count_in_the_text_matches_the_data():
    totals = recompute()
    problems = []
    for path in text_files():
        for value, word in GRAPH_WORDS.findall(path.read_text(encoding="utf-8")):
            if number(value) != totals[word]:
                problems.append(f"{path.relative_to(ROOT)}: {value} {word}, data has {totals[word]}")
    assert problems == []


def test_counts_known_on_21_november_2026():
    # The counts the build spec and the handover quote; change them together.
    assert recompute() == {"passages": 57, "sources": 10, "bank questions": 56, "things": 67,
                           "triplets": 131, "relations": 12, "kinds": 6, "vocabulary terms": 28}
