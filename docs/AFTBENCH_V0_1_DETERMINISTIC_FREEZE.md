# AFTBench v0.1 Deterministic Experiment Freeze

**Freeze Date:** 2026-08-04T11:15:00+08:00  
**Freeze Identifier:** aftbench-v0.1-deterministic-freeze  
**Purpose:** Freeze deterministic experiment version for reproducible evidence

---

## Source State

### Version Information
- **Source Tree Hash:** c08a8c73c1f742de
- **Task Data Hash:** c34605470d28f857
- **Config Hash:** e8a9766e08c88da0
- **Schema Hash:** c7cdcea2b5c2b471
- **Git Commit:** No commits (dirty tree)
- **Git Diff Hash:** no_diff

### Component Versions
- **Agent Version:** scripted-v1
- **Interface Version:** v0.1-deterministic-freeze
- **Analysis Version:** v0.1
- **Python Version:** 3.13.11

---

## Interface Definitions

### I0 - Legacy Baseline
- Synchronous request-response
- Verbose results
- No durable invocation identity
- No explicit unknown outcome

### I1 - Schema-Normalized
- Input validation
- Structured result envelope
- Normalized error categories

### I2 - Discovery-Aware
- Compact metadata
- Selective schema retrieval
- Catalog caching

### I3 - Lifecycle-Aware
- Invocation identity
- Authoritative status
- Status query and resume

### I4 - Effect-Aware
- Effect class
- Resource scope
- Preconditions
- Idempotency semantics

### I5 - Full AFT
- Durable execution state
- Explicit unknown outcome
- Reconciliation
- Effect evidence
- Deterministic verification

### Ablation Variants (To Be Implemented)
- I5-minus-selective-discovery
- I5-minus-resumable-invocation
- I5-minus-observable-execution
- I5-minus-structured-output
- I5-minus-side-effect-contract
- I5-minus-durable-state
- I5-minus-verification

---

## Task Set

### Total Tasks: 32 (8 per world)

#### Enterprise Records (8 tasks)
- er_01_resolve_ambiguity (development)
- er_02_versioned_update (development)
- er_03_link_records (development)
- er_04_multi_attribute_resolution (development)
- er_05_noop_already_correct (held-out)
- er_06_forbidden_target_safety (development)
- er_07_reversible_compensation (held-out)
- er_08_stale_state_refresh (development)

#### Long-Running Jobs (8 tasks)
- lrj_01_multi_stage_report (development)
- lrj_02_interruption_recovery (development)
- lrj_03_event_loss (development)
- lrj_04_interruption_after_stage1 (development)
- lrj_05_event_loss_recovery (held-out)
- lrj_06_cancellation_before_commit (development)
- lrj_07_worker_restart_durable (held-out)
- lrj_08_artifact_verification (development)

#### Large Catalog (8 tasks)
- lc_01_basic_discovery (development)
- lc_02_selective_retrieval (development)
- lc_03_fallback_search (development)
- lc_04_catalog_1000 (development)
- lc_05_similar_tools_disambiguation (held-out)
- lc_06_stale_cache_refresh (development)
- lc_07_renamed_capability (held-out)
- lc_08_multi_tool_workflow (development)

#### External Actions (8 tasks)
- ea_01_create_event (development)
- ea_02_send_message (development)
- ea_03_update_event (development)
- ea_04_create_exactly_one_event (development)
- ea_05_wrong_recipient_safety (held-out)
- ea_06_cancel_reversible_action (development)
- ea_07_partial_multi_recipient (held-out)
- ea_08_unknown_outcome_reconciliation (development)

### Split Distribution
- **Development:** 20 tasks (62.5%)
- **Held-out:** 12 tasks (37.5%)

---

## Fault Taxonomy

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

### Workload Factors (6 types)
1. entity_ambiguity_level (none, low, high)
2. catalog_size (10, 50, 200, 1000)
3. tool_confusion_level (low, medium, high)
4. workflow_length (short, medium, long)
5. effect_severity (reversible, irreversible)
6. approval_required (true, false)

**Note:** tool_confusion and catalog_scale are workload factors, not execution faults.

---

## Scripted Agent Policy

- **Version:** scripted-v1
- **Policy:** Deterministic, rule-based
- **No Oracle Access:** Cannot inspect hidden state
- **Recovery Behavior:** Interface-dependent
- **Fixed Across Interfaces:** Yes

---

## Known Limitations

1. **Trace Events:** Missing granular lifecycle events (REQUEST_ACCEPTED, BACKEND_STARTED, etc.)
2. **Metrics:** Some timing metrics may be zero for fast synthetic operations
3. **Production-Like Backend:** Not yet implemented
4. **LLM Integration:** Not included in deterministic freeze

---

## Change Policy

After this freeze:
- No interface semantics changes without verified defect
- No task changes without version bump
- No scripted-agent policy changes unless genuine bug found
- All changes must be documented
- All changes must regenerate artifacts with new source state hash

---

**Freeze Approved:** 2026-08-04T11:15:00+08:00  
**Next Review:** After deterministic evidence complete
