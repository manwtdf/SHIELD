# SHIELD -- Backend Implementation Plan
## Session-based Heuristic Intelligence for Event Level Defense

> This document is the complete implementation guide for the SHIELD backend.
> It is ordered by execution sequence. Every function, every file, every schema
> is specified completely enough to implement without additional context.
> Cross-reference README.md for system architecture and CLAUDE.md for phase gates.

---

## 0. BACKEND AT A GLANCE

```
backend/
├── main.py                    ← FastAPI app entry point
├── requirements.txt
│
├── routers/                   ← HTTP layer only -- no business logic here
│   ├── session.py
│   ├── score.py
│   ├── enroll.py
│   ├── sim_swap.py
│   ├── alert.py
│   ├── scenarios.py
│   ├── features.py
│   └── fleet.py
│
├── ml/                        ← All ML logic -- no HTTP here
│   ├── feature_schema.py
│   ├── one_class_svm.py
│   ├── lstm_autoencoder.py
│   ├── score_fusion.py
│   ├── fleet_anomaly.py
│   └── anomaly_explainer.py
│
├── data/                      ← Seed data generators
│   ├── seed_legitimate.py
│   ├── seed_scenarios.py
│   └── profiles.json
│
├── db/                        ← Database only
│   ├── database.py
│   └── models.py
│
├── utils/
│   ├── twilio_client.py
│   └── scoring.py
│
├── models/                    ← Auto-created. Stores .pkl files
│   └── .gitkeep
│
└── tests/
    ├── test_model.py
    ├── test_routes.py
    └── test_scenarios.py
```

**Rule:** Routers call services. Services call ML. ML calls DB. Nothing calls in reverse.
No business logic in routers. No HTTP in ML files.

---

## 1. SETUP FILES

### 1.1 `requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
sqlalchemy==2.0.30
scikit-learn==1.4.2
torch==2.3.0
numpy==1.26.4
scipy==1.13.0
pandas==2.2.2
twilio==9.0.4
python-dotenv==1.0.1
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.6
```

### 1.2 `main.py`

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db.database import init_db
from routers import session, score, enroll, sim_swap, alert, scenarios, features, fleet

load_dotenv()

app = FastAPI(
    title="SHIELD API",
    description="Session-based Heuristic Intelligence for Event Level Defense",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(session.router,   prefix="/session",    tags=["Session"])
app.include_router(score.router,     prefix="/score",      tags=["Score"])
app.include_router(enroll.router,    prefix="/enroll",     tags=["Enrollment"])
app.include_router(sim_swap.router,  prefix="/sim-swap",   tags=["SIM Swap"])
app.include_router(alert.router,     prefix="/alert",      tags=["Alerts"])
app.include_router(scenarios.router, prefix="/scenarios",  tags=["Scenarios"])
app.include_router(features.router,  prefix="/features",   tags=["Features"])
app.include_router(fleet.router,     prefix="/fleet",      tags=["Fleet"])

@app.on_event("startup")
async def startup():
    init_db()
    os.makedirs("models", exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok", "service": "SHIELD"}
```

---

## 2. DATABASE LAYER

### 2.1 `db/database.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = os.getenv("DB_PATH", "shield.db")
ENGINE = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def init_db():
    from db.models import User, Session, Score, SimSwapEvent, AlertLog, DeviceRegistry
    Base.metadata.create_all(bind=ENGINE)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.2 `db/models.py`

Implement all 6 tables. Every column, every type, every constraint specified:

```python
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, func
)
from db.database import Base

def new_uuid() -> str:
    return str(uuid.uuid4())

# ─────────────────────────────────────────────────────────────
# TABLE 1: users
# ─────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(100), nullable=False)
    enrolled_at    = Column(DateTime, nullable=True)       # set on first enrollment
    sessions_count = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────────────────────────
# TABLE 2: sessions
# ─────────────────────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    id             = Column(String(36), primary_key=True, default=new_uuid)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at     = Column(DateTime, default=datetime.utcnow)
    session_type   = Column(String(30), nullable=False)
    # Valid values:
    #   "legitimate"
    #   "scenario_1" through "scenario_6"
    #   "auto"  (from ?demo=auto mode)
    feature_vector = Column(Text, nullable=True)           # JSON: list[float] len=47
    completed      = Column(Boolean, default=False)
    completed_at   = Column(DateTime, nullable=True)

# ─────────────────────────────────────────────────────────────
# TABLE 3: scores
# ─────────────────────────────────────────────────────────────
class Score(Base):
    __tablename__ = "scores"

    id               = Column(String(36), primary_key=True, default=new_uuid)
    session_id       = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    computed_at      = Column(DateTime, default=datetime.utcnow)
    snapshot_index   = Column(Integer, nullable=False)     # 1–5
    confidence_score = Column(Integer, nullable=False)     # 0–100
    risk_level       = Column(String(10), nullable=False)  # LOW|MEDIUM|HIGH|CRITICAL
    action           = Column(String(20), nullable=False)  # ALLOW|STEP_UP|BLOCK|BLOCK_AND_FREEZE
    top_anomalies    = Column(Text, nullable=True)         # JSON: list[str] len=4

# ─────────────────────────────────────────────────────────────
# TABLE 4: sim_swap_events
# ─────────────────────────────────────────────────────────────
class SimSwapEvent(Base):
    __tablename__ = "sim_swap_events"

    id           = Column(String(36), primary_key=True, default=new_uuid)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    is_active    = Column(Boolean, default=True)
    cleared_at   = Column(DateTime, nullable=True)

# ─────────────────────────────────────────────────────────────
# TABLE 5: alert_log
# ─────────────────────────────────────────────────────────────
class AlertLog(Base):
    __tablename__ = "alert_log"

    id          = Column(String(36), primary_key=True, default=new_uuid)
    session_id  = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    alert_type  = Column(String(10), nullable=False)       # SMS | LOG
    sent_at     = Column(DateTime, default=datetime.utcnow)
    recipient   = Column(String(50), nullable=False)
    message     = Column(Text, nullable=False)
    message_sid = Column(String(50), nullable=True)        # Twilio SID if SMS

# ─────────────────────────────────────────────────────────────
# TABLE 6: device_registry
# ─────────────────────────────────────────────────────────────
class DeviceRegistry(Base):
    __tablename__ = "device_registry"

    id                 = Column(String(36), primary_key=True, default=new_uuid)
    user_id            = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_fingerprint = Column(String(64), nullable=False, index=True)
    first_seen         = Column(DateTime, default=datetime.utcnow)
    last_seen          = Column(DateTime, default=datetime.utcnow)
    is_trusted         = Column(Boolean, default=True)
```

---

## 3. ML LAYER

Build all ML files before touching routers. Routers depend on ML. ML does not depend on routers.

### 3.1 `ml/feature_schema.py`

```python
# Single source of truth for all 47 features.
# Import FEATURE_NAMES everywhere. Never hardcode feature names elsewhere.

FEATURE_NAMES: list[str] = [
    # ── Touch Dynamics (8) ──────────────────────────────────
    "tap_pressure_mean",
    "tap_pressure_std",
    "swipe_velocity_mean",
    "swipe_velocity_std",
    "gesture_curvature_mean",
    "pinch_zoom_accel_mean",
    "tap_duration_mean",
    "tap_duration_std",
    # ── Typing Biometrics (10) ──────────────────────────────
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
    # ── Device Motion (8) ───────────────────────────────────
    "accel_x_std",
    "accel_y_std",
    "accel_z_std",
    "gyro_x_std",
    "gyro_y_std",
    "gyro_z_std",
    "device_tilt_mean",
    "hand_stability_score",
    # ── Navigation Graph (9) ────────────────────────────────
    "screens_visited_count",
    "navigation_depth_max",
    "back_navigation_count",
    "time_on_dashboard_ms",
    "time_on_transfer_ms",
    "direct_to_transfer",
    "form_field_order_entropy",
    "session_revisit_count",
    "exploratory_ratio",
    # ── Temporal Behavior (8) ───────────────────────────────
    "session_duration_ms",
    "session_duration_z_score",
    "time_of_day_hour",
    "time_to_submit_otp_ms",
    "click_speed_mean",
    "click_speed_std",
    "form_submit_speed_ms",
    "interaction_pace_ratio",
    # ── Device Context (4) ──────────────────────────────────
    "is_new_device",
    "device_fingerprint_delta",
    "timezone_changed",
    "os_version_changed",
]

assert len(FEATURE_NAMES) == 47, f"Expected 47 features, got {len(FEATURE_NAMES)}"

FEATURE_INDEX: dict[str, int] = {name: i for i, name in enumerate(FEATURE_NAMES)}

# Feature groups -- used by anomaly_explainer to contextualize z-scores
FEATURE_GROUPS: dict[str, list[str]] = {
    "touch":      FEATURE_NAMES[0:8],
    "typing":     FEATURE_NAMES[8:18],
    "motion":     FEATURE_NAMES[18:26],
    "navigation": FEATURE_NAMES[26:35],
    "temporal":   FEATURE_NAMES[35:43],
    "device":     FEATURE_NAMES[43:47],
}

def dict_to_vector(feature_dict: dict[str, float]) -> list[float]:
    """
    Convert a partial or complete feature dict to a 47-length list.
    Missing features default to 0.0. Used for partial snapshot scoring.
    """
    return [float(feature_dict.get(name, 0.0)) for name in FEATURE_NAMES]

def vector_to_dict(vector: list[float]) -> dict[str, float]:
    assert len(vector) == 47
    return {name: vector[i] for i, name in enumerate(FEATURE_NAMES)}
```

### 3.2 `ml/one_class_svm.py`

```python
import os
import json
import pickle
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from ml.feature_schema import FEATURE_NAMES, dict_to_vector
One-Class SVM (Primary for demo)
Algorithm: sklearn.svm.OneClassSVM
Nu: 0.01 (1% outlier sensitivity)
Platt Scaling: Calibrates raw decision function to 0-100 range
Training: 10 legitimate sessions per user
Storage: 2 pickle files per user (model.pkl, scaler.pkl)
Inference: < 1ms on CPU

MODEL_DIR = os.getenv("MODEL_DIR", "models")

# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────

def _model_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"model_{user_id}.pkl")

def _scaler_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"scaler_{user_id}.pkl")

def _meta_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"meta_{user_id}.json")

def _calibration_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"calibration_{user_id}.pkl")

def _load_artifacts(user_id: int):
    """Returns (model, scaler, calibration_params) or raises FileNotFoundError."""
    with open(_model_path(user_id), "rb") as f:
        model = pickle.load(f)
    with open(_scaler_path(user_id), "rb") as f:
        scaler = pickle.load(f)
    with open(_calibration_path(user_id), "rb") as f:
        calibration = pickle.load(f)
    return model, scaler, calibration

# ─────────────────────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────────────────────

def train(user_id: int, feature_vectors: list[list[float]]) -> dict:
    """
    Train One-Class SVM on legitimate session feature vectors.

    Args:
        user_id:         int -- used for model file naming
        feature_vectors: list of 47-float lists, one per legitimate session

    Returns:
        {
            "baseline_mean": float,   -- mean score on training data
            "baseline_std":  float,   -- std of scores on training data
            "n_sessions":    int,
            "per_feature_mean": list[float],  -- used by anomaly_explainer
            "per_feature_std":  list[float],
        }
    """
    os.makedirs(MODEL_DIR, exist_ok=True)
    X = np.array(feature_vectors, dtype=float)  # shape (n, 47)

    # Step 1: Fit scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Step 2: Train One-Class SVM
    svm = OneClassSVM(kernel="rbf", nu=float(os.getenv("SVM_NU", "0.05")), gamma="scale")
    svm.fit(X_scaled)

    # Step 3: Calibrate raw decision_function scores to [0, 100]
    # Raw scores: negative = outlier, positive = inlier
    raw_scores = svm.decision_function(X_scaled)

    # Min-max normalize to [0,1] then invert (high raw = inlier = high confidence)
    raw_min = float(raw_scores.min())
    raw_max = float(raw_scores.max())
    # Extend range slightly so attacker scores have room below 0
    raw_min_extended = raw_min - (raw_max - raw_min) * 2.0

    calibration = {"raw_min": raw_min_extended, "raw_max": raw_max}

    # Step 4: Verify calibration hits target range (85–95 for legitimate sessions)
    calibrated_scores = [_calibrate(s, calibration) for s in raw_scores]
    baseline_mean = float(np.mean(calibrated_scores))
    baseline_std = float(np.std(calibrated_scores))

    # Step 5: Save all artifacts
    with open(_model_path(user_id), "wb") as f:
        pickle.dump(svm, f)
    with open(_scaler_path(user_id), "wb") as f:
        pickle.dump(scaler, f)
    with open(_calibration_path(user_id), "wb") as f:
        pickle.dump(calibration, f)

    # Step 6: Save per-feature stats for anomaly_explainer
    per_feature_mean = X.mean(axis=0).tolist()
    per_feature_std = X.std(axis=0).tolist()
    per_feature_std = [max(s, 1e-6) for s in per_feature_std]  # avoid division by zero

    meta = {
        "baseline_mean": baseline_mean,
        "baseline_std": baseline_std,
        "n_sessions": len(feature_vectors),
        "per_feature_mean": per_feature_mean,
        "per_feature_std": per_feature_std,
    }
    with open(_meta_path(user_id), "w") as f:
        json.dump(meta, f)

    return meta

# ─────────────────────────────────────────────────────────────
# PREDICTION
# ─────────────────────────────────────────────────────────────

def predict(user_id: int, feature_vector: list[float]) -> int:
    """
    Predict confidence score for a session.

    Args:
        user_id:        int
        feature_vector: list[float] len=47 (zeros for unrevealed features)

    Returns:
        int -- confidence score 0–100
        (high = legitimate, low = anomalous/attacker)

    Raises:
        FileNotFoundError if model not trained yet
    """
    model, scaler, calibration = _load_artifacts(user_id)

    X = np.array(feature_vector, dtype=float).reshape(1, -1)
    X_scaled = scaler.transform(X)
    raw_score = float(model.decision_function(X_scaled)[0])

    return _calibrate(raw_score, calibration)

def _calibrate(raw_score: float, calibration: dict) -> int:
    """Convert raw SVM score to 0–100 integer. High = legitimate."""
    raw_min = calibration["raw_min"]
    raw_max = calibration["raw_max"]
    normalized = (raw_score - raw_min) / (raw_max - raw_min)
    clamped = max(0.0, min(1.0, normalized))
    return int(round(clamped * 100))

# ─────────────────────────────────────────────────────────────
# METADATA ACCESS
# ─────────────────────────────────────────────────────────────

def get_baseline_stats(user_id: int) -> dict:
    """
    Returns per-feature mean and std from training data.
    Used by anomaly_explainer for z-score computation.
    Raises FileNotFoundError if model not trained.
    """
    with open(_meta_path(user_id), "r") as f:
        return json.load(f)

def model_exists(user_id: int) -> bool:
    return os.path.exists(_model_path(user_id))
```

### 3.3 `ml/score_fusion.py`

```python
import os

BLOCK_THRESHOLD  = int(os.getenv("SCORE_BLOCK_THRESHOLD", "30"))
STEPUP_THRESHOLD = int(os.getenv("SCORE_STEPUP_THRESHOLD", "45"))

def fuse_score(behavior_score: int, sim_swap_active: bool) -> dict:
    """
    Apply SIM swap signal fusion + risk classification.

    Fusion rules applied in strict priority order:

    Priority 1: SIM swap active AND score < 45
        → score = min(behavior_score, 25), CRITICAL, BLOCK_AND_FREEZE

    Priority 2: SIM swap active (any score)
        → score = int(behavior_score * 0.6), then re-classify

    Priority 3: score < 30  → CRITICAL, BLOCK_AND_FREEZE
    Priority 4: score < 45  → HIGH,     BLOCK_TRANSACTION
    Priority 5: score < 70  → MEDIUM,   STEP_UP_AUTH
    Priority 6: else         → LOW,      ALLOW

    Returns:
        {
            "final_score": int,
            "risk_level":  str,   # LOW | MEDIUM | HIGH | CRITICAL
            "action":      str,   # ALLOW | STEP_UP_AUTH | BLOCK_TRANSACTION | BLOCK_AND_FREEZE
        }
    """
    score = behavior_score

    # Priority 1
    if sim_swap_active and score < STEPUP_THRESHOLD:
        score = min(score, 25)
        return {"final_score": score, "risk_level": "CRITICAL", "action": "BLOCK_AND_FREEZE"}

    # Priority 2
    if sim_swap_active:
        score = int(score * 0.6)

    # Classify on final score
    return _classify(score)

def _classify(score: int) -> dict:
    if score < BLOCK_THRESHOLD:
        return {"final_score": score, "risk_level": "CRITICAL", "action": "BLOCK_AND_FREEZE"}
    elif score < STEPUP_THRESHOLD:
        return {"final_score": score, "risk_level": "HIGH",     "action": "BLOCK_TRANSACTION"}
    elif score < 70:
        return {"final_score": score, "risk_level": "MEDIUM",   "action": "STEP_UP_AUTH"}
    else:
        return {"final_score": score, "risk_level": "LOW",      "action": "ALLOW"}
```

### 3.4 `ml/anomaly_explainer.py`

```python
import numpy as np
from ml.feature_schema import FEATURE_NAMES

# ─────────────────────────────────────────────────────────────
# HUMAN-READABLE TEMPLATES
# One template per feature. {direction}, {pct}, {value}, {hour}, {typical}
# are filled at runtime.
# ─────────────────────────────────────────────────────────────
TEMPLATES: dict[str, str] = {
    "inter_key_delay_mean":      "Typing speed {direction} {pct}% from user baseline",
    "inter_key_delay_std":       "Typing rhythm variance {direction} {pct}% -- inconsistent keypresses",
    "inter_key_delay_p95":       "Peak typing delay {direction} {pct}% above normal",
    "dwell_time_mean":           "Key hold duration {direction} {pct}% from baseline",
    "dwell_time_std":            "Key hold variance {direction} -- possible manual hesitation",
    "error_rate":                "Typing error rate {direction} {pct}% -- {direction_text}",
    "backspace_frequency":       "Backspace use {direction} {pct}% from baseline",
    "typing_burst_count":        "Typing burst count {direction} -- possible single-burst automation",
    "words_per_minute":          "Input speed {direction} {pct}% from enrolled baseline",
    "tap_pressure_mean":         "Touch pressure {direction} {pct}% from baseline",
    "tap_pressure_std":          "Touch pressure variance {direction} -- unusual hand behavior",
    "swipe_velocity_mean":       "Swipe speed {direction} {pct}% -- possible non-touch device",
    "swipe_velocity_std":        "Swipe speed variance {direction} -- unfamiliar device handling",
    "gesture_curvature_mean":    "Gesture path curvature {direction} from enrolled pattern",
    "pinch_zoom_accel_mean":     "Pinch-zoom behavior {direction} -- gesture pattern mismatch",
    "tap_duration_mean":         "Tap duration {direction} {pct}% from baseline",
    "tap_duration_std":          "Tap duration variance elevated -- possible non-human input",
    "hand_stability_score":      "Device stability {direction} {pct}% -- motion pattern mismatch",
    "accel_x_std":               "X-axis accelerometer variance {direction} during session",
    "accel_y_std":               "Y-axis accelerometer variance {direction} during session",
    "accel_z_std":               "Z-axis accelerometer variance {direction} during session",
    "gyro_x_std":                "Gyroscope X-axis variance {direction} -- unusual device orientation",
    "gyro_y_std":                "Gyroscope Y-axis variance {direction}",
    "gyro_z_std":                "Gyroscope Z-axis variance {direction}",
    "device_tilt_mean":          "Device tilt angle {direction} {pct}% from enrolled posture",
    "screens_visited_count":     "Screen count {direction} {pct}% -- {direction_text} exploration",
    "navigation_depth_max":      "Navigation depth {direction} from typical session pattern",
    "back_navigation_count":     "Back-navigation count {direction} {pct}% -- {direction_text}",
    "time_on_dashboard_ms":      "Dashboard dwell time {direction} {pct}% -- {direction_text}",
    "time_on_transfer_ms":       "Transfer screen dwell {direction} {pct}% from baseline",
    "direct_to_transfer":        "Navigated directly to transfer -- atypical for this user",
    "form_field_order_entropy":  "Form completion order atypical -- possible automated input",
    "session_revisit_count":     "Screen revisit count {direction} {pct}%",
    "exploratory_ratio":         "Navigation {direction} {pct}% more exploratory than normal",
    "session_duration_ms":       "Session {direction} {pct}% than user average -- {direction_text}",
    "session_duration_z_score":  "Session duration z-score {direction} -- statistical outlier",
    "time_of_day_hour":          "Login at {value:.0f}:00 -- outside user's typical hours",
    "time_to_submit_otp_ms":     "OTP submitted {pct}% {direction} than user average",
    "click_speed_mean":          "Click speed {direction} {pct}% from baseline",
    "click_speed_std":           "Click timing variance {direction} -- possible automation",
    "form_submit_speed_ms":      "Form submission speed {direction} {pct}% -- {direction_text}",
    "interaction_pace_ratio":    "Interaction pace {direction} {pct}% -- {direction_text}",
    "is_new_device":             "Device fingerprint unknown -- never seen for this account",
    "device_fingerprint_delta":  "Device fingerprint similarity {direction} -- likely different hardware",
    "timezone_changed":          "Timezone differs from last 5 sessions -- location anomaly",
    "os_version_changed":        "OS version changed since last session",
    # SIM swap always appended last when active:
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
    Compute z-scores for all 47 features.
    Return the top n-1 anomalies as human-readable strings.
    If sim_swap_active: always include SIM_SWAP as the nth entry.

    Args:
        feature_vector:    list[float] len=47
        per_feature_mean:  list[float] len=47 -- from get_baseline_stats()
        per_feature_std:   list[float] len=47 -- from get_baseline_stats()
        sim_swap_active:   bool
        sim_swap_minutes:  int -- minutes since SIM swap triggered
        n:                 int -- total anomalies to return (default 4)

    Returns:
        list[str] len=n
    """
    fv = np.array(feature_vector)
    mu = np.array(per_feature_mean)
    sigma = np.array(per_feature_std)

    # z-score per feature
    z_scores = (fv - mu) / sigma  # shape (47,)

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

        # Skip binary features that are at baseline
        if feature_name in ("is_new_device", "timezone_changed", "os_version_changed",
                             "direct_to_transfer") and value == baseline:
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

def _format_anomaly(feature_name: str, z: float, value: float, baseline: float) -> str:
    """Format a single anomaly string using the template for this feature."""
    template = TEMPLATES.get(feature_name, "Feature {f} deviates from baseline (z={z:.1f})")

    direction = "higher" if z > 0 else "lower"
    pct = int(abs((value - baseline) / max(abs(baseline), 1e-6)) * 100)
    direction_text = {
        "higher": "unusual increase",
        "lower":  "unusual decrease",
    }[direction]

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
    )

def get_z_scores(
    feature_vector: list[float],
    per_feature_mean: list[float],
    per_feature_std: list[float],
) -> list[dict]:
    """
    Return z-score info for all 47 features.
    Used by GET /features/inspect/{session_id}.
    """
    fv = np.array(feature_vector)
    mu = np.array(per_feature_mean)
    sigma = np.array(per_feature_std)
    z_scores = (fv - mu) / sigma

    return [
        {
            "name":     FEATURE_NAMES[i],
            "value":    float(fv[i]),
            "baseline": float(mu[i]),
            "z_score":  float(z_scores[i]),
            "flagged":  abs(float(z_scores[i])) > 2.5,
        }
        for i in range(47)
    ]
```

### 3.5 `ml/fleet_anomaly.py`

```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from db.models import DeviceRegistry, User

FLEET_WINDOW_MINUTES = 60
FLEET_THRESHOLD      = 2   # ≥ 2 distinct accounts = fleet anomaly

def check_fleet_anomaly(
    db: DBSession,
    device_fingerprint: str,
    current_user_id: int,
) -> dict:
    """
    Check if this device fingerprint has been seen on ≥ FLEET_THRESHOLD
    distinct user accounts within the last FLEET_WINDOW_MINUTES minutes.

    Args:
        db:                 SQLAlchemy session
        device_fingerprint: str -- hash of device characteristics
        current_user_id:    int -- current session's user

    Returns:
        {
            "fleet_anomaly":    bool,
            "accounts_seen":    int,
            "affected_user_ids": list[int],
            "action":           str,   # "FREEZE_ALL_ACCOUNTS" | "ALLOW"
        }
    """
    cutoff = datetime.utcnow() - timedelta(minutes=FLEET_WINDOW_MINUTES)

    recent_entries = (
        db.query(DeviceRegistry)
        .filter(
            DeviceRegistry.device_fingerprint == device_fingerprint,
            DeviceRegistry.last_seen >= cutoff,
        )
        .all()
    )

    seen_user_ids = list({entry.user_id for entry in recent_entries})

    # Register current device
    _register_device(db, device_fingerprint, current_user_id)

    if current_user_id not in seen_user_ids:
        seen_user_ids.append(current_user_id)

    accounts_seen = len(seen_user_ids)
    fleet_anomaly = accounts_seen >= FLEET_THRESHOLD

    return {
        "fleet_anomaly":     fleet_anomaly,
        "accounts_seen":     accounts_seen,
        "affected_user_ids": seen_user_ids,
        "action":            "FREEZE_ALL_ACCOUNTS" if fleet_anomaly else "ALLOW",
    }

def _register_device(db: DBSession, fingerprint: str, user_id: int) -> None:
    """Upsert device fingerprint into registry."""
    existing = (
        db.query(DeviceRegistry)
        .filter_by(device_fingerprint=fingerprint, user_id=user_id)
        .first()
    )
    if existing:
        existing.last_seen = datetime.utcnow()
    else:
        db.add(DeviceRegistry(
            user_id=user_id,
            device_fingerprint=fingerprint,
            is_trusted=False,
        ))
    db.commit()
```

### 3.6 `ml/lstm_autoencoder.py`

```python
# LSTM Autoencoder -- production upgrade path.
# Demo: show this as a slide, not in live inference.
# Implement as a runnable script, not called during demo.

import torch
import torch.nn as nn
import numpy as np

class BehaviorAutoencoder(nn.Module):
    """
    LSTM Autoencoder for behavioral time-series anomaly detection.
    Input:  (batch, seq_len, 47) -- sequence of feature snapshots per session
    Output: reconstruction of input -- anomaly score = MSE reconstruction error
    """
    def __init__(self, input_dim: int = 47, hidden_dim: int = 32, latent_dim: int = 16):
        super().__init__()
        self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.hidden_to_latent = nn.Linear(hidden_dim, latent_dim)
        self.latent_to_hidden = nn.Linear(latent_dim, hidden_dim)
        self.decoder = nn.LSTM(hidden_dim, input_dim, batch_first=True)

    def forward(self, x: torch.Tensor):
        # x: (batch, seq, 47)
        enc_out, (h, _) = self.encoder(x)
        latent = self.hidden_to_latent(h[-1])              # (batch, latent_dim)
        hidden_init = self.latent_to_hidden(latent)        # (batch, hidden_dim)
        hidden_init = hidden_init.unsqueeze(0)             # (1, batch, hidden_dim)
        dec_in = torch.zeros_like(x)
        dec_out, _ = self.decoder(dec_in, (hidden_init, torch.zeros_like(hidden_init)))
        return dec_out                                     # (batch, seq, 47)

def anomaly_score(model: BehaviorAutoencoder, session_snapshots: list[list[float]]) -> float:
    """
    Compute reconstruction error for a session.
    Higher error = more anomalous.
    Args:
        session_snapshots: list of 47-float lists, one per snapshot (usually 5)
    Returns:
        float -- mean squared reconstruction error
    """
    x = torch.tensor([session_snapshots], dtype=torch.float32)  # (1, 5, 47)
    model.eval()
    with torch.no_grad():
        reconstructed = model(x)
    mse = ((x - reconstructed) ** 2).mean().item()
    return mse
```

---

## 4. DATA SEEDING

### 4.1 `data/profiles.json`

Create this file with behavioral distribution params for all scenarios.
Structure: each key is a scenario ID or "legitimate", value is a dict of
`feature_name → [mean, std]` for continuous features or a scalar for fixed values.

```json
{
  "legitimate": {
    "inter_key_delay_mean": [180, 15],
    "inter_key_delay_std": [25, 5],
    "inter_key_delay_p95": [280, 20],
    "dwell_time_mean": [95, 8],
    "dwell_time_std": [12, 3],
    "error_rate": [0.04, 0.01],
    "backspace_frequency": [2.1, 0.5],
    "typing_burst_count": [4, 1],
    "typing_burst_duration_mean": [3200, 400],
    "words_per_minute": [38, 4],
    "tap_pressure_mean": [0.55, 0.06],
    "tap_pressure_std": [0.08, 0.02],
    "swipe_velocity_mean": [450, 30],
    "swipe_velocity_std": [60, 10],
    "gesture_curvature_mean": [0.12, 0.03],
    "pinch_zoom_accel_mean": [0.22, 0.04],
    "tap_duration_mean": [145, 15],
    "tap_duration_std": [30, 8],
    "accel_x_std": [0.18, 0.03],
    "accel_y_std": [0.21, 0.04],
    "accel_z_std": [0.15, 0.03],
    "gyro_x_std": [0.08, 0.02],
    "gyro_y_std": [0.09, 0.02],
    "gyro_z_std": [0.07, 0.02],
    "device_tilt_mean": [72, 5],
    "hand_stability_score": [0.82, 0.05],
    "screens_visited_count": [6, 1],
    "navigation_depth_max": [4, 1],
    "back_navigation_count": [1.2, 0.5],
    "time_on_dashboard_ms": [45000, 8000],
    "time_on_transfer_ms": [28000, 5000],
    "direct_to_transfer": 0.15,
    "form_field_order_entropy": [0.12, 0.04],
    "session_revisit_count": [0.8, 0.4],
    "exploratory_ratio": [0.08, 0.02],
    "session_duration_ms": [240000, 30000],
    "session_duration_z_score": [0.0, 1.0],
    "time_of_day_hour_choices": [9, 10, 18, 19, 20],
    "time_to_submit_otp_ms": [8500, 2000],
    "click_speed_mean": [380, 40],
    "click_speed_std": [95, 20],
    "form_submit_speed_ms": [42000, 6000],
    "interaction_pace_ratio": [1.0, 0.12],
    "is_new_device": 0,
    "device_fingerprint_delta": [0.05, 0.01],
    "timezone_changed": 0,
    "os_version_changed": 0
  },
  "scenario_1": {
    "inter_key_delay_mean": [310, 60],
    "inter_key_delay_std": [90, 20],
    "inter_key_delay_p95": [520, 80],
    "dwell_time_mean": [140, 30],
    "error_rate": [0.08, 0.02],
    "typing_burst_count": [2, 1],
    "words_per_minute": [22, 5],
    "swipe_velocity_mean": [280, 80],
    "hand_stability_score": [0.51, 0.10],
    "session_duration_ms": [95000, 10000],
    "time_of_day_hour_choices": [2, 3],
    "direct_to_transfer": 1,
    "exploratory_ratio": [0.35, 0.08],
    "time_to_submit_otp_ms": [2100, 300],
    "interaction_pace_ratio": [1.8, 0.2],
    "is_new_device": 1,
    "device_fingerprint_delta": [0.94, 0.03]
  },
  "scenario_2": {
    "inter_key_delay_mean": [145, 20],
    "swipe_velocity_mean": 0,
    "tap_pressure_mean": 0,
    "tap_duration_mean": 0,
    "form_field_order_entropy": [0.85, 0.10],
    "session_duration_ms": [110000, 15000],
    "time_of_day_hour_choices": [1, 2, 3],
    "direct_to_transfer": 1,
    "is_new_device": 1,
    "device_fingerprint_delta": [0.97, 0.02],
    "exploratory_ratio": [0.28, 0.07],
    "time_to_submit_otp_ms": [3200, 500]
  },
  "scenario_3": {
    "inter_key_delay_mean": [42, 2],
    "inter_key_delay_std": [1.5, 0.3],
    "click_speed_std": [0.8, 0.2],
    "time_to_submit_otp_ms": [800, 50],
    "interaction_pace_ratio": [0.05, 0.01],
    "typing_burst_count": 1,
    "error_rate": 0,
    "direct_to_transfer": 1,
    "session_duration_ms": [45000, 3000],
    "exploratory_ratio": [0.01, 0.005],
    "is_new_device": 1,
    "words_per_minute": [95, 3]
  },
  "scenario_4": {
    "inter_key_delay_mean": [210, 35],
    "session_duration_ms": [95000, 8000],
    "direct_to_transfer": 1,
    "time_of_day_hour_choices": [3, 4],
    "time_to_submit_otp_ms": [3800, 600],
    "exploratory_ratio": [0.18, 0.05],
    "is_new_device": 0,
    "device_fingerprint_delta": [0.08, 0.02],
    "hand_stability_score": [0.71, 0.08]
  },
  "scenario_5": {
    "inter_key_delay_mean": [290, 55],
    "is_new_device": 1,
    "device_fingerprint_delta": [0.91, 0.03],
    "direct_to_transfer": 1,
    "time_to_submit_otp_ms": [1800, 200],
    "session_duration_ms": [75000, 8000],
    "FLEET_FINGERPRINT": "ATTACKER_DEVICE_FLEET_001"
  },
  "scenario_6": {
    "PRE_AUTH": true,
    "sms_balance_queries": 3,
    "ivr_calls": 2,
    "query_window_seconds": 120
  }
}
```

### 4.2 `data/seed_legitimate.py`

```python
"""
Generates 10 legitimate sessions for user_id=1.
Reads params from profiles.json["legitimate"].
Each session: 47-float vector drawn from the distributions.
Adds ±8% within-person variance (published behavioral biometrics literature).
"""
import json
import random
import numpy as np
from datetime import datetime, timedelta

WITHIN_PERSON_VARIANCE = 0.08   # ±8%

def generate_legitimate_sessions(n: int = 10) -> list[list[float]]:
    with open("data/profiles.json") as f:
        profile = json.load(f)["legitimate"]
    return [_generate_one(profile) for _ in range(n)]

def _generate_one(profile: dict) -> list[float]:
    from ml.feature_schema import FEATURE_NAMES
    vector = []
    for feature in FEATURE_NAMES:
        spec = profile.get(feature)
        if spec is None:
            # Try time_of_day_hour from choices
            if feature == "time_of_day_hour":
                choices = profile.get("time_of_day_hour_choices", [12])
                val = float(random.choice(choices))
            else:
                val = 0.0
        elif isinstance(spec, list) and len(spec) == 2:
            mean, std = spec
            val = float(np.random.normal(mean, std))
            # Apply within-person variance
            val *= (1 + np.random.uniform(-WITHIN_PERSON_VARIANCE, WITHIN_PERSON_VARIANCE))
            val = max(0.0, val)
        else:
            # scalar or boolean
            val = float(spec)
        vector.append(val)
    return vector
```

### 4.3 `data/seed_scenarios.py`

```python
"""
Generates 1 session per scenario (6 total).
Each session also has 5 progressive snapshots for the score degradation animation.
"""
import json
import random
import numpy as np

def generate_scenario_session(scenario_id: int) -> dict:
    """
    Returns:
        {
            "feature_vector": list[float],   # full 47-float session vector
            "snapshots": list[list[float]],  # 5 progressive partial vectors
        }
    """
    with open("data/profiles.json") as f:
        profiles = json.load(f)

    key = f"scenario_{scenario_id}"
    if key not in profiles:
        raise ValueError(f"No profile for {key}")

    profile = profiles[key]

    if profile.get("PRE_AUTH"):
        return {"feature_vector": [], "snapshots": [], "pre_auth": True}

    # Merge with legitimate baseline, override with attacker params
    with open("data/profiles.json") as f:
        legitimate = json.load(f)["legitimate"]

    merged = {**legitimate, **profile}
    feature_vector = _generate_one(merged)

    # Generate 5 progressive snapshots:
    # Snapshot 1: all legitimate values (starts normal)
    # Snapshot 2–4: gradually introduce attacker features
    # Snapshot 5: full attacker vector
    snapshots = _generate_progressive_snapshots(legitimate, merged, feature_vector)

    return {
        "feature_vector": feature_vector,
        "snapshots": snapshots,
        "fleet_fingerprint": profile.get("FLEET_FINGERPRINT"),
    }

def _generate_progressive_snapshots(
    legitimate: dict,
    attacker: dict,
    full_attacker_vector: list[float],
) -> list[list[float]]:
    """
    5 snapshots: interpolate from legitimate to full attacker.
    Snapshot 1 = 0% attacker, Snapshot 5 = 100% attacker.
    """
    from ml.feature_schema import FEATURE_NAMES

    legitimate_vector = _generate_one(legitimate)
    snapshots = []

    for i in range(5):
        alpha = i / 4.0   # 0.0, 0.25, 0.50, 0.75, 1.0
        snapshot = [
            (1 - alpha) * l + alpha * a
            for l, a in zip(legitimate_vector, full_attacker_vector)
        ]
        snapshots.append(snapshot)

    return snapshots

def _generate_one(profile: dict) -> list[float]:
    from ml.feature_schema import FEATURE_NAMES
    vector = []
    for feature in FEATURE_NAMES:
        spec = profile.get(feature)
        if spec is None:
            if feature == "time_of_day_hour":
                choices = profile.get("time_of_day_hour_choices", [12])
                val = float(random.choice(choices))
            else:
                val = 0.0
        elif isinstance(spec, list) and len(spec) == 2:
            mean, std = spec
            val = float(np.random.normal(mean, std))
            val = max(0.0, val)
        else:
            val = float(spec)
        vector.append(val)
    return vector
```

---

## 5. ROUTER LAYER

All routers follow this pattern:
- Import Pydantic request/response models
- Inject DB via `Depends(get_db)`
- Call ML or service functions -- no business logic in the router
- Return typed response

### 5.1 `routers/session.py`

```python
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import Session as SessionModel, Score, SimSwapEvent, User
from ml.one_class_svm import predict, get_baseline_stats, model_exists
from ml.score_fusion import fuse_score
from ml.anomaly_explainer import get_top_anomalies
from ml.feature_schema import dict_to_vector
from utils.scoring import get_sim_swap_minutes
import routers.alert as alert_router

router = APIRouter()

# ── Pydantic models ──────────────────────────────────────────

class StartRequest(BaseModel):
    user_id: int
    session_type: str   # "legitimate" | "scenario_1" ... "scenario_6"

class StartResponse(BaseModel):
    session_id: str
    started_at: str

class FeatureRequest(BaseModel):
    session_id: str
    feature_snapshot: dict     # partial or full feature dict
    snapshot_index: int        # 1–5

class FeatureResponse(BaseModel):
    score: int
    risk_level: str
    action: str
    top_anomalies: list[str]
    snapshot_index: int

class FleetCheckRequest(BaseModel):
    device_fingerprint: str
    user_id: int

class FleetCheckResponse(BaseModel):
    fleet_anomaly: bool
    accounts_seen: int
    action: str

# ── Routes ───────────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
def start_session(req: StartRequest, db: DBSession = Depends(get_db)):
    if not db.query(User).filter_by(id=req.user_id).first():
        raise HTTPException(404, "User not found")

    session = SessionModel(
        user_id=req.user_id,
        session_type=req.session_type,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartResponse(
        session_id=session.id,
        started_at=session.started_at.isoformat(),
    )

@router.post("/feature", response_model=FeatureResponse)
def submit_feature(req: FeatureRequest, db: DBSession = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=req.session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    if not model_exists(session.user_id):
        raise HTTPException(400, "User not enrolled. Call POST /enroll/{user_id} first.")

    # Build 47-float vector from partial snapshot
    feature_vector = dict_to_vector(req.feature_snapshot)

    # Get behavior score
    behavior_score = predict(session.user_id, feature_vector)

    # Check SIM swap status
    sim_swap = (
        db.query(SimSwapEvent)
        .filter_by(user_id=session.user_id, is_active=True)
        .first()
    )
    sim_swap_active = sim_swap is not None
    sim_swap_minutes = get_sim_swap_minutes(sim_swap) if sim_swap else 0

    # Fuse scores
    fusion = fuse_score(behavior_score, sim_swap_active)

    # Generate anomaly explanations
    meta = get_baseline_stats(session.user_id)
    anomalies = get_top_anomalies(
        feature_vector=feature_vector,
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
        sim_swap_active=sim_swap_active,
        sim_swap_minutes=sim_swap_minutes,
    )

    # Save score to DB
    score_record = Score(
        session_id=req.session_id,
        snapshot_index=req.snapshot_index,
        confidence_score=fusion["final_score"],
        risk_level=fusion["risk_level"],
        action=fusion["action"],
        top_anomalies=json.dumps(anomalies),
    )
    db.add(score_record)

    # Update session feature vector (last snapshot wins)
    session.feature_vector = json.dumps(feature_vector)
    db.commit()

    # Auto-trigger alert if BLOCK_AND_FREEZE
    if fusion["action"] == "BLOCK_AND_FREEZE":
        import os
        alert_router.send_sms_alert(
            session_id=req.session_id,
            score=fusion["final_score"],
            top_anomalies=anomalies,
            recipient=os.getenv("DEMO_ALERT_NUMBER", ""),
            db=db,
        )

    return FeatureResponse(
        score=fusion["final_score"],
        risk_level=fusion["risk_level"],
        action=fusion["action"],
        top_anomalies=anomalies,
        snapshot_index=req.snapshot_index,
    )

@router.post("/fleet-check", response_model=FleetCheckResponse)
def fleet_check(req: FleetCheckRequest, db: DBSession = Depends(get_db)):
    from ml.fleet_anomaly import check_fleet_anomaly
    result = check_fleet_anomaly(db, req.device_fingerprint, req.user_id)
    return FleetCheckResponse(
        fleet_anomaly=result["fleet_anomaly"],
        accounts_seen=result["accounts_seen"],
        action=result["action"],
    )
```

### 5.2 `routers/score.py`

```python
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import Score

router = APIRouter()

class ScoreResponse(BaseModel):
    score: int
    risk_level: str
    action: str
    top_anomalies: list[str]
    snapshot_index: int
    updated_at: str

@router.get("/{session_id}", response_model=ScoreResponse)
def get_score(session_id: str, db: DBSession = Depends(get_db)):
    latest = (
        db.query(Score)
        .filter_by(session_id=session_id)
        .order_by(Score.computed_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(404, "No score found for this session")

    return ScoreResponse(
        score=latest.confidence_score,
        risk_level=latest.risk_level,
        action=latest.action,
        top_anomalies=json.loads(latest.top_anomalies or "[]"),
        snapshot_index=latest.snapshot_index,
        updated_at=latest.computed_at.isoformat(),
    )
```

### 5.3 `routers/enroll.py`

```python
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import Session as SessionModel, User
from ml.one_class_svm import train

router = APIRouter()

REQUIRED_SESSIONS = 10

class EnrollResponse(BaseModel):
    enrolled: bool
    sessions_used: int
    model_saved: bool
    baseline_score: float
    baseline_std: float

@router.post("/{user_id}", response_model=EnrollResponse)
def enroll(user_id: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Get all legitimate sessions with feature vectors
    legitimate_sessions = (
        db.query(SessionModel)
        .filter_by(user_id=user_id, session_type="legitimate")
        .filter(SessionModel.feature_vector.isnot(None))
        .all()
    )

    if len(legitimate_sessions) < REQUIRED_SESSIONS:
        raise HTTPException(
            400,
            f"Need {REQUIRED_SESSIONS} sessions, have {len(legitimate_sessions)}. "
            "Run seed_runner.py first."
        )

    feature_vectors = [
        json.loads(s.feature_vector) for s in legitimate_sessions
    ]

    # Train model
    meta = train(user_id=user_id, feature_vectors=feature_vectors)

    # Update user enrollment timestamp
    user.enrolled_at = datetime.utcnow()
    user.sessions_count = len(legitimate_sessions)
    db.commit()

    return EnrollResponse(
        enrolled=True,
        sessions_used=len(legitimate_sessions),
        model_saved=True,
        baseline_score=meta["baseline_mean"],
        baseline_std=meta["baseline_std"],
    )
```

### 5.4 `routers/sim_swap.py`

```python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import SimSwapEvent
from utils.scoring import get_sim_swap_minutes

router = APIRouter()

class TriggerRequest(BaseModel):
    user_id: int

class TriggerResponse(BaseModel):
    event_id: str
    triggered_at: str
    is_active: bool

class ClearRequest(BaseModel):
    user_id: int

class StatusResponse(BaseModel):
    is_active: bool
    triggered_at: str | None
    minutes_ago: int | None

@router.post("/trigger", response_model=TriggerResponse)
def trigger(req: TriggerRequest, db: DBSession = Depends(get_db)):
    # Clear any existing active swap for this user
    existing = db.query(SimSwapEvent).filter_by(user_id=req.user_id, is_active=True).all()
    for e in existing:
        e.is_active = False
    db.commit()

    event = SimSwapEvent(user_id=req.user_id)
    db.add(event)
    db.commit()
    db.refresh(event)

    return TriggerResponse(
        event_id=event.id,
        triggered_at=event.triggered_at.isoformat(),
        is_active=True,
    )

@router.post("/clear")
def clear(req: ClearRequest, db: DBSession = Depends(get_db)):
    events = db.query(SimSwapEvent).filter_by(user_id=req.user_id, is_active=True).all()
    for e in events:
        e.is_active = False
        e.cleared_at = datetime.utcnow()
    db.commit()
    return {"cleared": True, "count": len(events)}

@router.get("/status/{user_id}", response_model=StatusResponse)
def status(user_id: int, db: DBSession = Depends(get_db)):
    event = (
        db.query(SimSwapEvent)
        .filter_by(user_id=user_id, is_active=True)
        .order_by(SimSwapEvent.triggered_at.desc())
        .first()
    )
    if not event:
        return StatusResponse(is_active=False, triggered_at=None, minutes_ago=None)

    return StatusResponse(
        is_active=True,
        triggered_at=event.triggered_at.isoformat(),
        minutes_ago=get_sim_swap_minutes(event),
    )
```

### 5.5 `routers/alert.py`

```python
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import AlertLog
from utils.twilio_client import send_sms

router = APIRouter()

class AlertRequest(BaseModel):
    session_id: str
    alert_type: str    # "SMS" | "LOG"
    recipient: str

class AlertResponse(BaseModel):
    sent: bool
    message_sid: str | None

@router.post("/send", response_model=AlertResponse)
def send_alert(
    req: AlertRequest,
    db: DBSession = Depends(get_db),
):
    from db.models import Score
    import json

    latest_score = (
        db.query(Score)
        .filter_by(session_id=req.session_id)
        .order_by(Score.computed_at.desc())
        .first()
    )
    score = latest_score.confidence_score if latest_score else 0
    anomalies = json.loads(latest_score.top_anomalies or "[]") if latest_score else []

    message_sid = None
    if req.alert_type == "SMS":
        message_sid = send_sms(
            to=req.recipient,
            score=score,
            top_anomalies=anomalies,
        )

    log = AlertLog(
        session_id=req.session_id,
        alert_type=req.alert_type,
        recipient=req.recipient,
        message=f"Score: {score} | " + " | ".join(anomalies[:2]),
        message_sid=message_sid,
    )
    db.add(log)
    db.commit()

    return AlertResponse(sent=True, message_sid=message_sid)

# Called internally by session.py -- not an HTTP route
def send_sms_alert(
    session_id: str,
    score: int,
    top_anomalies: list[str],
    recipient: str,
    db: DBSession,
) -> None:
    if not recipient:
        return
    message_sid = send_sms(to=recipient, score=score, top_anomalies=top_anomalies)
    log = AlertLog(
        session_id=session_id,
        alert_type="SMS",
        recipient=recipient,
        message=f"Auto-triggered | Score: {score}",
        message_sid=message_sid,
    )
    db.add(log)
    db.commit()
```

### 5.6 `routers/scenarios.py`

```python
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import Session as SessionModel, SimSwapEvent
from ml.one_class_svm import predict, get_baseline_stats
from ml.score_fusion import fuse_score
from ml.anomaly_explainer import get_top_anomalies
from ml.feature_schema import dict_to_vector

router = APIRouter()

SCENARIO_METADATA = [
    {"id": 1, "name": "New Phone + SIM",          "description": "SIM swap + attacker's own device",            "expected_score": 27, "expected_action": "BLOCK_AND_FREEZE",   "detection_time_s": 28,  "strength": "strong"},
    {"id": 2, "name": "Laptop + OTP SIM",         "description": "Fraud on laptop, OTP from SIM",               "expected_score": 31, "expected_action": "BLOCK_TRANSACTION",  "detection_time_s": 34,  "strength": "strong"},
    {"id": 3, "name": "Bot Automation",           "description": "Fully automated scripted attack",              "expected_score": 19, "expected_action": "BLOCK_AND_FREEZE",   "detection_time_s": 12,  "strength": "strong"},
    {"id": 4, "name": "Same Device Takeover",     "description": "Stolen phone + SIM -- hardest case",           "expected_score": 48, "expected_action": "STEP_UP_AUTH",       "detection_time_s": 52,  "strength": "moderate"},
    {"id": 5, "name": "Credential Stuffing",      "description": "Fleet attack: 3 accounts, 1 device, 8 min",   "expected_score": 22, "expected_action": "BLOCK_AND_FREEZE",   "detection_time_s": None, "strength": "strong"},
    {"id": 6, "name": "Pre-Auth SIM Probe",       "description": "Reconnaissance before login attempt",         "expected_score": None, "expected_action": "EARLY_WARNING",    "detection_time_s": None, "strength": "strong"},
    {"id": 7, "name": "Legitimate User (Control)","description": "Enrolled user -- should ALLOW",                "expected_score": 89, "expected_action": "ALLOW",              "detection_time_s": None, "strength": "control"},
]

class RunRequest(BaseModel):
    user_id: int

class RunResponse(BaseModel):
    scenario_id: int
    score_progression: list[int]
    final_score: int
    action: str
    risk_level: str
    top_anomalies: list[str]
    detection_time_s: float | None

@router.get("/list")
def list_scenarios():
    return SCENARIO_METADATA

@router.post("/{scenario_id}/run", response_model=RunResponse)
def run_scenario(scenario_id: int, req: RunRequest, db: DBSession = Depends(get_db)):
    if scenario_id not in range(1, 8):
        raise HTTPException(400, "scenario_id must be 1–7")

    # Get the pre-seeded scenario session
    session = (
        db.query(SessionModel)
        .filter_by(user_id=req.user_id, session_type=f"scenario_{scenario_id}")
        .first()
    )
    if not session or not session.feature_vector:
        raise HTTPException(404, f"Scenario {scenario_id} not seeded. Run seed_runner.py.")

    feature_vector = json.loads(session.feature_vector)

    # Check SIM swap for fusion
    sim_swap = db.query(SimSwapEvent).filter_by(user_id=req.user_id, is_active=True).first()
    sim_swap_active = sim_swap is not None

    # Compute score progression across 5 snapshots
    # For each snapshot i: reveal (i+1)/5 of attacker features
    meta = get_baseline_stats(req.user_id)
    legitimate_vector = [meta["per_feature_mean"][j] for j in range(47)]
    score_progression = []

    for i in range(5):
        alpha = (i + 1) / 5.0
        partial = [
            (1 - alpha) * l + alpha * a
            for l, a in zip(legitimate_vector, feature_vector)
        ]
        raw_score = predict(req.user_id, partial)
        fusion = fuse_score(raw_score, sim_swap_active)
        score_progression.append(fusion["final_score"])

    final_fusion = fuse_score(predict(req.user_id, feature_vector), sim_swap_active)
    anomalies = get_top_anomalies(
        feature_vector=feature_vector,
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
        sim_swap_active=sim_swap_active,
    )

    meta_entry = next((m for m in SCENARIO_METADATA if m["id"] == scenario_id), {})

    return RunResponse(
        scenario_id=scenario_id,
        score_progression=score_progression,
        final_score=final_fusion["final_score"],
        action=final_fusion["action"],
        risk_level=final_fusion["risk_level"],
        top_anomalies=anomalies,
        detection_time_s=meta_entry.get("detection_time_s"),
    )
```

### 5.7 `routers/features.py`

```python
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from db.models import Session as SessionModel
from ml.one_class_svm import get_baseline_stats
from ml.anomaly_explainer import get_z_scores

router = APIRouter()

@router.get("/inspect/{session_id}")
def inspect_features(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session or not session.feature_vector:
        raise HTTPException(404, "Session not found or no feature vector")

    feature_vector = json.loads(session.feature_vector)
    meta = get_baseline_stats(session.user_id)

    features = get_z_scores(
        feature_vector=feature_vector,
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
    )

    flagged_count = sum(1 for f in features if f["flagged"])

    return {
        "session_id": session_id,
        "total_features": 47,
        "flagged_count": flagged_count,
        "features": features,
    }
```

### 5.8 `routers/fleet.py`

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.database import get_db
from ml.fleet_anomaly import check_fleet_anomaly

router = APIRouter()

class FleetRequest(BaseModel):
    device_fingerprint: str
    user_id: int

@router.post("/check")
def check(req: FleetRequest, db: DBSession = Depends(get_db)):
    result = check_fleet_anomaly(db, req.device_fingerprint, req.user_id)
    return result
```

---

## 6. UTILITIES

### 6.1 `utils/scoring.py`

```python
from datetime import datetime

def get_sim_swap_minutes(sim_swap_event) -> int:
    """Returns minutes elapsed since SIM swap was triggered."""
    if sim_swap_event is None:
        return 0
    delta = datetime.utcnow() - sim_swap_event.triggered_at
    return int(delta.total_seconds() / 60)
```

### 6.2 `utils/twilio_client.py`

```python
import os
from twilio.rest import Client

def send_sms(to: str, score: int, top_anomalies: list[str]) -> str | None:
    """
    Send SMS alert via Twilio. Returns message SID or None if not configured.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not all([account_sid, auth_token, from_number, to]):
        print("[TWILIO] Not configured -- alert logged but not sent")
        return None

    # Max 2 anomalies in SMS to keep it readable
    reason_str = " | ".join(top_anomalies[:2])

    body = (
        f"[ALERT] SHIELD Alert: Suspicious activity detected.\n"
        f"Risk score: {score}/100.\n"
        f"Reason: {reason_str}.\n"
        f"Your transaction has been frozen.\n"
        f"Call 1800-SHIELD to verify."
    )

    client = Client(account_sid, auth_token)
    message = client.messages.create(body=body, from_=from_number, to=to)
    return message.sid
```

---

## 7. SEED RUNNER

### `demo/seed_runner.py`

```python
"""
One-command demo reset. Run before every demo.
Usage: python demo/seed_runner.py
Expected time: < 15 seconds
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.database import init_db, SessionLocal, ENGINE
from db.models import Base, User, Session as SessionModel, DeviceRegistry
from data.seed_legitimate import generate_legitimate_sessions
from data.seed_scenarios import generate_scenario_session
from ml.one_class_svm import train, predict
from ml.score_fusion import fuse_score

def run():
    print("SHIELD Seed Runner")
    print("══════════════════")

    # Step 1: Drop + recreate all tables
    print("1. Resetting database...")
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)
    print("   [DONE] Tables recreated")

    db = SessionLocal()

    # Step 2: Create demo user
    print("2. Creating demo user...")
    from datetime import datetime, timedelta
    user = User(id=1, name="Demo User", enrolled_at=datetime.utcnow() - timedelta(days=30))
    db.add(user)
    db.commit()
    print("   [DONE] User: Demo User (id=1)")

    # Step 3: Register 3 known devices
    print("3. Registering known devices...")
    for fp in ["DEVICE_KNOWN_001", "DEVICE_KNOWN_002", "DEVICE_KNOWN_003"]:
        db.add(DeviceRegistry(user_id=1, device_fingerprint=fp, is_trusted=True))
    db.commit()
    print("   [DONE] 3 known devices registered")

    # Step 4: Generate legitimate sessions
    print("4. Generating legitimate sessions...")
    vectors = generate_legitimate_sessions(n=10)
    for i, vec in enumerate(vectors):
        s = SessionModel(
            user_id=1,
            session_type="legitimate",
            feature_vector=json.dumps(vec),
            completed=True,
        )
        db.add(s)
    db.commit()
    print("   [DONE] 10 legitimate sessions seeded")

    # Step 5: Train model
    print("5. Training One-Class SVM...")
    meta = train(user_id=1, feature_vectors=vectors)
    print(f"   [DONE] Model trained | Baseline: {meta['baseline_mean']:.1f} ± {meta['baseline_std']:.1f}")

    # Verify legitimate sessions score correctly
    for vec in vectors:
        score = predict(1, vec)
        assert score >= 75, f"Legitimate session scored {score} -- calibration failed"
    print("   [DONE] Legitimate session scores verified (all ≥ 75)")

    # Step 6: Seed scenario sessions
    print("6. Seeding attack scenarios...")
    scenario_checks = {}
    for scenario_id in range(1, 7):
        data = generate_scenario_session(scenario_id)
        if data.get("pre_auth"):
            print(f"   [DONE] Scenario {scenario_id}: Pre-auth (no feature vector)")
            continue

        s = SessionModel(
            user_id=1,
            session_type=f"scenario_{scenario_id}",
            feature_vector=json.dumps(data["feature_vector"]),
            completed=True,
        )
        db.add(s)
        db.commit()

        # Verify prediction
        raw = predict(1, data["feature_vector"])
        fusion = fuse_score(raw, sim_swap_active=True)
        scenario_checks[scenario_id] = fusion["final_score"]

    # Step 7: Seed fleet scenario (scenario 5 -- register attacker device on user 2)
    user2 = User(id=2, name="Demo User 2", enrolled_at=None)
    db.add(user2)
    db.commit()
    db.add(DeviceRegistry(
        user_id=2,
        device_fingerprint="ATTACKER_DEVICE_FLEET_001",
        is_trusted=False,
    ))
    db.commit()
    print("   [DONE] Fleet scenario device registered (user_id=2)")

    # Step 8: Print verification table
    print("\n   Scenario Score Verification:")
    targets = {1: (0, 30), 2: (0, 35), 3: (0, 25), 4: (40, 60), 5: (0, 30)}
    all_ok = True
    for sid, score in scenario_checks.items():
        lo, hi = targets.get(sid, (0, 100))
        ok = lo <= score <= hi
        status = "[DONE]" if ok else "✗"
        if not ok:
            all_ok = False
        print(f"   {status} Scenario {sid}: score={score} (target {lo}–{hi})")

    if not all_ok:
        print("\n   ⚠ Some scores out of target range. Adjust SVM_NU in .env and re-run.")
    else:
        print("\n   [DONE] All scenario scores within target ranges")

    db.close()

    print("\n══════════════════")
    print("[DONE] SHIELD is ready.")
    print("  Run: uvicorn main:app --reload --port 8000")

if __name__ == "__main__":
    run()
```

---

## 8. TESTS

### `backend/tests/test_model.py`

```python
import json
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.one_class_svm import predict, get_baseline_stats
from ml.score_fusion import fuse_score
from ml.anomaly_explainer import get_top_anomalies, get_z_scores
from ml.fleet_anomaly import check_fleet_anomaly
from data.seed_legitimate import generate_legitimate_sessions
from data.seed_scenarios import generate_scenario_session

# These tests assume seed_runner.py has been run
USER_ID = 1

def test_legitimate_sessions_score_high():
    """All legitimate sessions must score ≥ 80."""
    vectors = generate_legitimate_sessions(n=10)
    for i, vec in enumerate(vectors):
        score = predict(USER_ID, vec)
        assert score >= 75, f"Legitimate session {i} scored {score} -- too low"

def test_scenario_1_blocked():
    """New device + SIM → score ≤ 30."""
    data = generate_scenario_session(1)
    score = predict(USER_ID, data["feature_vector"])
    fusion = fuse_score(score, sim_swap_active=True)
    assert fusion["final_score"] <= 30, f"Scenario 1 scored {fusion['final_score']}"
    assert fusion["action"] == "BLOCK_AND_FREEZE"

def test_scenario_3_fastest():
    """Bot attack → score ≤ 20."""
    data = generate_scenario_session(3)
    score = predict(USER_ID, data["feature_vector"])
    fusion = fuse_score(score, sim_swap_active=True)
    assert fusion["final_score"] <= 25, f"Scenario 3 scored {fusion['final_score']}"

def test_scenario_4_step_up():
    """Same device takeover → score in 40–60 range (STEP_UP, not BLOCK)."""
    data = generate_scenario_session(4)
    score = predict(USER_ID, data["feature_vector"])
    fusion = fuse_score(score, sim_swap_active=True)
    assert 35 <= fusion["final_score"] <= 65, \
        f"Scenario 4 scored {fusion['final_score']} -- expected step-up range"

def test_sim_swap_fusion_critical():
    """SIM swap + score < 45 → always CRITICAL."""
    result = fuse_score(behavior_score=40, sim_swap_active=True)
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "BLOCK_AND_FREEZE"

def test_sim_swap_fusion_penalizes():
    """SIM swap + score 80 → penalized to 48 (80*0.6) → MEDIUM."""
    result = fuse_score(behavior_score=80, sim_swap_active=True)
    assert result["final_score"] == 48
    assert result["risk_level"] == "MEDIUM"

def test_anomaly_count():
    """get_top_anomalies returns exactly 4 strings."""
    data = generate_scenario_session(1)
    meta = get_baseline_stats(USER_ID)
    anomalies = get_top_anomalies(
        feature_vector=data["feature_vector"],
        per_feature_mean=meta["per_feature_mean"],
        per_feature_std=meta["per_feature_std"],
        sim_swap_active=True,
        sim_swap_minutes=6,
        n=4,
    )
    assert len(anomalies) == 4
    # Last anomaly should mention SIM swap
    assert "SIM" in anomalies[-1] or "swap" in anomalies[-1].lower()

def test_z_scores_length():
    """get_z_scores returns exactly 47 entries."""
    vectors = generate_legitimate_sessions(n=1)
    meta = get_baseline_stats(USER_ID)
    z = get_z_scores(vectors[0], meta["per_feature_mean"], meta["per_feature_std"])
    assert len(z) == 47

def test_score_monotonically_decreases():
    """Progressive snapshots for scenario 1 must show decreasing scores."""
    data = generate_scenario_session(1)
    meta = get_baseline_stats(USER_ID)
    legitimate = meta["per_feature_mean"]
    attacker = data["feature_vector"]

    scores = []
    for i in range(5):
        alpha = (i + 1) / 5.0
        partial = [(1 - alpha) * l + alpha * a for l, a in zip(legitimate, attacker)]
        raw = predict(USER_ID, partial)
        fusion = fuse_score(raw, sim_swap_active=True)
        scores.append(fusion["final_score"])

    for i in range(1, 5):
        assert scores[i] <= scores[i-1] + 5, \
            f"Score increased from snapshot {i} to {i+1}: {scores[i-1]} → {scores[i]}"
```

---

## 9. IMPLEMENTATION SEQUENCE

```
Step 1:  requirements.txt + main.py + .env
Step 2:  db/database.py + db/models.py → run init_db(), verify tables exist
Step 3:  ml/feature_schema.py → run assert len == 47
Step 4:  data/profiles.json → write by hand, verify all keys present
Step 5:  data/seed_legitimate.py → generate_legitimate_sessions(10), spot-check 3 vectors
Step 6:  data/seed_scenarios.py → generate_scenario_session(1–6), spot-check outputs
Step 7:  ml/one_class_svm.py → train(), predict(), verify baseline scores 85–95
Step 8:  ml/score_fusion.py → run all 6 priority cases manually, verify output
Step 9:  ml/anomaly_explainer.py → get_top_anomalies() returns 4 strings with SIM_SWAP last
Step 10: ml/fleet_anomaly.py → verify fleet fires on 2nd account attempt
Step 11: utils/twilio_client.py + utils/scoring.py
Step 12: demo/seed_runner.py → must complete clean in < 15s
Step 13: routers/enroll.py → test POST /enroll/1 returns enrolled=True, baseline_score in 85–95
Step 14: routers/sim_swap.py → test trigger, status, clear
Step 15: routers/session.py → test /start, /feature (legitimate), /feature (scenario_1 + SIM swap active)
Step 16: routers/score.py → test GET /score/{id}
Step 17: routers/alert.py → test Twilio SMS actually arrives
Step 18: routers/scenarios.py → test all 6 /scenarios/{id}/run
Step 19: routers/features.py → verify 47 rows returned
Step 20: routers/fleet.py → verify fleet anomaly fires correctly
Step 21: backend/tests/ → all tests pass
Step 22: Full demo run end-to-end -- all 6 scenarios, Twilio fires, comparison table fills
```

**At each step: if output does not match spec, fix before proceeding.**
**Never skip a step. Never implement steps out of order.**