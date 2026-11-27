"""Build the page's glossary from the approved records (A5; decision 2a, 27 November 2026).

Run from the repository folder:
    python tools/build_glossary.py
It writes app/data/glossary.json from data/glossary.csv: one entry per term,
in alphabetical order, with its id, preferred label, alternative labels,
definition, the citation shown on the page, who wrote and who checked it,
and the forms of the term that are linked where they first appear in each
section of the page (app/js/glossary.js).

data/glossary.csv follows the rules of a controlled vocabulary (Lavan,
27 November 2026, decision 6): one preferred label per term, its aliases
as alternative labels, written by the vertical domain expert and checked by
the horizontal domain expert. A definition may use any term the glossary
defines. Its 144 terms were approved by the vertical domain expert on
27 November 2026, from the Glossary tab of the review Sheet.

No text is typed here: change data/glossary.csv, then run this tool. A test
(tests/test_glossary.py) rebuilds the file and fails if it differs.
"""

import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GLOSSARY = REPO / "data" / "glossary.csv"
OUT = REPO / "app" / "data" / "glossary.json"
TALISMAN = ("Talisman, J. (2026). Ontology Pipeline: A Framework for Knowledge Engineering. "
            "Technics Publications.")


def term_id(term):
    """'DQR (data quality rating)' -> 'dqr-data-quality-rating'.

    >>> term_id("Genus–differentia definition")
    'genus-differentia-definition'
    """
    return re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")


def split(cell):
    return [part for part in cell.split(";") if part]


def load():
    with open(GLOSSARY, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build():
    terms = []
    for row in sorted(load(), key=lambda r: r["term"].lower()):
        terms.append({"id": term_id(row["term"]), "term": row["term"], "preferred_label": row["preferred_label"],
                      "alternative_labels": split(row["alternative_labels"]), "definition": row["definition"],
                      "cite": row["cite_on_page"], "link_forms": split(row["link_forms"]),
                      "written_by": row["written_by"], "checked_by": row["checked_by"], "approved": row["approved"]})
    return {"note": "Written by tools/build_glossary.py from data/glossary.csv; do not edit by hand.",
            "reference": TALISMAN, "terms": terms}


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    linked = sum(1 for t in data["terms"] if t["link_forms"])
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['terms'])} terms, {linked} linked in the page text")


if __name__ == "__main__":
    main()
