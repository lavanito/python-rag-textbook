// read_as.js: the "Read as" line for a typed question, and the choices for
// correcting each part (A5, decision 24).
//
// What this file does
//   Turns the parameters read from a question (read_question.js) into the line
//   shown above the reply, for example
//     "Read as: Japan · GNI per head at purchasing power parities · 2024",
//   and lists the choices for each part's drop-down list. Years are shown as
//   the locked block will use them: "latest" as the last year in the data for
//   the first economy named, two or more years as a span.
//
// Inputs
//   reading: app/data/reading.json (measure descriptions, the words of the
//     line); figures: app/data/figures.json (economy names, last years).
//
// Output
//   readAs(reading, figures, parameters) returns { line, parts }, where each
//   part has its label and its choices ({ value, label }).
//
// Tested by tests/test_reading.py.

function word(reading, id) {
  return reading.read_as_wording[id].text;
}

function capitalised(text) {
  return text[0].toUpperCase() + text.slice(1);
}

function economyLabel(reading, figures, code) {
  if (code === "other") return word(reading, "other_economy");
  return figures.display_names[code] || code;
}

function measureLabel(reading, measure) {
  if (measure === "other") return word(reading, "other_measure");
  return reading.measures[measure].description;
}

function lastYearFor(figures, parameters) {
  const code = parameters.economies.find((c) => c !== "other");
  if (!code) return null;
  const key = `${code}|latest` in figures.last_years ? `${code}|latest` : "EA21|latest";
  return figures.last_years[key];
}

function yearLabel(reading, figures, parameters) {
  const last = lastYearFor(figures, parameters);
  const resolve = (text) => {
    if (text === "latest") return last === null ? word(reading, "latest_year") : String(last);
    const m = text.match(/^latest-(\d+)$/);
    if (m) return last === null ? text : String(last - Number(m[1]));
    return text;
  };
  if (!parameters.years.length) return last === null ? word(reading, "latest_year") : String(last);
  const years = parameters.years.map(resolve);
  return years.length > 1 ? `${years[0]} to ${years[years.length - 1]}` : years[0];
}

function readAs(reading, figures, parameters) {
  const economies = parameters.economies.length
    ? capitalised(parameters.economies.map((c) => economyLabel(reading, figures, c)).join(" and "))
    : word(reading, "no_economy");
  const measures = parameters.measures.length
    ? parameters.measures.map((m) => measureLabel(reading, m)).join(" and ") : word(reading, "no_measure");
  const years = yearLabel(reading, figures, parameters);
  const shown = [economies, measures, years];
  if (parameters.editions.length > 1) shown.push(word(reading, "both_editions"));
  const lastYears = Object.values(figures.last_years).filter((y) => y !== null);
  const yearChoices = [{ value: "latest", label: word(reading, "latest_year") }];
  for (let y = Math.max(...lastYears); y >= figures.first_year; y--) yearChoices.push({ value: String(y), label: String(y) });
  return {
    line: `${word(reading, "label")}: ${shown.join(" · ")}`,
    parts: {
      economies: { label: economies, choices: figures.economies.map((c) => ({ value: c, label: capitalised(economyLabel(reading, figures, c)) })) },
      measures: { label: measures, choices: Object.keys(reading.measures).map((m) => ({ value: m, label: measureLabel(reading, m) })) },
      years: { label: years, choices: yearChoices },
      editions: { label: parameters.editions.length > 1 ? word(reading, "both_editions") : figures.editions.latest,
                  choices: [{ value: "latest", label: figures.editions.latest },
                            { value: "latest,archive", label: word(reading, "both_editions") }] },
    },
  };
}

const api = { readAs };
if (typeof module !== "undefined") module.exports = api;
else globalThis.readAsCode = api;
