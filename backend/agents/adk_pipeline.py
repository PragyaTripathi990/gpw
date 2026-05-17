"""
LexGuard Multi-Agent Pipeline using Google ADK (Agent Development Kit).
This is the Google-native approach — gives MAXIMUM bonus points at Google hackathon.

Google ADK Docs: https://google.github.io/adk-docs/

This module provides an alternative to pipeline.py using Google's official
Agent Development Kit for orchestrating the adversarial debate system.
"""
import json
from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompts import (
    CORPORATE_LAWYER_PROMPT,
    CONSUMER_ADVOCATE_PROMPT,
    JUDGE_PROMPT,
    SIMPLIFIER_PROMPT,
    CLAUSE_SEGMENTATION_PROMPT,
)


# ============================================================
# ADK Agent Definitions
# ============================================================

# Agent 1: Corporate Lawyer — Defends the contract
corporate_lawyer_agent = LlmAgent(
    name="CorporateLawyer",
    model="gemini-2.5-pro",
    instruction="""You are a senior corporate lawyer with 20 years of experience.
    Your role: DEFEND the contract clause provided in the user message.
    Argue why it is standard, legally justified, necessary for business.
    Be thorough but honest. If something is genuinely unusual, acknowledge it.
    Cite common legal practices and industry standards.""",
    description="Defends contract clauses from a corporate/business perspective",
    output_key="defense_argument",
)

# Agent 2: Consumer Rights Advocate — Attacks the contract  
consumer_advocate_agent = LlmAgent(
    name="ConsumerAdvocate",
    model="gemini-2.5-pro",
    instruction="""You are an aggressive consumer rights advocate and legal aid attorney.
    Your role: ATTACK the contract clause provided in the user message.
    Find ALL risks: exploitative terms, hidden fees, one-sided liability,
    data privacy violations, rights waivers, auto-renewal traps, arbitration tricks,
    vague language that could be interpreted against the user.
    Be AGGRESSIVE in protecting the consumer. Give REAL-WORLD EXAMPLES.""",
    description="Attacks contract clauses to find consumer risks",
    output_key="prosecution_argument",
)

# Parallel debate: both agents analyze simultaneously
adversarial_debate = ParallelAgent(
    name="AdversarialDebate",
    sub_agents=[corporate_lawyer_agent, consumer_advocate_agent],
    description="Runs corporate lawyer and consumer advocate in parallel",
)

# Agent 3: Judge — Weighs both arguments
judge_agent = LlmAgent(
    name="NeutralJudge",
    model="gemini-2.5-pro",
    instruction="""You are a neutral senior judge with expertise in contract law.
    You will see arguments from a Corporate Lawyer (defense) and Consumer Advocate (prosecution).
    
    Your job:
    1. RISK SCORE: 1-10 (10 = most dangerous)
    2. RISK TYPE: EXPLOITATIVE, AMBIGUOUS, HIDDEN_RISK, ONE_SIDED, PRIVACY_VIOLATION, FINANCIAL_TRAP, RIGHTS_WAIVER, SAFE
    3. VERDICT: Balanced 3-4 sentence assessment
    4. PLAIN ENGLISH: What this clause actually means in simple language
    5. SUGGESTED FIX: Fairer clause text if score >= 5
    6. REAL WORLD IMPACT: One concrete example
    
    Return as JSON with keys: risk_score, risk_types, verdict, plain_english, suggested_fix, real_world_impact""",
    description="Delivers final verdict weighing both sides",
    output_key="judge_verdict",
)

# Agent 4: Simplifier — Plain English translation
simplifier_agent = LlmAgent(
    name="PlainEnglishTranslator",
    model="gemini-2.5-flash",
    instruction="""Translate the legal clause into simple English a 15-year-old would understand.
    Use everyday analogies and examples. If it's dangerous, make it VERY CLEAR why.
    Format:
    WHAT IT SAYS: (1-2 simple sentences)
    WHAT IT MEANS FOR YOU: (practical impact)
    THINK OF IT LIKE: (relatable analogy)""",
    description="Translates legalese to plain English",
    output_key="simple_explanation",
)

# Full sequential pipeline: Debate → Judge → Simplify
lexguard_pipeline = SequentialAgent(
    name="LexGuardPipeline",
    sub_agents=[adversarial_debate, judge_agent, simplifier_agent],
    description="Complete LexGuard adversarial analysis pipeline",
)


# ============================================================
# Runner
# ============================================================
async def run_adk_analysis(clause_text: str, clause_title: str, category: str, doc_type: str) -> dict:
    """
    Run the full ADK pipeline for a single clause.
    
    This uses Google's official Agent Development Kit for orchestration,
    which is the recommended approach for Google Cloud projects.
    """
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=lexguard_pipeline,
        app_name="lexguard",
        session_service=session_service,
    )
    
    # Create session
    session = await session_service.create_session(
        app_name="lexguard",
        user_id="analysis",
    )
    
    # Prepare the input message
    user_message = f"""
    DOCUMENT TYPE: {doc_type}
    CLAUSE CATEGORY: {category}
    CLAUSE TITLE: {clause_title}
    
    CLAUSE TEXT:
    {clause_text}
    
    Please analyze this contract clause.
    """
    
    # Run the pipeline
    result = {}
    async for event in runner.run_async(
        user_id="analysis",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ),
    ):
        if event.agent_name == "CorporateLawyer" and event.content:
            result["defense"] = event.content.parts[0].text
        elif event.agent_name == "ConsumerAdvocate" and event.content:
            result["prosecution"] = event.content.parts[0].text
        elif event.agent_name == "NeutralJudge" and event.content:
            try:
                result["verdict"] = json.loads(event.content.parts[0].text)
            except json.JSONDecodeError:
                result["verdict"] = {"risk_score": 5, "verdict": event.content.parts[0].text}
        elif event.agent_name == "PlainEnglishTranslator" and event.content:
            result["simple_explanation"] = event.content.parts[0].text
    
    return result
