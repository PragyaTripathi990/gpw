"""
Google Cloud Natural Language API integration.
Adds extra entity/sentiment analysis layer on top of Gemini agents.
"""
from google.cloud import language_v2


def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of a clause using Google Cloud NL API."""
    try:
        client = language_v2.LanguageServiceClient()
        
        document = language_v2.Document(
            content=text,
            type_=language_v2.Document.Type.PLAIN_TEXT,
        )
        
        response = client.analyze_sentiment(
            request={"document": document, "encoding_type": language_v2.EncodingType.UTF8}
        )
        
        sentiment = response.document_sentiment
        
        return {
            "score": sentiment.score,       # -1.0 (negative) to 1.0 (positive)
            "magnitude": sentiment.magnitude, # 0.0 to inf (strength of sentiment)
            "interpretation": _interpret_sentiment(sentiment.score, sentiment.magnitude),
        }
    except Exception as e:
        print(f"Sentiment analysis failed: {e}")
        return {"score": 0, "magnitude": 0, "interpretation": "unavailable"}


def analyze_entities(text: str) -> list[dict]:
    """Extract entities (organizations, people, etc) from text."""
    try:
        client = language_v2.LanguageServiceClient()
        
        document = language_v2.Document(
            content=text,
            type_=language_v2.Document.Type.PLAIN_TEXT,
        )
        
        response = client.analyze_entities(
            request={"document": document, "encoding_type": language_v2.EncodingType.UTF8}
        )
        
        entities = []
        for entity in response.entities:
            entities.append({
                "name": entity.name,
                "type": language_v2.Entity.Type(entity.type_).name,
                "salience": entity.salience,
            })
        
        return sorted(entities, key=lambda x: x["salience"], reverse=True)[:10]
    except Exception as e:
        print(f"Entity analysis failed: {e}")
        return []


def classify_text(text: str) -> list[dict]:
    """Classify text into categories."""
    try:
        client = language_v2.LanguageServiceClient()
        
        document = language_v2.Document(
            content=text,
            type_=language_v2.Document.Type.PLAIN_TEXT,
        )
        
        response = client.classify_text(request={"document": document})
        
        categories = []
        for category in response.categories:
            categories.append({
                "name": category.name,
                "confidence": category.confidence,
            })
        
        return categories
    except Exception as e:
        print(f"Text classification failed: {e}")
        return []


def _interpret_sentiment(score: float, magnitude: float) -> str:
    """Human-readable sentiment interpretation."""
    if magnitude < 0.2:
        return "neutral"
    if score > 0.3:
        return "positive/favorable"
    if score < -0.3:
        return "negative/restrictive"
    return "mixed"
