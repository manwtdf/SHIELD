# SHIELD — Desktop / PC / Laptop Detection

> Explains how SHIELD handles legitimate multi-device banking
> while precisely detecting attacker-on-PC post SIM swap.

---

## Why "Desktop = Suspicious" Is Wrong

Indian banking context:
- Professionals do NEFT/RTGS on office PC daily
- Tier 2/3 city users without smartphones bank at cybercafes
- Users transfer from relative's or family member's home PC
- Mobile-enrolled users prefer PC for large transfers

Treating desktop session as anomaly → **30–40% false positive rate** → unacceptable.

**Correct signal:** `desktop + SIM swap + zero prior PC history + unknown fingerprint = fraud`
**Not:** `desktop` alone.

---

## Core Principle

```
Risk source        =    context, not device class
Attacker signal    =    SIM swap  AND  device_class_switch  AND  is_known_fingerprint=0  AND  device_session_count=0
Cybercafe user     =    is_known_fingerprint=0  AND  behavior_score >= 70  →  ALLOW
Regular office PC  =    is_known_fingerprint=1  AND  no sim_swap           →  ALLOW
```

---

## What Changed and Why

### 1. `feature_schema.py` — 47 → 55 features

**Removed:** Raw `input_modality` flag (blunt, causes false positives).

**Added Group: Device Trust Context (5 features)**

These replace the modality flag entirely. The SVM scores them alongside behavioral signals — no separate hard rule needed.

| Feature | Type | Meaning |
|---|---|---|
| `device_class_known` | binary | 1 = user has prior sessions on this device class |
| `device_session_count` | int | Sessions recorded on this exact fingerprint |
| `device_class_switch` | binary | 1 = current class differs from dominant class last 30 days |
| `is_known_fingerprint` | binary | 1 = fingerprint in registry with session_count >= 3 |
| `time_since_last_seen_hours` | float | 0 = never seen before on this device |

Example: `device_class_known=1, device_session_count=8` → trusted office PC → no penalty.  
Example: `device_class_known=0, device_session_count=0, device_class_switch=1` → first-ever PC session → suspicious only in combination with SIM swap.

**Added Group: Desktop Mouse Biometrics (3 features)**

Always 0.0 on mobile (hardware impossible). Populated by JS SDK on desktop.

| Feature | Mobile | Human Desktop | Bot Desktop |
|---|---|---|---|
| `mouse_movement_entropy` | 0.0 | 0.3–0.8 (random path) | ~0.02 (scripted straight lines) |
| `mouse_speed_cv` | 0.0 | 0.3–0.7 (natural variation) | ~0.0 (inhuman consistency) |
| `scroll_wheel_event_count` | 0 | 8–30 | 0–2 |

`mouse_speed_cv ≈ 0` on desktop = bot automation. Same logic as `click_speed_std ≈ 0` in original model.

---

### 2. `db/models.py` — Schema Extensions

**`Session` table — new column:**
```sql
device_class TEXT DEFAULT 'mobile'   -- 'mobile' | 'desktop' | 'tablet'
```
Used by `train_model(device_class='desktop')` to filter device-specific sessions.

**`DeviceRegistry` table — 3 new columns:**
```sql
device_class   TEXT    DEFAULT 'mobile'  -- device class of this fingerprint
trust_level    TEXT    DEFAULT 'new'     -- 'new' | 'known' | 'one-time'
session_count  INTEGER DEFAULT 0         -- sessions on this exact fingerprint
```

Trust level progression:
```
session_count = 0     →  'new'       →  is_known_fingerprint = 0
session_count = 1–2   →  'new'       →  is_known_fingerprint = 0
session_count >= 3    →  'known'     →  is_known_fingerprint = 1
Never returns         →  'one-time'  →  is_known_fingerprint = 0
```

---

### 3. `one_class_svm.py` — Per-Device-Class Models + build_device_context()

**Model file naming changed:**

| `device_class` | File | When created |
|---|---|---|
| `"all"` | `model_{uid}_all.pkl` | At enrollment (always) |
| `"mobile"` | `model_{uid}_mobile.pkl` | When user has 5+ mobile sessions |
| `"desktop"` | `model_{uid}_desktop.pkl` | When user has 5+ desktop sessions |

**Prediction fallback chain:**
```
predict_score(user_id, vector, device_class="desktop")
  │
  ├── Try model_{uid}_desktop.pkl  →  found → use desktop-trained SVM
  │
  └── Not found (mobile-enrolled user, first desktop session)
        ├── Try model_{uid}_all.pkl  →  found → score against combined model
        │     Touch features = 0.0  → z-scores of −7 to −9σ
        │     SVM produces low score (20–35) automatically — no manual rule needed
        └── Not found → return 50 (neutral)
```

**`build_device_context()` — new function:**

Called at `POST /session/start`. Queries `DeviceRegistry` to populate the 5 Device Trust Context features before the feature vector is assembled.

```python
build_device_context(db, user_id, device_fingerprint, device_class)
→ {
    device_class_known:         0|1,
    device_session_count:       int,
    device_class_switch:        0|1,
    is_known_fingerprint:       0|1,
    time_since_last_seen_hours: float
  }
```

Same dict used for:
1. Filling feature vector positions [47:52]
2. Passing as `device_context=` to `fuse_score()`

---

### 4. `score_fusion.py` — 10-Rule Priority Chain

**Signature change:**
```python
# Before
fuse_score(behavior_score: int, sim_swap_active: bool) -> dict

# After
fuse_score(behavior_score: int, sim_swap_active: bool, device_context: dict = None) -> dict
```

`device_context=None` defaults to all-trusted — legacy callers unaffected.

**New rules added (Rules 1–7 replace original Rules 1–2):**

```
Rule 1 [ATTACKER PATTERN — BLOCK_AND_FREEZE]
  sim_swap=True AND device_class_switch=1
  AND is_known_fingerprint=0 AND device_session_count=0
  → score capped at 20, CRITICAL
  Catches: mobile-enrolled, attacker on unknown PC, SIM stolen

Rule 2 [KNOWN DESKTOP USER + SIM SWAP + ANOMALOUS — BLOCK_AND_FREEZE]
  sim_swap=True AND device_class_known=1 AND score < 45
  → score capped at 30, CRITICAL
  Catches: user who uses both mobile/PC, SIM stolen, behavior anomalous

Rule 3 [SIM SWAP ON KNOWN FINGERPRINT — 25% penalty]
  sim_swap=True AND is_known_fingerprint=1
  → score × 0.75, HIGH/MEDIUM, BLOCK/STEP_UP
  Allows: user on regular office PC (seen 3+ times) gets lighter penalty
  (vs 40% penalty for unknown device)

Rule 4 [SIM SWAP + ANOMALOUS — unknown device]
  sim_swap=True AND score < 45
  → score capped at 25, CRITICAL, BLOCK_AND_FREEZE

Rule 5 [SIM SWAP ALONE]
  sim_swap=True
  → score × 0.6, HIGH/MEDIUM

Rule 6 [UNKNOWN DEVICE + BEHAVIORAL DEVIATION — no SIM swap]
  is_known_fingerprint=0 AND device_session_count=0 AND score < 50
  → score × 0.85, MEDIUM, STEP_UP_AUTH
  For: cybercafe/relative's PC + unusual behavior → friction, not block

Rule 7 [UNKNOWN DEVICE + BEHAVIOR NORMAL — cybercafe/relative's PC]
  is_known_fingerprint=0 AND score >= 70
  → no penalty, LOW, ALLOW
  For: legitimate cybercafe user — bank's OTP flow handles new-device

Rules 8–10 [ORIGINAL BEHAVIOR-ONLY RULES — unchanged]
  behavior_score < 30 → CRITICAL | < 45 → HIGH | < 70 → MEDIUM | else → LOW
```

---

### 5. `anomaly_explainer.py` — 55-Feature + Desktop Templates

**Updated:**
- Works with 55-feature vectors automatically (no code change needed — scaler dims match)
- Scaler loading now tries device-specific scaler first, falls back to `all`
- New anomaly templates for desktop-specific features

**New templates:**
```python
"device_class_switch":     "Device class switched from enrolled type — first desktop session"
"is_known_fingerprint":    "Device fingerprint not in trusted registry (seen < 3 times)"
"mouse_movement_entropy":  "Mouse movement entropy below/above expected — possible bot"
"mouse_speed_cv":          "Mouse speed variation below baseline — possible automation"
"scroll_wheel_event_count":"Scroll wheel count outside expected range for device type"
```

---

## All Scenario Outcomes

| Scenario | `is_known_fp` | `class_switch` | `sim_swap` | `behavior_score` | Action |
|---|---|---|---|---|---|
| Regular office PC (NEFT daily) | 1 | 0 | No | 85 | ALLOW |
| Personal home PC, regular use | 1 | 0 | No | 80 | ALLOW |
| Relative's PC, first visit, normal behavior | 0 | 1 | No | 75 | ALLOW |
| Cybercafe, normal behavior | 0 | 1 | No | 72 | ALLOW |
| Cybercafe, anomalous timing | 0 | 1 | No | 44 | STEP_UP_AUTH |
| Friend's PC, unusual navigation | 0 | 1 | No | 48 | STEP_UP_AUTH |
| Own PC, SIM swap, behavior normal | 1 | 0 | Yes | 80 | STEP_UP_AUTH (→60) |
| Own PC, SIM swap, behavior anomalous | 1 | 0 | Yes | 38 | BLOCK_AND_FREEZE |
| Office PC (known), SIM swap | 1 | 0 | Yes | 72 | STEP_UP_AUTH (→54, MEDIUM) |
| **Attacker: unknown PC + SIM swap** | **0** | **1** | **Yes** | **any** | **BLOCK_AND_FREEZE (→≤20)** |
| Attacker: known PC class, SIM swap, anomalous | 1 | 1 | Yes | 35 | BLOCK_AND_FREEZE (→30) |

---

## SVM Detection Without Rules (Natural)

When mobile-enrolled user's feature vector arrives with touch features zeroed out:

| Feature | Mobile Baseline | PC Session Value | Z-Score |
|---|---|---|---|
| `tap_pressure_mean` | 0.72 | 0.0 | −8.4σ |
| `swipe_velocity_mean` | 4.2 | 0.0 | −7.1σ |
| `hand_stability_score` | 0.82 | 0.0 | −9.2σ |
| `accel_x_std` | 0.31 | 0.0 | −6.3σ |
| `gyro_x_std` | 0.18 | 0.0 | −5.8σ |

SVM decision_function → deeply negative → calibrated score: 20–35.
No rule needed for mobile-enrolled user on PC — SVM detects it implicitly.
Rules 1–7 in `score_fusion` add context-awareness on top of this natural detection.

---

## Frontend SDK Requirements

```typescript
const isTouchDevice = navigator.maxTouchPoints > 0;
const isDesktop     = window.innerWidth > 768 && !isTouchDevice;
const deviceClass   = isDesktop ? "desktop" : "mobile";

// Device fingerprint must include touch capability (key differentiator)
const fingerprint = await hashFingerprint({
    userAgent:    navigator.userAgent,
    touchSupport: navigator.maxTouchPoints > 0,  // false on all desktop PCs
    platform:     navigator.platform,            // 'Win32' vs 'iPhone'
    screenWidth:  screen.width,
    colorDepth:   screen.colorDepth,
    timezone:     Intl.DateTimeFormat().resolvedOptions().timeZone,
});

// Track mouse on desktop only
let mousePositions: {x: number, y: number, t: number}[] = [];
let scrollWheelCount = 0;

if (isDesktop) {
    window.addEventListener("mousemove", e =>
        mousePositions.push({x: e.clientX, y: e.clientY, t: Date.now()}));
    window.addEventListener("wheel", () => scrollWheelCount++);
}

// Feature extraction
features["mouse_movement_entropy"]   = isDesktop ? computeEntropy(mousePositions) : 0.0;
features["mouse_speed_cv"]           = isDesktop ? computeSpeedCV(mousePositions)  : 0.0;
features["scroll_wheel_event_count"] = isDesktop ? scrollWheelCount : 0;

// Touch + motion features = 0.0 on desktop (hardware unavailable)
if (isDesktop) {
    features["tap_pressure_mean"]   = 0.0;
    features["swipe_velocity_mean"] = 0.0;
    features["hand_stability_score"]= 0.0;
    features["accel_x_std"]         = 0.0;
    features["gyro_x_std"]          = 0.0;
    // ... all touch + IMU features = 0.0
}

// Session start payload
POST /session/start {
    user_id:            1,
    device_class:       deviceClass,       // "mobile" | "desktop"
    device_fingerprint: fingerprint,
}
```

---

## High-Value Transaction Heuristic (Cybercafe + Large Transfer)

Device trust rules handle most cases. For very large transfers on new devices, additional friction regardless of score:

```python
# In session router — applied after fuse_score()
LARGE_TRANSFER_THRESHOLD = 100_000  # INR

if (is_known_fingerprint == 0
        and transaction_amount > LARGE_TRANSFER_THRESHOLD):
    # Force additional verification even if behavior is normal
    action = max_friction(action, "STEP_UP_AUTH")
    reason += " | High-value transfer on unregistered device"
```

This covers the cybercafe scenario for large NEFT/RTGS transfers without blocking small UPI payments.
