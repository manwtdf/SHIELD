from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
from backend.data.seed_scenarios import SCENARIO_PROFILES
from backend.ml.score_fusion import fuse_score

router = APIRouter(prefix="/scenarios", tags=["Attack Simulation"])

class ScenarioInfo(BaseModel):
    id: str
    name: str
    description: str
    expected_score: int
    expected_action: str
    detection_time_s: int

class ScenarioRunResponse(BaseModel):
    score_progression: List[int]
    final_score: int
    action: str
    detection_time_s: float
    top_anomalies: List[str]

@router.get("/list", response_model=List[ScenarioInfo])
def list_scenarios():
    """
    Returns all 6 attack scenarios with their metadata for the simulator dashboard.
    """
    return [
        ScenarioInfo(
            id=k, 
            name=v["name"], 
            description=v["description"], 
            expected_score=v["expected_score"], 
            expected_action=v["expected_action"],
            detection_time_s=v.get("detection_time_s", 28)
        ) for k, v in SCENARIO_PROFILES.items() if k != "legitimate"
    ]

@router.post("/{scenario_id}/run", response_model=ScenarioRunResponse)
def run_scenario(scenario_id: str, user_id: int = 1):
    """
    Simulates a full scenario run end-to-end.
    Returns the score progression across 5 snapshots and final decision.
    """
    if scenario_id not in SCENARIO_PROFILES:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    profile = SCENARIO_PROFILES[scenario_id]
    
    # Standard progressions as specified in documentation
    progressions = {
        "scenario_1": [91, 74, 58, 44, 27],
        "scenario_2": [91, 78, 62, 47, 31],
        "scenario_3": [91, 65, 41, 28, 19],
        "scenario_4": [91, 82, 71, 61, 48],
        "scenario_5": [91, 72, 55, 40, 22],
        "scenario_6": [0, 0, 0, 0, 0], # Pre-auth SIM probe (n/a for behavioral)
    }
    
    score_progression = progressions.get(scenario_id, [91, 80, 70, 60, 50])
    final_score = score_progression[-1]
    
    # Fusion logic for detection result
    sim_swap_active = scenario_id in ["scenario_1", "scenario_4", "scenario_5"]
    fusion = fuse_score(final_score, sim_swap_active)
    
    detection_time_s = profile.get("detection_time_s", 28)
    
    return {
        "score_progression": score_progression,
        "final_score": fusion["final_score"],
        "action": fusion["action"],
        "detection_time_s": detection_time_s,
        "top_anomalies": ["Typing anomaly", "New device", "Navigation anomaly", "SIM swap detected"]
    }
