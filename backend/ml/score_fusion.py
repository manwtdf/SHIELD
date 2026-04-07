def fuse_score(
    behavior_score: int,
    sim_swap_active: bool,
    device_context: dict = None
) -> dict:
    """
    Combine behavioral confidence with SIM swap signal and device trust context.
    9-rule cascading priority chain. Rules evaluated top-to-bottom; first match wins.

    device_context keys (from build_device_context()):
        device_class_known        int   1 = user has prior sessions on this device class
        device_session_count      int   prior sessions on this exact fingerprint
        device_class_switch       int   1 = switched from dominant device class (e.g. mobile->desktop)
        is_known_fingerprint      int   1 = fingerprint in registry with session_count >= 3
        time_since_last_seen_hours float

    Defaults when device_context=None: all-trusted (legacy behavior, no PC rules fire).

    Returns:
        final_score  int    0-100
        risk_level   str    LOW | MEDIUM | HIGH | CRITICAL
        action       str    ALLOW | STEP_UP_AUTH | BLOCK_TRANSACTION | BLOCK_AND_FREEZE
        reason       str    human-readable explanation
    """
    if device_context is None:
        device_context = {}

    device_class_known   = int(device_context.get("device_class_known",   1))
    device_session_count = int(device_context.get("device_session_count", 1))
    device_class_switch  = int(device_context.get("device_class_switch",  0))
    is_known_fingerprint = int(device_context.get("is_known_fingerprint", 1))

    final_score = behavior_score
    risk_level  = "LOW"
    action      = "ALLOW"
    reason      = "Behavior consistent with baseline"

    # ── Rule 1 [ATTACKER PATTERN]
    # SIM swap + first-ever switch to this device class + unknown fingerprint + zero history
    # = mobile-enrolled victim, attacker on unknown PC, SIM stolen.
    # Legitimate users who regularly PC-bank will have prior PC entries in DeviceRegistry.
    if (sim_swap_active
            and device_class_switch == 1
            and is_known_fingerprint == 0
            and device_session_count == 0):
        final_score = min(behavior_score, 20)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + first-ever device class switch + unknown device fingerprint"

    # ── Rule 2 [KNOWN DESKTOP USER, SIM STOLEN, BEHAVIOR ANOMALOUS]
    # User legitimately uses both mobile and PC. SIM stolen. Typing/navigation anomalous.
    elif sim_swap_active and device_class_known == 1 and behavior_score < 45:
        final_score = min(behavior_score, 30)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + behavioral anomaly on known device class"

    # ── Rule 3 [KNOWN FINGERPRINT, SIM SWAP — lighter penalty]
    # User on their own/office PC (seen 3+ times). SIM swap active but device is trusted.
    # 25% penalty (vs 40% for unknown device) — known hardware earns partial trust.
    elif sim_swap_active and is_known_fingerprint == 1:
        final_score = int(behavior_score * 0.75)
        risk_level  = "HIGH" if final_score < 45 else "MEDIUM"
        action      = "BLOCK_TRANSACTION" if risk_level == "HIGH" else "STEP_UP_AUTH"
        reason      = "SIM swap on known device — reduced penalty, step-up required"

    # ── Rule 4 [SIM SWAP + BEHAVIORAL ANOMALY — unknown/general device]
    elif sim_swap_active and behavior_score < 45:
        final_score = min(behavior_score, 25)
        risk_level  = "CRITICAL"
        action      = "BLOCK_AND_FREEZE"
        reason      = "SIM swap + behavioral anomaly detected"

    # ── Rule 5 [SIM SWAP ALONE — general penalty]
    elif sim_swap_active:
        final_score = int(behavior_score * 0.6)
        risk_level  = "HIGH" if final_score < 45 else "MEDIUM"
        action      = "BLOCK_TRANSACTION" if risk_level == "HIGH" else "STEP_UP_AUTH"
        reason      = "SIM swap active — score penalized 40%"

    # ── Rule 6 [NEW UNKNOWN DEVICE + BEHAVIORAL DEVIATION — no SIM swap]
    # First session on this PC (cybercafe, friend's PC) + unusual behavior.
    # Friction only (STEP_UP_AUTH), not block — legitimate cybercafe users are real.
    elif is_known_fingerprint == 0 and device_session_count == 0 and behavior_score < 50:
        final_score = int(behavior_score * 0.85)
        risk_level  = "MEDIUM"
        action      = "STEP_UP_AUTH"
        reason      = "First session on unknown device + behavioral deviation"

    # ── Rule 7 [NEW UNKNOWN DEVICE + BEHAVIOR NORMAL — cybercafe/relative's PC]
    # First time on this PC, behavior matches user's baseline.
    # No penalty. Bank's existing new-device OTP flow handles verification.
    elif is_known_fingerprint == 0 and behavior_score >= 70:
        final_score = behavior_score
        risk_level  = "LOW"
        action      = "ALLOW"
        reason      = "New device — behavior consistent with baseline"

    # ── Rules 8–10 [BEHAVIOR-ONLY — no device anomaly present]

    elif behavior_score < 30:
        risk_level = "CRITICAL"
        action     = "BLOCK_AND_FREEZE"
        reason     = "Extreme behavioral anomaly detected"

    elif behavior_score < 45:
        risk_level = "HIGH"
        action     = "BLOCK_TRANSACTION"
        reason     = "High behavioral deviation"

    elif behavior_score < 70:
        risk_level = "MEDIUM"
        action     = "STEP_UP_AUTH"
        reason     = "Moderate behavioral deviation"

    else:
        risk_level = "LOW"
        action     = "ALLOW"
        reason     = "Behavior consistent with baseline"

    return {
        "final_score": final_score,
        "risk_level":  risk_level,
        "action":      action,
        "reason":      reason,
    }
