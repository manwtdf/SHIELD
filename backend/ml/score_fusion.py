def fuse_score(
    behavior_score: int,
    sim_swap_active: bool,
    device_context: dict = None
) -> dict:
    """
    Combine behavioral confidence with SIM swap signal and device trust context.

    device_context keys:
        device_class_known    (int)   1 = user has prior sessions on this device class
        device_session_count  (int)   prior session count on exact fingerprint
        device_class_switch   (int)   1 = switched from dominant device class (e.g. mobile→desktop)
        is_known_fingerprint  (int)   1 = fingerprint seen 3+ times before
        time_since_last_seen_hours (float) hours since last session on this device
    """
    if device_context is None:
        device_context = {}

    device_class_known        = int(device_context.get("device_class_known", 1))
    device_session_count      = int(device_context.get("device_session_count", 1))
    device_class_switch       = int(device_context.get("device_class_switch", 0))
    is_known_fingerprint      = int(device_context.get("is_known_fingerprint", 1))

    final_score = behavior_score
    risk_level  = "LOW"
    action      = "ALLOW"
    reason      = ""

    # ── Priority 0: SIM swap + first-ever device class switch + unknown fingerprint
    # Definitive attacker pattern: enrolled mobile, now on unknown PC, SIM stolen.
    # Legitimate users who PC-bank have prior PC sessions in registry.
    if (sim_swap_active
            and device_class_switch == 1
            and is_known_fingerprint == 0
            and device_session_count == 0):
        final_score = min(behavior_score, 20)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + no prior desktop banking history + unknown device"

    # ── Priority 1: SIM swap + known desktop user + behavioral anomaly
    # User legitimately uses both mobile and desktop. SIM stolen. Behavior anomalous.
    elif sim_swap_active and device_class_known == 1 and behavior_score < 45:
        final_score = min(behavior_score, 30)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + behavioral anomaly on known desktop"

    # ── Priority 2: SIM swap + known exact fingerprint (user's own PC or office PC)
    # Reduced penalty vs unknown device — known PC means some trust established.
    elif sim_swap_active and is_known_fingerprint == 1:
        final_score = int(behavior_score * 0.75)   # 25% penalty (vs 40% for unknown)
        risk_level  = "HIGH" if final_score < 45 else "MEDIUM"
        action      = "BLOCK_TRANSACTION" if risk_level == "HIGH" else "STEP_UP_AUTH"
        reason      = "SIM swap on known device — step-up required"

    # ── Priority 3: Original SIM swap rule (unknown device, no class switch info)
    elif sim_swap_active and behavior_score < 45:
        final_score = min(behavior_score, 25)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + low behavior confidence"

    elif sim_swap_active:
        final_score = int(behavior_score * 0.6)
        risk_level  = "HIGH" if final_score < 45 else "MEDIUM"
        action      = "BLOCK_TRANSACTION" if risk_level == "HIGH" else "STEP_UP_AUTH"
        reason      = "SIM swap active — score penalized"

    # ── Priority 4: New unknown device + behavioral anomaly (no SIM swap)
    # Cybercafe / friend's PC with unusual behavior. Friction, not block.
    elif is_known_fingerprint == 0 and device_session_count == 0 and behavior_score < 50:
        final_score = int(behavior_score * 0.85)
        risk_level  = "MEDIUM"
        action      = "STEP_UP_AUTH"
        reason      = "First session on unknown device + behavioral deviation"

    # ── Priority 5: New device, behavior within baseline (cybercafe, friend's PC)
    # User behavior is normal → light OTP re-verification only, no score penalty.
    elif is_known_fingerprint == 0 and behavior_score >= 70:
        final_score = behavior_score
        risk_level  = "LOW"
        action      = "ALLOW"
        reason      = "New device — behavior consistent with baseline"

    # ── Priorities 6–9: Original behavior-only rules (no device anomaly)
    elif behavior_score < 30:
        risk_level = "CRITICAL"
        action     = "BLOCK_AND_FREEZE"
        reason     = "Behavior critically anomalous"

    elif behavior_score < 45:
        risk_level = "HIGH"
        action     = "BLOCK_TRANSACTION"
        reason     = "High behavioral anomaly"

    elif behavior_score < 70:
        risk_level = "MEDIUM"
        action     = "STEP_UP_AUTH"
        reason     = "Moderate behavioral deviation"

    else:
        risk_level = "LOW"
        action     = "ALLOW"
        reason     = "Behavior within baseline"

    return {
        "final_score": final_score,
        "risk_level":  risk_level,
        "action":      action,
        "reason":      reason,
    }
