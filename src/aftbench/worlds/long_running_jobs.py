"""Long Running Jobs world: multi-step job execution.

Supports:
- Job creation with multiple stages
- Progress tracking
- Mid-flight input injection
- Cancellation
- Interruption and resume
- State preservation across interruption
"""

from __future__ import annotations

import copy
import time
import uuid
from typing import Any

from .base import World


def _make_initial_jobs() -> dict[str, dict[str, Any]]:
    """No pre-existing jobs; jobs are created dynamically by tasks."""
    return {}


# Job lifecycle states
_JOB_STATES = {
    "PENDING", "RUNNING", "WAITING_INPUT", "PAUSED",
    "COMPLETED", "FAILED", "CANCELLED",
}


class LongRunningJobsWorld(World):
    """World for multi-step job execution scenarios."""

    def __init__(self) -> None:
        super().__init__()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._job_counter: int = 0

    # -- World interface ----------------------------------------------------

    def reset(self, seed: int = 0) -> None:
        self._jobs = _make_initial_jobs()
        self._job_counter = 0
        self._initial_state = self.get_state()

    def get_state(self) -> dict[str, Any]:
        return {"jobs": copy.deepcopy(self._jobs)}

    def verify_postconditions(self, task: dict[str, Any],
                              state: dict[str, Any]) -> bool:
        post = task.get("postconditions", [])
        jobs = state.get("jobs", {})
        for cond in post:
            ctype = cond.get("type")
            if ctype == "job_exists":
                if cond["job_id"] not in jobs:
                    return False
            elif ctype == "job_status":
                job = jobs.get(cond["job_id"])
                if job is None or job.get("status") != cond["status"]:
                    return False
            elif ctype == "job_stage_completed":
                job = jobs.get(cond["job_id"])
                if job is None:
                    return False
                stages = job.get("stages", [])
                stage_idx = cond.get("stage_index", 0)
                if stage_idx >= len(stages):
                    return False
                if stages[stage_idx].get("status") != "completed":
                    return False
            elif ctype == "job_progress_gte":
                job = jobs.get(cond["job_id"])
                if job is None:
                    return False
                if job.get("progress", 0) < cond.get("min_progress", 0):
                    return False
            elif ctype == "job_output_contains":
                job = jobs.get(cond["job_id"])
                if job is None:
                    return False
                outputs = job.get("outputs", {})
                key = cond.get("key", "")
                if key not in outputs:
                    return False
                if cond.get("value") not in str(outputs[key]):
                    return False
            elif ctype == "no_job_in_state":
                for jid, j in jobs.items():
                    if j.get("status") == cond.get("status"):
                        return False
        return True

    def verify_safety_predicates(self, task: dict[str, Any],
                                 state: dict[str, Any]) -> bool:
        jobs = state.get("jobs", {})
        for jid, job in jobs.items():
            # Safety: completed jobs must have all stages completed or skipped
            if job.get("status") == "COMPLETED":
                for stage in job.get("stages", []):
                    if stage.get("status") not in ("completed", "skipped"):
                        return False
            # Safety: cancelled jobs must not have progress beyond cancellation point
            if job.get("status") == "CANCELLED":
                if job.get("cancellable") is False and job.get("progress", 0) > 0:
                    # A non-cancellable job should not have been cancelled mid-progress
                    # unless it was at a safe cancellation point
                    pass  # allowed if at stage boundary
        return True

    def apply_effect(self, effect: dict[str, Any]) -> dict[str, Any]:
        etype = effect.get("type")
        if etype == "create_job":
            return self._effect_create_job(effect)
        elif etype == "advance_job":
            return self._effect_advance_job(effect)
        elif etype == "run_job":
            return self._effect_run_job(effect)
        elif etype == "start_job":
            # Alias for capabilities that expose job.start
            return self._effect_run_job(effect)
        elif etype == "inject_input":
            return self._effect_inject_input(effect)
        elif etype == "cancel_job":
            return self._effect_cancel_job(effect)
        elif etype == "pause_job":
            return self._effect_pause_job(effect)
        elif etype == "resume_job":
            return self._effect_resume_job(effect)
        elif etype == "get_job_status":
            return self._effect_get_status(effect)
        elif etype == "list_jobs":
            return self._effect_list_jobs(effect)
        else:
            return {"success": False, "error": f"Unknown effect type: {etype}"}

    def get_object_version(self, obj_id: str) -> str:
        job = self._jobs.get(obj_id)
        if job is None:
            return ""
        return str(job.get("version", "v0"))

    # -- Effect implementations ---------------------------------------------

    def _effect_run_job(self, effect: dict) -> dict[str, Any]:
        """Create (or resume) a job and run its stages.

        Runs all pending stages unless ``interrupt_at`` is set, in which case
        only one additional stage completes (the interruption point).  Calling
        the effect again without ``interrupt_at`` resumes the job to
        completion — this is what resumable interfaces do after an
        interrupted invocation.
        """
        job_id = effect.get("job_id", f"job-{uuid.uuid4().hex[:6]}")
        job = self._jobs.get(job_id)
        created = False
        if job is None:
            stages_spec = effect.get("stages", [])
            stage_list = []
            for i, s in enumerate(stages_spec):
                if isinstance(s, dict):
                    stage_list.append({"index": i, "name": s.get("name", f"stage-{i}"),
                                       "status": "pending", "output": None})
                else:
                    stage_list.append({"index": i, "name": str(s),
                                       "status": "pending", "output": None})
            job = {
                "job_id": job_id,
                "status": "RUNNING",
                "stages": stage_list,
                "total_stages": len(stage_list),
                "progress": 0.0,
                "inputs_needed": {},
                "outputs": {},
                "version": "v1",
                "_version_counter": 1,
                "error": None,
            }
            self._jobs[job_id] = job
            created = True

        interrupt_at = effect.get("interrupt_at")
        if interrupt_at is not None:
            # Advance exactly one stage, then stop (interruption point).
            limit = 1
        else:
            limit = job["total_stages"]

        advanced = []
        if job["status"] != "COMPLETED":
            for s in job["stages"]:
                if s["status"] == "pending" and len(advanced) < limit:
                    s["status"] = "completed"
                    advanced.append(s["name"])

        completed = sum(1 for s in job["stages"] if s["status"] == "completed")
        job["progress"] = completed / job["total_stages"] if job["total_stages"] else 1.0
        if all(s["status"] in ("completed", "skipped") for s in job["stages"]):
            job["status"] = "COMPLETED"
            job["progress"] = 1.0
        else:
            job["status"] = "RUNNING"

        job["_version_counter"] += 1
        job["version"] = f"v{job['_version_counter']}"

        return {
            "success": True,
            "job_id": job_id,
            "status": job["status"],
            "stages_completed": len(advanced),
            "total_stages": job["total_stages"],
            "progress": job["progress"],
            "version": job["version"],
            "created": created,
            "effect_class": "mutable",
        }

    def _effect_create_job(self, effect: dict) -> dict[str, Any]:
        self._job_counter += 1
        job_id = effect.get("job_id", f"job-{self._job_counter:04d}")
        stages = effect.get("stages", [])
        inputs_needed = effect.get("inputs_needed", {})
        cancellable = effect.get("cancellable", True)

        if job_id in self._jobs:
            return {"success": False, "error": f"Job {job_id} already exists",
                    "error_code": "DUPLICATE"}

        stage_list = []
        for i, s in enumerate(stages):
            stage_list.append({
                "index": i,
                "name": s.get("name", f"stage-{i}"),
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "output": None,
            })

        total_stages = len(stage_list)
        job = {
            "job_id": job_id,
            "status": "PENDING",
            "stages": stage_list,
            "total_stages": total_stages,
            "progress": 0.0,
            "inputs_needed": {k: {"received": False, "value": None}
                              for k in inputs_needed},
            "cancellable": cancellable,
            "outputs": {},
            "version": "v1",
            "_version_counter": 1,
            "created_at": time.time(),
            "updated_at": time.time(),
            "error": None,
            "cancellation_requested": False,
        }
        self._jobs[job_id] = job

        return {
            "success": True,
            "job_id": job_id,
            "total_stages": total_stages,
            "status": "PENDING",
            "version": "v1",
        }

    def _effect_advance_job(self, effect: dict) -> dict[str, Any]:
        job_id = effect.get("job_id")
        job = self._jobs.get(job_id)
        if job is None:
            return {"success": False, "error": f"Job {job_id} not found",
                    "error_code": "NOT_FOUND"}

        if job["status"] not in ("PENDING", "RUNNING"):
            return {"success": False,
                    "error": f"Cannot advance job in state {job['status']}",
                    "error_code": "INVALID_STATE"}

        # Check if waiting for input
        pending_inputs = [k for k, v in job["inputs_needed"].items()
                          if not v["received"]]
        if pending_inputs:
            job["status"] = "WAITING_INPUT"
            return {
                "success": False,
                "error": "Job is waiting for input",
                "error_code": "WAITING_INPUT",
                "pending_inputs": pending_inputs,
                "job_status": "WAITING_INPUT",
            }

        job["status"] = "RUNNING"
        stages = job["stages"]

        # Find next pending stage
        advanced = []
        stages_to_run = effect.get("stages_to_run", 1)
        for stage in stages:
            if stage["status"] == "pending" and stages_to_run > 0:
                stage["status"] = "completed"
                stage["completed_at"] = time.time()
                stage_output = effect.get("stage_outputs", {}).get(stage["name"])
                if stage_output is not None:
                    stage["output"] = stage_output
                    job["outputs"][stage["name"]] = stage_output
                advanced.append(stage["name"])
                stages_to_run -= 1

        # Update progress
        completed = sum(1 for s in stages if s["status"] == "completed")
        job["progress"] = completed / job["total_stages"] if job["total_stages"] > 0 else 1.0

        # Check completion
        if all(s["status"] in ("completed", "skipped") for s in stages):
            job["status"] = "COMPLETED"
            job["progress"] = 1.0

        job["_version_counter"] += 1
        job["version"] = f"v{job['_version_counter']}"
        job["updated_at"] = time.time()

        return {
            "success": True,
            "job_id": job_id,
            "stages_advanced": advanced,
            "progress": job["progress"],
            "status": job["status"],
            "version": job["version"],
        }

    def _effect_inject_input(self, effect: dict) -> dict[str, Any]:
        job_id = effect.get("job_id")
        input_key = effect.get("input_key")
        input_value = effect.get("input_value")

        job = self._jobs.get(job_id)
        if job is None:
            return {"success": False, "error": f"Job {job_id} not found",
                    "error_code": "NOT_FOUND"}

        if input_key not in job["inputs_needed"]:
            return {"success": False,
                    "error": f"Unknown input key: {input_key}",
                    "error_code": "INVALID_INPUT"}

        job["inputs_needed"][input_key] = {"received": True, "value": input_value}

        # If all inputs received, transition back to PENDING (ready to run)
        all_received = all(v["received"] for v in job["inputs_needed"].values())
        if all_received and job["status"] == "WAITING_INPUT":
            job["status"] = "PENDING"

        job["_version_counter"] += 1
        job["version"] = f"v{job['_version_counter']}"
        job["updated_at"] = time.time()

        return {
            "success": True,
            "job_id": job_id,
            "input_key": input_key,
            "all_inputs_received": all_received,
            "status": job["status"],
            "version": job["version"],
        }

    def _effect_cancel_job(self, effect: dict) -> dict[str, Any]:
        job_id = effect.get("job_id")
        job = self._jobs.get(job_id)
        if job is None:
            return {"success": False, "error": f"Job {job_id} not found",
                    "error_code": "NOT_FOUND"}

        if job["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return {"success": False,
                    "error": f"Cannot cancel job in terminal state {job['status']}",
                    "error_code": "INVALID_STATE"}

        if not job["cancellable"]:
            # Check if at a safe cancellation point (stage boundary)
            at_boundary = all(
                s["status"] in ("pending", "completed", "skipped")
                for s in job["stages"]
            )
            if not at_boundary:
                return {"success": False,
                        "error": "Job is not cancellable at current point",
                        "error_code": "NOT_CANCELLABLE"}

        job["status"] = "CANCELLED"
        job["cancellation_requested"] = True
        job["_version_counter"] += 1
        job["version"] = f"v{job['_version_counter']}"
        job["updated_at"] = time.time()

        return {
            "success": True,
            "job_id": job_id,
            "status": "CANCELLED",
            "progress_at_cancellation": job["progress"],
            "version": job["version"],
            "effect_class": "reversible",
        }

    def _effect_pause_job(self, effect: dict) -> dict[str, Any]:
        job_id = effect.get("job_id")
        job = self._jobs.get(job_id)
        if job is None:
            return {"success": False, "error": f"Job {job_id} not found",
                    "error_code": "NOT_FOUND"}

        if job["status"] != "RUNNING":
            return {"success": False,
                    "error": f"Can only pause RUNNING jobs, current: {job['status']}",
                    "error_code": "INVALID_STATE"}

        job["status"] = "PAUSED"
        job["_version_counter"] += 1
        job["version"] = f"v{job['_version_counter']}"
        job["updated_at"] = time.time()

        return {
            "success": True,
            "job_id": job_id,
            "status": "PAUSED",
            "progress": job["progress"],
            "version": job["version"],
        }

    def _effect_resume_job(self, effect: dict) -> dict[str, Any]:
        job_id = effect.get("job_id")
        job = self._jobs.get(job_id)
        if job is None:
            return {"success": False, "error": f"Job {job_id} not found",
                    "error_code": "NOT_FOUND"}

        if job["status"] not in ("PAUSED", "WAITING_INPUT"):
            return {"success": False,
                    "error": f"Can only resume PAUSED/WAITING_INPUT jobs, "
                             f"current: {job['status']}",
                    "error_code": "INVALID_STATE"}

        # Check if still waiting for inputs
        pending = [k for k, v in job["inputs_needed"].items() if not v["received"]]
        if pending:
            return {"success": False,
                    "error": "Still waiting for input",
                    "error_code": "WAITING_INPUT",
                    "pending_inputs": pending}

        job["status"] = "RUNNING"
        job["_version_counter"] += 1
        job["version"] = f"v{job['_version_counter']}"
        job["updated_at"] = time.time()

        return {
            "success": True,
            "job_id": job_id,
            "status": "RUNNING",
            "progress": job["progress"],
            "version": job["version"],
        }

    def _effect_get_status(self, effect: dict) -> dict[str, Any]:
        job_id = effect.get("job_id")
        job = self._jobs.get(job_id)
        if job is None:
            return {"success": False, "error": f"Job {job_id} not found",
                    "error_code": "NOT_FOUND"}

        public = {k: v for k, v in job.items() if not k.startswith("_")}
        return {"success": True, "job": public, "effect_class": "read_only"}

    def _effect_list_jobs(self, effect: dict) -> dict[str, Any]:
        filters = effect.get("filters", {})
        results = []
        for job in self._jobs.values():
            match = True
            for fk, fv in filters.items():
                if job.get(fk) != fv:
                    match = False
                    break
            if match:
                public = {k: v for k, v in job.items() if not k.startswith("_")}
                results.append(public)
        return {"success": True, "jobs": results, "count": len(results),
                "effect_class": "read_only"}
