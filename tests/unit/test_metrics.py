"""Tests for compute_metrics with known ResultRow inputs."""

import pytest

from aftbench.metrics import (
    MetricReport,
    MetricSummary,
    compute_all_metrics,
    compute_metrics,
    compute_metrics_by_fault,
    compute_metrics_by_world,
)
from aftbench.schemas import ResultRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(**overrides) -> ResultRow:
    """Create a ResultRow with sensible defaults, overridable."""
    defaults = dict(
        run_id="run-1",
        task_id="task-1",
        world="enterprise_records",
        agent_id="scripted-v1",
        state_correct_completion=True,
        postcondition_satisfied=True,
        safety_predicate_satisfied=True,
        tool_calls=4,
        model_turns=2,
    )
    defaults.update(overrides)
    return ResultRow(**defaults)


# ---------------------------------------------------------------------------
# MetricReport / MetricSummary alias
# ---------------------------------------------------------------------------

class TestMetricAliases:
    def test_metric_report_is_metric_summary(self):
        assert MetricReport is MetricSummary

    def test_compute_all_metrics_is_compute_metrics(self):
        assert compute_all_metrics is compute_metrics


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def test_empty_rows_returns_zero_report(self):
        report = compute_metrics([])
        assert isinstance(report, MetricSummary)
        assert report.state_correct_completion == 0.0
        assert report.postcondition_satisfaction == 0.0
        assert report.n_runs == 0

    def test_all_correct(self):
        rows = [_make_row() for _ in range(5)]
        report = compute_metrics(rows)
        assert report.state_correct_completion == 1.0
        assert report.postcondition_satisfaction == 1.0
        assert report.safety_predicate_satisfaction == 1.0
        assert report.n_runs == 5

    def test_none_correct(self):
        rows = [_make_row(state_correct_completion=False, postcondition_satisfied=False)
                for _ in range(3)]
        report = compute_metrics(rows)
        assert report.state_correct_completion == 0.0
        assert report.postcondition_satisfaction == 0.0

    def test_mixed_correctness(self):
        rows = [
            _make_row(task_id="t1", state_correct_completion=True),
            _make_row(task_id="t2", state_correct_completion=False),
            _make_row(task_id="t3", state_correct_completion=True),
            _make_row(task_id="t4", state_correct_completion=False),
        ]
        report = compute_metrics(rows)
        assert report.state_correct_completion == 0.5

    def test_false_success_rate(self):
        rows = [
            _make_row(task_id="t1",
                       terminal_agent_claim="success",
                       terminal_oracle_outcome="failure"),
            _make_row(task_id="t2",
                       terminal_agent_claim="success",
                       terminal_oracle_outcome="success"),
            _make_row(task_id="t3",
                       terminal_agent_claim="failure",
                       terminal_oracle_outcome="failure"),
        ]
        report = compute_metrics(rows)
        assert abs(report.false_success_rate - 1/3) < 1e-9

    def test_false_failure_rate(self):
        rows = [
            _make_row(task_id="t1",
                       terminal_agent_claim="failure",
                       terminal_oracle_outcome="success"),
            _make_row(task_id="t2",
                       terminal_agent_claim="failure",
                       terminal_oracle_outcome="success"),
        ]
        report = compute_metrics(rows)
        assert report.false_failure_rate == 1.0

    def test_unresolved_rate(self):
        rows = [
            _make_row(task_id="t1", terminal_agent_claim="unknown"),
            _make_row(task_id="t2", terminal_agent_claim="success"),
        ]
        report = compute_metrics(rows)
        assert report.unresolved_outcome_rate == 0.5

    def test_recovery_metrics_only_when_needed(self):
        rows = [
            _make_row(task_id="t1", fault_type="transient_error",
                       recovery_success=True),
            _make_row(task_id="t2", fault_type=None,
                       recovery_success=None),
        ]
        report = compute_metrics(rows)
        # Only 1 row has recovery_success not None, and it succeeded
        assert report.recovery_success == 1.0

    def test_recovery_no_rows_needing_recovery(self):
        rows = [_make_row(recovery_success=None)]
        report = compute_metrics(rows)
        assert report.recovery_success == 0.0

    def test_reconciliation_accuracy(self):
        rows = [
            _make_row(task_id="t1", unknown_outcome_reconciled=True),
            _make_row(task_id="t2", unknown_outcome_reconciled=False),
        ]
        report = compute_metrics(rows)
        assert report.reconciliation_accuracy == 0.5

    def test_duplicate_effect_rate(self):
        rows = [
            _make_row(task_id="t1", duplicate_effect=True),
            _make_row(task_id="t2", duplicate_effect=False),
        ]
        report = compute_metrics(rows)
        assert report.duplicate_effect_rate == 0.5

    def test_unintended_effect_rate(self):
        rows = [
            _make_row(task_id="t1", unintended_effect=True),
            _make_row(task_id="t2", unintended_effect=True),
            _make_row(task_id="t3", unintended_effect=False),
        ]
        report = compute_metrics(rows)
        assert abs(report.unintended_effect_rate - 2/3) < 1e-9

    def test_unauthorized_effect_rate(self):
        rows = [_make_row(unauthorized_effect=True)]
        report = compute_metrics(rows)
        assert report.unauthorized_effect_rate == 1.0

    def test_residual_effect_rate(self):
        rows = [_make_row(residual_effect=False)]
        report = compute_metrics(rows)
        assert report.residual_effect_rate == 0.0

    def test_mean_model_turns(self):
        rows = [
            _make_row(task_id="t1", model_turns=2),
            _make_row(task_id="t2", model_turns=4),
        ]
        report = compute_metrics(rows)
        assert report.mean_model_turns == 3.0

    def test_mean_tool_calls(self):
        rows = [
            _make_row(task_id="t1", tool_calls=3),
            _make_row(task_id="t2", tool_calls=7),
        ]
        report = compute_metrics(rows)
        assert report.mean_tool_calls == 5.0

    def test_mean_wall_clock(self):
        rows = [
            _make_row(task_id="t1", wall_clock_ms=1000),
            _make_row(task_id="t2", wall_clock_ms=3000),
        ]
        report = compute_metrics(rows)
        assert report.mean_wall_clock_ms == 2000.0

    def test_human_intervention_count(self):
        rows = [
            _make_row(task_id="t1", human_intervention_count=2),
            _make_row(task_id="t2", human_intervention_count=3),
        ]
        report = compute_metrics(rows)
        assert report.human_intervention_count == 2.5

    def test_token_metrics(self):
        rows = [
            _make_row(task_id="t1", tool_definition_tokens=100, tool_result_tokens=50),
            _make_row(task_id="t2", tool_definition_tokens=200, tool_result_tokens=100),
        ]
        report = compute_metrics(rows)
        assert report.mean_tool_definition_tokens == 150.0
        assert report.mean_tool_result_tokens == 75.0

    def test_to_dict(self):
        report = compute_metrics([_make_row()])
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "state_correct_completion" in d
        assert "n_runs" in d

    def test_logical_reexecutions(self):
        rows = [
            _make_row(task_id="t1", logical_reexecutions=2),
            _make_row(task_id="t2", logical_reexecutions=0),
        ]
        report = compute_metrics(rows)
        assert report.logical_reexecutions == 1.0


# ---------------------------------------------------------------------------
# Grouping functions
# ---------------------------------------------------------------------------

class TestComputeMetricsByWorld:
    def test_groups_by_world(self):
        rows = [
            _make_row(task_id="t1", world="er"),
            _make_row(task_id="t2", world="lrj"),
        ]
        result = compute_metrics_by_world(rows)
        assert "er" in result
        assert "lrj" in result

    def test_single_world(self):
        rows = [_make_row(world="solo")]
        result = compute_metrics_by_world(rows)
        assert "solo" in result
        assert result["solo"].state_correct_completion == 1.0


class TestComputeMetricsByFault:
    def test_groups_by_fault(self):
        rows = [
            _make_row(task_id="t1", fault_type="stale_state"),
            _make_row(task_id="t2", fault_type=None),
            _make_row(task_id="t3", fault_type="stale_state"),
        ]
        result = compute_metrics_by_fault(rows)
        assert "stale_state" in result
        assert "__none__" in result

    def test_none_key_for_no_fault(self):
        rows = [_make_row(fault_type=None)]
        result = compute_metrics_by_fault(rows)
        assert "__none__" in result

    def test_multiple_fault_types(self):
        rows = [
            _make_row(task_id="t1", fault_type="stale_state"),
            _make_row(task_id="t2", fault_type="permission_drift"),
        ]
        result = compute_metrics_by_fault(rows)
        assert "stale_state" in result
        assert "permission_drift" in result
