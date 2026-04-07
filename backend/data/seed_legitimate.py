import numpy as np
import uuid
import datetime
from backend.db.models import SessionLocal, Session, User
from backend.ml.feature_schema import FEATURE_NAMES

LEGITIMATE_PROFILE = {
    "inter_key_delay_mean": (180, 15),     
    "inter_key_delay_std": (25, 5),
    "dwell_time_mean": (95, 8),
    "swipe_velocity_mean": (450, 30),
    "session_duration_ms": (240000, 30000), 
    "time_of_day_hour": [9, 10, 18, 19, 20], 
    "direct_to_transfer": 0.15,             
    "exploratory_ratio": (0.08, 0.02),
    "is_new_device": 0,
    "hand_stability_score": (0.82, 0.05),
    "time_to_submit_otp_ms": (8500, 2000), 
}

def generate_legitimate_session(user_id: int):
    features = {}
    
    # Randomly pick from profile
    for key, val in LEGITIMATE_PROFILE.items():
        if isinstance(val, tuple):
            features[key] = np.random.normal(val[0], val[1])
        elif isinstance(val, list):
            features[key] = np.random.choice(val)
        else:
            features[key] = val

    # Fill remaining 47 features with defaults/random variance
    for name in FEATURE_NAMES:
        if name not in features:
            if "std" in name:
                features[name] = np.random.uniform(5, 8) # Reduced variance
            elif "mean" in name:
                features[name] = np.random.uniform(140, 160) # Tighter mean
            elif "count" in name:
                features[name] = np.random.randint(2, 5)
            else:
                features[name] = 0.0

    # Ensure binary features are correct
    features["is_new_device"] = 0
    features["timezone_changed"] = 0
    features["os_version_changed"] = 0
    
    # Navigation depth
    features["navigation_depth_max"] = np.random.randint(3, 7)
    features["screens_visited_count"] = features["navigation_depth_max"] + np.random.randint(0, 3)

    # Reorder to match FEATURE_NAMES and cast to float
    vector = [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
    
    return Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        started_at=datetime.datetime.utcnow(),
        session_type='legitimate',
        feature_vector_json=vector
    )

def seed_legitimate_data(user_id: int, count: int = 10):
    db = SessionLocal()
    try:
        # Ensure user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, name="Atharva Kumar", sessions_count=0)
            db.add(user)
            db.commit()

        for _ in range(count):
            session = generate_legitimate_session(user_id)
            db.add(session)
            user.sessions_count += 1
        
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_legitimate_data(1)
    print("Seeded 10 legitimate sessions for user 1")
