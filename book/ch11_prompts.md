# Chapter 11 — Prompts, context and model settings

## 11.1 What this chapter builds

Chapters 3 to 10 found and measured passages. This chapter decides what the model is given with those passages, and with which settings it writes the answer.

1. **Context** (11.2): which passages go into the prompt, in what order, and how each is labelled.
2. **Instructions** (11.3): Chapter 2's rules, plus rules for passages that describe one country's practice, for the two SNA editions, and for answer length by role.
3. **Settings** (11.4): what temperature, top-k, top-p, min-p, seed, length limit, stop sequence and repeat penalty do, each tried on one question.
4. **The question bank** (11.5): all 32 definition questions answered for two roles, with tokens and seconds recorded, and code that counts citations.

The code counts what can be counted without judgement: ids cited, ids not given, sentences with no citation, bodies not named. Whether an answer is correct is Chapter 14.

## 11.2 Assembling the context

### 11.2.1 Principles

The **context** is everything the model is given to answer from: here, the passages. The model writes from what is in the prompt, so this step decides which facts the answer can use.

Three choices are made here:

- **Which passages.** The first three from Chapter 8's filtered search, in its order, in the non-commercial use mode.
- **How much text.** A **word budget** of 600 words of quoted text. The three longest passages in the corpus have 170, 178 and 180 words, so three passages always fit; the budget matters when a later chapter sends more.
- **How each is labelled.** Chapter 1's label (id, source, reference), then the edition, then a **scope line** if the passage describes one country's or one body's practice.

The scope line copies the passage's `scope` and `scope_note` fields (Chapter 8, corpus review). Without it, the model has no way to know that modified GNI is an Irish measure or that BEA's GDI is not the SNA's real GDI.

### 11.2.2 Code

`ragbook/ch11_prompts.py`, the constant `WORD_BUDGET` and the functions `format_evidence` and `assemble_context`

```python
WORD_BUDGET = 600
```

```python
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
```

```python
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
```

### 11.2.3 Annotations

- `"\n".join(lines)` puts each label on its own line above the quoted text, so the model reads the label before the words it labels.
- `passage["scope_note"] != ""` tests for an empty note. 31 of the 57 passages have one: all 14 from ESA 2010, all 6 from BEA, all 5 from the CSO, 3 from the Eurostat-OECD PPP manual, both from the ONS and 1 from the OECD textbook.
- `fits or kept == []` keeps the first passage even if it alone is over the budget. An empty context would leave the model nothing to cite.
- A passage left out because of the budget does not stop the loop: a shorter passage further down can still fit.

## 11.3 The instructions

### 11.3.1 Principles

Chapter 2's system message had four rules: answer about national accounts, use only the passages, cite an id after each sentence, say so when the passages do not answer. This chapter adds three.

- **Scope.** A passage with a scope line is presented as that body's practice, for example "in US practice (BEA)".
- **Editions.** If the 2008 SNA and the 2025 SNA differ, the answer says which edition says what. Chapter 8's edition filter withholds a 2008 passage when a 2025 passage on the same topic is kept, so this rule applies when a question names both editions.
- **Length by role.** An analyst gets a full answer; an executive at most two sentences. This follows the demonstrator's design: role changes length only, not the evidence.

A rule is an instruction, not a guarantee (Chapter 2). 11.5 counts how often the model follows the citation and scope rules; the length rule is counted the same way.

### 11.3.2 Code

`ragbook/ch11_prompts.py`, the text `INSTRUCTIONS`, the dictionary `ROLE_LENGTH` and the functions `build_messages` and `word_count`

```python
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
```

```python
ROLE_LENGTH = {
    "analyst": "Give a full answer, in as many sentences as the passages support.",
    "executive": "Answer in at most two sentences.",
}
```

```python
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
```

```python
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
```

### 11.3.3 Annotations

- `INSTRUCTIONS` replaces Chapter 2's text of the same name; Chapter 2's code is unchanged.
- The length rule is added at the end of the system message, so the two roles share every other word of the prompt. Any difference in their answers comes from that one sentence.
- `\"in US practice (BEA)\"` puts quotation marks inside a string that is itself in quotation marks; the backslash marks them as part of the text.
- `word_count` splits at spaces. A model counts tokens, not words; 11.5 compares the two on the laptop run.

### 11.3.4 An example

For q2-22, "What is modified GNI and why does Ireland publish it?", the search returns cso-gnistar-4, cso-gnistar-1 and cso-gnistar-6. Each has the scope line "national practice: Ireland". The executive prompt is 451 words: 118 of instructions and question, and the rest passages and labels.

Run `python -m ragbook.ch11_prompts` to print it.

## 11.4 The settings

### 11.4.1 Principles

At each step the model gives every token in its vocabulary a score. The scores become probabilities that add up to 1, and one token is drawn. The settings decide which tokens can be drawn and how the draw is made.

| Setting | What it does | Ollama's default | This book |
| --- | --- | --- | --- |
| `temperature` | Divides the scores before they become probabilities. Below 1, the likely tokens become more likely; above 1, the probabilities move closer together; 0 always takes the most likely token | 0.8 | 0.7 |
| `top_k` | Keeps only the k most likely tokens | 40 | 20 |
| `top_p` | From those, keeps the most likely tokens whose probabilities add up to p | 0.9 | 0.8 |
| `min_p` | Drops tokens whose probability is below min_p times the most likely token's | 0 | 0 |
| `seed` | Fixes the random draws, so the same prompt and settings give the same reply | 0 | 42 |
| `num_ctx` | The context window: prompt and reply together, in tokens | 2,048 | 4,096 |
| `num_predict` | The longest reply, in tokens; −1 means no limit | −1 | 400 |
| `repeat_penalty` | Lowers the scores of tokens used in the last 64 tokens; 1.0 turns it off | 1.0 | 1.0 |
| `stop` | Text that ends the reply when the model writes it | none | none |

The defaults are from [Ollama's Modelfile reference](https://docs.ollama.com/modelfile). A model in Ollama's library can set its own values, which replace these defaults; the code sets every value it uses, so the run does not depend on them. The book's values for the first four are those [Qwen's model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) gives (Chapter 2).

Ollama's reply reports two counts with every answer: `prompt_eval_count`, the tokens in the prompt, and `eval_count`, the tokens in the reply. It also gives the time taken in nanoseconds and `done_reason`, why the reply ended.

The trials in this section use one question, q2-01, "What is consumption of fixed capital?", with the analyst prompt. Its three passages are esa10-3.139, sna25-A4.10 and sna25-A4.59. Each trial changes one or two settings from the book's values.

| Trials | Changes | What they show |
| --- | --- | --- |
| 2 | None | Whether the same seed gives the same reply |
| 15 | Temperature 0, 0.7 and 1.5, each with seeds 1 to 5 | How many different replies five seeds give at each temperature |
| 1 | `num_predict` 40 | What a reply cut by the length limit looks like |
| 1 | `stop` at a blank line | A reply ended by a stop sequence |
| 1 | `repeat_penalty` 1.5 | Whether the penalty changes the reply |

### 11.4.2 Code

`ragbook/ch11_prompts.py`, the dictionary `SETTINGS` and the functions `ask_model_with_details`, `setting_trials`, `run_trials` and `distinct_replies`

```python
SETTINGS = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0,
    "seed": 42,
    "num_ctx": 4096,
    "num_predict": 400,
}
```

```python
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
```

```python
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
```

```python
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
```

```python
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
```

### 11.4.3 Annotations

- `SETTINGS` has the same values as Chapter 2's `ask_model`, written as a dictionary so trials can copy and change it.
- `options = dict(SETTINGS)` makes a copy before `options.update(changes)`. Changing the copy leaves `SETTINGS` as it was for the next trial; a test checks this.
- `reply.get("prompt_eval_count", 0)` returns 0 if Ollama leaves the field out, instead of stopping with an error.
- `1_000_000_000` is one billion; Python ignores the underscores, which are there to make the digits readable.
- `set()` keeps one copy of each reply text (Chapter 2), so its length is the number of different replies.

### 11.4.4 Results

All 20 trials sent the same prompt of 667 tokens. Lavan ran them on 30 October 2026; they took 18 minutes.

| Trial | Reply tokens | Seconds | Result |
| --- | --- | --- | --- |
| Seed 42, run 1 | 272 | 77.8 | Cites all three passages |
| Seed 42, run 2 | 389 | 70.7 | A different reply from run 1; cites all three |
| Temperature 0, seeds 1 to 5 | 321 each | 51.4 to 54.4 | One reply, the same for all five seeds |
| Temperature 0.7, seeds 1 to 5 | 265 to 345 | 43.0 to 60.3 | Five different replies; each cites all three |
| Temperature 1.5, seeds 1 to 5 | 277 to 373 | 42.7 to 61.9 | Five different replies; each cites all three |
| Reply limit 40 tokens | 40 | 6.1 | Cut off; `done_reason` "length"; ends "obsolescence. [esa10-3.139", with no closing bracket |
| Stop at a blank line | 389 | 61.3 | The same reply as run 2, word for word |
| Repeat penalty 1.5 | 400 | 63.2 | Cut off at the 400-token limit; cites two passages |

- **The same seed gave two different replies.** Run 1 was the first request after the model loaded. Run 2, the stop trial and the bank's analyst answer to q2-01 (11.5) all used the same prompt and settings, and all three are word for word the same.
- **So a fixed seed repeats here except on the first request.** A likely cause is that Ollama reused the processed prompt from the request before, which can change its arithmetic slightly; the run does not prove it. Chapter 2 (2.5.3) now notes this exception.
- **Temperature 0 gave one reply whatever the seed.** With no random draw, the seed has nothing to fix.
- **At 0.7 and 1.5 each seed gave a different reply, and every reply cited the same three passages.** The replies at 1.5 are still readable, likely because top-k 20 and top-p 0.8 limit each draw to a short list of likely tokens.
- **The 40-token limit cut the reply inside its first citation.** Without the closing bracket the code finds no id, so a limit too small for the answer produces an answer with no citation.
- **The stop sequence was never written.** The model separates paragraphs with a single line break, so the reply never contains a blank line and ran as in run 2. A stop sequence works only on text the model writes.
- **A repeat penalty of 1.5 changed the terms and then a fact.** The reply wrote "consumption-of-fixed-capital" with hyphens and "current EU practice (ESA 2013)", where the passage is from ESA 2010. A definition repeats its terms; penalising repeated tokens pushes the model away from them.

## 11.5 Answering the question bank, and counting citations

### 11.5.1 Principles

Each of the 32 definition questions is answered twice, once for each role, with the book's settings: 64 answers. The answers are saved with the passage ids given, tokens, seconds and `done_reason`, so later chapters and the tests read the file instead of asking the model again.

Four counts are made by code:

- **No citation.** An answer with no passage id at all. The demonstrator's design treats this as a defect: such an answer is not shipped.
- **Ids not given.** A cited id that was not among the three passages given. The model either made it up or copied the example id from the instructions.
- **Uncited sentences.** A sentence with no id, against the rule to cite after each sentence.
- **Body not named.** A cited passage that describes one country's practice, or Eurostat-OECD practice, where the answer does not name that country or body.

None of these says whether an answer is correct. An answer can cite the right passage and misstate it; Chapter 14 checks that.

### 11.5.2 Code

`ragbook/ch11_prompts.py`, the functions `answer_bank`, `cited_ids`, `sentences`, `check_citations`, `scope_named` and `summarise`, with the patterns and names they use

```python
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
```

```python
BRACKETS = re.compile(r"\[([^\[\]]+)\]")
PASSAGE_ID = re.compile(r"^[a-z0-9]+-[A-Za-z0-9.\-]+$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
LEADING_BRACKETS = re.compile(r"^(\[[^\[\]]+\]\s*)+")
```

```python
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
```

```python
def sentences(text):
    """
    Split a text into sentences at a full stop, question mark or
    exclamation mark followed by a space. Ids in brackets at the start of a
    piece belong to the sentence before it, because the model often writes
    the id after the full stop. A rough rule, but the same for every answer.

    Example:
        sentences("GDP is output. [a-1] GNI adds income [b-2].")
        returns ["GDP is output. [a-1]", "GNI adds income [b-2]."]
    """
    pieces = []
    for piece in SENTENCE_END.split(text.strip()):
        piece = piece.strip()
        leading = LEADING_BRACKETS.match(piece)
        if leading and pieces != []:
            pieces[-1] = pieces[-1] + " " + leading.group(0).strip()
            piece = piece[leading.end():].strip()
        if piece != "":
            pieces.append(piece)
    return pieces
```

```python
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
```

```python
SCOPE_NAMES = {
    "national practice: United States": ["US", "United States", "BEA", "American"],
    "national practice: Ireland": ["Ireland", "Irish", "CSO"],
    "national practice: United Kingdom": ["UK", "United Kingdom", "ONS", "British"],
    "international guidance": ["Eurostat", "OECD"],
}
```

```python
def scope_named(answer, cited_passages):
    """
    The cited passages whose body the answer does not name.

    Only passages with a scope note whose scope is one country's practice
    or international guidance are checked (in this corpus, the guidance
    with a note is the Eurostat-OECD PPP manual). SCOPE_NAMES lists the
    words that count as naming the body.

    Example:
        scope_named("Modified GNI removes ... [cso-gnistar-1].", [cso_gnistar_1])
        returns ["cso-gnistar-1"]   # neither "Ireland", "Irish" nor "CSO" appears
    """
    unnamed = []
    for passage in cited_passages:
        names = SCOPE_NAMES.get(passage["scope"])
        if names is None or passage["scope_note"] == "":
            continue
        if not any(re.search(r"\b" + re.escape(name) + r"\b", answer) for name in names):
            unnamed.append(passage["id"])
    return unnamed
```

```python
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
```

### 11.5.3 Annotations

- `re.compile` turns a pattern into an object that can be used many times. `\[([^\[\]]+)\]` finds text in square brackets: `[^\[\]]+` means one or more characters that are not brackets.
- `PASSAGE_ID` accepts lower-case letters and digits, a hyphen, then letters, digits, full stops or hyphens: `esa10-8.94`, `sna25-A4.59`, `bea-ch2-ndp-gni`. "[1]" and "[the table]" do not match, so they are not counted as citations.
- `(?<=[.!?])\s+` splits after a full stop, question mark or exclamation mark followed by a space. It also splits after "e.g. ", so a sentence count can be one too high; the rule is the same for every answer. Ids in brackets at the start of a piece are moved to the sentence before, because the model often writes the id after the full stop: "obsolescence. [esa10-3.139] This".
- `r"\b" + re.escape(name) + r"\b"` matches a name as a whole word: "US" matches "in US practice" but not "thus". `re.escape` treats any full stop in the name as a full stop, not as a pattern.
- `SCOPE_NAMES` leaves out ESA 2010 and the OECD textbook: their scope notes say they follow the SNA. Passages with no scope note, such as the IMF manual's and the World Bank's, are not checked.
- `counts["no_citation"] += 1` adds 1 to the count; it is short for `counts["no_citation"] = counts["no_citation"] + 1`.
- `done_reason` other than "stop" counts as cut off.

### 11.5.4 Results

Lavan ran the 64 answers on 30 October 2026; they took 53 minutes. The prompts averaged 532 words and 779 prompt tokens, about 1.5 tokens a word. The longest was 1,085 tokens, so a prompt and a 400-token reply fit the 4,096-token window.

| Count | Analyst | Executive |
| --- | --- | --- |
| Answers | 32 | 32 |
| No citation | 0 | 0 |
| An id not given | 1 | 0 |
| At least one uncited sentence | 29 | 5 |
| Uncited sentences, of all sentences | 119 of 252 | 5 of 54 |
| Body not named, of answers citing a passage that is checked | 2 of 13 | 2 of 6 |
| More than two sentences | 32 | 0 |
| Cut off at 400 tokens | 6 | 0 |
| Mean seconds | 69.3 | 30.2 |
| Mean reply tokens | 307 | 80 |

- **Every answer cites at least one passage.** None is a defect in the demonstrator's sense.
- **The one id not given is a misspelling.** The analyst answer to q2-31 cites [esa10-11.2.7] for esa10-11.27.
- **Nearly half the analyst's sentences have no citation: 119 of 252.** Many link or restate cited sentences. Some add claims no passage makes, such as q2-01's "This definition is consistent with the 2008 SNA"; Chapter 14 checks which.
- **The executive length rule held.** No executive answer has more than two sentences: 10 have one and 22 have two. They took 30.2 seconds on average, against 69.3 for the analyst's.
- **Six analyst answers were cut off at 400 tokens:** q2-08, q2-12, q2-16, q2-18, q2-24 and q2-25. A higher `num_predict` would let them finish, at the cost of time.
- **At 800 tokens all six finish.** Lavan reran the 32 analyst answers with `num_predict` 800 (40 minutes; `data/answers/ch11_answers_800.jsonl`): the six took 449 to 529 tokens and 85 to 137 seconds, and none was cut off. Of the other 26, 25 are unchanged; q2-01, the first request after the model loads, differs (11.4.4). Uncited sentences are 122 of 262, mean seconds 75.0 and mean reply tokens 320; the other counts are unchanged. The demonstrator uses the 800-token answers; this chapter keeps the 400-token run as its example.
- **The scope rule failed four times.** q2-12 cites the Eurostat-OECD passages ppp23-8.2 and ppp23-4.16 without naming Eurostat or the OECD, in both roles; its check in the question bank asks for exactly that. q2-20 (analyst) and q2-23 (executive) cite cso-gnistar-2 without naming Ireland or the CSO.

## 11.6 Tests, glossary and links

### 11.6.1 Tests

The file `tests/test_ch11_prompts.py` has 20 tests. None needs the model; three read the saved replies from the laptop runs. Run them with `python -m pytest tests/test_ch11_prompts.py -v`.

| Test | What it proves |
| --- | --- |
| Editions | Every passage has an edition |
| Scope line | Only passages with a scope note get a scope line; the edition is the second line and the quoted text the last |
| Budget | Passages are kept in rank order; one that would pass the budget is left out and a shorter one after it kept |
| First passage | The first passage is kept even when it is over the budget |
| Bank contexts | All 32 questions get three passages within 600 words |
| Role rule | Each role's messages are the instructions plus its length rule, then the question and labelled passages |
| Word count | Words are counted across messages |
| Trials | 20 trials with different labels; each changes only what it names; `SETTINGS` is unchanged |
| Different replies | Repeated reply texts are counted once |
| Ollama reply | Tokens, seconds and `done_reason` are read from Ollama's reply, with nanoseconds turned into seconds |
| Cited ids | Several ids in one bracket are found, each once; brackets that do not hold an id are ignored |
| Sentences | A text is split at sentence ends; ids after a full stop count for the sentence before |
| Citations | Ids not given and uncited sentences are counted |
| Scope | Irish, US and Eurostat-OECD passages cited without naming the body are found; passages with no scope note, and ESA passages, are not checked |
| Bank | 32 answers per role with three passage ids each; in commercial use every passage is open |
| Summary | The counts in `summarise` on three made-up answers |
| Save and load | Answers round-trip through the file, with model and date added |
| Saved trials | The 20 trials in order; run 1 differs from run 2; run 2 and the stop trial are the same; 1, 5 and 5 different replies at temperatures 0, 0.7 and 1.5; the 40-token and repeat-penalty replies are cut off |
| Saved answers | 64 answers; the counts in 11.5.4 for each role; the analyst answer to q2-01 is the same as settings run 2 |
| Saved answers at 800 tokens | 32 analyst answers; the counts at 800 tokens; only q2-01 and the six cut-off answers differ from the 400 run; the six finish in 449 to 529 tokens |

The bank test uses a stand-in model that cites the first passage label it sees, so it checks the pipeline, not the model.

### 11.6.2 Glossary additions

| Term | Meaning |
| --- | --- |
| Context | The passages given to the model with the question, which the answer is written from |
| Word budget | The most words of quoted text put into the prompt |
| Scope line | A line in a passage's label giving the country or body whose practice it describes |
| Role | Who the answer is for: analyst (full answer) or executive (at most two sentences) |
| Min-p | A setting that drops tokens whose probability is below a fraction of the most likely token's |
| Length limit | The most tokens a reply may have (`num_predict`); a reply that reaches it is cut off |
| Stop sequence | Text that ends the reply as soon as the model writes it |
| Repeat penalty | A setting that lowers the scores of tokens used recently; 1.0 turns it off |
| Prompt tokens, reply tokens | The tokens the model read and the tokens it wrote, as Ollama reports them |

### 11.6.3 Links

- [Ollama: Modelfile reference (settings and defaults)](https://docs.ollama.com/modelfile)
- [Ollama: usage fields in a reply](https://docs.ollama.com/api/usage)
- [Ollama: chat API](https://docs.ollama.com/api/chat)
- [Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Python: the re module](https://docs.python.org/3/library/re.html)
