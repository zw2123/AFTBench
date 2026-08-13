"""Matplotlib plot generation for AFTBench analysis.

Provides three plot functions:
  - interface_ladder_plot: bar chart of success rate by interface condition
  - fault_matrix_plot: heatmap of success rate by (interface, fault_type)
  - paired_difference_plot: distribution of paired differences between interfaces

All plots include labeled axes, sample counts (n=), and metric definitions
in titles/subtitles.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from ..schemas import ResultRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _success_rate(rows: Sequence[ResultRow]) -> float:
    """Fraction of rows with state_correct_completion == True."""
    if not rows:
        return 0.0
    n_correct = sum(1 for r in rows if r.state_correct_completion)
    return n_correct / len(rows)


def _ensure_output_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Interface ladder plot
# ---------------------------------------------------------------------------

def interface_ladder_plot(
    rows: list[ResultRow],
    output_path: str = "plots/interface_ladder.png",
    metric: str = "state_correct_completion",
) -> str:
    """Bar chart of success rate by interface condition, sorted descending.

    Args:
        rows: Benchmark result rows.
        output_path: Where to save the PNG.
        metric: Which metric to plot (currently only state_correct_completion).

    Returns:
        The output_path as a string.
    """
    _ensure_output_dir(output_path)

    # Group by interface
    by_interface: dict[str, list[ResultRow]] = defaultdict(list)
    for r in rows:
        by_interface[r.interface_condition].append(r)

    # Compute rates and sample counts
    items = []
    for iface, iface_rows in by_interface.items():
        rate = _success_rate(iface_rows)
        n = len(iface_rows)
        items.append((iface, rate, n))

    # Sort descending by rate
    items.sort(key=lambda x: x[1], reverse=True)

    labels = [f"{item[0]}\n(n={item[2]})" for item in items]
    rates = [item[1] for item in items]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(labels)), rates, color="#2196F3", edgecolor="#1565C0")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Success Rate")
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
    ax.set_title(
        "Interface Ladder — Task Completion Success Rate",
        fontsize=14,
        fontweight="bold",
    )
    ax.text(
        0.5, -0.18,
        "Metric: state_correct_completion — True iff postconditions AND safety predicates hold.\n"
        "Sorted by success rate descending. Error bars show 95% bootstrap CI (see bootstrap.py).",
        transform=ax.transAxes,
        ha="center",
        fontsize=8,
        color="gray",
    )

    # Add value labels on bars
    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{rate:.1%}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# Fault matrix plot
# ---------------------------------------------------------------------------

def fault_matrix_plot(
    rows: list[ResultRow],
    output_path: str = "plots/fault_matrix.png",
) -> str:
    """Heatmap of success rate by (interface_condition, fault_type).

    Args:
        rows: Benchmark result rows.
        output_path: Where to save the PNG.

    Returns:
        The output_path as a string.
    """
    _ensure_output_dir(output_path)

    # Collect interfaces and fault types (sorted for stability)
    interfaces = sorted(set(r.interface_condition for r in rows))
    fault_types = sorted(set((r.fault_type or "none") for r in rows))

    # Build matrix
    matrix: list[list[float]] = []
    counts: list[list[int]] = []
    for iface in interfaces:
        row_vals: list[float] = []
        row_counts: list[int] = []
        for ft in fault_types:
            subset = [
                r for r in rows
                if r.interface_condition == iface and (r.fault_type or "none") == ft
            ]
            row_vals.append(_success_rate(subset))
            row_counts.append(len(subset))
        matrix.append(row_vals)
        counts.append(row_counts)

    fig, ax = plt.subplots(figsize=(max(8, len(fault_types) * 1.5), max(5, len(interfaces) * 0.8)))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(fault_types)))
    ax.set_xticklabels([ft.replace("_", "\n") for ft in fault_types], rotation=0, ha="center", fontsize=8)
    ax.set_yticks(range(len(interfaces)))
    ax.set_yticklabels(interfaces, fontsize=9)

    # Annotate cells with rate and count
    for i, iface in enumerate(interfaces):
        for j, ft in enumerate(fault_types):
            rate = matrix[i][j]
            n = counts[i][j]
            text_color = "white" if rate < 0.4 or rate > 0.8 else "black"
            ax.text(j, i, f"{rate:.0%}\n(n={n})", ha="center", va="center",
                    fontsize=7, color=text_color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Success Rate")

    ax.set_title(
        "Fault Matrix — Success Rate by Interface × Fault Type",
        fontsize=13,
        fontweight="bold",
    )
    ax.text(
        0.5, -0.12,
        "Metric: state_correct_completion. Cell shows rate and sample count.",
        transform=ax.transAxes,
        ha="center",
        fontsize=8,
        color="gray",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# Paired difference plot
# ---------------------------------------------------------------------------

def paired_difference_plot(
    rows: list[ResultRow],
    output_path: str = "plots/paired_difference.png",
) -> str:
    """Histogram of paired differences in success between two interface conditions.

    Pairs results by (task_id, world, fault_type, seed, agent_id).
    For each pair, computes delta = success_a - success_b (as 0/1).
    Plots the distribution of deltas.

    Args:
        rows: Benchmark result rows.
        output_path: Where to save the PNG.

    Returns:
        The output_path as a string.
    """
    from .paired import build_pairs

    _ensure_output_dir(output_path)

    pairs = build_pairs(rows)
    if not pairs:
        # No pairs available — write a placeholder
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No paired data available", ha="center", va="center",
                fontsize=14, transform=ax.transAxes)
        ax.set_title("Paired Difference Distribution")
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path

    deltas = [p.delta_state_correct for p in pairs]
    n_pairs = len(deltas)

    fig, ax = plt.subplots(figsize=(8, 5))

    # Histogram with bins at -1, 0, 1
    bins = [-1.5, -0.5, 0.5, 1.5]
    counts, edges, patches = ax.hist(deltas, bins=bins, color="#4CAF50", edgecolor="#2E7D32",
                                      align="mid", rwidth=0.8)

    # Label bars
    for patch, count in zip(patches, counts):
        if count > 0:
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                count + 0.3,
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

    ax.set_xticks([-1, 0, 1])
    ax.set_xticklabels(["B better\n(−1)", "Tie\n(0)", "A better\n(+1)"])
    ax.set_xlabel("Paired Difference (Interface A − Interface B)")
    ax.set_ylabel("Number of Task Pairs")
    ax.set_title(
        f"Paired Difference Distribution (n={n_pairs} pairs)",
        fontsize=13,
        fontweight="bold",
    )

    # Summary stats
    n_a = sum(1 for d in deltas if d > 0)
    n_b = sum(1 for d in deltas if d < 0)
    n_tie = sum(1 for d in deltas if d == 0)
    summary_text = f"A wins: {n_a}  |  Ties: {n_tie}  |  B wins: {n_b}"
    ax.text(
        0.5, -0.18,
        f"{summary_text}\n"
        "Metric: state_correct_completion. Delta = success_A − success_B ∈ {−1, 0, +1}.",
        transform=ax.transAxes,
        ha="center",
        fontsize=8,
        color="gray",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
