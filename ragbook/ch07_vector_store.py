"""
Chapter 7 — Vector databases

What this file does
    Measures how the time of an exact search grows with the number of
    embeddings. Builds two near-neighbour graphs by hand and searches them
    the way HNSW does, measuring how many true neighbours each finds and how
    many comparisons it needs. Stores the corpus in Chroma, a vector database,
    and checks that Chroma ranks passages as Chapter 4's exact search does.

Inputs
    Random embeddings made by the code (7.2, 7.3); the corpus, the
    question bank and the saved embeddings (data/embeddings/) (7.5, 7.6);
    the example PDF of Chapter 6 (7.7, on a computer with the model).

Outputs
    Times per search; recall and comparison counts; a Chroma database in
    the folder chroma_db/ (not committed; rebuilt from data/ when needed);
    ranked passages.

Used by
    Chapter 8 (filters and access rules) and Chapter 9 (reranking).

Uses
    Chapter 2 (load_corpus); Chapter 3 (load_questions); Chapter 4
    (cosine_similarities, SemanticIndex, load_embeddings, load_model,
    embed_texts); Chapter 5 (saved_question_embedder); Chapter 6 (chunking).
    numpy; chromadb, the vector database; Python's time module.

Run the worked example
    python -m ragbook.ch07_vector_store
    python -m ragbook.ch07_vector_store --chunks
    The second embeds Chapter 6's chunks, so it needs the model (Chapter 4).
"""

import time
from pathlib import Path

import numpy as np

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import load_questions
from ragbook.ch04_semantic_search import SemanticIndex, cosine_similarities, load_embeddings
from ragbook.ch05_hybrid_search import saved_question_embedder

CHROMA_FOLDER = Path(__file__).parent.parent / "chroma_db"


# ---------------------------------------------------------------------------
# 7.2  Exact search and what it costs
# ---------------------------------------------------------------------------

def random_embeddings(how_many, dimensions=384, groups=50, spread=0.6, seed=42):
    """
    Make embeddings for testing: rows of numbers of length 1, in groups.

    Real embeddings are not scattered evenly: texts on one subject point in
    similar directions. So each row here is one of `groups` group centres
    plus some noise (`spread`), then scaled to length 1. The same `seed`
    always gives the same rows.

    Example:
        random_embeddings(1000).shape
        returns (1000, 384)
    """
    generator = np.random.default_rng(seed)
    centres = generator.normal(size=(groups, dimensions))
    centres = centres / np.linalg.norm(centres, axis=1, keepdims=True)
    group_of_row = generator.integers(0, groups, size=how_many)
    noise = generator.normal(scale=spread / np.sqrt(dimensions), size=(how_many, dimensions))
    rows = centres[group_of_row] + noise
    return (rows / np.linalg.norm(rows, axis=1, keepdims=True)).astype(np.float32)


def exact_search(vectors, query, how_many=10):
    """
    Return the rows of `vectors` most similar to `query`, most similar first.

    Every row is compared with the query (Chapter 4's cosine_similarities),
    so the answer is always right, and the work grows with the number of
    rows.

    Example:
        exact_search(np.array([[1, 0], [0, 1], [0.8, 0.6]]), np.array([1, 0]), 2)
        returns [0, 2]
    """
    similarities = cosine_similarities(vectors, query)
    order = np.argsort(-similarities, kind="stable")
    return [int(row) for row in order[:how_many]]


def time_exact_search(sizes, dimensions=384, queries=20):
    """
    Measure the average time of one exact search, in milliseconds, for each
    number of embeddings in `sizes`.

    Returns a list of (number of embeddings, milliseconds per search).
    Times depend on the computer; what matters is how they grow.

    Example:
        time_exact_search([1000, 10000])
        returns two pairs, the second about ten times slower
    """
    results = []
    for size in sizes:
        vectors = random_embeddings(size, dimensions)
        questions = random_embeddings(size + queries, dimensions)[size:]
        start = time.perf_counter()
        for query in questions:
            exact_search(vectors, query)
        seconds = time.perf_counter() - start
        results.append((size, 1000 * seconds / queries))
    return results


# ---------------------------------------------------------------------------
# 7.3  A near-neighbour graph, searched by hand
# ---------------------------------------------------------------------------

def nearest_neighbour_graph(vectors, neighbours=16):
    """
    Link each row to the `neighbours` other rows most similar to it.

    This looks like the right graph for a near-neighbour search, but when
    the rows form groups, every link stays inside its group: the graph
    falls apart into islands, and a search that starts in one island never
    reaches another (7.3).

    Example:
        nearest_neighbour_graph(vectors)[0]
        returns the 16 rows closest to row 0
    """
    graph = []
    for row in range(len(vectors)):
        similarities = vectors @ vectors[row]
        similarities[row] = -np.inf          # a row is not its own neighbour
        order = np.argsort(-similarities, kind="stable")
        graph.append([int(other) for other in order[:neighbours]])
    return graph


def navigable_graph(vectors, neighbours=16):
    """
    Build the graph as rows arrive: each new row links to the `neighbours`
    most similar rows already in the graph, and they link back.

    The first rows arrive when the graph is small, so their nearest rows
    are often in other groups: their links cross between groups. Later
    rows add short links inside groups. A search can then cross the
    collection in a few steps and finish among close neighbours. This is
    a navigable small world (NSW), the graph inside HNSW (7.4).

    Example:
        navigable_graph(vectors)[0]
        returns the rows linked to row 0, the first row added
    """
    graph = [[] for _ in range(len(vectors))]
    for row in range(1, len(vectors)):
        similarities = vectors[:row] @ vectors[row]
        for other in np.argsort(-similarities, kind="stable")[:neighbours]:
            graph[row].append(int(other))
            graph[int(other)].append(row)
    return graph


def graph_search(graph, vectors, query, how_many=10, candidates=50, start=0):
    """
    Find rows close to `query` by walking the graph from row `start`.

    The search keeps a list of the best rows found so far, at most
    `candidates` long. Each step takes the closest row not yet explored
    and compares the query with that row's neighbours; a neighbour closer
    than the worst on the list joins it. The search stops when no
    unexplored row on the list could improve it.

    A longer list (`candidates`) finds more of the true nearest rows and
    makes more comparisons. HNSW calls this length ef.

    Returns the `how_many` best rows found, closest first, and the number
    of comparisons made.

    Example:
        rows, comparisons = graph_search(graph, vectors, query)
        rows has 10 entries; comparisons is far fewer than len(vectors)
    """
    def similarity(row):
        return float(vectors[row] @ query)

    visited = {start}
    comparisons = 1
    best = [(similarity(start), start)]      # (similarity, row), at most `candidates` long
    to_explore = list(best)
    while to_explore:
        closest = max(to_explore)
        to_explore.remove(closest)
        if len(best) == candidates and closest[0] < min(best)[0]:
            break                            # nothing left on the list can help
        for neighbour in graph[closest[1]]:
            if neighbour in visited:
                continue
            visited.add(neighbour)
            comparisons += 1
            found = (similarity(neighbour), neighbour)
            if len(best) < candidates or found > min(best):
                best.append(found)
                to_explore.append(found)
                if len(best) > candidates:
                    best.remove(min(best))
    best.sort(reverse=True)
    return [row for _, row in best[:how_many]], comparisons


def recall(found, true):
    """
    The share of the true nearest rows that a search found, from 0 to 1.

    Example:
        recall([1, 2, 9], [1, 2, 3])
        returns 0.667 (two of three)
    """
    return len(set(found) & set(true)) / len(true)


def measure_graph_search(graph, vectors, queries, candidate_lengths=(10, 20, 50, 100), how_many=10):
    """
    For each list length, search the graph with every query and compare
    the result with exact search.

    Returns one row per length: (length, average recall, average
    comparisons).

    Example:
        measure_graph_search(graph, vectors, queries)[0]
        returns (10, recall at list length 10, comparisons at that length)
    """
    true_answers = [exact_search(vectors, query, how_many) for query in queries]
    results = []
    for length in candidate_lengths:
        recalls = []
        comparisons = []
        for query, true in zip(queries, true_answers):
            found, made = graph_search(graph, vectors, query, how_many, length)
            recalls.append(recall(found, true))
            comparisons.append(made)
        results.append((length, float(np.mean(recalls)), float(np.mean(comparisons))))
    return results


# ---------------------------------------------------------------------------
# 7.5  Storing the corpus in Chroma
# ---------------------------------------------------------------------------

def open_store(folder=CHROMA_FOLDER):
    """
    Open (or create) a Chroma database kept in a folder on this computer.

    Chroma runs inside this Python program: no server, no internet. The
    setting anonymized_telemetry=False stops it sending usage reports.

    Example:
        client = open_store()
    """
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=str(folder), settings=Settings(anonymized_telemetry=False))


# The facts stored beside each passage; Chapter 8 filters on them.
METADATA_FIELDS = ["source", "source_code", "reference", "edition", "scope", "licence"]


def store_passages(client, passages, embeddings, name="corpus"):
    """
    Put passages and their embeddings into a new Chroma collection.

    A collection is Chroma's name for one searchable set of embeddings.
    Any collection with the same name is deleted first, so the database
    always matches the corpus. The embeddings are given, so Chroma needs
    no model of its own ("embedding_function=None"). Similarity is cosine,
    as in Chapter 4.

    Example:
        collection = store_passages(client, passages, embeddings)
        collection.count()
        returns 57
    """
    if name in [collection.name for collection in client.list_collections()]:
        client.delete_collection(name)
    collection = client.create_collection(
        name,
        configuration={"hnsw": {"space": "cosine"}},
        embedding_function=None,
    )
    metadatas = []
    for passage in passages:
        metadatas.append({field: passage[field] for field in METADATA_FIELDS})
    collection.add(
        ids=[passage["id"] for passage in passages],
        embeddings=[embeddings[passage["id"]].tolist() for passage in passages],
        documents=[passage["text"] for passage in passages],
        metadatas=metadatas,
    )
    return collection


def search_store(collection, question_vector, how_many=3):
    """
    Return the stored passages closest to a question's embedding, closest
    first, each as a dictionary with its id, text, metadata and similarity.

    Chroma reports a distance: 1 minus the cosine similarity. It is turned
    back into a similarity so it can be compared with Chapter 4.

    Example:
        search_store(collection, question_vector)[0]["similarity"]
        returns about 0.7 for a close passage
    """
    answer = collection.query(query_embeddings=[np.asarray(question_vector).tolist()], n_results=how_many)
    results = []
    for passage_id, text, metadata, distance in zip(
        answer["ids"][0], answer["documents"][0], answer["metadatas"][0], answer["distances"][0]
    ):
        result = {"id": passage_id, "text": text, "similarity": 1 - distance}
        result.update(metadata)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# 7.6  Does Chroma agree with exact search?
# ---------------------------------------------------------------------------

def compare_with_exact(collection, semantic_index, questions, how_many=3):
    """
    For each question, compare Chroma's top passages with Chapter 4's exact
    ranking.

    Returns the number of questions with the same passages in the same
    order, and the ids of any that differ.

    Example:
        compare_with_exact(collection, semantic_index, questions)
        returns (32, []) when the two always agree
    """
    same = 0
    different = []
    for question in questions:
        exact_ids = [passage["id"] for passage in semantic_index.rank(question["question"], how_many)]
        vector = semantic_index.embed_question(question["question"])
        chroma_ids = [result["id"] for result in search_store(collection, vector, how_many)]
        if chroma_ids == exact_ids:
            same += 1
        else:
            different.append(question["id"])
    return same, different


def build_corpus_store(client):
    """
    Store the corpus with its saved embeddings, and build Chapter 4's exact
    index from the same embeddings for comparison.

    Returns the collection, the semantic index and the questions.
    """
    passages = load_corpus()
    questions = load_questions()
    saved = load_embeddings()
    collection = store_passages(client, passages, saved)
    vectors = [saved[passage["id"]] for passage in passages]
    semantic_index = SemanticIndex(passages, vectors, saved_question_embedder(questions, saved))
    return collection, semantic_index, questions


# ---------------------------------------------------------------------------
# 7.7  Chapter 6's chunks in Chroma
# ---------------------------------------------------------------------------

def store_chunks(client, chunks, model, name="mccarthy_ch18"):
    """
    Embed chunks with the model and store them in their own collection.

    Each chunk gets an id from its position ("chunk-0001"), and its section
    heading, the text before its first empty line (6.7), as metadata.

    Example:
        collection = store_chunks(client, chunks, load_model())
    """
    from ragbook.ch04_semantic_search import embed_texts

    if name in [collection.name for collection in client.list_collections()]:
        client.delete_collection(name)
    collection = client.create_collection(
        name,
        configuration={"hnsw": {"space": "cosine"}},
        embedding_function=None,
    )
    vectors = embed_texts(model, chunks)
    collection.add(
        ids=[f"chunk-{position:04d}" for position in range(1, len(chunks) + 1)],
        embeddings=vectors.tolist(),
        documents=chunks,
        metadatas=[{"heading": chunk.split("\n\n", 1)[0]} for chunk in chunks],
    )
    return collection


CHUNK_QUESTIONS = [
    "Why do PPPs extrapolated from one benchmark differ from the next benchmark?",
    "What is Eurostat's rolling benchmark approach?",
    "How does the Penn World Table produce PPPs for every year?",
]


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------

def main(chunks=False):
    print("7.2  Exact search: milliseconds per search")
    for size, milliseconds in time_exact_search([1_000, 10_000, 100_000]):
        print(f"     {size:>9,} embeddings  {milliseconds:8.2f} ms")

    print("\n7.3  Graph search on 5,000 embeddings (16 links per row)")
    rows = random_embeddings(5_100)
    vectors, queries = rows[:5_000], rows[5_000:]
    for label, graph in (("nearest neighbours only", nearest_neighbour_graph(vectors)),
                         ("built as rows arrive", navigable_graph(vectors))):
        print(f"     {label}")
        for length, average_recall, comparisons in measure_graph_search(graph, vectors, queries):
            print(f"       list length {length:>3}: recall {average_recall:.3f}, comparisons {comparisons:5.0f}")

    print("\n7.5  Storing the corpus in Chroma")
    client = open_store()
    collection, semantic_index, questions = build_corpus_store(client)
    print(f"     {collection.count()} passages in collection '{collection.name}'")
    example = questions[0]
    print(f"     {example['question']}")
    for result in search_store(collection, semantic_index.embed_question(example["question"])):
        print(f"     {result['similarity']:.3f}  [{result['id']}] {result['source']}, {result['reference']}")

    same, different = compare_with_exact(collection, semantic_index, questions)
    print(f"\n7.6  Same top three as exact search: {same} of {len(questions)} {different}")

    if chunks:
        from ragbook.ch04_semantic_search import embed_texts, load_model
        from ragbook.ch06_chunking import (
            EXAMPLE_PDF, clean_pdf_text, find_heading_lines, read_pdf_pages, recursive_chunks,
        )

        print("\n7.7  Chapter 6's recursive chunks in Chroma")
        text, _ = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
        pieces = recursive_chunks(text, find_heading_lines(EXAMPLE_PDF))
        model = load_model()
        chunk_collection = store_chunks(client, pieces, model)
        print(f"     {chunk_collection.count()} chunks in collection '{chunk_collection.name}'")
        for question in CHUNK_QUESTIONS:
            print(f"\n     {question}")
            vector = embed_texts(model, [question])[0]
            for result in search_store(chunk_collection, vector):
                body = result["text"].split("\n\n", 1)[-1]
                print(f"     {result['similarity']:.3f}  [{result['id']}] {result['heading']}: {body[:70]}…")


if __name__ == "__main__":
    import sys

    main(chunks="--chunks" in sys.argv)
