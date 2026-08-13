"""Lifecycle state machine: valid transitions and sequence validation."""

from __future__ import annotations

from .invocation import LifecycleState


# Valid transitions: from_state -> set of allowed to_states
_VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.CREATED: {
        LifecycleState.RUNNING,
        LifecycleState.FAILED,
    },
    LifecycleState.RUNNING: {
        LifecycleState.WAITING_INPUT,
        LifecycleState.PAUSED,
        LifecycleState.COMMITTED,
        LifecycleState.FAILED,
        LifecycleState.UNKNOWN,
    },
    LifecycleState.WAITING_INPUT: {
        LifecycleState.RUNNING,
        LifecycleState.FAILED,
        LifecycleState.UNKNOWN,
    },
    LifecycleState.PAUSED: {
        LifecycleState.RUNNING,
        LifecycleState.FAILED,
        LifecycleState.UNKNOWN,
    },
    LifecycleState.COMMITTED: set(),           # terminal
    LifecycleState.COMPENSATED: set(),         # terminal
    LifecycleState.FAILED: set(),              # terminal
    LifecycleState.UNKNOWN: {
        LifecycleState.COMMITTED,
        LifecycleState.COMPENSATED,
        LifecycleState.FAILED,
    },
}


class LifecycleStateMachine:
    """Validates lifecycle transitions and sequence numbers."""

    @staticmethod
    def is_valid_transition(from_state: LifecycleState,
                            to_state: LifecycleState) -> bool:
        allowed = _VALID_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    @staticmethod
    def validate_transition(from_state: LifecycleState,
                            to_state: LifecycleState) -> None:
        if not LifecycleStateMachine.is_valid_transition(from_state, to_state):
            raise ValueError(
                f"Invalid lifecycle transition: {from_state.value} -> {to_state.value}. "
                f"Allowed: {[s.value for s in _VALID_TRANSITIONS.get(from_state, set())]}"
            )

    @staticmethod
    def is_terminal(state: LifecycleState) -> bool:
        return state in (
            LifecycleState.COMMITTED,
            LifecycleState.COMPENSATED,
            LifecycleState.FAILED,
        )

    @staticmethod
    def validate_sequence(expected: int, actual: int) -> None:
        if actual != expected:
            raise ValueError(
                f"Sequence gap: expected {expected}, got {actual}. "
                "Events may have been lost."
            )

    @staticmethod
    def allowed_transitions(state: LifecycleState) -> list[LifecycleState]:
        return sorted(_VALID_TRANSITIONS.get(state, set()), key=lambda s: s.value)
