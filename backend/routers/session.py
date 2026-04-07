import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from backend.db.models import SessionLocal, Session, Score, SimSwapEvent
from backend.ml.one_class_svm import predict_score
from backend.ml.score_fusion import fuse_score
from backend.ml.anomaly_explainer import top_anomaly_strings
from backend.ml.feature_schema import FEATURE_NAMES

router = APIRouter(prefix="/session", tags=["Session Management"])

class SessionStart(BaseModel):
    user_id: int
    session_type: str # 'legitimate' | 'attacker' | 'scenario_N'

class FeatureSnapshot(BaseModel):
    session_id: str
    feature_snapshot: Dict[str, float]

class ScoreResponse(BaseModel):
    score: int
    risk_level: str
    action: str
    top_anomalies: List[str]

@router.post("/start")
def start_session(data: SessionStart):
    db = SessionLocal()
    try:
        session_id = str(uuid.uuid4())
        new_session = Session(
            id=session_id,
            user_id=data.user_id,
            session_type=data.session_type,
            feature_vector_json=[0.0] * 47 # Initially empty vector
        )
        db.add(new_session)
        db.commit()
        return {"session_id": session_id}
    finally:
        db.close()

@router.post("/feature", response_model=ScoreResponse)
def submit_feature(data: FeatureSnapshot):
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == data.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Merge snapshot into session vector
        current_vector = session.feature_vector_json or ([0.0] * 47)
        for k, v in data.feature_snapshot.items():
            if k in FEATURE_NAMES:
                 current_vector[FEATURE_NAMES.index(k)] = v
        
        session.feature_vector_json = current_vector
        db.commit()

        # Check SIM swap
        sim_swap = db.query(SimSwapEvent).filter(
            SimSwapEvent.user_id == session.user_id, 
            SimSwapEvent.is_active == True
        ).first()
        sim_swap_active = sim_swap is not None

        # Predict behavioral score
        behavior_score = predict_score(session.user_id, current_vector)
        
        # Fuse with SIM swap
        fusion = fuse_score(behavior_score, sim_swap_active)
        
        # Get anomalies using centralized logic
        anomalies = top_anomaly_strings(session.user_id, current_vector, sim_swap_active=sim_swap_active)
        
        # Save score
        new_score = Score(
            session_id=session.id,
            confidence_score=fusion["final_score"],
            risk_level=fusion["risk_level"],
            top_anomalies_json=anomalies
        )
        db.add(new_score)
        db.commit()
        
        return {
            "score": fusion["final_score"],
            "risk_level": fusion["risk_level"],
            "action": fusion["action"],
            "top_anomalies": anomalies
        }
    finally:
        db.close()

# Note: standalone fleet check is in /fleet router, but we keep the spec here if needed
@router.post("/fleet-check")
def fleet_check_proxy(device_fingerprint: str, user_id: int):
    # This will be handled by the fleet router standalone endpoint /fleet/check
    # but provided here for backward compatibility with existing main.py logic
    from backend.ml.fleet_anomaly import check_fleet_anomaly, register_device
    register_device(user_id, device_fingerprint)
    return check_fleet_anomaly(device_fingerprint, user_id)
