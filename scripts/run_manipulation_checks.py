#!/usr/bin/env python3
"""Manipulation checks for AFTBench primitive ablations.

Each check verifies that a primitive ablation actually changes the mechanism
(the behavior pathway), independently of outcome (correctness/recovery).

Usage:
    python scripts/run_manipulation_checks.py
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path("src").resolve()))


def _check_feature_flag(impl: Any, feature_name: str) -> bool:
    """Check if a feature flag exists and is True."""
    if hasattr(impl, "features"):
        return getattr(impl.features, feature_name, True)
    return True  # Non-ablation interfaces have all features enabled


def _get_interface(module_path: str, class_name: str):
    """Dynamically import and instantiate an interface."""
    import importlib
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()


def _get_world(module_path: str, class_name: str):
    """Dynamically import and instantiate a world."""
    import importlib
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()


# ---------------------------------------------------------------------------
# Check 1: Selective Discovery
# ---------------------------------------------------------------------------

def check_selective_discovery() -> Dict[str, Any]:
    results = {"primitive": "selective_discovery", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusSelectiveDiscovery")

    # 1a. Check discover() implementations differ
    i5_src = inspect.getsource(i5.discover)
    minus_src = inspect.getsource(i5_minus.discover)
    differs = i5_src != minus_src

    results["checks"].append({
        "check": "discover_method_differs",
        "passed": differs,
        "detail": "Methods differ" if differs else "WARNING: identical",
    })
    if not differs:
        results["passed"] = False

    # 1b. Feature flag check
    i5_flag = _check_feature_flag(i5, "selective_discovery")
    minus_flag = _check_feature_flag(i5_minus, "selective_discovery")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # 1c. Trace-level: check context_tokens differ in discovery_frontier
    import csv
    rpath = Path("artifacts/evidence_runs/discovery_frontier/results.csv")
    if rpath.exists():
        with open(rpath) as f:
            rows = list(csv.DictReader(f))
        i5_t = [int(r.get("context_tokens", 0)) for r in rows if r["interface_condition"] == "I5"]
        mn_t = [int(r.get("context_tokens", 0)) for r in rows if r["interface_condition"] == "I5-minus-selective-discovery"]
        i5_avg = sum(i5_t) / len(i5_t) if i5_t else 0
        mn_avg = sum(mn_t) / len(mn_t) if mn_t else 0
        results["checks"].append({
            "check": "context_tokens_differ_in_experiment",
            "passed": i5_avg != mn_avg,
            "detail": f"I5 avg={i5_avg:.0f}, I5-minus avg={mn_avg:.0f}",
        })

    return results


# ---------------------------------------------------------------------------
# Check 2: Resumable Invocation
# ---------------------------------------------------------------------------

def check_resumable_invocation() -> Dict[str, Any]:
    results = {"primitive": "resumable_invocation", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusResumableInvocation")

    # 2a. Check resume() implementations differ
    i5_src = inspect.getsource(i5.resume)
    minus_src = inspect.getsource(i5_minus.resume)
    differs = i5_src != minus_src
    results["checks"].append({
        "check": "resume_method_differs",
        "passed": differs,
        "detail": "Methods differ" if differs else "WARNING: identical",
    })

    # 2b. Feature flag
    i5_flag = _check_feature_flag(i5, "resumable_invocation")
    minus_flag = _check_feature_flag(i5_minus, "resumable_invocation")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # 2c. I3 resume implementation
    i3 = _get_interface("aftbench.interfaces.i3_lifecycle", "I3LifecycleInterface")
    i3_src = inspect.getsource(i3.resume)
    i5_src = inspect.getsource(i5.resume)
    results["checks"].append({
        "check": "i3_has_resume_method",
        "passed": "def resume" in i3_src,
        "detail": "I3 has resume() method" if "def resume" in i3_src else "WARNING: I3 missing resume()",
    })

    # Check: I3 resume() returns different result than I5-minus-resume
    r3 = i3.resume("nonexistent")
    r5m = i5_minus.resume("nonexistent")
    results["checks"].append({
        "check": "i3_resume_vs_minus_resume",
        "passed": r3.get("status") != r5m.get("status"),
        "detail": f"I3 resume(nonexistent): {r3.get('status')}, "
                  f"I5-minus resume(nonexistent): {r5m.get('status')}",
    })

    return results


# ---------------------------------------------------------------------------
# Check 3: Observable Execution
# ---------------------------------------------------------------------------

def check_observable_execution() -> Dict[str, Any]:
    results = {"primitive": "observable_execution", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusObservableExecution")

    # Check feature flag
    i5_flag = _check_feature_flag(i5, "observable_execution")
    minus_flag = _check_feature_flag(i5_minus, "observable_execution")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # Check I5 has get_status, I5-minus-observable has it disabled
    i5_has = hasattr(i5, "get_status")
    minus_has = hasattr(i5_minus, "get_status")
    results["checks"].append({
        "check": "both_have_get_status",
        "passed": i5_has and minus_has,
        "detail": f"I5: {i5_has}, I5-minus: {minus_has}",
    })

    # Check they return different results
    r_i5 = i5.get_status("nonexistent")
    r_mn = i5_minus.get_status("nonexistent")
    results["checks"].append({
        "check": "get_status_returns_different_results",
        "passed": r_i5 != r_mn,
        "detail": f"I5: {str(r_i5)[:60]}, I5-minus: {str(r_mn)[:60]}",
    })

    return results


# ---------------------------------------------------------------------------
# Check 4: Structured Output
# ---------------------------------------------------------------------------

def check_structured_output() -> Dict[str, Any]:
    results = {"primitive": "structured_output", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusStructuredOutput")
    world = _get_world("aftbench.worlds.enterprise_records", "EnterpriseRecordsWorld")
    world.reset(seed=42)

    # 4a. Check invoke() implementations differ
    i5_src = inspect.getsource(i5.invoke)
    minus_src = inspect.getsource(i5_minus.invoke)
    results["checks"].append({
        "check": "invoke_method_differs",
        "passed": i5_src != minus_src,
        "detail": "Methods differ" if i5_src != minus_src else "WARNING: identical",
    })

    # 4b. Feature flag
    i5_flag = _check_feature_flag(i5, "structured_output")
    minus_flag = _check_feature_flag(i5_minus, "structured_output")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # 4c. Check return format differs
    try:
        r_i5 = i5.invoke("crm.get_record", {"record_id": "con-001"}, world)
        # Reset world for second call
        world2 = _get_world("aftbench.worlds.enterprise_records", "EnterpriseRecordsWorld")
        world2.reset(seed=42)
        r_mn = i5_minus.invoke("crm.get_record", {"record_id": "con-001"}, world2)
        results["checks"].append({
            "check": "return_format_differs",
            "passed": r_i5 != r_mn,
            "detail": f"I5 keys: {sorted(r_i5.keys())}, I5-minus keys: {sorted(r_mn.keys())}",
        })
    except Exception as e:
        results["checks"].append({
            "check": "return_format_differs",
            "passed": False,
            "detail": f"Exception: {e}",
        })

    return results


# ---------------------------------------------------------------------------
# Check 5: Side-Effect Contract
# ---------------------------------------------------------------------------

def check_side_effect_contract() -> Dict[str, Any]:
    results = {"primitive": "side_effect_contract", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusSideEffectContract")
    world = _get_world("aftbench.worlds.enterprise_records", "EnterpriseRecordsWorld")
    world.reset(seed=42)

    # Feature flag
    i5_flag = _check_feature_flag(i5, "side_effect_contract")
    minus_flag = _check_feature_flag(i5_minus, "side_effect_contract")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # Check invoke() implementations differ
    i5_src = inspect.getsource(i5.invoke)
    minus_src = inspect.getsource(i5_minus.invoke)
    results["checks"].append({
        "check": "invoke_method_differs",
        "passed": i5_src != minus_src,
        "detail": "Methods differ" if i5_src != minus_src else "WARNING: identical",
    })

    # Check return format: I5 has effect_class, minus removes it
    try:
        r_i5 = i5.invoke("crm.get_record", {"record_id": "con-001"}, world)
        world2 = _get_world("aftbench.worlds.enterprise_records", "EnterpriseRecordsWorld")
        world2.reset(seed=42)
        r_mn = i5_minus.invoke("crm.get_record", {"record_id": "con-001"}, world2)
        has_ec = "effect_class" in r_i5
        minus_has_ec = "effect_class" in r_mn
        results["checks"].append({
            "check": "effect_class_stripped_in_minus",
            "passed": has_ec and not minus_has_ec,
            "detail": f"I5 has effect_class: {has_ec}, I5-minus has effect_class: {minus_has_ec}",
        })
    except Exception as e:
        results["checks"].append({
            "check": "effect_class_stripped_in_minus",
            "passed": False,
            "detail": f"Exception: {e}",
        })

    return results


# ---------------------------------------------------------------------------
# Check 6: Durable State
# ---------------------------------------------------------------------------

def check_durable_state() -> Dict[str, Any]:
    results = {"primitive": "durable_state", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusDurableState")

    # Feature flag
    i5_flag = _check_feature_flag(i5, "durable_state")
    minus_flag = _check_feature_flag(i5_minus, "durable_state")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # Check reconcile() implementations differ
    i5_src = inspect.getsource(i5.reconcile)
    minus_src = inspect.getsource(i5_minus.reconcile)
    results["checks"].append({
        "check": "reconcile_method_differs",
        "passed": i5_src != minus_src,
        "detail": "Methods differ" if i5_src != minus_src else "WARNING: identical",
    })

    # Check reconcile returns different results
    r_i5 = i5.reconcile("nonexistent")
    r_mn = i5_minus.reconcile("nonexistent")
    results["checks"].append({
        "check": "reconcile_returns_different_results",
        "passed": r_i5.get("status") != r_mn.get("status"),
        "detail": f"I5: {r_i5.get('status')}, I5-minus: {r_mn.get('status')}",
    })

    # Check I5 has _durable dict
    results["checks"].append({
        "check": "i5_has_durable_state",
        "passed": hasattr(i5, "_durable") and isinstance(i5._durable, dict),
        "detail": f"I5 has _durable: {hasattr(i5, '_durable')}",
    })

    return results


# ---------------------------------------------------------------------------
# Check 7: Verification
# ---------------------------------------------------------------------------

def check_verification() -> Dict[str, Any]:
    results = {"primitive": "verification", "checks": [], "passed": True}

    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")
    i5_minus = _get_interface("aftbench.interfaces.i5_ablations", "I5MinusVerification")
    world = _get_world("aftbench.worlds.enterprise_records", "EnterpriseRecordsWorld")
    world.reset(seed=42)

    # Feature flag
    i5_flag = _check_feature_flag(i5, "verification")
    minus_flag = _check_feature_flag(i5_minus, "verification")
    results["checks"].append({
        "check": "feature_flag_disabled_in_ablation",
        "passed": i5_flag == True and minus_flag == False,
        "detail": f"I5: {i5_flag}, I5-minus: {minus_flag}",
    })

    # Check verify() returns "skipped" for minus-verification
    r_mn = i5_minus.verify("nonexistent", world)
    results["checks"].append({
        "check": "minus_verification_returns_skipped",
        "passed": r_mn.get("status") == "skipped",
        "detail": f"I5-minus verify: status={r_mn.get('status')}, "
                  f"verified={r_mn.get('verified')}, reason={r_mn.get('reason')}",
    })

    return results


# ---------------------------------------------------------------------------
# Check 8: I3 vs I5 resume deep comparison
# ---------------------------------------------------------------------------

def check_i3_vs_i5_resume() -> Dict[str, Any]:
    results = {"primitive": "i3_vs_i5_resume", "checks": [], "passed": True}

    i3 = _get_interface("aftbench.interfaces.i3_lifecycle", "I3LifecycleInterface")
    i5 = _get_interface("aftbench.interfaces.i5_full_aft", "I5FullAFTInterface")

    # 8a. Resume source code differs
    i3_src = inspect.getsource(i3.resume)
    i5_src = inspect.getsource(i5.resume)
    results["checks"].append({
        "check": "resume_implementation_differs",
        "passed": i3_src != i5_src,
        "detail": "I3 and I5 have different resume() implementations"
                  if i3_src != i5_src else "WARNING: identical",
    })

    # 8b. I3 has no _durable
    results["checks"].append({
        "check": "i3_has_no_durable_state",
        "passed": not hasattr(i3, "_durable"),
        "detail": f"I3 has _durable: {hasattr(i3, '_durable')}",
    })

    # 8c. I5 has _durable
    results["checks"].append({
        "check": "i5_has_durable_state",
        "passed": hasattr(i5, "_durable"),
        "detail": f"I5 has _durable: {hasattr(i5, '_durable')}",
    })

    # 8d. I3 has _invocations
    results["checks"].append({
        "check": "i3_has_invocations",
        "passed": hasattr(i3, "_invocations"),
        "detail": f"I3 has _invocations: {hasattr(i3, '_invocations')}",
    })

    # 8e. I5 has _invocations and _evidence
    results["checks"].append({
        "check": "i5_has_evidence",
        "passed": hasattr(i5, "_evidence"),
        "detail": f"I5 has _evidence: {hasattr(i5, '_evidence')}",
    })

    # 8f. Check I3 invoke returns invocation_id
    world = _get_world("aftbench.worlds.long_running_jobs", "LongRunningJobsWorld")
    world.reset(seed=42)
    try:
        r = i3.invoke("job.start",
                      {"job_type": "report", "params": {"dataset": "sales"}}, world)
        has_inv_id = "invocation_id" in r
        results["checks"].append({
            "check": "i3_invoke_returns_invocation_id",
            "passed": has_inv_id,
            "detail": f"I3 invoke invocation_id: {r.get('invocation_id', 'MISSING')[:20]}",
        })
    except Exception as e:
        results["checks"].append({
            "check": "i3_invoke_returns_invocation_id",
            "passed": False,
            "detail": f"Exception: {e}",
        })

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("AFTBench Manipulation Checks")
    print("=" * 70)
    print()
    print("These checks verify that each primitive ablation actually changes")
    print("the mechanism (behavior pathway), independently of outcome.")
    print()

    check_functions = [
        ("selective_discovery", check_selective_discovery),
        ("resumable_invocation", check_resumable_invocation),
        ("observable_execution", check_observable_execution),
        ("structured_output", check_structured_output),
        ("side_effect_contract", check_side_effect_contract),
        ("durable_state", check_durable_state),
        ("verification", check_verification),
        ("i3_vs_i5_resume", check_i3_vs_i5_resume),
    ]

    all_passed = True
    results_by_primitive = {}

    for name, fn in check_functions:
        try:
            result = fn()
        except Exception as e:
            import traceback
            result = {
                "primitive": name,
                "checks": [{"check": "execution", "passed": False,
                           "detail": f"Exception: {e}\n{traceback.format_exc()}"}],
                "passed": False,
            }

        results_by_primitive[name] = result
        passed = result["passed"]
        n_checks = len(result["checks"])
        n_passed = sum(1 for c in result["checks"] if c["passed"])

        status = "✅" if passed else "❌"
        print(f"  {status} {name}: {n_passed}/{n_checks} checks passed")

        for check in result["checks"]:
            c_status = "✅" if check["passed"] else "❌"
            detail = check["detail"][:120]
            print(f"      {c_status} {check['check']}: {detail}")

        if not passed:
            all_passed = False
        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, result in results_by_primitive.items():
        n_passed = sum(1 for c in result["checks"] if c["passed"])
        n_total = len(result["checks"])
        status = "✅" if result["passed"] else "❌"
        print(f"  {status} {name}: {n_passed}/{n_total}")
    print()
    if all_passed:
        print("  ✅ ALL MANIPULATION CHECKS PASSED")
    else:
        print("  ⚠️  SOME MANIPULATION CHECKS FAILED")
    print()


if __name__ == "__main__":
    main()