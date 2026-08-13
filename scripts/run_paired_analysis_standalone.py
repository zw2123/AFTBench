#!/usr/bin/env python3
"""Standalone paired analysis script."""
import csv
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np


def load_results(results_path: str) -> list[dict]:
    """Load results from CSV."""
    results = []
    with open(results_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def bool_to_int(v: str) -> int:
    """Convert boolean string to int."""
    if v == "true":
        return 1
    elif v == "false":
        return 0
    return 0


def generate_contrasts(results: list[dict]) -> list[dict]:
    """Generate interface ladder and ablation contrasts."""
    # Group by (task_id, world, fault_type, seed)
    groups = defaultdict(list)
    for row in results:
        key = (row['task_id'], row['world'], row.get('fault_type', ''), row['seed'])
        groups[key].append(row)
    
    contrasts = []
    
    # Interface ladder contrasts
    ladder = [
        ("I1-I0", "I1", "I0"),
        ("I2-I1", "I2", "I1"),
        ("I3-I2", "I3", "I2"),
        ("I4-I3", "I4", "I3"),
        ("I5-I4", "I5", "I4"),
        ("I5-I0", "I5", "I0"),
    ]
    
    # Ablation contrasts
    ablations = [
        ("I5-vs-minus-selective-discovery", "I5", "I5-minus-selective-discovery"),
        ("I5-vs-minus-resumable-invocation", "I5", "I5-minus-resumable-invocation"),
        ("I5-vs-minus-observable-execution", "I5", "I5-minus-observable-execution"),
        ("I5-vs-minus-structured-output", "I5", "I5-minus-structured-output"),
        ("I5-vs-minus-side-effect-contract", "I5", "I5-minus-side-effect-contract"),
        ("I5-vs-minus-durable-state", "I5", "I5-minus-durable-state"),
        ("I5-vs-minus-verification", "I5", "I5-minus-verification"),
    ]
    
    all_contrasts = ladder + ablations
    
    for contrast_name, treatment, control in all_contrasts:
        treatment_values = []
        control_values = []
        task_ids = []
        valid_pairs = 0
        missing_treatment = 0
        missing_control = 0
        
        for key, group_rows in groups.items():
            interfaces = {r['interface_condition']: r for r in group_rows}
            
            if treatment in interfaces and control in interfaces:
                t_val = bool_to_int(interfaces[treatment].get('state_correct_completion', 'false'))
                c_val = bool_to_int(interfaces[control].get('state_correct_completion', 'false'))
                treatment_values.append(t_val)
                control_values.append(c_val)
                task_ids.append(key[0])
                valid_pairs += 1
            else:
                if treatment not in interfaces:
                    missing_treatment += 1
                if control not in interfaces:
                    missing_control += 1
        
        if treatment_values:
            t_arr = np.array(treatment_values)
            c_arr = np.array(control_values)
            diffs = t_arr - c_arr
            
            contrasts.append({
                "contrast_name": contrast_name,
                "treatment": treatment,
                "control": control,
                "valid_pairs": valid_pairs,
                "missing_treatment": missing_treatment,
                "missing_control": missing_control,
                "treatment_mean": float(np.mean(t_arr)),
                "control_mean": float(np.mean(c_arr)),
                "mean_difference": float(np.mean(diffs)),
                "median_difference": float(np.median(diffs)),
                "wins": int(np.sum(diffs > 0)),
                "ties": int(np.sum(diffs == 0)),
                "losses": int(np.sum(diffs < 0)),
            })
    
    return contrasts


def compute_bootstrap(contrasts: list[dict], results: list[dict], n_bootstrap: int = 2000, seed: int = 42) -> list[dict]:
    """Compute task-clustered bootstrap confidence intervals."""
    # Group by (task_id, world, fault_type, seed)
    groups = defaultdict(list)
    for row in results:
        key = (row['task_id'], row['world'], row.get('fault_type', ''), row['seed'])
        groups[key].append(row)
    
    bootstrap_results = []
    
    for contrast in contrasts:
        treatment = contrast['treatment']
        control = contrast['control']
        
        # Collect paired differences
        differences = []
        task_ids = []
        
        for key, group_rows in groups.items():
            interfaces = {r['interface_condition']: r for r in group_rows}
            
            if treatment in interfaces and control in interfaces:
                t_val = bool_to_int(interfaces[treatment].get('state_correct_completion', 'false'))
                c_val = bool_to_int(interfaces[control].get('state_correct_completion', 'false'))
                differences.append(t_val - c_val)
                task_ids.append(key[0])
        
        if not differences:
            bootstrap_results.append({
                "contrast_name": contrast['contrast_name'],
                "error": "No valid pairs",
            })
            continue
        
        diffs_arr = np.array(differences)
        task_ids_arr = np.array(task_ids)
        unique_tasks = np.unique(task_ids_arr)
        
        rng = np.random.RandomState(seed)
        bootstrap_means = []
        
        for _ in range(n_bootstrap):
            sampled_tasks = rng.choice(unique_tasks, size=len(unique_tasks), replace=True)
            sampled_diffs = []
            for task in sampled_tasks:
                task_mask = task_ids_arr == task
                sampled_diffs.extend(diffs_arr[task_mask])
            
            if sampled_diffs:
                bootstrap_means.append(np.mean(sampled_diffs))
        
        if bootstrap_means:
            bootstrap_means = np.array(bootstrap_means)
            ci_lower = float(np.percentile(bootstrap_means, 2.5))
            ci_upper = float(np.percentile(bootstrap_means, 97.5))
            
            bootstrap_results.append({
                "contrast_name": contrast['contrast_name'],
                "treatment": treatment,
                "control": control,
                "n_bootstrap": n_bootstrap,
                "mean_difference": float(np.mean(diffs_arr)),
                "ci_lower_95": ci_lower,
                "ci_upper_95": ci_upper,
                "ci_width": ci_upper - ci_lower,
                "valid_pairs": len(differences),
            })
    
    return bootstrap_results


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
    results = load_results(str(results_path))
    print(f"Loaded {len(results)} result rows")
    
    print(f"Generating contrasts...")
    contrasts = generate_contrasts(results)
    print(f"Generated {len(contrasts)} contrasts")
    
    # Write contrasts
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    contrasts_path = output_path / "explicit_contrasts.csv"
    if contrasts:
        with open(contrasts_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=contrasts[0].keys())
            writer.writeheader()
            writer.writerows(contrasts)
        print(f"Contrasts written to {contrasts_path}")
    
    print(f"Computing bootstrap intervals...")
    bootstrap_results = compute_bootstrap(contrasts, results, n_bootstrap=2000, seed=42)
    
    bootstrap_path = output_path / "bootstrap_intervals.csv"
    if bootstrap_results:
        with open(bootstrap_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=bootstrap_results[0].keys())
            writer.writeheader()
            writer.writerows(bootstrap_results)
        print(f"Bootstrap intervals written to {bootstrap_path}")
    
    print(f"\nSummary:")
    print(f"  Total contrasts: {len(contrasts)}")
    print(f"  Valid pairs per contrast: {sum(c['valid_pairs'] for c in contrasts) / len(contrasts) if contrasts else 0:.1f}")
