"""LLM-backed agent using the provider registry (multi-provider, logged).

Supports any provider profile defined in configs/llm/providers.yaml, with
per-provider pricing and cost/call limits.  All API calls are logged with
model_id, raw messages, and tool calls; no hidden chain-of-thought is used.

The agent is disabled by default: it activates only when (a) `agent: llm`
is set in the benchmark config and (b) the profile's API key is present in
the environment / .env.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .base import Agent
from ..llm.base import LLMProvider
from ..llm.registry import get_provider, load_profiles

logger = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    """Record of a single LLM API call."""
    timestamp: float
    model_id: str
    prompt_messages: list[dict[str, Any]]
    response_text: str | None
    tool_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None = None


@dataclass
class LLMAgentConfig:
    """Configuration for the LLM agent.

    ``model_id`` is the provider-profile name from providers.yaml
    (e.g. "qwen-3.7-plus").  ``provider`` may override the provider
    instance (used by tests); when None it is resolved from the registry.
    """
    model_id: str = "qwen-3.7-plus"
    cost_limit_usd: float = 5.0
    call_limit: int = 200
    temperature: float = 0.0
    max_tokens: int = 4096
    provider: LLMProvider | None = None


class LLMAgent(Agent):
    """LLM-backed agent (disabled by default; requires an API key)."""

    def __init__(
        self,
        config: LLMAgentConfig | None = None,
        agent_id: str = "llm-v1",
    ) -> None:
        self._id = agent_id
        self._config = config or LLMAgentConfig()
        self._call_log: list[LLMCallRecord] = []
        self._total_cost: float = 0.0
        self._total_calls: int = 0
        self._provider: LLMProvider | None = self._config.provider
        if self._provider is None:
            self._provider = get_provider(self._config.model_id)

    @classmethod
    def create_if_enabled(
        cls,
        config: LLMAgentConfig | None = None,
        agent_id: str = "llm-v1",
    ) -> "LLMAgent | None":
        """Factory returning None when the provider is not available."""
        cfg = config or LLMAgentConfig()
        if cfg.provider is not None:
            return cls(config=cfg, agent_id=agent_id)
        provider = get_provider(cfg.model_id)
        if provider is None:
            logger.info("LLMAgent disabled: profile %s has no key", cfg.model_id)
            return None
        return cls(config=cfg, agent_id=agent_id)

    @property
    def is_enabled(self) -> bool:
        return self._provider is not None

    @property
    def call_log(self) -> list[LLMCallRecord]:
        return list(self._call_log)

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_calls(self) -> int:
        return self._total_calls

    def _check_limits(self) -> bool:
        if self._total_cost >= self._config.cost_limit_usd:
            logger.warning("LLMAgent cost limit reached: $%.4f", self._total_cost)
            return False
        if self._total_calls >= self._config.call_limit:
            logger.warning("LLMAgent call limit reached: %d", self._total_calls)
            return False
        return True

    def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call the provider and log the record."""
        if self._provider is None:
            return {"content": None, "tool_calls": [], "error": "provider_disabled"}
        if not self._check_limits():
            return {"content": None, "tool_calls": [], "error": "limit_exceeded"}

        resp = self._provider.chat(
            messages,
            tools=tools,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        self._call_log.append(LLMCallRecord(
            timestamp=time.time(),
            model_id=self._config.model_id,
            prompt_messages=messages,
            response_text=resp.content,
            tool_calls=resp.tool_calls,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            cost_usd=resp.cost_usd,
            error=resp.error,
        ))
        self._total_cost += resp.cost_usd
        self._total_calls += 1

        return {
            "content": resp.content,
            "tool_calls": resp.tool_calls,
            "error": resp.error,
        }

    # ------------------------------------------------------------------
    # Agent interface
    # ------------------------------------------------------------------

    def select_tool(
        self,
        discovery_results: list[dict[str, Any]],
        task: dict[str, Any],
    ) -> str | None:
        if not self.is_enabled:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a tool-selection agent. Given a task description and "
                    "a list of available capabilities, select the most appropriate "
                    "capability_id. Respond with ONLY the capability_id string."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "task": task,
                    "capabilities": discovery_results,
                }, default=str),
            },
        ]

        response = self._call_llm(messages)
        if response.get("error"):
            return None

        content = (response.get("content") or "").strip()
        for cap in discovery_results:
            cap_id = cap.get("capability_id", "")
            if cap_id and cap_id in content:
                return cap_id
        if content and " " not in content:
            return content
        return None

    def build_params(
        self,
        capability_id: str,
        schema: dict[str, Any],
        task: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.is_enabled:
            return {}

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a parameter-building agent. Given a task, a capability "
                    "schema, and the task context, produce a JSON object with the "
                    "parameters for the capability invocation. Respond with ONLY "
                    "valid JSON."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "capability_id": capability_id,
                    "schema": schema,
                    "task": task,
                }, default=str),
            },
        ]

        response = self._call_llm(messages)
        if response.get("error"):
            return {}

        content = (response.get("content") or "").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for params: %s", content[:200])
            return {}

    def handle_response(
        self,
        response: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        if not self.is_enabled:
            return "abort"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a response-handling agent. Given a task and the "
                    "response from a tool invocation, decide the next action. "
                    "Respond with exactly one of: done, retry, resume, reconcile, abort."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "task": task,
                    "response": response,
                }, default=str),
            },
        ]

        response_data = self._call_llm(messages)
        if response_data.get("error"):
            return "abort"

        content = (response_data.get("content") or "").strip().lower()
        return _pick_action(content)

    def handle_error(
        self,
        error: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        """Return a runner-compatible action: retry | refresh_and_retry | abort.

        ``refresh_and_retry`` is returned when the interface exposes a
        structured error (typed error_code / current_version) — the adaptive
        agent is expected to refresh the stale version and retry, which is
        exactly the effect-contract mechanism H4b targets.
        """
        if not self.is_enabled:
            return "abort"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an error-handling agent. Given a task and an error "
                    "from a tool invocation, decide the next action. "
                    "Respond with exactly one of: done, retry, refresh_and_retry, abort. "
                    "Choose refresh_and_retry when the error exposes a current_version "
                    "or error_code that can be used to re-read and retry on fresh state."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "task": task,
                    "error": error,
                }, default=str),
            },
        ]

        response_data = self._call_llm(messages)
        if response_data.get("error"):
            return "abort"

        content = (response_data.get("content") or "").strip().lower()
        return _pick_action(content)

    def agent_id(self) -> str:
        return self._id


def _pick_action(content: str) -> str:
    """Map a free-form LLM reply to a runner-compatible action token."""
    valid = {"done", "retry", "resume", "reconcile", "abort", "refresh_and_retry"}
    for action in valid:
        if content == action or content.startswith(action):
            if action in ("done", "resume", "reconcile"):
                # Runner only branches on retry / refresh_and_retry; treat
                # other terminal actions as no-retry (abort-like).
                return "abort"
            return action
    return "abort"
