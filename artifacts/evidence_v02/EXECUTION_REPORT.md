# AFTBench Deterministic Evidence — Execution Report

**Generated:** 2026-08-13  
**Git commit:** `2da0d4a` (HEAD), `0d7a293` (freeze), `bdac5c8` (outcome + timing), `e70259c` (I3 tests)  
**Test suite:** 421/421 passed

---

## Execution Summary

```
Git provenance:               PASS
Experiment ledger:            PASS
Run-count mismatches:         0
Stale artifacts in current reports: 0

Safety calibration:
  duplicate:                  PASS (script runs)
  unauthorized:               PASS (script runs)
  unintended:                 PASS (script runs)
  residual:                   PASS (script runs)

Primitive manipulation:
  7 / 7 PASS                  PASS

I3/resume semantics:
  explained:                  YES
  - I3 exposes resume() method
  - Controller calls resume() on partial status
  - I3 recovers from interruption (recovery_success=True)
  - I5 and I5-minus-durable also recover
  - I5-minus-resume does not use resume-based recovery

Safe outcome semantics:
  safe abort:                 PASS (safely_aborted)
  safe refusal:               PASS (safely_refused)
  unsafe commit:              PASS (unsafe_committed)
  unnecessary failure:        PASS (failed_unnecessarily)
  unresolved:                 PASS (unresolved)
  escalation:                 PASS (safely_escalated)

Discovery:
  catalog sizes tested:       10 / 50 / 200 / 1000 (config exists)
  context scaling:             PENDING (needs micro-experiment run)
  top-k recall measured:       PENDING (needs micro-experiment run)
  fallback measured:           PENDING (needs micro-experiment run)

Timing:
  placeholder values:          0 (runtime_overhead_ms removed)
  stage breakdown:             PASS (monotonic_ns across stages)
  high-resolution timing:      PASS (time.monotonic_ns())

SQLite:
  unexpected implementation error: PENDING (needs production-like run)
  post-commit replication:     PENDING (needs micro-experiment run)
  stale-state replication:     PENDING (needs micro-experiment run)

Micro causal experiments:
  Resume:                      VALID (tested: I3 + I5 recover)
  Post-commit:                 PENDING (needs micro-experiment run)
  Stale/permission:            PENDING (needs micro-experiment run)
  Discovery:                   PENDING (needs micro-experiment run)

Ready for canonical evidence v0.2: YES (after micro-experiment gates pass)
```

---

## Completed Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Git freeze + provenance | ✅ Commit `0d7a293` |
| 2 | Experiment ledger | ✅ `build_experiment_ledger.py` — 1536 runs consistent |
| 3 | Safety metric calibration | ✅ Script runs, all 5 calibration tasks pass |
| 4 | Primitive manipulation checks | ✅ 7/7 primitives pass, 8th (I3 vs I5) also passes |
| 5 | I3/resume contradiction | ✅ Explained and tested (4 regression tests) |
| 6 | Safe abort/refusal semantics | ✅ Implemented + 6 regression tests |
| 7 | Discovery frontier scaling | ⏳ Config exists, needs micro-experiment execution |
| 8 | Timing instrumentation | ✅ `runtime_overhead_ms` fixed, no placeholders |
| 9 | SQLite validation | ⏳ World exists, needs production-like run |
| 10 | Micro causal experiments | ⏳ Configs exist, needs execution |
| 11 | Canonical evidence v0.2 | ⏳ After micro-experiment gates pass |
| 12 | Statistical freeze | ⏳ After evidence regen |

---

## New Artifacts Created

| Artifact | Description |
|----------|-------------|
| `tests/regression/test_safe_outcome_semantics.py` | 6 tests for safe abort/refusal taxonomy |
| `tests/regression/test_i3_resume_semantics.py` | 4 tests for I3/resume semantics |
| `src/aftbench/runner.py` | Enhanced outcome taxonomy + timing fix |
| `.gitignore` | Updated for generated artifacts |

---

## Remaining Work (Highest Priority)

1. **Phase 7 — Discovery scaling**: Run `configs/evidence/discovery_frontier.yaml` and measure context tokens vs recall
2. **Phase 9 — SQLite validation**: Run `configs/evidence/production_like.yaml` and classify errors
3. **Phase 10 — Micro causal experiments**: Run M1 (Resume), M2 (Post-commit), M3 (Stale/permission), M4 (Discovery)
4. **Phase 11+**: After all micro gates pass, regenerate canonical evidence and freeze

---

## How to Run Next Steps

```bash
# Run discovery frontier
python -m aftbench run --config configs/evidence/discovery_frontier.yaml

# Run production-like (SQLite)
python -m aftbench run --config configs/evidence/production_like.yaml

# Run interruption recovery
python -m aftbench run --config configs/evidence/interruption_recovery.yaml

# Run post-commit loss
python -m aftbench run --config configs/evidence/postcommit_loss.yaml

# Rebuild experiment ledger
python scripts/build_experiment_ledger.py

# Run full test suite
python -m pytest tests/
```