// Checks the page's embeddings (transformers.js, as the browser runs them) rank
// the measures as Python's do (build spec v3, 7.2). Run by the GitHub workflow
// "reading embeddings", after tools/make_reading_embeddings.py:
//   node app/js/check_embeddings.mjs
// For every question in data/embeddings/reading_questions.json it embeds the
// question in JavaScript (Xenova/all-MiniLM-L6-v2, in its 8-bit, 16-bit and full
// precision versions), ranks the measures by meaning with both vectors, and writes
// data/answers/a5_embedding_check.json: for each version, the number of questions with
// the same best measure and the same top three, and the largest cosine difference.
import fs from "fs";
import { createRequire } from "module";
import { pipeline } from "@huggingface/transformers";

const require = createRequire(import.meta.url);
const { meaningScores } = require("./read_question.js");
const ROOT = new URL("../../", import.meta.url).pathname;
const read = (p) => JSON.parse(fs.readFileSync(ROOT + p, "utf-8"));

const measures = read("app/data/measure_embeddings.json");
const stored = read("data/embeddings/reading_questions.json").questions;
const texts = {};
for (const f of ["questions", "routing_test_5_november", "routing_test_6_november", "parameters_test", "ch14_fair_test"]) {
  for (const line of fs.readFileSync(`${ROOT}data/question_bank/${f}.jsonl`, "utf-8").split("\n")) {
    if (line.trim()) { const q = JSON.parse(line); texts[q.id] = q.question; }
  }
}
// Each version of the browser model: 8-bit (about 23 MB), 16-bit and full precision.
const versions = {};
for (const dtype of ["q8", "fp16", "fp32"]) {
  const embed = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", { dtype });
  let sameBest = 0, sameTop3 = 0, worst = 0, n = 0;
  const differ = [];
  for (const [id, pythonVector] of Object.entries(stored)) {
    const out = await embed(texts[id], { pooling: "mean", normalize: true });
    const py = meaningScores({ vector: pythonVector, measures });
    const js = meaningScores({ vector: Array.from(out.data), measures });
    n += 1;
    if (py[0][0] === js[0][0]) sameBest += 1; else differ.push(id);
    if (py.slice(0, 3).map((x) => x[0]).join() === js.slice(0, 3).map((x) => x[0]).join()) sameTop3 += 1;
    const jsScores = Object.fromEntries(js);
    for (const [m, s] of py) worst = Math.max(worst, Math.abs(s - jsScores[m]));
  }
  versions[dtype] = { questions: n, same_best_measure: sameBest, same_top_three: sameTop3,
                      largest_cosine_difference: Number(worst.toFixed(4)), best_measure_differs: differ };
}
const result = { note: "Written by app/js/check_embeddings.mjs; do not edit by hand.",
                 javascript_model: "Xenova/all-MiniLM-L6-v2", python_model: measures.model, versions };
fs.writeFileSync(`${ROOT}data/answers/a5_embedding_check.json`, JSON.stringify(result, null, 1) + "\n");
console.log(JSON.stringify(result));
