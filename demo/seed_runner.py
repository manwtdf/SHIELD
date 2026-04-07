import sys
import os
import datetime

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.models import init_db, SessionLocal, User, Base, engine
from backend.data.seed_legitimate import seed_legitimate_data
from backend.data.seed_attacker import seed_attacker_data
from backend.ml.one_class_svm import train_model

def run_seed():
    print("--- SHIELD DEMO SEED RUNNER ---")
    print("Step 1: Dropping and recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    db = SessionLocal()
    try:
        print("Step 2: Creating user Atharva Kumar (user_id=1)...")
        user = User(
            id=1, 
            name="Atharva Kumar", 
            enrolled_at=datetime.datetime.utcnow() - datetime.timedelta(days=30),
            sessions_count=0
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    print("Step 3: Seeding 10 legitimate sessions for training baseline...")
    seed_legitimate_data(1, 10)
    
    print("Step 4: Seeding 1 attacker session for anomaly testing...")
    seed_attacker_data(1, 1)

    print("Step 5: Training One-Class SVM model for User 1...")
    result = train_model(1)
    if result.get("enrolled"):
        print(f"✓ Model trained successfully using {result['sessions_used']} sessions.")
    else:
        print(f"✗ Model training failed: {result.get('error')}")

    print("\n" + "="*40)
    print("✓ SHIELD DEMO READY")
    print("="*40)
    print("Next commands:")
    print("1. Terminal 1: python -m backend.main")
    print("2. Terminal 2: cd frontend && npm run dev")
    print("="*40)

if __name__ == "__main__":
    run_seed()
