"""Provider registry: maps model names to configured endpoints.

Non-secret configuration lives in ``configs/llm/providers.yaml`` (tracked).
Secrets live in the repo-root ``.env`` (gitignored) and are referenced by
``api_key_env`` (the environment variable name).  Nothing secret is ever
stored in a tracked file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .base import LLMProvider
from .env import get_secret
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

DEFAULT_PROVIDERS_YAML = Path(__file__).resolve().parents[3] / "configs" / "llm" / "providers.yaml"


@dataclass
class ProviderProfile:
    """One entry in providers.yaml — describes an endpoint, never a secret."""
    name: str
    api_base: str
    api_key_env: str
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    max_tokens: int = 4096
    timeout: float = 120.0


def load_profiles(path: str | Path | None = None) -> dict[str, ProviderProfile]:
    """Load all provider profiles from providers.yaml."""
    yaml_path = Path(path) if path else DEFAULT_PROVIDERS_YAML
    if not yaml_path.exists():
        logger.warning("providers.yaml not found: %s", yaml_path)
        return {}
    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}
    profiles: dict[str, ProviderProfile] = {}
    for name, cfg in (data.get("providers") or {}).items():
        profiles[name] = ProviderProfile(
            name=name,
            api_base=cfg.get("api_base", ""),
            api_key_env=cfg.get("api_key_env", ""),
            input_price_per_1k=float(cfg.get("input_price_per_1k", 0.0)),
            output_price_per_1k=float(cfg.get("output_price_per_1k", 0.0)),
            max_tokens=int(cfg.get("max_tokens", 4096)),
            timeout=float(cfg.get("timeout", 120.0)),
        )
    return profiles


def get_provider(
    profile_name: str,
    profiles: dict[str, ProviderProfile] | None = None,
    api_key: str | None = None,
) -> LLMProvider | None:
    """Instantiate a provider for a profile, resolving the key from .env.

    Returns None if the profile is unknown or the API key is not set.
    """
    profiles = profiles if profiles is not None else load_profiles()
    profile = profiles.get(profile_name)
    if profile is None:
        logger.warning("Unknown LLM provider profile: %s", profile_name)
        return None
    if not profile.api_base:
        logger.warning("Provider profile %s has no api_base", profile_name)
        return None
    key = api_key or get_secret(profile.api_key_env)
    if not key:
        logger.info(
            "Provider %s disabled: %s not set in environment/.env",
            profile_name, profile.api_key_env,
        )
        return None
    return OpenAICompatibleProvider(
        api_key=key,
        api_base=profile.api_base,
        model_id=profile_name,
        input_price_per_1k=profile.input_price_per_1k,
        output_price_per_1k=profile.output_price_per_1k,
        max_tokens=profile.max_tokens,
        timeout=profile.timeout,
    )
