# Chapter 1 — The Python you need

## 1.1 What this chapter builds

This chapter builds eight small functions for handling text. Every later chapter uses them: to clean passages taken from PDFs, to split text into words for keyword search, to keep each passage together with its source, and to lay passages out for a language model to read.

**Code file:** `ragbook/ch01_python_basics.py`

**Uses:** nothing from earlier chapters; Python's standard library only.

**Sample data:** `data/examples/ch01_sample_passages.jsonl`, three sentences written for this chapter. They are not quotations from any manual; the quoted corpus starts in Chapter 2.

| Section | Python idea | Function built |
| --- | --- | --- |
| 1.2 | Strings | `clean_text` |
| 1.3 | Lists | `split_into_words` |
| 1.4 | Dictionaries | `make_passage` |
| 1.5 | Loops and conditions | `find_passages_containing` |
| 1.6 | f-strings and join | `format_passage`, `format_passages` |
| 1.7 | Files | `save_passages`, `load_passages` |

## 1.2 Cleaning text

### 1.2.1 Principles

In Python, a piece of text is a **string**: a sequence of characters between quotation marks. Single and double quotation marks mean the same thing; this book uses double.

Text copied out of a PDF is untidy. A line break may fall in the middle of a sentence, and a gap may hold several spaces. Two passages that say the same thing can then look different to a computer. Cleaning puts every piece of text into one standard shape before it is used: one line, one space between words, nothing at the start or end.

### 1.2.2 Code

`ragbook/ch01_python_basics.py`, function `clean_text`

```python
def clean_text(text):
    """
    Remove extra spaces, tabs and line breaks from a piece of text.

    Text copied from a PDF often has line breaks in the middle of sentences
    and runs of spaces. This joins it back into one tidy line.

    Example:
        clean_text("  Gross domestic\\n   product  ")
        returns "Gross domestic product"
    """
    # split() with no argument splits on any run of spaces, tabs or line
    # breaks, and drops empty pieces at the start and end.
    pieces = text.split()

    # Put the pieces back together with exactly one space between them.
    cleaned = " ".join(pieces)
    return cleaned
```

### 1.2.3 Annotations

- `def clean_text(text):` defines a **function**: a named, reusable set of steps. `text` is its **argument**, the value given to it each time it runs.
- The text between the triple quotation marks is the **docstring**: a plain-English description with a worked example. Every function in this book has one.
- Lines starting with `#` are **comments**. Python ignores them; they are for the reader.
- `text.split()` breaks the text wherever there is space of any kind and returns the pieces as a list (see 1.3).
- `" ".join(pieces)` does the reverse: it joins the pieces into one string with a single space between each.
- `return cleaned` hands the result back to whoever called the function.
- `\n` inside a string means a line break. Inside a docstring it is written with two backslashes, so the example shows those characters instead of starting a new line.

## 1.3 Lists: splitting text into words

### 1.3.1 Principles

A **list** is an ordered collection of values, written between square brackets: `["gdp", "at", "market", "prices"]`. Each item keeps its position, counted from 0.

Keyword search (Chapter 3) compares the words in a question with the words in each passage. For that comparison to work, "GDP", "gdp" and "GDP," must all count as the same word. So the text is first put in lower case, punctuation is removed, and what remains is split into a list of words.

### 1.3.2 Code

`ragbook/ch01_python_basics.py`, function `split_into_words`

```python
def split_into_words(text):
    """
    Turn a piece of text into a list of lower-case words, without punctuation.

    Keyword search (Chapter 3) compares lists like this one.

    Example:
        split_into_words("GDP, at market prices.")
        returns ["gdp", "at", "market", "prices"]
    """
    # Step 1: lower case, so "GDP" and "gdp" count as the same word.
    lower_text = text.lower()

    # Step 2: replace every punctuation mark with a space.
    # string.punctuation is a ready-made string of all punctuation marks.
    without_punctuation = ""
    for character in lower_text:
        if character in string.punctuation:
            without_punctuation = without_punctuation + " "
        else:
            without_punctuation = without_punctuation + character

    # Step 3: split on spaces into a list of words.
    words = without_punctuation.split()
    return words
```

### 1.3.3 Annotations

- `text.lower()` returns a copy of the text in lower case. The original is unchanged.
- `string.punctuation` comes from Python's `string` module, loaded by the line `import string` at the top of the file. It holds every common punctuation mark: `!"#$%&'()*+,-./:;<=>?@[\]^_{|}~` and the backtick.
- `for character in lower_text:` is a **loop**. It runs the indented lines once for each character in the text, in order.
- `if … else …` is a **condition**. A punctuation mark is replaced by a space; any other character is kept.
- Replacing punctuation with a space, not with nothing, keeps words apart: "non-financial" becomes two words, "non" and "financial". Chapter 3 returns to whether that is what we want.
- Building a string one character at a time is slow for very long texts. It is used here because each step can be read; speed is not the aim of this book.

## 1.4 Dictionaries: a passage as a record

### 1.4.1 Principles

A **dictionary** stores values under names, called **keys**. It is written between curly brackets: `{"id": "ex-001", "source": "Example"}`. You read a value by its key: `passage["source"]` gives `"Example"`.

In this book every passage is a dictionary with the same four keys:

| Key | Holds | Example |
| --- | --- | --- |
| `id` | A short label, unique in the corpus | `ex-001` |
| `source` | The publication the passage comes from | `Example written for this book` |
| `reference` | Where in that publication: paragraph, section or page | `sentence 1` |
| `text` | The passage itself, cleaned | `Gross domestic product measures …` |

Keeping the source and reference in the same record as the text matters. Whatever later chapters do with a passage, its origin goes with it, so every answer can cite exactly where its evidence came from.

### 1.4.2 Code

`ragbook/ch01_python_basics.py`, function `make_passage`

```python
def make_passage(passage_id, source, reference, text):
    """
    Store one passage and the facts about it in a dictionary.

    Every passage in the book is a record like this. The source and the
    reference travel with the text, so an answer can always say where its
    evidence came from.

    Example:
        make_passage("ex-001", "Example", "para 1", "  GDP measures output. ")
        returns {"id": "ex-001", "source": "Example",
                 "reference": "para 1", "text": "GDP measures output."}
    """
    passage = {
        "id": passage_id,
        "source": source,
        "reference": reference,
        "text": clean_text(text),
    }
    return passage
```

### 1.4.3 Annotations

- The function takes four arguments and returns one dictionary.
- `"text": clean_text(text)` calls the function from 1.2, so every stored passage is already clean.
- Dictionaries keep their keys in the order they were added. (Since Python 3.7; some older notes say otherwise.)
- The argument is called `passage_id`, not `id`, because `id` is already the name of a built-in Python function.

## 1.5 Loops and conditions: finding passages

### 1.5.1 Principles

The simplest possible search goes through every passage in turn and keeps those that contain a given word. It needs two ideas already met in 1.3: a **loop**, to visit each passage, and a **condition**, to decide whether to keep it.

This search matches whole words only. "income" finds "Income," but not "incomes". That is a real weakness, and Chapters 3 to 5 deal with it. It is still worth building, because every better search in the book is a refinement of this one.

### 1.5.2 Code

`ragbook/ch01_python_basics.py`, function `find_passages_containing`

```python
def find_passages_containing(passages, word):
    """
    Return the passages whose text contains a given word.

    The match is on whole words, ignoring case and punctuation:
    "income" matches "Income," but not "incomes".

    Example:
        With passages about "gross domestic product" and "national income",
        find_passages_containing(passages, "income")
        returns only the passage about national income.
    """
    wanted_word = word.lower()
    matches = []
    for passage in passages:
        words_in_passage = split_into_words(passage["text"])
        if wanted_word in words_in_passage:
            matches.append(passage)
    return matches
```

### 1.5.3 Annotations

- `matches = []` starts an empty list; `matches.append(passage)` adds one item to its end.
- `split_into_words` is the function from 1.3, so the passage and the search word are treated the same way.
- `wanted_word in words_in_passage` is `True` if the word is one of the items in the list, and `False` otherwise.
- The passages come back in the order they were stored. Nothing is ranked yet; ranking starts in Chapter 3.

## 1.6 f-strings and join: formatting passages for a prompt

### 1.6.1 Principles

A language model reads plain text, not dictionaries. Before passages are given to a model (Chapter 2), each record must be laid out as text. The layout puts the passage's id, source and reference on a heading line above its words, so the model can cite them.

Two tools do this. An **f-string** is a string with an `f` in front, in which anything inside curly brackets is replaced by its value. `join` puts a list of strings together with a chosen separator between them.

### 1.6.2 Code

`ragbook/ch01_python_basics.py`, functions `format_passage` and `format_passages`

```python
def format_passage(passage):
    """
    Turn one passage record into a short labelled block of text.

    A language model reads text, not dictionaries. This block shows the
    model the source and reference beside the words, so it can cite them.

    Example:
        format_passage({"id": "ex-001", "source": "Example",
                        "reference": "para 1", "text": "GDP measures output."})
        returns
            "[ex-001] Example, para 1\\nGDP measures output."
    """
    heading_line = f"[{passage['id']}] {passage['source']}, {passage['reference']}"
    block = heading_line + "\n" + passage["text"]
    return block


def format_passages(passages):
    """
    Turn a list of passages into one block of text, blank line between each.

    Example:
        Two passages give
            "[ex-001] ...\\n...\\n\\n[ex-002] ...\\n..."
    """
    blocks = []
    for passage in passages:
        blocks.append(format_passage(passage))
    # "\n\n" puts one empty line between consecutive blocks.
    return "\n\n".join(blocks)
```

### 1.6.3 Annotations

- In `f"[{passage['id']}] …"`, the parts in curly brackets are replaced by the passage's values. Inside the f-string the keys use single quotation marks, because the string itself is in double ones.
- `heading_line + "\n" + passage["text"]` joins three strings with `+`: the heading, a line break, and the text.
- `format_passages` calls `format_passage` once per passage, collects the blocks in a list, then joins them with `"\n\n"`: a blank line between each.
- The two functions are kept separate so that each does one job. Chapter 2 reuses both.

With the first two sample passages, `format_passages` gives:

```text
[ex-001] Example written for this book, sentence 1
Gross domestic product measures the value of goods and services produced in an economy in a period.

[ex-002] Example written for this book, sentence 2
Net national income starts from gross domestic product, adds income received from abroad, subtracts income paid abroad, and subtracts the wear and tear on capital.
```

## 1.7 Files: saving and loading passages

### 1.7.1 Principles

Passages are kept in a file so that every chapter starts from the same corpus. The book uses **JSON Lines**: a text file with one passage per line, each line written in **JSON**, a standard text format for dictionaries and lists. One line of the sample file reads:

```text
{"id": "ex-001", "source": "Example written for this book", "reference": "sentence 1", "text": "Gross domestic product measures the value of goods and services produced in an economy in a period."}
```

The format has three advantages here. It opens in any text editor. Each line stands alone, so one damaged line does not spoil the rest. And Python reads and writes it with its own `json` module, with nothing to install.

### 1.7.2 Code

`ragbook/ch01_python_basics.py`, functions `save_passages` and `load_passages`

```python
def save_passages(passages, file_path):
    """
    Write passages to a file, one passage per line, in JSON format.

    This layout is called JSON Lines. Each line can be read on its own,
    and the file can be opened in any text editor.

    Example:
        save_passages([passage_1, passage_2], "passages.jsonl")
        writes a file with two lines.
    """
    file_path = Path(file_path)
    lines = []
    for passage in passages:
        # ensure_ascii=False keeps characters such as "é" readable in the file.
        lines.append(json.dumps(passage, ensure_ascii=False))
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_passages(file_path):
    """
    Read passages from a JSON Lines file into a list of dictionaries.

    Blank lines are skipped. The order of passages in the file is kept.

    Example:
        load_passages("passages.jsonl")
        returns [passage_1, passage_2]
    """
    file_path = Path(file_path)
    passages = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "":
            continue
        passages.append(json.loads(line))
    return passages
```

### 1.7.3 Annotations

- `Path(file_path)` turns a file name into a `Path` object from Python's `pathlib` module, which works the same way on Windows, Mac and Linux.
- `json.dumps(passage)` turns one dictionary into one line of JSON text; `json.loads(line)` does the reverse.
- `encoding="utf-8"` fixes how characters are stored, so accented letters in French or Spanish passages survive the round trip. Windows uses a different default, so the book always states it.
- `continue` skips the rest of the loop for that line and moves to the next one; here it skips blank lines.
- The test in 1.9 saves passages and loads them back, and checks that nothing changed.

## 1.8 Running the worked example

The end of the code file has a short worked example that runs each function on the sample passages and prints the result. From the repository folder, run:

```text
python -m ragbook.ch01_python_basics
```

The output:

```text
1.2  Cleaning text
    before: '  Gross domestic\n   product  '
    after:  'Gross domestic product'

1.3  Splitting into words
    ['gdp', 'at', 'market', 'prices']

1.7  Loading the sample passages
    loaded 3 passages

1.5  Passages containing 'income'
    ex-002

1.6  Formatted for a prompt
[ex-001] Example written for this book, sentence 1
Gross domestic product measures the value of goods and services produced in an economy in a period.

[ex-002] Example written for this book, sentence 2
Net national income starts from gross domestic product, adds income received from abroad, subtracts income paid abroad, and subtracts the wear and tear on capital.
```

Only ex-002 contains the word "income". Ex-003 does not, although purchasing power parities are used to compare incomes across countries. A reader asking about income would want it; word matching cannot see that. This is the weakness noted in 1.5.

## 1.9 Tests for this chapter

The file `tests/test_ch01_python_basics.py` holds ten tests. Each checks one function against a worked example. They run on every change to the repository; run them yourself with `python -m pytest tests/test_ch01_python_basics.py -v`.

| Test | What it proves |
| --- | --- |
| `clean_text` removes extra spaces and line breaks | Untidy PDF text becomes one tidy line |
| `clean_text` leaves tidy text unchanged | Cleaning twice does no harm |
| `split_into_words` lowers case and drops punctuation | "GDP," and "gdp" become the same word |
| `split_into_words` splits on hyphens | "non-financial" becomes two words, as 1.3.3 states |
| `make_passage` stores fields and cleans text | Every record has the four keys and clean text |
| `find_passages_containing` matches whole words only | "Income" finds "income," but not "incomes" |
| `format_passage` shows id, source, reference and text | The layout a model will read is exactly as shown in 1.6 |
| `format_passages` puts a blank line between blocks | Passages stay visibly separate |
| Save then load returns the same passages | Nothing is lost or changed in the file, accented letters included |
| The sample file loads three passages with all fields | The worked example's data is complete |

The repository also runs the rule from the front matter on every change: a chapter may import only from earlier chapters.

## 1.10 Glossary additions and links

| Term | Meaning |
| --- | --- |
| String | A piece of text, written between quotation marks |
| Function | A named, reusable set of steps; it takes arguments and returns a result |
| Argument | A value given to a function when it runs |
| Docstring | The plain-English description at the top of a function, with a worked example |
| Comment | A line starting with `#`, written for the reader and ignored by Python |
| List | An ordered collection of values, between square brackets |
| Dictionary | Values stored under names called keys, between curly brackets |
| Key | The name under which a dictionary stores a value |
| Loop | Lines that run once for each item in a collection |
| Condition | An `if` test that decides which lines run |
| f-string | A string with `f` in front, in which values in curly brackets are filled in |
| JSON | A standard text format for dictionaries and lists |
| JSON Lines | A text file holding one JSON record per line |
| Passage | One short piece of text, stored with its id, source and reference |
| Corpus | The full set of passages a system searches |

**Links**

- [Python tutorial: strings, lists, dictionaries, loops](https://docs.python.org/3/tutorial/introduction.html)
- [Python `json` module](https://docs.python.org/3/library/json.html)
- [Python `pathlib` module](https://docs.python.org/3/library/pathlib.html)
- [JSON Lines format](https://jsonlines.org/)
- [pytest: getting started](https://docs.pytest.org/en/stable/getting-started.html)
- [Chapter 1 code on GitHub](https://github.com/lavanito/python-rag-textbook/blob/main/ragbook/ch01_python_basics.py)
