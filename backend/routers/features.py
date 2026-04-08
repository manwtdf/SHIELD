import numpy as np
from fastapi import APIRouter, HTTPException
from backend.db.models import SessionLocal, Session
from backend.ml.feature_schema import FEATURE_NAMES

router = APIRouter(prefix="/features", tags=["Feature Inspection"])

@router.get("/inspect/{session_id}")
def inspect_features(session_id: str):
    """
    Returns full feature vector vs user baseline.
    Powers the Feature Inspector table in the Simulator dashboard.
    """
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        vector = session.feature_vector_json or ([0.0] * len(FEATURE_NAMES))
        
        # Load user baseline for statistical comparison
        # (10 sessions required)
        legit_sessions = db.query(Session).filter(
            Session.user_id == session.user_id,
            Session.session_type == 'legitimate'
        ).all()
        
        if not legit_sessions:
            return {"features": []}
            
        X_baseline = np.array([s.feature_vector_json for s in legit_sessions if s.feature_vector_json])
        if len(X_baseline) == 0:
            return {"features": []}
            
        baseline_mean = np.mean(X_baseline, axis=0)
        baseline_std = np.std(X_baseline, axis=0) + 1e-6 # epsilon for stability
        
        results = []
        for i, name in enumerate(FEATURE_NAMES):
            val = vector[i]
            base = baseline_mean[i]
            z = (val - base) / baseline_std[i]
            
            results.append({
                "name": name,
                "value": round(float(val), 3),
                "baseline": round(float(base), 3),
                "z_score": round(float(z), 2),
                "flagged": bool(abs(z) > 2.5)
            })
            
        return {"features": results}
    finally:
        db.close()
