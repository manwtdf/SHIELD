import sys
import os
import unittest
import numpy as np

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.models import SessionLocal, Session, init_db, Base, engine
from backend.ml.one_class_svm import train_model, predict_score
from backend.ml.score_fusion import fuse_score
from backend.utils.scoring import get_top_anomalies
from backend.data.seed_legitimate import generate_legitimate_session
from backend.data.seed_attacker import generate_attacker_session

class TestShieldModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        init_db()
        db = SessionLocal()
        cls.user_id = 1
        
        # Seed training data - increase to 30 for better stability
        from backend.data.seed_legitimate import seed_legitimate_data
        seed_legitimate_data(cls.user_id, 30)
        
        # Train model
        train_model(cls.user_id)
        db.close()

    def test_legitimate_scores_high(self):
        # Generate 5 new legits
        for _ in range(5):
            sess = generate_legitimate_session(self.user_id)
            score = predict_score(self.user_id, sess.feature_vector_json)
            self.assertGreaterEqual(score, 75, f"Legitimate session scored {score} - too low")

    def test_attacker_scores_low(self):
        # Generate attacker
        sess = generate_attacker_session(self.user_id)
        score = predict_score(self.user_id, sess.feature_vector_json)
        self.assertLessEqual(score, 45, f"Attacker session scored {score} - not detected")

    def test_sim_swap_fusion_critical(self):
        # Case: Critical behavior + SIM swap
        result = fuse_score(behavior_score=35, sim_swap_active=True)
        self.assertEqual(result["risk_level"], "CRITICAL")
        self.assertEqual(result["action"], "BLOCK_AND_FREEZE")
        
        # Case: Good behavior but SIM swap (penalized)
        result = fuse_score(behavior_score=90, sim_swap_active=True)
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertLess(result["final_score"], 60)

    def test_anomaly_count_attacker(self):
        sess = generate_attacker_session(self.user_id)
        anomalies = get_top_anomalies(self.user_id, sess.feature_vector_json, sim_swap_active=True)
        self.assertGreaterEqual(len(anomalies), 2)
        self.assertTrue(any("SIM swap" in a for a in anomalies))

if __name__ == "__main__":
    unittest.main()
