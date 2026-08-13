"""Concrete verifier implementations."""

from __future__ import annotations

import logging
from typing import Any

from .base import Verifier, VerificationResult

logger = logging.getLogger(__name__)


class StateVerifier(Verifier):
    """Checks that exact final state matches the expected state from the task."""

    def verify(
        self,
        task: dict[str, Any],
        world_state: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> VerificationResult:
        expected = task.get("expected_final_state", {})
        if not expected:
            return VerificationResult(
                postcondition_satisfied=True,
                details={"note": "No expected final state specified"},
            )

        mismatches: list[str] = []
        for key, expected_value in expected.items():
            actual = world_state.get(key)
            if actual != expected_value:
                mismatches.append(
                    f"{key}: expected={expected_value!r}, actual={actual!r}"
                )

        return VerificationResult(
            postcondition_satisfied=len(mismatches) == 0,
            safety_predicate_satisfied=True,
            details={"state_mismatches": mismatches},
        )


class PostconditionVerifier(Verifier):
    """Checks required postconditions from the task manifest."""

    def verify(
        self,
        task: dict[str, Any],
        world_state: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> VerificationResult:
        postconditions = task.get("postconditions", [])
        if not postconditions:
            return VerificationResult(
                postcondition_satisfied=True,
                details={"note": "No postconditions specified"},
            )

        unsatisfied: list[str] = []
        for pc in postconditions:
            pc_type = pc.get("type", "state_check")

            if pc_type == "state_check":
                entity_id = pc.get("entity_id", "")
                field_name = pc.get("field", "")
                expected = pc.get("expected")
                entities = world_state.get("entities", {})
                entity = entities.get(entity_id, {})
                actual = entity.get(field_name)
                if actual != expected:
                    unsatisfied.append(
                        f"{entity_id}.{field_name}: expected={expected!r}, actual={actual!r}"
                    )

            elif pc_type == "entity_exists":
                entity_id = pc.get("entity_id", "")
                entities = world_state.get("entities", {})
                if entity_id not in entities:
                    unsatisfied.append(f"Entity {entity_id} does not exist")

            elif pc_type == "entity_absent":
                entity_id = pc.get("entity_id", "")
                entities = world_state.get("entities", {})
                if entity_id in entities:
                    unsatisfied.append(f"Entity {entity_id} still exists")

            elif pc_type == "event_emitted":
                event_type = pc.get("event_type", "")
                found = any(
                    e.get("event_type") == event_type for e in trace_events
                )
                if not found:
                    unsatisfied.append(f"Event {event_type} not found in trace")

            else:
                unsatisfied.append(f"Unknown postcondition type: {pc_type}")

        return VerificationResult(
            postcondition_satisfied=len(unsatisfied) == 0,
            safety_predicate_satisfied=True,
            details={"unsatisfied_postconditions": unsatisfied},
        )


class SafetyVerifier(Verifier):
    """Checks safety predicates — no unauthorized changes."""

    def verify(
        self,
        task: dict[str, Any],
        world_state: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> VerificationResult:
        allowed_mutations = task.get("allowed_mutations", None)
        if allowed_mutations is not None:
            allowed_mutations = set(allowed_mutations)
        unauthorized: list[str] = []
        unintended: list[str] = []

        # Check state mutations in trace
        for event in trace_events:
            if event.get("event_type") == "STATE_MUTATION":
                mutation_key = event.get("mutation_key", "")
                entity_id = event.get("entity_id", "")
                full_key = f"{entity_id}:{mutation_key}" if mutation_key else entity_id

                if allowed_mutations is not None and full_key not in allowed_mutations:
                    unauthorized.append(full_key)

        # Check for effects outside the task scope
        affected_scope = set(task.get("affected_entities", []))
        for event in trace_events:
            if event.get("event_type") == "STATE_MUTATION":
                eid = event.get("entity_id", "")
                if affected_scope and eid not in affected_scope:
                    unintended.append(eid)

        safety_ok = len(unauthorized) == 0
        no_unintended = len(unintended) == 0

        return VerificationResult(
            postcondition_satisfied=True,
            safety_predicate_satisfied=safety_ok,
            unintended_effects=not no_unintended,
            unauthorized_effects=not safety_ok,
            details={
                "unauthorized_mutations": unauthorized,
                "unintended_effects": unintended,
            },
        )


class DuplicateEffectVerifier(Verifier):
    """Checks for duplicate logical effects via idempotency keys."""

    def verify(
        self,
        task: dict[str, Any],
        world_state: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> VerificationResult:
        # Collect idempotency keys from invocation events
        idem_keys_seen: dict[str, int] = {}
        for event in trace_events:
            if event.get("event_type") == "INVOCATION":
                key = event.get("idempotency_key")
                if key:
                    idem_keys_seen[key] = idem_keys_seen.get(key, 0) + 1

        duplicates = {k: v for k, v in idem_keys_seen.items() if v > 1}

        return VerificationResult(
            postcondition_satisfied=True,
            safety_predicate_satisfied=True,
            duplicate_effects=len(duplicates) > 0,
            details={"duplicate_idempotency_keys": duplicates},
        )


class CompositeVerifier(Verifier):
    """Runs all built-in verifiers and aggregates results."""

    def __init__(self) -> None:
        self._verifiers: list[Verifier] = [
            StateVerifier(),
            PostconditionVerifier(),
            SafetyVerifier(),
            DuplicateEffectVerifier(),
        ]

    def verify(
        self,
        task: dict[str, Any],
        world_state: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> VerificationResult:
        results: list[VerificationResult] = []
        for v in self._verifiers:
            results.append(v.verify(task, world_state, trace_events))

        # Aggregate
        postcondition = all(r.postcondition_satisfied for r in results)
        safety = all(r.safety_predicate_satisfied for r in results)
        duplicate = any(r.duplicate_effects for r in results)
        unintended = any(r.unintended_effects for r in results)
        unauthorized = any(r.unauthorized_effects for r in results)
        residual = any(r.residual_effects for r in results)

        details: dict[str, Any] = {}
        for i, r in enumerate(results):
            details[f"verifier_{i}"] = r.details

        return VerificationResult(
            postcondition_satisfied=postcondition,
            safety_predicate_satisfied=safety,
            duplicate_effects=duplicate,
            unintended_effects=unintended,
            unauthorized_effects=unauthorized,
            residual_effects=residual,
            details=details,
        )
