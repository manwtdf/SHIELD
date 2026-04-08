"""
SHIELD Enrollment Router
─────────────────────────
POST /enroll/{user_id}       — Train user behavioral model
POST /enroll/reset/{user_id} — Reset user data (sandbox mode)
"""

import json
import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import Session as SessionModel, User, Score, DeviceRegistry
from backend.ml.one_class_svm import train, model_exists

logger = logging.getLogger("shield.enroll")

router = APIRouter()

REQUIRED_SESSIONS = int(os.getenv("ENROLLMENT_SESSIONS_REQUIRED", "10"))


class EnrollResponse(BaseModel):
    enrolled: bool
    sessions_used: int
    model_saved: bool
    baseline_score: float
    baseline_std: float


@router.post("/{user_id}", response_model=EnrollResponse)
def enroll(user_id: int, db: DBSession = Depends(get_db)):
    """
    Train One-Class SVM on user's legitimate sessions.
    Requires at least ENROLLMENT_SESSIONS_REQUIRED legitimate sessions in DB.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Get all legitimate sessions with feature vectors
    legitimate_sessions = (
        db.query(SessionModel)
        .filter_by(user_id=user_id, session_type="legitimate")
        .filter(SessionModel.feature_vector.isnot(None))
        .all()
    )

    if len(legitimate_sessions) < REQUIRED_SESSIONS:
        raise HTTPException(
            400,
            f"Need {REQUIRED_SESSIONS} sessions, have {len(legitimate_sessions)}. "
            "Run seed_runner.py or capture more sessions first."
        )

    # Extract feature vectors
    feature_vectors = [
        json.loads(s.feature_vector) for s in legitimate_sessions
    ]

    # Train model (decoupled — pure function)
    meta = train(user_id=user_id, feature_vectors=feature_vectors)

    # Update user enrollment timestamp
    user.enrolled_at = datetime.utcnow()
    user.sessions_count = len(legitimate_sessions)
    db.commit()

    logger.info(
        f"User {user_id} enrolled: {len(legitimate_sessions)} sessions, "
        f"baseline={meta['baseline_mean']:.1f}±{meta['baseline_std']:.1f}"
    )

    return EnrollResponse(
        enrolled=True,
        sessions_used=len(legitimate_sessions),
        model_saved=True,
        baseline_score=meta["baseline_mean"],
        baseline_std=meta["baseline_std"],
    )


@router.post("/reset/{user_id}")
def reset_user(user_id: int, db: DBSession = Depends(get_db)):
    """
    Clear all sessions, scores, and models for a user. Used by sandbox mode.
    """
    try:
        # Delete scores for this user's sessions
        session_ids = [
            s.id for s in db.query(SessionModel).filter_by(user_id=user_id).all()
        ]
        if session_ids:
            db.query(Score).filter(Score.session_id.in_(session_ids)).delete(synchronize_session=False)

        # Delete sessions
        deleted_sessions = db.query(SessionModel).filter_by(user_id=user_id).delete()

        # Delete device registry entries
        db.query(DeviceRegistry).filter_by(user_id=user_id).delete()

        # Reset user enrollment
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            user.enrolled_at = None
            user.sessions_count = 0

        db.commit()

        # Delete model files
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "models")
        for suffix in ["cov", "scaler", "meta"]:
            ext = "json" if suffix == "meta" else "pkl"
            path = os.path.join(model_dir, f"{suffix}_{user_id}.{ext}")
            if os.path.exists(path):
                os.remove(path)

        logger.info(f"User {user_id} reset: {deleted_sessions} sessions cleared")
        return {"reset": True, "cleared_sessions": deleted_sessions, "user_id": user_id}

    except Exception as e:
        db.rollback()
        logger.error(f"Reset failed for user {user_id}: {e}")
        raise HTTPException(500, f"Reset failed: {str(e)}")
