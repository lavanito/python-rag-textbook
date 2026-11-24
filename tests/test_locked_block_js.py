"""
Test: the page's JavaScript locked-block code gives the same text as Python.

What this checks
    app/js/locked_block.js builds the locked block in the page for typed
    questions (build spec v3, 7.2). For every bank question with parameters
    and the nine sharper questions, its text equals the stored one in
    app/data/bank_replies.json, comparison line included. For the other
    labelled questions (Chapters 13 and 14 test sets) and some harder cases
    (beyond the data, editions, unreadable years, unknown economies and
    measures), every part of its locked block equals Python's locked_block.
    Also: app/data/figures.json equals a rebuild by tools/build_figures.py,
    and app/js/nni.js is nni-model's js/nni.js at the commit requirements.txt
    pins.

Chapter: none (demonstrator, gate A5). Runs on every change; the JavaScript
tests are skipped where Node.js is not installed.
"""

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ragbook.ch01_python_basics import load_passages
from ragbook.ch12_routing import load_last_years
from ragbook.ch13_model_tool import NEW_QUESTION_FILE, PARAMETER_FILE, model_questions
from ragbook.ch14_answer_checks import FAIR_TEST_FILE, load_definitions, locked_block

ROOT = Path(__file__).parent.parent
FIGURES = ROOT / "app" / "data" / "figures.json"
RUNNER = ROOT / "app" / "js" / "run_locked_blocks.js"
NEEDS_NODE = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_figures = load("build_figures")
copy_nni_js = load("copy_nni_js")
BANK = json.loads((ROOT / "app" / "data" / "bank_replies.json").read_text(encoding="utf-8"))
FIELDS = ("economies", "years", "measures", "editions", "change")


def parameters_of(record):
    return {key: record[key] for key in FIELDS if key in record}


def run_js(cases, tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    out = subprocess.run(["node", str(RUNNER), str(FIGURES), str(path)],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


def bank_cases():
    """The bank questions with parameters, and the sharper questions, with the stored text."""
    labelled = {p["id"]: p for p in load_passages(PARAMETER_FILE)}
    cases = []
    for r in BANK["replies"]:
        stored = r["modes"]["non-commercial"]
        if r["id"] in labelled:
            cases.append({"id": r["id"], "question": r["question"], "class": r["class"],
                          "parameters": parameters_of(labelled[r["id"]]), "stored": stored["locked"]})
        for option in stored.get("options", []):
            cases.append({"id": f"{r['id']} {option['aspect']}", "question": option["question"], "class": None,
                          "parameters": option["parameters"], "stored": option["locked"]})
    return cases


# Harder cases, compared with Python: beyond the data, both editions, the
# archive's missing euro area, an unreadable year, years before the data,
# an economy and measures not in the data, Ireland, and spans of growth.
HARDER = [
    ("Japan's GNI per head in 2026?", {"economies": ["JPN"], "years": ["2026"], "measures": ["gni_per_head_ppp"]}),
    ("Was India's population revised?", {"economies": ["IND"], "years": ["2010", "2020"],
                                          "measures": ["population"], "editions": ["latest", "archive"]}),
    ("Was the euro area's GNI revised?", {"economies": ["EA21"], "years": [], "measures": ["gni"],
                                          "editions": ["latest", "archive"]}),
    ("UK in the nineties?", {"economies": ["GBR"], "years": ["1995"], "measures": ["gni_per_head_ppp"]}),
    ("UK in some year?", {"economies": ["GBR"], "years": ["soon"], "measures": ["gni_per_head_ppp"]}),
    ("Brazil's income?", {"economies": ["Brazil"], "years": ["2020"], "measures": ["gni_per_head_ppp"]}),
    ("Terms of trade and the moon?", {"economies": ["USA"], "years": ["2020"],
                                      "measures": ["terms_of_trade", "moon"]}),
    ("Ireland's real NNI per head since 2015?", {"economies": ["IRL"], "years": ["2015", "latest"],
                                                  "measures": ["real_nni_per_head_ppp", "nni_growth"]}),
    ("Has Ireland fallen behind the United States since 2010?",
     {"economies": ["IRL", "USA"], "years": ["2010", "latest-1"], "measures": ["gdp_per_head_ppp"]}),
    ("Why did employment in China fall, and spending, and the trend gap?",
     {"economies": ["CHN", "GBR"], "years": ["2008", "2024"],
      "measures": ["employment_rate", "spending_components", "trend_gap"]}),
    ("Average hours in Japan and India, latest", {"economies": ["JPN", "IND"], "years": ["latest"],
                                                  "measures": ["average_hours", "real_nni_per_hour"]}),
    ("Revisions to China's growth?", {"economies": ["CHN", "USA"], "years": ["2015", "2022"],
                                      "measures": ["real_gdp_growth", "nni_growth"],
                                      "editions": ["latest", "archive"]}),
]


def python_cases():
    """Labelled questions not in the bank, and the harder cases, for comparison with Python.
    Questions naming a euro area member other than Ireland are left out: the page knows
    only the economies it can read."""
    known = set(json.loads(FIGURES.read_text(encoding="utf-8"))["economies"])
    texts = {q["id"]: q for q in model_questions()}
    records = [dict(texts[r["id"]], **r) for r in load_passages(PARAMETER_FILE)]
    records += load_passages(NEW_QUESTION_FILE) + load_passages(FAIR_TEST_FILE)
    bank = {r["id"] for r in BANK["replies"]}
    cases = [{"id": r["id"], "question": r["question"], "class": r.get("class"),
              "parameters": parameters_of(r)} for r in records
             if r["id"] not in bank and all(e in known or len(e) != 3 for e in r["economies"])]
    for i, (question, parameters) in enumerate(HARDER):
        cases.append({"id": f"harder-{i + 1}", "question": question, "class": None,
                      "parameters": dict({"editions": ["latest"], "change": False}, **parameters)})
    return cases


def test_figures_match_rebuild():
    assert json.loads(FIGURES.read_text(encoding="utf-8")) == json.loads(
        json.dumps(build_figures.build(), ensure_ascii=False))


def test_nni_js_is_the_pinned_copy():
    record = json.loads(copy_nni_js.SOURCE_RECORD.read_text(encoding="utf-8"))
    assert record["commit"] == copy_nni_js.pinned_commit()
    assert record["sha256"] == hashlib.sha256(copy_nni_js.TARGET.read_bytes()).hexdigest()


def test_cases_cover_the_bank():
    cases = bank_cases()
    assert len([c for c in cases if " " not in c["id"]]) == 14
    assert len([c for c in cases if " " in c["id"]]) == 9
    assert len(python_cases()) >= 30


@NEEDS_NODE
def test_js_equals_stored_bank_replies(tmp_path):
    cases = bank_cases()
    for case, js in zip(cases, run_js(cases, tmp_path)):
        assert js["reply"] == case["stored"], case["id"]


@NEEDS_NODE
def test_js_equals_python(tmp_path):
    cases = python_cases()
    last_years, definitions = load_last_years(), load_definitions()
    for case, js in zip(cases, run_js(cases, tmp_path)):
        assert js["block"] == locked_block(case["question"], case["parameters"], last_years, definitions), case["id"]


@NEEDS_NODE
def test_js_knows_only_the_economies_it_reads(tmp_path):
    case = {"question": "Germany?", "class": None,
            "parameters": {"economies": ["DEU"], "years": ["2020"], "measures": ["gni"], "editions": ["latest"]}}
    js = run_js([case], tmp_path)[0]["block"]
    assert js["missing"][0].startswith("DEU is not in the data.")


def test_no_wording_typed_twice():
    """Approved wording reaches the page from figures.json, not typed in the JavaScript."""
    code = (ROOT / "app" / "js" / "locked_block.js").read_text(encoding="utf-8")
    wording = json.loads(FIGURES.read_text(encoding="utf-8"))["wording"]
    for name, text in wording.items():
        assert text[:30] not in code, name
    assert not re.search(r"Passed to an analyst|benchmark how each", code)
