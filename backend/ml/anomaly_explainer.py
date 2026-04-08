"""
SHIELD Anomaly Explainer
─────────────────────────
Computes per-feature z-scores and generates human-readable anomaly explanations.
Used for:
    1. Top anomaly strings in score responses (get_top_anomalies)
    2. Feature inspector table in Frontend 3 (get_z_scores)

Decoupled: accepts per_feature_mean/std as parameters (from get_baseline_stats).
No internal model/scaler loading.
"""

import numpy as np
from backend.ml.feature_schema import FEATURE_NAMES, FEATURE_DIM, CATEGORICAL_FEATURES

# Z-score threshold: |z| > 2.5 captures ~99% of normal variation
Z_SCORE_FLAG_THRESHOLD = 2.5

# ─────────────────────────────────────────────────────────────
# HUMAN-READABLE TEMPLATES
# {direction}, {pct}, {value}, {hour}, {typical}, {direction_text}
# are filled at runtime.
# ─────────────────────────────────────────────────────────────

TEMPLATES: dict[str, str] = {
    # Touch Dynamics
    "tap_pressure_mean":         "Touch pressure {direction} {pct}% from baseline",
    "tap_pressure_std":          "Touch pressure variance {direction} — unusual hand behavior",
    "swipe_velocity_mean":       "Swipe speed {direction} {pct}% — possible non-touch device",
    "swipe_velocity_std":        "Swipe speed variance {direction} — unfamiliar device handling",
    "gesture_curvature_mean":    "Gesture path curvature {direction} from enrolled pattern",
    "pinch_zoom_accel_mean":     "Pinch-zoom behavior {direction} — gesture pattern mismatch",
    "tap_duration_mean":         "Tap duration {direction} {pct}% from baseline",
    "tap_duration_std":          "Tap duration variance elevated — possible non-human input",

    # Typing Biometrics
    "inter_key_delay_mean":      "Typing speed {direction} {pct}% from user baseline",
    "inter_key_delay_std":       "Typing rhythm variance {direction} {pct}% — inconsistent keypresses",
    "inter_key_delay_p95":       "Peak typing delay {direction} {pct}% above normal",
    "dwell_time_mean":           "Key hold duration {direction} {pct}% from baseline",
    "dwell_time_std":            "Key hold variance {direction} — possible manual hesitation",
    "error_rate":                "Typing error rate {direction} {pct}% — {direction_text}",
    "backspace_frequency":       "Backspace use {direction} {pct}% from baseline",
    "typing_burst_count":        "Typing burst count {direction} — possible single-burst automation",
    "typing_burst_duration_mean":"Typing burst duration {direction} {pct}% from baseline",
    "words_per_minute":          "Input speed {direction} {pct}% from enrolled baseline",

    # Device Motion
    "accel_x_std":               "X-axis accelerometer variance {direction} during session",
    "accel_y_std":               "Y-axis accelerometer variance {direction} during session",
    "accel_z_std":               "Z-axis accelerometer variance {direction} during session",
    "gyro_x_std":                "Gyroscope X-axis variance {direction} — unusual device orientation",
    "gyro_y_std":                "Gyroscope Y-axis variance {direction}",
    "gyro_z_std":                "Gyroscope Z-axis variance {direction}",
    "device_tilt_mean":          "Device tilt angle {direction} {pct}% from enrolled posture",
    "hand_stability_score":      "Device stability {direction} {pct}% — motion pattern mismatch",

    # Navigation Graph
    "screens_visited_count":     "Screen count {direction} {pct}% — {direction_text} exploration",
    "navigation_depth_max":      "Navigation depth {direction} from typical session pattern",
    "back_navigation_count":     "Back-navigation count {direction} {pct}% — {direction_text}",
    "time_on_dashboard_ms":      "Dashboard dwell time {direction} {pct}% — {direction_text}",
    "time_on_transfer_ms":       "Transfer screen dwell {direction} {pct}% from baseline",
    "direct_to_transfer":        "Navigated directly to transfer — atypical for this user",
    "form_field_order_entropy":  "Form completion order atypical — possible automated input",
    "session_revisit_count":     "Screen revisit count {direction} {pct}%",
    "exploratory_ratio":         "Navigation {direction} {pct}% more exploratory than normal",

    # Temporal Behavior
    "session_duration_ms":       "Session {direction} {pct}% than user average — {direction_text}",
    "session_duration_z_score":  "Session duration z-score {direction} — statistical outlier",
    "time_of_day_hour":          "Login at {value:.0f}:00 — outside user's typical hours",
    "time_to_submit_otp_ms":     "OTP submitted {pct}% {direction} than user average",
    "click_speed_mean":          "Click speed {direction} {pct}% from baseline",
    "click_speed_std":           "Click timing variance {direction} — possible automation",
    "form_submit_speed_ms":      "Form submission speed {direction} {pct}% — {direction_text}",
    "interaction_pace_ratio":    "Interaction pace {direction} {pct}% — {direction_text}",

    # Device Context
    "is_new_device":             "Device fingerprint unknown — never seen for this account",
    "device_fingerprint_delta":  "Device fingerprint similarity {direction} — likely different hardware",
    "timezone_changed":          "Timezone differs from last 5 sessions — location anomaly",
    "os_version_changed":        "OS version changed since last session",

    # Device Trust Context
    "device_class_known":        "First-ever session on this device class",
    "device_session_count":      "Zero prior sessions on this device fingerprint",
    "device_class_switch":       "Device class switched from enrolled type — new device type",
    "is_known_fingerprint":      "Device fingerprint not in trusted registry (seen < 3 times)",
    "time_since_last_seen_hours":"Device not seen for {value:.0f} hours — stale device",

    # Desktop Mouse Biometrics
    "mouse_movement_entropy":    "Mouse movement entropy {direction} — possible bot or scripted input",
    "mouse_speed_cv":            "Mouse speed variation {direction} baseline — possible automation",
    "scroll_wheel_event_count":  "Scroll wheel count {direction} expected range for device type",

    # SIM swap (always appended last)
    "SIM_SWAP":                  "SIM swap event detected {minutes} minute(s) ago (telecom signal)",
}


def get_top_anomalies(
    feature_vector: list[float],
    per_feature_mean: list[float],
    per_feature_std: list[float],
    sim_swap_active: bool,
    sim_swap_minutes: int = 6,
    n: int = 4,
) -> list[str]:
    """
    Compute z-scores for all 55 features.
    Return the top n-1 anomalies as human-readable strings.
    If sim_swap_active: always include SIM_SWAP as the nth entry.

    Args:
        feature_vector:    list[float] len=55
        per_feature_mean:  list[float] len=55
        per_feature_std:   list[float] len=55
        sim_swap_active:   bool
        sim_swap_minutes:  int — minutes since SIM swap triggered
        n:                 int — total anomalies to return (default 4)

    Returns:
        list[str] len=n
    """
    fv = np.array(feature_vector)
    mu = np.array(per_feature_mean)
    sigma = np.array(per_feature_std)

    # z-score per feature
    z_scores = (fv - mu) / sigma  # shape (55,)

    # Sort by abs(z) descending
    sorted_indices = np.argsort(np.abs(z_scores))[::-1]

    # Build anomaly strings for top (n-1) features
    anomalies = []
    slots = (n - 1) if sim_swap_active else n

    for idx in sorted_indices:
        if len(anomalies) >= slots:
            break

        feature_name = FEATURE_NAMES[idx]
        z = float(z_scores[idx])
        value = float(fv[idx])
        baseline = float(mu[idx])

        if abs(z) < 1.5:
            continue  # skip near-normal features

        # Skip categorical features that are at baseline
        if feature_name in CATEGORICAL_FEATURES and value == baseline:
            continue

        anomalies.append(_format_anomaly(feature_name, z, value, baseline))

    # Pad if fewer than slots found
    while len(anomalies) < slots:
        anomalies.append("Behavioral pattern deviates from enrolled baseline")

    # Append SIM swap signal
    if sim_swap_active:
        sim_msg = TEMPLATES["SIM_SWAP"].format(minutes=sim_swap_minutes)
        anomalies.append(sim_msg)

    return anomalies[:n]


def get_z_scores(
    feature_vector: list[float],
    per_feature_mean: list[float],
    per_feature_std: list[float],
) -> list[dict]:
    """
    Return z-score info for all 55 features.
    Used by GET /features/inspect/{session_id}.
    """
    fv = np.array(feature_vector)
    mu = np.array(per_feature_mean)
    sigma = np.array(per_feature_std)
    z_scores = (fv - mu) / sigma

    return [
        {
            "name":     FEATURE_NAMES[i],
            "value":    round(float(fv[i]), 4),
            "baseline": round(float(mu[i]), 4),
            "z_score":  round(float(z_scores[i]), 3),
            "flagged":  bool(abs(float(z_scores[i])) > Z_SCORE_FLAG_THRESHOLD),
        }
        for i in range(FEATURE_DIM)
    ]


def _format_anomaly(feature_name: str, z: float, value: float, baseline: float) -> str:
    """Format a single anomaly string using the template for this feature."""
    template = TEMPLATES.get(feature_name, f"Feature {feature_name} deviates from baseline (z={{z:.1f}})")

    direction = "higher" if z > 0 else "lower"
    pct = int(abs((value - baseline) / max(abs(baseline), 1e-6)) * 100)
    direction_text = "unusual increase" if z > 0 else "unusual decrease"

    try:
        return template.format(
            direction=direction,
            pct=pct,
            value=value,
            baseline=baseline,
            hour=value,
            typical="9–20",
            direction_text=direction_text,
            f=feature_name,
            z=z,
            minutes=6,
        )
    except (KeyError, ValueError):
        return f"{feature_name}: z-score={z:.1f} ({direction} than baseline)"
