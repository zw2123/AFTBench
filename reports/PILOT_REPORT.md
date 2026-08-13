# AFTBench Benchmark Report

*Generated: 2026-08-03 14:33 UTC*

**Total runs:** 2376

## Overall Metrics

| Metric | Value | 95% CI |
|--------|-------|--------|
| State-correct completion | 1782/2376 (75.0%) | [73.2%, 76.8%] |
| Postcondition satisfied | 1782/2376 (75.0%) | — |
| Safety predicate satisfied | 2376/2376 (100.0%) | — |

### Efficiency

| Metric | Mean | Median |
|--------|------|--------|
| Tool calls | 1.62 | 2 |
| Model turns | 1.62 | 2 |
| Wall-clock (ms) | 0 | 0 |
| Context tokens | 225 | 120 |

### Safety Issues

- Duplicate effects: 0
- Unintended effects: 0
- Unauthorized effects: 0
- Residual effects: 0

## Per-Interface Breakdown

| Interface | N | Success Rate | Mean Tool Calls | Mean Wall-Clock (ms) |
|-----------|---|-------------|-----------------|---------------------|
| I0 | 396 | 75.0% | 1.92 | 0 |
| I1 | 396 | 75.0% | 1.92 | 0 |
| I2 | 396 | 75.0% | 1.50 | 0 |
| I3 | 396 | 75.0% | 1.50 | 0 |
| I4 | 396 | 75.0% | 1.50 | 0 |
| I5 | 396 | 75.0% | 1.41 | 0 |

## Per-Fault-Type Breakdown

| Fault Type | N | Success Rate | Recovery Success |
|------------|---|-------------|-----------------|
| entity_ambiguity | 216 | 75.0% | 0/216 |
| failure_before_effect | 216 | 75.0% | 0/216 |
| handle_expiration | 216 | 75.0% | 0/216 |
| interrupted_execution | 216 | 75.0% | 36/216 |
| lost_response_after_effect | 216 | 75.0% | 36/216 |
| partial_completion | 216 | 75.0% | 0/216 |
| permission_drift | 216 | 75.0% | 0/216 |
| stale_state | 216 | 75.0% | 0/216 |

## Agent Claim vs. Oracle Outcome

| Agent Claim \ Oracle | Success | Failure | Unknown |
|----------------------|---------|---------|---------|
| success | 750 | 144 | 0 |
| failure | 1032 | 450 | 0 |

## Methodology Notes

- **Agent:** This pilot uses a *scripted agent* (deterministic tool selection and parameter building). Results reflect the benchmark harness and world implementations, not LLM capability. LLM agent results will be reported separately.
- **Bootstrap CI:** Confidence intervals computed via percentile bootstrap with 1000 resamples, seed=42. See `analysis/bootstrap.py`.
- **Paired analysis:** Each task is run under all interface conditions with the same seed; differences are computed per-pair to control for task difficulty.
- **Success metric:** `state_correct_completion` — True iff both postconditions are satisfied AND all safety predicates hold in the post-execution world state.

## Artifacts

- `results.csv` — raw result rows
- `traces.jsonl` — execution traces
- `manifest.json` — run configuration
- `paired_details.csv` — per-pair differences
- `failure_breakdown.csv` — failure counts by category
- `plots/` — visualization PNGs (if generated)
