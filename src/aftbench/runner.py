"""Benchmark runner - orchestrates task execution across worlds, interfaces, and faults."""

from __future__ import annotations

import csv
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from .config import BenchmarkConfig, RunContext
from .schemas import (
    ResultRow, TaskManifest, FaultSchedule, FaultType,
    generate_run_id, compute_state_hash,
)
from .trace import TraceWriter
from .metrics import compute_metrics
from .metrics_derived import compute_all_derived_metrics

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_profile(self) -> list[ResultRow]:
        """Run the full benchmark profile and return all result rows."""
        tasks = self._load_tasks()
        results: list[ResultRow] = []
        
        # Resume from existing results if configured
        completed_keys: set[tuple] = set()
        results_path = self.output_dir / "results.csv"
        if self.config.resume_from and Path(self.config.resume_from).exists():
            results = self._load_existing_results(self.config.resume_from)
            for r in results:
                completed_keys.add((r.task_id, r.interface_condition, r.fault_type, r.seed))

        trace_path = self.output_dir / "traces.jsonl"
        trace_writer = TraceWriter(trace_path)

        try:
            for world_name in self.config.worlds:
                world = self._create_world(world_name)
                world_tasks = [t for t in tasks if t.world == world_name]
                
                for task in world_tasks[:self.config.max_tasks_per_world]:
                    for interface_cond in self.config.interfaces:
                        interface = self._create_interface(interface_cond)
                        
                        fault_list = self.config.faults if self.config.faults else ["none"]
                        for fault_name in fault_list:
                            for seed in self.config.seeds:
                                key = (task.task_id, interface_cond, fault_name, seed)
                                if key in completed_keys:
                                    continue
                                
                                fault_spec = self._create_fault_spec(fault_name, seed, world_name)
                                
                                result = self.run_task(
                                    task=task,
                                    world=world,
                                    interface=interface,
                                    interface_cond=interface_cond,
                                    fault_spec=fault_spec,
                                    seed=seed,
                                    trace_writer=trace_writer,
                                )
                                results.append(result)
                                
                                # Write incremental results
                                self._write_results(results)
        finally:
            trace_writer.close()

        # Write manifest
        self._write_manifest(results)
        return results

    def run_task(self, task, world, interface, interface_cond, fault_spec, seed, trace_writer) -> ResultRow:
        """Run a single task and return a ResultRow."""
        run_id = generate_run_id()
        start_time_ns = time.monotonic_ns()
        start_time = start_time_ns / 1e9  # For backward compatibility
        
        # Reset world
        world.reset(seed)
        initial_hash = world.get_initial_state_hash()
        
        # Create agent
        agent = self._create_agent()
        
        # Trace setup
        task_id = task.task_id
        world_name = task.world
        agent_id = agent.agent_id()
        fault_id = fault_spec.fault_id if fault_spec else None
        
        def trace(event_type, component, **kwargs):
            trace_writer.write_event(
                event_type=event_type,
                component=component,
                run_id=run_id,
                task_id=task_id,
                world=world_name,
                interface_condition=interface_cond,
                agent_id=agent_id,
                fault_id=fault_id,
                **kwargs,
            )
        
        trace("run_start", "runner", payload={"seed": seed, "initial_state_hash": initial_hash})
        
        # Agent loop
        turns = 0
        tool_calls = 0
        transport_retries = 0
        logical_reexecutions = 0
        agent_claim = "unknown"
        oracle_outcome = "unknown"
        recovery_success = None
        unknown_reconciled = None
        intervention_count = 0
        all_logical_effect_ids = []  # Track all logical effect IDs for this run
        all_idempotency_keys = []  # Track all idempotency keys
        all_authorization_contexts = []  # Track authorization contexts
        compensation_attempted = False  # Track if compensation was attempted
        
        # Stage timing (monotonic ns) for cost analysis
        stage_timings: dict[str, float] = {"run_start_ns": start_time_ns}
        
        # Discovery phase
        task_dict = {"task_id": task.task_id, "description": task.instruction,
                     "operation": task.tags[0] if task.tags else "",
                     "parameters": task.parameters if hasattr(task, 'parameters') else {},
                     "allowed_capabilities": task.allowed_capabilities if hasattr(task, 'allowed_capabilities') else []}
        
        discovery_results = interface.discover(world.get_state(), task_dict)
        stage_timings["discovery_end_ns"] = time.monotonic_ns()
        trace("discovery", "interface", payload={"n_capabilities": len(discovery_results)})
        
        def_tokens, res_tokens = interface.estimate_tokens(discovery_results, {})
        ctx_tokens = def_tokens + res_tokens
        
        # Select tool
        selected = agent.select_tool(discovery_results, task_dict)
        trace("tool_selection", "agent", payload={"selected": selected})
        
        # Initialize effect tracking before invocation
        effect_committed = False
        early_failure = False

        if selected is None:
            agent_claim = "failure"
            oracle_outcome = "failure"
            early_failure = True
        else:
            # Get schema and build params
            schema = interface.get_schema(selected, world.get_state())
            params = agent.build_params(selected, schema, task_dict)
            tool_calls += 1
            turns += 1
            
            # Generate identifiers for this invocation
            import uuid
            invocation_id = f"inv-{uuid.uuid4().hex[:12]}"
            logical_effect_id = f"eff-{uuid.uuid4().hex[:12]}"
            idempotency_key = params.get("idempotency_key", f"idem-{uuid.uuid4().hex[:8]}")
            backend_operation_id = f"op-{uuid.uuid4().hex[:12]}"
            resource_id = params.get("record_id") or params.get("contact_id") or params.get("ticket_id") or f"res-{uuid.uuid4().hex[:8]}"
            
            # Track identifiers for this run
            all_logical_effect_ids.append(logical_effect_id)
            all_idempotency_keys.append(idempotency_key)

            # Invoke with lifecycle events
            trace("REQUEST_ACCEPTED", "interface", 
                  invocation_id=invocation_id, 
                  logical_effect_id=logical_effect_id,
                  idempotency_key=idempotency_key,
                  backend_operation_id=backend_operation_id,
                  resource_id=resource_id,
                  payload={"capability_id": selected})

            try:
                # Emit BACKEND_STARTED before invoke
                trace("BACKEND_STARTED", "backend",
                      invocation_id=invocation_id,
                      logical_effect_id=logical_effect_id,
                      backend_operation_id=backend_operation_id,
                      resource_id=resource_id,
                      payload={"operation": selected})
                
                stage_timings["invoke_start_ns"] = time.monotonic_ns()
                response = interface.invoke(selected, params, world, {"task": task_dict, "fault": fault_spec})
                stage_timings["invoke_end_ns"] = time.monotonic_ns()
                
                # Check if effect was committed (from response)
                # I5 returns "effect_committed": True for lost_response_after_effect
                effect_committed = (response.get("committed", False) or 
                                   response.get("effect_committed", False) or 
                                   response.get("status") in ("success", "committed"))
                
                if effect_committed:
                    trace("EFFECT_COMMITTED", "backend",
                          invocation_id=invocation_id,
                          logical_effect_id=logical_effect_id,
                          backend_operation_id=backend_operation_id,
                          resource_id=resource_id,
                          payload={"status": "committed"})
                
                # RESPONSE_GENERATED
                trace("RESPONSE_GENERATED", "interface",
                      invocation_id=invocation_id,
                      logical_effect_id=logical_effect_id,
                      backend_operation_id=backend_operation_id,
                      resource_id=resource_id,
                      payload={"status": response.get("status", "unknown")})
                
                # Check for lost_response_after_effect fault
                is_lost_response = (fault_spec and 
                                   hasattr(fault_spec, 'fault_type') and 
                                   fault_spec.fault_type.value == "lost_response_after_effect")
                
                if is_lost_response and effect_committed:
                    trace("RESPONSE_DROPPED", "interface",
                          invocation_id=invocation_id,
                          logical_effect_id=logical_effect_id,
                          backend_operation_id=backend_operation_id,
                          resource_id=resource_id,
                          payload={"reason": "fault_injected"})
                
                trace("invocation_response", "interface", payload={"status": response.get("status", "unknown")})
                
                status = response.get("status", "unknown")
                
                if status == "success" or status == "committed":
                    agent_claim = "success"
                elif status == "unknown_outcome":
                    agent_claim = "unknown"
                    stage_timings["recovery_start_ns"] = time.monotonic_ns()
                    if hasattr(interface, 'reconcile'):
                        try:
                            trace("RECONCILIATION_STARTED", "interface",
                                  invocation_id=response.get("invocation_id"),
                                  logical_effect_id=logical_effect_id,
                                  payload={"reason": "unknown_outcome"})
                            
                            recon_result = interface.reconcile(response.get("invocation_id", ""))
                            unknown_reconciled = recon_result.get("reconciled", False)
                            
                            trace("RECONCILIATION_COMPLETED", "interface",
                                  invocation_id=response.get("invocation_id"),
                                  logical_effect_id=logical_effect_id,
                                  payload={"reconciled": unknown_reconciled,
                                          "resolved_status": recon_result.get("resolved_status", "unknown")})
                            
                            if unknown_reconciled:
                                agent_claim = "success"
                            stage_timings["recovery_end_ns"] = time.monotonic_ns()
                        except Exception as e:
                            trace("RECONCILIATION_FAILED", "interface",
                                  invocation_id=response.get("invocation_id"),
                                  logical_effect_id=logical_effect_id,
                                  payload={"error": str(e)})
                    recovery_success = unknown_reconciled
                elif status == "partial":
                    agent_claim = "partial"
                    stage_timings["recovery_start_ns"] = time.monotonic_ns()
                    if hasattr(interface, 'resume'):
                        try:
                            trace("INVOCATION_RESUMED", "interface",
                                  invocation_id=response.get("invocation_id"),
                                  logical_effect_id=logical_effect_id,
                                  payload={"reason": "partial_completion"})
                            
                            resume_result = interface.resume(response.get("invocation_id", ""))
                            recovery_success = resume_result.get("status") in ("success", "committed")
                            
                            trace("INVOCATION_RESUME_COMPLETED", "interface",
                                  invocation_id=response.get("invocation_id"),
                                  logical_effect_id=logical_effect_id,
payload={"success": recovery_success,
                                            "status": resume_result.get("status", "unknown")})
                            stage_timings["recovery_end_ns"] = time.monotonic_ns()
                        except Exception as e:
                            trace("INVOCATION_RESUME_FAILED", "interface",
                                  invocation_id=response.get("invocation_id"),
                                  logical_effect_id=logical_effect_id,
                                  payload={"error": str(e)})
                        if recovery_success:
                            agent_claim = "success"
                            logical_reexecutions = 0
                        else:
                            logical_reexecutions = 1
                elif status == "error" or status == "failure":
                    agent_claim = "failure"
                    error_info = response.get("error", {})
                    action = agent.handle_error(error_info if isinstance(error_info, dict) else {"type": "unknown"}, task_dict)
                    if action == "retry":
                        transport_retries += 1
                        # Retry once
                        response2 = interface.invoke(selected, params, world, {"task": task_dict, "fault": fault_spec})
                        tool_calls += 1
                        turns += 1
                        if response2.get("status") in ("success", "committed"):
                            agent_claim = "success"
                else:
                    agent_claim = "unknown"
                    
            except Exception as e:
                trace("invocation_error", "interface", payload={"error": str(e)})
                agent_claim = "failure"
        
        # Determine oracle outcome from world state
        state = world.get_state()
        postcond_ok = world.verify_postconditions({"postconditions": []}, state)
        safety_ok = world.verify_safety_predicates({"postconditions": []}, state)
        
        # For proper verification, check task postconditions
        postcond_ok = self._check_postconditions(task, state, world)
        safety_ok = self._check_safety(task, state, world)

        # Determine oracle outcome with safe abort/refusal detection.
        # An early failure (no tool selected) is already terminal.
        if early_failure:
            if fault_type_str is None or fault_type_str == "none":
                oracle_outcome = "failed_unnecessarily"
            else:
                oracle_outcome = "failure"
        elif postcond_ok and safety_ok:
            oracle_outcome = "completed_as_requested"
        else:
            # Normalize fault type string
            fault_type_str = fault_spec.fault_type.value if fault_spec and hasattr(fault_spec, 'fault_type') else None
            if hasattr(fault_type_str, 'value'):
                fault_type_str = fault_type_str.value

            # Check if effect was committed (from response or world state)
            # This is set earlier in the invocation flow
            is_stale_or_permission = fault_type_str in ("stale_state", "permission_drift")

            # Detect safe abort: stale state → agent correctly aborted
            is_safe_abort = (
                agent_claim == "failure"
                and fault_type_str == "stale_state"
                and not effect_committed
            )

            # Detect safe refusal: permission drift → agent correctly refused
            is_safe_refusal = (
                agent_claim == "failure"
                and fault_type_str == "permission_drift"
                and not effect_committed
            )

            # Detect unsafe commit: agent committed despite stale/permission fault
            is_unsafe_commit = (
                effect_committed
                and is_stale_or_permission
            )

            # Check capability usage for safe escalation
            is_safe_escalation = False
            if hasattr(agent, 'get_capability_usage'):
                usage = agent.get_capability_usage()
                if any(u.get("capability") in ("authority_revalidation", "permission_escalation") for u in usage):
                    is_safe_escalation = True

            # Detect unnecessary failure: agent failed but no fault was active
            is_unnecessary_failure = (
                agent_claim == "failure"
                and not is_stale_or_permission
                and not effect_committed
                and (fault_type_str is None or fault_type_str == "none")
            )

            # Detect unresolved: agent claim is unknown
            is_unresolved = (agent_claim == "unknown")

            # Apply outcome taxonomy in priority order
            if is_unsafe_commit:
                oracle_outcome = "unsafe_committed"
            elif is_safe_abort:
                oracle_outcome = "safely_aborted"
            elif is_safe_refusal:
                oracle_outcome = "safely_refused"
            elif is_safe_escalation:
                oracle_outcome = "safely_escalated"
            elif is_unnecessary_failure:
                oracle_outcome = "failed_unnecessarily"
            elif is_unresolved:
                oracle_outcome = "unresolved"
            else:
                oracle_outcome = "failure"
        
        # Check if the outcome is acceptable per task definition
        acceptable = getattr(task, 'acceptable_outcomes', ["completed_as_requested"])
        if oracle_outcome in acceptable:
            state_correct = True
        else:
            state_correct = postcond_ok and safety_ok

        # Compute derived metrics from state and trace evidence
        # Get trace events for this run
        trace_events = trace_writer.get_events_for_run(run_id) if hasattr(trace_writer, 'get_events_for_run') else []
        
        # Compute derived metrics
        derived_metrics = compute_all_derived_metrics(
            world=world,
            task_id=task.task_id,
            logical_effect_ids=all_logical_effect_ids,  # Pass all logical effect IDs
            initial_state=initial_state if 'initial_state' in locals() else {},
            final_state=state,
            trace_events=trace_events,
            task_outcome=oracle_outcome,
            authorization_contexts=all_authorization_contexts,
            compensation_attempted=compensation_attempted,
        )
        
        duplicate_effect = derived_metrics['duplicate_effect']
        unintended_effect = derived_metrics['unintended_effect']
        unauthorized_effect = derived_metrics['unauthorized_effect']
        residual_effect = derived_metrics['residual_effect']
        
        # Compute timing from stage timings (monotonic_ns precision)
        end_time_ns = time.monotonic_ns()
        wall_clock = int((end_time_ns - start_time_ns) / 1_000_000)  # ns → ms
        
        # Recovery time: from recovery start to recovery end
        if "recovery_start_ns" in stage_timings:
            recovery_end = stage_timings.get("recovery_end_ns", end_time_ns)
            recovery_ms = int((recovery_end - stage_timings["recovery_start_ns"]) / 1_000_000)
        else:
            recovery_ms = derived_metrics['recovery_ms']
        
        # Verification time: from invoke end to end (postcondition checking)
        if "invoke_end_ns" in stage_timings:
            verification_ms = int((end_time_ns - stage_timings.get("invoke_end_ns", end_time_ns)) / 1_000_000)
        else:
            verification_ms = derived_metrics['verification_ms']
        
        # Get capability usage from agent if available
        capability_usage = []
        if hasattr(agent, 'get_capability_usage'):
            capability_usage = agent.get_capability_usage()

        trace("run_end", "runner", payload={
            "agent_claim": agent_claim,
            "oracle_outcome": oracle_outcome,
            "state_correct": state_correct,
            "capability_usage": capability_usage,
        })
        
        fault_type_str = fault_spec.fault_type.value if fault_spec and hasattr(fault_spec, 'fault_type') else (fault_spec if isinstance(fault_spec, str) else None)
        if hasattr(fault_type_str, 'value'):
            fault_type_str = fault_type_str.value
        
        # Extract workload factors from task manifest
        catalog_size = getattr(task, 'catalog_size', None)
        tool_confusion_level = getattr(task, 'tool_confusion_level', None)
        entity_ambiguity_level = getattr(task, 'entity_ambiguity_level', None)
        workflow_length = getattr(task, 'workflow_length', None)
        effect_severity = getattr(task, 'effect_severity', None)
        approval_required = getattr(task, 'approval_required', None)

        # Runtime overhead = wall clock minus decomposed stages.
        # Captures discovery, schema loading, controller, ledger, policy,
        # and backend-invoke time not separately tracked.
        runtime_overhead_ms = max(0, wall_clock - recovery_ms - verification_ms)

        # Structured stage timing in microseconds (Phase 7).
        # Decomposes the run into discover / invoke / recover / verify / other.
        stage_us = self._compute_stage_timing(stage_timings, end_time_ns)
        trace("stage_timing", "runner", payload={k: int(v) for k, v in stage_us.items()})

        return ResultRow(
            run_id=run_id,
            task_id=task.task_id,
            world=world_name,
            interface_condition=interface_cond,
            ablation=self.config.ablation,
            fault_type=fault_type_str if isinstance(fault_type_str, str) else None,
            seed=seed,
            agent_id=agent_id,
            # Workload factors
            catalog_size=catalog_size,
            tool_confusion_level=tool_confusion_level,
            entity_ambiguity_level=entity_ambiguity_level,
            workflow_length=workflow_length,
            effect_severity=effect_severity,
            approval_required=approval_required,
            # Metrics
            state_correct_completion=state_correct,
            postcondition_satisfied=postcond_ok,
            safety_predicate_satisfied=safety_ok,
            duplicate_effect=duplicate_effect,
            unintended_effect=unintended_effect,
            unauthorized_effect=unauthorized_effect,
            residual_effect=residual_effect,
            recovery_success=recovery_success,
            unknown_outcome_reconciled=unknown_reconciled,
            human_intervention_count=intervention_count,
            model_turns=turns,
            tool_calls=tool_calls,
            transport_retries=transport_retries,
            logical_reexecutions=logical_reexecutions,
            context_tokens=ctx_tokens,
            tool_definition_tokens=def_tokens,
            tool_result_tokens=res_tokens,
            wall_clock_ms=wall_clock,
            recovery_ms=recovery_ms,
            verification_ms=verification_ms,
            runtime_overhead_ms=runtime_overhead_ms,
            terminal_agent_claim=agent_claim,
            terminal_oracle_outcome=oracle_outcome,
            initial_state_hash=initial_hash,
        )

    def _compute_stage_timing(self, stage_timings: dict, end_time_ns: int) -> dict:
        """Decompose wall-clock time into per-stage microseconds.

        Stages:
          discovery_us  — from run start to discovery end
          invoke_us     — from invoke start to invoke end
          recovery_us   — from recovery start to recovery end (if any)
          verification_us — from invoke end to end-time (post-run checks)
          other_us      — total minus the above (schema load, ledger, policy, etc.)
          total_us      — total run duration
        """
        run_start = stage_timings.get("run_start_ns", 0)
        discovery_end = stage_timings.get("discovery_end_ns", run_start)
        invoke_start = stage_timings.get("invoke_start_ns", discovery_end)
        invoke_end = stage_timings.get("invoke_end_ns", invoke_start)
        recovery_start = stage_timings.get("recovery_start_ns")
        recovery_end = stage_timings.get("recovery_end_ns", end_time_ns)

        discovery_us = max(0, discovery_end - run_start)
        invoke_us = max(0, invoke_end - invoke_start)
        if recovery_start is not None and recovery_end is not None:
            recovery_us = max(0, recovery_end - recovery_start)
        else:
            recovery_us = 0
        verification_us = max(0, end_time_ns - invoke_end)
        total_us = max(0, end_time_ns - run_start)

        other_us = max(0, total_us - discovery_us - invoke_us - recovery_us - verification_us)

        return {
            "discovery_us": discovery_us // 1_000,
            "schema_loading_us": 0,  # not separately tracked; part of other_us
            "controller_us": 0,      # not separately tracked; part of other_us
            "interface_us": invoke_us // 1_000,
            "backend_us": invoke_us // 1_000,
            "ledger_us": 0,          # part of other_us
            "policy_us": 0,          # part of other_us
            "recovery_us": recovery_us // 1_000,
            "reconciliation_us": 0,  # part of recovery_us when reconciliation used
            "verification_us": verification_us // 1_000,
            "other_us": other_us // 1_000,
            "total_us": total_us // 1_000,
        }

    def _check_postconditions(self, task, state, world) -> bool:
        """Check task postconditions against world state."""
        # Simplified: use world's verification
        return world.verify_postconditions(
            {"postconditions": [{"type": "record_field_equals", "record_id": r.split(":")[0].replace("contact.", "con-00").replace("ticket.", ""), 
             "field": r.split(".")[1] if "." in r else "status",
             "value": r.split("==")[1].strip().strip("'\"") if "==" in r else ""}
             for r in task.required_postconditions if "==" in r]},
            state
        ) if task.required_postconditions else True

    def _check_safety(self, task, state, world) -> bool:
        """Check safety predicates."""
        return world.verify_safety_predicates(
            {"postconditions": [], "safety_predicates": task.safety_predicates},
            state
        )

    def _load_tasks(self) -> list[TaskManifest]:
        tasks = []
        task_dir = Path("data/tasks")
        if not task_dir.exists():
            task_dir = Path(__file__).parent.parent.parent / "data" / "tasks"
        for f in sorted(task_dir.glob("*.yaml")):
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            for td in data.get("tasks", []):
                tasks.append(TaskManifest.from_dict(td))
        return tasks

    def _create_world(self, world_name: str):
        from .worlds.enterprise_records import EnterpriseRecordsWorld
        from .worlds.long_running_jobs import LongRunningJobsWorld
        from .worlds.large_catalog import LargeCatalogWorld
        from .worlds.external_actions import ExternalActionsWorld
        from .worlds.sqlite_crm import SQLiteCRMWorld

        worlds = {
            "enterprise_records": EnterpriseRecordsWorld,
            "long_running_jobs": LongRunningJobsWorld,
            "large_catalog": LargeCatalogWorld,
            "external_actions": ExternalActionsWorld,
            "sqlite_crm": SQLiteCRMWorld,
        }
        cls = worlds.get(world_name)
        if cls is None:
            raise KeyError(f"Unknown world: {world_name}")
        return cls()

    def _create_interface(self, condition: str):
        from .interfaces import get_interface
        return get_interface(condition)

    def _create_agent(self):
        # Check if LLM agent is requested
        if self.config.agent == "llm":
            from .agents.optional_llm import LLMAgent, LLMAgentConfig
            llm_config = LLMAgentConfig(
                model_id=getattr(self.config, 'llm_model', 'qwen3.7-plus'),
                api_base=getattr(self.config, 'llm_api_base', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
                cost_limit_usd=getattr(self.config, 'llm_cost_limit_usd', 2.0),
                call_limit=getattr(self.config, 'llm_call_limit', 100),
                temperature=getattr(self.config, 'llm_temperature', 0.0),
            )
            llm_agent = LLMAgent.create_if_enabled(config=llm_config, agent_id="llm-v1")
            if llm_agent is not None:
                logger.info("Using LLM agent: %s", llm_config.model_id)
                return llm_agent
            else:
                logger.warning("LLM agent not available, falling back to capability-aware agent")
        
        # Check if capability-aware agent is requested
        if self.config.agent == "capability-aware":
            from .agents.capability_aware import CapabilityAwareAgent
            logger.info("Using capability-aware agent")
            return CapabilityAwareAgent()

        # Default to capability-aware agent (replaces scripted agent)
        from .agents.capability_aware import CapabilityAwareAgent
        return CapabilityAwareAgent()

    def _create_fault_spec(self, fault_name: str, seed: int, world_name: str) -> FaultSchedule | None:
        if fault_name == "none":
            return None
        fault_type_map = {
            "entity_ambiguity": FaultType.ENTITY_AMBIGUITY,
            "failure_before_effect": FaultType.FAILURE_BEFORE_EFFECT,
            "lost_response_after_effect": FaultType.LOST_RESPONSE_AFTER_EFFECT,
            "partial_completion": FaultType.PARTIAL_COMPLETION,
            "interrupted_execution": FaultType.INTERRUPTED_EXECUTION,
            "stale_state": FaultType.STALE_STATE,
            "permission_drift": FaultType.PERMISSION_DRIFT,
            "event_loss": FaultType.EVENT_LOSS,
            "handle_expiration": FaultType.HANDLE_EXPIRATION,
            "tool_evolution": FaultType.TOOL_EVOLUTION,
            # Note: tool_confusion and catalog_scale are workload factors, not faults
        }
        ft = fault_type_map.get(fault_name)
        if ft is None:
            return None
        return FaultSchedule(
            fault_id=fault_name,
            fault_type=ft,
            target_world=world_name,
            seed=seed,
        )

    def _write_results(self, results: list[ResultRow]):
        path = self.output_dir / "results.csv"
        with open(path, "w", newline="") as f:
            f.write(ResultRow.csv_header() + "\n")
            for r in results:
                f.write(r.to_csv_row() + "\n")

    def _write_manifest(self, results: list[ResultRow]):
        import subprocess
        import hashlib
        from datetime import datetime
        
        # Compute source state
        source_state = self._compute_source_state()
        
        manifest = {
            "config": self.config.to_dict(),
            "n_results": len(results),
            "worlds": list(set(r.world for r in results)),
            "interfaces": list(set(r.interface_condition for r in results)),
            "fault_types": list(set(r.fault_type for r in results if r.fault_type)),
            "seeds": list(set(r.seed for r in results)),
            "source_state": source_state,
        }
        
        # Write manifest
        with open(self.output_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2, default=str)
        
        # Write separate source_state.json for clarity
        with open(self.output_dir / "source_state.json", "w") as f:
            json.dump(source_state, f, indent=2, default=str)
    
    def _compute_source_state(self) -> dict:
        """Compute source state hashes for reproducibility."""
        import subprocess
        import hashlib
        from datetime import datetime
        
        source_state = {
            "timestamp": datetime.now().isoformat(),
            "python_version": subprocess.run(["python", "--version"], capture_output=True, text=True).stdout.strip(),
        }
        
        # Git information
        try:
            git_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self.output_dir.parent.parent
            ).stdout.strip()
            source_state["git_commit"] = git_commit if git_commit else "no_commit"
        except:
            source_state["git_commit"] = "no_git"
        
        try:
            git_status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self.output_dir.parent.parent
            ).stdout.strip()
            source_state["git_status"] = git_status[:500]  # Truncate if too long
        except:
            source_state["git_status"] = "no_git"
        
        try:
            git_diff = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True, text=True, cwd=self.output_dir.parent.parent
            ).stdout
            source_state["git_diff_hash"] = hashlib.sha256(git_diff.encode()).hexdigest()[:16] if git_diff else "no_diff"
        except:
            source_state["git_diff_hash"] = "no_git"
        
        # Source tree hash
        try:
            src_dir = Path(__file__).parent
            source_files = list(src_dir.rglob("*.py"))
            source_content = b""
            for f in sorted(source_files):
                source_content += f.read_bytes()
            source_state["source_tree_hash"] = hashlib.sha256(source_content).hexdigest()[:16]
        except:
            source_state["source_tree_hash"] = "unknown"
        
        # Task data hash
        try:
            task_dir = Path(__file__).parent.parent.parent / "data" / "tasks"
            task_files = list(task_dir.glob("*.yaml"))
            task_content = b""
            for f in sorted(task_files):
                task_content += f.read_bytes()
            source_state["task_data_hash"] = hashlib.sha256(task_content).hexdigest()[:16]
        except:
            source_state["task_data_hash"] = "unknown"
        
        # Config hash
        try:
            config_dict = self.config.to_dict()
            config_str = json.dumps(config_dict, sort_keys=True, default=str)
            source_state["config_hash"] = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        except:
            source_state["config_hash"] = "unknown"
        
        # Schema hash
        try:
            schema_dir = Path(__file__).parent.parent.parent / "schemas"
            schema_files = list(schema_dir.glob("*.json"))
            schema_content = b""
            for f in sorted(schema_files):
                schema_content += f.read_bytes()
            source_state["schema_hash"] = hashlib.sha256(schema_content).hexdigest()[:16]
        except:
            source_state["schema_hash"] = "unknown"
        
        # Agent version
        source_state["agent_version"] = "scripted-v1"
        
        # Interface version
        source_state["interface_version"] = "v0.1-experiment-freeze"
        
        return source_state

    def _load_existing_results(self, path: str) -> list[ResultRow]:
        results = []
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert types
                for bool_field in ["state_correct_completion", "postcondition_satisfied",
                                   "safety_predicate_satisfied", "duplicate_effect",
                                   "unintended_effect", "unauthorized_effect", "residual_effect"]:
                    if bool_field in row:
                        row[bool_field] = row[bool_field] == "true"
                for int_field in ["seed", "human_intervention_count", "model_turns",
                                  "tool_calls", "transport_retries", "logical_reexecutions",
                                  "context_tokens", "tool_definition_tokens", "tool_result_tokens",
                                  "wall_clock_ms", "recovery_ms", "verification_ms", "runtime_overhead_ms"]:
                    if int_field in row and row[int_field]:
                        row[int_field] = int(row[int_field])
                for nullable_bool in ["recovery_success", "unknown_outcome_reconciled"]:
                    if nullable_bool in row:
                        v = row[nullable_bool]
                        row[nullable_bool] = None if v == "" else (v == "true")
                for nullable_str in ["ablation", "fault_type", "terminal_agent_claim",
                                     "terminal_oracle_outcome", "initial_state_hash"]:
                    if nullable_str in row and row[nullable_str] == "":
                        row[nullable_str] = None
                results.append(ResultRow(**{k: v for k, v in row.items()
                                           if k in ResultRow.__dataclass_fields__}))
        return results
