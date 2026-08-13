# evidence_v02 Directory Map

Canonical deterministic evidence v0.2, organized per the frozen statistical
analysis plan (`docs/STATISTICAL_ANALYSIS_PLAN_V1.md` §8).

| Directory | Hypothesis | Canonical profile (config) | Shared data |
|-----------|------------|----------------------------|-------------|
| `discovery/` | H1 selective discovery | `configs/evidence/discovery_frontier.yaml` | — |
| `resume/` | H2 resumable invocation | `configs/evidence/interruption_recovery.yaml` | byte-identical to `durable_state/` |
| `durable_state/` | H3 durable state | same run as H2 (I5 vs I5-minus-durable-state contrast) | copy of `resume/` |
| `effect_contract/` | H4 effect contract | `postcommit_loss/` + `stale_permission/` | — |
| `verification/` | H5 verification | same run as H4-postcommit (I5 vs I5-minus-verification contrast) | copy of `effect_contract/postcommit_loss/` |
| `sqlite/` | external validity | `configs/evidence/production_like.yaml` (+ Phase 8 micro files) | — |
| `m1_resume/` … `m4_discovery/` | micro causal experiments (Phase 10) | scripts/run_m1..m4_experiment.py | — |
| `calibration_results.json` | safety metric calibration (Phase 3) | scripts/calibrate_safety_metrics_v2.py | — |

`durable_state/` and `verification/` contain byte-identical copies of the
shared runs because H2/H3 and H4/H5 draw their contrasts from the same
canonical executions (the profiles include all treatment and control
interfaces).  Provenance files inside each directory are identical to the
source run.
