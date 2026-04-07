# SHIELD — Complete Project Overview

---

## SYSTEM MAP

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BEHAVIORSHIELD                               │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │  Frontend 1      │    │  Frontend 2      │    │  Frontend 3  │  │
│  │  Mobile Banking  │    │  Bank Analyst    │    │  Attack Sim  │  │
│  │  App (Mock)      │    │  Dashboard       │    │  Control     │  │
│  │                  │    │                  │    │  Panel       │  │
│  │  React PWA       │    │  React Desktop   │    │  React       │  │
│  │  375px viewport  │    │  Full-width      │    │  Full-width  │  │
│  └────────┬─────────┘    └────────┬─────────┘    └──────┬───────┘  │
│           │                       │                      │          │
│           └───────────────────────┴──────────────────────┘          │
│                                   │                                 │
│                          ┌────────▼────────┐                        │
│                          │   FastAPI       │                        │
│                          │   Backend       │                        │
│                          │                 │                        │
│                          │ • ML Engine     │                        │
│                          │ • Score Fusion  │                        │
│                          │ • Session Store │                        │
│                          │ • Twilio Alerts │                        │
│                          └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## FRONTEND 1 — Mobile Banking App (The Victim's Phone)

**Purpose:** Where behavioral signals are captured. This is what the legitimate user and the attacker both interact with. Judges see this as the "real world."

**Viewport:** 375px wide, phone frame wrapper on desktop. Looks exactly like a banking app on a phone screen.

### Screens & Flow

```
┌─────────────────┐
│   🔐 Login      │  → captures: typing rhythm, dwell time, error rate
│                 │
│  [Username]     │
│  [Password]     │
│  [Login ▶]      │
└────────┬────────┘
         │
┌────────▼────────┐
│  🏠 Dashboard   │  → captures: time-on-screen, navigation intent, scroll
│                 │
│  ₹3,42,580      │
│  [Transfer]     │
│  [History]      │
│  [Profile]      │
└────────┬────────┘
         │
┌────────▼────────┐
│  💸 Transfer    │  → captures: form field order, speed, direct-to-transfer flag
│                 │
│  [Beneficiary]  │
│  [Amount]       │
│  [Send ▶]       │
└────────┬────────┘
         │
┌────────▼────────┐
│  📱 OTP Screen  │  → captures: time_to_submit_otp_ms (KEY attacker signal)
│                 │
│  Enter OTP:     │
│  [_ _ _ _ _ _]  │
│  Expires: 30s   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────────────┐
│  ✅   │ │ 🔒 FREEZE MODAL │
│ Done  │ │                 │
│       │ │ Transaction     │
│       │ │ blocked.        │
│       │ │ SMS sent.       │
│       │ │ Call bank.      │
└───────┘ └─────────────────┘
```

### UI/UX Spec

- **Color:** Deep navy `#0A1628` background, white text, `#FFD700` gold accent — premium banking aesthetic
- **Phone frame:** CSS device frame around the 375px app. Judges instantly read "this is a phone"
- **BehaviorShield badge:** Small pulsing green dot + "Protected" in top-right corner of every screen. Turns red when anomaly detected
- **No visible scoring here** — this app is intentionally unaware-looking. The magic happens on the dashboard, not here
- **Behavioral SDK runs silently** — no UI indication that signals are being captured (realistic)
- **Freeze modal:** Full-screen red overlay, not a small popup. Dramatic. Lock icon. "Your transaction has been frozen by BehaviorShield."

---

## FRONTEND 2 — Bank Analyst Dashboard (The Bank's Eyes)

**Purpose:** Real-time fraud ops view. Shows the bank's analyst what BehaviorShield sees. This is the **judge-facing centerpiece** — they watch this while the attack unfolds on Frontend 1.

**Layout:** Full desktop width, 3-column layout.

```
┌──────────────────────────────────────────────────────────────────────┐
│  BehaviorShield  •  Fraud Operations Center          🟢 LIVE         │
├─────────────────┬────────────────────────────┬───────────────────────┤
│                 │                            │                       │
│  USER PROFILE   │   CONFIDENCE SCORE         │  ACTIVE ALERTS        │
│                 │                            │                       │
│  Atharva Kumar  │   ╔══════════════╗          │  🔴 SIM SWAP ACTIVE   │
│  Acc: ****4521  │   ║      27      ║          │  Triggered: 6min ago  │
│  Risk: CRITICAL │   ║  ██████████  ║          │                       │
│                 │   ╚══════════════╝          │  🔴 New Device        │
│  Enrolled: ✅   │                            │  Fingerprint unknown  │
│  Sessions: 10   │   RISK: ■ CRITICAL          │                       │
│  Baseline: 91   │   ACTION: BLOCK+FREEZE      │  🟡 Typing Anomaly    │
│                 │                            │  +80% delay           │
│  Device:        │   [Live LineChart]          │                       │
│  Known: 3       │   91→74→58→44→27           │  🟡 Navigation        │
│  Current: ❌NEW │                            │  Direct to transfer   │
│                 │                            │                       │
│                 │                            │  [SEND SMS ALERT ▶]   │
├─────────────────┴────────────────────────────┴───────────────────────┤
│                                                                      │
│  TOP ANOMALIES (Why we blocked this)                                 │
│                                                                      │
│  1. Typing inter-key delay +80% above user baseline (z-score: 3.8)  │
│  2. Navigation: went directly to transfer — atypical (p=0.04)       │
│  3. Device fingerprint: never seen for this account                  │
│  4. SIM swap event detected 6 minutes ago (telecom API)             │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SESSION TIMELINE                                                    │
│  ──────────────────────────────────────────────────────────────────  │
│  0s    Login (score: 91) ●────                                       │
│  6s    Typing captured  (score: 74)      ●────                       │
│  12s   Navigation logged (score: 58)              ●────              │
│  18s   Device mismatch  (score: 44)                        ●────     │
│  24s   SIM swap fused   (score: 27) 🔒 BLOCKED                  ●   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### UI/UX Spec

- **Color:** Dark `#0F172A` base, red `#EF4444` for critical, amber `#F59E0B` for warnings, green `#22C55E` for safe
- **Score number:** Giant, center-stage. Framer Motion spring animation between values. Color transitions with risk level
- **LineChart (Recharts):** Score over time, x-axis = seconds, animated line drawing itself in real time. Reference line at 45 (step-up) and 30 (block) shown as dashed horizontal lines
- **Anomaly cards:** Each anomaly fades in as detected — not all at once. Judges watch them accumulate
- **Session timeline:** Horizontal, like a git blame view. Each snapshot is a node. Clicking a node shows that snapshot's feature values
- **Alert panel:** Live feed. Each alert is a card with timestamp, type, and severity badge

---

## FRONTEND 3 — Attack Simulation Control Panel (The Presenter's Weapon)

**Purpose:** The hackathon demo controller. Lets the presenter run all 4 attack scenarios interactively, showing judges each scenario systematically.

**Layout:** Full desktop, dark terminal aesthetic with clean controls.

```
┌──────────────────────────────────────────────────────────────────────┐
│  ⚡ BehaviorShield Attack Simulator          [RESET ALL]             │
├─────────────────────────────────────┬────────────────────────────────┤
│                                     │                                │
│  SCENARIO SELECT                    │  CURRENTLY RUNNING             │
│                                     │                                │
│  ┌─────────────────────────────┐    │  Scenario 1: New Device        │
│  │ 1. New Phone + SIM (Strong) │◀── │  Status: 🔴 BLOCKED            │
│  │ 2. Laptop + OTP SIM         │    │  Score: 27                     │
│  │ 3. Automated Bot Attack     │    │  Time: 28s                     │
│  │ 4. Same Device Takeover     │    │                                │
│  │ 5. Legitimate User Control  │    │  Detection: ✅                 │
│  └─────────────────────────────┘    │  False Positive: —             │
│                                     │                                │
│  STEP CONTROLS                      │                                │
│                                     │                                │
│  [1. Enroll User        ✅ Done]    │                                │
│  [2. Establish Baseline ✅ Done]    │                                │
│  [3. Trigger SIM Swap   ▶ Fire ]    │                                │
│  [4. Run Attack Session ▶ Start]    │                                │
│  [5. Compare: Legacy    ▶ Show ]    │                                │
│                                     │                                │
├─────────────────────────────────────┴────────────────────────────────┤
│                                                                      │
│  SCENARIO COMPARISON TABLE                                           │
│                                                                      │
│  Scenario              │ Score │ Detection │ Time   │ Result         │
│  ──────────────────────┼───────┼───────────┼────────┼─────────────  │
│  1. New Device + SIM   │  27   │    ✅     │  28s   │ BLOCKED        │
│  2. Laptop + OTP SIM   │  31   │    ✅     │  34s   │ BLOCKED        │
│  3. Bot Automation     │  19   │    ✅     │  12s   │ BLOCKED        │
│  4. Same Device        │  48   │    ✅     │  52s   │ STEP-UP AUTH   │
│  5. Legitimate User    │  89   │    —      │   —    │ ALLOWED        │
│  ──────────────────────┼───────┼───────────┼────────┼─────────────  │
│  Legacy Rule-Based     │  N/A  │    ❌     │  N/A   │ APPROVED ❌    │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LIVE FEATURE INSPECTOR  (what signals triggered the block)          │
│                                                                      │
│  Feature                  │ User Baseline │ This Session │ Z-Score   │
│  ─────────────────────────┼───────────────┼──────────────┼────────── │
│  inter_key_delay_mean     │    180ms      │    310ms     │  +3.8 🔴  │
│  time_to_submit_otp_ms    │   8500ms      │   2100ms     │  -3.2 🔴  │
│  direct_to_transfer       │     0.15      │     1.0      │  +4.1 🔴  │
│  hand_stability_score     │     0.82      │     0.51     │  -3.1 🔴  │
│  is_new_device            │      0        │      1       │  CAT 🔴  │
│  exploratory_ratio        │     0.08      │     0.35     │  +3.4 🔴  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### UI/UX Spec

- **Color:** Near-black `#09090B` terminal feel, green `#00FF88` for safe outputs, red for blocks — hacker aesthetic that fits the security track
- **Scenario cards:** Clicking any scenario pre-loads its seeded data. Transitions are instant — no loading spinners during demo
- **Comparison table:** Builds row by row as each scenario is run. Not pre-filled. Judges see it populate live
- **Feature Inspector:** Rows highlight red as z-score crosses 2.5. Judges can see exactly which features fired
- **Legacy System column:** Always shows APPROVED ❌ for all attack scenarios — the contrast is the point

---

## ALL 5 ATTACK SCENARIOS — What to Show & How to Detect

### Scenario 1 — New Device + SIM (from your doc)
**What attacker does:** SIM swap → opens bank app on own phone → gets OTP → drains account

**Key signals:** `is_new_device=1`, `device_fingerprint_delta` high, typing mismatch, `direct_to_transfer=1`, `time_of_day_hour=2`

**Score:** 27 | **Detection:** 28s | **Action:** BLOCK + FREEZE

---

### Scenario 2 — Laptop + OTP SIM (from your doc)
**What attacker does:** SIM only used for OTP, fraud executed on laptop browser

**New detection angle:** Mouse movement replaces touch — behavioral modality switch is itself an anomaly. `form_field_order_entropy` spikes (laptop tab-order vs mobile tap-order differs). `swipe_velocity` features all zero (no touch = suspicious on a "mobile session").

**Score:** 31 | **Detection:** 34s | **Action:** BLOCK

---

### Scenario 3 — Bot/Automated Attack (from your doc)
**What attacker does:** Scripts autofill forms, instant OTP submission

**Key signals:** `time_to_submit_otp_ms = 800ms` (humans take 6–10 seconds), `interaction_pace_ratio = 0.05` (too fast), `click_speed_std ≈ 0` (inhuman consistency), `typing_burst_count = 1` (single burst, no pauses)

**Insight to say:** *"Humans are messy. Bots are too perfect. Zero variance in click timing is itself the anomaly."*

**Score:** 19 | **Detection:** 12s | **Action:** BLOCK (fastest detection of all scenarios)

---

### Scenario 4 — Same Device Takeover (new, from your doc)
**What attacker does:** Steals phone + SIM. Device is known. Behavioral signals weaker.

**What still fires:** `session_duration_ms` 60% shorter than baseline, `direct_to_transfer=1`, `time_of_day_hour=3`, `time_to_submit_otp_ms` lower (urgency). SIM swap signal fuses in.

**Honest limitation:** Score lands at 48 → STEP-UP AUTH, not hard block. Demonstrate this as the system asking for Face ID re-verification.

**Say to judges:** *"We don't hard block because false positive cost is high here — it could be the legitimate user on their own phone. We step up to Face ID. The attacker cannot pass biometric re-auth. This is correct behavior, not a failure."*

**Score:** 48 | **Action:** STEP-UP (Face ID prompt shown)

---

### Scenario 5 — NEW: Credential Stuffing + SIM (not in your doc)
**What attacker does:** Uses leaked credential database + SIM swap. Tries 3 accounts in 8 minutes.

**New signals to add:** `session_velocity` — multiple sessions for different users from same device fingerprint within a short window. Cross-account anomaly detection: same device seen on 3 different user accounts in 10 minutes = automatic CRITICAL regardless of individual session scores.

**Why it's new and important:** This is how professional fraud rings operate — not one victim, many. Your current spec is single-user. Add a fleet-level anomaly in the Risk Engine: `device_seen_on_n_accounts_last_hour`. If n ≥ 2 → escalate to HIGH regardless of behavior score.

**Score:** 22 | **Detection:** Device flagged on 2nd account attempt | **Action:** All associated accounts frozen

---

### Scenario 6 — NEW: SIM Swap Without Device Takeover (Partial Attack)
**What attacker does:** Has SIM, doesn't have credentials yet. Uses the SIM to probe — calls bank IVR, checks balance via SMS banking, tests which bank the victim uses.

**New detection angle:** IVR probe pattern — 3 SMS balance queries in 2 minutes from new SIM = SIM swap + reconnaissance flag. Not behavioral biometrics — pure telecom signal. Demonstrate this as a pre-auth warning before the attacker even opens the app.

**Shows judges:** Your system catches the attack *before login*, not just during the session.

---

## BACKEND — Additions to CLAUDE.md

Add these new routes and components:

```
New routes:
POST /session/fleet-check
  → checks if current device fingerprint seen on > 1 account in last hour
  → returns: {fleet_anomaly: bool, accounts_seen: int, action: str}

GET /scenarios/list
  → returns all 6 pre-seeded scenarios with metadata for the simulator panel

POST /scenarios/{scenario_id}/run
  → runs a specific scenario end-to-end, returns full score progression

GET /features/inspect/{session_id}
  → returns feature vector vs baseline comparison with z-scores for all 47 features
  → powers the Feature Inspector table in Frontend 3

New ML component:
backend/ml/fleet_anomaly.py
  → device fingerprint → account mapping
  → flag device seen on ≥ 2 accounts in 60-min window
```

---

## THREE-SCREEN DEMO LAYOUT (How to physically show this)

```
Your laptop screen during demo:

┌─────────────────────────────────────────────────┐
│                                                 │
│  LEFT HALF              RIGHT HALF              │
│                                                 │
│  ┌───────────────┐      ┌────────────────────┐  │
│  │               │      │                    │  │
│  │  Frontend 3   │      │  Frontend 2        │  │
│  │  Attack Sim   │      │  Analyst Dashboard │  │
│  │  Control      │      │  (Score + Alerts)  │  │
│  │               │      │                    │  │
│  └───────────────┘      └────────────────────┘  │
│                                                 │
│  PROJECTOR / SECOND SCREEN:                     │
│  Frontend 1 — Mobile Banking App                │
│  (375px, phone frame, full screen)              │
│                                                 │
└─────────────────────────────────────────────────┘
```

Projector shows the banking app (what the "user" sees). Your laptop shows the attack panel + analyst dashboard. Judges see both worlds simultaneously.

---

## UPDATED SCENARIO MATRIX

| Scenario | Detection Strength | Score | Time | Action |
|---|---|---|---|---|
| New Device + SIM | 🟢 Very Strong | 27 | 28s | BLOCK + FREEZE |
| Laptop + OTP SIM | 🟢 Strong | 31 | 34s | BLOCK |
| Bot Automation | 🟢 Strongest | 19 | 12s | BLOCK |
| Same Device | 🟡 Moderate (honest) | 48 | 52s | STEP-UP |
| Credential Stuffing | 🟢 Strong (fleet) | 22 | 2nd account | FREEZE ALL |
| Pre-auth Probe | 🟢 Novel | — | Pre-login | EARLY WARN |
| Legitimate User | ✅ No action | 89 | — | ALLOW |
| Legacy Rule-Based | ❌ All pass | N/A | — | APPROVED |

