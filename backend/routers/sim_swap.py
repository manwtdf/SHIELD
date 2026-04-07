import datetime
from fastapi import APIRouter, HTTPException
from backend.db.models import SessionLocal, SimSwapEvent

router = APIRouter(prefix="/sim-swap", tags=["Telecom Signal Management"])

@router.post("/trigger")
def trigger_sim_swap(user_id: int):
    """
    Simulates a SIM swap event from a telecom API.
    """
    db = SessionLocal()
    try:
        event = SimSwapEvent(user_id=user_id, is_active=True)
        db.add(event)
        db.commit()
        return {
            "event_id": event.id, 
            "triggered_at": event.triggered_at.isoformat(),
            "is_active": True
        }
    finally:
        db.close()

@router.post("/clear")
def clear_sim_swap(user_id: int):
    """
    Clears active SIM swap status for a user.
    """
    db = SessionLocal()
    try:
        db.query(SimSwapEvent).filter(SimSwapEvent.user_id == user_id).update({"is_active": False})
        db.commit()
        return {"cleared": True}
    finally:
        db.close()

@router.get("/status/{user_id}")
def get_sim_swap_status(user_id: int):
    """
    Check if a user has an active SIM swap flag.
    """
    db = SessionLocal()
    try:
        event = db.query(SimSwapEvent).filter(SimSwapEvent.user_id == user_id, SimSwapEvent.is_active == True).first()
        if not event:
            return {"is_active": False, "triggered_at": None, "minutes_ago": None}
        
        minutes_ago = int((datetime.datetime.utcnow() - event.triggered_at).total_seconds() / 60)
        return {
            "is_active": True,
            "triggered_at": event.triggered_at.isoformat(),
            "minutes_ago": minutes_ago
        }
    finally:
        db.close()
