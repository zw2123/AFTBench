#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== AFTBench Pilot Run ==="
echo "Config: configs/pilot.yaml"
echo "Output: artifacts/pilot"
echo "Worlds: enterprise_records, long_running_jobs, large_catalog, external_actions"
echo "Interfaces: I0-I5"
echo "Faults: all 10 types + none"
echo "Seeds: 42, 123, 456"
echo ""

python -m aftbench run --config configs/pilot.yaml

echo ""
echo "=== Pilot run complete ==="
echo "Results: artifacts/pilot/results.csv"
echo "Traces:  artifacts/pilot/traces/"
echo "Report:  artifacts/pilot/report.html"
