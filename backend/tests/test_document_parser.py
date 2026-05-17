"""Tests for document parsing service."""
import pytest
from backend.services.document_parser import parse_text, parse_docx, parse_pdf_fallback


def test_parse_text_basic():
    """Plain text parser should return text as-is."""
    result = parse_text("Hello world")
    assert result["text"] == "Hello world"
    assert result["method"] == "plain_text"
    assert result["pages"] == 1


def test_parse_text_strips_whitespace():
    """Parser should strip leading/trailing whitespace."""
    result = parse_text("   test   ")
    assert result["text"] == "test"


def test_parse_text_empty():
    """Parser should handle empty string."""
    result = parse_text("")
    assert result["text"] == ""


def test_parse_text_multiline():
    """Parser should preserve multiline text."""
    text = "Line 1\nLine 2\nLine 3"
    result = parse_text(text)
    assert result["text"] == text


def test_parse_text_unicode():
    """Parser should handle unicode characters."""
    text = "Contrat de licence — Droits réservés © 2024"
    result = parse_text(text)
    assert "Contrat" in result["text"]
    assert "©" in result["text"]
