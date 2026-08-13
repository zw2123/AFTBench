"""Result contract: structured return from a capability invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorEnvelope:
    """Normalized error envelope used by I1+."""
    error_code: str
    message: str
    category: str  # "client_error" | "server_error" | "transient" | "not_found" | "permission"
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category,
            "retryable": self.retryable,
            "details": self.details,
        }


@dataclass
class ResultContract:
    """Structured result from a capability invocation.

    status:
        success   - operation completed fully
        failure   - operation did not complete, no partial effect
        partial   - some effects applied, some did not
        unknown   - outcome cannot be determined (e.g. response lost)
    """
    status: str  # "success" | "failure" | "partial" | "unknown"
    resource_refs: list[dict[str, str]] = field(default_factory=list)
    effect_summary: str = ""
    error_envelope: ErrorEnvelope | None = None
    evidence_ref: str | None = None
    retry_classification: str | None = None  # "safe" | "idempotent" | "unsafe" | None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "status": self.status,
            "resource_refs": self.resource_refs,
            "effect_summary": self.effect_summary,
        }
        if self.error_envelope is not None:
            d["error"] = self.error_envelope.to_dict()
        if self.evidence_ref is not None:
            d["evidence_ref"] = self.evidence_ref
        if self.retry_classification is not None:
            d["retry_classification"] = self.retry_classification
        return d

    @classmethod
    def success(cls, effect_summary: str = "",
                resource_refs: list[dict[str, str]] | None = None,
                evidence_ref: str | None = None) -> ResultContract:
        return cls(
            status="success",
            resource_refs=resource_refs or [],
            effect_summary=effect_summary,
            evidence_ref=evidence_ref,
            retry_classification="idempotent",
        )

    @classmethod
    def failure(cls, error: ErrorEnvelope) -> ResultContract:
        return cls(
            status="failure",
            error_envelope=error,
            retry_classification="safe" if not error.retryable else "idempotent",
        )

    @classmethod
    def unknown(cls, message: str = "Outcome could not be determined") -> ResultContract:
        return cls(
            status="unknown",
            effect_summary=message,
            error_envelope=ErrorEnvelope(
                error_code="UNKNOWN_OUTCOME",
                message=message,
                category="transient",
                retryable=True,
            ),
            retry_classification="idempotent",
        )
