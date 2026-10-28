# Chapter 10 — Is the retriever any good?

## 10.1 What this chapter builds

Chapters 3 to 9 counted **hits**: the questions with at least one gold passage in the first 1, 3 or 10 places. A hit ignores the other passages in those places and any gold passages missed; this chapter adds five measures that count them, and runs them on every search built so far.

1. **Gold lists** (10.2): for each question q, the set G(q) of passages judged to answer it, and the rule for judging. Every measure compares a search's first k passages with G(q).
2. **Precision, recall and F1** (10.3): how much of what the search returns is gold, and how much of the gold it returns.
3. **Reciprocal rank** (10.4): the place of the first gold passage.
4. **Average precision** (10.5): one number for whether all the gold passages come early.
5. **Measuring every search** (10.6): the five measures for seven searches, with query expansion measured on BM25 alone as well as inside hybrid search.
6. **The gold lists move the figures** (10.7): the same searches on four sets of gold lists, from before 26 October 2026 to the passage-by-passage judging of 27 and 28 October.
7. **Is one search better?** (10.8): the questions on which each of two searches scores higher, and whether 32 questions are enough to show a difference.

**Code file:** `ragbook/ch10_evaluation.py`

**Uses:** Python's `math` module. From earlier chapters: `load_corpus` (Chapter 2), `load_questions` and `KeywordIndex` (Chapter 3), `load_embeddings`, `SemanticIndex` and `EMBEDDING_FILE` (Chapter 4), `HybridIndex`, `KnowledgeGraph`, `expand_question` and `saved_question_embedder` (Chapter 5), `FilteredSearch` (Chapter 8), `RerankedSearch`, `saved_scorer`, `load_scores` and `SCORE_FILE` (Chapter 9). No model and no internet.

## 10.2 Gold lists: the passages every measure is checked against

### 10.2.1 Principles

Every measure in this chapter compares what a search returns with a **gold list**: the passages a person judged to answer the question. The measures are only as good as the lists.

The rule, set on 26 October 2026: **a passage is gold if it states what the expected answer says.** On 27 October Lavan Mahadeva read each of the 56 passages once and judged it against all 32 definition questions with that rule. On 28 October he revised four judgements, and one passage, sna25-11.238, was added to the corpus. Each judgement is yes or no; a passage cannot be half gold.

Some passages carry part of an expected answer without answering the question by themselves. They are kept as **supporting passages**: they stay in the gold list, and each question names them, so the figures can be shown with and without them (10.7). There are six, on five questions. Three passages answer no question; they are **distractors**, which test whether a search avoids related but wrong passages.

The 32 definition questions have 62 gold passages between them, 56 without the supporting ones. Most questions have one or two.

| Gold passages per question | Questions |
| --- | --- |
| 1 | 11 |
| 2 | 15 |
| 3 | 3 |
| 4 (q2-17, q2-22, q2-30) | 3 |

Three things follow.

- **A missing passage counts against the search.** If a passage answers the question but is not on the list, a search that returns it is scored as wrong. Chapter 9 found four such passages (9.6.3).
- **Lists made after looking at results favour the search looked at.** The four passages were added after reading the reranker's first choices. A search whose choices were checked gains; a search whose choices were not checked keeps any gaps (10.7). Judging every passage against every question removes this bias.
- **Withheld passages stay on the list.** In commercial use (Chapter 8) the filters withhold some gold passages. They still count, so a search cannot score full marks on a question whose gold it is not allowed to see. That is the intended reading: the measure says how well the user is served, not how well the search did with what it was given.

## 10.3 Precision, recall and F1

### 10.3.1 Principles

The answer is built from the first three passages (Chapter 2), so these measures look at the first three places.

- **Precision at 3** is the share of the first three passages that are gold. It asks: how much of what the model will read is right?
- **Recall at 3** is the share of the gold passages that are in the first three. It asks: how much of the right material does the model get?
- **F1** combines the two into one number. It is the harmonic mean: 2 × precision × recall ÷ (precision + recall). Unlike the plain average, it is low when either is low.

An example from Chapter 8's filtered search, q2-01 ("What is consumption of fixed capital?"). The gold list is esa10-3.139 and sna25-A4.59; the first three places are esa10-3.139, sna25-A4.10 and sna25-A4.59.

| Measure | Working | Value |
| --- | --- | --- |
| Precision at 3 | 2 gold of 3 returned | 0.67 |
| Recall at 3 | 2 found of 2 gold | 1.00 |
| F1 | 2 × 0.67 × 1.00 ÷ 1.67 | 0.80 |

The gold lists cap both measures, whatever the search.

- **Precision at 3 cannot reach 1** for a question with fewer than three gold passages: one gold passage caps it at 0.33, two at 0.67. Over the 32 questions, the highest mean possible is 0.61.
- **Recall at 3 cannot reach 1** for a question with more than three: q2-17, q2-22 and q2-30 have four, so each is capped at 0.75. The highest mean possible is 0.98.

So a precision of 0.46 is three-quarters of the way to the cap, not under half. The figures in 10.6 are read against these caps.

### 10.3.2 Code

`ragbook/ch10_evaluation.py`, the constants `TOP` and `DEPTH` and the functions `precision_at`, `recall_at` and `f1`

```python
TOP = 3      # the places precision, recall and F1 look at: the passages an answer uses
DEPTH = 10   # the places reciprocal rank and average precision look at
```

```python
def precision_at(found_ids, gold_ids, places=TOP):
    """
    The share of the first `places` passages that are gold.

    Example:
        precision_at(["a", "x", "b"], ["a", "b"], 3)
        returns 0.667 (two of three)
    """
    first = found_ids[:places]
    gold_found = 0
    for passage_id in first:
        if passage_id in gold_ids:
            gold_found = gold_found + 1
    return gold_found / places
```

```python
def recall_at(found_ids, gold_ids, places=TOP):
    """
    The share of the gold passages found in the first `places` passages.

    Example:
        recall_at(["a", "x", "y"], ["a", "b"], 3)
        returns 0.5 (one of two)
    """
    first = found_ids[:places]
    gold_found = 0
    for gold_id in gold_ids:
        if gold_id in first:
            gold_found = gold_found + 1
    return gold_found / len(gold_ids)
```

```python
def f1(precision, recall):
    """
    The harmonic mean of precision and recall: high only when both are high.

    Example:
        f1(1.0, 0.5)
        returns 0.667
        f1(0.0, 0.0)
        returns 0.0
    """
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
```

### 10.3.3 Annotations

- Each function takes lists of passage ids, not passages, so it can be checked by hand on letters, as the tests do.
- `precision_at` divides by `places`, not by the number of passages returned. A search that returns fewer than three passages does not score higher for returning fewer.
- `f1` returns 0 when both inputs are 0, rather than dividing by zero.
- Chapter 7 used recall for a different thing: how many of the true nearest embeddings a quick graph search finds. Here recall is always about gold passages.

## 10.4 Reciprocal rank

### 10.4.1 Principles

**Reciprocal rank** is 1 divided by the place of the first gold passage: 1 for first place, 0.5 for second, 0.1 for tenth, and 0 if no gold passage is in the first ten. The mean over the questions is the **mean reciprocal rank (MRR)**.

A gold passage in first place scores far more than one lower down. Moving from second to first adds 0.5; moving from tenth to ninth adds 0.01. That suits a reader who looks at the first passage and stops.

It is close to hits at 1: a question scores 1 exactly when it is a hit at 1, so the count of questions with reciprocal rank 1 equals Chapter 5's hits at 1 (a test checks this), but a miss at first place still scores something if the gold passage is near the top.

In q2-30 the filtered search's first gold passage, wb13-mccarthy-space-time, is fourth: reciprocal rank 0.25. The other gold passages below it do not change the score.

### 10.4.2 Code

`ragbook/ch10_evaluation.py`, the function `reciprocal_rank`

```python
def reciprocal_rank(found_ids, gold_ids, depth=DEPTH):
    """
    1 divided by the place of the first gold passage; 0 if none is in the
    first `depth` places.

    Example:
        reciprocal_rank(["x", "a", "b"], ["a", "b"])
        returns 0.5 (first gold passage in second place)
    """
    for place, passage_id in enumerate(found_ids[:depth], start=1):
        if passage_id in gold_ids:
            return 1 / place
    return 0.0
```

### 10.4.3 Annotations

- `enumerate(..., start=1)` counts places from 1, as a reader does, so `1 / place` is 1 for first place.
- The function returns as soon as it meets a gold passage. Later gold passages are never looked at.

## 10.5 Average precision

### 10.5.1 Principles

**Average precision** looks at every gold passage, not just the first. At the place of each gold passage found, take the precision up to that place; add these up and divide by the number of gold passages, so a gold passage outside the first ten places adds 0.

The mean over the questions is the **mean average precision (MAP)**. It is 1 only when every gold passage is ranked above every other passage.

q2-30 has four gold passages; the filtered search puts two of them at places 4 and 5.

| Gold passage found | Place | Gold passages so far | Precision at that place |
| --- | --- | --- | --- |
| wb13-mccarthy-space-time | 4 | 1 | 1 ÷ 4 = 0.25 |
| esa10-10.47 | 5 | 2 | 2 ÷ 5 = 0.40 |

The two precisions add to 0.65. Divided by four gold passages, not two found, the average precision is 0.16; the two gold passages not found each count as 0.

Average precision depends on order where precision at 3 does not. The lists a, b, x and x, a, b (gold a and b) both have precision at 3 of 0.67; their average precisions are 1.00 and 0.58.

### 10.5.2 Code

`ragbook/ch10_evaluation.py`, the function `average_precision`

```python
def average_precision(found_ids, gold_ids, depth=DEPTH):
    """
    The precision at the place of each gold passage found, added up and
    divided by the number of gold passages. A gold passage not found in the
    first `depth` places adds 0.

    Example:
        average_precision(["a", "x", "b"], ["a", "b"])
        returns (1/1 + 2/3) / 2 = 0.833
    """
    total = 0.0
    gold_found = 0
    for place, passage_id in enumerate(found_ids[:depth], start=1):
        if passage_id in gold_ids:
            gold_found = gold_found + 1
            total = total + gold_found / place
    return total / len(gold_ids)
```

### 10.5.3 Annotations

- `gold_found / place` is the precision up to the current place, worked out only where a gold passage stands.
- The total is divided by `len(gold_ids)`, every gold passage on the list. Dividing by the number found would give a search full marks for finding one gold passage of four, as long as it came first.
- Some books cut the average at the depth and divide by the smaller of the depth and the number of gold passages. No question here has more than ten gold passages, so the two give the same figure.

## 10.6 Measuring every search

### 10.6.1 Principles

Each search returns its first ten passages for each of the 32 definition questions. The five measures are worked out per question and then averaged, so every question counts the same, whether it has one gold passage or four.

Query expansion (Chapter 5) was only measured inside hybrid search. Here it is also measured on BM25 alone, to separate what the added names do from what fusion with semantic search does.

### 10.6.2 Code

`ragbook/ch10_evaluation.py`, the functions `measure_question`, `measure_search` and `build_searches`

```python
def measure_question(found_ids, gold_ids, places=TOP, depth=DEPTH):
    """
    The five measures for one question, as a dictionary.

    Example:
        measure_question(["a", "x", "b"], ["a", "b"])
        returns {"precision": 0.667, "recall": 1.0, "f1": 0.8, "rr": 1.0, "ap": 0.833}
    """
    precision = precision_at(found_ids, gold_ids, places)
    recall = recall_at(found_ids, gold_ids, places)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
        "rr": reciprocal_rank(found_ids, gold_ids, depth),
        "ap": average_precision(found_ids, gold_ids, depth),
    }
```

```python
def measure_search(rank_function, questions, places=TOP, depth=DEPTH):
    """
    The five measures for every question, and their means over the questions.

    rank_function takes a question's text and returns at least `depth`
    passages. The means of reciprocal rank and average precision are the
    mean reciprocal rank (MRR) and mean average precision (MAP).

    Example:
        means, by_question = measure_search(lambda q: index.rank(q, how_many=10), questions)
        means["ap"]
        returns the MAP
    """
    by_question = {}
    for question in questions:
        found_ids = []
        for passage in rank_function(question["question"])[:depth]:
            found_ids.append(passage["id"])
        by_question[question["id"]] = measure_question(found_ids, question["gold_passages"],
                                                       places, depth)
    means = {}
    for name in ["precision", "recall", "f1", "rr", "ap"]:
        values = [measures[name] for measures in by_question.values()]
        means[name] = sum(values) / len(values)
    return means, by_question
```

```python
def build_searches(use_mode="non-commercial", questions=None, passages=None,
                   embedding_file=EMBEDDING_FILE, score_file=SCORE_FILE):
    """
    Every search from Chapters 3 to 9, as rank functions that return the
    first DEPTH passages. Query expansion appears twice: on BM25 alone, and
    inside hybrid search. Pass earlier questions, corpus and saved files to
    rebuild earlier figures.

    Example:
        searches, questions = build_searches()
        searches["BM25"]("What is GDI?")
        returns ten passages
    """
    if passages is None:
        passages = load_corpus()
    if questions is None:
        questions = load_questions()
    saved = load_embeddings(embedding_file)
    embed_question = saved_question_embedder(questions, saved)
    keyword_index = KeywordIndex(passages)
    semantic_index = SemanticIndex(passages, [saved[passage["id"]] for passage in passages],
                                   embed_question)
    knowledge_graph = KnowledgeGraph(passages)
    hybrid_index = HybridIndex(keyword_index, semantic_index, knowledge_graph)
    filtered = FilteredSearch(passages, saved, embed_question)
    reranked = RerankedSearch(passages, saved, embed_question,
                              saved_scorer(questions, load_scores(score_file)))

    def bm25_expanded(question):
        return keyword_index.rank(expand_question(knowledge_graph, question), "bm25", how_many=DEPTH)

    searches = {
        "BM25": lambda q: keyword_index.rank(q, "bm25", how_many=DEPTH),
        "BM25 + query expansion": bm25_expanded,
        "Semantic search": lambda q: semantic_index.rank(q, how_many=DEPTH),
        "Hybrid search": lambda q: hybrid_index.rank(q, how_many=DEPTH),
        "Hybrid search + query expansion": lambda q: hybrid_index.rank(q, how_many=DEPTH, expand=True),
        "Filtered, " + use_mode: lambda q: filtered.rank(q, use_mode, how_many=DEPTH)[0],
        "Reranked, pool of 10": lambda q: reranked.rank(q, use_mode, pool_size=10, how_many=DEPTH)[0],
    }
    return searches, questions
```

### 10.6.3 Annotations

- `measure_search` returns the means and the measures for each question. The means go in the table; the per-question figures are used in 10.7 and 10.8.
- `build_searches` returns a dictionary of functions, one per search, each taking a question's text. The measuring code does not need to know how each search works.
- `build_searches` takes the questions, the corpus and the saved files as inputs, so the searches can be rebuilt as they were on an earlier date (10.7). Without inputs it uses the current question bank and files.
- `bm25_expanded` expands the question with the knowledge graph and gives the longer text to BM25 alone. Chapter 5's `HybridIndex` does the same for its keyword half, while its semantic half keeps the original question.
- The filtered and reranked searches return the passages and the withheld list (Chapter 8); `[0]` keeps the passages.

### 10.6.4 Results

The five measures, corpus and gold lists of 28 October 2026 with supporting passages counted, non-commercial use for the last two rows. Hits from earlier chapters are shown for comparison.

| Search | Precision at 3 | Recall at 3 | F1 at 3 | MRR | MAP | Hits at 1, 3, 10 |
| --- | --- | --- | --- | --- | --- | --- |
| BM25 (Chapter 3) | 0.41 | 0.72 | 0.50 | 0.87 | 0.76 | 26, 30, 31 |
| BM25 + query expansion | 0.41 | 0.74 | 0.50 | 0.80 | 0.69 | 22, 28, 32 |
| Semantic search (Chapter 4) | 0.43 | 0.74 | 0.52 | 0.76 | 0.65 | 18, 32, 32 |
| Hybrid search (Chapter 5) | 0.42 | 0.74 | 0.51 | 0.90 | 0.76 | 27, 30, 32 |
| Hybrid search + query expansion (Chapter 5) | 0.46 | 0.81 | 0.56 | 0.86 | 0.74 | 24, 31, 32 |
| Filtered (Chapter 8) | 0.45 | 0.79 | 0.55 | 0.87 | 0.73 | 25, 31, 32 |
| Reranked, pool of 10 (Chapter 9) | 0.45 | 0.78 | 0.54 | 0.88 | 0.74 | 26, 30, 32 |
| *Highest possible* | *0.61* | *0.98* |  | *1.00* | *1.00* | *32, 32, 32* |

Filtered search in commercial use scores 0.32, 0.53, 0.38, 0.65 and 0.50. Most of the drop is the filters, not the search: eight questions keep no gold passage in commercial use (Chapter 8), and every withheld gold passage counts as missed (10.2).

### 10.6.5 What the table shows

- **Hybrid search with query expansion finds the most gold passages.** It has the highest precision, recall and F1 at 3. Filtered search, the one the app uses, is close behind on all three.
- **The measures rank the searches differently.** Hybrid search has the highest MRR (0.90) and shares the highest MAP with BM25 (0.76); BM25 has the lowest recall at 3. Semantic search finds more gold in the first three than BM25 but puts it first less often (MRR 0.76). Which search is "best" depends on the measure, so the measure is chosen before the comparison.
- **Query expansion on BM25 alone lowers MRR and MAP.** It leaves precision at 0.41, raises recall by 0.02, and lowers MRR from 0.87 to 0.80 and MAP from 0.76 to 0.69. It costs first place on five questions: q2-06, q2-08, q2-11, q2-17 and q2-25.
- **Inside hybrid search the same expansion raises recall at 3.** Recall at 3 rises from 0.74 to 0.81, but MRR falls from 0.90 to 0.86. Semantic search uses the original question, so the ranking changes less; the added names bring in further gold passages.
- **The reranker lowers recall slightly and raises MRR and MAP** (recall 0.79 to 0.78, MRR 0.87 to 0.88, MAP 0.73 to 0.74), which agrees with Chapter 9: one more first place, one question fewer in the top three.
- **There is room left.** The best precision at 3, 0.46, is three-quarters of the 0.61 cap; the best recall, 0.81, is 0.17 short of the 0.98 cap.

### 10.6.6 Why query expansion lowers MRR and MAP for BM25

Expansion adds the other names of every concept the question names (Chapter 5). When the question's main subject is not its concept, the added names become most of the question's words, so BM25 scores passages about the concept above passages about the subject.

For q2-17, "Why are GDP estimates revised?", the knowledge graph finds GDP and adds "gross domestic product GDP domestic product". The question now has four words about GDP and one about revision, and BM25 ranks passages about GDP first; the first gold passage drops from first to seventh.

q2-11 ("How precise are PPPs?") follows the same pattern: the added names of PPP add more to each passage's score than "precise" does, and the gold passage drops to third. q2-08 ("What is a purchasing power parity?") gains the same names, and ppp23-1.13, a distractor on comparisons before PPPs existed, moves above the gold passage. For q2-06 the added words "export prices relative to import prices" give the ESA passage on real income a higher score than the SNA definition. q2-25 drops to third: its expansion adds 14 words, the names of real GDI and GNI, and passages on GNI move up.

Expansion raises the gold passage where it uses a name the question does not. For q2-21 ("Are remittances part of national income?") it adds "current transfers between households", the words that open the ESA definition esa10-4.129; that passage rises from ninth place to second, and recall at 3 rises from 0.50 to 1.00.

## 10.7 How the figures depend on the gold lists

### 10.7.1 Principles

The gold lists changed twice, and each change was recorded in the code with its date. Running the same searches on each set of lists shows how much a figure depends on the lists rather than on the search.

- **26 October 2026.** Four passages were added to four gold lists, after the reranker put them first (9.6.3); each was already gold for a neighbouring question.
- **27 October 2026.** A first attempt to check the lists used **pooling**: the first three passages of each of the seven searches, 134 not yet gold, were judged. Only 6 were judged gold, and 123 of the 134 were already gold for another question. Pooling cannot offer a passage that no search ranks high, and it lets the searches decide what gets checked. So every passage was then judged against every question instead. q2-03 was reworded, because the corpus did not answer the old question.
- **28 October 2026.** Four judgements were revised (q2-03, q2-12, q2-17, q2-22), and sna25-11.238 was added to the corpus, so q2-03 has a gold passage the edition filter keeps (Chapter 8). Against the lists of 26 October, 12 gold lists changed: 12 passages left them and 3 joined. Three of the four additions of 26 October stayed only as supporting passages.

| Question | Passage added on 26 October | 28 October |
| --- | --- | --- |
| q2-15 | esa10-10.22: chained volumes do not add up | Supporting |
| q2-17 | qna17-10.48: early estimates must be revised | Gold |
| q2-24 | bea-ch2-ndp-gni: the BEA definition of net domestic product | Supporting |
| q2-31 | sna25-16.95: hours worked assume every hour is of the same quality | Supporting |

That gives four sets of lists: before 26 October, 26 October, 28 October with supporting passages (the lists used in 10.6), and 28 October with gold passages only.

### 10.7.2 Code

`ragbook/ch10_evaluation.py`, the constants that record each revision and the files and corpus of 26 October, and the functions `corpus_of_26_october`, `earlier_gold_lists`, `gold_lists_of_26_october` and `gold_only`

```python
ADDED_26_OCTOBER = {
    "q2-15": ["esa10-10.22"],
    "q2-17": ["qna17-10.48"],
    "q2-24": ["bea-ch2-ndp-gni"],
    "q2-31": ["sna25-16.95"],
}
```

```python
ADDED_27_OCTOBER = {
    "q2-01": ["sna25-A4.59"],
    "q2-03": ["sna25-11.238"],
    "q2-27": ["una14-ch2-ppp"],
}
REMOVED_27_OCTOBER = {
    "q2-01": ["sna25-A4.10"],
    "q2-02": ["esa10-8.94"],
    "q2-03": ["sna25-A4.59"],
    "q2-06": ["esa10-10.47"],
    "q2-07": ["sna08-15.187"],
    "q2-08": ["ppp23-1.13"],
    "q2-12": ["ppp23-8.4"],
    "q2-21": ["esa10-2.10"],
    "q2-22": ["cso-gnistar-2"],
    "q2-23": ["cso-gnistar-4"],
    "q2-30": ["esa10-10.22", "wb13-mccarthy-ipd"],
}
# q2-03 was replaced the same day: the corpus did not answer the old question.
# On 28 October one passage was added to the corpus for it, and q2-12's check
# lost a clause no passage supports.
REPLACED_27_OCTOBER = {
    "q2-03": {
        "question": "Is depletion of natural resources a cost of production?",
        "expected": "Not in the 2008 SNA (other changes in volume of assets); yes in the 2025 SNA.",
        "check": "Edition pair: an answer giving only one edition fails.",
    },
    "q2-12": {
        "check": "Scope: must say this is Eurostat-OECD practice; other ICP regions adjust for productivity.",
    },
}
```

```python
EMBEDDING_FILE_26_OCTOBER = EMBEDDING_FILE.with_name("all-MiniLM-L6-v2-26-october.npz")
SCORE_FILE_26_OCTOBER = SCORE_FILE.with_name("ms-marco-MiniLM-L6-v2-26-october.npz")
```

```python
PASSAGES_ADDED_28_OCTOBER = ["sna25-11.238"]


def corpus_of_26_october():
    """The corpus as it was on 26 October 2026: today's, less the passages added since."""
    return [p for p in load_corpus() if p["id"] not in PASSAGES_ADDED_28_OCTOBER]
```

```python
def earlier_gold_lists(questions, added=ADDED_26_OCTOBER, removed=None, replaced=None):
    """
    Copies of the questions as they were before one revision of the gold
    lists: passages it added are taken out, passages it removed are put
    back, and replaced questions get their old wording. The questions passed
    in are not changed.

    Example:
        lists_26 = earlier_gold_lists(load_questions(), ADDED_27_OCTOBER,
                                      REMOVED_27_OCTOBER, REPLACED_27_OCTOBER)
        returns 32 questions; q2-31 has two gold passages instead of one
    """
    removed = removed or {}
    replaced = replaced or {}
    earlier = []
    for question in questions:
        copy = dict(question)
        copy.update(replaced.get(question["id"], {}))
        taken_out = added.get(question["id"], [])
        gold = [p for p in question["gold_passages"] if p not in taken_out]
        for passage_id in removed.get(question["id"], []):
            if passage_id not in gold:
                gold.append(passage_id)
        copy["gold_passages"] = gold
        earlier.append(copy)
    return earlier
```

```python
def gold_lists_of_26_october(questions):
    """The gold lists of 26 October 2026, rebuilt from the current ones."""
    earlier = earlier_gold_lists(questions, ADDED_27_OCTOBER, REMOVED_27_OCTOBER, REPLACED_27_OCTOBER)
    for question in earlier:
        question["supporting_passages"] = []
    return earlier
```

```python
def gold_only(questions):
    """
    Copies of the questions without their supporting passages: only the
    passages that answer each question by themselves count.

    Example:
        gold_only(load_questions())
        returns 32 questions; q2-31 has one gold passage instead of two
    """
    stricter = []
    for question in questions:
        copy = dict(question)
        supporting = question.get("supporting_passages", [])
        copy["gold_passages"] = [p for p in question["gold_passages"] if p not in supporting]
        stricter.append(copy)
    return stricter
```

### 10.7.3 Annotations

- `dict(question)` makes a copy, so the question bank in memory keeps the current lists. A test checks this.
- The changes are written in the code, with the date in the name, rather than read from an old copy of the question bank. The earlier lists can be rebuilt from the current file alone.
- `earlier_gold_lists` undoes one revision: it takes out what the revision added, puts back what it removed, and restores reworded questions. Applied twice, it rebuilds the lists before 26 October.
- The saved embeddings and reranker scores are filed by question and passage, so the reworded q2-03 and the added passage needed new ones. The files of 26 October are kept under dated names, and `build_searches` uses them, with `corpus_of_26_october`, for the earlier lists.

### 10.7.4 Results

MRR, MAP and hits at 1 on the four sets of lists:

| Search | Before 26 Oct | 26 Oct | 28 Oct | 28 Oct, gold only |
| --- | --- | --- | --- | --- |
| BM25 | 0.85, 0.70, 24 | 0.88, 0.73, 26 | 0.87, 0.76, 26 | 0.83, 0.72, 24 |
| BM25 + query expansion | 0.79, 0.67, 22 | 0.81, 0.69, 23 | 0.80, 0.69, 22 | 0.75, 0.65, 20 |
| Semantic search | 0.75, 0.64, 19 | 0.79, 0.66, 20 | 0.76, 0.65, 18 | 0.72, 0.62, 18 |
| Hybrid search | 0.86, 0.70, 25 | 0.90, 0.73, 27 | 0.90, 0.76, 27 | 0.84, 0.72, 25 |
| Hybrid search + query expansion | 0.84, 0.71, 24 | 0.89, 0.74, 26 | 0.86, 0.74, 24 | 0.80, 0.71, 22 |
| Filtered | 0.86, 0.71, 25 | 0.91, 0.74, 27 | 0.87, 0.73, 25 | 0.82, 0.70, 23 |
| Reranked, pool of 10 | 0.83, 0.67, 24 | 0.91, 0.72, 28 | 0.88, 0.74, 26 | 0.79, 0.67, 22 |

At first place the reranker against the filtered search is 24 against 25, then 28 against 27, then 26 against 25, then 22 against 23. Chapter 9's verdict at first place depends on which lists are used.

Average precision for the five questions with supporting passages, with and without them:

| Question | Filtered, with | Filtered, gold only | Reranked, with | Reranked, gold only |
| --- | --- | --- | --- | --- |
| q2-05 | 0.50 | 0.00 | 0.50 | 0.00 |
| q2-15 | 0.76 | 1.00 | 1.00 | 0.33 |
| q2-22 | 1.00 | 0.92 | 1.00 | 0.92 |
| q2-24 | 0.38 | 0.23 | 0.66 | 0.27 |
| q2-31 | 0.83 | 0.33 | 1.00 | 0.50 |

### 10.7.5 What the revisions show

- **MRR falls on the lists of 28 October for every search but hybrid search, which stays at 0.90.** The lists of 26 October credited passages on neighbouring topics; reading each passage against each question removed most of them. MAP rises for BM25, hybrid search and the reranker, which rank the remaining gold passages higher.
- **The reranker's gain comes from supporting passages.** It puts supporting passages first for q2-15 and q2-24. Counting them, it leads the filtered search by one first place; without them, it trails by one.
- **Adding a gold passage can lower a score.** For q2-15 the filtered search has the passage that answers the question first, and the supporting passages lower. Counting them, its average precision falls from 1.00 to 0.76.
- **The order of the searches changes.** On the lists of 26 October the filtered and reranked searches had the highest MRR; on those of 28 October hybrid search has. Semantic search is last by MAP on all four sets.
- **Small differences are not findings.** A change of 0.03 in MAP from a few passages on 32 questions is the same size as most of the gaps between searches in 10.6.

### 10.7.6 Making gold lists that do not favour one search

1. **Write the lists before measuring.** The 26 October revision was made after measuring and is recorded as such here.
2. **Judge every passage against every question, when the corpus allows.** At 57 passages that is one reading of each passage. Large test collections such as TREC cannot do this and use pooling instead; the pool here showed its limit, as most of what it offered was already gold for another question.
3. **Record each change with its date and rule.** `ADDED_26_OCTOBER` and the records of 27 and 28 October keep every earlier set of lists recoverable, so all four sets of figures can be shown, as here.

## 10.8 Is one search better than another?

### 10.8.1 Principles

A MAP 0.01 higher can come from one question much better, or ten slightly better and nine slightly worse. So two searches are also compared question by question: on how many questions is A better, worse, or the same?

The **sign test** asks whether such a split could be chance. Suppose the two searches were equally good: each question where they differ would then be like a coin toss. The test gives the chance of a split at least as uneven as the one seen; a small chance, such as 0.05 or below, suggests a real difference.

With 32 questions the test can only detect large differences. If 16 questions differ, one search must score higher on 13 and lower on 3 before the chance falls below 0.05; at 12 to 4 it is 0.08.

### 10.8.2 Code

`ragbook/ch10_evaluation.py`, the functions `compare_by_question` and `sign_test`

```python
def compare_by_question(by_question_a, by_question_b, measure="ap"):
    """
    The questions on which search A scores higher than search B on one
    measure, the questions on which it scores lower, and the number of ties.

    Example:
        better, worse, ties = compare_by_question(a, b, "rr")
        returns two lists of question ids and a count
    """
    better = []
    worse = []
    ties = 0
    for question_id in by_question_a:
        a = by_question_a[question_id][measure]
        b = by_question_b[question_id][measure]
        if math.isclose(a, b):
            ties = ties + 1
        elif a > b:
            better.append(question_id)
        else:
            worse.append(question_id)
    return better, worse, ties
```

```python
def sign_test(better, worse):
    """
    The chance of a split at least this uneven if each search were equally
    likely to score higher on each question that is not a tie (two-sided
    sign test).

    Example:
        sign_test(8, 1)
        returns 0.039: a split of 8 to 1 happens about 4 times in 100 by chance
        sign_test(3, 2)
        returns 1.0
    """
    differ = better + worse
    if differ == 0:
        return 1.0
    fewer = min(better, worse)
    one_side = 0
    for higher in range(fewer + 1):
        one_side = one_side + math.comb(differ, higher)
    return min(1.0, 2 * one_side / 2 ** differ)
```

### 10.8.3 Annotations

- `math.isclose` treats two scores as equal if they differ only in the last digits of the computer's arithmetic, so a tie is not counted as a higher score.
- Ties are left out of the test: they say nothing about which search is better.
- `math.comb(differ, higher)` is the number of ways to choose `higher` questions out of `differ`. Adding these from 0 up to the smaller count, and dividing by 2 to the power `differ`, gives the chance of a split that uneven in one direction; doubling covers either direction.
- The test counts the questions on which each search scores higher, not by how much, so one large gain counts the same as one small one.

### 10.8.4 Results

Average precision, question by question, corpus and gold lists of 28 October:

| Comparison | A better | A worse | Same | Sign test |
| --- | --- | --- | --- | --- |
| BM25 + query expansion against BM25 | 8 | 10 | 14 | 0.81 |
| Hybrid search against BM25 | 8 | 6 | 18 | 0.79 |
| Hybrid search + query expansion against hybrid search | 8 | 9 | 15 | 1.00 |
| Reranked, pool of 10, against filtered | 8 | 7 | 17 | 1.00 |

No comparison is clear. Each pair of searches differs on about half the questions, and on those each search scores higher on close to half.

The means in 10.6 still describe these 32 questions correctly. What 32 questions cannot show is that one search would be better on new questions; the decisions in Chapters 5, 8 and 9 depend on what the searches do, and on cost, as much as on these figures.

## 10.9 Tests, glossary and links

### 10.9.1 Tests

The file `tests/test_ch10_evaluation.py` has 20 tests. None needs a model. Run them with `python -m pytest tests/test_ch10_evaluation.py -v`.

| Test | What it proves |
| --- | --- |
| Precision and recall | Hand-worked values on short lists of letters |
| Recall cap | With four gold passages, recall at 3 stops at 0.75 |
| F1 | Hand-worked values; 0 when both inputs are 0 |
| Reciprocal rank | 1, 0.5, and 0 when the gold passage is past the depth |
| Average precision | Hand-worked values, including gold passages not found |
| Order | Order changes average precision, not precision at 3 |
| Range | Every measure stays between 0 and 1 |
| Sign test | Hand-worked chances, including 8 to 1 and no games |
| Ties | Equal scores are counted as ties, not as higher scores |
| Earlier gold lists | Rebuilt without changing the question bank |
| Revision of 27 October | Rebuilds the lists of 26 October, including the old q2-03; 71, 62 and 56 gold passages |
| MRR and hits at 1 | Questions with reciprocal rank 1 = Chapter 5's hits at 1, for every search |
| Recall and hits at 3 | Questions with recall above 0 = hits at 3, for every search |
| Results, 28 October | The table in 10.6.4 |
| Results, gold only | The last column of 10.7.4 |
| Results, 26 October | The 26 October column of 10.7.4 |
| Results, before 26 October | The first column of 10.7.4 |
| Commercial use | 0.32, 0.53, 0.38, 0.65, 0.50 |
| Query expansion on BM25 | First place lost on q2-06, q2-08, q2-11, q2-17, q2-25; 8 better, 10 worse, 14 the same |
| No clear comparison | The four splits of 10.8.4 and their sign tests, each above 0.05 |

The first eleven tests check the code on hand-worked cases and the gold-list records. The two hit tests tie this chapter to Chapter 5's counts; the last seven check the results.

### 10.9.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Gold list | The gold passages of one question |
| Supporting passage | A passage that carries part of a question's expected answer but does not answer the question by itself; counted in the gold list and named separately |
| Distractor | A corpus passage that is gold for no question |
| Precision at 3 | The share of the first three passages returned that are gold |
| Recall at 3 | The share of a question's gold passages found in the first three places |
| F1 | The harmonic mean of precision and recall: 2 × precision × recall ÷ (precision + recall) |
| Reciprocal rank | 1 divided by the place of the first gold passage; 0 if none is in the first ten |
| Mean reciprocal rank (MRR) | The mean of the reciprocal ranks over the questions |
| Average precision | The precision at each gold passage found, added up and divided by the number of gold passages |
| Mean average precision (MAP) | The mean of the average precisions over the questions |
| Sign test | A test of whether the split of questions on which each of two searches scores higher could be chance |
| Pooling | Judging the top passages of several searches together, so no search's choices are checked more than another's |

"Recall (of a near-neighbour search)" in Appendix C, from Chapter 7, is a different measure. The twelve rows are also in Appendix C.

### 10.9.3 Links

- [Manning, Raghavan and Schütze, *Introduction to Information Retrieval*, "Evaluation of ranked retrieval results"](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)
- [TREC: relevance judgements, made by pooling](https://trec.nist.gov/data/reljudge_eng.html)
- [Python `math.comb` and `math.isclose`](https://docs.python.org/3/library/math.html)
- [Chapter 10 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch10_evaluation.py)
