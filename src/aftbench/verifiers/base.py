"""Abstract base verifier and result dataclass."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    """Outcome of verification after a benchmark run."""
    postcondition_satisfied: bool = False
    safety_predicate_satisfied: bool = True
    duplicate_effects: bool = False
    unintended_effects: bool = False
    unauthorized_effects: bool = False
    residual_effects: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_pass(self) -> bool:
        """True when all predicates hold."""
        return (
            self.postcondition_satisfied
            and self.safety_predicate_satisfied
            and not self.duplicate_effects
            and not self.unintended_effects
            and not self.unauthorized_effects
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "postcondition_satisfied": self.postcondition_satisfied,
            "safety_predicate_satisfied": self.safety_predicate_satisfied,
            "duplicate_effects": self.duplicate_effects,
            "unintended_effects": self.unintended_effects,
            "unauthorized_effects": self.unauthorized_effects,
            "residual_effects": self.residual_effects,
            "overall_pass": self.overall_pass,
            "details": self.details,
        }


class Verifier(abc.ABC):
    """Abstract verifier that checks task outcomes."""

    @abc.abstractmethod
    def verify(
        self,
        task: dict[str, Any],
        world_state: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> VerificationResult:
        """Verify the outcome of a task execution.

        Args:
            task: The task manifest dict.
            world_state: Final state of the world after execution.
            trace_events: Ordered list of trace events from the run.

        Returns:
            VerificationResult with all predicate checks populated.
        """
