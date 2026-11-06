"""
Write data/series/last_year.csv: the last year of real NNI per head for each
economy in each WDI edition, the "ragged edge" of the data.

Inputs
    A local clone of github.com/lavanito/nni-model, given as the first
    argument. Its own loader and decomposition class decide which years have
    every input, so nothing is retyped here.

Outputs
    data/series/last_year.csv with columns economy, edition, last_year. A
    blank last_year means the economy is not in that edition.

Run
    python tools/build_last_year.py /path/to/nni-model
"""
import csv
import glob
import sys
from pathlib import Path

MODEL = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(MODEL))
from nni_model.data import Snapshot, build_euro_area, load_csv  # noqa: E402
from nni_model.decomposition import NNIDecomposition  # noqa: E402

ECONOMIES = ["USA", "EA21", "GBR", "CHN", "IND", "JPN", "IRL"]
EDITIONS = {
    "latest": sorted(glob.glob(str(MODEL / "data" / "wdi" / "wdi_latest_*.csv"))),
    "archive": [str(MODEL / "data" / "wdi" / "wdi_archive_202403.csv")],
}
OUT = Path(__file__).resolve().parent.parent / "data" / "series" / "last_year.csv"

rows = []
for edition, files in EDITIONS.items():
    snapshot = Snapshot(edition)
    for file in files:
        load_csv(file, snapshot)
    try:
        build_euro_area(snapshot)
    except TypeError:
        pass  # the archive edition has no euro area members
    for economy in ECONOMIES:
        model = NNIDecomposition(snapshot, economy)
        years = [year for year in range(2000, 2026) if model.levels(year) is not None]
        rows.append({"economy": economy, "edition": edition,
                     "last_year": years[-1] if years else ""})

with open(OUT, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["economy", "edition", "last_year"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} rows to {OUT}")
