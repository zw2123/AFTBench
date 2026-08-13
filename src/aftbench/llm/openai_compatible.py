"""OpenAI-compatible chat-completions provider.

Covers any endpoint implementing the OpenAI ``/chat/completions`` protocol
(Qwen/DashScope compatible-mode, DeepSeek, and most hosted providers).
Uses only the standard library (urllib) to avoid a hard SDK dependency.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """Minimal OpenAI-compatible chat completions client."""

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str,
        api_base: str,
        model_id: str,
        input_price_per_1k: float = 0.0,
        output_price_per_1k: float = 0.0,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_base=api_base,
            model_id=model_id,
            input_price_per_1k=input_price_per_1k,
            output_price_per_1k=output_price_per_1k,
            max_tokens=max_tokens,
        )
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if tools:
            body["tools"] = tools

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            logger.error("LLM API call failed: %s", exc)
            return LLMResponse(content=None, error=f"transport: {exc}")
        except Exception as exc:  # json decode, timeout, etc.
            logger.error("LLM API call failed: %s", exc)
            return LLMResponse(content=None, error=f"call: {exc}")

        choice = (result.get("choices") or [{}])[0]
        message = choice.get("message", {})
        usage = result.get("usage", {})

        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)

        return LLMResponse(
            content=message.get("content"),
            tool_calls=message.get("tool_calls", []),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.estimate_cost(input_tokens, output_tokens),
            error=None,
            raw=result,
        )
