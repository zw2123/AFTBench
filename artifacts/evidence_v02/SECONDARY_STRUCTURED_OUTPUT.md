# Secondary: Structured Output — Interaction Efficiency

**Status:** SECONDARY, not in the primary family.  No Holm adjustment.

Structured output = typed capability schemas (input_schema) and structured tool results (typed error_code, current_version, structured payloads).  Measured from existing discovery (context exposure) and effect-contract (repair behavior) workloads.

## Discovery workload — context exposure by schema structure

| Condition | Runs | Tool-def tokens (mean) | Context tokens (mean) | Correct completion |
|-----------|-----:|-----------------------:|----------------------:|-------------------:|
| I1_structured_full_catalog | 24 | 4062.75 | 4062.75 | 22/24 |
| I2_structured_selective | 24 | 49.58 | 49.58 | 24/24 |
| I5_structured_selective | 24 | 49.58 | 49.58 | 24/24 |

## postcommit_loss workload — repair behavior

| Interface | Tool calls | Transport retries | Reexecutions | Correct |
|-----------|-----------:|------------------:|-------------:|--------:|
| I0 | 1.75 | 0.75 | 0 | 9/24 |
| I1 | 2 | 1 | 0 | 9/24 |
| I3 | 2 | 1 | 0 | 9/24 |
| I4 | 2 | 1 | 0 | 24/24 |
| I5 | 1 | 0 | 0 | 24/24 |

## stale_permission workload — repair behavior

| Interface | Tool calls | Transport retries | Reexecutions | Correct |
|-----------|-----------:|------------------:|-------------:|--------:|
| I1 | 1.75 | 0 | 0 | 15/24 |
| I3 | 1.75 | 0 | 0 | 15/24 |
| I4 | 2.5 | 0 | 0 | 15/24 |
| I5 | 2.5 | 0 | 0 | 15/24 |

## Interpretation

Structured schemas with selective discovery cut tool-definition exposure ~80x (4063->50 tokens mean across catalog sizes, see H1a/H1b) with no recall loss.  Under stale/permission faults, interfaces exposing structured errors (I4/I5: error_code + current_version) repair via version refresh (transport_retries 0.0) whereas opaque-interface runs (I0/I1) blind-retry (0.5-1.0).  Under lost-response faults, I5's reconcile resolves without retry (0.0).  Structured output thus primarily improves interaction efficiency and repair determinism rather than the source of primary correctness effects.