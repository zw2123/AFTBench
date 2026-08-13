# Experiment Ledger — Consistency Report

**Generated:** auto
**Experiments:** 7

---
## discovery

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 96 |
| Observed runs | 96 |
| Successful | 0 |
| Failed | 4 |

### Trace consistency

| Check | Result |
|-------|--------|
| Traces match results | ✅ |
| Result run IDs | 96 |
| Trace run IDs | 96 |
| Missing from traces | 0 |
| Extra in traces | 0 |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 4 |
| Failure by interface: I1 | 2 |
| Failure by interface: I5-minus-selective-discovery | 2 |

### Oracle outcome distribution

- completed_as_requested: 92
- failure: 4

### Fault types used

``

---
## resume

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 120 |
| Observed runs | 120 |
| Successful | 0 |
| Failed | 48 |

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
| Effect committed | 24 | 20.0% |
| Response generated | 120 | 100.0% |
| Response dropped | 0 | 0.0% |

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 120 | 100% |
| Recovery attempted | 96 | 80.0% |
| Recovery succeeded | 48 | 40.0% |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 48 |
| Failure by interface: I5-minus-resumable-invocation | 24 |
| Failure by interface: I5-minus-durable-state | 24 |

### Oracle outcome distribution

- completed_as_requested: 72
- failure: 48

### Fault types used

`interrupted_execution`

---
## durable_state

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 120 |
| Observed runs | 120 |
| Successful | 0 |
| Failed | 48 |

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
| Effect committed | 24 | 20.0% |
| Response generated | 120 | 100.0% |
| Response dropped | 0 | 0.0% |

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 120 | 100% |
| Recovery attempted | 96 | 80.0% |
| Recovery succeeded | 48 | 40.0% |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 48 |
| Failure by interface: I5-minus-resumable-invocation | 24 |
| Failure by interface: I5-minus-durable-state | 24 |

### Oracle outcome distribution

- completed_as_requested: 72
- failure: 48

### Fault types used

`interrupted_execution`

---
## effect_contract/postcommit_loss

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 168 |
| Observed runs | 168 |
| Successful | 0 |
| Failed | 45 |

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
| Backend started | 258 | 153.6% |
| Effect committed | 228 | 135.7% |
| Response generated | 258 | 153.6% |
| Response dropped | 162 | 96.4% |

> ℹ️ 162/168 runs (96.4%) reached response_dropped stage.

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 168 | 100% |
| Recovery attempted | 72 | 42.9% |
| Recovery succeeded | 72 | 42.9% |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 45 |
| Failure by interface: I0 | 15 |
| Failure by interface: I1 | 15 |
| Failure by interface: I3 | 15 |

### Oracle outcome distribution

- completed_as_requested: 123
- failure: 45

### Fault types used

`lost_response_after_effect`

---
## effect_contract/stale_permission

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 240 |
| Observed runs | 240 |
| Successful | 0 |
| Failed | 15 |

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
| Backend started | 348 | 145.0% |
| Effect committed | 108 | 45.0% |
| Response generated | 348 | 145.0% |
| Response dropped | 0 | 0.0% |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 15 |
| Failure by interface: I1 | 3 |
| Failure by interface: I3 | 3 |
| Failure by interface: I4 | 3 |
| Failure by interface: I5 | 3 |
| Failure by interface: I5-minus-side-effect-contract | 3 |

### Oracle outcome distribution

- completed_as_requested: 72
- failure: 15
- safely_aborted: 12
- safely_refused: 90
- unsafe_committed: 51

### Fault types used

`permission_drift, stale_state`

---
## verification

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 168 |
| Observed runs | 168 |
| Successful | 0 |
| Failed | 45 |

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
| Backend started | 258 | 153.6% |
| Effect committed | 228 | 135.7% |
| Response generated | 258 | 153.6% |
| Response dropped | 162 | 96.4% |

> ℹ️ 162/168 runs (96.4%) reached response_dropped stage.

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 168 | 100% |
| Recovery attempted | 72 | 42.9% |
| Recovery succeeded | 72 | 42.9% |

### Error classification

| Type | Count |
|------|-------|
| Total failures | 45 |
| Failure by interface: I0 | 15 |
| Failure by interface: I1 | 15 |
| Failure by interface: I3 | 15 |

### Oracle outcome distribution

- completed_as_requested: 123
- failure: 45

### Fault types used

`lost_response_after_effect`

---
## sqlite/production_like

### Run counts

| Metric | Value |
|--------|-------|
| Expected runs | 144 |
| Observed runs | 144 |
| Successful | 0 |
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
| Backend started | 186 | 193.8% |
| Effect committed | 162 | 168.8% |
| Response generated | 186 | 193.8% |
| Response dropped | 48 | 50.0% |

> ℹ️ 48/96 runs (50.0%) reached response_dropped stage.

### Recovery funnel

| Stage | Count | % of eligible |
|-------|-------|---------------|
| Recovery eligible | 48 | 100% |
| Recovery attempted | 12 | 25.0% |
| Recovery succeeded | 12 | 25.0% |

### Oracle outcome distribution

- completed_as_requested: 138
- unsafe_committed: 6

### Fault types used

`, lost_response_after_effect, stale_state`

---
## Overall Summary

| Metric | Value |
|--------|-------|
| Total expected runs | 1056 |
| Total observed runs | 1056 |
| All checks passed | ✅ YES |
