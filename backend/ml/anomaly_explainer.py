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
    "direct_to_transfer":      "Went directly to transfer — atypical navigation pattern",
    "is_new_device":           "Device fingerprint unknown — never seen for this account",
    "exploratory_ratio":       "Navigation {pct}% more exploratory than normal",
    "hand_stability_score":    "Device motion stability {pct}% below baseline",
    "session_duration_ms":     "Session {pct}% {direction} than user average",
    "click_speed_std":         "Interaction timing variance {direction} — possible automation",
    "swipe_velocity_mean":     "Touch behavior absent — possible non-mobile device",
    "form_field_order_entropy":"Form completion order atypical",
    "time_of_day_hour":        "Login at {hour}:00 — outside user's typical hours",
    "typing_burst_count":      "Typing pattern: single unbroken burst — possible automation",
    "error_rate":              "Zero typing errors — possible automated input",
}


def get_scaler_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}.pkl")


def explain_anomalies(user_id: int, feature_vector: list) -> list[dict]:
    """
    Compute per-feature z-scores using StandardScaler parameters from training.
    Reuses the scaler already fitted during train_model().
    """
    if len(feature_vector) != 47:
        raise ValueError(f"Expected 47 features, got {len(feature_vector)}")

    try:
        with open(get_scaler_path(user_id), 'rb') as f:
            scaler = pickle.load(f)
    except FileNotFoundError:
        # No trained model: return neutral results
        return _build_empty_explanation(feature_vector)

    # StandardScaler stores mean_ and scale_ (std dev) per feature
    baseline_means = scaler.mean_           # shape (47,)
    baseline_stds  = scaler.scale_          # shape (47,)

    X = np.array(feature_vector)

    # Z-score: (value - mean) / std
    # Avoid division by zero for zero-variance features
    safe_stds = np.where(baseline_stds < 1e-8, 1e-8, baseline_stds)
    z_scores = (X - baseline_means) / safe_stds

    results = []
    for i, name in enumerate(FEATURE_NAMES):
        # Only process the first 47 features (sanity check)
        if i >= 47: break
        
        z = float(z_scores[i])
        results.append({
            "name":           name,
            "value":          float(feature_vector[i]),
            "baseline_mean":  float(baseline_means[i]),
            "baseline_std":   float(baseline_stds[i]),
            "z_score":        round(z, 3),
            "flagged":        abs(z) > Z_SCORE_FLAG_THRESHOLD,
        })

    # Sort by absolute z-score descending (most anomalous first)
    results.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return results


def top_anomaly_strings(user_id: int, feature_vector: list, top_n: int = 4) -> list[str]:
    """
    Return list of human-readable strings summarizing the top flagged anomalies.
    """
    explanations = explain_anomalies(user_id, feature_vector)
    flagged = [e for e in explanations if e["flagged"]]

    strings = []
    for e in flagged:
        if len(strings) >= top_n:
            break
            
        template = ANOMALY_TEMPLATES.get(e["name"])
        if template:
            direction = "faster" if e["z_score"] < 0 else "slower"
            # Special logic for navigation/binary features
            if e["name"] in ["direct_to_transfer", "is_new_device", "form_field_order_entropy"]:
                direction = "atypical"
            
            # Simple pct calculation for templating
            pct = int(abs(e["z_score"]) * 10)
            
            msg = template.format(
                direction=direction,
                pct=pct,
                hour=int(e["value"]),
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


def _build_empty_explanation(feature_vector: list) -> list[dict]:
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
