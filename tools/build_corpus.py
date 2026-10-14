"""Build data/corpus/passages.jsonl from passages copied from the source PDFs, and verify each sentence.

Run from the repository folder after tools/extract_text.sh:
    python3 -I tools/build_corpus.py
It writes the corpus only if every sentence of every passage is found in the
text of its source PDF. Add a passage with add(...) below, then rerun.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Text extracted from the source PDFs by tools/extract_text.sh (not committed).
SCRATCH = REPO / "data" / "raw" / "text"

SOURCE_FILES = {
    "SNA08": "SNA2008.txt",
    "QNA17": "QNAManual2017text.txt",
    "UNA14": "9789264214637-en.txt",
    "ESA10": "KS-02-13-269-EN.PDF.txt",
    "BEA": "all-chapters.txt",
    "CSO": "Modified GNI - CSO - Central Statistics Office.txt",
    "PPP23": "KS-GQ-24-011-EN-N.txt",
    "SNA25": "sna25.txt",
}

SOURCE_NAMES = {
    "SNA08": ("System of National Accounts 2008", "2008 SNA (2009)", "All rights reserved (EC, IMF, OECD, UN, World Bank); short quotation with full citation"),
    "QNA17": ("IMF, Quarterly National Accounts Manual", "2017 edition", "IMF fair use: non-commercial teaching and research, with citation"),
    "UNA14": ("OECD, Understanding National Accounts", "Second edition (2014)", "OECD 2014 rights notice: excerpts allowed in own documents and teaching materials with acknowledgement; public or commercial use by request to rights@oecd.org"),
    "ESA10": ("Eurostat, European System of Accounts (ESA 2010)", "2013", "Reproduction authorised, source acknowledged (European Union, 2013)"),
    "BEA": ("US Bureau of Economic Analysis, NIPA Handbook", "December 2024", "Public domain (BEA), credit to BEA requested"),
    "CSO": ("Central Statistics Office Ireland, Modified GNI", "Web page, read 12 October 2026", "CC BY 4.0"),
    "PPP23": ("Eurostat and OECD, Methodological Manual on Purchasing Power Parities", "2023 edition (2024)", "CC BY 4.0 (European Union/OECD 2024): credit given, changes indicated"),
    "SNA25": ("System of National Accounts 2025", "2025 SNA, pre-edit version (2025)", "All rights reserved (EC, IMF, OECD, UN, World Bank); short quotation with full citation"),
}

# (id, source code, reference, topic, components, partial, text)
P = []


def add(pid, code, reference, topic, components, text, partial=False, access="public"):
    P.append(dict(pid=pid, code=code, reference=reference, topic=topic,
                  components=components, text=text, partial=partial, access=access))


# --- SNA 2008 -------------------------------------------------------------
add("sna08-2.138", "SNA08", "para. 2.138", "GDP definition", ["C4"],
    "2.138 Basically, GDP derives from the concept of value added. Gross value added is the difference between output and intermediate consumption. GDP is the sum of gross value added of all resident producer units plus that part (possibly the total) of taxes on products, less subsidies on products, that is not included in the valuation of output.")
add("sna08-2.139", "SNA08", "para. 2.139", "GDP definition", ["C4"],
    "2.139 Next, GDP is also equal to the sum of the final uses of goods and services (all uses except intermediate consumption) measured at purchasers’ prices, less the value of imports of goods and services.")
add("sna08-2.140", "SNA08", "para. 2.140", "GDP definition", ["C4"],
    "2.140 Finally, GDP is also equal to the sum of primary incomes distributed by resident producer units.")
add("sna08-2.143", "SNA08", "para. 2.143", "Gross national income", ["C1a"],
    "2.143 Primary incomes generated in the production activity of resident producer units are distributed mostly to other resident institutional units; however, part of them may go to non-resident units. Symmetrically, some primary incomes generated in the rest of the world may come from resident units. This leads to the definition and measurement of gross national income (GNI). GNI is equal to GDP less primary incomes payable to non-resident units plus primary incomes receivable from non-resident units. In other words, GNI is equal to GDP less taxes (less subsidies) on production and imports, compensation of employees and property income payable to the rest of the world plus the corresponding items receivable from the rest of the world. Thus GNI is the sum of gross primary incomes receivable by resident institutional units or sectors. In contrast to GDP, GNI is not a concept of value added, but a concept of income.")
add("sna08-2.144", "SNA08", "para. 2.144", "Net national income", ["C1a"],
    "2.144 By deducting the consumption of fixed capital from GNI, net national income (NNI) is obtained. The remarks above about the conceptual relevance of the net concept in case of product apply even more strongly to national income.")
add("sna08-6.240", "SNA08", "para. 6.240", "Consumption of fixed capital", ["C1a"],
    "6.240 Consumption of fixed capital is the decline, during the course of the accounting period, in the current value of the stock of fixed assets owned and used by a producer as a result of physical deterioration, normal obsolescence or normal accidental damage. The term depreciation is often used in place of consumption of fixed capital but it is avoided in the SNA because in commercial accounting the term depreciation is often used in the context of writing off historic costs whereas in the SNA consumption of fixed capital is dependent on the current value of the asset.")
add("sna08-12.26", "SNA08", "para. 12.26", "Depletion of natural resources", ["C1a"],
    "12.26 The depletion of natural resources covers the reduction in the value of deposits of subsoil assets as a result of the physical removal and using up of the assets.")
add("sna08-15.44", "SNA08", "para. 15.44", "Price and volume measures", ["C2"],
    "15.44 On balance, situations favourable to the use of chain Laspeyres and Paasche indices over time seem more likely than those that are unfavourable. The underlying economic forces that are responsible for the observed long-term changes in relative prices and quantities, such as technological progress and increasing incomes, do not often go into reverse. Hence, it is generally recommended that annual indices be chained. The price and volume components of monthly and quarterly data are usually subject to much greater variation than their annual counterparts due to seasonality and short-term irregularities. Therefore, the advantages of chaining at these higher frequencies are less and chaining should definitely not be applied to seasonal data that are not adjusted for seasonal fluctuations.")
add("sna08-15.188", "SNA08", "para. 15.188 (first part)", "Real income and the terms of trade", ["C2"],
    "15.188 Real gross domestic income (real GDI) measures the purchasing power of the total incomes generated by domestic production. It is a concept that exists in real terms only. When the terms of trade change there may be a significant divergence between the movements of GDP in volume terms and real GDI. The difference between the change in GDP in volume terms and real GDI is generally described as the “trading gain” (or loss) or, to turn this round, the trading gain or loss from changes in the terms of trade is the difference between real GDI and GDP in volume terms. The differences between movements in GDP in volume terms and real GDI are not always small. If imports and exports are large relative to GDP and if the commodity composition of the goods and services that make up imports and exports is very different, the scope for potential trading gains and losses may be large. This may happen, for example, when the exports of a country consist mainly of a small number of primary products, such as cocoa, sugar or oil, while its imports consist mainly of manufactured products.",
    partial=True)
add("sna08-15.194", "SNA08", "para. 15.194", "Real income and the terms of trade", ["C2", "C1a"],
    "15.194 The transition from (a) to (b) is the trading gain from changes in the terms of trade explained immediately above. The steps needed in order to move from (b) to (d) above involve the deflation of flows between resident and nonresident institutional units, namely, primary incomes and current transfers receivable from abroad and payable to abroad. There may be no automatic choice of price deflator, but it is recommended that the purchasing power of these flows should be expressed in terms of a broadly based numeraire, specifically the set of goods and services that make up gross domestic final expenditure. This price index should, of course, be defined consistently with the volume and price indices for GDP.")
add("sna08-15.198", "SNA08", "para. 15.198", "Exchange rates versus PPPs", ["C3", "C1b"],
    "15.198 Users want to compare GDP and its components not only over time for a given country or countries in analyzing economic growth, for example, but also across countries for a given time period in analyzing relative economic size. A commonly used method of making such comparisons is to adjust national accounts values to a common currency using exchange rates, which has the advantage that the data are readily available and completely up to date. This is adequate if users need a ranking of a country’s relative spending power on the world market. However, it is not adequate for comparisons of productivity and standards of living because it does not adjust for the differences in price levels between countries and thus does not give a measure of countries’ relative sizes in the volume of goods and services they produce.")
add("sna08-15.199", "SNA08", "para. 15.199", "Purchasing power parities", ["C3"],
    "15.199 Purchasing power parities (PPPs) are used in producing a reliable set of estimates of the levels of activity between countries, expressed in a common currency. A purchasing power parity (PPP) is defined as the number of units of B’s currency that are needed in B to purchase the same quantity of individual good or service as one unit of A’s currency will purchase in A. Typically, a PPP for a country is expressed in terms of the currency of a base country, with the US dollar commonly being used. PPPs are thus weighted averages of the relative prices, quoted in national currency, of comparable items between countries. Used as deflators, they enable cross-country comparisons of GDP and its expenditure components.")
add("sna08-15.224", "SNA08", "para. 15.224", "Purchasing power parities", ["C3"],
    "15.224 One of most important uses of PPPs is to calculate comparable estimates of GDP and its major components, expressed in a common currency where the effects of differences in price levels between countries are removed. The national accounts are integral to PPP estimates in two ways. In the first place, the national accounts provide the weights that are used to aggregate prices from a detailed level to broader aggregates, up to GDP itself. Secondly, the national accounts provide the values that are “deflated” by the PPPs to provide the volumes (also referred to as “real expenditures”) expressed in a common currency that enable GDP and its expenditure components to be compared between countries.")
add("sna08-15.225", "SNA08", "para. 15.225", "Price level indices", ["C3", "C1b"],
    "15.225 The PPP exercise also produces comparative price level indices (PLI). A PLI is the ratio of the PPP for a country relative to the official exchange rate, both measured with respect to a reference currency. PLIs are generally expressed on a base of 100, with the base being either a single reference country or a regional average.")
add("sna08-15.227", "SNA08", "para. 15.227", "Price level indices", ["C3", "C1b"],
    "15.227 In practice, PPPs do not change rapidly over time and so a large change in a country’s PLI is usually due to a large change in exchange rates.")

# --- IMF QNA 2017 ---------------------------------------------------------
add("qna17-12.1", "QNA17", "para. 12.1", "Revisions and vintages", ["quality"],
    "12.1 Revisions are an essential part of good QNA compilation practice. Revisions are necessary to incorporate improvements in source data, methods, international standards, and classifications that are continuously made available. They provide users with data that are as timely and accurate as possible. Resource constraints, in combination with user needs, cause tension between the timeliness of published data on the one hand and reliability, accuracy, and comprehensiveness on the other hand. To reduce this tension, typically, preliminary data are compiled on a timely basis; later, revised estimates are produced when more and better source data become available. Good management of the process of revisions requires the existence of a well-established and transparent revision policy.")
add("qna17-12.2", "QNA17", "para. 12.2", "Revisions and vintages", ["quality"],
    "12.2 It is important to emphasize that revisions are conducted for the benefit of users: namely, to provide users with data that are as timely and accurate as possible. Revisions provide the possibility to incorporate new and more accurate information, and thus to improve the accuracy of the estimates, without introducing breaks in the time series. Although repeated revisions may be perceived as reflecting negatively on the trustworthiness of official statistics, delaying the incorporation of new data in the published estimates may increase the magnitude of later revisions (in particular, if these go in the same direction). Furthermore, not passing on known revisions reduces the actual trustworthiness of data even more, because the data do not reflect the best available information, and the public may know this or find this out (for instance, the public may wonder why a revision in the monthly production index is not reflected in the QNA).")
add("qna17-12.4", "QNA17", "para. 12.4", "Revisions and vintages", ["quality"],
    "12.4 Revisions to past data are not without potential problems and may draw criticism if not properly handled. Revisions to past data are inconvenient to users because they entail revisions to their databases and applications. More important, frequent revisions—particularly to data for the most recent periods—may cause users to feel uncertain about the current economic situation and thus uncertain about what policy actions should be taken. Some of this uncertainty may be unavoidable and merely reveal the fact that the information base for the estimates for the most recent periods is limited and thus that the data should be used with care. Some of the uncertainty, however, may be caused unnecessarily by the way the revisions are carried out or presented. On the other hand, unjustified differences between national accounts estimates and their source data may cause users to doubt the competence of the national accounts compilers with serious—and justified—criticism of the national accounts data as a result.")
add("qna17-10.48", "QNA17", "para. 10.48", "Revisions and vintages", ["quality"],
    "10.48 Given the provisional status of early estimates, it is necessary to develop a revision policy that fully integrates their dissemination into the broad system of ANA and QNA estimates. Revisions to early estimates are essential to incorporate new and updated source data made available after their release. Early estimates that are never revised may draw criticisms and dubious over the quality of the entire national accounts system. To avoid reputational and credibility risks, revisions to early estimates due to new or updated information should be published at the subsequent publication of the QNA. Revisions to early estimates should also follow a fixed and predetermined calendar, so that users are informed in advance about the timing of possible changes in the GDP estimates.")
add("qna17-7.2", "QNA17", "para. 7.2", "Seasonal adjustment", ["quality"],
    "7.2 Seasonal adjustment is the process of removing seasonal and calendar effects from a time series. This process is performed by means of analytical techniques that break down the series into components with different dynamic features. These components are unobserved and have to be identified from the observed data based on a priori assumptions on their expected behavior. In a broad sense, seasonal adjustment comprises the removal of both within-a-year seasonal movements and the influence of calendar effects (such as the different number of working days or moving holidays). By removing the repeated impact of these effects, seasonally adjusted data highlight the underlying long-term trend and short-run innovations in the series.")

# --- OECD Understanding National Accounts ---------------------------------
add("una14-ch1-nni", "UNA14", "Chapter 1, pp. 21–22", "Net national income", ["C1a"],
    "In order to arrive at a genuine measurement of the new wealth created during the period, a deduction has to be made for the cost of using up capital (such as the “wear and tear” on machinery). This is known as consumption of fixed capital. When this consumption is deducted, the result is net value added, and NDP is the sum of these net values added: NDP = Σ Net Values Added. Although less widely used than GDP, NDP is, in theory, a better measure of the wealth produced since it deducts the cost of wearing out the machinery and other capital assets used in production. For similar reasons, in theory, Net National Income is a better measure than GNI of the income created because Net National Income deducts the cost of using up capital assets. However, OECD economists tend to prefer GDP or GNI (over NDP and NNI) for two reasons. First, methods for calculating consumption of fixed capital are complex and tend to differ between countries, thus creating doubts about the comparability of results. Second, when ranking countries or analysing growth, the differences between GDP and NDP are small and do not change the conclusions.")
add("una14-ch1-gross-net", "UNA14", "Chapter 1, p. 31", "Consumption of fixed capital", ["C1a"],
    "The operating surplus is described as “gross” when no deduction is made for the cost of the depreciation of capital, known as “consumption of fixed capital” in the national accounts. It is in fact preferable to analyse this surplus in “net” terms, in other words, after deducting consumption of fixed capital, as we shall see in Chapter 7.")
add("una14-ch1-revisions", "UNA14", "Chapter 1, pp. 38–39", "Revisions and vintages", ["quality"],
    "These “provisional” figures are subsequently revised when Insee has at its disposal (one year later) first-hand information regarding companies’ accounts, the result being the so-called “semidefinitive” and, (two years later) the “definitive” accounts based on quasi exhaustive companies’ accounts. This term is in fact an overstatement, because these “definitive” accounts can themselves later be revised when a new “base” year is introduced.",
    partial=True)
add("una14-ch2-ppp", "UNA14", "Chapter 2, pp. 50–51", "Purchasing power parities", ["C3"],
    "Prices of certain goods and services can be very different from one country to another. For example, the price of renting a 100 m2 apartment may be 2000 euros in Amsterdam (the Netherlands), while for the same money one can rent a 300 m2 apartment in Istanbul (Turkey) or Mexico City. One therefore has to go further and eliminate differences in price levels so as to be able to compare solely the volumes produced in each country and not figures that are affected by differences in price levels. The OECD makes this adjustment by using “purchasing power parity”.",
    partial=True)
add("una14-ch3-levels", "UNA14", "Chapter 3, p. 81", "International comparisons of levels", ["C3", "C4"],
    "These international comparisons take place at three levels. The first and simplest consists of comparing the growth rates of certain variables, such as GDP in volume. In this case, the fact that countries have different currencies or institutions is not of great concern. The second level, to be examined in the second section, consists of the intercountry comparison of ratios, for example the profit rate or the public debt. In these cases, differences in statistical methods as well as in institutions can have a negative effect on comparisons, but the existence of different currencies still has no effect. The third level consists of comparing the absolute levels of certain national variables among several countries, such as the level of GDP per head or the level of household consumption per head. This final type of comparison is the most problematic. That is because on top of the two factors already mentioned, there is the added problem of currency conversion, which has to be solved by using “purchasing power parities”.",
    partial=True, access="subscriber")

# --- ESA 2010 -------------------------------------------------------------
add("esa10-8.94", "ESA10", "para. 8.94", "Gross and net national income", ["C1a"],
    "8.94 Gross (or net) national income (at market prices) represents total primary income receivable by resident institutional units: compensation of employees, taxes on production and imports less subsidies, property income (receivable less payable), (gross or net) operating surplus and (gross or net) mixed income. Gross national income (at market prices) equals GDP minus primary income payable by resident institutional units to non-resident institutional units plus primary income receivable by resident institutional units from the rest of the world. National income is not a production concept but an income concept, which is more significant if expressed in net terms, i.e. after deduction of the consumption of fixed capital.")
add("esa10-11.05", "ESA10", "para. 11.05", "Population", ["C4"],
    "11.05 Definition: on a given date, the total population of a country consists of all persons, national or foreign, who are permanently settled in the economic territory of the country, even if they are temporarily absent from it. An annual average of head counts will provide an appropriate basis for estimating national accounts variables or for use as a denominator in comparisons.")
add("esa10-11.06", "ESA10", "para. 11.06", "Population", ["C4"],
    "11.06 Total population is defined for national accounts according to the concept of residence as described in Chapter 2. A person who is staying, or intends to stay, on the economic territory of the country for a period of one year or more is regarded as permanently settled there. A person is regarded as being temporarily absent if he or she is permanently settled in the country but is staying, or intends to stay, in the rest of the world for a period of less than one year. All individuals who belong to the same household are resident where the household has a centre of predominant economic interest: this is where the household maintains a dwelling, or succession of dwellings, which members of the household treat, and use, as their principal residence. A member of a resident household continues to be a resident even if that individual makes frequent journeys outside the economic territory because their centre of economic interest remains in the economy in which the household is resident.")

# --- BEA NIPA Handbook ----------------------------------------------------
add("bea-ch1-revisions", "BEA", "Chapter 1: Introduction, “Why are the NIPA estimates revised?”", "Revisions and vintages", ["quality"],
    "BEA revises the NIPA estimates for two related reasons. First, as noted earlier, the NIPAs serve a multitude of purposes, some of which require frequent and immediately available estimates and others of which require consistent, long-term time series. Second, much of the source data that BEA uses to prepare the estimates are part of statistical programs that provide, over time, more complete or otherwise better coverage—for example, monthly surveys that are superseded by an annual survey that is drawn from a larger sample or that collects more detailed information. To address this implicit tradeoff between estimates that are the most timely possible and estimates that are the most accurate possible, BEA has developed a release cycle for the NIPA estimates. This cycle progresses from current quarterly estimates, which are released soon after the end of the quarter and which are based on limited source data, to comprehensive-update estimates, which are released about every 5 years and which incorporate the most extensive source data available.")
add("bea-ch2-gnp", "BEA", "Chapter 2: Fundamental Concepts", "Gross national income", ["C1a"],
    "Gross national product (GNP), which was discussed earlier in this chapter (see the section “Geographic coverage”), is equal to GDP minus net income payments to the rest of the world.")
add("bea-ch2-ndp-gni", "BEA", "Chapter 2: Fundamental Concepts", "Gross national income", ["C1a"],
    "Net domestic product (NDP) is a measure of how much of the nation’s output is available for consumption or for adding to the nation’s wealth. It is equal to GDP minus CFC. Gross national income (GNI) measures the costs incurred and the incomes earned in the production of GNP. It is equal to GNP minus the statistical discrepancy. It is also equal to GDI minus net income payments to the rest of the world.")

# --- CSO Ireland ----------------------------------------------------------
add("cso-gnistar-1", "CSO", "Modified GNI, paragraph 1", "Ireland and modified GNI", ["C1a", "quality"],
    "Modified Gross National Income (GNI) is an indicator designed specifically to measure the size of the Irish economy by excluding Globalisation effects.")
add("cso-gnistar-2", "CSO", "Modified GNI, paragraph 2", "Ireland and modified GNI", ["C1a", "quality"],
    "As we saw, Gross Domestic Product (GDP) is a measure of the total economic activity in the country, but a lot of Ireland’s GDP includes profits that are generated here but then go straight out to the owners of companies abroad. Gross National Income differs from GDP by the net amount of incomes sent to or received from abroad, so it excludes the net profits of companies that have been sent abroad.")
add("cso-gnistar-3", "CSO", "Modified GNI, paragraph 3", "Ireland and modified GNI", ["C1a", "quality"],
    "GNI, like GDP, is gross of Depreciation on Assets (that is, depreciation has not been deducted). Certain assets with high depreciation are held in Ireland by foreign-owned companies and add very significantly to our GNI. However, these assets are not always involved in production here, and if they are used in production, the profits all flow out to the foreign owner. The cost of depreciation on these assets is also borne by the owner overseas. For this reason, a measure that excluded this depreciation which does not relate to Irish income would be a better measure of the domestic economy.")
add("cso-gnistar-4", "CSO", "Modified GNI, paragraph 4", "Ireland and modified GNI", ["C1a", "quality"],
    "Modified GNI subtracts depreciation on two kinds of assets in order to exclude globalisation effects: Intellectual property (IP) and leased aircraft. First, depreciation on Intellectual Property is very high, and, because it is intangible and easily moved, it can cause GNI to jump around just because it has been relocated. Furthermore, while some of the IP is used for activity in Ireland (such as patents needed for manufacturing pharmaceuticals), most of the IP belongs to Foreign-Owned Corporations and it has a disproportionately small effect on the domestic economy.")
add("cso-gnistar-6", "CSO", "Modified GNI, paragraph 6", "Ireland and modified GNI", ["C1a", "quality"],
    "Finally, modified GNI excludes the income of Redomiciled PLCs. Gross National Income includes the profits that these companies receive from their subsidiaries abroad, and excludes the dividends that the company pays on to its shareholders. The difference between these two is their net income, and is quite substantial. It remains in the GNI estimate, even though these head offices have little interaction with the Irish economy. For this reason, modified GNI subtracts out the net income of Redomiciled PLCs.")

# --- Eurostat-OECD PPP manual ---------------------------------------------
add("ppp23-1.13", "PPP23", "para. 1.13", "Exchange rates versus PPPs", ["C3", "C1b"],
    "1.13 Before PPPs became available, only exchange rates were used to make international comparisons of GDP. Their use was underpinned by the theory of purchasing power parity in international economics. In its simplest form, the theory suggests that national price levels converted to a common currency using exchange rates should be equal. Arbitrage will ensure that the price of an individual good will be the same in all countries in which it is traded – the law of one price. Hence, when the individual goods are taken together, there will be high correlation in general price levels – at least in the medium and long term. The two key assumptions underlying the theory are that all goods are internationally tradable and that the demand and supply for currency is driven entirely by international trade in goods.")
add("ppp23-1.14", "PPP23", "para. 1.14", "Exchange rates versus PPPs", ["C3", "C1b"],
    "1.14 Exchange rates are determined by the supply and demand for different currencies. But the supply and demand for currencies are influenced by factors such as currency speculation, interest rates, government intervention and capital flows between countries, and not only by the currency requirements of international trade. Moreover, many goods and services, such as buildings, all government services and many market services, are not traded internationally. For these reasons, exchange rates do not reflect the relative purchasing powers of currencies in their national markets. Hence, while exchange rates provide GDP estimates that satisfy the third condition of being expressed in the same currency unit, they do not provide GDP estimates that satisfy the fourth condition of being valued at the same price level.")
add("ppp23-1.17", "PPP23", "para. 1.17", "Exchange rates versus PPPs", ["C3", "C1b"],
    "1.17 Currency conversions made with exchange rates do not take account of the larger price level differences between countries for non-tradable products. Hence, as demonstrated in Table 1.2, they overstate the size of economies with relatively high price levels and understate the size of economies with relatively low price levels.")
add("ppp23-1.31", "PPP23", "para. 1.31", "Purchasing power parities", ["C3", "quality"],
    "1.31 PPPs are statistical constructs rather than precise measures. While they provide the best available estimate of the size of a country’s economy and of its general price level in relation to other countries, they are, like all statistics, point estimates lying within a range of estimates – the error margin – that includes the true value. The error margins surrounding PPPs depend on the reliability of the expenditure weights and the price data as well as to the extent to which the particular goods and services selected for pricing by participating countries actually represent the price levels in each country. As with national accounts data generally, precise estimates of error margins for PPPs are challenging to derive.")

# --- SNA 2025 (pre-edit version) ------------------------------------------
add("sna25-3.142", "SNA25", "para. 3.142", "Net domestic product", ["C1a"],
    "3.142 In principle, the concept of value added should exclude allowances for depreciation and depletion. Depreciation, in effect, is not newly created value, but a reduction in the value of previously created fixed assets when they are used up in the production process. Depletion is also treated as a cost of production, as it represents the decline in the value of natural resources due to their extraction in the production of goods. Thus, theoretically, value added is a net concept. This conclusion applies to domestic product as well; theoretically, domestic product should be a net concept. Net domestic product (NDP) is obtained by deducting depreciation and depletion from GDP.")
add("sna25-3.144", "SNA25", "para. 3.144", "Gross national income", ["C1a"],
    "3.144 Earned incomes generated in the production activity of resident producer units are distributed mostly to other resident institutional units; however, part of them may go to non-resident units. Symmetrically, some earned incomes generated in the rest of the world may go to resident units. This leads to the definition and measurement of gross national income (GNI). GNI is equal to GDP less earned incomes payable to non-resident units plus earned incomes receivable from non-resident units. In other words, GNI is equal to GDP less taxes, less subsidies, on production and imports, remuneration of employees and property income payable to the rest of the world plus the corresponding items receivable from the rest of the world. Thus GNI is the sum of gross earned incomes receivable by resident institutional units or sectors. In contrast to GDP, GNI is not a concept of value added, but a concept of income.")
add("sna25-3.145", "SNA25", "para. 3.145", "Net national income", ["C1a"],
    "3.145 By deducting depreciation and depletion from GNI, net national income (NNI) is obtained. The remarks above about the conceptual relevance of the net concept in case of product apply even more strongly to national income.")
add("sna25-A4.10", "SNA25", "Annex 4, para. A4.10", "Net measures and growth", ["C1a", "C2"],
    "A4.10 Net income measures have been given more emphasis in the 2025 SNA. In this respect, the volume change of net domestic product (NDP) has been identified as the conceptually preferred measure of economic growth, not replacing but to be used alongside the volume change of gross domestic product (GDP). In the 2025 SNA, NDP is defined as GDP less depreciation and depletion of natural resources (in the 2025 SNA the term “depreciation” has replaced the term “consumption of fixed capital” used in the 2008 SNA; see table A4.2 below). See also section F.4 below for a discussion of the changed treatment of depletion in the 2025 SNA.")
add("sna25-A4.59", "SNA25", "Annex 4, para. A4.59", "Depletion of natural resources", ["C1a"],
    "A4.59 Depletion of non-produced natural resources is recorded as a cost of production in the 2025 SNA, instead of the 2008 SNA treatment as other changes in the volume of assets. Consequently, net domestic product is not only affected by depreciation (known as “consumption of fixed capital” in the 2008 SNA; see table A4.2 below), but also by the amount of depletion (see also section C.1 above).")
add("sna25-18.47", "SNA25", "para. 18.47", "Price and volume measures", ["C2"],
    "18.47 On balance, situations favourable to the use of chain Laspeyres and Paasche indices over time seem more likely than those that are unfavourable. The underlying economic forces that are responsible for the observed long-term changes in relative prices and quantities, such as technological progress and increasing incomes, do not often go into reverse. Hence, it is generally recommended that annual indices be chained. The price and volume components of monthly and quarterly data are usually subject to much greater variation than their annual counterparts due to seasonality and short-term irregularities. Therefore, the advantages of chaining at these higher frequencies are less and chaining should definitely not be applied to seasonal data that are not adjusted for seasonal fluctuations.")
add("sna25-23.68", "SNA25", "para. 23.68", "Globalisation and indicators other than GDP", ["C1a", "quality"],
    "23.68 Traditionally, analysis of economic activity within an economy focused on GDP as a broadly defined, internationally consistent measure of productive activity. Considering various economic developments, including increased globalization, the integrated framework of the SNA has given increased prominence to other key indicators, such as net domestic product (NDP), gross/net national income (GNI/NNI), gross/net national disposable income (GNDI/NNDI), and household (adjusted) disposable income. These indicators are generally less affected by globalization and less sensitive to the impact of MNE activities than GDP. This is an important factor to consider, especially for economies with significant MNE presence. As such, indicators other than GDP may better reflect the impact of the underlying economic activities of MNEs on an economy’s residents.")


# --- Additions after first review (13 Oct) ---------------------------------
add("sna08-15.187", "SNA08", "para. 15.187", "Real income and the terms of trade", ["C2"],
    "15.187 The terms of trade are defined as the ratio of the price of exports to the price of imports. If the prices of a country’s exports rise faster (or fall more slowly) than the prices of its imports (that is, if its terms of trade improve) fewer exports are needed to pay for a given volume of imports so that at a given level of domestic production goods and services can be reallocated from exports to consumption or capital formation. Thus, an improvement in the terms of trade makes it possible for an increased volume of goods and services to be purchased by residents out of the incomes generated by a given level of domestic production.")
add("sna08-15.2", "SNA08", "para. 15.2", "Nominal and real value added", ["C2"],
    "15.2 Another advantage of compiling price and volume measures within an accounting framework is that implicit price or volume measures can be derived for certain important balancing items. In particular, gross value added can be measured in real terms by subtracting intermediate consumption in volume terms from output in volume terms, the so-called “double deflation” method. Double deflation may be used at the level of an individual enterprise, industry or sector. However, the primary objective of the SNA is not simply to provide guidelines on measures of changes in prices and volumes for the main aggregates of the SNA but to assemble a set of interdependent measures that make it possible to carry out systematic and detailed analyses of inflation and economic growth.")
add("sna25-18.2", "SNA25", "para. 18.2", "Nominal and real value added", ["C2"],
    "18.2 Another advantage of compiling price and volume measures within an accounting framework is that implicit price or volume measures can be derived for certain important balancing items. In particular, gross value added can be measured in real terms by subtracting intermediate consumption in volume terms from output in volume terms, the so-called “double deflation” method. Double deflation may be used at the level of an individual enterprise, industry or sector. However, the primary objective of the integrated framework of the SNA is not simply to provide guidelines on measures of changes in prices and volumes for the main aggregates of the integrated framework but to assemble a set of interdependent measures that make it possible to carry out systematic and detailed analyses of inflation and economic growth.")
add("sna08-15.58", "SNA08", "para. 15.58", "Nominal and real value added", ["C2"],
    "15.58 An aggregate is defined as the sum of its components. Additivity in a national accounts context requires this identity to be preserved for a volume series. Although desirable from an accounting viewpoint, additivity is actually a very restrictive property. Laspeyres volume indices are the only index number formulae considered here that are additive.")
add("sna25-18.62", "SNA25", "para. 18.62", "Nominal and real value added", ["C2"],
    "18.62 A single link in a chain index is sufficient to destroy additivity even when additive indices, such as Laspeyres volume indices, are linked together. Consequently, if chain volume indices are converted into time series of values by using the indices to extrapolate the values of the base period, the index components may fail to add to aggregates in later periods. A perverse form of non-additivity can occur when the chain index for the aggregate lies outside the range spanned by the chain indices for its components, a result that may be regarded as intuitively unacceptable by many users. Whether published in monetary terms or indices, it is advisable to inform users that chain volume series are not additive.")
add("una14-ch1-deflator", "UNA14", "Chapter 1, p. 22, partial", "Nominal and real value added", ["C2"],
    "The macroeconomist will immediately want to know if this 10% growth (which may be described as “nominal” or “in value” or, better still, “at current prices”) is due to an increase in the quantity of pasta or to an increase in its price. An increase in quantity is good news, while an increase in prices (“inflation”) tends to be bad news. Keeping in mind the aim of separating the good growth (the quantities) from the bad growth (inflation), national accountants have developed sophisticated methods for separating out movements in GDP “at current prices” into two components: (1) an indicator of the change in quantity (the “real GDP” or, preferably, “GDP in volume”); and (2) an indicator of the change in prices, called the “GDP deflator”. These methods are described in detail in Chapter 2.",
    partial=True)
add("sna25-9.136", "SNA25", "para. 9.136", "Remittances and short-term workers", ["C1a"],
    "9.136 Current transfers between households consist of all current transfers made, or received, by resident households to or from other resident or non-resident households. The transfers include all cash transfers and the value of transfers in kind. In the context of remittances, current transfers between households are often referred to as personal transfers. They include regular remittances between households resident in different parts of the same country or in different countries, usually from a member of a family working in a foreign country for a period of a year or longer. Earnings remitted by border, seasonal, other short-term and remote workers to their families are not personal transfers as the workers remain resident in their country of origin (that is, they are still members of their original households) when they work abroad for periods of less than a year. Their earnings are recorded as remuneration of employees from abroad if they have the status of an employee in the non-resident country while they are working there or as the provision of services otherwise.")
add("sna25-19.52", "SNA25", "para. 19.52", "Remittances and short-term workers", ["C1a"],
    "19.52 In some countries, border or seasonal workers may have a significant effect on the amount of remuneration of employees that is either payable abroad or receivable from abroad. Remuneration earned abroad but repatriated to the country where the employee is resident (as opposed to where he or she works) adds to the income of households available for consumption. The concept of national income as opposed to domestic production is thus another key aggregate of the integrated framework of the SNA. As well as labour income from abroad in the form of remuneration of employees, income earned abroad on capital, especially financial capital, in the form of property income, is included in national income as well as any taxes less subsidies on production and imports payable by non-residents. Similar payments flowing out of the total economy to the rest of the world have to be deducted from GDP to reach national income.")
add("sna25-5.11", "SNA25", "para. 5.11", "Population", ["C4"],
    "5.11 Generally, persons who are resident in a country for one year or more, regardless of their citizenship, should be included in the population measure. An exception is foreign diplomatic personnel and defence personnel, together with their families, who should be included as part of the population of their home country. The “one-year rule” means that usual residents who are living abroad for less than one year are included in the population but foreign visitors (for example, holidaymakers) who are in the country for less than one year are excluded from the measured population. Further elaboration on the application of the residence criterion in special cases is given in section J.")

# --- Comparison-resistant services (13 Oct, second comment round) ---------
add("ppp23-4.16", "PPP23", "para. 4.16", "Comparison-resistant services", ["C3"],
    "4.16 Because they are sold at economically-significant prices, expenditures on market services can be obtained by multiplying the quantities sold by the prices they are sold at. The same prices can also be used to calculate the PPPs for market services. The lack of economically-significant prices for non-market services precludes their expenditures and their PPPs being derived in the same manner as they are for market services. Instead, following the convention adopted by national accountants, expenditures on non-market services are estimated by summing up their costs of production. Consistency with the prices underlying the expenditure estimates can be maintained by using the prices of inputs to calculate the PPPs for non-market services. This is referred to as the input-price approach. To implement the input-price approach, the expenditures on non-market services need to be broken down by cost components, namely: compensation of employees, intermediate consumption, consumption of fixed capital, net operating surplus, net taxes on production and receipts from sales. The disadvantage of the input-price approach is that differences in productivity across countries are not reflected in the resulting volume measures.")
add("ppp23-8.2", "PPP23", "para. 8.2", "Comparison-resistant services", ["C3", "quality"],
    "8.2 In practice, with this approach, only prices for the principal cost component – compensation of employees – are collected. PPPs are calculated with the prices (wages, salaries and allowances) that general government pays employees in selected occupations, such as teaching professionals, school administrators and support staff in the case of education. The volume measures generated by these PPPs are volume measures for inputs and do not reflect productivity differences between the non-market producers of participating countries. In the absence of any adjustment for productivity, this is widely perceived as a serious weakness of the approach. It is, in effect, assuming that productivity is uniform across the producers of non-market services in different countries which is unrealistic. For this reason, alternative approaches for non-market services have emerged and been adopted by the Programme. These approaches concern individual services such as health and education. The input-price approach is still used for collective services as described in Chapter 9.")
add("ppp23-8.4", "PPP23", "para. 8.4 (first part)", "Comparison-resistant services", ["C3", "quality"],
    "8.4 Education like other non-market services is considered to be comparison resistant. While this is principally because there are no economically significant prices with which to value output, it is also because the units of output are difficult to define and measure and because the differences in the quality of output between countries cannot be easily identified and quantified.",
    partial=True)

# --- Double deflation in practice (13 Oct) --------------------------------
add("sna25-18.143", "SNA25", "para. 18.143", "Nominal and real value added", ["C2", "quality"],
    "18.143 While the double deflation method is theoretically sound, the resulting estimates are subject to the errors of measurement in the volume estimates of both output and intermediate consumption. This may be especially true if output PPIs are applied to inputs, many of which are imported. Because value added is the relatively small difference between two much larger figures, it is extremely sensitive to error. It is therefore advisable to compare the growth rates of the price and volume measures of value added over recent years with the corresponding growth rates of output and intermediate inputs and, if possible, with volume estimates of inputs of labour and capital services to check for plausibility.")
add("sna25-18.145", "SNA25", "para. 18.145", "Nominal and real value added", ["C2", "quality"],
    "18.145 The choice to be made between the use of a single indicator method (which may yield biased results) or a double deflation method (which may yield volatile results) must be based on judgement. The same choice need not be made for all industry groups. Further, the single indicator method may be used for quarterly figures until the year is complete and better double deflation estimates are available.")
add("sna25-18.146", "SNA25", "para. 18.146", "Nominal and real value added", ["C2", "quality"],
    "18.146 In certain non-market service industries, it may be necessary to estimate movements in the volume of value added on the basis of the estimated volume changes of the inputs into the industries. The inputs may be total inputs, labour inputs on their own or intermediate inputs on their own. For example, it is not uncommon to find the movement of the implicit volume of value added estimated by means of changes in remuneration of employees at constant wage rates, or even simply by changes in numbers employed, in both market and non-market service industries. (There is extensive work being carried out to improve these working assumptions by trying to measure the outputs of government-provided health and education more objectively; see paragraphs 18.124 to 18.133.)")

# --- Hours worked, for splitting "per head" into per hour x hours (13 Oct) --
add("sna25-16.71", "SNA25", "para. 16.71", "Hours worked", ["C4"],
    "16.71 The volume quadrant describes the relationship between the hours of labour that are supplied by persons and the hours of labour that are used by enterprises. Hours worked (LAB1) are defined as the number of hours actually worked as an employee or self-employed person, to produce output recorded within the production boundary applied in the integrated framework of the SNA. It quantifies the number of hours actually worked by persons in all jobs. Total hours (actually) worked is the preferred measure to be used in productivity estimates as this is the best, and closest, measure that relates to the labour time used as the input to produce the output measured, both by industry and the whole economy.")
add("sna25-16.73", "SNA25", "para. 16.73", "Hours worked", ["C4", "quality"],
    "16.73 In practice, total hours actually worked and annual hours actually worked in full-time jobs may have to be estimated but substantial data on labour and output can be gathered from the same businesses to ensure consistency with the labour input to produce the output. In many countries, especially for monthly paid employee jobs, only normal hours or hours usually worked, any paid overtime, plus annual and holiday leave entitlements can be ascertained. An adjustment should be made to the total hours actually worked or annual (full-time) hours actually worked to account for the average level of absence from work due to illness. This difference will not affect full-time equivalent employment, as discussed further below, if sickness rates in part-time jobs are the same as in full-time jobs. However, if they are not, adjustments should be considered.")
add("sna25-16.95", "SNA25", "para. 16.95", "Hours worked", ["C4", "quality"],
    "16.95 Using total hours actually worked as the input measure for calculating (labour) productivity changes over time implicitly assumes that each hour worked is of the same quality (that is, there are no differences in the qualifications and skill levels of the labour employed). In other words, each hour worked by a highly skilled person, such as a brain surgeon, is assumed to produce the same quantity and quality of output as each hour worked by an unskilled worker. It is possible to produce a quality-adjusted measure of the labour inputs that takes account of changes in the mix of workers over time by weighting together indicators of quality for different grades of workers. (The term quality-adjusted is used as being parallel to the idea of quality-adjusted price indices but it could also be seen as an adjustment for the change in the composition of the workers involved.)")

# --- Scope: how far each passage generalises ------------------------------
SCOPE_BY_SOURCE = {
    "SNA08": "international standard",
    "SNA25": "international standard",
    "QNA17": "international guidance",
    "PPP23": "international guidance",
    "ESA10": "regional standard: European Union",
    "UNA14": "textbook",
    "BEA": "national practice: United States",
    "CSO": "national practice: Ireland",
}
CSO_NOTE = ("Modified GNI (GNI*) is an Irish measure, published by the CSO since 2017 to remove "
            "globalisation effects specific to Ireland. It is an example, not an international standard.")
PPP_EUOECD_NOTE = ("Describes Eurostat-OECD practice. Other regions of the World Bank's International Comparison "
                   "Program have made productivity adjustments to input prices that Eurostat and the OECD do not make "
                   "(manual glossary, “Productivity adjustment”; Deaton and Heston 2010, section D).")
SCOPE_NOTES = {
    "una14-ch1-revisions": "Insee is the French national statistics office. The “provisional”, “semi-definitive” and “definitive” stages describe French practice, given as an example; other agencies use other release schedules.",
    "una14-ch1-nni": "The preference for GDP and GNI over NDP and NNI is attributed to OECD economists in 2014. The 2025 SNA now names NDP growth as the preferred measure (sna25-A4.10).",
    "una14-ch2-ppp": "Describes what the OECD does; other bodies (Eurostat, the World Bank's International Comparison Program) also compile PPPs.",
    "bea-ch1-revisions": "NIPA (National Income and Product Accounts) is the US name for the national accounts. The release cycle described is BEA's own.",
    "bea-ch2-gnp": "GNP is the US term, still used by BEA. The 1993 SNA renamed GNP as GNI.",
    "bea-ch2-ndp-gni": "GDI here is BEA's gross domestic income: GDP measured from the income side, equal to GDP apart from the statistical discrepancy. It is not the SNA's “real GDI” (sna08-15.188). The link from GNI to GNP through the statistical discrepancy is a US identity.",
    "sna08-15.188": "“Real GDI” here is the SNA's purchasing-power measure: GDP in volume plus the trading gain, also called command-basis GDP. BEA uses “GDI” for the income-side estimate of GDP (bea-ch2-ndp-gni). Same letters, different measures.",
    "ppp23-4.16": PPP_EUOECD_NOTE, "ppp23-8.2": PPP_EUOECD_NOTE, "ppp23-8.4": PPP_EUOECD_NOTE,
    "cso-gnistar-1": CSO_NOTE, "cso-gnistar-2": CSO_NOTE, "cso-gnistar-3": CSO_NOTE,
    "cso-gnistar-4": CSO_NOTE, "cso-gnistar-6": CSO_NOTE,
}
ESA_NOTE = "ESA 2010 is the European Union's legally binding version of the SNA; its definitions follow the SNA closely."
for p in P:
    if p["code"] == "ESA10":
        SCOPE_NOTES.setdefault(p["pid"], ESA_NOTE)
for pid in SCOPE_NOTES:
    assert pid in {p["pid"] for p in P}, pid


# --- verification ---------------------------------------------------------
def normalise(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


source_text = {}
for code, name in SOURCE_FILES.items():
    raw = (SCRATCH / "corpus_raw" / name).read_text(encoding="utf-8", errors="replace")
    # Remove page furniture (page numbers, running headers) so sentences that
    # cross a page break can still be matched. Only whole lines are removed.
    furniture = [r"^\d{1,3}$", r"^12\. Revisions\s+\d+$", r"^UNDERSTANDING NATIONAL ACCOUNTS © OECD 2014$",
                 r"^1\.$", r"^THE ESSENTIAL MACROECONOMIC AGGREGATES$", r"^Pre edit version$", r"^Eurostat-OECD Methodological Manual on Purchasing Power Parities$", r"^Component expenditures of GDP$"]
    kept = []
    for line in raw.splitlines():
        if line.strip() == "" or any(re.match(f, line.strip()) for f in furniture):
            continue
        kept.append(line)
    raw = "\n".join(kept)
    layout = (SCRATCH / "corpus_text" / name).read_text(encoding="utf-8", errors="replace")
    source_text[code] = normalise(raw) + "|" + normalise(layout)

problems = []
for p in P:
    # Split into sentences; drop the leading paragraph number for matching.
    body = re.sub(r"^A?\d+\.\d+\s", "", p["text"])
    sentences = re.split(r"(?<=[.;:?])\s+(?=[A-Z“(])", body)
    for s in sentences:
        n = normalise(s)
        if len(n) < 8:
            continue
        if n not in source_text[p["code"]]:
            problems.append((p["pid"], s[:90]))

ids = [p["pid"] for p in P]
assert len(ids) == len(set(ids)), "duplicate ids"

if problems:
    print("NOT FOUND IN SOURCE:")
    for pid, s in problems:
        print(" ", pid, "|", s)
else:
    print("All sentences found in their sources.")

qna_words = sum(len(p["text"].split()) for p in P if p["code"] == "QNA17")
print("passages:", len(P), "| QNA17 words:", qna_words)

out = []
for p in P:
    title, edition, licence = SOURCE_NAMES[p["code"]]
    out.append({
        "id": p["pid"],
        "source": title,
        "reference": p["reference"],
        "text": p["text"],
        "edition": edition,
        "source_code": p["code"],
        "topic": p["topic"],
        "components": p["components"],
        "partial": p["partial"],
        "access": p["access"],
        "scope": SCOPE_BY_SOURCE[p["code"]],
        "scope_note": SCOPE_NOTES.get(p["pid"], ""),
        "licence": licence,
    })
if not problems:
    path = REPO / "data" / "corpus" / "passages.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print("written", path)
