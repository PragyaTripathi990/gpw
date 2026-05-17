"""Tests for analysis enrichment helpers."""
from backend.services.analysis_enrichment import enrich_analysis


def test_enrich_analysis_adds_top_red_flags_and_summary():
    analysis = {
        "document_type": "Freelancer Agreement",
        "overall_risk_score": 8.3,
        "recommendation": "DO NOT SIGN",
        "clause_results": [
            {
                "clause": {
                    "clause_number": 2,
                    "title": "Ownership Of Work",
                    "text": "All inventions and future rights become the sole property of the Company.",
                    "category": "IP_RIGHTS",
                },
                "verdict": {
                    "risk_score": 9,
                    "risk_types": ["EXPLOITATIVE", "RIGHTS_WAIVER"],
                    "plain_english": "The company is trying to own much more than the specific work you are hired to do.",
                    "suggested_fix": "Limit ownership to work made for hire under this agreement.",
                },
                "simple_explanation": "Too broad.",
                "matched_patterns": [
                    {
                        "pattern": "exclusive property of provider",
                        "risk": "MEDIUM",
                        "explanation": "Ideas or feedback you provide become their property.",
                    }
                ],
            }
        ],
    }

    enriched = enrich_analysis(analysis)

    assert "top_red_flags" in enriched
    assert "risk_summary" in enriched
    assert enriched["top_red_flags"][0]["clause_title"] == "Ownership Of Work"
    assert enriched["risk_summary"]["headline"]
