"""Data schemas for tasks, traces, results, and configurations."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class FaultType(str, Enum):
    ENTITY_AMBIGUITY = "entity_ambiguity"
    FAILURE_BEFORE_EFFECT = "failure_before_effect"
    LOST_RESPONSE_AFTER_EFFECT = "lost_response_after_effect"
    PARTIAL_COMPLETION = "partial_completion"
    INTERRUPTED_EXECUTION = "interrupted_execution"
    STALE_STATE = "stale_state"
    PERMISSION_DRIFT = "permission_drift"
    EVENT_LOSS = "event_loss"
    HANDLE_EXPIRATION = "handle_expiration"
    TOOL_EVOLUTION = "tool_evolution"
    FALSE_SUCCESS = "false_success"
    FALSE_FAILURE = "false_failure"
    # Note: TOOL_CONFUSION and CATALOG_SCALE are workload factors, not faults


class WorkloadFactor(str, Enum):
    """Workload factors that affect task difficulty but are not execution faults."""
    CATALOG_SIZE = "catalog_size"
    TOOL_CONFUSION = "tool_confusion"
    ENTITY_AMBIGUITY_LEVEL = "entity_ambiguity_level"
    WORKFLOW_LENGTH = "workflow_length"
    EFFECT_SEVERITY = "effect_severity"
    APPROVAL_REQUIRED = "approval_required"


class LifecycleState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    PAUSED = "paused"
    COMMITTED = "committed"
    COMPENSATED = "compensated"
    FAILED = "failed"
    UNKNOWN = "unknown"


class EffectClass(str, Enum):
    READ_ONLY = "read_only"
    MUTABLE = "mutable"
    REVERSIBLE = "reversible"
    COMPENSATABLE = "compensatable"
    IRREVERSIBLE = "irreversible"


@dataclass
class TaskManifest:
    task_id: str = ""
    world: str = ""
    instruction: str = ""
    initial_state_ref: str = ""
    allowed_capabilities: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    required_postconditions: list[str] = field(default_factory=list)
    safety_predicates: list[str] = field(default_factory=list)
    # Workload factors
    effect_severity: str = "mutable"
    workflow_length: str = "short"
    catalog_size: int = 10
    tool_confusion_level: str | None = None
    entity_ambiguity_level: str | None = None
    approval_required: bool | None = None
    fault_compatible_points: list[str] = field(default_factory=list)
    execution_budget: dict[str, int] = field(default_factory=lambda: {"max_turns": 10, "max_tool_calls": 8})
    expected_evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    acceptable_outcomes: list[str] = field(default_factory=lambda: ["completed_as_requested"])

    @classmethod
    def from_dict(cls, d: dict) -> TaskManifest:
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class FaultSchedule:
    fault_id: str = ""
    fault_type: FaultType = FaultType.ENTITY_AMBIGUITY
    target_world: str = ""
    target_operation: str | None = None
    logical_boundary: str = "after_backend"
    occurrence: str = "after_backend_before_response"
    seed: int = 42

    @classmethod
    def from_dict(cls, d: dict) -> FaultSchedule:
        if "fault_type" in d and isinstance(d["fault_type"], str):
            try:
                d = dict(d)
                d["fault_type"] = FaultType(d["fault_type"])
            except ValueError:
                pass
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class TraceEvent:
    run_id: str = ""
    task_id: str = ""
    world: str = ""
    interface_condition: str = ""
    agent_id: str = ""
    fault_id: str | None = None
    timestamp: float = 0.0
    monotonic_sequence: int = 0
    event_type: str = ""
    component: str = ""
    invocation_id: str | None = None
    logical_effect_id: str | None = None
    idempotency_key: str | None = None
    backend_operation_id: str | None = None
    resource_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultRow:
    run_id: str = ""
    task_id: str = ""
    world: str = ""
    interface_condition: str = ""
    ablation: str | None = None
    fault_type: str | None = None
    seed: int = 42
    agent_id: str = ""
    # Workload factors (separate from execution faults)
    catalog_size: int | None = None
    tool_confusion_level: str | None = None
    entity_ambiguity_level: str | None = None
    workflow_length: str | None = None
    effect_severity: str | None = None
    approval_required: bool | None = None
    # Metrics
    state_correct_completion: bool = False
    postcondition_satisfied: bool = False
    safety_predicate_satisfied: bool = True
    duplicate_effect: bool = False
    unintended_effect: bool = False
    unauthorized_effect: bool = False
    residual_effect: bool = False
    recovery_success: bool | None = None
    unknown_outcome_reconciled: bool | None = None
    human_intervention_count: int = 0
    model_turns: int = 0
    tool_calls: int = 0
    transport_retries: int = 0
    logical_reexecutions: int = 0
    context_tokens: int = 0
    tool_definition_tokens: int = 0
    tool_result_tokens: int = 0
    wall_clock_ms: int = 0
    recovery_ms: int = 0
    verification_ms: int = 0
    runtime_overhead_ms: int = 0
    terminal_agent_claim: str | None = None
    terminal_oracle_outcome: str | None = None
    initial_state_hash: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_csv_row(self) -> str:
        d = self.to_dict()
        return ",".join(_csv_val(v) for v in d.values())

    @staticmethod
    def csv_header() -> str:
        return ",".join(ResultRow.__dataclass_fields__.keys())


def _csv_val(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str) and ("," in v or '"' in v):
        return f'"{v.replace(chr(34), chr(34)+chr(34))}"'
    return str(v)


def generate_run_id() -> str:
    return str(uuid.uuid4())[:12]


def compute_state_hash(state: dict) -> str:
    canonical = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
