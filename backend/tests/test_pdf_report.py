"""Tests for PDF report generation."""
import pytest
from backend.services.pdf_report import generate_pdf_report


def _make_mock_analysis():
    """Create a mock analysis result for testing."""
    return {
        "document_type": "SaaS Agreement",
        "total_clauses": 2,
        "overall_risk_score": 7.5,
        "max_risk_score": 9,
        "risk_grade": "D",
        "recommendation": "DO NOT SIGN WITHOUT MAJOR CHANGES",
        "executive_summary": "This contract has significant risks.",
        "critical_issues": 1,
        "warnings_count": 1,
        "safe_count": 0,
        "clause_results": [
            {
                "clause": {"clause_number": 1, "title": "Termination", "text": "Company may terminate at any time.", "category": "TERMINATION"},
                "verdict": {"risk_score": 9, "plain_english": "They can cut you off anytime.", "suggested_fix": "Add 30-day notice.", "risk_types": ["EXPLOITATIVE"]},
            },
            {
                "clause": {"clause_number": 2, "title": "Payment", "text": "All fees non-refundable.", "category": "PAYMENT"},
                "verdict": {"risk_score": 6, "plain_english": "No refunds ever.", "suggested_fix": "N/A", "risk_types": ["FINANCIAL_TRAP"]},
            },
        ],
    }


def test_generate_pdf_returns_bytes():
    """PDF generation should return bytes."""
    pdf = generate_pdf_report(_make_mock_analysis())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0


def test_pdf_starts_with_correct_header():
    """PDF output should start with %PDF header."""
    pdf = generate_pdf_report(_make_mock_analysis())
    assert pdf[:5] == b"%PDF-"


def test_pdf_handles_empty_clauses():
    """PDF should handle analysis with no clause results."""
    analysis = _make_mock_analysis()
    analysis["clause_results"] = []
    pdf = generate_pdf_report(analysis)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0
