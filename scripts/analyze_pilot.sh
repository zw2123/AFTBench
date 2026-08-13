#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

RESULTS_DIR="artifacts/pilot"

if [ ! -f "$RESULTS_DIR/results.csv" ]; then
    echo "ERROR: No results found at $RESULTS_DIR/results.csv"
    echo "Run the pilot first: bash scripts/run_pilot.sh"
    exit 1
fi

echo "=== AFTBench Pilot Analysis ==="
echo ""

# Generate summary statistics
echo "--- Summary Statistics ---"
python -m aftbench analyze \
    --input "$RESULTS_DIR/results.csv" \
    --output "$RESULTS_DIR/report.html"

echo ""
echo "=== Analysis complete ==="
echo "Report: $RESULTS_DIR/report.html"
