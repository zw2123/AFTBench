"""Capability-aware scripted agent that uses interface primitives when available."""

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


class CapabilityAwareAgent(Agent):
    """Capability-aware agent that uses interface primitives when available.
    
    This agent:
    - Detects available capabilities from response metadata
    - Uses capabilities only when exposed by the interface
    - Records capability usage for tracing
    - Does not branch on interface names
    - Follows a unified policy across all interfaces
    """

    def __init__(self, agent_id: str = "capability-aware-v1") -> None:
        self._id = agent_id
        self._retry_count: int = 0
        self._last_capability: str | None = None
        self._capability_usage: list[dict] = []  # Track capability usage
        self._invocation_id: str | None = None  # Track current invocation
        self._logical_effect_id: str | None = None  # Track logical effect

    # ------------------------------------------------------------------
    # Capability detection and usage tracking
    # ------------------------------------------------------------------

    def _detect_capabilities(self, response: dict[str, Any]) -> dict[str, bool]:
        """Detect available capabilities from response metadata."""
        capabilities = {
            "status_query": False,
            "invocation_resume": False,
            "reconciliation": False,
            "idempotent_retry": False,
            "version_refresh": False,
            "authority_revalidation": False,
            "verification": False,
            "discovery_fallback": False,
        }
        
        # Status query: response has invocation_id and status field
        if response.get("invocation_id") and "status" in response:
            capabilities["status_query"] = True
        
        # Invocation resume: response has lifecycle_token or execution_handle
        if response.get("lifecycle_token") or response.get("execution_handle"):
            capabilities["invocation_resume"] = True
        
        # Reconciliation: response indicates reconciliation available
        if response.get("reconciliation_available", False):
            capabilities["reconciliation"] = True
        
        # Idempotent retry: response has idempotency_key or effect_committed
        if response.get("idempotency_key") or response.get("effect_committed"):
            capabilities["idempotent_retry"] = True
        
        # Version refresh: response has version field and error indicates conflict
        if response.get("version") or response.get("current_version"):
            capabilities["version_refresh"] = True
        
        # Authority revalidation: error indicates permission issue
        if response.get("error_code") in ("PERMISSION_DENIED", "AUTHORIZATION_REQUIRED"):
            capabilities["authority_revalidation"] = True
        
        # Verification: response has verification evidence
        if response.get("verification_evidence") or response.get("postcondition_check"):
            capabilities["verification"] = True
        
        # Discovery fallback: discovery returned empty or error
        # (This is detected in select_tool, not here)
        
        return capabilities

    def _record_capability_usage(self, capability: str, context: dict[str, Any]) -> None:
        """Record capability usage for tracing."""
        self._capability_usage.append({
            "capability": capability,
            "invocation_id": self._invocation_id,
            "logical_effect_id": self._logical_effect_id,
            "context": context,
        })
        logger.debug(f"Capability used: {capability} (inv={self._invocation_id})")

    def get_capability_usage(self) -> list[dict]:
        """Get recorded capability usage for tracing."""
        return self._capability_usage.copy()

    # ------------------------------------------------------------------
    # Agent interface
    # ------------------------------------------------------------------

    def select_tool(
        self,
        discovery_results: list[dict[str, Any]],
        task: dict[str, Any],
    ) -> str | None:
        if not discovery_results:
            # Discovery fallback: try to use task metadata
            allowed = task.get("allowed_capabilities", [])
            if allowed:
                self._record_capability_usage("discovery_fallback", {
                    "reason": "empty_discovery",
                    "fallback_to": allowed[0],
                })
                return allowed[0]
            return None

        # Priority 1: Use allowed_capabilities from task if available
        allowed = task.get("allowed_capabilities", [])
        if allowed:
            # Find the first allowed capability that's in discovery_results
            discovery_ids = {cap.get("capability_id") for cap in discovery_results}
            for allowed_cap in allowed:
                if allowed_cap in discovery_ids:
                    self._record_capability_usage("allowed_capability", {
                        "capability": allowed_cap,
                        "source": "task.allowed_capabilities",
                    })
                    return allowed_cap
            
            # If no allowed capability in discovery, fall back to first allowed
            self._record_capability_usage("discovery_fallback", {
                "reason": "allowed_not_in_discovery",
                "fallback_to": allowed[0],
            })
            return allowed[0]

        # Priority 2: Keyword matching from discovery_results
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
            self._record_capability_usage("discovery_fallback", {
                "reason": "no_keyword_match",
                "fallback_to": best_cap,
            })

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
        
        # Track invocation and effect IDs
        if response.get("invocation_id"):
            self._invocation_id = response["invocation_id"]
        if response.get("logical_effect_id"):
            self._logical_effect_id = response["logical_effect_id"]

        # Detect available capabilities
        capabilities = self._detect_capabilities(response)

        if status == "success" or status == "committed":
            # Check if verification is available and should be used
            if capabilities["verification"]:
                self._record_capability_usage("verification", {
                    "status": status,
                    "evidence": response.get("verification_evidence"),
                })
            
            self._retry_count = 0
            return "done"

        if status == "partial":
            # Use invocation resume if available
            if capabilities["invocation_resume"]:
                self._record_capability_usage("invocation_resume", {
                    "status": status,
                    "lifecycle_token": response.get("lifecycle_token"),
                })
                self._retry_count = 0
                return "resume"
            
            # Use reconciliation if available
            if capabilities["reconciliation"]:
                self._record_capability_usage("reconciliation", {
                    "status": status,
                    "reason": "partial_completion",
                })
                self._retry_count = 0
                return "reconcile"
            
            # No recovery path — abort
            return "abort"

        if status == "pending":
            # Use status query if available
            if capabilities["status_query"]:
                self._record_capability_usage("status_query", {
                    "status": status,
                    "invocation_id": self._invocation_id,
                })
            
            if self._retry_count < _MAX_RETRIES:
                # Use idempotent retry if available
                if capabilities["idempotent_retry"]:
                    self._record_capability_usage("idempotent_retry", {
                        "status": status,
                        "retry_count": self._retry_count,
                    })
                
                self._retry_count += 1
                return "retry"
            return "abort"

        if status == "unknown_outcome":
            # Use reconciliation if available
            if capabilities["reconciliation"]:
                self._record_capability_usage("reconciliation", {
                    "status": status,
                    "invocation_id": self._invocation_id,
                })
                self._retry_count = 0
                return "reconcile"
            
            # Use idempotent retry if effect was committed
            if capabilities["idempotent_retry"]:
                self._record_capability_usage("idempotent_retry", {
                    "status": status,
                    "reason": "unknown_outcome",
                })
                self._retry_count = 0
                return "retry"
            
            return "abort"

        if status == "error":
            error_code = response.get("error_code", "")
            
            # Version conflict: use version refresh
            if error_code == "VERSION_CONFLICT" and capabilities["version_refresh"]:
                self._record_capability_usage("version_refresh", {
                    "error_code": error_code,
                    "current_version": response.get("current_version"),
                })
                self._retry_count = 0
                return "refresh_and_retry"
            
            # Permission denied: use authority revalidation
            if error_code in ("PERMISSION_DENIED", "AUTHORIZATION_REQUIRED"):
                if capabilities["authority_revalidation"]:
                    self._record_capability_usage("authority_revalidation", {
                        "error_code": error_code,
                    })
                return "abort"  # Safe refusal
            
            # Not found: safe refusal
            if error_code == "NOT_FOUND":
                return "abort"
        
        # Generic failure
        if self._retry_count < _MAX_RETRIES:
            # Use idempotent retry if available
            if capabilities["idempotent_retry"]:
                self._record_capability_usage("idempotent_retry", {
                    "status": status,
                    "retry_count": self._retry_count,
                })
            
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

        # Structured error handling with capability-aware policy
        if error_type in ("TRANSIENT", "TIMEOUT"):
            if self._retry_count < _MAX_RETRIES:
                self._retry_count += 1
                return "retry"
            return "abort"

        if error_type == "VERSION_CONFLICT":
            # Only interfaces that expose the fresh version can refresh.
            if error.get("current_version"):
                self._record_capability_usage("version_refresh", {
                    "error_type": error_type,
                    "current_version": error.get("current_version"),
                })
                self._retry_count = 0
                return "refresh_and_retry"
            return "abort"

        if error_type == "PARTIAL_FAILURE":
            if error.get("lifecycle_token") or error.get("execution_handle"):
                self._record_capability_usage("invocation_resume", {
                    "error_type": error_type,
                })
                return "resume"
            if error.get("reconciliation_available", False):
                self._record_capability_usage("reconciliation", {
                    "error_type": error_type,
                })
                return "reconcile"
            return "abort"

        if error_type in ("PERMISSION_DENIED", "NOT_FOUND", "INVALID_STATE", "INTERNAL_FAILURE"):
            # Safe refusal
            self._record_capability_usage("safe_refusal", {
                "error_type": error_type,
            })
            return "abort"

        # Default: retry with limit
        if self._retry_count < _MAX_RETRIES:
            self._retry_count += 1
            return "retry"
        return "abort"

    def agent_id(self) -> str:
        return self._id
