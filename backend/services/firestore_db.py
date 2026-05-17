"""
Firestore database service for storing analysis results.
"""
import uuid
from datetime import datetime
from google.cloud import firestore


def get_db():
    """Get Firestore client."""
    return firestore.Client()


def save_analysis(analysis_result: dict, user_id: str = "anonymous") -> str:
    """Save analysis result to Firestore. Returns document ID."""
    try:
        db = get_db()
        doc_id = uuid.uuid4().hex
        
        # Prepare data (Firestore-safe)
        data = {
            "id": doc_id,
            "user_id": user_id,
            "document_type": analysis_result.get("document_type", ""),
            "total_clauses": analysis_result.get("total_clauses", 0),
            "overall_risk_score": analysis_result.get("overall_risk_score", 0),
            "risk_grade": analysis_result.get("risk_grade", ""),
            "recommendation": analysis_result.get("recommendation", ""),
            "executive_summary": analysis_result.get("executive_summary", ""),
            "critical_issues": analysis_result.get("critical_issues", 0),
            "warnings_count": analysis_result.get("warnings_count", 0),
            "safe_count": analysis_result.get("safe_count", 0),
            "created_at": datetime.utcnow(),
        }
        
        db.collection("analyses").document(doc_id).set(data)
        
        # Save clause results separately (sub-collection)
        for i, clause_result in enumerate(analysis_result.get("clause_results", [])):
            clause_data = {
                "clause": clause_result.get("clause", {}),
                "defense": clause_result.get("defense", ""),
                "prosecution": clause_result.get("prosecution", ""),
                "verdict": clause_result.get("verdict", {}),
                "simple_explanation": clause_result.get("simple_explanation", ""),
            }
            db.collection("analyses").document(doc_id).collection("clauses").document(f"clause_{i}").set(clause_data)
        
        return doc_id
    except Exception as e:
        print(f"Firestore save failed: {e}")
        return ""


def get_analysis(doc_id: str) -> dict:
    """Retrieve analysis from Firestore."""
    try:
        db = get_db()
        doc = db.collection("analyses").document(doc_id).get()
        
        if not doc.exists:
            return {}
        
        data = doc.to_dict()
        
        # Get clause results
        clauses = db.collection("analyses").document(doc_id).collection("clauses").stream()
        data["clause_results"] = [clause.to_dict() for clause in clauses]
        
        return data
    except Exception as e:
        print(f"Firestore read failed: {e}")
        return {}


def get_user_analyses(user_id: str, limit: int = 20) -> list[dict]:
    """Get all analyses for a user."""
    try:
        db = get_db()
        docs = (
            db.collection("analyses")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Firestore query failed: {e}")
        return []
