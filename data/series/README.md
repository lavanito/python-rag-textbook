# Series titles

`wdi_titles.csv`: the code and published title of each of the 17 World Bank WDI series in the nni-model snapshot (`lavanito/nni-model`, `data/wdi/wdi_latest_2026-10-08.csv`). Titles are the `name` field of the World Bank API (`https://api.worldbank.org/v2/indicator/<code>?format=json`), read in the domain expert's built-in browser on 3 November 2026 and copied without retyping.

Route R1 (no AI) reports these titles word for word: a question that asks for the exact name of a series in this list is answered from the file. A series not in the list is not R1 (decision of 3 November 2026).

Licence: CC BY 4.0, World Bank.

## Last year of the data (the ragged edge)

`last_year.csv`: the last year of real NNI per head for each economy (USA, EA21, GBR, CHN, IND, JPN, IRL) in each WDI edition (latest, 8 October 2026; archive, `202403`). Written by `tools/build_last_year.py` from the nni-model repository at commit 3124bfa, using its own loader and decomposition class; nothing is retyped. A blank last year means the economy is not in that edition. Added on 6 November 2026 (the domain expert).

The last year differs by measure too: hours worked (PWT 11.0) end in 2023, and published NNI ends in 2021 (UK 2018), filled and flagged "estimated" after that. This file does not record those; the answer step does.

## Size bands for changes (revisions, changes over time, gaps)

`revisions.csv`: every figure the NNI model gives in both WDI editions (latest, 8 October 2026; archive, `202403`), for the six economies, 1990 to 2022: the latest edition minus the archive edition, in log points for levels and percentage points for rates and shares. 985 rows. The euro area has no archive figures; Penn World Table measures have one edition.

`revision_bands.csv`: the 16.5th, 33rd, 67th and 83.5th percentiles of the 778 revisions of 0.005 or more (smaller ones show as 0.00). Large: below the 16.5th or above the 83.5th; small: 33rd to 67th inclusive; medium: in between. The same bands judge changes over time and gaps between economies (the domain expert, 16 November 2026). Written by `tools/build_revision_bands.py`.
