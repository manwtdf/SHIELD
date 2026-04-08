"""
SHIELD Database Models
──────────────────────
All 6 tables with proper types, constraints, indexes, and UUID keys.

Tables:
    1. users           — enrolled bank customers
    2. sessions        — behavioral capture sessions
    3. scores          — ML scoring snapshots
    4. sim_swap_events — telecom SIM swap signals
    5. alert_log       — SMS / LOG alert records
    6. device_registry — per-user device fingerprint registry
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, Index
)
from backend.db.database import Base


def _new_uuid() -> str:
    """Generate a new UUID4 string for primary keys."""
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────
# TABLE 1: users
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(100), nullable=False)
    enrolled_at    = Column(DateTime, nullable=True)          # set on first enrollment
    sessions_count = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
# TABLE 2: sessions
# ─────────────────────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"

    id             = Column(String(36), primary_key=True, default=_new_uuid)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at     = Column(DateTime, default=datetime.utcnow)
    session_type   = Column(String(30), nullable=False)
    # Valid values: "legitimate", "scenario_1" .. "scenario_6", "auto"
    device_class   = Column(String(20), default="mobile")     # mobile | desktop | tablet
    feature_vector = Column(Text, nullable=True)              # JSON: list[float] len=55
    completed      = Column(Boolean, default=False)
    completed_at   = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_sessions_user_type", "user_id", "session_type"),
    )


# ─────────────────────────────────────────────────────────────
# TABLE 3: scores
# ─────────────────────────────────────────────────────────────

class Score(Base):
    __tablename__ = "scores"

    id               = Column(String(36), primary_key=True, default=_new_uuid)
    session_id       = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    computed_at      = Column(DateTime, default=datetime.utcnow)
    snapshot_index   = Column(Integer, nullable=False)         # 1–5
    confidence_score = Column(Integer, nullable=False)         # 0–100
    risk_level       = Column(String(10), nullable=False)      # LOW | MEDIUM | HIGH | CRITICAL
    action           = Column(String(20), nullable=False)      # ALLOW | STEP_UP_AUTH | BLOCK_TRANSACTION | BLOCK_AND_FREEZE
    top_anomalies    = Column(Text, nullable=True)             # JSON: list[str] len≤4


# ─────────────────────────────────────────────────────────────
# TABLE 4: sim_swap_events
# ─────────────────────────────────────────────────────────────

class SimSwapEvent(Base):
    __tablename__ = "sim_swap_events"

    id           = Column(String(36), primary_key=True, default=_new_uuid)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    is_active    = Column(Boolean, default=True)
    cleared_at   = Column(DateTime, nullable=True)


# ─────────────────────────────────────────────────────────────
# TABLE 5: alert_log
# ─────────────────────────────────────────────────────────────

class AlertLog(Base):
    __tablename__ = "alert_log"

    id          = Column(String(36), primary_key=True, default=_new_uuid)
    session_id  = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    alert_type  = Column(String(10), nullable=False)           # SMS | LOG
    sent_at     = Column(DateTime, default=datetime.utcnow)
    recipient   = Column(String(50), nullable=False)
    message     = Column(Text, nullable=False)
    message_sid = Column(String(50), nullable=True)            # Twilio SID if SMS


# ─────────────────────────────────────────────────────────────
# TABLE 6: device_registry
# ─────────────────────────────────────────────────────────────

class DeviceRegistry(Base):
    __tablename__ = "device_registry"

    id                 = Column(String(36), primary_key=True, default=_new_uuid)
    user_id            = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_fingerprint = Column(String(64), nullable=False, index=True)
    device_class       = Column(String(20), default="mobile")  # mobile | desktop | tablet
    first_seen         = Column(DateTime, default=datetime.utcnow)
    last_seen          = Column(DateTime, default=datetime.utcnow)
    is_trusted         = Column(Boolean, default=False)
    session_count      = Column(Integer, default=0)            # sessions on this fingerprint

    __table_args__ = (
        Index("ix_device_fp_user", "device_fingerprint", "user_id"),
    )
