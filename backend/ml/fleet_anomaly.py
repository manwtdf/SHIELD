from datetime import datetime, timedelta
from backend.db.models import SessionLocal, DeviceRegistry

# Configurable thresholds
FLEET_WINDOW_MINUTES = 60
FLEET_MIN_ACCOUNTS = 2


def check_fleet_anomaly(device_fingerprint: str, user_id: int) -> dict:
    """
    Detect if a device fingerprint is being used across multiple accounts
    within a short time window (potential fraud signal).
    """
    db = SessionLocal()
    try:
        window_start = datetime.utcnow() - timedelta(minutes=FLEET_WINDOW_MINUTES)

        # Get distinct users using this device recently
        distinct_users = db.query(DeviceRegistry.user_id).filter(
            DeviceRegistry.device_fingerprint == device_fingerprint,
            DeviceRegistry.last_seen >= window_start
        ).distinct().all()

        user_ids = [u[0] for u in distinct_users]

        # Include current user if not already tracked
        if user_id not in user_ids:
            user_ids.append(user_id)

        fleet_anomaly = len(user_ids) >= FLEET_MIN_ACCOUNTS

        return {
            "fleet_anomaly": fleet_anomaly,
            "accounts_seen": len(user_ids),
            "affected_users": user_ids,
            "action": "FREEZE_ALL_ACCOUNTS" if fleet_anomaly else "ALLOW"
        }

    finally:
        db.close()


def register_device(user_id: int, device_fingerprint: str):
    """
    Register or update a device fingerprint for a user.
    """
    db = SessionLocal()
    try:
        device = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id,
            DeviceRegistry.device_fingerprint == device_fingerprint
        ).first()

        if device:
            device.last_seen = datetime.utcnow()
        else:
            device = DeviceRegistry(
                user_id=user_id,
                device_fingerprint=device_fingerprint
            )
            db.add(device)

        db.commit()
        return device

    finally:
        db.close()