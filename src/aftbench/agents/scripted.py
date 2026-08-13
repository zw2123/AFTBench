"""Deterministic scripted agent using keyword matching and fixed policies."""

from __future__ import annotations

import logging
from typing import Any

from .base import Agent

logger = logging.getLogger(__name__)

# Keyword → capability-name mapping for tool selection
_KEYWORD_MAP: dict[str, list[str]] = {
    "create": ["create", "add", "insert", "new", "register"],
    "delete": ["delete", "remove", "destroy", "drop", "unregister"],
    "update": ["update", "modify", "edit", "patch", "change"],
    "read": ["read", "get", "fetch", "query", "list", "describe"],
    "transfer": ["transfer", "move", "send", "ship", "dispatch"],
    "cancel": ["cancel", "abort", "revoke", "withdraw"],
    "approve": ["approve", "accept", "confirm", "authorize"],
    "assign": ["assign", "allocate", "grant", "designate"],
}

# Maximum retries before aborting
_MAX_RETRIES = 2


class ScriptedAgent(Agent):
    """Deterministic agent that uses keyword matching and fixed retry policies.

    This agent never accesses oracle state.  Under weak interfaces (I0) with
    ambiguous capability names it may select the wrong tool, producing
    realistic failures.
    """

    def __init__(self, agent_id: str = "scripted-v1") -> None:
        self._id = agent_id
        self._retry_count: int = 0
        self._last_capability: str | None = None

    # ------------------------------------------------------------------
    # Agent interface
    # ------------------------------------------------------------------

    def select_tool(
        self,
        discovery_results: list[dict[str, Any]],
        task: dict[str, Any],
    ) -> str | None:
        if not discovery_results:
            return None

        task_desc = task.get("description", "").lower()
        task_operation = task.get("operation", "").lower()
        combined = f"{task_desc} {task_operation}"

        # Score each capability by keyword overlap
        best_cap: str | None = None
        best_score: int = -1

        for cap in discovery_results:
            cap_id = cap.get("capability_id", "")
            cap_name = cap.get("name", "").lower()
            cap_desc = cap.get("description", "").lower()
            cap_text = f"{cap_id} {cap_name} {cap_desc}"

            score = 0.0
            for action_keywords in _KEYWORD_MAP.values():
                for kw in action_keywords:
                    if kw in combined and kw in cap_text:
                        score += 1.0
            # Tie-breaker: shared non-action words signal semantic match.
            task_words = set(w for w in combined.split() if len(w) > 2)
            cap_words = set(cap_text.split())
            all_action_kws = {kw for kws in _KEYWORD_MAP.values() for kw in kws}
            score += 0.01 * len(task_words & cap_words - all_action_kws)
            # Prefer canonical (non-generated) capabilities on exact ties.
            if not any(ch.isdigit() for ch in cap_id):
                score += 0.0001
            if score > best_score:
                best_score = score
                best_cap = cap_id

        # Under I0 with ambiguous names, first match may be wrong — that is
        # the intended realistic failure mode.
        if best_score == 0:
            # Fall back to first capability (may be wrong under ambiguity)
            best_cap = discovery_results[0].get("capability_id")

        self._last_capability = best_cap
        return best_cap

    def build_params(
        self,
        capability_id: str,
        schema: dict[str, Any],
        task: dict[str, Any],
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        # Schemas may either expose "properties" directly or wrap it inside
        # "input_schema" (I1-family interfaces).
        if isinstance(schema, dict) and isinstance(schema.get("input_schema"), dict):
            schema = schema["input_schema"]
        properties = schema.get("properties", {})

        for param_name, param_schema in properties.items():
            # Try to fill from task parameters
            task_params = task.get("parameters", {})
            if param_name in task_params:
                params[param_name] = task_params[param_name]
            elif param_name in task:
                params[param_name] = task[param_name]
            else:
                # Use default if available
                if "default" in param_schema:
                    params[param_name] = param_schema["default"]
                elif param_schema.get("type") == "string":
                    params[param_name] = ""
                elif param_schema.get("type") == "integer":
                    params[param_name] = 0
                elif param_schema.get("type") == "boolean":
                    params[param_name] = False

        # Include idempotency key when schema expects one
        if "idempotency_key" in properties:
            params.setdefault(
                "idempotency_key",
                task.get("idempotency_key", f"idem-{task.get('task_id', 'unknown')}"),
            )

        return params

    def handle_response(
        self,
        response: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        status = response.get("status", "unknown")

        if status == "success" or status == "committed":
            self._retry_count = 0
            return "done"

        if status == "partial":
            # Check if lifecycle-aware interface is available for resume
            if response.get("lifecycle_token") or response.get("execution_handle"):
                self._retry_count = 0
                return "resume"
            # Check if reconciliation (I5) is available
            if response.get("reconciliation_available", False):
                self._retry_count = 0
                return "reconcile"
            # No recovery path — abort
            return "abort"

        if status == "pending":
            if self._retry_count < _MAX_RETRIES:
                self._retry_count += 1
                return "retry"
            return "abort"

        if status == "unknown_outcome":
            # Unknown outcome: prefer reconciliation when available
            if response.get("reconciliation_available", False):
                self._retry_count = 0
                return "reconcile"
            return "abort"

        # Generic failure
        if self._retry_count < _MAX_RETRIES:
            self._retry_count += 1
            return "retry"
        return "abort"

    def handle_error(
        self,
        error: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        error_type = error.get("type", "unknown")
        structured = error.get("structured", False)

        if not structured:
            # Unstructured errors: retry up to limit
            if self._retry_count < _MAX_RETRIES:
                self._retry_count += 1
                return "retry"
            return "abort"

        # Structured error handling with fixed retry policy
        if error_type in ("TRANSIENT", "TIMEOUT"):
            if self._retry_count < _MAX_RETRIES:
                self._retry_count += 1
                return "retry"
            return "abort"

        if error_type == "VERSION_CONFLICT":
            if error.get("current_version"):
                self._retry_count = 0
                return "refresh_and_retry"
            return "abort"

        if error_type == "PARTIAL_FAILURE":
            if error.get("lifecycle_token") or error.get("execution_handle"):
                return "resume"
            if error.get("reconciliation_available", False):
                return "reconcile"
            return "abort"

        if error_type in ("PERMISSION_DENIED", "NOT_FOUND", "INVALID_STATE"):
            # Non-retryable
            return "abort"

        # Default: retry with limit
        if self._retry_count < _MAX_RETRIES:
            self._retry_count += 1
            return "retry"
        return "abort"

    def agent_id(self) -> str:
        return self._id
