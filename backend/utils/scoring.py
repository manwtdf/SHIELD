import numpy as np
from backend.db.models import SessionLocal, Session
from backend.ml.feature_schema import FEATURE_NAMES

ANOMALY_TEMPLATES = {
    "inter_key_delay_mean": "Typing delay is {pct}% {direction} than baseline.",
    "inter_key_delay_std": "Typing rhythm variance is {pct}% {direction} than normal.",
    "swipe_velocity_mean": "Swipe speed is {pct}% {direction} than baseline.",
    "direct_to_transfer": "Direct navigation to transfer — high-risk path.",
    "is_new_device": "New device fingerprint detected for this account.",
    "time_to_submit_otp_ms": "OTP submitted {pct}% faster than historical average.",
    "exploratory_ratio": "Navigation is {pct}% more exploratory than regular behavior.",
    "session_duration_ms": "Session duration is unusually {direction}.",
    "hand_stability_score": "Device stability is {pct}% below user's baseline.",
    "time_of_day_hour": "Login at {hour}:00 — outside typical user hours.",
    "tap_pressure_mean": "Touch pressure intensity is {direction}.",
    "form_field_order_entropy": "Form interaction sequence is highly atypical.",
}

def get_top_anomalies(user_id: int, current_vector: list, sim_swap_active: bool = False) -> list:
    db = SessionLocal()
    try:
        # Load legitimate sessions for baseline
        sessions = db.query(Session).filter(
            Session.user_id == user_id, 
            Session.session_type == 'legitimate'
        ).all()
        
        if not sessions:
            return ["No baseline data for comparison."]

        X_baseline = np.array([s.feature_vector_json for s in sessions])
        baseline_mean = np.mean(X_baseline, axis=0)
        baseline_std = np.std(X_baseline, axis=0) + 1e-6 # Avoid division by zero
        
        current = np.array(current_vector)
        z_scores = (current - baseline_mean) / baseline_std
        
        # Sort features by absolute z-score
        top_indices = np.argsort(np.abs(z_scores))[::-1]
        
        anomalies = []
        
        # Always add SIM swap if active
        if sim_swap_active:
            anomalies.append("CRITICAL: SIM swap event detected recently.")

        for idx in top_indices:
            if len(anomalies) >= (5 if sim_swap_active else 4):
                break
                
            name = FEATURE_NAMES[idx]
            z = z_scores[idx]
            
            if np.abs(z) < 1.0: # Significant if > 1 std dev
                continue
                
            template = ANOMALY_TEMPLATES.get(name)
            if template:
                direction = "higher" if z > 0 else "lower"
                pct = int(min(1000, np.abs(z) * 100))
                
                # Special cases for certain templates
                msg = template.format(
                    direction=direction, 
                    pct=pct, 
                    hour=int(current[idx]) if name == "time_of_day_hour" else 0
                )
                anomalies.append(msg)
            elif "mean" in name or "std" in name:
                anomalies.append(f"Anomaly in {name.replace('_', ' ')} detected.")

        return anomalies[:4] # Return top 4
    finally:
        db.close()
