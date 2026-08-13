# Secondary: Observable Execution — Efficiency Metrics

**Status:** SECONDARY, not in the primary family.  No Holm adjustment.

Observable execution primitives (resume, get_status, reconciliation) enable the agent to query backend status rather than blindly retrying after interruption or response loss.  Measured from existing resume (interrupted_execution) and postcommit_loss (lost_response_after_effect) workloads.

## Resume / Durable-State (interrupted_execution fault)

| Interface | Tool calls | Reexecutions | Retries | Recovery success | Recovery ms |
|-----------|-----------:|-------------:|-------:|-----------------:|-----------:|
| I2 | 1 | 0 | 0 | 0/24 | — |
| I3 | 1 | 0 | 0 | 24/24 | — |
| I5 | 1 | 0 | 0 | 24/24 | — |
| I5-minus-durable-state | 1 | 1 | 0 | 0/24 | — |
| I5-minus-resumable-invocation | 1 | 1 | 0 | 0/24 | — |

### Paired contrasts (recovery success)

| Contrast | Pairs | Treatment recovery | Control recovery | Treatment reexec | Control reexec |
|----------|------:|-------------------:|-----------------:|-----------------:|---------------:|
| I3_vs_minus_resumable | 24 | 24/24 | 0/24 | 0 | 1 |
| I5_vs_minus_durable | 24 | 24/24 | 0/24 | 0 | 1 |
| I5_vs_minus_resumable | 24 | 24/24 | 0/24 | 0 | 1 |

## Postcommit-Loss (lost_response_after_effect fault)

| Interface | Tool calls | Retries | Duplicate effect | Reconciliation |
|-----------|-----------:|-------:|-----------------:|--------------:|
| I0 | 1.75 | 0.75 | 18/24 | 0/24 |
| I1 | 2 | 1 | 24/24 | 0/24 |
| I3 | 2 | 1 | 24/24 | 0/24 |
| I4 | 2 | 1 | 0/24 | 0/24 |
| I5 | 1 | 0 | 0/24 | 24/24 |
| I5-minus-side-effect-contract | 1 | 0 | 0/24 | 24/24 |
| I5-minus-verification | 1 | 0 | 0/24 | 24/24 |

## Interpretation

Interfaces without observable execution (I5-minus-resumable-invocation, I5-minus-durable-state) trigger 1.0 unnecessary logical reexecutions under interruption.  Interfaces with resume (I3, I5) recover without restart.  Under dropped-response faults, I5's reconciliation primitive eliminates transport retries (0.0 vs 0.8-1.0 for I0/I1).