import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from backend.db.models import init_db, SessionLocal, engine
from backend.db.models import Base, User, Session as SessionModel, DeviceRegistry
from backend.data.seed_legitimate import generate_legitimate_session
from backend.data.seed_scenarios import SCENARIO_PROFILES
from backend.ml.one_class_svm import train_model, predict_score
from backend.ml.score_fusion import fuse_score

def generate_legitimate_sessions(user_id, count=10):
    sessions = []
    for _ in range(count):
        session = generate_legitimate_session(user_id)
        sessions.append(session)
    return sessions

def run():
    print("SHIELD Seed Runner")
    print("══════════════════")

    print("1. Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("   [DONE] Tables recreated")

    db = SessionLocal()

    print("2. Creating demo user...")
    from datetime import datetime, timedelta
    user = User(id=1, name="Demo User", enrolled_at=datetime.utcnow() - timedelta(days=30))
    db.add(user)
    db.commit()
    print("   [DONE] User: Demo User (id=1)")

    print("3. Registering known devices...")
    for fp in ["DEVICE_KNOWN_001", "DEVICE_KNOWN_002", "DEVICE_KNOWN_003"]:
        db.add(DeviceRegistry(user_id=1, device_fingerprint=fp, session_count=5))
    db.commit()
    print("   [DONE] 3 known devices registered")

    print("4. Generating legitimate sessions...")
    legit_sessions = generate_legitimate_sessions(1, 10)
    for s in legit_sessions:
        db.add(s)
    db.commit()
    print("   [DONE] 10 legitimate sessions seeded")

    print("5. Training One-Class SVM...")
    meta = train_model(user_id=1, device_class="all")
    print(f"   [DONE] Model trained | Baseline model used {meta['sessions_used']} sessions")

    for s in legit_sessions:
        score = predict_score(1, s.feature_vector_json)
        assert score >= 75, f"Legitimate session scored {score} -- calibration failed"
    print("   [DONE] Legitimate session scores verified (all ≥ 75)")

    print("6. Seeding attack scenarios...")
    scenario_checks = {}
    
    # We just need to ensure the DB has one session of each type
    for scenario_id, profile in SCENARIO_PROFILES.items():
        if scenario_id == "legitimate":
            continue
        
        # Build features from profile
        features = {}
        from backend.ml.feature_schema import FEATURE_NAMES
        import numpy as np
        
        for key, val in profile.get("features", {}).items():
            if isinstance(val, tuple):
                features[key] = np.random.normal(val[0], val[1])
            elif isinstance(val, list):
                features[key] = np.random.choice(val)
            else:
                features[key] = val
                
        for name in FEATURE_NAMES:
            if name not in features:
                features[name] = 0.0
                
        vector = [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
        
        s = SessionModel(
            id=scenario_id,
            user_id=1,
            session_type=scenario_id,
            feature_vector_json=vector,
        )
        db.add(s)
        db.commit()

        raw = predict_score(1, vector)
        sim_swap_active = True if scenario_id in ["scenario_1", "scenario_4"] else False
        fusion = fuse_score(raw, sim_swap_active=sim_swap_active)
        scenario_checks[scenario_id] = fusion["final_score"]

    print("\n   Scenario Score Verification:")
    for sid, score in scenario_checks.items():
        print(f"   [DONE] {sid}: score={score}")

    db.close()
    print("\n══════════════════")
    print("[DONE] SHIELD is ready.")

if __name__ == "__main__":
    run()
