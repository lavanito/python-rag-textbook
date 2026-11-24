"""Build the figures the page's JavaScript locked-block code reads (A5).

Run from the repository folder:
    python tools/build_figures.py
It writes app/data/figures.json: every result the NNI model tool (Chapter 13,
call_model) gives for the seven economies the page reads, each year from 2000
to 2025, the 12 measures with a figure and both editions, with the value,
flags, DQR band and reason, and the parts of NNI growth. It also writes what
the locked-block code needs alongside: measure descriptions, units, sources
and proxies, the measures with no figure, the last year by economy and
edition, the size cuts, the approved definitions and the approved wording.

The page works out everything else in JavaScript (app/js/locked_block.js):
which calls to make, the digits shown (nni.js), the comparisons, the premise
line and the escalation. tests/test_locked_block_js.py checks the JavaScript
gives the same locked block as Python, and tests/test_figures.py rebuilds this
file and fails if it differs.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from nni_model import dqr                                             # noqa: E402

from ragbook.ch12_routing import DISPLAY_NAMES, load_economies, load_last_years  # noqa: E402
from ragbook.ch13_model_tool import (ECONOMY_CODES, ESCALATION_NOTE, FIRST_YEAR, GAPS,  # noqa: E402
                                     MEASURES, PART_NAMES, call_model, load_edition)
from ragbook.ch14_answer_checks import (DEMONSTRATOR_ANALYST, SIZE_CUTS, SIZE_NOTE,  # noqa: E402
                                        SIZE_NOTE_OTHER, ZERO, load_definitions)
from tools.build_bank_replies import COMPARING_CLASSES, COMPARISON_LINE, DEFINITIONS_HEADING  # noqa: E402

OUT = REPO / "app" / "data" / "figures.json"
LAST_YEAR = 2025
EDITIONS = ("latest", "archive")


def economies():
    """The economies the page reads from a question: the knowledge graph's names (decision 30)."""
    return list(load_economies()["names"])


def results():
    """Every result with a value, keyed "economy|year|measure|edition", and the
    DQR reasons, each written once; a result gives its reason by position."""
    found, reasons = {}, []
    for code in economies():
        for edition in EDITIONS:
            for measure in MEASURES:
                for year in range(FIRST_YEAR, LAST_YEAR + 1):
                    r = call_model(code, year, measure, edition)
                    if r.value is None:
                        continue
                    if r.dqr_reason not in reasons:
                        reasons.append(r.dqr_reason)
                    record = {"value": r.value, "flags": r.flags, "dqr_band": r.dqr_band,
                              "dqr_reason": reasons.index(r.dqr_reason)}
                    if r.parts:
                        record["parts"] = r.parts
                    found[f"{code}|{year}|{measure}|{edition}"] = record
    return found, reasons


def build():
    last_years = load_last_years()
    found, reasons = results()
    return {
        "note": "Written by tools/build_figures.py; do not edit by hand.",
        "economies": economies(),
        "economy_codes": ECONOMY_CODES,
        "members": load_economies()["members"],
        "display_names": DISPLAY_NAMES,
        "editions": {e: load_edition(e).edition for e in EDITIONS},
        "first_year": FIRST_YEAR,
        "last_years": {f"{code}|{edition}": year for (code, edition), year in last_years.items()},
        "measures": {name: {key: m[key] for key in ("description", "unit", "source", "count", "proxy")
                            if key in m} for name, m in MEASURES.items()},
        "gaps": GAPS,
        "part_names": PART_NAMES,
        "bands": {name: band for band, name in dqr.NAMES.items()},
        "size_cuts": SIZE_CUTS,
        "zero": ZERO,
        "definitions": {m: {"means": d["means"], "leaves_out": d["leaves_out"], "passages": d["passages"]}
                        for m, d in load_definitions().items()},
        "wording": {"escalation_note": ESCALATION_NOTE, "demonstrator_analyst": DEMONSTRATOR_ANALYST,
                    "size_note": SIZE_NOTE, "size_note_other": SIZE_NOTE_OTHER,
                    "comparison_line": COMPARISON_LINE, "definitions_heading": DEFINITIONS_HEADING},
        "comparing_classes": sorted(COMPARING_CLASSES),
        "reasons": reasons,
        "results": found,
    }


def main():
    figures = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(figures, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(figures['results'])} results, "
          f"{OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
