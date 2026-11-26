"""
Test: the page's passage search for typed questions finds what Python finds.

What this checks
    app/js/search.js finds passages for a typed question in the page (build
    spec v3, 7.3): Chapter 8's filters, Chapter 5's query expansion, then
    Chapter 3's BM25, top three. For every bank and test question in both use
    modes it must give the same passages, the same withheld records and the
    same expanded question as the Python functions. app/data/search.json
    equals a rebuild.

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
MADE_UP = ["What did the 2008 SNA call depreciation?", "How do you get from GNI to net national income?",
           "What is GDI?", "Which pizza topping is best?", ""]
MODES = ["non-commercial", "commercial"]

spec = importlib.util.spec_from_file_location("build_search_data", ROOT / "tools" / "build_search_data.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def python_find(question, use_mode, corpus, graph):
    kept, withheld = filter_passages(corpus, question, use_mode)
    expanded = expand_question(graph, question)
    found = KeywordIndex(kept).rank(expanded, "bm25", how_many=3)
    return [p["id"] for p in found], withheld, expanded


def test_search_data_matches_rebuild():
    assert json.loads(build.OUT.read_text(encoding="utf-8")) == json.loads(
        json.dumps(build.build(), ensure_ascii=False))


@NEEDS_NODE
def test_js_finds_the_same_passages_as_python():
    questions = [q["question"] for name in QUESTION_FILES
                 for q in load_passages(ROOT / "data" / "question_bank" / name)] + MADE_UP
    cases = [(q, m) for q in questions for m in MODES]
    script = ("const fs=require('fs');const s=require(process.argv[1]);"
              "const data=JSON.parse(fs.readFileSync(process.argv[2],'utf-8'));"
              "const c=JSON.parse(fs.readFileSync(0,'utf-8'));"
              "process.stdout.write(JSON.stringify(c.map(([q,m])=>{const r=s.findPassages(data,q,m);"
              "return {ids:r.passages.map(x=>x.passage.id),withheld:r.withheld,expanded:r.expanded,"
              "why:r.passages.map(x=>x.keyword.length+x.expansion.length)}})));")
    out = subprocess.run(["node", "-e", script, str(ROOT / "app" / "js" / "search.js"), str(build.OUT)],
                         input=json.dumps(cases), capture_output=True, text=True, encoding="utf-8",
                         check=True).stdout
    corpus = load_corpus()
    graph = KnowledgeGraph(corpus)
    for (question, mode), js in zip(cases, json.loads(out)):
        ids, withheld, expanded = python_find(question, mode, corpus, graph)
        assert js["ids"] == ids, (question, mode)
        assert js["withheld"] == withheld, (question, mode)
        assert js["expanded"] == expanded, question
        assert all(n > 0 for n in js["why"]), question     # every passage found says why
    assert len(cases) == 2 * (134 + len(MADE_UP))
