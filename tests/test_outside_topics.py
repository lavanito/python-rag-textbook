"""
Test: a question about a topic none of the measures covers gets its approved line (A5).

What this checks
    app/data/outside_topics.json equals a rebuild from data/outside_topics.csv,
    and every row is approved. A question about unpaid household services gets
    the line, its source, and is passed to an analyst, with the locked block
    after it; other questions are unchanged. Among the bank and test questions,
    only u-15 names the topic (seen when the trigger words were drafted, so it
    is not a fair test of them).

Chapter: none (demonstrator, gate A5; Lavan, 24 Nov 2026, option (b)).
"""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ragbook.ch01_python_basics import load_passages

ROOT = Path(__file__).parent.parent
NEEDS_NODE = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
QUESTION_FILES = ["questions.jsonl", "routing_test_5_november.jsonl", "routing_test_6_november.jsonl",
                  "parameters_test.jsonl", "ch14_fair_test.jsonl"]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_outside_topics")
FIGURES = json.loads((ROOT / "app" / "data" / "figures.json").read_text(encoding="utf-8"))


def run(cases):
    script = ("const fs=require('fs');const t=require(process.argv[1]);"
              "const topics=JSON.parse(fs.readFileSync(process.argv[2],'utf-8'));"
              "const figures=JSON.parse(fs.readFileSync(process.argv[3],'utf-8'));"
              "const cs=JSON.parse(fs.readFileSync(0,'utf-8'));"
              "process.stdout.write(JSON.stringify(cs.map(c=>({ids:t.outsideTopics(topics,c.q).map(x=>x.id),"
              "text:t.withOutsideTopics(topics,figures,c.q,c.locked)}))));")
    out = subprocess.run(["node", "-e", script, str(ROOT / "app" / "js" / "outside_topics.js"), str(build.OUT),
                          str(ROOT / "app" / "data" / "figures.json")], input=json.dumps(cases),
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


def test_topics_match_rebuild_and_are_approved():
    built = build.build()
    assert json.loads(build.OUT.read_text(encoding="utf-8")) == json.loads(json.dumps(built, ensure_ascii=False))
    assert all(t["approved"] for t in built["topics"])
    assert built["topics"][0]["id"] == "unpaid_household_services"


@NEEDS_NODE
def test_question_about_unpaid_work_gets_the_line_and_escalates():
    line = build.build()["topics"][0]["line"]
    note = FIGURES["wording"]["escalation_note"]
    locked = "Figures (calculated from the data)\n- none"
    got = run([{"q": "How much is unpaid household work worth in the UK?", "locked": locked},
               {"q": "Why does GDP ignore the housework women do?", "locked": locked},
               {"q": "What was GNI per head in Japan in 2024?", "locked": locked}])
    assert got[0]["ids"] == got[1]["ids"] == ["unpaid_household_services"]
    assert got[0]["text"].startswith("Outside the data\n- " + line)
    assert got[0]["text"].count(note) == 1 and locked in got[0]["text"]
    assert got[2]["ids"] == [] and got[2]["text"] == locked


@NEEDS_NODE
def test_only_u15_names_the_topic():
    questions = [q for name in QUESTION_FILES for q in load_passages(ROOT / "data" / "question_bank" / name)]
    got = run([{"q": q["question"], "locked": ""} for q in questions])
    assert [q["id"] for q, g in zip(questions, got) if g["ids"]] == ["u-15"]
