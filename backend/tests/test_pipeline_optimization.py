"""Tests for pipeline fast-path optimization helpers."""
from backend.agents.pipeline import (
    _condense_clause_text,
    _select_llm_clause_indices,
    _should_use_heuristic_segmentation,
)


def test_condense_clause_text_keeps_short_text_unchanged():
    text = "Short clause text."
    assert _condense_clause_text(text, max_chars=200) == text


def test_condense_clause_text_trims_long_text_with_marker():
    text = "A" * 500 + "B" * 500 + "C" * 500
    condensed = _condense_clause_text(text, max_chars=300)
    assert len(condensed) < len(text)
    assert "omitted for faster analysis" in condensed
    assert condensed.startswith("A")
    assert condensed.endswith("C" * 250)


def test_select_llm_clause_indices_prefers_high_risk_clauses():
    heuristic_results = [
        {"verdict": {"risk_score": 3}, "matched_patterns": [], "benchmark_comparison": None},
        {"verdict": {"risk_score": 9}, "matched_patterns": [{"pattern": "x"}], "benchmark_comparison": {"fair_example": "..."},},
        {"verdict": {"risk_score": 8}, "matched_patterns": [], "benchmark_comparison": None},
        {"verdict": {"risk_score": 6}, "matched_patterns": [], "benchmark_comparison": None},
    ]

    selected = _select_llm_clause_indices(heuristic_results, max_llm_clauses=2)
    assert selected == [1, 2]


def test_should_use_heuristic_segmentation_for_structured_long_docs():
    fallback_clauses = [
        {"clause_number": 1, "title": "Payment", "text": "x", "category": "PAYMENT"},
        {"clause_number": 2, "title": "IP", "text": "x", "category": "IP_RIGHTS"},
        {"clause_number": 3, "title": "Arbitration", "text": "x", "category": "ARBITRATION"},
    ]
    assert _should_use_heuristic_segmentation("x" * 9000, fallback_clauses) is True
