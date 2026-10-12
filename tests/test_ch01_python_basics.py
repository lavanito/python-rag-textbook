"""
Tests for Chapter 1 — The Python you need.

Each test checks one function against a worked example from the chapter.
"""

from ragbook.ch01_python_basics import (
    SAMPLE_FILE,
    clean_text,
    find_passages_containing,
    format_passage,
    format_passages,
    load_passages,
    make_passage,
    save_passages,
    split_into_words,
)


def test_clean_text_removes_extra_spaces_and_line_breaks():
    assert clean_text("  Gross domestic\n   product  ") == "Gross domestic product"


def test_clean_text_leaves_tidy_text_unchanged():
    assert clean_text("Net national income") == "Net national income"


def test_split_into_words_lowers_case_and_drops_punctuation():
    assert split_into_words("GDP, at market prices.") == ["gdp", "at", "market", "prices"]


def test_split_into_words_splits_on_hyphens():
    # A hyphen is punctuation, so "non-financial" becomes two words.
    assert split_into_words("non-financial") == ["non", "financial"]


def test_make_passage_stores_fields_and_cleans_text():
    passage = make_passage("ex-001", "Example", "para 1", "  GDP measures output. ")
    assert passage == {
        "id": "ex-001",
        "source": "Example",
        "reference": "para 1",
        "text": "GDP measures output.",
    }


def test_find_passages_matches_whole_words_only():
    passages = [
        make_passage("a", "Example", "1", "National income, net of depreciation."),
        make_passage("b", "Example", "2", "Incomes vary across households."),
        make_passage("c", "Example", "3", "Gross domestic product."),
    ]
    found = find_passages_containing(passages, "Income")
    found_ids = [passage["id"] for passage in found]
    assert found_ids == ["a"]


def test_format_passage_shows_id_source_reference_and_text():
    passage = make_passage("ex-001", "Example", "para 1", "GDP measures output.")
    assert format_passage(passage) == "[ex-001] Example, para 1\nGDP measures output."


def test_format_passages_puts_a_blank_line_between_blocks():
    first = make_passage("a", "Example", "1", "First.")
    second = make_passage("b", "Example", "2", "Second.")
    assert format_passages([first, second]) == "[a] Example, 1\nFirst.\n\n[b] Example, 2\nSecond."


def test_save_then_load_returns_the_same_passages(tmp_path):
    passages = [
        make_passage("a", "Example", "1", "Prix à la consommation."),
        make_passage("b", "Example", "2", "Second passage."),
    ]
    file_path = tmp_path / "passages.jsonl"
    save_passages(passages, file_path)
    assert load_passages(file_path) == passages


def test_sample_file_loads_three_passages_with_all_fields():
    passages = load_passages(SAMPLE_FILE)
    assert len(passages) == 3
    for passage in passages:
        assert set(passage.keys()) == {"id", "source", "reference", "text"}
