import numpy as np
import pickle
import os
from backend.ml.feature_schema import FEATURE_NAMES

MODEL_DIR = os.path.join(os.getcwd(), "backend", "ml", "models")

# Z-score threshold above which a feature is flagged as anomalous
Z_SCORE_FLAG_THRESHOLD = 2.5


def get_scaler_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}.pkl")


def get_metadata_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"metadata_{user_id}.pkl")


def explain_anomalies(user_id: int, feature_vector: list) -> list[dict]:
    """
    Compute per-feature z-scores against user's trained scaler (mean/std).
    Returns list of all 47 features with z-score and flagged status.
    Sorted by absolute z-score descending (most anomalous first).

    Args:
        user_id:        User whose baseline scaler to compare against
        feature_vector: 47-float list from current session

    Returns:
        List of dicts: [{name, value, baseline_mean, baseline_std, z_score, flagged}]
    """
    if len(feature_vector) != len(FEATURE_NAMES):
        raise ValueError(f"Expected {len(FEATURE_NAMES)} features, got {len(feature_vector)}")

    try:
        with open(get_scaler_path(user_id), 'rb') as f:
            scaler = pickle.load(f)
    except FileNotFoundError:
        # No trained model: return zero z-scores, nothing flagged
        return _build_empty_explanation(feature_vector)

    # StandardScaler stores mean_ and scale_ (std dev) per feature
    baseline_means = scaler.mean_           # shape (47,)
    baseline_stds  = scaler.scale_          # shape (47,)

    X = np.array(feature_vector)

    # Z-score: how many std deviations from user's learned mean
    # Avoid division by zero for zero-variance features
    safe_stds = np.where(baseline_stds < 1e-8, 1e-8, baseline_stds)
    z_scores = (X - baseline_means) / safe_stds

    results = []
    for i, name in enumerate(FEATURE_NAMES):
        z = float(z_scores[i])
        results.append({
            "name":           name,
            "value":          float(feature_vector[i]),
            "baseline_mean":  float(baseline_means[i]),
            "baseline_std":   float(baseline_stds[i]),
            "z_score":        round(z, 3),
            "flagged":        abs(z) > Z_SCORE_FLAG_THRESHOLD,
        })

    # Sort: most anomalous first
    results.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return results


def top_anomaly_strings(user_id: int, feature_vector: list, top_n: int = 4) -> list[str]:
    """
    Return top N human-readable anomaly strings for display in alert feed.
    Example: "inter_key_delay_mean: +3.8 std above baseline"
    """
    explanations = explain_anomalies(user_id, feature_vector)
    flagged = [e for e in explanations if e["flagged"]]

    strings = []
    for e in flagged[:top_n]:
        direction = "above" if e["z_score"] > 0 else "below"
        magnitude = abs(e["z_score"])
        strings.append(
            f"{e['name']}: {magnitude:.1f} std {direction} baseline "
            f"(value={e['value']:.2f}, baseline={e['baseline_mean']:.2f})"
        )

    if not strings:
        strings.append("No significant anomalies detected")

    return strings


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
