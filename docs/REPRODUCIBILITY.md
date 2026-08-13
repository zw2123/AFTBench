# Reproducibility

## Prerequisites

- Python 3.11+
- Linux or macOS (Windows untested)
- ~500 MB disk space for artifacts

## Setup

```bash
make setup
```

This creates a virtual environment in `.venv/` and installs all dependencies.

## Quick Start

### Smoke Test (< 60 seconds)

```bash
make smoke
```

Or equivalently:

```bash
python -m aftbench run --config configs/smoke.yaml
```

### Full Pilot

```bash
make pilot
```

Or:

```bash
python -m aftbench run --config configs/pilot.yaml
```

### Analysis and Report

```bash
make analyze
make report
```

Or:

```bash
python -m aftbench analyze --input artifacts/pilot/results.csv
python -m aftbench report --input artifacts/pilot/results.csv
```

### Acceptance Check

```bash
make acceptance
```

Or:

```bash
python scripts/check_acceptance.py
```

## Deterministic Seeds

All benchmark runs accept a `seed` parameter. The same seed produces identical results:

```bash
python -m aftbench run --config configs/pilot.yaml --seed 42
```

## Resuming Interrupted Runs

The full profile supports resumption:

```bash
python -m aftbench run --config configs/full.yaml --resume artifacts/pilot/results.csv
```

## Artifact Locations

| Artifact | Path |
|----------|------|
| Smoke results | `artifacts/smoke/results.csv` |
| Smoke traces | `artifacts/smoke/traces.jsonl` |
| Pilot results | `artifacts/pilot/results.csv` |
| Pilot traces | `artifacts/pilot/traces.jsonl` |
| Analysis output | `artifacts/pilot/paired_summary.csv` |
| Plots | `artifacts/pilot/plots/` |
| Reports | `reports/PILOT_REPORT.md` |

## Verification

To verify results are reproducible:

```bash
# Run twice with same seed
python -m aftbench run --config configs/smoke.yaml --seed 42
cp artifacts/smoke/results.csv /tmp/run1.csv

python -m aftbench run --config configs/smoke.yaml --seed 42
diff /tmp/run1.csv artifacts/smoke/results.csv  # Should be empty
```

## Dependencies

All dependencies are listed in `pyproject.toml`. No system-level packages required beyond Python 3.11+.
