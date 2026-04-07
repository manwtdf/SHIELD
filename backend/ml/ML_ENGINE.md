# SHIELD ML Engine — Technical Reference (v2)

> Behavioral biometric fraud detection for SIM swap prevention.
> 55-feature vector. CPU-only. Sub-50ms inference. Per-user models.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [feature_schema.py](#1-feature_schemapy)
3. [one_class_svm.py](#2-one_class_svmpy)
4. [score_fusion.py](#3-score_fusionpy)
5. [anomaly_explainer.py](#4-anomaly_explainerpy)
6. [fleet_anomaly.py](#5-fleet_anomalypy)
7. [lstm_autoencoder.py](#6-lstm_autoencoderpy)
8. [Memory and Storage](#7-memory-and-storage)
9. [Runtime Data Flow](#8-runtime-data-flow)
10. [v1 to v2 Change Log](#9-v1-to-v2-change-log)

---

## Architecture Overview

```
Browser / Mobile SDK  →  POST /session/feature  (55-feature snapshot every 6s)
                                  │
               ┌──────────────────┼──────────────────────┐
               │                  │                       │
               ▼                  ▼                       ▼
     feature_schema.py   build_device_context()   fleet_anomaly.py
     validate 55 dims    query DeviceRegistry      cross-account check
               │                  │
               └──────────┬───────┘
                          │
                          ▼
               one_class_svm.py
               predict_score(device_class)
               fallback chain: desktop → all → 50
                          │
                          ▼
               anomaly_explainer.py
               z-scores across all 55 features
               device-class-aware scaler loading
                          │
                          ▼
               score_fusion.py
               10-rule precedence chain
               device_context-aware
                          │
                          ▼
               Dashboard / Alert Feed / Freeze Modal
```

---

## 1. `feature_schema.py`

Single source of truth for **55** behavioral features.
All ML modules and the SDK must match this count exactly.

### Feature Groups

| Group | Count | Description |
|---|---|---|
| Touch Dynamics | 8 | Tap pressure, swipe velocity, gesture curvature, pinch-zoom, tap duration |
| Typing Biometrics | 10 | Inter-key delay (mean/std/p95), dwell time, error rate, WPM, burst patterns |
| Device Motion | 8 | Accelerometer X/Y/Z std, gyroscope X/Y/Z std, device tilt, hand stability |
| Navigation Graph | 9 | Screens visited, nav depth, back presses, time on screens, field order entropy |
| Temporal Behavior | 8 | Session duration, time of day, OTP submit time, click speed, form pace |
| Device Context | 4 | New device flag, fingerprint delta, timezone change, OS version change |
| **Device Trust Context** | **5** | **NEW: device class history, fingerprint trust, class switch detection** |
| **Desktop Mouse Biometrics** | **3** | **NEW: mouse entropy, speed variation, scroll wheel count (0.0 on mobile)** |
| **Total** | **55** | |

### Device Trust Context (NEW)

| Feature | Values | Purpose |
|---|---|---|
| `device_class_known` | 0 or 1 | 1 = user has prior sessions on this device class |
| `device_session_count` | 0..N | Sessions on this exact fingerprint in DeviceRegistry |
| `device_class_switch` | 0 or 1 | 1 = current class != dominant class last 30 days |
| `is_known_fingerprint` | 0 or 1 | 1 = session_count >= 3 (trusted device) |
| `time_since_last_seen_hours` | float | 0 = first-ever session on this device |

Populated by `build_device_context()` at session start. Same values fed to both feature vector and `fuse_score()`.

### Desktop Mouse Biometrics (NEW)

| Feature | Mobile | Human Desktop | Bot/Scripted |
|---|---|---|---|
| `mouse_movement_entropy` | 0.0 | 0.3–0.8 | ~0.02 |
| `mouse_speed_cv` | 0.0 | 0.3–0.7 | ~0.0 (inhuman consistency) |
| `scroll_wheel_event_count` | 0 | 8–30 | 0–2 |

`mouse_speed_cv ≈ 0` on desktop = automation signal. Analogous to `click_speed_std ≈ 0`.

### Assert Guard

```python
assert len(FEATURE_NAMES) == 55  # crashes at import if dimension drifts
```

### Memory

| Item | Size |
|---|---|
| FEATURE_NAMES list in RAM | ~6 KB |
| Source file | ~4.5 KB |

---

## 2. `one_class_svm.py`

Per-user behavioral fingerprint. Trains separate models per device class.
Scores incoming 55-feature vectors by distance from learned legitimate boundary.

### Model

`sklearn.svm.OneClassSVM`  —  `kernel='rbf'`, `nu=0.01`, `gamma='scale'`

### Per-Device-Class Training (NEW)

```python
train_model(user_id: int, device_class: str = "all")
```

| `device_class` | Sessions used | Model saved as |
|---|---|---|
| `"all"` | All legitimate (default, enrollment) | `model_{uid}_all.pkl` |
| `"mobile"` | Mobile sessions only | `model_{uid}_mobile.pkl` |
| `"desktop"` | Desktop sessions only | `model_{uid}_desktop.pkl` |

Minimum training sessions: 5 per class.
Feature dimension guard: rejects vectors where `len != 55`.

### Prediction Fallback Chain (NEW)

```python
predict_score(user_id, feature_vector, device_class="all")
```

```
Request: device_class="desktop"
  ├── Try model_{uid}_desktop.pkl  →  found  →  score against desktop model
  └── Not found
        ├── Try model_{uid}_all.pkl  →  found  →  score against combined model
        │     touch features = 0.0  →  z-scores -7 to -9σ  →  score 20-35 naturally
        └── Not found  →  return 50 (neutral)
```

### `build_device_context()` (NEW)

```python
build_device_context(db, user_id, device_fingerprint, device_class) -> dict
```

Queries DeviceRegistry at session start:
- `session_count >= 3` → `is_known_fingerprint = 1`
- any prior session on same `device_class` → `device_class_known = 1`
- dominant class in last 30 days != current → `device_class_switch = 1`
- hours since `last_seen` on this fingerprint → `time_since_last_seen_hours`

### Memory per User

| Files | Size |
|---|---|
| `model_{uid}_all.pkl` | 80–200 KB |
| `scaler_{uid}_all.pkl` | 10–14 KB (55 means + 55 stds) |
| `metadata_{uid}_all.pkl` | 1–2 KB |
| 3 device classes × 3 files each | 270–648 KB total |

### Inference Time

| Operation | Time |
|---|---|
| `train_model()` on 10 sessions | 300–500ms |
| `predict_score()` | 0.3–1ms |
| `build_device_context()` DB queries | 1–5ms |

---

## 3. `score_fusion.py`

Cascading 10-rule priority chain. First matching rule wins.

### Signature (UPDATED)

```python
fuse_score(
    behavior_score: int,
    sim_swap_active: bool,
    device_context: dict = None  # NEW — defaults to all-trusted if None
) -> dict
# Returns: {final_score, risk_level, action, reason}
```

`device_context=None` → defaults all values to trusted → legacy callers unaffected.

### Priority Chain

| Rule | Conditions | Score | Action |
|---|---|---|---|
| 1 | sim_swap + class_switch=1 + is_known_fp=0 + session_count=0 | cap at 20 | BLOCK_AND_FREEZE |
| 2 | sim_swap + class_known=1 + score < 45 | cap at 30 | BLOCK_AND_FREEZE |
| 3 | sim_swap + is_known_fp=1 | ×0.75 | HIGH→BLOCK / MEDIUM→STEP_UP |
| 4 | sim_swap + score < 45 | cap at 25 | BLOCK_AND_FREEZE |
| 5 | sim_swap | ×0.60 | HIGH→BLOCK / MEDIUM→STEP_UP |
| 6 | is_known_fp=0 + session_count=0 + score < 50 | ×0.85 | STEP_UP_AUTH |
| 7 | is_known_fp=0 + score >= 70 | unchanged | ALLOW |
| 8 | score < 30 | unchanged | BLOCK_AND_FREEZE |
| 9 | score < 45 | unchanged | BLOCK_TRANSACTION |
| 10 | score < 70 | unchanged | STEP_UP_AUTH |
| — | else | unchanged | ALLOW |

### Key PC Scenarios

| Scenario | Rule fired | Action |
|---|---|---|
| Attacker: unknown PC + SIM swap | Rule 1 | BLOCK_AND_FREEZE (score ≤ 20) |
| Office PC regular user | Rules 1–7 all skip → rule 10 | ALLOW |
| Cybercafe, normal behavior | Rule 7 | ALLOW |
| Cybercafe, anomalous behavior | Rule 6 | STEP_UP_AUTH |
| Own PC + SIM swap (behavior OK) | Rule 3 | STEP_UP_AUTH (25% penalty) |
| Own PC + SIM swap + anomalous | Rule 2 | BLOCK_AND_FREEZE |

### Memory

| Item | Size |
|---|---|
| RAM | < 1 KB (pure arithmetic) |
| Inference | < 0.1ms |
| File | ~5 KB |

---

## 4. `anomaly_explainer.py`

Per-feature z-score computation. Explains why SVM scored session low.
Powers Feature Inspector and Alert Feed in Dashboard.

### Updated for 55 Features

Scaler loaded with device_class fallback (`desktop` → `all`).
Works with 55-dim scaler automatically — no explicit dim change needed in loop.

```python
explain_anomalies(user_id, feature_vector, device_class="all") -> list[dict]
top_anomaly_strings(user_id, feature_vector, device_class="all", top_n=4) -> list[str]
```

### New Desktop Templates

```python
"device_class_switch":     "Device class switched from enrolled type — first desktop session"
"is_known_fingerprint":    "Device fingerprint not in trusted registry (seen < 3 times)"
"mouse_movement_entropy":  "Mouse movement entropy below/above expected — possible bot"
"mouse_speed_cv":          "Mouse speed variation below baseline — possible automation"
"scroll_wheel_event_count":"Scroll wheel count outside expected range for device type"
```

### Desktop Z-Scores (Mobile-Enrolled User on PC)

| Feature | Mobile Baseline | PC Value | Z-Score |
|---|---|---|---|
| `tap_pressure_mean` | 0.72 | 0.0 | −8.4σ |
| `swipe_velocity_mean` | 4.2 | 0.0 | −7.1σ |
| `hand_stability_score` | 0.82 | 0.0 | −9.2σ |
| `accel_x_std` | 0.31 | 0.0 | −6.3σ |
| `device_class_switch` | 0.0 | 1.0 | extreme |

### Memory

| Item | Size |
|---|---|
| RAM (55 features) | ~3–5 KB |
| Inference | < 0.5ms |

---

## 5. `fleet_anomaly.py`

Cross-account device detection. Unchanged from v1 except internal refactoring.

### Logic

```
check_fleet_anomaly(device_fingerprint, user_id)
  window = last 60 minutes
  distinct user_ids using this fingerprint >= 2 → CRITICAL_ALL_ACCOUNTS_FROZEN
  _register_device() → upsert DeviceRegistry
```

Device-class agnostic — operates on fingerprint strings only.

### Memory

| Item | Size |
|---|---|
| DeviceRegistry rows | ~200 bytes per (user, device) |
| 10K users × 3 devices | ~6 MB |
| Inference | 1–5ms DB query |

---

## 6. `lstm_autoencoder.py`

Optional roadmap upgrade. No structural change for v2.

**One update:** `FEATURE_DIM = 55` (was implied as 47).
Input shape becomes `(batch, seq_len, 55)`. All encoder/decoder dims auto-scale.

### Memory per User

| File | Size |
|---|---|
| `lstm_{uid}.pt` | 400–700 KB |
| `lstm_meta_{uid}.pkl` | 1–2 KB |

---

## 7. Memory and Storage

### Per-User Storage

| Component | Files | Size |
|---|---|---|
| SVM `_all` model set | 3 pkl files | 90–215 KB |
| SVM `_mobile` model set | 3 pkl files | 90–215 KB |
| SVM `_desktop` model set | 3 pkl files | 90–215 KB |
| **SVM total (all 3 classes)** | **9 files** | **270–645 KB** |
| LSTM (optional) | 2 files | 400–700 KB |

> [!TIP]
> Most users will only have the `_all` model until they accumulate 5+ sessions per class.
> Realistic Storage: **90–215 KB per user** for first 6 months.

### Large-Scale Storage Estimates

| Users | SVM only (`_all` model set) | SVM 3-class + LSTM |
|---|---|---|
| 100 | ~22 MB | ~100 MB |
| 1,000 | ~215 MB | ~1 GB |
| 10,000 | ~2.15 GB | ~10 GB |

### Runtime RAM (per request)

| Component | RAM |
|---|---|
| FastAPI baseline | ~60 MB |
| SQLAlchemy | ~5 MB |
| SVM inference (55 features) | 3–6 MB |
| `build_device_context()` | < 1 MB |
| Fleet anomaly SQL | < 1 MB |
| **Total (SVM path)** | **~70–75 MB** |
| PyTorch LSTM (optional) | +40–80 MB |

### Inference Time per Request

| Step | Time |
|---|---|
| Feature validation | < 0.01ms |
| `build_device_context()` | 1–5ms |
| StandardScaler transform | 0.1ms |
| SVM `decision_function` | 0.3–1ms |
| Z-score computation (55 features) | 0.3–0.6ms |
| Fleet anomaly SQL | 1–5ms |
| Score fusion rules | < 0.1ms |
| DB write | 2–8ms |
| **Total (SVM path)** | **~5–20ms** |

---

## 8. Runtime Data Flow

```
POST /session/feature
{
  session_id:         "uuid",
  device_class:       "desktop",
  device_fingerprint: "sha256:abc...",
  feature_snapshot:   { ...55 features... }
}
          │
          ▼
feature_schema.py  →  assert len == 55
          │
          ├─────────────────────────────┐
          ▼                             ▼
one_class_svm.py              fleet_anomaly.py
build_device_context()         check_fleet_anomaly()
  → device_context dict         → ALLOW | CRITICAL_FROZEN
predict_score(device_class)
  fallback: desktop → all
  touch features = 0.0
  → behavior_score = 28
          │
          ▼
anomaly_explainer.py
  z-scores across 55 features
  tap_pressure_mean:   -8.4σ  🔴
  hand_stability_score:-9.2σ  🔴
  device_class_switch: extreme 🔴
          │
          ▼
score_fusion.py
  sim_swap_active = True
  device_context = {device_class_switch:1, is_known_fingerprint:0, device_session_count:0}
  → Rule 1 fires
  → final_score=20, CRITICAL, BLOCK_AND_FREEZE
  → reason="SIM swap + first-ever device class switch + unknown device fingerprint"
          │
          ▼
Response: {
  score:         20,
  risk_level:    "CRITICAL",
  action:        "BLOCK_AND_FREEZE",
  reason:        "SIM swap + first-ever device class switch + unknown device fingerprint",
  top_anomalies: [
    "Touch behavior absent — possible non-mobile device",
    "Device motion stability 92% below baseline",
    "Device class switched from enrolled type — first desktop session",
    "OTP submitted 45% faster than user average"
  ]
}
```

---

## 9. v1 to v2 Change Log

| Aspect | v1 | v2 |
|---|---|---|
| Feature count | 47 | **55** (+8) |
| Desktop sessions | Not handled | Device trust context + mouse biometrics |
| `fuse_score` params | 2 | **3** (`device_context` added) |
| `fuse_score` rules | 6 | **10** (4 new PC-aware rules) |
| `fuse_score` return | 3 keys | **4 keys** (+ `reason`) |
| SIM swap on known PC | 40% penalty | **25% penalty** (trust earned) |
| Attacker on unknown PC + SIM | Missed | **Rule 1 → BLOCK (score ≤ 20)** |
| Cybercafe normal user | Over-penalized | **Rule 7 → ALLOW** |
| Model file naming | `model_{uid}.pkl` | **`model_{uid}_{class}.pkl`** |
| Model fallback | None | **desktop → all → 50** |
| Feature dim check | Implicit | **Explicit ValueError / error dict** |
| `Session.device_class` | Missing | **Added** |
| `DeviceRegistry` columns | fingerprint + timestamps | **+ device_class, trust_level, session_count** |
| `anomaly_explainer` scaler | Single path | **device-class fallback chain** |
| Desktop anomaly templates | None | **5 new templates** |

---

*SHIELD ML Engine v2 — Session-based Heuristic Intelligence for Event Level Defense*
