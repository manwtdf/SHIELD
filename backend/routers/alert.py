"""
SHIELD Alert Router
───────────────────
POST /alert/send — Send SMS or LOG alert
"""

import json
import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import AlertLog, Score
from backend.utils.twilio_client import send_sms

logger = logging.getLogger("shield.alert")

router = APIRouter()


class AlertRequest(BaseModel):
    session_id: str
    alert_type: str = "SMS"  # "SMS" | "LOG"
    recipient: str = ""


class AlertResponse(BaseModel):
    sent: bool
    message_sid: str | None


@router.post("/send", response_model=AlertResponse)
def send_alert(req: AlertRequest, db: DBSession = Depends(get_db)):
    """Send SMS or LOG alert for a session."""
    # Get latest score for context
    latest_score = (
        db.query(Score)
        .filter_by(session_id=req.session_id)
        .order_by(Score.computed_at.desc())
        .first()
    )
    score = latest_score.confidence_score if latest_score else 0
    anomalies = json.loads(latest_score.top_anomalies or "[]") if latest_score else []

    # Determine recipient
    recipient = req.recipient or os.getenv("DEMO_ALERT_NUMBER", "")

    message_sid = None
    if req.alert_type == "SMS" and recipient:
        message_sid = send_sms(
            to=recipient,
            score=score,
            top_anomalies=anomalies,
        )
    else:
        logger.info(f"[LOG ALERT] Session: {req.session_id}, Score: {score}, Anomalies: {anomalies[:2]}")

    # Log alert to database
    log = AlertLog(
        session_id=req.session_id,
        alert_type=req.alert_type,
        recipient=recipient or "LOG",
        message=f"Score: {score} | " + " | ".join(anomalies[:2]),
        message_sid=message_sid,
    )
    db.add(log)
    db.commit()

    return AlertResponse(sent=True, message_sid=message_sid)


# ─────────────────────────────────────────────────────────────
# Internal helper — called by session router
# ─────────────────────────────────────────────────────────────

def send_sms_alert(
    session_id: str,
    score: int,
    top_anomalies: list[str],
    recipient: str,
    db: DBSession,
) -> None:
    """Auto-trigger SMS alert. Called internally by session.py on BLOCK_AND_FREEZE."""
    if not recipient:
        return

    message_sid = send_sms(to=recipient, score=score, top_anomalies=top_anomalies)

    log = AlertLog(
        session_id=session_id,
        alert_type="SMS",
        recipient=recipient,
        message=f"Auto-triggered | Score: {score}",
        message_sid=message_sid,
    )
    db.add(log)
    db.commit()
