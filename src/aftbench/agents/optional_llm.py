"""Optional LLM-backed agent with explicit cost/call limits and full logging."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from .base import Agent

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


@dataclass
class LLMAgentConfig:
    """Configuration for the LLM agent."""
    model_id: str = "gpt-4o"
    api_base: str = "https://api.openai.com/v1"
    cost_limit_usd: float = 5.0
    call_limit: int = 200
    temperature: float = 0.0
    max_tokens: int = 4096


class LLMAgent(Agent):
    """LLM-backed agent that is disabled by default.

    Requires AFTBENCH_LLM_API_KEY environment variable.  All calls are logged
    with exact model_id, raw messages, and tool calls.  No hidden chain of
    thought is used — all reasoning is in the logged messages.
    """

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
        self._api_key: str | None = os.environ.get("AFTBENCH_LLM_API_KEY")

    @classmethod
    def create_if_enabled(
        cls,
        config: LLMAgentConfig | None = None,
        agent_id: str = "llm-v1",
    ) -> "LLMAgent | None":
        """Factory that returns None when the API key is not set."""
        api_key = os.environ.get("AFTBENCH_LLM_API_KEY")
        if not api_key:
            logger.info("LLMAgent disabled: AFTBENCH_LLM_API_KEY not set")
            return None
        return cls(config=config, agent_id=agent_id)

    @property
    def is_enabled(self) -> bool:
        return self._api_key is not None

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
            logger.warning(
                "LLMAgent cost limit reached: $%.4f >= $%.4f",
                self._total_cost,
                self._config.cost_limit_usd,
            )
            return False
        if self._total_calls >= self._config.call_limit:
            logger.warning(
                "LLMAgent call limit reached: %d >= %d",
                self._total_calls,
                self._config.call_limit,
            )
            return False
        return True

    def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call the LLM API and return the response dict.

        Uses a simple HTTP request to avoid hard dependency on openai SDK.
        """
        if not self._api_key:
            raise RuntimeError("AFTBENCH_LLM_API_KEY not set")
        if not self._check_limits():
            return {
                "content": None,
                "tool_calls": [],
                "error": "limit_exceeded",
            }

        import urllib.request
        import urllib.error

        body: dict[str, Any] = {
            "model": self._config.model_id,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }
        if tools:
            body["tools"] = tools

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self._config.api_base}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            logger.error("LLM API call failed: %s", exc)
            return {"content": None, "tool_calls": [], "error": str(exc)}

        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = result.get("usage", {})

        # Rough cost estimate (USD per 1K tokens — approximate)
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = (input_tokens * 0.005 + output_tokens * 0.015) / 1000.0

        record = LLMCallRecord(
            timestamp=time.time(),
            model_id=self._config.model_id,
            prompt_messages=messages,
            response_text=message.get("content"),
            tool_calls=message.get("tool_calls", []),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self._call_log.append(record)
        self._total_cost += cost
        self._total_calls += 1

        return {
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls", []),
            "error": None,
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
        # Try to extract capability_id from response
        for cap in discovery_results:
            cap_id = cap.get("capability_id", "")
            if cap_id and cap_id in content:
                return cap_id

        # If the response looks like a bare id, return it
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
        valid_actions = {"done", "retry", "resume", "reconcile", "abort"}
        if content in valid_actions:
            return content

        # Try to extract from longer text
        for action in valid_actions:
            if action in content:
                return action

        return "abort"

    def handle_error(
        self,
        error: dict[str, Any],
        task: dict[str, Any],
    ) -> str:
        if not self.is_enabled:
            return "abort"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an error-handling agent. Given a task and an error "
                    "from a tool invocation, decide the next action. "
                    "Respond with exactly one of: done, retry, resume, reconcile, abort."
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
        valid_actions = {"done", "retry", "resume", "reconcile", "abort"}
        if content in valid_actions:
            return content

        for action in valid_actions:
            if action in content:
                return action

        return "abort"

    def agent_id(self) -> str:
        return self._id
