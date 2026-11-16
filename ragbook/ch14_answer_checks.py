"""
Chapter 14 — Checking answers

What this file does
    Splits every reply into two parts. The locked block is written by code:
    the figures, the differences and directions between them, what each
    measure means and leaves out, the source, edition, data quality rating
    (DQR), flags and escalation. The explanation is written by a language
    model and is shown only if it passes every check: numbers, direction
    words, words that code decides, citations, support and miscitation. An
    explanation that fails gets one retry, told what failed; if the retry
    fails too, the explanation is dropped and the locked block is shown alone.

Inputs
    A question, its parameters (economies, years, measures, editions), its
    question class from Chapter 12, and an ask function for the language
    model (Chapter 11's ask_model_with_details, or a stand-in in the tests).

Outputs
    A record per question: the locked block, the passages given as
    evidence, the first and second explanations with the problems each
    check found, and the status (lookup, passed, passed on retry, dropped).

Used by
    Chapter 15 (tracing and cost) and the demonstrator's reply page.

Uses
    Chapter 1 (load_passages); Chapter 2 (load_corpus); Chapter 3
    (search_words, bm25s_rank, QUESTION_FILE); Chapter 8 (licence_filter);
    Chapter 11 (citations, sentences, asking the model, saving answers);
    Chapter 12 (load_last_years, DISPLAY_NAMES); Chapter 13 (calling the
    NNI model, figure lines, escalation). Decisions: the domain expert, 13 November 2026
    (claude/ch14-decisions.md in the project).

Run the worked example
    python -m ragbook.ch14_answer_checks
        Writes the locked blocks for the bank's questions routed to code,
        rechecks Chapter 11's analyst answers, scores the support check
        against the domain expert's 20 judgements, and checks Chapter 13's replies as if
        they were explanations. Needs no language model.
    python -m ragbook.ch14_answer_checks --explain --review
        The same, after the domain expert's review of 16 November 2026, saved
        to data/answers/ch14_explanations_review.jsonl.
    python -m ragbook.ch14_answer_checks --explain
        Also asks the local language model (Ollama) for an explanation of
        each question routed to code (the bank's 14 and the fair test),
        with one retry, and saves the records.
"""
import csv
import json
import re
import sys
import urllib.error
from pathlib import Path

from nni_model import dqr

from ragbook.ch01_python_basics import load_passages
from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import QUESTION_FILE, bm25s_rank, search_words
from ragbook.ch08_filters import licence_filter
from ragbook.ch11_prompts import (ANSWER_FOLDER, ANSWERS_800_FILE, BRACKETS, SENTENCE_END, SETTINGS,
                                  ask_model_with_details, cited_ids, format_evidence,
                                  load_answers, save_answers, sentences)
from ragbook.ch12_routing import DISPLAY_NAMES, load_last_years
from ragbook.ch13_model_tool import (BANDS, ESCALATION_NOTE, MEASURES, PARAMETER_FILE,
                                     REPLIES_FILE, beyond_the_data, bank_model_questions,
                                     call_model, economy_code, escalate, figure_line, is_rate,
                                     log_change, numbers_in, plan_calls, show)

DATA_FOLDER = Path(__file__).parent.parent / "data"
DEFINITIONS_FILE = DATA_FOLDER / "definitions.csv"
GRAPH_FOLDER = DATA_FOLDER / "knowledge_graph"
JUDGEMENTS_FILE = ANSWER_FOLDER / "ch14_support_judgements.csv"
EXPLANATIONS_FILE = ANSWER_FOLDER / "ch14_explanations.jsonl"
# The rerun after the domain expert's review (16 November 2026): size bands, id protocol.
REVIEW_FILE = ANSWER_FOLDER / "ch14_explanations_review.jsonl"
FAIR_TEST_FILE = DATA_FOLDER / "question_bank" / "ch14_fair_test.jsonl"


# ---------------------------------------------------------------------------
# 14.2  The locked block
# ---------------------------------------------------------------------------

# The size of a change (the domain expert, 16 November 2026): every non-zero
# revision between the two editions, pooled in one unit (log points for levels,
# percentage points for rates and shares) and cut into three roughly equal
# parts. The same bands judge changes over time and gaps between economies.
# tools/build_revision_bands.py writes the cuts.
BANDS_FILE = DATA_FOLDER / "series" / "revision_bands.csv"
ZERO = 0.005        # a smaller change shows as 0.00, so it counts as no change
SIZE_NOTE = "which happens about one third of the time"
SIZE_NOTE_OTHER = "about one third of revisions are this large"


def load_size_cuts(file_path=BANDS_FILE):
    """
    The four cuts, in order: the 16.5th, 33rd, 67th and 83.5th percentiles of
    the non-zero revisions.

    Example:
        load_size_cuts() returns [-0.24, -0.01, 0.68, 1.72] (rounded here)
    """
    with open(file_path, encoding="utf-8") as file:
        return [float(row["value"]) for row in csv.DictReader(file)]


SIZE_CUTS = load_size_cuts()

EXPLANATION_HEADING = "Explanation (written by a language model and checked against the figures above)"
WITHHELD = ("The written explanation came from a language model and did not pass our quality "
            "checks, so it is not shown. Please contact our analyst if you want to know more.")
DEMONSTRATOR_WITHHELD = ("Demonstrator note: this is a demonstration, not a product. A product "
                         "would let you ask for the explanation to be refined, and would send "
                         "your question to a named analyst. Here, no analyst receives it.")
DEMONSTRATOR_ANALYST = "Demonstrator note: in this demonstrator, no analyst receives it."


def load_definitions(file_path=DEFINITIONS_FILE):
    """
    What each measure means and leaves out, approved by the domain expert on 13 November
    2026, with the passages that define it.

    Example:
        load_definitions()["gni"]["passages"] returns ["esa10-8.94"]
    """
    definitions = {}
    with open(file_path, encoding="utf-8") as file:
        for row in csv.DictReader(file):
            row["passages"] = [p for p in row["passages"].split("; ") if p]
            definitions[row["measure"]] = row
    return definitions


def definition_line(measure, definitions):
    """
    The definition line for one measure, as the locked block shows it.

    Example:
        definition_line("gni", load_definitions())
        starts "- GNI, total. What it means: Gross national income"
    """
    row = definitions[measure]
    line = f"- {MEASURES[measure]['description']}. What it means: {row['means']}"
    if row["leaves_out"]:
        line += f" What it leaves out: {row['leaves_out']}"
    if row["passages"]:
        line += f" See {', '.join(row['passages'])}."
    return line


def name_of(code):
    """An economy's name as a sentence starts it: "The United Kingdom"."""
    name = DISPLAY_NAMES.get(code, code)
    return name[0].upper() + name[1:]


def direction(change):
    """
    "up", "down" or "none": a change smaller than ZERO is none.

    Example:
        direction(-0.3) returns "down"
    """
    if abs(change) < ZERO:
        return "none"
    return "up" if change > 0 else "down"


def size(change, cuts=None):
    """
    "large", "medium" or "small": where a change falls among the revisions.
    Large below the 16.5th percentile or above the 83.5th; small from the
    33rd to the 67th, inclusive; medium in between.

    Example:
        size(-2.48) returns "large"
    """
    low_large, low_small, high_small, high_large = cuts or SIZE_CUTS
    if change < low_large or change > high_large:
        return "large"
    if low_small <= change <= high_small:
        return "small"
    return "medium"


def size_note(change, noun):
    """
    The size of a change over time or a gap, for the end of its brackets.

    Example:
        size_note(-31.2, "gap") returns "a large gap: about one third of revisions are this large"
    """
    return f"a {size(change)} {noun}: {SIZE_NOTE_OTHER}"


def sized(word, change, noun):
    """
    A direction word with the size of the change in brackets. For a revision
    the note gives how often a revision is that size; for a change over time
    or a gap, the size is still measured against revisions.

    Example:
        sized("revised down", -2.48, "revision")
        returns "revised down (a large revision, which happens about one third of the time)"
    """
    note = SIZE_NOTE if noun == "revision" else SIZE_NOTE_OTHER
    joiner = ", " if noun == "revision" else ": "
    return f"{word} (a {size(change)} {noun}{joiner}{note})"


def change_unit(unit):
    """The unit of a change: log points for levels and growth rates,
    percentage points for shares in per cent."""
    return "percentage points" if unit.startswith("per cent") else "log points"


def difference(old, new, unit):
    """A change from old to new: in log points for a level, as a plain
    difference for a rate or a share (it is already in log points or per cent)."""
    return new - old if is_rate(unit) else log_change(old, new)


def over_time(results):
    """
    For one economy, measure and edition over a span of years: the change
    from the first year to the last, with its direction. None for a single
    year. For growth in real NNI per head, the direction of the total growth.

    Example:
        over_time([UK 2007 result, ..., UK 2024 result])
        returns {"kind": "time", "direction": "up", "text": "- United Kingdom, ...: rose ..."}
    """
    first, last = results[0], results[-1]
    band = min(BANDS[r.dqr_band] for r in results)
    name = name_of(first.economy)
    description = MEASURES[first.measure]["description"]
    if first.measure == "nni_growth":
        total = sum(r.value for r in results)
        way = direction(total)
        words = {"up": "grew", "down": "shrank", "none": "was unchanged"}[way]
        note = "" if way == "none" else f"; {size_note(total, 'change')}"
        return {"kind": "growth", "direction": way,
                "text": f"- {name}, real NNI per head: {words} from {first.year - 1} to {last.year} "
                        f"({show(total, band, rate=True)} log points{note})."}
    if len(results) == 1:
        return None
    change = difference(first.value, last.value, first.unit)
    way = direction(change)
    words = {"up": "rose", "down": "fell", "none": "unchanged"}[way]
    note = "" if way == "none" else f"; {size_note(change, 'change')}"
    return {"kind": "time", "direction": way,
            "text": f"- {name}, {description}: {words} from {first.shown} in {first.year} to "
                    f"{last.shown} in {last.year} ({show(change, band, rate=True)} "
                    f"{change_unit(first.unit)}{note})."}


def revision(old, new):
    """
    One figure in two editions: how far it was revised, and which way.

    Example:
        revision(India 2016 in WDI 2024-03, India 2016 in WDI 2026-10-08)
        returns {"kind": "revision", "direction": "down", "text": "- India, ...: revised down ..."}
    """
    band = min(BANDS[old.dqr_band], BANDS[new.dqr_band])
    change = difference(old.value, new.value, old.unit)
    way = direction(change)
    words = "unchanged" if way == "none" else sized(
        {"up": "revised up", "down": "revised down"}[way], change, "revision")
    gap = "" if is_rate(old.unit) else f"a change of {show(new.value - old.value, band)}, "
    return {"kind": "revision", "direction": way,
            "text": f"- {name_of(old.economy)}, "
                    f"{MEASURES[old.measure]['description']}, {old.year}: {words}, from "
                    f"{old.shown} (edition {old.edition}) to {new.shown} (edition {new.edition}); "
                    f"{gap}{show(change, band, rate=True)} {change_unit(old.unit)}."}


def between(a_results, b_results):
    """
    Two economies on one measure: economy A against economy B, by the ratio
    in log points (the domain expert, 13 November 2026), in the first and last years
    they share. Over a span, also whether A gained or lost ground.

    Example:
        between(UK results 2007 and 2024, US results 2007 and 2024)
        returns {"kind": "gap", "direction": "same", "text": "- United Kingdom against ..."}
    """
    years = sorted({r.year for r in a_results} & {r.year for r in b_results})
    if not years:
        return None
    a = {r.year: r for r in a_results}
    b = {r.year: r for r in b_results}
    band = min(BANDS[r.dqr_band] for r in a_results + b_results)
    unit = a_results[0].unit
    name_a = DISPLAY_NAMES.get(a_results[0].economy, a_results[0].economy)
    name_b = DISPLAY_NAMES.get(b_results[0].economy, b_results[0].economy)
    rate = is_rate(unit)

    def gap_in(year):
        return difference(b[year].value, a[year].value, unit)

    def place(year):
        gap = gap_in(year)
        way = direction(gap)
        if rate:
            word = {"up": "higher than", "down": "lower than", "none": "the same as"}[way]
        else:
            word = {"up": "ahead of", "down": "behind", "none": "level with"}[way]
        note = "" if way == "none" else f"; {size_note(gap, 'gap')}"
        share = "" if rate else f", {a[year].value / b[year].value * 100:.1f}% of its level"
        return (f"in {year} {name_a} was {word} {name_b} "
                f"({show(gap, band, rate=True)} {change_unit(unit)}{share}{note})")

    text = f"- {name_of(a_results[0].economy)} against {name_b}, {MEASURES[a_results[0].measure]['description']}: {place(years[0])}"
    way = direction(gap_in(years[0]))
    kind = "level"
    if len(years) > 1:
        moved = gap_in(years[-1]) - gap_in(years[0])
        way = direction(moved)
        kind = "gap"
        words = {"up": f"{name_a} gained ground", "down": f"{name_a} lost ground",
                 "none": "the gap was unchanged"}[way]
        note = "" if way == "none" else f"; {size_note(moved, 'change')}"
        text += f"; {place(years[-1])}: {words} ({show(moved, band, rate=True)} {change_unit(unit)}{note})"
    return {"kind": kind, "direction": way, "text": text + "."}


def comparisons(groups):
    """
    Every difference and direction code can state for a set of figures:
    each figure over time, each figure between editions, and each economy
    against the first economy named. groups maps (economy, measure, edition)
    to that figure's results, year by year.
    """
    found = []
    for (code, measure, edition), results in groups.items():
        item = over_time(results)
        if item:
            found.append(item)
    editions = sorted({key[2] for key in groups})
    if "archive" in editions and "latest" in editions:
        for (code, measure, edition), results in groups.items():
            newer = groups.get((code, measure, "latest"))
            if edition == "archive" and newer:
                for old in results:
                    for new in newer:
                        if new.year == old.year:
                            found.append(revision(old, new))
    codes = []
    for key in groups:
        if key[0] not in codes:
            codes.append(key[0])
    for (code, measure, edition), results in groups.items():
        first = groups.get((codes[0], measure, edition))
        if edition == "archive" and len(editions) > 1:
            continue        # a revision question compares editions, not economies
        if code != codes[0] and first:
            item = between(first, results)
            if item:
                found.append(item)
    return found


# Words in a question that assume a direction (14.4, the question's premise).
# Comparisons between economies are read first and removed, so "fallen
# behind" is a comparison, not a fall.
COMPARE_DOWN = re.compile(r"\b(fall(?:en|ing|s)? behind|fell behind|behind|lost ground|lower than|slower than)\b")
COMPARE_UP = re.compile(r"\b(ahead|caught up|catch(?:ing)? up|gained ground|higher than|faster than)\b")
CHANGE_DOWN = re.compile(r"\b(fell|fall|falls|fallen|falling|declin\w*|dropp?\w*|decreas\w*|"
                         r"shr[iau]nk\w*|slow\w*|wors\w*|revised down)\b")
CHANGE_UP = re.compile(r"\b(rose|rise|rises|risen|rising|grew|grown|increas\w*|improv\w*|revised up)\b")


def assumed(text, down_words, up_words):
    """ "down", "up" or None: the direction a text assumes, if it names only one."""
    down = down_words.search(text) is not None
    up = up_words.search(text) is not None
    if down and not up:
        return "down"
    if up and not down:
        return "up"
    return None


def premise_line(question, found):
    """
    The line that opens the locked block when the question assumes a
    direction that the figures contradict (fixes failing F16). A comparison
    between economies ("fallen behind") is checked against the calculated
    comparisons between economies; a change ("fell") against changes over
    time and between editions.

    Example:
        premise_line("Why did China's GDP per head fall ...?", [{"kind": "revision", "direction": "up", ...}])
        returns "The question assumes a fall; the figures show a rise."
    """
    text = question.lower()
    compare = assumed(text, COMPARE_DOWN, COMPARE_UP)
    text = COMPARE_UP.sub(" ", COMPARE_DOWN.sub(" ", text))
    change = assumed(text, CHANGE_DOWN, CHANGE_UP)
    between_ways = {i["direction"] for i in found if i["kind"] in ("gap", "level")}
    change_ways = {i["direction"] for i in found if i["kind"] in ("time", "revision", "growth")}
    if compare == "down" and "down" not in between_ways and "up" in between_ways:
        return "The question assumes it fell behind; the figures show it gained ground or is ahead."
    if compare == "up" and "up" not in between_ways and "down" in between_ways:
        return "The question assumes it caught up or is ahead; the figures show it lost ground or is behind."
    if change == "down" and "down" not in change_ways and "up" in change_ways:
        return "The question assumes a fall; the figures show a rise."
    if change == "up" and "up" not in change_ways and "down" in change_ways:
        return "The question assumes a rise; the figures show a fall."
    return None


def fetch(parameters, last_years):
    """
    The figures for a question, as facts_for (13.6) finds them, but keeping
    each result: groups maps (economy, measure, edition) to results year by
    year. Also the problems, the latest figures where the question asks
    beyond the data, and whether to escalate.
    """
    parameters = dict(parameters)
    if not parameters["years"] and len(parameters["editions"]) > 1:
        lasts = [last_years.get((code if (code, edition) in last_years else "EA21", edition))
                 for code in map(economy_code, parameters["economies"]) if code
                 for edition in parameters["editions"]]
        if lasts and None not in lasts:
            parameters["years"] = [str(min(lasts))]
    calls, problems = plan_calls(parameters, last_years)
    groups = {}
    for code, year, measure, edition in calls:
        result = call_model(code, year, measure, edition)
        if result.value is None and not parameters["years"]:
            for back in (1, 2, 3):
                result = call_model(code, year - back, measure, edition)
                if result.value is not None:
                    break
        if result.value is None:
            problems.append(result.message)
        else:
            groups.setdefault((code, measure, edition), []).append(result)
    beyond = []
    for year, latest in beyond_the_data(parameters, last_years):
        if latest.value is not None:
            beyond.append(f"- {year} is beyond the data. Latest: " + figure_line([latest])[2:])
    return groups, problems, beyond, escalate(calls, problems)


def locked_block(question, parameters, last_years, definitions):
    """
    Everything code writes for a reply, in the order the page shows it:
    the premise line (if any), figures, comparisons, what is missing, what
    each measure means and leaves out, and the escalation.

    Example:
        locked_block("Why did China's GDP per head at PPP fall ...?", parameters,
                     load_last_years(), load_definitions())["text"]
        starts "The question assumes a fall; the figures show a rise."
    """
    groups, problems, beyond, escalated = fetch(parameters, last_years)
    found = comparisons(groups)
    premise = premise_line(question, found)
    measures = []
    for key in groups:
        if key[1] not in measures:
            measures.append(key[1])
    figures = [figure_line(results) for results in groups.values()] + beyond
    definition_lines = [definition_line(m, definitions) for m in measures if m in definitions]
    parts = []
    if premise:
        parts.append(premise)
    parts.append("Figures (calculated from the data)\n" + ("\n".join(figures) or "- none"))
    if found:
        parts.append("Comparisons (calculated from the figures)\n" + "\n".join(item["text"] for item in found))
    if problems:
        parts.append("Missing\n" + "\n".join(f"- {p}" for p in problems))
    if definition_lines:
        parts.append("What the measures mean\n" + "\n".join(definition_lines))
    if escalated:
        parts.append(f"{ESCALATION_NOTE}\n{DEMONSTRATOR_ANALYST}")
    return {"premise": premise, "figures": figures, "comparisons": [i["text"] for i in found],
            "directions": [i["direction"] for i in found], "missing": problems,
            "definitions": definition_lines, "measures": measures, "escalate": escalated,
            "text": "\n\n".join(parts)}


# ---------------------------------------------------------------------------
# 14.3  Numbers: every number in the explanation is in the locked block
# ---------------------------------------------------------------------------

def invented_numbers(explanation, allowed_text):
    """
    The numbers in an explanation that are not in the allowed text (the
    question, the locked block and the passages given). Passage ids in
    square brackets are left out first, so "[esa10-8.94]" is not a number.

    Example:
        invented_numbers("It fell by 140 [esa10-8.94].", "5710 and 5570")
        returns ["140"]
    """
    return sorted(numbers_in(BRACKETS.sub(" ", explanation)) - numbers_in(allowed_text))


# ---------------------------------------------------------------------------
# 14.4  Direction words, and words that code decides
# ---------------------------------------------------------------------------

# Words that state a change or a comparison. The explanation may not use
# them: the locked block states every direction (the domain expert, 13 November 2026).
# The list cannot be complete; 14.4 lists what it misses ("more", "above")
# and what it rejects wrongly.
DIRECTION_WORDS = re.compile(
    r"\b(rose|rise|rises|rising|risen|fell|fall|falls|falling|fallen|grew|grows|growing|grown|"
    r"increas\w*|decreas\w*|declin\w*|dropp?\w*|higher|lower|highest|lowest|ahead|behind|"
    r"faster|slower|slow\w*|narrow\w*|widen\w*|outpac\w*|lagg?\w*|recover\w*|improv\w*|"
    r"wors\w*|shr[iau]nk\w*|surg\w*|jump\w*|plung\w*|soar\w*|"
    r"caught up|catch up|catching up|lost ground|gained ground|revised up|revised down)\b")

# Words for flags, data quality and escalation, which only the locked block may state (fixes
# failings F17 and F18).
CODE_WORDS = re.compile(r"\b(passed to an analyst|dqr|data quality|proxy|stand-in|estimated|flagg?\w*)\b")

# Remarks about the passages themselves (fix E): when the passages do not
# explain a point, the model writes NO_EXPLANATION instead.
PASSAGE_TALK = re.compile(r"\b(passages?|the text|provided)\b")
NO_EXPLANATION = "No explanation is available from the passages."


def words_found(pattern, text):
    """
    The words in a text that match a pattern, lower case, each once.

    Example:
        words_found(DIRECTION_WORDS, "Prices rose, then fell.") returns ["fell", "rose"]
    """
    return sorted({match.group(0) for match in pattern.finditer(text.lower())})


# ---------------------------------------------------------------------------
# 14.5  Citations: every sentence cites a passage that supports it
# ---------------------------------------------------------------------------

# A sentence is supported if at least this share of its words (Chapter 3's
# search words) is in the passage it cites. A passage given but not cited
# whose share is at least MISCITED_BY higher shows a miscitation (fix C).
# Both chosen by looking at the domain expert's 20 judgements: a training choice.
SUPPORT_MIN = 0.2
MISCITED_BY = 0.2


def overlap(sentence, passage):
    """
    The share of a sentence's search words that are in a passage's text.
    Citations are left out first. Scope notes are not counted: they are our
    notes, not evidence (the domain expert, 13 November 2026).

    Example:
        overlap("PPPs are statistical constructs [ppp23-1.31].", ppp23-1.31) returns 1.0
    """
    words = set(search_words(BRACKETS.sub(" ", sentence)))
    if not words:
        return 0.0
    return len(words & set(search_words(passage["text"]))) / len(words)


# Abbreviations whose full stops do not end a sentence (the domain expert, 16 November 2026).
ABBREVIATIONS = re.compile(r"\b(i\.e\.|e\.g\.)")


def explanation_sentences(text):
    """
    Split an explanation into sentences, with the id protocol agreed by the
    domain expert on 16 November 2026: ids go after their sentence, but a
    reply that starts with an id is read as putting every id before its
    sentence. "i.e." and "e.g." do not end a sentence.

    Example:
        explanation_sentences("[a-1] GDP is output. [b-2] GNI is income.")
        returns ["[a-1] GDP is output.", "[b-2] GNI is income."]
    """
    kept = ABBREVIATIONS.sub(lambda match: match.group(1).replace(".", "\x00"), text.strip())
    if kept.startswith("["):
        pieces = [piece.strip() for piece in SENTENCE_END.split(kept) if piece.strip()]
    else:
        pieces = sentences(kept)
    return [piece.replace("\x00", ".") for piece in pieces]


def check_sentences(text, evidence, must_cite_first=()):
    """
    Check each sentence's citations against the passages given (evidence):
    a sentence with no id, an id not given, a sentence its passage does not
    support, a sentence whose words are in another passage given (miscited),
    and, for definition questions, a first sentence that does not cite the
    defining passage (fix G). Returns a list of problems in plain words.

    Example:
        check_sentences("GDI is income.", evidence)
        returns ["Sentence 1 has no passage id: 'GDI is income.'"]
    """
    by_id = {p["id"]: p for p in evidence}
    same_letters = {i.lower(): i for i in by_id}      # ids compared without capitals
    problems = []
    for number, sentence in enumerate(explanation_sentences(text), 1):
        ids = [same_letters.get(i.lower(), i) for i in cited_ids(sentence)]
        if not ids:
            problems.append(f"Sentence {number} has no passage id: '{sentence}'")
            continue
        unknown = [i for i in ids if i not in by_id]
        if unknown:
            problems.append(f"Sentence {number} cites {', '.join(unknown)}, which you were not given.")
            continue
        best_cited = max(overlap(sentence, by_id[i]) for i in ids)
        if best_cited < SUPPORT_MIN:
            problems.append(f"Sentence {number} is not supported by the passage it cites: '{sentence}'")
        others = [(overlap(sentence, p), p["id"]) for p in evidence if p["id"] not in ids]
        if others:
            share, better = max(others)
            if share >= best_cited + MISCITED_BY:
                problems.append(f"Sentence {number} cites {', '.join(ids)}, but its words are in "
                                f"{better}: cite {better} if that is the source.")
        if number == 1 and must_cite_first and not set(ids) & set(must_cite_first):
            problems.append(f"Sentence 1 must cite the defining passage: {', '.join(must_cite_first)}.")
    return problems


def check_explanation(explanation, question, locked, evidence, must_cite_first=()):
    """
    Every check on an explanation (14.3 to 14.5). Returns a dict of the
    problems each check found; an explanation passes when every list is
    empty. NO_EXPLANATION on its own passes.
    """
    if explanation.strip() == NO_EXPLANATION:
        return {"numbers": [], "directions": [], "code_words": [], "passage_talk": [], "citations": []}
    allowed = question + " " + locked["text"] + " " + " ".join(p["text"] for p in evidence)
    return {"numbers": invented_numbers(explanation, allowed),
            "directions": words_found(DIRECTION_WORDS, BRACKETS.sub(" ", explanation)),
            "code_words": words_found(CODE_WORDS, explanation),
            "passage_talk": words_found(PASSAGE_TALK, BRACKETS.sub(" ", explanation)),
            "citations": check_sentences(explanation, evidence, must_cite_first)}


def passed(checks):
    """True when no check found a problem."""
    return all(not found for found in checks.values())


def problems_in_words(checks):
    """
    The problems as lines the retry message can show the model.

    Example:
        problems_in_words({"numbers": ["140"], "directions": [], ...})
        returns ["It contains numbers not in the locked block: 140."]
    """
    lines = []
    if checks["numbers"]:
        lines.append(f"It contains numbers not in the locked block: {', '.join(checks['numbers'])}.")
    if checks["directions"]:
        lines.append(f"It uses direction words, which only the locked block may use: "
                     f"{', '.join(checks['directions'])}.")
    if checks["code_words"]:
        lines.append(f"It writes about things code decides (flags, data quality, escalation): "
                     f"{', '.join(checks['code_words'])}.")
    if checks["passage_talk"]:
        lines.append(f"It comments on the passages themselves ({', '.join(checks['passage_talk'])}). "
                     f"If they do not explain the point, write only: {NO_EXPLANATION}")
    lines += checks["citations"]
    return lines


# ---------------------------------------------------------------------------
# 14.6  Evidence, the explanation, one retry and the fall-back
# ---------------------------------------------------------------------------

def load_graph(folder=GRAPH_FOLDER):
    """The knowledge graph's things (id, label, aliases) and triplets."""
    with open(folder / "entities.csv", encoding="utf-8") as file:
        things = list(csv.DictReader(file))
    with open(folder / "triples.csv", encoding="utf-8") as file:
        triplets = list(csv.DictReader(file))
    return things, triplets


def concepts_named(question, things):
    """
    The concepts in the knowledge graph that a question names, by label or
    alias (economies, indicators and manuals are left out), longest names first so "real gross domestic income" is found
    before "income".

    Example:
        concepts_named("What are the terms of trade?", load_graph()[0])
        returns ["terms_of_trade"]
    """
    text = question.lower()
    found = []
    names = []
    for thing in things:
        if thing["type"] != "Concept":
            continue
        for name in [thing["label"]] + [a.strip() for a in thing["aliases"].split(";")]:
            if name:
                names.append((len(name), name.lower(), thing["id"]))
    for _, name, thing_id in sorted(names, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", text) and thing_id not in found:
            found.append(thing_id)
            text = text.replace(name, " ")
    return found


def defining_passages(concepts, triplets):
    """
    The passages that define each concept (relation defined_in), and the
    concepts with no defining passage in the corpus (fixes A and B).

    Example:
        defining_passages(["terms_of_trade"], load_graph()[1])
        returns (["sna08-15.187"], [])
    """
    passages, undefined = [], []
    for concept in concepts:
        ids = [t["object"] for t in triplets if t["subject"] == concept and t["relation"] == "defined_in"]
        if ids:
            passages += [i for i in ids if i not in passages]
        else:
            undefined.append(concept)
    return passages, undefined


MAX_EVIDENCE = 5


# Definition questions (Chapter 12's classes): the first sentence must cite
# the defining passage, and a concept with none is named in the locked block.
DEFINITION_CLASSES = ("Q2", "Q6")


def evidence_for(question, locked, route, question_class, corpus, graph, definitions,
                 use_mode="non-commercial"):
    """
    The passages the explanation may use, chosen by code, in this order: the
    passages that define the concepts the question names; for questions
    routed to passages (route R4), the top three by BM25; the passages that
    define the measures in the locked block. Licence filter first (Chapter 8);
    at most MAX_EVIDENCE passages. For definition questions, also the ids
    the first sentence must cite and the concepts with no defining passage.
    """
    allowed, _ = licence_filter(corpus, use_mode)
    by_id = {p["id"]: p for p in allowed}
    things, triplets = graph
    defining, undefined = defining_passages(concepts_named(question, things), triplets)
    ids = list(defining)
    if "R4" in route:
        ids += [p["id"] for p in bm25s_rank(allowed, question) if p["id"] not in ids]
    for measure in locked["measures"]:
        ids += [i for i in definitions.get(measure, {}).get("passages", []) if i not in ids]
    evidence = [by_id[i] for i in ids if i in by_id][:MAX_EVIDENCE]
    if question_class not in DEFINITION_CLASSES:
        return evidence, [], []
    must_cite_first = [i for i in defining if i in by_id]
    names = {t["id"]: t["label"] for t in things}
    return evidence, must_cite_first, [names[c] for c in undefined]


EXPLAIN_INSTRUCTIONS = """You explain answers about national accounts statistics. The figures, the comparisons between them, what each measure means, and the data quality are already given under LOCKED BLOCK. Explain why, using only the passages under PASSAGES.

- Put the id of the passage each sentence comes from in square brackets at the end of the sentence, before the full stop. Every sentence needs one. Example, with a made-up id: Gross national income is the total primary income received by residents [example-1.1]. Use only the ids under PASSAGES.
- Do not repeat figures or work out numbers.
- Do not use words for direction or comparison, such as rose, fell, grew, higher, lower, increase, decrease, ahead, behind, faster, slower, narrowed or widened. The locked block states every direction.
- Do not write about data quality, flags, estimates or proxies, and do not pass the question to an analyst. The locked block does that.
- Do not comment on the passages themselves. If they do not explain the point, write only: No explanation is available from the passages.
- At most 120 words. No headings."""

EXPLAIN_SETTINGS = dict(SETTINGS, temperature=0, num_predict=400)


def explanation_messages(question, locked, evidence, must_cite_first=()):
    """
    The messages that ask the model for an explanation.

    Example:
        explanation_messages("Why did ...?", locked, evidence)[-1]["content"]
        starts "Question: Why did ...?"
    """
    content = (f"Question: {question}\n\nLOCKED BLOCK:\n{locked['text']}\n\nPASSAGES:\n\n"
               + "\n\n".join(format_evidence(p) for p in evidence))
    if must_cite_first:
        content += f"\n\nYour first sentence must cite {', '.join(must_cite_first)}."
    return [{"role": "system", "content": EXPLAIN_INSTRUCTIONS},
            {"role": "user", "content": content}]


def retry_messages(messages, first_reply, problems):
    """
    The messages for the one retry: the first conversation, the model's
    reply, and the problems the checks found.
    """
    note = ("Your explanation failed these checks:\n" + "\n".join(f"- {p}" for p in problems)
            + "\nWrite the explanation again, following every rule.")
    return messages + [{"role": "assistant", "content": first_reply},
                       {"role": "user", "content": note}]


def explain(question, question_class, locked, evidence, must_cite_first, ask):
    """
    Ask for an explanation, check it, retry once if it fails, and drop it if
    the retry fails too (the domain expert, 13 November 2026). Lookups (class Q1) get no
    explanation. Returns the status, the text shown, and every attempt.
    """
    if question_class == "Q1":
        return {"status": "lookup", "shown": None, "attempts": []}
    messages = explanation_messages(question, locked, evidence, must_cite_first)
    attempts = []
    for attempt in (1, 2):
        reply = ask(messages, EXPLAIN_SETTINGS)
        checks = check_explanation(reply["answer"], question, locked, evidence, must_cite_first)
        attempts.append({"reply": reply["answer"], "checks": checks,
                         "prompt_tokens": reply["prompt_tokens"],
                         "reply_tokens": reply["reply_tokens"], "seconds": reply["seconds"]})
        if passed(checks):
            status = "passed" if attempt == 1 else "passed on retry"
            return {"status": status, "shown": reply["answer"], "attempts": attempts}
        messages = retry_messages(messages, reply["answer"], problems_in_words(checks))
    return {"status": "dropped", "shown": None, "attempts": attempts}


def reply_page(locked, result, undefined=()):
    """
    The reply as the user sees it: the locked block, then the explanation,
    or the withheld line and the demonstrator note.
    """
    parts = [locked["text"]]
    for label in undefined:
        parts.append(f"The passages found do not define {label}.")
    if result["status"] in ("passed", "passed on retry"):
        parts.append(f"{EXPLANATION_HEADING}\n{result['shown']}")
    elif result["status"] == "dropped":
        parts.append(f"{WITHHELD}\n{DEMONSTRATOR_WITHHELD}")
    return "\n\n".join(parts)


def answer(question, parameters, route, question_class, ask, last_years, definitions, corpus, graph):
    """From a question and its parameters to a checked reply: the locked block,
    the evidence, the explanation (with one retry) and the page."""
    locked = locked_block(question, parameters, last_years, definitions)
    evidence, must_cite_first, undefined = evidence_for(question, locked, route, question_class,
                                                        corpus, graph, definitions)
    result = explain(question, question_class, locked, evidence, must_cite_first, ask)
    return {"locked": locked, "evidence": [p["id"] for p in evidence],
            "must_cite_first": must_cite_first, "undefined": undefined,
            "status": result["status"], "attempts": result["attempts"],
            "page": reply_page(locked, result, undefined)}


# ---------------------------------------------------------------------------
# 14.7  Results
# ---------------------------------------------------------------------------

def recheck_passage_answers(records, corpus):
    """
    Chapter 11's analyst answers under 14.5's checks: for each answer, the
    problems found. No new model run.
    """
    by_id = {p["id"]: p for p in corpus}
    found = {}
    for record in records:
        evidence = [by_id[i] for i in record["passage_ids"] if i in by_id]
        found[record["id"]] = check_sentences(record["answer"], evidence)
    return found


def load_judgements(file_path=JUDGEMENTS_FILE):
    """The domain expert's 20 judgements of support and relevance (13 November 2026)."""
    with open(file_path, encoding="utf-8") as file:
        return list(csv.DictReader(file))


def support_agreement(judgements, records, corpus):
    """
    For each of the domain expert's 20 sentences: his judgement, and whether 14.5's
    checks pass the sentence. He counts a miscited sentence as a failure
    (13 November 2026), so a miscitation the check finds agrees with him
    when he marks the miscitation in his notes; the rows are listed for
    reading, not only counted.
    """
    by_id = {p["id"]: p for p in corpus}
    answers = {r["id"]: r for r in records}
    rows = []
    for row in judgements:
        evidence = [by_id[i] for i in answers[row["question_id"]]["passage_ids"] if i in by_id]
        problems = check_sentences(row["sentence"], evidence)
        rows.append({"row": row["row"], "question_id": row["question_id"],
                     "expert_support": row["support"], "code_passes": not problems,
                     "problems": problems})
    return rows


def fair_questions():
    """The fair test's questions, labelled after the freeze; empty before."""
    return load_passages(FAIR_TEST_FILE) if FAIR_TEST_FILE.exists() else []


def run_explanations(questions, expected, ask=ask_model_with_details):
    """The checked reply for each question; keeps everything for scoring."""
    last_years = load_last_years()
    definitions = load_definitions()
    corpus = load_corpus()
    graph = load_graph()
    records = []
    for question in questions:
        record = answer(question["question"], expected[question["id"]], question["route"],
                        question["class"], ask, last_years, definitions, corpus, graph)
        record["id"] = question["id"]
        records.append(record)
    return records


def report_explanations(label, records):
    """Print how many explanations passed, passed on retry or were dropped,
    and which checks failed on the first attempt."""
    status = {}
    first_failures = {}
    for record in records:
        status[record["status"]] = status.get(record["status"], 0) + 1
        if record["attempts"]:
            for check, found in record["attempts"][0]["checks"].items():
                if found:
                    first_failures[check] = first_failures.get(check, 0) + 1
    print(f"{label}: {len(records)} questions; " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())))
    print("      first attempt failed on: " + (", ".join(f"{k} {v}" for k, v in
                                                        sorted(first_failures.items())) or "nothing"))


def main():
    expected = {row["id"]: row for row in load_passages(PARAMETER_FILE)}
    last_years = load_last_years()
    definitions = load_definitions()
    corpus = load_corpus()
    for question in bank_model_questions():
        if question["id"] in ("q4-02", "q5-02"):
            locked = locked_block(question["question"], expected[question["id"]], last_years, definitions)
            print(f"14.2  {question['id']}: {question['question']}\n{locked['text']}\n")

    answers = load_answers(ANSWERS_800_FILE)
    found = recheck_passage_answers(answers, corpus)
    failing = sum(bool(problems) for problems in found.values())
    print(f"14.5  Chapter 11 analyst answers: {len(found)}; failing the citation checks {failing}")
    rows = support_agreement(load_judgements(), answers, corpus)
    print(f"14.5  The domain expert's 20 sentences: code passes {sum(r['code_passes'] for r in rows)}; "
          f"the domain expert judged Supported {sum(r['expert_support'] == 'Supported' for r in rows)} (training)")
    for r in rows:
        if not r["code_passes"] or r["expert_support"] != "Supported":
            print(f"      row {r['row']} {r['question_id']}: the domain expert {r['expert_support']}; "
                  f"code {'passes' if r['code_passes'] else 'fails: ' + ' | '.join(r['problems'])}")

    if REPLIES_FILE.exists():
        replies = load_answers(REPLIES_FILE)
        directions = sum(bool(words_found(DIRECTION_WORDS, r["reply"])) for r in replies)
        code_words = sum(bool(words_found(CODE_WORDS, r["reply"])) for r in replies)
        print(f"14.4  Chapter 13's {len(replies)} replies (written to Chapter 13's instructions, which "
              f"asked for DQR and escalation) read as explanations: with direction words "
              f"{directions}; with words code decides {code_words}")

    bank = bank_model_questions()
    fair = fair_questions()
    fair_expected = {row["id"]: row for row in fair}
    run_file = REVIEW_FILE if "--review" in sys.argv else EXPLANATIONS_FILE
    if "--explain" in sys.argv:
        try:
            records = run_explanations(bank, expected) + run_explanations(fair, fair_expected)
        except urllib.error.URLError as error:
            print(f"Could not reach Ollama ({error.reason}). Start Ollama and run again.")
            return
        save_answers(run_file, records)
    if run_file.exists():
        records = load_answers(run_file)
        bank_ids = {q["id"] for q in bank}
        report_explanations("14.7  Bank questions (training)", [r for r in records if r["id"] in bank_ids])
        fair_records = [r for r in records if r["id"] not in bank_ids]
        if fair_records:
            report_explanations("14.7  New questions (fair)", fair_records)
        seconds = sum(a["seconds"] for r in records for a in r["attempts"])
        print(f"      {len(records)} questions in {seconds / 60:.1f} minutes")


if __name__ == "__main__":
    main()
