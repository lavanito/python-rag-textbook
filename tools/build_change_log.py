"""Build the data for the demonstrator's change log for readers (A5, lesson L8).

Run from the repository folder:
    python tools/build_change_log.py
It copies data/change_log.csv (written and approved by people, one row per
dated change a reader should know about) into app/data/change_log.json, newest
first. Add a row to the CSV when an edition, the corpus, the knowledge graph,
the vocabulary or the method changes, then rerun.
"""

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "change_log.csv"
OUT = REPO / "app" / "data" / "change_log.json"


def build():
    with open(SOURCE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {"title": "What has changed", "status": "approved by the vertical domain expert, 23 Nov 2026",
            "entries": list(reversed(rows))}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}")
