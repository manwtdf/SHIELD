# SHIELD ML Engine — Technical Reference

> Behavioral biometric fraud detection layer for SIM swap prevention.
> All models run CPU-only, per-user, sub-50ms inference budget.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [feature_schema.py](#1-feature_schemapy)
3. [one_class_svm.py](#2-one_class_svmpy)
4. [score_fusion.py](#3-score_fusionpy)
5. [anomaly_explainer.py](#4-anomaly_explainerpy)
6. [fleet_anomaly.py](#5-fleet_anomalypy)
7. [lstm_autoencoder.py](#6-lstm_autoencoderpy)
8. [Memory & Storage Reference](#memory--storage-reference)
9. [Runtime Data Flow](#runtime-data-flow)

---

## Architecture Overview

```
Browser SDK (47 features every 6s)
            │
            ▼
    POST /session/feature
            │
     ┌──────┴───────────────────────────────┐
     │                                      │
     ▼                                      ▼
feature_schema.py               fleet_anomaly.py
(validate 47 dims)              (cross-account check)
     │                                      │
     ▼                                      │
one_class_svm.py                            │
(behavior_score 0–100)                      │
     │                                      │
     ▼                                      │
anomaly_explainer.py                        │
(per-feature z-scores)                      │
     │                                      │
     └──────────────┬───────────────────────┘
                    │
                    ▼
            score_fusion.py
     (final_score + risk_level + action)
                    │
                    ▼
     Dashboard / Alert Feed / Freeze Modal
```

---

## 1. `feature_schema.py`

### Role
Single source of truth for all 47 behavioral feature names and their canonical order.
No logic, no computation — pure contract.

### What It Contains

```
FEATURE_NAMES = [ ... ]   # Ordered list of 47 string identifiers
assert len(FEATURE_NAMES) == 47   # Hard crash if list ever breaks
```

### Feature Groups

| Group | Count | Features Captured |
|---|---|---|
| Touch Dynamics | 8 | Tap pressure, swipe velocity, gesture curvature, pinch-zoom, tap duration |
| Typing Biometrics | 10 | Inter-key delay (mean/std/p95), dwell time, error rate, WPM, burst patterns |
| Device Motion | 8 | Accelerometer X/Y/Z std, gyroscope X/Y/Z std, device tilt, hand stability |
| Navigation Graph | 9 | Screens visited, nav depth, back presses, time on screens, field order entropy |
| Temporal Behavior | 8 | Session duration, time of day, OTP submit time, click speed, form pace |
| Device Context | 4 | New device flag, fingerprint delta, timezone change, OS version change |

### Why Each Group Matters

**Touch Dynamics** — Every person applies unique pressure and swipe geometry.
Attacker on new device has zero match to victim's touch profile.

**Typing Biometrics** — Inter-key delay is person-specific, stable across sessions.
Bots produce near-zero variance (`click_speed_std ≈ 0`). Human variance is always present.

**Device Motion** — Phone held by owner has characteristic tilt and micro-vibration from typing.
New device / laptop substitution produces completely different accelerometer signature.

**Navigation Graph** — Legitimate users browse; attackers go directly to payment.
`direct_to_transfer = 1` with `exploratory_ratio ≈ 0` is strong fraud signal.

**Temporal Behavior** — `time_to_submit_otp_ms` is critical signal.
Human reads SMS OTP and types manually: ~8500ms. Bot pastes programmatically: ~800ms.

**Device Context** — Binary flags. `is_new_device = 1` alone shifts SVM score significantly.
Categorical features do not need to be continuous to be informative.

### Assert Guard

```python
assert len(FEATURE_NAMES) == 47
```

Executes at Python import time. If any file adds or removes a feature name,
entire backend crashes before any ML model receives mismatched input.
Prevents silent dimension mismatch bugs.

### Memory Usage

| Item | Size |
|---|---|
| `FEATURE_NAMES` list in RAM | ~4 KB |
| Import overhead | Negligible |
| Disk space | 3.3 KB (source file) |

---

## 2. `one_class_svm.py`

### Role
Core anomaly detector. Learns behavioral fingerprint of legitimate user during enrollment.
Scores incoming sessions by distance from learned boundary.

### Model Used

**`sklearn.svm.OneClassSVM`**
- Kernel: `rbf` (Radial Basis Function / Gaussian)
- Nu: `0.01` (1% of training data allowed as outliers)
- Gamma: `scale` (auto-computed from feature variance)

### Why OneClassSVM

- Training requires only legitimate sessions — no attack samples needed
- RBF kernel creates non-linear boundary matching behavioral manifold
- `nu` parameter absorbs natural legitimate variance (sick days, different environments)
- Single `.pkl` file per user — no stored training data required at inference
- Inference: single distance computation, sub-millisecond

### `train_model(user_id)` — Logic

```
1. Open DB connection
2. Query sessions WHERE user_id=uid AND session_type='legitimate'
3. Abort if count < 5 (insufficient boundary definition)
4. Stack feature_vector_json from all sessions → NumPy array (N, 47)
5. Fit StandardScaler → X_scaled (mean=0, std=1 per feature)
6. Train OneClassSVM on X_scaled
7. Run decision_function on X_scaled → get min_score, max_score
8. Serialize via pickle:
   ├── model_{user_id}.pkl     (SVM)
   ├── scaler_{user_id}.pkl    (StandardScaler)
   └── metadata_{user_id}.pkl (min/max calibration anchors)
9. Return {enrolled, sessions_used, model_saved}
10. Close DB (finally block — always executes)
```

### `predict_score(user_id, feature_vector)` — Logic

```
1. Load model, scaler, metadata from disk
   → FileNotFoundError: return default score 50

2. Wrap feature_vector in NumPy array shape (1, 47)
3. scaler.transform(X) → normalized using SAME scaler from training
   (critical: never refit scaler at inference — must use identical normalization)

4. raw_score = model.decision_function(X_scaled)[0]
   → Positive: inside learned boundary (likely legitimate)
   → Negative: outside boundary (likely attacker)

5. Calibrate raw_score → integer 0–100:

   raw_score >= -0.01  (probable legitimate)
   ├── raw_score >= min_s  → 85 + (raw - min) / range * 10   [maps 85–95]
   └── raw_score < min_s   → 75 + (raw / min_s) * 10         [maps 75–85]

   raw_score < -0.01  (outlier)
   └── 60 - (|raw| / |min_s|) * 40                           [maps 60→0]

6. Clamp → max(0, min(100, value))
7. Return integer score
```

### Calibration Zones

```
Score   Meaning
─────────────────────────────────────────────────
95–100  Deep inside training boundary — very legitimate
85–95   Inside training boundary — legitimate
75–85   Slightly outside training min — borderline
45–75   Outside boundary — suspicious
 0–45   Deep outlier — attack / strong anomaly
─────────────────────────────────────────────────
```

### Training Time

| Sessions | Training Time |
|---|---|
| 5 sessions | ~200ms |
| 10 sessions | ~400ms |
| 20 sessions | ~800ms |

### Memory & Storage (Per User)

| File | Typical Size | Contents |
|---|---|---|
| `model_{uid}.pkl` | 80–200 KB | Support vectors + kernel params |
| `scaler_{uid}.pkl` | 8–12 KB | 47 means + 47 std deviations |
| `metadata_{uid}.pkl` | 1–2 KB | min_score, max_score, user_id |
| **Total per user** | **~100–215 KB** | |

| Runtime | RAM Usage |
|---|---|
| Model loaded (inference) | 2–5 MB |
| NumPy array (1, 47) | < 1 KB |
| StandardScaler transform | < 1 KB |
| **Total inference RAM** | **~3–6 MB** |

| Timing | Duration |
|---|---|
| `train_model()` | 300–500ms (10 sessions) |
| `predict_score()` | 0.3–1ms |

---

## 3. `score_fusion.py`

### Role
Combines SVM behavioral score with SIM swap telecom signal.
Applies cascading priority rules to produce final risk verdict.

### Model Used
**No ML model. Pure rule-based decision function.**
Deterministic priority chain over two inputs.

### Why Rule-Based

SIM swap is a binary, verifiable external event from telecom API.
Combining probabilistic behavioral score with binary external signal
using rules is more reliable than learning a combiner — no training data exists
for such combinations, and rules are fully auditable.

### `fuse_score(behavior_score, sim_swap_active)` — Logic

```
Inputs:
  behavior_score    int  0–100  (from one_class_svm.predict_score)
  sim_swap_active   bool        (from sim_swap_events table)

Priority chain (first match wins):

Rule 1: sim_swap_active=True AND behavior_score < 45
        → final_score = min(behavior_score, 25)
        → risk_level  = CRITICAL
        → action      = BLOCK_AND_FREEZE
        Rationale: SIM confirmed stolen + behavior anomalous = certain fraud

Rule 2: sim_swap_active=True (any score)
        → final_score = int(behavior_score × 0.6)
        → risk_level  = HIGH   if final_score < 45
                        MEDIUM if final_score >= 45
        → action      = BLOCK_TRANSACTION or STEP_UP_AUTH
        Rationale: SIM swap alone is enough to penalize 40% regardless of behavior

Rule 3: behavior_score < 30 (no SIM swap)
        → risk_level = CRITICAL
        → action     = BLOCK_AND_FREEZE
        Rationale: Behavior alone is catastrophically anomalous

Rule 4: behavior_score < 45
        → risk_level = HIGH
        → action     = BLOCK_TRANSACTION

Rule 5: behavior_score < 70
        → risk_level = MEDIUM
        → action     = STEP_UP_AUTH

Rule 6: else
        → risk_level = LOW
        → action     = ALLOW

Output:
  {final_score: int, risk_level: str, action: str}
```

### Score Impact of SIM Swap

```
behavior_score=80, sim_swap=False  →  final=80,  LOW,      ALLOW
behavior_score=80, sim_swap=True   →  final=48,  MEDIUM,   STEP_UP_AUTH
behavior_score=50, sim_swap=True   →  final=30,  HIGH,     BLOCK_TRANSACTION
behavior_score=40, sim_swap=True   →  final=25,  CRITICAL, BLOCK_AND_FREEZE
behavior_score=25, sim_swap=False  →  final=25,  CRITICAL, BLOCK_AND_FREEZE
```

### Memory & Storage

| Item | Size |
|---|---|
| Source file | 1.4 KB |
| RAM at runtime | < 1 KB (pure arithmetic) |
| Inference time | < 0.1ms |
| Disk storage | None (no model files) |

---

## 4. `anomaly_explainer.py`

### Role
Answers: *why* was this session flagged?
Computes per-feature deviation from user's learned baseline.
Powers Feature Inspector table and Alert Feed in dashboards.

### Model Used
**No ML model. Statistical z-score computation using StandardScaler parameters.**
Reuses scaler already fitted during `train_model()`.

### Why Z-Score

- Reuses data already computed — zero marginal computation cost
- Deterministic: identical input always produces identical explanation
- Statistically interpretable: "3.8 standard deviations above your baseline"
- RBI audit-compliant: regulator can independently verify calculation
- Threshold |z| > 2.5 captures ~99% of normal variation within ±2.5σ

### `explain_anomalies(user_id, feature_vector)` — Logic

```
1. Validate len(feature_vector) == 47
   → raise ValueError if not (prevents silent wrong scores)

2. Load scaler_{user_id}.pkl
   → scaler.mean_  : array (47,) — user's historical mean per feature
   → scaler.scale_ : array (47,) — user's historical std dev per feature
   → FileNotFoundError: return empty explanation (z=0, flagged=False for all)

3. Compute z-scores:
   z[i] = (session_value[i] - baseline_mean[i]) / baseline_std[i]
   safe_std = max(baseline_std, 1e-8)  (prevent divide-by-zero for binary features)

4. Build result list (47 dicts):
   {
     name:           feature name string
     value:          session's actual value
     baseline_mean:  user's historical average
     baseline_std:   user's historical standard deviation
     z_score:        deviation in standard deviations
     flagged:        |z_score| > 2.5
   }

5. Sort by |z_score| descending (most anomalous first)
6. Return sorted list
```

### `top_anomaly_strings(user_id, feature_vector, top_n=4)` — Logic

```
1. Call explain_anomalies()
2. Filter: flagged=True only
3. Take top N results
4. Format each as human-readable string:
   "inter_key_delay_mean: 3.8 std above baseline (value=310.00, baseline=180.00)"
5. If no flagged features: return ["No significant anomalies detected"]
6. Return list of strings → fed into Alert Feed cards and score API response
```

### Z-Score Interpretation

```
|z-score|   Interpretation
─────────────────────────────────────────────────
0.0 – 1.0   Normal variation — within expected range
1.0 – 2.0   Slight deviation — not flagged
2.0 – 2.5   Moderate deviation — approaching threshold
2.5 – 3.5   Flagged — statistically significant anomaly
3.5 – 5.0   Strong anomaly — highly suspicious
> 5.0       Extreme anomaly — near-certain fraud signal
─────────────────────────────────────────────────
```

### Real Signal Examples

| Feature | Baseline | Attack Session | Z-Score | Interpretation |
|---|---|---|---|---|
| `inter_key_delay_mean` | 180ms | 310ms | +3.8 | Attacker types slowly, unfamiliar layout |
| `time_to_submit_otp_ms` | 8500ms | 800ms | -3.2 | Bot pasted OTP programmatically |
| `direct_to_transfer` | 0.15 | 1.0 | +4.1 | Straight to payment screen, no exploration |
| `hand_stability_score` | 0.82 | 0.51 | -3.1 | Unfamiliar device, different grip |
| `click_speed_std` | 120ms | 2ms | -4.7 | Inhuman consistency — automation |

### Memory & Storage

| Item | Size |
|---|---|
| Source file | ~3 KB |
| RAM at runtime (scaler loaded) | 2–4 KB (47 floats × 2 arrays) |
| Disk storage | None (reuses scaler file from SVM) |
| Inference time | < 0.5ms for all 47 features |

---

## 5. `fleet_anomaly.py`

### Role
Cross-account attack detection. Identifies same device used across
multiple user accounts in a short time window. Catches fraud rings.

### Model Used
**No ML model. Deterministic SQL query against `device_registry` table.**

### Why Rule-Based

Pattern is absolute: same physical device hitting multiple distinct accounts
within 60 minutes has no legitimate explanation. Probabilistic model would
introduce false positive risk where none is warranted. Rule is 100% precise.

### `check_fleet_anomaly(device_fingerprint, user_id)` — Logic

```
1. Compute cutoff = now - 60 minutes

2. _query_device_registry(db, fingerprint, cutoff):
   CREATE TABLE IF NOT EXISTS device_registry (...)  [demo-safe idempotent]
   SELECT DISTINCT user_id
   FROM device_registry
   WHERE device_fingerprint = :fp
     AND last_seen >= :cutoff
   → Returns set of user_ids who used this device recently

3. _register_device(db, fingerprint, user_id):
   Check if (user_id, fingerprint) row exists
   ├── Exists: UPDATE last_seen = now
   └── New:    INSERT (user_id, fingerprint, first_seen=now, last_seen=now)
   COMMIT

4. Evaluate:
   len(distinct_accounts) >= 2?
   ├── True:  fleet_anomaly=True, action=CRITICAL_ALL_ACCOUNTS_FROZEN
   └── False: fleet_anomaly=False, action=ALLOW

5. Return:
   {
     fleet_anomaly:    bool
     accounts_seen:    int
     action:           str
     flagged_accounts: list[int]   (all user_ids using this device)
     device_fingerprint: str
   }
```

### Detection Timeline (Scenario 5)

```
T+0s   Account A logs in → device registered
T+3m   Account B logs in → same fingerprint
       _query_device_registry → returns {A, B} → len=2 → FLEET ANOMALY
       Both accounts → CRITICAL_ALL_ACCOUNTS_FROZEN
T+5m   Account C logs in → same fingerprint
       All 3 accounts remain frozen
```

### Memory & Storage

| Item | Size |
|---|---|
| Source file | ~4 KB |
| `device_registry` table | ~200 bytes per (user, device) row |
| Rows at scale (10K users, 3 devices each) | ~6 MB total DB space |
| RAM at runtime | < 1 KB (SQL result set) |
| Inference time | 1–5ms (single indexed SQL query) |

---

## 6. `lstm_autoencoder.py`

### Role
Roadmap / production upgrade variant. Treats session as time series of
behavioral snapshots rather than single static feature vector.
Detects temporal anomalies invisible to SVM (sequence order, behavioral rhythm).

### Model Used

**`torch.nn.LSTM` — Sequence-to-sequence Autoencoder**

```
Architecture:
  Encoder LSTM: (batch, seq_len, 47) → hidden state (batch, 32)
  Repeat hidden: (batch, 32) → (batch, seq_len, 32)
  Decoder LSTM: (batch, seq_len, 32) → (batch, seq_len, 47)

Loss: MSELoss(reconstructed, original)
Anomaly score: reconstruction error magnitude
```

### Why LSTM Autoencoder

- SVM receives single aggregate vector — loses sequence ordering
- LSTM processes each snapshot in order — position in session matters
- Autoencoder trained only on legitimate sequences (same constraint as SVM)
- High reconstruction error = session behavior sequence unlike training = anomaly
- Catches behavioral rhythm: legitimate users slow down on transfer screens,
  attackers move at constant high speed throughout

### `LSTMAutoencoder` Class

```
__init__(feature_dim=47, hidden_dim=32, num_layers=1)
  self.encoder = LSTM(input=47, hidden=32, batch_first=True)
  self.decoder = LSTM(input=32, hidden=47, batch_first=True)

forward(x: Tensor[batch, seq_len, 47])
  _, (hidden, cell) = self.encoder(x)
  latent = hidden[-1]                        # (batch, 32)
  latent_seq = latent.repeat(seq_len, dim=1) # (batch, seq_len, 32)
  reconstructed, _ = self.decoder(latent_seq)
  return reconstructed                       # (batch, seq_len, 47)
```

### `train_lstm(user_id, session_sequences)` — Logic

```
Input: session_sequences — list of sessions
       Each session = list of snapshots, each snapshot = 47 floats
       Shape per session: (num_snapshots, 47)

1. Check >= 10 sessions (else return error)
2. Instantiate LSTMAutoencoder + Adam optimizer + MSELoss

3. Training loop (50 epochs):
   For each epoch:
     For each session sequence:
       x = Tensor(seq).unsqueeze(0)   # (1, num_snapshots, 47)
       reconstructed = model(x)
       loss = MSELoss(reconstructed, x)
       loss.backward() → optimizer.step()
   Track epoch_loss / num_sessions

4. Post-training threshold:
   Run model on all training sessions in eval mode
   errors = [MSELoss(model(x), x) for x in training_sessions]
   threshold = max(errors) × 1.2     (20% safety buffer)

5. Save:
   lstm_{user_id}.pt        (model state dict)
   lstm_meta_{user_id}.pkl  ({threshold, user_id, final_loss})

6. Return {trained, epochs, final_loss, anomaly_threshold, model_path}
```

### `predict_lstm_score(user_id, session_sequence)` — Logic

```
1. Load lstm_{user_id}.pt + lstm_meta_{user_id}.pkl
   → Missing: return default score 50

2. x = Tensor(session_sequence).unsqueeze(0)   # (1, num_snapshots, 47)
3. model.eval() → no gradient computation
4. recon = model(x)
5. error = MSELoss(recon, x).item()

6. Map error → score 0–100:
   error <= threshold:
     score = 100 - int((error / threshold) * 50)    [100 → 50]
   error > threshold:
     overshoot = (error - threshold) / threshold
     score = max(0, 50 - int(overshoot * 50))        [50 → 0]

7. Clamp to [0, 100] → return integer
```

### Score Mapping Visualization

```
Reconstruction Error     Score
─────────────────────────────────────────────
0                        100  (perfect reconstruction)
threshold × 0.5          75   (half-threshold error)
threshold × 1.0          50   (at boundary)
threshold × 1.5          25   (50% over boundary)
threshold × 2.0+          0   (definite anomaly)
─────────────────────────────────────────────
```

### Training Configuration

| Parameter | Value | Rationale |
|---|---|---|
| `hidden_dim` | 32 | Sufficient compression for 47-feature space |
| `num_layers` | 1 | Single layer adequate for 4–6 step sequences |
| `epochs` | 50 | Convergence typically at 30–40 for this scale |
| `lr` | 0.001 | Adam default — stable convergence |
| `batch_size` | 1 | Each session processed individually |
| `threshold_buffer` | 1.2× | 20% above worst training error |

### Memory & Storage (Per User)

| File | Size | Contents |
|---|---|---|
| `lstm_{uid}.pt` | 400–600 KB | LSTM weight tensors |
| `lstm_meta_{uid}.pkl` | 1–2 KB | threshold, loss, user_id |
| **Total per user** | **~400–600 KB** | |

| Runtime | RAM Usage |
|---|---|
| PyTorch import overhead | 40–80 MB (one-time, shared) |
| Model loaded per user | 2–5 MB |
| Input tensor (1, 6, 47) | < 1 KB |
| Inference computation graph | ~5 MB (freed after `.no_grad()`) |
| **Total inference RAM** | **~50–90 MB** |

| Timing | Duration |
|---|---|
| `train_lstm()` 10 sessions, 50 epochs | 20–60 seconds (CPU) |
| `predict_lstm_score()` | 5–20ms (CPU) |
| PyTorch first import | 500ms–2s (one-time) |

> [!NOTE]
> LSTM is positioned as production upgrade path only.
> SVM handles all demo scenarios. LSTM activates when sequence-level
> behavioral patterns need detection and infrastructure supports heavier inference.

---

## Memory & Storage Reference

### Per-User Storage Breakdown

| Component | Files | Size per User |
|---|---|---|
| One-Class SVM | `model_{uid}.pkl` | 80–200 KB |
| StandardScaler | `scaler_{uid}.pkl` | 8–12 KB |
| SVM Calibration | `metadata_{uid}.pkl` | 1–2 KB |
| **SVM Total** | **3 files** | **~90–215 KB** |
| LSTM Model | `lstm_{uid}.pt` | 400–600 KB |
| LSTM Metadata | `lstm_meta_{uid}.pkl` | 1–2 KB |
| **LSTM Total** | **2 files** | **~400–600 KB** |
| **Combined (both)** | **5 files** | **~490–815 KB per user** |

### Storage at Scale

| Users | SVM Only | SVM + LSTM |
|---|---|---|
| 100 | ~22 MB | ~82 MB |
| 1,000 | ~215 MB | ~815 MB |
| 10,000 | ~2.1 GB | ~8.1 GB |
| 100,000 | ~21 GB | ~81 GB |

> [!TIP]
> At 100K users, SVM-only storage (21 GB) fits on standard VPS SSD.
> LSTM at 100K users (81 GB) requires dedicated storage. Compress with `gzip`
> on old `.pkl` files — typical 40–60% reduction.

### Runtime RAM Breakdown (One Request)

| Component | Active RAM |
|---|---|
| FastAPI + Python baseline | ~60 MB |
| SQLAlchemy + SQLite connection | ~5 MB |
| StandardScaler (inference) | < 1 MB |
| One-Class SVM (inference) | 2–5 MB |
| NumPy arrays (feature vector) | < 1 MB |
| Z-score computation | < 1 MB |
| Fleet anomaly (SQL result) | < 1 MB |
| **Total (SVM mode)** | **~70–75 MB** |
| PyTorch import overhead | +40–80 MB |
| LSTM model (inference) | +2–5 MB |
| **Total (LSTM mode)** | **~115–160 MB** |

### Inference Time per Request

| Step | Time |
|---|---|
| Feature validation (`feature_schema`) | < 0.01ms |
| StandardScaler transform | 0.1ms |
| OneClassSVM decision_function | 0.3–1ms |
| Z-score computation (47 features) | 0.2–0.5ms |
| Fleet anomaly SQL query | 1–5ms |
| Score fusion rules | < 0.1ms |
| DB write (score record) | 2–8ms |
| **Total (SVM path)** | **~5–15ms** |
| LSTM forward pass (replaces SVM) | 5–20ms |
| **Total (LSTM path)** | **~10–35ms** |

Both paths comfortably within 50ms API budget.

---

## Runtime Data Flow

```
POST /session/feature
{
  session_id: "uuid",
  feature_snapshot: {
    "tap_pressure_mean": 0.72,
    "inter_key_delay_mean": 185.3,
    ... (47 total)
  },
  snapshot_index: 2
}

          │
          ▼
feature_schema.py
  assert len(feature_snapshot) == 47
  order values by FEATURE_NAMES → float array [0.72, 185.3, ...]

          │
          ├──────────────────────────────────────────────────────┐
          ▼                                                      ▼
one_class_svm.py                                    fleet_anomaly.py
  scaler.transform([...47 floats...])                 query device_registry
  model.decision_function(X_scaled)                  WHERE device=fp AND last_seen>=cutoff
  calibrate → behavior_score=74                       len(accounts) < 2 → ALLOW
          │
          ▼
anomaly_explainer.py
  z_scores = (session - baseline_mean) / baseline_std
  flagged = [f for f in features if |z| > 2.5]
  top_anomalies = ["inter_key_delay: +3.8σ above baseline", ...]

          │
          ▼
score_fusion.py
  sim_swap_active = query sim_swap_events WHERE user_id=1 AND is_active=True
  fuse_score(behavior_score=74, sim_swap_active=True)
  → final_score = 74 × 0.6 = 44
  → risk_level  = HIGH
  → action      = BLOCK_TRANSACTION

          │
          ▼
Response:
{
  "score": 44,
  "risk_level": "HIGH",
  "action": "BLOCK_TRANSACTION",
  "top_anomalies": [
    "inter_key_delay_mean: 3.8 std above baseline (value=310.00, baseline=180.00)",
    "direct_to_transfer: 4.1 std above baseline (value=1.00, baseline=0.15)",
    "time_to_submit_otp_ms: 3.2 std below baseline (value=800.00, baseline=8500.00)",
    "hand_stability_score: 3.1 std below baseline (value=0.51, baseline=0.82)"
  ]
}
```

---

