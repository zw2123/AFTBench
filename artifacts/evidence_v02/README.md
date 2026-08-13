# evidence_v02 Directory Map

Canonical deterministic evidence v0.2, organized per the frozen statistical
analysis plan (`docs/STATISTICAL_ANALYSIS_PLAN_V1.md`, v1.1).

| Directory | Hypothesis | Canonical profile (config) | Shared data |
|-----------|------------|----------------------------|-------------|
| `discovery/` | H1a/H1b selective discovery | `configs/evidence/discovery_frontier.yaml` | — |
| `resume/` | H2 resumable invocation | `configs/evidence/interruption_recovery.yaml` | byte-identical to `durable_state/` |
| `durable_state/` | H3 durable state | same run as H2 (I5 vs I5-minus-durable-state contrast) | copy of `resume/` |
| `effect_contract/` | H4a/H4b effect contract | `postcommit_loss/` + `stale_permission/` | — |
| `verification/` | H5 verification | `configs/evidence/verification.yaml` (false_success / false_failure workload) | — |
| `sqlite/` | external validity | `configs/evidence/production_like.yaml` (+ Phase 8 micro files) | — |
| `m1_resume/` … `m4_discovery/` | micro causal experiments (Phase 10) | scripts/run_m1..m4_experiment.py | — |
| `calibration_results.json` | safety metric calibration (Phase 3) | scripts/calibrate_safety_metrics_v2.py | — |

`durable_state/` contains a byte-identical copy of the `resume/` run because
H2 and H3 draw their contrasts from the same canonical execution (the
profile includes all treatment and control interfaces).

`CANONICAL_CONTRASTS.{json,md}` holds the 7 pre-registered contrasts with
direction-aware W/T/L, task-clustered bootstrap CIs, and Holm-corrected
p-values (`scripts/analyze_canonical_v02.py`).
