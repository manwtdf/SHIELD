import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.models import init_db
from backend.routers import session, score, enroll, sim_swap, alert, scenarios, features, fleet

app = FastAPI(
    title="SHIELD API",
    description="Behavioral Biometric Fraud Prevention for SIM Swap Defense",
    version="1.0.0"
)

# CORS Configuration
# Restricting to demo frontend as per claude.md
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"], # * for broader demo flexibility if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Register Modular Routers
app.include_router(session.router)
app.include_router(score.router)
app.include_router(enroll.router)
app.include_router(sim_swap.router)
app.include_router(alert.router)
app.include_router(scenarios.router)
app.include_router(features.router)
app.include_router(fleet.router)

@app.get("/")
def read_root():
    return {
        "name": "SHIELD API",
        "status": "[ACTIVE]",
        "docs": "/docs",
        "scenarios": "/scenarios/list"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
