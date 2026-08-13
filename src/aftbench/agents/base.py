"""Abstract base class for AFTBench agents."""

from __future__ import annotations

import abc
from typing import Any


class Agent(abc.ABC):
    """Abstract agent that selects tools, builds parameters, and handles outcomes."""

    @abc.abstractmethod
    def select_tool(
        self,
        discovery_results: list[dict[str, Any]],
        task: dict[str, Any],
    ) -> str | None:
        """Pick a capability id from discovery results for the current task.

        Returns the capability_id string, or None if no suitable tool is found.
        """

    @abc.abstractmethod
    def build_params(
        self,
        capability_id: str,
        schema: dict[str, Any],
        task: dict[str, Any],
    ) -> dict[str, Any]:
        """Build invocation parameters for the chosen capability."""

    @abc.abstractmethod
    def handle_response(
        self,
        response: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        """Decide next action after receiving a response.

        Returns one of: 'done', 'retry', 'resume', 'reconcile', 'abort'.
        """

    @abc.abstractmethod
    def handle_error(
        self,
        error: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        """Decide next action after receiving an error.

        Returns one of: 'done', 'retry', 'resume', 'reconcile', 'abort'.
        """

    @abc.abstractmethod
    def agent_id(self) -> str:
        """Return a stable identifier for this agent."""
