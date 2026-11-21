"""
Open every source link and report the ones that fail (lesson L1).

Inputs
    data/corpus/source_links.csv: one link per corpus source.
    data/series/series_links.csv: one link per data series and edition.

Outputs
    One line per distinct link: the HTTP status, or the error. Exit code 1
    if any link fails. Nothing is written.

Run
    python tools/check_source_links.py

    Run it before each release, on a machine with internet access. A link
    that opens can still point to an old document: compare document_date
    with the publisher's latest edition by eye.
"""
import csv
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
FILES = [DATA / "corpus" / "source_links.csv", DATA / "series" / "series_links.csv"]


def links():
    """Every distinct URL in the two link tables, in file order."""
    found = []
    for path in FILES:
        with open(path, encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                if row["url"] not in found:
                    found.append(row["url"])
    return found


def status(url):
    """The HTTP status of a GET request, or the error as text."""
    request = urllib.request.Request(url, headers={"User-Agent": "python-rag-textbook link check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except Exception as error:       # report every kind of failure, then go on
        return f"failed: {error}"


def main():
    failures = 0
    for url in links():
        result = status(url)
        if result != 200:
            failures += 1
        print(f"{result}  {url}")
    print(f"{failures} of {len(links())} links failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
