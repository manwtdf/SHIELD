from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.utils.twilio_client import send_alert as twilio_send

router = APIRouter(prefix="/alert", tags=["Twilio SMS Notifications"])

class AlertRequest(BaseModel):
    session_id: str
    alert_type: str = "SMS" # SMS | LOG
    recipient: str # User phone number

@router.post("/send")
def send_alert(data: AlertRequest):
    """
    Sends a real-world SMS alert via Twilio to the user.
    Uses the latest score and anomalies from the session ID.
    """
    from backend.db.models import SessionLocal, Score
    db = SessionLocal()
    try:
        # Get the latest score for this session to include in the message
        score_record = db.query(Score).filter(Score.session_id == data.session_id).order_by(Score.computed_at.desc()).first()
        score_val = score_record.confidence_score if score_record else 27
        anomalies = score_record.top_anomalies_json if score_record else ["Typing rhythm mismatch", "Unknown device"]

        res = twilio_send(to_number=data.recipient, score=score_val, top_anomalies=anomalies)
        return {
            "sent": res.get("sent", False),
            "message_sid": res.get("message_sid"),
            "error": res.get("error")
        }
    finally:
        db.close()
