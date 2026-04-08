"""
SHIELD Score Fusion Engine
──────────────────────────
Combines behavioral confidence score with SIM swap signal
and device trust context to produce final risk decision.

9-rule cascading priority chain. Rules evaluated top-to-bottom;
first match wins.
"""

import os
import logging

logger = logging.getLogger("shield.ml.fusion")

BLOCK_THRESHOLD  = int(os.getenv("SCORE_BLOCK_THRESHOLD", "30"))
STEPUP_THRESHOLD = int(os.getenv("SCORE_STEPUP_THRESHOLD", "45"))


def fuse_score(
    behavior_score: int,
    sim_swap_active: bool,
    device_context: dict = None,
) -> dict:
    """
    Apply SIM swap signal fusion + device context + risk classification.

    device_context keys (from build_device_context()):
        device_class_known        int   1 = user has prior sessions on this device class
        device_session_count      int   prior sessions on this exact fingerprint
        device_class_switch       int   1 = switched from dominant device class
        is_known_fingerprint      int   1 = fingerprint in registry with session_count >= 3

    Defaults when device_context=None: all-trusted (no device penalties).

    Returns:
        {
            "final_score": int,      0–100
            "risk_level":  str,      LOW | MEDIUM | HIGH | CRITICAL
            "action":      str,      ALLOW | STEP_UP_AUTH | BLOCK_TRANSACTION | BLOCK_AND_FREEZE
            "reason":      str,      human-readable explanation
        }
    """
    if device_context is None:
        device_context = {}

    dc_class_known   = int(device_context.get("device_class_known",   1))
    dc_session_count = int(device_context.get("device_session_count", 1))
    dc_class_switch  = int(device_context.get("device_class_switch",  0))
    dc_known_fp      = int(device_context.get("is_known_fingerprint", 1))

    score  = behavior_score
    level  = "LOW"
    action = "ALLOW"
    reason = "Behavior consistent with baseline"

    # ── Rule 1: SIM swap + first-ever device class switch + unknown FP + zero history
    # Attacker on completely new device type (e.g., mobile user → unknown PC)
    if (sim_swap_active
            and dc_class_switch == 1
            and dc_known_fp == 0
            and dc_session_count == 0):
        score  = min(behavior_score, 20)
        level  = "CRITICAL"
        action = "BLOCK_AND_FREEZE"
        reason = "SIM swap + first-ever device class switch + unknown device fingerprint"

    # ── Rule 2: SIM swap + known device class + behavioral anomaly
    elif sim_swap_active and dc_class_known == 1 and behavior_score < STEPUP_THRESHOLD:
        score  = min(behavior_score, BLOCK_THRESHOLD)
        level  = "CRITICAL"
        action = "BLOCK_AND_FREEZE"
        reason = "SIM swap + behavioral anomaly on known device class"

    # ── Rule 3: SIM swap + known fingerprint (trusted device) — lighter penalty
    elif sim_swap_active and dc_known_fp == 1:
        score  = int(behavior_score * 0.75)
        level  = "HIGH" if score < STEPUP_THRESHOLD else "MEDIUM"
        action = "BLOCK_TRANSACTION" if level == "HIGH" else "STEP_UP_AUTH"
        reason = "SIM swap on known device — reduced penalty, step-up required"

    # ── Rule 4: SIM swap + behavioral anomaly (unknown device)
    elif sim_swap_active and behavior_score < STEPUP_THRESHOLD:
        score  = min(behavior_score, 25)
        level  = "CRITICAL"
        action = "BLOCK_AND_FREEZE"
        reason = "SIM swap + behavioral anomaly detected"

    # ── Rule 5: SIM swap alone — general 40% penalty
    elif sim_swap_active:
        score  = int(behavior_score * 0.6)
        level  = "HIGH" if score < STEPUP_THRESHOLD else "MEDIUM"
        action = "BLOCK_TRANSACTION" if level == "HIGH" else "STEP_UP_AUTH"
        reason = "SIM swap active — score penalized 40%"

    # ── Rule 6: Unknown device + behavioral deviation (no SIM swap)
    elif dc_known_fp == 0 and dc_session_count == 0 and behavior_score < 50:
        score  = int(behavior_score * 0.85)
        level  = "MEDIUM"
        action = "STEP_UP_AUTH"
        reason = "First session on unknown device + behavioral deviation"

    # ── Rule 7: Unknown device + behavior normal
    elif dc_known_fp == 0 and behavior_score >= 70:
        score  = behavior_score
        level  = "LOW"
        action = "ALLOW"
        reason = "New device — behavior consistent with baseline"

    # ── Rules 8-10: Behavior-only thresholds
    elif behavior_score < BLOCK_THRESHOLD:
        level  = "CRITICAL"
        action = "BLOCK_AND_FREEZE"
        reason = "Extreme behavioral anomaly detected"

    elif behavior_score < STEPUP_THRESHOLD:
        level  = "HIGH"
        action = "BLOCK_TRANSACTION"
        reason = "High behavioral deviation"

    elif behavior_score < 70:
        level  = "MEDIUM"
        action = "STEP_UP_AUTH"
        reason = "Moderate behavioral deviation"

    else:
        level  = "LOW"
        action = "ALLOW"
        reason = "Behavior consistent with baseline"

    result = {
        "final_score": max(0, min(100, score)),
        "risk_level":  level,
        "action":      action,
        "reason":      reason,
    }

    logger.debug(f"Fusion: behavior={behavior_score}, sim_swap={sim_swap_active} → {result}")
    return result
