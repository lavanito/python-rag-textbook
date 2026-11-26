"""
Test: the demonstrator page is built from the files it says it reads.

What this checks
    app/index.html (tools/build_page.py) equals a rebuild from app/page.html,
    app/data/ and app/js/; it holds every data file and script; nothing in it
    loads from outside except the embedding model (transformers.js), so the
    page works without it. app/data/traces.json equals a rebuild.

Chapter: none (demonstrator, gate A5).
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


page = load("build_page")
traces = load("build_traces")


def test_page_matches_rebuild():
    assert page.OUT.read_text(encoding="utf-8") == page.build()


def test_page_holds_every_data_file_and_script():
    built = page.OUT.read_text(encoding="utf-8")
    start = built.index('<script id="page-data" type="application/json">') + len('<script id="page-data" type="application/json">')
    data = json.loads(built[start:built.index("</script>", start)])
    assert sorted(data) == sorted(page.DATA_FILES)
    for name in page.SCRIPTS:
        assert f"// app/js/{name}" in built


def test_only_the_embedding_model_loads_from_outside():
    built = page.OUT.read_text(encoding="utf-8")
    assert built.count("import(") == 1 and "cdn.jsdelivr.net/npm/@huggingface/transformers@" in built
    assert "<script src=" not in built


def test_traces_match_rebuild():
    assert json.loads(traces.OUT.read_text(encoding="utf-8")) == json.loads(
        json.dumps(traces.build(), ensure_ascii=False))
    assert set(json.loads(traces.OUT.read_text(encoding="utf-8"))["traces"]) == {
        r["id"] for r in json.loads((ROOT / "app" / "data" / "bank_replies.json").read_text(encoding="utf-8"))["replies"]}
