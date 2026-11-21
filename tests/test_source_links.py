"""
Test: every passage and every data series has a source link with two dates.

What this checks
    Each corpus source (data/corpus/source_links.csv) and each data series
    the measures use, in each edition (data/series/series_links.csv), has an
    https link, the document's own date and the date it was read. The date
    read comes after the document date. "not stated" is allowed for a
    document date the publisher does not give, so the gap is visible.

Why it matters
    A link with only the date read hides an old document (lesson L1, from
    Agri Map Navigator: a 2024 annual report marked "Checked Nov 2026").
    Whether each link still opens is checked by tools/check_source_links.py
    before each release, not here: tests do not use the internet.

Chapter: front matter (repository rules). Runs on every change.
"""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def check_dates(row):
    assert row["url"].startswith("https://"), row
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", row["date_read"]), row
    if row["document_date"] != "not stated":
        assert DATE.match(row["document_date"]), row
        assert row["document_date"] <= row["date_read"], row


def test_every_passage_source_has_a_link_with_two_dates():
    links = {row["source_code"]: row for row in read_csv(DATA / "corpus" / "source_links.csv")}
    with open(DATA / "corpus" / "passages.jsonl", encoding="utf-8") as file:
        used = {json.loads(line)["source_code"] for line in file if line.strip()}
    assert set(links) == used
    for row in links.values():
        check_dates(row)


def test_every_series_has_a_link_with_two_dates_per_edition():
    rows = read_csv(DATA / "series" / "series_links.csv")
    keys = [(row["series"], row["edition"]) for row in rows]
    assert len(keys) == len(set(keys))
    vocabulary = read_csv(DATA / "knowledge_graph" / "controlled_vocabulary.csv")
    needed = {code.strip() for term in vocabulary for code in term["series"].split("|") if code.strip()}
    assert {row["series"] for row in rows} == needed
    for row in rows:
        check_dates(row)
        if row["series"].startswith("PWT."):
            assert row["edition"] == "PWT 11.0"
        else:
            assert row["url"] == f"https://data.worldbank.org/indicator/{row['series']}"
