"""Abstract base class for all AFTBench worlds."""

from __future__ import annotations

import abc
import hashlib
import json
from typing import Any


class World(abc.ABC):
    """Base class for benchmark worlds.

    A world encapsulates the backend state that interfaces operate on.
    All interfaces for a given task MUST use the same world instance so
    that the parity invariant holds: differences in agent performance
    are attributable to interface contracts, not backend differences.
    """

    def __init__(self) -> None:
        self._initial_state: dict[str, Any] | None = None

    @abc.abstractmethod
    def reset(self, seed: int) -> None:
        """Reset to a deterministic initial state.

        The seed allows reproducible randomization (e.g. catalog ordering).
        After reset the world must be in a well-known state suitable for
        task execution.
        """

    @abc.abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return a snapshot of the current world state.

        The snapshot must be a plain dict (JSON-serializable) so it can
        be used for postcondition verification and hashing.
        """

    @abc.abstractmethod
    def verify_postconditions(self, task: dict[str, Any], state: dict[str, Any]) -> bool:
        """Verify that the state satisfies the task's postconditions.

        Returns True if all postconditions hold.
        """

    @abc.abstractmethod
    def verify_safety_predicates(self, task: dict[str, Any], state: dict[str, Any]) -> bool:
        """Verify that no safety predicates have been violated.

        Safety predicates are invariants that must hold regardless of
        what the task asks for (e.g. no unauthorized deletions).
        Returns True if all safety predicates hold.
        """

    @abc.abstractmethod
    def apply_effect(self, effect: dict[str, Any]) -> dict[str, Any]:
        """Apply a backend effect and return the result.

        Effects are the canonical operations that interfaces translate
        into.  Every interface must ultimately call apply_effect to
        mutate the world.  This is the parity invariant: all interfaces
        go through the same backend operations.
        """

    @abc.abstractmethod
    def get_object_version(self, obj_id: str) -> str:
        """Return the current version string for an object.

        Versions change on every mutation and are used for optimistic
        concurrency control and stale-state detection.
        """

    def get_initial_state_hash(self) -> str:
        """Return a deterministic hash of the initial state.

        Used to verify that the world was properly reset and that
        no pre-task mutations occurred.
        """
        if self._initial_state is None:
            self._initial_state = self.get_state()
        raw = json.dumps(self._initial_state, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
