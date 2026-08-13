"""Tests for LifecycleStateMachine transitions."""

import pytest

from aftbench.contracts.invocation import LifecycleState
from aftbench.contracts.lifecycle import LifecycleStateMachine


class TestLifecycleStateMachineValidTransitions:
    """Test valid state transitions."""

    def test_created_to_running(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.CREATED, LifecycleState.RUNNING
        )

    def test_created_to_failed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.CREATED, LifecycleState.FAILED
        )

    def test_running_to_waiting_input(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.RUNNING, LifecycleState.WAITING_INPUT
        )

    def test_running_to_paused(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.RUNNING, LifecycleState.PAUSED
        )

    def test_running_to_committed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.RUNNING, LifecycleState.COMMITTED
        )

    def test_running_to_failed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.RUNNING, LifecycleState.FAILED
        )

    def test_running_to_unknown(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.RUNNING, LifecycleState.UNKNOWN
        )

    def test_waiting_input_to_running(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.WAITING_INPUT, LifecycleState.RUNNING
        )

    def test_waiting_input_to_failed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.WAITING_INPUT, LifecycleState.FAILED
        )

    def test_waiting_input_to_unknown(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.WAITING_INPUT, LifecycleState.UNKNOWN
        )

    def test_paused_to_running(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.PAUSED, LifecycleState.RUNNING
        )

    def test_paused_to_failed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.PAUSED, LifecycleState.FAILED
        )

    def test_paused_to_unknown(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.PAUSED, LifecycleState.UNKNOWN
        )

    def test_unknown_to_committed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.UNKNOWN, LifecycleState.COMMITTED
        )

    def test_unknown_to_compensated(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.UNKNOWN, LifecycleState.COMPENSATED
        )

    def test_unknown_to_failed(self):
        assert LifecycleStateMachine.is_valid_transition(
            LifecycleState.UNKNOWN, LifecycleState.FAILED
        )


class TestLifecycleStateMachineInvalidTransitions:
    """Test invalid state transitions."""

    def test_created_to_committed_invalid(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.CREATED, LifecycleState.COMMITTED
        )

    def test_created_to_paused_invalid(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.CREATED, LifecycleState.PAUSED
        )

    def test_created_to_waiting_input_invalid(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.CREATED, LifecycleState.WAITING_INPUT
        )

    def test_committed_is_terminal(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.COMMITTED, LifecycleState.RUNNING
        )

    def test_compensated_is_terminal(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.COMPENSATED, LifecycleState.RUNNING
        )

    def test_failed_is_terminal(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.FAILED, LifecycleState.RUNNING
        )

    def test_running_to_created_invalid(self):
        assert not LifecycleStateMachine.is_valid_transition(
            LifecycleState.RUNNING, LifecycleState.CREATED
        )


class TestLifecycleStateMachineValidateTransition:
    """Test validate_transition raises on invalid transitions."""

    def test_valid_transition_no_raise(self):
        LifecycleStateMachine.validate_transition(
            LifecycleState.CREATED, LifecycleState.RUNNING
        )

    def test_invalid_transition_raises(self):
        with pytest.raises(ValueError, match="Invalid lifecycle transition"):
            LifecycleStateMachine.validate_transition(
                LifecycleState.COMMITTED, LifecycleState.RUNNING
            )


class TestLifecycleStateMachineTerminalStates:
    """Test terminal state detection."""

    def test_committed_is_terminal(self):
        assert LifecycleStateMachine.is_terminal(LifecycleState.COMMITTED)

    def test_compensated_is_terminal(self):
        assert LifecycleStateMachine.is_terminal(LifecycleState.COMPENSATED)

    def test_failed_is_terminal(self):
        assert LifecycleStateMachine.is_terminal(LifecycleState.FAILED)

    def test_created_not_terminal(self):
        assert not LifecycleStateMachine.is_terminal(LifecycleState.CREATED)

    def test_running_not_terminal(self):
        assert not LifecycleStateMachine.is_terminal(LifecycleState.RUNNING)

    def test_waiting_input_not_terminal(self):
        assert not LifecycleStateMachine.is_terminal(LifecycleState.WAITING_INPUT)

    def test_paused_not_terminal(self):
        assert not LifecycleStateMachine.is_terminal(LifecycleState.PAUSED)

    def test_unknown_not_terminal(self):
        assert not LifecycleStateMachine.is_terminal(LifecycleState.UNKNOWN)


class TestLifecycleStateMachineSequence:
    """Test sequence validation."""

    def test_valid_sequence(self):
        LifecycleStateMachine.validate_sequence(1, 1)
        LifecycleStateMachine.validate_sequence(5, 5)

    def test_sequence_gap_raises(self):
        with pytest.raises(ValueError, match="Sequence gap"):
            LifecycleStateMachine.validate_sequence(1, 3)

    def test_sequence_behind_raises(self):
        with pytest.raises(ValueError, match="Sequence gap"):
            LifecycleStateMachine.validate_sequence(5, 2)


class TestLifecycleStateMachineAllowedTransitions:
    """Test allowed_transitions listing."""

    def test_created_allowed(self):
        allowed = LifecycleStateMachine.allowed_transitions(LifecycleState.CREATED)
        assert LifecycleState.RUNNING in allowed
        assert LifecycleState.FAILED in allowed
        assert len(allowed) == 2

    def test_committed_no_allowed(self):
        allowed = LifecycleStateMachine.allowed_transitions(LifecycleState.COMMITTED)
        assert len(allowed) == 0

    def test_running_has_multiple(self):
        allowed = LifecycleStateMachine.allowed_transitions(LifecycleState.RUNNING)
        assert len(allowed) >= 4  # WAITING_INPUT, PAUSED, COMMITTED, FAILED, UNKNOWN

    def test_unknown_has_three(self):
        allowed = LifecycleStateMachine.allowed_transitions(LifecycleState.UNKNOWN)
        assert LifecycleState.COMMITTED in allowed
        assert LifecycleState.COMPENSATED in allowed
        assert LifecycleState.FAILED in allowed
        assert len(allowed) == 3
