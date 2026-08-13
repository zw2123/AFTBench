# AFTBench Canonical Evidence v0.2 — Report

**Generated:** 2026-08-13 (updated with SAP v1.1 inference + H5 workload)
**Source baseline:** commit `a04f4fb` (v0.2 measurement-validity fixes)
**Test suite:** 421/421 passed
**Evidence root:** `artifacts/evidence_v02/`
**Pre-registered plan:** `docs/STATISTICAL_ANALYSIS_PLAN_V1.md` (v1.1)

---

## 1. Execution Summary

| Gate | Status |
|------|--------|
| Git provenance recorded | PASS (git_commit, source hashes in every manifest) |
| Experiment ledger consistent | PASS (`artifacts/audit_v02/`) |
| Run-count mismatches | 0 (1032 runs, all expected) |
| Trace/results cross-validation | PASS |
| Smoke profile | 72 runs OK |
| Test suite | 421/421 |

## 2. Pre-registered Contrasts (SAP v1.1)

Matched task × seed pairs; direction-aware W/T/L; paired sign-flip
permutation p (10,000 perms); task-clustered bootstrap 95% CI; Holm
correction across the 7 primary contrasts; H1b one-sided non-inferiority
with frozen margin δ = 0.10.

| Contrast | Direction | Pairs | T mean | C mean | Util diff | W/T/L | CI95 | raw p | Holm p |
|----------|-----------|------:|-------:|-------:|----------:|-------|------|------:|-------:|
| H1a context exposure (I2 vs I1) | lower | 24 | 49.6 | 4062.8 | +4013.2 | 24/0/0 | [705, 8395] | 0.0001 | **0.0007** |
| H1b recall (I2 vs I1) | higher | 24 | 1.00 | 0.917 | +0.083 | 2/22/0 | [0, 0.167] | 0.499 | 0.499 |
| H2 recovery (I5 vs minus-resume) | higher | 24 | 1.00 | 0.00 | +1.00 | 24/0/0 | [1.0, 1.0] | 0.0001 | **0.0006** |
| H3 recovery (I5 vs minus-durable) | higher | 24 | 1.00 | 0.00 | +1.00 | 24/0/0 | [1.0, 1.0] | 0.0001 | **0.0005** |
| H4a duplicates (I4 vs I0) | lower | 24 | 0.00 | 0.75 | +0.75 | 18/6/0 | [0.375, 1.0] | 0.0001 | **0.0004** |
| H4b unsafe commits (I5 vs I1) | lower | 24 | 0.00 | 0.625 | +0.625 | 15/9/0 | [0.25, 0.875] | 0.0003 | **0.0006** |
| H5 incorrect claims (I5 vs minus-verification) | lower | 48 | 0.00 | 1.00 | +1.00 | 48/0/0 | [1.0, 1.0] | 0.0001 | **0.0003** |

**H1b non-inferiority p = 0.0001** (H0: recall loss ≥ 0.10 rejected).

Interpretation:

- **H1a supported**: selective discovery cuts context exposure by ~98%
  (49.6 vs 4062.8 tokens) — 24/24 pairs favor I2, CI excludes 0.
- **H1b non-inferior**: recall 24/24 vs 22/24 — no unacceptable recall
  loss at the frozen margin (the two I1 misses are keyword-noise selections
  over the full catalog).
- **H2 supported**: resumable invocation recovers 24/24 interrupted runs;
  minus-resume fails 24/24 (24/0/0, Holm p = 0.0006).
- **H3 supported** (ordinary interruption): durable-state I5 recovers 24/24;
  minus-durable fails 24/24. Process-state-loss durability is covered by
  M1 + regression tests.
- **H4a supported**: I4's idempotency contract eliminates duplicates
  (0/24 vs 18/24 for I0; 18/6/0, Holm p = 0.0004).
- **H4b supported**: effect contracts reduce stale-overwrite unsafe
  commits from 62.5% (I1) to 0 (I5); 15/9/0, Holm p = 0.0006.
- **H5 supported (new)**: under the false-outcome workload, verification
  corrects 100% of false terminal beliefs — I5 0/48 incorrect claims vs
  I5-minus-verification 48/48 and I4 48/48 (48/0/0, Holm p = 0.0003).

## 3. H5 False-Outcome Workload

Config: `configs/evidence/verification.yaml` — external_actions world,
I4 / I5 / I5-minus-verification, faults `false_success` /
`false_failure`, 8 task clusters × 3 seeds = 144 runs.

| Fault | Interface | Terminal claim | Actual effect | Incorrect claims |
|-------|-----------|----------------|---------------|-----------------:|
| false_success | I4 | success | absent | 24/24 |
| false_success | I5 | **failure (corrected)** | absent | 0/24 |
| false_success | minus-verification | success | absent | 24/24 |
| false_failure | I4 | failure | present | 24/24 |
| false_failure | I5 | **success (corrected)** | present | 0/24 |
| false_failure | minus-verification | failure | present | 24/24 |

Verification events (`VERIFICATION_STARTED` → `POSTCONDITION_EVIDENCE` →
`CLAIM_CORRECTED` → `VERIFICATION_COMPLETED`) are traced per run.

## 4. SQLite External Validity

| Interface | Duplicates | Unsafe commits | Correct |
|-----------|-----------:|---------------:|--------:|
| I0 | 9/36 | 3/36 | 36/36 |
| I1 | 9/36 | 3/36 | 36/36 |
| I4 | 0/36 | 0/36 | 36/36 |
| I5 | 0/36 | 0/36 | 36/36 |

Unexpected implementation error rate: **0.0%** (< 5% target).
Qualitative replication of the safety advantage across synthetic and
SQLite-backed environments.

## 5. Debugging Fixes Applied (v0.2)

The previous canonical evidence was invalidated by P0 measurement-validity
defects, all fixed (421/421 tests):

1. Task manifests: real parameters + structured postconditions (were vacuous).
2. `build_params` unwraps `input_schema` (params were empty for I1-family).
3. Fault simulation wired into the run loop (stale read-before-write,
   permission role revocation, lost-response transport retry).
4. Fresh interface per run (I4/I5 idempotency state leaked across runs).
5. lrj `run_job` effect with real interrupt/resume re-execution.
6. Weak interfaces strip idempotency/version metadata; I4/I5 pass
   structured errors (version-refresh recovery).
7. Real unintended/unauthorized derived metrics (world effect/authorization
   logs).
8. large_catalog per-task sizing + target guarantee + `capability_selected`
   recall.
9. Traces truncated on fresh runs.
10. False-outcome faults (`false_success`, `false_failure`) + verification
    claim correction (H5).
11. M3 acceptance claim corrected (its own "unsafe_committed appears" check
    had FAILED; the mechanism is now active and verified).

## 6. Remaining Gaps (documented)

- H5-C partial-success variant (subset of effects reported as full success)
  not yet implemented.
- Process-state-loss durability (H3) rests on M1 + regression tests; the
  canonical interruption profile covers ordinary interruption only.
- Fault-eligibility is not enforced by the runner; non-compatible pairs run
  and are stratified in the ledger.
- Keyword-scripted agents occasionally mis-select over full catalogs
  (2/24 in H1) — scripted-agent limitation, not an interface effect.
- Observable-execution and structured-output remain secondary experiments
  (event-loss polling / parser repair workloads) — deferred.

## 7. Files

- `artifacts/evidence_v02/{discovery,resume,durable_state,effect_contract,verification,sqlite}/`
- `artifacts/evidence_v02/CANONICAL_CONTRASTS.{json,md}`
- `artifacts/audit_v02/{experiment_ledger.json,fault_funnel.csv,consistency_report.md}`
- `scripts/analyze_canonical_v02.py` (contrast + inference pipeline)
- `docs/STATISTICAL_ANALYSIS_PLAN_V1.md` (v1.1, frozen at `a04f4fb`)
