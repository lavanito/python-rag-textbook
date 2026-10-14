"""
Chapter 2 — A minimal RAG pipeline

What this file does
    Answers a question about national accounts in five steps, using the
    quoted corpus and a language model running on your own computer:
    load the corpus, find matching passages, build the prompt, ask the
    model, and put the steps together. Each step is one function.

Inputs
    A question in plain English, and the corpus file
    data/corpus/passages.jsonl (one quoted passage per line).

Outputs
    A dictionary holding the question, the ids of the passages used,
    and the model's answer.

Used by
    Chapter 3 onwards, which replace one step at a time with a better one.

Uses
    Chapter 1 (split_into_words, format_passages, load_passages).
    Python's standard library (json, urllib) to talk to Ollama.
    Ollama, running locally, with the model qwen3:4b
    (install Ollama, then run: ollama pull qwen3:4b).

Run the worked example
    python -m ragbook.ch02_minimal_pipeline
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

from ragbook.ch01_python_basics import format_passages, load_passages, split_into_words

CORPUS_FILE = Path(__file__).parent.parent / "data" / "corpus" / "passages.jsonl"

# Ollama listens on this address on your own computer. Nothing is sent
# over the internet.
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b"


# ---------------------------------------------------------------------------
# 2.2  Step 1: load the corpus
# ---------------------------------------------------------------------------

def load_corpus(file_path=CORPUS_FILE):
    """
    Read the quoted corpus into a list of passage records.

    Each record holds the passage text and the facts about it: id, source,
    reference, edition, licence and scope.

    Example:
        passages = load_corpus()
        passages[0]["id"] returns "sna08-2.144"
    """
    passages = load_passages(file_path)
    return passages


# ---------------------------------------------------------------------------
# 2.3  Step 2: find matching passages
# ---------------------------------------------------------------------------

# Words so common that matching on them says nothing about the topic.
COMMON_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "get", "how", "in", "is", "it", "its", "of", "on", "or",
    "s", "should", "that", "the", "this", "to", "what", "when", "which",
    "who", "why", "with", "you",
}
# "s" is what is left of "country's" once the apostrophe is removed.


def topic_words(text):
    """
    Return the words of a text that say what it is about.

    The text is split into lower-case words (Chapter 1) and common words
    such as "the" and "what" are dropped. Each word is kept once.

    Example:
        topic_words("What is the GDP deflator?")
        returns ["gdp", "deflator"]
    """
    kept = []
    for word in split_into_words(text):
        if word not in COMMON_WORDS and word not in kept:
            kept.append(word)
    return kept


def find_matching_passages(passages, question, how_many=3):
    """
    Return the passages that share the most topic words with the question.

    Each passage scores one point for every topic word of the question it
    contains. Passages scoring zero are left out. The rest are sorted,
    highest score first; passages with equal scores keep their order in
    the corpus. At most how_many passages are returned.

    Example:
        find_matching_passages(passages, "What are the terms of trade?", 2)
        returns the passages sna08-15.187 and esa10-10.47, which contain
        both "terms" and "trade".
    """
    wanted = topic_words(question)
    scored = []
    for passage in passages:
        words_in_passage = split_into_words(passage["text"])
        score = 0
        for word in wanted:
            if word in words_in_passage:
                score = score + 1
        if score > 0:
            scored.append((score, passage))

    # Sort by score, highest first. Python's sort keeps the original order
    # of items with equal scores, so ties stay in corpus order.
    scored.sort(key=lambda pair: pair[0], reverse=True)

    best = []
    for score, passage in scored[:how_many]:
        best.append(passage)
    return best


# ---------------------------------------------------------------------------
# 2.4  Step 3: build the prompt
# ---------------------------------------------------------------------------

INSTRUCTIONS = (
    "You answer questions about national accounts. "
    "Use only the passages given below the question. "
    "After each sentence of your answer, give the id of the passage it comes from "
    "in square brackets, for example [esa10-8.94]. "
    "If the passages do not answer the question, say so and do not guess."
)


def build_prompt(question, passages):
    """
    Put the instructions, the question and the passages into messages for the model.

    A chat model reads a list of messages. The "system" message sets the
    rules; the "user" message holds the question and the evidence.

    Example:
        build_prompt("What is GNI?", [passage])
        returns [{"role": "system", "content": INSTRUCTIONS},
                 {"role": "user", "content": "Question: What is GNI?\\n\\n"
                                             "Passages:\\n\\n[esa10-8.94] ..."}]
    """
    user_text = f"Question: {question}\n\nPassages:\n\n{format_passages(passages)}"
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": user_text},
    ]
    return messages


# ---------------------------------------------------------------------------
# 2.5  Step 4: ask the model
# ---------------------------------------------------------------------------

def ask_model(messages, model=MODEL, url=OLLAMA_URL):
    """
    Send the messages to the local model through Ollama and return its reply.

    Settings:
        temperature 0  the model picks its most likely word each time, so the
                       same prompt gives the same answer (not a correct one;
                       see 2.5.3)
        num_predict    the longest reply allowed, in tokens (pieces of words)
        think False    Qwen3 answers directly, without writing out its reasoning

    Example:
        ask_model(build_prompt("What is GNI?", passages))
        returns a short answer citing [esa10-8.94]
    """
    request_body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 400},
    }
    data = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    # Running on a laptop processor, a reply can take a minute or more.
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.loads(response.read().decode("utf-8"))
    return reply["message"]["content"]


# ---------------------------------------------------------------------------
# 2.6  Step 5: put the steps together
# ---------------------------------------------------------------------------

NO_MATCH = "No passage in the corpus matches this question, so it is not answered."


def answer_question(question, passages, ask=ask_model, how_many=3):
    """
    Answer a question from the corpus: find passages, build the prompt, ask.

    If no passage matches, the model is not asked at all; the answer says so.
    The function that asks the model is an argument, so the tests can pass
    a stand-in that needs no model.

    Example:
        answer_question("How do you get from GNI to net national income?", passages)
        returns {"question": "How do you get ...",
                 "passage_ids": ["sna08-2.144", "bea-ch2-ndp-gni", "cso-gnistar-6"],
                 "answer": "..."}
    """
    found = find_matching_passages(passages, question, how_many)
    if found == []:
        answer = NO_MATCH
    else:
        answer = ask(build_prompt(question, found))

    passage_ids = []
    for passage in found:
        passage_ids.append(passage["id"])

    result = {"question": question, "passage_ids": passage_ids, "answer": answer}
    return result


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

EXAMPLE_QUESTIONS = [
    "How do you get from GNI to net national income?",
    "What are the terms of trade?",
    "Who counts in a country's population when calculating GDP per head?",
]


def main():
    passages = load_corpus()
    print(f"2.2  Loaded {len(passages)} passages")

    for question in EXAMPLE_QUESTIONS:
        print(f"\nQuestion: {question}")
        print("2.3  Topic words:", topic_words(question))
        found = find_matching_passages(passages, question)
        for passage in found:
            print(f"     matched [{passage['id']}] {passage['source']}, {passage['reference']}")
        try:
            result = answer_question(question, passages)
            print("2.5  Answer:")
            print(result["answer"])
        except urllib.error.URLError:
            print("2.5  Ollama is not running, so the model was not asked.")
            print("     Start Ollama and run this file again.")


if __name__ == "__main__":
    main()
