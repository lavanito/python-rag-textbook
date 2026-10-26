# Chapter 9 — Reranking

## 9.1 What this chapter builds

**Reranking** is a second, slower look at a short list. The first stage, Chapter 8's filtered hybrid search, ranks every passage quickly and passes a **pool** of the best few to a **reranker**, which reads the question and each passage together and sorts the pool again.

1. **Two stages** (9.2): why a quick first stage and a slower second stage are combined, and why the pool sets a limit the reranker cannot pass.
2. **The cross-encoder** (9.3): the model that reads a question and a passage as one text and returns one score.
3. **Saving the scores** (9.4): the model scores every pair of definition question and passage once, on the laptop; the chapter and the tests read the saved file.
4. **Reranking the pool** (9.5): sort the pool by score; equal scores keep their first-stage order.
5. **Measuring** (9.6): hits at 1, 3 and 10 on the 32 definition questions, against Chapter 8's 25, 30 and 32, for pools of 5, 10 and 20.
6. **What it costs** (9.7): time per pair on the target laptop, and per question for each pool size.
7. **Late interaction** (9.8): ColBERT, a third design between the two, described but not built.

**Code file:** `ragbook/ch09_reranking.py`

**Uses:** sentence-transformers 6.1.0 (Chapter 4) and its `CrossEncoder` class; Python's `sys` and `time` modules. From earlier chapters: `load_corpus` (Chapter 2), `load_questions` (Chapter 3), `load_embeddings` (Chapter 4), `hits_at` and `saved_question_embedder` (Chapter 5), `FilteredSearch` (Chapter 8).

## 9.2 Two stages: a pool, then a closer look

### 9.2.1 Principles

Chapter 4's embedding model turns the question and each passage into an embedding **separately**. The passage embeddings are worked out once and saved, so a search compares one new embedding with 56 saved ones. That is quick, but the model never sees the question and the passage at the same time: a passage that mentions every word of the question, in the wrong relation, can score as high as one that answers it.

A **cross-encoder** reads the question and one passage as a single text and returns one number: how well the passage answers the question. Each word of the question can be compared with each word of the passage, so word order and relations count. Nothing can be worked out in advance, because every score needs the question. Scoring every passage for every question grows with the collection: a million passages means a million runs of the model for each question.

The two are combined:

1. **First stage:** Chapter 8's filtered hybrid search ranks every passage the filters allow and keeps the best few, the **pool**.
2. **Second stage:** the cross-encoder scores each passage in the pool against the question, and the pool is sorted by that score.

The reranker only reorders the pool. A gold passage the first stage left outside the pool cannot be found, so the number of questions with a gold passage somewhere in the pool is the most the reranker can reach (the **ceiling**). A larger pool raises the ceiling and costs more time (9.7). The reranker also cannot see a passage the filters withheld, because withheld passages never enter the pool.

## 9.3 The cross-encoder

### 9.3.1 Principles

The model is `cross-encoder/ms-marco-MiniLM-L6-v2`:

| Property | Value |
| --- | --- |
| Size | About 23 million parameters (all-MiniLM-L6-v2 in Chapter 4 has about the same) |
| Input limit | 512 word pieces for the question and passage together; the longest corpus passage, 180 words, fits |
| Output | One number per pair; larger means more relevant |
| Trained on | MS MARCO: English web-search questions paired with web passages a person judged relevant |
| Licence | Apache 2.0 (the model) |

Two points about the training data matter here.

- **Subject.** MS MARCO questions are web searches, not national accounts. The model was not trained on manuals like the SNA, so whether it helps is measured, not assumed (9.6).
- **Terms.** Microsoft states that the MS MARCO data is for non-commercial research. The model's own licence is Apache 2.0. This book is non-commercial; anyone using the reranker commercially checks whether the training data's terms affect them. That is a note, not legal advice.

The model's raw output is kept: any number, positive or negative. sentence-transformers can turn it into a number between 0 and 1; that does not change the order, so the chapter does not use it.

### 9.3.2 Code

`ragbook/ch09_reranking.py`, the functions `load_reranker` and `model_scorer`

```python
RERANKER_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"
SCORE_FILE = Path(__file__).parent.parent / "data" / "reranker" / "ms-marco-MiniLM-L6-v2.npz"
```

```python
def load_reranker(model_name=RERANKER_NAME):
    """
    Load the cross-encoder on the computer's main processor (CPU).

    The first call downloads the model from Hugging Face and keeps a copy;
    later calls use the copy and need no internet connection.

    Example:
        reranker = load_reranker()
    """
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device="cpu")
```

```python
def model_scorer(reranker):
    """
    A function that scores a list of passages against one question with the
    model.

    Each score is the model's raw output for the pair: any number, positive
    or negative; the larger, the more relevant the model judges the passage.
    Only the order of the scores matters.

    Example:
        score_passages = model_scorer(load_reranker())
        score_passages("What is GDP?", passages[:2])
        returns two numbers, one per passage
    """
    import torch

    def score_passages(question, passages):
        pairs = []
        for passage in passages:
            pairs.append((question, passage["text"]))
        scores = reranker.predict(pairs, activation_fn=torch.nn.Identity(),
                                  show_progress_bar=False)
        return [float(score) for score in scores]

    return score_passages
```

### 9.3.3 Annotations

- `CrossEncoder` is imported inside `load_reranker`, so the rest of the file runs without sentence-transformers or the model, as in Chapter 4.
- `model_scorer` returns a function. The search code calls that function and does not know whether it runs the model or reads saved scores (9.4). Chapter 5's `saved_question_embedder` does the same for embeddings.
- `activation_fn=torch.nn.Identity()` asks for the raw output, unchanged.
- One call to `predict` scores the whole list of pairs, which is quicker than one call per pair.

## 9.4 Saving the scores, so the model runs once

### 9.4.1 Principles

Each score depends on both the question and the passage, so the model is run on every pair of the 32 definition questions and the 56 passages: 1,792 pairs. The scores are saved in one numpy file with the ids of its rows and columns, the model name and the time the scoring took. The laptop ran the model once; the rest of the chapter and the tests read the file and need no model and no internet.

Saving every pair, not just each first-stage pool, means the pool size can change without running the model again.

### 9.4.2 Code

`ragbook/ch09_reranking.py`, the functions `score_everything`, `save_scores`, `load_scores`, `scoring_time` and `saved_scorer`

```python
def score_everything(score_passages, questions, passages):
    """
    Score every pair of question and passage, and time the work.

    Returns a table of scores (one row per question, one column per passage)
    and the seconds taken.

    Example:
        scores, seconds = score_everything(score_passages, questions, passages)
        scores.shape
        returns (32, 56)
    """
    rows = []
    start = time.perf_counter()
    for question in questions:
        rows.append(score_passages(question["question"], passages))
    seconds = time.perf_counter() - start
    return np.array(rows, dtype=np.float32), seconds
```

```python
def save_scores(file_path, question_ids, passage_ids, scores, seconds, model_name=RERANKER_NAME):
    """
    Save the table of scores, the ids of its rows and columns, the model name
    and the seconds the scoring took, in one numpy file.

    Example:
        save_scores(SCORE_FILE, ["q2-01"], ["sna08-2.144"], [[3.2]], 0.05)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(file_path, question_ids=np.array(question_ids), passage_ids=np.array(passage_ids),
             scores=np.asarray(scores, dtype=np.float32), seconds=np.array(seconds),
             model_name=np.array(model_name))
```

```python
def load_scores(file_path=SCORE_FILE):
    """
    Read saved scores back as a dictionary: question id -> passage id -> score.

    Example:
        load_scores()["q2-01"]["sna08-2.144"]
        returns one number
    """
    saved = np.load(file_path)
    scores = {}
    for question_id, row in zip(saved["question_ids"], saved["scores"]):
        scores[str(question_id)] = {}
        for passage_id, score in zip(saved["passage_ids"], row):
            scores[str(question_id)][str(passage_id)] = float(score)
    return scores
```

```python
def scoring_time(file_path=SCORE_FILE):
    """
    The seconds the saved scoring took, and the number of pairs scored.

    Example:
        seconds, pairs = scoring_time(SCORE_FILE)
    """
    saved = np.load(file_path)
    return float(saved["seconds"]), int(saved["scores"].size)
```

```python
def saved_scorer(questions, scores):
    """
    A function that returns a bank question's saved scores, so the chapter
    runs without the model. Questions outside the bank are refused.

    Example:
        score_passages = saved_scorer(load_questions(), load_scores())
        score_passages("What is consumption of fixed capital?", passages[:2])
        returns the two saved scores
    """
    ids_by_text = {}
    for question in questions:
        ids_by_text[question["question"]] = question["id"]

    def score_passages(question, passages):
        if question not in ids_by_text:
            raise KeyError(f"No saved scores for: {question} (load the model as in 9.3)")
        row = scores[ids_by_text[question]]
        found = []
        for passage in passages:
            found.append(row[passage["id"]])
        return found

    return score_passages
```

### 9.4.3 Annotations

- `score_everything` times the whole run with `time.perf_counter`, Python's clock for measuring short intervals. The time is saved with the scores and used in 9.7.
- The saved table has one row per question and one column per passage. `load_scores` turns it into a dictionary of dictionaries, so a score is found by two ids: `scores["q2-01"]["sna08-2.144"]`.
- `saved_scorer` refuses a question that is not in the bank, rather than guessing. A new question needs the model.

## 9.5 Reranking the pool

### 9.5.1 Principles

The reranker sorts the pool by score, highest first. Two passages with the same score keep the order the first stage gave them, so the result never depends on chance.

### 9.5.2 Code

`ragbook/ch09_reranking.py`, the function `rerank` and the class `RerankedSearch`

```python
def rerank(question, pool, score_passages, how_many=3):
    """
    Sort a pool of passages by the reranker's score, highest first, and keep
    the first `how_many`.

    Passages with equal scores keep their order in the pool.

    Example:
        scores = {"a": 0.1, "b": 2.0, "c": 0.5}
        rerank("q", [{"id": "a"}, {"id": "b"}, {"id": "c"}],
               lambda q, ps: [scores[p["id"]] for p in ps])
        returns the passages in the order b, c, a
    """
    scores = score_passages(question, pool)
    pairs = []
    for place, (passage, score) in enumerate(zip(pool, scores)):
        pairs.append((-score, place, passage))
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    reranked = []
    for negative_score, place, passage in pairs[:how_many]:
        reranked.append(passage)
    return reranked
```

```python
class RerankedSearch:
    """
    Chapter 8's filtered hybrid search, then the reranker on its pool.

    pool_size is how many passages the first stage passes to the reranker.
    The reranker can only reorder the pool: a gold passage outside it cannot
    be found.

    Example:
        search = RerankedSearch(load_corpus(), load_embeddings(), embed_question, score_passages)
        results, withheld = search.rank("What is consumption of fixed capital?", "non-commercial")
    """

    def __init__(self, passages, saved, embed_question, score_passages):
        self.first_stage = FilteredSearch(passages, saved, embed_question)
        self.score_passages = score_passages

    def rank(self, question, use_mode, pool_size=10, how_many=3):
        pool, withheld = self.first_stage.rank(question, use_mode, how_many=pool_size)
        return rerank(question, pool, self.score_passages, how_many=how_many), withheld
```

### 9.5.3 Annotations

- `rerank` builds a list of triples: the score with its sign reversed, the place in the pool, and the passage. Sorting the triples puts the highest score first; for equal scores, the earlier place wins.
- `RerankedSearch` holds a Chapter 8 `FilteredSearch` as its first stage, so the licence and edition filters run before the reranker sees anything.
- `pool_size` sets how many passages the first stage passes on; `how_many` sets how many the reranker returns.

### 9.5.4 An example

q2-01, "What is consumption of fixed capital?", has two gold passages: esa10-3.139 and sna25-A4.10. The first stage's pool of 10, with the reranker's scores:

| Passage | First-stage place | Reranker score | Reranked place | Gold |
| --- | --- | --- | --- | --- |
| esa10-3.139 | 1 | 10.03 | 1 | Yes |
| sna25-A4.10 | 2 | 2.88 | 3 | Yes |
| sna25-A4.59 | 3 | 4.36 | 2 |  |
| esa10-10.47 | 4 | −5.60 | 6 |  |
| esa10-10.33 | 5 | 0.27 | 4 |  |
| bea-ch2-ndp-gni | 6 | −7.59 | 8 |  |
| esa10-8.94 | 7 | −1.77 | 5 |  |
| cso-gnistar-3 | 8 | −11.18 | 10 |  |
| esa10-8.89 | 9 | −6.93 | 7 |  |
| bea-ch4-chained | 10 | −10.29 | 9 |  |

The reranker agrees on the first passage and gives it a score far above the rest. It moves sna25-A4.59, on depletion of natural resources, above the second gold passage. The scores run from 10.03 to −11.18; only their order is used.

## 9.6 Measuring

### 9.6.1 Results

On this corpus the reranker does not improve on the first stage. It puts a gold passage first for 24 of the 32 definition questions, against 25 without it, and leaves the top three and top ten about where they were.

Hits at 1, 3 and 10, non-commercial use:

| Search | First place | Top three | Top ten | Ceiling |
| --- | --- | --- | --- | --- |
| First stage only (Chapter 8) | 25 | 30 | 32 |  |
| Reranked, pool of 5 | 24 | 30 | 31 | 31 |
| Reranked, pool of 10 | 24 | 29 | 32 | 32 |
| Reranked, pool of 20 | 24 | 30 | 32 | 32 |

A pool of 5 can hold at most 5 passages, so its top ten is its ceiling: 31. From a pool of 10, every question has a gold passage in the pool. The pool is therefore not what holds the reranker back; its scores are.

### 9.6.2 What changed

With a pool of 10, the reranker changes the first passage for three questions:

- **Gained, q2-30** ("Why can real GDP growth and comparisons at PPP tell different stories about two economies?"): McCarthy's passage on comparisons across countries and across time (wb13-mccarthy-space-time) moves from fourth to first.
- **Lost, q2-15** ("Should annual price and volume indices be chained?"): esa10-10.22, on the drawback of chained indices, moves from fifth to first, above both gold passages (esa10-10.20, first before reranking, and bea-ch4-fisher).
- **Lost, q2-25** ("What is real gross domestic income, and how does it lead to real national income?"): esa10-8.94, the definition of national income, moves above the gold passage esa10-10.47, which explains how the terms of trade affect real income.

The top three changes for three questions, one fewer in all. q2-04 and q2-29 lose their gold passage from it; for q2-29, ppp23-ov.13, eighth before reranking, moves above the gold passage ppp23-ov.12. q2-24 gains one: sna25-A4.10 moves from fourth to third.

### 9.6.3 Why

- **The first stage is already strong.** It misses first place on 7 questions and the top three on 2, so there is little to gain.
- **The model learned from web searches.** It appears to reward a passage that shares the question's terms and reads like an answer. Several passages in the corpus do both without being the definition the question asks for, such as esa10-8.94 for q2-25.
- **Some of its first choices are defensible.** esa10-10.22 states the case against chaining, which a full answer to q2-15 needs, but it is not in q2-15's gold list. A count can only be as good as the gold lists; Chapter 10 measures how much that matters.

The reranker is measured, not assumed to help. On 56 short passages with a strong first stage it adds time (9.7) and no hits.

### 9.6.4 When rerankers do not help

A reranker pays off when a crude first stage leaves the right passage low in a pool, and the reranker's training matches the questions. Most of the conditions that prevent this hold for the corpus in this book.

| Condition | Why the reranker cannot help | In this chapter |
| --- | --- | --- |
| The first stage is near the ceiling | The reranker can only reorder; if the right passage is already first, it can only lose | Holds: the first stage misses first place on 7 of 32 questions |
| The pool lacks the gold passage | No reordering finds a passage outside the pool | Holds for a pool of 5 (ceiling 31); not for 10 or 20 |
| The model was trained on other text | It learned what relevant means from web searches, not from statistical manuals | Holds: MS MARCO; esa10-8.94 beat the gold passage for q2-25 |
| The candidates are close | Several passages on one concept, in similar words, get scores a small margin apart | Likely: SNA, ESA 2010 and BEA passages cover the same concepts |
| The gold lists are incomplete | A correct passage that is not listed counts as a miss | Holds: esa10-10.22 for q2-15 |
| The answer needs several passages | The reranker scores each passage alone; it cannot see that two together answer the question | Likely for comparisons: q2-04 ("What is the difference between GDP and GNI?") lost its top-three place |
| Passages are cut or too long | Text past the input limit is dropped before scoring | Does not hold: the longest passage, 180 words, fits |
| The question is short or vague | Few words give the model little to compare | Not tested: definition questions are specific |
| The collection is small | A small collection lets the first stage use careful methods, leaving little for a second stage | Holds: 56 passages, searched with BM25, embeddings, fusion and query expansion |

A reranker would be worth measuring again with a model trained on statistical text, with a larger collection searched by a cruder first stage, or after the gold lists are reviewed (Chapter 10).

**Decision (Lavan, 26 October 2026):** the demonstrator app shows the first-stage ranking. The reranker stays in the book as a measured step that did not pay off on this corpus.

## 9.7 What it costs

On the target laptop (Intel Core i7-6820HQ, processor only) the model scored 1,792 pairs in 60.8 seconds: 34 milliseconds a pair. The time excludes loading the model and the one-off download of about 90 MB.

| Pool | Pairs per question | Reranker time per question |
| --- | --- | --- |
| 5 | 5 | 0.17 s |
| 10 | 10 | 0.34 s |
| 20 | 20 | 0.68 s |

The first stage, at 56 passages, takes a few milliseconds (Chapter 8), so the reranker is most of the time a search takes. The time grows with the pool, not the collection.

Scoring every passage instead, as 9.2 explains, grows with the collection: at 34 milliseconds a pair, a million passages would take about 9.4 hours for one question. That is why the reranker sees only the pool.

## 9.8 Late interaction: ColBERT

### 9.8.1 Principles

The embedding model and the cross-encoder are two ends of a range.

| Design | What is worked out in advance | What a search does | Speed and quality |
| --- | --- | --- | --- |
| Embedding model (Chapter 4) | One embedding per passage | Compares one question embedding with each saved one | Fastest; question and passage never meet |
| ColBERT | One embedding per word piece of each passage | Compares each word piece of the question with each word piece of the passage | Between the two |
| Cross-encoder (this chapter) | Nothing | Runs the model on each pair | Slowest; reads the pair as one text |

**ColBERT** keeps an embedding for every word piece of every passage. For each word piece of the question it finds the closest word piece in the passage, and adds up those best matches. The comparison of single words happens at search time, after the model has run: hence the name **late interaction**. The passage side is still worked out in advance, so ColBERT can search a large collection directly, and it keeps word-level matches that one embedding for the whole passage loses.

The cost is storage: a passage of 100 word pieces needs 100 embeddings instead of one. The book does not build it; at 56 passages the cross-encoder on a pool is quick enough.

## 9.9 Tests, glossary and links

### 9.9.1 Tests

The file `tests/test_ch09_reranking.py` holds 15 tests. None needs the model. Run them with `python -m pytest tests/test_ch09_reranking.py -v`.

| Test | What it proves |
| --- | --- |
| Sorting | The pool is sorted by score, highest first |
| Equal scores | Passages with equal scores keep their pool order |
| Negative scores | Negative scores sort correctly; `how_many` cuts the list |
| Scoring everything | One row of scores per question, one column per passage |
| Saved scores | Scores and timing round-trip through the file exactly |
| Unknown question | A question outside the bank is refused |
| Pool and filters | Reranked results are the pool, reordered; nothing withheld appears, in both use modes |
| Ceiling | Hits at the pool's depth are the same before and after reranking |
| First places | Questions gained and lost at first place are listed correctly |
| Saved file | Covers every definition question and every passage |
| Results | First stage 25, 30, 32; reranked 24, 30, 31 (pool of 5), 24, 29, 32 (10) and 24, 30, 32 (20) |
| Gained and lost | Pool of 10: q2-30 gained first place; q2-15 and q2-25 lost it |
| Pool of ten | Holds a gold passage for all 32 questions |
| Timing | The saved time covers 1,792 pairs |
| Top three | Pool of 10: q2-04 and q2-29 leave the top three; q2-24 enters it |

The pool and ceiling tests use a stand-in score file built from the saved embeddings, so they check the code, not the model. The last five hold the results of 9.6 and 9.7.

### 9.9.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Reranking | Sorting a short list from a first search again, with a slower and more careful scorer |
| Pool | The passages the first stage passes to the reranker |
| Reranker | The model or rule that sorts the pool again |
| Cross-encoder | A model that reads a question and a passage as one text and returns one relevance score |
| Ceiling | The number of questions with a gold passage somewhere in the pool: the most a reranker can reach |
| MS MARCO | A Microsoft collection of web-search questions and passages judged relevant, used to train rerankers |
| ColBERT | A search model that keeps one embedding per word piece and matches word pieces at search time |
| Late interaction | Comparing question and passage word by word after the model has run, as ColBERT does |

### 9.9.3 Links

- [MS MARCO: terms of use](https://microsoft.github.io/msmarco/Notice)
- [sentence-transformers: CrossEncoder](https://sbert.net/docs/package_reference/cross_encoder/model.html)
- [Model card: cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)
- [Khattab and Zaharia (2020), "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"](https://arxiv.org/abs/2004.12832)
- [Nogueira and Cho (2019), "Passage Re-ranking with BERT"](https://arxiv.org/abs/1901.04085)
- [Python `time` module](https://docs.python.org/3/library/time.html)
- [Chapter 9 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch09_reranking.py)
