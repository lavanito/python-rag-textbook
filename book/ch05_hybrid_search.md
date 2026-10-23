# Chapter 5 — Hybrid search and the knowledge graph

## 5.1 What this chapter builds

We have seen that Chapter 3's keyword search and Chapter 4's semantic search miss different questions. This chapter combines their rankings, then adds the knowledge graph so that a question can find passages written under another manual's name.

1. **Reciprocal rank fusion** (5.2): two rankings become one, using only positions, not scores.
2. **The knowledge graph** (5.3): the code reads the knowledge graph built for this book and finds the concept that is named in a concept.
3. **Query expansion** (5.4): the keyword search is widened with each concept's other names, so "GNI" also finds "gross national income".
4. **Moving between manuals** (5.5): from a concept to its passages in each manual, following the links that say two names mean the same thing, or that two similar names must not be mixed.

Each step is measured on the same 32 definition questions (5.6), at three depths: first place, top three, top ten.

| Method | First place | Top three | Top ten |
| --- | --- | --- | --- |
| BM25 (Chapter 3) | 24 | 30 | 31 |
| Semantic search (Chapter 4) | 18 | 31 | 32 |
| Hybrid search | 25 | 29 | 32 |
| Hybrid search with query expansion | 24 | 30 | 32 |

Combining the two methods puts a correct passage first more often and finds one for every question within ten places. It does not improve the top three. Section 5.6 shows why.

**Code file:** `ragbook/ch05_hybrid_search.py`

**Uses:** Chapter 2 (`load_corpus`); Chapter 3 (`search_words`, `KeywordIndex`, `load_questions`); Chapter 4 (`SemanticIndex`, `load_embeddings`); Python's `csv` and `re` modules. The chapter reads Chapter 4's saved embeddings, so it needs no model and no internet connection.

## 5.2 Reciprocal rank fusion

### 5.2.1 Principles

**Hybrid search** runs keyword search and semantic search on the same question and combines the two rankings. The difficulty is the scores: a BM25 score has no upper limit, while a cosine similarity runs from −1 to 1, so the two cannot simply be added.

**Reciprocal rank fusion** (RRF) uses positions instead. A passage in place r of a ranking scores 1 / (k + r); its scores from each ranking are added:

```latex
\text{RRF}(p) = \sum_{\text{rankings}} \frac{1}{k + r(p)}
```

- **k** is a constant, set to 60 as in the paper that proposed the method (Cormack, Clarke and Büttcher, 2009; 5.8.3).
- With k = 60, first place scores 1/61 and second 1/62: close. A passage ranked well by both methods beats one ranked first by one method and low by the other.
- A passage missing from one ranking scores nothing from it. Keyword search leaves out passages that share no word with the question (3.6); they can still score from semantic search.

RRF is not a measure of quality. Some notes call it an evaluation metric; it only combines rankings.

### 5.2.2 Code

`ragbook/ch05_hybrid_search.py`, function `reciprocal_rank_fusion`

```python
def reciprocal_rank_fusion(rankings, k=60, how_many=3):
    """
    Combine several rankings of passages into one.

    Each passage scores 1 / (k + rank) in each ranking it appears in, and the
    scores are added. Only positions count, not the original scores, so BM25
    scores and cosine similarities can be combined although their scales
    differ. k = 60 is the value used in the method's original paper; it stops
    first place from counting for much more than second or third.

    Equal totals keep the order in which passages were first met.

    Example:
        reciprocal_rank_fusion([[a, b, c], [b, c, a]], how_many=1)
        returns [b]: 1/62 + 1/61 beats a's 1/61 + 1/63
    """
    totals = {}
    passages_by_id = {}
    for ranking in rankings:
        for rank, passage in enumerate(ranking, start=1):
            passage_id = passage["id"]
            totals[passage_id] = totals.get(passage_id, 0.0) + 1 / (k + rank)
            passages_by_id[passage_id] = passage
    order = sorted(totals, key=lambda passage_id: -totals[passage_id])
    best = []
    for passage_id in order[:how_many]:
        best.append(passages_by_id[passage_id])
    return best
```

### 5.2.3 Annotations

- `enumerate(ranking, start=1)` gives each passage with its place, counting from 1, not 0.
- `totals.get(passage_id, 0.0)` starts a passage at zero the first time it is met, as `document_frequencies` did in Chapter 3 (3.4.2).
- `passages_by_id` keeps each passage itself, so the function can return passages, not only ids.
- `sorted(totals, ...)` sorts the ids. A dictionary keeps the order in which keys were added, and `sorted` keeps equal items in their original order, so equal totals keep the order in which passages were first met.

## 5.3 The knowledge graph, and the concepts a question names

### 5.3.1 Principles

The **knowledge graph** is a small, hand-built record of the ideas in the corpus and how they relate, kept in `data/knowledge_graph/`. Its design is in that folder's `README.md`; this chapter is its first use.

It has two parts: an **ontology**, the rules that say which kinds of thing exist and which relations may link them, and the facts that follow those rules. The glossary (5.8.2) defines both terms strictly and says how a knowledge graph differs from a concept map.

- `entities.csv` lists 51 things: concepts, manuals, economies, indicators and question types. Each has an id, a kind, a label and other names (**aliases**). For example, the concept `gni` has the label "gross national income" and the aliases "GNI" and "national income".
- `triples.csv` holds 73 facts, each in three parts: subject, relation, object. These are **triplets**. For example, `nni, defined_in, sna08-2.144` says that paragraph 2.144 of the 2008 SNA defines net national income. Every triplet records its evidence: a passage, or `author` for the author's own framing.
- `schema.json` lists the six kinds of thing and the eleven relations allowed between them: the ontology.

To use the knowledge graph, the code must first find which concepts a question names. It cleans each name exactly as Chapter 3 cleans questions (`search_words`), then looks for it word by word in the question.

Two rules keep the matching accurate:

- **The longer name wins.** "Net national income" contains "national income", an alias of GNI. When one concept's name lies inside a longer name found in the same place, only the longer one counts.
- **A note in brackets is not part of a name.** The label "gross domestic income (BEA)" says whose term it is; the code drops "(BEA)" before matching.

Cleaning can also make two names identical. The alias "GNI*" (Ireland's modified GNI) became "gni" once the asterisk was removed, so every question about GNI also matched modified GNI. The alias was dropped ("GNI star" remains), and a test now checks that no two unrelated concepts share a cleaned name (5.8.1).

### 5.3.2 Code

`ragbook/ch05_hybrid_search.py`, functions `read_csv` and `phrase_positions`, and class `KnowledgeGraph`

```python
def read_csv(file_path):
    """
    Read a CSV file into a list of dictionaries, one per row.

    Example:
        read_csv(GRAPH_FOLDER / "entities.csv")[0]["id"]
        returns "terms_of_trade"
    """
    with open(file_path, encoding="utf-8") as file:
        return list(csv.DictReader(file))
```

```python
def phrase_positions(phrase, words):
    """
    Find where a phrase appears in a list of search words.

    The phrase is cleaned exactly as the words were (Chapter 3's
    search_words), then looked for word by word. Each match is returned as
    (start, end) positions.

    Example:
        phrase_positions("national income", ["net", "national", "income"])
        returns [(1, 3)]
    """
    phrase_words = search_words(phrase)
    if phrase_words == []:
        return []
    size = len(phrase_words)
    found = []
    for start in range(len(words) - size + 1):
        if words[start:start + size] == phrase_words:
            found.append((start, start + size))
    return found
```

```python
# Relations that read the same in both directions.
TWO_WAY_RELATIONS = ["same_as", "differs_from", "related_to"]
```

```python
class KnowledgeGraph:
    """
    The knowledge graph: what each concept is called, and how things are linked.

    Example:
        knowledge_graph = KnowledgeGraph(load_corpus())
        knowledge_graph.concepts_in("What is GDI?")
        returns ["bea_gdi"]
    """

    def __init__(self, passages, folder=GRAPH_FOLDER):
        self.entities = {}
        for row in read_csv(folder / "entities.csv"):
            self.entities[row["id"]] = row
        self.triples = read_csv(folder / "triples.csv")
        self.passages = {}
        for passage in passages:
            self.passages[passage["id"]] = passage

    def names(self, concept_id):
        """
        Every name of a concept: its label, then its aliases.

        A note in brackets at the end of a label, such as "(BEA)", says whose
        term it is; it is not part of the name, so it is dropped.

        Example:
            names("bea_gdi")
            returns ["gross domestic income", "GDI", "income-side GDP"]
        """
        entity = self.entities[concept_id]
        label = re.sub(r"\s*\([^)]*\)$", "", entity["label"])
        names = [label]
        for alias in entity["aliases"].split(";"):
            alias = alias.strip()
            if alias != "":
                names.append(alias)
        return names

    def concepts_in(self, question):
        """
        List the concepts a question names, by label or alias.

        When one concept's name lies inside a longer name found in the same
        place, only the longer one counts: "net national income" is NNI, not
        also "national income" (GNI).

        Example:
            concepts_in("How do you get from GNI to net national income?")
            returns ["gni", "nni"]
        """
        words = search_words(question)
        matches = {}
        for concept_id, entity in self.entities.items():
            if entity["type"] != "Concept":
                continue
            places = []
            for name in self.names(concept_id):
                places.extend(phrase_positions(name, words))
            if places != []:
                matches[concept_id] = places

        found = []
        for concept_id, places in matches.items():
            if not self.always_inside_longer_name(concept_id, places, matches):
                found.append(concept_id)
        return found

    def always_inside_longer_name(self, concept_id, places, matches):
        """True if every place a concept was found lies inside a longer match of another concept."""
        for start, end in places:
            inside = False
            for other_id, other_places in matches.items():
                if other_id == concept_id:
                    continue
                for other_start, other_end in other_places:
                    longer = other_end - other_start > end - start
                    if longer and other_start <= start and end <= other_end:
                        inside = True
            if not inside:
                return False
        return True

    def linked(self, concept_id, relation):
        """
        Everything linked to a concept by one relation, with the note on the link.

        same_as, differs_from and related_to read both ways, so they are
        followed from either end.

        Example:
            linked("consumption_of_fixed_capital", "same_as")
            returns [("depreciation_2025", "The 2025 SNA renames ...")]
        """
        found = []
        for triple in self.triples:
            if triple["relation"] != relation:
                continue
            if triple["subject"] == concept_id:
                found.append((triple["object"], triple["note"]))
            elif triple["object"] == concept_id and relation in TWO_WAY_RELATIONS:
                found.append((triple["subject"], triple["note"]))
        return found
```

### 5.3.3 Annotations

- `csv.DictReader` reads a CSV file row by row, each row a dictionary keyed by the column names in the first line.
- `re.sub(r"\s*\([^)]*\)$", "", ...)` removes a note in brackets at the end of a label. `re` is Python's module for **regular expressions**, patterns that describe text: `\(` is an opening bracket, `[^)]*` any characters except a closing bracket, `$` the end of the text.
- `words[start:start + size] == phrase_words` compares a slice of the question's words with the phrase, one position at a time.
- `matches` maps each concept to every place its names were found, as (start, end) pairs; `always_inside_longer_name` then applies the longer-name rule.
- `linked` reads the triplets each time it is called. With 73 triplets that takes no noticeable time; a larger graph would be indexed once, as `KeywordIndex` does for words.

## 5.4 Widening the keyword search with aliases

### 5.4.1 Principles

**Query expansion** adds words to a question before searching. Here the added words are the names of each concept the question names, and of any concept linked to it by `same_as` (the same concept under another manual's name).

Chapter 4 showed why this might help (4.7.1). The question "What is the difference between GDP and GNI?" failed with BM25 because the passage that defines GNI writes "gross national income" in full. Query expansion adds that phrase.

The expanded question is used for keyword search only. Semantic search keeps the original question, for two reasons: its saved embedding can be reused, and the embedding model already places many synonyms close together (4.2.1).

Query expansion has a cost. Every question about GDP gains "gross domestic product" and "domestic product": words found in 9 to 11 of the 48 passages. Section 5.6 measures the trade.

`HybridIndex` puts the parts together: it ranks every passage both ways, optionally with the expanded question for BM25, then combines the two rankings with RRF.

### 5.4.2 Code

`ragbook/ch05_hybrid_search.py`, function `expand_question` and class `HybridIndex`

```python
def expand_question(knowledge_graph, question):
    """
    Add the other names of each concept the question names to the question.

    Names of concepts linked by same_as are added too: they are the same
    concept under another manual's name. The longer question is then used
    for keyword search only; semantic search keeps the original.

    Example:
        expand_question(knowledge_graph, "What is the difference between GDP and GNI?")
        returns the question followed by "gross domestic product GDP domestic
        product gross national income GNI national income"
    """
    extra_names = []
    for concept_id in knowledge_graph.concepts_in(question):
        same_concepts = [concept_id]
        for other_id, note in knowledge_graph.linked(concept_id, "same_as"):
            same_concepts.append(other_id)
        for same_id in same_concepts:
            for name in knowledge_graph.names(same_id):
                if name not in extra_names:
                    extra_names.append(name)
    if extra_names == []:
        return question
    return question + " " + " ".join(extra_names)
```

```python
class HybridIndex:
    """
    Keyword and semantic search combined by reciprocal rank fusion, with an
    option to widen the keyword search from the knowledge graph.

    Example:
        index = HybridIndex(keyword_index, semantic_index, knowledge_graph)
        index.rank("What is the difference between GDP and GNI?", expand=True)
        returns the three best passages after RRF
    """

    def __init__(self, keyword_index, semantic_index, knowledge_graph):
        self.keyword_index = keyword_index
        self.semantic_index = semantic_index
        self.knowledge_graph = knowledge_graph

    def rank(self, question, how_many=3, expand=False):
        """
        Rank every passage both ways, then combine the two rankings with RRF.

        With expand=True the keyword ranking uses the expanded question.
        """
        everything = len(self.keyword_index.passages)
        keyword_question = question
        if expand:
            keyword_question = expand_question(self.knowledge_graph, question)
        keyword_ranking = self.keyword_index.rank(keyword_question, "bm25", how_many=everything)
        semantic_ranking = self.semantic_index.rank(question, how_many=everything)
        return reciprocal_rank_fusion([keyword_ranking, semantic_ranking], how_many=how_many)
```

### 5.4.3 Annotations

- `for other_id, note in knowledge_graph.linked(...)` unpacks each (id, note) pair into two names; the note is not needed here.
- `if name not in extra_names` stops a name being added twice when two matched concepts share it.
- `" ".join(extra_names)` joins the names with spaces, as in Chapter 1 (1.6).
- `everything = len(self.keyword_index.passages)` asks both methods for a full ranking. RRF needs each method's whole order: a passage in fifth place still adds to its total.

## 5.5 From a concept to its passages, in each manual

### 5.5.1 Principles

Searching finds passages that look like the question. The knowledge graph can also say which passages are about a concept, in each manual, without searching at all. This is **traversal**: following links from one thing to the next.

From a concept, the code follows:

- `defined_in` and `discussed_in` to its passages, grouped by the manual each passage comes from (definitions first);
- `same_as` to the same concept under another name, and on to that concept's passages;
- `differs_from` to a concept with a similar name that an answer must not mix up with this one.

Two examples show what traversal adds:

- **Consumption of fixed capital.** The 2025 SNA renames it depreciation. A search for "consumption of fixed capital" does not find sna25-3.145, which writes only "depreciation"; the `same_as` link does.
- **GDI.** BEA's gross domestic income is GDP measured from incomes. Real gross domestic income in the SNA is a different measure: it adds the trading gain. The letters are the same. The `differs_from` link brings back the ESA 2010 passage on real income and the terms of trade, with a note, so the answer can say which GDI it means.

Traversal returns only what the knowledge graph records. It cannot find a passage no triplet points to, which is why it complements search rather than replacing it. Chapter 12 uses the same links to route questions.

### 5.5.2 Code

`ragbook/ch05_hybrid_search.py`, functions `passages_by_manual` and `concept_trail`

```python
def passages_by_manual(knowledge_graph, concept_id):
    """
    The passages that define or discuss a concept, grouped by manual.

    Each manual maps to a list of (passage id, relation) pairs, definitions
    first. The manual is the passage's source_code in the corpus.

    Example:
        passages_by_manual(knowledge_graph, "nni")
        returns {"SNA08": [("sna08-2.144", "defined_in")],
                 "SNA25": [("sna25-3.145", "defined_in")],
                 "ESA10": [("esa10-8.94", "discussed_in")]}
    """
    grouped = {}
    for relation in ["defined_in", "discussed_in"]:
        for passage_id, note in knowledge_graph.linked(concept_id, relation):
            manual = knowledge_graph.passages[passage_id]["source_code"]
            if manual not in grouped:
                grouped[manual] = []
            grouped[manual].append((passage_id, relation))
    return grouped
```

```python
def concept_trail(knowledge_graph, concept_id):
    """
    A concept's passages, then those of the concepts it is the same as or
    differs from.

    Returns a list of (concept id, relation that led there, note, passages
    by manual). same_as leads to the same idea under another manual's name;
    differs_from leads to a concept an answer must not mix up with this one.

    Example:
        concept_trail(knowledge_graph, "bea_gdi")
        returns BEA's GDI passages, then real GDI (SNA) under differs_from
    """
    trail = [(concept_id, "asked", "", passages_by_manual(knowledge_graph, concept_id))]
    for relation in ["same_as", "differs_from"]:
        for other_id, note in knowledge_graph.linked(concept_id, relation):
            trail.append((other_id, relation, note, passages_by_manual(knowledge_graph, other_id)))
    return trail
```

### 5.5.3 Annotations

- The manual comes from the passage's `source_code` field in the corpus, not from the knowledge graph, so the two never disagree.
- `if manual not in grouped: grouped[manual] = []` creates an empty list the first time a manual is met.
- The loop over `["defined_in", "discussed_in"]` puts definitions first within each manual.
- `concept_trail` returns a list of four-part tuples; the worked example (5.7) prints them.

## 5.6 Measuring at three depths

### 5.6.1 Principles

Chapter 3's measure counts questions with a gold passage in the top three. This chapter adds two depths: first place, and the top ten. The new function `hits_at` takes the depth as an argument.

| Method | First place | Top three | Top ten | Missed in the top three |
| --- | --- | --- | --- | --- |
| BM25 (Chapter 3) | 24 | 30 | 31 | q2-04, q2-30 |
| Semantic search (Chapter 4) | 18 | 31 | 32 | q2-24 |
| Hybrid search | 25 | 29 | 32 | q2-04, q2-24, q2-30 |
| Hybrid search with query expansion | 24 | 30 | 32 | q2-17, q2-24 |

**Hybrid search helps at first place and at ten.** Hybrid search puts a gold passage first for 25 questions, more than either method alone, and finds one within ten places for all 32.

**Hybrid search does not help in the top three.** RRF rewards passages both methods rank fairly well. A passage one method ranks second and the other eighth ends up between them. For "Is net domestic product a better measure than GDP?" (q2-24), BM25 ranks the gold passage second and semantic search eighth; the hybrid ranking puts it fourth. For "What is the difference between GDP and GNI?" (q2-04), semantic search ranks it second and BM25 seventeenth; the hybrid ranking puts it eighth.

**Query expansion fixes some questions and breaks others.** With query expansion, BM25 ranks a gold passage for q2-04 fifth instead of seventeenth, and the hybrid ranking third. q2-30 also comes back into the top three. But "Why are GDP estimates revised?" (q2-17) drops out: query expansion adds "gross domestic product" and "domestic product", words found in 9 to 11 of the 48 passages, which push the passages about revisions down.

Several rules to limit query expansion were tried: expanding only concepts named in few passages, and giving added words less weight. Each fixed one question and broke another. With 32 questions, one question is about three percentage points, and choosing a rule because it scores best on these same questions would only fit these questions. The chapter keeps the plain rule and reports what it does.

Chapter 10 measures query expansion separately, with more measures. The caveats of Chapter 3 (3.8.1) still apply.

### 5.6.2 Code

`ragbook/ch05_hybrid_search.py`, functions `hits_at`, `saved_question_embedder` and `build_indexes`

```python
def hits_at(rank_function, questions, depth):
    """
    Count the questions with at least one gold passage in the first `depth` places.

    Chapter 3's top_three_hits is hits_at(..., depth=3); rank_function must
    return at least `depth` passages for the count to be fair.

    Example:
        hits_at(lambda q: index.rank(q, how_many=10), questions, depth=1)
        counts the questions whose first passage is a gold one
    """
    hits = 0
    for question in questions:
        found_ids = []
        for passage in rank_function(question["question"])[:depth]:
            found_ids.append(passage["id"])
        for gold_id in question["gold_passages"]:
            if gold_id in found_ids:
                hits = hits + 1
                break
    return hits
```

```python
def saved_question_embedder(questions, saved):
    """
    A function that returns a bank question's saved embedding, so the
    chapter runs without the model. Questions outside the bank are refused.

    Example:
        embed = saved_question_embedder(load_questions(), load_embeddings())
        embed("What is GDI?").shape
        returns (384,)
    """
    ids_by_text = {}
    for question in questions:
        ids_by_text[question["question"]] = question["id"]

    def embed_question(text):
        if text not in ids_by_text:
            raise KeyError(f"No saved embedding for: {text} (load the model as in Chapter 4)")
        return saved[ids_by_text[text]]

    return embed_question
```

```python
def build_indexes():
    """
    Build the keyword, semantic and hybrid indexes and the knowledge graph from
    the saved files.

    Example:
        keyword_index, semantic_index, hybrid_index, questions = build_indexes()
    """
    passages = load_corpus()
    questions = load_questions()
    saved = load_embeddings()
    passage_vectors = []
    for passage in passages:
        passage_vectors.append(saved[passage["id"]])
    keyword_index = KeywordIndex(passages)
    semantic_index = SemanticIndex(passages, passage_vectors,
                                   saved_question_embedder(questions, saved))
    hybrid_index = HybridIndex(keyword_index, semantic_index, KnowledgeGraph(passages))
    return keyword_index, semantic_index, hybrid_index, questions
```

### 5.6.3 Annotations

- `rank_function(question["question"])[:depth]` keeps the first `depth` passages; the ranking function must return at least that many.
- `saved_question_embedder` builds and returns a function, `embed_question`, that remembers `ids_by_text`. A function defined inside another and returned this way is a **closure**.
- `raise KeyError(...)` stops with a clear message if a question has no saved embedding. A new question needs the model, as in Chapter 4 (4.4).
- `build_indexes` returns four things at once; `keyword_index, semantic_index, hybrid_index, questions = build_indexes()` unpacks them.

## 5.7 Running the worked example

From the repository folder:

```text
python -m ragbook.ch05_hybrid_search
```

The output from the test laptop (Windows), 23 October 2026, identical to the run used to write this chapter:

```text
5.2  Reciprocal rank fusion on two short rankings
     [a, b, c] and [b, c, a] give ['b', 'a', 'c']

5.3  Concepts named in a question
     How do you get from GNI to net national income?
       -> ['gni', 'nni']
     What is GDI?
       -> ['bea_gdi']
     What is real gross domestic income, and how does it lead to real gross national income?
       -> ['real_gdi', 'gni']

5.4  What is the difference between GDP and GNI?
     expanded: What is the difference between GDP and GNI? gross domestic product GDP domestic product gross national income GNI national income
     hybrid search: ['cso-gnistar-6', 'cso-gnistar-3', 'cso-gnistar-1']
     hybrid search + query expansion: ['cso-gnistar-6', 'bea-ch2-ndp-gni', 'bea-ch2-gnp']

5.5  From 'consumption of fixed capital' to its passages
     asked: consumption_of_fixed_capital
       ESA10: esa10-3.139 [defined_in]
       SNA08: sna08-2.144 [discussed_in]
     same_as: depreciation_2025  (The 2025 SNA renames consumption of fixed capital as depreciation)
       SNA25: sna25-3.145 [discussed_in]

5.5  From 'gross domestic income' to its passages
     asked: bea_gdi
       BEA: bea-ch2-ndp-gni [defined_in]
     differs_from: real_gdi  (Same letters: the SNA measure adds the trading gain; BEA's GDI is GDP measured from incomes)
       ESA10: esa10-10.47 [discussed_in]

5.6  Questions with a gold passage within the first 1, 3 and 10 places (of 32)
     BM25 (Chapter 3)                  24  30  31
     Semantic search (Chapter 4)       18  31  32
     Hybrid search                     25  29  32
     Hybrid search + query expansion   24  30  32
```

Three points stand out.

- **RRF on two short rankings.** In [a, b, c] and [b, c, a], b is second and first: 1/62 + 1/61. a is first and third: 1/61 + 1/63. The passage both rankings place well comes first.
- **The GDP and GNI question.** Without query expansion, all three places go to passages from the CSO's page on modified GNI, which use "GNI" often. With query expansion, BEA's passages on GDP, GNP and GNI enter, including bea-ch2-gnp, a gold passage.
- **The trails.** Consumption of fixed capital leads to the 2025 SNA through `same_as`. BEA's GDI leads to the ESA 2010 passage on real income through `differs_from`, with the note that says why the two must not be mixed.

The chapter reads only saved files, so every computer gives the same output.

## 5.8 Tests, glossary and links

### 5.8.1 Tests

The file `tests/test_ch05_hybrid_search.py` holds 17 tests. The first fourteen use small examples or the knowledge graph; the last three read the saved embeddings and fix the results reported in this chapter. Run them with `python -m pytest tests/test_ch05_hybrid_search.py -v`.

| Test | What it proves |
| --- | --- |
| RRF rewards agreement | [a, b, c] and [b, c, a] give b, a, c |
| RRF counts a passage missing from one ranking | A passage still scores from the other ranking |
| RRF keeps first-met order for equal totals | Ties are broken the same way every time |
| Phrase positions | A phrase is cleaned like the question and found word by word |
| Bracket note dropped | "gross domestic income (BEA)" is matched as "gross domestic income" |
| Longer name wins | "net national income" gives NNI only |
| Label with a bracket note is found | Real gross domestic income is recognised |
| No two unrelated concepts share a cleaned name | Catches errors such as "GNI*" becoming "gni" |
| Two-way relations | `same_as` is followed from either end |
| Query expansion adds full names | "GNI" adds "gross national income"; a question with no concept is unchanged |
| Query expansion follows `same_as` | Consumption of fixed capital adds "depreciation" |
| Passages grouped by manual | Net national income: 2008 SNA, 2025 SNA, ESA 2010, definitions first |
| Trail crosses manuals and flags differences | BEA's GDI leads to real GDI through `differs_from` |
| Hits within a depth | `hits_at` counts only the first `depth` places |
| Measured hits at depths 1, 3 and 10 | The table in 5.6 |
| Misses in the top three | The question ids in 5.6 |
| GDP and GNI ranking | The two rankings shown in 5.7 |

### 5.8.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Hybrid search | Ranking passages with keyword and semantic search together and combining the results |
| Reciprocal rank fusion (RRF) | Combining rankings by adding 1 / (k + place) for each passage across rankings |
| Ontology | The rules of a knowledge graph: which kinds of thing exist, and which relations may link which kinds. In this book: `schema.json`, six kinds and eleven relations |
| Knowledge graph | An ontology together with the facts that follow its rules: the things, and the triplets that link them. In this book: `data/knowledge_graph/`, 51 things and 73 triplets |
| Concept map | A diagram of concepts joined by labelled arrows, with no fixed rules on kinds or relations. A knowledge graph differs from it by having an ontology and checking every fact against it. This book does not use one |
| Alias | Another name for a concept, such as "GNI" for gross national income |
| Triplet | One fact in three parts: subject, relation, object |
| Query expansion | Adding words to a question before searching, here the names of the concepts it names |
| Traversal | Following links in the knowledge graph from one thing to the next |
| Regular expression | A pattern that describes text, used with Python's `re` module |
| Closure | A function defined inside another and returned, which keeps the values it was built with |

### 5.8.3 Links

- [Cormack, Clarke and Büttcher (2009), "Reciprocal rank fusion outperforms Condorcet and individual rank learning methods", SIGIR 2009 (DOI 10.1145/1571941.1572114)](https://dl.acm.org/doi/10.1145/1571941.1572114)
- [The same paper, free copy from the University of Waterloo](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Python `csv` module](https://docs.python.org/3/library/csv.html)
- [Python `re` module](https://docs.python.org/3/library/re.html)
- [Knowledge graph files on GitHub](https://github.com/lavanito/python-rag-textbook/tree/main/data/knowledge_graph)
- [Chapter 5 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch05_hybrid_search.py)
