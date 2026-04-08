"""
SHIELD Features Router
──────────────────────
GET /features/inspect/{session_id} — Full 55-feature z-score inspection
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import Session as SessionModel
from backend.ml.one_class_svm import get_baseline_stats
from backend.ml.anomaly_explainer import get_z_scores
from backend.ml.feature_schema import FEATURE_DIM

router = APIRouter()


@router.get("/inspect/{session_id}")
def inspect_features(session_id: str, db: DBSession = Depends(get_db)):
    """
    Return z-score info for all 55 features in a session.
    Powers the Feature Inspector table in Frontend 3.
    """
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session or not session.feature_vector:
        raise HTTPException(404, "Session not found or no feature vector")

    feature_vector = json.loads(session.feature_vector)

    try:
        meta = get_baseline_stats(session.user_id)
    except FileNotFoundError:
        raise HTTPException(400, "User not enrolled — no baseline stats available")

    features = get_z_scores(
        feature_vector=feature_vector,
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
    )

    flagged_count = sum(1 for f in features if f["flagged"])

    return {
        "session_id": session_id,
        "total_features": FEATURE_DIM,
        "flagged_count": flagged_count,
        "features": features,
    }
