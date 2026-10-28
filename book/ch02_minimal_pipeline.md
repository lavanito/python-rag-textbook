# Chapter 2 — A minimal RAG pipeline

## 2.1 What this chapter builds

This chapter answers a question about national accounts from quoted passages, in five steps. Each step is one function; later chapters replace one step at a time with a better one.

**RAG** (retrieval-augmented generation) means: find passages that bear on a question, then give them to a language model with the question, so the model answers from those passages. The model writes the answer; the passages supply the facts.

1. Load the corpus: read the 57 quoted passages from file (2.2).
2. Find matching passages: keep the few that share most words with the question (2.3).
3. Build the prompt: put rules, question and passages into messages for the model (2.4).
4. Ask the model: send the messages to Qwen3 running on your own computer (2.5).
5. Put the steps together: one function that runs steps 2 to 4 and returns the answer with the ids of the passages used (2.6).

**Code file:** `ragbook/ch02_minimal_pipeline.py`

**Uses:** Chapter 1 (`split_into_words`, `format_passages`, `load_passages`); Python's standard library; Ollama with the model `qwen3:4b-instruct`.

**Data:** `data/corpus/passages.jsonl`, 57 passages quoted word for word from ten manuals, statistics offices and books, each with its source, paragraph reference, edition, licence and scope. `data/corpus/SOURCES.md` lists the sources and their terms.

**Before you start:** install Ollama from ollama.com, then run `ollama pull qwen3:4b-instruct` once. The download is 2.5 GB. The model runs on the processor; no graphics card or internet connection is needed once it is downloaded.

**If Ollama crashes on an older graphics card:** Ollama uses the graphics card if it finds one. On the 2015 laptop this book was tested on, its model process crashed with error 0xc0000005 ("The memory could not be …"). Hiding the graphics card makes Ollama use the processor only. In PowerShell, run `setx CUDA_VISIBLE_DEVICES -1` and `setx GGML_VK_VISIBLE_DEVICES -1` once, then quit Ollama and start it again.

| Section | Step | Function built |
| --- | --- | --- |
| 2.2 | Load the corpus | `load_corpus` |
| 2.3 | Find matching passages | `topic_words`, `find_matching_passages` |
| 2.4 | Build the prompt | `build_prompt` |
| 2.5 | Ask the model | `ask_model` |
| 2.6 | Put the steps together | `answer_question` |

## 2.2 Step 1: load the corpus

### 2.2.1 Principles

The **corpus** is the set of passages the system may draw on. Here it is one file in the JSON Lines format from Chapter 1, one passage per line.

Each passage carries more than its text. The `id` lets an answer cite it; `source` and `reference` let a reader find it in the original; `scope` says whether it states an international standard or one country's practice.

### 2.2.2 Code

`ragbook/ch02_minimal_pipeline.py`, function `load_corpus`

```python
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
```

### 2.2.3 Annotations

- `file_path=CORPUS_FILE` gives the argument a **default value**: called with no argument, the function reads the book's corpus. A test can pass another file.
- `CORPUS_FILE` is set near the top of the code file from the location of the code file itself, so the function works from any folder.
- The function only calls `load_passages` from Chapter 1. It exists so that every later chapter loads the corpus the same way, by one name.

## 2.3 Step 2: find matching passages

### 2.3.1 Principles

The model sees only the passages it is given, so this step decides which facts the answer can use. A passage left out cannot be used; a wrong passage can mislead.

This chapter uses the simplest method that works at all. Drop common words such as "the" and "what" from the question; the words left are its **topic words**. Each passage scores one point for every topic word it contains, and the highest-scoring passages are kept.

Matching the whole question as one piece of text would find nothing, because no passage contains the question word for word. Matching word by word avoids that.

### 2.3.2 Code

`ragbook/ch02_minimal_pipeline.py`, the set `COMMON_WORDS` and the functions `topic_words` and `find_matching_passages`

```python
# Words so common that matching on them says nothing about the topic.
COMMON_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "get", "how", "in", "is", "it", "its", "of", "on", "or",
    "s", "should", "that", "the", "this", "to", "what", "when", "which",
    "who", "why", "with", "you",
}
# "s" is what is left of "country's" once the apostrophe is removed.
```

```python
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
```

```python
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
```

### 2.3.3 Annotations

- `COMMON_WORDS` is a **set**: a collection with no order and no repeats, written between curly brackets. Checking whether a word is in a set is fast, whatever its size.
- `scored.append((score, passage))` stores a **tuple**: two values kept together in round brackets. The score travels with its passage through the sort.
- `scored.sort(key=lambda pair: pair[0], reverse=True)` sorts by the first value of each tuple, highest first. `lambda pair: pair[0]` is a one-line function with no name: given a pair, return its first value.
- `scored[:how_many]` is a **slice**: the first `how_many` items of the list, or all of them if there are fewer.
- A passage scores the same for a word that appears once or ten times, and a rare word such as "deflator" counts no more than a common one such as "income". Chapter 3 fixes both.

## 2.4 Step 3: build the prompt

### 2.4.1 Principles

A chat model reads a list of **messages**, each with a role. The **system** message sets the rules for the whole exchange; the **user** message holds the request.

The rules here do three things. They limit the model to the passages given, they ask for the passage id after each sentence, and they tell the model to say so when the passages do not answer the question.

A rule is an instruction, not a guarantee. The model can still ignore it; Chapter 14 checks whether answers keep to their passages.

### 2.4.2 Code

`ragbook/ch02_minimal_pipeline.py`, the text `INSTRUCTIONS` and the function `build_prompt`

```python
INSTRUCTIONS = (
    "You answer questions about national accounts. "
    "Use only the passages given below the question. "
    "After each sentence of your answer, give the id of the passage it comes from "
    "in square brackets, for example [esa10-8.94]. "
    "If the passages do not answer the question, say so and do not guess."
)
```

```python
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
```

### 2.4.3 Annotations

- `INSTRUCTIONS` is one string written across several lines. Strings placed side by side inside round brackets are joined into one.
- `format_passages` (Chapter 1) puts each passage's id, source and reference on a line above its text. The model can then cite `[esa10-8.94]` because it has seen that label.
- The question appears once, in the user message. The system message holds only the rules.

## 2.5 Step 4: ask the model

### 2.5.1 Principles

**Ollama** is a free program that runs language models on your own computer. It listens at the address `http://localhost:11434`; "localhost" means this computer, so nothing leaves it.

**Qwen3 4B Instruct** is an open model from Alibaba under the Apache 2.0 licence; "4B" means about 4 billion numbers (parameters) set in training. It is small enough for a laptop processor. "Instruct" marks the version that answers directly. Ollama's plain `qwen3:4b` is the "thinking" version, which writes out its reasoning before every answer; on a laptop that is slow, and the reasoning can use up the length limit before the answer begins.

The code sends the messages as **JSON** (Chapter 1) to Ollama's chat address and reads the reply from the JSON that comes back. Settings for the model go inside `options`.

A model writes one token at a time. For each, it gives every possible next token a probability, and the settings decide how one is drawn from them. This chapter uses the values Qwen recommends and fixes the random draws so that results repeat; Chapter 11 compares the settings.

### 2.5.2 Code

`ragbook/ch02_minimal_pipeline.py`, function `ask_model`

```python
def ask_model(messages, model=MODEL, url=OLLAMA_URL):
    """
    Send the messages to the local model through Ollama and return its reply.

    Settings (all inside "options"):
        temperature, top_p, top_k, min_p
                       how the next word is drawn; the values Qwen recommends
                       for this model (see 2.5.3)
        seed 42        fixes the random draws, so the same prompt gives the
                       same reply each time (a repeatable reply, not
                       necessarily a correct one)
        num_ctx 4096   the context window: prompt plus reply, in tokens
        num_predict    the longest reply allowed, in tokens (pieces of words)

    Example:
        ask_model(build_prompt("What is GNI?", passages))
        returns a short answer citing [esa10-8.94]
    """
    request_body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "min_p": 0,
            "seed": 42,
            "num_ctx": 4096,
            "num_predict": 400,
        },
    }
    data = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    # Running on a laptop processor, a reply can take a minute or more.
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.loads(response.read().decode("utf-8"))
    return reply["message"]["content"]
```

### 2.5.3 Annotations

- `top_k` 20 keeps only the 20 most likely tokens. `top_p` 0.8 keeps, from those, the most likely tokens whose probabilities add up to 0.8. `min_p` 0 makes no further cut.
- `temperature` sets how strongly the draw favours the most likely token: 0 always takes it; higher values spread the choice. 0.7, with the three settings above, is what [Qwen's model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) suggests for this model.
- `seed` fixes the random draws. Ollama gives the same output for the same prompt and seed, so results repeat without temperature 0. The number 42 has no meaning. A repeatable answer is not thereby a correct one.
- `num_ctx` is the **context window**: the most tokens the model can hold at once, prompt and reply together. Ollama's default depends on the version and the computer's memory (its documentation gives 2,048 in one place and 4,096 in another), so the code sets it. This chapter's prompt is about 225 words, well inside 4,096 tokens; later chapters send more passages.
- `num_predict` caps the reply at 400 **tokens**. A token is a word or part of a word; 400 tokens is roughly 300 English words.
- `"stream": False` asks for the whole reply at once rather than word by word.
- Ollama has other settings, such as `repeat_penalty` and `stop`. They stay at Ollama's defaults here; Chapter 11 covers them.
- `urllib.request` is part of Python's standard library, so no package needs installing.
- `with ... as response:` opens the connection and closes it when the indented lines finish, even if one of them fails.
- `timeout=600` waits up to ten minutes before giving up. On the 2015 test laptop the three answers in 2.7 took about 3 minutes together.

## 2.6 Step 5: put the steps together

### 2.6.1 Principles

The last function runs steps 2 to 4 in order and returns three things: the question, the ids of the passages used and the answer. Keeping the ids beside the answer lets a reader check each citation.

When no passage matches, the model is not asked. A model given no passages may answer from what it absorbed in training, which this book cannot cite or check.

### 2.6.2 Code

`ragbook/ch02_minimal_pipeline.py`, the text `NO_MATCH` and the function `answer_question`

```python
NO_MATCH = "No passage in the corpus matches this question, so it is not answered."
```

```python
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
```

### 2.6.3 Annotations

- `ask=ask_model` makes the function that asks the model an argument. Normally it is `ask_model`; the tests pass a stand-in that returns a fixed reply, so they run without Ollama and check the pipeline, not the model's wording.
- `if found == []:` tests for an empty list: no passage scored above zero.
- The result is a dictionary (Chapter 1), so later chapters can add entries, such as the time taken, without changing what is already there.

## 2.7 Running the worked example

From the repository folder, with Ollama running, run:

```text
python -m ragbook.ch02_minimal_pipeline
```

The example loads the corpus and, for three questions, prints the topic words, the passages matched and the model's answer. The retrieval part of the output is fixed:

```text
2.2  Loaded 57 passages

Question: How do you get from GNI to net national income?
2.3  Topic words: ['gni', 'net', 'national', 'income']
     matched [sna08-2.144] System of National Accounts 2008, para. 2.144
     matched [bea-ch2-ndp-gni] US Bureau of Economic Analysis, NIPA Handbook, Chapter 2: Fundamental Concepts
     matched [cso-gnistar-6] Central Statistics Office Ireland, Modified GNI, paragraph 6

Question: What are the terms of trade?
2.3  Topic words: ['terms', 'trade']
     matched [sna08-15.187] System of National Accounts 2008, para. 15.187 (first sentence)
     matched [esa10-10.47] Eurostat, European System of Accounts (ESA 2010), para. 10.47 (part)
     matched [esa10-8.94] Eurostat, European System of Accounts (ESA 2010), para. 8.94

Question: Who counts in a country's population when calculating GDP per head?
2.3  Topic words: ['counts', 'country', 'population', 'calculating', 'gdp', 'per', 'head']
     matched [esa10-11.05] Eurostat, European System of Accounts (ESA 2010), para. 11.05
     matched [wb13-mccarthy-ipd] World Bank, Measuring the Real Size of the World Economy: The Framework, Methodology, and Results of the International Comparison Program (ICP), Chapter 18 (Paul McCarthy), section “Consistency between Time and Space”
     matched [esa10-11.06] Eurostat, European System of Accounts (ESA 2010), para. 11.06
```

**Model answers.** A run of `qwen3:4b-instruct` on the 2015 test laptop, processor only, on 15 October 2026. The three answers took about 3 minutes together, including loading the model:

```text
How do you get from GNI to net national income?
To get from GNI to net national income (NNI), you deduct the consumption of fixed capital from GNI. [sna08-2.144]

What are the terms of trade?
The terms of trade are defined as the ratio of the price of exports to the price of imports. [sna08-15.187]

Who counts in a country's population when calculating GDP per head?
When calculating GDP per head, a country's population includes all persons, national or foreign, who are permanently settled in the country's economic territory, even if they are temporarily absent from it. This is because the definition of population for national accounts is based on residence, and individuals are considered residents if they are staying or intend to stay in the country for one year or more, regardless of temporary absences. The calculation uses an annual average head count to provide a suitable basis for estimating national accounts variables or for use as a denominator in comparisons.
```

What the answers show:

- The first two are correct, one sentence each, and cite the right passage. The model ignored the passages that matched on words alone.
- The third is correct and comes from esa10-11.05 and esa10-11.06 (the one-year rule is in 11.06). But it cites no passage, although the rules ask for an id after every sentence. This is the point of 2.4.1: a rule is an instruction, not a guarantee. Chapter 14 checks citations.
- Another model version may word the answers differently; the passages matched will not change.

What the matches show:

- **Net national income.** The first match, sna08-2.144, is the right one: net national income is GNI less consumption of fixed capital. The other two match on "net", "national" and "income" but answer different questions (BEA's US identities, Ireland's modified GNI).
- **Terms of trade.** Both passages that define the terms of trade come first. The third, esa10-8.94, scores one point for "terms" in the phrase "in net terms". Word matching cannot tell the two senses apart.
- **Population.** The two ESA 2010 passages on population come first and third. Second is McCarthy's passage on extrapolating PPPs, which shares three topic words with the question ("country", "calculating", "gdp") but is not about population.

Without Ollama running, the example prints the matches and then a line saying the model was not asked, with the reason. If Ollama is running but refuses the request, it prints Ollama's error message instead.

## 2.8 How often matching finds the right passages

Every definition question in the question bank (`data/question_bank/questions.jsonl`) lists its **gold passages**: the passages that state what a correct answer says. Running `find_matching_passages` on all 32 definition questions, at least one gold passage is among the top three for 25 of them.

Three of the seven misses show the method's limits:

| Question | What went wrong |
| --- | --- |
| What is the GDP deflator? (q2-16) | The passage writes “GDP deflator” inside curly quotation marks. `split_into_words` (Chapter 1) removes only straight punctuation, so the passage holds the word deflator” with the mark attached, not deflator. |
| What is consumption of fixed capital? (q2-01) | Four passages contain all three words. Equal scores keep corpus order, and the definition (esa10-3.139) comes fourth. |
| Are remittances part of national income? (q2-21) | Passages with "national" and "income" score two points; the two passages on remittances score one. Every word counts the same, however rare. |

A question with no topic in the corpus can still match: "What is the capital of Peru?" matches three passages on the word "capital". The model's rules then matter: the passages do not answer the question, and it should say so.

Chapter 3 replaces this step with keyword scoring that weights rare words more, and Chapter 10 measures retrieval properly.

## 2.9 Tests for this chapter

The file `tests/test_ch02_minimal_pipeline.py` holds nine tests. Retrieval is tested exactly. The model is replaced by a stand-in, so no test depends on Ollama or on the model's wording. Run them with `python -m pytest tests/test_ch02_minimal_pipeline.py -v`.

| Test | What it proves |
| --- | --- |
| The corpus loads 57 passages, each with id, source, reference and text | Every passage can be cited |
| `topic_words` drops common words and repeats | "What is the GDP deflator?" gives `["gdp", "deflator"]` |
| `find_matching_passages` ranks by shared topic words | The net national income question returns the three passages shown in 2.7, in that order |
| `find_matching_passages` returns at most `how_many` passages | The prompt stays short |
| `find_matching_passages` returns nothing when no word matches | A question about Dublin restaurants finds no passage |
| `build_prompt` puts the rules first and labelled passages after the question | The model sees exactly the layout shown in 2.4 |
| `answer_question` sends only the matched passages | Each passage id returned was in the prompt |
| `answer_question` does not ask the model when nothing matches | No answer without evidence |
| `ask_model` sends its settings inside `options` and reads the reply | All seven settings reach the model, and the request names `qwen3:4b-instruct` |

The corpus has its own tests (`tests/test_corpus.py`): every passage has all its fields, scope notes are present where needed, and publishers' limits are kept.

## 2.10 Glossary additions and links

| Term | Meaning |
| --- | --- |
| RAG (retrieval-augmented generation) | Finding passages that bear on a question and giving them to a language model with the question, so the model answers from them |
| Language model | A program that writes text by predicting one word or part of a word at a time |
| Topic words | The words of a question left after common words are dropped |
| Default value | The value an argument takes when none is given |
| Set | A collection with no order and no repeats |
| Tuple | Values kept together in round brackets |
| Slice | Part of a list, such as `items[:3]`, the first three |
| Message | One turn given to a chat model, with a role: system or user |
| System message | The message that sets the rules for the model |
| Prompt | Everything sent to the model: here, the system and user messages |
| Ollama | A free program that runs language models on your own computer |
| Parameter (of a model) | One of the numbers set when the model was trained; Qwen3 4B Instruct has about 4 billion |
| Temperature | A setting for how strongly the model favours its most likely next word; 0 always takes it |
| Token | A word or part of a word, the unit a model reads and writes |
| Gold passages | The passages that state what a correct answer says, listed for each question in the question bank |
| Top-k, top-p | Settings that limit the draw to the k most likely next words, or to the most likely words whose probabilities add up to p |
| Seed | A number that fixes the random draws, so the same prompt gives the same reply |
| Context window | The most tokens a model can hold at once, prompt and reply together |

**Links**

- [Ollama: download](https://ollama.com/download)
- [Ollama API: chat](https://docs.ollama.com/api/chat)
- [Qwen3 on Ollama: model versions](https://ollama.com/library/qwen3/tags)
- [Qwen3 4B Instruct model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Apache License 2.0 (Qwen3's licence)](https://www.apache.org/licenses/LICENSE-2.0)
- [Python `urllib.request`](https://docs.python.org/3/library/urllib.request.html)
- [Python sorting how-to](https://docs.python.org/3/howto/sorting.html)
- [Corpus sources and licences](https://github.com/lavanito/python-rag-textbook/blob/main/data/corpus/SOURCES.md)
- [Chapter 2 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch02_minimal_pipeline.py)
