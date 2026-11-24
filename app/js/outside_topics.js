// outside_topics.js: questions about a topic none of the measures covers (A5).
//
// What this file does
//   A question naming such a topic (the first is unpaid household services)
//   gets the approved line for it, with its source, and is passed to an
//   analyst. The section goes first in the reply; the rest of the locked block
//   follows unchanged. Decided by Lavan, 24 Nov 2026 (option (b)): a rule in
//   the page only; the book's router is unchanged.
//
// Inputs
//   topics: app/data/outside_topics.json (tools/build_outside_topics.py).
//   figures: app/data/figures.json, for the approved escalation wording.
//
// Output
//   outsideTopics(topics, question) lists the topics a question names;
//   withOutsideTopics(topics, figures, question, lockedText) returns the
//   locked block's text with the section added and the question passed to an
//   analyst.
//
// Tested by tests/test_outside_topics.py.

const { words } = typeof require !== "undefined" ? require("./read_question.js") : globalThis.readQuestionCode;

function outsideTopics(topics, question) {
  const text = words(question);
  return topics.topics.filter((t) => t.trigger_words.some((w) => text.includes(words(w))));
}

function withOutsideTopics(topics, figures, question, lockedText) {
  const found = outsideTopics(topics, question);
  if (!found.length) return lockedText;
  const section = "Outside the data\n" + found.map((t) => `- ${t.line} Source: ${t.source}, ${t.url}.`).join("\n");
  const note = figures.wording.escalation_note;
  const escalation = lockedText.includes(note) ? "" : `\n\n${note}\n${figures.wording.demonstrator_analyst}`;
  return `${section}\n\n${lockedText}${escalation}`;
}

const api = { outsideTopics, withOutsideTopics };
if (typeof module !== "undefined") module.exports = api;
else globalThis.outsideTopicsCode = api;
