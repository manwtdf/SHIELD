def fuse_score(behavior_score: int, sim_swap_active: bool) -> dict:
    """
    Combine behavioral confidence with SIM swap signal.
    """
    final_score = behavior_score
    risk_level = "LOW"
    action = "ALLOW"

    # Rule 1: SIM swap + Low behavior confidence
    if sim_swap_active and behavior_score < 45:
        final_score = min(behavior_score, 25)
        risk_level = "CRITICAL"
        action = "BLOCK_AND_FREEZE"
    
    # Rule 2: SIM swap active (general penalty)
    elif sim_swap_active:
        final_score = int(behavior_score * 0.6)
        risk_level = "HIGH" if final_score < 45 else "MEDIUM"
        action = "BLOCK_TRANSACTION" if risk_level == "HIGH" else "STEP_UP_AUTH"

    # Rule 3: Behavior score below critical threshold (independent)
    elif behavior_score < 30:
        risk_level = "CRITICAL"
        action = "BLOCK_AND_FREEZE"

    # Rule 4: High risk (behavior only)
    elif behavior_score < 45:
        risk_level = "HIGH"
        action = "BLOCK_TRANSACTION"

    # Rule 5: Medium risk (behavior only)
    elif behavior_score < 70:
        risk_level = "MEDIUM"
        action = "STEP_UP_AUTH"

    # Rule 6: Low risk
    else:
        risk_level = "LOW"
        action = "ALLOW"

    return {
        "final_score": final_score, 
        "risk_level": risk_level, 
        "action": action
    }
