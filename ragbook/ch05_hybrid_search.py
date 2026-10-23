"""
Chapter 5 — Hybrid search and the knowledge graph

What this file does
    Combines Chapter 3's keyword ranking (BM25) and Chapter 4's semantic
    ranking into one, with reciprocal rank fusion. Then adds the knowledge graph
    (data/knowledge_graph/): it finds the concepts a question names, widens the
    keyword search with their other names (aliases), and moves from a concept
    to its passages in each manual, following same_as and differs_from links.
    It measures each step on the 32 definition questions.

Inputs
    The corpus, the question bank, the saved embeddings
    (data/embeddings/all-MiniLM-L6-v2.npz) and the knowledge graph
    (data/knowledge_graph/entities.csv and triples.csv).

Outputs
    Ranked lists of passages; the concepts found in a question; the passages
    for a concept, grouped by manual; hit counts at depths 1, 3 and 10.

Used by
    Chapter 10 (measuring retrieval) and Chapter 12 (routing questions).

Uses
    Chapter 2 (load_corpus); Chapter 3 (search_words, KeywordIndex,
    load_questions); Chapter 4 (SemanticIndex, load_embeddings).
    Python's csv and re modules.

Run the worked example
    python -m ragbook.ch05_hybrid_search
    It reads the saved embeddings, so it needs no model and no internet.
"""

import csv
import re
from pathlib import Path

from ragbook.ch02_minimal_pipeline import load_corpus
from ragbook.ch03_keyword_search import KeywordIndex, load_questions, search_words
from ragbook.ch04_semantic_search import SemanticIndex, load_embeddings

GRAPH_FOLDER = Path(__file__).parent.parent / "data" / "knowledge_graph"


# ---------------------------------------------------------------------------
# 5.2  Reciprocal rank fusion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 5.3  The knowledge graph, and the concepts a question names
# ---------------------------------------------------------------------------

def read_csv(file_path):
    """
    Read a CSV file into a list of dictionaries, one per row.

    Example:
        read_csv(GRAPH_FOLDER / "entities.csv")[0]["id"]
        returns "terms_of_trade"
    """
    with open(file_path, encoding="utf-8") as file:
        return list(csv.DictReader(file))


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


# Relations that read the same in both directions.
TWO_WAY_RELATIONS = ["same_as", "differs_from", "related_to"]


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


# ---------------------------------------------------------------------------
# 5.4  Widening the keyword search with aliases
# ---------------------------------------------------------------------------

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


class HybridIndex:
    """
    Keyword and semantic search combined by reciprocal rank fusion, with an
    option to widen the keyword search from the knowledge graph.

    Example:
        index = HybridIndex(keyword_index, semantic_index, knowledge_graph)
        index.rank("What is the difference between GDP and GNI?", expand=True)
        returns the three best passages after fusion
    """

    def __init__(self, keyword_index, semantic_index, knowledge_graph):
        self.keyword_index = keyword_index
        self.semantic_index = semantic_index
        self.knowledge_graph = knowledge_graph

    def rank(self, question, how_many=3, expand=False):
        """
        Rank every passage both ways, then fuse the two rankings.

        With expand=True the keyword ranking uses the expanded question.
        """
        everything = len(self.keyword_index.passages)
        keyword_question = question
        if expand:
            keyword_question = expand_question(self.knowledge_graph, question)
        keyword_ranking = self.keyword_index.rank(keyword_question, "bm25", how_many=everything)
        semantic_ranking = self.semantic_index.rank(question, how_many=everything)
        return reciprocal_rank_fusion([keyword_ranking, semantic_ranking], how_many=how_many)


# ---------------------------------------------------------------------------
# 5.5  From a concept to its passages, in each manual
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 5.6  Measuring at three depths
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

def main():
    keyword_index, semantic_index, hybrid_index, questions = build_indexes()
    knowledge_graph = hybrid_index.knowledge_graph

    print("5.2  Reciprocal rank fusion on two short rankings")
    a, b, c = {"id": "a"}, {"id": "b"}, {"id": "c"}
    fused = reciprocal_rank_fusion([[a, b, c], [b, c, a]])
    print("     [a, b, c] and [b, c, a] give", [p["id"] for p in fused])

    print("\n5.3  Concepts named in a question")
    for text in ["How do you get from GNI to net national income?",
                 "What is GDI?",
                 "What is real gross domestic income, and how does it lead to real gross national income?"]:
        print(f"     {text}\n       -> {knowledge_graph.concepts_in(text)}")

    example = "What is the difference between GDP and GNI?"
    print(f"\n5.4  {example}")
    print("     expanded:", expand_question(knowledge_graph, example))
    for label, expand in [("hybrid", False), ("hybrid + expansion", True)]:
        print(f"     {label}:", [p["id"] for p in hybrid_index.rank(example, expand=expand)])

    for concept_id in ["consumption_of_fixed_capital", "bea_gdi"]:
        print(f"\n5.5  From '{knowledge_graph.names(concept_id)[0]}' to its passages")
        for other_id, relation, note, grouped in concept_trail(knowledge_graph, concept_id):
            print(f"     {relation}: {other_id}" + (f"  ({note})" if note else ""))
            for manual, found in grouped.items():
                print(f"       {manual}: {', '.join(f'{pid} [{rel}]' for pid, rel in found)}")

    everything = len(keyword_index.passages)
    methods = [
        ("BM25 (Chapter 3)", lambda q: keyword_index.rank(q, "bm25", how_many=everything)),
        ("Semantic (Chapter 4)", lambda q: semantic_index.rank(q, how_many=everything)),
        ("Hybrid", lambda q: hybrid_index.rank(q, how_many=10)),
        ("Hybrid + expansion", lambda q: hybrid_index.rank(q, how_many=10, expand=True)),
    ]
    print(f"\n5.6  Questions with a gold passage within the first 1, 3 and 10 places (of {len(questions)})")
    for label, rank_function in methods:
        counts = [hits_at(rank_function, questions, depth) for depth in (1, 3, 10)]
        print(f"     {label:22} {counts[0]:>3} {counts[1]:>3} {counts[2]:>3}")


if __name__ == "__main__":
    main()
