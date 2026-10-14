# Tools for building the corpus and question bank

These scripts are for maintaining the data, not part of the book's code.

| File | What it does |
| --- | --- |
| `extract_text.sh` | Extracts text from the source PDFs into `data/raw/text/` (not committed) |
| `para.py` | Finds and prints numbered paragraphs in that text, to copy passages from |
| `build_corpus.py` | Holds every passage with its source, reference, topic, parts and scope; checks each sentence against the PDF text; writes `data/corpus/passages.jsonl` only if all are found |
| `build_questions.py` | Holds the question bank; writes `data/question_bank/questions.jsonl`; lists any passage no question uses |

## Adding a passage

1. Download the source PDF into your sources folder (see `data/corpus/SOURCES.md`).
2. Run `tools/extract_text.sh <sources folder>`.
3. Find the paragraph: `python3 -I tools/para.py find <text file> "<words>"`.
4. Copy it into `build_corpus.py` with `add(...)`; add a scope note if it names one agency's terms or practice.
5. Run `python3 -I tools/build_corpus.py`, then add a question that uses it in `build_questions.py` and run that.
6. Run `python -m pytest`. The tests fail if a passage lacks a scope note where needed or answers no question.
