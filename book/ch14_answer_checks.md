# Chapter 14 — Checking answers

## 14.1 What this chapter builds

Every reply now has two parts. Python functions produce the first part, the **locked block**, from the figures with fixed templates: the figures, the differences and directions between them, what each measure means and leaves out, the source, edition, DQR, flags and escalation. The template is a bit like a mathematical formula or a function. A language model writes the second, the **explanation**, and the user who asked the question sees that explanation only if it passes every check in this chapter.

In Chapter 13, we let the model write the whole reply from the figures that were worked out in code. Of 14 replies, one reply said a figure rose by 140 when it fell by 140 (failing F15); one said two figures fell when both rose (F16); seven ended with "Passed to an analyst." although the escalation rule in the Python code said no (F17); and seven called figures "estimated" or "proxy" although no such flag was set (F18). None of these sentences needed the model. Each could be produced by a subtraction, a comparison of two numbers, the escalation rule or the list of flags. This chapter does that: a Python function builds each such sentence from the figures with a fixed template, and a test checks each template.

We call this **Governed RAG**: Python functions select the passages and calculate the figures; the language model only writes an explanation of them. The language model's step comes between Python steps. Python steps run before the model (routing in Chapter 12, reading parameters in Chapter 13, the licence filter in Chapter 8, retrieval in Chapters 3 to 10, the figures from the NNI model) and after it (the checks here, the record in Chapter 15).

The checks are closed-world: a statement that the Python checks cannot match to the locked block or to a passage counts as false. A sentence with no passage id cannot be checked, so it fails.

| Part | Written by | What it contains | If something is wrong |
| --- | --- | --- | --- |
| Locked block | Code | Figures, comparisons, definition lines, premise line, source, edition, DQR, flags, escalation | A test fails before the code is used |
| Explanation | Language model | Reasons, each sentence citing a passage | One retry, told what failed; then dropped |

The checks, one section each:

- **Numbers (14.3):** every number in the explanation is in the question, the locked block or a passage given.
- **Direction words (14.4):** the explanation uses none; the locked block states every direction.
- **Flags, DQR and escalation (14.4):** only in the locked block, never in the explanation.
- **Citations (14.5):** every sentence cites a passage it was given, the passage supports it, and no other passage given supports it better.

The decisions in this chapter are the domain expert's, made on 13 November 2026 with the agent builder's proposals and examples. The result of the laptop run (14.7) is plain: under these checks, no explanation with content passed. The locked block answered every question by itself.

## 14.2 The locked block

### 14.2.1 Principles

The locked block comes first on the page, always, and the language model never changes it. It has five parts, in this order:

1. **Premise line**, only when the question assumes a direction the figures contradict.
2. **Figures**, as Chapter 13 wrote them: value, unit, year, source, edition, DQR band and reason, flags.
3. **Comparisons** calculated by Python functions from the figures: each figure over time, each figure between editions, and each economy against the first one named.
4. **What the measures mean:** a definition line per measure.
5. **Escalation**, added only when the escalation rule in the Python program returns yes, with a demonstrator note.

**Definition lines.** Each measure has one sentence on what it means and one on what it leaves out, approved by the domain expert on 13 November 2026 (`data/definitions.csv`, record in `data/DEFINITIONS.md`). Each cites the passages that define it by id; it does not quote them. Ten of the 13 measures name the same omission in the same words: "unpaid work at home, such as caring, cooking and cleaning, most of it done by women" (source: ILO 2018, women do 76.2 per cent of unpaid care work hours).

**Edition, not "last updated".** The edition date is the release we used. It is not the date the figure was last revised.

**Directions and sizes.** The locked block gives every change a direction and a size. The sizes come from the revisions between the two editions (the domain expert, 16 November 2026): every figure in both editions, the latest minus the older, in log points for levels and percentage points for rates and shares. The 778 revisions of 0.005 or more are cut into three roughly equal parts, and the same cuts judge changes over time and gaps between economies. A change below 0.005 shows as 0.00, so it reads "unchanged".

| Size | Percentiles of the revisions | Change (log points or percentage points) |
| --- | --- | --- |
| Large | below the 16.5th or above the 83.5th | below −0.24 or above 1.72 |
| Medium | in between | −0.24 to −0.01, and 0.68 to 1.72 |
| Small | 33rd to 67th, inclusive | −0.01 to 0.68 |

Most revisions are upward, so the cuts are not symmetric around zero: a fall of 0.3 is large, a rise of 0.3 small. A revision reads "revised down (a large revision, which happens about one third of the time)". A change over time or a gap puts its size in the brackets after the number, measured against revisions: "(56.5 log points; a large change: about one third of revisions are this large)". Most changes over many years, and most gaps between economies, are large.

The first rule, agreed on 13 November, was a threshold by DQR band (High 0.5, Medium 2, Low 5 log points), below which a change was "about the same". Under it, India's 2016 revision of −2.5 log points, rated Low, was "about the same".

**Ahead and behind.** Two economies are compared by the ratio of their figures, in log points, the unit used for growth. The gap in dollars grows with prices and growth even when the ratio does not move.

**The question's premise.** A Python function looks for direction words in the question. A comparison ("fallen behind") is compared with the calculated comparisons between economies; a change ("fell") against changes over time and between editions. When they clash, the premise line opens the locked block.

### 14.2.2 Code

```python
# The size of a change (the domain expert, 16 November 2026): every non-zero
# revision between the two editions, pooled in one unit (log points for levels,
# percentage points for rates and shares) and cut into three roughly equal
# parts. The same bands judge changes over time and gaps between economies.
# tools/build_revision_bands.py writes the cuts.
BANDS_FILE = DATA_FOLDER / "series" / "revision_bands.csv"
ZERO = 0.005        # a smaller change shows as 0.00, so it counts as no change
SIZE_NOTE = "which happens about one third of the time"
SIZE_NOTE_OTHER = "about one third of revisions are this large"


def load_size_cuts(file_path=BANDS_FILE):
    """
    The four cuts, in order: the 16.5th, 33rd, 67th and 83.5th percentiles of
    the non-zero revisions.

    Example:
        load_size_cuts() returns [-0.24, -0.01, 0.68, 1.72] (rounded here)
    """
    with open(file_path, encoding="utf-8") as file:
        return [float(row["value"]) for row in csv.DictReader(file)]


SIZE_CUTS = load_size_cuts()
```

```python
def direction(change):
    """
    "up", "down" or "none": a change smaller than ZERO is none.

    Example:
        direction(-0.3) returns "down"
    """
    if abs(change) < ZERO:
        return "none"
    return "up" if change > 0 else "down"


def size(change, cuts=None):
    """
    "large", "medium" or "small": where a change falls among the revisions.
    Large below the 16.5th percentile or above the 83.5th; small from the
    33rd to the 67th, inclusive; medium in between.

    Example:
        size(-2.48) returns "large"
    """
    low_large, low_small, high_small, high_large = cuts or SIZE_CUTS
    if change < low_large or change > high_large:
        return "large"
    if low_small <= change <= high_small:
        return "small"
    return "medium"


def size_note(change, noun):
    """
    The size of a change over time or a gap, for the end of its brackets.

    Example:
        size_note(-31.2, "gap") returns "a large gap: about one third of revisions are this large"
    """
    return f"a {size(change)} {noun}: {SIZE_NOTE_OTHER}"


def sized(word, change, noun):
    """
    A direction word with the size of the change in brackets. For a revision
    the note gives how often a revision is that size; for a change over time
    or a gap, the size is still measured against revisions.

    Example:
        sized("revised down", -2.48, "revision")
        returns "revised down (a large revision, which happens about one third of the time)"
    """
    note = SIZE_NOTE if noun == "revision" else SIZE_NOTE_OTHER
    joiner = ", " if noun == "revision" else ": "
    return f"{word} (a {size(change)} {noun}{joiner}{note})"
```

```python
def premise_line(question, found):
    """
    The line that opens the locked block when the question assumes a
    direction that the figures contradict (fixes failing F16). A comparison
    between economies ("fallen behind") is checked against the calculated
    comparisons between economies; a change ("fell") against changes over
    time and between editions.

    Example:
        premise_line("Why did China's GDP per head fall ...?", [{"kind": "revision", "direction": "up", ...}])
        returns "The question assumes a fall; the figures show a rise."
    """
    text = question.lower()
    compare = assumed(text, COMPARE_DOWN, COMPARE_UP)
    text = COMPARE_UP.sub(" ", COMPARE_DOWN.sub(" ", text))
    change = assumed(text, CHANGE_DOWN, CHANGE_UP)
    between_ways = {i["direction"] for i in found if i["kind"] in ("gap", "level")}
    change_ways = {i["direction"] for i in found if i["kind"] in ("time", "revision", "growth")}
    if compare == "down" and "down" not in between_ways and "up" in between_ways:
        return "The question assumes it fell behind; the figures show it gained ground or is ahead."
    if compare == "up" and "up" not in between_ways and "down" in between_ways:
        return "The question assumes it caught up or is ahead; the figures show it lost ground or is behind."
    if change == "down" and "down" not in change_ways and "up" in change_ways:
        return "The question assumes a fall; the figures show a rise."
    if change == "up" and "up" not in change_ways and "down" in change_ways:
        return "The question assumes a rise; the figures show a fall."
    return None
```

### 14.2.3 Annotations

- `direction` gives a direction to any change of 0.005 or more, and `size` places it among the revisions. A change of −0.3 log points is "down" and large; a rise of 0.3 is small.
- `load_size_cuts` reads the four cuts from `data/series/revision_bands.csv`, which `tools/build_revision_bands.py` writes from every revision in the NNI model (`data/series/revisions.csv`). A test checks that each size has about a third of the revisions.
- `premise_line` removes comparison phrases from the question before it looks for change words. Without that step, "Has the United Kingdom fallen behind?" reads as a fall in the United Kingdom's figure, and both figures rose.
- The comparisons skip economies in the older edition when a question compares editions: a revision question is about editions, not about one economy against another.

### 14.2.4 Results

q4-02 asks why China's and India's GDP per head at PPP fell with the new ICP results. Both rose. The locked block opens with the correction (extract):

```text
The question assumes a fall; the figures show a rise.

Comparisons (calculated from the figures)
- China, GDP per head at purchasing power parities, 2022: revised up (a large revision, which happens about one third of the time), from about 21483 (edition WDI 2024-03) to about 23028 (edition WDI 2026-10-08; PWT 11.0); a change of about 1546, about 6.9 log points.
- India, GDP per head at purchasing power parities, 2022: revised up (a large revision, which happens about one third of the time), from about 8400 (edition WDI 2024-03) to about 8941 (edition WDI 2026-10-08; PWT 11.0); a change of about 541, about 6.2 log points.
```

q5-02 asks whether the United Kingdom has fallen behind the United States since 2007. The calculated comparison says the United Kingdom lost ground: the ratio moved by −0.3 log points, a large change by the size bands. Under the first rule (a threshold by DQR band) it was "about the same".

```text
- The United Kingdom against the United States, GNI per head at purchasing power parities: in 2007 the United Kingdom was behind the United States (-31.2 log points, 73.2% of its level; a large gap: about one third of revisions are this large); in 2024 the United Kingdom was behind the United States (-31.5 log points, 73.0% of its level; a large gap: about one third of revisions are this large): the United Kingdom lost ground (-0.3 log points; a large change: about one third of revisions are this large).
```

The size bands also change an earlier answer. India's GNI per head for 2016 was revised from 5710 to 5570, −2.5 log points: "revised down (a large revision, which happens about one third of the time)". Chapter 13's model wrote "increased by 140"; the first rule said "about the same".

## 14.3 Numbers

### 14.3.1 Principles

Every number in the explanation must appear in the question, the locked block or a passage given. Python functions calculate every difference before the model is asked, so the model is not asked to calculate anything. This is Chapter 13's number check, now applied to the explanation only.

Passage ids are removed before the numbers are read: "[esa10-8.94]" contains 10 and 8.94, which are not figures.

### 14.3.2 Code

```python
def invented_numbers(explanation, allowed_text):
    """
    The numbers in an explanation that are not in the allowed text (the
    question, the locked block and the passages given). Passage ids in
    square brackets are left out first, so "[esa10-8.94]" is not a number.

    Example:
        invented_numbers("It fell by 140 [esa10-8.94].", "5710 and 5570")
        returns ["140"]
    """
    return sorted(numbers_in(BRACKETS.sub(" ", explanation)) - numbers_in(allowed_text))
```

### 14.3.3 Annotations

- The check compares strings of digits, so it treats the same number written another way as new. In the run, f-01's explanation turned "65.9% of its level" into a ratio of "0.659". The value was right; the check failed it.
- The check does not stop the model repeating numbers that are allowed. Five explanations restated figures from the locked block, which the instructions ask it not to do (14.7).

## 14.4 Direction words

### 14.4.1 Principles

A direction word states a change or a comparison: rose, fell, higher, lower, ahead, behind. Chapter 13's q4-02 reply had no invented number and still said the figures fell when they rose (failing F16). A number check cannot catch that, so directions need their own rule.

The rule (the domain expert, 13 November 2026): **the explanation may not use direction words at all.** Every direction is stated in the locked block, from the calculated comparisons, and the explanation gives only reasons. The alternative, matching each direction word to a figure, fails on ordinary English. Ten cases show why:

| # | Case | Example |
| --- | --- | --- |
| 1 | Negation | "Neither fell" contains "fell" and means the opposite. |
| 2 | Reference | "It rose", "and India too": which economy, which measure? |
| 3 | Direction without the usual verbs | slowdown, recovery, catch-up, shortfall, narrowed, widened, outpaced, lagged |
| 4 | Growth against level | "Growth fell" while the level still rose (failing F3). |
| 5 | Sign against meaning | A deficit that fell is an improvement; an income gap can become "less negative". |
| 6 | Basis | The ratio, log points and dollars give different answers (q5-02, 14.2). |
| 7 | Size | When does a change count as a change? (the size bands, 14.2) |
| 8 | Time against edition | "Revised down" compares editions; "fell" compares years. q4-02 swapped the editions (F16). |
| 9 | The question's premise | q4-02 asked why figures fell when they rose. |
| 10 | Hedges and quantifiers | "broadly flat", "slightly", "most economies" |

No word list covers all ten. The closed-world rule decides which way the errors go: a direction the list misses can reach the user, and a correct sentence that uses a listed word is dropped. The first is a **miss**, the second a **false alarm**. Both are reported, never one alone.

The same section bans the words for flags, DQR and escalation, which only the locked block may state (failings F17 and F18), and remarks about the passages themselves. When the passages do not explain the point, the model writes one fixed sentence instead: "No explanation is available from the passages."

### 14.4.2 Code

```python
DIRECTION_WORDS = re.compile(
    r"\b(rose|rise|rises|rising|risen|fell|fall|falls|falling|fallen|grew|grows|growing|grown|"
    r"increas\w*|decreas\w*|declin\w*|dropp?\w*|higher|lower|highest|lowest|ahead|behind|"
    r"faster|slower|slow\w*|narrow\w*|widen\w*|outpac\w*|lagg?\w*|recover\w*|improv\w*|"
    r"wors\w*|shr[iau]nk\w*|surg\w*|jump\w*|plung\w*|soar\w*|"
    r"caught up|catch up|catching up|lost ground|gained ground|revised up|revised down)\b")

# Words for flags, data quality and escalation, which only the locked block may state (fixes
# failings F17 and F18).
CODE_WORDS = re.compile(r"\b(passed to an analyst|dqr|data quality|proxy|stand-in|estimated|flagg?\w*)\b")

# Remarks about the passages themselves (fix E): when the passages do not
# explain a point, the model writes NO_EXPLANATION instead.
PASSAGE_TALK = re.compile(r"\b(passages?|the text|provided)\b")
NO_EXPLANATION = "No explanation is available from the passages."
```

### 14.4.3 Annotations

- `\w*` after a stem catches every ending: "increas\w*" matches increase, increased and increasing.
- Known misses, tested: "more than" and "above the trend" pass. "Up" and "down" are not listed because "made up of" and "broken down" are common in the passages.
- Known false alarm, tested: "Neither fell" fails.
- "Estimated" is banned because Chapter 13's model used it as an invented flag (F18). An explanation quoting a passage about estimates also fails.

### 14.4.4 Results

In the laptop run (14.7), direction words were found in four first attempts, all in questions the checks were built from:

- **True catch:** q5-02 wrote "The United Kingdom has not fallen behind the United States since 2007", the same claim as in Chapter 13. The locked block, under the size bands, says the United Kingdom lost ground (a large change).
- **True catch:** q4-01 wrote "has decreased". The locked block states the direction itself: "revised down (a large revision, which happens about one third of the time)".
- **False alarm:** q4-02 wrote "the figures show a rise, not a fall", which agrees with the premise line in the locked block. The ban rejected it anyway. Its next sentence ("The ICP revises PPPs upward, which reduces the estimated GDP per head") contradicts the figures and had no citation, so it would have failed in any case.

*Demonstrator note: this demonstrator bans direction words from the explanation because it cannot check them reliably. A product would need a measured error rate for its direction check, a review of the explanations it drops, and someone responsible for the size bands. It will never be right every time.*

## 14.5 Citations, support and miscitation

### 14.5.1 Principles

Chapter 11 asked the model to put a passage id in square brackets after each sentence. In the 32 analyst answers of 30 October (800-token setting), 122 of 262 sentences (47%) cite nothing, only 4 answers cite every sentence, and one cites an id that does not exist (q2-31, "esa10-11.2.7" for esa10-11.27).

The rule here is strict (the domain expert, 13 November 2026). Every sentence of the explanation must cite a passage it was given, and that passage must support it:

- **Cited:** the sentence ends with an id in square brackets.
- **Given:** the id is one of the passages that the Python program selected as evidence.
- **Supported:** at least 20% of the sentence's search words (Chapter 3) are in the passage's text.
- **Not miscited:** no other passage given scores at least 20 percentage points higher. A miscited sentence with true content still fails, because a reader who opens the cited passage will not find the claim (the domain expert, 13 November).
- **Defining passage first:** for definition questions (classes Q2 and Q6), the first sentence cites the passage the knowledge graph links to the concept with `defined_in`.

Scope notes are our notes, not evidence. Support is measured against the passage's own text only.

**The domain expert's 20 judgements.** To test the word-overlap check, the domain expert judged 20 sentences drawn at random from Chapter 11's answers (seed 14), without seeing the scores. He gave two judgements per sentence: does the passage support the sentence, and does the sentence help answer the question?

| Judgement | Result |
| --- | --- |
| Support | 19 Supported, 1 Partly |
| Answers the question | 14 Yes, 3 Partly, 3 No |

The model cites honestly in this sample. Its weakness is relevance: rows 2, 3 and 4 are true but off the question, and in row 4 the defining passage (sna08-15.187) was given but not used. Seven fixes follow from what went wrong:

| Cause | Example | Fix |
| --- | --- | --- |
| A. Right passage not found | No passage defining depletion for q2-03 | A Python function looks up the defining passage in the knowledge graph; if there is none, the corpus has a gap to fill |
| B. Right passage given but ignored | q2-06, sna08-15.187 | The defining passage, selected by a Python function, goes first |
| C. Miscited | Row 7, ppp23-1.17 for ppp23-1.13 | Overlap against every passage given |
| D. The model's own claims | Row 18 | Low overlap fails; one retry; then dropped |
| E. Remarks about the passages | "the passage does not define…" | Banned; the explanation is replaced by one fixed sentence |
| F. Supported only by our scope note | Row 17 | Not evidence |
| G. True but off the question | Rows 2, 3, 18 | First sentence cites the defining passage |

### 14.5.2 Code

```python
def overlap(sentence, passage):
    """
    The share of a sentence's search words that are in a passage's text.
    Citations are left out first. Scope notes are not counted: they are our
    notes, not evidence (the domain expert, 13 November 2026).

    Example:
        overlap("PPPs are statistical constructs [ppp23-1.31].", ppp23-1.31) returns 1.0
    """
    words = set(search_words(BRACKETS.sub(" ", sentence)))
    if not words:
        return 0.0
    return len(words & set(search_words(passage["text"]))) / len(words)
```

```python
# Abbreviations whose full stops do not end a sentence (the domain expert, 16 November 2026).
ABBREVIATIONS = re.compile(r"\b(i\.e\.|e\.g\.)")


def explanation_sentences(text):
    """
    Split an explanation into sentences, with the id protocol agreed by the
    domain expert on 16 November 2026: ids go after their sentence, but a
    reply that starts with an id is read as putting every id before its
    sentence. "i.e." and "e.g." do not end a sentence.

    Example:
        explanation_sentences("[a-1] GDP is output. [b-2] GNI is income.")
        returns ["[a-1] GDP is output.", "[b-2] GNI is income."]
    """
    kept = ABBREVIATIONS.sub(lambda match: match.group(1).replace(".", "\x00"), text.strip())
    if kept.startswith("["):
        pieces = [piece.strip() for piece in SENTENCE_END.split(kept) if piece.strip()]
    else:
        pieces = sentences(kept)
    return [piece.replace("\x00", ".") for piece in pieces]
```

```python
def check_sentences(text, evidence, must_cite_first=()):
    """
    Check each sentence's citations against the passages given (evidence):
    a sentence with no id, an id not given, a sentence its passage does not
    support, a sentence whose words are in another passage given (miscited),
    and, for definition questions, a first sentence that does not cite the
    defining passage (fix G). Returns a list of problems in plain words.

    Example:
        check_sentences("GDI is income.", evidence)
        returns ["Sentence 1 has no passage id: 'GDI is income.'"]
    """
    by_id = {p["id"]: p for p in evidence}
    same_letters = {i.lower(): i for i in by_id}      # ids compared without capitals
    problems = []
    for number, sentence in enumerate(explanation_sentences(text), 1):
        ids = [same_letters.get(i.lower(), i) for i in cited_ids(sentence)]
        if not ids:
            problems.append(f"Sentence {number} has no passage id: '{sentence}'")
            continue
        unknown = [i for i in ids if i not in by_id]
        if unknown:
            problems.append(f"Sentence {number} cites {', '.join(unknown)}, which you were not given.")
            continue
        best_cited = max(overlap(sentence, by_id[i]) for i in ids)
        if best_cited < SUPPORT_MIN:
            problems.append(f"Sentence {number} is not supported by the passage it cites: '{sentence}'")
        others = [(overlap(sentence, p), p["id"]) for p in evidence if p["id"] not in ids]
        if others:
            share, better = max(others)
            if share >= best_cited + MISCITED_BY:
                problems.append(f"Sentence {number} cites {', '.join(ids)}, but its words are in "
                                f"{better}: cite {better} if that is the source.")
        if number == 1 and must_cite_first and not set(ids) & set(must_cite_first):
            problems.append(f"Sentence 1 must cite the defining passage: {', '.join(must_cite_first)}.")
    return problems
```

### 14.5.3 Annotations

- The problems are written as sentences because the retry (14.6) shows them to the model as they stand.
- An unknown id ends the checks for that sentence: there is no passage to measure support against.
- `SUPPORT_MIN` (0.2) and `MISCITED_BY` (0.2) were chosen by looking at the domain expert's 20 judgements. Agreement with those 20 is therefore a training score.

### 14.5.4 Results

Chapter 11's analyst answers, rechecked without a new model run: 31 of 32 fail the strict rule. Only q2-10 passes ("What is a price level index?", three sentences, each citing ppp23-ov.13).

Against the domain expert's 20 judgements (training), the check passes 17 sentences; he judged 19 Supported. They differ on four rows:

| Row | Question | Domain expert | Check | Reading |
| --- | --- | --- | --- | --- |
| 7 | q2-09 | Supported | Fails: miscited (ppp23-1.13 scores 0.65, the cited ppp23-1.17 0.15) | Agrees with the domain expert's rule that a miscitation is a failure |
| 15 | q2-23 | Supported | Fails: miscited (sna25-23.68 scores 0.59, the cited CSO passage 0.05) | The sentence names the 2025 SNA but cites the CSO |
| 17 | q2-25 | Partly | Passes | Its support comes from our scope note; overlap with the BEA text is still 0.43 |
| 18 | q2-26 | Supported | Fails: overlap 0.15 | The passage defines double deflation but does not say it reflects "true volume growth" |

*Demonstrator note: support is checked by word overlap, which misses claims that reuse the passage's words but go beyond them. A product would measure this check against expert judgements and review what it lets through.*

## 14.6 Evidence, one retry and the fall-back

### 14.6.1 Principles

**The Python program selects the evidence.** The explanation may use only the passages that the program gives the model, at most five, after Chapter 8's licence filter, in this order:

1. The passages that define the concepts the question names (the knowledge graph's `defined_in`).
2. For questions routed to passages (route R4), the top three by BM25 (Chapter 3).
3. The passages that define the measures in the locked block (`data/definitions.csv`).

So every explanation has evidence to cite, even for a question routed only to the NNI model.

**Lookups get no explanation.** A question in class Q1 (one figure) is answered fully by the locked block.

**One retry, then the fall-back** (the domain expert, 13 November 2026). If the first explanation fails any check, the model gets the problems in plain words and one more try. If the second also fails, the page shows the locked block, then:

"The written explanation came from a language model and did not pass our quality checks, so it is not shown. Please contact our analyst if you want to know more."

*Demonstrator note: this is a demonstration, not a product. A product would let you ask for the explanation to be refined, and would send your question to a named analyst. Here, no analyst receives it.*

A failed check never escalates by itself; escalation is set only by the escalation rule, from the data. Every attempt is kept in the record, so the failures can be read later (Chapter 15).

We did not delete only the failing sentences: the sentences left often depend on the deleted ones ("This method…"), and the reader would not know the text was cut.

### 14.6.2 Code

```python
EXPLAIN_INSTRUCTIONS = """You explain answers about national accounts statistics. The figures, the comparisons between them, what each measure means, and the data quality are already given under LOCKED BLOCK. Explain why, using only the passages under PASSAGES.

- Put the id of the passage each sentence comes from in square brackets at the end of the sentence, before the full stop. Every sentence needs one. Example, with a made-up id: Gross national income is the total primary income received by residents [example-1.1]. Use only the ids under PASSAGES.
- Do not repeat figures or work out numbers.
- Do not use words for direction or comparison, such as rose, fell, grew, higher, lower, increase, decrease, ahead, behind, faster, slower, narrowed or widened. The locked block states every direction.
- Do not write about data quality, flags, estimates or proxies, and do not pass the question to an analyst. The locked block does that.
- Do not comment on the passages themselves. If they do not explain the point, write only: No explanation is available from the passages.
- At most 120 words. No headings."""
```

```python
def explain(question, question_class, locked, evidence, must_cite_first, ask):
    """
    Ask for an explanation, check it, retry once if it fails, and drop it if
    the retry fails too (the domain expert, 13 November 2026). Lookups (class Q1) get no
    explanation. Returns the status, the text shown, and every attempt.
    """
    if question_class == "Q1":
        return {"status": "lookup", "shown": None, "attempts": []}
    messages = explanation_messages(question, locked, evidence, must_cite_first)
    attempts = []
    for attempt in (1, 2):
        reply = ask(messages, EXPLAIN_SETTINGS)
        checks = check_explanation(reply["answer"], question, locked, evidence, must_cite_first)
        attempts.append({"reply": reply["answer"], "checks": checks,
                         "prompt_tokens": reply["prompt_tokens"],
                         "reply_tokens": reply["reply_tokens"], "seconds": reply["seconds"]})
        if passed(checks):
            status = "passed" if attempt == 1 else "passed on retry"
            return {"status": status, "shown": reply["answer"], "attempts": attempts}
        messages = retry_messages(messages, reply["answer"], problems_in_words(checks))
    return {"status": "dropped", "shown": None, "attempts": attempts}
```

### 14.6.3 Annotations

- `ask` is passed in, so the tests use a stand-in that gives fixed replies and the laptop run uses Ollama (Chapter 11's `ask_model_with_details`).
- The retry adds the model's first reply and the problems to the same conversation, so the model sees what it wrote and why it failed.
- Temperature 0: the same messages give the same reply, so a retry differs only because the problems were added.

### 14.6.4 Near measures

Three of the fair-test questions asked for a measure the NNI model does not have: real GDP per head (f-03) and revisions to the GDP level (f-04, f-06). The domain expert agreed the nearest measures in advance: GDP per head at PPP, and revisions to real GDP growth, with the answer stated in those terms. The locked block names the measure it used, but it does not yet say that this differs from the one asked for.

*Demonstrator note: when the data do not have the measure you asked for, this demonstrator answers with a near one chosen in advance. A product would find the nearest measure by meaning, say how near it is, and tell you plainly that it is not the measure you asked for.*

## 14.7 Results

### 14.7.1 The run

The checks were frozen in a commit (`9b1e82e`, 14 November 2026) before the agent builder saw the domain expert's 10 new questions. The domain expert agreed their labels on 16 November, and one laptop run (qwen3:4b-instruct, temperature 0) answered 24 questions in 30.9 minutes:

- **Training:** the bank's 14 questions routed to the NNI model, from which failings F15 to F18 came.
- **Fair:** the domain expert's 10 new questions (3 compare, 3 revision, 3 why, 1 lookup).

Command: `python -m ragbook.ch14_answer_checks --explain`. Saved run: `data/answers/ch14_explanations.jsonl`.

### 14.7.2 Results

**No explanation with content passed.** Every explanation shown is the fixed sentence "No explanation is available from the passages." The locked block answered every question by itself.

| Set | Questions | Lookup | Passed | Passed on retry | Dropped | Explanations with content shown |
| --- | --- | --- | --- | --- | --- | --- |
| Training (bank) | 14 | 2 | 2 | 0 | 10 | 0 |
| Fair (new) | 10 | 1 | 4 | 1 | 4 | 0 |

Of 15 first attempts that failed, the retry rescued one (f-06), and it did so by writing the fixed sentence.

What the 21 explanations did (one explanation can do several):

| What the model did | Questions | Kind of failure |
| --- | --- | --- |
| Wrote only the fixed sentence | q5-03, q7-01, f-02, f-03, f-04, f-05, f-06 (retry) | Passed, with nothing to say |
| Restated figures from the locked block | q3-02, q4-01, q5-01, q6-02, f-01, f-06 | Real: the instructions forbid it |
| Cited the locked block ("[locked-block]", "[Comparisons]") | q4-01, f-01 | Real: it wanted to cite the figures |
| Grouped all ids at the end of the paragraph | q4-02, q5-01, q5-05, q6-02 | Real: earlier sentences uncited |
| Used direction words | q4-01, q4-02, q5-01, q5-02 | Real in three; false alarm in q4-02 |
| Cited an id it was not given | q3-01, q5-05, f-07 | Real: invented or misspelt ("sn25-11.238") |
| Put each id before its sentence | q6-03, f-07, f-08, f-09 | False alarm: the check reads the id as the previous sentence's |
| Added the fixed sentence after other sentences | q3-01, q3-02, q6-03, f-07, f-09 | Real: the rule says "write only" |
| Contradicted the figures | q4-02 ("reduces the estimated GDP per head") | Real |

Three fair-test explanations came close. f-07 failed on one misspelt id and an id in lower case ("sna25-a4.59"). f-08 placed ids before sentences, and the sentence splitter cut "i.e." into a sentence of its own: both false alarms. f-09 left one sentence uncited.

### 14.7.3 What this shows

- **The locked block works.** It corrected q4-02's premise, gave q5-02 "about the same" under the first rule, and named a missing year (f-02, hours end 2023) and the escalation.
- **The model mostly restates rather than explains.** Given the figures and up to five passages, it repeated the figures or declined. Where it gave reasons, it rarely cited each sentence.
- **The checks have false alarms of their own:** ids placed before a sentence, "i.e." read as a sentence end, ids in lower case, and a direction word used to agree with the locked block. A product would need to count these separately from real failures.
- **The fair score and the training score tell the same story:** zero explanations with content in both.

Possible changes: show the model an example of where ids go; accept an id at the start of a sentence; treat "i.e." and "e.g." as part of a sentence; compare ids without regard to capitals; reject restated figures outright. The domain expert chose four of them on 16 November 2026; 14.8 reports the rerun.

### 14.7.4 Findings for later chapters

Running the frozen code on the new questions, before any model run, showed these gaps:

- No statement of a peak or the largest value (f-03, f-04).
- Comparing a growth rate's first and last years over a span says nothing (f-04). To fix.
- A revision over a span lists every year: about 24 lines for f-04 and f-05.
- The knowledge graph has no passage marked as defining PPP (f-09).
- Questions routed only to passages show "Figures: none" and do not yet quote the passages in the locked block, as decision 1 says they should.

*Demonstrator note: in this demonstrator a small model on a laptop writes the explanations, and strict checks drop every one that cannot be traced to a passage. A product would use a larger model, measure the checks' false alarms, and have analysts read the explanations it drops.*

## 14.8 After the review: the rerun

### 14.8.1 What changed

The domain expert reviewed the run on 16 November 2026. He judged two replies the fixes would let through: f-08's retry good (each sentence close to its passage), f-09's retry a fault (cited correctly, but it does not answer the question). With those labels, the saved replies were checked again in Python, with no model run:

| Checks | Good replies dropped (of 1) | Faulty replies shown (of 28) |
| --- | --- | --- |
| As frozen | 1 (f-08) | 0 |
| Ids at the start, "i.e.", capitals | 0 | 0 |
| The same, and a trailing fixed sentence removed | 0 | 1 (f-09) |

He chose the second row and an instruction with an example:

- **An id protocol.** The id goes at the end of its sentence, before the full stop. A reply that starts with an id is read as putting every id before its sentence.
- **"i.e." and "e.g."** do not end a sentence.
- **Ids are compared without regard to capitals:** sna25-a4.59 is sna25-A4.59.
- **Not chosen:** removing a fixed sentence added after other sentences (it would have shown f-09), and rejecting restated figures (no verdict changed).
- **Headings in literal words:** "Figures (calculated from the data)" and "Comparisons (calculated from the figures)", not "written by code".
- **Size bands** for every change (14.2), in place of the thresholds by DQR band.

### 14.8.2 Results

One laptop run on 16 November 2026 answered the same 24 questions in 32.4 minutes. Every score here is a training score: the fixes were chosen with f-08 and f-09 in view.

| Set | Questions | Lookup | Passed | Passed on retry | Dropped | Shown with content |
| --- | --- | --- | --- | --- | --- | --- |
| Training (bank) | 14 | 2 | 3 | 2 | 7 | 0 |
| The domain expert's 10 | 10 | 1 | 5 | 2 | 2 | 2 |

- **Two explanations with content passed:** f-07 (depletion), three sentences, each citing its passage at the end; and f-08 (modified NNI), four sentences close to their passages, saying nothing about Ireland.
- **The other passes are the fixed sentence.** Why, compare and revision questions still get no explanation with content.
- **The example id was copied.** The instruction's example cited esa10-8.94, and the model cited it when it was not given (q3-01, q6-02). The example now uses a made-up id, [example-1.1]; that change has not been run.

Command: `python -m ragbook.ch14_answer_checks --explain --review`. Saved run: `data/answers/ch14_explanations_review.jsonl`.

## Tests

`tests/test_ch14_answer_checks.py`, 33 tests; with the earlier chapters, 310 pass. A stand-in replaces the language model, so no Ollama is needed. They check:

- every measure has an approved definition whose passages exist, and the unpaid-work clause appears in the 10 measures the domain expert agreed;
- directions and size bands (q4-01's revision is "revised down (a large revision…)"; each size has about a third of the revisions);
- the id protocol: ids before sentences, "i.e." inside a sentence, ids compared without capitals;
- the premise line for q4-02, and that "fallen behind" is read as a comparison (q5-02);
- the number check ignores passage ids;
- the word lists, including one known miss and one known false alarm;
- the citation checks, the miscitation in the domain expert's row 7, the defining passage first, and the fixed sentence;
- the evidence respects the licence filter and the cap of five;
- the retry names the problems, and two failures drop the explanation.

## Glossary additions

- **Locked block:** the part of a reply that Python functions produce from the figures with fixed templates; the language model never changes it.
- **Explanation:** text written by the language model under the locked block, shown only if it passes every check.
- **Governed RAG:** retrieval and generation in which Python functions select the passages and calculate the figures, and the language model only writes an explanation of them.
- **Closed-world check:** a check that treats anything it cannot trace to the locked block or a passage as false.
- **Definition line:** what a measure means and what it leaves out, approved by the domain expert, citing passage ids.
- **Direction word:** a word that states a change or a comparison (rose, fell, higher, lower, ahead, behind).
- **Size band:** large, medium or small: where a change falls among the revisions between the two editions; each band has about a third of them.
- **Id protocol:** where a passage id goes: at the end of its sentence, or before every sentence when the reply starts with an id.
- **Premise line:** the line that opens the locked block when the question assumes a direction the figures contradict.
- **Support:** the cited passage says what the sentence says; here measured by word overlap.
- **Word overlap:** the share of a sentence's search words found in a passage's text.
- **Miscitation:** a sentence cites one passage given, while its words are in another.
- **Defining passage:** the passage the knowledge graph links to a concept with `defined_in`.
- **Retry:** a second call to the model, showing it the problems the checks found.
- **Fall-back:** the locked block alone, with the withheld line, after the retry fails.
- **Miss:** a check passes something wrong.
- **False alarm:** a check rejects something correct.
- **Demonstrator note:** an italic line saying what this demonstrator lacks and what a product would do.
- **Freeze commit:** the commit that fixes the checks before new test questions are written.
- **Edition:** the dated data release a figure comes from.

## Links

- Code: `ragbook/ch14_answer_checks.py`; tests: `tests/test_ch14_answer_checks.py`
- Definitions and their record: `data/definitions.csv`, `data/DEFINITIONS.md`
- The domain expert's 20 judgements: `data/answers/ch14_support_judgements.csv`
- Fair-test questions: `data/question_bank/ch14_fair_test.jsonl`; saved runs: `data/answers/ch14_explanations.jsonl`, `data/answers/ch14_explanations_review.jsonl`
- Revisions and size bands: `data/series/revisions.csv`, `data/series/revision_bands.csv`, `tools/build_revision_bands.py`
- Chapter 11 analyst answers: `data/answers/ch11_answers_800.jsonl`; Chapter 13 replies: `data/answers/ch13_replies.jsonl`
- Repository: [github.com/lavanito/python-rag-textbook](https://github.com/lavanito/python-rag-textbook), branch `ch14-review`
- [ILO, *Care work and care jobs for the future of decent work* (2018), news release](https://www.ilo.org/resource/news/ilo-calls-urgent-action-prevent-looming-global-care-crisis)
- [World Bank metadata, population (SP.POP.TOTL)](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/SP.POP.TOTL)
