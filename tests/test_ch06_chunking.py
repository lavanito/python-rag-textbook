"""Tests for Chapter 6 — Chunking (sections 6.2 and 6.3)."""

import hashlib

from ragbook.ch06_chunking import (
    EXAMPLE_PDF,
    clean_pdf_text,
    read_pdf_pages,
    remove_running_header,
    repair_text,
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
    assert repair_text("T esting\nT\nhe ••")[0] == "Testing\nThe •"


def test_clean_pdf_text_joins_words_across_pages():
    text, _ = clean_pdf_text(["Title\nA long esti -", "2\nHeader\nmate.", ""])
    assert text == "Title\nA long estimate."


def test_clean_example_no_running_headers_left():
    text, counts = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    assert "econo My" not in text and "Econo My" not in text
    assert "BEnChmark" not in text and "BEnch Mark" not in text
    assert len(text.split()) == 16883
    assert counts["word broken by a hyphen at the end of a line"] == 83
    assert counts["capital T split from the rest of its word"] == 16


def test_known_fault_hyphenated_compound_is_joined():
    # Reported in 6.3.3: one of the 83 hyphen repairs joins a real compound.
    text, _ = clean_pdf_text(read_pdf_pages(EXAMPLE_PDF))
    assert "PPPbased" in text
