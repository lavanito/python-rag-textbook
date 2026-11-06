# Series titles

`wdi_titles.csv`: the code and published title of each of the 17 World Bank WDI series in the nni-model snapshot (`lavanito/nni-model`, `data/wdi/wdi_latest_2026-10-08.csv`). Titles are the `name` field of the World Bank API (`https://api.worldbank.org/v2/indicator/<code>?format=json`), read in Lavan's built-in browser on 3 November 2026 and copied without retyping.

Route R1 (no AI) reports these titles word for word: a question that asks for the exact name of a series in this list is answered from the file. A series not in the list is not R1 (decision of 3 November 2026).

Licence: CC BY 4.0, World Bank.

## Last year of the data (the ragged edge)

`last_year.csv`: the last year of real NNI per head for each economy (USA, EA21, GBR, CHN, IND, JPN, IRL) in each WDI edition (latest, 8 October 2026; archive, `202403`). Written by `tools/build_last_year.py` from the nni-model repository at commit 3124bfa, using its own loader and decomposition class; nothing is retyped. A blank last year means the economy is not in that edition. Added on 6 November 2026 (Lavan).

The last year differs by measure too: hours worked (PWT 11.0) end in 2023, and published NNI ends in 2021 (UK 2018), filled and flagged "estimated" after that. This file does not record those; the answer step does.
