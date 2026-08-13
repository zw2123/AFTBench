"""Metrics computation from result rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .schemas import ResultRow


@dataclass
class MetricSummary:
    n_runs: int = 0
    state_correct_completion: float = 0.0
    postcondition_satisfaction: float = 0.0
    safety_predicate_satisfaction: float = 0.0
    duplicate_effect_rate: float = 0.0
    unintended_effect_rate: float = 0.0
    unauthorized_effect_rate: float = 0.0
    residual_effect_rate: float = 0.0
    false_success_rate: float = 0.0
    false_failure_rate: float = 0.0
    unresolved_outcome_rate: float = 0.0
    recovery_success: float = 0.0
    reconciliation_accuracy: float = 0.0
    repeated_backend_work: float = 0.0
    logical_reexecutions: float = 0.0
    human_intervention_count: float = 0.0
    mean_model_turns: float = 0.0
    mean_tool_calls: float = 0.0
    mean_transport_retries: float = 0.0
    mean_wall_clock_ms: float = 0.0
    mean_tool_definition_tokens: float = 0.0
    mean_tool_result_tokens: float = 0.0
    mean_context_tokens: float = 0.0
    mean_runtime_overhead_ms: float = 0.0
    mean_recovery_ms: float = 0.0
    mean_verification_ms: float = 0.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# Aliases for compatibility
MetricReport = MetricSummary


def compute_metrics(rows: Sequence[ResultRow]) -> MetricSummary:
    if not rows:
        return MetricSummary()

    n = len(rows)

    def _rate(attr):
        return sum(1 for r in rows if getattr(r, attr, False)) / n

    def _mean(attr):
        vals = [getattr(r, attr) for r in rows
                if getattr(r, attr, None) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    false_success = sum(
        1 for r in rows
        if r.terminal_agent_claim == "success"
        and r.terminal_oracle_outcome != "success"
    ) / n

    false_failure = sum(
        1 for r in rows
        if r.terminal_agent_claim == "failure"
        and r.terminal_oracle_outcome == "success"
    ) / n

    unresolved = sum(
        1 for r in rows if r.terminal_agent_claim == "unknown"
    ) / n

    recovery_needed = [r for r in rows if r.recovery_success is not None]
    recovery_rate = (
        sum(1 for r in recovery_needed if r.recovery_success) / len(recovery_needed)
        if recovery_needed else 0.0
    )

    recon_needed = [r for r in rows if r.unknown_outcome_reconciled is not None]
    recon_rate = (
        sum(1 for r in recon_needed if r.unknown_outcome_reconciled) / len(recon_needed)
        if recon_needed else 0.0
    )

    return MetricSummary(
        n_runs=n,
        state_correct_completion=_rate("state_correct_completion"),
        postcondition_satisfaction=_rate("postcondition_satisfied"),
        safety_predicate_satisfaction=_rate("safety_predicate_satisfied"),
        duplicate_effect_rate=_rate("duplicate_effect"),
        unintended_effect_rate=_rate("unintended_effect"),
        unauthorized_effect_rate=_rate("unauthorized_effect"),
        residual_effect_rate=_rate("residual_effect"),
        false_success_rate=false_success,
        false_failure_rate=false_failure,
        unresolved_outcome_rate=unresolved,
        recovery_success=recovery_rate,
        reconciliation_accuracy=recon_rate,
        repeated_backend_work=_mean("logical_reexecutions"),
        logical_reexecutions=_mean("logical_reexecutions"),
        human_intervention_count=_mean("human_intervention_count"),
        mean_model_turns=_mean("model_turns"),
        mean_tool_calls=_mean("tool_calls"),
        mean_transport_retries=_mean("transport_retries"),
        mean_wall_clock_ms=_mean("wall_clock_ms"),
        mean_tool_definition_tokens=_mean("tool_definition_tokens"),
        mean_tool_result_tokens=_mean("tool_result_tokens"),
        mean_context_tokens=_mean("context_tokens"),
        mean_runtime_overhead_ms=_mean("runtime_overhead_ms"),
        mean_recovery_ms=_mean("recovery_ms"),
        mean_verification_ms=_mean("verification_ms"),
    )


# Alias
compute_all_metrics = compute_metrics


def compute_metrics_by_world(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r.world, []).append(r)
    return {k: compute_metrics(v) for k, v in groups.items()}


def compute_metrics_by_fault(rows):
    groups = {}
    for r in rows:
        key = r.fault_type or "__none__"
        groups.setdefault(key, []).append(r)
    return {k: compute_metrics(v) for k, v in groups.items()}
