#!/usr/bin/env python3
"""Build experiment ledger from actual artifacts.

This script automatically computes:
- expected vs observed runs (from config)
- fault funnel (configured → reached → committed → dropped)
- recovery eligibility and success
- error classification
- cross-validation between results, traces, and config

All numbers in reports must come from this ledger.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_manifest(experiment_dir: Path) -> Optional[Dict]:
    """Load manifest.json from experiment directory."""
    path = experiment_dir / "manifest.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_config(experiment_dir: Path) -> Optional[Dict]:
    """Load config from manifest.json."""
    manifest = load_manifest(experiment_dir)
    if manifest and "config" in manifest:
        return manifest["config"]
    return None


def load_results(experiment_dir: Path) -> List[Dict]:
    """Load results.csv from experiment directory."""
    results_path = experiment_dir / "results.csv"
    if not results_path.exists():
        return []
    with open(results_path) as f:
        return list(csv.DictReader(f))


def load_traces(experiment_dir: Path) -> List[Dict]:
    """Load traces.jsonl from experiment directory."""
    traces_path = experiment_dir / "traces.jsonl"
    if not traces_path.exists():
        return []
    with open(traces_path) as f:
        return [json.loads(line) for line in f]


# ---------------------------------------------------------------------------
# Expected run count computation
# ---------------------------------------------------------------------------

def compute_expected_runs(config: Dict) -> int:
    """Compute expected number of runs from config.

    Mirrors the runner loop:
        for world in worlds:
            for task in world_tasks[:max_tasks_per_world]:
                for interface in interfaces:
                    for fault in faults:
                        for seed in seeds:
                            run(...)

    So expected = n_worlds * tasks_per_world * n_interfaces * n_faults * n_seeds,
    where tasks_per_world = max_tasks_per_world (assumes every world has at least
    that many tasks available).
    """
    worlds = config.get("worlds", [])
    interfaces = config.get("interfaces", [])
    faults = config.get("faults", ["none"])
    seeds = config.get("seeds", [42])
    max_tasks = config.get("max_tasks_per_world", 8)

    # Per-world task count: max_tasks_per_world tasks per world
    tasks_per_world = max_tasks

    return len(worlds) * tasks_per_world * len(interfaces) * len(faults) * len(seeds)


# ---------------------------------------------------------------------------
# Funnel builders
# ---------------------------------------------------------------------------

def build_fault_funnel(results: List[Dict], traces: List[Dict]) -> Dict[str, int]:
    """Build fault funnel from traces and results.

    Funnel stages:
    - fault_configured: runs with a non-none fault configured
    - request_accepted: REQUEST_ACCEPTED events in traces
    - backend_started: BACKEND_STARTED events
    - effect_committed: EFFECT_COMMITTED events
    - response_generated: RESPONSE_GENERATED events
    - response_dropped: RESPONSE_DROPPED events
    """
    funnel: Dict[str, int] = {
        "fault_configured": 0,
        "request_accepted": 0,
        "backend_started": 0,
        "effect_committed": 0,
        "response_generated": 0,
        "response_dropped": 0,
    }

    # Count fault_configured from results (fault_type != empty/none)
    for r in results:
        ft = (r.get("fault_type") or "").strip()
        if ft and ft != "none":
            funnel["fault_configured"] += 1

    # Count trace events
    funnel_event_map = {
        "REQUEST_ACCEPTED": "request_accepted",
        "BACKEND_STARTED": "backend_started",
        "EFFECT_COMMITTED": "effect_committed",
        "RESPONSE_GENERATED": "response_generated",
        "RESPONSE_DROPPED": "response_dropped",
    }
    for e in traces:
        et = e.get("event_type", "")
        if et in funnel_event_map:
            funnel[funnel_event_map[et]] += 1

    return funnel


def build_recovery_funnel(results: List[Dict], traces: List[Dict]) -> Dict[str, int]:
    """Build recovery funnel.

    Recovery stages:
    - recovery_eligible: runs with faults that can trigger recovery
    - recovery_attempted: runs where recovery was attempted (from traces)
    - recovery_succeeded: runs with recovery_success=true
    """
    funnel: Dict[str, int] = {
        "recovery_eligible": 0,
        "recovery_attempted": 0,
        "recovery_succeeded": 0,
    }

    # Count recovery_eligible from results
    recovery_faults = {"lost_response_after_effect", "interrupted_execution"}
    for r in results:
        ft = (r.get("fault_type") or "").strip()
        if ft in recovery_faults:
            funnel["recovery_eligible"] += 1

    # Count recovery_succeeded from results
    for r in results:
        if r.get("recovery_success") == "true":
            funnel["recovery_succeeded"] += 1

    # Count recovery_attempted from traces
    # Look for events that indicate recovery was triggered
    trace_event_types = Counter(e.get("event_type", "") for e in traces)
    recovery_events = {"reconciled", "resumed", "RECONCILED", "RESUMED",
                       "reconciliation", "RECONCILIATION",
                       "INVOCATION_RESUMED", "RECONCILIATION_STARTED"}
    attempted = 0
    for e in traces:
        if e.get("event_type", "") in recovery_events:
            attempted += 1
    funnel["recovery_attempted"] = attempted

    return funnel


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------

def cross_validate(experiment_name: str, results: List[Dict], traces: List[Dict],
                   config: Optional[Dict]) -> Dict[str, Any]:
    """Cross-validate results, traces, and config for consistency.

    Returns a dict of consistency checks with pass/fail status.
    """
    checks: Dict[str, Any] = {}

    # 1. Check 1: results count vs traces run_ids
    result_run_ids = set(r.get("run_id", "") for r in results)
    trace_run_ids = set(e.get("run_id", e.get("trace_id", "")) for e in traces)

    # Check which field traces use for run identification
    trace_id_field = "run_id" if any("run_id" in e for e in traces[:100]) else "trace_id"
    trace_run_ids = set(e.get(trace_id_field, "") for e in traces)

    missing_from_traces = result_run_ids - trace_run_ids
    extra_in_traces = trace_run_ids - result_run_ids

    checks["result_count"] = len(results)
    checks["trace_count"] = len(traces)
    checks["result_run_ids"] = len(result_run_ids)
    checks["trace_run_ids"] = len(trace_run_ids)
    checks["missing_from_traces"] = len(missing_from_traces)
    checks["extra_in_traces"] = len(extra_in_traces)
    checks["traces_match_results"] = len(missing_from_traces) == 0 and len(extra_in_traces) == 0

    # 2. Check 2: expected vs observed (if config available)
    if config:
        expected = compute_expected_runs(config)
        observed = len(results)
        checks["expected_runs"] = expected
        checks["observed_runs"] = observed
        checks["run_count_matches"] = expected == observed
        if expected != observed:
            checks["run_count_discrepancy"] = observed - expected
    else:
        checks["expected_runs"] = None
        checks["observed_runs"] = len(results)
        checks["run_count_matches"] = None

    # 3. Check 3: fault_type values in results
    ft_values = set((r.get("fault_type") or "").strip() for r in results)
    checks["fault_type_values"] = sorted(ft_values)

    # 4. Check 4: terminal_oracle_outcome values
    oracle_values = Counter(r.get("terminal_oracle_outcome", "") for r in results)
    checks["oracle_outcome_distribution"] = dict(oracle_values)

    # 5. Check 5: check for missing data in key fields
    missing_fields = []
    for r in results[:10]:  # sample
        for field in ["run_id", "task_id", "interface_condition", "world"]:
            if not r.get(field, "").strip():
                missing_fields.append(field)
    checks["missing_required_fields"] = list(set(missing_fields)) if missing_fields else []

    return checks


# ---------------------------------------------------------------------------
# Main ledger builder
# ---------------------------------------------------------------------------

def build_experiment_ledger(experiment_name: str, experiment_dir: Path) -> Dict[str, Any]:
    """Build complete ledger for one experiment."""
    results = load_results(experiment_dir)
    traces = load_traces(experiment_dir)
    config = load_config(experiment_dir)

    if not results:
        return {"experiment": experiment_name, "error": "No results found"}

    # Basic counts
    total_runs = len(results)
    successful_runs = sum(1 for r in results if r.get("terminal_oracle_outcome") == "success")
    failed_runs = sum(1 for r in results if r.get("terminal_oracle_outcome") == "failure")

    # Breakdown by dimensions (fix: normalize fault_type)
    by_interface = Counter(r["interface_condition"] for r in results)
    by_world = Counter(r["world"] for r in results)

    # Normalize fault_type: empty string → "none"
    by_fault: Dict[str, int] = {}
    for r in results:
        ft = (r.get("fault_type") or "").strip()
        if not ft:
            ft = "none"
        by_fault[ft] = by_fault.get(ft, 0) + 1

    by_seed = Counter(r.get("seed", "?") for r in results)

    # Funnels
    fault_funnel = build_fault_funnel(results, traces)
    recovery_funnel = build_recovery_funnel(results, traces)

    # Error classification
    error_classification = {"total_failures": failed_runs}
    if failed_runs > 0:
        # Group by interface for failures
        failures_by_interface = Counter(
            r["interface_condition"] for r in results
            if r.get("terminal_oracle_outcome") == "failure"
        )
        error_classification["by_interface"] = dict(failures_by_interface)

    # Cross-validation
    validation = cross_validate(experiment_name, results, traces, config)

    return {
        "experiment": experiment_name,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "by_interface": dict(by_interface),
        "by_world": dict(by_world),
        "by_fault": by_fault,
        "by_seed": dict(by_seed),
        "fault_funnel": fault_funnel,
        "recovery_funnel": recovery_funnel,
        "error_classification": error_classification,
        "validation": validation,
    }


# ---------------------------------------------------------------------------
# Consistency report generator
# ---------------------------------------------------------------------------

def generate_consistency_report(ledger: List[Dict]) -> str:
    """Generate a human-readable consistency report in markdown."""
    lines = []
    lines.append("# Experiment Ledger — Consistency Report")
    lines.append("")
    lines.append(f"**Generated:** auto")
    lines.append(f"**Experiments:** {len(ledger)}")
    lines.append("")

    total_expected = 0
    total_observed = 0
    all_checks_passed = True

    for exp in ledger:
        name = exp["experiment"]
        lines.append(f"---")
        lines.append(f"## {name}")
        lines.append("")

        if "error" in exp:
            lines.append(f"⚠️ **ERROR**: {exp['error']}")
            lines.append("")
            all_checks_passed = False
            continue

        val = exp.get("validation", {})
        expected = val.get("expected_runs")
        observed = val.get("observed_runs", exp["total_runs"])

        lines.append(f"### Run counts")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        if expected is not None:
            lines.append(f"| Expected runs | {expected} |")
            total_expected += expected
        lines.append(f"| Observed runs | {observed} |")
        total_observed += observed
        lines.append(f"| Successful | {exp['successful_runs']} |")
        lines.append(f"| Failed | {exp['failed_runs']} |")
        lines.append("")

        # Check consistency
        if expected is not None and expected != observed:
            all_checks_passed = False
            lines.append(f"⚠️ **MISMATCH**: expected {expected} runs, observed {observed} "
                         f"(Δ = {observed - expected})")
            lines.append("")

        # Trace consistency
        lines.append(f"### Trace consistency")
        lines.append("")
        traces_match = val.get("traces_match_results", False)
        lines.append(f"| Check | Result |")
        lines.append(f"|-------|--------|")
        lines.append(f"| Traces match results | {'✅' if traces_match else '❌'} |")
        lines.append(f"| Result run IDs | {val.get('result_run_ids', '?')} |")
        lines.append(f"| Trace run IDs | {val.get('trace_run_ids', '?')} |")
        lines.append(f"| Missing from traces | {val.get('missing_from_traces', '?')} |")
        lines.append(f"| Extra in traces | {val.get('extra_in_traces', '?')} |")
        if not traces_match:
            all_checks_passed = False
        lines.append("")

        # Fault funnel
        funnel = exp["fault_funnel"]
        if funnel["fault_configured"] > 0:
            lines.append(f"### Fault funnel")
            lines.append("")
            lines.append(f"| Stage | Count | % of configured |")
            lines.append(f"|-------|-------|-----------------|")
            fc = funnel["fault_configured"]
            lines.append(f"| Fault configured | {fc} | 100% |")
            lines.append(f"| Request accepted | {funnel['request_accepted']} | "
                         f"{funnel['request_accepted']/fc*100:.1f}% |")
            lines.append(f"| Backend started | {funnel['backend_started']} | "
                         f"{funnel['backend_started']/fc*100:.1f}% |")
            lines.append(f"| Effect committed | {funnel['effect_committed']} | "
                         f"{funnel['effect_committed']/fc*100:.1f}% |")
            lines.append(f"| Response generated | {funnel['response_generated']} | "
                         f"{funnel['response_generated']/fc*100:.1f}% |")
            lines.append(f"| Response dropped | {funnel['response_dropped']} | "
                         f"{funnel['response_dropped']/fc*100:.1f}% |")
            lines.append("")

            # Check for funnel consistency
            if funnel["response_dropped"] > 0:
                pct = funnel["response_dropped"] / fc * 100
                lines.append(f"> ℹ️ {funnel['response_dropped']}/{fc} runs ({pct:.1f}%) reached response_dropped stage.")
                lines.append("")

        # Recovery funnel
        recovery = exp["recovery_funnel"]
        if recovery["recovery_eligible"] > 0:
            lines.append(f"### Recovery funnel")
            lines.append("")
            lines.append(f"| Stage | Count | % of eligible |")
            lines.append(f"|-------|-------|---------------|")
            re = recovery["recovery_eligible"]
            lines.append(f"| Recovery eligible | {re} | 100% |")
            ra = recovery["recovery_attempted"]
            lines.append(f"| Recovery attempted | {ra} | "
                         f"{ra/re*100:.1f}% |")
            rs = recovery["recovery_succeeded"]
            lines.append(f"| Recovery succeeded | {rs} | "
                         f"{rs/re*100:.1f}% |")

            if ra == 0 and rs > 0:
                lines.append("")
                lines.append(f"> ⚠️ **NOTE**: recovery_attempted=0 but recovery_succeeded={rs}. "
                             f"Traces may not contain explicit recovery event types.")
            lines.append("")

        # Error classification
        err = exp["error_classification"]
        if err.get("total_failures", 0) > 0:
            lines.append(f"### Error classification")
            lines.append("")
            lines.append(f"| Type | Count |")
            lines.append(f"|------|-------|")
            lines.append(f"| Total failures | {err['total_failures']} |")
            for iface, count in err.get("by_interface", {}).items():
                lines.append(f"| Failure by interface: {iface} | {count} |")
            lines.append("")

        # Oracle outcome distribution
        oracle = val.get("oracle_outcome_distribution", {})
        if oracle:
            lines.append(f"### Oracle outcome distribution")
            lines.append("")
            for outcome, count in sorted(oracle.items()):
                lines.append(f"- {outcome}: {count}")
            lines.append("")

        # Fault type values
        ft_vals = val.get("fault_type_values", [])
        lines.append(f"### Fault types used")
        lines.append("")
        lines.append(f"`{', '.join(ft_vals)}`")
        lines.append("")

    # Overall summary
    lines.append("---")
    lines.append("## Overall Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total expected runs | {total_expected} |")
    lines.append(f"| Total observed runs | {total_observed} |")
    lines.append(f"| All checks passed | {'✅ YES' if all_checks_passed else '❌ NO'} |")
    if total_expected != total_observed:
        lines.append(f"| Total discrepancy | {total_observed - total_expected} |")
    lines.append("")

    if not all_checks_passed:
        lines.append("### Issues found")
        lines.append("")
        for exp in ledger:
            if "error" in exp:
                lines.append(f"- ❌ **{exp['experiment']}**: {exp['error']}")
                continue
            val = exp.get("validation", {})
            expected = val.get("expected_runs")
            observed = val.get("observed_runs", exp["total_runs"])
            if expected is not None and expected != observed:
                lines.append(f"- ⚠️ **{exp['experiment']}**: expected {expected} runs, "
                             f"observed {observed} (Δ = {observed - expected})")
            if not val.get("traces_match_results", False):
                lines.append(f"- ⚠️ **{exp['experiment']}**: traces do not match results "
                             f"(missing={val.get('missing_from_traces')}, extra={val.get('extra_in_traces')})")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Build ledger for all experiments."""
    import argparse
    parser = argparse.ArgumentParser(description="Build AFTBench experiment ledger")
    parser.add_argument("--evidence-dir", default="artifacts/legacy/evidence_runs",
                        help="Root directory of experiment outputs")
    parser.add_argument("--experiments", default=None,
                        help="Comma-separated experiment subdirectory names "
                             "(default: the six canonical profiles)")
    parser.add_argument("--output-dir", default="artifacts/audit",
                        help="Where to write ledger/funnel/report files")
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not evidence_dir.exists():
        print(f"Error: {evidence_dir} not found")
        return

    if args.experiments:
        experiments = [e.strip() for e in args.experiments.split(",") if e.strip()]
    else:
        experiments = [
            "primitive_ablations",
            "discovery_frontier",
            "postcommit_loss",
            "interruption_recovery",
            "stale_permission",
            "production_like",
        ]

    ledger = []
    for exp_name in experiments:
        exp_dir = evidence_dir / exp_name
        if exp_dir.exists():
            print(f"Building ledger for {exp_name}...")
            exp_ledger = build_experiment_ledger(exp_name, exp_dir)
            ledger.append(exp_ledger)
        else:
            print(f"Warning: {exp_dir} not found, skipping")

    # Write ledger JSON
    ledger_path = output_dir / "experiment_ledger.json"
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    print(f"\nLedger JSON written to {ledger_path}")

    # Also write to the old location for backward compatibility
    old_ledger_path = Path("artifacts/experiment_ledger.json")
    with open(old_ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    print(f"Ledger JSON also written to {old_ledger_path}")

    # Write fault funnel CSV
    funnel_path = output_dir / "fault_funnel.csv"
    with open(funnel_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "experiment", "fault_configured", "request_accepted", "backend_started",
            "effect_committed", "response_generated", "response_dropped",
            "recovery_eligible", "recovery_attempted", "recovery_succeeded"
        ])
        for exp in ledger:
            if "error" in exp:
                continue
            ff = exp["fault_funnel"]
            rf = exp["recovery_funnel"]
            writer.writerow([
                exp["experiment"],
                ff["fault_configured"],
                ff["request_accepted"],
                ff["backend_started"],
                ff["effect_committed"],
                ff["response_generated"],
                ff["response_dropped"],
                rf["recovery_eligible"],
                rf["recovery_attempted"],
                rf["recovery_succeeded"],
            ])
    print(f"Fault funnel written to {funnel_path}")

    # Generate consistency report
    report = generate_consistency_report(ledger)
    report_path = output_dir / "consistency_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Consistency report written to {report_path}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("EXPERIMENT LEDGER SUMMARY")
    print("=" * 60)
    print()

    all_ok = True
    for exp in ledger:
        name = exp["experiment"]
        if "error" in exp:
            print(f"  ❌ {name}: ERROR - {exp['error']}")
            all_ok = False
            continue

        val = exp.get("validation", {})
        expected = val.get("expected_runs", "?")
        observed = val.get("observed_runs", exp["total_runs"])
        ok = True

        if expected != "?" and expected != observed:
            print(f"  ⚠️  {name}: expected={expected}, observed={observed} (Δ={observed - expected})", end="")
            ok = False
        else:
            print(f"  ✅ {name}: {observed} runs", end="")

        if not val.get("traces_match_results", False):
            print(f" [traces mismatch]", end="")
            ok = False

        if exp["failed_runs"] > 0:
            print(f" [failures={exp['failed_runs']}]", end="")

        print()
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("  ✅ All experiments consistent.")
    else:
        print("  ⚠️  Some experiments have inconsistencies — see detailed report.")

    # Print run count diagnoses
    print()
    print("Run count diagnoses:")
    print()
    for exp in ledger:
        if "error" in exp:
            continue
        val = exp.get("validation", {})
        expected = val.get("expected_runs")
        n_w = len(exp.get("by_world", {}))
        n_i = len(exp.get("by_interface", {}))
        n_f = len(exp.get("by_fault", {}))
        n_s = len(exp.get("by_seed", {}))
        total = exp["total_runs"]
        # Infer tasks per world
        if n_w > 0 and n_i > 0 and n_f > 0 and n_s > 0:
            inferred_tasks = total / (n_w * n_i * n_f * n_s)
            if inferred_tasks.is_integer():
                print(f"  {exp['experiment']}: {n_w}w × {n_i}i × {int(inferred_tasks)}t × {n_f}f × {n_s}s = {int(total)} ✅")
            else:
                print(f"  {exp['experiment']}: {n_w}w × {n_i}i × {n_f}f × {n_s}s = {total} (tasks={inferred_tasks:.2f}?)")

    print(f"\nSee {report_path} for full details.")


if __name__ == "__main__":
    main()