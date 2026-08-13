#!/usr/bin/env python3
"""Analyze recovery metrics across ablation variants."""
import csv
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np


def analyze_recovery_metrics(results_dir: str, output_dir: str):
    """Analyze recovery metrics and generate manipulation checks."""
    results_path = Path(results_dir) / "results.csv"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load results
    with open(results_path) as f:
        results = list(csv.DictReader(f))
    
    # Group by interface and fault
    by_iface_fault = defaultdict(lambda: {'total': 0, 'recovery': 0, 'correct': 0})
    
    for r in results:
        key = (r['interface_condition'], r.get('fault_type', 'none'))
        by_iface_fault[key]['total'] += 1
        if r.get('recovery_success') == 'true':
            by_iface_fault[key]['recovery'] += 1
        if r.get('state_correct_completion') == 'true':
            by_iface_fault[key]['correct'] += 1
    
    # Generate recovery analysis
    recovery_analysis = []
    for (iface, fault), data in sorted(by_iface_fault.items()):
        recovery_rate = data['recovery'] / data['total'] if data['total'] > 0 else 0
        correct_rate = data['correct'] / data['total'] if data['total'] > 0 else 0
        
        recovery_analysis.append({
            'interface': iface,
            'fault': fault,
            'total_runs': data['total'],
            'recovery_count': data['recovery'],
            'recovery_rate': f"{recovery_rate:.3f}",
            'correct_count': data['correct'],
            'correct_rate': f"{correct_rate:.3f}",
        })
    
    # Write recovery analysis
    recovery_path = output_path / "recovery_analysis.csv"
    if recovery_analysis:
        with open(recovery_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=recovery_analysis[0].keys())
            writer.writeheader()
            writer.writerows(recovery_analysis)
    
    # Generate manipulation checks
    manipulation_checks = []
    
    # Define ablation contrasts
    ablations = [
        ('I5', 'I5-minus-selective-discovery', 'selective_discovery'),
        ('I5', 'I5-minus-resumable-invocation', 'resumable_invocation'),
        ('I5', 'I5-minus-observable-execution', 'observable_execution'),
        ('I5', 'I5-minus-structured-output', 'structured_output'),
        ('I5', 'I5-minus-side-effect-contract', 'side_effect_contract'),
        ('I5', 'I5-minus-durable-state', 'durable_state'),
        ('I5', 'I5-minus-verification', 'verification'),
    ]
    
    for treatment, control, primitive in ablations:
        # Find matching pairs (same fault)
        faults = set()
        for (iface, fault) in by_iface_fault.keys():
            if iface in (treatment, control):
                faults.add(fault)
        
        for fault in sorted(faults):
            t_key = (treatment, fault)
            c_key = (control, fault)
            
            if t_key in by_iface_fault and c_key in by_iface_fault:
                t_data = by_iface_fault[t_key]
                c_data = by_iface_fault[c_key]
                
                t_recovery = t_data['recovery'] / t_data['total'] if t_data['total'] > 0 else 0
                c_recovery = c_data['recovery'] / c_data['total'] if c_data['total'] > 0 else 0
                
                t_correct = t_data['correct'] / t_data['total'] if t_data['total'] > 0 else 0
                c_correct = c_data['correct'] / c_data['total'] if c_data['total'] > 0 else 0
                
                recovery_diff = t_recovery - c_recovery
                correct_diff = t_correct - c_correct
                
                # Determine if manipulation check passes
                # Pass if recovery difference > 10% or correct difference > 10%
                passes = abs(recovery_diff) > 0.10 or abs(correct_diff) > 0.10
                
                manipulation_checks.append({
                    'primitive': primitive,
                    'treatment': treatment,
                    'control': control,
                    'fault': fault,
                    'valid_pairs': min(t_data['total'], c_data['total']),
                    'treatment_recovery': f"{t_recovery:.3f}",
                    'control_recovery': f"{c_recovery:.3f}",
                    'recovery_difference': f"{recovery_diff:.3f}",
                    'treatment_correct': f"{t_correct:.3f}",
                    'control_correct': f"{c_correct:.3f}",
                    'correct_difference': f"{correct_diff:.3f}",
                    'manipulation_check': 'PASS' if passes else 'NULL',
                })
    
    # Write manipulation checks
    checks_path = output_path / "manipulation_checks.csv"
    if manipulation_checks:
        with open(checks_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=manipulation_checks[0].keys())
            writer.writeheader()
            writer.writerows(manipulation_checks)
    
    # Summary
    pass_count = sum(1 for m in manipulation_checks if m['manipulation_check'] == 'PASS')
    null_count = sum(1 for m in manipulation_checks if m['manipulation_check'] == 'NULL')
    
    return {
        'recovery_analysis_path': str(recovery_path),
        'manipulation_checks_path': str(checks_path),
        'total_checks': len(manipulation_checks),
        'pass_count': pass_count,
        'null_count': null_count,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_recovery.py <results_dir> <output_dir>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    result = analyze_recovery_metrics(results_dir, output_dir)
    print(f"Recovery analysis: {result['recovery_analysis_path']}")
    print(f"Manipulation checks: {result['manipulation_checks_path']}")
    print(f"Total checks: {result['total_checks']}")
    print(f"PASS: {result['pass_count']}, NULL: {result['null_count']}")
