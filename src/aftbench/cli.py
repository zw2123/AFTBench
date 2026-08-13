"""CLI entry point for AFTBench."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from .config import BenchmarkConfig


@click.group()
def main():
    """AFTBench: Benchmark for Agent-First Tooling."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@main.command()
@click.option("--config", required=True, type=click.Path(exists=True))
@click.option("--seed", type=int, default=None)
@click.option("--resume", type=click.Path(exists=True), default=None)
def run(config: str, seed: int | None, resume: str | None):
    """Run a benchmark profile."""
    cfg = BenchmarkConfig.from_yaml(config)
    if seed is not None:
        cfg.seed = seed
        cfg.seeds = [seed]
    if resume:
        cfg.resume_from = resume

    from .runner import BenchmarkRunner
    runner = BenchmarkRunner(cfg)
    results = runner.run_profile()
    click.echo(f"Completed {len(results)} runs. Results at {cfg.output_dir}/results.csv")


@main.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output", type=click.Path(), default=None)
def analyze(input_path: str, output: str | None):
    """Analyze benchmark results."""
    import csv
    from .schemas import ResultRow
    from .metrics import compute_metrics
    from .analysis.paired import run_paired_analysis
    from .analysis.bootstrap import bootstrap_ci

    rows = _load_results(input_path)
    summary = compute_metrics(rows)
    
    out_dir = Path(output) if output else Path(input_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Write summary
    summary_path = out_dir / "paired_summary.csv"
    with open(summary_path, "w") as f:
        for field_name in summary.__dataclass_fields__:
            f.write(f"{field_name},{getattr(summary, field_name)}\n")
    
    # Run paired analysis
    paired_path = out_dir / "paired_details.csv"
    run_paired_analysis(rows, str(paired_path))
    
    # Failure breakdown
    breakdown_path = out_dir / "failure_breakdown.csv"
    _write_failure_breakdown(rows, breakdown_path)
    
    click.echo(f"Analysis written to {out_dir}")


@main.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output", type=click.Path(), default=None)
def report(input_path: str, output: str | None):
    """Generate a benchmark report."""
    from .analysis.report import generate_report
    rows = _load_results(input_path)
    out_path = output or "reports/PILOT_REPORT.md"
    generate_report(rows, out_path)
    click.echo(f"Report written to {out_path}")


@main.command()
@click.option("--config", required=True, type=click.Path(exists=True))
def validate(config: str):
    """Validate a configuration file."""
    try:
        cfg = BenchmarkConfig.from_yaml(config)
        click.echo(f"Config valid: profile={cfg.profile}, worlds={cfg.worlds}")
    except Exception as e:
        click.echo(f"Config invalid: {e}", err=True)
        sys.exit(1)


def _load_results(path: str) -> list:
    import csv
    from .schemas import ResultRow
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
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
            rows.append(ResultRow(**{k: v for k, v in row.items()
                                    if k in ResultRow.__dataclass_fields__}))
    return rows


def _write_failure_breakdown(rows, path: str):
    from collections import Counter
    failures = [r for r in rows if not r.state_correct_completion]
    by_world = Counter(r.world for r in failures)
    by_interface = Counter(r.interface_condition for r in failures)
    by_fault = Counter(r.fault_type for r in failures if r.fault_type)
    
    with open(path, "w") as f:
        f.write("category,value,count\n")
        for w, c in by_world.items():
            f.write(f"world,{w},{c}\n")
        for i, c in by_interface.items():
            f.write(f"interface,{i},{c}\n")
        for ft, c in by_fault.items():
            f.write(f"fault,{ft},{c}\n")


if __name__ == "__main__":
    main()
