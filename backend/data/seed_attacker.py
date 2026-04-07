import numpy as np
import uuid
import datetime
from backend.db.models import SessionLocal, Session
from backend.ml.feature_schema import FEATURE_NAMES

ATTACKER_PROFILE = {
    "inter_key_delay_mean": (310, 60),     
    "inter_key_delay_std": (90, 20),       
    "dwell_time_mean": (140, 30),
    "swipe_velocity_mean": (280, 80),      
    "session_duration_ms": (95000, 10000), 
    "time_of_day_hour": [2, 3],            
    "direct_to_transfer": 1,               
    "exploratory_ratio": (0.35, 0.08),     
    "is_new_device": 1,                    
    "hand_stability_score": (0.51, 0.1),   
    "time_to_submit_otp_ms": (2100, 300),  
}

def generate_attacker_session(user_id: int):
    features = {}
    
    # Randomly pick from profile
    for key, val in ATTACKER_PROFILE.items():
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
                features[name] = np.random.uniform(20, 50)  # higher variance for attackers
            elif "mean" in name:
                features[name] = np.random.uniform(300, 500) # slower responses for attackers
            elif "count" in name:
                features[name] = np.random.randint(5, 15)  # more interactions (exploratory)
            else:
                features[name] = 0.0

    # Ensure binary features are correct
    features["is_new_device"] = 1
    features["timezone_changed"] = 1
    features["os_version_changed"] = 0
    
    # Navigation depth
    features["navigation_depth_max"] = np.random.randint(2, 4)
    features["screens_visited_count"] = features["navigation_depth_max"] + np.random.randint(1, 4)

    # Reorder to match FEATURE_NAMES and cast to float
    vector = [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
    
    return Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        started_at=datetime.datetime.utcnow(),
        session_type='attacker',
        feature_vector_json=vector
    )

def seed_attacker_data(user_id: int, count: int = 1):
    db = SessionLocal()
    try:
        for _ in range(count):
            session = generate_attacker_session(user_id)
            db.add(session)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_attacker_data(1)
    print("Seeded 1 attacker session for user 1")
