"""Tests for the legal knowledge base and RAG retrieval."""
import pytest
from backend.services.legal_knowledge_base import (
    FAIR_CLAUSE_BENCHMARKS,
    EXPLOITATIVE_PATTERNS,
    retrieve_relevant_knowledge,
)


def test_benchmarks_have_required_categories():
    """Knowledge base should cover key legal categories."""
    required = {"LIABILITY", "TERMINATION", "DATA_PRIVACY", "ARBITRATION", "IP_RIGHTS", "NON_COMPETE"}
    actual = set(FAIR_CLAUSE_BENCHMARKS.keys())
    assert required.issubset(actual), f"Missing categories: {required - actual}"


def test_each_benchmark_has_required_fields():
    """Each benchmark should have fair_example, red_flags, and consumer_rights."""
    for category, data in FAIR_CLAUSE_BENCHMARKS.items():
        assert "fair_example" in data, f"{category} missing fair_example"
        assert "red_flags" in data, f"{category} missing red_flags"
        assert "consumer_rights" in data, f"{category} missing consumer_rights"
        assert isinstance(data["red_flags"], list), f"{category} red_flags should be list"
        assert len(data["red_flags"]) > 0, f"{category} should have at least 1 red flag"


def test_exploitative_patterns_structure():
    """Each exploitative pattern should have pattern, risk, and explanation."""
    for p in EXPLOITATIVE_PATTERNS:
        assert "pattern" in p
        assert "risk" in p
        assert "explanation" in p
        assert p["risk"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def test_retrieve_knowledge_with_known_category():
    """Retrieval should return benchmark for a known category."""
    result = retrieve_relevant_knowledge(
        "The company may terminate this agreement at any time.",
        "TERMINATION",
    )
    assert result["benchmark"] is not None
    assert "fair_example" in result["benchmark"]
    assert isinstance(result["matched_patterns"], list)


def test_retrieve_knowledge_with_unknown_category():
    """Retrieval should handle unknown categories gracefully."""
    result = retrieve_relevant_knowledge(
        "Some random clause text.",
        "UNKNOWN_CATEGORY",
    )
    assert result["benchmark"] is None
    assert isinstance(result["matched_patterns"], list)


def test_pattern_matching_detects_exploitative_language():
    """Pattern matcher should detect known exploitative phrases."""
    text = "You grant us a perpetual, irrevocable, royalty-free license to use your content."
    result = retrieve_relevant_knowledge(text, "IP_RIGHTS")
    assert len(result["matched_patterns"]) > 0
    assert result["matched_patterns"][0]["risk"] == "CRITICAL"
