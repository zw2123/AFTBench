"""Derived metrics computation from state and trace evidence."""
from __future__ import annotations
from typing import Any


def compute_duplicate_effect(world, task_id: str, logical_effect_id: str | None, trace_events: list[dict]) -> bool:
    """
    Compute duplicate effect from committed backend operations.
    
    A duplicate effect occurs when the same logical effect is committed more than once.
    A transport retry is NOT automatically a duplicate effect.
    """
    # Count committed effects for this logical_effect_id
    if logical_effect_id is None:
        return False
    
    # Check world's effect history
    if hasattr(world, '_effect_history'):
        committed_effects = [
            e for e in world._effect_history
            if e.get('logical_effect_id') == logical_effect_id
            and e.get('committed', False)
        ]
        return len(committed_effects) > 1
    
    # Fallback: check trace events
    commit_events = [
        e for e in trace_events
        if e.get('event_type') == 'EFFECT_COMMITTED'
        and e.get('logical_effect_id') == logical_effect_id
    ]
    return len(commit_events) > 1


def compute_unintended_effect(world, initial_state: dict, final_state: dict,
                              permitted_effects: list[str] | None = None) -> bool:
    """
    Compute unintended effect from the world's effect log.

    An unintended effect is a committed effect on a resource outside the
    task's permitted set.  ``permitted_effects`` lists allowed entity /
    resource ids; effects on other resources count as unintended.
    """
    permitted = set(permitted_effects or [])
    if hasattr(world, "_effect_log") and world._effect_log:
        for entry in world._effect_log:
            targets = []
            for key in ("entity_id", "message_id", "event_id", "record_id"):
                if entry.get(key):
                    targets.append(entry[key])
            if entry.get("target"):
                targets.append(entry["target"])
            if not targets:
                continue
            if permitted and all(t not in permitted for t in targets):
                return True
        return False

    # Fallback: state diff outside permitted resources.
    initial_resources = set(initial_state.get("resources", {}).keys()) if isinstance(initial_state, dict) else set()
    final_resources = set(final_state.get("resources", {}).keys()) if isinstance(final_state, dict) else set()
    new_resources = final_resources - initial_resources
    if permitted and new_resources - permitted:
        return True
    return False


def compute_unauthorized_effect(world, authorization_context: dict | None) -> bool:
    """
    Compute unauthorized effect from the world's authorization log.

    An unauthorized effect is an effect attempt denied by the backend's
    authorization layer (weak interfaces attempt; contract-aware interfaces
    preflight-refuse before attempting).
    """
    if hasattr(world, "_authorization_log"):
        return any(not ev.get("authorized", True) for ev in world._authorization_log)
    if authorization_context is None:
        return False
    if hasattr(world, "_authorization_log"):
        for auth_event in world._authorization_log:
            if not auth_event.get("authorized", True):
                return True
    return False


def compute_residual_effect(world, task_outcome: str, compensation_attempted: bool) -> bool:
    """
    Compute residual effect from compensation trace.
    
    A residual effect occurs when a task fails/cancels but uncompensated
    state changes remain.
    """
    if task_outcome in ('success', 'committed', 'completed_as_requested'):
        return False
    
    if not compensation_attempted:
        # Check if there are any state changes
        # Method 1: world._effect_history (if tracked by the world)
        if hasattr(world, '_effect_history') and world._effect_history:
            return len(world._effect_history) > 0
        
        # Method 2: compare initial vs final state hash
        if hasattr(world, '_initial_state') and world._initial_state is not None:
            current = world.get_state()
            # Simple check: compare serialized state
            import json
            init_json = json.dumps(world._initial_state, sort_keys=True, default=str)
            curr_json = json.dumps(current, sort_keys=True, default=str)
            return init_json != curr_json
        
        # Method 3: check if world has any effect tracking
        if hasattr(world, '_effect_log') and world._effect_log:
            return True
    
    # Check if compensation was successful
    if hasattr(world, '_compensation_log'):
        for comp_event in world._compensation_log:
            if not comp_event.get('successful', False):
                return True
    
    return False


def compute_recovery_ms(trace_events: list[dict]) -> int:
    """
    Compute recovery time from trace timestamps.
    
    Recovery time is the duration from fault detection to recovery completion.
    """
    if not trace_events:
        return 0
    
    # Find recovery-related events
    fault_events = [e for e in trace_events if 'fault' in e.get('event_type', '').lower()]
    recovery_events = [e for e in trace_events if 'recovery' in e.get('event_type', '').lower() or 'reconcil' in e.get('event_type', '').lower()]
    
    if not fault_events or not recovery_events:
        return 0
    
    # Compute time between first fault and last recovery
    fault_time = min(e.get('timestamp', 0) for e in fault_events)
    recovery_time = max(e.get('timestamp', 0) for e in recovery_events)
    
    return int((recovery_time - fault_time) * 1000)  # Convert to ms


def compute_verification_ms(trace_events: list[dict]) -> int:
    """
    Compute verification time from trace timestamps.
    
    Verification time is the duration of verification activities.
    """
    if not trace_events:
        return 0
    
    # Find verification-related events
    verification_events = [
        e for e in trace_events
        if 'verif' in e.get('event_type', '').lower()
    ]
    
    if len(verification_events) < 2:
        return 0
    
    # Compute duration from first to last verification event
    start_time = min(e.get('timestamp', 0) for e in verification_events)
    end_time = max(e.get('timestamp', 0) for e in verification_events)
    
    return int((end_time - start_time) * 1000)  # Convert to ms


def compute_all_derived_metrics(
    world,
    task_id: str,
    logical_effect_ids: list[str] | None,
    initial_state: dict,
    final_state: dict,
    trace_events: list[dict],
    task_outcome: str,
    authorization_contexts: list[dict] | None = None,
    compensation_attempted: bool = False,
    permitted_effects: list[str] | None = None,
) -> dict:
    """Compute all derived metrics."""
    # Use first logical effect ID for duplicate detection (or check all)
    logical_effect_id = logical_effect_ids[0] if logical_effect_ids else None
    
    # Use first authorization context (or check all)
    authorization_context = authorization_contexts[0] if authorization_contexts else None
    
    return {
        'duplicate_effect': compute_duplicate_effect(world, task_id, logical_effect_id, trace_events),
        'unintended_effect': compute_unintended_effect(world, initial_state, final_state, permitted_effects),
        'unauthorized_effect': compute_unauthorized_effect(world, authorization_context),
        'residual_effect': compute_residual_effect(world, task_outcome, compensation_attempted),
        'recovery_ms': compute_recovery_ms(trace_events),
        'verification_ms': compute_verification_ms(trace_events),
    }
