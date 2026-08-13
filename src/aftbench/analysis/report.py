"""Generate a Markdown benchmark report from AFTBench results.

Produces a structured report with:
  - Configuration summary
  - Overall metrics (success rate, safety, efficiency)
  - Per-interface breakdown
  - Per-fault-type breakdown
  - Paired analysis summary
  - Notes on methodology (scripted agent, bootstrap CIs)
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from ..schemas import ResultRow
from .bootstrap import bootstrap_ci
from .paired import build_pairs, paired_summary


def generate_report(
    rows: list[ResultRow],
    output_path: str = "reports/PILOT_REPORT.md",
) -> str:
    """Generate a Markdown report and write it to output_path.

    Args:
        rows: Benchmark result rows.
        output_path: Where to write the report.

    Returns:
        The output_path as a string.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    sections: list[str] = []

    # Header
    sections.append("# AFTBench Benchmark Report\n")
    sections.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n")
    sections.append(f"**Total runs:** {len(rows)}\n")

    # --- Overall Metrics ---
    sections.append("## Overall Metrics\n")

    n = len(rows)
    if n == 0:
        sections.append("*No results to report.*\n")
        _write_report(sections, output_path)
        return output_path

    # Success rates
    n_correct = sum(1 for r in rows if r.state_correct_completion)
    n_postcond = sum(1 for r in rows if r.postcondition_satisfied)
    n_safety = sum(1 for r in rows if r.safety_predicate_satisfied)

    success_vals = [1.0 if r.state_correct_completion else 0.0 for r in rows]
    ci = bootstrap_ci(success_vals, seed=42)

    sections.append("| Metric | Value | 95% CI |")
    sections.append("|--------|-------|--------|")
    sections.append(
        f"| State-correct completion | {n_correct}/{n} ({n_correct/n:.1%}) "
        f"| [{ci[0]:.1%}, {ci[1]:.1%}] |"
    )
    sections.append(
        f"| Postcondition satisfied | {n_postcond}/{n} ({n_postcond/n:.1%}) | — |"
    )
    sections.append(
        f"| Safety predicate satisfied | {n_safety}/{n} ({n_safety/n:.1%}) | — |"
    )

    # Efficiency metrics
    tool_calls_vals = [r.tool_calls for r in rows]
    turns_vals = [r.model_turns for r in rows]
    wall_clock_vals = [r.wall_clock_ms for r in rows]
    ctx_tokens_vals = [r.context_tokens for r in rows]

    sections.append("")
    sections.append("### Efficiency\n")
    sections.append("| Metric | Mean | Median |")
    sections.append("|--------|------|--------|")
    sections.append(
        f"| Tool calls | {statistics.fmean(tool_calls_vals):.2f} "
        f"| {statistics.median(tool_calls_vals):.0f} |"
    )
    sections.append(
        f"| Model turns | {statistics.fmean(turns_vals):.2f} "
        f"| {statistics.median(turns_vals):.0f} |"
    )
    sections.append(
        f"| Wall-clock (ms) | {statistics.fmean(wall_clock_vals):.0f} "
        f"| {statistics.median(wall_clock_vals):.0f} |"
    )
    sections.append(
        f"| Context tokens | {statistics.fmean(ctx_tokens_vals):.0f} "
        f"| {statistics.median(ctx_tokens_vals):.0f} |"
    )

    # Safety issues
    n_dup = sum(1 for r in rows if r.duplicate_effect)
    n_unintended = sum(1 for r in rows if r.unintended_effect)
    n_unauthorized = sum(1 for r in rows if r.unauthorized_effect)
    n_residual = sum(1 for r in rows if r.residual_effect)

    sections.append("")
    sections.append("### Safety Issues\n")
    sections.append(f"- Duplicate effects: {n_dup}")
    sections.append(f"- Unintended effects: {n_unintended}")
    sections.append(f"- Unauthorized effects: {n_unauthorized}")
    sections.append(f"- Residual effects: {n_residual}")

    # --- Per-Interface Breakdown ---
    sections.append("")
    sections.append("## Per-Interface Breakdown\n")

    by_interface: dict[str, list[ResultRow]] = defaultdict(list)
    for r in rows:
        by_interface[r.interface_condition].append(r)

    sections.append("| Interface | N | Success Rate | Mean Tool Calls | Mean Wall-Clock (ms) |")
    sections.append("|-----------|---|-------------|-----------------|---------------------|")
    for iface in sorted(by_interface.keys()):
        iface_rows = by_interface[iface]
        rate = sum(1 for r in iface_rows if r.state_correct_completion) / len(iface_rows)
        mean_tc = statistics.fmean(r.tool_calls for r in iface_rows)
        mean_wc = statistics.fmean(r.wall_clock_ms for r in iface_rows)
        sections.append(
            f"| {iface} | {len(iface_rows)} | {rate:.1%} | {mean_tc:.2f} | {mean_wc:.0f} |"
        )

    # --- Per-Fault Breakdown ---
    fault_rows = [r for r in rows if r.fault_type]
    if fault_rows:
        sections.append("")
        sections.append("## Per-Fault-Type Breakdown\n")

        by_fault: dict[str, list[ResultRow]] = defaultdict(list)
        for r in fault_rows:
            by_fault[r.fault_type].append(r)

        sections.append("| Fault Type | N | Success Rate | Recovery Success |")
        sections.append("|------------|---|-------------|-----------------|")
        for ft in sorted(by_fault.keys()):
            ft_rows = by_fault[ft]
            rate = sum(1 for r in ft_rows if r.state_correct_completion) / len(ft_rows)
            n_recovered = sum(1 for r in ft_rows if r.recovery_success)
            sections.append(
                f"| {ft} | {len(ft_rows)} | {rate:.1%} | {n_recovered}/{len(ft_rows)} |"
            )

    # --- Paired Analysis ---
    pairs = build_pairs(rows)
    if pairs:
        sections.append("")
        sections.append("## Paired Interface Comparison\n")
        sections.append(
            f"*{len(pairs)} paired comparisons "
            f"(matched on task_id, world, fault_type, seed, agent_id)*\n"
        )

        summary = paired_summary(pairs)
        sections.append("| Metric | N Pairs | Mean Δ | A Wins | B Wins | Ties |")
        sections.append("|--------|---------|--------|--------|--------|------|")
        for metric, stats in summary.items():
            label = metric.replace("delta_", "").replace("_", " ").title()
            sections.append(
                f"| {label} | {stats['n_pairs']} | {stats['mean_delta']:+.3f} "
                f"| {stats['n_a_better']} | {stats['n_b_better']} | {stats['n_tied']} |"
            )

    # --- Agent-Claim vs Oracle ---
    sections.append("")
    sections.append("## Agent Claim vs. Oracle Outcome\n")

    claim_oracle: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        claim = r.terminal_agent_claim or "unknown"
        oracle = r.terminal_oracle_outcome or "unknown"
        claim_oracle[(claim, oracle)] += 1

    sections.append("| Agent Claim \\ Oracle | Success | Failure | Unknown |")
    sections.append("|----------------------|---------|---------|---------|")
    for claim in ["success", "failure", "partial", "unknown"]:
        s = claim_oracle.get((claim, "success"), 0)
        f_ = claim_oracle.get((claim, "failure"), 0)
        u = claim_oracle.get((claim, "unknown"), 0)
        if s + f_ + u > 0:
            sections.append(f"| {claim} | {s} | {f_} | {u} |")

    # --- Methodology Notes ---
    sections.append("")
    sections.append("## Methodology Notes\n")
    sections.append(
        "- **Agent:** This pilot uses a *scripted agent* (deterministic tool selection "
        "and parameter building). Results reflect the benchmark harness and world "
        "implementations, not LLM capability. LLM agent results will be reported separately."
    )
    sections.append(
        "- **Bootstrap CI:** Confidence intervals computed via percentile bootstrap "
        "with 1000 resamples, seed=42. See `analysis/bootstrap.py`."
    )
    sections.append(
        "- **Paired analysis:** Each task is run under all interface conditions with "
        "the same seed; differences are computed per-pair to control for task difficulty."
    )
    sections.append(
        "- **Success metric:** `state_correct_completion` — True iff both postconditions "
        "are satisfied AND all safety predicates hold in the post-execution world state."
    )

    # --- Artifacts ---
    sections.append("")
    sections.append("## Artifacts\n")
    sections.append("- `results.csv` — raw result rows")
    sections.append("- `traces.jsonl` — execution traces")
    sections.append("- `manifest.json` — run configuration")
    sections.append("- `paired_details.csv` — per-pair differences")
    sections.append("- `failure_breakdown.csv` — failure counts by category")
    sections.append("- `plots/` — visualization PNGs (if generated)")

    _write_report(sections, output_path)
    return output_path


def _write_report(sections: list[str], output_path: str) -> None:
    """Write report sections to file."""
    content = "\n".join(sections) + "\n"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
