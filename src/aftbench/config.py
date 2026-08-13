"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BenchmarkConfig:
    profile: str = "smoke"
    seed: int = 42
    output_dir: str = "artifacts/smoke"
    worlds: list[str] = field(default_factory=lambda: [
        "enterprise_records", "long_running_jobs",
        "large_catalog", "external_actions",
    ])
    interfaces: list[str] = field(default_factory=lambda: ["I0", "I3", "I5"])
    faults: list[str] = field(default_factory=lambda: ["none"])
    max_tasks_per_world: int = 3
    seeds: list[int] = field(default_factory=lambda: [42])
    task_ids: list[str] | None = None
    agent: str = "scripted"
    resume_from: str | None = None
    cost_limit: float = 0.0
    call_limit: int = 0
    max_turns: int = 20
    ablation: str | None = None
    # LLM agent (agent: llm) — model_id is a provider profile name from
    # configs/llm/providers.yaml; API keys come from .env (gitignored).
    llm_model: str = "qwen-3.7-plus"
    llm_cost_limit_usd: float = 5.0
    llm_call_limit: int = 200
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    @classmethod
    def from_yaml(cls, path: str | Path) -> BenchmarkConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunContext:
    """Runtime context for a single benchmark run."""
    run_id: str
    task_id: str
    world: str
    interface_condition: str
    agent_id: str
    fault_id: str | None
    seed: int
    output_dir: Path
    ablation: str | None = None
