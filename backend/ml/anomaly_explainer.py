import numpy as np
import pickle
import os
from backend.ml.feature_schema import FEATURE_NAMES

MODEL_DIR = os.path.join(os.getcwd(), "backend", "ml", "models")

# Z-score threshold |z| > 2.5 captures ~99% of normal variation
Z_SCORE_FLAG_THRESHOLD = 2.5

ANOMALY_TEMPLATES = {
    "inter_key_delay_mean":    "Typing speed {direction} {pct}% from baseline",
    "time_to_submit_otp_ms":   "OTP submitted {pct}% {direction} than user average",
    "direct_to_transfer":      "Went directly to transfer -- atypical navigation pattern",
    "is_new_device":           "Device fingerprint unknown -- never seen for this account",
    "exploratory_ratio":       "Navigation {pct}% more exploratory than normal",
    "hand_stability_score":    "Device motion stability {pct}% below baseline",
    "session_duration_ms":     "Session {pct}% {direction} than user average",
    "click_speed_std":         "Interaction timing variance {direction} -- possible automation",
    "swipe_velocity_mean":     "Touch behavior absent -- possible non-mobile device",
    "form_field_order_entropy":"Form completion order atypical",
    "time_of_day_hour":        "Login at {hour}:00 -- outside user's typical hours",
    "typing_burst_count":      "Typing pattern: single unbroken burst -- possible automation",
    "error_rate":              "Zero typing errors -- possible automated input",
    "device_class_switch":     "Device class switched from enrolled type -- first {device_class} session",
    "is_known_fingerprint":    "Device fingerprint not in trusted registry (seen < 3 times)",
    "mouse_movement_entropy":  "Mouse movement entropy {direction} -- possible bot or scripted input",
    "mouse_speed_cv":          "Mouse speed variation {direction} baseline -- possible automation",
    "scroll_wheel_event_count":"Scroll wheel count {direction} expected range for device type",
}


def get_scaler_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}_{device_class}.pkl")


def explain_anomalies(
    user_id: int,
    feature_vector: list,
    device_class: str = "all"
) -> list:
    """
    Compute per-feature z-scores against user's trained StandardScaler.
    Returns all 55 features ranked by absolute z-score (most anomalous first).

    Loads scaler for device_class='desktop' if available, falls back to 'all'.
    Works with 55-feature vectors automatically — scaler dims match training dims.
    """
    if len(feature_vector) != len(FEATURE_NAMES):
        raise ValueError(f"Expected {len(FEATURE_NAMES)} features, got {len(feature_vector)}")

    # Scaler fallback: device-specific → all
    scaler = None
    for dc in ([device_class, "all"] if device_class != "all" else ["all"]):
        try:
            with open(get_scaler_path(user_id, dc), "rb") as f:
                scaler = pickle.load(f)
            break
        except FileNotFoundError:
            continue

    if scaler is None:
        return _build_empty_explanation(feature_vector)

    baseline_means = scaler.mean_   # shape (55,)
    baseline_stds  = scaler.scale_  # shape (55,)

    X         = np.array(feature_vector)
    safe_stds = np.where(baseline_stds < 1e-8, 1e-8, baseline_stds)
    z_scores  = (X - baseline_means) / safe_stds

    results = []
    for i, name in enumerate(FEATURE_NAMES):
        z = float(z_scores[i])
        results.append({
            "name":          name,
            "value":         float(feature_vector[i]),
            "baseline_mean": float(baseline_means[i]),
            "baseline_std":  float(baseline_stds[i]),
            "z_score":       round(z, 3),
            "flagged":       abs(z) > Z_SCORE_FLAG_THRESHOLD,
        })

    # Most anomalous first
    results.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return results


def top_anomaly_strings(
    user_id: int,
    feature_vector: list,
    device_class: str = "all",
    top_n: int = 4
) -> list:
    """
    Return top N human-readable anomaly strings for display in alert feed.
    Passes device_class to explain_anomalies for correct scaler selection.
    """
    explanations = explain_anomalies(user_id, feature_vector, device_class)
    flagged      = [e for e in explanations if e["flagged"]]

    strings = []
    for e in flagged:
        if len(strings) >= top_n:
            break

        template = ANOMALY_TEMPLATES.get(e["name"])
        if template:
            direction = "faster" if e["z_score"] < 0 else "slower"
            if e["name"] in ["direct_to_transfer", "is_new_device", "form_field_order_entropy",
                              "device_class_switch", "is_known_fingerprint"]:
                direction = "atypical"
            if e["name"] in ["mouse_movement_entropy", "mouse_speed_cv",
                              "scroll_wheel_event_count"]:
                direction = "below" if e["z_score"] < 0 else "above"

            pct = int(abs(e["z_score"]) * 10)
            msg = template.format(
                direction=direction,
                pct=pct,
                hour=int(e["value"]),
                device_class="desktop" if e["value"] == 1 else "mobile",
            )
            strings.append(msg)
        else:
            direction = "above" if e["z_score"] > 0 else "below"
            magnitude = abs(e["z_score"])
            strings.append(
                f"{e['name']}: {magnitude:.1f} std {direction} baseline"
            )

    if not strings:
        strings.append("No significant anomalies detected")

    return strings[:top_n]


def _build_empty_explanation(feature_vector: list) -> list:
    """Fallback when no trained scaler exists."""
    return [
        {
            "name":          name,
            "value":         float(feature_vector[i]),
            "baseline_mean": 0.0,
            "baseline_std":  1.0,
            "z_score":       0.0,
            "flagged":       False,
        }
        for i, name in enumerate(FEATURE_NAMES)
    ]
