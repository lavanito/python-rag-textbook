"""
Chapter 11 — Prompts, context and model settings

What this file does
    Turns the passages found by Chapter 8's filtered search into the
    messages a language model reads, and asks the model with settings that
    are written down. It labels each passage with its edition and scope
    note, keeps the passages within a word budget, adds rules for scope,
    editions and answer length, and records tokens and seconds for every
    reply. It then counts, for every answer, the passage ids cited and the
    sentences with no citation. It does not judge whether an answer is
    correct; Chapter 14 does that.

Inputs
    The corpus (data/corpus/passages.jsonl), the question bank
    (data/question_bank/questions.jsonl), the saved embeddings
    (data/embeddings/all-MiniLM-L6-v2.npz) and the knowledge graph.

Outputs
    The model's replies, saved with their settings, tokens and seconds to
    data/answers/ch11_settings.jsonl (one question, many settings) and
    data/answers/ch11_answers.jsonl (every definition question, two roles),
    so later chapters and the tests can use them without the model.

Used by
    Chapter 12 (routing) and Chapter 14 (checking answers).

Uses
    Chapter 2 (load_corpus, MODEL, OLLAMA_URL); Chapter 3 (load_questions);
    Chapter 4 (load_embeddings); Chapter 5 (saved_question_embedder);
    Chapter 8 (FilteredSearch). Python's json, re, sys, datetime and urllib
    modules. Ollama, running locally, with qwen3:4b-instruct.

Run the worked example
    python -m ragbook.ch11_prompts --settings --bank
        Asks the model: about 20 replies to one question, then 64 answers
        (32 definition questions, two roles). On a laptop processor this
        takes about an hour. Needs Ollama running.
    python -m ragbook.ch11_prompts
        Reads the saved replies, so it needs no model.
"""

import datetime
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ragbook.ch02_minimal_pipeline import MODEL, OLLAMA_URL, load_corpus
from ragbook.ch03_keyword_search import load_questions
from ragbook.ch04_semantic_search import load_embeddings
from ragbook.ch05_hybrid_search import saved_question_embedder
from ragbook.ch08_filters import FilteredSearch

ANSWER_FOLDER = Path(__file__).parent.parent / "data" / "answers"
SETTINGS_FILE = ANSWER_FOLDER / "ch11_settings.jsonl"
ANSWERS_FILE = ANSWER_FOLDER / "ch11_answers.jsonl"


# ---------------------------------------------------------------------------
# 11.2  Assembling the context
# ---------------------------------------------------------------------------

WORD_BUDGET = 600


def format_evidence(passage):
    """
    Turn one passage into a labelled block for the prompt.

    The first line is Chapter 1's label: id, source and reference. The
    second gives the edition. If the passage describes one body's practice,
    a third line gives its scope and scope note, so the model can say whose
    practice it is. The quoted text comes last.

    Example:
        format_evidence(passage)   # passage cso-gnistar-1
        returns
            "[cso-gnistar-1] Central Statistics Office Ireland, Modified GNI, paragraph 1\\n"
            "Edition: ...\\n"
            "Scope: national practice: Ireland. Modified GNI (GNI*) is an Irish measure, ...\\n"
            "..."
    """
    lines = [f"[{passage['id']}] {passage['source']}, {passage['reference']}"]
    lines.append(f"Edition: {passage['edition']}")
    if passage["scope_note"] != "":
        lines.append(f"Scope: {passage['scope']}. {passage['scope_note']}")
    lines.append(passage["text"])
    return "\n".join(lines)


def assemble_context(ranked, how_many=3, word_budget=WORD_BUDGET):
    """
    Keep passages in rank order until how_many are kept or the next would
    take the quoted text over word_budget words.

    Returns the passages kept and the passages left out. The first passage
    is always kept, so the model never receives an empty context because
    one passage is long.

    Example:
        kept, left_out = assemble_context(ranked, how_many=3, word_budget=600)
        [passage["id"] for passage in kept]
        returns the ids of the first three passages, if they fit
    """
    kept = []
    left_out = []
    words_used = 0
    for passage in ranked:
        words = len(passage["text"].split())
        fits = words_used + words <= word_budget
        if len(kept) < how_many and (fits or kept == []):
            kept.append(passage)
            words_used = words_used + words
        else:
            left_out.append(passage)
    return kept, left_out


# ---------------------------------------------------------------------------
# 11.3  The instructions
# ---------------------------------------------------------------------------

INSTRUCTIONS = (
    "You answer questions about national accounts. "
    "Use only the passages given below the question. "
    "After each sentence of your answer, give the id of the passage it comes from "
    "in square brackets, for example [esa10-8.94]. "
    "If the passages do not answer the question, say so and do not guess. "
    "Some passages have a Scope line: they describe one country's or one body's practice. "
    "Present what they say as that practice, for example \"in US practice (BEA)\", "
    "not as a rule for all national accounts. "
    "If passages from the 2008 SNA and the 2025 SNA differ, say which edition says what."
)

ROLE_LENGTH = {
    "analyst": "Give a full answer, in as many sentences as the passages support.",
    "executive": "Answer in at most two sentences.",
}


def build_messages(question, passages, role="analyst"):
    """
    Put the instructions, the length rule for the role, the question and
    the labelled passages into messages for the model.

    Example:
        build_messages("What is modified GNI?", kept, role="executive")
        returns [{"role": "system", "content": INSTRUCTIONS + " Answer in at most two sentences."},
                 {"role": "user", "content": "Question: What is modified GNI?\\n\\nPassages:\\n\\n..."}]
    """
    system_text = INSTRUCTIONS + " " + ROLE_LENGTH[role]
    blocks = []
    for passage in passages:
        blocks.append(format_evidence(passage))
    user_text = f"Question: {question}\n\nPassages:\n\n" + "\n\n".join(blocks)
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]


def word_count(messages):
    """
    The number of words in all the messages, split at spaces.

    Example:
        word_count([{"role": "user", "content": "What is GDP?"}])
        returns 3
    """
    total = 0
    for message in messages:
        total = total + len(message["content"].split())
    return total


# ---------------------------------------------------------------------------
# 11.4  The settings
# ---------------------------------------------------------------------------

SETTINGS = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0,
    "seed": 42,
    "num_ctx": 4096,
    "num_predict": 400,
}


def ask_model_with_details(messages, options=SETTINGS, model=MODEL, url=OLLAMA_URL):
    """
    Send the messages to the local model and return the reply with its
    counts: tokens in the prompt, tokens in the reply, seconds taken, and
    why the reply ended.

    Ollama reports times in nanoseconds (billionths of a second); the code
    divides by 1,000,000,000 to give seconds.

    Example:
        ask_model_with_details(build_messages("What is GNI?", kept))
        returns {"answer": "...", "prompt_tokens": 512, "reply_tokens": 85,
                 "seconds": 41.2, "done_reason": "stop"}
    """
    request_body = {"model": model, "messages": messages, "stream": False, "options": options}
    data = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.loads(response.read().decode("utf-8"))
    return {
        "answer": reply["message"]["content"],
        "prompt_tokens": reply.get("prompt_eval_count", 0),
        "reply_tokens": reply.get("eval_count", 0),
        "seconds": reply.get("total_duration", 0) / 1_000_000_000,
        "done_reason": reply.get("done_reason", ""),
    }


def setting_trials():
    """
    The changes to SETTINGS tried on one question, as (label, changes) pairs.

    Two identical runs show whether a fixed seed repeats. Five seeds at
    each of three temperatures show how much the reply varies. The last
    three show a short length limit, a stop sequence and a repeat penalty.

    Example:
        setting_trials()[0]
        returns ("seed 42, run 1", {})
    """
    trials = [("seed 42, run 1", {}), ("seed 42, run 2", {})]
    for temperature in (0, 0.7, 1.5):
        for seed in (1, 2, 3, 4, 5):
            label = f"temperature {temperature}, seed {seed}"
            trials.append((label, {"temperature": temperature, "seed": seed}))
    trials.append(("reply limit 40 tokens", {"num_predict": 40}))
    trials.append(("stop at a blank line", {"stop": ["\n\n"]}))
    trials.append(("repeat penalty 1.5", {"repeat_penalty": 1.5}))
    return trials


def run_trials(messages, ask=ask_model_with_details, trials=None):
    """
    Ask the model once for each trial and return one record per reply.

    Each record has the label, the full settings used and the reply with
    its counts. The function that asks the model is an argument, so the
    tests can pass a stand-in.

    Example:
        records = run_trials(build_messages(question, kept))
        records[0]["label"]
        returns "seed 42, run 1"
    """
    if trials is None:
        trials = setting_trials()
    records = []
    for label, changes in trials:
        options = dict(SETTINGS)
        options.update(changes)
        record = {"label": label, "options": options}
        record.update(ask(messages, options))
        records.append(record)
    return records


def distinct_replies(records):
    """
    The number of different reply texts among the records.

    Example:
        distinct_replies([{"answer": "A"}, {"answer": "A"}, {"answer": "B"}])
        returns 2
    """
    texts = set()
    for record in records:
        texts.add(record["answer"])
    return len(texts)


# ---------------------------------------------------------------------------
# 11.5  Answering the question bank, and counting citations
# ---------------------------------------------------------------------------

def answer_bank(questions, search, use_mode="non-commercial", role="analyst",
                ask=ask_model_with_details, how_many=3):
    """
    Answer every question: search with the filters, assemble the context,
    build the messages for the role, ask the model.

    Returns one record per question: id, question, role, use mode, the ids
    of the passages given, the reply and its counts.

    Example:
        records = answer_bank(load_questions(), search, role="executive")
        records[0]["passage_ids"]
        returns the ids of the passages given for q2-01
    """
    records = []
    for question in questions:
        ranked, withheld = search.rank(question["question"], use_mode, how_many=10)
        kept, left_out = assemble_context(ranked, how_many)
        messages = build_messages(question["question"], kept, role)
        record = {
            "id": question["id"],
            "question": question["question"],
            "role": role,
            "use_mode": use_mode,
            "passage_ids": [passage["id"] for passage in kept],
            "prompt_words": word_count(messages),
        }
        record.update(ask(messages, SETTINGS))
        records.append(record)
    return records


BRACKETS = re.compile(r"\[([^\[\]]+)\]")
PASSAGE_ID = re.compile(r"^[a-z0-9]+-[A-Za-z0-9.\-]+$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def cited_ids(text):
    """
    The passage ids written in square brackets in a text, in order, each once.

    A bracket may hold several ids separated by commas or semicolons.
    Brackets holding anything that does not look like an id are ignored.

    Example:
        cited_ids("GNI is income [esa10-8.94]. NNI deducts CFC [sna08-2.144; esa10-8.94].")
        returns ["esa10-8.94", "sna08-2.144"]
    """
    found = []
    for inside in BRACKETS.findall(text):
        for piece in re.split(r"[,;]", inside):
            piece = piece.strip()
            if PASSAGE_ID.match(piece) and piece not in found:
                found.append(piece)
    return found


def sentences(text):
    """
    Split a text into sentences at a full stop, question mark or
    exclamation mark followed by a space. A rough rule, but the same for
    every answer.

    Example:
        sentences("GDP is output [a-1]. GNI adds income [b-2].")
        returns ["GDP is output [a-1].", "GNI adds income [b-2]."]
    """
    pieces = []
    for piece in SENTENCE_END.split(text.strip()):
        if piece.strip() != "":
            pieces.append(piece.strip())
    return pieces


def check_citations(answer, given_ids):
    """
    Count what an answer cites against the passages it was given.

    Returns the ids cited, the cited ids that were not given (the model
    made them up or took them from the instructions' example), and the
    number of sentences with no id in brackets.

    Example:
        check_citations("GNI is income [esa10-8.94]. It is large.", ["esa10-8.94"])
        returns {"cited": ["esa10-8.94"], "not_given": [], "uncited_sentences": 1}
    """
    cited = cited_ids(answer)
    not_given = [passage_id for passage_id in cited if passage_id not in given_ids]
    uncited = 0
    for sentence in sentences(answer):
        if cited_ids(sentence) == []:
            uncited = uncited + 1
    return {"cited": cited, "not_given": not_given, "uncited_sentences": uncited}


SCOPE_NAMES = {
    "national practice: United States": ["US", "United States", "BEA", "American"],
    "national practice: Ireland": ["Ireland", "Irish", "CSO"],
    "national practice: United Kingdom": ["UK", "United Kingdom", "ONS", "British"],
    "international guidance": ["Eurostat", "OECD"],
}


def scope_named(answer, cited_passages):
    """
    The cited passages whose body the answer does not name.

    Only passages whose scope is one country's practice or the
    Eurostat-OECD guidance are checked; their scope lists the words that
    count as naming the body.

    Example:
        scope_named("Modified GNI removes ... [cso-gnistar-1].", [cso_gnistar_1])
        returns ["cso-gnistar-1"]   # neither "Ireland", "Irish" nor "CSO" appears
    """
    unnamed = []
    for passage in cited_passages:
        names = SCOPE_NAMES.get(passage["scope"])
        if names is None:
            continue
        if not any(re.search(r"\b" + re.escape(name) + r"\b", answer) for name in names):
            unnamed.append(passage["id"])
    return unnamed


def summarise(records, passages_by_id):
    """
    Counts over a set of answers: how many cite nothing, cite an id not
    given, leave sentences uncited, leave a body unnamed, run over two
    sentences, or were cut off by the length limit; and the mean seconds
    and tokens.

    Example:
        summarise(load_answers(ANSWERS_FILE), passages_by_id)["no_citation"]
        returns the number of answers with no passage id at all
    """
    counts = {"answers": len(records), "no_citation": 0, "not_given": 0,
              "uncited_sentences": 0, "scope_unnamed": 0, "over_two_sentences": 0,
              "cut_off": 0}
    seconds = 0.0
    reply_tokens = 0
    for record in records:
        check = check_citations(record["answer"], record["passage_ids"])
        cited = [passages_by_id[i] for i in check["cited"] if i in passages_by_id]
        if check["cited"] == []:
            counts["no_citation"] += 1
        if check["not_given"] != []:
            counts["not_given"] += 1
        if check["uncited_sentences"] > 0:
            counts["uncited_sentences"] += 1
        if scope_named(record["answer"], cited) != []:
            counts["scope_unnamed"] += 1
        if len(sentences(record["answer"])) > 2:
            counts["over_two_sentences"] += 1
        if record["done_reason"] != "stop":
            counts["cut_off"] += 1
        seconds = seconds + record["seconds"]
        reply_tokens = reply_tokens + record["reply_tokens"]
    if records:
        counts["mean_seconds"] = round(seconds / len(records), 1)
        counts["mean_reply_tokens"] = round(reply_tokens / len(records))
    return counts


def save_answers(file_path, records):
    """
    Write records to a JSON Lines file, with the model name and the date
    of the run added to each.

    Example:
        save_answers(ANSWERS_FILE, records)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    with open(file_path, "w", encoding="utf-8") as file:
        for record in records:
            line = {"model": MODEL, "date": today}
            line.update(record)
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


def load_answers(file_path):
    """
    Read records saved by save_answers.

    Example:
        len(load_answers(ANSWERS_FILE))
        returns 64
    """
    records = []
    with open(file_path, encoding="utf-8") as file:
        for line in file:
            if line.strip() != "":
                records.append(json.loads(line))
    return records


def build_search():
    """
    Chapter 8's filtered search, built from the saved files.

    Example:
        search, questions, passages = build_search()
    """
    passages = load_corpus()
    questions = load_questions()
    saved = load_embeddings()
    search = FilteredSearch(passages, saved, saved_question_embedder(questions, saved))
    return search, questions, passages


# ---------------------------------------------------------------------------
# Worked example: run this file to see each step
# ---------------------------------------------------------------------------

SETTINGS_QUESTION = "q2-01"


def run_and_save(search, questions):
    """Ask the model for the settings trials and the bank, and save both."""
    if "--settings" in sys.argv:
        question = [q for q in questions if q["id"] == SETTINGS_QUESTION][0]
        ranked, withheld = search.rank(question["question"], "non-commercial", how_many=10)
        kept, left_out = assemble_context(ranked)
        records = run_trials(build_messages(question["question"], kept))
        for record in records:
            record["id"] = question["id"]
            record["passage_ids"] = [passage["id"] for passage in kept]
        save_answers(SETTINGS_FILE, records)
        print(f"11.4  {len(records)} replies saved to data/answers/{SETTINGS_FILE.name}")
    if "--bank" in sys.argv:
        records = []
        for role in ("analyst", "executive"):
            records = records + answer_bank(questions, search, role=role)
            print(f"11.5  {role}: {len(questions)} answers")
        save_answers(ANSWERS_FILE, records)
        print(f"11.5  {len(records)} answers saved to data/answers/{ANSWERS_FILE.name}")


def main():
    search, questions, passages = build_search()
    passages_by_id = {passage["id"]: passage for passage in passages}

    example = [q for q in questions if q["id"] == "q2-22"][0]["question"]
    ranked, withheld = search.rank(example, "non-commercial", how_many=10)
    kept, left_out = assemble_context(ranked)
    messages = build_messages(example, kept, role="executive")
    print(f"11.3  Messages for: {example} (executive)")
    print(messages[0]["content"])
    print()
    print(messages[1]["content"])
    print(f"\n      {word_count(messages)} words")

    try:
        run_and_save(search, questions)
    except urllib.error.URLError as error:
        print(f"Could not reach Ollama ({error.reason}). Start Ollama and run again.")
        return

    if SETTINGS_FILE.exists():
        records = load_answers(SETTINGS_FILE)
        print(f"\n11.4  Settings trials on {SETTINGS_QUESTION}")
        for record in records:
            check = check_citations(record["answer"], record["passage_ids"])
            print(f"      {record['label']:<28} {record['reply_tokens']:>4} tokens "
                  f"{record['seconds']:>6.1f} s  {record['done_reason']:<6} cites {check['cited']}")
        same = distinct_replies(records[:2]) == 1
        print(f"      seed 42 twice gives the same reply: {same}")
        for temperature in (0, 0.7, 1.5):
            group = [r for r in records if r["label"].startswith(f"temperature {temperature},")]
            print(f"      temperature {temperature}: {distinct_replies(group)} different replies from 5 seeds")

    if ANSWERS_FILE.exists():
        records = load_answers(ANSWERS_FILE)
        for role in ("analyst", "executive"):
            group = [r for r in records if r["role"] == role]
            print(f"\n11.5  {role}: {summarise(group, passages_by_id)}")


if __name__ == "__main__":
    main()
