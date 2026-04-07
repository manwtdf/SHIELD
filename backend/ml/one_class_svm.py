import numpy as np
import os
import pickle
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from backend.db.models import SessionLocal, Session, User
from backend.ml.feature_schema import FEATURE_NAMES

MODEL_DIR = os.path.join(os.getcwd(), "backend", "ml", "models")

# ── Path helpers: device_class='mobile'|'desktop'|'all'
# 'all' = combined model (fallback when device-specific model missing)

def get_model_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"model_{user_id}_{device_class}.pkl")

def get_scaler_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}_{device_class}.pkl")

def get_metadata_path(user_id: int, device_class: str = "all") -> str:
    return os.path.join(MODEL_DIR, f"metadata_{user_id}_{device_class}.pkl")


def train_model(user_id: int, device_class: str = "all"):
    """
    Train OneClassSVM on user's legitimate sessions.

    device_class:
        'mobile'  — train only on mobile sessions (touch input)
        'desktop' — train only on desktop sessions (mouse input)
        'all'     — train on all sessions regardless of device class (default)
    """
    db = SessionLocal()
    try:
        query = db.query(Session).filter(
            Session.user_id == user_id,
            Session.session_type == "legitimate"
        )

        # Filter by device class when device_class column available
        if device_class != "all":
            query = query.filter(Session.device_class == device_class)

        sessions = query.all()

        if len(sessions) < 5:
            return {"error": f"Not enough sessions for training ({device_class}, min 5, got {len(sessions)})"}

        X = np.array([s.feature_vector_json for s in sessions])

        # Validate feature dimension
        if X.shape[1] != len(FEATURE_NAMES):
            return {"error": f"Feature dimension mismatch: expected {len(FEATURE_NAMES)}, got {X.shape[1]}"}

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = OneClassSVM(kernel="rbf", nu=0.01, gamma="scale")
        model.fit(X_scaled)

        scores = model.decision_function(X_scaled)
        min_score = float(np.min(scores))
        max_score = float(np.max(scores))

        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(get_model_path(user_id, device_class), "wb") as f:
            pickle.dump(model, f)
        with open(get_scaler_path(user_id, device_class), "wb") as f:
            pickle.dump(scaler, f)
        with open(get_metadata_path(user_id, device_class), "wb") as f:
            pickle.dump({"min_score": min_score, "max_score": max_score,
                         "user_id": user_id, "device_class": device_class}, f)

        return {
            "enrolled": True,
            "sessions_used": len(sessions),
            "model_saved": True,
            "device_class": device_class,
        }
    finally:
        db.close()


def predict_score(user_id: int, feature_vector: list, device_class: str = "all") -> int:
    """
    Score feature_vector against trained model.
    Falls back to 'all' model if device-specific model missing
    (e.g. mobile-only enrolled user on desktop for first time).
    """
    if len(feature_vector) != len(FEATURE_NAMES):
        raise ValueError(f"Expected {len(FEATURE_NAMES)} features, got {len(feature_vector)}")

    # Try device-specific model first, fall back to 'all'
    model, scaler, metadata = None, None, None
    for dc in ([device_class, "all"] if device_class != "all" else ["all"]):
        try:
            with open(get_model_path(user_id, dc), "rb") as f:
                model = pickle.load(f)
            with open(get_scaler_path(user_id, dc), "rb") as f:
                scaler = pickle.load(f)
            with open(get_metadata_path(user_id, dc), "rb") as f:
                metadata = pickle.load(f)
            break
        except FileNotFoundError:
            continue

    if model is None:
        return 50  # No model available — neutral score

    X = np.array([feature_vector])
    X_scaled = scaler.transform(X)
    raw_score = model.decision_function(X_scaled)[0]

    min_s = metadata["min_score"]
    max_s = metadata["max_score"]
    score_range = max_s - min_s
    if score_range < 0.01:
        score_range = 1.0

    if raw_score >= -0.01:
        if raw_score >= min_s:
            normalized = 85 + (raw_score - min_s) / (score_range + 1e-6) * 10
        else:
            normalized = 75 + (raw_score / (min_s + 1e-6)) * 10
    else:
        normalized = 60 - (abs(raw_score) / (abs(min_s) + 0.1)) * 40

    return int(max(0, min(100, normalized)))


if __name__ == "__main__":
    # Train all-device model (default)
    res = train_model(1, device_class="all")
    print(res)
