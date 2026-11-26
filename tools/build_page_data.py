"""Build the wording and lookups the page itself needs (A5; build spec v3, component 17).

Run from the repository folder:
    python tools/build_page_data.py
It writes app/data/page.json:
- the page's own wording (headings, labels, notes) from data/page_wording.csv,
  each with the date the vertical domain expert approved it (empty until he
  does);
- the reply wording approved for the bank replies (tools/build_bank_replies.py),
  so typed questions use the same words;
- the published title of each series in the data, for questions naming a
  series code (route R1);
- the three aspects of a vague question and the measure for each, from the
  sharper questions (build spec v3, 9.4).
A test rebuilds this file and fails if it differs.
"""

import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch12_routing import load_titles                       # noqa: E402

OUT = REPO / "app" / "data" / "page.json"
WORDING = REPO / "data" / "page_wording.csv"
REPLY_WORDING = ["PASSAGES_HEADING", "NO_DQR", "NO_PASSAGES", "SERIES_HEADING", "CLARIFY_LINE", "NOT_BUILT",
                 "DEMONSTRATOR_NOT_BUILT", "COMPARISON_LINE", "EXPLANATION_HEADING", "WITHHELD",
                 "DEMONSTRATOR_WITHHELD", "CORRECTED_HEADING"]


def bank_module():
    spec = importlib.util.spec_from_file_location("build_bank_replies", REPO / "tools" / "build_bank_replies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_wording():
    with open(WORDING, encoding="utf-8", newline="") as f:
        return {row["id"]: {"text": row["text"], "approved": row["approved"]} for row in csv.DictReader(f)}


def build():
    bank = bank_module()
    first = bank.SHARPER["amb-01"]
    return {
        "note": "Written by tools/build_page_data.py; do not edit by hand.",
        "wording": load_wording(),
        "reply_wording": {name: getattr(bank, name) for name in REPLY_WORDING},
        "series_titles": load_titles(),
        "aspects": [{"aspect": aspect, "measure": labels["measures"][0]} for aspect, _, labels in first],
    }


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    waiting = sum(1 for w in data["wording"].values() if not w["approved"])
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['wording'])} wording items ({waiting} awaiting approval)")


if __name__ == "__main__":
    main()
