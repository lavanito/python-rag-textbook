# Chapter 8 — Filters, metadata and access rules

## 8.1 What this chapter builds

A **filter** decides which passages a question may use, before any search. A passage the filter withholds never enters a ranking, so it never reaches the model.

1. **The licence filter** (8.2): a **use mode** keeps only the licence classes it allows. Commercial use keeps 41 of the 56 passages.
2. **The edition filter** (8.3): a question gets the SNA edition it names, or the latest edition on each topic when it names none.
3. **Both filters and the log** (8.4): every withheld passage is written to a log with the reason.
4. **Searching only what passes** (8.5): hit counts in each use mode. Five questions lose every gold passage in commercial use.
5. **The same filters in Chroma** (8.6): conditions on metadata give the same top three as exact search on all 32 definition questions, in both use modes.

Until this chapter one passage, esa10-10.20, carried the label `access: subscriber`. The label stood for a rule no publisher set. The licence class is a real term of use, recorded for every passage, so the filter reads it instead. The label and the `access` field that held it are gone, so no field other than the licence class can be read as a term of use.

**Code file:** `ragbook/ch08_filters.py`

**Uses:** chromadb 1.5.9 (Chapter 7); Python's `json` and `datetime` modules. From earlier chapters: `load_corpus` (Chapter 2), `KeywordIndex` and `load_questions` (Chapter 3), `SemanticIndex` and `load_embeddings` (Chapter 4), `HybridIndex`, `KnowledgeGraph`, `hits_at` and `saved_question_embedder` (Chapter 5), `open_store` and `store_passages` (Chapter 7).

## 8.2 The licence filter

### 8.2.1 Principles

Each source sets its own terms for reuse. The corpus records them as one of three **licence classes**, in the field `licence_class` (`data/corpus/SOURCES.md` gives each source's terms and where they were read).

| Licence class | Meaning | Sources | Passages |
| --- | --- | --- | --- |
| open | Reuse allowed with attribution, commercial use included | ESA10, BEA, CSO, PPP23, ONS, WB13 | 41 |
| non-commercial | Reuse allowed for non-commercial teaching and research only | QNA17 | 5 |
| quotation only | No licence; short quotation with full citation only | SNA08, SNA25, UNA14 | 10 |

A use mode states how the answers will be used. The book has two:

- **non-commercial** (this book and its demonstrator): all three classes.
- **commercial**: open passages only.

The book uses quotation-only passages in non-commercial use only. That is a choice for this book, not legal advice; anyone reusing the code for another purpose checks each source's terms.

### 8.2.2 Code

`ragbook/ch08_filters.py`, `USE_MODES` and the function `licence_filter`

```python
# Which licence classes each use mode may send to the model.
USE_MODES = {
    "non-commercial": ["open", "non-commercial", "quotation only"],
    "commercial": ["open"],
}


def licence_filter(passages, use_mode):
    """
    Keep the passages whose licence class the use mode allows.

    Returns two lists: the passages kept, and one record for each passage
    withheld, giving its id and the reason.

    Example:
        kept, withheld = licence_filter(load_corpus(), "commercial")
        len(kept), len(withheld)
        returns (41, 15)
    """
    allowed = USE_MODES[use_mode]
    kept = []
    withheld = []
    for passage in passages:
        if passage["licence_class"] in allowed:
            kept.append(passage)
        else:
            reason = f"licence: '{passage['licence_class']}' is not allowed in {use_mode} use"
            withheld.append({"id": passage["id"], "filter": "licence", "reason": reason})
    return kept, withheld
```

### 8.2.3 Annotations

- `USE_MODES` maps each use mode to the licence classes it allows. A new use mode is one more line.
- Each withheld passage gets a record of three fields: `id`, `filter` and `reason`. The reason is written for a person reading the log (8.4).
- Commercial use keeps 41 passages and withholds 15: five from QNA17 and ten quotation-only passages.

## 8.3 The edition filter

### 8.3.1 Principles

The corpus holds two editions of the SNA: the 2008 SNA (3 passages) and the 2025 SNA (5). They differ. The 2025 SNA calls consumption of fixed capital "depreciation", and deducts depletion of natural resources as well when moving from GNI to net national income (q2-02). An answer that mixes the two editions without saying so is wrong for one of them.

The rule:

1. If the question names an edition, only that edition's SNA passages are kept.
2. If it names none, the latest edition is used. A passage from an older edition is withheld only when the newer edition has a passage on the same topic (the field `topic`).
3. Passages from other sources are never touched. ESA 2010 follows the 2008 SNA closely, but it is a separate standard and its passages carry their own scope note.

Rule 2 applied to the three 2008 SNA passages:

| 2008 SNA passage | Topic | 2025 SNA passage on the same topic | Result |
| --- | --- | --- | --- |
| sna08-2.144 | Net national income | sna25-3.145 | Withheld |
| sna08-12.26 | Depletion of natural resources | sna25-A4.59 | Withheld |
| sna08-15.187 | Real income and the terms of trade | None | Kept |

Withholding every 2008 passage would remove 15.187, the only SNA passage on the terms of trade and the trading gain (gold for q2-06, q2-07 and q2-30).

The filter recognises "2008 SNA", "SNA 2008", "2025 SNA" and "SNA 2025", in any mix of capitals. It does not recognise "the previous SNA" or "SNA08".

q2-02 and q2-03 ask about the difference between the editions but name neither. Rule 2 withholds the 2008 passage, so they are answered from the 2025 SNA alone (decision, 25 Oct 2026). A reader who wants the comparison names both editions in the question.

### 8.3.2 Code

`ragbook/ch08_filters.py`, `EDITIONS`, `EDITION_NAMES` and the functions `editions_named` and `edition_filter`

```python
# Editions of one standard, oldest first, and the names a question may use.
EDITIONS = ["SNA08", "SNA25"]
EDITION_NAMES = {
    "SNA08": ["2008 SNA", "SNA 2008"],
    "SNA25": ["2025 SNA", "SNA 2025"],
}


def editions_named(question):
    """
    The editions a question names, as source codes, oldest first.

    Example:
        editions_named("What did the 2008 SNA call depreciation?")
        returns ["SNA08"]
    """
    named = []
    for code in EDITIONS:
        for name in EDITION_NAMES[code]:
            if name.lower() in question.lower():
                named.append(code)
                break
    return named


def edition_filter(passages, question):
    """
    Keep the edition of the SNA that the question asks for.

    If the question names one or more editions, passages from the other
    editions are withheld. If it names none, a passage from an older edition
    is withheld only when a newer edition has a passage on the same topic;
    an older passage with no newer counterpart stays. Passages from other
    sources are never touched.

    Example:
        kept, withheld = edition_filter(load_corpus(), "What is net national income?")
        [record["id"] for record in withheld]
        returns ["sna08-2.144", "sna08-12.26"]
    """
    named = editions_named(question)
    newest_topics = {}
    for passage in passages:
        if passage["source_code"] in EDITIONS:
            position = EDITIONS.index(passage["source_code"])
            if position > newest_topics.get(passage["topic"], -1):
                newest_topics[passage["topic"]] = position
    kept = []
    withheld = []
    for passage in passages:
        code = passage["source_code"]
        reason = ""
        if code in EDITIONS and named and code not in named:
            reason = f"edition: the question asks for the {' and '.join(EDITION_NAMES[c][0] for c in named)}"
        elif code in EDITIONS and not named and EDITIONS.index(code) < newest_topics[passage["topic"]]:
            newer = EDITION_NAMES[EDITIONS[newest_topics[passage["topic"]]]][0]
            reason = f"edition: the {newer} has a passage on '{passage['topic']}'"
        if reason:
            withheld.append({"id": passage["id"], "filter": "edition", "reason": reason})
        else:
            kept.append(passage)
    return kept, withheld
```

### 8.3.3 Annotations

- `EDITIONS` lists the editions oldest first, so a passage's position in the list says how new its edition is.
- `newest_topics` maps each SNA topic to the position of the newest edition with a passage on it: 0 for the 2008 SNA, 1 for the 2025 SNA. `.get(passage["topic"], -1)` counts a topic not yet seen as −1, so the first edition found on it is always newer.
- `break` stops checking an edition's other names once one is found, so an edition is listed once.
- `' and '.join(...)` writes "the 2008 SNA and 2025 SNA" when a question names both.

## 8.4 Both filters, and the log

### 8.4.1 Principles

The licence filter runs first, then the edition filter. A passage withheld for its licence is not checked for its edition, so each withheld passage is recorded once, with one reason. In commercial use every SNA passage is withheld for its licence, and the edition filter has nothing left to do.

Each withheld passage is written to a **log**: one line per passage, giving the time, the use mode, the question, the passage, the filter and the reason. The log is added to, never overwritten. It shows anyone why a passage did not appear in an answer.

The log lives in `logs/withheld.jsonl`. The folder `logs/` is not committed (Chapter 15's traces go there too).

### 8.4.2 Code

`ragbook/ch08_filters.py`, the functions `filter_passages` and `record_withheld`

```python
def filter_passages(passages, question, use_mode):
    """
    Apply the licence filter, then the edition filter.

    Returns the passages kept and every withheld record. A passage withheld
    by the licence filter is not checked again for its edition.

    Example:
        kept, withheld = filter_passages(load_corpus(), "What is net national income?", "commercial")
        len(kept)
        returns 41
    """
    kept, withheld_by_licence = licence_filter(passages, use_mode)
    kept, withheld_by_edition = edition_filter(kept, question)
    return kept, withheld_by_licence + withheld_by_edition


def record_withheld(question, use_mode, withheld, log_file=LOG_FILE):
    """
    Add one line to the log for each withheld passage.

    Each line is a JSON record: date and time, use mode, question, passage
    id, filter and reason. The log is appended to, never overwritten.

    Example:
        record_withheld("What is net national income?", "commercial", withheld)
    """
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    when = datetime.datetime.now().isoformat(timespec="seconds")
    with open(log_file, "a", encoding="utf-8") as file:
        for record in withheld:
            line = {"time": when, "use_mode": use_mode, "question": question}
            line.update(record)
            file.write(json.dumps(line, ensure_ascii=False) + "\n")
```

### 8.4.3 Annotations

- `withheld_by_licence + withheld_by_edition` joins two lists into one.
- `open(log_file, "a", ...)` opens the file to add lines at its end; `"w"` would empty it first.
- `ensure_ascii=False` writes characters such as "é" as they are, so the log stays readable.
- `mkdir(parents=True, exist_ok=True)` makes the folder, and any folder above it, if missing, and does nothing if it exists.

One line of the log, for "How do you get from GNI to net national income?" in commercial use:

```json
{"time": "2026-10-25T19:41:19", "use_mode": "commercial", "question": "How do you get from GNI to net national income?", "id": "qna17-12.1", "filter": "licence", "reason": "licence: 'non-commercial' is not allowed in commercial use"}
```

## 8.5 Searching only what the filters allow

### 8.5.1 Principles

The filters run before the search, not after it. Removing passages from a finished ranking would leave fewer than three, or force a deeper search to fill the gap. Filtering first also means BM25's word statistics (Chapter 3) count only the passages that may be used.

`FilteredSearch` rebuilds Chapter 5's keyword, semantic and hybrid indexes from the kept passages for each question. At 56 passages that takes a few milliseconds. A **reachable** question is one that keeps at least one gold passage after filtering; no search can find a gold passage that was withheld.

### 8.5.2 Code

`ragbook/ch08_filters.py`, the class `FilteredSearch` and the function `reachable`

```python
class FilteredSearch:
    """
    Chapter 5's hybrid search, run on the passages that pass the filters.

    The indexes are rebuilt for each question from the kept passages, so a
    withheld passage cannot appear in a ranking and does not count in the
    BM25 word statistics. At 56 passages this takes a few milliseconds.

    Example:
        search = FilteredSearch(load_corpus(), load_embeddings(), embed_question)
        results, withheld = search.rank("What is net national income?", "commercial")
    """

    def __init__(self, passages, saved, embed_question):
        self.passages = passages
        self.saved = saved
        self.embed_question = embed_question

    def rank(self, question, use_mode, how_many=3, expand=True):
        kept, withheld = filter_passages(self.passages, question, use_mode)
        vectors = [self.saved[passage["id"]] for passage in kept]
        keyword_index = KeywordIndex(kept)
        semantic_index = SemanticIndex(kept, vectors, self.embed_question)
        hybrid_index = HybridIndex(keyword_index, semantic_index, KnowledgeGraph(kept))
        return hybrid_index.rank(question, how_many=how_many, expand=expand), withheld


def reachable(questions, passages, use_mode):
    """
    The questions that keep at least one gold passage after filtering.

    A question whose gold passages are all withheld cannot be answered from
    the corpus in that use mode, however good the search.

    Example:
        len(reachable(load_questions(), load_corpus(), "commercial"))
        returns 26
    """
    kept_questions = []
    for question in questions:
        kept, withheld = filter_passages(passages, question["question"], use_mode)
        kept_ids = [passage["id"] for passage in kept]
        if any(gold_id in kept_ids for gold_id in question["gold_passages"]):
            kept_questions.append(question)
    return kept_questions
```

### 8.5.3 Annotations

- `rank` returns two things: the ranked passages and the withheld records. The caller can log the second (8.4).
- `expand=True` turns on query expansion from the knowledge graph, as in the last row of Chapter 5's results (5.6).
- `any(...)` is true if at least one gold passage is among the kept ids.

### 8.5.4 Results

Hybrid search with query expansion, on the 32 definition questions:

| Use mode | Passages kept | Questions reachable | Hits at 1 | Hits at 3 | Hits at 10 |
| --- | --- | --- | --- | --- | --- |
| No filter (Chapter 5) | 56 | 32 | 26 | 32 | 32 |
| non-commercial | 54 | 32 | 27 | 32 | 32 |
| commercial | 41 | 27 | 21 | 25 | 27 |

"Passages kept" is for a question that names no edition.

- **Non-commercial** differs from Chapter 5 only through the edition filter. q2-25 rises from second place to first, although its gold passage was never withheld: removing two passages changes how many passages contain each word, so BM25 scores every passage differently, and moves other passages up both rankings. For q2-31, the definition esa10-11.27 rises from third place to second for the same reason.
- **Commercial** finds a gold passage within ten places for every reachable question. The five it cannot reach, q2-03, q2-16, q2-18, q2-19 and q2-32, have gold passages only in non-commercial or quotation-only sources. Answering them in commercial use needs open sources added to the corpus, or an answer that says the corpus holds no passage it may use.

## 8.6 The same filters inside Chroma

### 8.6.1 Principles

A vector database filters on metadata: it checks a condition on each passage's metadata and ranks only the passages that meet it (Chapter 7, 7.5). Chapter 7 stored source, reference, edition, scope and licence. This chapter adds `licence_class` and `passage_id`; Chroma merges new fields into the metadata already stored.

The licence condition reads `licence_class`, so it works on any collection whose items carry that field, such as Chapter 6's chunks once each is given its source's licence class. The edition condition lists the passages the edition filter withheld.

### 8.6.2 Code

`ragbook/ch08_filters.py`, the functions `add_filter_fields`, `chroma_filter`, `search_store_filtered` and `compare_with_filtered_exact`

```python
def add_filter_fields(collection, passages):
    """
    Add the fields the filters read to each stored passage's metadata.

    Chapter 7 stored source, reference, edition, scope and licence. Chroma merges
    new fields into the metadata already stored, so nothing else changes.

    Example:
        add_filter_fields(collection, load_corpus())
    """
    collection.update(
        ids=[passage["id"] for passage in passages],
        metadatas=[{"licence_class": passage["licence_class"], "passage_id": passage["id"]}
                   for passage in passages],
    )


def chroma_filter(use_mode, withheld):
    """
    Turn the use mode and the edition filter's withheld ids into a Chroma
    "where" condition.

    The licence condition reads licence_class, so it works on any collection
    whose items carry that field. The edition condition lists the passages
    to leave out.

    Example:
        chroma_filter("commercial", [])
        returns {"licence_class": {"$in": ["open"]}}
    """
    licence = {"licence_class": {"$in": USE_MODES[use_mode]}}
    edition_ids = [record["id"] for record in withheld if record["filter"] == "edition"]
    if not edition_ids:
        return licence
    return {"$and": [licence, {"passage_id": {"$nin": edition_ids}}]}


def search_store_filtered(collection, question_vector, where, how_many=3):
    """
    Chapter 7's search, with Chroma checking the condition before it ranks.

    Example:
        search_store_filtered(collection, vector, chroma_filter("commercial", []))
        returns only passages whose licence_class is "open"
    """
    answer = collection.query(query_embeddings=[np.asarray(question_vector).tolist()],
                              n_results=how_many, where=where)
    results = []
    for passage_id, metadata, distance in zip(answer["ids"][0], answer["metadatas"][0], answer["distances"][0]):
        result = {"id": passage_id, "similarity": 1 - distance}
        result.update(metadata)
        results.append(result)
    return results


def compare_with_filtered_exact(collection, passages, saved, questions, use_mode, how_many=3):
    """
    For each question, compare Chroma's filtered top passages with an exact
    semantic ranking of the passages that pass the same filters.

    Returns the number of questions that agree and the ids of any that do not.
    """
    same = 0
    different = []
    for question in questions:
        kept, withheld = filter_passages(passages, question["question"], use_mode)
        vector = saved[question["id"]]
        index = SemanticIndex(kept, [saved[p["id"]] for p in kept], lambda text: vector)
        exact_ids = [p["id"] for p in index.rank(question["question"], how_many)]
        where = chroma_filter(use_mode, withheld)
        chroma_ids = [r["id"] for r in search_store_filtered(collection, vector, where, how_many)]
        if chroma_ids == exact_ids:
            same += 1
        else:
            different.append(question["id"])
    return same, different
```

### 8.6.3 Annotations

- `$in`, `$nin` and `$and` are Chroma's words for "is one of", "is not one of" and "all of these".
- `where=` hands the condition to Chroma, which applies it before ranking.
- `lambda text: vector` is a one-line function that returns the question's saved embedding whatever text it is given, so the exact index needs no model.
- `compare_with_filtered_exact` builds Chapter 4's exact semantic index from the kept passages only, and checks that Chroma returns the same three passages in the same order.

Result: Chroma's filtered top three equal exact search on 32 of 32 questions, in both use modes.

## 8.7 Tests, glossary and links

### 8.7.1 Tests

The file `tests/test_ch08_filters.py` holds 12 tests. The Chroma tests build their database in a temporary folder. None needs the embedding model. Run them with `python -m pytest tests/test_ch08_filters.py -v`.

| Test | What it proves |
| --- | --- |
| Non-commercial use | Keeps all 56 passages |
| Commercial use | Keeps only open passages: 41 kept, 15 withheld, each with a reason |
| Editions named | Finds "2008 SNA", both editions, or none |
| Latest edition | Withholds sna08-2.144 and sna08-12.26; keeps sna08-15.187 |
| Named edition | Withholds the 2025 SNA only; ESA 2010 and BEA stay |
| Both filters | No passage is both kept and withheld; together they make 56, for every question in both use modes |
| Log | One line per withheld passage, added to, with six fields |
| Filtered search | No withheld passage appears in the first ten places |
| Reachable questions | Commercial use loses q2-03, q2-16, q2-18, q2-19 and q2-32 |
| Chroma condition | The condition written for each use mode |
| Chroma licence | Commercial results are all open |
| Chroma agrees | Same top three as filtered exact search on all 32 questions, both use modes |

The corpus test that counted one subscriber passage is replaced by one that checks no passage has an `access` field.

### 8.7.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Filter | A rule that decides, before any search, which passages a question may use |
| Licence class | A passage's terms of reuse in one of three words: open, non-commercial, quotation only |
| Use mode | How the answers will be used; it decides which licence classes are allowed |
| Licence filter | The filter that keeps only the licence classes the use mode allows |
| Edition filter | The filter that keeps the SNA edition a question names, or the latest edition on each topic |
| Withheld passage | A passage a filter removed for one question, recorded with the reason |
| Log | A file to which one line is added per event, here per withheld passage |
| Reachable question | A question that keeps at least one gold passage after filtering |
| Metadata filter | A condition on metadata that a vector database checks before ranking |

### 8.7.3 Links

- [Chroma documentation](https://docs.trychroma.com/)
- [Python `json` module](https://docs.python.org/3/library/json.html)
- [Python `datetime` module](https://docs.python.org/3/library/datetime.html)
- [Creative Commons licences](https://creativecommons.org/licenses/)
- [Chapter 8 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch08_filters.py)
