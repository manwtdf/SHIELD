"""
data/seed_legitimate.py + seed_scenarios.py
────────────────────────────────────────────────────────────────────────────────
Generates feature vectors for legitimate sessions and all 5 attack scenarios.
All distributions come from profiles.py — no hardcoded values here.
"""

import random
import numpy as np
from backend.data.profiles import PROFILES
from backend.ml.feature_schema import FEATURE_NAMES

WITHIN_PERSON_VARIANCE = 0.08   # ±8% noise on continuous features (published lit.)


# ─────────────────────────────────────────────────────────────────────────────
# SEED LEGITIMATE
# ─────────────────────────────────────────────────────────────────────────────

def generate_legitimate_sessions(n: int = 10) -> list[list[float]]:
    """
    Generate n legitimate user sessions from the 'legitimate' profile.
    Each session gets ±8% within-person variance on continuous features.
    Returns list of n 55-float vectors.
    """
    profile = PROFILES["legitimate"]
    return [_generate_one(profile, apply_variance=True) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# SEED SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────

def generate_scenario_session(scenario_id: int) -> dict:
    """
    Generate one attacker session for the given scenario.

    Returns:
        {
            "feature_vector": list[float],      # full 55-float vector
            "snapshots":      list[list[float]], # 5 progressive partial vectors
            "fleet_fingerprint": str | None,
            "pre_auth": bool,
        }
    """
    key = f"scenario_{scenario_id}"
    if key not in PROFILES:
        raise ValueError(f"No profile found for '{key}' in profiles.py")

    attacker_profile = PROFILES[key]

    if attacker_profile.get("_pre_auth"):
        return {"feature_vector": [], "snapshots": [], "pre_auth": True,
                "fleet_fingerprint": None}

    # Merge legitimate baseline with attacker overrides
    # Attacker profile keys override legitimate keys
    merged = {**PROFILES["legitimate"], **attacker_profile}

    # Generate full attacker vector (no within-person variance — attacker
    # behavior has its own noise already encoded in the profile std values)
    attacker_vector = _generate_one(merged, apply_variance=False)

    # Generate 5 progressive snapshots for the score degradation animation:
    # Snapshot i reveals ((i+1)/5) proportion of attacker features.
    # Start = legitimate baseline, End = full attacker vector.
    legitimate_vector = _generate_one(PROFILES["legitimate"], apply_variance=False)
    snapshots = _progressive_snapshots(legitimate_vector, attacker_vector, n=5)

    return {
        "feature_vector":   attacker_vector,
        "snapshots":        snapshots,
        "fleet_fingerprint": attacker_profile.get("_fleet_fingerprint"),
        "pre_auth":         False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _generate_one(profile: dict, apply_variance: bool = True) -> list[float]:
    """
    Sample a single 55-float feature vector from the given profile.

    Profile value formats:
      [mean, std]          → Normal(mean, std), clamped to >= 0
      {"choices": [...]}   → uniform sample from list
      scalar (float/int)   → fixed value
    """
    vector = []
    for feature in FEATURE_NAMES:
        spec = profile.get(feature)

        if spec is None:
            val = 0.0
        elif isinstance(spec, dict) and "choices" in spec:
            val = float(random.choice(spec["choices"]))
        elif isinstance(spec, list) and len(spec) == 2:
            mean, std = spec
            val = float(np.random.normal(mean, std))
            val = max(0.0, val)
            if apply_variance:
                noise = np.random.uniform(-WITHIN_PERSON_VARIANCE, WITHIN_PERSON_VARIANCE)
                val = max(0.0, val * (1.0 + noise))
        else:
            val = float(spec)

        vector.append(val)

    return vector


def _progressive_snapshots(
    legitimate: list[float],
    attacker: list[float],
    n: int = 5,
) -> list[list[float]]:
    """
    Generate n feature vectors interpolating from legitimate to attacker.
    Snapshot 1 = mostly legitimate (alpha=0.2)
    Snapshot 5 = full attacker (alpha=1.0)

    This drives the score degradation animation:
      snapshot 1 → score ~85 (starts normal)
      snapshot 5 → score ~15-30 (fully attacker)
    """
    snapshots = []
    for i in range(n):
        alpha = (i + 1) / n   # 0.2, 0.4, 0.6, 0.8, 1.0
        snapshot = [
            (1.0 - alpha) * l + alpha * a
            for l, a in zip(legitimate, attacker)
        ]
        snapshots.append(snapshot)
    return snapshots


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICATION (called from seed_runner.py)
# ─────────────────────────────────────────────────────────────────────────────

def verify_attacker_deviation(scenario_id: int) -> dict:
    """
    Verify that an attacker scenario deviates significantly from legitimate baseline
    on at least 4 features. Returns deviation report.
    Called from seed_runner.py as a sanity check before training.
    """
    legitimate_vector = np.array(_generate_one(PROFILES["legitimate"]))
    attacker_data = generate_scenario_session(scenario_id)

    if attacker_data["pre_auth"]:
        return {"scenario": scenario_id, "pre_auth": True, "pass": True}

    attacker_vector = np.array(attacker_data["feature_vector"])

    # Use rough per-feature std from legitimate profile to compute z-scores
    stds = []
    for feature in FEATURE_NAMES:
        spec = PROFILES["legitimate"].get(feature)
        if isinstance(spec, list) and len(spec) == 2:
            stds.append(max(spec[1], 1e-6))
        else:
            stds.append(1.0)
    stds = np.array(stds)

    z_scores = np.abs((attacker_vector - legitimate_vector) / stds)
    flagged_count = int(np.sum(z_scores > 2.5))
    top_5_features = [
        (FEATURE_NAMES[i], float(z_scores[i]))
        for i in np.argsort(z_scores)[::-1][:5]
    ]

    return {
        "scenario":       scenario_id,
        "features_above_2.5_sigma": flagged_count,
        "pass":           flagged_count >= 4,
        "top_deviations": top_5_features,
    }
