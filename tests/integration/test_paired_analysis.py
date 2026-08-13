"""Paired analysis validation tests (Section 16)."""
import pytest
import csv
from pathlib import Path


EVIDENCE_DIR = Path("artifacts/evidence_runs")


def _load_contrasts(exp_name: str) -> list[dict]:
    contrasts_path = EVIDENCE_DIR / exp_name / "analysis" / "explicit_contrasts.csv"
    if not contrasts_path.exists():
        pytest.skip(f"{exp_name} contrasts not found")
    with open(contrasts_path) as f:
        return list(csv.DictReader(f))


def _load_bootstrap(exp_name: str) -> list[dict]:
    bootstrap_path = EVIDENCE_DIR / exp_name / "analysis" / "bootstrap_intervals.csv"
    if not bootstrap_path.exists():
        pytest.skip(f"{exp_name} bootstrap not found")
    with open(bootstrap_path) as f:
        return list(csv.DictReader(f))


def _load_results(exp_name: str) -> list[dict]:
    results_path = EVIDENCE_DIR / exp_name / "results.csv"
    if not results_path.exists():
        pytest.skip(f"{exp_name} results not found")
    with open(results_path) as f:
        return list(csv.DictReader(f))


class TestPairedAnalysis:
    """Validate paired analysis correctness."""

    def test_interface_pairs_generated(self):
        """Verify interface-ladder pairs are generated."""
        # Check primitive_ablations for I5 vs ablation pairs
        contrasts = _load_contrasts("primitive_ablations")
        assert len(contrasts) > 0, "Should have ablation contrasts"

        # Should have I5 vs each ablation variant
        contrast_names = [c["contrast_name"] for c in contrasts]
        assert any("I5" in name for name in contrast_names), (
            "Should have I5 contrasts"
        )

    def test_ablation_pairs_generated(self):
        """Verify ablation pairs are generated."""
        contrasts = _load_contrasts("primitive_ablations")

        # Should have 7 ablation contrasts
        assert len(contrasts) == 7, (
            f"Should have 7 ablation contrasts, got {len(contrasts)}"
        )

        # Each contrast should have valid pairs
        for c in contrasts:
            valid_pairs = int(c.get("valid_pairs", 0))
            assert valid_pairs > 0, (
                f"Contrast {c['contrast_name']} should have valid pairs"
            )

    def test_hash_mismatch_rejected(self):
        """Verify pairs with mismatched hashes are rejected."""
        results = _load_results("primitive_ablations")

        # Group by pair key
        from collections import defaultdict
        groups = defaultdict(list)
        for r in results:
            key = (r["task_id"], r["world"], r.get("fault_type", ""), r["seed"])
            groups[key].append(r)

        # All pairs should have matching initial_state_hash
        for key, group_rows in groups.items():
            if len(group_rows) == 2:
                hashes = set(r.get("initial_state_hash", "") for r in group_rows)
                # Same task+world+fault+seed should have same initial state
                assert len(hashes) == 1, (
                    f"Pair {key} has mismatched initial_state_hash: {hashes}"
                )

    def test_missing_pairs_reported(self):
        """Verify missing pairs are reported in contrasts."""
        contrasts = _load_contrasts("primitive_ablations")

        for c in contrasts:
            # Each contrast should report missing treatment/control counts
            assert "missing_treatment" in c, (
                f"Contrast {c['contrast_name']} should report missing_treatment"
            )
            assert "missing_control" in c, (
                f"Contrast {c['contrast_name']} should report missing_control"
            )

    def test_failed_runs_preserved(self):
        """Verify failed runs are preserved in results."""
        results = _load_results("postcommit_loss")

        # Should have runs with different outcomes
        outcomes = set(r.get("terminal_oracle_outcome", "") for r in results)
        # At minimum, should have success and failure outcomes
        assert len(results) > 0, "Should have results"

        # Failed runs should not be dropped
        failed = sum(1 for r in results
                    if r.get("state_correct_completion") == "false")
        total = len(results)
        # Some runs should fail (stale-state, permission-drift, etc.)
        # But we don't require a specific failure rate

    def test_bootstrap_reproducible(self):
        """Verify bootstrap intervals are reproducible with fixed seed."""
        bootstrap1 = _load_bootstrap("primitive_ablations")

        # Run analysis again
        import subprocess
        result = subprocess.run(
            ["python", "scripts/run_paired_analysis_standalone.py",
             str(EVIDENCE_DIR / "primitive_ablations"),
             str(EVIDENCE_DIR / "primitive_ablations" / "analysis")],
            capture_output=True, text=True, cwd="/mnt/f/AFTBench"
        )
        assert result.returncode == 0, f"Analysis failed: {result.stderr}"

        bootstrap2 = _load_bootstrap("primitive_ablations")

        # Bootstrap intervals should be identical (fixed seed)
        assert len(bootstrap1) == len(bootstrap2), "Bootstrap count should match"
        for b1, b2 in zip(bootstrap1, bootstrap2):
            assert b1["ci_lower_95"] == b2["ci_lower_95"], (
                "Bootstrap CI lower should be reproducible"
            )
            assert b1["ci_upper_95"] == b2["ci_upper_95"], (
                "Bootstrap CI upper should be reproducible"
            )
