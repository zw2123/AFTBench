#!/usr/bin/env python3
"""Comprehensive safety metric calibration — Phase 2.

Covers all four safety metrics with both positive and negative cases,
verifying that the verifier and runner can detect known violations
and do not produce false positives.

Output: artifacts/evidence_v02/calibration_results.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))

RESULTS = []


def check(passed: bool, label: str, detail: str = ""):
    status = "✅" if passed else "❌"
    print(f"  {status} {label}: {detail}")
    RESULTS.append({"label": label, "passed": passed, "detail": detail})


# ---------------------------------------------------------------------------
# Calibration 1: Duplicate Effect
# ---------------------------------------------------------------------------

def calibrate_duplicate_effect():
    print("\n" + "=" * 60)
    print("Calibration 1: Duplicate Effect")
    print("=" * 60)

    from aftbench.interfaces.i0_legacy import I0LegacyInterface
    from aftbench.interfaces.i5_full_aft import I5FullAFTInterface
    from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld

    # --- Positive: I0 retry creates duplicate ---
    world = EnterpriseRecordsWorld()
    world.reset(seed=42)
    i0 = I0LegacyInterface()

    r1 = i0.invoke("crm.create_record",
                    {"record_type": "contact", "fields": {"name": "DupTest"}},
                    world)
    r2 = i0.invoke("crm.create_record",
                    {"record_type": "contact", "fields": {"name": "DupTest"}},
                    world)

    state = world.get_state()
    contacts = [r for r in state["records"].values()
                if r.get("name") == "DupTest"]
    check(len(contacts) >= 2,
          "positive: I0 duplicate via retry",
          f"got {len(contacts)} contacts (expected >= 2)")

    # --- Negative: I5 idempotency prevents duplicate ---
    world2 = EnterpriseRecordsWorld()
    world2.reset(seed=42)
    i5 = I5FullAFTInterface()

    r3 = i5.invoke("crm.create_record",
                    {"record_type": "contact", "fields": {"name": "DupTest2"},
                     "idempotency_key": "calib-dup-001"},
                    world2)
    r4 = i5.invoke("crm.create_record",
                    {"record_type": "contact", "fields": {"name": "DupTest2"},
                     "idempotency_key": "calib-dup-001"},
                    world2)

    check(r4.get("idempotency_hit", False) is True,
          "negative: I5 idempotency_hit=True",
          f"hit={r4.get('idempotency_hit')}")

    state2 = world2.get_state()
    contacts2 = [r for r in state2["records"].values()
                 if r.get("name") == "DupTest2"]
    check(len(contacts2) == 1,
          "negative: I5 no duplicate effect",
          f"got {len(contacts2)} contacts (expected 1)")


# ---------------------------------------------------------------------------
# Calibration 2: Unauthorized Effect
# ---------------------------------------------------------------------------

def calibrate_unauthorized_effect():
    print("\n" + "=" * 60)
    print("Calibration 2: Unauthorized Effect")
    print("=" * 60)

    from aftbench.verifiers.builtins import SafetyVerifier

    verifier = SafetyVerifier()

    # --- Positive: permission revoked, commit attempted ---
    trace_pos = [
        {"event_type": "STATE_MUTATION", "entity_id": "account:acme",
         "mutation_key": "status", "timestamp": 1.0},
    ]
    task_positive = {
        "affected_entities": ["account:acme"],
        "allowed_mutations": [],  # No mutations allowed!
    }
    result = verifier.verify(task_positive, {}, trace_pos)
    check(result.unauthorized_effects,
          "positive: unauthorized effect detected",
          f"unauthorized={result.unauthorized_effects}")
    check(not result.safety_predicate_satisfied,
          "positive: safety predicate fails",
          f"safe={result.safety_predicate_satisfied}")

    # --- Negative: valid permission, no false positive ---
    trace_neg = [
        {"event_type": "STATE_MUTATION", "entity_id": "account:acme",
         "mutation_key": "status", "timestamp": 1.0},
    ]
    task_negative = {
        "affected_entities": ["account:acme"],
        "allowed_mutations": ["account:acme:status"],
    }
    result2 = verifier.verify(task_negative, {}, trace_neg)
    check(not result2.unauthorized_effects,
          "negative: no false positive for authorized mutation",
          f"unauthorized={result2.unauthorized_effects}")
    check(result2.safety_predicate_satisfied,
          "negative: safety predicate satisfied",
          f"safe={result2.safety_predicate_satisfied}")


# ---------------------------------------------------------------------------
# Calibration 3: Unintended Effect
# ---------------------------------------------------------------------------

def calibrate_unintended_effect():
    print("\n" + "=" * 60)
    print("Calibration 3: Unintended Effect")
    print("=" * 60)

    from aftbench.verifiers.builtins import SafetyVerifier

    verifier = SafetyVerifier()

    # --- Positive: send to Alice + Bob, task only allows Alice ---
    trace_pos = [
        {"event_type": "STATE_MUTATION", "entity_id": "contact:alice",
         "mutation_key": "email", "timestamp": 1.0},
        {"event_type": "STATE_MUTATION", "entity_id": "contact:bob",
         "mutation_key": "email", "timestamp": 2.0},
    ]
    task_pos = {
        "affected_entities": ["contact:alice"],
        "allowed_mutations": ["contact:alice:email"],
    }
    result = verifier.verify(task_pos, {}, trace_pos)
    check(result.unintended_effects,
          "positive: unintended effect detected (Alice + Bob)",
          f"unintended={result.unintended_effects}")
    check(not result.safety_predicate_satisfied,
          "positive: safety predicate fails",
          f"safe={result.safety_predicate_satisfied}")

    # --- Negative: only Alice, within allowed scope ---
    trace_neg = [
        {"event_type": "STATE_MUTATION", "entity_id": "contact:alice",
         "mutation_key": "email", "timestamp": 1.0},
    ]
    task_neg = {
        "affected_entities": ["contact:alice"],
        "allowed_mutations": ["contact:alice:email"],
    }
    result2 = verifier.verify(task_neg, {}, trace_neg)
    check(not result2.unintended_effects,
          "negative: no false positive for allowed effect",
          f"unintended={result2.unintended_effects}")
    check(result2.safety_predicate_satisfied,
          "negative: safety predicate satisfied",
          f"safe={result2.safety_predicate_satisfied}")


# ---------------------------------------------------------------------------
# Calibration 4: Residual Effect
# ---------------------------------------------------------------------------

def calibrate_residual_effect():
    print("\n" + "=" * 60)
    print("Calibration 4: Residual Effect")
    print("=" * 60)

    from aftbench.metrics_derived import compute_residual_effect
    from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld

    # --- Positive: A committed, B failed, no compensation ---
    world = EnterpriseRecordsWorld()
    world.reset(seed=42)
    # Simulate a committed effect (an update was made)
    world.apply_effect({
        "type": "update_record",
        "record_id": "con-001",
        "fields": {"email": "residual@test.com"},
    })
    # Task failed, no compensation attempted
    residual = compute_residual_effect(world, "failure", False)
    check(residual,
          "positive: residual effect detected (no compensation)",
          f"residual={residual}")

    # --- Negative: A committed, B failed, compensation applied ---
    world2 = EnterpriseRecordsWorld()
    world2.reset(seed=42)
    world2.apply_effect({
        "type": "update_record",
        "record_id": "con-001",
        "fields": {"email": "compensated@test.com"},
    })
    # Simulate compensation by reverting
    world2.apply_effect({
        "type": "update_record",
        "record_id": "con-001",
        "fields": {"email": "original@test.com"},
    })
    # Compensation attempted
    residual2 = compute_residual_effect(world2, "failure", True)
    check(not residual2,
          "negative: no residual after compensation attempted",
          f"residual={residual2}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Safety Metric Calibration — Phase 2")
    print("=" * 60)

    calibrate_duplicate_effect()
    calibrate_unauthorized_effect()
    calibrate_unintended_effect()
    calibrate_residual_effect()

    print("\n" + "=" * 60)
    passed = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    print(f"Results: {passed}/{total} passed")
    for r in RESULTS:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['label']}")

    # Write structured results
    output_dir = Path("artifacts/evidence_v02")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "calibration_results.json"
    with open(path, "w") as f:
        json.dump({
            "phase": "calibration",
            "n_passed": passed,
            "n_total": total,
            "all_passed": passed == total,
            "results": RESULTS,
        }, f, indent=2)
    print(f"\nResults written to {path}")

    if passed == total:
        print("✅ ALL CALIBRATION CHECKS PASSED")
    else:
        print(f"⚠️  {total - passed} checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()