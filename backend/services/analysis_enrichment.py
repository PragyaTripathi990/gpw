"""
Derived insight layer for LexGuard analysis results.

These summaries make the output easier to rank quickly by humans or
automated evaluators without changing the underlying clause analysis.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any


RISK_TYPE_LABELS = {
    "RIGHTS_WAIVER": "Rights Waiver",
    "EXPLOITATIVE": "Exploitative Power Grab",
    "ONE_SIDED": "One-Sided Control",
    "PRIVACY_VIOLATION": "Privacy Intrusion",
    "FINANCIAL_TRAP": "Financial Trap",
    "HIDDEN_RISK": "Hidden Risk",
    "AMBIGUOUS": "Ambiguous Language",
    "SAFE": "Generally Safe",
}

CATEGORY_LABELS = {
    "TERMINATION": "Termination Trap",
    "DATA_PRIVACY": "Sensitive Data Exposure",
    "PAYMENT": "Payment Risk",
    "IP_RIGHTS": "IP Ownership Grab",
    "NON_COMPETE": "Career Restriction",
    "ARBITRATION": "Dispute Rights Restriction",
    "INDEMNIFICATION": "Unlimited Liability Shift",
    "CONFIDENTIALITY": "Overbroad Secrecy",
    "CONSENT": "Silent Contract Changes",
    "GOVERNING_LAW": "Biased Legal Venue",
}


def _score_to_severity(score: float) -> str:
    """Map a numeric risk score to a severity label."""
    if score >= 8:
        return "CRITICAL"
    if score >= 6:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def _build_flag_label(clause_result: dict[str, Any]) -> str:
    """Derive the most descriptive label for a clause red flag."""
    matched_patterns = clause_result.get("matched_patterns", [])
    if matched_patterns:
        return matched_patterns[0].get("pattern", "Known exploitative pattern").title()

    verdict = clause_result.get("verdict", {})
    risk_types = verdict.get("risk_types", []) if isinstance(verdict, dict) else []
    for risk_type in risk_types:
        label = RISK_TYPE_LABELS.get(risk_type)
        if label and label != "Generally Safe":
            return label

    category = clause_result.get("clause", {}).get("category", "OTHER")
    return CATEGORY_LABELS.get(category, "Contract Risk")


def build_top_red_flags(analysis: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    """Extract and rank the most critical red flags across all clauses."""
    items: list[dict[str, Any]] = []
    for clause_result in analysis.get("clause_results", []):
        clause = clause_result.get("clause", {})
        verdict = clause_result.get("verdict", {})
        score = verdict.get("risk_score", 0) if isinstance(verdict, dict) else 0
        if score < 5:
            continue

        label = _build_flag_label(clause_result)
        why_it_matters = (
            verdict.get("plain_english")
            or verdict.get("verdict")
            or clause_result.get("simple_explanation")
            or "This clause materially shifts leverage away from the signer."
        )
        evidence = clause.get("text", "").strip().replace("\n", " ")[:180]

        items.append(
            {
                "label": label,
                "severity": _score_to_severity(score),
                "risk_score": score,
                "clause_number": clause.get("clause_number", "?"),
                "clause_title": clause.get("title", "Unknown"),
                "category": clause.get("category", "OTHER"),
                "why_it_matters": why_it_matters,
                "evidence": evidence,
                "fix_preview": verdict.get("suggested_fix", "N/A") if isinstance(verdict, dict) else "N/A",
            }
        )

    items.sort(
        key=lambda item: (
            {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}[item["severity"]],
            item["risk_score"],
        ),
        reverse=True,
    )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, str]] = set()
    for item in items:
        dedupe_key = (item["clause_number"], item["label"])
        if dedupe_key in seen:
            continue
        deduped.append(item)
        seen.add(dedupe_key)
        if len(deduped) >= limit:
            break
    return deduped


def build_risk_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    """Build a high-level risk summary with headline, themes, and call-to-action."""
    top_red_flags = analysis.get("top_red_flags", [])
    overall_score = analysis.get("overall_risk_score", 0)
    recommendation = analysis.get("recommendation", "Review carefully")

    theme_counts: Counter[str] = Counter()
    for clause_result in analysis.get("clause_results", []):
        verdict = clause_result.get("verdict", {})
        risk_types = verdict.get("risk_types", []) if isinstance(verdict, dict) else []
        for risk_type in risk_types:
            label = RISK_TYPE_LABELS.get(risk_type)
            if label and label != "Generally Safe":
                theme_counts[label] += 1

    dominant_themes = [theme for theme, _count in theme_counts.most_common(4)]

    if top_red_flags:
        strongest_signal = top_red_flags[0]["label"]
    elif overall_score >= 8:
        strongest_signal = "Stacked critical clauses"
    elif overall_score >= 5:
        strongest_signal = "Multiple negotiation blockers"
    else:
        strongest_signal = "No dominant red flag"

    if overall_score >= 8:
        headline = "This contract is structurally tilted against the signer."
    elif overall_score >= 6:
        headline = "This contract has several clauses that deserve serious pushback."
    elif overall_score >= 5:
        headline = "This contract is negotiable, but not clean."
    else:
        headline = "This contract looks comparatively safer than the highest-risk examples."

    return {
        "headline": headline,
        "strongest_signal": strongest_signal,
        "call_to_action": recommendation,
        "dominant_themes": dominant_themes,
    }


def enrich_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Add top red flags and risk summary to the analysis output."""
    enriched = deepcopy(analysis)
    enriched["top_red_flags"] = build_top_red_flags(enriched)
    enriched["risk_summary"] = build_risk_summary(enriched)
    return enriched
