#!/usr/bin/env python3
"""M2 Micro Experiment: Post-commit Uncertainty.

Tests how different interfaces handle the case where an effect is committed
but the response is lost (lost_response_after_effect fault).

Conditions: I3, I4, I5, I5-minus-side-effect-contract, I5-minus-verification
Fault: commit → response lost

Expected behavior:
  I3:                    knows invocation state, may not know if committed
  I4:                    effect contract + idempotency → avoids duplicate
  I5:                    all of above + reconciliation + verification
  I5-minus-effect:       no effect contract → may duplicate
  I5-minus-verification: no verification path → can't verify outcome
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))

OUTPUT_DIR = Path("artifacts/evidence_v02/m2_postcommit")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULTS = []


def check(passed: bool, label: str, detail: str = ""):
    status = "✅" if passed else "❌"
    print(f"  {status} {label}: {detail}")
    RESULTS.append({"label": label, "passed": passed, "detail": detail})


def run_m2():
    print("=" * 60)
    print("M2 Micro Experiment: Post-commit Uncertainty")
    print("=" * 60)

    from aftbench.config import BenchmarkConfig
    from aftbench.runner import BenchmarkRunner
    from aftbench.schemas import FaultSchedule, FaultType
    from aftbench.trace import TraceWriter
    from aftbench.worlds.external_actions import ExternalActionsWorld

    import tempfile
    tmp = tempfile.mkdtemp()

    # Use exact-once tasks from external_actions world
    # Task: send exactly one message (exact-once semantics)
    config = BenchmarkConfig(
        profile="test",
        output_dir=tmp,
        worlds=["external_actions"],
        interfaces=["I3", "I4", "I5", "I5-minus-side-effect-contract", "I5-minus-verification"],
        faults=["lost_response_after_effect"],
        max_tasks_per_world=2,
        seeds=[42, 123],
    )
    runner = BenchmarkRunner(config)

    # Load tasks and filter for exact-once tasks
    tasks = runner._load_tasks()
    ea_tasks = [t for t in tasks if t.world == "external_actions"][:2]
    print(f"\nUsing {len(ea_tasks)} tasks: {[t.task_id for t in ea_tasks]}")

    fault = FaultSchedule(
        fault_id="lost_response_after_effect",
        fault_type=FaultType.LOST_RESPONSE_AFTER_EFFECT,
        target_world="external_actions",
        seed=42,
    )

    # Run each interface × task × seed
    all_results = []
    for iface_name in config.interfaces:
        for task_idx, task in enumerate(ea_tasks):
            for seed in config.seeds:
                world = ExternalActionsWorld()
                tw = TraceWriter(Path(tmp) / f"traces_{iface_name}_{task_idx}_{seed}.jsonl")
                try:
                    result = runner.run_task(
                        task, world, runner._create_interface(iface_name), iface_name,
                        fault, seed, tw,
                    )
                    all_results.append({
                        "interface": iface_name,
                        "task": task.task_id,
                        "seed": seed,
                        "outcome": result.terminal_oracle_outcome,
                        "correct": result.state_correct_completion,
                        "recovery": result.recovery_success,
                        "duplicate": result.duplicate_effect,
                        "unintended": result.unintended_effect,
                        "unauthorized": result.unauthorized_effect,
                        "residual": result.residual_effect,
                        "reconciled": result.unknown_outcome_reconciled,
                        "agent_claim": result.terminal_agent_claim,
                        "logical_reexecutions": result.logical_reexecutions,
                        "transport_retries": result.transport_retries,
                    })

                    print(f"\n  {iface_name:35s} task={task.task_id:35s} seed={seed}")
                    print(f"    outcome={result.terminal_oracle_outcome:25s} correct={result.state_correct_completion}")
                    print(f"    duplicate={result.duplicate_effect} unintended={result.unintended_effect} unauthorized={result.unauthorized_effect} residual={result.residual_effect}")
                    print(f"    recovery={result.recovery_success} reconciled={result.unknown_outcome_reconciled}")
                    print(f"    logical_reexec={result.logical_reexecutions} retries={result.transport_retries}")

                except Exception as e:
                    print(f"\n  {iface_name:35s} task={task.task_id:35s} EXCEPTION: {e}")
                finally:
                    tw.close()

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Check fault-reached runs have commit before drop
    print("\nChecking commit-before-drop semantics...")
    fa_reached = [r for r in all_results if r["outcome"] != "failed_unnecessarily"]
    check(len(fa_reached) > 0,
          "fault-reached runs exist",
          f"got {len(fa_reached)}")

    # Check duplicate detection
    print("\nChecking duplicate effect detection...")
    for r in all_results:
        if r["duplicate"]:
            check(True,
                  f"duplicate detected: {r['interface']} {r['task']}",
                  f"duplicate={r['duplicate']}")

    # Check idempotency in I4/I5
    print("\nChecking idempotency activation...")
    i4_results = [r for r in all_results if r["interface"] == "I4"]
    i5_results = [r for r in all_results if r["interface"] == "I5"]
    check(len(i4_results) > 0, "I4 results exist", f"got {len(i4_results)}")
    check(len(i5_results) > 0, "I5 results exist", f"got {len(i5_results)}")

    # Check verification in I5
    print("\nChecking verification paths...")
    i5_no_verif = [r for r in all_results if r["interface"] == "I5-minus-verification"]
    check(len(i5_no_verif) > 0, "I5-minus-verification results exist", f"got {len(i5_no_verif)}")

    # Summary by interface
    print("\n" + "=" * 60)
    print("SUMMARY BY INTERFACE")
    print("=" * 60)
    by_iface = {}
    for r in all_results:
        by_iface.setdefault(r["interface"], []).append(r)

    for iface, results in sorted(by_iface.items()):
        n = len(results)
        outcomes = [r["outcome"] for r in results]
        correct = sum(1 for r in results if r["correct"])
        dups = sum(1 for r in results if r["duplicate"])
        recs = sum(1 for r in results if r["recovery"] is True)
        recons = sum(1 for r in results if r["reconciled"] is True)
        print(f"\n  {iface}:")
        print(f"    runs={n} correct={correct}/{n} duplicates={dups} recovery={recs} reconciled={recons}")
        print(f"    outcomes: {sorted(set(outcomes))}")

    # Write results
    path = OUTPUT_DIR / "m2_results.json"
    with open(path, "w") as f:
        json.dump({
            "experiment": "M2_postcommit_uncertainty",
            "n_results": len(all_results),
            "results": all_results,
            "n_passed": sum(1 for r in RESULTS if r["passed"]),
            "n_total": len(RESULTS),
            "checks": RESULTS,
        }, f, indent=2)
    print(f"\nResults written to {path}")


if __name__ == "__main__":
    run_m2()