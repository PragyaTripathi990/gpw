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

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # "gemini" or "openai" or "groq"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

from .prompts import (
    CLAUSE_SEGMENTATION_PROMPT,
    CONTRADICTION_DETECTION_PROMPT,
    OVERALL_SUMMARY_PROMPT,
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

def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client

def _get_openai():
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
        clause_text=clause.get("text", ""),
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
    seg_prompt = CLAUSE_SEGMENTATION_PROMPT.format(document_text=document_text[:15000])
    clauses = await call_llm_json(seg_prompt)
    if isinstance(clauses, dict):
        clauses = clauses.get("clauses", [clauses])
    print(f"[LexGuard] Found {len(clauses)} clauses")
    
    # Calls 2..N: Analyze each clause (1 call each)
    results = []
    for i, clause in enumerate(clauses):
        print(f"[LexGuard] Analyzing clause {i+1}/{len(clauses)}: {clause.get('title', '?')}")
        try:
            r = await analyze_clause(clause, doc_type)
            results.append(r)
        except Exception as e:
            print(f"[LexGuard] Clause {i+1} failed: {e}")
            results.append({
                "clause": clause, "defense": "", "prosecution": "",
                "verdict": {"risk_score": 5, "risk_types": [], "verdict": "Analysis failed",
                            "plain_english": "Could not analyze this clause", "suggested_fix": "N/A",
                            "real_world_impact": "", "defense_validity": 0, "prosecution_validity": 0},
                "simple_explanation": "", "scenarios": [], "negotiation_advice": {},
                "benchmark_comparison": None, "matched_patterns": [],
            })
    
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
    contradictions = {"contradictions": [], "ambiguities": [], "missing_protections": [], "unusual_terms": []}
    try:
        all_text = "\n".join([f"CLAUSE {c.get('clause_number', i+1)}: {c.get('title', '?')} - {c.get('text', '')[:300]}" for i, c in enumerate(clauses)])
        contradictions = await call_llm_json(CONTRADICTION_DETECTION_PROMPT.format(all_clauses_text=all_text[:6000]))
    except Exception:
        pass
    
    # Call N+2: Executive summary
    print("[LexGuard] Generating summary...")
    top_risks = "\n".join([
        f"- {r['clause']['title']} ({r['verdict'].get('risk_score', '?')}/10): {r['verdict'].get('plain_english', '')[:200]}"
        for r in sorted(results, key=lambda x: x.get('verdict', {}).get('risk_score', 0) if isinstance(x.get('verdict'), dict) else 0, reverse=True)[:5]
    ])
    summary = await call_llm_text(OVERALL_SUMMARY_PROMPT.format(
        doc_type=doc_type, total_clauses=len(clauses),
        critical_count=len(critical_issues), warning_count=len(warnings),
        safe_count=len(safe_clauses), avg_score=f"{avg_score:.1f}", top_risks=top_risks,
    ))
    
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
