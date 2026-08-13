"""I3 – Lifecycle interface."""
from __future__ import annotations
import uuid
from typing import Any
from .i2_discovery import I2DiscoveryInterface
from .i0_shared import cap_to_effect
class I3LifecycleInterface(I2DiscoveryInterface):
    def __init__(self) -> None:
        super().__init__()
        self._invocations: dict[str, dict[str, Any]] = {}
    @property
    def condition_name(self) -> str: return "I3"
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        invocation_id = f"inv-{uuid.uuid4().hex[:12]}"
        effect = cap_to_effect(capability_id, params)
        if "error" in effect: return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":effect["error"]}
        self._invocations[invocation_id] = {"capability_id":capability_id,"params":params,"lifecycle_state":"running"}
        
        # Check for interruption fault in context (like I5 does)
        if context is not None:
            fault = context.get("fault")
            if fault is not None:
                ft = getattr(fault, "fault_type", None)
                fv = ft.value if hasattr(ft, "value") else str(ft) if ft is not None else str(fault)
                if fv in ("interrupted_execution", "INTERRUPTED_EXECUTION"):
                    self._invocations[invocation_id]["lifecycle_state"] = "interrupted"
                    return {"status": "partial", "invocation_id": invocation_id,
                            "lifecycle_state": "interrupted", "error": "Execution interrupted."}
        
        try: result = world.apply_effect(effect)
        except Exception as exc:
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":str(exc)}
        if not result.get("success",True):
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","error":result.get("error","Backend error")}
        payload = {k:v for k,v in result.items() if k!="success"}
        self._invocations[invocation_id]["lifecycle_state"] = "completed"
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"completed","data":payload}
    def resume(self, invocation_id: str) -> dict:
        inv = self._invocations.get(invocation_id)
        if inv is None: return {"status":"error","error":f"Invocation '{invocation_id}' not found."}
        inv["lifecycle_state"] = "resumed"
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"resumed"}
    def get_status(self, invocation_id: str) -> dict:
        inv = self._invocations.get(invocation_id)
        if inv is None: return {"status":"error","error":f"Invocation '{invocation_id}' not found."}
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":inv["lifecycle_state"]}
