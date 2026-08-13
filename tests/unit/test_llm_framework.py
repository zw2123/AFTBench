"""Tests for the LLM provider framework and LLM agent wiring."""

import os
import json
from pathlib import Path

import pytest

from aftbench.llm.base import LLMProvider, LLMResponse
from aftbench.llm.env import load_dotenv, get_secret
from aftbench.llm.registry import load_profiles, get_provider
from aftbench.agents.optional_llm import LLMAgent, LLMAgentConfig


class FakeProvider(LLMProvider):
    """Deterministic provider that returns canned responses, no network."""
    name = "fake"
    def __init__(self, responses=None, **kwargs):
        super().__init__(api_key="test-key", api_base="https://fake.invalid/v1",
                         model_id="fake-model", **kwargs)
        self._responses = responses or [{"content": "reply", "tool_calls": []}]
        self._index = 0
        self.calls: list[dict] = []

    def chat(self, messages, tools=None, temperature=0.0, max_tokens=None):
        self.calls.append({"messages": messages, "tools": tools})
        r = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return LLMResponse(
            content=r.get("content"),
            tool_calls=r.get("tool_calls", []),
            input_tokens=r.get("input_tokens", 10),
            output_tokens=r.get("output_tokens", 5),
            cost_usd=self.estimate_cost(10, 5),
        )


@pytest.fixture
def tmp_env(tmp_path):
    f = tmp_path / ".env"
    f.write_text(
        "# test\n"
        "AFTBENCH_TEST_KEY=abc123\n"
        'AFTBENCH_TEST_QUOTED="xyz"\n'
    )
    return f


class TestEnvLoader:
    def test_loads_key_value_pairs(self, tmp_env, monkeypatch):
        # isolate from any real env
        monkeypatch.delenv("AFTBENCH_TEST_KEY", raising=False)
        monkeypatch.delenv("AFTBENCH_TEST_QUOTED", raising=False)
        assert load_dotenv(tmp_env) is True
        assert os.environ.get("AFTBENCH_TEST_KEY") == "abc123"
        assert os.environ.get("AFTBENCH_TEST_QUOTED") == "xyz"

    def test_existing_env_wins(self, tmp_env, monkeypatch):
        monkeypatch.setenv("AFTBENCH_TEST_KEY", "real")
        load_dotenv(tmp_env)
        assert os.environ.get("AFTBENCH_TEST_KEY") == "real"

    def test_missing_file_returns_false(self):
        assert load_dotenv("/nonexistent/.env") is False

    def test_get_secret(self, tmp_env, monkeypatch):
        monkeypatch.delenv("AFTBENCH_TEST_KEY", raising=False)
        load_dotenv(tmp_env)
        assert get_secret("AFTBENCH_TEST_KEY") == "abc123"


class TestRegistry:
    def test_load_profiles_from_yaml(self, tmp_path):
        y = tmp_path / "providers.yaml"
        y.write_text(json.dumps({
            "providers": {
                "test-model": {
                    "api_base": "https://example.com/v1",
                    "api_key_env": "AFTBENCH_TEST_KEY",
                    "input_price_per_1k": 0.5,
                    "output_price_per_1k": 1.5,
                }
            }
        }))
        profiles = load_profiles(y)
        assert "test-model" in profiles
        p = profiles["test-model"]
        assert p.api_base == "https://example.com/v1"
        assert p.api_key_env == "AFTBENCH_TEST_KEY"
        assert p.input_price_per_1k == 0.5

    def test_get_provider_requires_key(self, tmp_path, monkeypatch):
        y = tmp_path / "providers.yaml"
        y.write_text(json.dumps({
            "providers": {
                "no-key-model": {
                    "api_base": "https://example.com/v1",
                    "api_key_env": "AFTBENCH_NEVER_SET_KEY",
                }
            }
        }))
        monkeypatch.delenv("AFTBENCH_NEVER_SET_KEY", raising=False)
        profiles = load_profiles(y)
        assert get_provider("no-key-model", profiles) is None

    def test_get_provider_with_key(self, tmp_path, monkeypatch):
        y = tmp_path / "providers.yaml"
        y.write_text(json.dumps({
            "providers": {
                "keyed-model": {
                    "api_base": "https://example.com/v1",
                    "api_key_env": "AFTBENCH_TEST_KEY",
                }
            }
        }))
        monkeypatch.setenv("AFTBENCH_TEST_KEY", "sekrit")
        profiles = load_profiles(y)
        prov = get_provider("keyed-model", profiles)
        assert prov is not None
        assert prov.api_key == "sekrit"
        assert prov.model_id == "keyed-model"


class TestLLMAgentWiring:
    def test_agent_disabled_without_provider(self, monkeypatch):
        monkeypatch.delenv("AFTBENCH_LLM_API_KEY", raising=False)
        # Unknown profile -> provider None -> disabled
        agent = LLMAgent(LLMAgentConfig(model_id="does-not-exist"))
        assert agent.is_enabled is False

    def test_agent_enabled_with_injected_provider(self):
        provider = FakeProvider(responses=[{"content": "crm.create_record"}])
        agent = LLMAgent(LLMAgentConfig(provider=provider), agent_id="test-llm")
        assert agent.is_enabled is True

    def test_select_tool_uses_discovery(self):
        provider = FakeProvider(responses=[{"content": "crm.create_record"}])
        agent = LLMAgent(LLMAgentConfig(provider=provider))
        caps = [
            {"capability_id": "crm.create_record", "summary": "Create record"},
            {"capability_id": "crm.delete_record", "summary": "Delete record"},
        ]
        sel = agent.select_tool(caps, {"description": "create a record"})
        assert sel == "crm.create_record"
        assert provider.calls[0]["tools"] is None  # no tools passed in select_tool

    def test_build_params_parses_json(self):
        provider = FakeProvider(responses=[{
            "content": json.dumps({"record_type": "contact", "fields": {"name": "x"}}),
        }])
        agent = LLMAgent(LLMAgentConfig(provider=provider))
        params = agent.build_params("crm.create_record",
                                    {"properties": {}},
                                    {"parameters": {}})
        assert params == {"record_type": "contact", "fields": {"name": "x"}}

    def test_build_params_invalid_json_returns_empty(self):
        provider = FakeProvider(responses=[{"content": "not json at all"}])
        agent = LLMAgent(LLMAgentConfig(provider=provider))
        assert agent.build_params("x", {}, {}) == {}

    def test_handle_error_maps_refresh_and_retry(self):
        provider = FakeProvider(responses=[{"content": "refresh_and_retry"}])
        agent = LLMAgent(LLMAgentConfig(provider=provider))
        action = agent.handle_error(
            {"error_code": "VERSION_CONFLICT", "current_version": "v2"},
            {"task_id": "t1"},
        )
        assert action == "refresh_and_retry"

    def test_handle_error_abort_on_unknown(self):
        provider = FakeProvider(responses=[{"content": "maybe"}])
        agent = LLMAgent(LLMAgentConfig(provider=provider))
        assert agent.handle_error({"error": "boom"}, {}) == "abort"

    def test_cost_and_call_limits(self):
        provider = FakeProvider()
        agent = LLMAgent(LLMAgentConfig(provider=provider, call_limit=2))
        agent.select_tool([{"capability_id": "a"}], {})
        agent.select_tool([{"capability_id": "a"}], {})
        assert agent.total_calls == 2
        # Third call hits the limit
        result = agent._call_llm([{"role": "user", "content": "x"}])
        assert result["error"] == "limit_exceeded"
        assert agent.total_calls == 2
