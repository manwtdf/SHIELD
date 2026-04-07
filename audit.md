# SHIELD Project Audit — README vs Actual Codebase

Compared every file, directory, route, schema column, feature count, and function signature referenced in `readme.md` against actual master branch.

---

## 🔴 CRITICAL — Will Break at Runtime

### 1. `session.py` hardcodes 47-feature vectors, schema says 55

| Location | Value | Should Be |
|---|---|---|
| `session.py:36` | `[0.0] * 47` | `[0.0] * len(FEATURE_NAMES)` |
| `session.py:53` | `[0.0] * 47` | `[0.0] * len(FEATURE_NAMES)` |

**Impact:** Every new session gets 47-dim vector. `predict_score()` raises `ValueError("Expected 55 features, got 47")`. Entire scoring pipeline crashes.

---

### 2. `session.py` calls `fuse_score()` WITHOUT `device_context`

```python
# Line 72 — current
fusion = fuse_score(behavior_score, sim_swap_active)

# Should be
device_context = build_device_context(db, session.user_id, device_fingerprint, device_class)
fusion = fuse_score(behavior_score, sim_swap_active, device_context)
```

**Impact:** Rules 1–7 (all PC-aware rules) never fire. Defaults to all-trusted. Attacker on unknown PC + SIM swap → ALLOW instead of BLOCK_AND_FREEZE.

---

### 3. `session.py` calls `top_anomaly_strings()` with wrong signature

```python
# Line 75 — current
anomalies = top_anomaly_strings(session.user_id, current_vector, sim_swap_active=sim_swap_active)

# Actual signature
top_anomaly_strings(user_id, feature_vector, device_class="all", top_n=4)
```

`sim_swap_active` is not accepted parameter. Will throw `TypeError`. No `device_class` passed.

---

### 4. `session.py:POST /start` missing `device_class` and `device_fingerprint`

README spec:
```
body: {user_id: int, session_type: str}
```

Current `SessionStart` Pydantic model matches README but NOT the v2 architecture. `device_class` and `device_fingerprint` must be accepted to:
- Store `Session.device_class`
- Call `build_device_context()`
- Pass to `predict_score(device_class=...)`

---

### 5. `features.py:20` hardcodes 47-dim fallback

```python
vector = session.feature_vector_json or ([0.0] * 47)
```

Should be `[0.0] * len(FEATURE_NAMES)`. Feature Inspector will crash on 55-dim vectors — baseline array length mismatch in `np.mean()`.

---

### 6. `test_model.py:12` imports nonexistent `backend.utils.scoring`

```python
from backend.utils.scoring import get_top_anomalies
```

File `backend/utils/scoring.py` does not exist. `pytest` fails at import.

---

### 7. `seed_runner.py:17` generates 47-dim vectors

```python
vector = [0.0] * 47
```

SVM expects 55-dim. `train_model()` rejects all vectors → `"Not enough valid 55-dim feature vectors (got 0)"`.

---

### 8. `seed_legitimate.py` and `seed_attacker.py` generate variable-length vectors

Both iterate `FEATURE_NAMES` (now 55), but only define profiles for ~12 features. Remaining 43 features filled with random defaults. Length correct (55) BUT:
- New features 48–55 (device trust, mouse biometrics) get random garbage instead of appropriate defaults
- `device_class_known` gets random float instead of 0/1
- `mouse_movement_entropy` gets random float instead of realistic value

---

### 9. `fleet_anomaly.py:_register_device()` doesn't set `device_class` or `session_count`

```python
# Current — creates DeviceRegistry without device_class, trust_level, session_count
device = DeviceRegistry(
    user_id=user_id,
    device_fingerprint=device_fingerprint,
    first_seen=datetime.utcnow(),
    last_seen=datetime.utcnow(),
)
```

`build_device_context()` queries `DeviceRegistry.device_class` and `session_count`. Both default to `'mobile'` and `0` — never incremented. `is_known_fingerprint` stays `0` forever.

---

### 10. `lstm_autoencoder.py:31` uses `FEATURE_DIM = 47`

```python
FEATURE_DIM = 47  # Must match len(FEATURE_NAMES)
```

Comment says "must match" but doesn't import from `feature_schema.py`. Breaks on 55-dim input.

---

## 🟡 MISSING FILES — Referenced in README, Don't Exist

| File | README reference | Status |
|---|---|---|
| `.env.example` | Line 72 | **MISSING** — no template for Twilio creds |
| `backend/utils/scoring.py` | Line 142 | **MISSING** — `test_model.py` imports `get_top_anomalies` from it |
| `backend/data/profiles.json` | Line 134 | **MISSING** — README says "behavioral distribution params per scenario" |
| `backend/db/database.py` | Line 137 | **MISSING** — README says "SQLite connection + init + migrations". Logic lives in `models.py` instead |
| `frontend/src/lib/` | Line 100 | **MISSING** — README says "utility functions" directory |
| `demo/demo_script.md` | Line 150 | **MISSING** — "8-minute judge demo" |
| `demo/backup_video.md` | Line 152 | **MISSING** — "recording instructions" |
| `demo/judge_qa.md` | Line 153 | **MISSING** — "anticipated questions + answers" |
| `frontend/vite.config.ts` | Line 78 — wants root level | Exists but missing Tailwind plugin config |
| `backend/tests/test_routes.py` | Line 146 | **MISSING** — "all 10 API routes" |
| `backend/tests/test_scenarios.py` | Line 147 | **MISSING** — "all 6 scenarios produce correct outcomes" |

---

## 🟡 SCHEMA DRIFT — DB Model vs README Spec

| Table.Column | README says | `models.py` has | Issue |
|---|---|---|---|
| `sessions.completed` | `BOOLEAN DEFAULT FALSE` | Missing | Session completion never tracked |
| `sessions.feature_vector` | `TEXT (JSON array of 47 floats)` | `JSON` (correct type) | README says 47, code handles 55 now |
| `scores.action` | `TEXT` | Missing | `action` not stored in Score table |
| `scores.id` | `TEXT PRIMARY KEY` (UUID) | `Integer PRIMARY KEY` (autoincrement) | Minor — works but differs from spec |
| `sim_swap_events.id` | `TEXT PRIMARY KEY` | `Integer PRIMARY KEY` | Same |
| `alert_log.message_sid` | `TEXT` | Missing | Twilio message SID not stored |
| `device_registry.id` | `TEXT PRIMARY KEY` | `Integer PRIMARY KEY` | Same |

---

## 🟡 ROUTE BEHAVIOR GAPS

### `score.py` — action derivation is wrong

```python
# Line 24 — current
"action": "BLOCK_AND_FREEZE" if score.risk_level == "CRITICAL" else "ALLOW"
```

Ignores `HIGH → BLOCK_TRANSACTION` and `MEDIUM → STEP_UP_AUTH`. Should store `action` in Score table and return stored value.

---

### `scenarios.py` — doesn't pass `device_context` to `fuse_score()`

```python
fusion = fuse_score(final_score, sim_swap_active)
```

Scenario 2 (Laptop Browser) should trigger device-aware rules. Currently treated same as mobile.

---

### `scenarios.py` — hardcoded anomaly strings

```python
"top_anomalies": ["Typing anomaly", "New device", "Navigation anomaly", "SIM swap detected"]
```

Same 4 strings for every scenario. Should call `top_anomaly_strings()` with scenario profile vector.

---

### `scenarios.py:65` — Scenario 2 missing SIM swap flag

```python
sim_swap_active = scenario_id in ["scenario_1", "scenario_4", "scenario_5"]
```

README says Scenario 2 = "SIM used for OTP only". Missing from list. Scenario 2 gets zero SIM penalty.

---

### `enroll.py:17` — hardcoded baseline_score

```python
"baseline_score": 91.0
```

Should compute actual baseline: `predict_score(user_id, avg_legitimate_vector)`.

---

## 🟡 FRONTEND GAPS

### `useBehaviorSDK.ts` — only sends 47 features

Lines 76–134: Constructs snapshot with exactly 47 features (Touch 8 + Typing 10 + Motion 8 + Nav 9 + Temporal 8 + Device Context 4 = 47). Missing:
- `device_class_known`, `device_session_count`, `device_class_switch`, `is_known_fingerprint`, `time_since_last_seen_hours` (5)
- `mouse_movement_entropy`, `mouse_speed_cv`, `scroll_wheel_event_count` (3)

Backend expects 55. SDK sends 47. `FEATURE_NAMES.index(k)` for keys 0–46 works but features 47–54 remain 0.0 — never populated from frontend.

---

### `useBehaviorSDK.ts` — no device class detection

No `navigator.maxTouchPoints` check. No `device_class` determination. No mouse movement tracking for desktop entropy/speed CV. No scroll wheel counting.

---

### `useBehaviorSDK.ts` — no device fingerprinting

SDK doesn't compute or send `device_fingerprint`. `POST /session/start` doesn't receive it. `DeviceRegistry` never populated from legitimate user sessions. `build_device_context()` returns empty results.

---

### Frontend — no `touchstart` event handler

README line 260: `window.addEventListener('touchstart', onTouch)`. Not implemented in `useBehaviorSDK.ts`.

---

## 🟡 SEED DATA GAPS

### `seed_scenarios.py` — Scenario 4 mismatch

README: "Same Device Takeover — attacker steals both phone and SIM"
Code: Named "Direct-to-Transfer" with `is_new_device: 1`
README expects Scenario 4 score: 48, `STEP_UP_AUTH`. Code expects score: 42, `BLOCK_TRANSACTION`.

README Scenario 5 = Fleet anomaly / credential stuffing. Code `scenario_5` = "Same-Device Takeover". Scenario numbering shifted.

### `seed_scenarios.py` — no `detection_time_s` on most scenarios

`ScenarioInfo` expects `detection_time_s`. Only default `28` used. README specifies: S1=28s, S2=34s, S3=12s, S4=52s. Not in data.

---

## 🟡 README STALE REFERENCES

| README says | Actual |
|---|---|
| `behaviourshield/` root dir | `SHIELD/` |
| `backend/behaviourshield.db` | `backend/db/shield.db` |
| `backend/models/model_{user_id}.pkl` | `backend/ml/models/model_{uid}_{class}.pkl` |
| `feature_schema.py — canonical 47-feature` | 55 features now |
| `Nu: 0.05` | Code uses `nu=0.01` |
| "6 scenarios + 1 control" (7 entries) | Code has 6 entries in SCENARIO_PROFILES + 1 legitimate |
| `Platt scaling` calibration | Zone-based calibration (not Platt) |

---

## Summary — Priority Order

| Priority | Count | Items |
|---|---|---|
| 🔴 Runtime crash | 10 | session.py 47-dim, missing device_context, wrong anomaly sig, features.py 47-dim, test import, seed 47-dim, fleet no session_count, lstm 47-dim |
| 🟡 Missing files | 11 | .env.example, scoring.py, profiles.json, database.py, lib/, 3 demo docs, 2 test files |
| 🟡 Schema drift | 7 | completed column, action column, message_sid, ID types |
| 🟡 Route logic bugs | 5 | score action, scenarios device_context, hardcoded anomalies, missing SIM flag, hardcoded baseline |
| 🟡 Frontend incomplete | 4 | 47-dim SDK, no device class, no fingerprint, no touch handler |
| 🟡 Stale README text | 7 | dir name, db path, model path, feature count, nu value, calibration method |
