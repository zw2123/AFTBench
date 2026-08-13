# Paper Requirements Traceability

This document maps each paper requirement to its implementation, test, and benchmark artifact.

## Terminology Check

| Paper Term | Code Term | Status |
|-----------|-----------|--------|
| callability | agent-operability | ALIGNED |
| selective discovery | selective_discovery (I2) | IMPLEMENTED |
| resumable invocation | resumable_invocation (I3) | IMPLEMENTED |
| observable execution | observable_execution (I3) | IMPLEMENTED |
| minimal sufficient structured outputs | structured_result (I1+) | IMPLEMENTED |
| explicit side-effect contracts | effect_contract (I4) | IMPLEMENTED |
| recoverable execution state | durable_execution (I5) | IMPLEMENTED |
| unknown outcome | unknown_outcome (I5) | IMPLEMENTED |
| reconciliation | reconciliation (I5) | IMPLEMENTED |
| state-correct completion | state_correct_completion | IMPLEMENTED |

## Requirements Map

### R1: Agent-First Tooling Model
- **Paper Section**: Agent-First Tooling Model
- **Implementation**: `src/aftbench/interfaces/i5_full_aft.py`
- **Test**: `tests/integration/test_i5_contract.py`
- **Artifact**: Pilot results with I5 condition
- **Status**: IMPLEMENTED

### R2: AFT Compatibility Layer
- **Paper Section**: AFT: System Design
- **Implementation**: `src/aftbench/interfaces/base.py`, all interface files
- **Test**: `tests/integration/test_interface_parity.py`
- **Artifact**: Interface ladder comparison
- **Status**: IMPLEMENTED

### R3: AFTBench Benchmark
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/runner.py`, `src/aftbench/worlds/`
- **Test**: `tests/benchmark/test_smoke.py`
- **Artifact**: `artifacts/pilot/results.csv`
- **Status**: IMPLEMENTED

### R4: Interface Conditions I0–I5
- **Paper Section**: Experimental Setup
- **Implementation**: `src/aftbench/interfaces/i0_legacy.py` through `i5_full_aft.py`
- **Test**: `tests/integration/test_interface_ladder.py`
- **Artifact**: All interface conditions in results
- **Status**: IMPLEMENTED

### R5: Selective Discovery (Primitive)
- **Paper Section**: Agent-First Tooling Model / Primitives
- **Implementation**: `src/aftbench/interfaces/i2_discovery.py`
- **Test**: `tests/unit/test_selective_discovery.py`
- **Artifact**: Ablation: I5 vs no-discovery
- **Status**: IMPLEMENTED

### R6: Resumable Invocation (Primitive)
- **Paper Section**: Agent-First Tooling Model / Primitives
- **Implementation**: `src/aftbench/interfaces/i3_lifecycle.py`, `src/aftbench/contracts/lifecycle.py`
- **Test**: `tests/unit/test_lifecycle.py`, `tests/integration/test_resume.py`
- **Artifact**: Ablation: I5 vs no-lifecycle
- **Status**: IMPLEMENTED

### R7: Observable Execution (Primitive)
- **Paper Section**: Agent-First Tooling Model / Primitives
- **Implementation**: `src/aftbench/interfaces/i3_lifecycle.py`
- **Test**: `tests/unit/test_observable_execution.py`
- **Artifact**: Event sequence validation in traces
- **Status**: IMPLEMENTED

### R8: Minimal Sufficient Structured Outputs (Primitive)
- **Paper Section**: Agent-First Tooling Model / Primitives
- **Implementation**: `src/aftbench/contracts/result.py`, `src/aftbench/interfaces/i1_schema.py`
- **Test**: `tests/unit/test_structured_outputs.py`
- **Artifact**: Schema validation in results
- **Status**: IMPLEMENTED

### R9: Explicit Side-Effect Contracts (Primitive)
- **Paper Section**: Agent-First Tooling Model / Primitives
- **Implementation**: `src/aftbench/contracts/effects.py`, `src/aftbench/interfaces/i4_effect.py`
- **Test**: `tests/unit/test_effect_contracts.py`
- **Artifact**: Ablation: I5 vs no-effects
- **Status**: IMPLEMENTED

### R10: Recoverable Execution State (Primitive)
- **Paper Section**: Agent-First Tooling Model / Primitives
- **Implementation**: `src/aftbench/interfaces/i5_full_aft.py`
- **Test**: `tests/integration/test_durable_state.py`
- **Artifact**: Ablation: I5 vs no-durable-state
- **Status**: IMPLEMENTED

### R11: Enterprise Records World
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/worlds/enterprise_records.py`
- **Test**: `tests/integration/test_enterprise_records.py`
- **Artifact**: `data/tasks/enterprise_records.yaml`
- **Status**: IMPLEMENTED

### R12: Long-Running Jobs World
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/worlds/long_running_jobs.py`
- **Test**: `tests/integration/test_long_running_jobs.py`
- **Artifact**: `data/tasks/long_running_jobs.yaml`
- **Status**: IMPLEMENTED

### R13: Large Catalog World
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/worlds/large_catalog.py`
- **Test**: `tests/integration/test_large_catalog.py`
- **Artifact**: `data/tasks/large_catalog.yaml`
- **Status**: IMPLEMENTED

### R14: External Actions World
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/worlds/external_actions.py`
- **Test**: `tests/integration/test_external_actions.py`
- **Artifact**: `data/tasks/external_actions.yaml`
- **Status**: IMPLEMENTED

### R15: Fault Matrix (10 fault types)
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/faults/injector.py`
- **Test**: `tests/unit/test_fault_injection.py`
- **Artifact**: `data/faults/schedules.yaml`
- **Status**: IMPLEMENTED

### R16: Deterministic Scripted Agent
- **Paper Section**: Experimental Setup
- **Implementation**: `src/aftbench/agents/scripted.py`
- **Test**: `tests/unit/test_scripted_agent.py`
- **Artifact**: All pilot results (scripted)
- **Status**: IMPLEMENTED

### R17: Paired Statistical Analysis
- **Paper Section**: Experimental Setup
- **Implementation**: `src/aftbench/analysis/paired.py`, `src/aftbench/analysis/bootstrap.py`
- **Test**: `tests/unit/test_paired_analysis.py`
- **Artifact**: `artifacts/pilot/paired_summary.csv`
- **Status**: IMPLEMENTED

### R18: State-Based Verification
- **Paper Section**: AFTBench: Benchmark Design
- **Implementation**: `src/aftbench/verifiers/builtins.py`
- **Test**: `tests/unit/test_verifiers.py`
- **Artifact**: Verification results in traces
- **Status**: IMPLEMENTED

### R19: Paper-to-Code Traceability
- **Paper Section**: All
- **Implementation**: This document
- **Test**: `scripts/check_acceptance.py`
- **Artifact**: This file
- **Status**: IMPLEMENTED

## NOT YET EVIDENCED

| Claim | What's Needed |
|-------|--------------|
| I5 improves frontier LLM performance | Live LLM pilot with API credentials |
| Token reduction from selective discovery scales with catalog size | Full profile run with 1000-tool catalog |
| Recovery latency is acceptable for interactive use | Network-latency modeling |
| AFT layer overhead is < X% | Runtime overhead profiling at scale |
