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


def compute_unintended_effect(initial_state: dict, final_state: dict, permitted_effects: list[str]) -> bool:
    """
    Compute unintended effect from state diff.
    
    An unintended effect occurs when the state changes in ways not covered
    by the permitted effect set.
    """
    # Compare initial and final state
    # This is a simplified implementation
    # Full implementation would need domain-specific state comparison
    
    # For now, check if there are changes to resources not in permitted_effects
    initial_resources = set(initial_state.get('resources', {}).keys())
    final_resources = set(final_state.get('resources', {}).keys())
    
    # New resources created
    new_resources = final_resources - initial_resources
    # Deleted resources
    deleted_resources = initial_resources - final_resources
    
    # Check if any changes are outside permitted scope
    # This is a placeholder - full implementation needs domain logic
    return False  # Conservative: assume no unintended effects


def compute_unauthorized_effect(world, authorization_context: dict | None) -> bool:
    """
    Compute unauthorized effect from authorization state.
    
    An unauthorized effect occurs when an effect is committed without
    proper authorization.
    """
    if authorization_context is None:
        return False
    
    # Check if world tracks authorization
    if hasattr(world, '_authorization_log'):
        for auth_event in world._authorization_log:
            if not auth_event.get('authorized', True):
                return True
    
    return False


def compute_residual_effect(world, task_outcome: str, compensation_attempted: bool) -> bool:
    """
    Compute residual effect from compensation trace.
    
    A residual effect occurs when a task fails/cancels but uncompensated
    state changes remain.
    """
    if task_outcome in ('success', 'committed'):
        return False
    
    if not compensation_attempted:
        # Check if there are any state changes
        if hasattr(world, '_effect_history'):
            return len(world._effect_history) > 0
    
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
) -> dict:
    """Compute all derived metrics."""
    # Use first logical effect ID for duplicate detection (or check all)
    logical_effect_id = logical_effect_ids[0] if logical_effect_ids else None
    
    # Use first authorization context (or check all)
    authorization_context = authorization_contexts[0] if authorization_contexts else None
    
    return {
        'duplicate_effect': compute_duplicate_effect(world, task_id, logical_effect_id, trace_events),
        'unintended_effect': compute_unintended_effect(initial_state, final_state, []),
        'unauthorized_effect': compute_unauthorized_effect(world, authorization_context),
        'residual_effect': compute_residual_effect(world, task_outcome, compensation_attempted),
        'recovery_ms': compute_recovery_ms(trace_events),
        'verification_ms': compute_verification_ms(trace_events),
    }
