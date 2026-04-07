from datetime import datetime, timedelta
from backend.db.models import SessionLocal, DeviceRegistry

# Configurable thresholds
FLEET_WINDOW_MINUTES = 60
FLEET_MIN_ACCOUNTS = 2


def check_fleet_anomaly(device_fingerprint: str, user_id: int) -> dict:
    """
    Cross-account attack detection. Identifies same device used across
    multiple user accounts in a short time window.
    """
    db = SessionLocal()
    try:
        window_start = datetime.utcnow() - timedelta(minutes=FLEET_WINDOW_MINUTES)

        # 1. Get distinct user_ids recently using this device
        rows = db.query(DeviceRegistry.user_id).filter(
            DeviceRegistry.device_fingerprint == device_fingerprint,
            DeviceRegistry.last_seen >= window_start
        ).distinct().all()

        distinct_accounts = [r[0] for r in rows]

        # 2. Register current check
        _register_device(db, device_fingerprint, user_id)

        # If current user isn't in registry yet, add to memory for the len check
        if user_id not in distinct_accounts:
            distinct_accounts.append(user_id)

        fleet_anomaly = len(distinct_accounts) >= FLEET_MIN_ACCOUNTS

        return {
            "fleet_anomaly":      fleet_anomaly,
            "accounts_seen":      len(distinct_accounts),
            "action":             "CRITICAL_ALL_ACCOUNTS_FROZEN" if fleet_anomaly else "ALLOW",
            "flagged_accounts":   distinct_accounts,
            "device_fingerprint": device_fingerprint
        }

    finally:
        db.close()


def _register_device(db, device_fingerprint: str, user_id: int):
    """
    Internal: Upsert device registration.
    """
    device = db.query(DeviceRegistry).filter(
        DeviceRegistry.user_id == user_id,
        DeviceRegistry.device_fingerprint == device_fingerprint
    ).first()

    if device:
        device.last_seen = datetime.utcnow()
    else:
        device = DeviceRegistry(
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )
        db.add(device)

    db.commit()