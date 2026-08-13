"""Invocation contract: tracks a single capability invocation through its lifecycle."""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class LifecycleState(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    PAUSED = "PAUSED"
    COMMITTED = "COMMITTED"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class EventEntry:
    sequence_number: int
    timestamp: float
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvocationContract:
    """Tracks a single capability invocation through its lifecycle.

    Every invocation gets a stable ID and a monotonically increasing sequence
    number.  Each state transition appends an EventEntry to the event_log so
    that clients can detect lost events and reconcile.
    """

    invocation_id: str
    capability_id: str
    idempotency_key: str
    created_at: float
    lifecycle_state: LifecycleState = LifecycleState.CREATED
    sequence_number: int = 0
    event_log: list[EventEntry] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    pending_input: dict[str, Any] | None = None
    effect: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @classmethod
    def create(cls, capability_id: str, params: dict[str, Any] | None = None,
               idempotency_key: str | None = None) -> InvocationContract:
        inv_id = f"inv-{uuid.uuid4().hex[:12]}"
        now = time.time()
        inv = cls(
            invocation_id=inv_id,
            capability_id=capability_id,
            idempotency_key=idempotency_key or f"idk-{uuid.uuid4().hex[:10]}",
            created_at=now,
            lifecycle_state=LifecycleState.CREATED,
            sequence_number=0,
            params=params or {},
        )
        inv._append_event("created", {"capability_id": capability_id})
        return inv

    def _append_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self.sequence_number += 1
        entry = EventEntry(
            sequence_number=self.sequence_number,
            timestamp=time.time(),
            event_type=event_type,
            payload=payload or {},
        )
        self.event_log.append(entry)

    def transition_to(self, new_state: LifecycleState, payload: dict[str, Any] | None = None) -> None:
        old = self.lifecycle_state
        self.lifecycle_state = new_state
        self._append_event("state_transition", {
            "from": old.value,
            "to": new_state.value,
            **(payload or {}),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "capability_id": self.capability_id,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
            "lifecycle_state": self.lifecycle_state.value,
            "sequence_number": self.sequence_number,
            "event_count": len(self.event_log),
        }
