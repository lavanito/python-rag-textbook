"""
Open every source link and report the ones that fail (lesson L1).

Inputs
    data/corpus/source_links.csv: one link per corpus source.
    data/series/series_links.csv: one link per data series and edition.

Outputs
    One line per distinct link: the HTTP status, or the error. Exit code 1
    if any link fails. Nothing is written.

    Some sites refuse requests from scripts (HTTP 403) but open in a
    browser. A World Bank indicator page is then checked through the World
    Bank's data API instead; any other 403 is listed as "open by hand" and
    does not count as a failure.

Run
    python tools/check_source_links.py

    Run it before each release, on a machine with internet access. A link
    that opens can still point to an old document: compare document_date
    with the publisher's latest edition by eye.
"""
import csv
import sys
import urllib.error
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


HEADERS = {"User-Agent": "Mozilla/5.0 (python-rag-textbook link check)",
           "Accept": "text/html,application/pdf,application/json,*/*"}
WORLD_BANK = "https://data.worldbank.org/indicator/"


def status(url):
    """The HTTP status of a GET request (403 included), or the error as text."""
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:       # report every kind of failure, then go on
        return f"failed: {error}"


def check(url):
    """One line of the report and whether the link counts as failed.

    Example:
        check("https://doi.org/10.34894/FABVLR") returns ("200  https://doi.org/...", False)
    """
    result = status(url)
    if result == 200:
        return f"200  {url}", False
    if result == 403 and url.startswith(WORLD_BANK):
        code = url[len(WORLD_BANK):]
        api = status(f"https://api.worldbank.org/v2/indicator/{code}?format=json")
        if api == 200:
            return f"200 (World Bank API)  {url}", False
    if result == 403:
        return f"403, open by hand  {url}", False
    return f"{result}  {url}", True


def main():
    failures = 0
    by_hand = 0
    for url in links():
        line, failed = check(url)
        failures += failed
        by_hand += line.startswith("403")
        print(line)
    print(f"{failures} of {len(links())} links failed; {by_hand} to open by hand")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
