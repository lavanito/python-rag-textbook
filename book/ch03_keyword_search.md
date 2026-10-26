# Chapter 3 — Keyword search: word counts, TF-IDF and BM25

## 3.1 What this chapter builds

Chapter 2 found passages by counting how many of the question's words they contain. This chapter replaces that step with three better scores, each built by hand, and measures how much each one helps.

1. **Word counts** (3.3): add up how often the question's words appear.
2. **TF-IDF** (3.4): weight each word by how rare it is in the corpus.
3. **BM25** (3.5): also stop repeated words from piling up, and allow for passage length.

All three need the same first step: splitting text into words properly (3.2). BM25 is then checked against a published library (3.7), and all three are measured on the 32 definition questions in the question bank (3.8).

| Method | Definition questions with a correct passage in the top three |
| --- | --- |
| Chapter 2: shared topic words | 25 of 32 |
| Word counts | 28 of 32 |
| TF-IDF | 30 of 32 |
| BM25 | 30 of 32 |

**Code file:** `ragbook/ch03_keyword_search.py`

**Uses:** Chapter 1 (`split_into_words`, `load_passages`); Chapter 2 (`COMMON_WORDS`, `load_corpus`); Python's `math` module; the bm25s library (MIT licence) in 3.7 only. Install it once with `pip install bm25s`.

## 3.2 Words, cleaned properly

### 3.2.1 Principles

Every score in this chapter compares words, so the words must be split the same way in the question and in the passage.

Chapter 1's `split_into_words` removes the punctuation on a keyboard. The manuals' PDFs also use typographic marks: curly quotation marks (“ ” ‘ ’), long dashes (– —) and the ellipsis (…). These stayed attached to words. One passage writes “GDP deflator”, which split into “gdp and deflator”, so the question "What is the GDP deflator?" could not match it (Chapter 2, 2.8).

This chapter's `search_words` replaces those marks with spaces first. It also drops common words, as Chapter 2 did, but keeps every repeat: counting repeats is the point of this chapter.

### 3.2.2 Code

`ragbook/ch03_keyword_search.py`, the text `TYPOGRAPHIC_MARKS` and the functions `search_words` and `count_words`

```python
# Typographic marks that PDFs use and that Chapter 1's split_into_words does
# not remove, because they are not in Python's string.punctuation.
TYPOGRAPHIC_MARKS = "“”‘’–—…"
```

```python
def search_words(text):
    """
    Split a text into lower-case words for searching, dropping common words.

    Curly quotation marks, dashes and the ellipsis are replaced by spaces
    first, so “GDP deflator” gives "gdp" and "deflator", not "“gdp" and
    "deflator”". Words are kept every time they appear: counting them is
    the point of this chapter.

    Example:
        search_words("What is the “GDP deflator”?")
        returns ["gdp", "deflator"]
    """
    for mark in TYPOGRAPHIC_MARKS:
        text = text.replace(mark, " ")
    words = []
    for word in split_into_words(text):
        if word not in COMMON_WORDS:
            words.append(word)
    return words
```

```python
def count_words(words):
    """
    Count how often each word appears in a list of words.

    Example:
        count_words(["gdp", "income", "gdp"])
        returns {"gdp": 2, "income": 1}
    """
    counts = {}
    for word in words:
        if word in counts:
            counts[word] = counts[word] + 1
        else:
            counts[word] = 1
    return counts
```

### 3.2.3 Annotations

- `text.replace(mark, " ")` returns a new string with every copy of `mark` replaced. Strings cannot be changed in place, so the result is stored back in `text`.
- `for mark in TYPOGRAPHIC_MARKS:` loops over the characters of a string, one at a time.
- An apostrophe written as ’ is one of the marks, so "country’s" becomes "country" and "s"; "s" is in `COMMON_WORDS` (Chapter 2) and is dropped.
- `count_words` builds a **dictionary** (Chapter 1) from word to count. `counts.get(word, 0)`, used in 3.3, returns 0 for a word not in the dictionary instead of failing.

## 3.3 Scoring by word counts

### 3.3.1 Principles

The simplest improvement on Chapter 2 is to count every appearance. A passage that uses "deflator" three times scores three for it, not one.

Two faults remain. Every word counts the same, so "income", found in many passages, weighs as much as "deflator", found in two. And long passages collect more appearances simply by being long.

### 3.3.2 Code

`ragbook/ch03_keyword_search.py`, function `count_score`

```python
def count_score(question_words, passage_words):
    """
    Score a passage by how often the question's words appear in it.

    Each question word is counted once, however often it appears in the
    question; its count in the passage is added to the score.

    Example:
        count_score(["gdp", "deflator"], ["gdp", "growth", "gdp"])
        returns 2 (two appearances of "gdp", none of "deflator")
    """
    counts = count_words(passage_words)
    score = 0
    for word in set(question_words):
        score = score + counts.get(word, 0)
    return score
```

### 3.3.3 Annotations

- `set(question_words)` keeps each question word once, so a question that repeats a word does not count it twice.
- Score: 28 of 32 questions now have a correct passage in the top three, up from 25 (3.8).

## 3.4 TF-IDF: rare words count for more

### 3.4.1 Principles

**TF-IDF** multiplies two numbers for each word of the question found in a passage:

- **Term frequency (TF):** how often the word appears in the passage.
- **Inverse document frequency (IDF):** how rare the word is across the corpus, log(N ÷ n), where N is the number of passages and n the number that contain the word.

In this corpus, "deflator" is in 2 of the 56 passages and "gdp" in 18. One "deflator" adds log(56 ÷ 2) = 3.33 to a passage's score; one "gdp" adds log(56 ÷ 18) = 1.13. A word found in every passage adds log(1) = 0: it tells the passages apart not at all.

The **document frequency** n counts passages, not appearances: a passage that says "gdp" five times adds one to n.

### 3.4.2 Code

`ragbook/ch03_keyword_search.py`, functions `document_frequencies` and `tf_idf_score`

```python
def document_frequencies(passage_word_lists):
    """
    For each word, count how many passages contain it at least once.

    Example:
        document_frequencies([["gdp", "gdp"], ["gdp", "income"]])
        returns {"gdp": 2, "income": 1}
    """
    frequencies = {}
    for words in passage_word_lists:
        for word in set(words):
            frequencies[word] = frequencies.get(word, 0) + 1
    return frequencies
```

```python
def tf_idf_score(question_words, passage_words, frequencies, number_of_passages):
    """
    Score a passage with TF-IDF: term frequency times inverse document frequency.

    Term frequency (TF) is how often the word appears in this passage.
    Inverse document frequency (IDF) is log(N / n): N passages in all, n of
    them containing the word. A word found in every passage gets IDF 0 and
    adds nothing; a word found in one passage gets the largest IDF.

    Example:
        In the corpus, "deflator" is in 2 of the 56 passages and "gdp" in 18.
        One "deflator" adds log(56/2) = 3.33; one "gdp" adds log(56/18) = 1.13.
    """
    counts = count_words(passage_words)
    score = 0.0
    for word in set(question_words):
        if word in counts:
            idf = math.log(number_of_passages / frequencies[word])
            score = score + counts[word] * idf
    return score
```

### 3.4.3 Annotations

- `math.log` is the natural logarithm. Any base gives the same ranking; only the size of the scores changes.
- `for word in set(words):` inside `document_frequencies` counts each word once per passage, however often it appears there.
- `frequencies.get(word, 0) + 1` adds one to the count, starting from 0 for a word seen for the first time.
- Score: 30 of 32.

## 3.5 BM25: repeats and passage length

### 3.5.1 Principles

**BM25** keeps TF-IDF's idea and fixes its two remaining faults.

- **Repeats count for less and less.** The term-frequency part rises with each extra appearance but levels off. The setting k1 (1.5 here) decides how fast: a passage that says "deflator" five times scores more than one that says it once, but less than five times as much.
- **Long passages are marked down.** A passage's length is compared with the average (62.5 words after common words are dropped). A longer passage needs more appearances for the same score. The setting b (0.75 here) decides how much: 0 ignores length, 1 adjusts fully.

BM25 also uses a slightly different IDF, log(1 + (N − n + 0.5) ÷ (n + 0.5)), which never falls below zero.

For each question word found in the passage, with tf its count there:

```latex
\text{score} = \text{IDF} \times \frac{tf \times (k_1 + 1)}{tf + k_1 \times \left(1 - b + b \times \frac{\text{passage length}}{\text{average length}}\right)}
```

The passage's score is the sum over the question's words.

### 3.5.2 Code

`ragbook/ch03_keyword_search.py`, function `bm25_score`

```python
def bm25_score(question_words, passage_words, frequencies, number_of_passages,
               average_length, k1=1.5, b=0.75):
    """
    Score a passage with BM25, the method most search engines use by default.

    Two changes from TF-IDF:
      - Repeats count for less and less. The term-frequency part rises with
        each extra appearance but levels off; k1 sets how fast (1.5 here).
      - Long passages are marked down. A passage longer than average needs
        more appearances for the same score; b sets how much (0.75 here).
    The IDF used is log(1 + (N - n + 0.5) / (n + 0.5)), which stays above zero.

    Example:
        A passage that mentions "deflator" five times scores less than five
        times one that mentions it once.
    """
    counts = count_words(passage_words)
    length_ratio = len(passage_words) / average_length
    score = 0.0
    for word in set(question_words):
        if word in counts:
            n = frequencies[word]
            idf = math.log(1 + (number_of_passages - n + 0.5) / (n + 0.5))
            tf = counts[word]
            tf_part = tf * (k1 + 1) / (tf + k1 * (1 - b + b * length_ratio))
            score = score + idf * tf_part
    return score
```

### 3.5.3 Annotations

- `k1=1.5, b=0.75` are default values (Chapter 2, 2.2.3), the same as bm25s's defaults. Elasticsearch uses k1 = 1.2 with the same b. Chapter 10 tests whether other settings work better on this corpus.
- `length_ratio` is above 1 for a passage longer than average, which makes the bottom of the fraction larger and the score smaller.
- Score: 30 of 32, the same as TF-IDF (3.8).

## 3.6 Ranking with an index

### 3.6.1 Principles

Scoring needs every passage split into words, the document frequencies and the average length. Working these out again for every question repeats the same work. An **index** does it once, when the corpus is loaded, and keeps the results.

Here the index is a **class**: a bundle of data and the functions that use it. The data are the passages, their word lists and the counts; the functions score and rank.

### 3.6.2 Code

`ragbook/ch03_keyword_search.py`, class `KeywordIndex`

```python
class KeywordIndex:
    """
    The corpus, split into words once, with the counts every score needs.

    Splitting every passage for every question would repeat the same work;
    the index does it once when it is built.

    Example:
        index = KeywordIndex(load_corpus())
        index.rank("What is the GDP deflator?", "bm25", how_many=3)
        returns the three best passages by BM25
    """

    def __init__(self, passages):
        self.passages = passages
        self.word_lists = []
        for passage in passages:
            self.word_lists.append(search_words(passage["text"]))
        self.frequencies = document_frequencies(self.word_lists)
        self.number_of_passages = len(passages)
        total_length = 0
        for words in self.word_lists:
            total_length = total_length + len(words)
        self.average_length = total_length / self.number_of_passages

    def score(self, question_words, position, method):
        """Score the passage at one position in the corpus by the named method."""
        passage_words = self.word_lists[position]
        if method == "counts":
            return count_score(question_words, passage_words)
        if method == "tfidf":
            return tf_idf_score(question_words, passage_words,
                                self.frequencies, self.number_of_passages)
        if method == "bm25":
            return bm25_score(question_words, passage_words, self.frequencies,
                              self.number_of_passages, self.average_length)
        raise ValueError(f"Unknown method: {method}")

    def rank(self, question, method, how_many=3):
        """
        Return the best passages for a question, highest score first.

        Passages scoring zero are left out; equal scores keep corpus order.
        """
        question_words = search_words(question)
        scored = []
        for position in range(self.number_of_passages):
            score = self.score(question_words, position, method)
            if score > 0:
                scored.append((score, position))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        best = []
        for score, position in scored[:how_many]:
            best.append(self.passages[position])
        return best
```

### 3.6.3 Annotations

- `class KeywordIndex:` defines a class. `index = KeywordIndex(passages)` builds one **object** of it; Python runs `__init__` to fill in its data.
- `self` is the object itself. `self.word_lists` is data stored in the object, so `rank` can use it later without splitting the passages again.
- A function inside a class is called a **method**: `index.rank(question, "bm25")`.
- The argument `method` (not to be confused with a class's methods) names the score to use. One `rank` function serves all three scores, so 3.8 can compare them on equal terms.
- `raise ValueError(...)` stops with an error message if the name is not one of the three. A misspelt name fails loudly instead of returning nothing.
- `range(self.number_of_passages)` counts 0, 1, 2 … up to 47: the position of each passage.

## 3.7 Checking against bm25s, and what Elasticsearch does

### 3.7.1 Principles

A formula typed by hand can hide a mistake. One check is to compare it with a published library that implements the same formula. **bm25s** is a small Python library for BM25 under the MIT licence.

Given the same words, the hand-built BM25 and bm25s put the same three passages in the same order for all 32 definition questions. A test checks this on every change (3.10).

bm25s's "lucene" method follows **Lucene**, the search library inside **Elasticsearch**. BM25 is Elasticsearch's default way of scoring text. So this section is, at small scale, what Elasticsearch does over millions of documents. There are two small differences. Lucene leaves out the (k1 + 1) at the top of the fraction in 3.5; that scales every score by the same number, so the order of passages does not change. And Elasticsearch's default k1 is 1.2, not 1.5, which can change the order slightly.

### 3.7.2 Code

`ragbook/ch03_keyword_search.py`, function `bm25s_rank`

```python
def bm25s_rank(passages, question, how_many=3):
    """
    Rank passages with the bm25s library, using this chapter's words.

    bm25s implements the same formula ("lucene" method). Giving it the same
    word lists lets the two be compared fairly.

    Example:
        bm25s_rank(load_corpus(), "What is the GDP deflator?")
        returns the same three passages as KeywordIndex.rank(..., "bm25")
    """
    import bm25s

    word_lists = []
    for passage in passages:
        word_lists.append(search_words(passage["text"]))
    retriever = bm25s.BM25(k1=1.5, b=0.75, method="lucene")
    retriever.index(word_lists, show_progress=False)

    question_words = []
    for word in search_words(question):
        if word not in question_words:
            question_words.append(word)
    known_words = set()
    for words in word_lists:
        known_words.update(words)
    question_words = [word for word in question_words if word in known_words]
    if question_words == []:
        return []

    positions, scores = retriever.retrieve([question_words], k=how_many, show_progress=False)
    best = []
    for position, score in zip(positions[0], scores[0]):
        if score > 0:
            best.append(passages[int(position)])
    return best
```

### 3.7.3 Annotations

- `import bm25s` sits inside the function, so the rest of the chapter runs even where bm25s is not installed.
- `retriever.index(word_lists)` builds bm25s's own index from this chapter's word lists, so both methods see exactly the same words.
- bm25s cannot score a word it has never seen, so the question keeps only words found somewhere in the corpus. If none are left, no passage matches.
- `retriever.retrieve` returns two lists: the positions of the best passages and their scores. `zip` walks through both together.
- `int(position)` turns bm25s's number type into an ordinary Python whole number, so it can pick a passage from the list.

## 3.8 Measuring: from 25 to 30 of 32

### 3.8.1 Principles

Each definition question (class Q2) in the question bank lists its **gold passages**: the passages a correct answer should rest on. The measure used since Chapter 2 counts the questions for which at least one gold passage is in the top three.

| Method | Questions with a gold passage in the top three | Questions missed |
| --- | --- | --- |
| Chapter 2: shared topic words | 25 of 32 | 7 |
| Word counts | 28 of 32 | q2-04, q2-21, q2-26, q2-30 |
| TF-IDF | 30 of 32 | q2-04, q2-30 |
| BM25 | 30 of 32 | q2-04, q2-30 |

Each step fixes a fault named earlier, and word counts also show the fault they bring:

- **Word counts** find four questions Chapter 2 missed, among them the GDP deflator (q2-16, helped by the curly-quote fix) and consumption of fixed capital (q2-01). But they lose one Chapter 2 found: double deflation (q2-26). Long passages on PPPs that repeat some of the question's everyday words many times now crowd out the right ones.
- **TF-IDF** wins back double deflation and adds remittances (q2-21): the rare word "remittances" now outweighs "national" and "income".
- **BM25** finds the same 30 questions as TF-IDF. Marking down long passages still shows: for labour input (q2-31), the definition esa10-11.27 rises from fifth place to second.

The two questions BM25 still misses show the limit of matching words:

- **What is the difference between GDP and GNI? (q2-04).** The gold passage, esa10-8.94, writes "gross national income" in full; the letters "GNI" never appear in it. Asked with the full name, the same passage comes second. Matching words cannot know that GNI and gross national income are the same thing. Chapter 5 adds that knowledge from the knowledge graph.
- **Why can real GDP growth and comparisons at PPP tell different stories about two economies? (q2-30).** The question is long and most of its words ("tell", "stories", "different", "two") are not about national accounts. The answer rests on links between ideas (the terms of trade, and how PPPs are carried forward between benchmark years), not on shared words.

Three points about this measure. It checks only the top three, not whether the answer is right. It uses gold passages chosen by the author. And 32 questions are few: one question is about three percentage points. Chapter 10 adds stricter measures.

### 3.8.2 Code

`ragbook/ch03_keyword_search.py`, functions `load_questions` and `top_three_hits`

```python
def load_questions(file_path=QUESTION_FILE, question_class="Q2"):
    """
    Read the questions of one class from the question bank.

    Class Q2 holds the definition questions, each with its gold passages:
    the passages a correct answer should rest on.

    Example:
        len(load_questions()) returns 32
    """
    chosen = []
    for question in load_passages(file_path):
        if question["class"] == question_class:
            chosen.append(question)
    return chosen
```

```python
def top_three_hits(rank_function, questions):
    """
    Count the questions for which at least one gold passage is in the top three.

    rank_function takes a question and returns a ranked list of passages.

    Example:
        top_three_hits(lambda q: index.rank(q, "bm25"), load_questions())
        returns the number of hits out of 32
    """
    hits = 0
    for question in questions:
        found_ids = []
        for passage in rank_function(question["question"]):
            found_ids.append(passage["id"])
        for gold_id in question["gold_passages"]:
            if gold_id in found_ids:
                hits = hits + 1
                break
    return hits
```

### 3.8.3 Annotations

- `load_passages` (Chapter 1) reads any JSON Lines file, so it reads the question bank as well as the corpus.
- `rank_function` is a function passed as an argument, as `ask` was in Chapter 2 (2.6.3). Any ranking method can be measured the same way.
- `lambda q: index.rank(q, "bm25")`, in the docstring above, is a one-line function that ranks a question by BM25.
- `break` leaves the inner loop at the first gold passage found, so a question counts once however many gold passages it finds.

## 3.9 Running the worked example

From the repository folder, run:

```text
python -m ragbook.ch03_keyword_search
```

The output (no language model is used in this chapter, so it is the same on every computer):

```text
3.2  Words, cleaned properly
     ['gdp', 'deflator']

3.6  What is the GDP deflator?  (counts)
     [una14-ch1-deflator] OECD, Understanding National Accounts, Chapter 1, p. 22, partial
     [bea-ch4-chained] US Bureau of Economic Analysis, NIPA Handbook, Chapter 4: Estimating Methods, “Chained-dollar measures”
     [wb13-mccarthy-ipd] World Bank, Measuring the Real Size of the World Economy: The Framework, Methodology, and Results of the International Comparison Program (ICP), Chapter 18 (Paul McCarthy), section “Consistency between Time and Space”

3.6  What is the GDP deflator?  (tfidf)
     [esa10-10.47] Eurostat, European System of Accounts (ESA 2010), para. 10.47 (part)
     [una14-ch1-deflator] OECD, Understanding National Accounts, Chapter 1, p. 22, partial
     [bea-ch4-chained] US Bureau of Economic Analysis, NIPA Handbook, Chapter 4: Estimating Methods, “Chained-dollar measures”

3.6  What is the GDP deflator?  (bm25)
     [una14-ch1-deflator] OECD, Understanding National Accounts, Chapter 1, p. 22, partial
     [esa10-10.47] Eurostat, European System of Accounts (ESA 2010), para. 10.47 (part)
     [cso-gnistar-2] Central Statistics Office Ireland, Modified GNI, paragraph 2

3.7  Hand-built BM25 and bm25s agree on the top three: True

3.8  Questions with a correct passage in the top three (of 32)
     counts  28
     tfidf   30
     bm25    30
```

For the GDP deflator question, word counts put the right passage first, but fill the other places with passages that merely say "GDP" often: five times in bea-ch4-chained, four in wb13-mccarthy-ipd. TF-IDF lets esa10-10.47 overtake it, because that passage uses the rare word "deflator" three times. BM25 limits the reward for repeats, so the passage written about the GDP deflator is first again.

## 3.10 Tests, glossary and links

### 3.10.1 Tests

The file `tests/test_ch03_keyword_search.py` holds 13 tests. Retrieval is tested exactly: if a change to the code or the corpus moves a ranking or a count reported in this chapter, a test fails. Run them with `python -m pytest tests/test_ch03_keyword_search.py -v`.

| Test | What it proves |
| --- | --- |
| `search_words` removes curly quotes and common words | “GDP deflator” gives `gdp`, `deflator`; "country’s" gives `country` |
| `search_words` keeps repeats | "GDP and GDP" gives `gdp` twice |
| `count_words` counts each word | The dictionary of counts is right |
| `count_score` adds each question word once | A repeated question word does not count twice |
| `document_frequencies` counts passages, not appearances | Five uses in one passage add one |
| TF-IDF gives nothing to a word in every passage | IDF is log(1) = 0 |
| BM25: repeats count for less | Five appearances score less than five times one |
| BM25: long passages are marked down | The same word in a longer passage scores less |
| Corpus frequencies quoted in 3.4 | "gdp" in 18 passages, "deflator" in 2 |
| BM25 ranks the deflator passage first | The ranking shown in 3.9 |
| Hand-built BM25 matches bm25s on all 32 questions | The formula in 3.5 is typed correctly |
| Top-three counts reported in 3.8 | 28, 30 and 30 of 32 |
| An unknown method is refused | A misspelt method name fails loudly |

### 3.10.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Term frequency (TF) | How often a word appears in one passage |
| Document frequency | How many passages contain a word at least once |
| Inverse document frequency (IDF) | A weight that is large for rare words and zero for words in every passage: log(N ÷ n) |
| TF-IDF | A score that multiplies term frequency by inverse document frequency |
| BM25 | A score that refines TF-IDF: repeats count for less and less, and long passages are marked down |
| Index | Data about the corpus worked out once and kept, so each search is quick |
| Class | A bundle of data and the functions that use it |
| Object | One example of a class, built with its data |
| Method (of a class) | A function that belongs to a class |
| Lucene | The open-source search library inside Elasticsearch and OpenSearch |
| Elasticsearch | A search engine for large collections of documents; scores text with BM25 by default |

### 3.10.3 Links

- [bm25s on GitHub (MIT licence)](https://github.com/xhluca/bm25s)
- [Robertson and Zaragoza (2009), "The Probabilistic Relevance Framework: BM25 and Beyond"](https://doi.org/10.1561/1500000019)
- [Elasticsearch: similarity settings (BM25 is the default)](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html)
- [Python `math` module](https://docs.python.org/3/library/math.html)
- [Python tutorial: classes](https://docs.python.org/3/tutorial/classes.html)
- [Chapter 3 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch03_keyword_search.py)
