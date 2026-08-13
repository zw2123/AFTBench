# Evidence Baseline Audit

**Audit Date:** 2026-08-04T10:18:35+08:00  
**Auditor:** Autonomous Mission  
**Purpose:** Verify current repository claims and artifact validity

---

## 1. Test State Verification

### Claimed State
- Tests: 352 passed, 0 failed
- Acceptance: 77/77 criteria met

### Observed State
```bash
$ python -m pytest -q
352 passed, 1 warning in 1.83s

$ python scripts/check_acceptance.py
Results: 77 passed, 0 failed
All acceptance criteria MET.
```

**Status:** ✓ **VALIDATED**

---

## 2. Artifact-Source Consistency

### Required Fields (per mission spec)
- [ ] git commit
- [ ] git status
- [ ] git diff hash
- [ ] source-tree hash
- [ ] task-data hash
- [ ] config hash
- [ ] schema hash
- [ ] agent/controller version
- [ ] interface implementation version
- [ ] timestamp

### Observed in artifacts/pilot/manifest.json
```json
{
  "config": {...},
  "n_results": 2376,
  "worlds": [...],
  "interfaces": [...],
  "fault_types": [...],
  "seeds": [...]
}
```

**Missing Fields:**
- ✗ git commit
- ✗ source-tree hash
- ✗ git diff hash
- ✗ task-data hash
- ✗ config hash
- ✗ schema hash
- ✗ agent version
- ✗ interface version
- ✗ timestamp (only implicit from file mtime)

**Status:** ✗ **INVALID_FOR_PAPER**

**Action Required:** Mark existing artifacts as `LEGACY_UNVERIFIED` and regenerate with source state tracking.

---

## 3. Critical Fault Trace Audit

### Requirement
Inspect at least five `lost_response_after_effect` traces. Each must prove:
1. REQUEST_ACCEPTED
2. BACKEND_STARTED
3. EFFECT_COMMITTED
4. RESPONSE_GENERATED
5. RESPONSE_DROPPED

In that order, with:
- invocation_id
- logical_effect_id
- backend_operation_id
- resource_id
- commit evidence

### Observed Trace Events
Current trace event types:
```
run_start
discovery
tool_selection
invocation_start
invocation_response
run_end
```

**Missing Events:**
- ✗ REQUEST_ACCEPTED
- ✗ BACKEND_STARTED
- ✗ EFFECT_COMMITTED (partially present in I5 interface)
- ✗ RESPONSE_GENERATED
- ✗ RESPONSE_DROPPED

**Status:** ✗ **PARTIALLY_VALIDATED**

**Issue:** Traces lack granular lifecycle events required for fault validation. I5 interface records `effect_committed` and `response_dropped` internally but these are not consistently emitted as trace events.

**Action Required:** Enhance trace emission to include all required lifecycle events.

---

## 4. Metric Provenance Audit

### Required Metrics (must be derived, not hard-coded)
- state_correct_completion
- duplicate_effect
- unintended_effect
- unauthorized_effect
- residual_effect
- recovery_success
- unknown_outcome_reconciled
- wall_clock_ms
- recovery_ms
- verification_ms

### Observed in runner.py
```python
# Lines 180-195
duplicate_effect = False
unintended_effect = False
unauthorized_effect = False
residual_effect = False
recovery_ms = 0
verification_ms = 0
runtime_overhead_ms = 0
```

**Status:** ✗ **INVALID_FOR_PAPER**

**Issue:** Core safety metrics are hard-coded constants, not derived from oracle state or trace evidence.

**Action Required:** Implement metric computation from:
- Oracle state diff for duplicate/unintended/unauthorized effects
- Trace timestamps for recovery_ms, verification_ms
- Compensation trace for residual_effect

---

## 5. Task Manifest Audit

### Current Task Count
```bash
$ find data/tasks -name "*.yaml" | wc -l
4
```

### Tasks per World
- enterprise_records: ~3 tasks
- long_running_jobs: ~3 tasks
- large_catalog: ~3 tasks
- external_actions: ~3 tasks

**Total:** ~12 tasks

**Status:** ✗ **INSUFFICIENT**

**Requirement:** Minimum 24 validated task instances (6 per world), target 40 (10 per world).

**Action Required:** Expand task set with parameterized instances and held-out split.

---

## 6. Taxonomy Audit

### Current Fault Types
```python
class FaultType(str, Enum):
    ENTITY_AMBIGUITY = "entity_ambiguity"
    FAILURE_BEFORE_EFFECT = "failure_before_effect"
    LOST_RESPONSE_AFTER_EFFECT = "lost_response_after_effect"
    PARTIAL_COMPLETION = "partial_completion"
    INTERRUPTED_EXECUTION = "interrupted_execution"
    STALE_STATE = "stale_state"
    PERMISSION_DRIFT = "permission_drift"
    EVENT_LOSS = "event_loss"
    HANDLE_EXPIRATION = "handle_expiration"
    TOOL_EVOLUTION = "tool_evolution"
    TOOL_CONFUSION = "tool_confusion"
    CATALOG_SCALE = "catalog_scale"
```

**Issue:** `tool_confusion` and `catalog_scale` are workload factors, not execution faults.

**Status:** ✗ **TAXONOMY_MIXED**

**Action Required:** Separate:
- Execution faults (9 types)
- Workload factors (catalog_size, tool_confusion, entity_ambiguity, etc.)

---

## 7. Overall Assessment

| Component | Status | Action Required |
|-----------|--------|-----------------|
| Tests | ✓ VALIDATED | None |
| Acceptance | ✓ VALIDATED | None |
| Artifact-Source Consistency | ✗ INVALID | Add source state tracking |
| Fault Traces | ✗ PARTIAL | Add lifecycle events |
| Metric Provenance | ✗ INVALID | Derive from state/trace |
| Task Set | ✗ INSUFFICIENT | Expand to 24+ tasks |
| Taxonomy | ✗ MIXED | Separate faults/workload |

**Overall Status:** ✗ **INVALID_FOR_PAPER**

**Recommendation:** Existing artifacts cannot be used for paper claims. Must regenerate with:
1. Source state tracking
2. Enhanced trace events
3. Derived metrics
4. Expanded task set
5. Clean taxonomy

---

## 8. Next Actions

1. **Phase 1:** Freeze benchmark version with source state tracking
2. **Phase 2:** Clean taxonomy (separate faults from workload factors)
3. **Phase 3:** Expand task set to 24+ instances
4. **Phase 4:** Implement real ablations
5. **Phase 5:** Enhance trace events
6. **Phase 6:** Derive metrics from state/trace
7. **Phase 7:** Run canonical experiments
8. **Phase 8:** Generate paper artifacts

**Estimated Time:** 4-5 hours

---

**Audit Completed:** 2026-08-04T10:25:00+08:00  
**Next Review:** After Phase 1 completion
