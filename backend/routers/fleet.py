"""
SHIELD Fleet Router
───────────────────
POST /fleet/check — Cross-account device fingerprint check
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.ml.fleet_anomaly import check_fleet_anomaly

router = APIRouter()


class FleetRequest(BaseModel):
    device_fingerprint: str
    user_id: int


class FleetResponse(BaseModel):
    fleet_anomaly: bool
    accounts_seen: int
    affected_user_ids: list[int]
    action: str


@router.post("/check", response_model=FleetResponse)
def check(req: FleetRequest, db: DBSession = Depends(get_db)):
    """
    Standalone cross-account fraud check.
    Identifies if a single device is attempting to access 2+ accounts within 60 min.
    """
    result = check_fleet_anomaly(db, req.device_fingerprint, req.user_id)
    return FleetResponse(
        fleet_anomaly=result["fleet_anomaly"],
        accounts_seen=result["accounts_seen"],
        affected_user_ids=result["affected_user_ids"],
        action=result["action"],
    )
