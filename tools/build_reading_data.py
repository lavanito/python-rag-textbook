"""Build what the page needs to read a typed question in parts (A5, decision 24).

Run from the repository folder:
    python tools/build_reading_data.py
It writes app/data/reading.json, read by app/js/read_question.js:
- economies: each economy's names from the knowledge graph (decision 30), the
  euro area members, and the names of economies not in the data (Chapter 12,
  fourth round);
- measures: the catalogue of measures (decision 25): for each of the 13
  measures in the controlled vocabulary, its preferred name and other names;
  for the 3 measures with no figure, their description and the graph's names;
- other_concepts: names of concepts in the knowledge graph that are not
  measures here (GDP, investment, depreciation ...): a question naming one is
  read as asking for a measure not in the data ("other");
- revision words (Chapter 12), the first year of the data and the last years;
- the browser model and the demonstrator note for typed questions (approved
  by the vertical domain expert, data/demonstrator_notes.csv);
- the words of the "Read as" line (data/read_as_wording.csv), each with the
  date the vertical domain expert approved it, or blank while a draft.
The texts embedded for reading the measure by meaning are the measures'
names listed here (tools/make_reading_embeddings.py). A test rebuilds this
file and fails if it differs.
"""

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch12_routing import NOT_IN_DATA_FOURTH, REVISION_WORDS, load_economies  # noqa: E402
from ragbook.ch13_model_tool import FIRST_YEAR, GAPS, MEASURES                      # noqa: E402

OUT = REPO / "app" / "data" / "reading.json"
NOTES = REPO / "data" / "demonstrator_notes.csv"
READ_AS = REPO / "data" / "read_as_wording.csv"
# The model the page loads to read the measure by meaning (Lavan, 26 Nov 2026,
# option (a)): 16-bit ranks the measures as Python's model does on all 134
# questions; the 8-bit model (about 23 MB) disagrees on 9
# (data/answers/a5_embedding_check.json).
BROWSER_MODEL = {"name": "Xenova/all-MiniLM-L6-v2", "dtype": "fp16"}
GRAPH = REPO / "data" / "knowledge_graph"


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def names(text):
    return [name.strip() for name in text.split("|") if name.strip()] if "|" in text else \
           [name.strip() for name in text.split(";") if name.strip()]


# Short forms made by fixed rules from each name, so "GNI per head at PPP" and
# "population" match "GNI per head at purchasing power parities" and
# "population, total". Made from the names, not from any question.
def short_forms(name):
    forms = [name]
    for cut in (" (", ", total", " at ", ", split into parts"):
        forms += [f.split(cut)[0] for f in forms if cut in f]
    forms += [f.replace("purchasing power parities", "PPP") for f in forms if "purchasing power parities" in f]
    forms += [f.replace("per head", "per capita") for f in forms if "per head" in f]
    return list(dict.fromkeys(form.strip() for form in forms))


def catalogue():
    """Each measure the NNI model tool knows, with its names, in the tool's order."""
    vocabulary = {row["notation"]: row for row in read_csv(GRAPH / "controlled_vocabulary.csv")
                  if row["scheme"] == "measure"}
    entities = {row["id"]: row for row in read_csv(GRAPH / "entities.csv")}
    measures = {}
    for measure, m in MEASURES.items():
        row = vocabulary[measure]
        vocabulary_names = [row["prefLabel"]] + names(row["altLabel"]) + names(row["hiddenLabel"])
        by_rule = [f for n in vocabulary_names for f in short_forms(n) if f not in vocabulary_names]
        measures[measure] = {"figure": True, "description": m["description"],
                             "names": vocabulary_names + list(dict.fromkeys(by_rule)),
                             "names_by_rule": list(dict.fromkeys(by_rule))}
    for measure, gap in GAPS.items():
        graph = entities.get(measure)
        extra = [graph["label"]] + names(graph["aliases"]) if graph else []
        measures[measure] = {"figure": False, "description": gap["description"],
                             "names": [gap["description"]] + extra, "names_by_rule": []}
    return measures


def other_concepts(measures):
    """Names of graph concepts that are not a measure here, nor one of its names."""
    taken = {name.lower() for m in measures.values() for name in m["names"]}
    found = {}
    for row in read_csv(GRAPH / "entities.csv"):
        if row["type"] != "Concept" or row["id"] in measures:
            continue
        concept_names = [n for n in [row["label"]] + names(row["aliases"]) if n.lower() not in taken]
        if concept_names:
            found[row["id"]] = concept_names
    return found


def build():
    economies = load_economies()
    measures = catalogue()
    last_years = {}
    with open(REPO / "data" / "series" / "last_year.csv", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            last_years[f"{row['economy']}|{row['edition']}"] = int(row["last_year"]) if row["last_year"] else None
    return {"note": "Written by tools/build_reading_data.py; do not edit by hand.",
            "economies": economies["names"], "members": economies["members"],
            "not_in_data": NOT_IN_DATA_FOURTH,
            "measures": measures, "other_concepts": other_concepts(measures),
            "revision_words": REVISION_WORDS, "first_year": FIRST_YEAR, "last_years": last_years,
            "browser_model": BROWSER_MODEL,
            "demonstrator_note": next(r["text"] for r in read_csv(NOTES) if r["id"] == "typed_questions"),
            "read_as_wording": {r["id"]: {"text": r["text"], "approved": r["approved"]} for r in read_csv(READ_AS)}}


def main():
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}: {len(data['measures'])} measures, "
          f"{sum(len(m['names']) for m in data['measures'].values())} measure names, "
          f"{len(data['other_concepts'])} other concepts")


if __name__ == "__main__":
    main()
