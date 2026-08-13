"""Paired statistical analysis for AFTBench results.

Pairs results by (task_id, world, fault_type, seed, agent_id) and computes
differences between interface conditions. Writes paired_details.csv.
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any
import numpy as np

from ..schemas import ResultRow


@dataclass
class PairedComparison:
    """A single paired comparison between two interface conditions."""
    task_id: str
    world: str
    fault_type: str | None
    seed: int
    agent_id: str
    interface_a: str
    interface_b: str
    # Metric differences (a - b)
    delta_state_correct: int  # 1 if a correct and b not, -1 if vice versa, 0 otherwise
    delta_postcondition: int
    delta_safety: int
    delta_tool_calls: int
    delta_turns: int
    delta_wall_clock_ms: int
    delta_context_tokens: int


def _pair_key(row: ResultRow) -> tuple:
    """Key used to pair results across interface conditions."""
    return (row.task_id, row.world, row.fault_type, row.seed, row.agent_id)


def _bool_to_int(v: bool | None) -> int:
    if v is None:
        return 0
    return 1 if v else 0


def build_pairs(rows: list[ResultRow]) -> list[PairedComparison]:
    """Build paired comparisons from result rows.

    Groups rows by (task_id, world, fault_type, seed, agent_id).
    For each group with exactly 2 interface conditions, computes the
    difference in each metric (interface_a - interface_b), where
    interface_a < interface_b lexicographically.
    """
    groups: dict[tuple, list[ResultRow]] = defaultdict(list)
    for r in rows:
        groups[_pair_key(r)].append(r)

    pairs: list[PairedComparison] = []
    for key, group_rows in groups.items():
        if len(group_rows) != 2:
            continue  # skip unpaired groups

        # Sort by interface_condition for deterministic ordering
        group_rows.sort(key=lambda r: r.interface_condition)
        a, b = group_rows

        pairs.append(PairedComparison(
            task_id=a.task_id,
            world=a.world,
            fault_type=a.fault_type,
            seed=a.seed,
            agent_id=a.agent_id,
            interface_a=a.interface_condition,
            interface_b=b.interface_condition,
            delta_state_correct=_bool_to_int(a.state_correct_completion) - _bool_to_int(b.state_correct_completion),
            delta_postcondition=_bool_to_int(a.postcondition_satisfied) - _bool_to_int(b.postcondition_satisfied),
            delta_safety=_bool_to_int(a.safety_predicate_satisfied) - _bool_to_int(b.safety_predicate_satisfied),
            delta_tool_calls=a.tool_calls - b.tool_calls,
            delta_turns=a.model_turns - b.model_turns,
            delta_wall_clock_ms=a.wall_clock_ms - b.wall_clock_ms,
            delta_context_tokens=a.context_tokens - b.context_tokens,
        ))

    return pairs


def paired_summary(pairs: list[PairedComparison]) -> dict[str, dict[str, float]]:
    """Compute summary statistics over paired differences.

    Returns a dict keyed by metric name, each containing:
      - n_pairs: number of pairs
      - mean_delta: mean of differences
      - median_delta: median of differences
      - stdev_delta: standard deviation (0 if n < 2)
      - n_a_better: count where a outperformed b (positive delta for correctness metrics)
      - n_b_better: count where b outperformed a
      - n_tied: count of ties
    """
    metric_fields = [
        "delta_state_correct",
        "delta_postcondition",
        "delta_safety",
        "delta_tool_calls",
        "delta_turns",
        "delta_wall_clock_ms",
        "delta_context_tokens",
    ]

    summary: dict[str, dict[str, float]] = {}
    for metric in metric_fields:
        values = [getattr(p, metric) for p in pairs]
        n = len(values)
        if n == 0:
            summary[metric] = {
                "n_pairs": 0,
                "mean_delta": 0.0,
                "median_delta": 0.0,
                "stdev_delta": 0.0,
                "n_a_better": 0,
                "n_b_better": 0,
                "n_tied": 0,
            }
            continue

        mean_val = statistics.fmean(values)
        median_val = statistics.median(values)
        stdev_val = statistics.stdev(values) if n >= 2 else 0.0

        n_a_better = sum(1 for v in values if v > 0)
        n_b_better = sum(1 for v in values if v < 0)
        n_tied = sum(1 for v in values if v == 0)

        summary[metric] = {
            "n_pairs": n,
            "mean_delta": round(mean_val, 4),
            "median_delta": round(median_val, 4),
            "stdev_delta": round(stdev_val, 4),
            "n_a_better": n_a_better,
            "n_b_better": n_b_better,
            "n_tied": n_tied,
        }

    return summary


def run_paired_analysis(rows: list[ResultRow], output_path: str) -> dict[str, dict[str, float]]:
    """Run the full paired analysis pipeline and write paired_details.csv.

    Returns the summary dict.
    """
    pairs = build_pairs(rows)

    # Write paired details CSV
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pair_fields = [f.name for f in fields(PairedComparison)]
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=pair_fields)
        writer.writeheader()
        for p in pairs:
            writer.writerow({
                "task_id": p.task_id,
                "world": p.world,
                "fault_type": p.fault_type or "",
                "seed": p.seed,
                "agent_id": p.agent_id,
                "interface_a": p.interface_a,
                "interface_b": p.interface_b,
                "delta_state_correct": p.delta_state_correct,
                "delta_postcondition": p.delta_postcondition,
                "delta_safety": p.delta_safety,
                "delta_tool_calls": p.delta_tool_calls,
                "delta_turns": p.delta_turns,
                "delta_wall_clock_ms": p.delta_wall_clock_ms,
                "delta_context_tokens": p.delta_context_tokens,
            })

    # Compute and return summary
    summary = paired_summary(pairs)

    # Also write summary alongside details
    summary_path = out.with_name("paired_summary_stats.csv")
    with open(summary_path, "w") as f:
        f.write("metric,n_pairs,mean_delta,median_delta,stdev_delta,n_a_better,n_b_better,n_tied\n")
        for metric, stats in summary.items():
            f.write(
                f"{metric},{stats['n_pairs']},{stats['mean_delta']},"
                f"{stats['median_delta']},{stats['stdev_delta']},"
                f"{stats['n_a_better']},{stats['n_b_better']},{stats['n_tied']}\n"
            )

    return summary
