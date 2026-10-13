# Question bank

`questions.jsonl` holds the test questions. Each line is one question with:

| Field | Meaning |
| --- | --- |
| `id` | Class and number, for example `q2-05` |
| `question` | The question as a user would ask it |
| `class` | Question class: Q1 lookup, Q2 definition, Q3 compute, Q4 vintage, Q5 multi-country, Q6 mixed, Q7 scenario, Q8 multi-step, AMB too vague to answer until refined, OUT out of scope |
| `route` | Route tier: R2 model class, R4 retrieval, R5 small model, R6 agent loop, clarify (offer sharper questions), or escalate to a person |
| `gold_passages` | Corpus passages that should be retrieved to answer it |
| `expected` | A short statement of the right answer |
| `check` | What an answer must do to pass, beyond being correct (name both editions, state the scope, avoid false certainty) |

Countries (task A2a): United States, euro area, United Kingdom, China, India, Japan.

Draft 2, 13 October 2026: 51 questions. Every corpus passage is the answer to at least one question; `tests/test_question_bank.py` checks this.
