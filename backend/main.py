"""
SHIELD API — FastAPI Entry Point
─────────────────────────────────
Session-based Heuristic Intelligence for Event Level Defense

Startup sequence:
    1. Load .env
    2. Register CORS middleware
    3. Register all routers with prefixes
    4. Initialize database tables
    5. Ensure models directory exists
"""

import sys
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure the root directory is in the path to resolve "backend.xy" imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db.database import init_db
from backend.routers import session, score, enroll, sim_swap, alert, scenarios, features, fleet

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("shield")

# ─────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="SHIELD API",
    description="Session-based Heuristic Intelligence for Event Level Defense",
    version="1.0.0",
)

# CORS — scoped to frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Router Registration
# ─────────────────────────────────────────────────────────────

app.include_router(session.router,   prefix="/session",   tags=["Session"])
app.include_router(score.router,     prefix="/score",     tags=["Score"])
app.include_router(enroll.router,    prefix="/enroll",    tags=["Enrollment"])
app.include_router(sim_swap.router,  prefix="/sim-swap",  tags=["SIM Swap"])
app.include_router(alert.router,     prefix="/alert",     tags=["Alerts"])
app.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
app.include_router(features.router,  prefix="/features",  tags=["Features"])
app.include_router(fleet.router,     prefix="/fleet",     tags=["Fleet"])

# ─────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("SHIELD API starting up...")
    init_db()
    # Ensure models directory exists for pickle files
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml", "models")
    os.makedirs(model_dir, exist_ok=True)
    logger.info("SHIELD API ready.")


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "SHIELD"}


@app.get("/")
def root():
    return {
        "name": "SHIELD API",
        "status": "ACTIVE",
        "docs": "/docs",
        "scenarios": "/scenarios/list",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
