"""Tests for each fault type injection via FaultInjector."""

import pytest
import random

from aftbench.faults.injector import FaultInjector, ModifiedContext
from aftbench.faults.model import FaultOccurrence, FaultSpec, FaultType


def _make_spec(fault_type: FaultType, **overrides) -> FaultSpec:
    defaults = dict(
        fault_id="test-fault-001",
        fault_type=fault_type,
        target_world="enterprise_records",
        target_operation="create_contact",
        logical_boundary="backend",
        occurrence=FaultOccurrence.BEFORE_BACKEND,
        seed=42,
    )
    defaults.update(overrides)
    return FaultSpec(**defaults)


def _make_context():
    """Standard test context for injection."""
    world = {
        "entities": {
            "con-001": {"id": "con-001", "name": "contact_alpha", "type": "contact",
                         "status": "active", "version": 1},
        },
    }
    interface = {
        "capabilities": [
            {"name": "create_contact", "version": 1,
             "schema": {"properties": {"name": {"type": "string", "enum": ["specific"]},
                                        "entity_id": {"type": "string", "description": "the id"}}}},
        ],
    }
    invocation_context = {
        "total_stages": 4,
    }
    return world, interface, invocation_context


class TestFaultInjectorDispatch:
    """Test that the injector dispatches to the correct handler."""

    def test_all_fault_types_have_handlers(self):
        from aftbench.faults.injector import _FAULT_HANDLERS
        for ft in FaultType:
            assert ft in _FAULT_HANDLERS, f"Missing handler for {ft}"

    def test_unknown_fault_type_returns_unapplied(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.ENTITY_AMBIGUITY)
        # Force an invalid fault type by direct attribute manipulation
        spec.fault_type = "NONEXISTENT"
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is False


class TestEntityAmbiguity:
    """Test ENTITY_AMBIGUITY fault injection."""

    def test_introduces_ambiguous_entities(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.ENTITY_AMBIGUITY)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert "ambiguous_entity_ids" in result.oracle_updates
        assert len(result.oracle_updates["ambiguous_entity_ids"]) == 3

    def test_world_state_modified(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.ENTITY_AMBIGUITY)
        world, iface, ctx = _make_context()
        original_count = len(world["entities"])
        result = injector.inject(spec, world, iface, ctx)
        assert len(result.world_state["entities"]) > original_count

    def test_original_world_not_mutated(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.ENTITY_AMBIGUITY)
        world, iface, ctx = _make_context()
        original_count = len(world["entities"])
        injector.inject(spec, world, iface, ctx)
        assert len(world["entities"]) == original_count


class TestFailureBeforeEffect:
    """Test FAILURE_BEFORE_EFFECT fault injection."""

    def test_sets_backend_error(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.FAILURE_BEFORE_EFFECT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert "backend_error" in result.invocation_context
        assert result.invocation_context["backend_error"]["type"] == "TRANSIENT"

    def test_world_state_unchanged(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.FAILURE_BEFORE_EFFECT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.world_state == world

    def test_abort_before_commit_set(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.FAILURE_BEFORE_EFFECT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.invocation_context["abort_before_commit"] is True

    def test_oracle_no_response(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.FAILURE_BEFORE_EFFECT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.oracle_updates["response_delivered"] is False
        assert result.oracle_updates["commit_status"] == "none"


class TestLostResponseAfterEffect:
    """Test LOST_RESPONSE_AFTER_EFFECT fault injection."""

    def test_backend_committed_but_response_dropped(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.LOST_RESPONSE_AFTER_EFFECT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert result.invocation_context["backend_committed"] is True
        assert result.invocation_context["response_dropped"] is True
        assert result.invocation_context["response"] is None

    def test_oracle_commit_full(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.LOST_RESPONSE_AFTER_EFFECT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.oracle_updates["commit_status"] == "full"
        assert result.oracle_updates["response_generated"] is True
        assert result.oracle_updates["response_delivered"] is False


class TestPartialCompletion:
    """Test PARTIAL_COMPLETION fault injection."""

    def test_partial_stages_completed(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.PARTIAL_COMPLETION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        stages = result.invocation_context["stages_completed"]
        total = result.invocation_context["total_stages"]
        assert len(stages) < total
        assert len(stages) >= 1

    def test_lifecycle_token_provided(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.PARTIAL_COMPLETION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert "lifecycle_token" in result.invocation_context

    def test_oracle_partial_commit(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.PARTIAL_COMPLETION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.oracle_updates["commit_status"] == "partial"


class TestInterruptedExecution:
    """Test INTERRUPTED_EXECUTION fault injection."""

    def test_execution_interrupted(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.INTERRUPTED_EXECUTION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert result.invocation_context["execution_interrupted"] is True
        assert "execution_handle" in result.invocation_context

    def test_oracle_no_commit(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.INTERRUPTED_EXECUTION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.oracle_updates["commit_status"] == "none"
        assert result.oracle_updates["response_delivered"] is False


class TestStaleState:
    """Test STALE_STATE fault injection."""

    def test_version_mismatch(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.STALE_STATE)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert result.invocation_context["optimistic_concurrency_error"] is True

    def test_entity_version_bumped(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.STALE_STATE, target_operation="contact")
        world, iface, ctx = _make_context()
        original_version = world["entities"]["con-001"]["version"]
        result = injector.inject(spec, world, iface, ctx)
        new_version = result.world_state["entities"]["con-001"]["version"]
        assert new_version > original_version


class TestPermissionDrift:
    """Test PERMISSION_DRIFT fault injection."""

    def test_permissions_revoked(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.PERMISSION_DRIFT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert result.invocation_context["permission_drift"] is True
        assert len(result.invocation_context["permissions_after_drift"]) < \
               len(result.invocation_context["initial_permissions"])

    def test_oracle_permission_denied_at_stage(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.PERMISSION_DRIFT)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        # permission_denied_at_stage is in invocation_context
        assert "permission_denied_at_stage" in result.invocation_context
        # stage_reached is in oracle_updates
        assert "stage_reached" in result.oracle_updates


class TestEventLoss:
    """Test EVENT_LOSS fault injection."""

    def test_events_dropped(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.EVENT_LOSS)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        emitted = result.invocation_context["emitted_events"]
        expected = result.invocation_context["expected_events"]
        assert len(emitted) < len(expected)

    def test_oracle_tracks_dropped_count(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.EVENT_LOSS)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.oracle_updates["events_dropped"] > 0


class TestHandleExpiration:
    """Test HANDLE_EXPIRATION fault injection."""

    def test_handle_expired(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.HANDLE_EXPIRATION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert result.invocation_context["handle_expired"] is True
        assert "execution_handle" in result.invocation_context

    def test_handle_error_structured(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.HANDLE_EXPIRATION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        error = result.invocation_context["handle_error"]
        assert error["type"] == "HANDLE_EXPIRED"
        assert error["structured"] is True


class TestToolEvolution:
    """Test TOOL_EVOLUTION fault injection."""

    def test_schema_version_changed(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.TOOL_EVOLUTION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        assert result.fault_applied is True
        assert result.oracle_updates["tool_schema_evolved"] is True

    def test_field_renamed(self):
        injector = FaultInjector()
        spec = _make_spec(FaultType.TOOL_EVOLUTION)
        world, iface, ctx = _make_context()
        result = injector.inject(spec, world, iface, ctx)
        caps = result.interface_state["capabilities"]
        create_cap = [c for c in caps if "create_contact" in c.get("name", "")]
        assert len(create_cap) == 1
        props = create_cap[0]["schema"]["properties"]
        # "name" should have been renamed to "display_name"
        assert "display_name" in props
        assert "name" not in props


class TestModifiedContext:
    """Test ModifiedContext data structure."""

    def test_default_fields(self):
        mc = ModifiedContext(
            world_state={},
            interface_state={},
            invocation_context={},
            oracle_updates={},
        )
        assert mc.fault_applied is False
        assert mc.fault_description == ""

    def test_fields_populated(self):
        mc = ModifiedContext(
            world_state={"a": 1},
            interface_state={"b": 2},
            invocation_context={"c": 3},
            oracle_updates={"d": 4},
            fault_applied=True,
            fault_description="test fault",
        )
        assert mc.world_state == {"a": 1}
        assert mc.fault_applied is True
        assert mc.fault_description == "test fault"


class TestFaultSpec:
    """Test FaultSpec serialization."""

    def test_to_dict(self):
        spec = _make_spec(FaultType.ENTITY_AMBIGUITY)
        d = spec.to_dict()
        assert d["fault_id"] == "test-fault-001"
        assert d["fault_type"] == "ENTITY_AMBIGUITY"
        assert d["occurrence"] == "BEFORE_BACKEND"

    def test_from_dict_roundtrip(self):
        spec = _make_spec(FaultType.STALE_STATE, seed=99)
        d = spec.to_dict()
        restored = FaultSpec.from_dict(d)
        assert restored.fault_id == spec.fault_id
        assert restored.fault_type == spec.fault_type
        assert restored.seed == spec.seed
        assert restored.target_operation == spec.target_operation
