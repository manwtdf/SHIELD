def fuse_score(
    behavior_score: int,
    sim_swap_active: bool
) -> dict:
    """
    Combine behavioral confidence with binary SIM swap signal.
    Applies cascading priority rules (Rule 1-6) from ML_ENGINE.md.
    """
    final_score = behavior_score
    risk_level  = "LOW"
    action      = "ALLOW"
    reason      = "Behavior within baseline"

    # Rule 1: SIM confirmed stolen + behavior anomalous = certain fraud
    if sim_swap_active and behavior_score < 45:
        final_score = min(behavior_score, 25)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + behavioral anomaly detected"

    # Rule 2: SIM swap alone (probabilistic penalty)
    elif sim_swap_active:
        final_score = int(behavior_score * 0.6)
        risk_level  = "HIGH" if final_score < 45 else "MEDIUM"
        action      = "BLOCK_TRANSACTION" if risk_level == "HIGH" else "STEP_UP_AUTH"
        reason      = "SIM swap active — score penalized 40%"

    # Rule 3: Extreme behavioral outlier (no SIM swap)
    elif behavior_score < 30:
        risk_level = "CRITICAL"
        action     = "BLOCK_AND_FREEZE"
        reason     = "Extreme behavioral anomaly detected"

    # Rule 4: High behavioral anomaly
    elif behavior_score < 45:
        risk_level = "HIGH"
        action     = "BLOCK_TRANSACTION"
        reason     = "High behavioral deviation"

    # Rule 5: Moderate behavioral deviation
    elif behavior_score < 70:
        risk_level = "MEDIUM"
        action     = "STEP_UP_AUTH"
        reason     = "Moderate behavioral deviation"

    # Rule 6: Normal behavior
    else:
        risk_level = "LOW"
        action     = "ALLOW"
        reason     = "Behavior consistent with baseline"

    return {
        "final_score": final_score,
        "risk_level":  risk_level,
        "action":      action,
        "reason":      reason
    }
