// read_question.js: reading a typed question in parts (A5, decision 24).
//
// What this file does
//   Reads the economies, years, editions and measures a typed question asks
//   about, so the page can show "Read as: Japan · GNI per head at PPP · 2024"
//   with a drop-down list to correct each part, and then build the locked
//   block (locked_block.js). Each part says how it was found.
//   - Economies: names from the knowledge graph, matched as whole words; a
//     named economy not in the data is read as "other".
//   - Years: four-digit years; "latest" for words such as "latest", "today",
//     "current" and for "since 2015"; "last five years" as latest-5 to latest.
//   - Editions: both editions when the question uses a revision word.
//   - Measures: first by name, from the catalogue of measures (the controlled
//     vocabulary's names); if no name matches, by meaning: the question's
//     embedding (all-MiniLM-L6-v2) against the embeddings of the measures'
//     names; if neither finds a measure, "other" when the question names a
//     concept from the knowledge graph that is not a measure here, else none.
//
// Inputs
//   reading: app/data/reading.json (tools/build_reading_data.py).
//   question: the typed text.
//   meaning (optional): { vector, measures } where vector is the question's
//     embedding and measures is app/data/measure_embeddings.json. Without it,
//     the measure is read by name only.
//
// Output
//   { economies, years, editions, measures, change, how }, the same fields as
//   the labelled parameters (Chapter 13), plus how each part was found.
//
// The rules and the two settings below were fixed on the bank questions
// before the reading was scored on the 78 test questions (Chapters 12 to 14).

// Settings for reading the measure by meaning (cosine similarity, 0 to 1).
const MEANING_MIN = 0.5;      // the best measure must score at least this
const MEANING_MARGIN = 0.05;  // other measures within this of the best are kept too

const LATEST_WORDS = ["latest", "last year", "today", "current", "currently", "most recent", "this year"];
const SCENARIO_WORDS = ["what if", "had been", "had grown", "had changed", "had continued"];
const NUMBER_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };

// Lower case, punctuation as spaces, single spaces, padded: as Chapter 1's split_into_words.
function words(text) {
  return " " + text.toLowerCase().replace(/[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~’‘“”]/g, " ")
    .split(/\s+/).filter(Boolean).join(" ") + " ";
}

function has(text, name) {
  return text.includes(words(name));
}

function readEconomies(reading, text) {
  const found = [], how = [];
  for (const [code, names] of Object.entries(reading.economies)) {
    const name = names.find((n) => has(text, n));
    if (name) { found.push(code); how.push(`"${name.trim()}"`); }
  }
  const other = reading.not_in_data.find((n) => has(text, n));
  if (other) { found.push("other"); how.push(`"${other}" (not in the data)`); }
  return [found, how];
}

function readYears(text) {
  const years = [...text.matchAll(/ ((?:19|20)\d\d) /g)].map((m) => m[1]);
  const how = years.map((y) => y);
  const since = / since (?:19|20)\d\d /.test(text);
  const latest = LATEST_WORDS.find((w) => has(text, w));
  const span = text.match(/ last (\w+) (years?|decades?) /);
  if (span) {
    let count = /^\d+$/.test(span[1]) ? Number(span[1]) : NUMBER_WORDS[span[1]] || 1;
    if (span[2].startsWith("decade")) count *= 10;
    years.push(`latest-${count}`, "latest");
    how.push(`"last ${span[1]} ${span[2]}"`);
  } else if (since || latest) {
    years.push("latest");
    how.push(since ? '"since"' : `"${latest}"`);
  }
  return [[...new Set(years)], how];
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return dot / Math.sqrt(na * nb);
}

// Each measure's best score: the highest cosine over its names.
function meaningScores(meaning) {
  const scores = {};
  for (const item of meaning.measures.texts) {
    const s = cosine(meaning.vector, item.vector);
    if (!(item.measure in scores) || s > scores[item.measure]) scores[item.measure] = s;
  }
  return Object.entries(scores).sort((a, b) => b[1] - a[1]);
}

function readMeasures(reading, text, meaning) {
  // By name: every measure one of whose names is in the question. A name inside
  // a longer matched name of another measure does not count.
  const matched = [];
  for (const [measure, m] of Object.entries(reading.measures)) {
    for (const name of m.names) if (has(text, name)) matched.push([measure, words(name)]);
  }
  const kept = matched.filter(([measure, name]) =>
    !matched.some(([other, longer]) => other !== measure && longer !== name && longer.includes(name)));
  const byName = [...new Set(kept.map(([measure]) => measure))];
  if (byName.length) {
    return [byName, byName.map((m) => `by name: "${kept.find(([x]) => x === m)[1].trim()}"`)];
  }
  if (meaning) {
    const ranked = meaningScores(meaning);
    const [best, top] = ranked[0];
    if (top >= MEANING_MIN) {
      const chosen = ranked.filter(([, s]) => s >= MEANING_MIN && s >= top - MEANING_MARGIN);
      return [chosen.map(([m]) => m), chosen.map(([m, s]) => `by meaning: ${s.toFixed(2)}`)];
    }
  }
  for (const [concept, names] of Object.entries(reading.other_concepts)) {
    const name = names.find((n) => has(text, n));
    if (name) return [["other"], [`"${name}" is not a measure here (${concept})`]];
  }
  return [[], []];
}

function readQuestion(reading, question, meaning = null) {
  const text = words(question);
  const [economies, economyHow] = readEconomies(reading, text);
  const [years, yearHow] = readYears(text);
  const revision = reading.revision_words.find((w) => question.toLowerCase().includes(w));
  const editions = revision ? ["latest", "archive"] : ["latest"];
  const [measures, measureHow] = readMeasures(reading, text, meaning);
  const change = SCENARIO_WORDS.some((w) => has(text, w));
  return { economies, years, editions, measures, change,
           how: { economies: economyHow, years: yearHow, editions: revision ? [`"${revision}"`] : [],
                  measures: measureHow } };
}

const api = { readQuestion, words, meaningScores, MEANING_MIN, MEANING_MARGIN };
if (typeof module !== "undefined") module.exports = api;
else globalThis.readQuestionCode = api;
