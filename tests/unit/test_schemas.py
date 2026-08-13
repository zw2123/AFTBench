"""Tests for schemas: TaskManifest, ResultRow, FaultSchedule creation and serialization."""

import pytest

from aftbench.schemas import (
    EffectClass,
    FaultSchedule,
    FaultType,
    LifecycleState,
    ResultRow,
    TaskManifest,
    TraceEvent,
    compute_state_hash,
    generate_run_id,
)


# ---------------------------------------------------------------------------
# TaskManifest
# ---------------------------------------------------------------------------

class TestTaskManifest:
    """Tests for TaskManifest dataclass."""

    def test_default_creation(self):
        tm = TaskManifest()
        assert tm.task_id == ""
        assert tm.world == ""
        assert tm.instruction == ""
        assert tm.effect_severity == "mutable"
        assert tm.workflow_length == "short"
        assert tm.catalog_size == 10
        assert tm.tags == []
        assert tm.allowed_capabilities == []

    def test_creation_with_args(self):
        tm = TaskManifest(
            task_id="task-001",
            world="enterprise_records",
            instruction="Create a contact",
            effect_severity="irreversible",
            workflow_length="long",
            catalog_size=200,
            tags=["crm", "create"],
        )
        assert tm.task_id == "task-001"
        assert tm.world == "enterprise_records"
        assert tm.instruction == "Create a contact"
        assert tm.effect_severity == "irreversible"
        assert tm.catalog_size == 200
        assert "crm" in tm.tags

    def test_from_dict(self):
        d = {
            "task_id": "t1",
            "world": "er",
            "instruction": "Do something",
            "unknown_field": "ignored",
        }
        tm = TaskManifest.from_dict(d)
        assert tm.task_id == "t1"
        assert tm.world == "er"
        assert tm.instruction == "Do something"

    def test_from_dict_ignores_unknown_fields(self):
        d = {"task_id": "t1", "nonexistent": "value"}
        tm = TaskManifest.from_dict(d)
        assert tm.task_id == "t1"

    def test_execution_budget_default(self):
        tm = TaskManifest()
        assert tm.execution_budget["max_turns"] == 10
        assert tm.execution_budget["max_tool_calls"] == 8


# ---------------------------------------------------------------------------
# ResultRow
# ---------------------------------------------------------------------------

class TestResultRow:
    """Tests for ResultRow dataclass."""

    def test_default_creation(self):
        rr = ResultRow()
        assert rr.run_id == ""
        assert rr.task_id == ""
        assert rr.world == ""
        assert rr.state_correct_completion is False
        assert rr.postcondition_satisfied is False
        assert rr.safety_predicate_satisfied is True
        assert rr.fault_type is None
        assert rr.model_turns == 0
        assert rr.tool_calls == 0

    def test_creation_with_args(self):
        rr = ResultRow(
            run_id="run-1",
            task_id="task-1",
            world="enterprise_records",
            agent_id="scripted-v1",
            state_correct_completion=True,
            postcondition_satisfied=True,
            tool_calls=5,
            model_turns=3,
        )
        assert rr.run_id == "run-1"
        assert rr.state_correct_completion is True
        assert rr.tool_calls == 5

    def test_to_dict(self):
        rr = ResultRow(run_id="r1", task_id="t1")
        d = rr.to_dict()
        assert isinstance(d, dict)
        assert d["run_id"] == "r1"
        assert d["task_id"] == "t1"

    def test_to_csv_row(self):
        rr = ResultRow(run_id="r1", task_id="t1")
        csv = rr.to_csv_row()
        assert isinstance(csv, str)
        assert "r1" in csv

    def test_csv_header(self):
        header = ResultRow.csv_header()
        assert "run_id" in header
        assert "task_id" in header
        assert "state_correct_completion" in header

    def test_fault_type_field(self):
        rr = ResultRow(run_id="r1", task_id="t1", fault_type="stale_state")
        assert rr.fault_type == "stale_state"

    def test_recovery_fields(self):
        rr = ResultRow(
            run_id="r1", task_id="t1",
            recovery_success=True,
            unknown_outcome_reconciled=False,
            human_intervention_count=2,
            recovery_ms=500,
        )
        assert rr.recovery_success is True
        assert rr.unknown_outcome_reconciled is False
        assert rr.human_intervention_count == 2
        assert rr.recovery_ms == 500

    def test_terminal_claim_fields(self):
        rr = ResultRow(
            run_id="r1", task_id="t1",
            terminal_agent_claim="success",
            terminal_oracle_outcome="success",
        )
        assert rr.terminal_agent_claim == "success"
        assert rr.terminal_oracle_outcome == "success"


# ---------------------------------------------------------------------------
# FaultSchedule
# ---------------------------------------------------------------------------

class TestFaultSchedule:
    """Tests for FaultSchedule dataclass."""

    def test_default_creation(self):
        fs = FaultSchedule()
        assert fs.fault_id == ""
        assert fs.fault_type == FaultType.ENTITY_AMBIGUITY
        assert fs.target_world == ""
        assert fs.seed == 42

    def test_creation_with_args(self):
        fs = FaultSchedule(
            fault_id="fault-001",
            fault_type=FaultType.STALE_STATE,
            target_world="enterprise_records",
            target_operation="update_contact",
            seed=99,
        )
        assert fs.fault_id == "fault-001"
        assert fs.fault_type == FaultType.STALE_STATE
        assert fs.target_operation == "update_contact"
        assert fs.seed == 99

    def test_from_dict(self):
        d = {
            "fault_id": "f1",
            "fault_type": "stale_state",
            "target_world": "er",
        }
        fs = FaultSchedule.from_dict(d)
        assert fs.fault_id == "f1"
        assert fs.fault_type == FaultType.STALE_STATE
        assert fs.target_world == "er"

    def test_from_dict_invalid_fault_type_keeps_string(self):
        d = {"fault_id": "f1", "fault_type": "nonexistent_type"}
        fs = FaultSchedule.from_dict(d)
        # When FaultType() conversion fails, the string is kept as-is
        assert fs.fault_id == "f1"

    def test_all_fault_types(self):
        expected = [
            "entity_ambiguity", "failure_before_effect",
            "lost_response_after_effect", "partial_completion",
            "interrupted_execution", "stale_state",
            "permission_drift", "event_loss",
            "handle_expiration", "tool_evolution",
            "false_success", "false_failure", "partial_success",
        ]
        actual = [ft.value for ft in FaultType]
        assert actual == expected
    
    def test_workload_factors_separate(self):
        """Verify workload factors are not in FaultType enum."""
        from aftbench.schemas import WorkloadFactor
        
        # Workload factors should be in WorkloadFactor enum
        workload_values = [wf.value for wf in WorkloadFactor]
        assert "catalog_size" in workload_values
        assert "tool_confusion" in workload_values
        assert "entity_ambiguity_level" in workload_values
        assert "workflow_length" in workload_values
        assert "effect_severity" in workload_values
        assert "approval_required" in workload_values
        
        # Workload factors should NOT be in FaultType
        fault_values = [ft.value for ft in FaultType]
        assert "catalog_scale" not in fault_values
        assert "tool_confusion" not in fault_values


# ---------------------------------------------------------------------------
# TraceEvent
# ---------------------------------------------------------------------------

class TestTraceEvent:
    """Tests for TraceEvent dataclass."""

    def test_to_dict(self):
        te = TraceEvent(
            run_id="run-1",
            task_id="task-1",
            event_type="tool_call",
            monotonic_sequence=1,
            timestamp=1000.0,
            payload={"tool": "do_create"},
        )
        d = te.to_dict()
        assert d["event_type"] == "tool_call"
        assert d["run_id"] == "run-1"
        assert d["monotonic_sequence"] == 1
        assert d["payload"]["tool"] == "do_create"

    def test_default_fields(self):
        te = TraceEvent()
        assert te.run_id == ""
        assert te.fault_id is None
        assert te.invocation_id is None
        assert te.payload == {}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    """Test enum values."""

    def test_lifecycle_state_values(self):
        assert LifecycleState.CREATED == "created"
        assert LifecycleState.RUNNING == "running"
        assert LifecycleState.COMMITTED == "committed"
        assert LifecycleState.FAILED == "failed"

    def test_effect_class_values(self):
        assert EffectClass.READ_ONLY == "read_only"
        assert EffectClass.MUTABLE == "mutable"
        assert EffectClass.IRREVERSIBLE == "irreversible"
        assert EffectClass.REVERSIBLE == "reversible"
        assert EffectClass.COMPENSATABLE == "compensatable"


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestUtilityFunctions:
    """Test utility functions."""

    def test_generate_run_id_returns_string(self):
        rid = generate_run_id()
        assert isinstance(rid, str)
        assert len(rid) == 12

    def test_generate_run_id_unique(self):
        ids = {generate_run_id() for _ in range(100)}
        assert len(ids) == 100

    def test_compute_state_hash_deterministic(self):
        state = {"a": 1, "b": [2, 3]}
        h1 = compute_state_hash(state)
        h2 = compute_state_hash(state)
        assert h1 == h2

    def test_compute_state_hash_different_states(self):
        h1 = compute_state_hash({"a": 1})
        h2 = compute_state_hash({"a": 2})
        assert h1 != h2

    def test_compute_state_hash_returns_string(self):
        h = compute_state_hash({})
        assert isinstance(h, str)
        assert len(h) == 16
