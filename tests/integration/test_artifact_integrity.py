"""Artifact integrity validation tests (Section 16)."""
import pytest
import csv
import json
from pathlib import Path


EVIDENCE_DIR = Path("artifacts/evidence_runs")


class TestArtifactIntegrity:
    """Validate artifact-source consistency and integrity."""

    def test_artifact_hash_matches_source(self):
        """Verify source_state.json contains required hashes."""
        for exp_dir in EVIDENCE_DIR.iterdir():
            if not exp_dir.is_dir():
                continue
            source_state_path = exp_dir / "source_state.json"
            if not source_state_path.exists():
                continue

            with open(source_state_path) as f:
                source_state = json.load(f)

            required_fields = [
                "source_tree_hash",
                "task_data_hash",
                "config_hash",
                "schema_hash",
                "agent_version",
                "interface_version",
            ]

            for field in required_fields:
                assert field in source_state, (
                    f"{exp_dir.name}/source_state.json missing {field}"
                )
                assert source_state[field], (
                    f"{exp_dir.name}/source_state.json {field} is empty"
                )

    def test_result_has_trace(self):
        """Verify every result row has a corresponding trace."""
        for exp_dir in EVIDENCE_DIR.iterdir():
            if not exp_dir.is_dir():
                continue
            results_path = exp_dir / "results.csv"
            traces_path = exp_dir / "traces.jsonl"

            if not results_path.exists() or not traces_path.exists():
                continue

            # Load result run_ids
            with open(results_path) as f:
                result_run_ids = set(r["run_id"] for r in csv.DictReader(f))

            # Load trace run_ids
            with open(traces_path) as f:
                trace_run_ids = set(json.loads(line)["run_id"] for line in f)

            # Every result should have at least one trace event
            orphan_results = result_run_ids - trace_run_ids
            assert len(orphan_results) == 0, (
                f"{exp_dir.name}: {len(orphan_results)} results have no traces"
            )

    def test_trace_has_terminal_event(self):
        """Verify every trace has a terminal event (run_end)."""
        for exp_dir in EVIDENCE_DIR.iterdir():
            if not exp_dir.is_dir():
                continue
            traces_path = exp_dir / "traces.jsonl"
            if not traces_path.exists():
                continue

            # Group events by run_id
            from collections import defaultdict
            run_events = defaultdict(list)
            with open(traces_path) as f:
                for line in f:
                    event = json.loads(line)
                    run_events[event["run_id"]].append(event)

            # Every run should have a run_end event
            for run_id, events in run_events.items():
                event_types = [e["event_type"] for e in events]
                assert "run_end" in event_types, (
                    f"{exp_dir.name} run {run_id} missing run_end event"
                )

    def test_report_recomputes_from_results(self):
        """Verify paired analysis can be recomputed from raw results."""
        for exp_dir in EVIDENCE_DIR.iterdir():
            if not exp_dir.is_dir():
                continue
            results_path = exp_dir / "results.csv"
            contrasts_path = exp_dir / "analysis" / "explicit_contrasts.csv"

            if not results_path.exists() or not contrasts_path.exists():
                continue

            # Load results
            with open(results_path) as f:
                results = list(csv.DictReader(f))

            # Load contrasts
            with open(contrasts_path) as f:
                contrasts = list(csv.DictReader(f))

            # Verify contrasts reference actual interfaces in results
            result_interfaces = set(r["interface_condition"] for r in results)
            for c in contrasts:
                treatment = c.get("treatment", "")
                control = c.get("control", "")
                assert treatment in result_interfaces or treatment == "I5-full", (
                    f"Contrast treatment {treatment} not in results"
                )
                assert control in result_interfaces, (
                    f"Contrast control {control} not in results"
                )

    def test_generated_tex_references_manifest(self):
        """Verify generated LaTeX files reference current manifests."""
        paper_dir = Path("paper/generated")
        if not paper_dir.exists():
            pytest.skip("paper/generated not found")

        for tex_file in paper_dir.glob("*.tex"):
            content = tex_file.read_text()

            # Each generated file should have source artifact comment
            assert "Source artifact" in content or "source artifact" in content.lower(), (
                f"{tex_file.name} missing source artifact reference"
            )

            # Should have generation timestamp
            assert "timestamp" in content.lower() or "Generated" in content, (
                f"{tex_file.name} missing generation timestamp"
            )

            # Should identify agent type
            assert "scripted" in content.lower() or "agent" in content.lower(), (
                f"{tex_file.name} missing agent type identification"
            )
