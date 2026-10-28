"""
Chapter 4 — Embeddings and semantic search

What this file does
    Ranks passages by meaning rather than by shared words. An embedding
    model turns each passage, and the question, into a list of 384 numbers
    (an embedding); passages whose embeddings point in nearly the same
    direction as the question's are ranked first. The direction is compared
    with cosine similarity, written first by hand and then with numpy. The
    chapter measures how often a correct passage is in the top three, against
    BM25's 30 of 32 from Chapter 3.

Inputs
    The corpus (data/corpus/passages.jsonl) and the question bank
    (data/question_bank/questions.jsonl).

Outputs
    Ranked lists of passages; the embeddings saved to
    data/embeddings/all-MiniLM-L6-v2.npz, so later chapters and the tests
    can use them without running the model.

Used by
    Chapter 5 (hybrid search), Chapter 7 (vector databases) and Chapter 10
    (measuring retrieval).

Uses
    Chapter 2 (load_corpus); Chapter 3 (KeywordIndex, load_questions,
    top_three_hits).
    Python's math module; numpy; the sentence-transformers library and the
    all-MiniLM-L6-v2 model (section 4.4).

Run the worked example
    python -m ragbook.ch04_semantic_search
    The first run downloads the model (about 90 MB) from Hugging Face.
"""

import math
from pathlib import Path

import numpy as np

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import KeywordIndex, load_questions, top_three_hits

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_FILE = Path(__file__).parent.parent / "data" / "embeddings" / "all-MiniLM-L6-v2.npz"


# ---------------------------------------------------------------------------
# 4.3  Cosine similarity, by hand
# ---------------------------------------------------------------------------

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


def vector_length(a):
    """
    The length of a list of numbers seen as an arrow: the square root of the
    sum of the squares.

    Example:
        vector_length([3, 4])
        returns 5.0
    """
    return math.sqrt(dot_product(a, a))


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


# ---------------------------------------------------------------------------
# 4.3  The same, with numpy, for every passage at once
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 4.4  The embedding model
# ---------------------------------------------------------------------------

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


def embed_texts(model, texts):
    """
    Turn a list of texts into embeddings: one row of 384 numbers per text.

    Example:
        embed_texts(model, ["What is GDP?"]).shape
        returns (1, 384)
    """
    return model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)


# ---------------------------------------------------------------------------
# 4.5  Saving embeddings, so the model runs once
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 4.6  Ranking passages by meaning
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

def main():
    passages = load_corpus()
    questions = load_questions()

    print("4.3  Cosine similarity by hand")
    print("     same direction:", cosine_similarity([1, 0], [2, 0]))
    print("     at right angles:", cosine_similarity([1, 0], [0, 3]))

    print(f"\n4.4  Loading {MODEL_NAME} (the first run downloads it)")
    model = load_model()
    passage_vectors = embed_texts(model, [passage["text"] for passage in passages])
    question_vectors = embed_texts(model, [question["question"] for question in questions])
    print("     passage embeddings:", passage_vectors.shape)
    print("     first five numbers of the first passage:", np.round(passage_vectors[0][:5], 3))

    ids = [passage["id"] for passage in passages] + [question["id"] for question in questions]
    save_embeddings(EMBEDDING_FILE, ids, np.vstack([passage_vectors, question_vectors]))
    print(f"\n4.5  Saved to {EMBEDDING_FILE.relative_to(EMBEDDING_FILE.parent.parent.parent)}")

    index = SemanticIndex(passages, passage_vectors,
                          lambda question: embed_texts(model, [question])[0])
    example = "What is the GDP deflator?"
    print(f"\n4.6  {example}")
    for passage, score in zip(index.rank(example), sorted(index.similarities(example), reverse=True)):
        print(f"     {score:.3f}  [{passage['id']}] {passage['source']}, {passage['reference']}")

    hits = top_three_hits(index.rank, questions)
    keyword_index = KeywordIndex(passages)
    bm25_hits = top_three_hits(lambda q: keyword_index.rank(q, "bm25"), questions)
    print(f"\n4.7  Questions with a correct passage in the top three: {hits} of {len(questions)}"
          f" (BM25 in Chapter 3: {bm25_hits})")


if __name__ == "__main__":
    main()
