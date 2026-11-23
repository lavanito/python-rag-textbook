"""Build the data for the demonstrator's coverage grid (A5, lesson L6).

Run from the repository folder:
    python tools/build_coverage_grid.py
It writes app/data/coverage_grid.json: the 16 measures against the six
economies, each cell "exact", "proxy" (a stand-in, flagged and rated at most
Low) or "no figure", with the years the NNI model can answer in the latest
edition, the first year flagged "nowcast" and the data quality rating of the
last year. Every cell comes from calling the NNI model tool (Chapter 13), not
from a typed table, and a test (tests/test_coverage_grid.py) rebuilds the
file and fails if it differs.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch13_model_tool import GAPS, MEASURES, call_model   # noqa: E402

OUT = REPO / "app" / "data" / "coverage_grid.json"
ECONOMIES = {"USA": "United States", "EA21": "euro area", "GBR": "United Kingdom",
             "JPN": "Japan", "CHN": "China", "IND": "India"}
YEARS = range(2000, 2030)


def cell(economy, measure):
    """One cell: kind, first and last year with a figure, first nowcast year, last year's DQR."""
    kind = "proxy" if "proxy" in MEASURES[measure] else "exact"
    replies = {y: call_model(economy, y, measure) for y in YEARS}
    years = [y for y, r in replies.items() if r.value is not None]
    if not years:
        return {"kind": "no figure"}
    nowcast = [y for y in years if any(f.startswith("nowcast") for f in replies[y].flags)]
    last = replies[max(years)]
    return {"kind": kind, "first": min(years), "last": max(years),
            "nowcast_from": min(nowcast) if nowcast else None, "dqr_last_year": last.dqr_band}


def build():
    rows = []
    for measure, m in MEASURES.items():
        row = {"measure": measure, "description": m["description"], "unit": m["unit"],
               "cells": {code: cell(code, measure) for code in ECONOMIES}}
        if "proxy" in m:
            row["how_it_differs"] = m["proxy"]["differs"]
            row["best_data"] = m["proxy"]["best_data"]
        rows.append(row)
    for measure, gap in GAPS.items():
        rows.append({"measure": measure, "description": gap["description"], "unit": None,
                     "cells": {code: {"kind": "no figure"} for code in ECONOMIES},
                     "best_data": gap["best_data"]})
    return {"title": "Coverage: 16 measures by six economies", "edition": "latest",
            "economies": ECONOMIES, "rows": rows}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}")
