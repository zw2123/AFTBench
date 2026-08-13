"""Tests for benchmark invariants.

These tests verify structural properties that must hold across all benchmark
results, regardless of agent, world, interface, or fault configuration.
"""

import pytest

from aftbench.metrics import compute_all_metrics
from aftbench.schemas import ResultRow
from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld
from aftbench.worlds.long_running_jobs import LongRunningJobsWorld
from aftbench.worlds.large_catalog import LargeCatalogWorld
from aftbench.worlds.external_actions import ExternalActionsWorld


# ---------------------------------------------------------------------------
# Invariant: state_correct = postconditions AND safety
# ---------------------------------------------------------------------------

class TestStateCorrectInvariant:
    """state_correct_completion should equal postcondition_satisfied AND safety_predicate_satisfied."""

    def test_consistent_correct_row(self):
        row = ResultRow(
            run_id="r1", task_id="t1",
            postcondition_satisfied=True,
            safety_predicate_satisfied=True,
            state_correct_completion=True,
        )
        expected = row.postcondition_satisfied and row.safety_predicate_satisfied
        assert row.state_correct_completion == expected

    def test_unsafe_implies_not_correct(self):
        row = ResultRow(
            run_id="r1", task_id="t1",
            postcondition_satisfied=True,
            safety_predicate_satisfied=False,
            state_correct_completion=False,
        )
        expected = row.postcondition_satisfied and row.safety_predicate_satisfied
        assert row.state_correct_completion == expected

    def test_both_fail_implies_not_correct(self):
        row = ResultRow(
            run_id="r1", task_id="t1",
            postcondition_satisfied=False,
            safety_predicate_satisfied=False,
            state_correct_completion=False,
        )
        expected = row.postcondition_satisfied and row.safety_predicate_satisfied
        assert row.state_correct_completion == expected

    def test_postcond_fails_safety_pass(self):
        row = ResultRow(
            run_id="r1", task_id="t1",
            postcondition_satisfied=False,
            safety_predicate_satisfied=True,
            state_correct_completion=False,
        )
        expected = row.postcondition_satisfied and row.safety_predicate_satisfied
        assert row.state_correct_completion == expected


# ---------------------------------------------------------------------------
# Invariant: recovery metrics only computed over fault rows
# ---------------------------------------------------------------------------

class TestRecoveryMetricsScope:
    """Recovery metrics should only count rows where recovery_success is not None."""

    def test_no_recovery_needed_zero(self):
        rows = [
            ResultRow(run_id="r1", task_id="t1", fault_type=None,
                       recovery_success=None),
        ]
        report = compute_all_metrics(rows)
        assert report.recovery_success == 0.0

    def test_fault_rows_counted(self):
        rows = [
            ResultRow(run_id="r1", task_id="t1", fault_type="stale_state",
                       recovery_success=True),
            ResultRow(run_id="r1", task_id="t2", fault_type="stale_state",
                       recovery_success=False),
        ]
        report = compute_all_metrics(rows)
        assert report.recovery_success == 0.5

    def test_mixed_fault_and_no_fault(self):
        rows = [
            ResultRow(run_id="r1", task_id="t1", fault_type="stale_state",
                       recovery_success=True),
            ResultRow(run_id="r1", task_id="t2", fault_type=None,
                       recovery_success=None),
        ]
        report = compute_all_metrics(rows)
        # Only 1 row has recovery_success not None, and it recovered
        assert report.recovery_success == 1.0


# ---------------------------------------------------------------------------
# Invariant: effect rates are proportions
# ---------------------------------------------------------------------------

class TestEffectRateInvariant:
    """Effect rates are proportions of rows with the effect flag set."""

    def test_duplicate_effect_rate(self):
        rows = [
            ResultRow(run_id="r1", task_id="t1", duplicate_effect=True),
            ResultRow(run_id="r1", task_id="t2", duplicate_effect=False),
        ]
        report = compute_all_metrics(rows)
        assert report.duplicate_effect_rate == 0.5

    def test_no_duplicates(self):
        rows = [
            ResultRow(run_id="r1", task_id="t1", duplicate_effect=False),
            ResultRow(run_id="r1", task_id="t2", duplicate_effect=False),
        ]
        report = compute_all_metrics(rows)
        assert report.duplicate_effect_rate == 0.0

    def test_all_unintended(self):
        rows = [
            ResultRow(run_id="r1", task_id="t1", unintended_effect=True),
            ResultRow(run_id="r1", task_id="t2", unintended_effect=True),
        ]
        report = compute_all_metrics(rows)
        assert report.unintended_effect_rate == 1.0


# ---------------------------------------------------------------------------
# Invariant: world state is deterministic after reset
# ---------------------------------------------------------------------------

class TestWorldDeterminism:
    """Each world must produce identical state after reset with the same seed."""

    def test_er_deterministic(self):
        w = EnterpriseRecordsWorld()
        w.reset(seed=42)
        s1 = w.get_state()
        w.reset(seed=42)
        s2 = w.get_state()
        assert s1 == s2

    def test_lrj_deterministic(self):
        w = LongRunningJobsWorld()
        w.reset(seed=42)
        s1 = w.get_state()
        w.reset(seed=42)
        s2 = w.get_state()
        assert s1 == s2

    def test_lc_deterministic(self):
        w = LargeCatalogWorld()
        w.reset(seed=42)
        s1 = w.get_state()
        w.reset(seed=42)
        s2 = w.get_state()
        assert s1 == s2

    def test_ea_deterministic(self):
        w = ExternalActionsWorld()
        w.reset(seed=42)
        s1 = w.get_state()
        w.reset(seed=42)
        s2 = w.get_state()
        assert s1 == s2


# ---------------------------------------------------------------------------
# Invariant: world initial state hash is stable
# ---------------------------------------------------------------------------

class TestInitialStateHash:
    """get_initial_state_hash must be deterministic for the same seed."""

    def test_er_hash_stable(self):
        w = EnterpriseRecordsWorld()
        w.reset(seed=42)
        h1 = w.get_initial_state_hash()
        w.reset(seed=42)
        h2 = w.get_initial_state_hash()
        assert h1 == h2

    def test_lc_hash_stable(self):
        w = LargeCatalogWorld()
        w.reset(seed=42)
        h1 = w.get_initial_state_hash()
        w.reset(seed=42)
        h2 = w.get_initial_state_hash()
        assert h1 == h2

    def test_ea_hash_stable(self):
        w = ExternalActionsWorld()
        w.reset(seed=42)
        h1 = w.get_initial_state_hash()
        w.reset(seed=42)
        h2 = w.get_initial_state_hash()
        assert h1 == h2


# ---------------------------------------------------------------------------
# Invariant: all worlds implement the World interface
# ---------------------------------------------------------------------------

class TestWorldInterfaceCompliance:
    """All worlds must implement the abstract World interface."""

    @pytest.mark.parametrize("world_cls", [
        EnterpriseRecordsWorld,
        LongRunningJobsWorld,
        LargeCatalogWorld,
        ExternalActionsWorld,
    ])
    def test_world_has_required_methods(self, world_cls):
        w = world_cls()
        assert hasattr(w, "reset")
        assert hasattr(w, "get_state")
        assert hasattr(w, "verify_postconditions")
        assert hasattr(w, "verify_safety_predicates")
        assert hasattr(w, "apply_effect")
        assert hasattr(w, "get_object_version")
        assert hasattr(w, "get_initial_state_hash")

    @pytest.mark.parametrize("world_cls", [
        EnterpriseRecordsWorld,
        LongRunningJobsWorld,
        LargeCatalogWorld,
        ExternalActionsWorld,
    ])
    def test_world_reset_and_get_state(self, world_cls):
        w = world_cls()
        w.reset(seed=0)
        state = w.get_state()
        assert isinstance(state, dict)

    @pytest.mark.parametrize("world_cls", [
        EnterpriseRecordsWorld,
        LongRunningJobsWorld,
        LargeCatalogWorld,
        ExternalActionsWorld,
    ])
    def test_world_safety_predicates_return_bool(self, world_cls):
        w = world_cls()
        w.reset(seed=0)
        state = w.get_state()
        result = w.verify_safety_predicates({}, state)
        assert isinstance(result, bool)

    @pytest.mark.parametrize("world_cls", [
        EnterpriseRecordsWorld,
        LongRunningJobsWorld,
        LargeCatalogWorld,
        ExternalActionsWorld,
    ])
    def test_world_postconditions_return_bool(self, world_cls):
        w = world_cls()
        w.reset(seed=0)
        state = w.get_state()
        result = w.verify_postconditions({}, state)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Invariant: read-only effects don't mutate state
# ---------------------------------------------------------------------------

class TestReadOnlyInvariant:
    """Read-only effects must not change world state."""

    def test_er_read_does_not_mutate(self):
        w = EnterpriseRecordsWorld()
        w.reset(seed=42)
        state_before = w.get_state()
        w.apply_effect({"type": "read_record", "record_id": "con-001"})
        state_after = w.get_state()
        assert state_before == state_after

    def test_er_list_does_not_mutate(self):
        w = EnterpriseRecordsWorld()
        w.reset(seed=42)
        state_before = w.get_state()
        w.apply_effect({"type": "list_records", "filters": {}})
        state_after = w.get_state()
        assert state_before == state_after

    def test_lc_get_catalog_does_not_mutate(self):
        w = LargeCatalogWorld()
        w.reset(seed=42)
        state_before = w.get_state()
        w.apply_effect({"type": "get_catalog", "size": 10})
        state_after = w.get_state()
        assert state_before == state_after

    def test_ea_read_does_not_mutate(self):
        w = ExternalActionsWorld()
        w.reset(seed=42)
        state_before = w.get_state()
        w.apply_effect({"type": "read_entity", "entity_id": "evt-001"})
        state_after = w.get_state()
        assert state_before == state_after

    def test_lrj_get_status_does_not_mutate(self):
        w = LongRunningJobsWorld()
        w.reset(seed=42)
        w.apply_effect({
            "type": "create_job",
            "job_id": "job-ro",
            "stages": [{"name": "s1"}],
        })
        state_before = w.get_state()
        w.apply_effect({"type": "get_job_status", "job_id": "job-ro"})
        state_after = w.get_state()
        assert state_before == state_after

    def test_lrj_list_does_not_mutate(self):
        w = LongRunningJobsWorld()
        w.reset(seed=42)
        state_before = w.get_state()
        w.apply_effect({"type": "list_jobs"})
        state_after = w.get_state()
        assert state_before == state_after


# ---------------------------------------------------------------------------
# Invariant: version changes on mutation
# ---------------------------------------------------------------------------

class TestVersionMutationInvariant:
    """Object versions must change after mutation."""

    def test_er_version_changes_on_update(self):
        w = EnterpriseRecordsWorld()
        w.reset(seed=42)
        v_before = w.get_object_version("con-001")
        w.apply_effect({
            "type": "update_record",
            "record_id": "con-001",
            "fields": {"phone": "x"},
        })
        v_after = w.get_object_version("con-001")
        assert v_before != v_after

    def test_ea_version_changes_on_update(self):
        w = ExternalActionsWorld()
        w.reset(seed=42)
        v_before = w.get_object_version("evt-001")
        w.apply_effect({
            "type": "update_entity",
            "entity_id": "evt-001",
            "fields": {"title": "Updated"},
        })
        v_after = w.get_object_version("evt-001")
        assert v_before != v_after


# ---------------------------------------------------------------------------
# Invariant: n_runs in metric report matches input row count
# ---------------------------------------------------------------------------

class TestMetricReportCountInvariant:
    """MetricReport.n_runs must equal the number of input rows."""

    def test_n_runs_matches(self):
        rows = [_make_row(task_id=f"t{i}") for i in range(7)]
        report = compute_all_metrics(rows)
        assert report.n_runs == 7

    def test_n_runs_empty(self):
        report = compute_all_metrics([])
        assert report.n_runs == 0

    def test_n_runs_single(self):
        report = compute_all_metrics([_make_row()])
        assert report.n_runs == 1


def _make_row(**overrides) -> ResultRow:
    defaults = dict(run_id="r1", task_id="t1")
    defaults.update(overrides)
    return ResultRow(**defaults)
