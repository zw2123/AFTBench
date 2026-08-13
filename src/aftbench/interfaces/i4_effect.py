"""I4 – Effect interface."""
from __future__ import annotations
import uuid
from typing import Any
from .i3_lifecycle import I3LifecycleInterface
from .i0_shared import CAPS, CAPS_BY_ID, cap_to_effect, cap_to_effect_world, false_response_fault, truncate_partial_effect
_EFFECT_CLASS_MAP = {"crm":"mutable","ticketing":"mutable","cal":"reversible","msg":"irreversible","report":"reversible","job":"reversible","catalog":"read_only","pub":"irreversible"}
_READ_ONLY_EFFECTS = {"get_catalog","search_catalog","check_job"}
class I4EffectInterface(I3LifecycleInterface):
    def __init__(self) -> None:
        super().__init__()
        self._idem: dict[str, dict[str, Any]] = {}
    @property
    def condition_name(self) -> str: return "I4"
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        invocation_id = f"inv-{uuid.uuid4().hex[:12]}"
        idem_key = params.get("idempotency_key")
        if idem_key and idem_key in self._idem:
            c = self._idem[idem_key]
            return {"status":"success","invocation_id":c["invocation_id"],"idempotency_hit":True,"effect_class":c["effect_class"],"version":c["version"],"committed":True,"data":c["data"]}
        # False-outcome faults simulate a lying response channel.
        false_fault = false_response_fault(context)
        if false_fault == "false_success":
            # Report success without applying the effect.
            return {"status":"success","invocation_id":invocation_id,"effect_class":"mutable",
                    "version":"1.0","committed":False,"data":{}}
        effect = cap_to_effect_world(capability_id, params, world)
        if false_fault == "partial_success":
            # Backend applies only part of the effect; the response channel
            # below still reports full success.
            truncate_partial_effect(effect)
        if "error" in effect: return {"status":"error","invocation_id":invocation_id,"error":effect["error"]}
        cap = CAPS_BY_ID.get(capability_id, {})
        et = cap.get("effect_type","")
        ec = "read_only" if et in _READ_ONLY_EFFECTS else _EFFECT_CLASS_MAP.get(cap.get("domain",""),"mutable")
        v = "1.0"
        self._invocations[invocation_id] = {"capability_id":capability_id,"params":params,"lifecycle_state":"running"}
        try: result = world.apply_effect(effect)
        except Exception as exc:
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","effect_class":ec,"version":v,"error":str(exc)}
        if not result.get("success",True):
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","effect_class":ec,"version":v,
                    "error":result.get("error","Backend error"),
                    "error_code":result.get("error_code",""),
                    "current_version":result.get("current_version","")}
        payload = {k:v for k,v in result.items() if k!="success"}
        self._invocations[invocation_id]["lifecycle_state"] = "completed"
        if idem_key: self._idem[idem_key] = {"invocation_id":invocation_id,"effect_class":ec,"version":v,"data":payload}
        if false_fault == "false_failure":
            # The effect committed, but the response channel reports failure.
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"completed",
                    "effect_class":ec,"version":v,
                    "error":"Internal failure (response channel fault)",
                    "error_code":"INTERNAL_FAILURE"}
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"completed","effect_class":ec,"version":v,"committed":True,"data":payload}
