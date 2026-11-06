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
    Chapter 12 (ECONOMIES). The nni_model package: data, decomposition,
    dqr and crosschecks. Python's dataclasses and functools modules.

Run the worked example
    python -m ragbook.ch13_model_tool
        Calls the model for the bank's two value lookups and one year of the
        decomposition. Needs no language model.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import nni_model
from nni_model import dqr
from nni_model.crosschecks import load_inputs, output_per_hour
from nni_model.data import EURO_MEMBERS, Snapshot, load_csv
from nni_model.decomposition import NNIDecomposition

from ragbook.ch12_routing import ECONOMIES

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
}
SERIES = {"gni_per_head_ppp": "NY.GNP.PCAP.PP.CD", "population": "SP.POP.TOTL"}

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


def rating(measure, code, flags=(), chk=None):
    """The DQR band and reason, or (None, reason) for an economy S3 does not rate."""
    if code not in dqr.ECONOMIES:
        return None, "S3 rates only the six economies; no DQR for a single euro area member"
    words = [flag.split(":")[0] for flag in flags]
    result = dqr.rate(MEASURES[measure]["purpose"], code, flags=words, chk=chk,
                      inputs=MEASURES[measure]["inputs"])
    return result.name, result.reason


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

    if reply.value is None:
        reply.message = (f"No value for {measure} in {economy} in {year} "
                         f"in the {reply.edition} edition.")
        return reply
    reply.dqr_band, reply.dqr_reason = rating(measure, code, reply.flags, chk)
    if reply.dqr_band is None:
        reply.shown = f"{reply.value:.0f}"     # no band, so no digits rule; whole numbers
    else:
        band = {"High": dqr.HIGH, "Medium": dqr.MEDIUM, "Low": dqr.LOW}[reply.dqr_band]
        reply.shown = dqr.show(reply.value, band)
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


def main():
    for args in [("United Kingdom", 2024, "gni_per_head_ppp"),
                 ("India", 2022, "population"),
                 ("Japan", 2024, "nni_growth")]:
        r = call_model(*args)
        print(f"{r.economy} {r.year} {r.measure}: {r.shown} {r.unit} "
              f"[{r.dqr_band}: {r.dqr_reason}] flags={r.flags}")


if __name__ == "__main__":
    main()
