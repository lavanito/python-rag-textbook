"""Build three parts of the demonstrator page's text from the records (A5).

Run from the repository folder:
    python tools/build_page_text.py
It writes, in app/data/:
- lessons.json: "Lessons for a production version" (decision 26), read from
  Chapter 15, section 15.7 (book/ch15_token_cost.md), so the page and the
  book say the same thing.
- at_full_scale.json: the "In this demonstration version / In a full-scale
  production version" table (build spec v3, component 13, agreed 17 November
  2026; rows rewritten and approved 27 November 2026), from data/at_full_scale.csv.
- walkthrough.json: the six lifecycle steps (build spec v3, component 13).
  For each step: the process sentence and chapters (data/walkthrough.csv,
  approved 24 November 2026), the steps and the means used for each (front
  matter, "Steps and the means used", table "Answering one question") and the "At full scale"
  rows that belong to the step.
- sources.json: the sources page (build spec v3, 17.8): the ten corpus
  sources with their terms for quoting (data/corpus/SOURCES.md) and links
  with two dates (data/corpus/source_links.csv), and the data sources by
  edition (data/series/series_links.csv).
No text is typed here: change the records, then run this tool. A test
(tests/test_page_text.py) rebuilds the files and fails if they differ.
"""

import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
OUT = REPO / "app" / "data"
CHAPTER_15 = REPO / "book" / "ch15_token_cost.md"
LESSONS_HEADING = "## 15.7 Lessons for a production version"

# Data sources: all three are CC BY 4.0 (A2 data list, decision log section 3).
DATA_SOURCES = {
    "WDI": {"name": "World Bank, World Development Indicators", "licence": "CC BY 4.0"},
    "PWT": {"name": "Penn World Table 11.0 (Groningen Growth and Development Centre)", "licence": "CC BY 4.0"},
}


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Lessons, from Chapter 15.7
# ---------------------------------------------------------------------------

def numbered_items(lines):
    """Numbered list items; an indented paragraph belongs to the item above it."""
    items = []
    for line in lines:
        found = re.match(r"^(\d+)\. (.*)$", line)
        if found:
            items.append(found.group(2))
        elif line.startswith("    ") and line.strip() and items:
            items[-1] += "\n\n" + line.strip()
    return items


def lessons():
    text = CHAPTER_15.read_text(encoding="utf-8")
    section = text.split(LESSONS_HEADING, 1)[1].split("\n## ", 1)[0]
    parts = {}
    for block in section.split("\n### ")[1:]:
        heading, body = block.split("\n", 1)
        parts[heading.strip()] = numbered_items(body.splitlines())
    return {"note": "Written by tools/build_page_text.py from book/ch15_token_cost.md, section 15.7; "
                    "do not edit by hand.",
            "source": "Chapter 15, section 15.7",
            "what_worked": parts["What worked"],
            "what_a_production_version_needs": parts["What a production version needs"]}


# ---------------------------------------------------------------------------
# At full scale
# ---------------------------------------------------------------------------

def at_full_scale():
    rows = read_csv(DATA / "at_full_scale.csv")
    return {"note": "Written by tools/build_page_text.py from data/at_full_scale.csv; do not edit by hand.",
            "columns": ["In this demonstration version", "In a full-scale production version"],
            "rows": [{"in_this_build": r["in_this_build"], "at_full_scale": r["at_full_scale"],
                      "agreed": r["agreed"]} for r in sorted(rows, key=lambda r: int(r["order"]))]}


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def corpus_sources():
    """The corpus sources table in SOURCES.md, joined to the links with two dates."""
    lines = (DATA / "corpus" / "SOURCES.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Code |"))
    header = [cell.strip() for cell in lines[start].strip("|").split("|")]
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append(dict(zip(header, [cell.strip() for cell in line.strip("|").split("|")])))
    links = {r["source_code"]: r for r in read_csv(DATA / "corpus" / "source_links.csv")}
    return [{"code": r["Code"], "source": r["Source"], "edition": r["Edition"],
             "terms_for_quoting": r["Terms for quoting"], "status": r["Status"],
             "url": links[r["Code"]]["url"], "document_date": links[r["Code"]]["document_date"],
             "date_read": links[r["Code"]]["date_read"]} for r in rows]


def data_sources():
    """One entry per data source and edition, with the series it supplies."""
    entries = {}
    for r in read_csv(DATA / "series" / "series_links.csv"):
        producer = "PWT" if r["edition"].startswith("PWT") else "WDI"
        entry = entries.setdefault(r["edition"], {
            "edition": r["edition"], **DATA_SOURCES[producer],
            "document_date": r["document_date"], "date_precision": r["date_precision"],
            "date_read": r["date_read"], "ppp_benchmark": "", "series": []})
        entry["series"].append({"code": r["series"], "url": r["url"]})
        entry["ppp_benchmark"] = entry["ppp_benchmark"] or r["ppp_benchmark"]
    return list(entries.values())


def sources():
    return {"note": "Written by tools/build_page_text.py from data/corpus/SOURCES.md, "
                    "data/corpus/source_links.csv and data/series/series_links.csv; do not edit by hand.",
            "corpus": corpus_sources(), "data": data_sources()}


# ---------------------------------------------------------------------------
# Walkthrough
# ---------------------------------------------------------------------------

FRONT_MATTER = REPO / "book" / "front_matter.md"
TASKS_HEADING = "### Answering one question"


def answering_tasks():
    """Step -> the means used (code, the language model or a named person), from the
    front matter's "Answering one question" table."""
    text = FRONT_MATTER.read_text(encoding="utf-8")
    table = text.split(TASKS_HEADING, 1)[1].split("\n### ", 1)[0]
    tasks = {}
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] not in ("Step", "---"):
            tasks[cells[0]] = cells[1]
    return tasks


def walkthrough():
    tasks = answering_tasks()
    full_scale = {r["order"]: r for r in read_csv(DATA / "at_full_scale.csv")}
    steps = []
    for row in sorted(read_csv(DATA / "walkthrough.csv"), key=lambda r: int(r["step"])):
        steps.append({
            "step": int(row["step"]), "title": row["title"], "process": row["process"],
            "chapters": row["chapters"].split(";"),
            "means": [{"step": t, "means": tasks[t]} for t in row["tasks"].split(";")],
            "at_full_scale": [{"in_this_build": full_scale[n]["in_this_build"],
                               "at_full_scale": full_scale[n]["at_full_scale"]}
                              for n in row["at_full_scale_rows"].split(";") if n],
            "approved": row["approved"]})
    return {"note": "Written by tools/build_page_text.py from data/walkthrough.csv, book/front_matter.md "
                    "and data/at_full_scale.csv; do not edit by hand.",
            "diagram": "The front matter's diagram \"Governed RAG · steps and tools\" (provenance sandwich, P2)",
            "steps": steps}


FILES = {"lessons.json": lessons, "at_full_scale.json": at_full_scale, "sources.json": sources,
         "walkthrough.json": walkthrough}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in FILES.items():
        (OUT / name).write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Wrote app/data/{name}")


if __name__ == "__main__":
    main()
