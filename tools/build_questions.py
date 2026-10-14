"""Build data/question_bank/questions.jsonl and report passages no question uses.

Run from the repository folder: python3 -I tools/build_questions.py
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
Q = []

def q(qid, cls, route, question, gold, expected, check=""):
    Q.append({"id": qid, "question": question, "class": cls, "route": route,
              "gold_passages": gold, "expected": expected, "check": check})

R4 = "R4"
# --- Q2 Definition: retrieval over the manuals ------------------------------
q("q2-01", "Q2", R4, "What is consumption of fixed capital?",
  ["sna08-6.240", "una14-ch1-gross-net", "sna25-A4.10"],
  "The decline in the value of fixed assets through use in production. The 2025 SNA renames it depreciation.",
  "Names both terms and says which edition uses which.")
q("q2-02", "Q2", R4, "How do you get from GNI to net national income?",
  ["sna08-2.144", "sna25-3.145", "esa10-8.94", "una14-ch1-nni"],
  "Deduct consumption of fixed capital (2008 SNA); deduct depreciation and depletion (2025 SNA).",
  "Edition-sensitive: must state that the 2025 SNA also deducts depletion.")
q("q2-03", "Q2", R4, "Is depletion of natural resources a cost of production?",
  ["sna08-12.26", "sna25-A4.59", "sna25-3.142"],
  "Not in the 2008 SNA (other changes in volume of assets); yes in the 2025 SNA.",
  "Edition pair: an answer giving only one edition fails.")
q("q2-04", "Q2", R4, "What is the difference between GDP and GNI?",
  ["sna08-2.143", "sna25-3.144", "esa10-8.94", "bea-ch2-gnp"],
  "GNI adds income receivable from abroad and deducts income payable abroad; GDP is production, GNI income.",
  "If bea-ch2-gnp is used, say GNP is the US term.")
q("q2-05", "Q2", R4, "What is GDI?",
  ["sna08-15.188", "bea-ch2-ndp-gni"],
  "Two meanings. In the SNA, real GDI is GDP in volume plus the trading gain (purchasing power). In BEA usage, GDI is GDP measured from incomes.",
  "Same-letters clash: must give both, each with its source, or ask which is meant.")
q("q2-06", "Q2", R4, "What are the terms of trade?",
  ["sna08-15.187"],
  "The ratio of export prices to import prices.")
q("q2-07", "Q2", R4, "What is the trading gain and how is it measured?",
  ["sna08-15.188", "sna08-15.194", "sna08-15.187"],
  "The difference between real GDI and GDP in volume, arising from changes in the terms of trade; T = (X-M)/P - (X/Px - M/Pm).",
  "Formula is in the book text, not the quoted passage: the answer must not invent a different one.")
q("q2-08", "Q2", R4, "What is a purchasing power parity?",
  ["sna08-15.199", "ppp23-1.13", "una14-ch2-ppp"],
  "The number of units of one currency needed to buy in that country what one unit of another currency buys in its own.")
q("q2-09", "Q2", R4, "Why not compare GDP across countries with market exchange rates?",
  ["ppp23-1.14", "ppp23-1.17", "sna08-15.198", "sna08-15.224"],
  "Exchange rates reflect capital flows and speculation and ignore non-traded goods; they overstate high-price economies.")
q("q2-10", "Q2", R4, "What is a price level index?",
  ["sna08-15.225", "sna08-15.227"],
  "The ratio of a PPP to the exchange rate; shows whether a country is expensive relative to others.")
q("q2-11", "Q2", R4, "How precise are PPPs?",
  ["ppp23-1.31"],
  "Statistical estimates with error margins, not precise measures.")
q("q2-12", "Q2", R4, "How are PPPs for government services such as health and education calculated?",
  ["ppp23-4.16", "ppp23-8.2", "ppp23-8.4"],
  "From input prices, mainly pay, which assumes equal productivity; Eurostat and the OECD now use output methods for health and education.",
  "Scope: must say this is Eurostat-OECD practice; other ICP regions adjust for productivity.")
q("q2-13", "Q2", R4, "What is double deflation?",
  ["sna08-15.2", "sna25-18.2", "sna25-18.143"],
  "Real value added = output in volume minus intermediate consumption in volume, each deflated by its own prices.")
q("q2-14", "Q2", R4, "Do chain-linked volume measures add up to the total?",
  ["sna25-18.62", "sna08-15.58"],
  "No. Chained volumes are not additive; only Laspeyres volumes are additive.")
q("q2-15", "Q2", R4, "Should annual price and volume indices be chained?",
  ["sna08-15.44", "sna25-18.47"],
  "Yes, annually; not for seasonally unadjusted sub-annual data.",
  "The two passages are word for word the same: cite both editions or say the text is unchanged.")
q("q2-16", "Q2", R4, "What is the GDP deflator?",
  ["una14-ch1-deflator"],
  "The price index that separates GDP growth at current prices from GDP growth in volume; nominal divided by real.",
  "Should not equate it with a producer price index.")
q("q2-17", "Q2", R4, "Why are GDP estimates revised?",
  ["qna17-12.1", "qna17-12.2", "bea-ch1-revisions", "una14-ch1-revisions"],
  "Early estimates use incomplete data; later data and new methods replace them.",
  "Scope: BEA and Insee schedules are examples of national practice.")
q("q2-18", "Q2", R4, "What problems can revisions cause, and how should they be handled?",
  ["qna17-12.4", "qna17-10.48"],
  "They can confuse users; a planned revision policy and release calendar reduce this.")
q("q2-19", "Q2", R4, "What is seasonal adjustment?",
  ["qna17-7.2"],
  "Removing seasonal and calendar effects from a time series.")
q("q2-20", "Q2", R4, "Who counts in a country's population when calculating GDP per head?",
  ["esa10-11.05", "esa10-11.06", "sna25-5.11"],
  "Residents staying a year or more; holidaymakers and short-term visitors are excluded.")
q("q2-21", "Q2", R4, "Are remittances part of national income?",
  ["sna25-9.136", "sna25-19.52"],
  "Transfers from migrants abroad a year or more are current transfers, in disposable income, not NNI. Pay of border or seasonal workers abroad under a year is in GNI.")
q("q2-22", "Q2", R4, "What is modified GNI and why does Ireland publish it?",
  ["cso-gnistar-1", "cso-gnistar-2", "cso-gnistar-3", "cso-gnistar-4", "cso-gnistar-6"],
  "An Irish measure removing depreciation of foreign-owned IP and leased aircraft and the income of redomiciled PLCs.",
  "Scope: Irish national practice, not an international standard.")
q("q2-23", "Q2", R4, "Why can GDP mislead for economies with large multinational companies?",
  ["sna25-23.68", "cso-gnistar-2", "cso-gnistar-4"],
  "MNE profits and IP moves inflate GDP; GNI, NNI and household income are less affected.")
q("q2-24", "Q2", R4, "Is net domestic product a better measure than GDP?",
  ["sna25-3.142", "sna25-A4.10", "una14-ch1-nni", "sna25-3.145"],
  "Conceptually yes; the 2025 SNA prefers NDP growth alongside GDP. In 2014 OECD economists preferred gross measures for practical reasons.",
  "Sources disagree by date: answer must date each view.")
q("q2-25", "Q2", R4, "What is real gross domestic income, and how does it lead to real national income?",
  ["sna08-15.188", "sna08-15.194"],
  "Real GDI = GDP in volume plus trading gain; add real net primary income from abroad, deflated by domestic final expenditure prices.",
  "Must use the SNA meaning of GDI.")
q("q2-26", "Q2", R4, "Does double deflation stop service firms' price rises being counted as output growth?",
  ["sna25-18.2", "sna25-18.143", "sna25-18.145", "sna25-18.146"],
  "Probably to a significant extent, not known precisely: in principle yes, but service price indices are weak, errors are magnified, and many services are estimated from inputs.",
  "Judgement question. Options: definitely no / definitely yes / probably to a significant extent / we do not know. False certainty fails.")
q("q2-27", "Q2", R4, "At what levels can countries' economies be compared?",
  ["una14-ch3-levels"],
  "Growth rates, ratios and absolute levels: three different questions, the last needing PPPs.",
  "Access test: una14-ch3-levels is subscriber-only. A public user must not see it.")
q("q2-28", "Q2", R4, "What are the three ways of measuring GDP?",
  ["sna08-2.138", "sna08-2.139", "sna08-2.140"],
  "Production (value added plus taxes less subsidies on products), expenditure (final uses less imports) and income (primary incomes).")

# --- Q2 additions from the Krugman reading (13 Oct) ------------------------
q("q2-29", "Q2", R4, "What does nominal GNI divided by the consumer price index measure, and can it compare countries?",
  ["sna08-15.194", "ppp23-1.14", "sna08-15.199", "ppp23-1.17"],
  "The change over time in what national income can buy in consumer goods, in one country. A CPI is an index with no level, in its own currency and basket, so it supports growth comparisons only. For levels, divide nominal GNI by a PPP; for living standards, a consumption PPP fits better than a GDP PPP.",
  "Must separate comparing growth rates (possible) from comparing levels (needs PPPs).")
q("q2-30", "Q2", R4, "Why can real GDP growth and comparisons at PPP tell different stories about two economies?",
  ["sna08-15.188", "sna08-15.187", "sna25-18.62", "ppp23-1.31"],
  "Real GDP growth values output at the base year's prices; PPP levels use current prices. If one country specialises in goods whose prices fall fast (tech), its volume growth is high while its command over goods rises less: the trading-gain logic of real GDI.",
  "Should link to terms of trade and real GDI; Krugman (2026) is book text, not corpus.")

q("q2-31", "Q2", R4, "What is the best measure of labour input for comparing productivity?",
  ["sna25-16.71", "sna25-16.73"],
  "Total hours actually worked by employees and the self-employed. Often estimated from usual hours with adjustments, so less precise than headcounts.",
  "Should note that hours are estimated, which limits comparisons of levels across countries.")
q("q2-32", "Q2", R4, "Does output per hour worked allow for differences in workers' skills?",
  ["sna25-16.95"],
  "No: it treats every hour alike. A quality-adjusted labour input weights hours by type of worker.")

# --- Ambiguous: the question must be refined before it can be answered -------
q("amb-01", "AMB", "clarify", "Is the United States doing better than the euro area?",
  ["ppp23-1.17", "sna08-15.188"],
  "Not answerable as asked. Offer three questions: living standards (GNI per head at PPP, and per hour worked), growth (real GDP at base-year prices), productivity (real GDP per hour at PPP). Then answer the one chosen, with measurement caveats.",
  "Fails if it answers with one number without saying which question it answered.")
q("amb-02", "AMB", "clarify", "Is China catching up with the United States?",
  ["ppp23-1.31", "ppp23-1.17"],
  "Catching up in size (total GDP at PPP), income per head, or productivity? PPP levels for China carry wide error margins and have moved between ICP rounds.",
  "Must state PPP uncertainty for China.")
q("amb-03", "AMB", "clarify", "Is the UK falling behind?",
  [],
  "Behind whom, and on what: growth, living standards or productivity? Ask before answering.")

# --- Q6 Mixed: definition plus number --------------------------------------
q("q6-01", "Q6", "R4+R2", "What is the exchange-rate component, and how large was it for Japan in 2024?",
  ["ppp23-1.14", "sna08-15.198"], "Definition from the manuals plus the C1b value from the model.")
q("q6-02", "Q6", "R4+R2", "What is the PPP component, and how large was it for India in 2024?",
  ["sna08-15.199", "ppp23-1.17"], "Definition plus the C3 value.")
q("q6-03", "Q6", "R4+R2", "What is the gap between GDP and national income, and how large is it for the euro area?",
  ["sna08-2.143", "sna25-3.144", "sna25-23.68", "cso-gnistar-2"],
  "Definition plus the C1a value. Ireland's multinational profits sit inside the euro area total.",
  "Should mention that one member (Ireland) distorts the aggregate.")

# --- Data questions: answered by the model class, passages give context ------
q("q1-01", "Q1", "R2", "What was GNI per head at PPP in the United Kingdom in 2024?", ["sna08-15.199"], "A single value from the fact table, with unit and vintage.")
q("q1-02", "Q1", "R2", "What was the population of India in 2022?", ["esa10-11.05", "sna25-5.11"], "A single value with source and vintage.")
q("q3-01", "Q3", "R2", "What drove growth in real NNI per head in Japan last year?", [], "The five components and the check term.")
q("q3-02", "Q3", "R2", "How much of the United Kingdom's growth came from prices rather than volumes?", ["una14-ch1-deflator"], "C2 from the model.")
q("q4-01", "Q4", "R2", "How has the estimate of India's GNI per head for 2016 changed between data vintages?", ["qna17-12.1"], "Both vintages and the revision.")
q("q5-01", "Q5", "R2", "How does the euro area compare with the United States on GNI per head at PPP, and on GDP per hour worked?", ["ppp23-1.17", "una14-ch1-nni"],
  "Two ratios; the gap per head is larger than the gap per hour because Europeans work fewer hours.",
  "Needs hours-worked data; must say hours are less comparable across countries than GDP.")
q("q5-02", "Q5", "R2", "Has the United Kingdom fallen behind the United States since 2007?", ["sna08-15.188", "ppp23-1.31"],
  "Two runs: real GDP growth and the GNI-per-head-at-PPP ratio, which can differ.")
q("q7-01", "Q7", "R5>R2", "What if the yen had been 10% weaker against the dollar in 2024?", [], "Small model extracts the parameter; the class computes.")
q("q8-01", "Q8", "R6", "How does China now compare with the United States three years ago, and what explains the change?", ["ppp23-1.31"], "Agent loop within a step budget.")

# --- Out of scope: escalate ------------------------------------------------
q("out-01", "OUT", "escalate", "Is the euro area's growth sustainable?", [], "Escalate: a judgement for a person.")
q("out-02", "OUT", "escalate", "Should the Bank of England cut interest rates?", [], "Escalate: policy advice.")
q("out-03", "OUT", "escalate", "What will China's GDP be in 2030?", [], "Escalate: no forecasts in the data.")
q("out-04", "OUT", "escalate", "What is the best restaurant in Dublin?", [], "Decline: outside the corpus and the data.")

path = REPO / "data" / "question_bank" / "questions.jsonl"
path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in Q) + "\n", encoding="utf-8")

corpus = {json.loads(l)["id"] for l in (REPO / "data/corpus/passages.jsonl").read_text().splitlines()}
used = {g for x in Q for g in x["gold_passages"]}
missing = used - corpus
print("questions:", len(Q), "| unknown gold ids:", sorted(missing))
print("passages not used by any question:", sorted(corpus - used))
