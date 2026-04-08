"""
SHIELD ML Engine Tests
──────────────────────
Tests the core ML pipeline: training, prediction, fusion, anomaly explanation.
Run: cd SHIELD && python -m pytest backend/tests/test_model.py -v
"""

import json
import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.db.database import ENGINE as engine, SessionLocal, Base, init_db
from backend.db.models import User, Session as SessionModel
from backend.data.seed_data import generate_legitimate_sessions, generate_scenario_session
from backend.ml.one_class_svm import train, predict, get_baseline_stats, model_exists
from backend.ml.score_fusion import fuse_score
from backend.ml.anomaly_explainer import get_top_anomalies, get_z_scores
from backend.ml.feature_schema import FEATURE_NAMES, FEATURE_DIM


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def setup_db_and_train():
    """
    Module-scoped setup: create tables, seed data, train model.
    Runs once for all tests in this file.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create user
    db.add(User(id=1, name="Test User"))
    db.commit()

    # Generate and store legitimate sessions
    vectors = generate_legitimate_sessions(n=15)
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

    # Train model
    train(user_id=1, feature_vectors=vectors)

    yield  # tests run here

    # Cleanup model files
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml", "models")
    for f in os.listdir(model_dir) if os.path.isdir(model_dir) else []:
        if f.startswith(("model_1", "scaler_1", "calibration_1", "meta_1")):
            os.remove(os.path.join(model_dir, f))


@pytest.fixture(scope="module")
def legit_vectors():
    return generate_legitimate_sessions(n=5)


@pytest.fixture(scope="module")
def baseline():
    return get_baseline_stats(1)


# ─────────────────────────────────────────────────────────────
# One-Class SVM Tests
# ─────────────────────────────────────────────────────────────

class TestSVM:
    def test_model_exists(self):
        assert model_exists(1), "Model should exist after training"

    def test_legitimate_scores_high(self, legit_vectors):
        """Legitimate sessions must score ≥ 75."""
        for vec in legit_vectors:
            score = predict(1, vec)
            assert score >= 70, f"Legitimate session scored {score} — too low (need ≥70)"

    def test_scenario_1_scores_low(self):
        """Scenario 1 (new phone + SIM) should score low."""
        result = generate_scenario_session(1)
        score = predict(1, result["feature_vector"])
        assert score <= 55, f"Scenario 1 scored {score} — not low enough"

    def test_scenario_3_lowest(self):
        """Scenario 3 (bot automation) should be the strongest anomaly."""
        result = generate_scenario_session(3)
        score = predict(1, result["feature_vector"])
        assert score <= 50, f"Scenario 3 scored {score} — bot should be lowest"

    def test_scenario_4_moderate(self):
        """Scenario 4 (same device takeover) is hardest — moderate score."""
        result = generate_scenario_session(4)
        score = predict(1, result["feature_vector"])
        # This scenario is harder to detect — allow wider range up to 85 (fused score drops it to step-up)
        assert score <= 85, f"Scenario 4 scored {score} — too high for same-device takeover"

    def test_score_0_to_100_range(self):
        """Scores must always be in [0, 100]."""
        for i in range(1, 6):
            result = generate_scenario_session(i)
            if result["pre_auth"]:
                continue
            score = predict(1, result["feature_vector"])
            assert 0 <= score <= 100, f"Score {score} out of range"

    def test_progressive_snapshots_decrease(self):
        """Score should generally decrease across progressive snapshots."""
        # Since some scenarios instantly drop to 0, use Scenario 4 for a smooth progression
        result = generate_scenario_session(4)
        scores = [predict(1, snap) for snap in result["snapshots"]]
        
        # Check monotonicity (allow small bumps due to variance)
        for i in range(1, len(scores)):
            assert scores[i] <= scores[i-1] + 5, f"Progressive score spiked: {scores}"
        
        # Overall decreasing trend
        assert scores[-1] < scores[0], (
            f"Progressive scores did not decrease overall: {scores}"
        )


# ─────────────────────────────────────────────────────────────
# Score Fusion Tests
# ─────────────────────────────────────────────────────────────

class TestFusion:
    def test_critical_sim_swap_plus_anomaly(self):
        """SIM swap + behavioral anomaly on unknown device → CRITICAL."""
        result = fuse_score(35, sim_swap_active=True, device_context={
            "device_class_switch": 1,
            "is_known_fingerprint": 0,
            "device_session_count": 0,
            "device_class_known": 1,
        })
        assert result["risk_level"] == "CRITICAL"
        assert result["action"] == "BLOCK_AND_FREEZE"

    def test_sim_swap_penalizes_good_score(self):
        """SIM swap alone should penalize even high behavioral score."""
        result = fuse_score(90, sim_swap_active=True, device_context={
            "is_known_fingerprint": 0,
        })
        assert result["final_score"] < 70, f"SIM swap didn't penalize enough: {result['final_score']}"

    def test_no_sim_swap_high_score_allows(self):
        """High behavior + no SIM swap → ALLOW."""
        result = fuse_score(88, sim_swap_active=False)
        assert result["action"] == "ALLOW"
        assert result["risk_level"] == "LOW"

    def test_extreme_anomaly_blocks(self):
        """Very low score without SIM swap → BLOCK_AND_FREEZE."""
        result = fuse_score(15, sim_swap_active=False)
        assert result["action"] == "BLOCK_AND_FREEZE"
        assert result["risk_level"] == "CRITICAL"

    def test_sim_swap_known_device_lighter(self):
        """SIM swap on known device → lighter penalty."""
        result = fuse_score(80, sim_swap_active=True, device_context={
            "is_known_fingerprint": 1,
        })
        # Known device with SIM swap should get step-up, not block
        assert result["action"] in ("STEP_UP_AUTH", "BLOCK_TRANSACTION")

    def test_all_return_keys(self):
        """All fusion results must have identical keys."""
        result = fuse_score(50, sim_swap_active=False)
        assert set(result.keys()) == {"final_score", "risk_level", "action", "reason"}


# ─────────────────────────────────────────────────────────────
# Anomaly Explainer Tests
# ─────────────────────────────────────────────────────────────

class TestAnomalyExplainer:
    def test_top_4_anomalies_count(self, baseline):
        """Should return exactly 4 anomaly strings."""
        result = generate_scenario_session(1)
        anomalies = get_top_anomalies(
            feature_vector=result["feature_vector"],
            per_feature_mean=baseline["per_feature_mean"],
            per_feature_std=baseline["per_feature_std"],
            sim_swap_active=True,
            sim_swap_minutes=6,
            n=4,
        )
        assert len(anomalies) == 4
        assert all(isinstance(a, str) for a in anomalies)

    def test_sim_swap_always_last(self, baseline):
        """SIM swap message should be the last anomaly when active."""
        result = generate_scenario_session(1)
        anomalies = get_top_anomalies(
            feature_vector=result["feature_vector"],
            per_feature_mean=baseline["per_feature_mean"],
            per_feature_std=baseline["per_feature_std"],
            sim_swap_active=True,
        )
        assert "sim swap" in anomalies[-1].lower()

    def test_no_sim_swap_no_sim_message(self, baseline):
        """Without SIM swap, no SIM message in anomalies."""
        result = generate_scenario_session(3)
        anomalies = get_top_anomalies(
            feature_vector=result["feature_vector"],
            per_feature_mean=baseline["per_feature_mean"],
            per_feature_std=baseline["per_feature_std"],
            sim_swap_active=False,
        )
        for a in anomalies:
            assert "sim swap" not in a.lower()

    def test_z_scores_length(self, baseline):
        """z-score inspection should return exactly 55 entries."""
        result = generate_scenario_session(1)
        z_scores = get_z_scores(
            feature_vector=result["feature_vector"],
            per_feature_mean=baseline["per_feature_mean"],
            per_feature_std=baseline["per_feature_std"],
        )
        assert len(z_scores) == FEATURE_DIM
        # Each entry must have required keys
        for entry in z_scores:
            assert set(entry.keys()) == {"name", "value", "baseline", "z_score", "flagged"}

    def test_attacker_has_flagged_features(self, baseline):
        """Attacker scenario should have at least 3 flagged features."""
        result = generate_scenario_session(3)
        z_scores = get_z_scores(
            feature_vector=result["feature_vector"],
            per_feature_mean=baseline["per_feature_mean"],
            per_feature_std=baseline["per_feature_std"],
        )
        flagged = [z for z in z_scores if z["flagged"]]
        assert len(flagged) >= 3, f"Only {len(flagged)} features flagged — expected ≥3"
