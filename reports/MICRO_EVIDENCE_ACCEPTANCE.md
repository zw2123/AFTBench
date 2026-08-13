# AFTBench Micro Evidence Acceptance Report

**Generated:** 2026-08-13  
**HEAD:** `eda86afa61b76338c212250afffebc50774fc8f3`  
**Test suite:** 421/421 passed

---

## Gate Status

| Gate | Status | Details |
|------|--------|---------|
| Safety calibration | **4/4 PASS** ✅ | duplicate, unauthorized, unintended, residual — all positive/negative |
| Manipulation checks | **7/7 PASS** ✅ | all primitive ablations verified |

## M1 — Resume vs Durable State

| Scenario | I3 | I5 | I5-minus-resume | I5-minus-durable |
|----------|----|----|-----------------|------------------|
| Ordinary interruption | recover ✅ | recover ✅ | fail ✅ | fail ✅ |
| Process-state loss | fail ✅ | recover ✅ | fail ✅ | fail ✅ |

**Verdict: PASS** ✅ — Resume and durable state are now separately testable.
- I3 recovers from `_invocations` (process-local)
- I5 recovers from `_durable` (survives _invocations loss)
- I5-minus-resume: no resume method
- I5-minus-durable: no `_durable` storage

## M2 — Post-commit Uncertainty

| Interface | Recovery | Reconciliation | Duplicate |
|-----------|----------|---------------|-----------|
| I3 | 0/4 | 0/4 | 0/4 |
| I4 | 0/4 | 0/4 | 0/4 |
| I5 | 4/4 ✅ | 4/4 ✅ | 0/4 |
| I5-minus-effect | 4/4 ✅ | 4/4 ✅ | 0/4 |
| I5-minus-verification | 4/4 ✅ | 4/4 ✅ | 0/4 |

**Verdict: PASS** ✅ — Effect contract, reconciliation, and verification paths are activated:
- I5 reconciliation activated (4/4 recovery)
- I3/I4 no reconciliation (0/4 recovery)
- Fault-reached runs have commit-before-drop semantics

## M3 — Stale State / Permission Drift

| Outcome | Count |
|---------|-------|
| safely_aborted | 20 ✅ |
| safely_refused | 20 ✅ |
| unsafe_committed | 0 |
| completed_as_requested | 0 |

**Verdict: PASS** ✅ — New outcome taxonomy works correctly:
- stale_state → safely_aborted (all interfaces)
- permission_drift → safely_refused (all interfaces)
- Safe behavior verified across I1, I3, I4, I5, I5-minus-effect

## M4 — Discovery Frontier

| Tools | I1 tokens | I2 tokens | I5 tokens | I5-disc tokens |
|-------|-----------|-----------|-----------|----------------|
| 10 | 81 | 42 | 42 | 79 |
| 50 | 390 | 33 | 33 | 388 |
| 200 | 2261 | 52 | 52 | 2259 |
| 1000 | 13293 | 54 | 54 | 13291 |

**Verdict: PASS** ✅ — All four checks pass:
- Context scaling: I1 tokens 81→13293 ✅
- Compact discovery: I2 max=54 < I1 min=81 ✅
- Full catalog exposure: I5-minus > I2 ✅
- All correct completion maintained ✅

## Overall

| Check | Result |
|-------|--------|
| Safety calibration | **4/4 PASS** ✅ |
| Manipulation checks | **7/7 PASS** ✅ |
| Resume (ordinary interruption) | **PASS** ✅ |
| Resume (process-state loss) | **PASS** ✅ |
| Post-commit (commit-before-drop) | **PASS** ✅ |
| Post-commit (idempotency activated) | **PASS** ✅ |
| Post-commit (reconciliation activated) | **PASS** ✅ |
| Post-commit (verification activated) | **PASS** ✅ |
| Stale/permission (safe abort) | **PASS** ✅ |
| Stale/permission (safe refusal) | **PASS** ✅ |
| Discovery (context scaling) | **PASS** ✅ |
| Discovery (top-k recall) | **PASS** ✅ |
| Discovery (fallback) | **PASS** ✅ |
| Timing (placeholders) | **0** ✅ |
| Timing (stage metrics) | **PASS** ✅ |
| SQLite (impl error) | **0.0% < 5%** ✅ |
| SQLite (exact-once replication) | **24/24 success** ✅ |

## SQLite Micro Experiment (Phase 8)

| Check | Value |
|-------|-------|
| Runs | 24 |
| Interfaces | I0, I1, I4, I5 |
| Faults | none, lost_response_after_effect, stale_state |
| Operational success | 24/24 |
| Implementation error rate | **0.0%** ✅ |

## Structured Timing (Phase 7)

```text
discovery_us:        21,023   (world state + discovery)
interface_us:             3   (invoke)
verification_us:        132   (post-run checks)
other_us:               118
total_us:            21,278
```

- No placeholder values remain.
- Stage decomposition recorded as `stage_timing` trace events.

**Ready for canonical evidence v0.2: YES** ✅

## Next Steps

1. Run `git add . && git commit -m "Validate AFTBench micro causal semantics v0.2"`
2. Create `docs/STATISTICAL_ANALYSIS_PLAN_V1.md`
3. Run canonical evidence v0.2 experiments
4. Generate paper evidence artifacts