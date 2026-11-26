"""
Test: the page reads a typed question in parts (A5, decision 24).

What this checks
    app/data/reading.json equals a rebuild by tools/build_reading_data.py.
    app/js/read_question.js reads economies, years, editions and measures as
    its rules say, on made-up questions (not the test questions, which score
    the reading). The embeddings, once the workflow "reading embeddings" has
    made them, cover every measure name and question, and the browser's 16-bit
    and full-precision models rank the measures as Python's do.

Chapter: none (demonstrator, gate A5). Runs on every change; the JavaScript
tests are skipped where Node.js is not installed.
"""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
NEEDS_NODE = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
MEASURE_EMBEDDINGS = ROOT / "app" / "data" / "measure_embeddings.json"
CHECK = ROOT / "data" / "answers" / "a5_embedding_check.json"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_reading_data")


def read(questions):
    script = ("const fs=require('fs');const {readQuestion}=require(process.argv[1]);"
              "const r=JSON.parse(fs.readFileSync(process.argv[2],'utf-8'));"
              "const qs=JSON.parse(fs.readFileSync(0,'utf-8'));"
              "process.stdout.write(JSON.stringify(qs.map(q=>readQuestion(r,q))));")
    out = subprocess.run(["node", "-e", script, str(ROOT / "app" / "js" / "read_question.js"),
                          str(build.OUT)], input=json.dumps(questions), capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


def test_reading_data_matches_rebuild():
    assert json.loads(build.OUT.read_text(encoding="utf-8")) == json.loads(
        json.dumps(build.build(), ensure_ascii=False))


def test_short_forms_come_from_names_only():
    assert build.short_forms("GNI per head at purchasing power parities") == [
        "GNI per head at purchasing power parities", "GNI per head", "GNI per head at PPP",
        "GNI per capita at purchasing power parities", "GNI per capita", "GNI per capita at PPP"]
    assert build.short_forms("population, total") == ["population, total", "population"]


@NEEDS_NODE
def test_parts_read_by_the_rules():
    got = read(["What was Japan's GNI per head at PPP in 2019 and 2021?",
                "Has Britain's population risen over the last five years, compared with Switzerland?",
                "Was the euro area's GDP per capita at PPP revised since 2015?",
                "What if the UK had grown faster?"])
    assert got[0]["economies"] == ["JPN"] and got[0]["years"] == ["2019", "2021"]
    assert got[0]["measures"] == ["gni_per_head_ppp"] and got[0]["editions"] == ["latest"]
    assert got[1]["economies"] == ["GBR", "other"] and got[1]["years"] == ["latest-5", "latest"]
    assert got[1]["measures"] == ["population"]
    assert got[2]["editions"] == ["latest", "archive"] and got[2]["years"] == ["2015", "latest"]
    assert got[2]["measures"] == ["gdp_per_head_ppp"]
    assert got[3]["change"] is True and got[3]["economies"] == ["GBR"]


@pytest.mark.skipif(not MEASURE_EMBEDDINGS.exists(), reason="the workflow has not made the embeddings yet")
def test_embeddings_cover_every_name_and_question():
    reading = json.loads(build.OUT.read_text(encoding="utf-8"))
    texts = json.loads(MEASURE_EMBEDDINGS.read_text(encoding="utf-8"))["texts"]
    assert [(t["measure"], t["text"]) for t in texts] == [
        (m, name) for m, item in reading["measures"].items() for name in item["names"]]
    assert all(len(t["vector"]) == 384 for t in texts)
    versions = json.loads(CHECK.read_text(encoding="utf-8"))["versions"]
    for dtype in ("fp16", "fp32"):       # the 8-bit model disagrees on some questions
        check = versions[dtype]
        assert check["same_best_measure"] == check["same_top_three"] == check["questions"], dtype


def test_demonstrator_note_counts_match_the_score():
    """The note's numbers are the scored ones (data/answers/a5_reading_scores_test.json)."""
    import csv
    import re
    with open(build.NOTES, encoding="utf-8", newline="") as file:
        note = next(r for r in csv.DictReader(file) if r["id"] == "typed_questions")
    assert note["approved"] and note["reason"]
    totals = json.loads((ROOT / "data" / "answers" / "a5_reading_scores_test.json").read_text(
        encoding="utf-8"))["totals"]["all"]
    numbers = [int(n) for n in re.findall(r"\b\d+\b", note["text"])]
    assert numbers == [totals["questions"], totals["all_right"], totals["questions"],
                       totals["measures"], totals["questions"]]
