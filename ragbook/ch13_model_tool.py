"""
Chapter 13 — Calling a model instead of writing numbers

What this file does
    Calls the NNI model (github.com/lavanito/nni-model, installed from
    requirements.txt) as a tool. Each call names an economy, a year, a
    measure and a data edition; the reply gives the value with its unit,
    source, edition, input flags and data quality rating (DQR). Code works
    out every number and rating; a language model only reports them.

Inputs
    economy: a name ("United Kingdom") or a code ("GBR"); euro area members
        by code ("IRL").
    year: a whole year, such as 2024.
    measure: one of the names in MEASURES.
    edition: "latest" (WDI 8 October 2026) or "archive" (WDI March 2024).

Outputs
    A ToolResult. If the value cannot be worked out, value is None and
    message says what is missing and what the data contain.

Used by
    Chapter 14 (checking answers) and the demonstrator's route R2.

Uses
    Chapter 1 (load_passages, split_into_words); Chapter 2 (MODEL,
    OLLAMA_URL); Chapter 3 (QUESTION_FILE); Chapter 11 (SETTINGS, saving
    answers); Chapter 12 (economy names, test sets, the ragged edge). The
    nni_model package: data, decomposition, dqr and crosschecks. Python's
    json, re, urllib, dataclasses and functools modules.

Run the worked example
    python -m ragbook.ch13_model_tool
        Calls the model for the bank's two value lookups and one year of the
        decomposition, and scores the keyword rules that read parameters
        from questions (13.4). Needs no language model.
    python -m ragbook.ch13_model_tool --model
        Also asks the local language model (Ollama) for the parameters of
        the 28 questions routed to code, saves the replies and scores them.
"""
import json
import math
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import nni_model
from nni_model import dqr
from nni_model.crosschecks import load_inputs, output_per_hour
from nni_model.data import EURO_MEMBERS, Snapshot, load_csv
from nni_model.decomposition import NNIDecomposition

from ragbook.ch01_python_basics import load_passages, split_into_words
from ragbook.ch02_minimal_pipeline import MODEL, OLLAMA_URL
from ragbook.ch03_keyword_search import QUESTION_FILE
from ragbook.ch11_prompts import ANSWER_FOLDER, SETTINGS, load_answers, save_answers
from ragbook.ch12_routing import (ECONOMIES, ECONOMY_NAMES, REVISION_WORDS, SECOND_TEST_FILE,
                                  TEST_FILE, beyond_the_edge_message, contains_any,
                                  load_last_years)

# The six economies by name, and the codes the model uses.
ECONOMY_CODES = {
    "United States": "USA",
    "euro area": "EA21",
    "United Kingdom": "GBR",
    "China": "CHN",
    "India": "IND",
    "Japan": "JPN",
}
assert set(ECONOMY_CODES) == set(ECONOMIES)   # the same six as the router

# What the tool can return. Each measure names its unit, its source, the DQR
# purpose (S3 purposes table) and the inputs the rating looks at.
MEASURES = {
    "gni_per_head_ppp": {
        "description": "GNI per head at purchasing power parities",
        "unit": "current international dollars",
        "source": "World Bank WDI, series NY.GNP.PCAP.PP.CD",
        "purpose": "P2",
        "inputs": ["gni_nni", "ppp", "population"],
    },
    "population": {
        "description": "Population, total",
        "unit": "people",
        "source": "World Bank WDI, series SP.POP.TOTL",
        "purpose": "P2",
        "inputs": ["population"],
        "count": True,           # shown as a whole number whatever the band
    },
    "gdp_per_hour": {
        "description": "Real GDP per hour worked, at constant 2021 PPPs",
        "unit": "constant 2021 international dollars per hour",
        "source": "World Bank WDI (NY.GDP.MKTP.PP.KD); PWT 11.0 hours and persons engaged",
        "purpose": "P3",
        "inputs": ["real_gdp", "ppp", "employment", "hours"],
    },
    "nni_growth": {
        "description": "Growth in real NNI per head from the year before, split into parts",
        "unit": "log points",
        "source": "NNI model decomposition of World Bank WDI data",
        "purpose": "P4",
        "inputs": dqr.INPUTS["P4"],
    },
    # Added from the gap table, approved by Lavan on 7 November 2026. A
    # "proxy" entry is a stand-in for the figure asked: it is flagged, says
    # how it differs and where the best data are, and is rated at most Low.
    "real_gdp_growth": {
        "description": "Growth in real GDP (total, not per head) from the year before",
        "unit": "log points",
        "source": "World Bank WDI, series NY.GDP.MKTP.KN",
        "purpose": "P1",
        "inputs": ["real_gdp"],
    },
    "gdp_per_head_ppp": {
        "description": "GDP per head at purchasing power parities",
        "unit": "current international dollars",
        "source": "World Bank WDI: GDP (NY.GDP.MKTP.CN) / PPP factor (PA.NUS.PPP) / population",
        "purpose": "P2",
        "inputs": ["ppp", "population"],
    },
    "gni": {
        "description": "GNI, total",
        "unit": "current US dollars",
        "source": "World Bank WDI, series NY.GNP.MKTP.CD",
        "purpose": "P2",
        "inputs": ["gni_nni"],
        "count": True,
    },
    "average_hours": {
        "description": "Average annual hours worked per person engaged",
        "unit": "hours a year",
        "source": "Penn World Table 11.0 (avh)",
        "purpose": "P3",
        "inputs": ["hours"],
    },
    "real_nni_per_head_ppp": {
        "description": "Real NNI per head, at constant 2021 household-consumption PPPs",
        "unit": "constant 2021 international dollars",
        "source": "NNI model: real NNI per head, converted at the 2021 household PPP (PA.NUS.PRVT.PP)",
        "purpose": "P4",
        "inputs": dqr.INPUTS["P4"],
    },
    "real_nni_per_hour": {
        "description": "Real NNI per hour worked, at constant 2021 household-consumption PPPs",
        "unit": "constant 2021 international dollars per hour",
        "source": "NNI model real NNI per head; Penn World Table 11.0 hours and persons engaged",
        "purpose": "P4",
        "inputs": dqr.INPUTS["P4"],
        "also": [("P3", ["employment", "hours"])],
    },
    "employment_rate": {
        "description": "Employment rate",
        "unit": "per cent of total population",
        "source": "Penn World Table 11.0 persons engaged / World Bank WDI population",
        "purpose": "P3",
        "inputs": ["employment"],
        "proxy": {"differs": "persons engaged divided by total population; the usual rate divides "
                             "by the population aged 15 to 64",
                  "best_data": "ILOSTAT employment-to-population ratio; OECD employment rate, 15 to 64"},
    },
    "spending_components": {
        "description": "GDP by spending component",
        "unit": "per cent of GDP",
        "source": "World Bank WDI: household consumption (NE.CON.PRVT.CN) / GDP (NY.GDP.MKTP.CN)",
        "purpose": "P1",
        "inputs": ["real_gdp"],
        "proxy": {"differs": "household consumption only; government consumption, investment "
                             "and net trade are not in the data",
                  "best_data": "BEA NIPA Table 1.1.5 (Gross Domestic Product); World Bank WDI "
                               "NE.CON.GOVT.CN, NE.GDI.TOTL.CN, NE.EXP.GNFS.CN, NE.IMP.GNFS.CN"},
    },
    "trend_gap_2007": {
        "description": "Real GDP per head compared with its 2000 to 2007 trend",
        "unit": "per cent above (+) or below (-) the trend",
        "source": "World Bank WDI: GDP (NY.GDP.MKTP.KN) / population, constant local currency",
        "purpose": "P1",
        "inputs": ["real_gdp"],
        "proxy": {"differs": "the trend is growth from 2000 to 2007 only, because the data start "
                             "in 2000; a study may use a longer period and another method",
                  "best_data": "the study the question cites"},
    },
}
SERIES = {"gni_per_head_ppp": "NY.GNP.PCAP.PP.CD", "population": "SP.POP.TOTL",
          "gni": "NY.GNP.MKTP.CD", "average_hours": "PWT.AVH"}

# Figures not in the data at all: the reply names the best data and passes
# the question to an analyst (gap table, Lavan, 7 November 2026).
GAPS = {
    "terms_of_trade": {
        "description": "The terms of trade effect",
        "best_data": "export and import deflators: World Bank WDI exports and imports of goods and "
                     "services in current and constant local currency (NE.EXP.GNFS.CN and .KN, "
                     "NE.IMP.GNFS.CN and .KN), or national accounts",
    },
    "net_trade": {
        "description": "Net trade as a share of GDP",
        "best_data": "World Bank WDI NE.RSB.GNFS.ZS (external balance on goods and services, "
                     "% of GDP), or national accounts",
    },
    "public_service_measurement": {
        "description": "A comparison of how public services are measured",
        "best_data": "a comparable study of how each statistical office measures the volume of "
                     "public services, and a common method",
    },
}
ESCALATION_NOTE = "Passed to an analyst."

ARCHIVE_FILE = Path(nni_model.__file__).parent / "data" / "wdi" / "wdi_archive_202403.csv"


@dataclass
class ToolResult:
    """One reply from the model: the number and everything needed to report it."""
    economy: str
    year: int
    measure: str
    edition: str
    value: float = None
    shown: str = None            # the value as the page shows it, digits set by DQR band
    unit: str = None
    source: str = None
    flags: list = field(default_factory=list)
    dqr_band: str = None         # High, Medium or Low
    dqr_reason: str = None
    parts: dict = field(default_factory=dict)   # nni_growth only: C1a, C2, C4 and the rest
    message: str = None          # set when value is None


@lru_cache(maxsize=None)
def load_edition(edition):
    """The model's data for one edition, loaded once.

    The latest edition is the model's cross-check data: WDI 8 October 2026
    with the euro area built, PWT 11.0, and euro area GDP at PPPs summed
    from its members.
    """
    if edition == "latest":
        return load_inputs()
    if edition == "archive":
        return load_csv(ARCHIVE_FILE, Snapshot("WDI 2024-03"))
    raise ValueError(f"Unknown edition {edition!r}: use 'latest' or 'archive'")


def economy_code(economy):
    """A name or code for an economy, as the model's code, or None if not in the data."""
    if economy in ECONOMY_CODES:
        return ECONOMY_CODES[economy]
    if economy in ECONOMY_CODES.values() or economy in EURO_MEMBERS:
        return economy
    return None


# S3 rates only the six economies. A euro area member is given the euro area's
# rating: the members' statistical offices follow one standard, ESA 2010.
# Assumption agreed by Lavan, 6 November 2026.
MEMBER_ASSUMPTION = ("Assumption: rated as the euro area, because its members "
                     "follow one standard (ESA 2010)")


def rating(measure, code, flags=(), chk=None):
    """The DQR band and the reason that set it.

    A measure with more than one purpose takes the weakest rating. A proxy
    is rated at most Low (Lavan, 7 November 2026).
    """
    rated_as = "EA21" if code in EURO_MEMBERS else code
    words = [flag.split(":")[0] for flag in flags]
    m = MEASURES[measure]
    results = [dqr.rate(purpose, rated_as, flags=words, chk=chk, inputs=inputs)
               for purpose, inputs in [(m["purpose"], m["inputs"])] + m.get("also", [])]
    result = min(results, key=lambda r: r.band)          # weakest; first listed wins ties
    band, reason = result.band, result.reason
    if "proxy" in m:
        band, reason = dqr.LOW, f"proxy, rated at most Low; also {reason}"
    if rated_as != code:
        reason = f"{MEMBER_ASSUMPTION}; {reason}"
    return dqr.NAMES[band], reason


def show(value, band, count=False):
    """The value as the page shows it. Counts, such as population, have no
    decimal places (Lavan, 7 November 2026); other values follow the digits
    rule by band, and a Low band still says "about"."""
    if not count:
        return dqr.show(value, band)
    whole = f"{value:.0f}"
    return f"about {whole}" if band == dqr.LOW else whole


def log_change(old, new):
    """The change from old to new in log points."""
    return (math.log(new) - math.log(old)) * 100


def euro_area_sum(snapshot, code, value):
    """For the euro area, the sum of value(member) over its 21 members; otherwise value(code).
    None if any part is missing."""
    parts = [value(m) for m in EURO_MEMBERS] if code == "EA21" else [value(code)]
    return None if None in parts else sum(parts)


def gdp_per_head_ppp(s, code, y):
    """GDP in local currency / PPP factor / population; the euro area sums its members."""
    def at_ppp(e):
        gdp, ppp = s.get(e, "NY.GDP.MKTP.CN", y), s.get(e, "PA.NUS.PPP", y)
        return None if None in (gdp, ppp) else gdp / ppp
    total, population = euro_area_sum(s, code, at_ppp), s.get(code, "SP.POP.TOTL", y)
    return (None if None in (total, population) else total / population), []


def real_gdp_growth(s, code, y):
    old, new = s.get(code, "NY.GDP.MKTP.KN", y - 1), s.get(code, "NY.GDP.MKTP.KN", y)
    return (None if None in (old, new) else log_change(old, new)), []


def household_ppp(s, code, y):
    """The household-consumption PPP factor; for the euro area, members' household
    consumption in euros over the same in international dollars."""
    if code != "EA21":
        return s.get(code, "PA.NUS.PRVT.PP", y)
    euros = euro_area_sum(s, code, lambda e: s.get(e, "NE.CON.PRVT.CN", y))
    def dollars(e):
        cons, ppp = s.get(e, "NE.CON.PRVT.CN", y), s.get(e, "PA.NUS.PRVT.PP", y)
        return None if None in (cons, ppp) else cons / ppp
    international = euro_area_sum(s, code, dollars)
    return None if None in (euros, international) else euros / international


def real_nni_per_head_ppp(s, code, y, base=2021):
    """Real NNI per head in constant 2021 international dollars.

    In 2021: NNI in local currency / the 2021 household PPP / population.
    Other years: the 2021 level moved by the model's own real NNI per head,
    so growth matches the decomposition exactly (method approved by Lavan,
    7 November 2026).
    """
    model = NNIDecomposition(s, code)
    at_base, now = model.levels(base), model.levels(y)
    ppp, gdp = household_ppp(s, code, base), s.get(code, "NY.GDP.MKTP.CN", base)
    if None in (at_base, now, ppp, gdp):
        return None, []
    base_level = at_base.nni_to_gdp * gdp / ppp / at_base.population
    return base_level * now.real_nni_per_head / at_base.real_nni_per_head, list(now.flags)


def real_nni_per_hour(s, code, y):
    """Real NNI per head divided by hours worked per person in the population."""
    per_head, flags = real_nni_per_head_ppp(s, code, y)
    emp, avh, population = (s.get(code, c, y) for c in ("PWT.EMP", "PWT.AVH", "SP.POP.TOTL"))
    if None in (per_head, emp, avh, population):
        return None, []
    return per_head / (emp * avh / population), flags


def employment_rate(s, code, y):
    emp, population = s.get(code, "PWT.EMP", y), s.get(code, "SP.POP.TOTL", y)
    return (None if None in (emp, population) else emp / population * 100), []


def spending_components(s, code, y):
    cons, gdp = s.get(code, "NE.CON.PRVT.CN", y), s.get(code, "NY.GDP.MKTP.CN", y)
    return (None if None in (cons, gdp) else cons / gdp * 100), []


def trend_gap_2007(s, code, y):
    """Real GDP per head in year y against growth from 2000 to 2007 continued."""
    def per_head(t):
        gdp, population = s.get(code, "NY.GDP.MKTP.KN", t), s.get(code, "SP.POP.TOTL", t)
        return None if None in (gdp, population) else gdp / population
    first, last, now = per_head(2000), per_head(2007), per_head(y)
    if None in (first, last, now) or y <= 2007:
        return None, []
    trend = last * math.exp(math.log(last / first) / 7 * (y - 2007))
    return (now / trend - 1) * 100, []


# The measures worked out from the data by the functions above.
COMPUTE = {
    "real_gdp_growth": real_gdp_growth,
    "gdp_per_head_ppp": gdp_per_head_ppp,
    "real_nni_per_head_ppp": real_nni_per_head_ppp,
    "real_nni_per_hour": real_nni_per_hour,
    "employment_rate": employment_rate,
    "spending_components": spending_components,
    "trend_gap_2007": trend_gap_2007,
}


def call_model(economy, year, measure, edition="latest"):
    """Ask the NNI model for one value. Returns a ToolResult."""
    code = economy_code(economy)
    reply = ToolResult(economy=economy, year=year, measure=measure, edition=edition)
    if measure not in MEASURES:
        reply.message = f"Measure {measure!r} is not in the model. It offers: {', '.join(MEASURES)}."
        return reply
    if code is None:
        reply.message = (f"{economy} is not in the data. The data contain "
                         f"{', '.join(ECONOMY_CODES)} and the 21 euro area members.")
        return reply
    snapshot = load_edition(edition)
    reply.edition = snapshot.edition
    reply.unit = MEASURES[measure]["unit"]
    reply.source = MEASURES[measure]["source"]

    chk = None
    if measure in SERIES:
        reply.value = snapshot.get(code, SERIES[measure], year)
    elif measure == "gdp_per_hour":
        try:
            reply.value = output_per_hour(snapshot, code, year)
        except TypeError:          # a value is missing, so the division fails
            reply.value = None
    elif measure == "nni_growth":
        result = NNIDecomposition(snapshot, code).year(year)
        if result is not None:
            reply.value = result.total
            reply.flags = list(result.flags)
            chk = result.chk
            reply.parts = {"C1a": result.c1a, "C2": result.c2, "C4": result.c4,
                           "C4a": result.c4a, "C4b": result.c4b, "C4c": result.c4c,
                           "CHK": result.chk}
    elif measure in COMPUTE:
        reply.value, reply.flags = COMPUTE[measure](snapshot, code, year)
    if "proxy" in MEASURES[measure]:
        proxy = MEASURES[measure]["proxy"]
        reply.flags.append(f"proxy: {proxy['differs']}. Best data: {proxy['best_data']}")

    if reply.value is None:
        reply.message = (f"No value for {measure} in {economy} in {year} "
                         f"in the {reply.edition} edition.")
        return reply
    reply.dqr_band, reply.dqr_reason = rating(measure, code, reply.flags, chk)
    band = {"High": dqr.HIGH, "Medium": dqr.MEDIUM, "Low": dqr.LOW}[reply.dqr_band]
    reply.shown = show(reply.value, band, MEASURES[measure].get("count", False))
    return reply


# How the same tool is described to a language model that calls tools
# itself (Ollama's tool calling). The router's code does not need this: it
# calls call_model directly.
TOOL = {
    "type": "function",
    "function": {
        "name": "call_model",
        "description": "Get one value from the NNI model, with its unit, source, "
                       "data edition, flags and data quality rating.",
        "parameters": {
            "type": "object",
            "properties": {
                "economy": {"type": "string",
                            "enum": list(ECONOMY_CODES) + EURO_MEMBERS},
                "year": {"type": "integer", "description": "A year from 2000 to 2025"},
                "measure": {"type": "string", "enum": list(MEASURES),
                            "description": "; ".join(f"{name}: {m['description']}"
                                                     for name, m in MEASURES.items())},
                "edition": {"type": "string", "enum": ["latest", "archive"]},
            },
            "required": ["economy", "year", "measure"],
        },
    },
}


# ---------------------------------------------------------------------------
# 13.4  Reading the parameters from the question
# ---------------------------------------------------------------------------

PARAMETER_FILE = QUESTION_FILE.parent / "parameters_7_november.jsonl"
PARAMETER_REPLIES = ANSWER_FOLDER / "ch13_parameter_replies.jsonl"
FIRST_YEAR = 2000

# Phrases for the keyword rules, written out so a reader can argue with them.
MEASURE_PHRASES = {
    "gni_per_head_ppp": ["gni per head", "gni per capita"],
    "population": ["population"],
    "gdp_per_hour": ["gdp per hour", "output per hour", "productivity"],
    "nni_growth": ["growth in real nni", "nni growth", "drove growth", "deflator mix",
                   "between gdp and national income", "prices rather than volumes"],
    # Phrases for the measures added from the gap table (7 November 2026).
    "real_gdp_growth": ["real gdp growth"],
    "gdp_per_head_ppp": ["gdp per head at ppp"],
    "gni": ["gni in"],
    "average_hours": ["average hours worked"],
    "real_nni_per_head_ppp": ["net national income per head"],
    "real_nni_per_hour": ["nni per hour"],
    "employment_rate": ["employment rate"],
    "spending_components": ["expenditure components", "spending components"],
    "trend_gap_2007": ["trends had continued", "trend had continued"],
    "terms_of_trade": ["terms of trade"],
    "net_trade": ["net trade"],
    "public_service_measurement": ["public services are measured"],
}
SCENARIO_PHRASES = ["what if", "had been", "had grown", "had changed", "had continued"]
NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10}
LAST_N = re.compile(r"\blast (\w+) (years?|decades?)\b")
YEAR_WORD = re.compile(r"\b(?:19|20)[0-9]{2}\b")


def read_with_rules(question):
    """
    Read the parameters from a question with keyword rules.

    Years are kept as text: a four-digit year, "latest" (the last year in
    the data), or "latest-N" (N years before it). Code turns them into
    years later, from the ragged edge.

    Example:
        read_with_rules("What drove growth in real NNI per head in Japan last year?")
        returns {"economies": ["JPN"], "years": ["latest"], "measures": ["nni_growth"],
                 "editions": ["latest"], "change": False}
    """
    text = " " + " ".join(split_into_words(question)) + " "
    lower = question.lower()
    economies = [code for code, names in ECONOMY_NAMES.items()
                 if any(" " + name + " " in text for name in names)]
    years = YEAR_WORD.findall(question)
    if re.search(r"\bsince (?:19|20)[0-9]{2}\b", lower) or contains_any(lower, ["last year", "today"]):
        years.append("latest")
    span = LAST_N.search(lower)
    if span:
        word = span.group(1)
        count = int(word) if word.isdigit() else NUMBER_WORDS.get(word, 1)
        if span.group(2).startswith("decade"):
            count = count * 10
        years += [f"latest-{count}", "latest"]
    measures = [measure for measure, phrases in MEASURE_PHRASES.items()
                if contains_any(lower, phrases)]
    editions = ["latest", "archive"] if contains_any(lower, REVISION_WORDS) else ["latest"]
    return {"economies": economies, "years": list(dict.fromkeys(years)),
            "measures": measures or ["other"], "editions": editions,
            "change": contains_any(lower, SCENARIO_PHRASES)}


# The shape the model's reply must take. Ollama enforces it: the reply is
# valid JSON with these fields, and the choices listed are the only ones.
PARAMETER_SCHEMA = {
    "type": "object",
    "properties": {
        "economies": {"type": "array", "items": {
            "type": "string", "enum": list(ECONOMY_CODES) + EURO_MEMBERS + ["other"]}},
        "years": {"type": "array", "items": {"type": "string"}},
        "measures": {"type": "array", "items": {
            "type": "string", "enum": list(MEASURES) + list(GAPS) + ["other"]}},
        "editions": {"type": "array", "items": {"type": "string", "enum": ["latest", "archive"]}},
        "change": {"type": "boolean"},
    },
    "required": ["economies", "years", "measures", "editions", "change"],
}

PARAMETER_INSTRUCTIONS = """You read questions about national accounts statistics and reply with JSON only.

economies: the economies the question names. Use "United States", "euro area", "United Kingdom", "China", "India" or "Japan"; a single euro area member by its three-letter code (Ireland IRL, Germany DEU, France FRA); "other" for any other economy.
years: each year the question names, as four digits. "latest" for the last year in the data (last year, today, now, since a year). "latest-N" for N years before it (the last five years: "latest-5", "latest"). An empty list if no year is named.
measures: the measures the question asks for, from:
{measures}
Use "other" for any other measure. An empty list if none is named.
editions: ["latest"], or ["latest", "archive"] if the question asks about revisions or vintages.
change: true if the question asks what would happen if something had been different."""

# Made-up examples, not in the bank or the test sets, so every question there can be scored.
PARAMETER_EXAMPLES = [
    ("What was China's population in 2019?",
     {"economies": ["China"], "years": ["2019"], "measures": ["population"],
      "editions": ["latest"], "change": False}),
    ("How has the estimate of the UK's GNI per head at PPP for 2018 been revised?",
     {"economies": ["United Kingdom"], "years": ["2018"], "measures": ["gni_per_head_ppp"],
      "editions": ["latest", "archive"], "change": False}),
    ("What drove India's real NNI per head over the last three years?",
     {"economies": ["India"], "years": ["latest-3", "latest"], "measures": ["nni_growth"],
      "editions": ["latest"], "change": False}),
    ("What if Germany's population had been 5% larger in 2020?",
     {"economies": ["DEU"], "years": ["2020"], "measures": ["population"],
      "editions": ["latest"], "change": True}),
    ("How does euro area GDP per head in pounds compare with Japan's?",
     {"economies": ["euro area", "Japan"], "years": [], "measures": ["other"],
      "editions": ["latest"], "change": False}),
]

PARAMETER_SETTINGS = dict(SETTINGS, temperature=0, num_predict=150)


def parameter_messages(question):
    """
    Build the messages that ask the model to read one question's parameters.

    Example:
        parameter_messages("What is GDI?")[-1]
        returns {"role": "user", "content": "What is GDI?"}
    """
    measures = "\n".join(f"- {name}: {m['description']}"
                         for name, m in list(MEASURES.items()) + list(GAPS.items()))
    messages = [{"role": "system", "content": PARAMETER_INSTRUCTIONS.format(measures=measures)}]
    for example, reply in PARAMETER_EXAMPLES:
        messages.append({"role": "user", "content": example})
        messages.append({"role": "assistant", "content": json.dumps(reply)})
    messages.append({"role": "user", "content": question})
    return messages


def ask_model_for_json(messages, schema, options=PARAMETER_SETTINGS, model=MODEL, url=OLLAMA_URL):
    """
    Send the messages to the local model with a JSON shape the reply must
    follow (Ollama's "format" field). Returns the reply with its counts, as
    Chapter 11's ask_model_with_details does.
    """
    request_body = {"model": model, "messages": messages, "stream": False,
                    "options": options, "format": schema}
    data = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.loads(response.read().decode("utf-8"))
    return {
        "answer": reply["message"]["content"],
        "prompt_tokens": reply.get("prompt_eval_count", 0),
        "reply_tokens": reply.get("eval_count", 0),
        "seconds": reply.get("total_duration", 0) / 1_000_000_000,
    }


def read_model_reply(reply):
    """
    Turn the model's JSON reply into parameters, with economies as codes.

    A reply that is not valid JSON, or lacks a field, gives None, which
    counts as wrong.

    Example:
        read_model_reply('{"economies": ["Japan"], "years": [], "measures": [],
                           "editions": ["latest"], "change": false}')["economies"]
        returns ["JPN"]
    """
    try:
        found = json.loads(reply)
        return {"economies": [ECONOMY_CODES.get(e, e) for e in found["economies"]],
                "years": [str(year) for year in found["years"]],
                "measures": list(found["measures"]), "editions": list(found["editions"]),
                "change": bool(found["change"])}
    except (ValueError, KeyError, TypeError):
        return None


FIELDS = ["economies", "years", "measures", "editions", "change"]


def fields_right(found, expected):
    """
    Compare found parameters with the expected ones, field by field. Lists
    are compared as sets, so order does not count.

    Example:
        fields_right({"economies": ["JPN"], ...}, {"economies": ["JPN"], ...})["economies"]
        returns True
    """
    if found is None:
        return {name: False for name in FIELDS}
    return {name: (set(found[name]) == set(expected[name]) if name != "change"
                   else found[name] == expected[name]) for name in FIELDS}


def score_parameters(questions, expected, read):
    """
    Read every question's parameters and compare them with the expected ones.

    read: a function from a question to parameters, or to a saved reply
    record with "found" in it.
    """
    records = []
    for question in questions:
        found = read(question)
        right = fields_right(found, expected[question["id"]])
        records.append({"id": question["id"], "question": question["question"],
                        "found": found, "right": right, "all_right": all(right.values())})
    return records


def report_parameters(label, records):
    counts = {name: sum(r["right"][name] for r in records) for name in FIELDS}
    whole = sum(r["all_right"] for r in records)
    print(f"{label}: all five right {whole} of {len(records)}; "
          + ", ".join(f"{name} {count}" for name, count in counts.items()))


def resolve_year(text, last):
    """
    Turn "2016", "latest" or "latest-5" into a year, given the last year.

    Example:
        resolve_year("latest-5", 2024) returns 2019
    """
    if text == "latest":
        return last
    if text.startswith("latest-") and text[7:].isdigit():
        return last - int(text[7:])
    return int(text) if text.isdigit() else None


def plan_calls(parameters, last_years):
    """
    Check the parameters against the data and list the calls to make.

    Years are resolved from the ragged edge: "latest" is the last year with
    data for every economy named. A year outside the data, an economy or a
    measure not in the model, gives a problem message instead of a call.
    A span of years calls every year in it; for nni_growth, every year's
    growth, so the parts can be added up.

    Example:
        plan_calls({"economies": ["JPN"], "years": ["latest"], "measures": ["nni_growth"],
                    "editions": ["latest"], "change": False}, load_last_years())
        returns ([("JPN", 2024, "nni_growth", "latest")], [])
    """
    calls, problems = [], []
    codes = []
    for economy in parameters["economies"]:
        code = economy_code(economy)
        if code is None:
            problems.append(f"{economy} is not in the data. The data contain "
                            f"{', '.join(ECONOMY_CODES)} and the 21 euro area members.")
        else:
            codes.append(code)
    for measure in parameters["measures"]:
        if measure in GAPS:
            gap = GAPS[measure]
            problems.append(f"{gap['description']} is not in the data used here. "
                            f"Best data: {gap['best_data']}. {ESCALATION_NOTE}")
        elif measure not in MEASURES:
            problems.append(f"That measure is not one the model gives. It gives: "
                            f"{', '.join(m['description'] for m in MEASURES.values())}. "
                            f"{ESCALATION_NOTE}")
    measures = [m for m in parameters["measures"] if m in MEASURES]
    if not codes or not measures:
        return calls, problems
    for edition in parameters["editions"]:
        # A euro area member without its own row in last_year.csv uses the euro area's.
        rows = {code: code if (code, edition) in last_years else "EA21" for code in codes}
        lasts = {code: last_years[(rows[code], edition)] for code in codes}
        if None in lasts.values():
            missing = [code for code, last in lasts.items() if last is None]
            problems.append(beyond_the_edge_message((rows[missing[0]], edition, None)))
            continue
        last = min(lasts.values())
        years = [resolve_year(text, last) for text in parameters["years"]] or [last]
        if None in years:
            problems.append(f"Could not read the years {parameters['years']}.")
            continue
        for year in years:
            if year > last:
                code = min(lasts, key=lasts.get)
                problems.append(beyond_the_edge_message((rows[code], edition, lasts[code])))
            elif year < FIRST_YEAR:
                problems.append(f"The data here start in {FIRST_YEAR}.")
        years = sorted({year for year in years if FIRST_YEAR <= year <= last})
        if not years:
            continue
        for measure in measures:
            # A span fetches every year in it (Lavan, 7 November 2026). Growth in
            # a year is growth from the year before, so for nni_growth a span
            # from 2004 to 2024 is the growth of 2005 to 2024: 20 years.
            start = years[0] + 1 if measure == "nni_growth" else years[0]
            span = range(start, years[-1] + 1) if len(years) > 1 else years
            calls += [(code, year, measure, edition) for code in codes for year in span]
    return calls, problems


def escalate(calls, problems):
    """
    Say whether a question is passed to an analyst: when any figure asked
    for is missing, or is given only as a stand-in (proxy).

    Example:
        escalate([("GBR", 2023, "employment_rate", "latest")], []) returns True
    """
    return bool(problems) or any("proxy" in MEASURES[call[2]] for call in calls)


def model_questions():
    """The 28 questions routed to code: route R2, R4+R2 or R5>R2, bank and test sets."""
    questions = []
    for file_path in [QUESTION_FILE, TEST_FILE, SECOND_TEST_FILE]:
        questions += [q for q in load_passages(file_path) if "R2" in q["route"]]
    return questions


def read_parameters_with_model(questions, ask=ask_model_for_json):
    """Ask the model for each question's parameters; keep the reply, tokens and seconds."""
    records = []
    for question in questions:
        reply = ask(parameter_messages(question["question"]), PARAMETER_SCHEMA)
        records.append({"id": question["id"], "reply": reply["answer"],
                        "prompt_tokens": reply["prompt_tokens"],
                        "reply_tokens": reply["reply_tokens"], "seconds": reply["seconds"]})
    return records


def main():
    for args in [("United Kingdom", 2024, "gni_per_head_ppp"),
                 ("India", 2022, "population"),
                 ("Japan", 2024, "nni_growth")]:
        r = call_model(*args)
        print(f"{r.economy} {r.year} {r.measure}: {r.shown} {r.unit} "
              f"[{r.dqr_band}: {r.dqr_reason}] flags={r.flags}")
    questions = model_questions()
    expected = {row["id"]: row for row in load_passages(PARAMETER_FILE)}
    report_parameters("13.4  Rules", score_parameters(
        questions, expected, lambda q: read_with_rules(q["question"])))
    if "--model" in sys.argv:
        try:
            save_answers(PARAMETER_REPLIES, read_parameters_with_model(questions))
        except urllib.error.URLError as error:
            print(f"Could not reach Ollama ({error.reason}). Start Ollama and run again.")
            return
    if PARAMETER_REPLIES.exists():
        replies = {r["id"]: r for r in load_answers(PARAMETER_REPLIES)}
        report_parameters("13.4  Model", score_parameters(
            questions, expected, lambda q: read_model_reply(replies[q["id"]]["reply"])))
        seconds = sum(r["seconds"] for r in replies.values())
        print(f"      {len(replies)} replies in {seconds / 60:.1f} minutes")


if __name__ == "__main__":
    main()
