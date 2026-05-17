"""
Legal Knowledge Base + RAG (Retrieval-Augmented Generation)
===========================================================

This module provides a curated knowledge base of:
- Standard/fair clause benchmarks (what a FAIR clause looks like)
- Known exploitative patterns (red flags)
- Legal rights by jurisdiction
- Industry-standard terms

Used for:
1. BENCHMARK COMPARISON — Compare user's clause vs fair standard
2. RAG — Augment agent analysis with legal knowledge
3. PATTERN MATCHING — Detect known exploitative patterns

Uses: Google Vertex AI Embeddings + in-memory vector store
"""
from backend.services.embeddings import get_embedding, get_embeddings_batch, cosine_similarity


# ============================================================
# KNOWLEDGE BASE: Fair/Standard Clause Benchmarks
# ============================================================
FAIR_CLAUSE_BENCHMARKS = {
    "LIABILITY": {
        "fair_example": "Each party's total liability under this agreement shall not exceed the total fees paid or payable during the 12 months preceding the claim. Neither party excludes liability for death, personal injury, fraud, or gross negligence.",
        "red_flags": [
            "Liability limited to fees paid in last 1-3 months only",
            "Complete exclusion of all liability including negligence",
            "One-sided liability — only customer bears risk",
            "No liability for data breaches or data loss",
        ],
        "consumer_rights": "Under most jurisdictions, companies cannot exclude liability for gross negligence, fraud, or personal injury. Liability caps below 12 months of fees are generally considered unfair.",
    },
    "TERMINATION": {
        "fair_example": "Either party may terminate this agreement with 30 days written notice. Upon termination, the provider shall make all customer data available for export for 30 days. Refunds will be provided for unused prepaid services on a pro-rata basis.",
        "red_flags": [
            "Provider can terminate without notice but customer cannot",
            "No data export period after termination",
            "No refund of prepaid fees upon termination",
            "Customer must pay through end of term regardless of who terminates",
        ],
        "consumer_rights": "Consumers generally have the right to terminate with reasonable notice. EU Consumer Rights Directive provides 14-day cooling-off period. Data portability is protected under GDPR.",
    },
    "DATA_PRIVACY": {
        "fair_example": "Provider shall process Customer Data only for the purpose of delivering the Service. Customer Data will not be shared with third parties except as necessary to provide the Service. Customer Data will be deleted within 30 days of termination upon request.",
        "red_flags": [
            "Perpetual license to use customer data for any purpose",
            "Right to share data with undefined 'partners' or 'affiliates'",
            "No obligation to delete data after termination",
            "Right to use data for advertising or profiling",
            "Anonymized data can be used without restriction",
        ],
        "consumer_rights": "GDPR, CCPA, and most privacy laws require clear consent for data processing, right to deletion, data portability, and purpose limitation.",
    },
    "AUTO_RENEWAL": {
        "fair_example": "This agreement renews automatically for successive terms equal to the initial term. Either party may cancel auto-renewal with 30 days notice before the renewal date. Renewal reminders will be sent 45 and 15 days before renewal.",
        "red_flags": [
            "90+ day cancellation notice required",
            "No reminder before auto-renewal",
            "Price can increase at renewal without cap",
            "Renewal term longer than original term",
        ],
        "consumer_rights": "Many US states require auto-renewal disclosures. California ARL requires clear disclosure and easy cancellation. FTC requires transparency in auto-renewal terms.",
    },
    "ARBITRATION": {
        "fair_example": "Disputes shall first be attempted to be resolved through good-faith negotiation. If unresolved after 30 days, either party may pursue mediation or binding arbitration. Each party bears its own costs. Class action rights are preserved.",
        "red_flags": [
            "Mandatory binding arbitration with no court option",
            "Class action waiver",
            "Customer pays all arbitration costs",
            "Arbitration in provider's home jurisdiction only",
            "Confidential arbitration preventing public accountability",
        ],
        "consumer_rights": "Class action waivers have been challenged in courts. EU law generally prevents mandatory arbitration for consumers. Some US states limit enforcement of arbitration clauses.",
    },
    "IP_RIGHTS": {
        "fair_example": "Customer retains all intellectual property rights in Customer Data and content. Provider retains rights in the Service. Feedback may be used by Provider to improve the Service but Provider does not claim ownership of feedback.",
        "red_flags": [
            "Provider claims ownership of customer content/data",
            "Perpetual irrevocable license to customer IP",
            "Feedback becomes exclusive property of provider",
            "Waiver of moral rights",
            "Broad license to create derivative works from customer data",
        ],
        "consumer_rights": "IP ownership should remain with the creator. Broad licensing of customer content for 'any purpose' is generally considered overreaching.",
    },
    "INDEMNIFICATION": {
        "fair_example": "Each party shall indemnify the other against third-party claims arising from their breach of this agreement or negligent acts. Indemnification obligations are mutual and subject to the liability cap.",
        "red_flags": [
            "One-sided indemnification (only customer indemnifies provider)",
            "Indemnification not subject to liability cap",
            "Customer indemnifies for provider's own negligence",
            "Indemnification covers unlimited attorneys' fees",
        ],
        "consumer_rights": "Mutual indemnification is the industry standard. One-sided indemnification clauses are often considered unconscionable.",
    },
    "PAYMENT": {
        "fair_example": "Fees are as specified in the Order Form. Price increases will not exceed 5% per year and require 60 days notice. Late payments incur interest at the lower of 1% per month or the legal maximum. Disputed charges may be withheld pending resolution.",
        "red_flags": [
            "All fees non-refundable regardless of circumstances",
            "Unlimited price increases with short notice",
            "Excessive late payment penalties (1.5%+ per month)",
            "No right to dispute charges",
            "Hidden fees not in main pricing",
        ],
        "consumer_rights": "Many jurisdictions cap late fees. Unfair price increase terms may be challenged under consumer protection laws.",
    },
    "CONFIDENTIALITY": {
        "fair_example": "Both parties agree to keep confidential information private for the term plus 2 years. Standard exceptions apply (public knowledge, independent development, legal requirements). Neither party is restricted from publicly discussing the general nature of the relationship.",
        "red_flags": [
            "Cannot publicly review or benchmark the service",
            "Cannot disclose pricing to anyone",
            "Perpetual confidentiality with no exceptions",
            "Cannot discuss terms even with own legal counsel",
        ],
        "consumer_rights": "Clauses that prevent honest reviews or benchmarking are increasingly challenged. Right to consult legal counsel about contract terms is fundamental.",
    },
    "NON_COMPETE": {
        "fair_example": "During the term of employment and for 6 months after, Employee agrees not to directly compete with Company in the same specific product category within a 50-mile radius.",
        "red_flags": [
            "Non-compete lasting more than 1 year",
            "Overly broad geographic scope (nationwide/global)",
            "Vague definition of competing activities",
            "Non-compete applies even if employer terminates without cause",
            "No compensation during non-compete period",
        ],
        "consumer_rights": "FTC has proposed banning non-competes. California, Oklahoma, and North Dakota ban most non-competes. Many states require reasonable scope, duration, and geography.",
    },
}


# ============================================================
# KNOWN EXPLOITATIVE PATTERNS (for pattern detection)
# ============================================================
EXPLOITATIVE_PATTERNS = [
    {
        "pattern": "perpetual, irrevocable, royalty-free license",
        "risk": "CRITICAL",
        "explanation": "Grants permanent rights to your content/data that can never be taken back, even after you leave the platform.",
    },
    {
        "pattern": "waive any right to participate in a class action",
        "risk": "HIGH",
        "explanation": "Prevents you from joining class action lawsuits, forcing individual arbitration which is often impractical for small claims.",
    },
    {
        "pattern": "modify this agreement at any time",
        "risk": "HIGH",
        "explanation": "Allows the company to change the rules after you've agreed, potentially adding unfavorable terms.",
    },
    {
        "pattern": "non-refundable regardless",
        "risk": "HIGH",
        "explanation": "You cannot get money back even if the service is terrible or they breach the agreement.",
    },
    {
        "pattern": "terminate immediately without notice for any reason",
        "risk": "HIGH",
        "explanation": "They can cut off your service at any moment without warning or explanation.",
    },
    {
        "pattern": "no obligation to retain.*data after termination",
        "risk": "HIGH",
        "explanation": "Your data may be permanently deleted the moment your account is closed with no recovery option.",
    },
    {
        "pattern": "exclusive property of provider",
        "risk": "MEDIUM",
        "explanation": "Ideas or feedback you provide become their property — you lose all rights to your own suggestions.",
    },
    {
        "pattern": "increase fees at any time",
        "risk": "MEDIUM",
        "explanation": "Prices can go up without limit or your meaningful consent.",
    },
    {
        "pattern": "consent to the exclusive jurisdiction",
        "risk": "MEDIUM",
        "explanation": "Forces legal disputes to be handled in their chosen location, which may be inconvenient or expensive for you.",
    },
    {
        "pattern": "deemed accepted",
        "risk": "MEDIUM",
        "explanation": "Your silence is treated as agreement — you must actively object or you're locked in.",
    },
]


# ============================================================
# RAG: Retrieve relevant knowledge for a clause
# ============================================================
_benchmark_embeddings_cache = None


def _get_benchmark_embeddings() -> list[dict]:
    """Build and cache embeddings for all benchmarks."""
    global _benchmark_embeddings_cache
    
    if _benchmark_embeddings_cache is not None:
        return _benchmark_embeddings_cache
    
    items = []
    texts = []
    
    for category, data in FAIR_CLAUSE_BENCHMARKS.items():
        text = f"Category: {category}. Fair clause: {data['fair_example']}. Red flags: {'. '.join(data['red_flags'])}. Rights: {data['consumer_rights']}"
        items.append({
            "text": text,
            "metadata": {
                "category": category,
                "fair_example": data["fair_example"],
                "red_flags": data["red_flags"],
                "consumer_rights": data["consumer_rights"],
            }
        })
        texts.append(text)
    
    for pattern in EXPLOITATIVE_PATTERNS:
        text = f"Exploitative pattern: {pattern['pattern']}. Risk: {pattern['risk']}. Explanation: {pattern['explanation']}"
        items.append({
            "text": text,
            "metadata": pattern,
        })
        texts.append(text)
    
    try:
        embeddings = get_embeddings_batch(texts)
        for i, emb in enumerate(embeddings):
            items[i]["embedding"] = emb
        _benchmark_embeddings_cache = items
    except Exception as e:
        print(f"Failed to build benchmark embeddings: {e}")
        _benchmark_embeddings_cache = []
    
    return _benchmark_embeddings_cache


def retrieve_relevant_knowledge(clause_text: str, category: str, top_k: int = 3) -> dict:
    """
    RAG: Retrieve the most relevant legal knowledge for a given clause.
    Returns benchmark comparison, known patterns, and consumer rights.
    """
    result = {
        "benchmark": None,
        "matched_patterns": [],
        "consumer_rights": "",
        "rag_context": "",
    }
    
    # Direct category match (fast path)
    if category in FAIR_CLAUSE_BENCHMARKS:
        benchmark = FAIR_CLAUSE_BENCHMARKS[category]
        result["benchmark"] = {
            "fair_example": benchmark["fair_example"],
            "red_flags": benchmark["red_flags"],
        }
        result["consumer_rights"] = benchmark["consumer_rights"]
    
    # Pattern matching
    clause_lower = clause_text.lower()
    for pattern in EXPLOITATIVE_PATTERNS:
        # Simple substring check + semantic similarity will catch more
        if pattern["pattern"].lower() in clause_lower:
            result["matched_patterns"].append(pattern)
    
    # Semantic similarity RAG (using embeddings)
    try:
        benchmarks = _get_benchmark_embeddings()
        if benchmarks:
            query_emb = get_embedding(clause_text[:500])
            
            similarities = []
            for item in benchmarks:
                if "embedding" in item:
                    sim = cosine_similarity(query_emb, item["embedding"])
                    similarities.append({"similarity": sim, **item})
            
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            top_matches = similarities[:top_k]
            
            # Build RAG context for the agents
            rag_parts = []
            for match in top_matches:
                if match["similarity"] > 0.5:
                    rag_parts.append(f"[Relevance: {match['similarity']:.2f}] {match['text']}")
            
            result["rag_context"] = "\n".join(rag_parts)
    except Exception as e:
        print(f"RAG retrieval failed: {e}")
    
    return result
