"""
Test: the coverage grid matches what the NNI model tool can answer.

What this checks
    tools/build_coverage_grid.py rebuilds app/data/coverage_grid.json by
    calling the NNI model tool for every measure, economy and year. The stored
    file must equal the rebuilt one (lessons L6 and L9; gate B3s), and every
    stand-in and missing figure names the best data.

Chapter: none (demonstrator, gate A5). Runs on every change.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_coverage_grid", ROOT / "tools" / "build_coverage_grid.py")
grid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grid)
BUILT = grid.build()


def test_stored_grid_equals_the_rebuilt_grid():
    stored = json.loads(grid.OUT.read_text(encoding="utf-8"))
    assert stored == json.loads(json.dumps(BUILT))


def test_sixteen_measures_by_six_economies():
    assert len(BUILT["rows"]) == 16
    kinds = [c["kind"] for row in BUILT["rows"] for c in row["cells"].values()]
    assert len(kinds) == 96
    assert (kinds.count("exact"), kinds.count("proxy"), kinds.count("no figure")) == (60, 18, 18)


def test_every_stand_in_and_missing_figure_names_the_best_data():
    for row in BUILT["rows"]:
        if any(c["kind"] != "exact" for c in row["cells"].values()):
            assert row["best_data"], row["measure"]


def test_proxies_are_rated_at_most_low():
    for row in BUILT["rows"]:
        for c in row["cells"].values():
            if c["kind"] == "proxy":
                assert c["dqr_last_year"] == "Low"
