# AFTBench Canonical Evidence v0.2 — Report

**Generated:** 2026-08-13
**Source baseline:** `37a3546` (HEAD) + debug fixes (this session)
**Test suite:** 421/421 passed
**Evidence root:** `artifacts/evidence_v02/`
**Pre-registered plan:** `docs/STATISTICAL_ANALYSIS_PLAN_V1.md` (frozen at `d7fcf84`)

---

## 1. Execution Summary

| Gate | Status |
|------|--------|
| Git provenance recorded | PASS (git_commit, source hashes in every manifest) |
| Experiment ledger consistent | PASS (`artifacts/audit_v02/`) |
| Run-count mismatches | 0 (96+120+120+168+240+168+144 = 1056 rows, all expected) |
| Trace/results cross-validation | PASS (every run_id matches) |
| Smoke profile | 72 runs OK |
| Test suite | 421/421 |

## 2. Pre-registered Contrasts (task × seed matched pairs)

Full detail: `artifacts/evidence_v02/CANONICAL_CONTRASTS.json`

| Contrast | Valid pairs | Treatment | Control | Paired diff | W/T/L |
|----------|------------:|----------:|--------:|------------:|-------|
| H1 context exposure (I2 vs I1) | 24 | 49.6 tok | 4062.8 tok | **−4013.2 tok** | 0/0/24 |
| H1 recall (I2 vs I1) | 24 | 24/24 | 22/24 | +0.083 | 2/22/0 |
| H2 recovery (I5 vs I5-minus-resume) | 24 | 1.00 | 0.00 | **+1.00** | 24/0/0 |
| H3 recovery (I5 vs I5-minus-durable) | 24 | 1.00 | 0.00 | **+1.00** | 24/0/0 |
| H4 duplicates (I4 vs I0) | 24 | 0.00 | 0.75 | **−0.75** | 0/6/18 |
| H4b unsafe commits (I1 vs I5) | 24 | 0.625 | 0.00 | **+0.625** | 15/9/0 |
| H5 correctness (I5 vs I5-minus-verification) | 24 | 1.00 | 1.00 | 0.00 | 0/24/0 |

Interpretation:

- **H1 supported**: selective discovery cuts tool-context exposure by ~98%
  (49.6 vs 4062.8 tokens) with no recall loss (24/24 vs 22/24; the two I1
  misses are keyword-noise selections over the full catalog, a real
  limitation of the scripted agent under full exposure).
- **H2 supported**: resumable invocation recovers 24/24 interrupted runs;
  minus-resume fails 24/24.
- **H3 supported** (ordinary interruption): durable-state I5 recovers 24/24;
  I5-minus-durable fails 24/24. Process-state-loss durability is covered by
  the M1 micro experiment (`m1_resume/`) and regression tests.
- **H4 supported**: I4's idempotency contract eliminates duplicates
  (0/24 vs 18/24 for I0); I5 eliminates them via reconciliation. Effect
  contracts reduce stale-overwrite unsafe commits from 62.5% (I1) to 0 (I5).
- **H5 not yet activated**: I5 and I5-minus-verification show identical
  outcomes in the canonical post-commit workload. Verification events
  (`VERIFICATION_STARTED` / `POSTCONDITION_EVIDENCE` / `VERIFICATION_COMPLETED`)
  are instrumented, but no canonical workload currently produces a false
  claim under I5-family interfaces (reconciliation already resolves unknown
  outcomes). A dedicated false-success workload (entity-ambiguity after
  commit) is deferred to the next iteration.

## 3. SQLite External Validity

| Interface | Duplicates | Unsafe commits | Correct |
|-----------|-----------:|---------------:|--------:|
| I0 | 9/36 | 3/36 | 36/36 |
| I1 | 9/36 | 3/36 | 36/36 |
| I4 | 0/36 | 0/36 | 36/36 |
| I5 | 0/36 | 0/36 | 36/36 |

Unexpected implementation error rate: **0.0%** (< 5% target).

## 4. Debugging Fixes Applied This Session

The previous canonical evidence was invalidated by several defects, all now
fixed (421/421 tests):

1. **Task manifests** (`data/tasks/*.yaml`): er/ea/lrj/lc tasks had no
   `parameters` and string-format postconditions that no world verifier
   could evaluate (postcondition checks passed vacuously). All tasks now
   carry real parameters and structured dict postconditions.
2. **`build_params` schema mismatch**: agents read `schema["properties"]`
   but I1-family `get_schema` wraps it in `input_schema` → all params were
   empty (junk effects everywhere). Fixed in both agents.
3. **Fault simulation was dead code**: `FaultInjector` was never called.
   The runner now simulates stale-state (read → external update → write),
   permission drift (role revocation), and lost-response (transport retry
   with shared logical effect id).
4. **Weak/strong interface contracts**: I0/I1/I3 now strip idempotency keys
   and version metadata (legacy behavior); I4/I5 pass structured errors
   (`error_code`, `current_version`) enabling version-refresh recovery.
5. **Interface state leaked across runs**: interface instances were shared
   across fault/seed iterations; I4/I5 idempotency caches produced phantom
   successes. Fresh interface per run.
6. **Traces appended across re-runs** → stale trace lines mixed with fresh
   evidence. Fresh runs now truncate the trace file (resume runs keep it).
7. **Resume was a no-op**: I3/I5 `resume()` flipped a flag without
   re-executing; interrupted jobs were never completed. `run_job` effect +
   resume re-drives the job to completion.
8. **large_catalog world**: catalog size now follows the task manifest;
   task targets are guaranteed present (`ensure_capability`); recall is
   measured via `capability_selected` postconditions.
9. **Derived metrics**: `unintended_effect`/`unauthorized_effect` were
   placeholders; now computed from world effect/authorization logs.
10. **M3 acceptance correction**: the M3 micro report claimed
    "unsafe_committed appears: PASS", but `m3_results.json` shows that check
    FAILED (0 unsafe outcomes) — the stale-state mechanism was not active.
    This is now fixed and the canonical stale-permission evidence shows
    15–18/24 unsafe commits for weak interfaces and 0/24 for I4/I5.

## 5. Remaining Gaps (documented, not hidden)

- H5 verification outcome contrast needs a dedicated false-success workload.
- Process-state-loss durability (H3) relies on the M1 micro experiment; the
  canonical interruption profile covers ordinary interruption only.
- Fault-eligibility is not enforced by the runner: non-compatible
  task × fault pairs run and are stratified in the ledger instead.
- Keyword-scripted agents occasionally mis-select over full catalogs
  (2/24 in H1) — a scripted-agent limitation, not an interface effect.

## 6. Files

- `artifacts/evidence_v02/{discovery,resume,durable_state,effect_contract,verification,sqlite}/`
- `artifacts/evidence_v02/CANONICAL_CONTRASTS.{json,md}`
- `artifacts/audit_v02/{experiment_ledger.json,fault_funnel.csv,consistency_report.md}`
- `scripts/analyze_canonical_v02.py` (contrast pipeline)
