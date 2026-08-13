# Experiment Ledger — Consistency Report

**Generated:** auto
**Experiments:** 6

---
## primitive_ablations

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 768 |
| Observed runs | 768 |
| Successful | 576 |
| Failed | 192 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 768 |
| Trace run IDs | 768 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Fault funnel

| Stage | Count | % of configured |
|-------|-------|-----------------|
| Fault configured | 512 | 100% |
| Request accepted | 768 | 150.0% |
| Backend started | 768 | 150.0% |
| Effect committed | 236 | 46.1% |
| Response generated | 768 | 150.0% |
| Response dropped | 118 | 23.0% |

> ℹ️ 118/512 runs (23.0%) reached response_dropped stage.

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 512 | 100% |
| Recovery attempted | 0 | 0.0% |
| Recovery succeeded | 326 | 63.7% |

> ⚠️ **NOTE**: recovery_attempted=0 but recovery_succeeded=326. Traces may not contain explicit recovery event types.

### Error classification

| Type | Count |
|------|-------|
| Total failures | 192 |
| Failure by interface: I5 | 24 |
| Failure by interface: I5-minus-selective-discovery | 24 |
| Failure by interface: I5-minus-resumable-invocation | 24 |
| Failure by interface: I5-minus-observable-execution | 24 |
| Failure by interface: I5-minus-structured-output | 24 |
| Failure by interface: I5-minus-side-effect-contract | 24 |
| Failure by interface: I5-minus-durable-state | 24 |
| Failure by interface: I5-minus-verification | 24 |

### Oracle outcome distribution

- failure: 192
- success: 576

### Fault types used

`, interrupted_execution, lost_response_after_effect`

---
## discovery_frontier

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 96 |
| Observed runs | 96 |
| Successful | 96 |
| Failed | 0 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 96 |
| Trace run IDs | 96 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Oracle outcome distribution

- success: 96

### Fault types used

``

---
## postcommit_loss

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 168 |
| Observed runs | 168 |
| Successful | 168 |
| Failed | 0 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 168 |
| Trace run IDs | 168 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Fault funnel

| Stage | Count | % of configured |
|-------|-------|-----------------|
| Fault configured | 168 | 100% |
| Request accepted | 168 | 100.0% |
| Backend started | 168 | 100.0% |
| Effect committed | 123 | 73.2% |
| Response generated | 168 | 100.0% |
| Response dropped | 123 | 73.2% |

> ℹ️ 123/168 runs (73.2%) reached response_dropped stage.

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 168 | 100% |
| Recovery attempted | 0 | 0.0% |
| Recovery succeeded | 63 | 37.5% |

> ⚠️ **NOTE**: recovery_attempted=0 but recovery_succeeded=63. Traces may not contain explicit recovery event types.

### Oracle outcome distribution

- success: 168

### Fault types used

`lost_response_after_effect`

---
## interruption_recovery

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 120 |
| Observed runs | 120 |
| Successful | 120 |
| Failed | 0 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 120 |
| Trace run IDs | 120 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Fault funnel

| Stage | Count | % of configured |
|-------|-------|-----------------|
| Fault configured | 120 | 100% |
| Request accepted | 120 | 100.0% |
| Backend started | 120 | 100.0% |
| Effect committed | 0 | 0.0% |
| Response generated | 120 | 100.0% |
| Response dropped | 0 | 0.0% |

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 120 | 100% |
| Recovery attempted | 0 | 0.0% |
| Recovery succeeded | 48 | 40.0% |

> ⚠️ **NOTE**: recovery_attempted=0 but recovery_succeeded=48. Traces may not contain explicit recovery event types.

### Oracle outcome distribution

- success: 120

### Fault types used

`interrupted_execution`

---
## stale_permission

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 240 |
| Observed runs | 240 |
| Successful | 0 |
| Failed | 240 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 240 |
| Trace run IDs | 240 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Fault funnel

| Stage | Count | % of configured |
|-------|-------|-----------------|
| Fault configured | 240 | 100% |
| Request accepted | 240 | 100.0% |
| Backend started | 240 | 100.0% |
| Effect committed | 42 | 17.5% |
| Response generated | 240 | 100.0% |
| Response dropped | 0 | 0.0% |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 240 |
| Failure by interface: I1 | 48 |
| Failure by interface: I3 | 48 |
| Failure by interface: I4 | 48 |
| Failure by interface: I5 | 48 |
| Failure by interface: I5-minus-side-effect-contract | 48 |

### Oracle outcome distribution

- failure: 240

### Fault types used

`permission_drift, stale_state`

---
## production_like

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 144 |
| Observed runs | 144 |
| Successful | 144 |
| Failed | 0 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 144 |
| Trace run IDs | 144 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Fault funnel

| Stage | Count | % of configured |
|-------|-------|-----------------|
| Fault configured | 96 | 100% |
| Request accepted | 144 | 150.0% |
| Backend started | 144 | 150.0% |
| Effect committed | 81 | 84.4% |
| Response generated | 144 | 150.0% |
| Response dropped | 27 | 28.1% |

> ℹ️ 27/96 runs (28.1%) reached response_dropped stage.

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 48 | 100% |
| Recovery attempted | 0 | 0.0% |
| Recovery succeeded | 6 | 12.5% |

> ⚠️ **NOTE**: recovery_attempted=0 but recovery_succeeded=6. Traces may not contain explicit recovery event types.

### Oracle outcome distribution

- success: 144

### Fault types used

`, lost_response_after_effect, stale_state`

---
## Overall Summary

| Metric | Value |
|--------|-------|
| Total expected runs | 1536 |
| Total observed runs | 1536 |
| All checks passed | ✅ YES |
