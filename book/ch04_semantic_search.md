# Chapter 4 — Embeddings and semantic search

## 4.1 What this chapter builds

Chapter 3 found passages by the words they share with the question. This chapter finds them by meaning: a passage can match a question with which it shares no words.

1. **Embeddings** (4.2): a model turns each text into a list of 384 numbers, so that texts with similar meanings get similar lists.
2. **Cosine similarity** (4.3): a measure of how closely two lists point the same way, written by hand and then with numpy.
3. **The model** (4.4): all-MiniLM-L6-v2, run with the sentence-transformers library on the laptop's main processor.
4. **Saving and ranking** (4.5, 4.6): the embeddings are worked out once and saved; each question is then compared with every passage.

Semantic search is measured on the same 32 definition questions as Chapter 3 (4.7).

| Method | Definition questions with a correct passage in the top three |
| --- | --- |
| Chapter 3: BM25 | 30 of 32 |
| Semantic search | 30 of 32 |

The two methods miss different questions. Chapter 5 combines them.

**Code file:** `ragbook/ch04_semantic_search.py`

**Uses:** Chapter 2 (`load_corpus`); Chapter 3 (`load_questions`, `top_three_hits`); Python's `math` module; numpy (BSD licence); sentence-transformers (Apache 2.0 licence), which installs torch. Install them with `pip install -r requirements.txt`.

## 4.2 What an embedding is

### 4.2.1 Principles

An **embedding** is a fixed-length list of numbers that stands for a piece of text. The model used here gives 384 numbers for any text, whether three words or two hundred.

The numbers are not chosen by hand. The model was trained on many pairs of texts that mean the same thing, such as a question and its answer. Training adjusted it until the two texts of a pair got similar lists, and unrelated texts got different ones.

So each list can be read as an arrow in a space with 384 directions. Texts with similar meanings point roughly the same way. No single number means anything on its own: meaning sits in the direction of the whole list.

This is why semantic search can match words that differ. A question about "GNI" and a passage about "gross national income" share no words, but if the model learned that the two are used alike, their arrows point close together. Keyword search (Chapter 3) cannot do this.

Two limits follow from how embeddings are made:

- **The model knows what it was trained on.** all-MiniLM-L6-v2 learned from general English text, not from national accounts manuals. It may treat two technical terms as close because they appear in similar sentences, not because they mean the same thing.
- **An embedding is a summary.** Two hundred words become 384 numbers. Detail is lost, and a passage that says many things is pulled towards its average.

There is no code in this section: 4.3 measures direction, and 4.4 makes the embeddings.

## 4.3 Cosine similarity

### 4.3.1 Principles

To compare two embeddings, measure the angle between their arrows. **Cosine similarity** is the cosine of that angle:

```latex
\cos\theta = \frac{a \cdot b}{\lVert a \rVert \, \lVert b \rVert}
```

- The **dot product** a · b multiplies the two lists position by position and adds the results.
- The **length** of a list, written ‖a‖, is the square root of its dot product with itself (Pythagoras, in 384 directions).
- Dividing by both lengths removes length, so only direction counts.

The result runs from −1 to 1. Arrows pointing the same way give 1; at right angles, 0; opposite, −1. A score is a ranking aid, not a probability: 0.62 does not mean "62% relevant", and no threshold stops a model from inventing an answer.

The hand-written version loops over 384 numbers for each passage. numpy, a library for tables of numbers, does the same for all 56 passages in one step, and the two give the same answers (a test checks this, 4.9).

### 4.3.2 Code

`ragbook/ch04_semantic_search.py`, functions `dot_product`, `vector_length`, `cosine_similarity` and `cosine_similarities`

```python
def dot_product(a, b):
    """
    Multiply two lists of numbers position by position and add the results.

    Example:
        dot_product([1, 2, 3], [4, 5, 6])
        returns 1*4 + 2*5 + 3*6 = 32
    """
    total = 0.0
    for x, y in zip(a, b):
        total = total + x * y
    return total
```

```python
def vector_length(a):
    """
    The length of a list of numbers seen as an arrow: the square root of the
    sum of the squares.

    Example:
        vector_length([3, 4])
        returns 5.0
    """
    return math.sqrt(dot_product(a, a))
```

```python
def cosine_similarity(a, b):
    """
    How closely two embeddings point in the same direction.

    The dot product divided by both lengths. It runs from -1 (opposite
    directions) through 0 (unrelated) to 1 (the same direction). Length is
    divided out, so only direction counts.

    Example:
        cosine_similarity([1, 0], [2, 0]) returns 1.0  (same direction)
        cosine_similarity([1, 0], [0, 3]) returns 0.0  (at right angles)
    """
    return dot_product(a, b) / (vector_length(a) * vector_length(b))
```

```python
def cosine_similarities(passage_vectors, question_vector):
    """
    Cosine similarity between one question and every passage, in one step.

    passage_vectors is a numpy table with one row per passage; question_vector
    is one row. Each row is divided by its length first, so a plain dot
    product then gives the cosine similarity.

    Example:
        cosine_similarities(np.array([[1, 0], [0, 3]]), np.array([2, 0]))
        returns array([1., 0.])
    """
    passage_vectors = np.asarray(passage_vectors, dtype=float)
    question_vector = np.asarray(question_vector, dtype=float)
    passage_lengths = np.linalg.norm(passage_vectors, axis=1)
    question_length = np.linalg.norm(question_vector)
    return passage_vectors @ question_vector / (passage_lengths * question_length)
```

### 4.3.3 Annotations

- `zip(a, b)` pairs the two lists position by position, as in Chapter 3 (3.7.3).
- `math.sqrt` is the square root, from Python's `math` module.
- `np.asarray(..., dtype=float)` turns a list of lists into a numpy **array**: a table of numbers numpy can work on all at once.
- `np.linalg.norm(passage_vectors, axis=1)` gives the length of each row; `axis=1` means "along each row".
- `@` is numpy's matrix product: each passage row's dot product with the question, 56 results in one step.
- Dividing one array by another divides position by position, so each passage's dot product is divided by its own length.

## 4.4 The embedding model

### 4.4.1 Principles

A **transformer** is the kind of model behind both language models and embedding models. It reads text as **word pieces** (whole words, or parts of rarer words) and produces one list of numbers per piece.

A **sentence transformer** adds one step: it averages the pieces' lists into a single list for the whole text, and is trained so that whole texts with the same meaning get close lists. The method was published by Reimers and Gurevych in 2019 (4.9.3).

**sentence-transformers** is the Python library that loads and runs these models. It is open source (Apache 2.0) and now maintained by Hugging Face. It also provides the reranker used in Chapter 9, so it is installed once for both chapters. It needs **torch**, the library that does the arithmetic inside the model; on a laptop without a graphics card, torch runs on the main processor (CPU).

The model is **all-MiniLM-L6-v2** (Apache 2.0):

| Property | Value |
| --- | --- |
| Numbers per text (dimensions) | 384 |
| Size | about 22 million parameters; a 91 MB download |
| Longest text read | 256 word pieces; anything longer is cut off without warning |

Some notes say this model gives 768 numbers. It gives 384; 768 belongs to larger models.

The longest passage in the corpus has 180 words, close to the 256-piece limit. Chapter 6, on cutting manuals into passages, checks whether any passage is cut off.

The first run downloads the model from Hugging Face and keeps a copy in the user's folder (`.cache/huggingface`). Later runs need no internet connection.

### 4.4.2 Code

`ragbook/ch04_semantic_search.py`, the name `MODEL_NAME` and the functions `load_model` and `embed_texts`

```python
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
```

```python
def load_model(model_name=MODEL_NAME):
    """
    Load the embedding model on the computer's main processor (CPU).

    The first call downloads the model from Hugging Face and keeps a copy;
    later calls use the copy and need no internet connection.

    Example:
        model = load_model()
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")
```

```python
def embed_texts(model, texts):
    """
    Turn a list of texts into embeddings: one row of 384 numbers per text.

    Example:
        embed_texts(model, ["What is GDP?"]).shape
        returns (1, 384)
    """
    return model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
```

### 4.4.3 Annotations

- The import sits inside `load_model`, as bm25s did in Chapter 3 (3.7.3), so the rest of the chapter and its tests run without sentence-transformers.
- `device="cpu"` keeps the model on the main processor, so the code behaves the same on every laptop.
- `model.encode` embeds a whole list at once, which is faster than one text at a time.
- `convert_to_numpy=True` returns a numpy array rather than torch's own type, so 4.3's functions can use it directly.
- `.shape` gives an array's size as (rows, columns): one row per text, 384 columns.

## 4.5 Saving embeddings, so the model runs once

### 4.5.1 Principles

A passage's embedding changes only if the passage or the model changes. So the embeddings are worked out once and saved in one file, `data/embeddings/all-MiniLM-L6-v2.npz`, with the id of each passage and question beside its numbers.

The file also records the model's name. Embeddings from different models cannot be compared: each model has its own space, and a question embedded by one model means nothing against passages embedded by another.

The saved file has two further uses. The tests (4.9) read it, so they check the reported results without running the model. And Chapter 7 loads it into a vector database instead of embedding the corpus again.

### 4.5.2 Code

`ragbook/ch04_semantic_search.py`, the name `EMBEDDING_FILE` and the functions `save_embeddings` and `load_embeddings`

```python
EMBEDDING_FILE = Path(__file__).parent.parent / "data" / "embeddings" / "all-MiniLM-L6-v2.npz"
```

```python
def save_embeddings(file_path, ids, vectors, model_name=MODEL_NAME):
    """
    Save embeddings and the ids they belong to in one numpy file.

    The model name is saved too, so embeddings from different models are
    never mixed.

    Example:
        save_embeddings(EMBEDDING_FILE, ["q2-01"], vectors)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(file_path, ids=np.array(ids), vectors=np.asarray(vectors, dtype=np.float32),
             model_name=np.array(model_name))
```

```python
def load_embeddings(file_path=EMBEDDING_FILE):
    """
    Read saved embeddings back as a dictionary: id -> row of numbers.

    Example:
        load_embeddings()["sna08-2.144"].shape
        returns (384,)
    """
    saved = np.load(file_path)
    embeddings = {}
    for item_id, vector in zip(saved["ids"], saved["vectors"]):
        embeddings[str(item_id)] = vector
    return embeddings
```

### 4.5.3 Annotations

- `Path(__file__).parent.parent` is the repository folder, as in Chapter 3's `QUESTION_FILE`; `/` joins folder names into a path.
- `mkdir(parents=True, exist_ok=True)` creates the folder if it is missing and does nothing if it exists.
- `np.savez` saves several named arrays in one `.npz` file; `np.load` reads them back by name.
- `np.float32` stores each number in 4 bytes rather than 8. The model itself works at this precision, so nothing is lost, and the file is half the size.
- `str(item_id)` turns numpy's text type back into an ordinary Python string, so ids match those in the corpus.

## 4.6 Ranking passages by meaning

### 4.6.1 Principles

Ranking by meaning has three steps: embed the question, compute its cosine similarity with every passage, and keep the highest.

Two differences from keyword search (Chapter 3, 3.6):

- **Every passage gets a score.** A passage sharing no word with the question still has an angle to it. Keyword search left out passages scoring zero; semantic search always returns three, even for a question the corpus cannot answer. Chapter 14 deals with that.
- **The question needs the model too.** `SemanticIndex` takes a function, `embed_question`, that turns a question into an embedding. In use it calls the model; in the tests it reads the saved file. The ranking code is the same in both.

### 4.6.2 Code

`ragbook/ch04_semantic_search.py`, class `SemanticIndex`

```python
class SemanticIndex:
    """
    The corpus with one embedding per passage, ready to rank by meaning.

    embed_question is a function that turns a question into an embedding.
    In use it calls the model; in the tests it reads saved embeddings, so the
    tests need no model.

    Example:
        index = SemanticIndex(passages, passage_vectors, embed_question)
        index.rank("What is the GDP deflator?", how_many=3)
        returns the three passages closest in meaning
    """

    def __init__(self, passages, passage_vectors, embed_question):
        self.passages = passages
        self.passage_vectors = np.asarray(passage_vectors, dtype=float)
        self.embed_question = embed_question

    def similarities(self, question):
        """Cosine similarity between the question and each passage, in corpus order."""
        return cosine_similarities(self.passage_vectors, self.embed_question(question))

    def rank(self, question, how_many=3):
        """
        Return the passages closest in meaning to the question, closest first.

        Every passage gets a score, so unlike keyword search none is left out;
        equal scores keep corpus order.
        """
        scores = self.similarities(question)
        order = sorted(range(len(self.passages)), key=lambda position: -scores[position])
        best = []
        for position in order[:how_many]:
            best.append(self.passages[position])
        return best
```

### 4.6.3 Annotations

- `self.embed_question` stores a function in the object, as data. `self.embed_question(question)` then calls it.
- `sorted(range(...), key=...)` sorts the passage positions 0 to 47 by their scores. `-scores[position]` puts the highest score first.
- `sorted` keeps the original order of items with equal keys, so equal scores keep corpus order, as in Chapter 3.
- `order[:how_many]` keeps the first three positions; the loop turns them back into passages.
- `rank` takes a question and returns passages, the same shape as Chapter 3's rankings, so `top_three_hits` measures it unchanged (4.7).

## 4.7 Measuring: 30 of 32, and different misses

### 4.7.1 Principles

The measure is Chapter 3's: the number of definition questions with at least one gold passage in the top three. `top_three_hits` takes any ranking function, so it measures `SemanticIndex.rank` unchanged.

| Method | Questions with a gold passage in the top three | Questions missed |
| --- | --- | --- |
| BM25 (Chapter 3) | 30 of 32 | q2-04, q2-30 |
| Semantic search | 30 of 32 | q2-24, q2-31 |

The headline is one question short of BM25. The more useful finding is that the two methods miss different questions.

**What is the difference between GDP and GNI? (q2-04).** BM25 missed it because the gold passages never write "GNI". Semantic search ranks bea-ch2-gnp second (similarity 0.728). That passage says GNP equals GDP minus net income paid abroad: it answers the question without sharing its key word. But the other gold passage, esa10-8.94, which writes "gross national income" in full, comes only twelfth (0.495). The model did not reliably treat "GNI" and "gross national income" as the same thing. Chapter 5 adds that knowledge from the knowledge graph.

**Why can real GDP growth and comparisons at PPP tell different stories about two economies? (q2-30).** Semantic search ranks wb13-mccarthy-space-time first (0.648): McCarthy explains that PPPs compare countries at one time and national accounts compare one country over time, and that both cannot be kept consistent. That is half the answer. The passages on the terms of trade, the other half, come 12th and 43rd.

**What is the best measure of labour input for comparing productivity? (q2-31).** The gold passage, esa10-11.27 on hours worked, comes fifth. Above it are esa10-10.33 on measuring output with a single indicator, sna25-16.95 on the quality of hours worked, and the two ONS passages on public-sector productivity. All are close to the topic; only esa10-11.27 defines the measure. A larger corpus gives more passages close to the topic to compete for three places.

**Is net domestic product a better measure than GDP? (q2-24).** BM25 finds it; semantic search does not. Its top three are passages about GDP and other measures in general. The passage that gives the judgement, sna25-A4.10 ("the conceptually preferred measure of economic growth"), comes eighth (0.561). Close in meaning to the question is not the same as answering it.

The pattern is general: keyword search is exact on terms the question names; semantic search finds passages written in other words, but can drift to the topic. Chapter 5 combines the two rankings.

The caveats of Chapter 3 (3.8.1) still apply: three places only, gold passages chosen by the author, and 32 questions, so one question is about three percentage points.

### 4.7.2 Code

No new function. The worked example (4.8) measures with Chapter 3's `top_three_hits`:

```text
hits = top_three_hits(index.rank, questions)
```

### 4.7.3 Annotations

- `index.rank` is passed without brackets: the function itself, not its result. `top_three_hits` calls it once per question.
- The similarity figures in this section come from the saved embeddings, so anyone running the code gets the same numbers.

## 4.8 Running the worked example

From the repository folder, install the packages once and run the chapter:

```text
pip install -r requirements.txt
python -m ragbook.ch04_semantic_search
```

The output from the test laptop (Windows, Python 3.14, CPU only), 21 October 2026, without the download messages of the first run:

```text
4.3  Cosine similarity by hand
     same direction: 1.0
     at right angles: 0.0

4.4  Loading sentence-transformers/all-MiniLM-L6-v2 (the first run downloads it)
     passage embeddings: (56, 384)
     first five numbers of the first passage: [-0.031 -0.014  0.059 -0.01   0.018]

4.5  Saved to data\embeddings\all-MiniLM-L6-v2.npz

4.6  What is the GDP deflator?
     0.621  [esa10-8.89] Eurostat, European System of Accounts (ESA 2010), para. 8.89
     0.589  [bea-ch2-gnp] US Bureau of Economic Analysis, NIPA Handbook, Chapter 2: Fundamental Concepts
     0.583  [una14-ch1-deflator] OECD, Understanding National Accounts, Chapter 1, p. 22, partial

4.7  Questions with a correct passage in the top three: 30 of 32 (BM25 in Chapter 3: 30)
```

The first five of the 384 numbers show that no single number means anything to a reader; only comparisons between embeddings do.

For the GDP deflator question, BM25 put una14-ch1-deflator first, because it uses the word "deflator". Semantic search puts it third, behind two passages about GDP and how it is measured. All three scores sit between 0.58 and 0.63: close in meaning, with no sharp winner. The gold passage is still in the top three, so the question counts as a hit.

The first run also prints warnings on Windows: that the download cache cannot use shortcuts (it keeps full copies instead), and that no Hugging Face token is set (downloads are slower). Neither affects the results.

Other computers may give slightly different numbers in the last decimal places; the saved file fixes the numbers used in this chapter.

## 4.9 Tests, glossary and links

### 4.9.1 Tests

The file `tests/test_ch04_semantic_search.py` holds 12 tests. The first eight use small hand-made vectors, so they run without the model. The last four read the saved embeddings and fix the results reported in this chapter. Run them with `python -m pytest tests/test_ch04_semantic_search.py -v`.

| Test | What it proves |
| --- | --- |
| Dot product | [1, 2, 3] · [4, 5, 6] = 32 |
| Vector length | The length of [3, 4] is 5 |
| Cosine similarity runs from −1 to 1 | Same direction 1, right angles 0, opposite −1 |
| Cosine similarity ignores length | [1, 2] and [10, 20] score 1 |
| numpy version matches the hand version | 4.3's two versions give the same answers |
| Ranking puts the closest direction first | A small three-passage example ranks correctly |
| Equal scores keep corpus order | Ties are broken the same way as in Chapter 3 |
| Saving and loading round trip | Ids, numbers and the model name come back unchanged |
| Saved embeddings cover the corpus and questions | All 56 passages (384 numbers each) and 32 questions |
| 30 of 32 questions | The count reported in 4.7 |
| Semantic search misses q2-24 and q2-31 | The different misses reported in 4.7 |
| Deflator ranking | The ranking shown in 4.8 |

### 4.9.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Embedding | A fixed-length list of numbers that stands for a text; similar meanings give similar lists |
| Dimensions | How many numbers an embedding has: 384 for all-MiniLM-L6-v2 |
| Dot product | Two lists multiplied position by position and the results added |
| Vector length | The square root of a list's dot product with itself |
| Cosine similarity | The dot product divided by both lengths: how closely two embeddings point the same way, from −1 to 1 |
| Semantic search | Ranking passages by the similarity of their embeddings to the question's |
| Transformer | The kind of model behind language models and embedding models |
| Word piece | A whole word, or part of a rarer word, as a transformer reads it |
| Sentence transformer | A transformer trained to give one embedding for a whole text |
| Array | numpy's table of numbers, worked on all at once |

### 4.9.3 Links

- [sentence-transformers documentation](https://sbert.net)
- [sentence-transformers on GitHub (Apache 2.0 licence)](https://github.com/huggingface/sentence-transformers)
- [all-MiniLM-L6-v2 model card (Apache 2.0 licence)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Reimers and Gurevych (2019), "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"](https://arxiv.org/abs/1908.10084)
- [numpy documentation](https://numpy.org/doc/stable/)
- [PyTorch (torch)](https://pytorch.org)
- [Chapter 4 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch04_semantic_search.py)
