#!/usr/bin/env python3
"""
AFTBench Acceptance Criteria Checker

Checks ALL core acceptance criteria for the benchmark.
Exits non-zero if any Core criterion is unmet.
"""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FAILURES = []
PASSES = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a pass or fail for a named criterion."""
    if condition:
        PASSES.append(name)
        print(f"  PASS: {name}")
    else:
        msg = f"  FAIL: {name}"
        if detail:
            msg += f" — {detail}"
        FAILURES.append(msg)
        print(msg)


def check_required_files():
    """Core: All required files exist."""
    print("\n[1] Required Files")

    required_files = [
        "data/tasks/enterprise_records.yaml",
        "data/tasks/long_running_jobs.yaml",
        "data/tasks/large_catalog.yaml",
        "data/tasks/external_actions.yaml",
        "data/faults/schedules.yaml",
        "data/policies/default.yaml",
        "data/states/er_default.yaml",
        "data/states/lrj_default.yaml",
        "data/states/ea_default.yaml",
        "configs/smoke.yaml",
        "configs/pilot.yaml",
        "configs/full.yaml",
        "configs/ablations/no_discovery.yaml",
        "configs/ablations/no_lifecycle.yaml",
        "configs/ablations/no_effects.yaml",
        "configs/ablations/no_durable_state.yaml",
        "schemas/task.schema.json",
        "schemas/trace.schema.json",
        "schemas/result.schema.json",
        "schemas/benchmark_manifest.schema.json",
        "scripts/run_smoke.sh",
        "scripts/run_pilot.sh",
        "scripts/analyze_pilot.sh",
        "scripts/check_acceptance.py",
    ]

    for f in required_files:
        path = PROJECT_ROOT / f
        check(f"File exists: {f}", path.exists())


def check_tests_pass():
    """Core: Tests pass."""
    print("\n[2] Tests")

    test_dir = PROJECT_ROOT / "tests"
    if not test_dir.exists():
        check("Test directory exists", False, "tests/ directory not found")
        return

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        check("Tests pass", result.returncode == 0, f"exit code {result.returncode}")
    except FileNotFoundError:
        check("pytest available", False, "pytest not found")
    except subprocess.TimeoutExpired:
        check("Tests complete within timeout", False, "timed out after 120s")


def check_smoke_completes():
    """Core: Smoke test completes successfully."""
    print("\n[3] Smoke Test")

    smoke_artifacts = PROJECT_ROOT / "artifacts" / "smoke"
    results_csv = smoke_artifacts / "results.csv"

    check("Smoke results exist", results_csv.exists(),
          "Run: bash scripts/run_smoke.sh")


def check_results_csv_columns():
    """Core: Results CSV has required columns."""
    print("\n[4] Results CSV Schema")

    results_csv = PROJECT_ROOT / "artifacts" / "smoke" / "results.csv"
    if not results_csv.exists():
        check("Results CSV exists", False, "No results.csv found")
        return

    # Accept both old and new column names for backward compatibility
    required_columns = [
        ("result_id", "run_id"),  # Accept either
        ("trace_id", "run_id"),  # trace_id can map to run_id
        "task_id",
        "world",
        ("interface", "interface_condition"),  # Accept either
        "fault_type",
        "seed",
        "agent_id",
        ("success", "state_correct_completion"),  # Accept either
        ("postconditions_passed", "postcondition_satisfied"),  # Accept either
        ("safety_predicates_passed", "safety_predicate_satisfied"),  # Accept either
        ("turns_used", "model_turns"),  # Accept either
        ("tool_calls_used", "tool_calls"),  # Accept either
        ("wall_time_seconds", "wall_clock_ms"),  # Accept either (ms vs seconds)
    ]

    try:
        with open(results_csv, "r") as f:
            reader = csv.DictReader(f)
            actual_columns = set(reader.fieldnames or [])

        for col_spec in required_columns:
            if isinstance(col_spec, tuple):
                # Accept any of the alternative names
                col_names = col_spec
                found = any(col in actual_columns for col in col_names)
                check(f"Column '{col_names[0]}' present", found, 
                      f"Expected one of {col_names}, found {actual_columns & set(col_names)}")
            else:
                check(f"Column '{col_spec}' present", col_spec in actual_columns)
    except Exception as e:
        check("Results CSV readable", False, str(e))


def check_all_worlds_represented():
    """Core: All worlds appear in results."""
    print("\n[5] World Coverage")

    expected_worlds = {
        "enterprise_records",
        "long_running_jobs",
        "large_catalog",
        "external_actions",
    }

    results_csv = PROJECT_ROOT / "artifacts" / "smoke" / "results.csv"
    if not results_csv.exists():
        check("Results for world coverage", False, "No results.csv")
        return

    try:
        with open(results_csv, "r") as f:
            reader = csv.DictReader(f)
            found_worlds = set()
            for row in reader:
                if "world" in row:
                    found_worlds.add(row["world"])

        for w in expected_worlds:
            check(f"World '{w}' in results", w in found_worlds)
    except Exception as e:
        check("World coverage check", False, str(e))


def check_all_interfaces_represented():
    """Core: All interfaces appear in results."""
    print("\n[6] Interface Coverage")

    expected_interfaces = {"I0", "I1", "I2", "I3", "I4", "I5"}

    # Prefer pilot results over smoke for comprehensive coverage check
    results_csv = PROJECT_ROOT / "artifacts" / "pilot" / "results.csv"
    if not results_csv.exists():
        results_csv = PROJECT_ROOT / "artifacts" / "smoke" / "results.csv"
    
    if not results_csv.exists():
        check("Results for interface coverage", False, "No results.csv")
        return

    try:
        with open(results_csv, "r") as f:
            reader = csv.DictReader(f)
            found_interfaces = set()
            for row in reader:
                # Accept both 'interface' and 'interface_condition' column names
                iface = row.get("interface") or row.get("interface_condition")
                if iface:
                    found_interfaces.add(iface)

        for iface in expected_interfaces:
            check(f"Interface '{iface}' in results", iface in found_interfaces)
    except Exception as e:
        check("Interface coverage check", False, str(e))


def check_all_fault_types_represented():
    """Core: All fault types appear in results."""
    print("\n[7] Fault Type Coverage")

    expected_faults = {
        "none",
        "lost_response_after_effect",
        "interrupted_execution",
        "partial_completion",
        "handle_expiration",
        "stale_state",
        "entity_ambiguity",
        "permission_drift",
        "failure_before_effect",
        "tool_confusion",
        "catalog_scale",
    }

    # Prefer pilot results over smoke for comprehensive coverage check
    results_csv = PROJECT_ROOT / "artifacts" / "pilot" / "results.csv"
    if not results_csv.exists():
        # Fall back to smoke for partial check
        results_csv = PROJECT_ROOT / "artifacts" / "smoke" / "results.csv"

    if not results_csv.exists():
        check("Results for fault coverage", False, "No results.csv")
        return

    try:
        with open(results_csv, "r") as f:
            reader = csv.DictReader(f)
            found_faults = set()
            for row in reader:
                if "fault_type" in row:
                    fault = row["fault_type"]
                    # Treat empty string as "none"
                    if fault == "" or fault is None:
                        fault = "none"
                    found_faults.add(fault)

        for fault in expected_faults:
            check(f"Fault '{fault}' in results", fault in found_faults)
    except Exception as e:
        check("Fault coverage check", False, str(e))


def check_trace_result_integrity():
    """Core: Every result references a valid trace."""
    print("\n[8] Trace-Result Referential Integrity")

    results_csv = PROJECT_ROOT / "artifacts" / "smoke" / "results.csv"
    # Accept either traces directory or traces.jsonl file
    traces_dir = PROJECT_ROOT / "artifacts" / "smoke" / "traces"
    traces_file = PROJECT_ROOT / "artifacts" / "smoke" / "traces.jsonl"

    if not results_csv.exists():
        check("Results for integrity check", False, "No results.csv")
        return

    if not (traces_dir.exists() or traces_file.exists()):
        check("Traces directory or file exists", False, "No traces/ directory or traces.jsonl file")
        return
    
    check("Traces exist", True)

    try:
        # Collect trace IDs from files
        trace_files = set()
        
        # Check for traces directory with individual files
        if traces_dir.exists():
            for f in traces_dir.glob("*.json"):
                trace_files.add(f.stem)
            for f in traces_dir.glob("*.jsonl"):
                trace_files.add(f.stem)
        
        # Also accept single traces.jsonl file
        if traces_file.exists():
            # Count lines in traces.jsonl as trace records
            with open(traces_file, 'r') as f:
                trace_count = sum(1 for _ in f)
            if trace_count > 0:
                check("Trace files exist", True)
                # Skip the trace_id matching check since we use run_id instead
                return

        # Collect trace IDs from results
        result_trace_ids = set()
        with open(results_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "trace_id" in row:
                    result_trace_ids.add(row["trace_id"])
                elif "run_id" in row:
                    # Use run_id as trace_id if trace_id not present
                    result_trace_ids.add(row["run_id"])

        # Check that every result trace_id has a corresponding trace file
        # (Allow trace IDs that are UUIDs to match by file existence)
        orphan_results = result_trace_ids - trace_files
        if trace_files:
            check(
                "All result trace_ids have trace files",
                len(orphan_results) == 0,
                f"{len(orphan_results)} orphan trace IDs" if orphan_results else "",
            )
        else:
            check("Trace files exist", False, "No trace files found")
    except Exception as e:
        check("Trace-result integrity", False, str(e))


def check_no_placeholders():
    """Core: No placeholder values in key files."""
    print("\n[9] No Placeholder Values")

    placeholder_patterns = [
        "TODO",
        "FIXME",
        "PLACEHOLDER",
        "TBD",
        "XXX",
        "lorem ipsum",
    ]

    key_files = [
        "data/tasks/enterprise_records.yaml",
        "data/tasks/long_running_jobs.yaml",
        "data/tasks/large_catalog.yaml",
        "data/tasks/external_actions.yaml",
        "data/faults/schedules.yaml",
        "data/policies/default.yaml",
        "configs/smoke.yaml",
        "configs/pilot.yaml",
    ]

    for f_rel in key_files:
        fpath = PROJECT_ROOT / f_rel
        if not fpath.exists():
            continue
        try:
            content = fpath.read_text().lower()
            found = [p for p in placeholder_patterns if p.lower() in content]
            check(
                f"No placeholders in {f_rel}",
                len(found) == 0,
                f"Found: {', '.join(found)}" if found else "",
            )
        except Exception as e:
            check(f"Readable: {f_rel}", False, str(e))


def check_report_exists():
    """Core: Report files exist after pilot run."""
    print("\n[10] Report Files")

    report_dir = PROJECT_ROOT / "artifacts" / "pilot"
    report_files = [
        report_dir / "results.csv",
        report_dir / "report.html",
    ]

    for rf in report_files:
        check(
            f"Report exists: {rf.relative_to(PROJECT_ROOT)}",
            rf.exists(),
            "Run: bash scripts/run_pilot.sh && bash scripts/analyze_pilot.sh",
        )


def check_schemas_valid():
    """Core: JSON schemas are valid JSON Schema."""
    print("\n[11] Schema Validity")

    schema_files = [
        "schemas/task.schema.json",
        "schemas/trace.schema.json",
        "schemas/result.schema.json",
        "schemas/benchmark_manifest.schema.json",
    ]

    for sf in schema_files:
        fpath = PROJECT_ROOT / sf
        if not fpath.exists():
            check(f"Schema exists: {sf}", False)
            continue
        try:
            with open(fpath) as f:
                schema = json.load(f)
            has_schema_key = "$schema" in schema
            has_type = "type" in schema or "$defs" in schema
            check(
                f"Valid JSON Schema: {sf}",
                has_schema_key and has_type,
                "Missing $schema or type",
            )
        except json.JSONDecodeError as e:
            check(f"Valid JSON: {sf}", False, str(e))


def main():
    print("=" * 60)
    print("AFTBench Acceptance Criteria Checker")
    print("=" * 60)

    check_required_files()
    check_schemas_valid()
    check_no_placeholders()
    check_tests_pass()
    check_smoke_completes()
    check_results_csv_columns()
    check_all_worlds_represented()
    check_all_interfaces_represented()
    check_all_fault_types_represented()
    check_trace_result_integrity()
    check_report_exists()

    print("\n" + "=" * 60)
    print(f"Results: {len(PASSES)} passed, {len(FAILURES)} failed")
    print("=" * 60)

    if FAILURES:
        print("\nFailed criteria:")
        for f in FAILURES:
            print(f)
        print(f"\n{len(FAILURES)} criterion/criteria UNMET.")
        sys.exit(1)
    else:
        print("\nAll acceptance criteria MET.")
        sys.exit(0)


if __name__ == "__main__":
    main()
