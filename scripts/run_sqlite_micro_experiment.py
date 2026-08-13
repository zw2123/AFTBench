#!/usr/bin/env python3
"""SQLite micro experiment — error classification and replication.

Phase 8: Run a small SQLite experiment to classify errors.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path("src").resolve()))

OUTPUT_DIR = Path("artifacts/evidence_v02/sqlite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULTS = []


def check(passed: bool, label: str, detail: str = ""):
    status = "✅" if passed else "❌"
    print(f"  {status} {label}: {detail}")
    RESULTS.append({"label": label, "passed": passed, "detail": detail})


def run_sqlite():
    print("=" * 60)
    print("SQLite Micro Experiment")
    print("=" * 60)

    from aftbench.config import BenchmarkConfig
    from aftbench.runner import BenchmarkRunner

    import tempfile
    tmp = tempfile.mkdtemp()

    # Small run: 2 tasks, 4 interfaces, 2 faults, 1 seed
    config = BenchmarkConfig(
        profile="test",
        output_dir=tmp,
        worlds=["sqlite_crm"],
        interfaces=["I0", "I1", "I4", "I5"],
        faults=["none", "lost_response_after_effect", "stale_state"],
        max_tasks_per_world=2,
        seeds=[42],
    )
    runner = BenchmarkRunner(config)
    results = runner.run_profile()

    # Classify errors
    print(f"\nTotal runs: {len(results)}")
    errors = []
    for r in results:
        # Classify each run
        if r.terminal_oracle_outcome == "completed_as_requested":
            classification = "operational_success"
        elif r.terminal_oracle_outcome in ("safely_aborted", "safely_refused"):
            classification = "expected_operational_failure"
        elif r.terminal_oracle_outcome == "failure":
            classification = "true_agent_failure"
        elif r.terminal_oracle_outcome == "unsafe_committed":
            classification = "unsafe_commit"
        else:
            classification = "other"

        # Check for implementation-specific errors
        is_impl_error = False
        if r.terminal_agent_claim == "failure" and r.fault_type in ("none", ""):
            is_impl_error = True
            classification = "unexpected_implementation_error"

        errors.append({
            "run_id": r.run_id,
            "interface": r.interface_condition,
            "fault": r.fault_type,
            "outcome": r.terminal_oracle_outcome,
            "correct": r.state_correct_completion,
            "classification": classification,
            "impl_error": is_impl_error,
        })

    # Summary
    print("\n" + "=" * 60)
    print("ERROR CLASSIFICATION")
    print("=" * 60)
    class_counts = Counter(e["classification"] for e in errors)
    for cls, count in sorted(class_counts.items()):
        print(f"  {cls:40s}: {count}")

    impl_errors = sum(1 for e in errors if e["impl_error"])
    total = len(errors)
    impl_error_rate = impl_errors / total * 100 if total > 0 else 0
    print(f"\n  Implementation error rate: {impl_error_rate:.1f}% ({impl_errors}/{total})")
    check(impl_error_rate < 5,
          f"implementation error rate < 5%",
          f"got {impl_error_rate:.1f}%")

    # Write CSV
    csv_path = OUTPUT_DIR / "sqlite_error_breakdown.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "run_id", "interface", "fault", "outcome",
            "correct", "classification", "impl_error",
        ])
        writer.writeheader()
        writer.writerows(errors)
    print(f"\nError breakdown written to {csv_path}")

    # Write results
    path = OUTPUT_DIR / "sqlite_results.json"
    with open(path, "w") as f:
        json.dump({
            "experiment": "sqlite_micro",
            "n_runs": total,
            "impl_error_rate": impl_error_rate,
            "classifications": dict(class_counts),
            "n_passed": sum(1 for r in RESULTS if r["passed"]),
            "n_total": len(RESULTS),
            "checks": RESULTS,
        }, f, indent=2)
    print(f"Results written to {path}")


if __name__ == "__main__":
    run_sqlite()