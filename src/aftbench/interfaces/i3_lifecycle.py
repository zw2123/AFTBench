"""I3 – Lifecycle interface."""
from __future__ import annotations
import uuid
from typing import Any
from .i2_discovery import I2DiscoveryInterface
from .i0_shared import cap_to_effect, cap_to_effect_world, strip_version_metadata
class I3LifecycleInterface(I2DiscoveryInterface):
    def __init__(self) -> None:
        super().__init__()
        self._invocations: dict[str, dict[str, Any]] = {}
    @property
    def condition_name(self) -> str: return "I3"
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        invocation_id = f"inv-{uuid.uuid4().hex[:12]}"
        # I3 has no idempotency/versioning contract: keys are never sent and
        # version metadata is not exposed.
        params = {k: v for k, v in params.items() if k != "idempotency_key"}
        effect = cap_to_effect_world(capability_id, params, world)
        if "error" in effect: return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":effect["error"]}
        self._invocations[invocation_id] = {"capability_id":capability_id,"params":params,"lifecycle_state":"running","world":world,"effect":effect}
        
        # Check for interruption fault in context (like I5 does)
        if context is not None:
            fault = context.get("fault")
            if fault is not None:
                ft = getattr(fault, "fault_type", None)
                fv = ft.value if hasattr(ft, "value") else str(ft) if ft is not None else str(fault)
                if fv in ("interrupted_execution", "INTERRUPTED_EXECUTION"):
                    # Execution is interrupted mid-flight: the backend effect
                    # is applied up to the interruption point, then the
                    # invocation reports partial completion (resumable).
                    effect["interrupt_at"] = 1
                    self._invocations[invocation_id]["lifecycle_state"] = "interrupted"
                    self._invocations[invocation_id]["effect"] = effect
                    try:
                        result = world.apply_effect(effect)
                    except Exception as exc:
                        self._invocations[invocation_id]["lifecycle_state"] = "failed"
                        return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":str(exc)}
                    return {"status": "partial", "invocation_id": invocation_id,
                            "lifecycle_state": "interrupted",
                            "job_id": result.get("job_id"),
                            "progress": result.get("progress", 0.0),
                            "error": "Execution interrupted."}
        
        try: result = world.apply_effect(effect)
        except Exception as exc:
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":str(exc)}
        if not result.get("success",True):
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":result.get("error","Backend error")}
        payload = strip_version_metadata({k:v for k,v in result.items() if k!="success"})
        self._invocations[invocation_id]["lifecycle_state"] = "completed"
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"completed","data":payload}
    def resume(self, invocation_id: str) -> dict:
        inv = self._invocations.get(invocation_id)
        if inv is None: return {"status":"error","error":f"Invocation '{invocation_id}' not found."}
        # Re-drive the interrupted effect to completion.
        effect = dict(inv.get("effect") or {})
        effect.pop("interrupt_at", None)
        world = inv.get("world")
        if world is not None and effect:
            try:
                result = world.apply_effect(effect)
                if not result.get("success", True):
                    return {"status":"error","error":result.get("error","Backend error")}
                inv["lifecycle_state"] = "completed"
                return {"status":"success","invocation_id":invocation_id,
                        "lifecycle_state":"completed","job_id":result.get("job_id"),
                        "progress":result.get("progress",1.0)}
            except Exception as exc:
                return {"status":"error","error":str(exc)}
        inv["lifecycle_state"] = "resumed"
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"resumed"}
    def get_status(self, invocation_id: str) -> dict:
        inv = self._invocations.get(invocation_id)
        if inv is None: return {"status":"error","error":f"Invocation '{invocation_id}' not found."}
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":inv["lifecycle_state"]}
