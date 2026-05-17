"""
LexGuard Multi-Agent Adversarial Pipeline
==========================================
Supports BOTH Google Gemini and OpenAI as LLM backend.
Set LLM_PROVIDER=openai in .env to use OpenAI, otherwise defaults to Gemini.

For hackathon demo: switch back to Gemini when quota resets.
"""
import json
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_configured_provider = os.getenv("LLM_PROVIDER", "").strip().lower()

if _configured_provider:
    LLM_PROVIDER = _configured_provider
elif GEMINI_API_KEY:
    LLM_PROVIDER = "gemini"
elif OPENAI_API_KEY:
    LLM_PROVIDER = "openai"
elif GROQ_API_KEY:
    LLM_PROVIDER = "groq"
else:
    LLM_PROVIDER = "gemini"


def _env_flag(name: str, default: bool) -> bool:
    """Read a boolean flag from environment variables."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


ANALYSIS_CONCURRENCY = max(1, int(os.getenv("LEXGUARD_ANALYSIS_CONCURRENCY", "3")))
MAX_LLM_CLAUSES = max(0, int(os.getenv("LEXGUARD_MAX_LLM_CLAUSES", "6")))
MAX_CLAUSE_PROMPT_CHARS = max(900, int(os.getenv("LEXGUARD_MAX_CLAUSE_PROMPT_CHARS", "1800")))
HEURISTIC_SEGMENTATION_MIN_CLAUSES = max(
    1, int(os.getenv("LEXGUARD_HEURISTIC_SEGMENTATION_MIN_CLAUSES", "3"))
)
USE_HEURISTIC_SEGMENTATION_FIRST = _env_flag("LEXGUARD_HEURISTIC_SEGMENTATION_FIRST", True)
USE_LLM_CONTRADICTIONS = _env_flag("LEXGUARD_USE_LLM_CONTRADICTIONS", False)
USE_LLM_SUMMARY = _env_flag("LEXGUARD_USE_LLM_SUMMARY", False)

from .prompts import (
    CLAUSE_SEGMENTATION_PROMPT,
    CONTRADICTION_DETECTION_PROMPT,
    OVERALL_SUMMARY_PROMPT,
)
from backend.services.heuristic_fallback import (
    analyze_clause_heuristic,
    build_document_issues_heuristic,
    build_executive_summary_heuristic,
    segment_document_fallback,
)

# RAG knowledge base (local, no API calls)
try:
    from backend.services.legal_knowledge_base import retrieve_relevant_knowledge
    HAS_RAG = True
except Exception:
    HAS_RAG = False


# ============================================================
# LLM CALL LAYER — supports Gemini, OpenAI, and Groq
# ============================================================

_groq_client = None
_openai_client = None


def _condense_clause_text(text: str, max_chars: int = MAX_CLAUSE_PROMPT_CHARS) -> str:
    """Shrink long clauses before prompting to reduce token usage."""
    normalized = (text or "").strip()
    if len(normalized) <= max_chars:
        return normalized

    section_len = max(250, (max_chars - 80) // 3)
    middle_start = max(0, len(normalized) // 2 - section_len // 2)
    middle_end = middle_start + section_len
    omitted = max(0, len(normalized) - (section_len * 3))

    return (
        f"{normalized[:section_len]}\n"
        f"...[{omitted} characters omitted for faster analysis]...\n"
        f"{normalized[middle_start:middle_end]}\n"
        "...[continuing]...\n"
        f"{normalized[-section_len:]}"
    )


def _should_use_heuristic_segmentation(document_text: str, fallback_clauses: list[dict]) -> bool:
    """Prefer deterministic segmentation for long, structured contracts."""
    if not USE_HEURISTIC_SEGMENTATION_FIRST or not fallback_clauses:
        return False
    if len(fallback_clauses) >= HEURISTIC_SEGMENTATION_MIN_CLAUSES:
        return True
    return len(document_text) > 8000 and len(fallback_clauses) >= 2


def _llm_priority_tuple(result: dict) -> tuple[int, int, int]:
    """Rank clauses so expensive LLM review focuses on the highest-signal issues."""
    verdict = result.get("verdict", {})
    score = verdict.get("risk_score", 0) if isinstance(verdict, dict) else 0
    matched_patterns = result.get("matched_patterns", [])
    benchmark = result.get("benchmark_comparison")
    return (
        int(score),
        len(matched_patterns),
        1 if benchmark else 0,
    )


def _select_llm_clause_indices(heuristic_results: list[dict], max_llm_clauses: int = MAX_LLM_CLAUSES) -> list[int]:
    """Choose which clauses deserve deep LLM analysis."""
    if max_llm_clauses <= 0 or not heuristic_results:
        return []
    if len(heuristic_results) <= max_llm_clauses:
        return list(range(len(heuristic_results)))

    ranked_indices = sorted(
        range(len(heuristic_results)),
        key=lambda idx: _llm_priority_tuple(heuristic_results[idx]),
        reverse=True,
    )

    selected: list[int] = []
    for threshold in (8, 6):
        for idx in ranked_indices:
            score = heuristic_results[idx].get("verdict", {}).get("risk_score", 0)
            if score >= threshold and idx not in selected:
                selected.append(idx)
                if len(selected) >= max_llm_clauses:
                    return sorted(selected)

    for idx in ranked_indices:
        if idx not in selected:
            selected.append(idx)
        if len(selected) >= max_llm_clauses:
            break
    return sorted(selected)

def _get_groq():
    """Lazy-initialize and return the Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _get_openai():
    """Lazy-initialize and return the OpenAI client singleton."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _parse_json_safe(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{') if '{' in text else text.find('[')
        end = max(text.rfind('}'), text.rfind(']')) + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        return {}


async def call_llm_json(prompt: str) -> dict:
    """Call LLM and get JSON response."""
    if LLM_PROVIDER == "groq":
        client = _get_groq()
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt + "\n\nRespond with ONLY valid JSON, no markdown."}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=8000,
        )
        return _parse_json_safe(response.choices[0].message.content)
    elif LLM_PROVIDER == "openai":
        client = _get_openai()
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=8192,
        )
        return json.loads(response.choices[0].message.content)
    else:
        import google.generativeai as genai
        from backend.config import GEMINI_API_KEY, GEMINI_FLASH_MODEL
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        response = await asyncio.to_thread(
            model.generate_content, prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4, max_output_tokens=8192,
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)


async def call_llm_text(prompt: str) -> str:
    """Call LLM and get text response."""
    if LLM_PROVIDER == "groq":
        client = _get_groq()
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    elif LLM_PROVIDER == "openai":
        client = _get_openai()
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    else:
        import google.generativeai as genai
        from backend.config import GEMINI_API_KEY, GEMINI_FLASH_MODEL
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        response = await asyncio.to_thread(
            model.generate_content, prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7, max_output_tokens=4096,
            )
        )
        return response.text


# ============================================================
# COMBINED PROMPT: All 6 agents in ONE call per clause
# ============================================================
COMBINED_ANALYSIS_PROMPT = """You are LexGuard, an AI legal analysis system with multiple expert personas.
Analyze this contract clause by role-playing as ALL of the following experts:

CLAUSE TITLE: {title}
CATEGORY: {category}
DOCUMENT TYPE: {doc_type}
CLAUSE TEXT: "{clause_text}"
{rag_section}

Return a JSON object with these keys:

{{
  "defense": "[As CORPORATE LAWYER: 2-3 paragraphs defending this clause as standard and justified]",
  "prosecution": "[As CONSUMER ADVOCATE: 2-3 paragraphs attacking all risks - exploitative terms, hidden costs, one-sided liability, privacy issues, rights waivers. Give real-world examples]",
  "verdict": {{
    "risk_score": <1-10, where 10=critical>,
    "risk_types": ["EXPLOITATIVE", "AMBIGUOUS", "HIDDEN_RISK", "ONE_SIDED", "PRIVACY_VIOLATION", "FINANCIAL_TRAP", "RIGHTS_WAIVER", "SAFE"],
    "verdict": "[As NEUTRAL JUDGE: 3-4 sentence balanced assessment]",
    "plain_english": "[Simple language a teenager understands]",
    "suggested_fix": "[Fairer rewritten clause, or N/A if safe]",
    "real_world_impact": "[One concrete example of how this hurts the user]",
    "defense_validity": <1-10>,
    "prosecution_validity": <1-10>
  }},
  "simple_explanation": "[What it says (1-2 sentences). What it means for you (impact). Think of it like (analogy)]",
  "scenarios": [
    {{"scenario_title": "<title>", "description": "<what happens>", "likelihood": "HIGH/MEDIUM/LOW", "financial_impact": "<cost>", "outcome": "<what user can do>"}}
  ],
  "negotiation_advice": {{
    "negotiation_strategy": "<approach>",
    "talking_points": ["<point1>", "<point2>", "<point3>"],
    "acceptable_compromise": "<middle ground>",
    "walk_away_threshold": "<when to refuse>",
    "alternative_clause": "<fair rewrite>"
  }}
}}

If risk_score < 5, set scenarios to [] and negotiation_advice to {{}}.
Return ONLY valid JSON.
"""


async def analyze_clause(clause: dict, doc_type: str) -> dict:
    """Run ALL 6 agents in a SINGLE API call per clause."""
    
    # RAG: local knowledge lookup (no API call needed)
    rag_section = ""
    benchmark_comparison = None
    matched_patterns = []
    if HAS_RAG:
        try:
            knowledge = retrieve_relevant_knowledge(
                clause.get("text", ""), clause.get("category", "OTHER"),
            )
            benchmark_comparison = knowledge.get("benchmark")
            matched_patterns = knowledge.get("matched_patterns", [])
            if benchmark_comparison:
                rag_section = f"\nBENCHMARK (fair version): \"{benchmark_comparison.get('fair_example', '')}\""
                rag_section += f"\nRED FLAGS: {', '.join(benchmark_comparison.get('red_flags', []))}"
        except Exception:
            pass
    
    prompt = COMBINED_ANALYSIS_PROMPT.format(
        title=clause.get("title", "Unknown"),
        category=clause.get("category", "OTHER"),
        doc_type=doc_type,
        clause_text=_condense_clause_text(clause.get("text", "")),
        rag_section=rag_section,
    )
    
    result = await call_llm_json(prompt)
    
    verdict = result.get("verdict", {})
    if isinstance(verdict, str):
        verdict = {"risk_score": 5, "verdict": verdict, "risk_types": [],
                   "plain_english": verdict, "suggested_fix": "N/A",
                   "real_world_impact": "", "defense_validity": 5, "prosecution_validity": 5}
    
    return {
        "clause": clause,
        "defense": result.get("defense", ""),
        "prosecution": result.get("prosecution", ""),
        "verdict": verdict,
        "simple_explanation": result.get("simple_explanation", ""),
        "scenarios": result.get("scenarios", []),
        "negotiation_advice": result.get("negotiation_advice", {}),
        "benchmark_comparison": benchmark_comparison,
        "matched_patterns": matched_patterns,
    }


async def analyze_document(document_text: str, doc_type: str = "General Contract") -> dict:
    """Run complete LexGuard analysis."""
    
    print(f"[LexGuard] Using LLM provider: {LLM_PROVIDER}")
    
    # Call 1: Segment clauses
    print("[LexGuard] Segmenting clauses...")
    fallback_clauses = segment_document_fallback(document_text)
    clauses = []

    if _should_use_heuristic_segmentation(document_text, fallback_clauses):
        print("[LexGuard] Using heuristic-first segmentation for faster full-document coverage")
        clauses = fallback_clauses
    else:
        try:
            seg_prompt = CLAUSE_SEGMENTATION_PROMPT.format(document_text=document_text[:15000])
            clauses = await call_llm_json(seg_prompt)
            if isinstance(clauses, dict):
                clauses = clauses.get("clauses", [clauses])
            if not isinstance(clauses, list):
                clauses = []
        except Exception as e:
            print(f"[LexGuard] Clause segmentation failed, using fallback: {e}")
            clauses = []

        clauses = [
            {
                **clause,
                "clause_number": clause.get("clause_number", i + 1),
                "title": clause.get("title", f"Clause {i + 1}"),
                "text": clause.get("text", ""),
                "category": clause.get("category", "OTHER"),
            }
            for i, clause in enumerate(clauses)
            if isinstance(clause, dict) and clause.get("text")
        ]

        if not clauses:
            clauses = fallback_clauses
        elif len(document_text) > 15000 and len(fallback_clauses) > len(clauses):
            print("[LexGuard] Using heuristic segmentation for better full-document coverage")
            clauses = fallback_clauses
    print(f"[LexGuard] Found {len(clauses)} clauses")
    
    # Calls 2..N: Analyze highest-signal clauses deeply, keep heuristics for the rest
    heuristic_results = [analyze_clause_heuristic(clause, doc_type) for clause in clauses]
    selected_llm_indices = _select_llm_clause_indices(heuristic_results)
    print(
        f"[LexGuard] Deep-reviewing {len(selected_llm_indices)}/{len(clauses)} clauses "
        f"with LLM (concurrency={ANALYSIS_CONCURRENCY})"
    )

    results = list(heuristic_results)

    async def _analyze_selected_clause(idx: int) -> tuple[int, dict]:
        """Run deep LLM analysis for a single clause by index."""
        clause = clauses[idx]
        print(f"[LexGuard] Deep analysis for clause {idx+1}/{len(clauses)}: {clause.get('title', '?')}")
        try:
            return idx, await analyze_clause(clause, doc_type)
        except Exception as e:
            print(f"[LexGuard] Clause {idx+1} failed, keeping heuristic fallback: {e}")
            return idx, heuristic_results[idx]

    if selected_llm_indices:
        semaphore = asyncio.Semaphore(ANALYSIS_CONCURRENCY)

        async def _bounded(idx: int) -> tuple[int, dict]:
            """Semaphore-bounded wrapper for concurrent clause analysis."""
            async with semaphore:
                return await _analyze_selected_clause(idx)

        llm_results = await asyncio.gather(*[_bounded(idx) for idx in selected_llm_indices])
        for idx, clause_result in llm_results:
            results[idx] = clause_result
    
    # Compute scores
    risk_scores = []
    critical_issues, warnings, safe_clauses = [], [], []
    for r in results:
        v = r.get("verdict", {})
        score = v.get("risk_score", 5) if isinstance(v, dict) else 5
        risk_scores.append(score)
        if score >= 8: critical_issues.append(r)
        elif score >= 5: warnings.append(r)
        else: safe_clauses.append(r)
    
    avg_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    max_score = max(risk_scores) if risk_scores else 0
    
    if avg_score >= 8: grade, recommendation = "F", "DO NOT SIGN"
    elif avg_score >= 6.5: grade, recommendation = "D", "DO NOT SIGN WITHOUT MAJOR CHANGES"
    elif avg_score >= 5: grade, recommendation = "C", "NEGOTIATE BEFORE SIGNING"
    elif avg_score >= 3.5: grade, recommendation = "B", "GENERALLY SAFE — REVIEW WARNINGS"
    else: grade, recommendation = "A", "SAFE TO SIGN"
    
    # Call N+1: Contradiction detection
    print("[LexGuard] Detecting contradictions...")
    contradictions = build_document_issues_heuristic(clauses, results)
    if USE_LLM_CONTRADICTIONS and clauses:
        try:
            all_text = "\n".join([f"CLAUSE {c.get('clause_number', i+1)}: {c.get('title', '?')} - {c.get('text', '')[:300]}" for i, c in enumerate(clauses)])
            contradictions = await call_llm_json(CONTRADICTION_DETECTION_PROMPT.format(all_clauses_text=all_text[:6000]))
        except Exception as e:
            print(f"[LexGuard] Contradiction detection failed, using heuristic fallback: {e}")
    
    # Call N+2: Executive summary
    print("[LexGuard] Generating summary...")
    top_risks = "\n".join([
        f"- {r['clause']['title']} ({r['verdict'].get('risk_score', '?')}/10): {r['verdict'].get('plain_english', '')[:200]}"
        for r in sorted(results, key=lambda x: x.get('verdict', {}).get('risk_score', 0) if isinstance(x.get('verdict'), dict) else 0, reverse=True)[:5]
    ])
    summary = build_executive_summary_heuristic(doc_type, results, avg_score, recommendation)
    if USE_LLM_SUMMARY and selected_llm_indices:
        try:
            summary = await call_llm_text(OVERALL_SUMMARY_PROMPT.format(
                doc_type=doc_type, total_clauses=len(clauses),
                critical_count=len(critical_issues), warning_count=len(warnings),
                safe_count=len(safe_clauses), avg_score=f"{avg_score:.1f}", top_risks=top_risks,
            ))
        except Exception as e:
            print(f"[LexGuard] Summary generation failed, using heuristic fallback: {e}")
    
    print(f"[LexGuard] Done! Grade: {grade}, Score: {avg_score:.1f}/10")
    
    return {
        "document_type": doc_type,
        "total_clauses": len(clauses),
        "overall_risk_score": round(avg_score, 1),
        "max_risk_score": max_score,
        "risk_grade": grade,
        "recommendation": recommendation,
        "executive_summary": summary,
        "critical_issues": len(critical_issues),
        "warnings_count": len(warnings),
        "safe_count": len(safe_clauses),
        "clause_results": results,
        "contradictions": contradictions,
    }
