"""Smoke integration tests.

Includes both in-process component smoke tests and a subprocess end-to-end
test that runs the CLI with the smoke profile.
"""

import subprocess
import os

import pytest

from aftbench.config import BenchmarkConfig
from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld
from aftbench.worlds.long_running_jobs import LongRunningJobsWorld
from aftbench.worlds.large_catalog import LargeCatalogWorld
from aftbench.worlds.external_actions import ExternalActionsWorld
from aftbench.agents.scripted import ScriptedAgent
from aftbench.metrics import compute_all_metrics
from aftbench.schemas import ResultRow


# ---------------------------------------------------------------------------
# Subprocess end-to-end smoke test
# ---------------------------------------------------------------------------

class TestSmokeSubprocess:
    """Run the benchmark CLI as a subprocess with the smoke profile."""

    def test_smoke_runs(self):
        env = dict(os.environ, PYTHONPATH="src")
        r = subprocess.run(
            [".venv/bin/python", "-m", "aftbench", "run",
             "--config", "configs/smoke.yaml"],
            capture_output=True,
            text=True,
            cwd="/mnt/f/AFTBench",
            env=env,
            timeout=120,
        )
        assert r.returncode == 0, f"Smoke failed: {r.stderr}"
        assert os.path.exists("/mnt/f/AFTBench/artifacts/smoke/results.csv")


# ---------------------------------------------------------------------------
# In-process smoke tests (component-level)
# ---------------------------------------------------------------------------

class TestSmokeConfig:
    """Test smoke profile configuration loading."""

    def test_smoke_config_from_yaml(self):
        config = BenchmarkConfig.from_yaml("/mnt/f/AFTBench/configs/smoke.yaml")
        assert config.profile == "smoke"
        assert config.seed == 42

    def test_smoke_worlds_list(self):
        config = BenchmarkConfig.from_yaml("/mnt/f/AFTBench/configs/smoke.yaml")
        assert len(config.worlds) > 0

    def test_smoke_max_tasks_small(self):
        config = BenchmarkConfig.from_yaml("/mnt/f/AFTBench/configs/smoke.yaml")
        assert config.max_tasks_per_world <= 10


class TestSmokeWorldsInitialize:
    """Test that all smoke-profile worlds initialize correctly."""

    def test_enterprise_records_reset(self):
        world = EnterpriseRecordsWorld()
        world.reset(seed=42)
        state = world.get_state()
        assert len(state["records"]) > 0

    def test_long_running_jobs_reset(self):
        world = LongRunningJobsWorld()
        world.reset(seed=42)
        state = world.get_state()
        assert "jobs" in state

    def test_large_catalog_reset(self):
        world = LargeCatalogWorld()
        world.reset(seed=42)
        state = world.get_state()
        assert "catalog_sizes" in state

    def test_external_actions_reset(self):
        world = ExternalActionsWorld()
        world.reset(seed=42)
        state = world.get_state()
        assert "entities" in state


class TestSmokeAgentWorkflow:
    """Test scripted agent can operate on each world end-to-end."""

    def test_agent_creates_contact_in_er(self):
        world = EnterpriseRecordsWorld()
        world.reset(seed=42)
        agent = ScriptedAgent()

        catalog = [
            {"capability_id": "do_create", "name": "do_create",
             "description": "Create a new record"},
            {"capability_id": "do_read", "name": "do_read",
             "description": "Read a record"},
        ]

        task = {"description": "Create a new contact named John", "parameters": {
            "record_type": "contact",
            "record_id": "con-smoke",
            "fields": {"name": "John"},
        }}
        selected = agent.select_tool(catalog, task)
        assert selected == "do_create"

        schema = {"properties": {
            "record_type": {"type": "string"},
            "record_id": {"type": "string"},
            "fields": {"type": "object"},
        }}
        params = agent.build_params(selected, schema, task)
        assert params["record_type"] == "contact"

        effect = {"type": "create_record", **params}
        result = world.apply_effect(effect)
        assert result["success"] is True

        state = world.get_state()
        assert "con-smoke" in state["records"]

    def test_agent_runs_job_in_lrj(self):
        world = LongRunningJobsWorld()
        world.reset(seed=42)

        result = world.apply_effect({
            "type": "create_job",
            "job_id": "job-smoke",
            "stages": [{"name": "build"}, {"name": "test"}],
        })
        assert result["success"] is True

        result = world.apply_effect({"type": "advance_job", "job_id": "job-smoke"})
        assert result["success"] is True
        assert result["progress"] == 0.5

    def test_agent_searches_catalog(self):
        world = LargeCatalogWorld()
        world.reset(seed=42)

        result = world.apply_effect({"type": "get_catalog", "size": 10})
        assert result["success"] is True
        assert len(result["catalog"]) == 10

    def test_agent_creates_event_in_ea(self):
        world = ExternalActionsWorld()
        world.reset(seed=42)

        result = world.apply_effect({
            "type": "create_entity",
            "entity_type": "calendar_event",
            "entity_id": "evt-smoke",
            "fields": {"title": "Smoke Test Meeting", "status": "scheduled"},
        })
        assert result["success"] is True
        state = world.get_state()
        assert "evt-smoke" in state["entities"]


class TestSmokeEndToEnd:
    """Full end-to-end smoke test: init worlds, run agent, compute metrics."""

    def test_full_smoke_pipeline(self):
        worlds = {
            "enterprise_records": EnterpriseRecordsWorld(),
            "long_running_jobs": LongRunningJobsWorld(),
            "large_catalog": LargeCatalogWorld(),
            "external_actions": ExternalActionsWorld(),
        }
        for w in worlds.values():
            w.reset(seed=42)

        agent = ScriptedAgent()
        result_rows = []

        # ER: create a contact
        er_world = worlds["enterprise_records"]
        er_world.apply_effect({
            "type": "create_record",
            "record_type": "contact",
            "record_id": "con-e2e",
            "fields": {"name": "E2E Test"},
        })
        er_state = er_world.get_state()
        er_post = er_world.verify_postconditions(
            {"postconditions": [{"type": "record_exists", "name": "E2E Test",
                                  "record_type": "contact"}]},
            er_state,
        )
        er_safe = er_world.verify_safety_predicates({}, er_state)
        result_rows.append(ResultRow(
            run_id="e2e-smoke", task_id="er-create",
            agent_id=agent.agent_id(), world="enterprise_records",
            state_correct_completion=er_post and er_safe,
            postcondition_satisfied=er_post,
            safety_predicate_satisfied=er_safe,
            tool_calls=1,
        ))

        # LRJ: create and advance a job
        lrj_world = worlds["long_running_jobs"]
        lrj_world.apply_effect({
            "type": "create_job",
            "job_id": "job-e2e",
            "stages": [{"name": "build"}, {"name": "test"}],
        })
        lrj_world.apply_effect({"type": "advance_job", "job_id": "job-e2e"})
        lrj_state = lrj_world.get_state()
        lrj_post = lrj_world.verify_postconditions(
            {"postconditions": [{"type": "job_exists", "job_id": "job-e2e"}]},
            lrj_state,
        )
        result_rows.append(ResultRow(
            run_id="e2e-smoke", task_id="lrj-run",
            agent_id=agent.agent_id(), world="long_running_jobs",
            state_correct_completion=lrj_post,
            postcondition_satisfied=lrj_post,
            tool_calls=2,
        ))

        # LC: get catalog
        lc_world = worlds["large_catalog"]
        lc_result = lc_world.apply_effect({"type": "get_catalog", "size": 10})
        result_rows.append(ResultRow(
            run_id="e2e-smoke", task_id="lc-discover",
            agent_id=agent.agent_id(), world="large_catalog",
            state_correct_completion=lc_result["success"],
            postcondition_satisfied=lc_result["success"],
            tool_calls=1,
        ))

        # EA: create event
        ea_world = worlds["external_actions"]
        ea_world.apply_effect({
            "type": "create_entity",
            "entity_type": "calendar_event",
            "entity_id": "evt-e2e",
            "fields": {"title": "E2E Meeting"},
        })
        ea_state = ea_world.get_state()
        ea_post = ea_world.verify_postconditions(
            {"postconditions": [{"type": "entity_exists", "entity_id": "evt-e2e"}]},
            ea_state,
        )
        result_rows.append(ResultRow(
            run_id="e2e-smoke", task_id="ea-create",
            agent_id=agent.agent_id(), world="external_actions",
            state_correct_completion=ea_post,
            postcondition_satisfied=ea_post,
            tool_calls=1,
        ))

        # Compute metrics
        report = compute_all_metrics(result_rows)
        assert report.state_correct_completion == 1.0
        assert report.postcondition_satisfaction == 1.0
        assert report.safety_predicate_satisfaction == 1.0
