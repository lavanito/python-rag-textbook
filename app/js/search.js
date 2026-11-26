// search.js: the passages for a typed question (A5; build spec v3, 7.3).
//
// What this file does
//   Finds the three best passages for a typed question, as the book does it,
//   in the same order and with the Python names in camelCase:
//   - Chapter 8's filters first: the licence filter for the use mode, then
//     the edition filter (filter_passages); withheld passages are listed with
//     the reason.
//   - Chapter 5's query expansion (expand_question): the other names of each
//     concept the question names, and of the concepts linked to it by
//     same_as, are added to the question.
//   - Chapter 3's BM25 (KeywordIndex.rank with "bm25") over the passages
//     kept, top three; passages scoring zero are left out.
//   For each passage found it also says why: the question's own words found
//   in it ("keyword") and the words added by expansion ("expansion").
//
// Inputs
//   search: app/data/search.json (tools/build_search_data.py).
//
// Output
//   findPassages(search, question, useMode) returns
//   { passages: [{ passage, keyword, expansion }], withheld, expanded }.
//
// Tested by tests/test_search_js.py: the same passages as Python for every
// bank and test question in both use modes.

// Chapter 1's split_into_words and Chapter 3's search_words.
function searchWords(search, text) {
  for (const mark of search.typographic_marks) text = text.replaceAll(mark, " ");
  const punctuation = new Set(search.punctuation);
  const common = new Set(search.common_words);
  let out = "";
  for (const ch of text.toLowerCase()) out += punctuation.has(ch) ? " " : ch;
  return out.split(/\s+/).filter((w) => w && !common.has(w));
}

// Chapter 8's licence_filter, edition_filter and filter_passages.
function licenceFilter(search, passages, useMode) {
  const allowed = search.use_modes[useMode];
  const kept = [], withheld = [];
  for (const p of passages) {
    if (allowed.includes(p.licence_class)) kept.push(p);
    else withheld.push({ id: p.id, filter: "licence",
                         reason: `licence: '${p.licence_class}' is not allowed in ${useMode} use` });
  }
  return [kept, withheld];
}

function editionsNamed(search, question) {
  const q = question.toLowerCase();
  return search.editions.filter((code) => search.edition_names[code].some((n) => q.includes(n.toLowerCase())));
}

function editionFilter(search, passages, question) {
  const named = editionsNamed(search, question);
  const editions = search.editions;
  const newest = {};
  for (const p of passages) {
    if (!editions.includes(p.source_code)) continue;
    const position = editions.indexOf(p.source_code);
    if (position > (p.topic in newest ? newest[p.topic] : -1)) newest[p.topic] = position;
  }
  const kept = [], withheld = [];
  for (const p of passages) {
    const code = p.source_code;
    let reason = "";
    if (editions.includes(code) && named.length && !named.includes(code)) {
      reason = `edition: the question asks for the ${named.map((c) => search.edition_names[c][0]).join(" and ")}`;
    } else if (editions.includes(code) && !named.length && editions.indexOf(code) < newest[p.topic]) {
      reason = `edition: the ${search.edition_names[editions[newest[p.topic]]][0]} has a passage on '${p.topic}'`;
    }
    if (reason) withheld.push({ id: p.id, filter: "edition", reason });
    else kept.push(p);
  }
  return [kept, withheld];
}

function filterPassages(search, question, useMode) {
  const [byLicence, withheldLicence] = licenceFilter(search, search.passages, useMode);
  const [kept, withheldEdition] = editionFilter(search, byLicence, question);
  return [kept, [...withheldLicence, ...withheldEdition]];
}

// Chapter 5's phrase_positions, concepts_in and expand_question.
function phrasePositions(search, phrase, words) {
  const phraseWords = searchWords(search, phrase);
  if (!phraseWords.length) return [];
  const size = phraseWords.length, found = [];
  for (let start = 0; start + size <= words.length; start++) {
    if (phraseWords.every((w, i) => words[start + i] === w)) found.push([start, start + size]);
  }
  return found;
}

function alwaysInsideLongerName(id, places, matches) {
  for (const [start, end] of places) {
    let inside = false;
    for (const [other, otherPlaces] of matches) {
      if (other === id) continue;
      for (const [s, e] of otherPlaces) if (e - s > end - start && s <= start && end <= e) inside = true;
    }
    if (!inside) return false;
  }
  return true;
}

function conceptsIn(search, question) {
  const words = searchWords(search, question);
  const matches = [];
  for (const id of search.concepts) {
    const places = search.names[id].flatMap((name) => phrasePositions(search, name, words));
    if (places.length) matches.push([id, places]);
  }
  return matches.filter(([id, places]) => !alwaysInsideLongerName(id, places, matches)).map(([id]) => id);
}

function expandQuestion(search, question) {
  const extra = [];
  for (const id of conceptsIn(search, question)) {
    for (const same of [id, ...search.same_as[id]]) {
      for (const name of search.names[same]) if (!extra.includes(name)) extra.push(name);
    }
  }
  return extra.length ? question + " " + extra.join(" ") : question;
}

// Chapter 3's BM25 and KeywordIndex.rank.
function bm25Rank(search, passages, question, howMany = 3, k1 = 1.5, b = 0.75) {
  const lists = passages.map((p) => searchWords(search, p.text));
  const frequencies = {};
  for (const words of lists) for (const w of new Set(words)) frequencies[w] = (frequencies[w] || 0) + 1;
  const n = passages.length;
  const average = lists.reduce((t, w) => t + w.length, 0) / n;
  const questionWords = [...new Set(searchWords(search, question))];
  const scored = [];
  lists.forEach((words, position) => {
    const counts = {};
    for (const w of words) counts[w] = (counts[w] || 0) + 1;
    const ratio = words.length / average;
    let score = 0;
    for (const w of questionWords) {
      if (!(w in counts)) continue;
      const idf = Math.log(1 + (n - frequencies[w] + 0.5) / (frequencies[w] + 0.5));
      const tf = counts[w];
      score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * ratio));
    }
    if (score > 0) scored.push([score, position]);
  });
  scored.sort((x, y) => y[0] - x[0]);
  return scored.slice(0, howMany).map(([, position]) => ({ passage: passages[position], words: new Set(lists[position]) }));
}

function findPassages(search, question, useMode) {
  const [kept, withheld] = filterPassages(search, question, useMode);
  const expanded = expandQuestion(search, question);
  const own = [...new Set(searchWords(search, question))];
  const added = [...new Set(searchWords(search, expanded))].filter((w) => !own.includes(w));
  const passages = bm25Rank(search, kept, expanded).map(({ passage, words }) => ({
    passage, keyword: own.filter((w) => words.has(w)), expansion: added.filter((w) => words.has(w)) }));
  return { passages, withheld, expanded };
}

const api = { findPassages, searchWords, filterPassages, conceptsIn, expandQuestion, bm25Rank };
if (typeof module !== "undefined") module.exports = api;
else globalThis.searchCode = api;
