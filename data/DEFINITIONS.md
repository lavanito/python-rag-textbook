# Definitions and judgements for Chapter 14

## `definitions.csv`

One row per measure the NNI model gives (13). Columns: `measure` (code name), `means` (what it means), `leaves_out` (what it leaves out; empty when the definition already says it), `passages` (passage ids that define it, separated by "; "; empty when the corpus has none). Each reply's locked block shows them as "What it means: … What it leaves out: … See …". Passages are cited by id, not quoted.

| Date | Change | Decided by |
|---|---|---|
| 13 Nov 2026 | Round 1: the AI coding assistant drafted 13 definitions; the vertical domain expert approved 7, changed 5, asked about 1 (average hours). | Vertical domain expert |
| 13 Nov 2026 | Round 2: "per head" kept (defined as "divided by the resident population"); "parts", not "components"; "persons in work" (Penn World Table's "persons engaged": employees and self-employed); a "What it leaves out" sentence for every measure. | Vertical domain expert, on the AI coding assistant's proposals |
| 13 Nov 2026 | Unpaid work at home named in every measure it touches: "unpaid work at home, such as caring, cooking and cleaning, most of it done by women" (ILO, *Care work and care jobs for the future of decent work*, 2018: women do 76.2 per cent of unpaid care work hours). No corpus passage yet covers it. | Vertical domain expert |
| 13 Nov 2026 | GNI total: "at the official exchange rate" removed; the World Bank's note for NY.GNP.MKTP.CD (sent by the vertical domain expert) does not say which rate converts it. Population checked against the World Bank's metadata (de facto, mid-year). | Vertical domain expert, the AI coding assistant |
| 13 Nov 2026 | All 13 rows approved in chat ("i agree", 09:24), not in the spreadsheet. | Vertical domain expert |

## `answers/ch14_support_judgements.csv`

The vertical domain expert's judgements of 20 sentences from Chapter 11's analyst answers (run of 30 October 2026, 800 tokens). Sentences citing exactly one id that was given; answers q2-05, q2-10, q2-13 and q2-31 left out (discussed beforehand); 20 of the remaining 27 answers drawn at random, one sentence each (Python random, seed 14). Code's word-overlap score was not shown to him.

| Date | Change | Decided by |
|---|---|---|
| 13 Nov 2026 | First judgement (one column: Supported 16, Partly 2, Not supported 2). | Vertical domain expert |
| 13 Nov 2026 | Second round with two judgements: `support` (Supported 19, Partly 1) and `answers_question` (Yes 14, Partly 3, No 3). Scope notes are our notes, not evidence. A miscited sentence with true content counts as a failure. | Vertical domain expert |

The support check's thresholds (`SUPPORT_MIN`, `MISCITED_BY` in `ragbook/ch14_answer_checks.py`) were chosen by looking at these 20, so agreement with them is a training score.

## `question_bank/ch14_fair_test.jsonl`

The vertical domain expert's 10 new questions for Chapter 14's fair test, written after the checks were frozen at `9b1e82e` (14 November 2026) and opened by the AI coding assistant only after that commit was pushed. Labels (class, route, economies, years, measures, editions) proposed by the AI coding assistant on 14 November and agreed by the vertical domain expert on 16 November.

| Date | Label | Decided by |
|---|---|---|
| 16 Nov 2026 | f-03 "real GDP per head" → GDP per head at PPP (the model has no real GDP per head level). | Vertical domain expert |
| 16 Nov 2026 | f-04, f-06 "real GDP" revisions → revisions to real GDP growth (no GDP level in the model); the answer must be in those terms. | Vertical domain expert |
| 16 Nov 2026 | f-06 "revised in 2023": no 2023 edition; the March 2024 and October 2026 editions are compared. | Vertical domain expert |
| 16 Nov 2026 | Principle for later: when the measure asked for is not in the data but a near one is, answer with the near one and say so openly; matching by meaning, not only by words. Not in the frozen code. | Vertical domain expert |
