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
  ["esa10-3.139", "sna25-A4.10"],
  "The decline in the value of fixed assets through use in production. The 2025 SNA renames it depreciation.",
  "Names both terms and says which edition uses which.")
q("q2-02", "Q2", R4, "How do you get from GNI to net national income?",
  ["sna08-2.144", "sna25-3.145", "esa10-8.94"],
  "Deduct consumption of fixed capital (2008 SNA); deduct depreciation and depletion (2025 SNA).",
  "Edition-sensitive: must state that the 2025 SNA also deducts depletion.")
q("q2-03", "Q2", R4, "Is depletion of natural resources a cost of production?",
  ["sna08-12.26", "sna25-A4.59"],
  "Not in the 2008 SNA (other changes in volume of assets); yes in the 2025 SNA.",
  "Edition pair: an answer giving only one edition fails.")
q("q2-04", "Q2", R4, "What is the difference between GDP and GNI?",
  ["esa10-8.94", "bea-ch2-gnp"],
  "GNI adds income receivable from abroad and deducts income payable abroad; GDP is production, GNI income.",
  "If bea-ch2-gnp is used, say GNP is the US term.")
q("q2-05", "Q2", R4, "What is GDI?",
  ["esa10-10.47", "bea-ch2-ndp-gni"],
  "Two meanings. In the SNA, real GDI is GDP in volume plus the trading gain (purchasing power). In BEA usage, GDI is GDP measured from incomes.",
  "Same-letters clash: must give both, each with its source, or ask which is meant.")
q("q2-06", "Q2", R4, "What are the terms of trade?",
  ["sna08-15.187", "esa10-10.47"],
  "The ratio of export prices to import prices. When they improve, fewer exports pay for the same imports.")
q("q2-07", "Q2", R4, "What is the trading gain and how is it measured?",
  ["esa10-10.47", "sna08-15.187"],
  "The difference between real gross domestic income and GDP in volume, arising from changes in the terms of trade. The trade balance is deflated by a general price index chosen by the statistics office, often the average of export and import prices.",
  "The formula is in the book text, not the quoted passage: the answer must not invent one.")
q("q2-08", "Q2", R4, "What is a purchasing power parity?",
  ["ppp23-1.13", "una14-ch2-ppp"],
  "The number of units of one currency needed to buy in that country what one unit of another currency buys in its own.")
q("q2-09", "Q2", R4, "Why not compare GDP across countries with market exchange rates?",
  ["ppp23-1.14", "ppp23-1.17"],
  "Exchange rates reflect capital flows and speculation and ignore non-traded goods; they overstate high-price economies.")
q("q2-10", "Q2", R4, "What is a price level index?",
  ["ppp23-ov.13"],
  "The ratio of a PPP to the exchange rate; shows whether a country is expensive relative to others.")
q("q2-11", "Q2", R4, "How precise are PPPs?",
  ["ppp23-1.31"],
  "Statistical estimates with error margins, not precise measures.")
q("q2-12", "Q2", R4, "How are PPPs for government services such as health and education calculated?",
  ["ppp23-4.16", "ppp23-8.2", "ppp23-8.4"],
  "From input prices, mainly pay, which assumes equal productivity; Eurostat and the OECD now use output methods for health and education.",
  "Scope: must say this is Eurostat-OECD practice; other ICP regions adjust for productivity.")
q("q2-13", "Q2", R4, "What is double deflation?",
  ["esa10-10.32"],
  "Real value added = output in volume minus intermediate consumption in volume, each deflated by its own prices.")
q("q2-14", "Q2", R4, "Do chain-linked volume measures add up to the total?",
  ["esa10-10.22", "bea-ch4-chained"],
  "No. Chain-linked volumes are not additive, so components do not sum to the total and shares are inaccurate.",
  "BEA passage is US practice (chained dollars); the point holds for chain-linked volumes everywhere.")
q("q2-15", "Q2", R4, "Should annual price and volume indices be chained?",
  ["esa10-10.20", "bea-ch4-fisher", "esa10-10.22"],
  "Yes. Volumes are measured at the previous year's prices and the annual links are chained. ESA 2010 uses Laspeyres volume and Paasche price indices; BEA uses Fisher indices. The cost: chained volumes are not additive, so they cannot be used to balance supply and use tables (ESA 2010).",
  "Should say the index formula differs between the EU and the US but both chain annually.")
q("q2-16", "Q2", R4, "What is the GDP deflator?",
  ["una14-ch1-deflator"],
  "The price index that separates GDP growth at current prices from GDP growth in volume; nominal divided by real.",
  "Should not equate it with a producer price index.")
q("q2-17", "Q2", R4, "Why are GDP estimates revised?",
  ["qna17-12.1", "qna17-12.2", "bea-ch1-revisions", "qna17-10.48"],
  "Early estimates use incomplete data; later data and new methods replace them.",
  "Scope: the BEA schedule is an example of national practice.")
q("q2-18", "Q2", R4, "What problems can revisions cause, and how should they be handled?",
  ["qna17-12.4", "qna17-10.48"],
  "They can confuse users; a planned revision policy and release calendar reduce this.")
q("q2-19", "Q2", R4, "What is seasonal adjustment?",
  ["qna17-7.2"],
  "Removing seasonal and calendar effects from a time series.")
q("q2-20", "Q2", R4, "Who counts in a country's population when calculating GDP per head?",
  ["esa10-11.05", "esa10-11.06"],
  "Persons permanently settled in the economic territory, national or foreign, even if temporarily absent; an annual average of head counts.")
q("q2-21", "Q2", R4, "Are remittances part of national income?",
  ["esa10-4.129", "esa10-2.10", "esa10-18.53"],
  "Transfers from migrants abroad a year or more are current transfers between households, in disposable income, not NNI. Border and seasonal workers abroad under a year stay resident at home; their pay is compensation of employees, in GNI.")
q("q2-22", "Q2", R4, "What is modified GNI and why does Ireland publish it?",
  ["cso-gnistar-1", "cso-gnistar-2", "cso-gnistar-3", "cso-gnistar-4", "cso-gnistar-6"],
  "An Irish measure removing depreciation of foreign-owned IP and leased aircraft and the income of redomiciled PLCs.",
  "Scope: Irish national practice, not an international standard.")
q("q2-23", "Q2", R4, "Why can GDP mislead for economies with large multinational companies?",
  ["sna25-23.68", "cso-gnistar-2", "cso-gnistar-4"],
  "MNE profits and IP moves inflate GDP; GNI, NNI and household income are less affected.")
q("q2-24", "Q2", R4, "Is net domestic product a better measure than GDP?",
  ["sna25-A4.10", "sna25-3.145", "bea-ch2-ndp-gni"],
  "Conceptually yes. Setting aside how hard depreciation is to measure, NDP is the better measure of the output an economy generates sustainably. It deducts consumption of fixed capital (wear, tear and obsolescence) and, in the 2025 SNA, depletion of natural resources, so it counts only what is available for consumption or for adding to wealth. GDP measures total production before those deductions. The 2025 SNA names NDP growth the preferred measure of growth, used alongside GDP, not replacing it. In US practice (BEA), NDP is GDP minus consumption of fixed capital.",
  "Must say NDP complements GDP rather than replaces it.")
q("q2-25", "Q2", R4, "What is real gross domestic income, and how does it lead to real national income?",
  ["esa10-10.47"],
  "Real gross domestic income is GDP in volume plus the trading gain from changes in the terms of trade. Adding real primary income from abroad, net, gives real national income.",
  "Must use the SNA/ESA meaning of real GDI, not BEA's GDI.")
q("q2-26", "Q2", R4, "Does double deflation stop service firms' price rises being counted as output growth?",
  ["esa10-10.32", "esa10-10.33"],
  "Probably to a significant extent, not known precisely: in principle yes, but service price indices are weak, errors are magnified, and many services are estimated from inputs.",
  "Judgement question. Options: definitely no / definitely yes / probably to a significant extent / we do not know. False certainty fails.")
q("q2-27", "Q2", R4, "At what levels can countries' economies be compared?",
  ["ppp23-ov.12"],
  "Levels across countries need PPPs: volume indices compare the size of economies; per capita volume indices compare material well-being. Growth needs each country's own volume series.")
q("q2-28", "Q2", R4, "What are the three ways of measuring GDP?",
  ["esa10-8.89"],
  "Production (value added plus taxes less subsidies on products), expenditure (final uses plus exports less imports) and income (compensation of employees, taxes less subsidies on production and imports, operating surplus and mixed income).")

# --- Q2 additions from the Krugman reading (13 Oct) ------------------------
q("q2-29", "Q2", R4, "What does nominal GNI divided by the consumer price index measure, and can it compare countries?",
  ["ppp23-1.14", "ppp23-1.17", "ppp23-ov.12"],
  "The change over time in what national income can buy in consumer goods, in one country. A CPI is an index with no level, in its own currency and basket, so it supports growth comparisons only. For levels, divide nominal GNI by a PPP; for living standards, a consumption PPP fits better than a GDP PPP.",
  "Must separate comparing growth rates (possible) from comparing levels (needs PPPs).")
q("q2-30", "Q2", R4, "Why can real GDP growth and comparisons at PPP tell different stories about two economies?",
  # The two wb13-mccarthy passages were added 24 Oct with the corpus batch:
  # they answer this question directly (decision: Lavan, 24 Oct).
  ["esa10-10.47", "sna08-15.187", "esa10-10.22", "ppp23-1.31", "wb13-mccarthy-space-time", "wb13-mccarthy-ipd"],
  "Real GDP growth values output at the base year's prices; PPP levels use current prices. Between benchmark years, PPPs are extrapolated with GDP deflators, and comparisons across countries and across time cannot both be kept consistent. If one country specialises in goods whose prices fall fast (tech), its volume growth is high while its command over goods rises less: the trading-gain logic of real GDI.",
  "Should link to terms of trade and real GDI; Krugman (2026) is book text, not corpus.")

q("q2-31", "Q2", R4, "What is the best measure of labour input for comparing productivity?",
  ["esa10-11.27", "sna25-16.95"],
  "Total hours actually worked by employees and the self-employed, not a head count. Hours worked still treat every hour as equal in quality, whatever the worker's skills (2025 SNA).",
  "Should note that hours are estimated, which limits comparisons of levels across countries.")
q("q2-32", "Q2", R4, "Does output per hour worked allow for differences in workers' skills?",
  ["sna25-16.95"],
  "No: it treats every hour alike. A quality-adjusted labour input weights hours by type of worker.")

# --- Ambiguous: the question must be refined before it can be answered -------
q("amb-01", "AMB", "clarify", "Is the United States doing better than the euro area?",
  ["ppp23-1.17", "esa10-10.47"],
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
q("q6-01", "Q6", "R4+R2", "What is the deflator mix, and how large was it for Japan in 2024?",
  ["esa10-10.47", "sna08-15.187"],
  "Definition plus the C2 value: growth of the GDP deflator minus growth of the household consumption deflator, in log points.",
  "Should link it to the terms of trade without calling it the trading gain.")
q("q6-02", "Q6", "R4+R2", "What is output per hour worked, and how did it change for India in 2023?",
  ["esa10-11.27", "sna25-16.95"],
  "Definition plus the C4a value. The DQR is Low: India's hours rest on weak underlying data, and its employment source changed in 2019.",
  "Must report the Low DQR and its reason.")
q("q6-03", "Q6", "R4+R2", "What is the gap between GDP and national income, and how large is it for the euro area?",
  ["esa10-8.94", "sna25-23.68", "cso-gnistar-2"],
  "Definition plus the C1a value. Ireland's multinational profits sit inside the euro area total.",
  "Should mention that one member (Ireland) distorts the aggregate.")

# --- Data questions: answered by the model class, passages give context ------
q("q1-01", "Q1", "R2", "What was GNI per head at PPP in the United Kingdom in 2024?", ["ppp23-ov.12"], "A single value from the fact table, with unit and vintage.")
q("q1-02", "Q1", "R2", "What was the population of India in 2022?", ["esa10-11.05"], "A single value with source and vintage.")
q("q3-01", "Q3", "R2", "What drove growth in real NNI per head in Japan last year?", [], "The five components and the check term.")
q("q3-02", "Q3", "R2", "How much of the United Kingdom's growth came from prices rather than volumes?", ["una14-ch1-deflator"], "Growth of the GDP deflator against growth of real GDP, from the model: nominal GDP growth is their sum, in log points.")
q("q4-01", "Q4", "R2", "How has the estimate of India's GNI per head for 2016 changed between data vintages?", ["qna17-12.1"], "Both vintages and the revision.")
q("q5-01", "Q5", "R2", "How does the euro area compare with the United States on GNI per head at PPP, and on GDP per hour worked?", ["ppp23-1.17", "esa10-11.27"],
  "Two ratios; the gap per head is larger than the gap per hour because Europeans work fewer hours.",
  "Needs hours-worked data; must say hours are less comparable across countries than GDP.")
q("q5-02", "Q5", "R2", "Has the United Kingdom fallen behind the United States since 2007?", ["esa10-10.47", "ppp23-1.31"],
  "Two runs: real GDP growth and the GNI-per-head-at-PPP ratio, which can differ.")
q("q5-03", "Q5", "R4+R2", "Does the gap in real GDP growth between the United States and the euro area depend on how public services are measured?",
  ["ons-psp-1", "ons-psp-2"],
  "Partly, and by an unknown amount. Public services are about a fifth of the UK economy; collectively provided services such as defence are measured by what they cost, so no productivity growth is recorded. Economies with different shares or methods can show different growth for the same real change.",
  "States the caveat qualitatively, gives no size for the effect, and presents the ONS figures as UK practice, not as the US or euro area.")
# Added 24 Oct with the corpus batch. Outside Q2, so the 32 definition
# questions that Chapters 3-7 measure are unchanged.
q("q4-02", "Q4", "R4+R2", "Why did China's and India's GDP per head at PPP fall when new ICP results came out?",
  ["wb13-deaton-revision", "wb13-deaton-benchmark", "wb13-deaton-updating"],
  "Earlier PPPs for many poorer countries were extrapolated from old benchmarks or guessed; the 2005 ICP measured their prices directly. China's PPP rose by a factor of 1.65 and India's by 1.55, so their GDP per head in international dollars fell, although their economies did not change. Rich countries that compute PPPs every year saw little revision.",
  "Says the change is relative to the United States, not a fall in output, and names the benchmark year.")
q("q5-04", "Q5", "R4+R2", "Why does a country's growth measured at PPP differ from its official real growth?",
  ["wb13-mccarthy-space-time", "wb13-mccarthy-ipd"],
  "Between benchmark years, PPPs are extrapolated with each country's GDP deflator relative to the United States. PPPs compare countries at one time; national accounts compare one country over time. Both cannot be kept consistent at once, and the gap grows when economic structures differ or change fast, as for the United States and China.",
  "Names extrapolation from the benchmark year and the conflict between comparisons across space and across time.")
q("q5-05", "Q5", "R4+R2", "Can different price measurement make US and euro area real growth hard to compare?",
  ["bea-ch4-quality"],
  "Yes. Price indexes that hold quality constant, such as hedonic indexes, show lower inflation and so higher real growth for products whose quality improves fast, such as computers. Where and how much hedonic methods are used differs between countries.",
  "Presents the BEA passage as US practice and gives no size for the effect.")
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
