"""Build the page's topics outside the data (A5; Lavan, 24 Nov 2026, option (b)).

Run from the repository folder:
    python tools/build_outside_topics.py
It writes app/data/outside_topics.json from data/outside_topics.csv: for each
topic none of the measures covers, the words that mark a question about it,
the approved line the page shows, and its source. The first topic is unpaid
household services: a question about it gets the line and is passed to an
analyst, instead of passages that do not mention it. The rule lives in the
page only; the book's router (Chapter 12) is unchanged. A test rebuilds this
file and fails if it differs, or if a row is not approved.
"""

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "outside_topics.csv"
OUT = REPO / "app" / "data" / "outside_topics.json"


def build():
    with open(SOURCE, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    return {"note": "Written by tools/build_outside_topics.py from data/outside_topics.csv; do not edit by hand.",
            "topics": [{"id": r["id"], "trigger_words": [w.strip() for w in r["trigger_words"].split(";")],
                        "line": r["line"], "source": r["source"], "url": r["url"],
                        "date_read": r["date_read"], "approved": r["approved"]} for r in rows]}


def main():
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
