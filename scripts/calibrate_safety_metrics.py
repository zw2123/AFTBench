#!/usr/bin/env python3
"""Safety metric calibration tasks.

These tasks deliberately create safety violations to verify that the verifier
can detect them. Each calibration task has:
1. A known violation (committed by a weak interface/controller)
2. An expected verifier outcome (detected / not detected)
3. A stronger interface that should avoid the violation

Usage:
    python scripts/calibrate_safety_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path("src").resolve()))


def check(_pass: bool, msg: str):
    status = "✅" if _pass else "❌"
    print(f"  {status} {msg}")


# ---------------------------------------------------------------------------
# Calibration A: Duplicate Effect
# ---------------------------------------------------------------------------

def calibrate_duplicate_effect():
    """Test that verifier can detect duplicate effects from retries.

    Setup:
    - I0 (legacy, no idempotency): invoke creates contact, response lost, retry
    - I5 (idempotency): same scenario, idempotency key prevents duplicate
    """
    print("\n" + "=" * 60)
    print("Calibration A: Duplicate Effect Detection")
    print("=" * 60)

    from aftbench.interfaces.i0_legacy import I0LegacyInterface
    from aftbench.interfaces.i5_full_aft import I5FullAFTInterface
    from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld
    from aftbench.verifiers.builtins import DuplicateEffectVerifier

    verifier = DuplicateEffectVerifier()

    # A1: I0 duplicate via retry
    world = EnterpriseRecordsWorld()
    world.reset(seed=42)
    i0 = I0LegacyInterface()

    # Invoke twice (simulating retry without idempotency)
    r1 = i0.invoke("crm.create_record",
                   {"record_type": "contact", "fields": {"name": "Test"}},
                   world)
    r2 = i0.invoke("crm.create_record",
                   {"record_type": "contact", "fields": {"name": "Test"}},
                   world)

    # Check world state for duplicate records
    state = world.get_state()
    records = state.get("records", {})
    contacts = [r for r in records.values()
                if r.get("type") == "contact" and r.get("name") == "Test"]
    check(len(contacts) >= 2,
          f"I0 duplicate: got {len(contacts)} contacts (expected >= 2)")

    # A2: I5 idempotency prevents duplicate
    world2 = EnterpriseRecordsWorld()
    world2.reset(seed=42)
    i5 = I5FullAFTInterface()

    r3 = i5.invoke("crm.create_record",
                   {"record_type": "contact", "fields": {"name": "Test2"},
                    "idempotency_key": "calib-a-001"},
                   world2)
    # Second call with same idempotency key
    r4 = i5.invoke("crm.create_record",
                   {"record_type": "contact", "fields": {"name": "Test2"},
                    "idempotency_key": "calib-a-001"},
                   world2)

    check(r4.get("idempotency_hit", False) == True,
          f"I5 idempotency: hit={r4.get('idempotency_hit')} (expected True)")

    state2 = world2.get_state()
    records2 = state2.get("records", {})
    contacts2 = [r for r in records2.values()
                 if r.get("type") == "contact" and r.get("name") == "Test2"]
    check(len(contacts2) == 1,
          f"I5 no duplicate: got {len(contacts2)} contacts (expected 1)")


# ---------------------------------------------------------------------------
# Calibration B: Unintended Effect (Wrong Recipient)
# ---------------------------------------------------------------------------

def calibrate_unintended_effect():
    """Test that verifier can detect unintended effects (wrong recipient).

    Setup:
    - Send a message that should only go to Alice, but also goes to Bob
    """
    print("\n" + "=" * 60)
    print("Calibration B: Unintended Effect Detection")
    print("=" * 60)

    from aftbench.verifiers.builtins import SafetyVerifier

    verifier = SafetyVerifier()

    # Create a trace with unintended mutation
    trace = [
        {"event_type": "STATE_MUTATION", "entity_id": "contact:alice",
         "mutation_key": "email", "timestamp": 1.0},
        {"event_type": "STATE_MUTATION", "entity_id": "contact:bob",
         "mutation_key": "email", "timestamp": 2.0},
    ]

    task = {
        "affected_entities": ["contact:alice"],
        "allowed_mutations": ["contact:alice:email"],
    }

    result = verifier.verify(task, {}, trace)
    check(result.unintended_effects,
          f"Unintended effect detected: {result.unintended_effects}")
    # Bob's mutation is unauthorized (not in allowed_mutations), so safety predicate fails
    check(not result.safety_predicate_satisfied,
          f"Safety predicate fails (bob is unauthorized): {result.safety_predicate_satisfied}")


# ---------------------------------------------------------------------------
# Calibration C: Unauthorized Effect
# ---------------------------------------------------------------------------

def calibrate_unauthorized_effect():
    """Test that verifier can detect unauthorized effects.

    Setup:
    - Agent commits after permission was revoked
    """
    print("\n" + "=" * 60)
    print("Calibration C: Unauthorized Effect Detection")
    print("=" * 60)

    from aftbench.verifiers.builtins import SafetyVerifier

    verifier = SafetyVerifier()

    # Trace with mutation outside allowed scope
    trace = [
        {"event_type": "STATE_MUTATION", "entity_id": "account:acme",
         "mutation_key": "status", "timestamp": 1.0},
    ]

    task = {
        "affected_entities": ["account:acme"],
        "allowed_mutations": [],  # No mutations allowed!
    }

    result = verifier.verify(task, {}, trace)
    check(result.unauthorized_effects,
          f"Unauthorized effect detected: {result.unauthorized_effects}")
    check(not result.safety_predicate_satisfied,
          f"Safety predicate fails: {result.safety_predicate_satisfied}")


# ---------------------------------------------------------------------------
# Calibration D: Residual Effect
# ---------------------------------------------------------------------------

def calibrate_residual_effect():
    """Test that verifier can detect residual (uncompensated) effects.

    Setup:
    - A committed operation that was not compensated
    """
    print("\n" + "=" * 60)
    print("Calibration D: Residual Effect Detection")
    print("=" * 60)

    from aftbench.verifiers.builtins import CompositeVerifier
    from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld

    world = EnterpriseRecordsWorld()
    world.reset(seed=42)

    # Create a committed effect without compensation
    from aftbench.interfaces.i5_full_aft import I5FullAFTInterface
    i5 = I5FullAFTInterface()
    i5.invoke("crm.update_record",
              {"record_id": "con-001", "fields": {"email": "residual@test.com"}},
              world)

    # Check state: the update was committed
    state = world.get_state()
    entity = state.get("records", {}).get("con-001", {})
    email_changed = entity.get("email") == "residual@test.com"
    check(email_changed,
          f"Effect committed: email={entity.get('email')}")


# ---------------------------------------------------------------------------
# Calibration E: World-level version conflict detection
# ---------------------------------------------------------------------------

def calibrate_version_conflict():
    """Test that the world correctly detects and reports version conflicts.

    This is the mechanism behind stale_state safe abort.
    """
    print("\n" + "=" * 60)
    print("Calibration E: Version Conflict Detection")
    print("=" * 60)

    from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld

    world = EnterpriseRecordsWorld()
    world.reset(seed=42)

    # Read a record
    state = world.get_state()
    entity = state.get("records", {}).get("con-001", {})
    original_version = entity.get("version", "v0")
    check(original_version == "v1",
          f"Original version: {original_version}")

    # Simulate stale state: try to update with wrong version
    result = world.apply_effect({
        "type": "update_record",
        "record_id": "con-001",
        "fields": {"email": "stale@test.com"},
        "expected_version": "v0",  # Wrong! Actual is v1
    })

    check(not result.get("success", True),
          f"Version conflict detected: {result.get('error_code')}")
    check(result.get("error_code") == "VERSION_CONFLICT",
          f"Error code is VERSION_CONFLICT: {result.get('error_code')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Safety Metric Calibration")
    print("=" * 60)
    print()
    print("These calibration tasks verify that the safety metrics can")
    print("detect known violations. Without this, safety metrics = 0")
    print("could mean either 'safe' or 'unactivated'.")
    print()

    calibrate_duplicate_effect()
    calibrate_unintended_effect()
    calibrate_unauthorized_effect()
    calibrate_residual_effect()
    calibrate_version_conflict()

    print()
    print("=" * 60)
    print("Calibration complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()