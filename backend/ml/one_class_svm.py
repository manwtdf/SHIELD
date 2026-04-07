import numpy as np
import os
import pickle
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from backend.db.models import SessionLocal, Session, User

MODEL_DIR = os.path.join(os.getcwd(), "backend", "ml", "models")

def get_model_path(user_id: int):
    return os.path.join(MODEL_DIR, f"model_{user_id}.pkl")

def get_scaler_path(user_id: int):
    return os.path.join(MODEL_DIR, f"scaler_{user_id}.pkl")

def get_metadata_path(user_id: int):
    return os.path.join(MODEL_DIR, f"metadata_{user_id}.pkl")

def train_model(user_id: int):
    db = SessionLocal()
    try:
        # Load all legitimate sessions for user
        sessions = db.query(Session).filter(
            Session.user_id == user_id, 
            Session.session_type == 'legitimate'
        ).all()
        
        if len(sessions) < 5:
            return {"error": "Not enough sessions for training (min 5)"}

        X = np.array([s.feature_vector_json for s in sessions])
        
        # StandardScaler fit on X
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train OneClassSVM - Nu=0.01 to be very permissive to legit variance
        model = OneClassSVM(kernel='rbf', nu=0.01, gamma='scale')
        model.fit(X_scaled)
        
        # Calibration using min-max on decision scores
        scores = model.decision_function(X_scaled)
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        # Save model, scaler and calibration metadata
        with open(get_model_path(user_id), 'wb') as f:
            pickle.dump(model, f)
        
        with open(get_scaler_path(user_id), 'wb') as f:
            pickle.dump(scaler, f)
            
        with open(get_metadata_path(user_id), 'wb') as f:
            pickle.dump({
                "min_score": min_score,
                "max_score": max_score,
                "user_id": user_id
            }, f)
            
        return {
            "enrolled": True, 
            "sessions_used": len(sessions), 
            "model_saved": True
        }
    finally:
        db.close()

def predict_score(user_id: int, feature_vector: list):
    # Load model and scaler
    try:
        with open(get_model_path(user_id), 'rb') as f:
            model = pickle.load(f)
        with open(get_scaler_path(user_id), 'rb') as f:
            scaler = pickle.load(f)
        with open(get_metadata_path(user_id), 'rb') as f:
            metadata = pickle.load(f)
    except FileNotFoundError:
        return 50 # Default if model not trained

    X = np.array([feature_vector])
    X_scaled = scaler.transform(X)
    
    raw_score = model.decision_function(X_scaled)[0]
    
    # Min-max normalization for [0-100]
    # We want training range [min, max] to map to [85, 95]
    # Score = 85 + (raw - min)/(max - min) * 10
    
    min_s = metadata["min_score"]
    max_s = metadata["max_score"]
    
    # Range of training scores
    score_range = max_s - min_s
    if score_range < 0.01:
        score_range = 1.0 # Default fallback
        
    # Calibration: map training range to [85, 95]
    if raw_score >= -0.01:
        # Probable legitimate
        if raw_score >= min_s:
            normalized = 85 + (raw_score - min_s) / (score_range + 1e-6) * 10
        else:
            # Slightly below training min but still likely legit
            normalized = 75 + (raw_score / (min_s + 1e-6)) * 10
    else:
        # Outlier
        normalized = 60 - (abs(raw_score) / (abs(min_s) + 0.1)) * 40
        
    return int(max(0, min(100, normalized)))

if __name__ == "__main__":
    res = train_model(1)
    print(res)
