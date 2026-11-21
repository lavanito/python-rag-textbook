"""
Copy each term's alternative labels from the controlled vocabulary into the
knowledge graph's aliases, so aliases are written in one place only.

Inputs
    data/knowledge_graph/controlled_vocabulary.csv: the governed list of
    terms. Alternative labels are separated by " | " (the import format of
    Talisman's SKOS editor).

Outputs
    data/knowledge_graph/entities.csv, rewritten: for every thing whose id is
    in the vocabulary, the aliases column becomes the vocabulary's
    alternative labels, separated by "; ". Other rows are unchanged.

Run
    python tools/sync_vocabulary_aliases.py

    Edit the vocabulary, never the aliases of those things in entities.csv.
    tests/test_vocabulary.py fails if the two differ.
"""
import csv
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent / "data" / "knowledge_graph"


def vocabulary_aliases(folder=FOLDER):
    """
    Each vocabulary id and its aliases in the knowledge graph's form.

    Example:
        vocabulary_aliases()["japan"] returns "Japanese"
    """
    with open(folder / "controlled_vocabulary.csv", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    return {row["id"]: "; ".join(a.strip() for a in row["altLabel"].split("|") if a.strip())
            for row in rows}


def main(folder=FOLDER):
    aliases = vocabulary_aliases(folder)
    with open(folder / "entities.csv", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        things = list(reader)
    changed = 0
    for thing in things:
        if thing["id"] in aliases and thing["aliases"] != aliases[thing["id"]]:
            thing["aliases"] = aliases[thing["id"]]
            changed += 1
    with open(folder / "entities.csv", "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, columns, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(things)
    print(f"{changed} things' aliases changed")


if __name__ == "__main__":
    main()
