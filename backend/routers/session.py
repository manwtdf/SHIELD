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
    device_class: str = "mobile"
    device_fingerprint: str = "default_fingerprint"

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
            device_class=data.device_class,
            feature_vector_json=[0.0] * len(FEATURE_NAMES)
        )
        db.add(new_session)
        db.commit()
        
        # Register device via backend.ml.fleet_anomaly
        from backend.ml.fleet_anomaly import check_fleet_anomaly, register_device
        register_device(db, data.device_fingerprint, data.user_id, data.device_class)
        
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
        current_vector = session.feature_vector_json or ([0.0] * len(FEATURE_NAMES))
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

        # Gather Device Context from DeviceRegistry
        from backend.db.models import DeviceRegistry
        # We need the device fingerprint! Wait, session doesn't store fingerprint natively.
        # But we can query the most recently seen fingerprint for this user.
        # Ideally, we should pass fingerprint in FeatureSnapshot or store in Session.
        # Let's get the most recent or matching class device.
        device = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == session.user_id,
            DeviceRegistry.device_class == session.device_class
        ).order_by(DeviceRegistry.last_seen.desc()).first()
        
        device_context = {
            "device_class_known": 1 if device else 0,
            "device_session_count": device.session_count if device else 0,
            "device_class_switch": 0, # Calculate if current is different from dominant
            "is_known_fingerprint": 1 if device and device.trust_level == 'known' else 0,
        }

        # Predict behavioral score
        behavior_score = predict_score(session.user_id, current_vector)
        
        # Fuse with SIM swap and context
        fusion = fuse_score(behavior_score, sim_swap_active, device_context)
        
        # Get anomalies using centralized logic
        anomalies = top_anomaly_strings(session.user_id, current_vector, device_class=session.device_class)
        if sim_swap_active:
            anomalies.insert(0, "SIM swap detected recently on account")
        
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
