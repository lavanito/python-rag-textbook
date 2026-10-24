"""Tests for Chapter 6 — Chunking."""

import hashlib

import pytest

from ragbook.ch06_chunking import (
    CHUNK_WORDS,
    EXAMPLE_PDF,
    all_methods,
    chunk_sizes,
    clean_pdf_text,
    count_words,
    cut_to_fit,
    find_heading_lines,
    font_sizes,
    fixed_size_chunks,
    header_chunks,
    pack,
    paragraph_chunks,
    read_pdf_pages,
    recursive_chunks,
    remove_first_page_footer,
    remove_running_header,
    repair_text,
    split_paragraphs,
    split_sections,
    split_sentences,
)

EXPECTED_SHA256 = "6203bc15a46196a4cb0933b2a26e119e5d74f3e845129f5420aed8ababb35901"


def test_example_pdf_is_the_published_file():
    digest = hashlib.sha256(EXAMPLE_PDF.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256


def test_read_pdf_pages_counts():
    pages = read_pdf_pages(EXAMPLE_PDF)
    assert len(pages) == 34
    assert pages[-1].strip() == ""
    assert pages[0].startswith("Extrapolating PPPs and Comparing")
    assert sum(len(page_text.split()) for page_text in pages) == 17384


def test_remove_running_header_number_on_its_own_line():
    page_text = "474\nMeasuring the real size of the World econo My\nText."
    assert remove_running_header(page_text) == "Text."


def test_remove_running_header_number_and_header_on_one_line():
    page_text = "487Extra Polating PPP s and coMParing\nText."
    assert remove_running_header(page_text) == "Text."


def test_remove_running_header_leaves_other_pages_alone():
    assert remove_running_header("Title\nText.") == "Title\nText."


def test_repair_text_examples():
    text, counts = repair_text("the esti -\nmates of the ICP .")
    assert text == "the estimates of the ICP."
    assert counts["word broken by a hyphen at the end of a line"] == 1
    assert repair_text("T esting\nT\nhe ••")[0] == "Testing\n\nThe •"


def test_remove_first_page_footer():
    page_text = "Text \n18\nPaul Mccarthy\nCHAPTER\n473"
    assert remove_first_page_footer(page_text) == "Text "
    assert remove_first_page_footer("Text.") == "Text."


def test_clean_pdf_text_joins_words_across_pages():
    text, _ = clean_pdf_text(["Title\nA long esti -", "2\nHeader\nmate.", ""])
    assert text == "Title\n\nA long estimate."


def test_paragraph_end_is_a_line_with_no_space_at_its_end():
    text, counts = repair_text("Line one \nends here.\nNext paragraph.")
    assert text == "Line one\nends here.\n\nNext paragraph."
    assert counts["line with no space at its end: a paragraph ends, so add an empty line"] == 1


def test_clean_example_no_running_headers_left():
    text, counts = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    assert "econo My" not in text and "Econo My" not in text
    assert "BEnChmark" not in text and "BEnch Mark" not in text
    assert len(text.split()) == 16634
    assert "Paul Mccarthy" not in text
    assert counts["word broken by a hyphen at the end of a line"] == 83
    assert counts["capital T split from the rest of its word"] == 16


def test_known_fault_hyphenated_compound_is_joined():
    # Reported in 6.3.3: one of the 83 hyphen repairs joins a real compound.
    text, _ = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    assert "PPPbased" in text


def test_equation_bracket_pieces_removed():
    text, counts = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    assert not any("\ue000" <= character <= "\uf8ff" for character in text)
    assert "\u202f" not in text
    assert "\n\n\n" not in text
    assert counts["piece of a large bracket drawn from a font's private symbols"] == 244


def test_paragraph_continues_across_page_and_footer():
    # The first paragraph after the opening runs from page 473 to page 474,
    # with the first-page footer between.
    text, counts = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    assert "from this imputation\nprocedure depends" in text
    assert counts["line with no space at its end: a paragraph ends, so add an empty line"] == 519
    assert len(split_paragraphs(text)) == 425


# 6.4 Fixed-size chunks

def test_count_words():
    assert count_words("Real GDP\nper head") == 4


def test_fixed_size_chunks_without_overlap():
    assert fixed_size_chunks("a b c d e", size=2) == ["a b", "c d", "e"]


def test_fixed_size_chunks_with_overlap():
    assert fixed_size_chunks("a b c d e", size=2, overlap=1) == ["a b", "b c", "c d", "d e"]
    assert fixed_size_chunks("a b c", size=5, overlap=2) == ["a b c"]


def test_fixed_size_chunks_rejects_overlap_as_large_as_size():
    with pytest.raises(ValueError):
        fixed_size_chunks("a b c", size=2, overlap=2)


# 6.5 Paragraph chunks

def test_split_paragraphs():
    assert split_paragraphs("One\nline.\n\nTwo.\n\n") == ["One line.", "Two."]


def test_pack():
    assert pack(["a b", "c", "d e f"], size=3) == ["a b c", "d e f"]
    assert pack(["a b c d"], size=3) == ["a b c d"]


def test_paragraph_chunks():
    assert paragraph_chunks("a b\n\nc\n\nd e f", size=3) == ["a b\n\nc", "d e f"]


# 6.6 Header chunks

def test_font_sizes_example():
    sizes = dict(font_sizes(EXAMPLE_PDF))
    assert font_sizes(EXAMPLE_PDF)[0] == (10.0, 89714)
    assert sizes[15.0] == 806 and sizes[12.0] == 110 and sizes[18.0] == 53


def test_find_heading_lines_example():
    heading_lines = find_heading_lines(EXAMPLE_PDF)
    assert len(heading_lines) == 37
    assert heading_lines[:3] == [
        "Extrapolating PPPs and Comparing",
        "ICP Benchmark Results",
        "Estimating PPPs for Nonbenchmark Years",
    ]
    assert heading_lines.count("Conclusion") == 2


def test_split_sections_and_header_chunks():
    text = "Intro.\n\nANNEX A\n\nPrices\nand costs\n\nText.\n\nMore."
    heading_lines = ["ANNEX A", "Prices", "and costs"]
    assert split_sections(text, heading_lines) == [
        ("", "Intro."),
        ("ANNEX A Prices and costs", "Text.\n\nMore."),
    ]
    assert header_chunks(text, heading_lines) == [
        "Intro.",
        "ANNEX A Prices and costs\n\nText.\n\nMore.",
    ]


def test_header_chunks_example():
    text, _ = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    sections = split_sections(text, find_heading_lines(EXAMPLE_PDF))
    assert len(sections) == 24
    assert sections[0][0] == "Extrapolating PPPs and Comparing ICP Benchmark Results"
    assert sections[5][0] == "International Comparisons in World Development Indicators"
    assert sections[18][0] == "ANNEX A World Bank Atlas Method"


# 6.7 Recursive chunking

def test_split_sentences():
    assert split_sentences("GDP rose. It fell (later).") == ["GDP rose.", "It fell (later)."]
    assert split_sentences("Prices rose, e.g., for food.") == ["Prices rose, e.g., for food."]


def test_cut_to_fit_uses_paragraphs_then_sentences_then_words():
    assert cut_to_fit("a b c.\n\nd e. F g h i.", size=3) == ["a b c.", "d e.", "F g h", "i."]


def test_recursive_chunks_repeat_the_heading():
    text = "Prices\n\na b.\n\nc d."
    assert recursive_chunks(text, ["Prices"], size=3) == ["Prices\n\na b.", "Prices\n\nc d."]


def test_recursive_chunks_example_fit_and_keep_every_word():
    text, _ = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    heading_lines = find_heading_lines(EXAMPLE_PDF)
    chunks = recursive_chunks(text, heading_lines)
    assert max(count_words(chunk) for chunk in chunks) <= CHUNK_WORDS
    bodies = [body for _, body in split_sections(text, heading_lines)]
    without_headings = [chunk.split("\n\n", 1)[1] for chunk in chunks]
    assert " ".join(" ".join(bodies).split()) == " ".join(" ".join(without_headings).split())


# 6.8 Comparing the methods

def test_chunk_sizes():
    assert chunk_sizes(["a", "b c", "d e f"]) == {
        "chunks": 3, "smallest": 1, "median": 2, "largest": 3,
    }


def test_chunk_limit_fits_the_embedding_model():
    # 90 words is the largest limit at which no recursive chunk of the
    # example passes all-MiniLM-L6-v2's 256 word pieces (checked on the
    # laptop, 24 Oct 2026: 243 pieces at most; 100 words gave 260).
    assert CHUNK_WORDS == 90


def test_compare_methods_on_example():
    text, _ = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    methods = all_methods(text, find_heading_lines(EXAMPLE_PDF))
    counts = {name: len(chunks) for name, chunks in methods.items()}
    assert counts == {
        "fixed size": 185,
        "fixed size with overlap": 231,
        "paragraph": 158,
        "header": 24,
        "recursive": 278,
    }
    assert chunk_sizes(methods["header"])["largest"] == 2638
    assert chunk_sizes(methods["paragraph"])["largest"] == 279
