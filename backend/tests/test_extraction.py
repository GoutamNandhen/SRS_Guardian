import pytest
from pathlib import Path
from backend.app.nlp.extractors import (
    extract_pdf,
    extract_docx,
    extract_txt,
    extract_text,
    ExtractedDocument,
)
from backend.app.nlp.cleaning import (
    clean_text,
    remove_repeated_headers_footers,
    remove_standalone_page_numbers,
    repair_hyphenated_line_breaks,
    join_wrapped_lines,
    collapse_excess_whitespace,
)
from backend.app.utils.file_validation import validate_file


def test_txt_extraction():
    path = Path("data/test/sample_srs.txt")
    doc = extract_txt(path)
    assert isinstance(doc, ExtractedDocument)
    assert doc.page_count == 1
    assert "ONLINE BANKING SYSTEM" in doc.text
    assert "REQ-001" in doc.text
    assert "REQ-006" in doc.text


def test_docx_extraction_paragraphs_and_tables():
    path = Path("data/test/sample_srs.docx")
    doc = extract_docx(path)
    assert isinstance(doc, ExtractedDocument)
    assert doc.page_count >= 1
    assert "ONLINE BANKING SYSTEM" in doc.text
    assert "REQ-001" in doc.text
    # Verify table cells were extracted
    assert "REQ-004" in doc.text
    assert "at least 8 characters" in doc.text
    assert "REQ-005" in doc.text


def test_pdf_extraction():
    path = Path("data/test/sample_srs.pdf")
    doc = extract_pdf(path)
    assert isinstance(doc, ExtractedDocument)
    assert doc.page_count == 2
    assert "ONLINE BANKING SYSTEM" in doc.text
    assert "REQ-001" in doc.text
    assert "REQ-006" in doc.text


def test_extract_text_dispatcher():
    doc_txt = extract_text("data/test/sample_srs.txt")
    assert doc_txt.meta["file_type"] == "txt"

    doc_docx = extract_text("data/test/sample_srs.docx")
    assert doc_docx.meta["file_type"] == "docx"

    doc_pdf = extract_text("data/test/sample_srs.pdf")
    assert doc_pdf.meta["file_type"] == "pdf"

    with pytest.raises(ValueError):
        extract_text("data/test/unsupported.xyz")


def test_cleaning_hyphenation_and_whitespace():
    raw = "The sys-\ntem shall allow users to reset their pass-\nword."
    repaired = repair_hyphenated_line_breaks(raw)
    assert "system" in repaired
    assert "password" in repaired


def test_cleaning_page_numbers():
    raw = "Header text\nPage 1 of 10\nSome requirement\n- 2 -\nEnd text"
    cleaned = remove_standalone_page_numbers(raw)
    assert "Page 1 of 10" not in cleaned
    assert "- 2 -" not in cleaned
    assert "Some requirement" in cleaned


def test_cleaning_repeated_headers_footers():
    pages = [
        "Header Company Inc\nTitle Page 1\nContent 1\nFooter Confidential",
        "Header Company Inc\nContent 2\nFooter Confidential",
        "Header Company Inc\nContent 3\nFooter Confidential",
    ]
    cleaned = remove_repeated_headers_footers(pages, threshold=0.6)
    for p in cleaned:
        assert "Header Company Inc" not in p
        assert "Footer Confidential" not in p
        assert "Content" in p


def test_cleaning_preserves_raw_text():
    raw = "REQ-001: First line.\nREQ-002: Second line."
    result = clean_text(raw)
    assert result.raw_text == raw
    assert "REQ-001" in result.cleaned_text
    assert "REQ-002" in result.cleaned_text


def test_file_validation(tmp_path):
    # Valid existing file
    valid, err = validate_file("data/test/sample_srs.txt")
    assert valid
    assert err == ""

    # Non-existent file
    valid, err = validate_file("data/test/non_existent.txt")
    assert not valid
    assert "does not exist" in err

    # Unsupported format
    unsupported = tmp_path / "test.jpg"
    unsupported.write_text("dummy")
    valid, err = validate_file(unsupported)
    assert not valid
    assert "Unsupported file format" in err

    # Empty file
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    valid, err = validate_file(empty)
    assert not valid
    assert "empty" in err
