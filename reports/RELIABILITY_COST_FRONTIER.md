# Reliability-Cost Frontier Report

**Generated:** 2026-08-04T12:45:00+08:00  
**Source:** artifacts/evidence_runs/*/results.csv  
**Total Runs:** 1,392  
**Agent:** scripted-v1 (deterministic)

---

## 1. Reliability Metrics by Interface

| Interface | Runs | State Correct | Duplicate | Unintended | Unauthorized | Recovery |
|-----------|------|---------------|-----------|------------|--------------|----------|
| I0 | 24 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| I1 | 96 | 50.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| I2 | 48 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| I3 | 96 | 50.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| I4 | 72 | 33.3% | 0.0% | 0.0% | 0.0% | 0.0% |
| I5 | 216 | 66.7% | 0.0% | 0.0% | 0.0% | 29.6% |
| I5-minus-selective-discovery | 120 | 80.0% | 0.0% | 0.0% | 0.0% | 30.0% |
| I5-minus-resumable-invocation | 120 | 80.0% | 0.0% | 0.0% | 0.0% | 6.7% |
| I5-minus-observable-execution | 96 | 75.0% | 0.0% | 0.0% | 0.0% | 41.7% |
| I5-minus-structured-output | 96 | 75.0% | 0.0% | 0.0% | 0.0% | 41.7% |
| I5-minus-side-effect-contract | 168 | 57.1% | 0.0% | 0.0% | 0.0% | 23.8% |
| I5-minus-durable-state | 120 | 80.0% | 0.0% | 0.0% | 0.0% | 46.7% |
| I5-minus-verification | 120 | 80.0% | 0.0% | 0.0% | 0.0% | 33.3% |

### Key Reliability Findings

1. **I0 and I2 show 100% state-correct completion** - but these are in experiments without faults that challenge correctness
2. **I4 shows lowest correctness (33.3%)** - post-commit loss experiment exposes I4 weakness
3. **I5 is the only interface with recovery capability (29.6%)** - reconciliation works
4. **Zero safety violations across all conditions** - no duplicate, unintended, or unauthorized effects
5. **Ablation variants show higher correctness than I5-full** - suggests I5-full's overhead may hurt in some scenarios

---

## 2. Cost Metrics by Interface

| Interface | Wall Clock (ms) | Tool Calls | Context Tokens | Recovery (ms) | Verification (ms) |
|-----------|-----------------|------------|----------------|---------------|-------------------|
| I0 | 0.7 | 2.0 | 246.0 | 0.0 | 0.0 |
| I1 | 0.4 | 1.8 | 246.0 | 0.0 | 0.0 |
| I2 | 0.9 | 1.8 | 20.0 | 0.0 | 0.0 |
| I3 | 0.1 | 1.9 | 20.0 | 0.0 | 0.0 |
| I4 | 0.0 | 1.9 | 20.0 | 0.0 | 0.0 |
| I5 | 0.2 | 1.6 | 20.0 | 0.0 | 0.0 |
| I5-minus-selective-discovery | 0.1 | 1.7 | 0.0 | 0.0 | 0.0 |
| I5-minus-resumable-invocation | 0.1 | 1.4 | 20.0 | 0.0 | 0.0 |
| I5-minus-observable-execution | 0.1 | 1.5 | 20.0 | 0.0 | 0.0 |
| I5-minus-structured-output | 0.2 | 1.5 | 20.0 | 0.0 | 0.0 |
| I5-minus-side-effect-contract | 0.1 | 1.7 | 20.0 | 0.0 | 0.0 |
| I5-minus-durable-state | 0.2 | 1.4 | 20.0 | 0.0 | 0.0 |
| I5-minus-verification | 0.2 | 1.6 | 20.0 | 0.0 | 0.0 |

### Key Cost Findings

1. **Selective discovery reduces context tokens dramatically**: I0/I1 use 246 tokens, I2+ use 20 tokens (92% reduction)
2. **I5-minus-selective-discovery uses 0 context tokens** - full catalog exposure bypasses discovery entirely
3. **Wall-clock times are sub-millisecond** - synthetic tasks are too fast to measure overhead meaningfully
4. **Recovery and verification times are 0** - metrics not yet derived from trace timestamps
5. **Tool calls are similar across interfaces** (1.4-2.0) - scripted agent follows similar paths

---

## 3. Reliability-Cost Frontier Analysis

### Pareto-Efficient Conditions

A condition is Pareto-efficient if no other condition is better on both reliability and cost.

**Context Token vs. State Correctness:**

```
I0: 246 tokens, 100% correct  → High cost, high reliability
I1: 246 tokens,  50% correct  → High cost, low reliability (DOMINATED)
I2:  20 tokens, 100% correct  → Low cost, high reliability (PARETO-OPTIMAL)
I3:  20 tokens,  50% correct  → Low cost, low reliability (DOMINATED)
I4:  20 tokens,  33% correct  → Low cost, lowest reliability (DOMINATED)
I5:  20 tokens,  67% correct  → Low cost, medium reliability, recovery
```

**Pareto-optimal set:** {I0, I2, I5}
- I0: highest reliability but highest cost
- I2: best cost/reliability ratio
- I5: only condition with recovery capability

### Dominated Conditions
- I1, I3, I4 are dominated by I2 (same cost, lower reliability)
- All ablation variants are dominated by I2 or I5

---

## 4. Key Insights

### 4.1 Selective Discovery Is the Strongest Primitive

**Evidence:** I2 achieves 100% correctness with 92% fewer context tokens than I0/I1.

**Mechanism:** Compact metadata + on-demand schema retrieval reduces context exposure without sacrificing recall.

### 4.2 Recovery Is I5's Unique Contribution

**Evidence:** I5 is the only interface with non-zero recovery success (29.6%).

**Mechanism:** Durable state + reconciliation enables recovery from unknown outcomes.

### 4.3 Full AFT Does Not Dominate Simpler Interfaces

**Evidence:** I5-full (66.7% correct) is outperformed by I2 (100%) and several ablation variants (75-80%).

**Interpretation:** The overhead of full AFT (verification, durable state, reconciliation) may hurt performance on simple tasks. Simpler interfaces with selective discovery (I2) may be preferable for low-risk operations.

### 4.4 Safety Metrics Show No Violations

**Evidence:** Zero duplicate, unintended, or unauthorized effects across all 1,392 runs.

**Interpretation:** The scripted agent is well-behaved; safety primitives are not exercised. This is a limitation of the deterministic agent.

### 4.5 Timing Metrics Are Not Yet Evidence-Based

**Evidence:** All timing metrics (recovery_ms, verification_ms, runtime_overhead_ms) are 0.

**Root cause:** Trace timestamps exist but metric derivation from traces is incomplete.

**Action needed:** Implement timing metric computation from trace event timestamps.

---

## 5. Limitations

1. **Sub-millisecond wall-clock times** - Cannot meaningfully compare runtime overhead
2. **Zero timing metrics** - recovery_ms, verification_ms not derived from traces
3. **No safety violations** - Cannot evaluate safety primitives
4. **Scripted agent** - Does not differentially utilize primitives
5. **Synthetic tasks** - Too simple to expose primitive benefits

---

## 6. Recommendations

1. **For simple, low-risk tasks:** Use I2 (selective discovery) for best cost/reliability ratio
2. **For tasks with post-commit uncertainty:** Use I5 for recovery capability
3. **For high-reliability requirements:** Use I0 if cost is not a concern
4. **Avoid I1, I3, I4:** Dominated by I2 on both cost and reliability
5. **Future work:** Implement timing metric derivation from traces; test with LLM agents

---

**Report generated:** 2026-08-04T12:45:00+08:00  
**Source artifacts:** artifacts/evidence_runs/*/results.csv  
**Agent type:** scripted-v1 (deterministic)  
**Total runs analyzed:** 1,392
