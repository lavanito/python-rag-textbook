"""Build the page's glossary from its record (A5; Lavan, 27 Nov 2026).

Run from the repository folder:
    python tools/build_glossary.py
It writes app/data/glossary.json from data/glossary.csv: 144 terms approved by
the vertical domain expert on 27 Nov 2026, in controlled-vocabulary form
(preferred term, definition, aliases, source, who writes and who checks).
For each term it also lists the words that link to it on the page: the term
without its qualifier in brackets, and its aliases. A term marked
auto_link "no" is a common English word (such as "class" or "range") and is
shown in the glossary but not linked automatically, because most of its uses
on the page are not in the glossary's sense.
A test rebuilds this file and fails if it differs.
"""

import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RECORD = REPO / "data" / "glossary.csv"
OUT = REPO / "app" / "data" / "glossary.json"


def link_words(term, aliases):
    """The words that link to a term: its name without a bracketed qualifier, then its aliases.

    Example:
        link_words("DQR (data quality rating)", ["data quality rating"])
        returns ["DQR", "data quality rating"]
    """
    words = [re.sub(r"\s*\(.*\)$", "", term)] + aliases
    return [w for i, w in enumerate(words) if w and w not in words[:i] and "(" not in w]


def build():
    with open(RECORD, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    entries = []
    for r in rows:
        aliases = [a for a in r["aliases"].split(" | ") if a]
        entries.append({"id": r["id"], "term": r["term"], "definition": r["definition"], "aliases": aliases,
                        "source": r["source"], "approved": r["approved"],
                        "links": link_words(r["term"], aliases) if r["auto_link"] == "yes" else []})
    return {"note": "Written by tools/build_glossary.py from data/glossary.csv; do not edit by hand.",
            "entries": sorted(entries, key=lambda e: e["term"].lower())}


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['entries'])} terms")


if __name__ == "__main__":
    main()
