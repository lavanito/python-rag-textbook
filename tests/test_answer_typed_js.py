"""
Test: a typed question gets the reply the bank builder gives its route.

What this checks
    app/js/answer_typed.js puts a typed question together in the page. For
    every bank and test question in both use modes, routed by the page's
    router:
    - escalated, series-title and not-built replies equal the bank builder's
      (tools/build_bank_replies.py) for that route and rule;
    - a passage reply (R4) quotes, in the bank builder's format, the passages
      Python finds with the filters, query expansion and BM25;
    - a code reply is the locked block for the parts read from the question;
    - every reply has text and a trace starting with the route.
    app/data/page.json equals a rebuild, and its wording ids are unique.

Chapter: none (demonstrator, gate A5). The JavaScript tests are skipped
where Node.js is not installed.
"""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ragbook.ch01_python_basics import load_passages
from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import KeywordIndex
from ragbook.ch05_hybrid_search import KnowledgeGraph, expand_question
from ragbook.ch08_filters import filter_passages

ROOT = Path(__file__).parent.parent
NEEDS_NODE = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
QUESTION_FILES = ["questions.jsonl", "routing_test_5_november.jsonl", "routing_test_6_november.jsonl",
                  "parameters_test.jsonl", "ch14_fair_test.jsonl"]
MADE_UP = ["What does SP.POP.TOTL measure?", "What will Japan's population be in 2031?",
           "How does China now compare with the United States three years ago, and what explains the change?",
           "Is the United States doing better than the euro area?", "What is GDI?",
           "How much are unpaid household services worth in the United Kingdom?"]
MODES = ["non-commercial", "commercial"]
DATA = {"routing": "routing", "reading": "reading", "figures": "figures", "search": "search",
        "topics": "outside_topics", "page": "page"}


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


page_data = load("build_page_data")


def run(cases):
    files = {key: str(ROOT / "app" / "data" / f"{name}.json") for key, name in DATA.items()}
    script = ("const fs=require('fs');const a=require(process.argv[1]);const L=require(process.argv[2]);"
              "const files=JSON.parse(process.argv[3]);const data={};"
              "for(const k in files)data[k]=JSON.parse(fs.readFileSync(files[k],'utf-8'));"
              "const c=JSON.parse(fs.readFileSync(0,'utf-8'));"
              "process.stdout.write(JSON.stringify(c.map(([q,m])=>{const r=a.answerTyped(data,q,m);"
              "return {route:r.route,kind:r.kind,text:r.text,ids:r.found.passages.map(p=>p.passage.id),"
              "first:r.steps[0].step,locked:r.parameters&&r.kind==='code'?L.reply(data.figures,q,r.parameters,r.route.class):null,"
              "readAs:r.readAs&&r.readAs.line}})));")
    out = subprocess.run(["node", "-e", script, str(ROOT / "app" / "js" / "answer_typed.js"),
                          str(ROOT / "app" / "js" / "locked_block.js"), json.dumps(files)],
                         input=json.dumps(cases), capture_output=True, text=True, encoding="utf-8",
                         check=True).stdout
    return json.loads(out)


def test_page_data_matches_rebuild():
    assert json.loads(page_data.OUT.read_text(encoding="utf-8")) == json.loads(
        json.dumps(page_data.build(), ensure_ascii=False))


def test_page_wording_ids_are_unique():
    import csv
    with open(page_data.WORDING, encoding="utf-8", newline="") as f:
        ids = [row["id"] for row in csv.DictReader(f)]
    assert len(ids) == len(set(ids))


@NEEDS_NODE
def test_typed_replies_follow_the_bank_builder():
    bank = load("build_bank_replies")
    context = bank.load_context()
    corpus = load_corpus()
    graph = KnowledgeGraph(corpus)
    questions = [q["question"] for name in QUESTION_FILES
                 for q in load_passages(ROOT / "data" / "question_bank" / name)] + MADE_UP
    cases = [(q, m) for q in questions for m in MODES]
    kinds = set()
    for (question, mode), js in zip(cases, run(cases)):
        route, rule = js["route"]["route"], js["route"]["rule"]
        assert js["text"] and js["first"] == "route", question
        topic = js["text"].startswith("Outside the data")
        if topic:
            kinds.add("outside topic")
            continue
        q = {"id": "typed", "question": question}
        if route == "escalate":
            expected = bank.escalated_reply(q, rule, context)[mode]["page"]
        elif route == "R1":
            expected = bank.series_reply(q, context)[mode]["page"]
        elif route == "R6":
            expected = bank.fixed_reply(f"{bank.NOT_BUILT}\n{bank.DEMONSTRATOR_NOT_BUILT}", context)[mode]["page"]
        elif route == "R4":
            kept, _ = filter_passages(corpus, question, mode)
            found = KeywordIndex(kept).rank(expand_question(graph, question), "bm25", how_many=3)
            assert js["ids"] == [p["id"] for p in found], question
            expected = bank.passage_block(found, [])
        elif route == "clarify":
            expected = bank.CLARIFY_LINE
            assert js["readAs"].startswith("Read as: "), question
        else:
            expected = js["locked"]
            assert js["kind"] == "code" and js["readAs"].startswith("Read as: "), question
        assert js["text"] == expected, (question, mode)
        kinds.add(route)
    assert {"escalate", "R1", "R6", "R4", "clarify", "R2", "outside topic"} <= kinds, kinds
