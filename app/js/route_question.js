// route_question.js: the question type and route for a typed question (A5).
//
// What this file does
//   The JavaScript version of Chapter 12's fourth-round rules
//   (ragbook/ch12_routing.py, route_question_graph and the functions it
//   calls), rule by rule and in the same order. It gives the question's class
//   (Q1 to Q8, AMB or OUT), its route and the rule that decided, and, for an
//   escalated question, the reason and message (escalation_message).
//
// Inputs
//   routing: app/data/routing.json (tools/build_routing_data.py): the word
//     lists and patterns, read from the Python code, and the data they need.
//
// Output
//   routeQuestion(routing, question) returns [class, route, rule], as Python.
//
// Tested by tests/test_route_question_js.py: equal to Python on every bank
// and test question and on made-up questions for each rule.

// Chapter 1's split_into_words: lower case, ASCII punctuation as spaces.
const PUNCTUATION = new Set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~");

function splitIntoWords(text) {
  let out = "";
  for (const ch of text.toLowerCase()) out += PUNCTUATION.has(ch) ? " " : ch;
  return out.split(/\s+/).filter(Boolean);
}

// Chapter 2's topic_words: common words dropped, each word kept once.
function topicWords(routing, text) {
  const common = new Set(routing.common_words);
  const kept = [];
  for (const word of splitIntoWords(text)) if (!common.has(word) && !kept.includes(word)) kept.push(word);
  return kept;
}

function containsAny(question, phrases) {
  const text = question.toLowerCase();
  return phrases.some((p) => text.includes(p));
}

function pattern(routing, name, flags = "") {
  return new RegExp(routing.patterns[name], flags);
}

function economiesIn(routing, question) {
  const text = " " + splitIntoWords(question).join(" ") + " ";
  return routing.economies.filter(([, names]) => names.some((n) => text.includes(" " + n + " "))).map(([code]) => code);
}

function allYears(question) {
  return [...question.matchAll(/\b(?:19|20)[0-9]{2}\b/g)].map((m) => Number(m[0]));
}

function dataYears(routing, question) {
  const years = allYears(question);
  for (const m of question.matchAll(pattern(routing, "REVISION_DATE", "g"))) {
    const i = years.indexOf(Number(m[1]));
    if (i !== -1) years.splice(i, 1);
  }
  return years;
}

function lastYear(routing, economy, edition) {
  const row = routing.last_years.find(([e, ed]) => e === economy && ed === edition);
  if (!row) throw new Error(`No last year for ${economy}, ${edition}`);   // Python: KeyError
  return row[2];
}

function beyondTheEdgeGraph(routing, question) {
  const years = dataYears(routing, question);
  if (!years.length) return null;
  const top = Math.max(...years);
  const named = economiesIn(routing, question);
  const editions = ["latest"];
  if (containsAny(question, routing.word_lists.REVISION_WORDS)) editions.push("archive");
  if (!named.length) {
    const latest = Math.max(...routing.last_years.filter(([, ed, y]) => ed === "latest" && y !== null).map(([, , y]) => y));
    return top > latest ? ["", "latest", latest] : null;
  }
  for (const economy of named) {
    for (const edition of editions) {
      const last = lastYear(routing, economy, edition);
      if (last === null || top > last) return [economy, edition, last];
    }
  }
  return null;
}

function routeQuestion(routing, question) {
  const lists = routing.word_lists;
  const text = question.toLowerCase();
  const wordsInText = " " + splitIntoWords(question).join(" ") + " ";
  const named = economiesIn(routing, question);
  const members = named.filter((c) => c in routing.members);
  const main = named.filter((c) => !(c in routing.members));
  const hasYear = pattern(routing, "YEAR").test(question);
  const code = question.match(pattern(routing, "ANY_CODE"));
  if (code) {
    if (routing.series_codes.includes(code[0])) return ["Q1", "R1", "series code"];
    return ["OUT", "escalate", "series not in the data"];
  }
  if (lists.NOT_IN_DATA_FOURTH.some((n) => wordsInText.includes(" " + n + " "))) {
    return ["OUT", "escalate", "economy not in the data"];
  }
  if (pattern(routing, "CONDITIONAL").test(text)) return ["Q7", "R5>R2", "scenario (if ... had)"];
  if (beyondTheEdgeGraph(routing, question)) return ["OUT", "escalate", "beyond the data"];
  if (members.length && dataYears(routing, question).length) return ["Q1", "R2", "value lookup (euro area member)"];
  if (text.includes("components") && main.length) return ["Q3", "R2", "compute (components)"];
  if (pattern(routing, "FORECAST").test(text)) return ["OUT", "escalate", "forecast"];
  if (pattern(routing, "ADVICE").test(text)) return ["OUT", "escalate", "policy advice"];
  if (containsAny(question, lists.JUDGEMENT)) return ["OUT", "escalate", "judgement"];
  if (containsAny(question, lists.SCENARIO)) return ["Q7", "R5>R2", "scenario"];
  if (containsAny(question, lists.VAGUE_FOURTH) && !hasYear) return ["AMB", "clarify", "too vague"];
  if (` ${text} `.includes(" now ") && text.includes(" ago")) return ["Q8", "R6", "two dates and an explanation"];
  if (containsAny(question, lists.VINTAGE_FOURTH) && main.length) {
    return ["Q4", text.startsWith("why") ? "R4+R2" : "R2", "vintage"];
  }
  if (containsAny(question, lists.MEASUREMENT) && main.length) return ["Q2", "R4", "measurement"];
  if (main.length >= 2) return ["Q5", containsAny(question, lists.WHY) ? "R4+R2" : "R2", "two economies"];
  if (main.length && text.startsWith("what is")) return ["Q6", "R4+R2", "definition and a figure"];
  if (main.length && containsAny(question, [...lists.DRIVERS, "how much of"])) return ["Q3", "R2", "compute"];
  if (main.length && hasYear) return ["Q1", "R2", "value lookup"];
  const words = topicWords(routing, question);
  const known = new Set(routing.known_words);
  if (words.length && words.filter((w) => known.has(w)).length / words.length < routing.outside_share) {
    return ["OUT", "escalate", "outside the corpus"];
  }
  return ["Q2", "R4", "definition (default)"];
}

// Chapter 12's escalation_message: the reason and the message for an escalated rule.
function escalationMessage(routing, rule) {
  const e = routing.escalation;
  const reason = e.reasons[rule];
  const message = e.messages[reason].replaceAll("{last_year}", String(e.last_year))
    .replaceAll("{economies}", e.economies_in_data).replaceAll("{count}", String(routing.series_codes.length));
  return [reason, message];
}

const api = { routeQuestion, escalationMessage, beyondTheEdgeGraph, splitIntoWords, topicWords };
if (typeof module !== "undefined") module.exports = api;
else globalThis.routeQuestionCode = api;
