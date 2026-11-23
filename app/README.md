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
