"""Build the data for the demonstrator's "Method and caveats" page (A5, lesson L5).

Run from the repository folder:
    python tools/build_method_page.py
It writes app/data/method_and_caveats.json. Every number on the page is
counted here from the data, the saved runs and the NNI model, never typed by
hand, so the page cannot drift from the data (lesson L9; gate B3s). A test
(tests/test_method_page.py) rebuilds the file and fails if it differs.

The sentences are a draft for the vertical domain expert to approve
("status": "draft" until then). Change the wording here, not in the JSON.
"""

import collections
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from nni_model.contracts import NNI_EXCEPTIONS                      # noqa: E402
from nni_model.crosschecks import SIX, agreement_rates, load_inputs, output_level_gap  # noqa: E402
from nni_model.fingerprints import raw_files                         # noqa: E402

from ragbook.ch01_python_basics import load_passages                 # noqa: E402
from ragbook.ch11_prompts import load_answers                        # noqa: E402
from ragbook.ch13_model_tool import GAPS, MEASURES                   # noqa: E402
from ragbook.ch14_answer_checks import EXPLAIN_SETTINGS, NO_EXPLANATION, RERUN_FILE  # noqa: E402

DATA = REPO / "data"
OUT = REPO / "app" / "data" / "method_and_caveats.json"
NAMES = {"USA": "the United States", "EA21": "the euro area", "GBR": "the United Kingdom",
         "CHN": "China", "IND": "India", "JPN": "Japan", "IRL": "Ireland"}


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def counts():
    passages = load_passages(DATA / "corpus" / "passages.jsonl")
    with open(DATA / "question_bank" / "questions.jsonl", encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]
    rerun = load_answers(RERUN_FILE)
    bands = collections.Counter()
    for record in rerun:
        for line in record["locked"]["text"].splitlines():
            found = re.search(r"DQR (High|Medium|Low)", line)
            if found and line.startswith("- "):
                bands[found.group(1)] += 1
    status = collections.Counter(record["status"] for record in rerun)
    shown = [r for r in rerun if r["status"] in ("passed", "passed on retry")]
    fixed = sum(r["attempts"][-1]["reply"].strip() == NO_EXPLANATION for r in shown)
    gaps = [abs(output_level_gap(load_inputs(), e)) for e in SIX]
    judged = collections.Counter(row["judgement"] for row in read_csv(DATA / "answers" / "a5_judgements.csv")
                                 if row["id"] in {r["id"] for r in shown})
    proxies = [m for m in MEASURES.values() if "proxy" in m]
    return {
        "passages": len(passages),
        "sources": len({p["source_code"] for p in passages}),
        "passages_by_licence": dict(sorted(collections.Counter(p["licence_class"] for p in passages).items())),
        "questions": len(questions),
        "questions_by_route": dict(collections.Counter(q["route"] for q in questions).most_common()),
        "measures": len(MEASURES) + len(GAPS),
        "measures_exact": len(MEASURES) - len(proxies),
        "measures_proxy": len(proxies),
        "measures_no_figure": len(GAPS),
        "figures_by_band": {band: bands[band] for band in ("High", "Medium", "Low")},
        "explanations": {"questions": len(rerun), "lookup": status["lookup"],
                         "shown_with_content": len(shown) - fixed, "judged_good": judged["good"],
                         "judged_fault": judged["fault"], "shown_fixed_sentence": fixed,
                         "dropped": status["dropped"]},
        "level_gaps_percent": [round(g, 1) for g in sorted(gaps)],
        "raw_files_fingerprinted": len(raw_files()),
        "series_links": len(read_csv(DATA / "series" / "series_links.csv")),
        "agreement": [{"check": c, "agree": a, "total": n} for c, a, n in agreement_rates()],
    }


def last_years():
    by = collections.defaultdict(dict)
    for row in read_csv(DATA / "series" / "last_year.csv"):
        if row["last_year"] and row["economy"] in NAMES and row["economy"] != "IRL":
            by[row["edition"]][row["economy"]] = int(row["last_year"])
    return by


def caveats(c):
    latest = last_years()["latest"]
    groups = collections.defaultdict(list)
    for economy, year in latest.items():
        groups[year].append(NAMES[economy])
    edge = "; ".join(f"{', '.join(sorted(names))} {year}" for year, names in sorted(groups.items()))
    uk_last = max(NNI_EXCEPTIONS["GBR"][0])
    links = read_csv(DATA / "series" / "series_links.csv")
    benchmarks = sorted({(r["edition"], r["ppp_benchmark"]) for r in links if r["ppp_benchmark"]})
    benchmark_text = " and ".join(f"{b} in {e.replace('WDI ', 'the ').replace('archive 202403', 'March 2024 edition').replace('latest', 'latest edition')}"
                                  for e, b in benchmarks)
    level = next(a for a in c["agreement"] if a["check"].startswith("level"))
    growth = next(a for a in c["agreement"] if a["check"].startswith("growth, within"))
    e = c["explanations"]
    other_gaps = [g for g in c["level_gaps_percent"] if g >= 0.99]
    return [
        {"title": "The last year differs by economy",
         "text": f"In the latest edition the data end in different years: {edge}. "
                 "\"Last year\" in a question means the last year for that economy."},
        {"title": "Net national income after the last published year is a nowcast",
         "text": "WDI publishes adjusted net national income to 2021 (the United Kingdom to "
                 f"{uk_last}). Later years hold the last published ratio of net to gross national "
                 "income and are flagged \"nowcast\", rated at most Medium."},
        {"title": "The two editions use different PPP benchmarks",
         "text": f"Purchasing power parities rest on {benchmark_text}. A change between editions "
                 "in a figure at PPP includes the change of benchmark."},
        {"title": "First releases cannot be identified",
         "text": "WDI republishes producers' figures, so comparing two WDI editions does not tell us "
                 "which values are first releases. We can only mark a value as provisional if we know "
                 "the producer's own release dates."},
        {"title": "Sources disagree more on levels than editions do",
         "text": f"Real GDP in 2021 from WDI and from the Penn World Table agree within a typical "
                 f"revision for {level['agree']} of {level['total']} economies; the others differ by "
                 f"{min(other_gaps)} to {max(other_gaps)} per cent. Growth rates agree "
                 f"within a typical revision in {growth['agree']} of {growth['total']} economy-years."},
        {"title": "Some measures have only a stand-in or no figure",
         "text": f"Of {c['measures']} measures, {c['measures_exact']} have an exact figure, "
                 f"{c['measures_proxy']} a stand-in (proxy, rated at most Low) and "
                 f"{c['measures_no_figure']} no figure. Questions that need a stand-in or a missing figure "
                 "are passed to an analyst."},
        {"title": "Explanations come from a small language model and are often dropped",
         "text": f"Of the {e['questions']} questions answered with figures from code, {e['lookup']} are lookups "
                 f"and get no explanation. Of the rest, {e['shown_with_content']} showed an explanation with "
                 f"content (the vertical domain expert judged {e['judged_good']} good and {e['judged_fault']} a fault), "
                 f"{e['shown_fixed_sentence']} showed only the sentence \"{NO_EXPLANATION}\", and "
                 f"{e['dropped']} were dropped because the explanation failed the checks twice. "
                 f"The explanations were written on a laptop by qwen3:4b-instruct "
                 f"(context {EXPLAIN_SETTINGS['num_ctx']:,} tokens, temperature {EXPLAIN_SETTINGS['temperature']})."},
    ]


def build():
    c = counts()
    return {"title": "Method and caveats", "status": "draft", "counts": c, "caveats": caveats(c)}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}")
