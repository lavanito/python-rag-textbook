"""Build the demonstrator page's questions and answers (A5).

Run from the repository folder:
    python tools/build_faq.py
It writes app/data/faq.json from data/faq.csv. The wording is written and
approved by the vertical domain expert (24 November 2026); change it in the
CSV, not in the JSON. The old FAQ on Drive is retired. A test
(tests/test_faq.py) rebuilds the file and fails if it differs.
"""

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "faq.csv"
OUT = REPO / "app" / "data" / "faq.json"


def build():
    with open(SOURCE, encoding="utf-8", newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda row: int(row["order"]))
    return {"note": "Written by tools/build_faq.py from data/faq.csv; do not edit by hand.",
            "questions": [{"question": r["question"], "answer": r["answer"],
                           "written_by": r["written_by"], "date": r["date"]} for r in rows]}


def main():
    page = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(page, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(page['questions'])} questions")


if __name__ == "__main__":
    main()
