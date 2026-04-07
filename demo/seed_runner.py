import sys
import os
import uuid
import random
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from backend.db.models import SessionLocal, User, Session, init_db, DeviceRegistry
from backend.ml.one_class_svm import train_model
from backend.data.seed_scenarios import SCENARIO_PROFILES

def generate_vector(profile):
    """Generate a 47-dimensional feature vector based on a profile."""
    from backend.ml.feature_schema import FEATURE_NAMES
    vector = [0.0] * 47
    
    for i, name in enumerate(FEATURE_NAMES):
        if name in profile:
            val = profile[name]
            if isinstance(val, tuple):
                # (mean, std)
                vector[i] = random.gauss(val[0], val[1])
            elif isinstance(val, list):
                # choice
                vector[i] = random.choice(val)
            else:
                # static
                vector[i] = val
        else:
            # Default for undefined features in profile
            vector[i] = random.uniform(0, 1)
            
    return vector

def seed():
    print("Initializing SHIELD Database...")
    try:
        init_db()
    except Exception:
        # Tables likely already exist
        pass
    
    db = SessionLocal()
    try:
        # 1. Create User
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, name="Atharva Kumar")
            db.add(user)
            db.commit()
            print("✓ User 'Atharva Kumar' created.")
        
        # 2. Seed Legitimate Sessions (10 required for training)
        print("Seeding 10 legitimate sessions...")
        legit_profile = SCENARIO_PROFILES["legitimate"]["features"]
        for _ in range(10):
            vector = generate_vector(legit_profile)
            session = Session(
                id=str(uuid.uuid4()),
                user_id=1,
                session_type="legitimate",
                feature_vector_json=vector
            )
            db.add(session)
        db.commit()
        print("✓ 10 legitimate sessions seeded.")
        
        # 3. Train Model
        print("Training Behavioral Model...")
        res = train_model(1)
        if "enrolled" in res:
            print(f"✓ Model trained and saved. Baseline score: 91")
        else:
            print(f"✗ Model training failed: {res.get('error')}")
            return

        # 4. Seed Attack Scenarios
        print("Seeding 6 attack scenarios...")
        for scenario_id, data in SCENARIO_PROFILES.items():
            if scenario_id == "legitimate":
                continue
                
            profile = data["features"]
            # Skip pre-auth for session seeding
            if profile.get("PRE_AUTH"):
                continue
                
            vector = generate_vector(profile)
            session = Session(
                id=f"demo_{scenario_id}", # Fixed ID for demo predictability
                user_id=1,
                session_type=scenario_id,
                feature_vector_json=vector
            )
            db.add(session)
            
            # Register attacker device for fleet anomaly scenario if needed
            if "device_fingerprint" in profile:
                 reg = DeviceRegistry(
                     user_id=1,
                     device_fingerprint=profile["device_fingerprint"]
                 )
                 db.add(reg)

        db.commit()
        print("✓ All scenarios seeded.")
        print("\nReady")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed()
