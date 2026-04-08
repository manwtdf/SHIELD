"""
SHIELD API Route Tests
──────────────────────
FastAPI TestClient integration tests for all routes.
Run: cd SHIELD && python -m pytest backend/tests/test_routes.py -v
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from backend.db.database import ENGINE as engine, SessionLocal, Base, init_db
from backend.db.models import User, Session as SessionModel, DeviceRegistry
from backend.data.seed_data import generate_legitimate_sessions
from backend.ml.one_class_svm import train
from backend.main import app


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Module-scoped test client with seeded database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db.add(User(id=1, name="Test User"))
    db.commit()

    # Register a known device
    db.add(DeviceRegistry(
        user_id=1,
        device_fingerprint="TEST_DEVICE_001",
        device_class="mobile",
        session_count=5,
        is_trusted=True,
    ))
    db.commit()

    # Seed legitimate sessions and train
    vectors = generate_legitimate_sessions(n=10)
    for vec in vectors:
        db.add(SessionModel(
            user_id=1,
            session_type="legitimate",
            device_class="mobile",
            feature_vector=json.dumps(vec),
            completed=True,
        ))
    db.commit()
    db.close()

    train(user_id=1, feature_vectors=vectors)

    yield TestClient(app)


# ─────────────────────────────────────────────────────────────
# Health & Root
# ─────────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "SHIELD" in resp.json()["name"]


# ─────────────────────────────────────────────────────────────
# Session Routes
# ─────────────────────────────────────────────────────────────

class TestSession:
    def test_start_session(self, client):
        resp = client.post("/session/start", json={
            "user_id": 1,
            "session_type": "auto",
            "device_class": "mobile",
            "device_fingerprint": "TEST_DEVICE_001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "started_at" in data

    def test_start_session_unknown_user(self, client):
        resp = client.post("/session/start", json={
            "user_id": 999,
            "session_type": "auto",
        })
        assert resp.status_code == 404

    def test_submit_feature(self, client):
        # Start session first
        start = client.post("/session/start", json={
            "user_id": 1,
            "session_type": "auto",
            "device_fingerprint": "TEST_DEVICE_001",
        })
        session_id = start.json()["session_id"]

        # Submit features
        resp = client.post("/session/feature", json={
            "session_id": session_id,
            "snapshot_index": 1,
            "feature_snapshot": {
                "inter_key_delay_mean": 180.0,
                "dwell_time_mean": 95.0,
                "swipe_velocity_mean": 450.0,
                "hand_stability_score": 0.82,
                "session_duration_ms": 240000.0,
                "direct_to_transfer": 0.0,
                "is_new_device": 0.0,
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "risk_level" in data
        assert "action" in data
        assert "top_anomalies" in data
        assert 0 <= data["score"] <= 100

    def test_submit_feature_missing_session(self, client):
        resp = client.post("/session/feature", json={
            "session_id": "nonexistent",
            "feature_snapshot": {},
        })
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────
# Score Route
# ─────────────────────────────────────────────────────────────

class TestScore:
    def test_get_score_404_no_score(self, client):
        resp = client.get("/score/nonexistent-session")
        assert resp.status_code == 404

    def test_get_score_after_feature(self, client):
        # Start + submit feature
        start = client.post("/session/start", json={
            "user_id": 1, "device_fingerprint": "TEST_DEVICE_001",
        })
        sid = start.json()["session_id"]
        client.post("/session/feature", json={
            "session_id": sid,
            "feature_snapshot": {"inter_key_delay_mean": 180.0},
        })

        # Now GET score
        resp = client.get(f"/score/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "snapshot_index" in data
        assert "updated_at" in data


# ─────────────────────────────────────────────────────────────
# Enrollment Routes
# ─────────────────────────────────────────────────────────────

class TestEnrollment:
    def test_enroll_user(self, client):
        resp = client.post("/enroll/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enrolled"] is True
        assert data["sessions_used"] >= 10

    def test_enroll_unknown_user(self, client):
        resp = client.post("/enroll/999")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────
# SIM Swap Routes
# ─────────────────────────────────────────────────────────────

class TestSimSwap:
    def test_trigger_and_status(self, client):
        # Trigger
        resp = client.post("/sim-swap/trigger", json={"user_id": 1})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

        # Status
        resp = client.get("/sim-swap/status/1")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True
        assert resp.json()["minutes_ago"] is not None

    def test_clear(self, client):
        client.post("/sim-swap/trigger", json={"user_id": 1})
        resp = client.post("/sim-swap/clear", json={"user_id": 1})
        assert resp.status_code == 200
        assert resp.json()["cleared"] is True

        # Verify cleared
        resp = client.get("/sim-swap/status/1")
        assert resp.json()["is_active"] is False


# ─────────────────────────────────────────────────────────────
# Alert Route
# ─────────────────────────────────────────────────────────────

class TestAlert:
    def test_send_alert_log(self, client):
        # Start session first
        start = client.post("/session/start", json={
            "user_id": 1, "device_fingerprint": "TEST_DEVICE_001",
        })
        sid = start.json()["session_id"]

        resp = client.post("/alert/send", json={
            "session_id": sid,
            "alert_type": "LOG",
        })
        assert resp.status_code == 200
        assert resp.json()["sent"] is True


# ─────────────────────────────────────────────────────────────
# Scenarios Route
# ─────────────────────────────────────────────────────────────

class TestScenarios:
    def test_list_scenarios(self, client):
        resp = client.get("/scenarios/list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6


# ─────────────────────────────────────────────────────────────
# Features Route
# ─────────────────────────────────────────────────────────────

class TestFeatures:
    def test_inspect_features(self, client):
        # Start session + submit features
        start = client.post("/session/start", json={
            "user_id": 1, "device_fingerprint": "TEST_DEVICE_001",
        })
        sid = start.json()["session_id"]
        client.post("/session/feature", json={
            "session_id": sid,
            "feature_snapshot": {"inter_key_delay_mean": 350.0, "is_new_device": 1.0},
        })

        resp = client.get(f"/features/inspect/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_features"] == 55
        assert len(data["features"]) == 55


# ─────────────────────────────────────────────────────────────
# Fleet Route
# ─────────────────────────────────────────────────────────────

class TestFleet:
    def test_fleet_check_single_account(self, client):
        resp = client.post("/fleet/check", json={
            "device_fingerprint": "UNIQUE_DEVICE",
            "user_id": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["fleet_anomaly"] is False
        assert data["action"] == "ALLOW"
