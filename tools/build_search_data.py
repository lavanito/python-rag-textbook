"""Build what the page needs to find passages for a typed question (A5; build spec v3, 7.3).

Run from the repository folder:
    python tools/build_search_data.py
It writes app/data/search.json, read by app/js/search.js: the 57 passages
word for word with the facts the page shows and the filters need; Chapter 2's
common words and Chapter 3's typographic marks, for splitting text into
search words; the use modes and SNA editions of Chapter 8's filters; and, for
query expansion (Chapter 5), every concept's names and its same_as links from
the knowledge graph. Nothing here is typed again: each value is read from
the Python code or the data. A test rebuilds this file and fails if it
differs.
"""

import json
import string
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch02_minimal_pipeline import COMMON_WORDS, load_corpus   # noqa: E402
from ragbook.ch03_keyword_search import TYPOGRAPHIC_MARKS           # noqa: E402
from ragbook.ch05_hybrid_search import KnowledgeGraph               # noqa: E402
from ragbook.ch08_filters import EDITION_NAMES, EDITIONS, USE_MODES  # noqa: E402

OUT = REPO / "app" / "data" / "search.json"
PASSAGE_FIELDS = ["id", "source", "reference", "text", "edition", "source_code", "topic", "scope",
                  "scope_note", "licence", "licence_class"]


def build():
    passages = load_corpus()
    graph = KnowledgeGraph(passages)
    concepts = [c for c, e in graph.entities.items() if e["type"] == "Concept"]
    same_as = {c: [other for other, _ in graph.linked(c, "same_as")] for c in concepts}
    named = sorted({c for c in concepts} | {o for others in same_as.values() for o in others})
    return {
        "note": "Written by tools/build_search_data.py; do not edit by hand.",
        "passages": [{f: p.get(f, "") for f in PASSAGE_FIELDS} for p in passages],
        "punctuation": string.punctuation,
        "typographic_marks": TYPOGRAPHIC_MARKS,
        "common_words": sorted(COMMON_WORDS),
        "use_modes": USE_MODES,
        "editions": EDITIONS,
        "edition_names": EDITION_NAMES,
        "concepts": concepts,
        "names": {c: graph.names(c) for c in named},
        "same_as": same_as,
    }


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['passages'])} passages, {len(data['concepts'])} concepts")


if __name__ == "__main__":
    main()
