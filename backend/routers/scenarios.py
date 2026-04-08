"""
SHIELD Scenarios Router
───────────────────────
GET  /scenarios/list           — List all 7 scenarios with metadata
POST /scenarios/{id}/run       — Run actual ML scoring on progressive snapshots
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import Session as SessionModel, SimSwapEvent
from backend.ml.one_class_svm import predict, get_baseline_stats, model_exists
from backend.ml.score_fusion import fuse_score
from backend.ml.anomaly_explainer import get_top_anomalies
SCENARIO_METADATA = {
    1: {"id": 1, "name": "New Phone + SIM", "type": "attack", "desc": "Attacker uses own device with swapped SIM"},
    2: {"id": 2, "name": "Laptop + OTP SIM", "type": "attack", "desc": "Device modality switch (mobile -> desktop)"},
    3: {"id": 3, "name": "Bot Automation", "type": "attack", "desc": "Inhumanly consistent speed & low entropy"},
    4: {"id": 4, "name": "Same Device Takeover", "type": "attack", "desc": "Attacker on user's unlocked device"},
    5: {"id": 5, "name": "Credential Stuffing + Fleet", "type": "attack", "desc": "Known attacker device across accounts"},
    6: {"id": 6, "name": "Pre-Auth SIM Probe", "type": "attack", "desc": "SIM trigger before authentication starts"},
    7: {"id": 7, "name": "Legitimate User (Control)", "type": "legitimate", "desc": "Normal baseline behavior"},
}

logger = logging.getLogger("shield.scenarios")

router = APIRouter()


class RunResponse(BaseModel):
    scenario_id: int
    score_progression: list[int]
    final_score: int
    action: str
    risk_level: str
    top_anomalies: list[str]
    detection_time_s: float | None


# ─────────────────────────────────────────────────────────────
# GET /scenarios/list
# ─────────────────────────────────────────────────────────────

@router.get("/list")
def list_scenarios():
    """Return all 7 scenario metadata entries."""
    return SCENARIO_METADATA


# ─────────────────────────────────────────────────────────────
# POST /scenarios/{scenario_id}/run
# ─────────────────────────────────────────────────────────────

@router.post("/{scenario_id}/run", response_model=RunResponse)
def run_scenario(scenario_id: int, user_id: int = 1, db: DBSession = Depends(get_db)):
    """
    Run ACTUAL ML scoring on a pre-seeded scenario.
    Computes score progression across 5 progressive alpha-interpolated
    snapshots. This is NOT hardcoded — real OneClassSVM inference happens.
    """
    if scenario_id not in range(1, 8):
        raise HTTPException(400, "scenario_id must be 1–7")

    if not model_exists(user_id):
        raise HTTPException(400, f"User {user_id} not enrolled. Run seed_runner.py first.")

    # Scenario 7 = legitimate control
    session_type = f"scenario_{scenario_id}" if scenario_id <= 6 else "legitimate"

    # Get pre-seeded session
    session = (
        db.query(SessionModel)
        .filter_by(user_id=user_id, session_type=session_type)
        .first()
    )
    if not session or not session.feature_vector:
        # Fallback: if not seeded (e.g. sandbox was reset), generate on the fly
        from backend.data.seed_data import generate_scenario_session
        data = generate_scenario_session(scenario_id)
        if data["pre_auth"]:
            feature_vector = []
        else:
            feature_vector = data["feature_vector"]
            # Also store it back for future
            new_sess = SessionModel(
                user_id=user_id,
                session_type=session_type,
                feature_vector=json.dumps(feature_vector),
                completed=True
            )
            db.add(new_sess)
            db.commit()
    else:
        feature_vector = json.loads(session.feature_vector)

    # Check SIM swap
    sim_swap = db.query(SimSwapEvent).filter_by(user_id=user_id, is_active=True).first()
    sim_swap_active = sim_swap is not None

    # Get baseline stats for interpolation
    meta = get_baseline_stats(user_id)
    legitimate_vector = meta["per_feature_mean"]

    # Compute score progression across 5 snapshots
    # alpha: 0.2 → 0.4 → 0.6 → 0.8 → 1.0
    score_progression = []

    for i in range(5):
        alpha = (i + 1) / 5.0
        partial = [
            (1 - alpha) * l + alpha * a
            for l, a in zip(legitimate_vector, feature_vector)
        ]
        raw_score = predict(user_id, partial)
        fusion = fuse_score(raw_score, sim_swap_active)
        score_progression.append(fusion["final_score"])

    # Final score on full attacker vector
    final_raw = predict(user_id, feature_vector)
    final_fusion = fuse_score(final_raw, sim_swap_active)

    # Anomaly explanations
    anomalies = get_top_anomalies(
        feature_vector=feature_vector,
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
        sim_swap_active=sim_swap_active,
    )

    # Get detection time from metadata
    meta_entry = next((m for m in SCENARIO_METADATA if m["id"] == scenario_id), {})

    logger.info(
        f"Scenario {scenario_id}: progression={score_progression} "
        f"final={final_fusion['final_score']} action={final_fusion['action']}"
    )

    return RunResponse(
        scenario_id=scenario_id,
        score_progression=score_progression,
        final_score=final_fusion["final_score"],
        action=final_fusion["action"],
        risk_level=final_fusion["risk_level"],
        top_anomalies=anomalies,
        detection_time_s=meta_entry.get("detection_time_s"),
    )
