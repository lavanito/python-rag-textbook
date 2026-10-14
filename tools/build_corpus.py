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
add("sna08-2.144", "SNA08", "para. 2.144", "Net national income", ["C1a"],
    "2.144 By deducting the consumption of fixed capital from GNI, net national income (NNI) is obtained. The remarks above about the conceptual relevance of the net concept in case of product apply even more strongly to national income.")
add("sna08-12.26", "SNA08", "para. 12.26", "Depletion of natural resources", ["C1a"],
    "12.26 The depletion of natural resources covers the reduction in the value of deposits of subsoil assets as a result of the physical removal and using up of the assets.")

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
add("una14-ch2-ppp", "UNA14", "Chapter 2, pp. 50–51", "Purchasing power parities", ["C3"],
    "Prices of certain goods and services can be very different from one country to another. For example, the price of renting a 100 m2 apartment may be 2000 euros in Amsterdam (the Netherlands), while for the same money one can rent a 300 m2 apartment in Istanbul (Turkey) or Mexico City. One therefore has to go further and eliminate differences in price levels so as to be able to compare solely the volumes produced in each country and not figures that are affected by differences in price levels. The OECD makes this adjustment by using “purchasing power parity”.",
    partial=True)

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
add("sna25-3.145", "SNA25", "para. 3.145", "Net national income", ["C1a"],
    "3.145 By deducting depreciation and depletion from GNI, net national income (NNI) is obtained. The remarks above about the conceptual relevance of the net concept in case of product apply even more strongly to national income.")
add("sna25-A4.10", "SNA25", "para. A4.10 (first part)", "Net measures and growth", ["C1a", "C2"],
    "A4.10 Net income measures have been given more emphasis in the 2025 SNA. In this respect, the volume change of net domestic product (NDP) has been identified as the conceptually preferred measure of economic growth, not replacing but to be used alongside the volume change of gross domestic product (GDP). In the 2025 SNA, NDP is defined as GDP less depreciation and depletion of natural resources (in the 2025 SNA the term “depreciation” has replaced the term “consumption of fixed capital” used in the 2008 SNA; see table A4.2 below).",
    partial=True)
add("sna25-A4.59", "SNA25", "Annex 4, para. A4.59", "Depletion of natural resources", ["C1a"],
    "A4.59 Depletion of non-produced natural resources is recorded as a cost of production in the 2025 SNA, instead of the 2008 SNA treatment as other changes in the volume of assets. Consequently, net domestic product is not only affected by depreciation (known as “consumption of fixed capital” in the 2008 SNA; see table A4.2 below), but also by the amount of depletion (see also section C.1 above).")
add("sna25-23.68", "SNA25", "para. 23.68 (first part)", "Globalisation and indicators other than GDP", ["C1a", "quality"],
    "23.68 Traditionally, analysis of economic activity within an economy focused on GDP as a broadly defined, internationally consistent measure of productive activity. Considering various economic developments, including increased globalization, the integrated framework of the SNA has given increased prominence to other key indicators, such as net domestic product (NDP), gross/net national income (GNI/NNI), gross/net national disposable income (GNDI/NNDI), and household (adjusted) disposable income. These indicators are generally less affected by globalization and less sensitive to the impact of MNE activities than GDP.",
    partial=True)


# --- Additions after first review (13 Oct) ---------------------------------
add("sna08-15.187", "SNA08", "para. 15.187 (first sentence)", "Real income and the terms of trade", ["C2"],
    "15.187 The terms of trade are defined as the ratio of the price of exports to the price of imports.",
    partial=True)
add("una14-ch1-deflator", "UNA14", "Chapter 1, p. 22, partial", "Nominal and real value added", ["C2"],
    "The macroeconomist will immediately want to know if this 10% growth (which may be described as “nominal” or “in value” or, better still, “at current prices”) is due to an increase in the quantity of pasta or to an increase in its price. An increase in quantity is good news, while an increase in prices (“inflation”) tends to be bad news. Keeping in mind the aim of separating the good growth (the quantities) from the bad growth (inflation), national accountants have developed sophisticated methods for separating out movements in GDP “at current prices” into two components: (1) an indicator of the change in quantity (the “real GDP” or, preferably, “GDP in volume”); and (2) an indicator of the change in prices, called the “GDP deflator”. These methods are described in detail in Chapter 2.",
    partial=True)

# --- Comparison-resistant services (13 Oct, second comment round) ---------
add("ppp23-4.16", "PPP23", "para. 4.16", "Comparison-resistant services", ["C3"],
    "4.16 Because they are sold at economically-significant prices, expenditures on market services can be obtained by multiplying the quantities sold by the prices they are sold at. The same prices can also be used to calculate the PPPs for market services. The lack of economically-significant prices for non-market services precludes their expenditures and their PPPs being derived in the same manner as they are for market services. Instead, following the convention adopted by national accountants, expenditures on non-market services are estimated by summing up their costs of production. Consistency with the prices underlying the expenditure estimates can be maintained by using the prices of inputs to calculate the PPPs for non-market services. This is referred to as the input-price approach. To implement the input-price approach, the expenditures on non-market services need to be broken down by cost components, namely: compensation of employees, intermediate consumption, consumption of fixed capital, net operating surplus, net taxes on production and receipts from sales. The disadvantage of the input-price approach is that differences in productivity across countries are not reflected in the resulting volume measures.")
add("ppp23-8.2", "PPP23", "para. 8.2", "Comparison-resistant services", ["C3", "quality"],
    "8.2 In practice, with this approach, only prices for the principal cost component – compensation of employees – are collected. PPPs are calculated with the prices (wages, salaries and allowances) that general government pays employees in selected occupations, such as teaching professionals, school administrators and support staff in the case of education. The volume measures generated by these PPPs are volume measures for inputs and do not reflect productivity differences between the non-market producers of participating countries. In the absence of any adjustment for productivity, this is widely perceived as a serious weakness of the approach. It is, in effect, assuming that productivity is uniform across the producers of non-market services in different countries which is unrealistic. For this reason, alternative approaches for non-market services have emerged and been adopted by the Programme. These approaches concern individual services such as health and education. The input-price approach is still used for collective services as described in Chapter 9.")
add("ppp23-8.4", "PPP23", "para. 8.4 (first part)", "Comparison-resistant services", ["C3", "quality"],
    "8.4 Education like other non-market services is considered to be comparison resistant. While this is principally because there are no economically significant prices with which to value output, it is also because the units of output are difficult to define and measure and because the differences in the quality of output between countries cannot be easily identified and quantified.",
    partial=True)

# --- Double deflation in practice (13 Oct) --------------------------------

# --- Hours worked, for splitting "per head" into per hour x hours (13 Oct) --
add("sna25-16.95", "SNA25", "para. 16.95 (first part)", "Hours worked", ["C4", "quality"],
    "16.95 Using total hours actually worked as the input measure for calculating (labour) productivity changes over time implicitly assumes that each hour worked is of the same quality (that is, there are no differences in the qualifications and skill levels of the labour employed). In other words, each hour worked by a highly skilled person, such as a brain surgeon, is assumed to produce the same quantity and quality of output as each hour worked by an unskilled worker.",
    partial=True)

# --- Open-licence replacements for SNA and UNA14 passages (14 Oct) ---------
# SNA and UNA14 are not openly licensed, so they are cut to a short, cited set
# (caps tested in tests/test_corpus.py). ESA 2010, the PPP manual and the BEA
# handbook cover the same ground on open terms. "[…]" marks words left out.
add("esa10-8.89", "ESA10", "para. 8.89", "GDP definition", ["C4"],
    "8.89 Gross domestic product at market prices is the final result of the production activity of resident producer units. It can be defined in three ways: (a) production approach: GDP is the sum of gross value added of the various institutional sectors or the various industries plus taxes and less subsidies on products (which are not allocated to sectors and industries). It is also the balancing item in the total economy production account; (b) expenditure approach: GDP is the sum of final uses of goods and services by resident institutional units (final consumption and gross capital formation), plus exports and minus imports of goods and services; (c) income approach: GDP is the sum of uses in the total economy generation of income account (compensation of employees, taxes on production and imports less subsidies, gross operating surplus and mixed income of the total economy).")
add("esa10-3.139", "ESA10", "para. 3.139 (first part)", "Consumption of fixed capital", ["C1a"],
    "3.139 Definition: consumption of fixed capital (P.51c) is the decline in value of fixed assets owned, as a result of normal wear and tear and obsolescence. The estimate of decline in value includes a provision for losses of fixed assets as a result of accidental damage which can be insured against.",
    partial=True)
add("esa10-10.47", "ESA10", "para. 10.47 (part)", "Real income and the terms of trade", ["C2", "C1a"],
    "10.47 Gross domestic product at previous year prices measures the total production (less the intermediate consumption) in volume terms for the total economy. The total real income of residents is influenced not only by this volume of production but also by the rate at which exports can be traded against imports from the rest of the world. If the terms of trade improve, fewer exports are needed to pay for a given volume of imports, so that at a given level of domestic production goods and services can be reallocated from exports to consumption or capital formation. Real gross domestic income can be derived by adding the so-called trading gain to volume figures on gross domestic product. […] The choice of an appropriate deflator P for the current trade balances should be left to the statistical authorities in a country, taking account of the particular circumstances of that country. In circumstances in which there is uncertainty about the choice of deflator an average of the import and the export price indices is likely to provide a suitable deflator.",
    partial=True)
add("esa10-10.20", "ESA10", "para. 10.20 (last part)", "Price and volume measures", ["C2"],
    "In the calculation of the volume, quantities are weighted up by prices of the base period, so that the result depends on the price structure. Changes in price structure are likely to be less important for short periods than for long periods. Therefore, the calculation of the volume is made only for two successive years, i.e. the volume is calculated at the prices of the previous year. For comparisons over longer periods of time, the Laspeyres volume indices and the Paasche price indices are calculated first in relation to the previous year and then the chain indices are determined.",
    partial=True, access="subscriber")
add("esa10-10.22", "ESA10", "para. 10.22", "Nominal and real value added", ["C2"],
    "10.22 Chained indices present the drawback that they lead to volumes having no additivity so that they cannot be used in the balancing procedures of products based on supply and use tables.")
add("esa10-10.32", "ESA10", "para. 10.32 (part)", "Nominal and real value added", ["C2"],
    "10.32 Definition: value added in volume terms is defined as the difference between output in volume terms and intermediate consumption in volume terms. […] The theoretically correct method to calculate value added in volume terms is by double deflation, i.e. deflating separately the two flows of the production account (output and intermediate consumption) and calculating the balance of those two revalued flows.",
    partial=True)
add("esa10-10.33", "ESA10", "para. 10.33 (part)", "Nominal and real value added", ["C2", "quality"],
    "10.33 In some cases, where the statistical data remain incomplete or insufficiently reliable, it may be necessary to use a single indicator. […] For certain market and non-market service industries, such as finance, business services or defence, it may not be possible to obtain satisfactory estimates of price or volume changes for output. In such cases the movements of value added in volume terms can be estimated by means of changes in compensation of employees at wage rates of the previous year and consumption of fixed capital in volume terms. Compilers of data may be forced to adopt such expedients, even when there is no good reason to assume that labour productivity remains unchanged in the short or long term.",
    partial=True)
add("esa10-11.27", "ESA10", "para. 11.27 (first part)", "Hours worked", ["C4"],
    "11.27 Definition: total hours worked represents the aggregate number of hours actually worked as an employee or self-employed person during the accounting period, when their output is within the production boundary. Given the broad definition of employees which covers persons temporarily not at work but with a formal attachment, and part-time workers, the appropriate measure for productivity calculation is not a head count but total hours worked. Total hours worked is the most appropriate measure of labour inputs for the national accounts.",
    partial=True)
add("esa10-2.10", "ESA10", "para. 2.10 (part)", "Remittances and short-term workers", ["C1a"],
    "Households, except in their capacity as owners of land and buildings, are resident units of the economic territory where they have a centre of predominant economic interest. They are resident irrespective of periods spent abroad of less than one year. They shall include, in particular, the following: (a) border workers, defined as people who cross the frontier daily to work in a neighbouring country; (b) seasonal workers, defined as people who leave the country for several months according to season, but less than a year, to work in another country;",
    partial=True)
add("esa10-4.129", "ESA10", "para. 4.129", "Remittances and short-term workers", ["C1a"],
    "4.129 Definition: current transfers between households (D.752) consist of all current transfers in cash or in kind made, or received, by resident households to, or from, other resident or non-resident households. In particular, they comprise remittances by emigrants or workers permanently settled abroad (or working abroad for a period of a year or longer) to members of their family living in their country of origin, or by parents to children in another location.")
add("esa10-18.53", "ESA10", "para. 18.53", "Remittances and short-term workers", ["C1a"],
    "18.53 Other workers, such as border and seasonal workers, do not change their economy of residence from the home economy. Instead of transfers, the international transactions of such workers include compensation of employees, taxes and travel costs. In the balance of payments, a supplementary presentation of personal remittances brings together personal transfers with those related items. Personal remittances include personal transfers, compensation of employees less taxes and travel, and capital transfers between households.")
add("bea-ch4-fisher", "BEA", "Chapter 4: Estimating Methods, “Estimates for NIPA aggregates”", "Price and volume measures", ["C2"],
    "In the NIPAs, the annual changes in quantities and prices are calculated using a Fisher formula that incorporates weights from 2 adjacent years. For example, the 2014–2015 change in real GDP uses prices for 2014 and 2015 as weights, and the 2014–2015 change in prices uses quantities for 2014 and 2015 as weights. These annual changes are “chained” (multiplied) together to form time series of quantity and price indexes.",
    partial=True)
add("bea-ch4-chained", "BEA", "Chapter 4: Estimating Methods, “Chained-dollar measures”", "Nominal and real value added", ["C2"],
    "Despite the greater accuracy provided by the chain-type indexes, users of macroeconomic statistics need more than index numbers and percent changes. The earlier fixed-weighted estimates were denominated in constant dollars, and the real levels for the components of GDP added up to total GDP. Because the system was additive, the shares of the real components reflected their relative importance in total GDP. Similarly, in decomposing total GDP growth by component, the change in constant-dollar values measured the component’s contribution to the change in the fixed-weighted aggregate. For GDP and most of its components, BEA prepares estimates in chained dollars as well as chain-type indexes (see the appendix to this chapter). However, because these chained-dollar measures are not based on a single set of weights, they are not additive and thus do not yield accurate measures of shares and contributions to growth.")
add("ppp23-ov.12", "PPP23", "Overview, para. 12", "International comparisons of levels", ["C3", "C4"],
    "12. The volume indices and per capita volume indices are based on real expenditures. Real expenditures are national expenditures – that is, expenditures expressed in national currencies and valued at national price levels – that have been converted to a common currency and valued at a uniform price level with PPPs. The expenditures are real because, being at the same price level, they reflect only differences in the volume of goods and services purchased in countries. Both indices are indicative of the relative magnitudes of the component expenditure being compared with the per capita indices also taking into account the differences in the size of populations between countries. At the level of GDP, the volume indices are used to compare the economic size of countries and the per capita volume indices the material well-being of their residents.")
add("ppp23-ov.13", "PPP23", "Overview, para. 13", "Price level indices", ["C3", "C1b"],
    "13. The price level indices (PLIs) are the ratios of PPPs to exchange rates. As such, they provide a measure of the differences in price levels between countries by indicating for a given component expenditure the number of units of common currency needed to buy the same volume of the component expenditure in each country. At the level of GDP, PLIs provide a measure of the differences in the general price levels of countries.")

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
    "una14-ch2-ppp": "Describes what the OECD does; other bodies (Eurostat, the World Bank's International Comparison Program) also compile PPPs.",
    "bea-ch1-revisions": "NIPA (National Income and Product Accounts) is the US name for the national accounts. The release cycle described is BEA's own.",
    "bea-ch2-gnp": "GNP is the US term, still used by BEA. The 1993 SNA renamed GNP as GNI.",
    "bea-ch2-ndp-gni": "GDI here is BEA's gross domestic income: GDP measured from the income side, equal to GDP apart from the statistical discrepancy. It is not the SNA's “real gross domestic income” (esa10-10.47). The link from GNI to GNP through the statistical discrepancy is a US identity.",
    "bea-ch4-fisher": "NIPAs is the US name for the national accounts. BEA uses a Fisher formula; most EU countries chain Laspeyres volume and Paasche price indices (esa10-10.20). Both chain annually.",
    "bea-ch4-chained": "Chained dollars are BEA's name for chain-linked volumes in national currency. The point about additivity holds for chain-linked volumes everywhere (esa10-10.22).",
    "esa10-10.47": "ESA 2010 follows the 2008 SNA here (2008 SNA 15.187–15.188). “Real gross domestic income” is the purchasing-power measure, not BEA's income-side GDI (bea-ch2-ndp-gni).",
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
    sentences = re.split(r"\s*\[…\]\s*|(?<=[.;:?])\s+(?=[A-Z“(])", body)
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
