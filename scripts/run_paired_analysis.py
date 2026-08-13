#!/usr/bin/env python3
"""Run paired analysis on experimental results."""
import sys
import csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aftbench.schemas import ResultRow
from aftbench.analysis.paired import run_full_paired_analysis


def load_results_from_csv(results_path: str) -> list[ResultRow]:
    """Load results from CSV file."""
    results = []
    with open(results_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert types
            for bool_field in ["state_correct_completion", "postcondition_satisfied",
                               "safety_predicate_satisfied", "duplicate_effect",
                               "unintended_effect", "unauthorized_effect", "residual_effect"]:
                if bool_field in row:
                    row[bool_field] = row[bool_field] == "true"
            for int_field in ["seed", "human_intervention_count", "model_turns",
                              "tool_calls", "transport_retries", "logical_reexecutions",
                              "context_tokens", "tool_definition_tokens", "tool_result_tokens",
                              "wall_clock_ms", "recovery_ms", "verification_ms", "runtime_overhead_ms"]:
                if int_field in row and row[int_field]:
                    row[int_field] = int(row[int_field])
            for nullable_bool in ["recovery_success", "unknown_outcome_reconciled"]:
                if nullable_bool in row:
                    v = row[nullable_bool]
                    row[nullable_bool] = None if v == "" else (v == "true")
            for nullable_str in ["ablation", "fault_type", "terminal_agent_claim",
                                 "terminal_oracle_outcome", "initial_state_hash"]:
                if nullable_str in row and row[nullable_str] == "":
                    row[nullable_str] = None
            
            results.append(ResultRow(**{k: v for k, v in row.items()
                                       if k in ResultRow.__dataclass_fields__}))
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_paired_analysis.py <results_dir> <output_dir>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    results_path = Path(results_dir) / "results.csv"
    if not results_path.exists():
        print(f"Error: {results_path} not found")
        sys.exit(1)
    
    print(f"Loading results from {results_path}...")
    rows = load_results_from_csv(str(results_path))
    print(f"Loaded {len(rows)} result rows")
    
    print(f"Running paired analysis...")
    result = run_full_paired_analysis(rows, output_dir)
    
    print(f"\nResults:")
    print(f"  Basic paired comparisons: {len(result['basic_summary'])} metrics")
    print(f"  Explicit contrasts: {result['n_explicit_contrasts']}")
    print(f"  Contrasts written to: {result['contrasts_path']}")
    print(f"  Bootstrap intervals written to: {result['bootstrap_path']}")
