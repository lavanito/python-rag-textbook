"""Build the demonstrator as one self-contained page (A5; build spec v3, component 17).

Run from the repository folder, after the tools that write app/data/:
    python tools/build_page.py
It writes app/index.html from app/page.html: every file in app/data/ the
page reads, inside one JSON script element, and the page's JavaScript files
from app/js/, each inside its own function so their names do not clash. The
page needs no server: it opens from the file or as a published page. The only
thing it loads from outside is the embedding model for reading the measure
by meaning (transformers.js and all-MiniLM-L6-v2); where that cannot load,
the measure is read by name only (Lavan, 26 Nov 2026, option (a)).
A test rebuilds this file and fails if it differs.

    python tools/build_page.py --review <file>
writes a copy for reviewing the page's own wording instead: each piece of it
is followed by its id in data/page_wording.csv, in brackets like these: ⟦title⟧.
The copy is for the reviewer only and is not kept in the repository.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "app"
TEMPLATE = APP / "page.html"
OUT = APP / "index.html"

DATA_FILES = ["bank_replies", "figures", "reading", "routing", "search", "outside_topics", "page", "traces",
              "measure_embeddings", "method_and_caveats", "coverage_grid", "walkthrough", "at_full_scale",
              "lessons", "change_log", "faq", "sources", "glossary"]
# In the order they need each other: each reads the ones before it from globalThis.
SCRIPTS = ["nni.js", "locked_block.js", "read_question.js", "read_as.js", "route_question.js", "search.js",
           "outside_topics.js", "answer_typed.js"]


def script(name):
    code = (APP / "js" / name).read_text(encoding="utf-8")
    assert "</script" not in code.lower(), name
    if name == "nni.js":   # nni-model's file, unchanged: it sets module.exports, which becomes globalThis.nni
        code = f"var module = {{ exports: {{}} }};\n{code}\nglobalThis.nni = module.exports;"
    return f"<script>\n// app/js/{name}\n(function () {{\n{code}\n}})();\n</script>"


def build(review=False):
    data = {name: json.loads((APP / "data" / f"{name}.json").read_text(encoding="utf-8")) for name in DATA_FILES}
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("</", "<\\/").replace("<!--", "\\u003c!--")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*DATA*/", text, 1)
    page = page.replace("/*REVIEW*/false", "true" if review else "false", 1)
    return page.replace("/*SCRIPTS*/", "\n".join(script(name) for name in SCRIPTS), 1)


def main():
    review = "--review" in sys.argv
    out = Path(sys.argv[sys.argv.index("--review") + 1]) if review else OUT
    page = build(review)
    out.write_text(page, encoding="utf-8")
    if review:
        print(f"Wrote {out}: wording review copy")
        return
    print(f"Wrote {OUT.relative_to(REPO)}: {len(page.encode('utf-8')) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
