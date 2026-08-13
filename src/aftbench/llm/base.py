"""LLM provider abstraction.

A provider wraps a single chat-completions endpoint.  Providers are
endpoint-agnostic: they expose ``chat`` returning a normalized
``LLMResponse``, so the agent layer never touches HTTP or JSON details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Normalized response from a chat-completions call."""
    content: str | None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    """A chat-completions endpoint with known pricing."""

    name: str = "base"

    def __init__(
        self,
        api_key: str,
        api_base: str,
        model_id: str,
        input_price_per_1k: float = 0.0,
        output_price_per_1k: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model_id = model_id
        self.input_price_per_1k = input_price_per_1k
        self.output_price_per_1k = output_price_per_1k
        self.max_tokens = max_tokens

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Call the endpoint and return a normalized LLMResponse.

        Must never raise on transport errors; set ``error`` instead so the
        caller can degrade gracefully (abort / retry policy).
        """

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_price_per_1k
            + output_tokens * self.output_price_per_1k
        ) / 1000.0
