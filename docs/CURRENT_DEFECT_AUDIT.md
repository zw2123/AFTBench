# Current Defect Audit - AFTBench

**Audit Date:** 2026-08-04T09:14:50+08:00  
**Baseline Tests:** 229 total, 38 failed, 191 passed  
**Baseline Acceptance:** NOT RUN (no acceptance script found)

## Critical Defects (Core Execution Chain)

### 2.1 Fault Injector Not Connected - NOT VERIFIED YET
**Status:** NEEDS INVESTIGATION  
**Evidence:** Runner.py exists but fault injection integration unclear  
**Impact:** All faults may not be injected at authoritative boundaries

### 2.2 lost_response_after_effect Incorrect Semantics - NOT VERIFIED YET
**Status:** NEEDS INVESTIGATION  
**Evidence:** Need to inspect I5 interface implementation  
**Impact:** Most important paper fault may have wrong semantics

### 2.3 Core Safety Metrics Hard-coded - NOT VERIFIED YET
**Status:** NEEDS INVESTIGATION  
**Evidence:** Need to inspect runner.py metric computation  
**Impact:** Metrics may be fabricated constants

### 2.4 Trace Events Insufficient - NOT VERIFIED YET
**Status:** NEEDS INVESTIGATION  
**Evidence:** Need to inspect trace event generation  
**Impact:** Missing required lifecycle events

### 2.5 Task Parameters Not Reaching Agent - NOT VERIFIED YET
**Status:** NEEDS INVESTIGATION  
**Evidence:** Need to inspect agent parameter passing  
**Impact:** Agent may receive empty parameters

## Confirmed Defects from Baseline Tests

### Interface Layer Defects

#### D1: condition_name() API Mismatch - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `TypeError: 'str' object is not callable`  
**Root Cause:** Tests call `iface.condition_name()` but implementation has it as attribute  
**Files:** 
- `src/aftbench/interfaces/i0_legacy.py`
- `src/aftbench/interfaces/i1_schema.py`
- `src/aftbench/interfaces/i2_discovery.py`
- `src/aftbench/interfaces/i3_lifecycle.py`
- `src/aftbench/interfaces/i4_effect.py`
- `src/aftbench/interfaces/i5_full_aft.py`
**Tests:** 
- `tests/unit/test_interfaces.py::TestI0LegacyInterface::test_condition_name`
- All similar tests for I1-I5
**Impact:** All interface identification broken

#### D2: invoke() Not Calling apply_effect() - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `assert 0 == 1` for `world.effect_calls`  
**Root Cause:** Interface invoke() methods not routing to world.apply_effect()  
**Files:**
- `src/aftbench/interfaces/i0_legacy.py`
- `src/aftbench/interfaces/i5_full_aft.py`
**Tests:**
- `tests/integration/test_interface_parity.py::TestI0Parity::test_invoke_create_routes_to_apply_effect`
- `tests/integration/test_interface_parity.py::TestI0AndI5SameBackend::test_both_call_apply_effect_on_same_world`
**Impact:** Core execution chain broken - no effects actually applied

#### D3: Missing success Field in Results - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `KeyError: 'success'`  
**Root Cause:** invoke() returns dict without 'success' field  
**Files:** All interface implementations  
**Tests:**
- `tests/unit/test_interfaces.py::TestI0LegacyInterface::test_invoke_success`
- `tests/integration/test_interface_parity.py::TestI0Parity::test_invoke_unknown_tool_returns_error`
**Impact:** Result validation broken

#### D4: I5 reconcile() Signature Error - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `TypeError: reconcile() takes 2 positional arguments but 3 were given`  
**Root Cause:** Method signature mismatch  
**Files:** `src/aftbench/interfaces/i5_full_aft.py`  
**Tests:**
- `tests/unit/test_interfaces.py::TestI5FullAFTInterface::test_reconcile_nonexistent_invocation`
**Impact:** I5 reconciliation broken

#### D5: I5 get_evidence() Wrong Status Field - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `assert 'success' == 'ok'`  
**Root Cause:** Evidence status uses 'success' instead of 'ok'  
**Files:** `src/aftbench/interfaces/i5_full_aft.py`  
**Tests:**
- `tests/unit/test_interfaces.py::TestI5FullAFTInterface::test_get_evidence_after_invoke`
**Impact:** Evidence validation broken

### World Layer Defects

#### D6: LargeCatalogWorld Missing catalog_sizes - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `KeyError: 'catalog_sizes'`  
**Root Cause:** get_state() doesn't return catalog_sizes dict  
**Files:** `src/aftbench/worlds/large_catalog.py`  
**Tests:**
- `tests/unit/test_worlds.py::TestLargeCatalogWorld::test_reset_creates_all_catalog_sizes`
- `tests/integration/test_smoke.py::TestSmokeWorldsInitialize::test_large_catalog_reset`
**Impact:** Discovery experiments broken

#### D7: LargeCatalogWorld Missing target_capability_id - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `KeyError: 'target_capability_id'`  
**Root Cause:** get_state() doesn't expose target capability  
**Files:** `src/aftbench/worlds/large_catalog.py`  
**Tests:**
- `tests/unit/test_worlds.py::TestLargeCatalogWorld::test_target_capability_set`
**Impact:** Postcondition verification broken

#### D8: LargeCatalogWorld get_catalog() Wrong Size - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `assert 50 == 10`  
**Root Cause:** get_catalog() returns full catalog instead of requested size  
**Files:** `src/aftbench/worlds/large_catalog.py`  
**Tests:**
- `tests/unit/test_worlds.py::TestLargeCatalogWorld::test_get_catalog_returns_correct_size`
**Impact:** Selective discovery experiments broken

#### D9: LargeCatalogWorld apply_effect() Missing catalog Field - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `KeyError: 'catalog'`  
**Root Cause:** get_catalog effect doesn't return catalog in result  
**Files:** `src/aftbench/worlds/large_catalog.py`  
**Tests:**
- `tests/unit/test_worlds.py::TestLargeCatalogWorld::test_apply_effect_get_catalog`
**Impact:** Discovery workflow broken

#### D10: LargeCatalogWorld get_object_version() Wrong Value - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** `assert '02f1bbf1ef' == 'v1'`  
**Root Cause:** Returns hash instead of version string  
**Files:** `src/aftbench/worlds/large_catalog.py`  
**Tests:**
- `tests/unit/test_worlds.py::TestLargeCatalogWorld::test_get_object_version_always_v1`
**Impact:** Version tracking broken

#### D11: LargeCatalogWorld verify_postconditions() Always True - CONFIRMED
**Status:** CONFIRMED  
**Symptom:** Wrong selection returns True  
**Root Cause:** Postcondition verification logic broken  
**Files:** `src/aftbench/worlds/large_catalog.py`  
**Tests:**
- `tests/unit/test_worlds.py::TestLargeCatalogWorld::test_verify_postconditions_wrong_selection`
**Impact:** Verification broken

## Priority Order

1. **D2: invoke() not calling apply_effect()** - Core execution broken
2. **D1: condition_name() API mismatch** - Interface identification broken
3. **D3: Missing success field** - Result validation broken
4. **D6-D11: LargeCatalogWorld defects** - Discovery experiments broken
5. **D4-D5: I5 reconciliation defects** - Full AFT broken
6. **2.1-2.5: Unverified critical defects** - Need investigation

## Next Actions

1. Fix D2 (invoke routing) - highest priority
2. Fix D1 (condition_name API)
3. Fix D3 (success field)
4. Fix D6-D11 (LargeCatalogWorld)
5. Fix D4-D5 (I5 reconciliation)
6. Investigate 2.1-2.5 (fault injection, traces, metrics)
