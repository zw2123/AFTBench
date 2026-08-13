# AFTBench Statistical Analysis Plan — v1.0

**Status:** Frozen before canonical evidence v0.2  
**Frozen at:** commit `d7fcf84`  
**Purpose:** Pre-register primary hypotheses, endpoints, pair keys, and multiple-comparison corrections BEFORE looking at new evidence results.

---

## 1. Primary Hypotheses

| ID | Hypotheses (H1: treatment effect) | Primary endpoint(s) |
|----|------------------------------------|---------------------|
| H1 | Selective discovery reduces tool-context exposure **without** unacceptable recall loss | `context_tokens`, `top1_recall` |
| H2 | Resumable invocation improves recovery under transient interruption | `recovery_success` |
| H3 | Durable state improves recovery under process-local state loss | `recovery_after_state_loss` |
| H4 | Effect-aware contracts reduce unsafe external effects | `duplicate_effect`, `unsafe_committed` |
| H5 | Verification reduces false success/failure and unresolved outcomes | `false_success`, `false_failure`, `unresolved` |

**Pre-registration rule:** these hypotheses are frozen. No hypothesis may be added, removed, or reframed after looking at v0.2 evidence.

---

## 2. Primary Contrasts

Each hypothesis maps to a treatment–control contrast:

| Hypothesis | Treatment | Control |
|------------|-----------|---------|
| H1 | I2 or I5 (selective discovery) | I1 (full catalog) |
| H2 | I5 or I3 (resume available) | I5-minus-resume |
| H3 | I5 (durable state) | I5-minus-durable |
| H4 | I4 or I5 (effect contract) | I0/I1 or I5-minus-effect |
| H5 | I5 (verification) | I5-minus-verification |

---

## 3. Pair Key

Every contrast uses matched pairs based on:

```text
task_id
task_manifest_hash
world
backend_version
initial_state_hash
fault_type
fault_schedule_hash
fault_location
controller_version
interface_feature_hash
seed
repetition_id
```

Only runs sharing the same pair key are compared (paired analysis).  
Unmatched aggregate (interface-level mean) comparisons are **not** causal evidence.

---

## 4. Statistical Methods

### Primary hypotheses (confirmatory)
- **Holm correction** across the 5 primary hypotheses.
- Bootstrap paired analysis with **task-clustered** resampling.
- Report: `effect_size`, `95% clustered CI`, `win/tie/loss`, `raw_p`, `adjusted_p`.

### Exploratory analyses
- **Benjamini–Hochberg FDR** control.
- Exploratory endpoints: `state_correct_completion`, `tool_calls`, `compensation`, `recovery_latency`, `policy_overhead`.

### Power / sample reporting
- Always report `n_runs` and `n_task_clusters` per contrast (e.g., "96 runs, 8 independent task clusters").
- Deterministic repeated runs within a cluster are NOT independent samples.

---

## 5. Validity Exclusions

Exclusions must be declared a priori:

1. **Manipulation invalid pairs:** any run where the minus-one treatment failed its manipulation check is excluded from primary analysis.
2. **Fault not reached:** runs where the configured fault did not actually trigger are excluded from fault-mechanism analyses (but included in ITT where specified).
3. **Implementation error:** runs with `unexpected implementation error` (classified in error breakdown) are excluded from mechanism analyses but reported separately; ITT analyses include all planned runs.

---

## 6. Required Output per Contrast

```text
expected_pairs
valid_pairs
missing_pairs
treatment_mean
control_mean
paired_difference
paired_median_difference
win_tie_loss
task_clustered_95pct_CI
raw_p_value
adjusted_p_value
effect_direction
```

---

## 7. Outcome Taxonomy (frozen)

```text
completed_as_requested
safely_aborted
safely_refused
safely_escalated
unsafe_committed
failed_unnecessarily
unresolved
failure
```

- `safely_aborted` / `safely_refused` / `safely_escalated` are **correct** outcomes only when listed in `task.acceptable_outcomes`.
- `unsafe_committed` and `failed_unnecessarily` are **never** scored as correct.
- `state_correct_completion` remains a global summary metric, NOT the sole endpoint for any primary hypothesis.

---

## 8. Evidence Architecture (v0.2)

```text
artifacts/evidence_v02/
    discovery/          (H1)
    resume/             (H2)
    durable_state/      (H3)
    effect_contract/    (H4)
    verification/       (H5)
    sqlite/             (external validity)
    calibration_results.json
    m1_resume/
    m2_postcommit/
    m3_stale_permission/
    m4_discovery/
```

---

## 9. Freeze Rule

After v0.2 evidence is generated, benchmark semantics may NOT be changed
to make LLM results look better. Any semantic change requires a new
benchmark version and full re-run.