"""
SHIELD Fleet Anomaly Detection
───────────────────────────────
Cross-account device fingerprint attack detection.

Rule:
    Same device_fingerprint seen on ≥ 2 distinct user accounts
    within 60 minutes → FREEZE_ALL_ACCOUNTS.

Detection fires on the 2nd account attempt.

Accepts db session via dependency injection — no internal SessionLocal.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from backend.db.models import DeviceRegistry

logger = logging.getLogger("shield.ml.fleet")

FLEET_WINDOW_MINUTES = 60
FLEET_THRESHOLD      = 2  # ≥ 2 distinct accounts = fleet anomaly


def check_fleet_anomaly(
    db: DBSession,
    device_fingerprint: str,
    current_user_id: int,
) -> dict:
    """
    Check if this device fingerprint has been seen on ≥ FLEET_THRESHOLD
    distinct user accounts within the last FLEET_WINDOW_MINUTES minutes.

    Args:
        db:                 SQLAlchemy session (injected by caller)
        device_fingerprint: str — hash of device characteristics
        current_user_id:    int — current session's user

    Returns:
        {
            "fleet_anomaly":     bool,
            "accounts_seen":     int,
            "affected_user_ids": list[int],
            "action":            str,   "FREEZE_ALL_ACCOUNTS" | "ALLOW"
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

    if fleet_anomaly:
        logger.warning(
            f"Fleet anomaly detected: device={device_fingerprint[:16]}... "
            f"seen on {accounts_seen} accounts: {seen_user_ids}"
        )

    return {
        "fleet_anomaly":     fleet_anomaly,
        "accounts_seen":     accounts_seen,
        "affected_user_ids": seen_user_ids,
        "action":            "FREEZE_ALL_ACCOUNTS" if fleet_anomaly else "ALLOW",
    }


def _register_device(
    db: DBSession,
    fingerprint: str,
    user_id: int,
    device_class: str = "mobile",
) -> None:
    """Upsert device fingerprint into registry. Increments session_count."""
    existing = (
        db.query(DeviceRegistry)
        .filter_by(device_fingerprint=fingerprint, user_id=user_id)
        .first()
    )
    if existing:
        existing.last_seen = datetime.utcnow()
        existing.session_count = (existing.session_count or 0) + 1
        if existing.session_count >= 3:
            existing.is_trusted = True
    else:
        db.add(DeviceRegistry(
            user_id=user_id,
            device_fingerprint=fingerprint,
            device_class=device_class,
            is_trusted=False,
            session_count=1,
        ))
    db.commit()