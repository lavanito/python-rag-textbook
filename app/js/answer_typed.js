// answer_typed.js: the reply to a typed question, put together in the page (A5).
//
// What this file does
//   Puts a typed question through the same steps as a bank question, in the
//   page, with code only (build spec v3, 7.2, 7.3, 9 and 10). Each route gets
//   the reply the bank builder (tools/build_bank_replies.py) gives that route,
//   with the same approved words:
//   - escalate: the escalation message (Chapter 12), passed to an analyst;
//   - clarify: the clarify line and the three aspects to pick from;
//   - R1: the series title;
//   - R6: not built in this demonstrator;
//   - R4: the passages found, quoted (search.js), with no DQR;
//   - R2, R4+R2, R5>R2: the question read in parts (read_question.js), or the
//     parts as the user corrected them, then the locked block
//     (locked_block.js). Typed questions get no explanation.
//   A question about a topic none of the measures covers gets the approved
//   line first (outside_topics.js). Each step adds one line to the trace.
//
// Inputs
//   data: { routing, reading, figures, search, topics, page }, the files in
//     app/data/ of the same names (page is page.json).
//   question: the typed text; useMode: "non-commercial" or "commercial".
//   meaning (optional): { vector, measures } for reading the measure by
//     meaning; without it the measure is read by name only.
//   corrected (optional): the parts as the user corrected them.
//
// Output
//   { route, kind, parameters, readAs, text, found, aspects, steps }.
//
// Tested by tests/test_answer_typed_js.py.

const load = (file, name) => (typeof require !== "undefined" ? require(file) : globalThis[name]);
const { routeQuestion, escalationMessage, beyondTheEdgeGraph } = load("./route_question.js", "routeQuestionCode");
const { readQuestion } = load("./read_question.js", "readQuestionCode");
const { readAs } = load("./read_as.js", "readAsCode");
const { reply, beyondTheEdgeMessage } = load("./locked_block.js", "lockedBlockCode");
const { withOutsideTopics } = load("./outside_topics.js", "outsideTopicsCode");
const { findPassages } = load("./search.js", "searchCode");

// Chapter 8's passage_lines and the bank builder's passage_block.
function passageLines(p) {
  const scope = p.scope_note ? `${p.scope} (our note: ${p.scope_note})` : p.scope;
  return `- [${p.id}] ${p.source}, ${p.reference}\n` +
         `  Edition: ${p.edition} · Licence: ${p.licence_class} · Scope: ${scope}\n` +
         `  "${p.text}"`;
}

function passageBlock(words, passages) {
  const lines = passages.map(passageLines).join("\n") || `- ${words.NO_PASSAGES}`;
  return `${words.PASSAGES_HEADING}\n${lines}\n\n${words.NO_DQR}`;
}

function escalated(data, question, rule) {
  const w = data.figures.wording;
  const message = rule === "beyond the data"
    ? beyondTheEdgeMessage(data.figures, beyondTheEdgeGraph(data.routing, question))
    : escalationMessage(data.routing, rule)[1];
  return `${message}\n\n${w.escalation_note}\n${w.demonstrator_analyst}`;
}

const CODE = "code; no language model";

function answerTyped(data, question, useMode, meaning = null, corrected = null) {
  const words = data.page.reply_wording;
  const [questionClass, route, rule] = routeQuestion(data.routing, question);
  const steps = [{ step: "route", outputs: { class: questionClass, route, rule }, means: CODE }];
  const found = findPassages(data.search, question, useMode);
  const licence = found.withheld.filter((w) => w.filter === "licence").map((w) => w.id);
  const edition = found.withheld.filter((w) => w.filter === "edition").map((w) => w.id);
  steps.push({ step: "licence filter", outputs: { kept: data.search.passages.length - licence.length, withheld: licence }, means: CODE });
  steps.push({ step: "edition filter", outputs: { withheld: edition }, means: CODE });
  steps.push({ step: "passages found", outputs: { ids: found.passages.map((p) => p.passage.id) }, means: CODE });
  let kind = "fixed", parameters = null, text, aspects = null;
  const read = () => {
    parameters = corrected || readQuestion(data.reading, question, meaning);
    steps.push({ step: corrected ? "parameters (corrected by the user)" : "read question",
                 outputs: { economies: parameters.economies, years: parameters.years, editions: parameters.editions,
                            measures: parameters.measures, how: corrected ? null : parameters.how }, means: CODE });
  };
  if (route === "escalate") {
    text = escalated(data, question, rule);
  } else if (route === "clarify") {
    read();
    kind = "clarify";
    aspects = data.page.aspects;
    text = words.CLARIFY_LINE;
  } else if (route === "R1") {
    const code = Object.keys(data.page.series_titles).find((c) => question.includes(c));
    text = `${words.SERIES_HEADING}\n- ${code}: ${data.page.series_titles[code]}`;
  } else if (route === "R6") {
    text = `${words.NOT_BUILT}\n${words.DEMONSTRATOR_NOT_BUILT}`;
  } else if (route === "R4") {
    kind = "passages";
    text = passageBlock(words, found.passages.map((p) => p.passage));
  } else {
    read();
    kind = "code";
    text = reply(data.figures, question, parameters, questionClass);
    steps.push({ step: "locked block", outputs: { measures: parameters.measures }, means: CODE });
  }
  text = withOutsideTopics(data.topics, data.figures, question, text);
  const shown = parameters ? readAs(data.reading, data.figures, parameters) : null;
  return { route: { class: questionClass, route, rule }, kind, parameters, readAs: shown, text, found, aspects, steps };
}

const api = { answerTyped, passageBlock };
if (typeof module !== "undefined") module.exports = api;
else globalThis.answerTypedCode = api;
