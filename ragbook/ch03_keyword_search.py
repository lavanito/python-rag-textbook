"""
Chapter 3 — Keyword search: word counts, TF-IDF and BM25

What this file does
    Replaces Chapter 2's matching step with three better ways of scoring a
    passage against a question, each built by hand: counting how often the
    question's words appear, weighting rare words more (TF-IDF), and BM25,
    which also allows for passage length. It then checks the hand-built BM25
    against the bm25s library and measures how often each method puts a
    correct passage in its top three.

Inputs
    The corpus (data/corpus/passages.jsonl) and the question bank
    (data/question_bank/questions.jsonl).

Outputs
    Ranked lists of passages, and the share of definition questions for
    which a correct passage is in the top three.

Used by
    Chapter 5 (hybrid search) and Chapter 10 (measuring retrieval).

Uses
    Chapter 1 (split_into_words, load_passages); Chapter 2 (COMMON_WORDS,
    load_corpus). Python's math module. The bm25s library (section 3.6).

Run the worked example
    python -m ragbook.ch03_keyword_search
"""

import math
from pathlib import Path

from ragbook.ch01_python_basics import load_passages, split_into_words
from ragbook.ch02_minimal_pipeline import COMMON_WORDS, load_corpus

QUESTION_FILE = Path(__file__).parent.parent / "data" / "question_bank" / "questions.jsonl"


# ---------------------------------------------------------------------------
# 3.2  Words, cleaned properly
# ---------------------------------------------------------------------------

# Typographic marks that PDFs use and that Chapter 1's split_into_words does
# not remove, because they are not in Python's string.punctuation.
TYPOGRAPHIC_MARKS = "“”‘’–—…"


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


# ---------------------------------------------------------------------------
# 3.3  Scoring by word counts
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 3.4  TF-IDF: rare words count for more
# ---------------------------------------------------------------------------

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


def tf_idf_score(question_words, passage_words, frequencies, number_of_passages):
    """
    Score a passage with TF-IDF: term frequency times inverse document frequency.

    Term frequency (TF) is how often the word appears in this passage.
    Inverse document frequency (IDF) is log(N / n): N passages in all, n of
    them containing the word. A word found in every passage gets IDF 0 and
    adds nothing; a word found in one passage gets the largest IDF.

    Example:
        In the corpus, "deflator" is in 2 of the 57 passages and "gdp" in 18.
        One "deflator" adds log(57/2) = 3.35; one "gdp" adds log(57/18) = 1.15.
    """
    counts = count_words(passage_words)
    score = 0.0
    for word in set(question_words):
        if word in counts:
            idf = math.log(number_of_passages / frequencies[word])
            score = score + counts[word] * idf
    return score


# ---------------------------------------------------------------------------
# 3.5  BM25: allowing for repeats and passage length
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 3.6  Ranking with any of the three scores
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 3.7  Checking the hand-built BM25 against a library
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 3.8  Measuring: is a correct passage in the top three?
# ---------------------------------------------------------------------------

def load_questions(file_path=QUESTION_FILE, question_class="Q2"):
    """
    Read the questions of one class from the question bank.

    Class Q2 is the definition questions, each with its gold passages:
    the passages that state what a correct answer says.

    Example:
        len(load_questions()) returns 32
    """
    chosen = []
    for question in load_passages(file_path):
        if question["class"] == question_class:
            chosen.append(question)
    return chosen


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


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

def main():
    passages = load_corpus()
    index = KeywordIndex(passages)
    questions = load_questions()

    print("3.2  Words, cleaned properly")
    print("    ", search_words("What is the “GDP deflator”?"))

    example = "What is the GDP deflator?"
    for method in ["counts", "tfidf", "bm25"]:
        print(f"\n3.6  {example}  ({method})")
        for passage in index.rank(example, method):
            print(f"     [{passage['id']}] {passage['source']}, {passage['reference']}")

    print("\n3.7  Hand-built BM25 and bm25s agree on the top three:",
          [p["id"] for p in index.rank(example, "bm25")] ==
          [p["id"] for p in bm25s_rank(passages, example)])

    print(f"\n3.8  Questions with a correct passage in the top three (of {len(questions)})")
    for method in ["counts", "tfidf", "bm25"]:
        hits = top_three_hits(lambda question: index.rank(question, method), questions)
        print(f"     {method:7} {hits}")


if __name__ == "__main__":
    main()
