"""
Test: the A5 exit condition, "each preset reproduces printed figures; client-side only".

What this checks
    - Every line of a template part that the book prints (in a text block of
      any chapter) appears, word for word, in a stored reply on the page.
      On 28 November 2026 the book prints three such lines, all for q4-02
      and q5-02 (Chapter 14.2.4).
    - The suggested questions that the book discusses give what the book
      says: q4-02 opens with the false-premise correction (Chapter 14.2.4);
      q5-01 names no year, so its GNI per head figures are for 2024
      (Chapter 13.4).
    - "Client-side only" is checked in tests/test_page.py
      (test_only_the_embedding_model_loads_from_outside).

The book prints no figures for the other suggested questions; their figures
are checked equal to Python in tests/test_bank_replies.py.

Chapter: none (demonstrator, gate A5).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
BANK = json.loads((ROOT / "app" / "data" / "bank_replies.json").read_text(encoding="utf-8"))
REPLIES = {reply["id"]: reply for reply in BANK["replies"]}
TEMPLATE_LINE = re.compile(r"edition WDI|log points|Figures \(calculated|DQR (High|Medium|Low)")


def printed_template_lines():
    """Every line of a template part printed in a text block of the book."""
    lines = []
    for chapter in sorted((ROOT / "book").glob("*.md")):
        text = chapter.read_text(encoding="utf-8")
        for block in re.findall(r"```text\n(.*?)```", text, re.S):
            lines += [line.strip() for line in block.split("\n") if TEMPLATE_LINE.search(line)]
    return lines


def all_reply_text():
    parts = []
    for reply in BANK["replies"]:
        for mode in reply["modes"].values():
            parts.append(mode["locked"])
    return "\n".join(parts)


def test_every_printed_template_line_is_on_the_page():
    printed = printed_template_lines()
    assert len(printed) >= 3
    page = all_reply_text()
    for line in printed:
        assert line in page, line


def test_q4_02_opens_with_the_false_premise_correction():
    for mode in REPLIES["q4-02"]["modes"].values():
        assert mode["locked"].startswith("The question assumes a fall; the figures show a rise.")


def test_q5_01_uses_the_latest_year():
    locked = REPLIES["q5-01"]["modes"]["non-commercial"]["locked"]
    gni_lines = [line for line in locked.split("\n") if "GNI per head" in line and "current international dollars in" in line]
    assert len(gni_lines) == 2
    assert all("in 2024." in line for line in gni_lines)


def test_suggested_questions_are_the_agreed_set():
    """Build spec v3, 'Ask: suggested questions', less q8-01 (R6, not built; 23 Nov)."""
    assert BANK["suggested"] == ["q1-01", "q2-05", "q3-01", "q4-02", "q5-01", "q6-03", "q7-01", "amb-01", "out-03"]
