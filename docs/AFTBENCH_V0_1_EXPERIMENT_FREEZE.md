# AFTBench v0.1 Experiment Freeze

**Freeze Date:** 2026-08-04T10:30:00+08:00  
**Freeze Identifier:** aftbench-v0.1-experiment-freeze  
**Purpose:** Freeze benchmark version for reproducible experiments

---

## 1. Source State

### Version Information
- **Source Tree Hash:** Computed at runtime (see source_state.json)
- **Git Commit:** Tracked at runtime
- **Git Diff Hash:** Tracked at runtime
- **Task Data Hash:** Tracked at runtime
- **Config Hash:** Tracked at runtime
- **Schema Hash:** Tracked at runtime

### Component Versions
- **Agent Version:** scripted-v1
- **Interface Version:** v0.1-experiment-freeze
- **Python Version:** 3.13.11
- **Pytest Version:** 9.1.1

---

## 2. Interface Definitions

### I0 - Legacy Baseline
- Synchronous request-response
- Verbose results
- No durable invocation identity
- No explicit unknown outcome
- No interface-level idempotency

### I1 - Schema-Normalized
- Input validation
- Structured result envelope
- Normalized error categories
- Stable resource references

### I2 - Discovery-Aware
- Compact metadata
- Selective schema retrieval
- Catalog caching
- Version/freshness metadata

### I3 - Lifecycle-Aware
- Invocation identity
- Authoritative status
- Legal lifecycle transitions
- Status query and resume

### I4 - Effect-Aware
- Effect class
- Resource scope
- Preconditions
- Object versions
- Idempotency semantics

### I5 - Full AFT
- Durable execution state
- Explicit unknown outcome
- Reconciliation
- Effect evidence
- Deterministic verification

### Ablation Variants
- I5-minus-selective-discovery
- I5-minus-resumable-invocation
- I5-minus-observable-execution
- I5-minus-structured-output
- I5-minus-side-effect-contract
- I5-minus-durable-state
- I5-minus-verification

---

## 3. World Versions

### Enterprise Records
- **Version:** v0.1
- **Features:** Record CRUD, version control, permissions, approval
- **Effects:** create_record, update_record, delete_record, read_record, list_records

### Long-Running Jobs
- **Version:** v0.1
- **Features:** Multi-stage jobs, interruption, resumption
- **Effects:** start_job, check_status, advance_job, cancel_job

### Large Catalog
- **Version:** v0.1
- **Features:** Catalog sizes 10-1000, selective retrieval
- **Effects:** get_catalog, search_catalog, get_schema, select_capability

### External Actions
- **Version:** v0.1
- **Features:** Message sending, event creation, side effects
- **Effects:** send_message, create_event, update_event, cancel_event

---

## 4. Task Schema Version

- **Schema Version:** v0.1
- **Schema File:** schemas/task.schema.json
- **Required Fields:** task_id, world, instruction, required_postconditions
- **Optional Fields:** agent_inputs, safety_predicates, effect_severity

---

## 5. Trace Schema Version

- **Schema Version:** v0.1
- **Schema File:** schemas/trace.schema.json
- **Required Fields:** run_id, task_id, event_type, timestamp
- **Optional Fields:** invocation_id, logical_effect_id, payload

---

## 6. Result Schema Version

- **Schema Version:** v0.1
- **Schema File:** schemas/result.schema.json
- **Required Fields:** run_id, task_id, world, interface_condition, seed
- **Metrics:** state_correct_completion, duplicate_effect, recovery_success, etc.

---

## 7. Fault Taxonomy

### Execution Faults (9 types)
1. failure_before_effect
2. lost_response_after_effect
3. partial_completion
4. interrupted_execution
5. stale_state
6. permission_drift
7. event_loss
8. handle_expiration
9. tool_evolution

### Workload Factors (separate from faults)
- catalog_size (10, 50, 200, 1000)
- tool_confusion (low, medium, high)
- entity_ambiguity (none, low, high)
- workflow_length (short, medium, long)
- effect_severity (reversible, irreversible)
- approval_required (true, false)

**Note:** tool_confusion and catalog_scale are currently in FaultType enum for backward compatibility but should be treated as workload factors in analysis.

---

## 8. Scripted Agent Policy

- **Version:** scripted-v1
- **Policy:** Deterministic, rule-based
- **No Oracle Access:** Cannot inspect hidden state
- **Recovery Behavior:** Interface-dependent

---

## 9. Known Limitations

1. **Metrics:** Some safety metrics still hard-coded (duplicate_effect, unintended_effect, etc.)
2. **Traces:** Missing granular lifecycle events (REQUEST_ACCEPTED, BACKEND_STARTED, etc.)
3. **Task Set:** Only ~12 tasks (requirement: 24+)
4. **Ablations:** Not yet implemented
5. **LLM Integration:** Not yet tested

---

## 10. Freeze Verification

To verify this freeze:
```bash
# Check source state
cat artifacts/<run>/source_state.json

# Verify interface version
grep -r "v0.1-experiment-freeze" src/

# Verify agent version
grep -r "scripted-v1" src/
```

---

## 11. Change Policy

After this freeze:
- No interface semantics changes without verified defect
- No task schema changes without version bump
- No trace schema changes without version bump
- All changes must be documented in CHANGELOG.md
- All changes must regenerate artifacts with new source state hash

---

**Freeze Approved:** 2026-08-04T10:30:00+08:00  
**Next Review:** After evidence generation complete
