# Chapter 13 — Calling a model instead of writing numbers

## 13.1 What this chapter builds

The router (Chapter 12) gives each question a class and a route. Route R2 sends Q1, Q3, Q4 and Q5 questions, and the figure half of Q6, to code instead of a language model.

This chapter writes that code. One function, `call_model`, asks the NNI model for one value and returns it with its unit, source, data edition, flags and data quality rating (DQR).

- **The language model only reports the number.** A language model writes text one token at a time; a figure it writes is a guess unless it copies one from its prompt. Code works out every value and every rating.
- **The NNI model is installed, not copied.** It lives in its own repository. `requirements.txt` installs it from GitHub at one fixed commit, so the textbook and the demonstrator run the same code on the same data.

## 13.2 A tool's contract

### 13.2.1 Principles

A tool is a function a program can call, with fixed inputs and outputs. Its contract lists both, so the caller knows what to send and what comes back.

| Input | What it is |
| --- | --- |
| economy | A name ("United Kingdom") or a code ("GBR"); euro area members by code ("IRL") |
| year | A whole year, such as 2024 |
| measure | One of the measures in MEASURES: four at first (GNI per head at PPP, population, GDP per hour worked, growth in real NNI per head split into parts), 13 after the gap table of 13.5 |
| edition | "latest" (WDI 8 October 2026) or "archive" (WDI March 2024) |

| Output | What it is |
| --- | --- |
| value, shown | The number, and the number with its digits set by DQR band |
| unit, source, edition | What the number measures and where it comes from |
| flags | "estimated" or "break", with the reason |
| DQR band and reason | High, Medium or Low, and the input that set it |
| parts | For growth only: C1a, C2, C4, C4a, C4b, C4c and CHK |
| message | Set when there is no value: what is missing and what the data contain |

There are two ways to call the same function.

- **Code calls it from the router's labels.** This chapter does so: the router names R2, and code passes the economy, year and measure.
- **A language model calls it itself.** The model is given a description of the tool. It replies with the function's name and arguments, and the program runs the function (Ollama's tool calling).

### 13.2.2 Code

`ragbook/ch13_model_tool.py`, the measures, the reply and the tool description:

```python
MEASURES = {
    "gni_per_head_ppp": {
        "description": "GNI per head at purchasing power parities",
        "unit": "current international dollars",
        "source": "World Bank WDI, series NY.GNP.PCAP.PP.CD",
        "purpose": "P2",
        "inputs": ["gni_nni", "ppp", "population"],
    },
```

```python
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
```

```python
TOOL = {
    "type": "function",
    "function": {
        "name": "call_model",
        "description": "Get one value from the NNI model, with its unit, source, "
                       "data edition, flags and data quality rating.",
```

### 13.2.3 Annotations

- **Each measure names its DQR purpose and inputs,** from the S3 statement. The rating looks only at those inputs: India's population is rated on population alone (Medium, last census 2011).
- `shown` **sets the digits by band** (build spec v2, decision 4): High one decimal place, Medium a whole number, Low "about" and a whole number. Counts, such as population, are always whole numbers (Lavan, 7 November 2026).
- **The description lists the measures and economies as fixed choices.** A reply outside them gets a message, not a number.

## 13.3 Calling the model

### 13.3.1 Principles

The NNI model is installed as a package, `nni-model`, pinned to one commit (Lavan, 6 November 2026). The textbook imports it like any other package.

`call_model` checks the economy and the measure, loads the edition once, works out the value and rates it. When there is no value, it says what is missing and what the data contain, as Chapter 12's escalation messages do.

### 13.3.2 Code

```python
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
```

```python
# Rates (log points, per cent) get one more decimal place than levels:
# High 2, Medium 1, Low "about" and 1 (Lavan, 7 November 2026).
RATE_DECIMALS = {dqr.HIGH: 2, dqr.MEDIUM: 1, dqr.LOW: 1}


def is_rate(unit):
    """A growth rate or a share: its unit is log points or per cent."""
    return "log points" in unit or unit.startswith("per cent")


def show(value, band, count=False, rate=False):
    """The value as the page shows it. Counts, such as population, have no
    decimal places (Lavan, 7 November 2026); rates have one more decimal
    place than levels; other values follow the digits rule by band. A Low
    band always says "about".

    Example:
        show(1.234, dqr.MEDIUM, rate=True) returns "1.2"
    """
    if rate:
        text = f"{value:.{RATE_DECIMALS[band]}f}"
    elif count:
        text = f"{value:.0f}"
    else:
        return dqr.show(value, band)
    return f"about {text}" if band == dqr.LOW else text
```

```python
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
    reply.shown = show(reply.value, band, MEASURES[measure].get("count", False),
                       is_rate(MEASURES[measure]["unit"]))
    return reply
```

### 13.3.3 Annotations

- **Two editions.** "latest" is WDI of 8 October 2026 with PWT 11.0, and euro area GDP at PPPs summed from its members. "archive" is WDI of March 2024, with no euro area. Q4 questions compare the two: India's GNI per head at PPP for 2016 differs between them.
- **Euro area members are rated as the euro area.** S3 rates only the six economies. The members' statistical offices follow one standard, ESA 2010, so a member is given the euro area's band, and the reason states this as an assumption (Lavan, 6 November 2026). Ireland's GNI per head at PPP for 2024 is 105767, rated Medium: the euro area's rating, whose reason is Ireland's multinational profits.
- **The model builds euro area GNI per head at PPP** (Lavan, 6 November 2026). Each member's GNI in euros, divided by its PPP conversion factor, is in current international dollars, so the members add up; the total is divided by euro area population. For the United States, United Kingdom, Japan and China the same formula reproduces WDI's published figure within WDI's rounding to 10 dollars. The euro area's value for 2024 is 65935, rated Medium because its total includes Ireland's multinational profits.

### 13.3.4 Results

The worked example, `python -m ragbook.ch13_model_tool`, with two more calls:

| Economy, year | Measure | Shown | DQR band | Flags |
| --- | --- | --- | --- | --- |
| United Kingdom, 2024 | GNI per head at PPP | 62220 current international dollars | Medium | none |
| India, 2022 | Population | 1425423212 | Medium | none |
| Japan, 2024 | Growth in real NNI per head | 1 log point | Medium | estimated |
| United States, 2023 | GDP per hour worked | 84 constant 2021 international dollars | Medium | none |
| euro area, 2023 | GDP per hour worked | 75 constant 2021 international dollars | Medium | none |

Each Medium band comes from one input: PPPs after 2021 are extrapolated from the ICP 2021 benchmark, India's last census was in 2011, and depreciation estimates differ in method between economies.

## 13.4 Reading the parameters from the question

### 13.4.1 Principles

Before code can call the model, someone must read the question: which economies, which years, which measure. Chapter 12 named this route R5>R2: a small model reads, then code computes.

The reading gives five parameters.

| Parameter | What it holds |
| --- | --- |
| economies | Codes: USA, EA21, GBR, CHN, IND, JPN, or a euro area member such as IRL |
| years | Four digits; "latest" for the last year in the data; "latest-5" for five years before it |
| measures | The four measures of 13.2, or "other" |
| editions | latest, or latest and archive for a question about revisions |
| change | Whether the question asks what would happen if something had been different (Q7) |

Years stay as text until code checks them. "Last year" for Japan becomes 2024, because Japan's data end in 2024; for the United Kingdom it becomes 2025. This is Chapter 12's ragged edge.

Two readers are compared, as in Chapter 12.

- **Keyword rules:** phrase lists for measures, Chapter 12's economy names, and patterns for years such as "since 2007" and "the last two decades".
- **The small model:** qwen3:4b-instruct at temperature 0, given the five parameters, the four measures and five made-up examples. Ollama makes the reply follow a fixed JSON shape: valid JSON, the five fields, and only the listed economies and measures.

Then code checks the reply against the data and lists the calls to `call_model`. Anything outside the data gives a message instead of a call.

### 13.4.2 Code

`ragbook/ch13_model_tool.py`, the reply's shape, reading the reply, and the checks:

```python
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
```

```python
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
```

```python
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
```

### 13.4.3 Annotations

- **The shape stops some errors, not all.** The model cannot reply with a measure that is not listed or with broken JSON. It can still pick the wrong measure from the list.
- **"Latest" uses the earliest last year among the economies named.** A comparison of the United States (data end in 2024) and the United Kingdom (2025) uses 2024 for both.
- **No year named means the latest year.** q5-01 asks how the euro area compares with the United States, with no year, so code uses 2024.
- **A member without its own last year uses the euro area's.** The ragged-edge table has rows for Ireland and the six economies only.

### 13.4.4 Results

The expected parameters for the 28 questions routed to code (14 from the bank, 14 from the two test sets) are in `data/question_bank/parameters_7_november.jsonl`. Claude proposed them on 7 November 2026. Lavan checked them the same day and changed five (q5-02, q5-05, t-25, t-30, u-09); PARAMETERS.md records each change. He also decided that a span of years fetches every year to the end of the data, for every measure.

| Reader | All five right | Economies | Years | Measures | Editions | Change |
| --- | --- | --- | --- | --- | --- | --- |
| Keyword rules (training score) | 21 | 27 | 27 | 22 | 28 | 28 |
| Small model (training score) | 12 | 28 | 23 | 15 | 26 | 28 |

- **Both scores are training scores.** The rules and the model's instructions were written after reading all 28 questions.
- **The rules miss seven.** "Fallen behind" (q5-02), "average hours ... contributes" (u-05) and "grown" with a deflator (u-14) match no measure phrase; q7-01 names the yen, not Japan; t-02's "2026 IEA analysis" is read as a data year. q5-05 needs no figure and t-25 asks for growth per head: Lavan set both after the rules were written.
- **Every figure asked for now has a route.** The first four measures covered 16 of the 28; the gap table of 13.5 adds nine measures and three figures that are not in the data.

Lavan ran the model on 7 November 2026: 28 replies in 5.6 minutes, 11.9 seconds each, with about 841 tokens in and 49 out. Every reply was valid JSON.

- **The model scores lower than the rules: 12 against 21.** It gets none right that the rules miss.
- **Most misses are the measure (13 of 16).** The parts of NNI growth are not named in its description, so "the deflator mix" (q6-01) and "the gap between GDP and national income" (q6-03) became "other", and "prices rather than volumes" (q3-02) became the terms of trade.
- **A measure's name can mislead.** q5-02 asks about the UK "since 2007"; the model picked trend_gap_2007, whose name contains the year.
- **Some misses are arguable.** For t-25 ("what if euro area GDP had grown at the same rate as the US") the model picked real GDP growth; the key has growth per head, chosen before real GDP growth was a measure.
- **Two year misses change nothing downstream.** t-26 lists 2022, 2023 and 2024 instead of 2022 and 2024, and code fetches every year in a span either way. t-22 lists the 20 years before the latest but not the latest, so code would stop a year early.
- **Revisions were missed twice** (q4-02, t-23): the model gave only the latest edition.

### 13.4.5 Round 2 and a fair test

A change to the instructions written after reading the 28 questions will raise the score on those 28. That shows only that it fits them. To learn whether it helps on questions a user might ask, it must be scored on questions written after the change.

The order was fixed in advance (Lavan, 7 November 2026):

1. **Claude wrote round 2 and committed it** (`7b756d3`): spans give their first and last year; the model decides first whether a question asks for a level or for growth; every measure says which it is; nni_growth names its parts; revision words mean both editions; trend_gap_2007 became trend_gap.
2. **Lavan wrote 20 new questions** without showing them. Claude proposed labels, with 13 judgement calls noted, and Lavan agreed them.
3. **One laptop run** gave round 2 on the 28, and both rounds on the 20: 68 replies in 13.9 minutes. Round 2's instructions are longer: 1,111 tokens in, against 838.

A second, looser score counts a reading as right if code would fetch the same figures: no year and "latest" fetch the same, for example.

```python
def same_calls(found, expected, last_years):
    """
    Say whether found parameters would fetch the same figures as the
    expected ones: the same calls, a problem message in both or neither,
    and the same answer on "what if". A second, looser score: no year and
    "latest" fetch the same figures, so they count as the same here.
    """
    if found is None:
        return False
    calls, problems = plan_calls(found, last_years)
    expected_calls, expected_problems = plan_calls(expected, last_years)
    return (set(calls) == set(expected_calls) and bool(problems) == bool(expected_problems)
            and found["change"] == expected["change"])
```

| Reader | 28 questions (training): all five right | Same figures | 20 new questions (fair): all five right | Same figures |
| --- | --- | --- | --- | --- |
| Keyword rules | 21 | 21 | 1 | 2 |
| Model, round 1 | 12 | 13 | 2 | 6 |
| Model, round 2 | 15 | 17 | 6 | 9 |

- **The rules fall from 21 of 28 to 1 of 20.** Their phrase lists match the wordings they were written from; on new wordings they find the measure for 3 of 20.
- **Round 2 reads new questions better than round 1: 6 against 2.** It is right on four questions where round 1 is wrong (n-10, n-11, n-12, n-19) and wrong on none where round 1 is right. Four changes are too few to rule out chance (sign test, p = 0.125), but none goes the other way.
- **On the 28, round 2 gains four and loses one** (t-24): 15 against 12.
- **No reader is good enough to use alone.** The best fair score is 6 of 20, or 9 of 20 on the figures fetched.
- **Round 2's misses on the new questions:**
    - Four times (n-01 to n-04) "how much has real NNI per head grown" gave the level as well as growth.
    - Three times "the latest data" gave no year; the same figures are fetched.
    - n-13 and n-14 (how long to catch up) and n-06 (how much China's GDP is revised) became "other".
    - n-09 read "real GDP per head" as real GDP growth, the level and growth confusion this chapter tests for.

## 13.5 Flags and messages

### 13.5.1 Principles

Every figure carries flags, and three of them lower its DQR band.

| Flag | When | Band at most |
| --- | --- | --- |
| estimated | NNI after the last published year: NNI = GNI times the last published NNI/GNI | Medium |
| break | A series changes source or base, such as India's GDP in 2022 | Low |
| proxy | A stand-in for the figure asked for | Low |

Some questions ask for a figure the tool did not give. Lavan's rule (7 November 2026) gives up to three answers at once.

1. **If the figure is in the data, give it exactly,** as a new measure.
2. **If only a near figure is in the data, give that stand-in,** flagged "proxy", with how it differs from what was asked and the best data for the question.
3. **If neither, give no figure;** name the best data and who publishes it.

Any answer that is not exact is also escalated: the trace marks it "passed to an analyst". The gap table lists what each figure gets.

| Figure asked for | Questions | The reply gives |
| --- | --- | --- |
| Real GDP growth (total) | q5-03 | Exact: growth per head plus population growth |
| GDP per head at PPP, both editions | q4-02 | Exact |
| GNI, total | t-21 | Exact |
| Average hours worked | u-09 | Exact (PWT, to 2023) |
| Real NNI per head in international dollars | u-02 | Exact (method below) |
| Real NNI per hour worked | u-07 | Exact (to 2023) |
| Employment rate | u-06 | Proxy: persons engaged over total population |
| GDP by spending component | t-26 | Proxy: household consumption share only |
| UK GDP per head against its pre-2008 trend | t-02 | Proxy: trend from 2000 to 2007 |
| Terms of trade effect | t-30 | No figure: export and import deflators needed |
| Net trade | t-24 | No figure |
| How public services are measured | q5-03 | No figure: a comparable study needed |

### 13.5.2 Code

A proxy measure names how it differs and where the best data are:

```python
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
```

Real NNI per head in international dollars:

```python
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
```

When a question is passed to an analyst:

```python
def escalate(calls, problems):
    """
    Say whether a question is passed to an analyst: when any figure asked
    for is missing, or is given only as a stand-in (proxy).

    Example:
        escalate([("GBR", 2023, "employment_rate", "latest")], []) returns True
    """
    return bool(problems) or any("proxy" in MEASURES[call[2]] for call in calls)
```

### 13.5.3 Annotations

- **The level of real NNI per head is fixed in 2021 and moved by the model's growth.** Its growth from one year to the next equals the decomposition's total exactly; a test checks this for the six economies.
- **The euro area's household PPP weights members by household consumption:** members' consumption in euros, divided by the same in international dollars.
- **Real GDP growth is exact, not a stand-in:** growth in real GDP per head plus growth in population. A test checks the sum.
- **Sources checked on 7 November 2026.** Five of the seven WDI codes and the BEA table name were found on the web. Lavan checked the other two against the World Bank API the same day: NE.GDI.TOTL.CN is "Gross capital formation (current LCU)" and NE.IMP.GNFS.KN is "Imports of goods and services (constant LCU)".

### 13.5.4 Results

| Economy, year | Figure | Shown | DQR band |
| --- | --- | --- | --- |
| United States, 2024 | Real GDP growth | 2.75 log points | High |
| China, 2016 | GDP per head at PPP, latest / archive edition | about 14157 / about 13483 current international dollars | Low |
| Ireland, 2008 | GNI | 238433636292 current US dollars | Medium |
| China, 2021 | Average hours worked | about 2292 hours a year | Low |
| Japan, 2024 | Real NNI per head | 31756 constant 2021 international dollars | Medium (estimated) |
| United States, 2023 | Real NNI per hour worked | 68 constant 2021 international dollars an hour | Medium (estimated) |
| United Kingdom, 2023 | Employment rate (proxy) | about 49.0 per cent of total population | Low |
| United Kingdom, 2025 | GDP per head against the 2000 to 2007 trend (proxy) | about -23.3 per cent | Low |

Rates (log points, per cent) show one more decimal place than levels: High 2, Medium 1, Low "about" and 1 (Lavan, 7 November 2026). Under the first rule, Japan's 2024 growth read "1 log point" with parts of 0 and 1.

### 13.5.5 Beyond the data

Chapter 12's escalation message for a year after the data end says only where the data stop. The fuller message also gives the latest figure, with its source, edition and DQR, so the user leaves with a number.

```python
def beyond_the_data(parameters, last_years):
    """
    The latest figure for each economy and measure whose question asks for
    a year after the data end: the year asked for, and a ToolResult for the
    last year with data, with its source, edition and DQR.

    Example:
        beyond_the_data({"economies": ["JPN"], "years": ["2026"],
                         "measures": ["gni_per_head_ppp"], ...}, load_last_years())
        returns [(2026, ToolResult for Japan in 2024)]
    """
    found = []
    for economy in parameters["economies"]:
        code = economy_code(economy)
        if code is None:
            continue
        for edition in parameters["editions"]:
            row = code if (code, edition) in last_years else "EA21"
            last = last_years.get((row, edition))
            if last is None:
                continue
            asked = [resolve_year(text, last) for text in parameters["years"]]
            beyond = [year for year in asked if year is not None and year > last]
            for measure in [m for m in parameters["measures"] if m in MEASURES]:
                for year in beyond:
                    found.append((year, call_model(code, last, measure, edition)))
    return found
```

## 13.6 Results

### 13.6.1 Principles

The last step turns figures into a reply. Code works out every figure and writes it as one line: the value, unit, year, source, edition, DQR band and reason, and flags. The language model is asked only to report those lines in words.

Code then checks the reply. Every number in it must appear in the question or the figures; any other number is invented. The reply must end "Passed to an analyst." exactly when code decided to escalate.

The test uses the bank's 14 questions routed to code, with the checked parameters of 13.4, so a misread question does not count against the reply.

### 13.6.2 Code

```python
REPLY_INSTRUCTIONS = """You answer questions about national accounts statistics. Use only the figures you are given.

- Copy every number exactly as it is written in FIGURES, with its unit and year. Do not work out new numbers.
- Give each figure's DQR band (High, Medium or Low).
- If a figure is flagged "estimated" or "proxy", say so in plain words.
- If MISSING lists anything, say what is missing and where the best data are.
- If ESCALATE is yes, end with the sentence: Passed to an analyst.
- At most 150 words. No headings."""
```

```python
def check_reply(question, facts, reply):
    """
    Check a reply against its facts. Returns the numbers in the reply that
    are not in the question or the facts (invented numbers), and whether
    the reply escalates exactly when it should.
    """
    allowed = numbers_in(question + " " + " ".join(facts["figures"] + facts["missing"]))
    invented = sorted(numbers_in(reply) - allowed)
    escalated = "Passed to an analyst" in reply
    return {"invented": invented, "escalation_right": escalated == facts["escalate"]}
```

### 13.6.3 Results

Lavan ran the model on 7 November 2026: 14 replies in 5.1 minutes, with about 347 tokens in and 88 out each.

| Check | Replies right of 14 |
| --- | --- |
| No invented number | 13 |
| Escalates exactly when code decided | 7 |
| No flag the figures do not have | 7 |

- **One reply worked out a number, and got its sign wrong.** For q4-01 the model wrote that India's 2016 GNI per head "increased by 140" between editions. It fell, from 5710 in the March 2024 edition to 5570 in the latest. The number check caught it.
- **One reply followed a wrong premise, and the check missed it.** q4-02 asks why China's and India's GDP per head at PPP fell with the new ICP results. In the data both rose: China from 21483 to 23028 in 2022. The model copied the numbers correctly but swapped the editions, so it reported a fall. No number was invented.
- **The model escalated whenever it could.** Seven replies end "Passed to an analyst." when code had decided not to escalate.
- **It added flags.** Seven replies call a figure "estimated" or "proxy" when the figures carry no such flag.
- **What follows:** anything code can decide, code should write. The escalation sentence and the flags can be added by code after the reply. Only the wording is left to the model, and Chapter 14 checks it further.

## Tests

`tests/test_ch13_model_tool.py`, 45 tests. They check properties and saved results, never wording.

- **The tool:** values match the model's own data; ratings match the model's rule; the parts of NNI growth add up to the total; flags and breaks appear where they should; euro area members are rated as the euro area; counts and rates show the agreed digits.
- **The added measures:** real GDP growth equals growth per head plus population growth; real NNI per head grows exactly as the decomposition says; a proxy is flagged and rated Low; a figure not in the data names the best data and escalates.
- **Reading parameters:** every question routed to code has an answer key; relative years come from the ragged edge; spans fetch every year; a stand-in model that copies the key scores 28.
- **Saved runs:** each laptop run scores as reported (12, 15, 2 and 6, and the reply checks).

## Glossary additions

- **Tool:** a function a program or a language model can call, with fixed inputs and outputs.
- **Contract (of a tool):** the list of a tool's inputs and outputs.
- **Tool calling:** a language model replies with a function's name and arguments; the program runs the function.
- **Pinned install:** installing a package at one fixed commit, so every run uses the same code.
- **Parameter:** one input a question gives to the tool: an economy, a year, a measure or an edition.
- **Enforced JSON shape:** Ollama makes the reply valid JSON with the listed fields, and allows only the listed choices.
- **Relative year:** "latest" or "latest-N", turned into a year from the last year of data.
- **Answer key:** the expected parameters each reading is scored against.
- **Fair score:** a score on questions written after the rules or instructions were fixed.
- **Sign test:** counts the questions on which one reader is right and the other wrong, and asks how likely that split is by chance.
- **Proxy:** a stand-in figure close to the one asked for, flagged and rated at most Low.
- **Gap table:** for each figure the tool lacks, what the reply gives instead.
- **Escalate:** mark a question as passed to an analyst, with what was missing.
- **Household-consumption PPP:** a currency converter based on the prices of what households buy.
- **Invented number:** a number in a reply that is in neither the question nor the figures.

## Links

- [nni-model repository](https://github.com/lavanito/nni-model)
- [World Bank WDI: GDP per capita, PPP (NY.GDP.PCAP.PP.CD)](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD?start=2015)
- [World Bank WDI: general government final consumption (NE.CON.GOVT.CN)](https://data.worldbank.org/indicator/NE.CON.GOVT.CN)
- [BEA NIPA Table 1.1.5, Gross Domestic Product (via FRED)](https://fred.stlouisfed.org/graph/?g=1hBCO)
- Repository files: `ragbook/ch13_model_tool.py`, `data/question_bank/PARAMETERS.md`, `data/question_bank/parameters_test.jsonl`, `data/answers/ch13_replies.jsonl`
