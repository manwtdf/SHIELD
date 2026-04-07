from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    enrolled_at = Column(DateTime, default=datetime.datetime.utcnow)
    sessions_count = Column(Integer, default=0)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    session_type = Column(String)   # 'legitimate' | 'attacker'
    device_class = Column(String, default="mobile")  # 'mobile' | 'desktop' | 'tablet'
    feature_vector_json = Column(JSON)

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    computed_at = Column(DateTime, default=datetime.datetime.utcnow)
    confidence_score = Column(Integer)
    risk_level = Column(String)
    top_anomalies_json = Column(JSON)

class SimSwapEvent(Base):
    __tablename__ = "sim_swap_events"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

class AlertLog(Base):
    __tablename__ = "alert_log"
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    alert_type = Column(String)  # 'SMS' | 'LOG'
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    recipient = Column(String)
    message = Column(String)

class DeviceRegistry(Base):
    __tablename__ = "device_registry"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_fingerprint = Column(String)
    device_class = Column(String, default="mobile")   # 'mobile' | 'desktop' | 'tablet'
    trust_level = Column(String, default="new")        # 'new' | 'known' | 'one-time'
    session_count = Column(Integer, default=0)         # sessions on this exact fingerprint
    first_seen = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)

# Database connection
def get_db_path():
    db_dir = os.path.join(os.getcwd(), "backend", "db")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return f"sqlite:///{os.path.join(db_dir, 'shield.db')}"

engine = create_engine(get_db_path())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
