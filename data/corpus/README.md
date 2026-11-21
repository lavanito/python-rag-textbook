# Corpus

Short passages on GDP statistics, quoted from published manuals and statistical
offices. Each passage records its source, edition, paragraph reference and
licence. Built in task S1; empty until then.

## Source links (added 21 November 2026)

`source_links.csv` gives each source a link and two dates: `document_date`,
the document's own date ("not stated" when the publisher gives none), and
`date_read`, when its text and licence were read (the dates in `SOURCES.md`).
A passage's link is its source's link; its `reference` finds the paragraph.
`tests/test_source_links.py` checks every source has both dates;
`tools/check_source_links.py` opens every link before a release.
