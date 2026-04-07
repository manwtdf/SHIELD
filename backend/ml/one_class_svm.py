import os
import pickle
import datetime
import numpy as np
from sqlalchemy import func
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from backend.db.models import SessionLocal, Session, User, DeviceRegistry
from backend.ml.feature_schema import FEATURE_NAMES

MODEL_DIR = os.path.join(os.getcwd(), "backend", "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURE_DIM = len(FEATURE_NAMES)  # 55


# ─────────────────────────────────────────────
# Path Helpers
# device_class: 'mobile' | 'desktop' | 'all'
# 'all' = combined model; used as fallback when device-specific model missing
# ─────────────────────────────────────────────

def _model_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"model_{user_id}_{device_class}.pkl")

def _scaler_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}_{device_class}.pkl")

def _meta_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"metadata_{user_id}_{device_class}.pkl")


# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────

def train_model(user_id: int, device_class: str = "all") -> dict:
    """
    Train OneClassSVM on user's legitimate sessions.

    device_class:
        'all'     — all sessions regardless of device (run at enrollment, serves as fallback)
        'mobile'  — mobile sessions only (touch features populated)
        'desktop' — desktop sessions only (mouse features populated, touch features = 0.0)

    Saves per-(user_id, device_class):
        model_{uid}_{class}.pkl     — trained SVM
        scaler_{uid}_{class}.pkl    — fitted StandardScaler (55 dims)
        metadata_{uid}_{class}.pkl  — calibration anchors + metadata

    Minimum sessions required: 5
    Feature dimension required: 55 (enforced via FEATURE_DIM guard)
    """
    db = SessionLocal()
    try:
        query = db.query(Session).filter(
            Session.user_id == user_id,
            Session.session_type == "legitimate"
        )

        # Filter by device class when not aggregating all
        if device_class != "all":
            query = query.filter(Session.device_class == device_class)

        sessions = query.all()

        if len(sessions) < 5:
            return {
                "enrolled": False,
                "error": f"Minimum 5 sessions required (device_class={device_class}, got={len(sessions)})"
            }

        # Accept only correctly dimensioned vectors
        X = [
            s.feature_vector_json for s in sessions
            if s.feature_vector_json and len(s.feature_vector_json) == FEATURE_DIM
        ]

        if len(X) < 5:
            return {
                "enrolled": False,
                "error": f"Not enough valid {FEATURE_DIM}-dim feature vectors (got {len(X)})"
            }

        X = np.array(X)

        # Normalize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train — nu=0.01: permits 1% of training points as outliers (permissive)
        model = OneClassSVM(kernel="rbf", nu=0.01, gamma="scale")
        model.fit(X_scaled)

        # Calibration anchors: min/max of decision_function on training set
        raw_scores = model.decision_function(X_scaled)
        min_score  = float(np.min(raw_scores))
        max_score  = float(np.max(raw_scores))

        # Persist
        with open(_model_path(user_id, device_class), "wb") as f:
            pickle.dump(model, f)
        with open(_scaler_path(user_id, device_class), "wb") as f:
            pickle.dump(scaler, f)
        with open(_meta_path(user_id, device_class), "wb") as f:
            pickle.dump({
                "min_score":    min_score,
                "max_score":    max_score,
                "user_id":      user_id,
                "device_class": device_class,
                "sessions_used": len(X),
            }, f)

        # Update enrollment timestamp
        db.query(User).filter(User.id == user_id).update(
            {"enrolled_at": datetime.datetime.utcnow()}
        )
        db.commit()

        return {
            "enrolled":      True,
            "sessions_used": len(X),
            "model_saved":   True,
            "device_class":  device_class,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
# Prediction
# ─────────────────────────────────────────────

def predict_score(
    user_id: int,
    feature_vector: list,
    device_class: str = "all"
) -> int:
    """
    Score feature_vector against trained SVM. Returns 0–100.

    Fallback chain:
        1. model_{uid}_{device_class}.pkl  — device-specific model
        2. model_{uid}_all.pkl             — combined fallback
        3. return 50                       — no model trained yet (neutral)

    Why fallback matters:
        Mobile-enrolled user on desktop for first time has no desktop model.
        Scoring against the 'all' / mobile baseline naturally produces a low score
        because touch features (features 0-15 and 24-31) = 0.0 in the vector,
        producing z-scores of -7 to -9 sigma vs the mobile baseline.
        No manual rule needed — SVM boundary does this automatically.

    Raises ValueError if len(feature_vector) != 55.
    """
    if len(feature_vector) != FEATURE_DIM:
        raise ValueError(f"Expected {FEATURE_DIM} features, got {len(feature_vector)}")

    model, scaler, meta = None, None, None

    search_order = ([device_class, "all"] if device_class != "all" else ["all"])
    for dc in search_order:
        try:
            with open(_model_path(user_id, dc), "rb") as f:
                model = pickle.load(f)
            with open(_scaler_path(user_id, dc), "rb") as f:
                scaler = pickle.load(f)
            with open(_meta_path(user_id, dc), "rb") as f:
                meta = pickle.load(f)
            break
        except FileNotFoundError:
            continue

    if model is None:
        return 50  # No model — neutral

    X = np.array(feature_vector).reshape(1, -1)
    X_scaled    = scaler.transform(X)
    raw_score   = float(model.decision_function(X_scaled)[0])

    min_s       = meta["min_score"]
    max_s       = meta["max_score"]
    score_range = (max_s - min_s) if (max_s - min_s) > 1e-6 else 1e-6

    # Zone-based calibration:
    #   raw >= -0.01 and >= min_s  → deep legitimate  → 85–95
    #   raw >= -0.01 but < min_s   → borderline        → 75–85
    #   raw <  -0.01               → outlier           → 60→0
    if raw_score >= -0.01:
        if raw_score >= min_s:
            calibrated = 85 + ((raw_score - min_s) / score_range) * 10
        else:
            calibrated = 75 + (raw_score / (min_s + 1e-6)) * 10
    else:
        deviation_ratio = abs(raw_score) / (abs(min_s) + 1e-6)
        calibrated = 60 - (deviation_ratio * 40)

    return int(max(0, min(100, calibrated)))


# ─────────────────────────────────────────────
# Device Trust Context Builder
# ─────────────────────────────────────────────

def build_device_context(
    db,
    user_id: int,
    device_fingerprint: str,
    device_class: str
) -> dict:
    """
    Query DeviceRegistry to populate 5 Device Trust Context features.
    Called at POST /session/start before feature vector is assembled.

    Returned dict is used for:
      1. Filling feature vector positions [47:52] (device trust context group)
      2. Passing as device_context= arg to fuse_score()

    Keys:
        device_class_known        int  0|1
        device_session_count      int  0..N
        device_class_switch       int  0|1
        is_known_fingerprint      int  0|1
        time_since_last_seen_hours float

    DeviceRegistry.session_count progression:
        0     → trust_level='new',      is_known_fingerprint=0
        1–2   → trust_level='new',      is_known_fingerprint=0
        >=3   → trust_level='known',    is_known_fingerprint=1
    """
    # Exact fingerprint record
    entry = db.query(DeviceRegistry).filter(
        DeviceRegistry.user_id == user_id,
        DeviceRegistry.device_fingerprint == device_fingerprint
    ).first()

    session_count = entry.session_count if entry else 0
    is_known_fp   = 1 if session_count >= 3 else 0

    # Has user ever used this device class (mobile/desktop/tablet) before?
    class_count = db.query(DeviceRegistry).filter(
        DeviceRegistry.user_id == user_id,
        DeviceRegistry.device_class == device_class
    ).count()
    device_class_known = 1 if class_count > 0 else 0

    # Dominant device class in last 30 days
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    dominant_row = (
        db.query(Session.device_class, func.count(Session.id).label("cnt"))
        .filter(Session.user_id == user_id, Session.started_at >= cutoff)
        .group_by(Session.device_class)
        .order_by(func.count(Session.id).desc())
        .first()
    )
    dominant_class      = dominant_row[0] if dominant_row else "mobile"
    device_class_switch = 1 if dominant_class != device_class else 0

    # Hours since last seen on this exact fingerprint
    hours_since = 0.0
    if entry:
        delta       = datetime.datetime.utcnow() - entry.last_seen
        hours_since = round(delta.total_seconds() / 3600, 1)

    return {
        "device_class_known":         device_class_known,
        "device_session_count":       session_count,
        "device_class_switch":        device_class_switch,
        "is_known_fingerprint":       is_known_fp,
        "time_since_last_seen_hours": hours_since,
    }


if __name__ == "__main__":
    result = train_model(1, device_class="all")
    print(result)
