# Corpus sources

Every passage in the corpus is quoted word for word from one of these sources,
with its paragraph or section reference. This file records what each source is,
where it was downloaded, and on what terms it may be quoted.

Status of each licence entry: **confirmed** (read on the publisher's own page,
date given) or **to confirm** (not yet read on the publisher's page).

| Code | Source | Edition | Terms for quoting | Status | Download |
| --- | --- | --- | --- | --- | --- |
| SNA08 | United Nations, European Commission, IMF, OECD, World Bank: *System of National Accounts 2008* | 2009 | "Copyright © 2009 European Communities, IMF, OECD, United Nations and World Bank. All rights reserved." No licence is published. un.org terms of use allow personal, non-commercial download only. Short quotation with full citation relies on the quotation exception in copyright law; anything more needs permission from UN Publications, Rights and Permissions (shop.un.org/rights-permissions) | confirmed 14 Oct 2026 (PDF rights page; un.org copyright and terms of use) | https://unstats.un.org/UNSD/nationalaccount/docs/SNA2008.pdf |
| SNA25 | Same five organisations: *System of National Accounts 2025* | Pre-edit version, adopted by the UN Statistical Commission in March 2025 | Same as SNA08: "Copyright © 2025 … All rights reserved." | confirmed 14 Oct 2026 (PDF rights page). The UNSD 2025 SNA page still links only the pre-edit version; no edited final version published. Text used: "White Cover Version", 1,260 pages, dated 15 Aug 2025 | https://unstats.un.org/unsd/nationalaccount/docs/2025_SNA_Pre-edit.pdf |
| QNA17 | IMF: *Quarterly National Accounts Manual*, 2017 edition | 2018 | Fair use for non-commercial teaching, scholarship or research: up to 1,000 words or one quarter of the content from any one source, whichever is less, with a complete citation | confirmed 12 Oct 2026, imf.org copyright and terms | https://www.imf.org/external/pubs/ft/qna/pdf/2017/QNAManual2017text.pdf |
| UNA14 | Derek Blades and others, OECD: *Understanding National Accounts*, second edition | 2014 | PDF rights notice (© OECD 2014): excerpts may be included in your own documents, presentations, blogs, websites and teaching materials with acknowledgement of source and copyright owner. Public or commercial use: request to rights@oecd.org | confirmed 14 Oct 2026 (PDF rights page) | https://www.oecd.org/content/dam/oecd/en/publications/reports/2014/10/understanding-national-accounts_g1g43f55/9789264214637-en.pdf |
| ESA10 | Eurostat: *European System of Accounts — ESA 2010* | 2013 | PDF rights notice (© European Union, 2013): reproduction authorised provided the source is acknowledged. Eurostat copyright page: commercial reuse allowed; changes must be stated | confirmed 14 Oct 2026 (PDF rights page; Eurostat copyright page) | https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-02-13-269 |
| BEA | US Bureau of Economic Analysis: *NIPA Handbook: Concepts and Methods of the U.S. National Income and Product Accounts* | Chapters 1–14, December 2024 | Public domain unless stated otherwise; may be reproduced without permission; credit to BEA requested; no suggestion of BEA endorsement | confirmed 14 Oct 2026 (bea.gov FAQ and citation guidelines) | https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/all-chapters.pdf |
| CSO | Central Statistics Office, Ireland: *Modified GNI* (Statistics Explained) | web page | CC BY 4.0, source acknowledged | confirmed 12 Oct 2026, cso.ie copyright policy | https://www.cso.ie/en/interactivezone/statisticsexplained/nationalaccountsexplained/modifiedgni/ |
| PPP23 | Eurostat and OECD: *Methodological Manual on Purchasing Power Parities*, 2023 edition | 2024 | PDF rights notice (© European Union/OECD 2024): CC BY 4.0; credit given, changes indicated. Cover image excluded | confirmed 14 Oct 2026 (PDF rights page) | https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/w/ks-gq-24-011 |

### Decision for the author

Two sources are not openly licensed: SNA08 and SNA25 (all rights reserved; 36 passages, about 3,700 words) and UNA14 (6 passages, about 700 words; public or commercial use needs OECD permission). The repository is public and the book is published by Lavan Mahadeva Ltd. Options: ask UN Publications and OECD for permission; or keep SNA and UNA14 passages short and few enough to rely on quotation with citation.

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
  Footnote markers such as "(140)" are left out.
- Reference to paragraph, section or page, enough for a reader to find it.
- Edition recorded, so the same paragraph in two editions can be held side by side.
- Short: one paragraph, under 200 words. A passage that stops before the end of its paragraph is marked `partial`.
- Within each source's limits; for QNA17, no more than 1,000 words in total.
- The licence recorded beside each passage.
- The scope recorded beside each passage: international standard, international
  guidance, regional standard (EU), textbook, or one country's practice. A passage
  that names an agency, a national term or one country's practice (NIPA, Insee,
  GNP, modified GNI) carries a `scope_note` saying so. Answers must present such
  passages as examples, not as the general rule. A test enforces the note.

## Passage plan

65 passages from eight sources (see `passages.jsonl`), 20 of them from the
2025 SNA. They are chosen to answer the question bank and to cover
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

## Further reading cited in the book, not quoted in the corpus

- Angus Deaton and Alan Heston (2010), "Understanding PPPs and PPP-based national
  accounts", *American Economic Journal: Macroeconomics* 2(4), section D:
  comparison-resistant items (housing and government services), input prices and
  productivity adjustment. Journal copyright; cited, not quoted.
- Work by Nicholas Oulton on comparing services output across countries: exact
  references to be chosen.
