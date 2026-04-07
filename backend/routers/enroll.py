from fastapi import APIRouter
from backend.ml.one_class_svm import train_model

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
