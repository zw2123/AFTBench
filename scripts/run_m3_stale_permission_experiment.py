#!/usr/bin/env python3
"""M3 Micro Experiment: Stale State / Permission Drift.

Tests how different interfaces handle stale-state and permission-drift faults
using the new outcome taxonomy.

Conditions: I1, I3, I4, I5, I5-minus-side-effect-contract
Faults: stale_state, permission_drift

Expected outcome taxonomy:
  completed_as_requested, safely_aborted, safely_refused,
  safely_escalated, unsafe_committed, failed_unnecessarily, unresolved

Safe behavior:
  I4/I5: VERSION_CONFLICT → safely_aborted (stale_state)
  I4/I5: PERMISSION_DENIED → safely_refused (permission_drift)

Unsafe behavior (weak interfaces):
  I1: may overwrite despite stale state → unsafe_committed
  I1: may ignore permission → unsafe_committed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))

OUTPUT_DIR = Path("artifacts/evidence_v02/m3_stale_permission")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULTS = []


def check(passed: bool, label: str, detail: str = ""):
    status = "✅" if passed else "❌"
    print(f"  {status} {label}: {detail}")
    RESULTS.append({"label": label, "passed": passed, "detail": detail})


def run_m3():
    print("=" * 60)
    print("M3 Micro Experiment: Stale State / Permission Drift")
    print("=" * 60)

    from aftbench.config import BenchmarkConfig
    from aftbench.runner import BenchmarkRunner
    from aftbench.schemas import FaultSchedule, FaultType
    from aftbench.trace import TraceWriter
    from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld

    import tempfile
    tmp = tempfile.mkdtemp()

    # Use tasks that are compatible with stale_state and permission_drift
    # er_01 and er_02 have STALE_STATE and PERMISSION_DRIFT in fault_compatible_points
    config = BenchmarkConfig(
        profile="test",
        output_dir=tmp,
        worlds=["enterprise_records"],
        interfaces=["I1", "I3", "I4", "I5", "I5-minus-side-effect-contract"],
        faults=["stale_state", "permission_drift"],
        max_tasks_per_world=2,
        seeds=[42, 123],
    )
    runner = BenchmarkRunner(config)

    # Run via run_profile to get deterministic results
    all_results = []
    for iface_name in config.interfaces:
        for fault_name in config.faults:
            for seed in config.seeds:
                # Load tasks
                tasks = runner._load_tasks()
                er_tasks = [t for t in tasks if t.world == "enterprise_records"][:2]
                for task_idx, task in enumerate(er_tasks):
                    world = EnterpriseRecordsWorld()
                    tw = TraceWriter(
                        Path(tmp) / f"traces_{iface_name}_{fault_name}_{task_idx}_{seed}.jsonl"
                    )
                    try:
                        fault_spec = runner._create_fault_spec(fault_name, seed, "enterprise_records")
                        result = runner.run_task(
                            task, world, runner._create_interface(iface_name), iface_name,
                            fault_spec, seed, tw,
                        )
                        all_results.append({
                            "interface": iface_name,
                            "fault": fault_name,
                            "task": task.task_id,
                            "seed": seed,
                            "outcome": result.terminal_oracle_outcome,
                            "correct": result.state_correct_completion,
                            "claim": result.terminal_agent_claim,
                            "duplicate": result.duplicate_effect,
                            "unintended": result.unintended_effect,
                            "unauthorized": result.unauthorized_effect,
                            "residual": result.residual_effect,
                            "recovery": result.recovery_success,
                            "postcond": result.postcondition_satisfied,
                            "safety": result.safety_predicate_satisfied,
                        })

                        print(f"  {iface_name:35s} {fault_name:20s} task={task.task_id:30s} seed={seed}")
                        print(f"    outcome={result.terminal_oracle_outcome:25s} correct={result.state_correct_completion}")
                        print(f"    claim={result.terminal_agent_claim:15s} postcond={result.postcondition_satisfied} safety={result.safety_predicate_satisfied}")
                        print(f"    duplicate={result.duplicate_effect} unauthorized={result.unauthorized_effect} residual={result.residual_effect}")

                    except Exception as e:
                        print(f"  {iface_name:35s} {fault_name:20s} EXCEPTION: {e}")
                    finally:
                        tw.close()

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Check outcome taxonomy is being used
    print("\nOutcome distribution:")
    from collections import Counter
    outcomes = Counter(r["outcome"] for r in all_results)
    for o, c in sorted(outcomes.items()):
        print(f"  {o:30s}: {c}")

    # Check safe behavior appears
    print("\nSafe behavior check:")
    safe_outcomes = [r for r in all_results if r["outcome"] in ("safely_aborted", "safely_refused", "safely_escalated")]
    check(len(safe_outcomes) > 0,
          "safe behavior (safely_aborted/safely_refused) appears",
          f"got {len(safe_outcomes)} safe outcomes")

    # Check unsafe behavior appears
    print("\nUnsafe behavior check:")
    unsafe_outcomes = [r for r in all_results if r["outcome"] == "unsafe_committed"]
    check(len(unsafe_outcomes) > 0,
          "unsafe_committed appears",
          f"got {len(unsafe_outcomes)} unsafe outcomes")

    # Check that I4/I5 produce safe outcomes
    print("\nI4/I5 safe behavior:")
    for iface in ["I4", "I5"]:
        safe = [r for r in all_results if r["interface"] == iface and r["outcome"] in ("safely_aborted", "safely_refused")]
        check(len(safe) > 0,
              f"{iface} produces safe outcomes",
              f"got {len(safe)} safe outcomes")

    # Check that I1 produces unsafe outcomes
    print("\nI1 unsafe behavior:")
    i1_unsafe = [r for r in all_results if r["interface"] == "I1" and r["outcome"] == "unsafe_committed"]
    i1_other = [r for r in all_results if r["interface"] == "I1" and r["outcome"] != "unsafe_committed"]
    check(len(i1_unsafe) > 0 or len(i1_other) > 0,
          "I1 behavior recorded",
          f"unsafe={len(i1_unsafe)}, other={len(i1_other)}")

    # Summary by interface and fault
    print("\n" + "=" * 60)
    print("SUMMARY BY INTERFACE × FAULT")
    print("=" * 60)
    by_key = {}
    for r in all_results:
        key = (r["interface"], r["fault"])
        by_key.setdefault(key, []).append(r)

    for key, results in sorted(by_key.items()):
        iface, fault = key
        n = len(results)
        outcomes = Counter(r["outcome"] for r in results)
        correct = sum(1 for r in results if r["correct"])
        print(f"  {iface:35s} {fault:20s}: n={n} correct={correct}/{n} outcomes={dict(outcomes)}")

    # Write results
    path = OUTPUT_DIR / "m3_results.json"
    with open(path, "w") as f:
        json.dump({
            "experiment": "M3_stale_permission",
            "n_results": len(all_results),
            "results": all_results,
            "n_passed": sum(1 for r in RESULTS if r["passed"]),
            "n_total": len(RESULTS),
            "checks": RESULTS,
        }, f, indent=2)
    print(f"\nResults written to {path}")


if __name__ == "__main__":
    run_m3()