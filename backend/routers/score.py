from fastapi import APIRouter, HTTPException
from backend.db.models import SessionLocal, Score

router = APIRouter(prefix="/score", tags=["Scoring"])

@router.get("/{session_id}")
def get_score(session_id: str):
    db = SessionLocal()
    try:
        # Get the latest score snapshot for this session
        score = db.query(Score).filter(Score.session_id == session_id).order_by(Score.computed_at.desc()).first()
        if not score:
            # Baseline or empty session case
            return {
                "score": 91, 
                "risk_level": "LOW", 
                "action": "ALLOW", 
                "top_anomalies": [],
                "updated_at": "baseline"
            }
        return {
            "score": score.confidence_score,
            "risk_level": score.risk_level,
            "action": "BLOCK_AND_FREEZE" if score.risk_level == "CRITICAL" else "ALLOW",
            "top_anomalies": score.top_anomalies_json,
            "updated_at": score.computed_at.isoformat()
        }
    finally:
        db.close()
