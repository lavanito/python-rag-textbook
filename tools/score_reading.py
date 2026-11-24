"""Score the reading of typed questions in parts (A5, decision 24).

Run from the repository folder, with Node.js:
    python tools/score_reading.py bank      # the bank questions the rules were set on
    python tools/score_reading.py test      # the 78 test questions, once their labels are approved
Each question is read by app/js/read_question.js, with its embedding from
data/embeddings/reading_questions.json (Python's; the browser's ranks agree,
data/answers/a5_embedding_check.json). A part is right when it equals the
label, order aside: economies, years, editions, measures. Writes
data/answers/a5_reading_scores_<set>.json with the commit of the reading code.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ragbook.ch01_python_basics import load_passages   # noqa: E402

BANK = REPO / "data" / "question_bank"
PARTS = ["economies", "years", "editions", "measures"]
# Labels for each set. The routing tests' labels are in two files: the 14 routed
# to code (Chapter 13) and the other 34 (drafted by Claude, approved by the
# vertical domain expert).
SETS = {
    "bank": [("bank", "parameters_7_november.jsonl", "questions.jsonl")],
    "test": [("routing test 5 Nov", "parameters_7_november.jsonl", "routing_test_5_november.jsonl"),
             ("routing test 5 Nov", "parameters_routing_tests.jsonl", "routing_test_5_november.jsonl"),
             ("routing test 6 Nov", "parameters_7_november.jsonl", "routing_test_6_november.jsonl"),
             ("routing test 6 Nov", "parameters_routing_tests.jsonl", "routing_test_6_november.jsonl"),
             ("parameters test", "parameters_test.jsonl", "parameters_test.jsonl"),
             ("Chapter 14 fair test", "ch14_fair_test.jsonl", "ch14_fair_test.jsonl")],
}
SCRIPT = """
const fs = require('fs');
const { readQuestion } = require(process.argv[1]);
const reading = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
const measures = JSON.parse(fs.readFileSync(process.argv[3], 'utf-8'));
const cases = JSON.parse(fs.readFileSync(0, 'utf-8'));
process.stdout.write(JSON.stringify(cases.map(c => readQuestion(reading, c.question, { vector: c.vector, measures }))));
"""


def cases(set_name):
    found = []
    for label, label_file, question_file in SETS[set_name]:
        questions = {q["id"]: q for q in load_passages(BANK / question_file)}
        for record in load_passages(BANK / label_file):
            if record["id"] not in questions:
                continue
            if "approved" in record and not record["approved"]:
                sys.exit(f"{record['id']}: label not approved yet")
            found.append({"set": label, "id": record["id"], "question": questions[record["id"]]["question"],
                          "label": {part: record[part] for part in PARTS}})
    return found


def read(found):
    vectors = json.loads((REPO / "data" / "embeddings" / "reading_questions.json").read_text(encoding="utf-8"))
    payload = [{"question": c["question"], "vector": vectors["questions"][c["id"]]} for c in found]
    out = subprocess.run(["node", "-e", SCRIPT, str(REPO / "app" / "js" / "read_question.js"),
                          str(REPO / "app" / "data" / "reading.json"),
                          str(REPO / "app" / "data" / "measure_embeddings.json")],
                         input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


def commit_of(*paths):
    return subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%H", "--", *paths],
                          capture_output=True, text=True, check=True).stdout.strip()


def score(set_name):
    found = cases(set_name)
    rows, totals = [], {}
    for c, got in zip(found, read(found)):
        right = {part: sorted(got[part]) == sorted(c["label"][part]) for part in PARTS}
        rows.append({"set": c["set"], "id": c["id"], "right": right, "all_right": all(right.values()),
                     "read": {part: got[part] for part in PARTS}, "how": got["how"], "label": c["label"]})
        for key in [c["set"], "all"]:
            t = totals.setdefault(key, {"questions": 0, "all_right": 0, **{p: 0 for p in PARTS}})
            t["questions"] += 1
            t["all_right"] += all(right.values())
            for part in PARTS:
                t[part] += right[part]
    return {"note": "Written by tools/score_reading.py; do not edit by hand.",
            "set": set_name,
            "reading_code_commit": commit_of("app/js/read_question.js", "app/data/reading.json",
                                             "app/data/measure_embeddings.json"),
            "totals": totals, "questions": rows}


def main():
    set_name = sys.argv[1] if len(sys.argv) > 1 else "bank"
    result = score(set_name)
    out = REPO / "data" / "answers" / f"a5_reading_scores_{set_name}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for key, t in result["totals"].items():
        print(f"{key}: {t['questions']} questions; all parts right {t['all_right']}; "
              + "; ".join(f"{p} {t[p]}" for p in PARTS))


if __name__ == "__main__":
    main()
