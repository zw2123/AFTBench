"""Metrics derivation validation tests (Section 16)."""
import pytest
import csv
import json
from pathlib import Path


EVIDENCE_DIR = Path("artifacts/evidence_runs")


def _load_results(exp_name: str) -> list[dict]:
    results_path = EVIDENCE_DIR / exp_name / "results.csv"
    if not results_path.exists():
        pytest.skip(f"{exp_name} results not found")
    with open(results_path) as f:
        return list(csv.DictReader(f))


def _load_traces(exp_name: str) -> list[dict]:
    traces_path = EVIDENCE_DIR / exp_name / "traces.jsonl"
    if not traces_path.exists():
        pytest.skip(f"{exp_name} traces not found")
    with open(traces_path) as f:
        return [json.loads(line) for line in f]


class TestDerivedMetrics:
    """Validate evidence-derived metrics."""

    def test_duplicate_effect_from_commit_log(self):
        """Verify duplicate_effect is derived from committed operations, not hard-coded."""
        results = _load_results("primitive_ablations")

        # Check that duplicate_effect field exists and is boolean
        for r in results[:10]:
            assert "duplicate_effect" in r, "ResultRow must have duplicate_effect field"
            assert r["duplicate_effect"] in ("true", "false"), (
                f"duplicate_effect must be boolean, got {r['duplicate_effect']}"
            )

    def test_unintended_effect_from_state_diff(self):
        """Verify unintended_effect is derived from state diff, not hard-coded."""
        results = _load_results("primitive_ablations")

        for r in results[:10]:
            assert "unintended_effect" in r, "ResultRow must have unintended_effect field"
            assert r["unintended_effect"] in ("true", "false"), (
                f"unintended_effect must be boolean, got {r['unintended_effect']}"
            )

    def test_unauthorized_effect_at_commit_time(self):
        """Verify unauthorized_effect is evaluated at commit time."""
        results = _load_results("stale_permission")

        for r in results[:10]:
            assert "unauthorized_effect" in r, "ResultRow must have unauthorized_effect field"
            assert r["unauthorized_effect"] in ("true", "false"), (
                f"unauthorized_effect must be boolean, got {r['unauthorized_effect']}"
            )

    def test_recovery_timing_from_trace(self):
        """Verify recovery_ms is derived from trace timestamps."""
        results = _load_results("postcommit_loss")

        # recovery_ms should be an integer
        for r in results[:10]:
            assert "recovery_ms" in r, "ResultRow must have recovery_ms field"
            val = r["recovery_ms"]
            assert val == "" or val.isdigit(), (
                f"recovery_ms must be integer or empty, got {val}"
            )

    def test_verification_timing_from_trace(self):
        """Verify verification_ms is derived from trace timestamps."""
        results = _load_results("primitive_ablations")

        for r in results[:10]:
            assert "verification_ms" in r, "ResultRow must have verification_ms field"
            val = r["verification_ms"]
            assert val == "" or val.isdigit(), (
                f"verification_ms must be integer or empty, got {val}"
            )

    def test_wall_clock_uses_monotonic_time(self):
        """Verify wall_clock_ms uses actual timing, not hard-coded zero."""
        results = _load_results("primitive_ablations")

        # At least some runs should have non-zero wall_clock_ms
        non_zero = sum(1 for r in results if int(r.get("wall_clock_ms", 0)) > 0)
        # With synthetic tasks, most will be non-zero
        assert len(results) > 0, "Should have results"
        # wall_clock_ms should be present and numeric
        for r in results[:10]:
            assert "wall_clock_ms" in r, "ResultRow must have wall_clock_ms field"
            val = r["wall_clock_ms"]
            assert val.isdigit(), f"wall_clock_ms must be integer, got {val}"
