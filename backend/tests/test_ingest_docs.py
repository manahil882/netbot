from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest
from scripts.ingest_docs import extract_text_from_file

def test_extract_text_pdf() -> None:
    """Verifies text extraction from a PDF file using mock PdfReader."""
    mock_pdf_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF page text content"
    mock_pdf_reader.pages = [mock_page]
    
    with patch("scripts.ingest_docs.PdfReader", return_value=mock_pdf_reader):
        sections = extract_text_from_file(Path("sample_test_doc.pdf"))
        assert len(sections) == 1
        assert sections[0]["text"] == "PDF page text content"
        assert sections[0]["page_number"] == 1

def test_extract_text_txt() -> None:
    """Verifies text extraction from a TXT/MD file using open mock."""
    with patch("builtins.open", mock_open(read_data="Plain text file content")):
        sections = extract_text_from_file(Path("sample_test_doc.txt"))
        assert len(sections) == 1
        assert sections[0]["text"] == "Plain text file content"
        assert sections[0]["page_number"] == 1

def test_extract_text_docx() -> None:
    """Verifies text extraction from a DOCX file using mock docx Document."""
    mock_doc = MagicMock()
    mock_paragraph = MagicMock()
    mock_paragraph.text = "Word document paragraph content"
    mock_doc.paragraphs = [mock_paragraph]
    
    with patch("scripts.ingest_docs.docx.Document", return_value=mock_doc):
        sections = extract_text_from_file(Path("sample_test_doc.docx"))
        assert len(sections) == 1
        assert sections[0]["text"] == "Word document paragraph content"
        assert sections[0]["page_number"] == 1


def test_extract_text_from_uploaded_bytes() -> None:
    from app.services.ingest_service import extract_text_from_bytes

    sections = extract_text_from_bytes("policy.txt", b"Refunds are issued within 14 days.")
    assert len(sections) == 1
    assert "Refunds" in sections[0]["text"]
