from fastapi import APIRouter
from backend.ml.one_class_svm import train_model
from backend.db.models import SessionLocal, Session
import os

router = APIRouter(prefix="/enroll", tags=["Account Enrollment"])

@router.post("/{user_id}")
def enroll_user(user_id: int):
    """
    Triggers the training process for the behavioral pattern of a specific user.
    Uses existing 'legitimate' sessions in the database for that user.
    """
    res = train_model(user_id)
    return {
        "enrolled": res.get("enrolled", False),
        "sessions_used": res.get("sessions_used", 0),
        "model_saved": res.get("enrolled", False),
        "baseline_score": 91.0 # Standard enrollment baseline
    }

@router.post("/reset/{user_id}")
def reset_user(user_id: int):
    """
    Clears all sessions and models for the given user to start fresh.
    """
    db = SessionLocal()
    try:
        deleted_count = db.query(Session).filter(Session.user_id == user_id).delete()
        db.commit()
        # Delete old models
        for suffix in ['all', 'mobile', 'desktop']:
            m = f"backend/ml/models/model_{user_id}_{suffix}.pkl"
            s = f"backend/ml/models/scaler_{user_id}_{suffix}.pkl"
            if os.path.exists(m): os.remove(m)
            if os.path.exists(s): os.remove(s)
        return {"reset": True, "cleared_sessions": deleted_count, "user_id": user_id}
    except Exception as e:
        db.rollback()
        return {"reset": False, "error": str(e)}
    finally:
        db.close()
