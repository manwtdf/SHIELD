"""
ml/one_class_svm.py
────────────────────────────────────────────────────────────────────────────────
SHIELD Behavioral Scorer — Mahalanobis Distance Implementation

WHY NOT ONE-CLASS SVM:
  OneClassSVM with RBF kernel on N=10 samples in D=55 dimensions fails because:
  - N << D → decision boundary is arbitrary, not meaningful
  - RBF gamma='scale' = 1/(D * var(X)) → near-zero → near-flat kernel matrix
  - Calibration is nonlinear over a tiny range, magnifying noise into score jumps
  - 5% nu on 10 samples = 0.5 samples → effectively no soft margin

WHY MAHALANOBIS:
  - Directly measures "how many standard deviations away from the mean is this point"
  - Accounts for feature correlations via the covariance matrix
  - Stable with N=10 if we use regularized (shrinkage) covariance
  - Score is proportional by construction: larger deviation = lower confidence
  - Monotonically decreasing: legitimate sessions score ~85-95, attackers ~10-30
  - No hyperparameter tuning required

IMPLEMENTATION:
  score = 100 * exp(-lambda * D_M(x))

  where D_M(x) = sqrt((x - mu)^T * Sigma^-1 * (x - mu))
  and lambda is calibrated so that the mean training distance maps to score=90

  Regularization: Ledoit-Wolf shrinkage on covariance → stable inverse even
  when N < D (reduces to diagonal + off-diagonal shrinkage factor)
"""

import os
import json
import pickle
import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.preprocessing import StandardScaler

from ml.feature_schema import FEATURE_NAMES

MODEL_DIR = os.getenv("MODEL_DIR", "models")
N_FEATURES = len(FEATURE_NAMES)  # 55


# ─────────────────────────────────────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────────────────────────────────────

def _scaler_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}.pkl")

def _cov_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"cov_{user_id}.pkl")

def _meta_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"meta_{user_id}.json")


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────────────────────────────────────

def train(user_id: int, feature_vectors: list[list[float]]) -> dict:
    """
    Fit a regularized Mahalanobis distance scorer on legitimate sessions.

    Steps:
    1. StandardScale the data (mean=0, std=1 per feature)
    2. Fit Ledoit-Wolf shrinkage covariance on scaled data
    3. Compute mean vector (mu) and precision matrix (Sigma^-1)
    4. Compute D_M for each training sample
    5. Find lambda such that mean(D_M_training) → score = 90
    6. Save all artifacts

    Args:
        user_id:         int
        feature_vectors: list of N 55-float lists (legitimate sessions)

    Returns:
        {
            baseline_mean: float,       — mean score on training samples
            baseline_std: float,        — std of training scores
            n_sessions: int,
            per_feature_mean: list[float],   — for anomaly explainer
            per_feature_std:  list[float],   — for anomaly explainer
            lambda: float,              — calibration parameter
            mean_training_distance: float,
        }
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    X = np.array(feature_vectors, dtype=float)  # (N, 55)
    N, D = X.shape

    # ── Step 1: StandardScaler ────────────────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)  # (N, 55), each feature: mean=0 std=1

    # ── Step 2: Regularized covariance via Ledoit-Wolf shrinkage ─────────────
    # Ledoit-Wolf is optimal for N < D: analytically minimizes MSE of covariance
    # estimate, producing a well-conditioned (invertible) matrix even when N << D.
    lw = LedoitWolf(assume_centered=True)  # data is already centered by scaler
    lw.fit(X_scaled)

    # precision_matrix = Sigma^-1 (already computed by LedoitWolf)
    precision_matrix = lw.precision_  # (55, 55)
    mu = np.zeros(D)  # assume_centered=True means mu=0 in scaled space

    # ── Step 3: Compute Mahalanobis distances on training data ───────────────
    training_distances = _mahalanobis_batch(X_scaled, mu, precision_matrix)
    # training_distances: array of shape (N,), each is sqrt(x^T Sigma^-1 x)

    mean_d = float(np.mean(training_distances))
    std_d  = float(np.std(training_distances))

    # ── Step 4: Calibrate lambda ──────────────────────────────────────────────
    # We want: score(mean training point) = 90
    # score = 100 * exp(-lambda * D_M)
    # 90 = 100 * exp(-lambda * mean_d)
    # lambda = -ln(0.90) / mean_d
    target_score = 90.0
    lam = -np.log(target_score / 100.0) / mean_d if mean_d > 0 else 0.01
    lam = float(lam)

    # ── Step 5: Verify training scores ───────────────────────────────────────
    training_scores = [_distance_to_score(d, lam) for d in training_distances]
    baseline_mean = float(np.mean(training_scores))
    baseline_std  = float(np.std(training_scores))

    # ── Step 6: Save artifacts ────────────────────────────────────────────────
    artifacts = {
        "mu": mu.tolist(),
        "precision_matrix": precision_matrix.tolist(),
        "lam": lam,
    }
    with open(_cov_path(user_id), "wb") as f:
        pickle.dump(artifacts, f)
    with open(_scaler_path(user_id), "wb") as f:
        pickle.dump(scaler, f)

    # Per-feature stats for anomaly_explainer (in ORIGINAL space, not scaled)
    per_feature_mean = X.mean(axis=0).tolist()
    per_feature_std  = np.maximum(X.std(axis=0), 1e-6).tolist()

    meta = {
        "baseline_mean": baseline_mean,
        "baseline_std":  baseline_std,
        "n_sessions":    N,
        "lambda":        lam,
        "mean_training_distance": mean_d,
        "std_training_distance":  std_d,
        "per_feature_mean": per_feature_mean,
        "per_feature_std":  per_feature_std,
    }
    with open(_meta_path(user_id), "w") as f:
        json.dump(meta, f, indent=2)

    return meta


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION
# ─────────────────────────────────────────────────────────────────────────────

def predict(user_id: int, feature_vector: list[float]) -> int:
    """
    Predict confidence score for a session feature vector.

    Score interpretation:
      85–100 → legitimate user (within normal behavioral range)
      45–84  → anomalous (step-up or block depending on fusion)
      0–44   → strongly anomalous (block)

    Args:
        user_id:        int
        feature_vector: list[float] len=55

    Returns:
        int — confidence score 0–100

    Raises:
        FileNotFoundError if model not trained
    """
    scaler, artifacts = _load_artifacts(user_id)

    x = np.array(feature_vector, dtype=float).reshape(1, -1)
    x_scaled = scaler.transform(x).flatten()

    mu  = np.array(artifacts["mu"])
    P   = np.array(artifacts["precision_matrix"])
    lam = artifacts["lam"]

    d = _mahalanobis_single(x_scaled, mu, P)
    return _distance_to_score(d, lam)


def predict_batch(user_id: int, feature_vectors: list[list[float]]) -> list[int]:
    """Predict scores for multiple vectors at once. More efficient for scenario runs."""
    scaler, artifacts = _load_artifacts(user_id)

    X = np.array(feature_vectors, dtype=float)
    X_scaled = scaler.transform(X)

    mu  = np.array(artifacts["mu"])
    P   = np.array(artifacts["precision_matrix"])
    lam = artifacts["lam"]

    distances = _mahalanobis_batch(X_scaled, mu, P)
    return [_distance_to_score(d, lam) for d in distances]


# ─────────────────────────────────────────────────────────────────────────────
# METADATA ACCESS
# ─────────────────────────────────────────────────────────────────────────────

def get_baseline_stats(user_id: int) -> dict:
    """
    Returns per-feature mean, std, and model metadata.
    Used by anomaly_explainer for z-score computation.
    """
    with open(_meta_path(user_id), "r") as f:
        return json.load(f)

def model_exists(user_id: int) -> bool:
    return os.path.exists(_cov_path(user_id))


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_artifacts(user_id: int):
    """Returns (scaler, artifacts_dict). Raises FileNotFoundError if missing."""
    with open(_scaler_path(user_id), "rb") as f:
        scaler = pickle.load(f)
    with open(_cov_path(user_id), "rb") as f:
        artifacts = pickle.load(f)
    return scaler, artifacts

def _mahalanobis_single(x: np.ndarray, mu: np.ndarray, precision: np.ndarray) -> float:
    """
    Compute Mahalanobis distance for a single scaled vector.
    D_M = sqrt((x - mu)^T * Precision * (x - mu))
    """
    diff = x - mu
    return float(np.sqrt(diff @ precision @ diff))

def _mahalanobis_batch(X: np.ndarray, mu: np.ndarray, precision: np.ndarray) -> np.ndarray:
    """
    Vectorized Mahalanobis for a batch of scaled vectors.
    Returns array of shape (N,).
    """
    diff = X - mu                          # (N, D)
    left = diff @ precision                # (N, D)
    sq   = np.sum(left * diff, axis=1)     # (N,) — elementwise product then sum
    sq   = np.maximum(sq, 0.0)             # numerical safety: avoid sqrt of -epsilon
    return np.sqrt(sq)

def _distance_to_score(distance: float, lam: float) -> int:
    """
    Convert Mahalanobis distance to 0–100 confidence score.

    score = 100 * exp(-lambda * distance)

    Properties:
      - distance=0 (identical to mean) → score=100
      - distance=mean_training → score=90 (by calibration)
      - distance → ∞ → score → 0
      - Monotonically decreasing: larger deviation = lower confidence
      - No clipping needed: exp output is always in (0, 100]
    """
    score = 100.0 * np.exp(-lam * distance)
    return int(round(np.clip(score, 0, 100)))


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS (call from seed_runner.py to verify calibration)
# ─────────────────────────────────────────────────────────────────────────────

def diagnostic_report(user_id: int, legitimate_vectors: list[list[float]],
                       attacker_vectors: dict[str, list[float]]) -> dict:
    """
    Runs all vectors through the trained model and returns a calibration report.
    Call this from seed_runner.py after training to verify score ranges.

    Args:
        legitimate_vectors: list of 10 legitimate feature vectors
        attacker_vectors:   {"scenario_1": [...], "scenario_2": [...], ...}

    Returns dict with per-scenario score summaries.
    """
    legit_scores = predict_batch(user_id, legitimate_vectors)

    report = {
        "legitimate": {
            "scores": legit_scores,
            "mean":   float(np.mean(legit_scores)),
            "min":    int(np.min(legit_scores)),
            "max":    int(np.max(legit_scores)),
            "all_above_75": all(s >= 75 for s in legit_scores),
        },
        "attackers": {}
    }

    for scenario_key, vector in attacker_vectors.items():
        score = predict(user_id, vector)
        report["attackers"][scenario_key] = {"score": score}

    return report
