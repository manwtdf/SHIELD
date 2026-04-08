"""
SHIELD SIM Swap Router
──────────────────────
POST /sim-swap/trigger      — Simulate SIM swap event
POST /sim-swap/clear        — Clear active SIM swap
GET  /sim-swap/status/{uid} — Check SIM swap status
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db.models import SimSwapEvent
from backend.utils.scoring import get_sim_swap_minutes

router = APIRouter()


class TriggerRequest(BaseModel):
    user_id: int


class TriggerResponse(BaseModel):
    event_id: str
    triggered_at: str
    is_active: bool


class ClearRequest(BaseModel):
    user_id: int


class StatusResponse(BaseModel):
    is_active: bool
    triggered_at: str | None
    minutes_ago: int | None


@router.post("/trigger", response_model=TriggerResponse)
def trigger(req: TriggerRequest, db: DBSession = Depends(get_db)):
    """Simulate a SIM swap event from telecom API."""
    # Clear any existing active swaps for this user
    existing = db.query(SimSwapEvent).filter_by(user_id=req.user_id, is_active=True).all()
    for e in existing:
        e.is_active = False
        e.cleared_at = datetime.utcnow()
    db.commit()

    # Create new swap event
    event = SimSwapEvent(user_id=req.user_id)
    db.add(event)
    db.commit()
    db.refresh(event)

    return TriggerResponse(
        event_id=event.id,
        triggered_at=event.triggered_at.isoformat(),
        is_active=True,
    )


@router.post("/clear")
def clear(req: ClearRequest, db: DBSession = Depends(get_db)):
    """Clear active SIM swap status for a user."""
    events = db.query(SimSwapEvent).filter_by(user_id=req.user_id, is_active=True).all()
    for e in events:
        e.is_active = False
        e.cleared_at = datetime.utcnow()
    db.commit()
    return {"cleared": True, "count": len(events)}


@router.get("/status/{user_id}", response_model=StatusResponse)
def status(user_id: int, db: DBSession = Depends(get_db)):
    """Check if a user has an active SIM swap flag."""
    event = (
        db.query(SimSwapEvent)
        .filter_by(user_id=user_id, is_active=True)
        .order_by(SimSwapEvent.triggered_at.desc())
        .first()
    )
    if not event:
        return StatusResponse(is_active=False, triggered_at=None, minutes_ago=None)

    return StatusResponse(
        is_active=True,
        triggered_at=event.triggered_at.isoformat(),
        minutes_ago=get_sim_swap_minutes(event),
    )
