#!/usr/bin/env python3
"""M4 Micro Experiment: Discovery Frontier Scaling.

Tests catalog sizes 10, 50, 200, 1000 with I1, I2, I5, I5-minus-discovery.

Required metrics per catalog size:
  full_catalog_tokens, compact_metadata_tokens
  schemas_visible, schemas_materialized
  top1_recall, top3_recall, top5_recall
  fallback_called, fallback_success
  wrong_tool_selected

Expected: I1 tokens grow with catalog size, I2 tokens are compact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path("src").resolve()))

OUTPUT_DIR = Path("artifacts/evidence_v02/m4_discovery")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULTS = []


def check(passed: bool, label: str, detail: str = ""):
    status = "✅" if passed else "❌"
    print(f"  {status} {label}: {detail}")
    RESULTS.append({"label": label, "passed": passed, "detail": detail})


def run_m4():
    print("=" * 60)
    print("M4 Micro Experiment: Discovery Frontier")
    print("=" * 60)

    from aftbench.config import BenchmarkConfig
    from aftbench.runner import BenchmarkRunner
    from aftbench.schemas import FaultSchedule, FaultType
    from aftbench.trace import TraceWriter
    from aftbench.worlds.large_catalog import LargeCatalogWorld

    import tempfile
    tmp = tempfile.mkdtemp()

    catalog_sizes = [10, 50, 200, 1000]
    interfaces = ["I1", "I2", "I5", "I5-minus-selective-discovery"]
    seeds = [42, 123]

    config = BenchmarkConfig(
        profile="test",
        output_dir=tmp,
        worlds=["large_catalog"],
        interfaces=interfaces,
        faults=["none"],
        max_tasks_per_world=1,
        seeds=seeds,
    )
    runner = BenchmarkRunner(config)

    # Load a task that uses large_catalog world
    tasks = [t for t in runner._load_tasks() if t.world == "large_catalog"]
    task = tasks[0] if tasks else None
    if task is None:
        check(False, "no large_catalog task found", "")
        return

    # For each catalog size and interface, run and measure
    table = defaultdict(lambda: defaultdict(dict))

    for csize in catalog_sizes:
        for iface in interfaces:
            for seed in seeds:
                world = LargeCatalogWorld(catalog_size=csize)
                tw = TraceWriter(
                    Path(tmp) / f"traces_{iface}_c{csize}_s{seed}.jsonl"
                )
                try:
                    result = runner.run_task(
                        task, world, runner._create_interface(iface), iface,
                        None, seed, tw,
                    )

                    # Collect metrics
                    def_tokens = result.tool_definition_tokens
                    correct = result.state_correct_completion
                    ctx_tokens = result.context_tokens

                    # Store by (csize, iface)
                    key = (csize, iface)
                    if "tokens" not in table[key]:
                        table[key]["tokens"] = []
                    table[key]["tokens"].append(ctx_tokens)
                    if "def_tokens" not in table[key]:
                        table[key]["def_tokens"] = []
                    table[key]["def_tokens"].append(def_tokens)
                    if "correct" not in table[key]:
                        table[key]["correct"] = []
                    table[key]["correct"].append(correct)

                    print(f"  csize={csize:4d} {iface:30s} seed={seed} "
                          f"ctx_tokens={ctx_tokens:5d} def_tokens={def_tokens:5d} "
                          f"correct={correct}")

                except Exception as e:
                    print(f"  csize={csize:4d} {iface:30s} EXCEPTION: {e}")
                finally:
                    tw.close()

    # Build results table
    print("\n" + "=" * 60)
    print("RESULTS TABLE")
    print("=" * 60)
    print(f"{'Tools':>6} {'I1 tokens':>12} {'I2 tokens':>12} {'I5 tokens':>12} {'I5-disc tokens':>14} {'I1 correct':>12} {'I2 correct':>12}")
    print("-" * 80)

    for csize in catalog_sizes:
        row = f"{csize:>6}"
        for iface in interfaces:
            key = (csize, iface)
            if key in table and table[key]["tokens"]:
                avg_t = sum(table[key]["tokens"]) / len(table[key]["tokens"])
                avg_d = sum(table[key]["def_tokens"]) / len(table[key]["def_tokens"])
                corr = sum(1 for c in table[key]["correct"] if c)
                total = len(table[key]["correct"])
                row += f" {avg_t:>8.0f}/{avg_d:>8.0f}"
            else:
                row += f" {'N/A':>12}"
        print(row)

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Check that I1 tokens scale with catalog size
    print("\nContext scaling check:")
    i1_tokens_by_size = {}
    for csize in catalog_sizes:
        key = (csize, "I1")
        if key in table and table[key]["tokens"]:
            i1_tokens_by_size[csize] = sum(table[key]["tokens"]) / len(table[key]["tokens"])

    if len(i1_tokens_by_size) >= 2:
        sizes = sorted(i1_tokens_by_size.keys())
        scales = i1_tokens_by_size[sizes[-1]] > i1_tokens_by_size[sizes[0]]
        check(scales,
              "I1 tokens scale with catalog size",
              f"min={i1_tokens_by_size[sizes[0]]:.0f} max={i1_tokens_by_size[sizes[-1]]:.0f}")
    else:
        check(False, "I1 tokens scaling", "insufficient data")

    # Check that I2 tokens are compact
    print("\nCompact discovery check:")
    i2_tokens_by_size = {}
    for csize in catalog_sizes:
        key = (csize, "I2")
        if key in table and table[key]["tokens"]:
            i2_tokens_by_size[csize] = sum(table[key]["tokens"]) / len(table[key]["tokens"])

    if i2_tokens_by_size:
        max_i2 = max(i2_tokens_by_size.values())
        min_i1 = min(i1_tokens_by_size.values()) if i1_tokens_by_size else 999999
        check(max_i2 < min_i1,
              "I2 tokens are compact (less than I1 at smallest catalog)",
              f"I2 max={max_i2:.0f} < I1 min={min_i1:.0f}")
    else:
        check(False, "I2 compact discovery", "insufficient data")

    # Check that I5-minus-discovery exposes full catalog
    print("\nFull catalog exposure check:")
    i5minus_tokens_by_size = {}
    for csize in catalog_sizes:
        key = (csize, "I5-minus-selective-discovery")
        if key in table and table[key]["tokens"]:
            i5minus_tokens_by_size[csize] = sum(table[key]["tokens"]) / len(table[key]["tokens"])

    if i5minus_tokens_by_size and i2_tokens_by_size:
        # I5-minus-discovery should expose more tokens than I2
        avg_i5minus = sum(i5minus_tokens_by_size.values()) / len(i5minus_tokens_by_size)
        avg_i2 = sum(i2_tokens_by_size.values()) / len(i2_tokens_by_size)
        check(avg_i5minus > avg_i2,
              "I5-minus-discovery exposes more context than I2",
              f"I5-minus avg={avg_i5minus:.0f} > I2 avg={avg_i2:.0f}")
    else:
        check(False, "full catalog exposure", "insufficient data")

    # Write results
    path = OUTPUT_DIR / "m4_results.json"
    row_data = []
    for csize in catalog_sizes:
        row = {"catalog_size": csize}
        for iface in interfaces:
            key = (csize, iface)
            if key in table:
                row[f"{iface}_tokens"] = sum(table[key]["tokens"]) / len(table[key]["tokens"]) if table[key]["tokens"] else 0
                row[f"{iface}_def_tokens"] = sum(table[key]["def_tokens"]) / len(table[key]["def_tokens"]) if table[key]["def_tokens"] else 0
                row[f"{iface}_correct"] = sum(1 for c in table[key]["correct"] if c)
                row[f"{iface}_total"] = len(table[key]["correct"])
        row_data.append(row)

    with open(path, "w") as f:
        json.dump({
            "experiment": "M4_discovery_frontier",
            "catalog_sizes": catalog_sizes,
            "interfaces": interfaces,
            "table": row_data,
            "n_passed": sum(1 for r in RESULTS if r["passed"]),
            "n_total": len(RESULTS),
            "checks": RESULTS,
        }, f, indent=2)
    print(f"\nResults written to {path}")

    if sum(1 for r in RESULTS if r["passed"]) == len(RESULTS):
        print("✅ M4: ALL CHECKS PASSED")
    else:
        print(f"⚠️  M4: some checks failed")


if __name__ == "__main__":
    run_m4()