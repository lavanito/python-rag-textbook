"""
Write the size bands for changes: how large a revision, a change over time
or a gap between economies is (the domain expert, 16 November 2026).

Every figure the NNI model gives in both WDI editions is compared: the
latest edition minus the archive edition, for the same economy, measure and
year. Levels are compared in log points (100 times the change in the natural
log, close to a per cent change); rates and shares as a plain difference in
percentage points. A revision smaller than 0.005 shows as 0.00 at the
finest digits the page uses, so it counts as no revision. All other revisions are pooled into one distribution
and cut into three roughly equal parts:

    large   below the 16.5th percentile or above the 83.5th
    small   from the 33rd to the 67th percentile, inclusive
    medium  in between

The cuts are not symmetric around zero: most revisions are upward.

Inputs
    The NNI model through ragbook.ch13_model_tool.call_model, both editions,
    years 1990 to 2022 (the archive edition ends in 2022), for the six
    economies. The euro area has no archive figures, and the Penn World
    Table measures have one edition, so neither gives revisions.

Outputs
    data/series/revisions.csv: one row per economy, measure and year.
    data/series/revision_bands.csv: the four cuts (percentile and value).

Run
    python tools/build_revision_bands.py
"""
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ragbook.ch13_model_tool import MEASURES, call_model, is_rate, log_change  # noqa: E402

ECONOMIES = ["USA", "EA21", "GBR", "CHN", "IND", "JPN"]
YEARS = range(1990, 2023)
CUTS = [16.5, 33, 67, 83.5]
ZERO = 0.005     # below this a change shows as 0.00, so it counts as no change
REVISIONS_FILE = ROOT / "data" / "series" / "revisions.csv"
BANDS_FILE = ROOT / "data" / "series" / "revision_bands.csv"


def percentile(values, share):
    """
    The value below which share per cent of the sorted values fall, with
    straight-line steps between neighbours (Excel's PERCENTILE.INC and
    numpy's default).

    Example:
        percentile([1, 2, 3, 4], 50) returns 2.5
    """
    ordered = sorted(values)
    position = (len(ordered) - 1) * share / 100
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def main():
    rows = []
    for measure in MEASURES:
        for economy in ECONOMIES:
            for year in YEARS:
                old = call_model(economy, year, measure, "archive")
                new = call_model(economy, year, measure, "latest")
                if old.value is None or new.value is None:
                    continue
                rate = is_rate(old.unit)
                change = new.value - old.value if rate else log_change(old.value, new.value)
                rows.append({"measure": measure, "economy": economy, "year": year,
                             "unit": "percentage points" if rate else "log points",
                             "archive": old.value, "latest": new.value,
                             "revision": round(change, 6)})
    with open(REVISIONS_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    non_zero = [r["revision"] for r in rows if abs(r["revision"]) >= ZERO]
    with open(BANDS_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["percentile", "value"])
        for share in CUTS:
            writer.writerow([share, round(percentile(non_zero, share), 6)])
    print(f"{len(rows)} revisions, {len(non_zero)} not zero; "
          f"median {statistics.median(non_zero):.3f}; written {BANDS_FILE.name}")


if __name__ == "__main__":
    main()
