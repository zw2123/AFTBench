# AFTBench Next-Step Plan: Deterministic Evidence v1.0

> **Project:** AFTBench  
> **Paper:** *Tools Without Hands: Behavioral Contracts and Controlled Evaluation for Agent-First Tooling*  
> **Current stage:** Phase 1–6, 8 completed; remaining phases pending micro-experiment gates  
> **Primary goal:** Complete and freeze the deterministic benchmark before any LLM experiments  
> **Last execution:** 2026-08-13 — 3 phases completed (git freeze, timing, outcome semantics, I3 regression)

---

# 0. Current Status

The repository has already made substantial progress:

- 411/411 tests reportedly pass;
- experiment ledger and consistency auditing exist;
- I3 lifecycle interface has been implemented;
- built-in verifiers have been added;
- safety-metric calibration infrastructure exists;
- the runner has been substantially rewritten;
- reconciliation, resume, retry, safe-abort logic, and derived metrics now live in the main execution path;
- source-state tracking is implemented;
- resume-from support exists;
- capability-aware agent routing exists.

However, the current deterministic evidence must be regenerated because the largest runner changes occurred after the previous 1,536-run evidence suite.

The goal of this phase is therefore:

> Freeze the corrected measurement stack, prove that every primitive is behaviorally activated, validate all core metrics with known-positive and known-negative cases, then regenerate canonical evidence.

---

# 1. Do Not Expand the Benchmark Yet

Do **not** prioritize:

- more task templates;
- more random seeds;
- more synthetic worlds;
- additional LLM models;
- API credential debugging;
- local-model deployment;
- full 1,536-run reruns before micro-validation passes;
- broad leaderboard-style comparisons.

The correct order is:

```text
Git Freeze
→ Metric Calibration
→ Primitive Manipulation Checks
→ I3/Resume Debug
→ Safe Outcome Semantics
→ Discovery Scaling
→ Timing Instrumentation
→ SQLite Validation
→ Micro Causal Experiments
→ Canonical Evidence v0.2
→ Statistical Freeze
→ AFTBench v1.0 Deterministic
→ LLM Experiments
```

---

# 2. Phase 1 — Git and Provenance Freeze

## Goal

Create a real publication-grade source baseline before generating new evidence.

The current repository reportedly has no commit history and many untracked files. This must be fixed first.

## Tasks

### 2.1 Audit `.gitignore`

Ensure at least the following are ignored:

```gitignore
.venv/
venv/
__pycache__/
*.pyc
.env
.env.*
*.log
artifacts/tmp/
artifacts/cache/
```

Review large generated artifacts before committing.

### 2.2 Create the first deterministic freeze commit

Recommended:

```bash
git add src tests configs data schemas scripts docs README.md pyproject.toml
git commit -m "Freeze AFTBench deterministic measurement stack v0.2"
```

Then record:

```bash
git rev-parse HEAD
git status --short
```

### 2.3 Update experiment manifests

Every new experiment must record:

```text
benchmark_version
git_commit
git_status
git_diff_hash
source_tree_hash
task_data_hash
config_hash
schema_hash
controller_version
interface_version
analysis_version
```

## Completion criteria

- [ ] Repository has a real commit.
- [ ] Untracked source files are not silently excluded from provenance.
- [ ] Dirty-state hash is recorded when applicable.
- [ ] New artifacts reference the exact source baseline.

---

# 3. Phase 2 — Rebuild the Experiment Ledger

## Goal

Eliminate all run-count, denominator, and report inconsistencies.

## Required script

Create or finalize:

```text
scripts/build_experiment_ledger.py
```

## Inputs

```text
configs/
results.csv
traces.jsonl
manifest.json
source_state.json
```

## Outputs

```text
artifacts/audit/experiment_ledger.csv
artifacts/audit/fault_funnel.csv
artifacts/audit/recovery_funnel.csv
artifacts/audit/consistency_report.md
```

## Required fields

```text
experiment_name
expected_runs
observed_runs
completed_runs
failed_runs
skipped_runs
internal_error_runs

runs_by_interface
runs_by_world
runs_by_task
runs_by_fault
runs_by_seed
```

For fault experiments:

```text
fault_configured
fault_reached
request_accepted
backend_started
effect_committed
response_generated
response_dropped
recovery_eligible
recovery_attempted
recovery_succeeded
```

## Completion criteria

- [ ] `expected_runs == observed_runs` or all discrepancies are explicitly classified.
- [ ] Every percentage in reports can be recomputed from ledger fields.
- [ ] No report uses a copied or manually entered denominator.
- [ ] No recovery rate uses all configured runs when only a subset is recovery-eligible.

---

# 4. Phase 3 — Safety Metric Calibration

## Goal

Prove that safety metrics can detect known violations and do not always return false.

Run explicit positive and negative calibration cases.

---

## 4.1 Duplicate-Effect Calibration

### Positive case

Force:

```text
commit #1
→ response lost
→ legacy retry
→ commit #2
```

Required identity:

```text
logical_effect_id = same
backend_operation_id = different
```

Expected:

```text
I0:
duplicate_effect = true
```

### Negative case

Use idempotency under I4/I5:

```text
same idempotency_key
second commit blocked/deduplicated
duplicate_effect = false
```

---

## 4.2 Unauthorized-Effect Calibration

Force:

```text
permission valid during planning
→ permission revoked
→ commit attempted
```

Expected weak behavior:

```text
unauthorized_effect = true
```

Expected strong behavior:

```text
safely_refused
unauthorized_effect = false
```

---

## 4.3 Unintended-Effect Calibration

Task:

```text
Send only to Alice.
```

Force:

```text
Alice + Bob receive the effect
```

Expected:

```text
unintended_effect = true
```

---

## 4.4 Residual-Effect Calibration

Scenario:

```text
A committed
B failed
C skipped
```

Without compensation:

```text
residual_effect = true
```

With compensation:

```text
A reverted
residual_effect = false
```

## Completion criteria

| Metric | Positive calibration | Negative calibration |
|---|---:|---:|
| duplicate_effect | detected | no false positive |
| unauthorized_effect | detected | no false positive |
| unintended_effect | detected | no false positive |
| residual_effect | detected | no false positive |

All four must pass before safety-related paper claims are allowed.

---

# 5. Phase 4 — Independent Manipulation Checks for All Seven Primitives

## Goal

Prove that each minus-one treatment changes the intended mechanism before measuring outcome differences.

Outcome differences must **not** be used as the manipulation check.

---

## 5.1 Selective Discovery

Record:

```text
schemas_visible
schemas_materialized
metadata_tokens
full_schema_tokens
fallback_search_called
```

Expected:

```text
I5-full:
compact metadata
few schemas materialized

I5-minus-discovery:
full catalog/schema exposure
```

---

## 5.2 Resumable Invocation

Required trace evidence:

```text
INTERRUPTED
INVOCATION_RESUMED
same invocation_id
```

For minus-resume:

```text
INTERRUPTED
CAPABILITY_UNAVAILABLE(resume)
```

---

## 5.3 Observable Execution

Force event loss.

Full treatment must show:

```text
STATUS_QUERY_USED
EVENT_RECONCILED
```

Minus-observable must show:

```text
CAPABILITY_UNAVAILABLE(observable_execution)
```

---

## 5.4 Structured Output

Record:

```text
parser_path
parse_error
repair_attempt
result_tokens
```

Expected:

```text
I5-full:
typed envelope
structured parser

I5-minus-structured-output:
free-form/legacy parser
```

---

## 5.5 Side-Effect Contract

Record:

```text
PRECONDITION_CHECKED
IDEMPOTENCY_CHECKED
AUTHORIZATION_CHECKED
```

Minus-effect must not silently perform these checks elsewhere.

---

## 5.6 Durable State

Force:

```text
process-local invocation state deleted
controller/runtime recreated
```

Expected:

```text
I5-full:
durable invocation state recovered

I5-minus-durable:
state unavailable
```

---

## 5.7 Verification

Construct:

```text
effect committed
agent initially believes failure/unknown
```

Expected full behavior:

```text
VERIFICATION_STARTED
POSTCONDITION_EVIDENCE
VERIFICATION_COMPLETED
terminal outcome corrected/resolved
```

Minus-verification:

```text
no verification evidence
```

## Required output

Create:

```text
artifacts/audit/manipulation_checks.csv
```

Columns:

```text
primitive
condition
task_id
fault
feature_exposed
feature_used
expected_behavior_observed
manipulation_pass
```

## Completion criteria

- [ ] 7/7 primitives have independent manipulation checks.
- [ ] Full treatment shows the target behavior.
- [ ] Minus-one treatment does not.
- [ ] Unrelated features remain unchanged.
- [ ] Primary analysis later uses only manipulation-valid pairs.

---

# 6. Phase 5 — Resolve the I3 / Resume Contradiction

## Goal

Explain why previous results showed:

```text
I3 recovery = 0%
I5 recovery = 100%
I5-minus-resume = 0%
```

despite I3 being lifecycle-aware.

## Micro experiment

Use one held-out long-running task such as:

```text
lrj_04_interruption_after_stage1
```

Fix:

```text
task
initial state
fault location
seed
controller version
```

Run:

```text
I3
I5
I5-minus-resume
I5-minus-durable
```

## Compare traces

Inspect:

```text
INVOCATION_CREATED
RUNNING
STAGE_COMPLETED
INTERRUPTED
INVOCATION_RESUMED
STATE_RESTORED
LOGICAL_REEXECUTION
TERMINATED
```

## Questions to answer

1. Does I3 receive an invocation handle?
2. Does I3 expose `resume()`?
3. Does the controller call it?
4. Is I3 invocation state destroyed by the fault?
5. Is I5 recovering through resume, durable state, or reconciliation?
6. Does `recovery_success` recognize I3 and I5 consistently?
7. Is I5 receiving hidden runtime support outside the interface abstraction?

## Desired semantic decomposition

```text
connection interruption
→ resumability may be sufficient

client restart
→ resumability + externally retained invocation state

worker restart
→ durable state may be necessary

process-local ledger loss
→ durable state should be necessary
```

## Completion criteria

- [ ] I3 behavior is fully explained.
- [ ] Resume and durable-state effects are separately testable.
- [ ] Recovery metric does not privilege one interface format.
- [ ] Regression tests preserve the corrected semantics.

---

# 7. Phase 6 — Fix Safe Abort / Refusal Outcome Semantics

## Goal

Make stale-state and permission-drift tasks evaluate policy compliance, not merely whether a mutation occurred.

## New terminal outcome taxonomy

Support:

```text
completed_as_requested
safely_aborted
safely_refused
safely_escalated
unsafe_committed
failed_unnecessarily
unresolved
```

## Example stale-state task

User intent:

```text
Update only if the record has not changed; otherwise abort.
```

Task manifest:

```yaml
acceptable_outcomes:
  - completed_as_requested
  - safely_aborted
```

## Example permission task

```yaml
acceptable_outcomes:
  - completed_as_requested
  - safely_refused
  - safely_escalated
```

## Required tests

```text
test_safe_abort_counts_as_correct_when_policy_requires_abort
test_permission_refusal_counts_as_correct
test_unnecessary_refusal_is_not_success
test_unsafe_commit_fails_safety
```

## Completion criteria

- [ ] I4/I5 can receive credit for safe abort/refusal.
- [ ] Weak interfaces can still be penalized for unsafe commit.
- [ ] Final-state correctness and policy correctness remain distinguishable.

---

# 8. Phase 7 — Complete the Discovery Frontier

## Goal

Turn the existing token-proxy result into a scale-sensitive discovery experiment.

## Required catalog sizes

```text
10
50
200
1000
```

## Required metrics by catalog size

```text
full_catalog_tokens
compact_metadata_tokens
schemas_loaded
top1_recall
top3_recall
top5_recall
fallback_rate
wrong_tool_rate
first_correct_action_latency
```

## Required table

| Catalog size | I1 tokens | I2 tokens | I1 top-1 | I2 top-1 | I2 fallback |
|---:|---:|---:|---:|---:|---:|
| 10 | | | | | |
| 50 | | | | | |
| 200 | | | | | |
| 1000 | | | | | |

## Validity checks

- [ ] Catalog size actually changes exposed tool surface.
- [ ] Distractor count increases with catalog size.
- [ ] Target capability ID is not leaked through hidden metadata.
- [ ] Recall is measured directly, not inferred from final task success.
- [ ] Fallback behavior is separately recorded.

## Completion criteria

The experiment can support:

> Selective discovery reduces context exposure while preserving acceptable recall across growing tool catalogs.

only if both exposure and recall are directly measured.

---

# 9. Phase 8 — Implement Real Timing Instrumentation

## Goal

Remove the final timing placeholder and make cost analysis usable.

## Current known TODO

```text
runtime_overhead_ms = 0
```

must be removed.

## Required implementation

Use:

```python
time.monotonic_ns()
```

Record:

```text
discovery_us
schema_loading_us
controller_us
interface_us
ledger_us
policy_us
backend_us
recovery_us
reconciliation_us
verification_us
total_us
```

## Synthetic structural overhead

Report real CPU-side microsecond measurements.

## Controlled latency sensitivity

Optionally support:

```yaml
latency_model:
  discovery_ms: 2
  backend_read_ms: 5
  backend_write_ms: 10
  remote_call_ms: 50
  ledger_ms: 1
  verification_ms: 3
```

Label this clearly as:

```text
controlled latency model
```

not real network latency.

## Completion criteria

- [ ] No placeholder timing values remain.
- [ ] Recovery timing is nonzero when recovery occurs.
- [ ] Verification timing is nonzero when verification occurs.
- [ ] Runtime overhead is decomposed by stage.
- [ ] Cost-frontier claims use matched workloads.

---

# 10. Phase 9 — Clean the SQLite Production-Like Backend

## Goal

Reduce implementation failures and make persistent-backend evidence interpretable.

## Step 10.1 Classify all current errors

Create:

```text
artifacts/sqlite/sqlite_error_breakdown.csv
```

Categories:

```text
unsupported_operation
wrong_capability
invalid_arguments
task_adapter_error
fault_not_reached
backend_error
verification_error
expected_operational_failure
true_agent_failure
```

## Step 10.2 Fix implementation errors

Priority:

1. unsupported operations;
2. wrong capability mapping;
3. missing parameters;
4. task-adapter errors;
5. verifier mismatch.

## Target

```text
unexpected implementation error rate < 5%
```

Expected operational failures may remain.

## Step 10.3 Run only two core replications

### A. Exact-once external effect

```text
I0
I4
I5
```

Fault:

```text
commit
→ response lost
```

Measure:

```text
duplicate_effect
unknown_outcome
reconciliation
```

### B. Stale update

```text
I1
I4
I5
```

Scenario:

```text
read v1
external update → v2
write expected v1
```

Measure:

```text
unsafe_overwrite
safely_aborted
```

## Completion criteria

- [ ] Commit and response delivery are independently observable.
- [ ] ITT analysis includes every planned run.
- [ ] Unexpected implementation errors <5%.
- [ ] Results are stratified by task and fault eligibility.
- [ ] Synthetic and SQLite findings can be compared on semantically matched operations.

---

# 11. Phase 10 — Run Four Micro Causal Experiments

Do not immediately rerun the full evidence suite.

## M1 — Resume

```text
1–2 held-out long-running tasks
2 fault locations
2 seeds
I3
I5
I5-minus-resume
I5-minus-durable
```

Primary metrics:

```text
resume_success
work_preserved
stages_repeated
logical_reexecution
```

## M2 — Post-Commit Uncertainty

```text
1–2 exact-once tasks
2 seeds
I3
I4
I5
I5-minus-effect
I5-minus-verification
```

Primary metrics:

```text
duplicate_effect
unknown_outcome
idempotent_retry
reconciliation
verification
```

## M3 — Stale State / Permission

```text
2 policy-sensitive tasks
2 seeds
I1
I3
I4
I5
I5-minus-effect
```

Primary outcomes:

```text
completed_as_requested
safely_aborted
safely_refused
unsafe_committed
failed_unnecessarily
```

## M4 — Discovery

```text
2 held-out discovery tasks
catalog sizes: 10 / 100 / 1000
2 seeds
I1
I2
I5
I5-minus-discovery
```

Primary metrics:

```text
catalog_tokens
schema_tokens
top1_recall
top3_recall
fallback_rate
```

## Micro-experiment acceptance

Every micro experiment must satisfy:

- [ ] manipulation check passes;
- [ ] fault is actually reached;
- [ ] task oracle is correct;
- [ ] primary metric activates;
- [ ] matched pairs are generated;
- [ ] no internal implementation error dominates the result.

Only after these pass should the full canonical suite be rerun.

---

# 12. Phase 11 — Canonical Evidence v0.2

Create a fresh artifact root:

```text
artifacts/evidence_v02/
```

Do not overwrite prior evidence.

## Recommended design

Use mechanism-targeted experiments, not all primitives × all worlds × all faults.

| Primitive | Primary workload |
|---|---|
| Selective Discovery | Large Catalog |
| Resumable Invocation | Long-Running Jobs |
| Observable Execution | Event Loss |
| Structured Output | Parsing / Result Interpretation |
| Side-Effect Contract | Post-Commit / Stale / Permission |
| Durable State | Process-State Loss |
| Verification | Unknown Outcome |

## Primary endpoints

### Discovery

```text
context exposure
tool recall
```

### Resume

```text
work preserved
recovery success
```

### Observable Execution

```text
event-loss recovery
poll/query count
```

### Structured Output

```text
parse failures
repair turns
result context
```

### Side-Effect Contract

```text
duplicate effects
unsafe commits
unauthorized effects
```

### Durable State

```text
recovery after process-local state loss
```

### Verification

```text
false success
false failure
unknown-outcome resolution
```

Binary `state_correct_completion` remains useful, but must not be the only primary endpoint.

---

# 13. Phase 12 — Freeze the Statistical Plan

Define primary hypotheses before looking at the new full evidence results.

## H1 — Discovery

```text
Selective discovery reduces tool-context exposure
without unacceptable recall loss.
```

## H2 — Resume

```text
Resumable invocation improves recovery
under transient interruption.
```

## H3 — Durable State

```text
Durable state improves recovery
under process-local state loss.
```

## H4 — Effect Contract

```text
Effect-aware contracts reduce unsafe external effects.
```

## H5 — Verification

```text
Verification reduces false success/failure
and unresolved outcomes.
```

## Secondary / exploratory

- observable execution;
- structured output;
- total state correctness;
- tool calls;
- compensation;
- recovery latency;
- policy overhead.

## Multiple-comparison control

Primary hypotheses:

```text
Holm correction
```

Exploratory analyses:

```text
Benjamini–Hochberg FDR
```

## Pair keys

Use:

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

## Required statistics

For each primary contrast:

```text
valid_pairs
missing_pairs
treatment_mean
control_mean
paired_difference
paired_median_difference
win_tie_loss
task_clustered_95pct_CI
adjusted_p_value
```

Never use unmatched overall interface rankings as causal evidence.

---

# 14. Deterministic v1.0 Completion Criteria

AFTBench deterministic evidence is considered complete only when all sections below pass.

## 14.1 Provenance

- [ ] Real Git commit exists.
- [ ] Every artifact points to source hash.
- [ ] Dirty-state changes are captured.
- [ ] No stale artifact is mixed with new evidence.

## 14.2 Experiment ledger

- [ ] Expected runs equal observed runs or discrepancies are classified.
- [ ] Every report denominator comes from the ledger.
- [ ] Fault and recovery funnels are complete.
- [ ] No manual run count remains.

## 14.3 Metric calibration

- [ ] Duplicate-effect positive/negative calibration passes.
- [ ] Unauthorized-effect positive/negative calibration passes.
- [ ] Unintended-effect positive/negative calibration passes.
- [ ] Residual-effect positive/negative calibration passes.

## 14.4 Manipulation validity

- [ ] 7/7 primitive manipulation checks pass.
- [ ] Removed primitive is behaviorally unavailable.
- [ ] Unrelated primitives remain active.
- [ ] Primary analysis uses manipulation-valid pairs only.

## 14.5 Outcome semantics

- [ ] Safe abort is correctly scored.
- [ ] Safe refusal is correctly scored.
- [ ] Unsafe commit is separately identified.
- [ ] False success/failure are measurable.

## 14.6 Discovery validity

- [ ] Context exposure scales with catalog size.
- [ ] Top-k recall is measured directly.
- [ ] Fallback is measured directly.
- [ ] 1000-tool result is reproducible.

## 14.7 Recovery validity

- [ ] Fault eligibility denominator is correct.
- [ ] Resume is separated from restart.
- [ ] Process-state loss is separated from ordinary interruption.
- [ ] I3/I5 recovery semantics are explained.

## 14.8 Timing validity

- [ ] No timing placeholders remain.
- [ ] High-resolution monotonic timing is used.
- [ ] Recovery/verification timing is nonzero when applicable.
- [ ] Runtime overhead is stage-decomposed.

## 14.9 SQLite validity

- [ ] Unexpected implementation error <5%.
- [ ] All error runs are classified.
- [ ] ITT analysis includes all planned runs.
- [ ] Post-commit and stale-state replications use matched comparisons.

## 14.10 Statistical validity

- [ ] Primary hypotheses frozen before full rerun.
- [ ] Pairing includes source/config/controller hashes.
- [ ] Task-clustered intervals reported.
- [ ] Multiple comparisons corrected.
- [ ] Effect size and interval both reported.
- [ ] No unmatched aggregate becomes a headline claim.

## 14.11 Paper validity

- [ ] Every number points to a current artifact.
- [ ] Every figure points to a manifest.
- [ ] Unsupported claims are downgraded.
- [ ] Scripted-agent limitation is explicit.
- [ ] No LLM generalization is implied.
- [ ] Results and Limitations are consistent.

---

# 15. Final Freeze

After all deterministic v1.0 criteria pass:

```bash
git add .
git commit -m "Freeze AFTBench deterministic evidence v1.0"
```

Create:

```text
docs/AFTBENCH_V1_0_DETERMINISTIC_FREEZE.md
artifacts/evidence_v10/FINAL_EVIDENCE_REPORT.md
```

Then do **not** change benchmark semantics during the LLM experiment phase.

Future LLMs become an experimental factor, not a reason to rewrite the benchmark.

---

# 16. Only After v1.0: Begin LLM Experiments

LLM experiments remain out of scope for the current phase.

After deterministic freeze, recommended model set:

```text
Qwen 3.7 Plus
DeepSeek V4 Pro
GPT-5.6 Sol
```

Use only a targeted held-out experiment matrix, not the full synthetic Cartesian product.

The later LLM stage should study:

```text
model effect
interface effect
model × interface interaction
```

---

# 17. Recommended 4-Hour Execution Schedule

If assigning the next task to Qwen/Codex:

| Time | Work |
|---|---|
| 0:00–0:20 | Git freeze + provenance verification |
| 0:20–0:50 | Safety metric calibration |
| 0:50–1:25 | Seven independent manipulation checks |
| 1:25–1:50 | I3/resume contradiction debugging |
| 1:50–2:15 | Safe abort/refusal semantics |
| 2:15–2:40 | Discovery scaling + recall |
| 2:40–3:00 | Timing instrumentation |
| 3:00–3:25 | SQLite error classification/fixes |
| 3:25–3:45 | Four micro causal experiments |
| 3:45–4:00 | Micro evidence acceptance + report |

Do not run the full canonical suite inside this 4-hour pass unless all micro gates pass early.

---

# 18. Final Output Expected from the Next Execution

The final report should look like this:

```text
Git provenance: PASS
Experiment ledger: PASS
Run-count mismatches: 0
Stale artifacts in current reports: 0

Safety calibration:
duplicate: PASS
unauthorized: PASS
unintended: PASS
residual: PASS

Primitive manipulation:
7 / 7 PASS

I3/resume semantics:
explained: YES

Safe outcome semantics:
safe abort: PASS
safe refusal: PASS

Discovery:
catalog sizes tested: 10 / 50 / 200 / 1000
context scaling: PASS
top-k recall measured: YES
fallback measured: YES

Timing:
placeholder values: 0
stage breakdown: PASS

SQLite:
unexpected implementation error: <5%
post-commit replication: PASS
stale-state replication: PASS

Micro causal experiments:
Resume: valid
Post-commit: valid
Stale/permission: valid
Discovery: valid

Ready for canonical evidence v0.2: YES/NO
```

This report is far more valuable than “thousands of runs completed.”

---

# 19. One-Sentence Objective

The next phase is complete only when:

> Every observed interface effect can be traced to an independently verified primitive manipulation, measured with a calibrated metric, under a matched fault/task pair, with a reproducible source and artifact lineage.
