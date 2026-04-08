"""
SHIELD Score Router
───────────────────
GET /score/{session_id} — Get latest score for a session
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import Score

router = APIRouter()


class ScoreResponse(BaseModel):
    score: int
    risk_level: str
    action: str
    top_anomalies: list[str]
    snapshot_index: int
    updated_at: str


@router.get("/{session_id}", response_model=ScoreResponse)
def get_score(session_id: str, db: DBSession = Depends(get_db)):
    latest = (
        db.query(Score)
        .filter_by(session_id=session_id)
        .order_by(Score.computed_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(404, "No score found for this session")

    return ScoreResponse(
        score=latest.confidence_score,
        risk_level=latest.risk_level,
        action=latest.action,
        top_anomalies=json.loads(latest.top_anomalies or "[]"),
        snapshot_index=latest.snapshot_index,
        updated_at=latest.computed_at.isoformat(),
    )
