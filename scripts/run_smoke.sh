#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== AFTBench Smoke Test ==="
echo "Config: configs/smoke.yaml"
echo "Output: artifacts/smoke"
echo ""

python -m aftbench run --config configs/smoke.yaml

echo ""
echo "=== Smoke test complete ==="
echo "Results: artifacts/smoke/results.csv"
echo "Traces:  artifacts/smoke/traces/"
