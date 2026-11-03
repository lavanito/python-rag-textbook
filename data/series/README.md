# Series titles

`wdi_titles.csv`: the code and published title of each of the 17 World Bank WDI series in the nni-model snapshot (`lavanito/nni-model`, `data/wdi/wdi_latest_2026-10-08.csv`). Titles are the `name` field of the World Bank API (`https://api.worldbank.org/v2/indicator/<code>?format=json`), read in Lavan's built-in browser on 3 November 2026 and copied without retyping.

Route R1 (no AI) reports these titles word for word: a question that asks for the exact name of a series in this list is answered from the file. A series not in the list is not R1 (decision of 3 November 2026).

Licence: CC BY 4.0, World Bank.
