# Corpus sources

Every passage in the corpus is quoted word for word from one of these sources,
with its paragraph or section reference. This file records what each source is,
where it was downloaded, and on what terms it may be quoted.

Status of each licence entry: **confirmed** (read on the publisher's own page,
date given) or **to confirm** (not yet read on the publisher's page).

| Code | Source | Edition | Terms for quoting | Status | Download |
| --- | --- | --- | --- | --- | --- |
| SNA08 | United Nations, European Commission, IMF, OECD, World Bank: *System of National Accounts 2008* | 2009 | UN copyright; short quotation with full citation | to confirm (UNSD copyright page did not load) | https://unstats.un.org/UNSD/nationalaccount/docs/SNA2008.pdf |
| SNA25 | Same five organisations: *System of National Accounts 2025* | Pre-edit version, adopted by the UN Statistical Commission in March 2025 | UN copyright; short quotation with full citation | to confirm; also check whether an edited final version has replaced it | https://unstats.un.org/unsd/nationalaccount/docs/2025_SNA_Pre-edit.pdf |
| QNA17 | IMF: *Quarterly National Accounts Manual*, 2017 edition | 2018 | Fair use for non-commercial teaching, scholarship or research: up to 1,000 words or one quarter of the content from any one source, whichever is less, with a complete citation | confirmed 12 Oct 2026, imf.org copyright and terms | https://www.imf.org/external/pubs/ft/qna/pdf/2017/QNAManual2017text.pdf |
| UNA14 | Derek Blades and others, OECD: *Understanding National Accounts*, second edition | 2014 | OECD terms of use | to confirm (OECD terms page did not load) | https://www.oecd.org/content/dam/oecd/en/publications/reports/2014/10/understanding-national-accounts_g1g43f55/9789264214637-en.pdf |
| ESA10 | Eurostat: *European System of Accounts — ESA 2010* | 2013 | Eurostat reuse policy, source acknowledged | to confirm | https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-02-13-269 |
| BEA | US Bureau of Economic Analysis: *NIPA Handbook: Concepts and Methods of the U.S. National Income and Product Accounts* | Chapters 1–14, December 2024 | US federal government work, public domain | to confirm | https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/all-chapters.pdf |
| CSO | Central Statistics Office, Ireland: *Modified GNI* (Statistics Explained) | web page | CC BY 4.0, source acknowledged | confirmed 12 Oct 2026, cso.ie copyright policy | https://www.cso.ie/en/interactivezone/statisticsexplained/nationalaccountsexplained/modifiedgni/ |
| PPP23 | Eurostat and OECD: *Methodological Manual on Purchasing Power Parities*, 2023 edition | 2024 | to confirm | to confirm | https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/w/ks-gq-24-011 |

## Not used

The draft 2025 SNA chapter files (`2025SNA_CH07_V5.pdf` and others on the chapter
list page) carry tracked changes: deleted and inserted words run together in the
text, for example "consumption of fixed capitaldepreciation and depletion". They
cannot be quoted. The pre-edit version of the full 2025 SNA is used instead.

## How each passage was checked

Each passage was copied from text extracted from the publisher's PDF. A script
then confirmed that every sentence of every passage appears in that PDF's text,
ignoring only spacing, punctuation and page furniture (page numbers and running
headers). The PDFs themselves are not stored in this repository.

## Rules for every passage

- Quoted exactly, from the publisher's own file, never from memory or a summary.
- Reference to paragraph, section or page, enough for a reader to find it.
- Edition recorded, so the same paragraph in two editions can be held side by side.
- Short: one paragraph, under 200 words. A passage that stops before the end of its paragraph is marked `partial`.
- Within each source's limits; for QNA17, no more than 1,000 words in total.
- The licence recorded beside each passage.

## Passage plan

40 passages so far from seven sources (see `passages.jsonl`), with about six to
follow from the 2025 SNA. They are chosen to answer the question bank and to cover
the five components of the NNI decomposition (C1a–C4).

| Topic | Component | Sources | Passages |
| --- | --- | --- | --- |
| GDP: definition and the three approaches | C4 | SNA08, UNA14, BEA | 5 |
| Gross national income and primary income from abroad | C1a | SNA08, SNA25, BEA | 5 |
| Net national income and consumption of fixed capital | C1a | SNA08, SNA25, UNA14 | 5 |
| Depletion of natural resources (2008 vs 2025 treatment: content vintage) | C1a | SNA08, SNA25 | 4 |
| Price and volume measures; deflators; chain-linking | C2 | SNA08, SNA25, QNA17 | 6 |
| Purchasing power parities versus exchange rates | C3 | PPP23, UNA14 | 6 |
| Exchange-rate conversion of national accounts | C1b | UNA14, ESA10 | 3 |
| Real output per head; population | C4 | UNA14, ESA10 | 3 |
| Revisions, releases and vintages | data quality | QNA17, BEA | 5 |
| Seasonal adjustment | data quality | QNA17 | 2 |
| Ireland and multinational effects; modified GNI | C1a, data quality | CSO, SNA25 (globalisation) | 4 |

One passage will carry a demonstration label "subscriber only" to show access
rules at retrieval (Chapter 8). The label is part of the demonstration; it does
not describe the publisher's terms.
