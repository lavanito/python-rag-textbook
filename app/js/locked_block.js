// locked_block.js: the JavaScript version of the locked-block code (A5).
//
// What this file does
//   Builds the locked block of a reply in the page, for a question whose
//   parameters (economies, years, measures, editions) have been read. It
//   follows ragbook/ch14_answer_checks.py (locked_block and the functions it
//   calls), ragbook/ch13_model_tool.py (plan_calls, escalate, beyond_the_data,
//   figure_line) and the comparison line of tools/build_bank_replies.py,
//   function by function and in the same order. Names are the Python names
//   in camelCase.
//
// Inputs
//   figures: app/data/figures.json (written by tools/build_figures.py): every
//     NNI model result the page can ask for, the last years, measures, size
//     cuts, definitions and approved wording.
//   nni: nni-model's js/nni.js (copied to app/js/nni.js), for the digits shown
//     (show) and changes in log points (logChange).
//
// Outputs
//   lockedBlock(figures, question, parameters) returns the same object as
//   Python's locked_block; reply(figures, question, parameters, questionClass)
//   returns the locked block's text as the page shows it, with the comparison
//   line where the reply compares economies.
//
// Differences from Python
//   Only the economies in figures.economies are known: the six and Ireland,
//   the economies the page can read from a question. Python also knows the
//   other 20 euro area members by code.
//
// Tested by tests/test_locked_block_js.py: for every bank question with
// parameters and the nine sharper questions, the text equals the stored one
// in app/data/bank_replies.json; for the other labelled questions, it equals
// Python's.

const nni = typeof require !== "undefined" ? require("./nni.js") : globalThis.nni;

// ---------------------------------------------------------------------------
// Chapter 13: the NNI model's results, read from figures.json
// ---------------------------------------------------------------------------

function economyCode(figures, economy) {
  if (economy in figures.economy_codes) return figures.economy_codes[economy];
  if (figures.economies.includes(economy)) return economy;
  return null;
}

function isRate(unit) {
  return unit.includes("log points") || unit.startsWith("per cent");
}

// Chapter 13's show: rates one more decimal, counts whole, levels by band.
function show(value, band, { count = false, rate = false } = {}) {
  return nni.show(value, band, { rate, count });
}

function bandOf(figures, name) {
  return figures.bands[name];
}

function bandName(figures, band) {
  return Object.keys(figures.bands).find((name) => figures.bands[name] === band);
}

// A ToolResult, as call_model returns it.
function callModel(figures, code, year, measure, edition) {
  const m = figures.measures[measure];
  const reply = { economy: code, year, measure, edition: figures.editions[edition],
                  value: null, shown: null, unit: m.unit, source: m.source, flags: [],
                  dqr_band: null, dqr_reason: null, parts: {}, message: null };
  const found = figures.results[`${code}|${year}|${measure}|${edition}`];
  if (!found) {
    reply.message = `No value for ${measure} in ${code} in ${year} in the ${reply.edition} edition.`;
    return reply;
  }
  reply.value = found.value;
  reply.flags = [...found.flags];
  reply.dqr_band = found.dqr_band;
  reply.dqr_reason = figures.reasons[found.dqr_reason];
  reply.parts = found.parts || {};
  reply.shown = show(found.value, bandOf(figures, found.dqr_band),
                     { count: Boolean(m.count), rate: isRate(m.unit) });
  return reply;
}

function displayName(figures, code) {
  return code in figures.display_names ? figures.display_names[code] : code;
}

// Chapter 12's message for a question beyond the ragged edge.
function beyondTheEdgeMessage(figures, [economy, edition, last]) {
  if (last === null) {
    return `The ${edition} edition used here has no data for ${figures.display_names[economy]}, ` +
           "so its figures cannot be compared across editions.";
  }
  const name = economy in figures.display_names ? figures.display_names[economy] : "any economy";
  if (edition === "archive") {
    return `The archive edition used here ends in ${last} for ${name}, ` +
           `so revisions after ${last} cannot be compared.`;
  }
  return `The data here for ${name} end in ${last}, so later years are not available.`;
}

function resolveYear(text, last) {
  if (text === "latest") return last;
  if (text.startsWith("latest-") && /^\d+$/.test(text.slice(7))) return last - Number(text.slice(7));
  return /^\d+$/.test(text) ? Number(text) : null;
}

// Python's repr of a list of strings, as in "Could not read the years ['x']."
function pythonList(items) {
  return "[" + items.map((s) => (s.includes("'") && !s.includes('"') ? `"${s}"` : `'${s}'`)).join(", ") + "]";
}

function lastYear(figures, code, edition) {
  const key = `${code}|${edition}`;
  return key in figures.last_years ? figures.last_years[key] : undefined;
}

// The row of last_year.csv an economy uses: its own, or the euro area's.
function rowFor(figures, code, edition) {
  return lastYear(figures, code, edition) !== undefined ? code : "EA21";
}

function planCalls(figures, parameters) {
  const calls = [], problems = [], codes = [];
  const economies = Object.keys(figures.economy_codes);
  for (const economy of parameters.economies) {
    const code = economyCode(figures, economy);
    if (code === null) {
      problems.push(`${economy} is not in the data. The data contain ` +
                    `${economies.join(", ")} and the 21 euro area members.`);
    } else {
      codes.push(code);
    }
  }
  for (const measure of parameters.measures) {
    if (measure in figures.gaps) {
      const gap = figures.gaps[measure];
      problems.push(`${gap.description} is not in the data used here. ` +
                    `Best data: ${gap.best_data}. ${figures.wording.escalation_note}`);
    } else if (!(measure in figures.measures)) {
      problems.push("That measure is not one the model gives. It gives: " +
                    `${Object.values(figures.measures).map((m) => m.description).join(", ")}. ` +
                    `${figures.wording.escalation_note}`);
    }
  }
  const measures = parameters.measures.filter((m) => m in figures.measures);
  if (codes.length === 0 || measures.length === 0) return [calls, problems];
  for (const edition of parameters.editions) {
    const rows = {}, lasts = new Map();
    for (const code of codes) {
      rows[code] = rowFor(figures, code, edition);
      lasts.set(code, lastYear(figures, rows[code], edition));
    }
    if ([...lasts.values()].includes(null)) {
      const missing = [...lasts].filter(([, last]) => last === null).map(([code]) => code);
      problems.push(beyondTheEdgeMessage(figures, [rows[missing[0]], edition, null]));
      continue;
    }
    const last = Math.min(...lasts.values());
    let years = parameters.years.map((text) => resolveYear(text, last));
    if (years.length === 0) years = [last];
    if (years.includes(null)) {
      problems.push(`Could not read the years ${pythonList(parameters.years)}.`);
      continue;
    }
    for (const year of years) {
      if (year > last) {
        // The economy whose data end first (the first one named, on a tie).
        let code = null;
        for (const [c, l] of lasts) if (code === null || l < lasts.get(code)) code = c;
        problems.push(beyondTheEdgeMessage(figures, [rows[code], edition, lasts.get(code)]));
      } else if (year < figures.first_year) {
        problems.push(`The data here start in ${figures.first_year}.`);
      }
    }
    years = [...new Set(years.filter((y) => figures.first_year <= y && y <= last))].sort((a, b) => a - b);
    if (years.length === 0) continue;
    for (const measure of measures) {
      const start = measure === "nni_growth" ? years[0] + 1 : years[0];
      const span = [];
      if (years.length > 1) for (let y = start; y <= years[years.length - 1]; y++) span.push(y);
      else span.push(...years);
      for (const code of codes) for (const year of span) calls.push([code, year, measure, edition]);
    }
  }
  return [calls, problems];
}

function escalate(figures, calls, problems) {
  return problems.length > 0 || calls.some((call) => "proxy" in figures.measures[call[2]]);
}

function beyondTheData(figures, parameters) {
  const found = [];
  for (const economy of parameters.economies) {
    const code = economyCode(figures, economy);
    if (code === null) continue;
    for (const edition of parameters.editions) {
      const last = lastYear(figures, rowFor(figures, code, edition), edition);
      if (last === null || last === undefined) continue;
      const asked = parameters.years.map((text) => resolveYear(text, last));
      const beyond = asked.filter((year) => year !== null && year > last);
      for (const measure of parameters.measures.filter((m) => m in figures.measures)) {
        for (const year of beyond) found.push([year, callModel(figures, code, last, measure, edition)]);
      }
    }
  }
  return found;
}

function sum(values) {
  return values.reduce((total, v) => total + v, 0);
}

// The weakest band of some results; the first listed wins ties.
function weakest(figures, results) {
  return results.reduce((w, r) => (bandOf(figures, r.dqr_band) < bandOf(figures, w.dqr_band) ? r : w));
}

function partsText(figures, parts, band) {
  let text = ["C1a", "C2", "C4"].map(
    (name) => `${figures.part_names[name]} ${show(parts[name], band, { rate: true })}`).join(", ");
  if (["C4a", "C4b", "C4c"].every((name) => parts[name] !== null && parts[name] !== undefined)) {
    text += " (of which " + ["C4a", "C4b", "C4c"].map(
      (name) => `${figures.part_names[name]} ${show(parts[name], band, { rate: true })}`).join(", ") + ")";
  }
  return text;
}

function figureLine(figures, results) {
  const first = results[0], last = results[results.length - 1];
  const low = weakest(figures, results);
  const band = bandOf(figures, low.dqr_band);
  const flags = [...new Set(results.flatMap((r) => r.flags))].sort();
  let value;
  if (first.measure === "nni_growth") {
    const parts = {};
    for (const name of Object.keys(figures.part_names)) {
      parts[name] = results.some((r) => r.parts[name] === null || r.parts[name] === undefined)
        ? null : sum(results.map((r) => r.parts[name]));
    }
    const total = sum(results.map((r) => r.value));
    value = `${show(total, band, { rate: true })} log points from ${first.year - 1} to ` +
            `${last.year}; made up of ${partsText(figures, parts, band)}`;
  } else if (results.length > 1) {
    value = `${first.shown} in ${first.year} and ${last.shown} in ${last.year} (${first.unit})`;
  } else {
    value = `${first.shown} ${first.unit} in ${first.year}`;
  }
  return `- ${displayName(figures, first.economy)}, ` +
         `${figures.measures[first.measure].description}: ${value}. Source: ${first.source}; ` +
         `edition ${first.edition}. DQR ${bandName(figures, band)}: ${low.dqr_reason}.` +
         (flags.length ? ` Flags: ${flags.join("; ")}.` : "");
}

// ---------------------------------------------------------------------------
// Chapter 14: the locked block
// ---------------------------------------------------------------------------

function definitionLine(figures, measure) {
  const row = figures.definitions[measure];
  let line = `- ${figures.measures[measure].description}. What it means: ${row.means}`;
  if (row.leaves_out) line += ` What it leaves out: ${row.leaves_out}`;
  if (row.passages.length) line += ` See ${row.passages.join(", ")}.`;
  return line;
}

function nameOf(figures, code) {
  const name = displayName(figures, code);
  return name[0].toUpperCase() + name.slice(1);
}

function direction(figures, change) {
  if (Math.abs(change) < figures.zero) return "none";
  return change > 0 ? "up" : "down";
}

function size(figures, change) {
  const [lowLarge, lowSmall, highSmall, highLarge] = figures.size_cuts;
  if (change < lowLarge || change > highLarge) return "large";
  if (lowSmall <= change && change <= highSmall) return "small";
  return "medium";
}

function sizeNote(figures, change, noun) {
  return `a ${size(figures, change)} ${noun}: ${figures.wording.size_note_other}`;
}

function sized(figures, word, change, noun) {
  const note = noun === "revision" ? figures.wording.size_note : figures.wording.size_note_other;
  const joiner = noun === "revision" ? ", " : ": ";
  return `${word} (a ${size(figures, change)} ${noun}${joiner}${note})`;
}

function changeUnit(unit) {
  return unit.startsWith("per cent") ? "percentage points" : "log points";
}

function difference(oldValue, newValue, unit) {
  return isRate(unit) ? newValue - oldValue : nni.logChange(oldValue, newValue);
}

function minBand(figures, results) {
  return Math.min(...results.map((r) => bandOf(figures, r.dqr_band)));
}

function overTime(figures, results) {
  const first = results[0], last = results[results.length - 1];
  const band = minBand(figures, results);
  const name = nameOf(figures, first.economy);
  const description = figures.measures[first.measure].description;
  if (first.measure === "nni_growth") {
    const total = sum(results.map((r) => r.value));
    const way = direction(figures, total);
    const words = { up: "grew", down: "shrank", none: "was unchanged" }[way];
    const note = way === "none" ? "" : `; ${sizeNote(figures, total, "change")}`;
    return { kind: "growth", direction: way,
             text: `- ${name}, real NNI per head: ${words} from ${first.year - 1} to ${last.year} ` +
                   `(${show(total, band, { rate: true })} log points${note}).` };
  }
  if (results.length === 1) return null;
  const change = difference(first.value, last.value, first.unit);
  const way = direction(figures, change);
  const words = { up: "rose", down: "fell", none: "unchanged" }[way];
  const note = way === "none" ? "" : `; ${sizeNote(figures, change, "change")}`;
  return { kind: "time", direction: way,
           text: `- ${name}, ${description}: ${words} from ${first.shown} in ${first.year} to ` +
                 `${last.shown} in ${last.year} (${show(change, band, { rate: true })} ` +
                 `${changeUnit(first.unit)}${note}).` };
}

function revision(figures, oldR, newR) {
  const band = Math.min(bandOf(figures, oldR.dqr_band), bandOf(figures, newR.dqr_band));
  const change = difference(oldR.value, newR.value, oldR.unit);
  const way = direction(figures, change);
  const words = way === "none" ? "unchanged"
    : sized(figures, { up: "revised up", down: "revised down" }[way], change, "revision");
  const gap = isRate(oldR.unit) ? "" : `a change of ${show(newR.value - oldR.value, band)}, `;
  return { kind: "revision", direction: way,
           text: `- ${nameOf(figures, oldR.economy)}, ` +
                 `${figures.measures[oldR.measure].description}, ${oldR.year}: ${words}, from ` +
                 `${oldR.shown} (edition ${oldR.edition}) to ${newR.shown} (edition ${newR.edition}); ` +
                 `${gap}${show(change, band, { rate: true })} ${changeUnit(oldR.unit)}.` };
}

function between(figures, aResults, bResults) {
  const bYears = new Set(bResults.map((r) => r.year));
  const years = [...new Set(aResults.map((r) => r.year))].filter((y) => bYears.has(y)).sort((x, y) => x - y);
  if (years.length === 0) return null;
  const a = {}, b = {};
  for (const r of aResults) a[r.year] = r;
  for (const r of bResults) b[r.year] = r;
  const band = minBand(figures, [...aResults, ...bResults]);
  const unit = aResults[0].unit;
  const nameA = displayName(figures, aResults[0].economy);
  const nameB = displayName(figures, bResults[0].economy);
  const rate = isRate(unit);
  const gapIn = (year) => difference(b[year].value, a[year].value, unit);
  const place = (year) => {
    const gap = gapIn(year);
    const way = direction(figures, gap);
    const word = rate ? { up: "higher than", down: "lower than", none: "the same as" }[way]
                      : { up: "ahead of", down: "behind", none: "level with" }[way];
    const note = way === "none" ? "" : `; ${sizeNote(figures, gap, "gap")}`;
    const share = rate ? "" : `, ${nni.fixed(a[year].value / b[year].value * 100, 1)}% of its level`;
    return `in ${year} ${nameA} was ${word} ${nameB} ` +
           `(${show(gap, band, { rate: true })} ${changeUnit(unit)}${share}${note})`;
  };
  let text = `- ${nameOf(figures, aResults[0].economy)} against ${nameB}, ` +
             `${figures.measures[aResults[0].measure].description}: ${place(years[0])}`;
  let way = direction(figures, gapIn(years[0]));
  let kind = "level";
  if (years.length > 1) {
    const moved = gapIn(years[years.length - 1]) - gapIn(years[0]);
    way = direction(figures, moved);
    kind = "gap";
    const words = { up: `${nameA} gained ground`, down: `${nameA} lost ground`,
                    none: "the gap was unchanged" }[way];
    const note = way === "none" ? "" : `; ${sizeNote(figures, moved, "change")}`;
    text += `; ${place(years[years.length - 1])}: ${words} ` +
            `(${show(moved, band, { rate: true })} ${changeUnit(unit)}${note})`;
  }
  return { kind, direction: way, text: text + "." };
}

// groups: a Map from "economy|measure|edition" to that figure's results, in
// the order Python's dict keeps them.
function comparisons(figures, groups) {
  const found = [];
  const split = (key) => key.split("|");
  for (const results of groups.values()) {
    const item = overTime(figures, results);
    if (item) found.push(item);
  }
  const editions = [...new Set([...groups.keys()].map((k) => split(k)[2]))].sort();
  if (editions.includes("archive") && editions.includes("latest")) {
    for (const [key, results] of groups) {
      const [code, measure, edition] = split(key);
      const newer = groups.get(`${code}|${measure}|latest`);
      if (edition === "archive" && newer) {
        for (const oldR of results) {
          for (const newR of newer) if (newR.year === oldR.year) found.push(revision(figures, oldR, newR));
        }
      }
    }
  }
  const codes = [];
  for (const key of groups.keys()) if (!codes.includes(split(key)[0])) codes.push(split(key)[0]);
  for (const [key, results] of groups) {
    const [code, measure, edition] = split(key);
    const first = groups.get(`${codes[0]}|${measure}|${edition}`);
    if (edition === "archive" && editions.length > 1) continue;
    if (code !== codes[0] && first) {
      const item = between(figures, first, results);
      if (item) found.push(item);
    }
  }
  return found;
}

const COMPARE_DOWN = /\b(fall(?:en|ing|s)? behind|fell behind|behind|lost ground|lower than|slower than)\b/g;
const COMPARE_UP = /\b(ahead|caught up|catch(?:ing)? up|gained ground|higher than|faster than)\b/g;
const CHANGE_DOWN = /\b(fell|fall|falls|fallen|falling|declin\w*|dropp?\w*|decreas\w*|shr[iau]nk\w*|slow\w*|wors\w*|revised down)\b/;
const CHANGE_UP = /\b(rose|rise|rises|risen|rising|grew|grown|increas\w*|improv\w*|revised up)\b/;

function found(pattern, text) {
  return new RegExp(pattern.source).test(text);
}

function assumed(text, downWords, upWords) {
  const down = found(downWords, text), up = found(upWords, text);
  if (down && !up) return "down";
  if (up && !down) return "up";
  return null;
}

function premiseLine(question, items) {
  let text = question.toLowerCase();
  const compare = assumed(text, COMPARE_DOWN, COMPARE_UP);
  text = text.replace(COMPARE_DOWN, " ").replace(COMPARE_UP, " ");
  const change = assumed(text, CHANGE_DOWN, CHANGE_UP);
  const betweenWays = new Set(items.filter((i) => ["gap", "level"].includes(i.kind)).map((i) => i.direction));
  const changeWays = new Set(items.filter((i) => ["time", "revision", "growth"].includes(i.kind)).map((i) => i.direction));
  if (compare === "down" && !betweenWays.has("down") && betweenWays.has("up")) {
    return "The question assumes it fell behind; the figures show it gained ground or is ahead.";
  }
  if (compare === "up" && !betweenWays.has("up") && betweenWays.has("down")) {
    return "The question assumes it caught up or is ahead; the figures show it lost ground or is behind.";
  }
  if (change === "down" && !changeWays.has("down") && changeWays.has("up")) {
    return "The question assumes a fall; the figures show a rise.";
  }
  if (change === "up" && !changeWays.has("up") && changeWays.has("down")) {
    return "The question assumes a rise; the figures show a fall.";
  }
  return null;
}

function fetchFigures(figures, parametersIn) {
  const parameters = { ...parametersIn };
  if (parameters.years.length === 0 && parameters.editions.length > 1) {
    const lasts = [];
    for (const economy of parameters.economies) {
      const code = economyCode(figures, economy);
      if (!code) continue;
      for (const edition of parameters.editions) {
        const last = lastYear(figures, rowFor(figures, code, edition), edition);
        lasts.push(last === undefined ? null : last);
      }
    }
    if (lasts.length && !lasts.includes(null)) parameters.years = [String(Math.min(...lasts))];
  }
  const [calls, problems] = planCalls(figures, parameters);
  const groups = new Map();
  for (const [code, year, measure, edition] of calls) {
    let result = callModel(figures, code, year, measure, edition);
    if (result.value === null && parameters.years.length === 0) {
      for (const back of [1, 2, 3]) {
        result = callModel(figures, code, year - back, measure, edition);
        if (result.value !== null) break;
      }
    }
    if (result.value === null) {
      problems.push(result.message);
    } else {
      const key = `${code}|${measure}|${edition}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(result);
    }
  }
  const beyond = [];
  for (const [year, latest] of beyondTheData(figures, parameters)) {
    if (latest.value !== null) beyond.push(`- ${year} is beyond the data. Latest: ` + figureLine(figures, [latest]).slice(2));
  }
  return [groups, problems, beyond, escalate(figures, calls, problems)];
}

function lockedBlock(figures, question, parameters) {
  const [groups, problems, beyond, escalated] = fetchFigures(figures, parameters);
  const items = comparisons(figures, groups);
  const premise = premiseLine(question, items);
  const measures = [];
  for (const key of groups.keys()) {
    const measure = key.split("|")[1];
    if (!measures.includes(measure)) measures.push(measure);
  }
  const figureLines = [...[...groups.values()].map((results) => figureLine(figures, results)), ...beyond];
  const definitionLines = measures.filter((m) => m in figures.definitions).map((m) => definitionLine(figures, m));
  const parts = [];
  if (premise) parts.push(premise);
  parts.push("Figures (calculated from the data)\n" + (figureLines.join("\n") || "- none"));
  if (items.length) parts.push("Comparisons (calculated from the figures)\n" + items.map((i) => i.text).join("\n"));
  if (problems.length) parts.push("Missing\n" + problems.map((p) => `- ${p}`).join("\n"));
  if (definitionLines.length) parts.push(`${figures.wording.definitions_heading}\n` + definitionLines.join("\n"));
  if (escalated) parts.push(`${figures.wording.escalation_note}\n${figures.wording.demonstrator_analyst}`);
  return { premise, figures: figureLines, comparisons: items.map((i) => i.text),
           directions: items.map((i) => i.direction), missing: problems,
           definitions: definitionLines, measures, escalate: escalated, text: parts.join("\n\n") };
}

// ---------------------------------------------------------------------------
// tools/build_bank_replies.py: the comparison line
// ---------------------------------------------------------------------------

function comparesEconomies(figures, questionClass, parameters) {
  return figures.comparing_classes.includes(questionClass) || ((parameters || {}).economies || []).length > 1;
}

function withComparisonLine(figures, lockedText) {
  const line = `- ${figures.wording.comparison_line}`;
  const heading = figures.wording.definitions_heading;
  const parts = lockedText.split("\n\n");
  for (let i = 0; i < parts.length; i++) {
    if (parts[i].startsWith(heading)) {
      parts[i] = parts[i] + "\n" + line;
      return parts.join("\n\n");
    }
  }
  const escalation = parts.findIndex((part) => part.startsWith(figures.wording.escalation_note));
  parts.splice(escalation === -1 ? parts.length : escalation, 0, `${heading}\n${line}`);
  return parts.join("\n\n");
}

// The locked block's text as the page shows it.
function reply(figures, question, parameters, questionClass = null) {
  const text = lockedBlock(figures, question, parameters).text;
  return comparesEconomies(figures, questionClass, parameters) ? withComparisonLine(figures, text) : text;
}

const api = { lockedBlock, reply, withComparisonLine, comparesEconomies, planCalls, callModel,
              figureLine, premiseLine };
if (typeof module !== "undefined") module.exports = api;
else globalThis.lockedBlockCode = api;
