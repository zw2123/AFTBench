"""Data models for fault specification and oracle tracking."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class FaultType(enum.Enum):
    """Categories of faults that can be injected."""
    ENTITY_AMBIGUITY = "ENTITY_AMBIGUITY"
    FAILURE_BEFORE_EFFECT = "FAILURE_BEFORE_EFFECT"
    LOST_RESPONSE_AFTER_EFFECT = "LOST_RESPONSE_AFTER_EFFECT"
    PARTIAL_COMPLETION = "PARTIAL_COMPLETION"
    INTERRUPTED_EXECUTION = "INTERRUPTED_EXECUTION"
    STALE_STATE = "STALE_STATE"
    PERMISSION_DRIFT = "PERMISSION_DRIFT"
    EVENT_LOSS = "EVENT_LOSS"
    HANDLE_EXPIRATION = "HANDLE_EXPIRATION"
    TOOL_EVOLUTION = "TOOL_EVOLUTION"


class FaultOccurrence(enum.Enum):
    """When in the request lifecycle the fault occurs."""
    BEFORE_BACKEND = "BEFORE_BACKEND"
    AFTER_BACKEND_BEFORE_RESPONSE = "AFTER_BACKEND_BEFORE_RESPONSE"
    DURING_EXECUTION = "DURING_EXECUTION"
    AT_COMMIT = "AT_COMMIT"


@dataclass
class FaultSpec:
    """Specification for a single fault to inject."""
    fault_id: str
    fault_type: FaultType
    target_world: str
    target_operation: str
    logical_boundary: str
    occurrence: FaultOccurrence
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_id": self.fault_id,
            "fault_type": self.fault_type.value,
            "target_world": self.target_world,
            "target_operation": self.target_operation,
            "logical_boundary": self.logical_boundary,
            "occurrence": self.occurrence.value,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FaultSpec":
        return cls(
            fault_id=data["fault_id"],
            fault_type=FaultType(data["fault_type"]),
            target_world=data["target_world"],
            target_operation=data["target_operation"],
            logical_boundary=data["logical_boundary"],
            occurrence=FaultOccurrence(data["occurrence"]),
            seed=data.get("seed", 0),
        )


@dataclass
class FaultOracle:
    """Tracks ground truth about the request lifecycle for verification.

    This oracle records what *actually* happened at each stage, independent
    of what the agent or interface observed.
    """
    request_received: bool = False
    backend_started: bool = False
    stage_reached: int = 0
    total_stages: int = 0
    commit_status: str = "none"  # none | partial | full | rolled_back
    response_generated: bool = False
    response_delivered: bool = False
    compensation_applied: bool = False
    final_state: dict[str, Any] = field(default_factory=dict)

    # Detailed stage tracking
    stages_completed: list[str] = field(default_factory=list)
    events_emitted: list[dict[str, Any]] = field(default_factory=list)
    state_mutations: list[dict[str, Any]] = field(default_factory=list)

    def record_stage(self, stage_name: str) -> None:
        """Record that a stage was completed."""
        self.stages_completed.append(stage_name)
        self.stage_reached += 1

    def record_mutation(self, entity_id: str, field_name: str, old: Any, new: Any) -> None:
        """Record a state mutation."""
        self.state_mutations.append({
            "entity_id": entity_id,
            "field": field_name,
            "old_value": old,
            "new_value": new,
        })

    def record_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Record a lifecycle event."""
        self.events_emitted.append({
            "event_type": event_type,
            "payload": payload or {},
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_received": self.request_received,
            "backend_started": self.backend_started,
            "stage_reached": self.stage_reached,
            "total_stages": self.total_stages,
            "commit_status": self.commit_status,
            "response_generated": self.response_generated,
            "response_delivered": self.response_delivered,
            "compensation_applied": self.compensation_applied,
            "final_state": self.final_state,
            "stages_completed": list(self.stages_completed),
            "events_emitted": list(self.events_emitted),
            "state_mutations": list(self.state_mutations),
        }
