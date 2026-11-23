"""
Test: the change log for readers is dated, in order, and agrees with the data.

What this checks
    data/change_log.csv has one row per dated change, oldest first, each with
    a date as precise as it is known. Each data edition named in it has the
    same date and PPP benchmark as data/series/series_links.csv. The page's
    copy (app/data/change_log.json) equals a rebuild (lesson L8; gate B3s).

Chapter: none (demonstrator, gate A5). Runs on every change.
"""

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_change_log", ROOT / "tools" / "build_change_log.py")
log = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


ROWS = read_csv(ROOT / "data" / "change_log.csv")


def test_rows_are_dated_and_in_order():
    lengths = {"day": 10, "month": 7, "year": 4}
    for row in ROWS:
        assert len(row["date"]) == lengths[row["date_precision"]], row
        assert row["area"] in {"data edition", "corpus", "knowledge graph", "vocabulary", "method"}, row
        assert row["change"].endswith("."), row
    dates = [row["date"] for row in ROWS]
    assert dates == sorted(dates)


def test_editions_match_the_series_links():
    links = read_csv(ROOT / "data" / "series" / "series_links.csv")
    for link in links:
        if link["ppp_benchmark"]:
            match = [r for r in ROWS if r["date"] == link["document_date"] and r["area"] == "data edition"]
            assert match, link["edition"]
            assert link["ppp_benchmark"] in match[0]["change"]


def test_page_copy_equals_the_rebuild():
    stored = json.loads(log.OUT.read_text(encoding="utf-8"))
    assert stored == log.build()
