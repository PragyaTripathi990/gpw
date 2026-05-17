"""Tests for deterministic fallback analysis."""
from backend.services.heuristic_fallback import (
    analyze_clause_heuristic,
    build_document_issues_heuristic,
    build_executive_summary_heuristic,
    segment_document_fallback,
)


def test_segment_document_fallback_handles_numbered_sections():
    document = """
1. PAYMENT TERMS
Compensation may be withheld at the sole discretion of the Company.

2. NON-COMPETE
The Contractor shall not engage in substantially similar business activity worldwide for 7 years.
"""
    clauses = segment_document_fallback(document)
    assert len(clauses) == 2
    assert clauses[0]["title"] == "Payment Terms"
    assert clauses[0]["category"] == "PAYMENT"
    assert clauses[1]["category"] == "NON_COMPETE"


def test_analyze_clause_heuristic_detects_overbroad_non_compete():
    clause = {
        "clause_number": 4,
        "title": "Non-Compete",
        "text": (
            "For a period of 7 years following termination of this Agreement, "
            "the Contractor shall not engage in software development or any substantially "
            "similar business activity worldwide."
        ),
        "category": "NON_COMPETE",
    }
    result = analyze_clause_heuristic(clause, "Freelancer Agreement")
    assert result["verdict"]["risk_score"] >= 8
    assert "RIGHTS_WAIVER" in result["verdict"]["risk_types"]
    assert "working in huge parts of your field" in result["verdict"]["plain_english"]


def test_heuristic_document_issues_and_summary_are_structured():
    clause = {
        "clause_number": 1,
        "title": "Automatic Consent",
        "text": "Continued use shall constitute automatic acceptance of future modifications at the Company's sole discretion.",
        "category": "CONSENT",
    }
    result = analyze_clause_heuristic(clause, "General Contract")
    issues = build_document_issues_heuristic([clause], [result])
    summary = build_executive_summary_heuristic("General Contract", [result], 8.0, "DO NOT SIGN")

    assert isinstance(issues["ambiguities"], list)
    assert isinstance(issues["missing_protections"], list)
    assert "DO NOT SIGN" in summary
