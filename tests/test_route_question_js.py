"""
Test: the page's JavaScript router gives the same class, route and rule as Python.

What this checks
    app/js/route_question.js routes typed questions in the page (build spec
    v3, 7.2: question type from the router). It must equal Chapter 12's
    route_question_graph on every bank and test question, and on made-up
    questions aimed at each rule in turn; its escalation messages must equal
    escalation_message. app/data/routing.json equals a rebuild.

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
from ragbook.ch12_routing import ESCALATION_REASONS, escalation_message, route_question_graph

ROOT = Path(__file__).parent.parent
NEEDS_NODE = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
QUESTION_FILES = ["questions.jsonl", "routing_test_5_november.jsonl", "routing_test_6_november.jsonl",
                  "parameters_test.jsonl", "ch14_fair_test.jsonl"]

# One or more made-up questions for each rule, in the rules' order.
MADE_UP = [
    "https://data.worldbank.org/indicator/SP.POP.TOTL",
    "What does AB.CDE.FGH measure?",
    "How does the UK compare with Switzerland?",
    "What if India had grown faster?",
    "Japan’s GNI per head in 2030?",
    "Was the euro area's GNI in 2025 revised?",
    "What was Ireland's real NNI per head in 2020?",
    "What are the components of growth in Japan?",
    "Will the UK be richer in 2035?",
    # A forecast year after 2029 is beyond the data first; only a year that dates a
    # revision ("revised ... in") reaches the forecast rule.
    "Will GDP be revised in 2035?",
    "Should the UK cut interest rates?",
    "Is India's growth sustainable?",
    "Suppose China grew by 5 per cent.",
    "Is China catching up?",
    "What is GNI per head in Japan now, and ten years ago?",
    "How does GNI per head in Japan now compare with ten years ago?",
    "Why was the UK's GDP revised?",
    "How was Japan's GDP in 2020 revised in 2023?",
    "Could India's growth be affected by unmeasured work?",
    "Why do the UK and Japan differ in hours worked?",
    "What is the UK's GNI per head?",
    "What drove India's growth?",
    "What was the UK's population in 2019?",
    "Which pizza topping is best for a picnic?",
    "What is a deflator?",
    "",
]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_routing_data")


def run(questions, rules):
    script = ("const fs=require('fs');const r=require(process.argv[1]);"
              "const routing=JSON.parse(fs.readFileSync(process.argv[2],'utf-8'));"
              "const c=JSON.parse(fs.readFileSync(0,'utf-8'));"
              "process.stdout.write(JSON.stringify({routes:c.questions.map(q=>r.routeQuestion(routing,q)),"
              "messages:c.rules.map(x=>r.escalationMessage(routing,x))}));")
    out = subprocess.run(["node", "-e", script, str(ROOT / "app" / "js" / "route_question.js"), str(build.OUT)],
                         input=json.dumps({"questions": questions, "rules": rules}),
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


def test_routing_data_matches_rebuild():
    assert json.loads(build.OUT.read_text(encoding="utf-8")) == json.loads(
        json.dumps(build.build(), ensure_ascii=False))


@NEEDS_NODE
def test_js_routes_as_python():
    context = load("build_bank_replies").load_context()
    questions = [q["question"] for name in QUESTION_FILES
                 for q in load_passages(ROOT / "data" / "question_bank" / name)] + MADE_UP
    rules = list(ESCALATION_REASONS)
    got = run(questions, rules)
    for question, js in zip(questions, got["routes"]):
        python = route_question_graph(question, context["known_words"], context["titles"],
                                      context["last_years"], context["economies"])
        assert tuple(js) == python, question
    for rule, js in zip(rules, got["messages"]):
        assert tuple(js) == escalation_message(rule, context["titles"]), rule


def test_made_up_questions_reach_every_rule():
    context = load("build_bank_replies").load_context()
    rules = {route_question_graph(q, context["known_words"], context["titles"], context["last_years"],
                                  context["economies"])[2] for q in MADE_UP}
    assert len(rules) == 21, sorted(rules)
