from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from backend.ml.fleet_anomaly import check_fleet_anomaly, register_device

router = APIRouter(prefix="/fleet", tags=["Fleet Analysis"])

class FleetCheckRequest(BaseModel):
    device_fingerprint: str
    user_id: int

class FleetCheckResponse(BaseModel):
    fleet_anomaly: bool
    accounts_seen: int
    affected_users: List[int]
    action: str

@router.post("/check", response_model=FleetCheckResponse)
def fleet_check(data: FleetCheckRequest):
    """
    Stand-alone cross-account fraud check.
    Identifies if a single device is attempting to access 2+ accounts within 60 mins.
    Action: FREEZE_ALL_ACCOUNTS if detected.
    """
    register_device(data.user_id, data.device_fingerprint)
    res = check_fleet_anomaly(data.device_fingerprint, data.user_id)
    return res
