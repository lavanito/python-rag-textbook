"""Build what the page needs to route a typed question (A5; build spec v3, 7.2).

Run from the repository folder:
    python tools/build_routing_data.py
It writes app/data/routing.json, read by app/js/route_question.js, the
JavaScript version of Chapter 12's fourth-round rules (route_question_graph):
the word lists and patterns as Chapter 12 defines them, the economies' names
from the knowledge graph, the last years, the series codes in the data, the
topic words found in the corpus, Chapter 2's common words and the escalation
messages. Nothing here is typed again: each value is read from the Python
code or the data. A test rebuilds this file and fails if it differs.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook import ch12_routing as ch12                       # noqa: E402
from ragbook.ch02_minimal_pipeline import COMMON_WORDS         # noqa: E402
from ragbook.ch02_minimal_pipeline import load_corpus          # noqa: E402

OUT = REPO / "app" / "data" / "routing.json"
PATTERNS = ["FORECAST", "ADVICE", "CONDITIONAL", "ANY_CODE", "YEAR", "REVISION_DATE"]
WORD_LISTS = ["JUDGEMENT", "SCENARIO", "VAGUE_FOURTH", "VINTAGE_FOURTH", "MEASUREMENT", "DRIVERS", "WHY",
              "NOT_IN_DATA_FOURTH", "REVISION_WORDS"]


def build():
    economies = ch12.load_economies()
    return {
        "note": "Written by tools/build_routing_data.py; do not edit by hand.",
        "patterns": {name: getattr(ch12, name).pattern for name in PATTERNS},
        "word_lists": {name: getattr(ch12, name) for name in WORD_LISTS},
        "outside_share": ch12.OUTSIDE_SHARE,
        "economies": [[code, names] for code, names in economies["names"].items()],
        "members": economies["members"],
        "last_years": [[economy, edition, year] for (economy, edition), year in ch12.load_last_years().items()],
        "series_codes": sorted(ch12.load_titles()),
        "known_words": sorted(ch12.corpus_words(load_corpus())),
        "common_words": sorted(COMMON_WORDS),
        "escalation": {"reasons": ch12.ESCALATION_REASONS, "messages": ch12.ESCALATION_MESSAGES,
                       "last_year": ch12.LAST_YEAR, "economies_in_data": ch12.ECONOMIES_IN_DATA},
    }


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['known_words'])} corpus words, "
          f"{len(data['series_codes'])} series codes")


if __name__ == "__main__":
    main()
