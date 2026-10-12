# Python RAG — code for the textbook

This repository holds the tested Python code for *Python RAG*, a textbook on retrieval-augmented generation (RAG). RAG means finding the right passages in your own documents first, then asking a language model to answer from those passages only.

The running example is a small corpus of passages on GDP statistics, quoted from published national accounts manuals, and a bank of test questions. The same material drives the online demonstration *Demonstrating AI readiness: what it takes*.

## What the code is, and is not

- **Written to be read.** Plain loops, full names, one step per line, results printed between steps. It is slower than it could be, on purpose.
- **Tested.** Every function the book shows is checked automatically on every change.
- **Not production software.** It shows how each part works; it does not handle scale, security or failure the way a live system must.
- **Local and open source.** It runs on an ordinary laptop. Nothing is sent to a paid or cloud service.

## Layout

| Folder or file | What it holds |
| --- | --- |
| `ragbook/` | One file per chapter, named `chNN_topic.py` (for example `ch03_keyword_search.py`) |
| `tests/` | The checks for each chapter, and the rule that code is reused forward only |
| `data/corpus/` | Quoted passages, each with source, edition, paragraph reference and licence |
| `data/question_bank/` | Test questions, each with the passages that should answer it |
| `requirements.txt` | The packages to install, with fixed versions |

## Code is reused forward only

A chapter's file may import functions from earlier chapters, never from the same or later ones. Chapter 5 may use Chapter 3; Chapter 3 never uses anything from Chapter 5. The test `tests/test_import_direction.py` checks every import on every change, and also checks that it catches a deliberate mistake.

## Running the tests

On your own computer, from this folder:

```
pip install -r requirements.txt
python -m pytest -v
```

GitHub runs the same tests on every change. The **Actions** tab shows each run; each step's name says what it proved.

## Tools

| Tool | Job | Licence |
| --- | --- | --- |
| Python | The language | PSF licence |
| pytest | Runs the tests | MIT |

Further tools are added as chapters need them, each with its licence: Ollama and Qwen3 (the local language model), sentence-transformers, bm25s and Chroma.

## Licences

- **Code:** MIT (see `LICENSE`). Reuse it with credit.
- **Book text:** CC BY 4.0, added when chapters move into this repository. Share and adapt it with credit.
- **Quoted passages** in `data/corpus/` keep their publishers' terms, recorded beside each passage.

## Status

Repository skeleton only. Chapters are drafted in a shared document and their code is added here chapter by chapter.

## Author

Lavan Mahadeva
