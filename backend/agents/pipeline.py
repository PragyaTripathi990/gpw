"""
LexGuard Multi-Agent Adversarial Pipeline
Uses Google Gemini for the adversarial debate system.
"""
import json
import asyncio
import google.generativeai as genai
from typing import Optional
from .prompts import (
    CLAUSE_SEGMENTATION_PROMPT,
    CORPORATE_LAWYER_PROMPT,
    CONSUMER_ADVOCATE_PROMPT,
    JUDGE_PROMPT,
    SIMPLIFIER_PROMPT,
    OVERALL_SUMMARY_PROMPT,
    SCENARIO_SIMULATION_PROMPT,
    NEGOTIATION_PROMPT,
    CONTRADICTION_DETECTION_PROMPT,
)
from backend.config import GEMINI_API_KEY, GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL

# RAG + Embeddings (optional — gracefully degrades)
try:
    from backend.services.legal_knowledge_base import retrieve_relevant_knowledge, FAIR_CLAUSE_BENCHMARKS
    HAS_RAG = True
except Exception:
    HAS_RAG = False


def configure_gemini():
    """Configure the Gemini API."""
    genai.configure(api_key=GEMINI_API_KEY)


def get_model(model_name: str = GEMINI_FLASH_MODEL):
    """Get a Gemini model instance."""
    return genai.GenerativeModel(model_name)


async def call_gemini(prompt: str, model_name: str = GEMINI_FLASH_MODEL, retries: int = 3) -> str:
    """Make an async call to Gemini with retry on rate limit."""
    model = get_model(model_name)
    for attempt in range(retries):
        try:
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=4096,
                )
            )
            return response.text
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = (attempt + 1) * 15
                print(f"Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise


async def call_gemini_json(prompt: str, model_name: str = GEMINI_FLASH_MODEL, retries: int = 3) -> dict:
    """Make a Gemini call and parse JSON response with retry."""
    model = get_model(model_name)
    for attempt in range(retries):
        try:
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                )
            )
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                text = response.text
                start = text.find('[') if text.find('[') < text.find('{') or text.find('{') == -1 else text.find('{')
                end = text.rfind(']') + 1 if start == text.find('[') else text.rfind('}') + 1
                if start != -1 and end > start:
                    return json.loads(text[start:end])
                raise
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = (attempt + 1) * 15
                print(f"Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise


# ============================================================
# STAGE 1: Clause Segmentation
# ============================================================
async def segment_clauses(document_text: str) -> list[dict]:
    """Split document into individual clauses using Gemini."""
    prompt = CLAUSE_SEGMENTATION_PROMPT.format(document_text=document_text[:15000])
    result = await call_gemini_json(prompt, GEMINI_FLASH_MODEL)
    if isinstance(result, dict):
        result = [result]
    return result


# ============================================================
# STAGE 2: Adversarial Analysis (per clause)
# ============================================================
async def run_corporate_lawyer(clause: dict, doc_type: str, rag_context: str = "") -> str:
    """Agent 1: Corporate Lawyer — defends the clause."""
    rag_section = ""
    if rag_context:
        rag_section = f"\nRELEVANT LEGAL KNOWLEDGE (for reference):\n{rag_context}\n"
    prompt = CORPORATE_LAWYER_PROMPT.format(
        category=clause.get("category", "OTHER"),
        title=clause.get("title", "Unknown"),
        clause_text=clause.get("text", ""),
        doc_type=doc_type,
        rag_context=rag_section,
    )
    return await call_gemini(prompt, GEMINI_FLASH_MODEL)


async def run_consumer_advocate(clause: dict, doc_type: str, rag_context: str = "") -> str:
    """Agent 2: Consumer Advocate — attacks the clause."""
    rag_section = ""
    if rag_context:
        rag_section = f"\nRELEVANT LEGAL KNOWLEDGE & BENCHMARKS (use these to compare):\n{rag_context}\n"
    prompt = CONSUMER_ADVOCATE_PROMPT.format(
        category=clause.get("category", "OTHER"),
        title=clause.get("title", "Unknown"),
        clause_text=clause.get("text", ""),
        doc_type=doc_type,
        rag_context=rag_section,
    )
    return await call_gemini(prompt, GEMINI_FLASH_MODEL)


async def run_judge(clause: dict, defense: str, prosecution: str) -> dict:
    """Agent 3: Judge — delivers verdict."""
    prompt = JUDGE_PROMPT.format(
        title=clause.get("title", "Unknown"),
        category=clause.get("category", "OTHER"),
        clause_text=clause.get("text", ""),
        defense_argument=defense,
        prosecution_argument=prosecution,
    )
    return await call_gemini_json(prompt, GEMINI_FLASH_MODEL)


async def run_simplifier(clause: dict, risk_score: int) -> str:
    """Agent 4: Simplifier — translates to plain English."""
    prompt = SIMPLIFIER_PROMPT.format(
        clause_text=clause.get("text", ""),
        risk_score=risk_score,
    )
    return await call_gemini(prompt, GEMINI_FLASH_MODEL)


# ============================================================
# STAGE 3: Full adversarial analysis for one clause
# ============================================================
async def run_scenario_simulation(clause: dict, risk_score: int) -> list:
    """Agent 5: Scenario Simulator — shows real-world consequences."""
    if risk_score < 5:
        return []  # Skip for safe clauses
    prompt = SCENARIO_SIMULATION_PROMPT.format(
        clause_text=clause.get("text", ""),
        category=clause.get("category", "OTHER"),
        risk_score=risk_score,
    )
    try:
        return await call_gemini_json(prompt, GEMINI_FLASH_MODEL)
    except Exception:
        return []


async def run_negotiation_advisor(clause: dict, risk_score: int, key_issues: str) -> dict:
    """Agent 6: Negotiation Advisor — suggests how to negotiate."""
    if risk_score < 5:
        return {}  # Skip for safe clauses
    prompt = NEGOTIATION_PROMPT.format(
        clause_text=clause.get("text", ""),
        category=clause.get("category", "OTHER"),
        risk_score=risk_score,
        key_issues=key_issues,
    )
    try:
        return await call_gemini_json(prompt, GEMINI_FLASH_MODEL)
    except Exception:
        return {}


async def analyze_clause(clause: dict, doc_type: str) -> dict:
    """Run the full adversarial pipeline for a single clause."""
    
    # Step 0: RAG — retrieve relevant legal knowledge & benchmarks
    rag_context = ""
    benchmark_comparison = None
    matched_patterns = []
    
    if HAS_RAG:
        try:
            knowledge = retrieve_relevant_knowledge(
                clause.get("text", ""),
                clause.get("category", "OTHER"),
            )
            rag_context = knowledge.get("rag_context", "")
            benchmark_comparison = knowledge.get("benchmark")
            matched_patterns = knowledge.get("matched_patterns", [])
        except Exception:
            pass
    
    # Step 1: Corporate Lawyer defends
    defense = await run_corporate_lawyer(clause, doc_type, rag_context)
    await asyncio.sleep(2)  # Small delay to avoid rate limit
    
    # Step 2: Consumer Advocate attacks
    prosecution = await run_consumer_advocate(clause, doc_type, rag_context)
    await asyncio.sleep(2)
    
    # Step 3: Judge weighs both sides
    verdict = await run_judge(clause, defense, prosecution)
    await asyncio.sleep(2)
    
    # Step 4: Get risk score for downstream agents
    risk_score = verdict.get("risk_score", 5) if isinstance(verdict, dict) else 5
    key_issues = verdict.get("verdict", "") if isinstance(verdict, dict) else ""
    
    # Step 5: Simplifier
    simple_explanation = await run_simplifier(clause, risk_score)
    await asyncio.sleep(2)
    
    # Step 6: Scenarios + Negotiation (only for risky clauses)
    scenarios = await run_scenario_simulation(clause, risk_score)
    await asyncio.sleep(2)
    negotiation = await run_negotiation_advisor(clause, risk_score, key_issues)
    
    return {
        "clause": clause,
        "defense": defense,
        "prosecution": prosecution,
        "verdict": verdict,
        "simple_explanation": simple_explanation,
        "scenarios": scenarios,
        "negotiation_advice": negotiation,
        "benchmark_comparison": benchmark_comparison,
        "matched_patterns": matched_patterns,
    }


# ============================================================
# STAGE 4: Full document analysis
# ============================================================
async def analyze_document(document_text: str, doc_type: str = "General Contract") -> dict:
    """Run complete LexGuard analysis on a document."""
    
    configure_gemini()
    
    # Stage 1: Segment into clauses
    clauses = await segment_clauses(document_text)
    
    # Stage 2: Analyze all clauses (with controlled concurrency)
    # Process up to 3 clauses in parallel to avoid rate limits
    results = []
    # Process ONE clause at a time to respect free-tier rate limits
    for clause in clauses:
        result = await analyze_clause(clause, doc_type)
        results.append(result)
        await asyncio.sleep(3)  # Breathing room between clauses
    
    # Stage 3: Compute overall scores
    risk_scores = []
    critical_issues = []
    warnings = []
    safe_clauses = []
    
    for r in results:
        verdict = r.get("verdict", {})
        score = verdict.get("risk_score", 5) if isinstance(verdict, dict) else 5
        risk_scores.append(score)
        
        if score >= 8:
            critical_issues.append(r)
        elif score >= 5:
            warnings.append(r)
        else:
            safe_clauses.append(r)
    
    avg_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    max_score = max(risk_scores) if risk_scores else 0
    
    # Overall risk grade
    if avg_score >= 8:
        grade = "F"
        recommendation = "DO NOT SIGN"
    elif avg_score >= 6.5:
        grade = "D"
        recommendation = "DO NOT SIGN WITHOUT MAJOR CHANGES"
    elif avg_score >= 5:
        grade = "C"
        recommendation = "NEGOTIATE BEFORE SIGNING"
    elif avg_score >= 3.5:
        grade = "B"
        recommendation = "GENERALLY SAFE — REVIEW WARNINGS"
    else:
        grade = "A"
        recommendation = "SAFE TO SIGN"
    
    # Stage 4: Contradiction Detection (whole-document analysis)
    contradictions = {}
    try:
        all_clauses_text = "\n\n".join([
            f"CLAUSE {c.get('clause_number', i+1)}: {c.get('title', 'Unknown')}\n{c.get('text', '')}"
            for i, c in enumerate(clauses)
        ])
        contradiction_prompt = CONTRADICTION_DETECTION_PROMPT.format(
            all_clauses_text=all_clauses_text[:8000]
        )
        contradictions = await call_gemini_json(contradiction_prompt, GEMINI_FLASH_MODEL)
    except Exception:
        contradictions = {"contradictions": [], "ambiguities": [], "missing_protections": [], "unusual_terms": []}
    
    # Stage 5: Generate executive summary
    top_risks = "\n".join([
        f"- {r['clause']['title']} (Score: {r['verdict'].get('risk_score', '?')}/10): "
        f"{r['verdict'].get('plain_english', 'N/A')[:200]}"
        for r in sorted(results, key=lambda x: x.get('verdict', {}).get('risk_score', 0) if isinstance(x.get('verdict'), dict) else 0, reverse=True)[:5]
    ])
    
    summary_prompt = OVERALL_SUMMARY_PROMPT.format(
        doc_type=doc_type,
        total_clauses=len(clauses),
        critical_count=len(critical_issues),
        warning_count=len(warnings),
        safe_count=len(safe_clauses),
        avg_score=f"{avg_score:.1f}",
        top_risks=top_risks,
    )
    executive_summary = await call_gemini(summary_prompt, GEMINI_FLASH_MODEL)
    
    return {
        "document_type": doc_type,
        "total_clauses": len(clauses),
        "overall_risk_score": round(avg_score, 1),
        "max_risk_score": max_score,
        "risk_grade": grade,
        "recommendation": recommendation,
        "executive_summary": executive_summary,
        "critical_issues": len(critical_issues),
        "warnings_count": len(warnings),
        "safe_count": len(safe_clauses),
        "clause_results": results,
        "contradictions": contradictions,
    }
