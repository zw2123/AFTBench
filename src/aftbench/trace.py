"""JSONL trace writer."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .schemas import TraceEvent


class TraceWriter:
    """Thread-safe append-only JSONL trace writer."""

    def __init__(self, output_path: str | Path):
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sequence = 0
        self._fh = open(self._path, "a")
        self._events_cache: list[dict] = []  # Cache events for retrieval

    def write_event(
        self,
        event_type: str,
        component: str,
        run_id: str,
        task_id: str,
        world: str,
        interface_condition: str,
        agent_id: str,
        fault_id: str | None = None,
        invocation_id: str | None = None,
        logical_effect_id: str | None = None,
        idempotency_key: str | None = None,
        backend_operation_id: str | None = None,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TraceEvent:
        with self._lock:
            self._sequence += 1
            event = TraceEvent(
                run_id=run_id,
                task_id=task_id,
                world=world,
                interface_condition=interface_condition,
                agent_id=agent_id,
                fault_id=fault_id,
                timestamp=time.time(),
                monotonic_sequence=self._sequence,
                event_type=event_type,
                component=component,
                invocation_id=invocation_id,
                logical_effect_id=logical_effect_id,
                idempotency_key=idempotency_key,
                backend_operation_id=backend_operation_id,
                resource_id=resource_id,
                payload=payload or {},
            )
            event_dict = event.to_dict()
            self._fh.write(json.dumps(event_dict, default=str) + "\n")
            self._events_cache.append(event_dict)  # Cache for retrieval
            return event

    def get_events_for_run(self, run_id: str) -> list[dict]:
        """Get all trace events for a specific run."""
        with self._lock:
            return [e for e in self._events_cache if e.get('run_id') == run_id]

    def flush(self):
        with self._lock:
            self._fh.flush()

    def close(self):
        with self._lock:
            self._fh.flush()
            self._fh.close()

    @property
    def path(self) -> Path:
        return self._path
