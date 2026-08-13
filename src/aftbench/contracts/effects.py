"""Effect contract: classifies the side-effects of a capability invocation."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class EffectClass(str, enum.Enum):
    READ_ONLY = "read_only"
    MUTABLE = "mutable"
    REVERSIBLE = "reversible"
    COMPENSATABLE = "compensatable"
    IRREVERSIBLE = "irreversible"


@dataclass
class CompensationStep:
    """A single step in a compensation plan."""
    action: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class EffectContract:
    """Describes the side-effect profile of a capability invocation.

    effect_class:
        read_only     - no state change
        mutable       - state changed but no external visibility
        reversible    - can be undone by the system
        compensatable - can be offset by a compensation action
        irreversible  - cannot be undone or compensated

    preview_commit_separation:
        True when the effect is not applied until an explicit commit.

    approval_required:
        True when a human/system approval step is needed before commit.
    """
    effect_class: EffectClass = EffectClass.READ_ONLY
    resource_scope: list[str] = field(default_factory=list)
    preconditions: list[dict[str, Any]] = field(default_factory=list)
    object_versions: dict[str, str] = field(default_factory=dict)
    idempotency_key: str | None = None
    preview_commit_separation: bool = False
    approval_required: bool = False
    commit_point: str | None = None  # description of what constitutes the commit
    compensation_plan: list[CompensationStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "effect_class": self.effect_class.value,
            "resource_scope": self.resource_scope,
            "preconditions": self.preconditions,
            "object_versions": self.object_versions,
        }
        if self.idempotency_key is not None:
            d["idempotency_key"] = self.idempotency_key
        if self.preview_commit_separation:
            d["preview_commit_separation"] = True
        if self.approval_required:
            d["approval_required"] = True
        if self.commit_point is not None:
            d["commit_point"] = self.commit_point
        if self.compensation_plan:
            d["compensation_plan"] = [
                {"action": s.action, "target": s.target, "params": s.params}
                for s in self.compensation_plan
            ]
        return d
