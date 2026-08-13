# AFTBench Statistical Analysis Plan — v1.1

**Status:** Pre-specified analysis plan for the final evidence freeze.
**Frozen at:** commit `1e1f565` (co-committed with the H5 false-outcome
workload and the final canonical contrast regeneration).

**Preregistration provenance (git-verifiable):**

| Plan | Commit | Relationship to evidence |
|------|--------|--------------------------|
| SAP v1.0 (5 hypotheses, H1–H4) | `82ba77d` (plan decided at `d7fcf84`) | **Preregistered**: committed 4 commits earlier in history than the v0.2 canonical evidence at `a04f4fb` (`82ba77d` → `bc01085` → `b971640` → `37a3546` → `a04f4fb`). |
| SAP v1.1 (7 contrasts, adds H5) | `1e1f565` | **Pre-specified, not preregistered**: first exists in the same commit as the H5 workload, H5 results, and the 7-contrast analysis. |

**Honesty rule:** H5 and the 7-contrast Holm family must be described in the
paper as *pre-specified* (a priori analysis plan for the final evidence
freeze), **not** as preregistered. H1a/H1b/H2/H3/H4a/H4b derive their
pre-registered status from SAP v1.0; only their endpoint directions and the
non-inferiority margin were fixed in v1.1.

**Revision history:**
- v1.0 (committed at `82ba77d`): 5 primary hypotheses, pair keys, Holm/BH split.
- v1.1 (this document): primary hypotheses split into **7 pre-specified
  contrasts** with explicit endpoint directions, a frozen non-inferiority
  margin for recall, and a frozen W/T/L utility convention.

---

## 1. Primary Contrasts (7, confirmatory)

| ID | Contrast | Primary endpoint | Direction | Claim |
|----|----------|------------------|-----------|-------|
| H1a | I2 vs I1 (selective discovery) | `context_tokens` | lower is better | C(I2) < C(I1) |
| H1b | I2 vs I1 (recall non-inferiority) | `state_correct_completion` (tool-recall proxy) | higher is better | R(I2) ≥ R(I1) − δ, δ = 0.10 |
| H2 | I5 vs I5-minus-resumable-invocation | `recovery_success` | higher is better | resume improves interruption recovery |
| H3 | I5 vs I5-minus-durable-state | `recovery_success` | higher is better | durable state improves state-loss recovery |
| H4a | I4 vs I0 (post-commit loss) | `duplicate_effect` | lower is better | effect contract reduces duplicates |
| H4b | I5 vs I1 (stale state) | `unsafe_committed` | lower is better | effect contract reduces unsafe commits |
| H5 | I5 vs I5-minus-verification (false-outcome workload) | `incorrect_terminal_claim` | lower is better | verification corrects false terminal beliefs |

Endpoints are computed as **binary per-run** indicators; contrasts use
task × seed matched pairs. `incorrect_terminal_claim` = (agent claim of
success) XOR (postconditions and safety predicates satisfied).

## 2. W/T/L Utility Convention

Win/tie/loss always counts **utility** of treatment over control, never raw
numeric ordering:

```text
win   = treatment better than control in endpoint utility
tie   = equal utility
loss  = treatment worse
```

For lower-is-better endpoints, a smaller treatment value is a win.

## 3. Inference

- **Primary family (7 contrasts): Holm correction** across H1a–H5.
- Paired **sign-flip permutation test** (10,000 permutations, seed 42) per
  contrast for raw p-values; task-clustered resampling for 95% CIs.
- **H1b uses a one-sided non-inferiority permutation test** against
  H0: R(I2) ≤ R(I1) − δ with the pre-frozen margin δ = 0.10.
- Report per contrast: `valid_pairs`, `treatment_mean`, `control_mean`,
  `paired_difference` (utility-oriented), `win_tie_loss`, `raw_p`,
  `adjusted_p` (Holm), `task_clustered_95pct_CI`, `direction`.

## 4. Secondary / Exploratory

Benjamini–Hochberg FDR; endpoints: `tool_calls`, `transport_retries`,
`logical_reexecutions`, `recovery_ms`, `verification_ms`,
`runtime_overhead_ms`, `unknown_outcome_reconciled`.

**H5-C robustness variant (secondary, NOT in the primary family):**
`partial_success` lying response channel — the backend applies only part of
the effect (list-valued sub-effects truncated to their first half) while the
channel reports full success. Contrast: I5 vs I5-minus-verification on
`incorrect_terminal_claim` (lower is better), task × seed matched pairs,
reported with its own permutation p, never Holm-adjusted with H1a–H5.
Motivation: extends H5 from all-or-nothing lies to partial effects, without
expanding the confirmatory family.

**Observable-execution secondary:** efficiency metrics from the existing
resume/durable-state (interrupted_execution) and postcommit-loss workloads:
`logical_reexecutions`, `transport_retries`, `recovery_ms`, `tool_calls`.
Claim: observable primitives (resume, reconcile) eliminate unnecessary
restarts and blind retries.

**Structured-output secondary:** interaction-efficiency metrics from the
existing discovery and effect-contract workloads: `tool_definition_tokens`,
`transport_retries`, repair turns. Claim: structured schemas and structured
errors (typed `error_code` + `current_version`) primarily improve interaction
efficiency and repair determinism, not primary correctness.

## 5. Exclusions (a priori)

1. Manipulation-invalid pairs excluded from primary analysis.
2. Fault-not-reached runs excluded from mechanism analyses, included in ITT.
3. Unexpected implementation errors reported separately; ITT includes all.

## 6. Workloads

```text
H1a/H1b  discovery/            (discovery_frontier profile, 8 task clusters)
H2       resume/               (interruption_recovery, ordinary interruption)
H3       durable_state/        (same run; process-state loss via M1 micro)
H4a      effect_contract/      (postcommit_loss)
H4b      effect_contract/      (stale_permission)
H5       verification/         (false-outcome workload: false_success,
                                false_failure)
H5-C     verification_partial/  (robustness variant: partial_success only)
```

## 7. Freeze Rule

After the v1.1 evidence freeze (`1e1f565`), benchmark semantics may NOT be
changed to improve results. Any semantic change requires a new benchmark
version and full re-run.
