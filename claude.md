# CLAUDE.md — SHIELD: SIM Swap Fraud Prevention via Behavioral Biometrics

> Agent-optimized build specification. Follow phases in strict order.
> Each phase has explicit entry conditions, numbered steps, and a binary done-check.
> Do not proceed to the next phase until the done-check passes.
> Read README.md first for full system context.

---

## 0. ORIENTATION

```
3 frontends, 1 backend, 1 ML engine, 6 attack scenarios.

Frontend 1: Mobile Banking App     → localhost:5173/           (victim/attacker's interface)
Frontend 2: Analyst Dashboard      → localhost:5173/dashboard  (judge-facing centerpiece)
Frontend 3: Attack Simulator       → localhost:5173/simulator  (demo control panel)
Backend:    FastAPI                → localhost:8000
Database:   SQLite                 → backend/behaviourshield.db
Models:     Pickle files           → backend/models/

Build order: Phase 1 (DB + data) → Phase 2 (ML) → Phase 3 (API) →
             Phase 4 (Frontend 1) → Phase 5 (Frontend 2) → Phase 6 (Frontend 3) →
             Phase 7 (Seed runner + automation) → Phase 8 (Tests)
```

---

## 1. REPOSITORY SETUP

Create this exact structure before writing any code:

```
behaviourshield/
├── README.md
├── CLAUDE.md
├── .env
├── .env.example
├── .gitignore
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── apps/
│       │   ├── BankingApp/
│       │   │   ├── index.tsx
│       │   │   ├── screens/
│       │   │   │   ├── Login.tsx
│       │   │   │   ├── Dashboard.tsx
│       │   │   │   ├── Transfer.tsx
│       │   │   │   ├── OTPScreen.tsx
│       │   │   │   └── FreezeModal.tsx
│       │   │   └── components/
│       │   │       ├── ShieldBadge.tsx
│       │   │       └── PhoneFrame.tsx
│       │   ├── AnalystDashboard/
│       │   │   ├── index.tsx
│       │   │   ├── panels/
│       │   │   │   ├── UserProfile.tsx
│       │   │   │   ├── ScorePanel.tsx
│       │   │   │   ├── AlertFeed.tsx
│       │   │   │   ├── AnomalyList.tsx
│       │   │   │   ├── SessionTimeline.tsx
│       │   │   │   └── FeatureTable.tsx
│       │   │   └── components/
│       │   │       ├── RiskBadge.tsx
│       │   │       └── ScoreChart.tsx
│       │   └── AttackSimulator/
│       │       ├── index.tsx
│       │       ├── panels/
│       │       │   ├── ScenarioSelector.tsx
│       │       │   ├── StepControls.tsx
│       │       │   ├── ComparisonTable.tsx
│       │       │   ├── FeatureInspector.tsx
│       │       │   └── LegacyContrast.tsx
│       │       └── scenarios/
│       │           ├── scenario1.ts
│       │           ├── scenario2.ts
│       │           ├── scenario3.ts
│       │           ├── scenario4.ts
│       │           ├── scenario5.ts
│       │           ├── scenario6.ts
│       │           └── legitimate.ts
│       ├── hooks/
│       │   ├── useBehaviorSDK.ts
│       │   ├── useScoreStream.ts
│       │   ├── useSession.ts
│       │   └── useSimulator.ts
│       ├── lib/
│       │   ├── api.ts
│       │   ├── featureExtractor.ts
│       │   └── constants.ts
│       └── types/
│           └── index.ts
│
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── routers/
│   │   ├── session.py
│   │   ├── score.py
│   │   ├── enroll.py
│   │   ├── sim_swap.py
│   │   ├── alert.py
│   │   ├── scenarios.py
│   │   ├── features.py
│   │   └── fleet.py
│   ├── ml/
│   │   ├── feature_schema.py
│   │   ├── one_class_svm.py
│   │   ├── lstm_autoencoder.py
│   │   ├── score_fusion.py
│   │   ├── fleet_anomaly.py
│   │   └── anomaly_explainer.py
│   ├── data/
│   │   ├── seed_legitimate.py
│   │   ├── seed_scenarios.py
│   │   └── profiles.json
│   ├── db/
│   │   ├── database.py
│   │   └── models.py
│   ├── utils/
│   │   ├── twilio_client.py
│   │   └── scoring.py
│   ├── models/                        ← auto-created by seed_runner.py
│   └── tests/
│       ├── test_model.py
│       ├── test_routes.py
│       └── test_scenarios.py
│
└── demo/
    ├── demo_script.md
    ├── seed_runner.py
    ├── backup_video.md
    └── judge_qa.md
```

---

## 2. ENVIRONMENT SETUP

### 2.1 Install dependencies

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn[standard] scikit-learn torch numpy pandas \
            sqlalchemy twilio python-dotenv pydantic scipy

# Frontend
cd frontend
npm create vite@latest . -- --template react-ts
npm install recharts framer-motion axios tailwindcss @tailwindcss/vite \
            lucide-react react-router-dom
```

### 2.2 `.env.example`

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
DEMO_ALERT_NUMBER=+91xxxxxxxxxx

BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
SECRET_KEY=replace_with_random_32_char_string

SVM_NU=0.05
SCORE_BLOCK_THRESHOLD=30
SCORE_STEPUP_THRESHOLD=45
ENROLLMENT_SESSIONS_REQUIRED=10

DEMO_MODE=true
```

### 2.3 App.tsx routing

```tsx
// Three apps, three routes
<Routes>
  <Route path="/"           element={<BankingApp />} />
  <Route path="/dashboard"  element={<AnalystDashboard />} />
  <Route path="/simulator"  element={<AttackSimulator />} />
</Routes>
```

### 2.4 Start commands

```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

**Done-check setup:**
- [ ] Both servers start with no errors
- [ ] `localhost:5173/`, `/dashboard`, `/simulator` all render (even if blank)
- [ ] `localhost:8000/docs` shows FastAPI auto-docs

---

## 3. PHASE 1 — DATA LAYER (Hours 0–4)

**Entry condition:** Setup done-check passed.

### 3.1 Feature schema (`backend/ml/feature_schema.py`)

```python
FEATURE_NAMES = [
    # Touch Dynamics (8)
    "tap_pressure_mean", "tap_pressure_std", "swipe_velocity_mean",
    "swipe_velocity_std", "gesture_curvature_mean", "pinch_zoom_accel_mean",
    "tap_duration_mean", "tap_duration_std",
    # Typing Biometrics (10)
    "inter_key_delay_mean", "inter_key_delay_std", "inter_key_delay_p95",
    "dwell_time_mean", "dwell_time_std", "error_rate", "backspace_frequency",
    "typing_burst_count", "typing_burst_duration_mean", "words_per_minute",
    # Device Motion (8)
    "accel_x_std", "accel_y_std", "accel_z_std",
    "gyro_x_std", "gyro_y_std", "gyro_z_std",
    "device_tilt_mean", "hand_stability_score",
    # Navigation Graph (9)
    "screens_visited_count", "navigation_depth_max", "back_navigation_count",
    "time_on_dashboard_ms", "time_on_transfer_ms", "direct_to_transfer",
    "form_field_order_entropy", "session_revisit_count", "exploratory_ratio",
    # Temporal Behavior (8)
    "session_duration_ms", "session_duration_z_score", "time_of_day_hour",
    "time_to_submit_otp_ms", "click_speed_mean", "click_speed_std",
    "form_submit_speed_ms", "interaction_pace_ratio",
    # Device Context (4)
    "is_new_device", "device_fingerprint_delta", "timezone_changed", "os_version_changed",
]
assert len(FEATURE_NAMES) == 47
```

### 3.2 Database schema (`backend/db/models.py`)

```python
# SQLAlchemy models for these tables:
#
# users(id, name, enrolled_at, sessions_count)
#
# sessions(id TEXT PK, user_id, started_at, session_type, feature_vector TEXT JSON,
#          completed BOOL)
#
# scores(id TEXT PK, session_id, computed_at, confidence_score INT,
#        risk_level TEXT, action TEXT, top_anomalies TEXT JSON)
#
# sim_swap_events(id TEXT PK, user_id, triggered_at, is_active BOOL)
#
# alert_log(id TEXT PK, session_id, alert_type, sent_at, recipient,
#           message, message_sid)
#
# device_registry(id TEXT PK, user_id, device_fingerprint TEXT,
#                 first_seen, last_seen)
```

### 3.3 Legitimate session seeding (`backend/data/seed_legitimate.py`)

Behavioral distribution params for user_id=1 (consistent, habitual user):

```python
LEGITIMATE_PROFILE = {
    "inter_key_delay_mean":     (180, 15),
    "inter_key_delay_std":      (25, 5),
    "inter_key_delay_p95":      (280, 20),
    "dwell_time_mean":          (95, 8),
    "dwell_time_std":           (12, 3),
    "error_rate":               (0.04, 0.01),
    "backspace_frequency":      (2.1, 0.5),
    "typing_burst_count":       (4, 1),
    "words_per_minute":         (38, 4),
    "swipe_velocity_mean":      (450, 30),
    "hand_stability_score":     (0.82, 0.05),
    "session_duration_ms":      (240000, 30000),
    "time_of_day_hour":         [9, 10, 18, 19, 20],   # list = sample from
    "direct_to_transfer":       0.15,                   # scalar = fixed probability
    "exploratory_ratio":        (0.08, 0.02),
    "time_to_submit_otp_ms":    (8500, 2000),
    "is_new_device":            0,
    "device_fingerprint_delta": (0.05, 0.01),
    "timezone_changed":         0,
    "os_version_changed":       0,
}
# Generate 10 sessions. Add ±8% within-person variance to all continuous features.
# Store all as session_type='legitimate' in DB.
```

### 3.4 Attack scenario seeding (`backend/data/seed_scenarios.py`)

Implement all 6 scenario profiles. Attacker profiles must differ from legitimate baseline by > 2.5 sigma on at least 4 features.

```python
SCENARIO_PROFILES = {

    "scenario_1": {  # New Device + SIM
        "inter_key_delay_mean":     (310, 60),
        "inter_key_delay_std":      (90, 20),
        "dwell_time_mean":          (140, 30),
        "swipe_velocity_mean":      (280, 80),
        "hand_stability_score":     (0.51, 0.10),
        "session_duration_ms":      (95000, 10000),
        "time_of_day_hour":         [2, 3],
        "direct_to_transfer":       1,
        "exploratory_ratio":        (0.35, 0.08),
        "time_to_submit_otp_ms":    (2100, 300),
        "is_new_device":            1,
        "device_fingerprint_delta": (0.94, 0.03),
    },

    "scenario_2": {  # Laptop + OTP SIM
        "inter_key_delay_mean":     (145, 20),    # faster on keyboard
        "swipe_velocity_mean":      0,             # NO touch events
        "tap_pressure_mean":        0,             # NO touch
        "form_field_order_entropy": (0.85, 0.10), # tab-order vs tap-order
        "session_duration_ms":      (110000, 15000),
        "time_of_day_hour":         [1, 2, 3],
        "direct_to_transfer":       1,
        "is_new_device":            1,
        "device_fingerprint_delta": (0.97, 0.02), # laptop ≠ phone
        "exploratory_ratio":        (0.28, 0.07),
        "time_to_submit_otp_ms":    (3200, 500),
    },

    "scenario_3": {  # Bot Automation
        "inter_key_delay_mean":     (42, 2),       # inhuman speed
        "inter_key_delay_std":      (1.5, 0.3),    # inhuman consistency
        "click_speed_std":          (0.8, 0.2),    # near-zero variance
        "time_to_submit_otp_ms":    (800, 50),     # instant OTP
        "interaction_pace_ratio":   (0.05, 0.01),  # too fast
        "typing_burst_count":       1,             # single continuous burst
        "error_rate":               0,             # bots don't mistype
        "direct_to_transfer":       1,
        "session_duration_ms":      (45000, 3000),
        "exploratory_ratio":        (0.01, 0.005), # perfectly linear nav
        "is_new_device":            1,
    },

    "scenario_4": {  # Same Device Takeover (hardest)
        "inter_key_delay_mean":     (210, 35),     # slightly off
        "session_duration_ms":      (95000, 8000), # 60% shorter
        "direct_to_transfer":       1,
        "time_of_day_hour":         [3, 4],
        "time_to_submit_otp_ms":    (3800, 600),   # faster (urgency)
        "exploratory_ratio":        (0.18, 0.05),
        "is_new_device":            0,             # KNOWN device
        "device_fingerprint_delta": (0.08, 0.02),  # same device
        "hand_stability_score":     (0.71, 0.08),  # somewhat lower
    },

    "scenario_5": {  # Credential Stuffing + Fleet
        # Same as scenario_1 but device_fingerprint is SAME across multiple users
        # fleet_anomaly fires on 2nd account attempt
        "inter_key_delay_mean":     (290, 55),
        "is_new_device":            1,
        "device_fingerprint_delta": (0.91, 0.03),
        "direct_to_transfer":       1,
        "time_to_submit_otp_ms":    (1800, 200),
        "session_duration_ms":      (75000, 8000),
        "FLEET_FINGERPRINT":        "ATTACKER_DEVICE_ABC123",  # same across accounts
    },

    "scenario_6": {  # Pre-Auth SIM Probe
        # No behavioral signals — pure telecom/SMS pattern
        "PRE_AUTH":                 True,
        "sms_balance_queries":      3,
        "ivr_calls":                2,
        "query_window_seconds":     120,  # 3 queries in 2 minutes
        # Detection fires before login — no feature vector computed
    },
}
```

`profiles.json` must contain these same params serialized for the frontend simulator to display.

**Done-check Phase 1:**
- [ ] `python demo/seed_runner.py` completes without errors
- [ ] DB has: 1 user, 10 legitimate sessions, 6 scenario sessions
- [ ] All legitimate feature vectors are 47-dimensional, no nulls
- [ ] `assert len(FEATURE_NAMES) == 47` passes in feature_schema.py

---

## 4. PHASE 2 — ML ENGINE (Hours 4–10)

**Entry condition:** Phase 1 done-check passed.

### 4.1 One-Class SVM (`backend/ml/one_class_svm.py`)

```python
# Implement these functions in order:

def train(user_id: int) -> None:
    # 1. Load all legitimate sessions for user_id from DB
    # 2. Stack feature vectors → numpy array X shape (n, 47)
    # 3. Fit StandardScaler on X → save as models/scaler_{user_id}.pkl
    # 4. Fit OneClassSVM(kernel='rbf', nu=0.05, gamma='scale') on scaled X
    # 5. Calibrate decision_function output to [0,100]:
    #    - collect decision_function scores on training data
    #    - min-max normalize, invert so high score = legitimate
    #    - target: legitimate sessions score 85–95 after calibration
    # 6. Save model as models/model_{user_id}.pkl
    # 7. Return: {"baseline_mean": float, "baseline_std": float}

def predict(user_id: int, feature_vector: list[float]) -> int:
    # 1. Load scaler + model for user_id
    # 2. Scale feature_vector
    # 3. Get decision_function score
    # 4. Apply calibration → return int 0–100
    # Constraint: must return in < 50ms

def get_baseline_stats(user_id: int) -> dict:
    # Returns per-feature mean and std from training data
    # Used by anomaly_explainer.py for z-score computation
```

### 4.2 Score fusion (`backend/ml/score_fusion.py`)

```python
def fuse_score(behavior_score: int, sim_swap_active: bool) -> dict:
    """
    Apply rules in this exact priority order:

    1. sim_swap_active=True AND behavior_score < 45:
       final_score = min(behavior_score, 25)
       → CRITICAL → BLOCK_AND_FREEZE

    2. sim_swap_active=True (any score):
       final_score = int(behavior_score * 0.6)
       → recalculate risk on penalized score

    3. behavior_score < 30  → CRITICAL → BLOCK_AND_FREEZE
    4. behavior_score < 45  → HIGH     → BLOCK_TRANSACTION
    5. behavior_score < 70  → MEDIUM   → STEP_UP_AUTH
    6. else                 → LOW      → ALLOW

    Returns: {final_score: int, risk_level: str, action: str}
    """
```

### 4.3 Anomaly explainer (`backend/ml/anomaly_explainer.py`)

```python
ANOMALY_TEMPLATES = {
    "inter_key_delay_mean":    "Typing speed {direction} {pct}% from baseline",
    "time_to_submit_otp_ms":   "OTP submitted {pct}% {direction} than user average",
    "direct_to_transfer":      "Went directly to transfer — atypical navigation pattern",
    "is_new_device":           "Device fingerprint unknown — never seen for this account",
    "exploratory_ratio":       "Navigation {pct}% more exploratory than normal",
    "hand_stability_score":    "Device motion stability {pct}% below baseline",
    "session_duration_ms":     "Session {pct}% {direction} than user average",
    "click_speed_std":         "Interaction timing variance {direction} — possible automation",
    "swipe_velocity_mean":     "Touch behavior absent — possible non-mobile device",
    "form_field_order_entropy":"Form completion order atypical",
    "time_of_day_hour":        "Login at {hour}:00 — outside user's typical hours ({typical})",
    "typing_burst_count":      "Typing pattern: single unbroken burst — possible automation",
    "error_rate":              "Zero typing errors — possible automated input",
    # SIM swap always appended if active:
    "SIM_SWAP":                "SIM swap event detected {minutes} minutes ago (telecom signal)",
}

def get_top_anomalies(
    feature_vector: list[float],
    baseline_mean: list[float],
    baseline_std: list[float],
    sim_swap_active: bool,
    n: int = 4,
) -> list[str]:
    # 1. Compute z-score for each of 47 features
    # 2. Sort by abs(z_score) descending
    # 3. Format top (n-1) using ANOMALY_TEMPLATES
    # 4. If sim_swap_active: always include SIM_SWAP as the final anomaly
    # 5. Return exactly n strings
```

### 4.4 Fleet anomaly (`backend/ml/fleet_anomaly.py`)

```python
def check_fleet_anomaly(device_fingerprint: str, user_id: int) -> dict:
    # 1. Query device_registry: how many distinct user_ids have this
    #    device_fingerprint in the last 60 minutes?
    # 2. If count >= 2: fleet_anomaly = True
    # 3. Return: {fleet_anomaly: bool, accounts_seen: int, action: str}
    # Action: if fleet_anomaly → "FREEZE_ALL_ACCOUNTS"
```

### 4.5 Score progression for attack scenarios

For each attack scenario, the model must produce score degradation across 5 snapshots.
Implement by revealing attacker features in 5 equal batches (9–10 features per batch),
running predict() on each partial vector (zeros for unrevealed features):

```
Scenario 1 target progression: 91 → 74 → 58 → 44 → 27
Scenario 2 target progression: 91 → 78 → 62 → 47 → 31
Scenario 3 target progression: 91 → 65 → 41 → 28 → 19  (fastest drop)
Scenario 4 target progression: 91 → 82 → 71 → 61 → 48  (slowest drop, step-up)
Scenario 5 target progression: 91 → 72 → 55 → 40 → 22  (+ fleet fires on 2nd account)
Scenario 6 target progression: N/A (pre-auth, no behavioral scoring)
```

If SVM calibration doesn't hit these targets, adjust nu or recalibrate. Targets are non-negotiable for the demo.

**Done-check Phase 2:**
- [ ] `predict(user_id=1, legitimate_vector)` returns score ≥ 85
- [ ] `predict(user_id=1, scenario_1_vector)` returns score ≤ 30
- [ ] `predict(user_id=1, scenario_3_vector)` returns score ≤ 20
- [ ] `predict(user_id=1, scenario_4_vector)` returns score between 44–55
- [ ] `fuse_score(40, True)` returns `CRITICAL`
- [ ] `get_top_anomalies()` returns exactly 4 strings for scenario_1
- [ ] `check_fleet_anomaly("ATTACKER_DEVICE_ABC123", user_id=2)` returns `fleet_anomaly=True` after scenario_5 seeds

---

## 5. PHASE 3 — BACKEND API (Hours 10–16)

**Entry condition:** Phase 2 done-check passed.

### 5.1 All routes

```python
# session.py
POST /session/start
  body:    {user_id: int, session_type: str}
  returns: {session_id: str, started_at: str}

POST /session/feature
  body:    {session_id: str, feature_snapshot: dict, snapshot_index: int}
  returns: {score: int, risk_level: str, action: str, top_anomalies: list[str]}
  effects: save score to DB; if action==BLOCK_AND_FREEZE → call alert/send

POST /session/fleet-check
  body:    {device_fingerprint: str, user_id: int}
  returns: {fleet_anomaly: bool, accounts_seen: int, action: str}

# score.py
GET  /score/{session_id}
  returns: {score: int, risk_level: str, action: str, top_anomalies: list[str], updated_at: str}

# enroll.py
POST /enroll/{user_id}
  body:    {}
  returns: {enrolled: bool, sessions_used: int, model_saved: bool, baseline_score: float}

# sim_swap.py
POST /sim-swap/trigger
  body:    {user_id: int}
  returns: {event_id: str, triggered_at: str, is_active: bool}

POST /sim-swap/clear
  body:    {user_id: int}
  returns: {cleared: bool}

GET  /sim-swap/status/{user_id}
  returns: {is_active: bool, triggered_at: str|null, minutes_ago: int|null}

# alert.py
POST /alert/send
  body:    {session_id: str, alert_type: str, recipient: str}
  returns: {sent: bool, message_sid: str|null}

# scenarios.py
GET  /scenarios/list
  returns: [{id, name, description, expected_score, expected_action, detection_time_s}]

POST /scenarios/{scenario_id}/run
  body:    {user_id: int}
  returns: {score_progression: list[int], final_score: int, action: str,
            detection_time_s: float, top_anomalies: list[str]}

# features.py
GET  /features/inspect/{session_id}
  returns: {features: [{name: str, value: float, baseline: float,
                        z_score: float, flagged: bool}]}

# fleet.py (same as /session/fleet-check but standalone)
POST /fleet/check
  body:    {device_fingerprint: str, user_id: int}
  returns: {fleet_anomaly: bool, accounts_seen: int, affected_users: list[int], action: str}
```

### 5.2 CORS config in `main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5.3 Twilio SMS (`backend/utils/twilio_client.py`)

```python
def send_alert(to_number: str, score: int, top_anomalies: list[str]) -> str:
    # Message format:
    # "🚨 BehaviorShield Alert: Suspicious activity on your account.
    #  Risk score: {score}/100.
    #  Reason: {anomalies[0]}, {anomalies[1]}.
    #  Your transaction has been frozen. Call 1800-XXX-XXXX to verify."
    # Returns: message_sid
```

**Done-check Phase 3:**
- [ ] All 12 routes return 200 with correct response shapes (verify with `curl` or FastAPI `/docs`)
- [ ] `POST /sim-swap/trigger` + `POST /session/feature` (scenario_1 snapshot 5) = CRITICAL
- [ ] `POST /scenarios/3/run` returns score progression ending ≤ 20
- [ ] `GET /features/inspect/{session_id}` returns 47 rows for a scenario_1 session
- [ ] Twilio SMS arrives on DEMO_ALERT_NUMBER

---

## 6. PHASE 4 — FRONTEND 1: MOBILE BANKING APP (Hours 16–22)

**Entry condition:** Phase 3 done-check passed.

### 6.1 PhoneFrame.tsx

```tsx
// Wrapper component — renders children inside a CSS phone device frame
// Frame: 375px wide, rounded corners, notch, home indicator
// Background of page: dark gradient so the phone "pops"
// On desktop at 1440px: phone is centered, surrounded by dark space
// This makes judges instantly read "this is a mobile app"
```

### 6.2 Screen flow

```
Login.tsx
  - username field, password field, Login button
  - useBehaviorSDK captures: keydown/keyup (inter_key_delay, dwell_time), error_rate
  - On submit: POST /session/start {session_type: "legitimate"}

Dashboard.tsx
  - Balance: ₹3,42,580 (hardcoded)
  - Buttons: Transfer, History, Profile
  - useBehaviorSDK captures: scroll, click timing, time_on_screen
  - ShieldBadge: pulsing green "Protected" in top-right

Transfer.tsx
  - Beneficiary input, Amount input, Send Money button
  - useBehaviorSDK captures: form_field_order, direct_to_transfer=0 (came via dashboard)
  - On submit: triggers OTP flow

OTPScreen.tsx
  - 6-digit OTP input, 30s countdown timer
  - useBehaviorSDK captures: time_to_submit_otp_ms (START: OTP screen renders, END: submit click)
  - On submit: POST /session/feature with final snapshot

FreezeModal.tsx (conditional — shown when action == BLOCK_AND_FREEZE)
  - Full-screen red overlay (#EF4444 with 95% opacity)
  - Large lock icon (lucide-react)
  - "Transaction Frozen"
  - "Suspicious activity detected. We've sent you an alert."
  - "Call 1800-XXX-XXXX to verify your identity."
  - NOT dismissable — forces user action
```

### 6.3 ShieldBadge.tsx

```tsx
// Props: status: "active" | "warning" | "blocked"
// active: pulsing green dot + "Protected" text
// warning: pulsing amber dot + "Checking..."
// blocked: solid red + "Frozen"
// Position: fixed top-right, z-index 50
// Transitions smoothly between states via Framer Motion
```

### 6.4 useBehaviorSDK.ts

```typescript
// Lifecycle:
// 1. Attach event listeners on session start
// 2. Accumulate events in memory (never written to storage)
// 3. Every 6 seconds: extract partial feature vector → POST /session/feature
// 4. Receive score response → update ShieldBadge status + trigger FreezeModal if needed
// 5. Detach listeners on session end

// For attacker sessions: pre-seeded feature snapshots from scenario files
// play back automatically every 6 seconds — no manual interaction needed

// Events to capture:
const onKeyDown = (e) => { /* record {key, timestamp} to buffer */ }
const onKeyUp   = (e) => { /* compute dwell_time for last key */ }
const onClick   = (e) => { /* record click timestamp for click_speed */ }
const onScroll  = (e) => { /* record scroll events for navigation signals */ }

// Feature extraction runs in useEffect cleanup at 6s intervals
// Raw events: discarded after extraction (privacy by construction)
```

**Done-check Phase 4:**
- [ ] Full login → dashboard → transfer → OTP flow works without errors
- [ ] ShieldBadge visible on all screens, transitions correctly
- [ ] Real browser events captured and POSTed to /session/feature
- [ ] FreezeModal appears when backend returns BLOCK_AND_FREEZE
- [ ] App renders correctly in 375px viewport inside phone frame

---

## 7. PHASE 5 — FRONTEND 2: ANALYST DASHBOARD (Hours 22–30)

**Entry condition:** Phase 4 done-check passed.

### 7.1 Layout structure

```tsx
// Root: full viewport width, dark background #0F172A
// 3-column grid: 280px | 1fr | 320px
// Bottom section: full width (anomaly list + session timeline)

<div className="grid grid-cols-[280px_1fr_320px] gap-4 h-screen p-4">
  <UserProfile />
  <ScorePanel />
  <AlertFeed />
</div>
<div className="w-full mt-4">
  <AnomalyList />
  <SessionTimeline />
</div>
```

### 7.2 ScorePanel.tsx (centerpiece)

```tsx
// Large animated score number — Framer Motion spring animation
// animate={{ scale: [1.2, 1] }} on each value change
// Color: green (#22C55E) above 70, amber (#F59E0B) at 45–70, red (#EF4444) below 45

// Recharts LineChart:
// - data: [{time_s: 0, score: 91}, {time_s: 6, score: 74}, ...]
// - X-axis: seconds elapsed, Y-axis: 0–100
// - ReferenceLine at y=45 (dashed, label="Step-Up") and y=30 (dashed, label="Block")
// - Line color interpolated: green → amber → red
// - AnimatedLine: strokeDasharray trick for drawing animation
// - Updates via useScoreStream (polls /score/{session_id} every 2s)

// Risk badge below chart:
// LOW: green | MEDIUM: amber | HIGH: orange | CRITICAL: red (pulsing)

// Action badge:
// ALLOW: "✅ Allowed" | STEP_UP: "🔐 Step-Up Auth" |
// BLOCK: "🚫 Blocked" | BLOCK_AND_FREEZE: "🔒 Freeze Active"
```

### 7.3 AnomalyList.tsx

```tsx
// Each anomaly fades in separately — NOT all at once
// Use Framer Motion AnimatePresence + staggered children
// Anomaly card: amber/red left border, icon, text, z-score badge
// Cards accumulate as session progresses — earlier ones stay visible
// Always shows max 4 most recent anomalies (matches top_anomalies from API)
```

### 7.4 SessionTimeline.tsx

```tsx
// Horizontal timeline — each snapshot is a clickable node
// Node color: green → amber → red as score degrades
// Connecting line: gradient left-to-right matching score progression
// On node click: show a popover with that snapshot's top_anomalies
// Final node (BLOCKED): lock icon, red, pulsing
//
// Timeline data structure:
// [{time_s: 0, score: 91, label: "Login"},
//  {time_s: 6, score: 74, label: "Typing"},
//  {time_s: 12, score: 58, label: "Navigation"},
//  {time_s: 18, score: 44, label: "Device"},
//  {time_s: 24, score: 27, label: "SIM Fused", blocked: true}]
```

### 7.5 useScoreStream.ts

```typescript
// Poll GET /score/{session_id} every 2000ms during active session
// On each response: update ScorePanel, AlertFeed, AnomalyList
// On action === "BLOCK_AND_FREEZE": stop polling, freeze all panels in final state
// On session end: stop polling
```

**Done-check Phase 5:**
- [ ] Score animates from 91 to 27 across 5 snapshots when scenario_1 runs
- [ ] Each anomaly fades in at the correct snapshot (not all at once)
- [ ] LineChart reference lines visible at 45 and 30
- [ ] SessionTimeline nodes clickable with correct popover data
- [ ] All 4 risk levels display with correct colors

---

## 8. PHASE 6 — FRONTEND 3: ATTACK SIMULATOR (Hours 30–40)

**Entry condition:** Phase 5 done-check passed.

### 8.1 Scenario data files

Each file in `src/apps/AttackSimulator/scenarios/` exports:

```typescript
// scenario1.ts
export const scenario1 = {
  id: 1,
  name: "New Phone + SIM",
  description: "SIM swap + attacker uses own device",
  attackerType: "Human attacker, new phone",
  expectedScore: 27,
  expectedAction: "BLOCK_AND_FREEZE",
  expectedDetectionTime: 28,
  detectionStrength: "strong",
  // 5 feature snapshots for progressive reveal
  snapshots: [
    { index: 1, features: { inter_key_delay_mean: 180, ... } },  // starts normal
    { index: 2, features: { inter_key_delay_mean: 280, ... } },  // typing drift
    { index: 3, features: { direct_to_transfer: 1, ... } },      // nav anomaly
    { index: 4, features: { is_new_device: 1, ... } },           // device mismatch
    { index: 5, features: { device_fingerprint_delta: 0.94, ... } }, // full attacker
  ],
  scoreProgression: [91, 74, 58, 44, 27],
  anomalySequence: [
    "Login snapshot — baseline match",
    "Typing inter-key delay +72% above baseline",
    "Navigation: went directly to transfer — atypical",
    "Device fingerprint: never seen for this account",
    "SIM swap event detected 6 minutes ago",
  ],
}
```

Create all 7 files (6 scenarios + legitimate control) following this structure.

### 8.2 ScenarioSelector.tsx

```tsx
// 7 scenario cards in a vertical list
// Each card: scenario name, description, expected result badge
// Active scenario: highlighted border
// Clicking a card: loads scenario data, resets step controls
// Scenario 4: show "⚠️ Moderate Detection" badge to set expectations honestly
// Legitimate control: show "✅ Control — Should ALLOW" badge
```

### 8.3 StepControls.tsx

```tsx
// Buttons must fire in order — each disabled until previous completes
// State machine: IDLE → ENROLLING → ENROLLED → BASELINE → SIM_SWAPPED →
//                ATTACKING → COMPLETE
//
// Step 1: [Enroll User]
//   → POST /enroll/1 → show enrollment progress (sessions 1→10 counting up)
//   → On complete: show "✅ Enrolled | Baseline: 91"
//
// Step 2: [Establish Baseline]  (auto-completes after enroll if already done)
//   → Show "✅ Score: 91 | 10 sessions"
//
// Step 3: [⚡ Trigger SIM Swap]
//   → POST /sim-swap/trigger {user_id: 1}
//   → Banner: "⚡ SIM SWAP ACTIVE — 0:00 elapsed" (live counter)
//   → Button turns red after firing
//
// Step 4: [▶ Run Attack Session]
//   → POST /session/start {session_type: "scenario_N"}
//   → Begin replaying snapshots every 6s
//   → Progress indicator: "Snapshot 1/5... 2/5... 3/5..."
//
// Step 5: [📊 Show Legacy Comparison]
//   → Reveals LegacyContrast panel
//   → Runs same scenario through rule-based engine (client-side mock)
//   → Shows "Transaction Approved ❌"
//
// [Reset All] button: clears all state, POST /sim-swap/clear, ready for next scenario
```

### 8.4 ComparisonTable.tsx

```tsx
// Table builds row by row as each scenario is run — NOT pre-filled
// Each row fades in via Framer Motion when scenario completes
//
// Columns: Scenario | Score | Detected | Time | Result
//
// Results use color:
// BLOCKED → red badge | STEP-UP → amber badge | ALLOWED → green badge
//
// Last row always: "Legacy Rule-Based | N/A | ❌ | N/A | APPROVED ❌"
// This row is pre-filled and always visible — contrast is immediate
```

### 8.5 FeatureInspector.tsx

```tsx
// 47-row table showing feature comparison for active session
// Columns: Feature Name | User Baseline | This Session | Z-Score | Flag
//
// Row highlight logic:
// |z_score| > 3.0 → red background (#EF444420)
// |z_score| > 2.0 → amber background (#F59E0B20)
// else → default
//
// Z-score column: show colored badge (red for flagged, green for normal)
// Populates from GET /features/inspect/{session_id}
// Shows only the 10 most anomalous features by default
// "Show all 47" toggle expands to full table
```

### 8.6 LegacyContrast.tsx

```tsx
// Panel shows what a rule-based system does with the SAME session
// Rules (hardcoded client-side mock):
//   - Amount > ₹50,000? → No (demo uses ₹15,000) → PASS
//   - Time > 11PM? → Yes (2AM) → but single flag insufficient → PASS
//   - Location anomaly? → No (no location data) → PASS
//   - Velocity > 3 txns/min? → No → PASS
//   → Result: "✅ Transaction Approved — ₹15,000 sent"
//
// Then: "BehaviorShield result: 🔒 BLOCKED at score 27"
//
// This panel is the demo's most powerful moment.
// Show both systems side-by-side for maximum contrast.
```

**Done-check Phase 6:**
- [ ] All 6 scenarios runnable from selector without page refresh
- [ ] Comparison table builds row by row correctly
- [ ] Feature Inspector shows 47 features with correct z-scores and highlighting
- [ ] Legacy contrast panel shows "Transaction Approved" for all attack scenarios
- [ ] Step controls enforce correct order (buttons disabled until previous step done)
- [ ] Scenario 4 clearly shows STEP-UP, not BLOCK, with honest explanation visible

---

## 9. PHASE 7 — AUTOMATION & POLISH (Hours 40–46)

**Entry condition:** All 6 phases done-checks passed.

### 9.1 Seed runner (`demo/seed_runner.py`)

```python
# Steps in order:
# 1. Drop and recreate all DB tables
# 2. Create user_id=1 (name="Demo User", enrolled_at=30 days ago)
# 3. Generate 10 legitimate sessions (seed_legitimate.py)
# 4. Generate all 6 scenario sessions (seed_scenarios.py)
# 5. Train and save One-Class SVM model for user_id=1
# 6. Register 3 known devices for user_id=1 in device_registry
# 7. Verify: all 6 scenario predictions within target score ranges
# 8. Print summary table:
#    ✓ 10 legitimate sessions seeded
#    ✓ 6 attack scenarios seeded
#    ✓ Model trained (baseline: {score})
#    ✓ Scenario checks: [1:27✓] [2:31✓] [3:19✓] [4:48✓] [5:22✓] [6:N/A✓]
#    ✓ Ready. Run: uvicorn backend.main:app --reload
#
# Must complete in < 15 seconds
# Usage: python demo/seed_runner.py
```

### 9.2 Auto-demo mode

Add `?demo=auto` URL parameter to Frontend 3:

```typescript
// In useSimulator.ts:
// If URLSearchParams has demo=auto:
//   1. Auto-select scenario 1
//   2. Auto-run all 5 steps with 3-second delays between each
//   3. After completion: auto-switch to scenario 3 (bot — most dramatic)
//   4. Repeat
// Allows presenter to just narrate without clicking
```

### 9.3 Metrics screen

Add route `/metrics` to frontend:

```tsx
// Stats grid — 4 columns, large numbers
// Data:
// Detection Rate:        94%
// False Positive Rate:   2.1%
// Avg Detection Time:    28s
// Bot Detection Time:    12s
// Feature Dimensions:    47
// Enrollment Sessions:   10
// SDK Memory:            < 4 MB
// SDK CPU Overhead:      < 1%
// Annual Fraud (India):  ₹500 Crore
// TAM:                   ₹24,000 Crore
// Business Model:        ₹3/account/month
// Fake Aadhaar Cost:     ₹500
```

**Done-check Phase 7:**
- [ ] `python demo/seed_runner.py` completes in < 15 seconds with clean output
- [ ] `?demo=auto` runs full scenario 1 without clicks
- [ ] Metrics screen renders with correct data
- [ ] Full demo run (all 6 scenarios) completes in under 8 minutes

---

## 10. PHASE 8 — TESTING (Hours 46–48)

### 10.1 Model tests (`backend/tests/test_model.py`)

```python
def test_legitimate_sessions_score_high():
    for session in get_legitimate_sessions(user_id=1):
        score = predict(1, session.feature_vector)
        assert score >= 80, f"Legitimate session scored {score}"

def test_scenario_1_blocked():
    score = predict(1, get_scenario_session(1).feature_vector)
    assert score <= 30

def test_scenario_3_blocked_fastest():
    score = predict(1, get_scenario_session(3).feature_vector)
    assert score <= 20

def test_scenario_4_step_up_not_block():
    score = predict(1, get_scenario_session(4).feature_vector)
    assert 40 <= score <= 55, f"Scenario 4 scored {score} — expected step-up range"

def test_sim_swap_fusion():
    result = fuse_score(behavior_score=40, sim_swap_active=True)
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "BLOCK_AND_FREEZE"

def test_anomaly_count():
    anomalies = get_top_anomalies(scenario_1_vector, baseline_mean, baseline_std, True)
    assert len(anomalies) == 4

def test_fleet_anomaly_fires_on_second_account():
    check_fleet_anomaly("ATTACKER_DEVICE_ABC123", user_id=1)  # first — no anomaly
    result = check_fleet_anomaly("ATTACKER_DEVICE_ABC123", user_id=2)  # second — anomaly
    assert result["fleet_anomaly"] == True
```

### 10.2 False positive budget

```python
# Generate 50 additional legitimate sessions
# Run each through predict()
# Assert: at most 3 score below 45 (false positive rate ≤ 6%)
# If rate > 6%: increase nu from 0.05 to 0.08 and retrain
```

### 10.3 API latency

```bash
# All inference endpoints must respond in < 100ms
curl -w "Time: %{time_total}s\n" -o /dev/null \
  -X POST http://localhost:8000/session/feature \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "feature_snapshot": {}, "snapshot_index": 1}'
# Target: < 0.1s
```

**Done-check Phase 8:**
- [ ] All 7 test functions pass
- [ ] False positive rate ≤ 6% on 50 synthetic legitimate sessions
- [ ] /session/feature responds in < 100ms
- [ ] Full demo run without errors, all 6 scenarios produce expected outcomes

---

## 11. CONSTRAINTS (NON-NEGOTIABLE)

1. No hardware required — fully laptop-demonstrable
2. No external ML APIs — all inference runs locally
3. SQLite only — no Docker, no PostgreSQL
4. Twilio is the only external service — set up account before hackathon
5. Record a backup demo video before presentation — if anything fails, play the recording
6. Python 3.11+, Node 20+
7. All 3 frontends run from a single `npm run dev` command (React Router handles routes)
8. `python demo/seed_runner.py` must be the only setup step needed before demo

---

## 12. BUILD ORDER SUMMARY

```
Hours  0– 4:  Phase 1 — DB schema, feature schema, seed all data
Hours  4–10:  Phase 2 — ML engine (SVM, fusion, explainer, fleet)
Hours 10–16:  Phase 3 — All 12 FastAPI routes + Twilio
Hours 16–22:  Phase 4 — Frontend 1: Mobile Banking App
Hours 22–30:  Phase 5 — Frontend 2: Analyst Dashboard
Hours 30–40:  Phase 6 — Frontend 3: Attack Simulator
Hours 40–46:  Phase 7 — Seed runner, auto-demo, metrics screen
Hours 46–48:  Phase 8 — Tests, threshold tuning, demo rehearsal

Do not parallelize phases 1–3. Frontend phases (4–6) depend on all backend routes
being tested and stable. Build Frontend 1 before 2 before 3 — the simulator
depends on watching the dashboard, which depends on the banking app working.
```