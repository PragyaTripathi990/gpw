"""
Deterministic contract-analysis fallback used when LLM calls fail.

The goal is not to replace the richer multi-agent path, but to ensure
LexGuard still produces structured, explainable results in restricted
or offline environments.
"""
from __future__ import annotations

import re
from typing import Any

from backend.services.legal_knowledge_base import retrieve_relevant_knowledge


NUMBERED_SECTION_RE = re.compile(r"(?m)^\s*(\d{1,3})[.)]\s+([^\n]+?)\s*$")
ALL_CAPS_SECTION_RE = re.compile(r"(?m)^\s*([A-Z][A-Z0-9 &/\-]{3,})\s*$")

CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("NON_COMPETE", ("non-compete", "non compete", "compete", "competitive activity")),
    ("IP_RIGHTS", ("intellectual property", "ownership of work", "ownership", "work product", "inventions")),
    ("DATA_PRIVACY", ("data collection", "biometric", "webcam", "microphone", "monitoring", "privacy", "ai training")),
    ("ARBITRATION", ("arbitration", "class action", "jury trial", "appeal")),
    ("INDEMNIFICATION", ("indemnify", "hold harmless", "regulatory actions", "regardless of fault")),
    ("PAYMENT", ("payment", "compensation", "fees", "forfeited", "withheld")),
    ("TERMINATION", ("termination", "terminate", "resignation", "notice before resignation")),
    ("CONFIDENTIALITY", ("confidentiality", "non-disparagement", "publicly discuss", "reputation")),
    ("CONSENT", ("automatic consent", "continued use", "future modifications", "deemed accepted")),
    ("LIABILITY", ("liability", "damages", "losses", "claims")),
    ("GOVERNING_LAW", ("governing law", "jurisdiction", "courts", "most favorable")),
]

HIGH_RISK_CATEGORIES = {
    "NON_COMPETE",
    "IP_RIGHTS",
    "DATA_PRIVACY",
    "ARBITRATION",
    "INDEMNIFICATION",
    "PAYMENT",
    "TERMINATION",
    "CONFIDENTIALITY",
    "CONSENT",
}

RISK_THEME_LABELS = {
    "RIGHTS_WAIVER": "Rights Waiver",
    "EXPLOITATIVE": "Power Imbalance",
    "ONE_SIDED": "One-Sided Control",
    "PRIVACY_VIOLATION": "Privacy Intrusion",
    "FINANCIAL_TRAP": "Financial Trap",
    "HIDDEN_RISK": "Hidden Risk",
    "AMBIGUOUS": "Ambiguous Language",
    "SAFE": "Generally Safe",
}

SEVERITY_ORDER = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}

HEURISTIC_RULES: list[dict[str, Any]] = [
    {
        "label": "Unbounded IP Grab",
        "patterns": (
            r"assigns? all worldwide intellectual property rights",
            r"sole property of the company",
            r"future rights not yet recognized",
            r"derivative concepts developed during or after",
        ),
        "score_bonus": 4,
        "risk_types": ("EXPLOITATIVE", "RIGHTS_WAIVER", "ONE_SIDED"),
        "plain_english": "The company is trying to own not just the work you do for them, but also ideas and future creations far beyond the job.",
        "impact": "You could lose control of side projects, research notes, prompts, or future inventions that should stay yours.",
        "suggested_fix": "Limit ownership to deliverables created specifically for the engagement, and carve out pre-existing IP, personal projects, and independently developed work.",
    },
    {
        "label": "Overbroad Non-Compete",
        "patterns": (
            r"for a period of\s+\d+\s+years",
            r"worldwide",
            r"substantially similar business activity",
            r"shall not engage in software development",
        ),
        "score_bonus": 4,
        "risk_types": ("EXPLOITATIVE", "RIGHTS_WAIVER", "ONE_SIDED"),
        "plain_english": "This restriction is so broad that it can block you from working in huge parts of your field for years.",
        "impact": "You could finish the contract and still be shut out of normal jobs, consulting work, or startup ideas.",
        "suggested_fix": "Limit any non-compete to a narrow product area, short duration, clear geography, and paid garden-leave style compensation if the restriction continues after termination.",
    },
    {
        "label": "Invasive Surveillance",
        "patterns": (
            r"keystrokes",
            r"biometric data",
            r"webcam activity",
            r"microphone activity",
            r"personal communications",
            r"monitoring may continue indefinitely",
        ),
        "score_bonus": 4,
        "risk_types": ("PRIVACY_VIOLATION", "EXPLOITATIVE", "RIGHTS_WAIVER"),
        "plain_english": "This clause lets the company watch and collect extremely personal information long after a normal work need ends.",
        "impact": "Your location, messages, camera, voice, and device activity could be monitored in ways that feel more like surveillance than work administration.",
        "suggested_fix": "Limit monitoring to specific business systems, exclude biometric and personal-device tracking by default, and impose a short retention period with clear consent controls.",
    },
    {
        "label": "Synthetic Identity Use",
        "patterns": (
            r"synthetic identity generation",
            r"voice recordings",
            r"facial data",
            r"behavioral characteristics",
            r"coding patterns",
            r"writing style",
        ),
        "score_bonus": 4,
        "risk_types": ("PRIVACY_VIOLATION", "RIGHTS_WAIVER", "EXPLOITATIVE"),
        "plain_english": "The company wants permission to train AI on your personal style and identity signals in ways that can outlast the contract.",
        "impact": "Your voice, face, writing, or coding patterns could be reused to build models or synthetic personas without meaningful control.",
        "suggested_fix": "Require separate opt-in consent for AI training, prohibit synthetic identity generation, and allow deletion of personal biometric or behavioral data.",
    },
    {
        "label": "Unlimited Indemnity",
        "patterns": (
            r"regardless of fault",
            r"hold harmless",
            r"regulatory actions",
            r"reputational harm",
        ),
        "score_bonus": 3,
        "risk_types": ("ONE_SIDED", "EXPLOITATIVE", "FINANCIAL_TRAP"),
        "plain_english": "You could end up paying for losses or legal trouble even when the company or outside factors are actually to blame.",
        "impact": "A dispute, investigation, or bad publicity event could be pushed onto you financially even if you did nothing wrong.",
        "suggested_fix": "Make indemnity mutual, tie it to proven breach or negligence, and keep it subject to a reasonable liability cap.",
    },
    {
        "label": "One-Sided Termination",
        "patterns": (
            r"terminate.*without notice",
            r"without explanation",
            r"without compensation",
            r"must provide 180 days written notice",
        ),
        "score_bonus": 3,
        "risk_types": ("ONE_SIDED", "EXPLOITATIVE", "RIGHTS_WAIVER"),
        "plain_english": "They can end the deal immediately, while you are trapped by a very long notice period.",
        "impact": "You could lose the engagement on the spot but still be blocked from leaving on reasonable terms yourself.",
        "suggested_fix": "Use the same termination standard for both sides, require notice except for serious cause, and reduce resignation notice to a short reasonable period.",
    },
    {
        "label": "Payment Forfeiture",
        "patterns": (
            r"compensation may be delayed",
            r"withheld",
            r"reversed",
            r"forfeited",
            r"sole discretion of the company",
        ),
        "score_bonus": 3,
        "risk_types": ("FINANCIAL_TRAP", "ONE_SIDED", "EXPLOITATIVE"),
        "plain_english": "The company can decide not to pay, or even claw money back, based on vague internal standards.",
        "impact": "You can do the work and still face delayed or lost compensation with little ability to challenge the decision.",
        "suggested_fix": "Define payment dates, objective acceptance criteria, and a clear dispute process before any withholding or chargeback is allowed.",
    },
    {
        "label": "Forced Arbitration Lock-In",
        "patterns": (
            r"binding arbitration",
            r"class action",
            r"jury trial",
            r"no right to appeal",
            r"jurisdiction selected solely by the company",
        ),
        "score_bonus": 3,
        "risk_types": ("RIGHTS_WAIVER", "ONE_SIDED", "EXPLOITATIVE"),
        "plain_english": "You are giving up normal court options and letting the company control where and how disputes get decided.",
        "impact": "If something goes wrong, pursuing a claim can become more expensive, less public, and much harder to appeal.",
        "suggested_fix": "Use a neutral venue, preserve statutory rights, and allow either party to seek court relief for urgent or small-value claims.",
    },
    {
        "label": "Unilateral Future Changes",
        "patterns": (
            r"automatic acceptance",
            r"future modifications",
            r"continued use.*constitute automatic acceptance",
            r"without notice",
        ),
        "score_bonus": 3,
        "risk_types": ("HIDDEN_RISK", "ONE_SIDED", "RIGHTS_WAIVER"),
        "plain_english": "The company can change the contract later and treat your silence or continued use as agreement.",
        "impact": "Terms can worsen after signing, and you may be bound before you even realize the rules changed.",
        "suggested_fix": "Require written notice, a clear effective date, and explicit acceptance for material contract changes.",
    },
    {
        "label": "Retroactive Confidentiality",
        "patterns": (
            r"indefinitely",
            r"already publicly known",
            r"later classifies it as confidential",
        ),
        "score_bonus": 3,
        "risk_types": ("EXPLOITATIVE", "AMBIGUOUS", "RIGHTS_WAIVER"),
        "plain_english": "The company is trying to retroactively hide information and keep the restriction going forever.",
        "impact": "You could be accused of breaking confidentiality even for things that were public or should never have been secret.",
        "suggested_fix": "Use standard confidentiality exceptions for public information, prior knowledge, and legal advice, with a reasonable time limit.",
    },
    {
        "label": "Speech Restriction",
        "patterns": (
            r"not to criticize",
            r"negatively comment",
            r"parody",
            r"mock",
            r"reference the company publicly or privately",
        ),
        "score_bonus": 2,
        "risk_types": ("RIGHTS_WAIVER", "EXPLOITATIVE"),
        "plain_english": "This tries to stop you from speaking honestly about the company, even in situations that should be protected.",
        "impact": "You may feel pressured to stay silent about unfair treatment, poor practices, or disputes.",
        "suggested_fix": "Narrow any non-disparagement term to knowingly false statements and preserve lawful reporting, testimony, and private advice.",
    },
    {
        "label": "Biased Governing Law",
        "patterns": (
            r"most favorable to the company",
            r"selected solely by the company",
        ),
        "score_bonus": 2,
        "risk_types": ("ONE_SIDED", "AMBIGUOUS"),
        "plain_english": "The company is picking legal rules and venues in whatever way benefits it most.",
        "impact": "That makes enforcement unpredictable and can deprive you of a fair, neutral forum if a dispute starts.",
        "suggested_fix": "Choose a specific, neutral governing law and forum up front instead of letting one side decide later.",
    },
]


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _normalize_title(raw_title: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw_title).strip(" :-\t")
    return cleaned.title() if cleaned.isupper() else cleaned


def infer_clause_category(title: str, text: str) -> str:
    haystack = f"{title} {text}".lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return category
    return "OTHER"


def segment_document_fallback(document_text: str) -> list[dict[str, Any]]:
    """Split contracts into clauses without relying on an LLM."""
    numbered_matches = list(NUMBERED_SECTION_RE.finditer(document_text))
    clauses: list[dict[str, Any]] = []

    if numbered_matches:
        for index, match in enumerate(numbered_matches):
            start = match.end()
            end = numbered_matches[index + 1].start() if index + 1 < len(numbered_matches) else len(document_text)
            body = document_text[start:end].strip()
            title = _normalize_title(match.group(2))
            clause_number = int(match.group(1))
            clause_text = body or title
            clauses.append(
                {
                    "clause_number": clause_number,
                    "title": title,
                    "text": clause_text,
                    "category": infer_clause_category(title, clause_text),
                }
            )
        return clauses

    caps_matches = list(ALL_CAPS_SECTION_RE.finditer(document_text))
    if caps_matches:
        for index, match in enumerate(caps_matches):
            start = match.end()
            end = caps_matches[index + 1].start() if index + 1 < len(caps_matches) else len(document_text)
            title = _normalize_title(match.group(1))
            body = document_text[start:end].strip()
            if len(body) < 30:
                continue
            clauses.append(
                {
                    "clause_number": len(clauses) + 1,
                    "title": title,
                    "text": body,
                    "category": infer_clause_category(title, body),
                }
            )
        if clauses:
            return clauses

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", document_text)
        if len(paragraph.strip()) >= 60
    ]
    for index, paragraph in enumerate(paragraphs, start=1):
        title = paragraph.splitlines()[0][:60].strip()
        clauses.append(
            {
                "clause_number": index,
                "title": _normalize_title(title or f"Clause {index}"),
                "text": paragraph,
                "category": infer_clause_category(title, paragraph),
            }
        )
    return clauses


def _match_rules(text: str) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for rule in HEURISTIC_RULES:
        if any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in rule["patterns"]):
            matched.append(rule)
    return matched


def _pattern_risk_weight(risk: str) -> int:
    return {
        "CRITICAL": 3,
        "HIGH": 2,
        "MEDIUM": 1,
        "LOW": 0,
    }.get(risk, 0)


def _score_to_severity(score: float) -> str:
    if score >= 8:
        return "CRITICAL"
    if score >= 6:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def _default_label(category: str, risk_types: list[str]) -> str:
    for risk_type in risk_types:
        if risk_type in RISK_THEME_LABELS:
            return RISK_THEME_LABELS[risk_type]
    return {
        "TERMINATION": "Termination Risk",
        "DATA_PRIVACY": "Privacy Exposure",
        "PAYMENT": "Payment Risk",
        "IP_RIGHTS": "IP Ownership Risk",
        "NON_COMPETE": "Employment Restriction",
        "ARBITRATION": "Dispute Rights Restriction",
        "INDEMNIFICATION": "Liability Shift",
        "CONFIDENTIALITY": "Speech Restriction",
        "CONSENT": "Silent Contract Changes",
        "OTHER": "Contract Risk",
    }.get(category, "Contract Risk")


def _default_plain_english(category: str, text: str, score: float) -> str:
    if score < 5:
        return "This clause looks closer to standard contract language and does not stand out as one of the most dangerous parts of the document."
    if category == "TERMINATION":
        return "This part gives the company much more control over ending the relationship than it gives you."
    if category == "DATA_PRIVACY":
        return "This part lets the company collect or keep more personal data than most people would expect."
    if category == "PAYMENT":
        return "This part makes it too easy for the company to control when or whether you get paid."
    if category == "ARBITRATION":
        return "This part limits the normal ways you could challenge the company if there is a dispute."
    if category == "IP_RIGHTS":
        return "This part reaches too far into ownership of your work, ideas, or side projects."
    snippet = re.sub(r"\s+", " ", text).strip()[:160]
    return f"This clause creates an uneven deal and needs negotiation. Key language: {snippet}"


def _default_impact(category: str) -> str:
    return {
        "TERMINATION": "You could lose the engagement quickly while still carrying obligations that continue after the company walks away.",
        "DATA_PRIVACY": "Sensitive personal information could be collected or reused in ways that are hard to reverse later.",
        "PAYMENT": "You may complete the work but still face delayed, reduced, or disputed payment.",
        "ARBITRATION": "Enforcing your rights could become slower, more expensive, and less transparent.",
        "IP_RIGHTS": "You could lose ownership or leverage over work that should remain yours.",
        "NON_COMPETE": "Your future work options may be narrowed far beyond what is reasonable.",
    }.get(category, "The clause shifts leverage to the company in a way that can hurt you if the relationship goes bad.")


def _build_defense(category: str, score: float) -> str:
    if score < 5:
        return "This clause appears closer to ordinary protective language and may be defensible as standard risk management."
    if category in {"DATA_PRIVACY", "IP_RIGHTS"}:
        return "The company would argue it needs broad rights and monitoring powers to protect systems, improve products, and avoid downstream disputes."
    if category in {"TERMINATION", "PAYMENT", "INDEMNIFICATION"}:
        return "The company would argue this gives it operational flexibility and reduces uncertainty if the relationship becomes costly or risky."
    return "The company would likely say this clause is designed to keep control, reduce litigation risk, and streamline enforcement."


def _build_prosecution(primary_label: str, rules: list[dict[str, Any]], matched_patterns: list[dict[str, Any]]) -> str:
    parts = [f"The main problem is {primary_label.lower()}."]
    if rules:
        parts.extend(rule["plain_english"] for rule in rules[:2])
    if matched_patterns:
        parts.append(matched_patterns[0]["explanation"])
    return " ".join(parts)


def _build_scenarios(primary_label: str, impact: str, score: float) -> list[dict[str, str]]:
    if score < 7:
        return []
    return [
        {
            "scenario_title": primary_label,
            "description": impact,
            "likelihood": "HIGH" if score >= 8 else "MEDIUM",
            "financial_impact": "Potentially material depending on the project value or dispute size.",
            "outcome": "Negotiate before signing, or avoid the agreement if the company refuses to narrow the clause.",
        }
    ]


def _build_negotiation(primary_label: str, suggested_fix: str, score: float) -> dict[str, Any]:
    if score < 6:
        return {}
    return {
        "negotiation_strategy": f"Treat {primary_label.lower()} as a must-fix issue and ask for mutual, limited, and clearly defined language.",
        "talking_points": [
            "This clause is broader than necessary for legitimate business protection.",
            "The current wording creates risk that is not matched by any equivalent protection for me.",
            "I need objective limits, notice rights, and a clearer carve-out for normal professional activity.",
        ],
        "acceptable_compromise": "Keep the business protection but narrow the scope, duration, retention, or discretion involved.",
        "walk_away_threshold": f"If the company insists on keeping {primary_label.lower()} in its current form.",
        "alternative_clause": suggested_fix,
    }


def analyze_clause_heuristic(clause: dict[str, Any], doc_type: str) -> dict[str, Any]:
    """Produce a structured clause review with rule-based logic."""
    clause_text = clause.get("text", "") or ""
    title = clause.get("title", "Unknown")
    category = clause.get("category") or infer_clause_category(title, clause_text)
    knowledge = retrieve_relevant_knowledge(clause_text, category)
    matched_rules = _match_rules(clause_text)
    matched_patterns = knowledge.get("matched_patterns", [])

    risk_types: list[str] = []
    score = 2
    if category in HIGH_RISK_CATEGORIES:
        score += 1
    if knowledge.get("benchmark"):
        score = max(score, 4)
    if matched_patterns:
        score += max(_pattern_risk_weight(pattern.get("risk", "")) for pattern in matched_patterns)
        risk_types.extend(["HIDDEN_RISK", "EXPLOITATIVE"])

    for rule in matched_rules:
        score += rule["score_bonus"]
        risk_types.extend(rule["risk_types"])

    if len(matched_rules) > 1:
        score += min(2, len(matched_rules) - 1)

    score = min(10, score)
    severity = _score_to_severity(score)
    primary_rule = max(matched_rules, key=lambda item: item["score_bonus"], default=None)

    if score < 5 and not risk_types:
        risk_types = ["SAFE"]

    risk_types = _unique_preserve_order(risk_types or ["HIDDEN_RISK"])
    primary_label = primary_rule["label"] if primary_rule else _default_label(category, risk_types)
    plain_english = primary_rule["plain_english"] if primary_rule else _default_plain_english(category, clause_text, score)
    impact = primary_rule["impact"] if primary_rule else _default_impact(category)
    suggested_fix = primary_rule["suggested_fix"] if primary_rule else "N/A"

    benchmark = knowledge.get("benchmark")
    if suggested_fix == "N/A" and score >= 5 and benchmark:
        suggested_fix = benchmark.get("fair_example", "N/A")

    verdict = (
        f"This clause is {severity.lower()} risk because it creates {primary_label.lower()}."
        if score >= 5
        else "This clause does not stand out as a major source of contractual abuse compared with the rest of the document."
    )
    if benchmark and score >= 5:
        verdict += " A fairer market-standard version would narrow the scope and make the obligation more balanced."

    return {
        "clause": {
            **clause,
            "category": category,
        },
        "defense": _build_defense(category, score),
        "prosecution": _build_prosecution(primary_label, matched_rules, matched_patterns),
        "verdict": {
            "risk_score": score,
            "risk_types": risk_types,
            "verdict": verdict,
            "plain_english": plain_english,
            "suggested_fix": suggested_fix,
            "real_world_impact": impact,
            "defense_validity": 4 if score >= 7 else 6,
            "prosecution_validity": 9 if score >= 7 else 7,
        },
        "simple_explanation": plain_english,
        "scenarios": _build_scenarios(primary_label, impact, score),
        "negotiation_advice": _build_negotiation(primary_label, suggested_fix, score),
        "benchmark_comparison": benchmark,
        "matched_patterns": matched_patterns,
    }


def build_document_issues_heuristic(
    clauses: list[dict[str, Any]],
    clause_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create document-level warnings without calling an LLM."""
    ambiguities: list[dict[str, Any]] = []
    unusual_terms: list[dict[str, Any]] = []
    missing_protections: list[str] = []

    ambiguity_rules = [
        ("sole discretion", ["only the company decides what counts", "the standard can change whenever the company wants"]),
        ("substantially similar", ["direct competitor only", "almost any work in the same broad field"]),
        ("most favorable to the company", ["a single fixed jurisdiction", "whatever legal regime benefits the company later"]),
        ("regardless of fault", ["only proven contractor misconduct", "any negative outcome even when the contractor is not responsible"]),
    ]

    for clause in clauses:
        text_lower = clause.get("text", "").lower()
        for phrase, interpretations in ambiguity_rules:
            if phrase in text_lower:
                ambiguities.append(
                    {
                        "clause": clause.get("title", "Unknown"),
                        "ambiguous_term": phrase,
                        "possible_interpretations": interpretations,
                    }
                )

    for result in clause_results:
        clause = result.get("clause", {})
        verdict = result.get("verdict", {})
        score = verdict.get("risk_score", 0) if isinstance(verdict, dict) else 0
        category = clause.get("category", "OTHER")
        if score >= 8:
            unusual_terms.append(
                {
                    "clause": clause.get("title", "Unknown"),
                    "why_unusual": f"{clause.get('title', 'This clause')} is unusually aggressive for a {category.lower().replace('_', ' ')} term and would normally be narrowed in a fair agreement.",
                }
            )

        if score >= 7 and category == "IP_RIGHTS":
            missing_protections.append("A carve-out for pre-existing IP, side projects, and independently developed work.")
        if score >= 7 and category == "NON_COMPETE":
            missing_protections.append("A narrow scope, short duration, limited geography, and compensation during any restricted period.")
        if score >= 7 and category == "DATA_PRIVACY":
            missing_protections.append("Specific limits on biometric monitoring, retention windows, and deletion rights.")
        if score >= 7 and category == "PAYMENT":
            missing_protections.append("Objective payment criteria and a formal process to dispute withheld compensation.")
        if score >= 7 and category == "ARBITRATION":
            missing_protections.append("A neutral venue, cost-sharing, and preserved rights for urgent court relief.")
        if score >= 7 and category == "TERMINATION":
            missing_protections.append("Mutual notice obligations and a reasonable off-ramp for both sides.")

    return {
        "contradictions": [],
        "ambiguities": ambiguities[:5],
        "missing_protections": _unique_preserve_order(missing_protections)[:5],
        "unusual_terms": unusual_terms[:5],
    }


def build_executive_summary_heuristic(
    doc_type: str,
    results: list[dict[str, Any]],
    overall_score: float,
    recommendation: str,
) -> str:
    """Generate a concise document summary without an LLM."""
    sorted_results = sorted(
        results,
        key=lambda item: item.get("verdict", {}).get("risk_score", 0),
        reverse=True,
    )
    top_titles = [item.get("clause", {}).get("title", "Unknown") for item in sorted_results[:3]]
    dominant_themes: list[str] = []
    for item in sorted_results[:5]:
        risk_types = item.get("verdict", {}).get("risk_types", [])
        for risk_type in risk_types:
            label = RISK_THEME_LABELS.get(risk_type)
            if label:
                dominant_themes.append(label.lower())
    dominant_themes = _unique_preserve_order(dominant_themes)[:3]

    if overall_score >= 8:
        risk_level = "extremely high risk"
    elif overall_score >= 6:
        risk_level = "high risk"
    elif overall_score >= 5:
        risk_level = "moderate to high risk"
    else:
        risk_level = "mixed but manageable"

    title_summary = ", ".join(title for title in top_titles if title) or "several high-risk clauses"
    theme_summary = ", ".join(dominant_themes) or "one-sided leverage"

    return (
        f"This {doc_type.lower()} is {risk_level} overall. "
        f"The strongest red flags are in {title_summary}. "
        f"Across the document, the contract concentrates power through {theme_summary}. "
        f"Recommendation: {recommendation}. Focus on narrowing ownership, limiting monitoring, fixing exit rights, and restoring fair dispute protections before signing."
    )
