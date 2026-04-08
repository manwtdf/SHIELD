"""
ml/feature_schema.py
────────────────────────────────────────────────────────────────────────────────
Single source of truth for all 55 behavioral features.
Import FEATURE_NAMES everywhere. Never hardcode feature names elsewhere.

Feature count: 55 (updated from 47 — added Device Trust Context + Mouse Biometrics)
"""

FEATURE_NAMES: list[str] = [
    # ── Touch Dynamics (8) ──────────────────────────────────────────────────
    "tap_pressure_mean",
    "tap_pressure_std",
    "swipe_velocity_mean",
    "swipe_velocity_std",
    "gesture_curvature_mean",
    "pinch_zoom_accel_mean",
    "tap_duration_mean",
    "tap_duration_std",
    # ── Typing Biometrics (10) ──────────────────────────────────────────────
    "inter_key_delay_mean",
    "inter_key_delay_std",
    "inter_key_delay_p95",
    "dwell_time_mean",
    "dwell_time_std",
    "error_rate",
    "backspace_frequency",
    "typing_burst_count",
    "typing_burst_duration_mean",
    "words_per_minute",
    # ── Device Motion (8) ───────────────────────────────────────────────────
    "accel_x_std",
    "accel_y_std",
    "accel_z_std",
    "gyro_x_std",
    "gyro_y_std",
    "gyro_z_std",
    "device_tilt_mean",
    "hand_stability_score",
    # ── Navigation Graph (9) ────────────────────────────────────────────────
    "screens_visited_count",
    "navigation_depth_max",
    "back_navigation_count",
    "time_on_dashboard_ms",
    "time_on_transfer_ms",
    "direct_to_transfer",
    "form_field_order_entropy",
    "session_revisit_count",
    "exploratory_ratio",
    # ── Temporal Behavior (8) ───────────────────────────────────────────────
    "session_duration_ms",
    "session_duration_z_score",
    "time_of_day_hour",
    "time_to_submit_otp_ms",
    "click_speed_mean",
    "click_speed_std",
    "form_submit_speed_ms",
    "interaction_pace_ratio",
    # ── Device Context (4) ──────────────────────────────────────────────────
    "is_new_device",
    "device_fingerprint_delta",
    "timezone_changed",
    "os_version_changed",
    # ── Device Trust Context (5) ────────────────────────────────────────────
    "device_class_known",         # 1 if device class (mobile/desktop) matches history
    "device_session_count",       # number of times this device has been seen before
    "device_class_switch",        # 1 if device class changed (e.g. mobile → desktop)
    "is_known_fingerprint",       # 1 if exact fingerprint in device_registry
    "time_since_last_seen_hours", # hours since this device was last used by this user
    # ── Desktop Mouse Biometrics (3) ────────────────────────────────────────
    "mouse_movement_entropy",     # entropy of mouse movement directions (bits)
    "mouse_speed_cv",             # coefficient of variation of cursor speed
    "scroll_wheel_event_count",   # number of scroll events in session
]

assert len(FEATURE_NAMES) == 55, f"Expected 55 features, got {len(FEATURE_NAMES)}"

# Fast index lookup
FEATURE_INDEX: dict[str, int] = {name: i for i, name in enumerate(FEATURE_NAMES)}

# Feature groups for anomaly_explainer context
FEATURE_GROUPS: dict[str, list[str]] = {
    "touch":        FEATURE_NAMES[0:8],
    "typing":       FEATURE_NAMES[8:18],
    "motion":       FEATURE_NAMES[18:26],
    "navigation":   FEATURE_NAMES[26:35],
    "temporal":     FEATURE_NAMES[35:43],
    "device":       FEATURE_NAMES[43:47],
    "device_trust": FEATURE_NAMES[47:52],
    "mouse":        FEATURE_NAMES[52:55],
}

# Features that are categorical (0/1 or small integers) — treated differently
# in anomaly explainer (no percentage change, just flag/not flag)
CATEGORICAL_FEATURES = {
    "is_new_device",
    "timezone_changed",
    "os_version_changed",
    "direct_to_transfer",
    "device_class_known",
    "device_class_switch",
    "is_known_fingerprint",
}

def dict_to_vector(feature_dict: dict[str, float]) -> list[float]:
    """
    Convert a partial or complete feature dict to a 55-length list.
    Missing features default to 0.0.
    Used for partial snapshot scoring and frontend → backend transmission.
    """
    return [float(feature_dict.get(name, 0.0)) for name in FEATURE_NAMES]

def vector_to_dict(vector: list[float]) -> dict[str, float]:
    assert len(vector) == 55, f"Expected 55, got {len(vector)}"
    return {name: vector[i] for i, name in enumerate(FEATURE_NAMES)}
