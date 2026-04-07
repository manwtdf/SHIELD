from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import uuid
import datetime

from backend.db.models import SessionLocal, Session, User, init_db, Score, SimSwapEvent
from backend.ml.one_class_svm import predict_score, train_model
from backend.ml.score_fusion import fuse_score
from backend.utils.scoring import get_top_anomalies

app = FastAPI(title="SHIELD API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For demo purposes
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
def startup():
    init_db()

# Models
class SessionStart(BaseModel):
    user_id: int
    session_type: str # 'legitimate' | 'attacker'

class FeatureSnapshot(BaseModel):
    session_id: str
    feature_snapshot: Dict[str, float]

class ScoreResponse(BaseModel):
    score: int
    risk_level: str
    action: str
    top_anomalies: List[str]

# Routes
@app.post("/session/start")
def start_session(data: SessionStart):
    db = SessionLocal()
    try:
        session_id = str(uuid.uuid4())
        new_session = Session(
            id=session_id,
            user_id=data.user_id,
            session_type=data.session_type,
            feature_vector_json=[0.0] * 47 # Initial empty vector
        )
        db.add(new_session)
        db.commit()
        return {"session_id": session_id}
    finally:
        db.close()

@app.post("/session/feature", response_model=ScoreResponse)
def submit_feature(data: FeatureSnapshot):
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == data.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # In a real app, we'd merge the snapshot. 
        # For the demo, we assume the snapshot IS the full vector (for attacker) 
        # or a partial update. 
        # Let's just use the provided values to update the 47-feature vector.
        # For simplicity, if 'feature_vector' is in the snapshot, use it.
        current_vector = list(data.feature_snapshot.values())
        if len(current_vector) != 47:
             # handle partial updates or just mock it for demo
             pass

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
        
        # Get anomalies
        anomalies = get_top_anomalies(session.user_id, current_vector, sim_swap_active)
        
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

@app.get("/score/{session_id}")
def get_score(session_id: str):
    db = SessionLocal()
    try:
        score = db.query(Score).filter(Score.session_id == session_id).order_by(Score.computed_at.desc()).first()
        if not score:
            return {"score": 91, "risk_level": "LOW", "action": "ALLOW", "top_anomalies": []}
        return {
            "score": score.confidence_score,
            "risk_level": score.risk_level,
            "top_anomalies": score.top_anomalies_json
        }
    finally:
        db.close()

@app.post("/enroll/{user_id}")
def enroll_user(user_id: int):
    return train_model(user_id)

@app.post("/sim-swap/trigger")
def trigger_sim_swap(user_id: int):
    db = SessionLocal()
    try:
        event = SimSwapEvent(user_id=user_id, is_active=True)
        db.add(event)
        db.commit()
        return {"event_id": event.id, "triggered_at": event.triggered_at}
    finally:
        db.close()

@app.post("/sim-swap/clear")
def clear_sim_swap(user_id: int):
    db = SessionLocal()
    try:
        db.query(SimSwapEvent).filter(SimSwapEvent.user_id == user_id).update({"is_active": False})
        db.commit()
        return {"cleared": True}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
