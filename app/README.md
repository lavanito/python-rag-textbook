# Demonstrator page data (gate A5)

The demonstrator is one self-contained page with no server (build spec v3,
component 17). Every file in `app/data/` is written by a script in `tools/`
from the data, the saved runs and the NNI model; nothing here is edited by
hand, and a test rebuilds each file and fails if it differs.

| File | Written by | What it holds |
| --- | --- | --- |
| `data/method_and_caveats.json` | `tools/build_method_page.py` | The "Method and caveats" page (lesson L5): counts of passages, questions by route, measures, figures by data quality rating, explanations, fingerprinted files, cross-check agreement; seven caveats |
| `data/coverage_grid.json` | `tools/build_coverage_grid.py` | The coverage grid (lesson L6): 16 measures by six economies, each cell exact, proxy or no figure, with years, the first nowcast year and the last year's data quality rating, from the NNI model tool |
| `data/change_log.json` | `tools/build_change_log.py` | The change log for readers (lesson L8), newest first, from `data/change_log.csv` (written and approved by people) |
| `data/bank_replies.json` | `tools/build_bank_replies.py` | The reply to each of the 56 bank questions in both use modes: locked block, evidence, withheld passages, explanation and the page text; the sharper questions for the three vague questions; the suggested questions. Commercial explanations come from `data/answers/a5_explanations_commercial.jsonl`, written on the laptop by `tools/run_commercial_explanations.py` |
| `data/faq.json` | `tools/build_faq.py` | The page's questions and answers, from `data/faq.csv` (written by the vertical domain expert, 24 Nov 2026) |
| `data/lessons.json` | `tools/build_page_text.py` | Lessons for a production version (decision 26), read from Chapter 15, section 15.7 |
| `data/at_full_scale.json` | `tools/build_page_text.py` | The "In this build / At full scale" table, from `data/at_full_scale.csv` (agreed 17 Nov 2026) |
| `data/sources.json` | `tools/build_page_text.py` | The sources page: ten corpus sources with terms for quoting and links with two dates; data sources by edition |
| `data/walkthrough.json` | `tools/build_page_text.py` | The six lifecycle steps: process sentence (`data/walkthrough.csv`, approved 24 Nov 2026), steps and the means used for each (front matter, "Steps and the means used"), and the "At full scale" rows for each step |
| `data/figures.json` | `tools/build_figures.py` | Every NNI model result the page can ask for (seven economies, 2000 to 2025, 12 measures, two editions) with value, flags, DQR band and reason; with the last years, measures, size cuts, approved definitions and approved wording the locked-block code needs |

## JavaScript (`app/js/`)

| File | Written by | What it does |
| --- | --- | --- |
| `js/locked_block.js` | by hand, from Chapters 13 and 14 | Builds the locked block for a typed question from `data/figures.json`: calls, digits, comparisons with size bands, premise line, definition lines, escalation, comparison line. `tests/test_locked_block_js.py` checks it equals the stored bank replies and Python's `locked_block` |
| `js/nni.js` | `tools/copy_nni_js.py` | nni-model's `js/nni.js`, unchanged, at the commit `requirements.txt` pins (recorded in `js/nni_js_source.json`); gives the digits shown and changes in log points |
| `js/run_locked_blocks.js` | by hand | Runs the locked-block code on a list of questions for the tests |
