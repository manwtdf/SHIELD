"""
demo/seed_runner.py
────────────────────────────────────────────────────────────────────────────────
ONE command: reset DB → seed data → train Mahalanobis model → verify calibration.
Run this before every demo. Must complete in < 20 seconds.

Usage:
    cd backend
    python ../demo/seed_runner.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.database import init_db, SessionLocal, ENGINE
from db.models import Base, User, Session as SessionModel, DeviceRegistry
from data.seed_legitimate import generate_legitimate_sessions
from data.seed_scenarios import generate_scenario_session, verify_attacker_deviation
from ml.one_class_svm import train, predict, diagnostic_report, model_exists
from ml.score_fusion import fuse_score
from datetime import datetime, timedelta

GREEN  = "\033[92m"
RED    = "\033[91m"
AMBER  = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"   {GREEN}✓{RESET} {msg}")
def fail(msg):  print(f"   {RED}✗{RESET} {msg}")
def warn(msg):  print(f"   {AMBER}⚠{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


def run():
    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  S.H.I.E.L.D — Seed Runner{RESET}")
    print(f"{BOLD}{'═'*55}{RESET}")

    # ── Step 1: Reset database ────────────────────────────────────────────────
    header("1. Resetting database")
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)
    ok("All tables dropped and recreated")

    db = SessionLocal()

    # ── Step 2: Create demo users ─────────────────────────────────────────────
    header("2. Creating demo users")
    enrolled_at = datetime.utcnow() - timedelta(days=30)
    user1 = User(id=1, name="John Kumar",   enrolled_at=enrolled_at)
    user2 = User(id=2, name="Fleet Target", enrolled_at=None)
    db.add_all([user1, user2])
    db.commit()
    ok("User 1: John Kumar (enrolled, 30 days ago)")
    ok("User 2: Fleet Target (for fleet anomaly scenario)")

    # ── Step 3: Register known devices for user 1 ─────────────────────────────
    header("3. Registering known devices")
    for fp in ["DEVICE_KNOWN_001", "DEVICE_KNOWN_002", "DEVICE_KNOWN_003"]:
        db.add(DeviceRegistry(user_id=1, device_fingerprint=fp, is_trusted=True))
    db.commit()
    ok("3 known devices registered for user 1")

    # Register attacker fleet device on user 2 (pre-primes fleet detection)
    db.add(DeviceRegistry(
        user_id=2,
        device_fingerprint="ATTACKER_DEVICE_FLEET_001",
        is_trusted=False,
    ))
    db.commit()
    ok("Fleet attacker device registered on user 2")

    # ── Step 4: Generate legitimate sessions ──────────────────────────────────
    header("4. Generating legitimate sessions (N=10)")
    legitimate_vectors = generate_legitimate_sessions(n=10)
    for vec in legitimate_vectors:
        s = SessionModel(
            user_id=1,
            session_type="legitimate",
            feature_vector=json.dumps(vec),
            completed=True,
        )
        db.add(s)
    db.commit()
    ok(f"10 legitimate sessions seeded (55 features each)")

    # ── Step 5: Verify attacker deviations before training ───────────────────
    header("5. Verifying attacker scenario deviations")
    all_deviations_ok = True
    for sid in range(1, 6):
        result = verify_attacker_deviation(sid)
        if result.get("pre_auth"):
            ok(f"Scenario {sid}: pre-auth (no feature vector — skip)")
            continue
        n_flagged = result["features_above_2.5_sigma"]
        top = result["top_deviations"][:3]
        top_str = ", ".join(f"{f[0]}(z={f[1]:.1f})" for f in top)
        if result["pass"]:
            ok(f"Scenario {sid}: {n_flagged} features > 2.5σ | {top_str}")
        else:
            fail(f"Scenario {sid}: only {n_flagged} features > 2.5σ (need ≥ 4)")
            all_deviations_ok = False
    if not all_deviations_ok:
        warn("Some scenarios have weak attacker signal. Check profiles.py.")

    # ── Step 6: Train Mahalanobis model ───────────────────────────────────────
    header("6. Training Mahalanobis Distance Scorer")
    meta = train(user_id=1, feature_vectors=legitimate_vectors)
    ok(f"Model trained")
    ok(f"Baseline: {meta['baseline_mean']:.1f} ± {meta['baseline_std']:.1f}")
    ok(f"Lambda (calibration): {meta['lambda']:.4f}")
    ok(f"Mean training distance: {meta['mean_training_distance']:.3f}")

    # ── Step 7: Seed scenario sessions ───────────────────────────────────────
    header("7. Seeding attack scenario sessions")

    # Targets: what score range we expect (with sim_swap_active=True fusion)
    SCORE_TARGETS = {
        1: (0, 30),   # new device + SIM → BLOCK
        2: (0, 35),   # laptop + OTP → BLOCK
        3: (0, 25),   # bot → BLOCK (fastest, lowest score)
        4: (40, 65),  # same device → STEP-UP (moderate)
        5: (0, 30),   # fleet → BLOCK
    }

    attacker_vectors_for_diagnostic = {}
    all_scores_ok = True

    for sid in range(1, 6):
        data = generate_scenario_session(sid)
        if data["pre_auth"]:
            ok(f"Scenario {sid}: pre-auth (logged, no ML scoring)")
            continue

        s = SessionModel(
            user_id=1,
            session_type=f"scenario_{sid}",
            feature_vector=json.dumps(data["feature_vector"]),
            completed=True,
        )
        db.add(s)
        db.commit()

        # Score with SIM swap active (how it fires in demo)
        raw_score = predict(1, data["feature_vector"])
        fusion = fuse_score(raw_score, sim_swap_active=True)
        final = fusion["final_score"]

        lo, hi = SCORE_TARGETS[sid]
        in_range = lo <= final <= hi
        if not in_range:
            all_scores_ok = False

        attacker_vectors_for_diagnostic[f"scenario_{sid}"] = data["feature_vector"]

        status = ok if in_range else fail
        label = fusion["action"].replace("_", " ")
        status(
            f"Scenario {sid}: raw={raw_score} fused={final} "
            f"({fusion['risk_level']}, {label}) "
            f"[target {lo}–{hi}] {'✓' if in_range else '✗'}"
        )

    # ── Step 8: Diagnostic report ─────────────────────────────────────────────
    header("8. Full diagnostic report")
    report = diagnostic_report(
        user_id=1,
        legitimate_vectors=legitimate_vectors,
        attacker_vectors=attacker_vectors_for_diagnostic,
    )
    legit = report["legitimate"]
    ok(f"Legitimate scores: mean={legit['mean']:.1f}, "
       f"min={legit['min']}, max={legit['max']}, "
       f"all≥75={'✓' if legit['all_above_75'] else '✗'}")

    if not legit["all_above_75"]:
        fail("Some legitimate sessions scored below 75.")
        warn("This means the training data has high variance OR")
        warn("the LedoitWolf covariance estimate is noisy.")
        warn("Try increasing N legitimate sessions in seed_runner (n=15 or n=20).")

    if not all_scores_ok:
        warn("Some attacker scenarios outside target score range.")
        warn("This usually means the attacker profile needs stronger deviation.")
        warn("Check profiles.py and increase std on key features (e.g. inter_key_delay_mean).")

    # ── Step 9: Progressive snapshot verification ─────────────────────────────
    header("9. Verifying score degradation progression")
    from data.seed_scenarios import generate_scenario_session as gen
    from ml.feature_schema import FEATURE_NAMES as FN

    scenario_1_data = gen(1)
    legit_vec = [meta["per_feature_mean"][i] for i in range(55)]
    attacker_vec = scenario_1_data["feature_vector"]

    progression = []
    for i in range(5):
        alpha = (i + 1) / 5.0
        partial = [(1 - alpha) * l + alpha * a for l, a in zip(legit_vec, attacker_vec)]
        raw = predict(1, partial)
        fused = fuse_score(raw, sim_swap_active=True)["final_score"]
        progression.append(fused)

    ok(f"Scenario 1 progression: {' → '.join(str(s) for s in progression)}")
    monotone = all(progression[i] <= progression[i-1] + 8 for i in range(1, 5))
    if monotone:
        ok("Score is monotonically decreasing (required for animation)")
    else:
        warn("Score progression not monotone — check interpolation in seed_scenarios.py")

    # ── Done ─────────────────────────────────────────────────────────────────
    db.close()
    print(f"\n{BOLD}{'═'*55}{RESET}")
    if legit["all_above_75"] and all_scores_ok:
        print(f"{GREEN}{BOLD}  ✓ SHIELD is ready for demo.{RESET}")
    else:
        print(f"{AMBER}{BOLD}  ⚠ SHIELD seeded with warnings — review above.{RESET}")
    print(f"  Run: uvicorn main:app --reload --port 8000")
    print(f"{BOLD}{'═'*55}{RESET}\n")


if __name__ == "__main__":
    run()
