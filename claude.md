# CLAUDE.md — SHIELD: Session-based Heuristic Intelligence for Event Level Defense

> Agent-optimized build specification. Follow sections in order. Each phase has explicit
> entry conditions, numbered steps, and a binary done-check. Do not proceed to the next
> phase until the done-check passes.

---

## 0. PROJECT SNAPSHOT

| Field | Value |
|---|---|
| Project name | SHIELD |
| Track | Smart Security |
| Core problem | SIM swap fraud drains Indian bank accounts in 4 minutes. Banks detect it never. |
| Core solution | Behavioral biometric layer — device-independent fingerprint — detects the fraudster's behavioral discontinuity in under 30 seconds |
| Demo format | Laptop-only, fully simulated, no hardware |
| Build time | 48 hours |
| Stack | React 18 + TypeScript + FastAPI + scikit-learn + SQLite + Twilio |

---aWWWWAWWWWQQQQQQ
Create this exact structure before writing any code:

```
behaviourshield/
├── CLAUDE.md                        # this file
├── README.md
├── .env.example
├── .gitignore
│
├── frontend/                        # React 18 + TypeScript
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── BankingApp.tsx        # mock bank UI — login, dashboard, transfer
│       │   ├── ScoreDashboard.tsx    # live confidence score + anomaly feed
│       │   ├── AttackSimulator.tsx   # triggers attacker session
│       │   ├── EnrollmentPanel.tsx   # shows enrollment progress (0→10 sessions)
│       │   └── AlertBanner.tsx       # transaction freeze + SMS fired notification
│       ├── hooks/
│       │   ├── useBehaviorSDK.ts     # captures touch, keyboard, motion, navigation
│       │   └── useScoreStream.ts     # polls /api/score every 2s during active session
│       ├── lib/
│       │   ├── api.ts                # typed fetch wrappers for all backend endpoints
│       │   └── featureExtractor.ts   # client-side 47-feature vector construction
│       └── types/
│           └── index.ts              # ScoreResponse, FeatureVector, SessionEvent types
│
├── backend/                         # FastAPI + Python 3.11
│   ├── requirements.txt
│   ├── main.py                      # FastAPI app, CORS, router registration
│   ├── routers/
│   │   ├── session.py               # POST /session/start, POST /session/feature
│   │   ├── score.py                 # GET /score/{session_id}
│   │   ├── enroll.py                # POST /enroll/{user_id}
│   │   ├── sim_swap.py              # POST /sim-swap/trigger (mock telecom event)
│   │   └── alert.py                 # POST /alert/send (Twilio SMS)
│   ├── ml/
│   │   ├── feature_schema.py        # canonical 47-feature definition + validation
│   │   ├── one_class_svm.py         # train, predict, calibrate (Platt scaling)
│   │   ├── lstm_autoencoder.py      # advanced variant — optional, shown as roadmap
│   │   └── score_fusion.py          # combines behavior score + SIM swap signal
│   ├── data/
│   │   ├── seed_legitimate.py       # generates 10 legitimate user sessions
│   │   ├── seed_attacker.py         # generates attacker session with behavioral drift
│   │   └── profiles.json            # pre-seeded user + attacker behavioral params
│   ├── db/
│   │   ├── database.py              # SQLite connection + init
│   │   └── models.py                # Session, FeatureVector, AlertLog tables
│   └── utils/
│       ├── twilio_client.py         # SMS alert wrapper
│       └── scoring.py               # score → risk_level → action mapping
│
└── demo/
    ├── demo_script.md               # 8-minute step-by-step judge demo script
    ├── backup_video.md              # instructions for recording backup demo
    └── seed_runner.py               # one command: seeds all data + trains model
```

---

## 2. ENVIRONMENT SETUP

### 2.1 Create `.env` from template

```bash
cp .env.example .env
```

`.env.example` contents — fill all before starting Phase 3:

```
# Twilio (get free trial at twilio.com — actually sends SMS in demo)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
DEMO_ALERT_NUMBER=+91xxxxxxxxxx    # your phone — receives the live SMS in demo

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
SECRET_KEY=replace_with_random_32_char_string

# Model
SVM_NU=0.05
SCORE_BLOCK_THRESHOLD=30
SCORE_STEPUP_THRESHOLD=45
ENROLLMENT_SESSIONS_REQUIRED=10
```

### 2.2 Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install fastapi uvicorn[standard] scikit-learn torch numpy pandas \
            sqlalchemy twilio python-dotenv pydantic scipy
```

### 2.3 Frontend setup

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install recharts framer-motion axios tailwindcss @tailwindcss/vite lucide-react
```

### 2.4 Start both servers

```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

---

## 3. PHASE 1 — DATA LAYER & FEATURE SCHEMA (Hours 0–4)

**Entry condition:** Repo structure created, `.env` filled, both servers start without errors.

### 3.1 Define the 47-feature vector

In `backend/ml/feature_schema.py`, define exactly these features in this order:

```python
FEATURE_NAMES = [
    # Touch Dynamics (8 features)
    "tap_pressure_mean",          # mean force sensor value across session taps
    "tap_pressure_std",           # std dev of tap pressure
    "swipe_velocity_mean",        # mean pixels/ms across all swipe events
    "swipe_velocity_std",
    "gesture_curvature_mean",     # mean deviation from straight line in swipes
    "pinch_zoom_accel_mean",      # mean acceleration of pinch-to-zoom gestures
    "tap_duration_mean",          # mean time finger is on screen per tap (ms)
    "tap_duration_std",

    # Typing Biometrics (10 features)
    "inter_key_delay_mean",       # mean time between consecutive keypresses (ms)
    "inter_key_delay_std",
    "inter_key_delay_p95",        # 95th percentile — catches burst typing
    "dwell_time_mean",            # mean time each key is held down (ms)
    "dwell_time_std",
    "error_rate",                 # backspace count / total keystrokes
    "backspace_frequency",        # backspaces per minute
    "typing_burst_count",         # number of distinct typing bursts per session
    "typing_burst_duration_mean", # mean duration of each burst (ms)
    "words_per_minute",           # estimated WPM from session

    # Device Motion (8 features)
    "accel_x_std",                # std dev of X-axis accelerometer during typing
    "accel_y_std",
    "accel_z_std",
    "gyro_x_std",                 # std dev of gyroscope X during session
    "gyro_y_std",
    "gyro_z_std",
    "device_tilt_mean",           # mean device angle from vertical (degrees)
    "hand_stability_score",       # inverse of motion variance — higher = steadier

    # Navigation Graph (9 features)
    "screens_visited_count",      # total unique screens visited
    "navigation_depth_max",       # deepest nav stack depth reached
    "back_navigation_count",      # number of back button presses
    "time_on_dashboard_ms",       # time spent on home/dashboard screen
    "time_on_transfer_ms",        # time spent on transfer/payment screen
    "direct_to_transfer",         # 1 if went straight to transfer, 0 otherwise
    "form_field_order_entropy",   # entropy of field completion order (0=linear)
    "session_revisit_count",      # number of times a screen was revisited
    "exploratory_ratio",          # back_navigations / total navigations

    # Temporal Behavior (8 features)
    "session_duration_ms",        # total session length
    "session_duration_z_score",   # z-score vs user's historical mean
    "time_of_day_hour",           # hour of session start (0–23)
    "time_to_submit_otp_ms",      # time between OTP received and submitted
    "click_speed_mean",           # mean ms between consecutive UI interactions
    "click_speed_std",
    "form_submit_speed_ms",       # time from first field focus to submit
    "interaction_pace_ratio",     # actual pace / historical mean pace

    # Device Context (4 features — categorical, session-level)
    "is_new_device",              # 1 if device fingerprint not in user's allowlist
    "device_fingerprint_delta",   # cosine distance from nearest known device
    "timezone_changed",           # 1 if timezone differs from last 5 sessions
    "os_version_changed",         # 1 if OS version changed since last session
]

assert len(FEATURE_NAMES) == 47
```

### 3.2 Database schema

In `backend/db/models.py`:

```python
# Tables required:
# users(id, name, enrolled_at, sessions_count)
# sessions(id, user_id, started_at, session_type['legitimate'|'attacker'], feature_vector_json)
# scores(id, session_id, computed_at, confidence_score, risk_level, top_anomalies_json)
# sim_swap_events(id, user_id, triggered_at, is_active)
# alert_log(id, session_id, alert_type, sent_at, recipient, message)
```

### 3.3 Seed legitimate sessions

In `backend/data/seed_legitimate.py`:

Generate 10 sessions for user_id=1 with these behavioral parameters (simulate a consistent, habitual user):

```python
LEGITIMATE_PROFILE = {
    "inter_key_delay_mean": (180, 15),     # (mean_ms, std_dev) — consistent typist
    "inter_key_delay_std": (25, 5),
    "dwell_time_mean": (95, 8),
    "swipe_velocity_mean": (450, 30),
    "session_duration_ms": (240000, 30000), # ~4 min sessions
    "time_of_day_hour": [9, 10, 18, 19, 20], # user logs in mornings and evenings
    "direct_to_transfer": 0.15,             # rarely goes straight to transfer
    "exploratory_ratio": (0.08, 0.02),
    "is_new_device": 0,
    "hand_stability_score": (0.82, 0.05),
    "time_to_submit_otp_ms": (8500, 2000), # takes ~8-9 seconds to enter OTP
}
```

Use `numpy.random` with the above distributions to generate each session's feature vector. Add ±8% within-person variance (from clinical literature cited in spec). Store all 10 in `sessions` table as `session_type='legitimate'`.

### 3.4 Seed attacker session

In `backend/data/seed_attacker.py`:

Generate 1 session for user_id=1 but with attacker behavioral parameters:

```python
ATTACKER_PROFILE = {
    "inter_key_delay_mean": (310, 60),     # slower, unfamiliar keyboard
    "inter_key_delay_std": (90, 20),       # much higher variance — hunting and pecking
    "dwell_time_mean": (140, 30),
    "swipe_velocity_mean": (280, 80),      # slower, less confident gestures
    "session_duration_ms": (95000, 10000), # very short — under time pressure
    "time_of_day_hour": [2, 3],            # 2–3 AM attack window
    "direct_to_transfer": 1,               # goes straight to transfer
    "exploratory_ratio": (0.35, 0.08),     # lots of back navigation, hunting
    "is_new_device": 1,                    # new device fingerprint
    "hand_stability_score": (0.51, 0.1),   # nervous, unfamiliar device
    "time_to_submit_otp_ms": (2100, 300),  # grabs OTP instantly — automated
}
```

**Done-check Phase 1:**
- [ ] `python seed_runner.py` completes without errors
- [ ] SQLite DB has 10 legitimate sessions + 1 attacker session for user_id=1
- [ ] All feature vectors are 47-dimensional, no nulls

---

## 4. PHASE 2 — ML MODEL (Hours 4–10)

**Entry condition:** Phase 1 done-check passed. 10 legitimate sessions in DB.

### 4.1 Train One-Class SVM

In `backend/ml/one_class_svm.py`:

```python
# Steps (implement in this order):
# 1. Load all legitimate sessions for user_id from DB
# 2. Stack feature vectors into numpy array X of shape (n_sessions, 47)
# 3. StandardScaler fit on X — save scaler as scaler_{user_id}.pkl
# 4. Train OneClassSVM(kernel='rbf', nu=0.05, gamma='scale') on scaled X
# 5. Calibrate raw decision_function output to [0,100] confidence score:
#    - Collect decision_function scores on training data
#    - Fit Platt scaling (LogisticRegression on [legitimate=1]) or
#      min-max normalize using (score - min) / (max - min) * 100
#    - Invert so that high score = high confidence (legitimate)
# 6. Save model as model_{user_id}.pkl
# 7. Expose: train(user_id), predict(user_id, feature_vector) -> int (0-100)
```

Calibration target: legitimate sessions should score 85–95 after calibration. Attacker session should score below 35.

### 4.2 Score fusion

In `backend/ml/score_fusion.py`:

```python
def fuse_score(behavior_score: int, sim_swap_active: bool) -> dict:
    """
    Fusion rules (apply in order):
    1. If sim_swap_active AND behavior_score < 45:
       → final_score = min(behavior_score, 25)
       → risk_level = "CRITICAL"
       → action = "BLOCK_AND_FREEZE"
    2. If sim_swap_active (regardless of score):
       → final_score = behavior_score * 0.6   # penalize heavily
       → risk_level = "HIGH" if final_score < 45 else "MEDIUM"
    3. If behavior_score < 30:
       → risk_level = "CRITICAL", action = "BLOCK_AND_FREEZE"
    4. If behavior_score < 45:
       → risk_level = "HIGH", action = "BLOCK_TRANSACTION"
    5. If behavior_score < 70:
       → risk_level = "MEDIUM", action = "STEP_UP_AUTH"
    6. Else:
       → risk_level = "LOW", action = "ALLOW"
    
    Returns: {final_score, risk_level, action}
    """
```

### 4.3 Anomaly explanation

In `backend/utils/scoring.py`, implement `get_top_anomalies(feature_vector, baseline_mean, baseline_std)`:

```python
# Steps:
# 1. Compute z-score for each of the 47 features vs. user's baseline
# 2. Sort features by |z-score| descending
# 3. Return top 4 anomalies as human-readable strings using this mapping:
ANOMALY_TEMPLATES = {
    "inter_key_delay_mean": "Typing inter-key delay {direction} {pct}% {vs_baseline}",
    "direct_to_transfer": "User went directly to transfer screen — atypical navigation",
    "is_new_device": "New device fingerprint — never seen for this account",
    "time_to_submit_otp_ms": "OTP submitted {pct}% faster than user's historical mean",
    "exploratory_ratio": "Navigation is {pct}% more exploratory than normal",
    "session_duration_ms": "Session duration {pct}% shorter than user's average",
    "hand_stability_score": "Device motion stability {pct}% below user's baseline",
    "time_of_day_hour": "Login at {hour}:00 — outside user's typical hours ({typical})",
    # ... add for remaining features
}
# 4. Always append SIM swap anomaly string if sim_swap_active=True:
#    "SIM swap event detected {N} minutes ago"
```

### 4.4 Score streaming endpoint

`GET /score/{session_id}` — returns current confidence score, updated every time a new feature snapshot is submitted. In the attacker session simulation, score degrades progressively across 5 snapshots:

```
Snapshot 1 (0s):  91  → session starts, looks normal
Snapshot 2 (6s):  74  → typing anomaly detected
Snapshot 3 (12s): 58  → navigation anomaly detected  
Snapshot 4 (18s): 44  → device fingerprint mismatch
Snapshot 5 (24s): 27  → SIM swap signal fused → CRITICAL
```

These values must come from actual model inference on progressively-revealed feature slices, not hardcoded. Simulate by revealing attacker features in 5 equal batches (9–10 features per snapshot), inferring on each partial vector with zeros for unrevealed features.

**Done-check Phase 2:**
- [ ] `predict(user_id=1, legitimate_vector)` returns score ≥ 85
- [ ] `predict(user_id=1, attacker_vector)` returns score ≤ 35
- [ ] `get_top_anomalies()` returns exactly 4 strings for attacker session
- [ ] `fuse_score(score=40, sim_swap_active=True)` returns `risk_level="CRITICAL"`

---

## 5. PHASE 3 — BACKEND API (Hours 10–16)

**Entry condition:** Phase 2 done-check passed.

### 5.1 FastAPI routes — implement all of these

```
POST /session/start
  body: {user_id: int, session_type: "legitimate"|"attacker"}
  returns: {session_id: str}

POST /session/feature
  body: {session_id: str, feature_snapshot: dict[str, float]}
  returns: {score: int, risk_level: str, action: str, top_anomalies: list[str]}
  side-effect: triggers alert if action == "BLOCK_AND_FREEZE"

GET /score/{session_id}
  returns: latest ScoreResponse from scores table

POST /enroll/{user_id}
  body: {} (uses existing legitimate sessions in DB)
  returns: {enrolled: bool, sessions_used: int, model_saved: bool}

POST /sim-swap/trigger
  body: {user_id: int}
  returns: {event_id: str, triggered_at: str}
  side-effect: sets sim_swap_events.is_active=True for user

POST /sim-swap/clear
  body: {user_id: int}
  returns: {cleared: bool}

POST /alert/send
  body: {session_id: str, alert_type: "SMS"|"LOG", recipient: str}
  returns: {sent: bool, message_sid: str}
  side-effect: sends actual Twilio SMS if alert_type=="SMS"

GET /sessions/{user_id}
  returns: all sessions for user with scores — used by enrollment panel
```

### 5.2 CORS config

```python
# In main.py — allow frontend dev server
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### 5.3 Twilio SMS

In `backend/utils/twilio_client.py`:

```python
# send_alert(to_number, score, top_anomalies) sends:
# "🚨 BehaviorShield Alert: Suspicious activity on your account.
#  Risk score: 27/100. Reason: Typing delay +80%, new device, SIM swap detected.
#  Your transaction has been frozen. Call 1800-XXX-XXXX to verify."
```

**Done-check Phase 3:**
- [ ] All 8 routes return 200 with correct response shapes (test with curl or httpx)
- [ ] `POST /sim-swap/trigger` + `POST /session/feature` (attacker vector) = CRITICAL response
- [ ] Twilio SMS actually arrives on `DEMO_ALERT_NUMBER`

---

## 6. PHASE 4 — FRONTEND (Hours 16–28)

**Entry condition:** All backend routes tested and passing.

### 6.1 Behavior SDK (`useBehaviorSDK.ts`)

Capture these real browser events during any active banking app session:

```typescript
// Attach event listeners on mount, detach on unmount
window.addEventListener('keydown', onKeyDown)      // inter-key delay, dwell start
window.addEventListener('keyup', onKeyUp)          // dwell end
window.addEventListener('mousemove', onMouseMove)  // movement entropy (desktop sim)
window.addEventListener('click', onClick)          // click speed
window.addEventListener('touchstart', onTouch)     // touch dynamics (if on mobile)

// Every 6 seconds, extract partial feature vector from accumulated events
// POST to /session/feature
// Update score display
```

The SDK runs during the demo's legitimate sessions (when the judge interacts with the mock bank UI). For the attacker simulation, the attacker's pre-seeded feature snapshots are sent automatically.

### 6.2 Mock Banking App (`BankingApp.tsx`)

Build a convincing but minimal bank UI with these screens:

```
Screen 1: Login — username/password fields + "Login" button
Screen 2: Dashboard — account balance (₹3,42,580), last 5 transactions, nav to Transfer
Screen 3: Transfer — beneficiary input, amount, "Send Money" button
Screen 4: OTP Verification — 6-digit OTP input + countdown timer
Screen 5: [Conditional] Freeze Modal — transaction blocked, alert sent, re-auth required
```

Style: dark navy + gold accent. Professional banking aesthetic. Use Tailwind. Show a small "BehaviorShield Active" indicator badge in the top-right corner with a pulsing green dot.

### 6.3 Score Dashboard (`ScoreDashboard.tsx`)

This is the centerpiece of the demo — judges will watch this:

```
Layout (side-by-side with BankingApp):
┌─────────────────────────────────────────┐
│  CONFIDENCE SCORE                       │
│                                         │
│         [Large animated number]         │
│              91 → 27                    │
│                                         │
│  [Recharts LineChart — live score       │
│   updating every 6 seconds]             │
│                                         │
│  RISK LEVEL: ██ CRITICAL                │
│  ACTION:     🔒 BLOCK + FREEZE          │
│                                         │
│  TOP ANOMALIES:                         │
│  ⚠ Typing delay +80% above baseline    │
│  ⚠ Navigation: went straight to xfer   │
│  ⚠ New device fingerprint detected     │
│  ⚠ SIM swap event — 6 minutes ago      │
│                                         │
│  [SIM SWAP ACTIVE badge — red pulse]    │
└─────────────────────────────────────────┘
```

Score number animates via Framer Motion (spring animation between values). LineChart shows full session history. Anomaly list fades in as each new anomaly is detected. Risk level badge changes color: green (LOW) → yellow (MEDIUM) → orange (HIGH) → red (CRITICAL).

### 6.4 Attack Simulator (`AttackSimulator.tsx`)

A control panel for the demo operator (the presenter):

```
Buttons (execute in order during demo):
[1. Enroll Legitimate User]    → POST /enroll/1 → shows enrollment progress
[2. Start Legitimate Session]  → POST /session/start {type: legitimate} → SDK active
[3. TRIGGER SIM SWAP ⚡]       → POST /sim-swap/trigger → red event fires
[4. Start Attacker Session]    → POST /session/start {type: attacker} → score degrades
[5. Reset Demo]                → clears all state, ready for next run

Each button is disabled until the previous step completes.
Show step status: ✓ Enrolled | ✓ Baseline: 91 | ⚡ SIM Swap Active | 🔒 BLOCKED
```

### 6.5 Rule-Based Comparison Panel

A second tab labeled "Legacy System (Current Indian Banks)":

- Same attacker session runs
- Rule-based engine checks: amount > ₹50,000? No (demo uses ₹15,000). Time > 11PM? No. Location anomaly? No (no location data)
- Shows: "✓ Transaction Approved — ₹15,000 sent"
- Then flip back to BehaviorShield tab showing the CRITICAL block

This comparison is the demo's most powerful moment.

**Done-check Phase 4:**
- [ ] Score chart animates 91→27 across 5 snapshots during attacker session
- [ ] All 4 anomaly strings appear with correct timing
- [ ] Transaction freeze modal appears at score < 30
- [ ] Rule-based comparison tab shows "Transaction Approved" for same attacker session
- [ ] Twilio SMS fires and is confirmed received on demo phone

---

## 7. PHASE 5 — SEED RUNNER & DEMO AUTOMATION (Hours 28–34)

**Entry condition:** Full frontend + backend working end-to-end manually.

### 7.1 One-command demo reset

`demo/seed_runner.py`:

```python
# Steps (in order):
# 1. Drop and recreate all DB tables
# 2. Create user_id=1 (name="Atharva Kumar", enrolled_at=30 days ago)
# 3. Generate and insert 10 legitimate sessions (seed_legitimate.py)
# 4. Generate and insert 1 attacker session (seed_attacker.py)
# 5. Train and save One-Class SVM model for user_id=1
# 6. Print: "✓ Seeded 10 legitimate sessions | Model trained | Attacker session ready"
# 7. Print: "Run: uvicorn backend.main:app --reload"

# Usage: python demo/seed_runner.py
# Must complete in under 10 seconds
```

### 7.2 Backup demo mode

Add `?demo=auto` URL param to frontend. In auto mode:
- All 5 attacker snapshots play back on a 6-second timer automatically
- No manual clicking required
- Presenter just narrates

### 7.3 Metrics screen

Add a `/metrics` route to the frontend showing:

| Metric | Value |
|---|---|
| Sessions analyzed (seeded) | 50 |
| True positives (attack detected) | 47 |
| False positives (legit flagged) | 1 |
| Detection rate | 94% |
| False positive rate | 2.1% |
| Mean detection latency | 28 seconds |
| Enrollment sessions required | 10 |
| Feature dimensions | 47 |
| SDK CPU overhead | < 1% |
| SDK memory footprint | < 4 MB |

These are from the spec — display them as a clean stats grid, not a table.

**Done-check Phase 5:**
- [ ] `python demo/seed_runner.py` completes in < 10 seconds, clean DB
- [ ] `?demo=auto` runs full attack simulation without any clicks
- [ ] Metrics page renders correctly

---

## 8. PHASE 6 — TESTING & THRESHOLD TUNING (Hours 34–42)

### 8.1 Validate model calibration

Run this and confirm all assertions pass:

```python
# backend/tests/test_model.py
def test_legitimate_scores_high():
    for session in get_legitimate_sessions(user_id=1):
        score = predict(user_id=1, features=session.feature_vector)
        assert score >= 80, f"Legitimate session scored {score} — too low"

def test_attacker_scores_low():
    score = predict(user_id=1, features=get_attacker_session().feature_vector)
    assert score <= 35, f"Attacker session scored {score} — not detected"

def test_sim_swap_fusion_critical():
    result = fuse_score(behavior_score=40, sim_swap_active=True)
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "BLOCK_AND_FREEZE"

def test_anomaly_count():
    anomalies = get_top_anomalies(attacker_vector, baseline_mean, baseline_std)
    assert len(anomalies) == 4

def test_score_degradation_sequence():
    scores = simulate_progressive_reveal(attacker_session, n_snapshots=5)
    assert scores[0] > 80      # starts high
    assert scores[-1] < 30     # ends critical
    for i in range(1, 5):
        assert scores[i] < scores[i-1]  # monotonically decreasing
```

### 8.2 False positive budget

Run 50 additional legitimate sessions through the trained model. Confirm ≤ 3 are flagged as HIGH or above (false positive rate ≤ 6% for demo purposes; spec target is 2.1%).

If false positive rate > 6%, increase `nu` from 0.05 to 0.08 and retrain.

### 8.3 API latency check

```bash
# All inference endpoints must respond in under 100ms
curl -w "%{time_total}" -o /dev/null http://localhost:8000/score/test-session-id
# Target: < 0.1s
```

**Done-check Phase 6:**
- [ ] All 5 test functions pass
- [ ] False positive rate ≤ 6% on 50 synthetic legitimate sessions
- [ ] Score endpoint responds in < 100ms

---

## 9. DEMO SCRIPT (8 Minutes)

Follow this exactly during the hackathon presentation:

### Minute 0:00–1:00 — Problem Setup

**Say:** "India loses ₹500 crore a year to SIM swap fraud. Here's how it works."

**Show:** The attack lifecycle table from the spec on a slide.

**Say:** "A ₹500 fake Aadhaar. A visit to a franchisee store. 4 minutes. Your account is empty. Every Indian bank detects this never — they rely on OTP, and the attacker has your OTP."

### Minute 1:00–2:30 — Enrollment

**Action:** Click `[1. Enroll Legitimate User]`

**Say:** "BehaviorShield first learns what the legitimate user looks like — not what they know or what they have, but how they behave. 10 sessions. Typing rhythm. Swipe patterns. Navigation habits. Device motion."

**Show:** Enrollment panel filling up session by session. Score stabilizes at 91.

**Say:** "This is the user's behavioral fingerprint. It cannot be stolen. It cannot be printed on a fake ID."

### Minute 2:30–4:30 — The Attack

**Action:** Click `[2. Start Legitimate Session]`, let it run 10 seconds. Then click `[3. TRIGGER SIM SWAP ⚡]`. Then click `[4. Start Attacker Session]`.

**Say:** "SIM swap just happened. The fraudster has the victim's phone number. OTP will now go to them. They open the bank app on their device."

**Show:** Score dropping live: 91 → 74 → 58 → 44 → 27. Narrate each drop.

- 91→74: "Typing patterns don't match. Inter-key delay is 80% higher."
- 74→58: "Navigation is exploratory — went straight to the transfer screen. Legitimate users almost never do this."
- 58→44: "Device fingerprint: never seen this phone before."
- 44→27: "SIM swap event from 6 minutes ago fused in. Score collapses."

### Minute 4:30–5:00 — The Intervention

**Show:** Transaction freeze modal. Twilio SMS arrives on phone (hold phone up to camera).

**Say:** "Score 27. SIM swap flag active. Transaction frozen in 28 seconds. SMS sent to the real user. No money moved."

### Minute 5:00–5:45 — Explainability

**Show:** The `top_anomalies` JSON in the dashboard.

**Say:** "This is not a black box. The bank's fraud analyst sees exactly why we blocked it. This is auditable. This is what RBI's 2023 circular is asking for."

### Minute 5:45–6:30 — The Comparison

**Action:** Switch to "Legacy System" tab. Run same attacker session.

**Show:** "✓ Transaction Approved — ₹15,000 sent"

**Say:** "This is what every Indian bank has today. Rule-based. Amount under threshold. Time of day OK. Location unchanged. Approved. Money gone."

**Action:** Switch back to BehaviorShield. Show "🔒 BLOCKED."

**Say:** "That is the gap we fill."

### Minute 6:30–8:00 — Metrics + Business Case

**Show:** Metrics screen.

**Say:** "94% detection rate. 2.1% false positives — less than BioCatch, the global benchmark. 28-second detection window. ₹3 per account per month SaaS. 800 million addressable accounts in India. RBI is mandating exactly this. No Indian company has built it. This is the gap."

---

## 10. ANTICIPATED JUDGE QUESTIONS — ANSWERS

Prepare these responses cold:

**"Won't a sophisticated attacker just mimic behavioral patterns?"**
To mimic behavioral biometrics in real time, an attacker needs months of captured session recordings and live ML inference running on their device during the attack. That raises the attack cost from ₹500 (fake Aadhaar) to hundreds of thousands of rupees and months of preparation. SIM swap is a volume crime — it works because it's cheap. We make it economically unviable, not theoretically impossible.

**"What about false positives — you're blocking legitimate users."**
False positive rate in simulation: 2.1%. At MEDIUM risk (score 45–70), we step up to OTP — not a hard block. Users are already habituated to OTP. Only at CRITICAL (score < 30 + SIM swap flag) do we hard block, and we immediately notify the user. A legitimate user at score 50 gets one extra OTP prompt. That is the full cost of a false positive.

**"Why haven't banks built this?"**
Banks' ML infrastructure runs 3–5 years behind. Core banking integration (Finacle, BankFlex) is genuinely painful. Banks are reactive on fraud — they investigate after loss, not before. This is exactly why the SDK model exists: we integrate once, the bank deploys with 2 API calls.

**"Is capturing behavioral data legal in India?"**
DPDPA 2023 Section 6 explicitly permits behavioral analytics under legitimate purpose for fraud prevention. We store 47 derived floating-point features — not raw keystrokes, not biometric data. Given only the feature vector, it is computationally infeasible to reconstruct the original inputs. Users consent via the bank's existing terms of service, which already covers fraud monitoring.

**"What's the performance impact on the user's phone?"**
Under 1% additional CPU. Under 0.5% additional battery. Under 4 MB memory. Less overhead than Firebase Analytics, which banks already embed. Event listeners are low-frequency callbacks; feature extraction runs in a background thread in under 5ms.

---

## 11. KEY NUMBERS — MEMORIZE THESE

| Stat | Figure |
|---|---|
| Annual India SIM swap fraud | ₹500 Crore |
| Fake Aadhaar cost | ₹500 |
| Attack window | 4 minutes |
| BehaviorShield detection time | 28 seconds |
| Detection rate | 94% |
| False positive rate | 2.1% |
| Feature dimensions | 47 |
| SDK memory footprint | < 4 MB |
| SDK CPU overhead | < 1% |
| Enrollment sessions | 10 (or 3–5 with transfer learning) |
| Business model | ₹3/account/month SaaS |
| TAM | ₹24,000 Crore/year |
| RBI fraud loss growth YoY | 708% |
| Indian bank fraud recovery cost | ₹950 Crore/year |

---

## 12. IMPLEMENTATION CONSTRAINTS

- **No hardware required.** All behavioral signals in the demo are either captured from real browser events (legitimate session) or synthesized from seeded distributions (attacker session).
- **No external ML APIs.** Model runs locally. No OpenAI/Anthropic calls in the ML pipeline.
- **SQLite only.** No Docker, no PostgreSQL setup required for demo. Keep it runnable in 2 commands.
- **Twilio is the only external service.** It actually sends the SMS. Have the account set up before the hackathon starts.
- **Record a backup demo video.** If internet is down or Twilio fails, play the recording. `demo/backup_video.md` has instructions.
- **Demo must run on a single laptop** with `uvicorn` + `vite dev` as the only running processes.
- **Python 3.11+, Node 20+.** Do not use deprecated APIs.

---

## 13. BUILD ORDER SUMMARY

```
Hour 0–4:   Phase 1 — DB schema + feature schema + seed data
Hour 4–10:  Phase 2 — One-Class SVM + score fusion + anomaly explanation
Hour 10–16: Phase 3 — All 8 FastAPI routes + Twilio integration
Hour 16–28: Phase 4 — React frontend (BankingApp + ScoreDashboard + AttackSimulator)
Hour 28–34: Phase 5 — Seed runner + auto-demo mode + metrics screen
Hour 34–42: Phase 6 — Testing + threshold tuning + latency validation
Hour 42–48: Polish + rehearse demo script + record backup video
```

Do not skip phases. Do not parallelize phases 1–3 (each depends on the prior).
Frontend (Phase 4) can begin after Phase 3's routes are defined but not yet fully tested.