# Definitions and judgements for Chapter 14

## `definitions.csv`

One row per measure the NNI model gives (13). Columns: `measure` (code name), `means` (what it means), `leaves_out` (what it leaves out; empty when the definition already says it), `passages` (passage ids that define it, separated by "; "; empty when the corpus has none). Each reply's locked block shows them as "What it means: … What it leaves out: … See …". Passages are cited by id, not quoted.

| Date | Change | Decided by |
|---|---|---|
| 13 Nov 2026 | Round 1: Claude drafted 13 definitions; Lavan approved 7, changed 5, asked about 1 (average hours). | Lavan |
| 13 Nov 2026 | Round 2: "per head" kept (defined as "divided by the resident population"); "parts", not "components"; "persons in work" (Penn World Table's "persons engaged": employees and self-employed); a "What it leaves out" sentence for every measure. | Lavan, on Claude's proposals |
| 13 Nov 2026 | Unpaid work at home named in every measure it touches: "unpaid work at home, such as caring, cooking and cleaning, most of it done by women" (ILO, *Care work and care jobs for the future of decent work*, 2018: women do 76.2 per cent of unpaid care work hours). No corpus passage yet covers it. | Lavan |
| 13 Nov 2026 | GNI total: "at the official exchange rate" removed; the World Bank's note for NY.GNP.MKTP.CD (sent by Lavan) does not say which rate converts it. Population checked against the World Bank's metadata (de facto, mid-year). | Lavan, Claude |
| 13 Nov 2026 | All 13 rows approved in chat ("i agree", 09:24), not in the spreadsheet. | Lavan |

## `answers/ch14_support_judgements.csv`

Lavan's judgements of 20 sentences from Chapter 11's analyst answers (run of 30 October 2026, 800 tokens). Sentences citing exactly one id that was given; answers q2-05, q2-10, q2-13 and q2-31 left out (discussed beforehand); 20 of the remaining 27 answers drawn at random, one sentence each (Python random, seed 14). Code's word-overlap score was not shown to him.

| Date | Change | Decided by |
|---|---|---|
| 13 Nov 2026 | First judgement (one column: Supported 16, Partly 2, Not supported 2). | Lavan |
| 13 Nov 2026 | Second round with two judgements: `support` (Supported 19, Partly 1) and `answers_question` (Yes 14, Partly 3, No 3). Scope notes are our notes, not evidence. A miscited sentence with true content counts as a failure. | Lavan |

The support check's thresholds (`SUPPORT_MIN`, `MISCITED_BY` in `ragbook/ch14_answer_checks.py`) were chosen by looking at these 20, so agreement with them is a training score.
