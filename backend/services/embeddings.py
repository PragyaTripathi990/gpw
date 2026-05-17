"""
Vertex AI Embeddings Service
Uses Google's text-embedding model for semantic similarity analysis.
Enables: RAG, benchmark comparison, contradiction detection.
"""
import google.generativeai as genai
from backend.config import GEMINI_API_KEY


def configure() -> None:
    """Configure the Google Generative AI SDK with the API key."""
    genai.configure(api_key=GEMINI_API_KEY)


EMBEDDING_MODEL = "models/gemini-embedding-exp-03-07"


def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a text using Google's embedding model."""
    configure()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
    )
    return result['embedding']


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts in batch."""
    configure()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=texts,
    )
    return result['embedding']


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = sum(a * a for a in vec_a) ** 0.5
    magnitude_b = sum(b * b for b in vec_b) ** 0.5
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def find_most_similar(query_embedding: list[float], corpus_embeddings: list[dict]) -> list[dict]:
    """
    Find most similar items from a corpus.
    corpus_embeddings: [{"text": "...", "embedding": [...], "metadata": {...}}, ...]
    """
    results = []
    for item in corpus_embeddings:
        similarity = cosine_similarity(query_embedding, item["embedding"])
        results.append({
            "text": item["text"],
            "metadata": item.get("metadata", {}),
            "similarity": similarity,
        })
    
    return sorted(results, key=lambda x: x["similarity"], reverse=True)
