"""Fault injection logic for each fault type."""

from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass, field
from typing import Any

from .model import FaultOccurrence, FaultSpec, FaultType, FaultOracle

logger = logging.getLogger(__name__)


@dataclass
class ModifiedContext:
    """The result of fault injection — a modified invocation context."""
    world_state: dict[str, Any]
    interface_state: dict[str, Any]
    invocation_context: dict[str, Any]
    oracle_updates: dict[str, Any]
    fault_applied: bool = False
    fault_description: str = ""


class FaultInjector:
    """Injects faults into the world/interface/invocation context.

    Each fault type has specific injection logic that modifies the context
    to simulate the corresponding failure mode.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def inject(
        self,
        fault_spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        invocation_context: dict[str, Any],
    ) -> ModifiedContext:
        """Inject the specified fault and return the modified context."""
        self._rng.seed(fault_spec.seed)

        handler = _FAULT_HANDLERS.get(fault_spec.fault_type)
        if handler is None:
            logger.warning("No handler for fault type: %s", fault_spec.fault_type)
            return ModifiedContext(
                world_state=copy.deepcopy(world),
                interface_state=copy.deepcopy(interface),
                invocation_context=copy.deepcopy(invocation_context),
                oracle_updates={},
                fault_applied=False,
                fault_description=f"Unhandled fault type: {fault_spec.fault_type}",
            )

        return handler(
            self, fault_spec, world, interface, invocation_context
        )

    # ------------------------------------------------------------------
    # Per-fault-type injection methods
    # ------------------------------------------------------------------

    def _inject_entity_ambiguity(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Ensure multiple matching entities exist so the agent may pick wrong."""
        world = copy.deepcopy(world)
        interface = copy.deepcopy(interface)
        ctx = copy.deepcopy(ctx)

        entities = world.get("entities", {})
        target_op = spec.target_operation.lower()

        # Create ambiguous entities that match the operation's expected pattern
        ambiguous_entities: dict[str, Any] = {}
        base_name = target_op.replace("create_", "").replace("update_", "")
        for i in range(3):
            eid = f"{base_name}_ambiguous_{i}"
            ambiguous_entities[eid] = {
                "id": eid,
                "name": f"{base_name}_{self._rng.choice(['alpha', 'beta', 'gamma'])}",
                "type": base_name,
                "status": "active",
                "version": 1,
            }

        entities.update(ambiguous_entities)
        world["entities"] = entities

        # Ensure interface does NOT disambiguate (weak interface behaviour)
        caps = interface.get("capabilities", [])
        for cap in caps:
            if spec.target_operation in cap.get("name", ""):
                # Remove disambiguation hints from schema
                props = cap.get("schema", {}).get("properties", {})
                if "entity_id" in props:
                    props["entity_id"].pop("enum", None)
                    props["entity_id"].pop("description", None)

        return ModifiedContext(
            world_state=world,
            interface_state=interface,
            invocation_context=ctx,
            oracle_updates={
                "entity_ambiguity_introduced": True,
                "ambiguous_entity_ids": list(ambiguous_entities.keys()),
            },
            fault_applied=True,
            fault_description=f"Introduced {len(ambiguous_entities)} ambiguous entities for {spec.target_operation}",
        )

    def _inject_failure_before_effect(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Make backend raise before any state change occurs."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        ctx["backend_error"] = {
            "type": "TRANSIENT",
            "message": f"Backend failure before effect for {spec.target_operation}",
            "structured": True,
            "stage": "pre_validation",
        }
        ctx["abort_before_commit"] = True

        return ModifiedContext(
            world_state=world,  # unchanged — no effect
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "stage_reached": 0,
                "commit_status": "none",
                "response_generated": False,
                "response_delivered": False,
            },
            fault_applied=True,
            fault_description="Backend raises before any state change",
        )

    def _inject_lost_response_after_effect(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Let backend commit but drop the response."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        # Simulate the backend having committed the change
        ctx["backend_committed"] = True
        ctx["response_dropped"] = True
        ctx["response"] = None  # agent sees no response

        return ModifiedContext(
            world_state=world,
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "commit_status": "full",
                "response_generated": True,
                "response_delivered": False,
            },
            fault_applied=True,
            fault_description="Backend committed but response was lost",
        )

    def _inject_partial_completion(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Complete some stages but not all."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        total_stages = ctx.get("total_stages", 4)
        completed_stages = max(1, total_stages // 2)

        ctx["stages_completed"] = list(range(completed_stages))
        ctx["total_stages"] = total_stages
        ctx["partial_failure"] = True
        ctx["lifecycle_token"] = f"lc-{spec.fault_id}-{self._rng.randint(1000, 9999)}"

        return ModifiedContext(
            world_state=world,
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "stage_reached": completed_stages,
                "total_stages": total_stages,
                "commit_status": "partial",
                "response_generated": True,
                "response_delivered": True,
            },
            fault_applied=True,
            fault_description=f"Completed {completed_stages}/{total_stages} stages",
        )

    def _inject_interrupted_execution(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Pause mid-execution — the operation is in-flight."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        ctx["execution_interrupted"] = True
        ctx["execution_handle"] = f"exec-{spec.fault_id}-{self._rng.randint(1000, 9999)}"
        ctx["interrupted_at_stage"] = self._rng.randint(1, ctx.get("total_stages", 4) - 1)

        return ModifiedContext(
            world_state=world,
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "stage_reached": ctx["interrupted_at_stage"],
                "commit_status": "none",
                "response_generated": False,
                "response_delivered": False,
            },
            fault_applied=True,
            fault_description=f"Execution interrupted at stage {ctx['interrupted_at_stage']}",
        )

    def _inject_stale_state(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Set object version to mismatch — optimistic concurrency failure."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        entities = world.get("entities", {})
        # Bump version on entities to create stale read
        for eid, entity in entities.items():
            if spec.target_operation in eid or spec.target_operation in entity.get("type", ""):
                entity["version"] = entity.get("version", 1) + self._rng.randint(2, 10)

        ctx["stale_version_expected"] = 1
        ctx["stale_version_actual"] = 11
        ctx["optimistic_concurrency_error"] = True

        return ModifiedContext(
            world_state=world,
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "stage_reached": 0,
                "commit_status": "none",
                "response_generated": True,
                "response_delivered": True,
            },
            fault_applied=True,
            fault_description="Object version mismatch — stale state detected",
        )

    def _inject_permission_drift(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Change role permissions mid-execution."""
        world = copy.deepcopy(world)
        interface = copy.deepcopy(interface)
        ctx = copy.deepcopy(ctx)

        # Simulate permission change mid-flight
        ctx["initial_permissions"] = ["read", "write", "execute"]
        ctx["permissions_after_drift"] = ["read"]
        ctx["permission_drift"] = True
        ctx["permission_denied_at_stage"] = self._rng.randint(1, 3)

        return ModifiedContext(
            world_state=world,
            interface_state=interface,
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "stage_reached": ctx["permission_denied_at_stage"],
                "commit_status": "none",
                "response_generated": True,
                "response_delivered": True,
            },
            fault_applied=True,
            fault_description="Permissions revoked mid-execution",
        )

    def _inject_event_loss(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Drop or reorder lifecycle events."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        events = [
            {"seq": 1, "type": "STARTED", "payload": {}},
            {"seq": 2, "type": "STAGE_1_COMPLETE", "payload": {}},
            {"seq": 3, "type": "STAGE_2_COMPLETE", "payload": {}},
            {"seq": 4, "type": "COMMITTED", "payload": {}},
            {"seq": 5, "type": "COMPLETED", "payload": {}},
        ]

        # Drop some events and reorder others
        drop_indices = set(self._rng.sample(range(len(events)), k=min(2, len(events))))
        remaining = [e for i, e in enumerate(events) if i not in drop_indices]

        # Possibly reorder
        if len(remaining) >= 2 and self._rng.random() < 0.5:
            i, j = self._rng.sample(range(len(remaining)), 2)
            remaining[i], remaining[j] = remaining[j], remaining[i]

        ctx["emitted_events"] = remaining
        ctx["expected_events"] = events
        ctx["events_dropped"] = len(events) - len(remaining)

        return ModifiedContext(
            world_state=world,
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "events_emitted": remaining,
                "events_expected": events,
                "events_dropped": ctx["events_dropped"],
            },
            fault_applied=True,
            fault_description=f"Dropped {ctx['events_dropped']} lifecycle events",
        )

    def _inject_handle_expiration(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Invalidate the execution handle."""
        world = copy.deepcopy(world)
        ctx = copy.deepcopy(ctx)

        handle_id = f"exec-{spec.fault_id}-{self._rng.randint(1000, 9999)}"
        ctx["execution_handle"] = handle_id
        ctx["handle_expired"] = True
        ctx["handle_error"] = {
            "type": "HANDLE_EXPIRED",
            "message": f"Execution handle {handle_id} has expired",
            "structured": True,
        }

        return ModifiedContext(
            world_state=world,
            interface_state=copy.deepcopy(interface),
            invocation_context=ctx,
            oracle_updates={
                "request_received": True,
                "backend_started": True,
                "stage_reached": 1,
                "commit_status": "none",
                "response_generated": True,
                "response_delivered": True,
            },
            fault_applied=True,
            fault_description=f"Execution handle {handle_id} expired",
        )

    def _inject_tool_evolution(
        self,
        spec: FaultSpec,
        world: dict[str, Any],
        interface: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ModifiedContext:
        """Change capability schema version — the tool interface evolved."""
        world = copy.deepcopy(world)
        interface = copy.deepcopy(interface)
        ctx = copy.deepcopy(ctx)

        caps = interface.get("capabilities", [])
        for cap in caps:
            if spec.target_operation in cap.get("name", ""):
                old_version = cap.get("version", 1)
                cap["version"] = old_version + 1
                # Rename a field to break parameter mapping
                schema_props = cap.get("schema", {}).get("properties", {})
                if "name" in schema_props:
                    schema_props["display_name"] = schema_props.pop("name")
                    cap["schema"]["properties"] = schema_props
                cap["schema_changed"] = True
                ctx["old_schema_version"] = old_version
                ctx["new_schema_version"] = old_version + 1

        return ModifiedContext(
            world_state=world,
            interface_state=interface,
            invocation_context=ctx,
            oracle_updates={
                "tool_schema_evolved": True,
                "old_version": ctx.get("old_schema_version", 1),
                "new_version": ctx.get("new_schema_version", 2),
            },
            fault_applied=True,
            fault_description="Capability schema version changed",
        )


# ---------------------------------------------------------------------------
# Handler dispatch table
# ---------------------------------------------------------------------------

_FAULT_HANDLERS: dict[FaultType, Any] = {
    FaultType.ENTITY_AMBIGUITY: FaultInjector._inject_entity_ambiguity,
    FaultType.FAILURE_BEFORE_EFFECT: FaultInjector._inject_failure_before_effect,
    FaultType.LOST_RESPONSE_AFTER_EFFECT: FaultInjector._inject_lost_response_after_effect,
    FaultType.PARTIAL_COMPLETION: FaultInjector._inject_partial_completion,
    FaultType.INTERRUPTED_EXECUTION: FaultInjector._inject_interrupted_execution,
    FaultType.STALE_STATE: FaultInjector._inject_stale_state,
    FaultType.PERMISSION_DRIFT: FaultInjector._inject_permission_drift,
    FaultType.EVENT_LOSS: FaultInjector._inject_event_loss,
    FaultType.HANDLE_EXPIRATION: FaultInjector._inject_handle_expiration,
    FaultType.TOOL_EVOLUTION: FaultInjector._inject_tool_evolution,
}
