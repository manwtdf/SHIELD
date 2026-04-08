"""
SHIELD Session Router
─────────────────────
POST /session/start       — Start a new session
POST /session/feature     — Submit feature snapshot (CORE SCORING PIPELINE)
POST /session/fleet-check — Cross-account device check
"""

import json
import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import Session as SessionModel, Score, SimSwapEvent, User, DeviceRegistry
from backend.ml.one_class_svm import predict, get_baseline_stats, model_exists
from backend.ml.score_fusion import fuse_score
from backend.ml.anomaly_explainer import get_top_anomalies
from backend.ml.feature_schema import FEATURE_NAMES, FEATURE_DIM, dict_to_vector
from backend.utils.scoring import get_sim_swap_minutes

logger = logging.getLogger("shield.session")

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    user_id: int
    session_type: str = "legitimate"  # "legitimate" | "scenario_1" ... "scenario_6" | "auto"
    device_class: str = "mobile"
    device_fingerprint: str = "default_fingerprint"


class StartResponse(BaseModel):
    session_id: str
    started_at: str


class FeatureRequest(BaseModel):
    session_id: str
    feature_snapshot: dict  # partial or full feature dict
    snapshot_index: int = 1  # 1–5


class FeatureResponse(BaseModel):
    score: int
    risk_level: str
    action: str
    top_anomalies: list[str]
    snapshot_index: int


class FleetCheckRequest(BaseModel):
    device_fingerprint: str
    user_id: int


class FleetCheckResponse(BaseModel):
    fleet_anomaly: bool
    accounts_seen: int
    action: str


# ─────────────────────────────────────────────────────────────
# POST /session/start
# ─────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
def start_session(req: StartRequest, db: DBSession = Depends(get_db)):
    # Verify user exists
    if not db.query(User).filter_by(id=req.user_id).first():
        raise HTTPException(404, "User not found")

    session = SessionModel(
        user_id=req.user_id,
        session_type=req.session_type,
        device_class=req.device_class,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Register device in registry
    from backend.ml.fleet_anomaly import _register_device
    _register_device(db, req.device_fingerprint, req.user_id, req.device_class)

    logger.info(f"Session started: {session.id} for user {req.user_id} ({req.session_type})")

    return StartResponse(
        session_id=session.id,
        started_at=session.started_at.isoformat(),
    )


# ─────────────────────────────────────────────────────────────
# POST /session/feature — CORE REAL-TIME SCORING PIPELINE
# ─────────────────────────────────────────────────────────────
# Pipeline:
#   1. Merge snapshot into session vector
#   2. Build 55-float vector
#   3. Run ML scoring (predict)
#   4. Check SIM swap status
#   5. Build device context
#   6. Run score fusion
#   7. Generate anomaly explanations
#   8. Persist score to DB
#   9. Trigger alert if BLOCK_AND_FREEZE
# ─────────────────────────────────────────────────────────────

@router.post("/feature", response_model=FeatureResponse)
def submit_feature(req: FeatureRequest, db: DBSession = Depends(get_db)):
    # Load session
    session = db.query(SessionModel).filter_by(id=req.session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    if not model_exists(session.user_id):
        raise HTTPException(400, "User not enrolled. Call POST /enroll/{user_id} first.")

    # Step 1: Merge snapshot into existing session vector
    if session.feature_vector:
        current_vector = json.loads(session.feature_vector)
    else:
        current_vector = [0.0] * FEATURE_DIM

    # Merge incoming snapshot keys into vector
    for key, value in req.feature_snapshot.items():
        if key in FEATURE_NAMES:
            idx = FEATURE_NAMES.index(key)
            current_vector[idx] = float(value)

    # Step 2: Build feature vector (already done via merge)
    feature_vector = current_vector

    # Step 3: ML scoring
    behavior_score = predict(session.user_id, feature_vector)

    # Step 4: Check SIM swap status
    sim_swap = (
        db.query(SimSwapEvent)
        .filter_by(user_id=session.user_id, is_active=True)
        .first()
    )
    sim_swap_active = sim_swap is not None
    sim_swap_minutes = get_sim_swap_minutes(sim_swap) if sim_swap else 0

    # Step 5: Build device context from DeviceRegistry
    device_context = _build_device_context(db, session)

    # Step 6: Score fusion
    fusion = fuse_score(behavior_score, sim_swap_active, device_context)

    # Step 7: Generate anomaly explanations
    meta = get_baseline_stats(session.user_id)
    anomalies = get_top_anomalies(
        feature_vector=feature_vector,
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
        sim_swap_active=sim_swap_active,
        sim_swap_minutes=sim_swap_minutes,
    )

    # Step 8: Persist score to DB
    score_record = Score(
        session_id=req.session_id,
        snapshot_index=req.snapshot_index,
        confidence_score=fusion["final_score"],
        risk_level=fusion["risk_level"],
        action=fusion["action"],
        top_anomalies=json.dumps(anomalies),
    )
    db.add(score_record)

    # Update session feature vector
    session.feature_vector = json.dumps(feature_vector)
    db.commit()

    # Step 9: Auto-trigger alert if BLOCK_AND_FREEZE
    if fusion["action"] == "BLOCK_AND_FREEZE":
        _auto_alert(req.session_id, fusion["final_score"], anomalies, db)

    logger.info(
        f"Score: session={req.session_id[:8]}... "
        f"snap={req.snapshot_index} "
        f"score={fusion['final_score']} "
        f"risk={fusion['risk_level']} "
        f"action={fusion['action']}"
    )

    return FeatureResponse(
        score=fusion["final_score"],
        risk_level=fusion["risk_level"],
        action=fusion["action"],
        top_anomalies=anomalies,
        snapshot_index=req.snapshot_index,
    )


# ─────────────────────────────────────────────────────────────
# POST /session/fleet-check
# ─────────────────────────────────────────────────────────────

@router.post("/fleet-check", response_model=FleetCheckResponse)
def fleet_check(req: FleetCheckRequest, db: DBSession = Depends(get_db)):
    from backend.ml.fleet_anomaly import check_fleet_anomaly
    result = check_fleet_anomaly(db, req.device_fingerprint, req.user_id)
    return FleetCheckResponse(
        fleet_anomaly=result["fleet_anomaly"],
        accounts_seen=result["accounts_seen"],
        action=result["action"],
    )


# ─────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────

def _build_device_context(db: DBSession, session: SessionModel) -> dict:
    """Build device trust context from DeviceRegistry for score fusion."""
    from sqlalchemy import func

    device = (
        db.query(DeviceRegistry)
        .filter(
            DeviceRegistry.user_id == session.user_id,
            DeviceRegistry.device_class == session.device_class,
        )
        .order_by(DeviceRegistry.last_seen.desc())
        .first()
    )

    session_count = device.session_count if device else 0
    is_known_fp = 1 if (device and device.session_count >= 3) else 0

    # Has user ever used this device class before?
    class_count = (
        db.query(DeviceRegistry)
        .filter(
            DeviceRegistry.user_id == session.user_id,
            DeviceRegistry.device_class == session.device_class,
        )
        .count()
    )
    device_class_known = 1 if class_count > 0 else 0

    # Dominant device class in last 30 days
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)
    dominant_row = (
        db.query(SessionModel.device_class, func.count(SessionModel.id).label("cnt"))
        .filter(SessionModel.user_id == session.user_id, SessionModel.started_at >= cutoff)
        .group_by(SessionModel.device_class)
        .order_by(func.count(SessionModel.id).desc())
        .first()
    )
    dominant_class = dominant_row[0] if dominant_row else "mobile"
    device_class_switch = 1 if dominant_class != session.device_class else 0

    return {
        "device_class_known":   device_class_known,
        "device_session_count": session_count,
        "device_class_switch":  device_class_switch,
        "is_known_fingerprint": is_known_fp,
    }


def _auto_alert(session_id: str, score: int, anomalies: list[str], db: DBSession):
    """Auto-trigger SMS alert on BLOCK_AND_FREEZE."""
    recipient = os.getenv("DEMO_ALERT_NUMBER", "")
    if not recipient:
        return

    from backend.utils.twilio_client import send_sms
    from backend.db.models import AlertLog

    message_sid = send_sms(to=recipient, score=score, top_anomalies=anomalies)
    log = AlertLog(
        session_id=session_id,
        alert_type="SMS",
        recipient=recipient,
        message=f"Auto-triggered | Score: {score}",
        message_sid=message_sid,
    )
    db.add(log)
    db.commit()
