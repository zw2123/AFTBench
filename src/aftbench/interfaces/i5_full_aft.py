"""I5 – Full AFT interface."""
from __future__ import annotations
import uuid
from typing import Any
from .i4_effect import I4EffectInterface, _EFFECT_CLASS_MAP, _READ_ONLY_EFFECTS
from .i0_shared import CAPS, CAPS_BY_ID, cap_to_effect, cap_to_effect_world, false_response_fault
class I5FullAFTInterface(I4EffectInterface):
    def __init__(self) -> None:
        super().__init__()
        self._evidence: dict[str, list[dict]] = {}
        self._durable: dict[str, dict[str, Any]] = {}
    @property
    def condition_name(self) -> str: return "I5"
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        context = context or {}
        invocation_id = f"inv-{uuid.uuid4().hex[:12]}"
        fault = context.get("fault")
        
        # Check for lost_response_after_effect fault
        # This fault should occur AFTER the effect is committed
        lost_response_fault = False
        false_fault = false_response_fault(context)
        if false_fault == "false_success":
            # Report success without applying the effect.
            return {"status":"success","invocation_id":invocation_id,"effect_class":"mutable",
                    "version":"1.0","committed":False,"data":{}}
        if fault is not None:
            ft = getattr(fault,"fault_type",None)
            fv = ft.value if hasattr(ft,"value") else str(ft) if ft is not None else str(fault)
            if fv in ("lost_response_after_effect","LOST_RESPONSE_AFTER_EFFECT"):
                lost_response_fault = True
            elif fv in ("interrupted_execution","INTERRUPTED_EXECUTION"):
                # Execution interrupted mid-flight: apply the effect up to the
                # interruption point, then report partial completion.
                effect = cap_to_effect_world(capability_id, params, world)
                effect["interrupt_at"] = 1
                self._durable[invocation_id] = {"status":"partial","capability_id":capability_id,
                                                "params":params,"world":world,"effect":effect}
                self._evidence.setdefault(invocation_id,[]).append({"type":"fault_injected","fault":"interrupted_execution"})
                try:
                    result = world.apply_effect(effect)
                except Exception as exc:
                    return {"status":"error","invocation_id":invocation_id,"error":str(exc)}
                return {"status":"partial","invocation_id":invocation_id,
                        "job_id":result.get("job_id"),"progress":result.get("progress",0.0),
                        "error":"Execution interrupted."}
        
        idem_key = params.get("idempotency_key")
        if idem_key and idem_key in self._idem:
            c = self._idem[idem_key]
            return {"status":"success","invocation_id":c["invocation_id"],"idempotency_hit":True,"effect_class":c["effect_class"],"version":c["version"],"committed":True,"data":c["data"]}
        effect = cap_to_effect_world(capability_id, params, world)
        if "error" in effect: return {"status":"error","invocation_id":invocation_id,"error":effect["error"]}
        cap = CAPS_BY_ID.get(capability_id,{})
        et = cap.get("effect_type","")
        ec = "read_only" if et in _READ_ONLY_EFFECTS else _EFFECT_CLASS_MAP.get(cap.get("domain",""),"mutable")
        v = "1.0"
        self._invocations[invocation_id] = {"capability_id":capability_id,"params":params,"lifecycle_state":"running"}
        self._evidence.setdefault(invocation_id,[]).append({"type":"invocation_started"})
        try: result = world.apply_effect(effect)
        except Exception as exc:
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            self._durable[invocation_id] = {"status":"error","error":str(exc)}
            self._evidence[invocation_id].append({"type":"exception","error":str(exc)})
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","effect_class":ec,"version":v,"error":str(exc)}
        if not result.get("success",True):
            self._invocations[invocation_id]["lifecycle_state"] = "failed"
            em = result.get("error","Backend error")
            self._durable[invocation_id] = {"status":"error","error":em}
            self._evidence[invocation_id].append({"type":"backend_error","error":em})
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"failed","effect_class":ec,"version":v,
                    "error":em,"error_code":result.get("error_code",""),"current_version":result.get("current_version","")}
        
        # Effect has been committed successfully
        payload = {k:v for k,v in result.items() if k!="success"}
        self._invocations[invocation_id]["lifecycle_state"] = "completed"
        self._durable[invocation_id] = {"status":"success","committed":True}
        self._evidence[invocation_id].append({"type":"effect_committed"})
        self._evidence[invocation_id].append({"type":"invocation_completed"})
        
        # NOW check if we should drop the response (after effect is committed)
        if lost_response_fault:
            self._durable[invocation_id] = {"status":"unknown_outcome","capability_id":capability_id,"committed":True}
            self._evidence[invocation_id].append({"type":"fault_injected","fault":"lost_response_after_effect"})
            self._evidence[invocation_id].append({"type":"response_dropped"})
            return {"status":"unknown_outcome","invocation_id":invocation_id,"error":"Response lost after effect.","effect_committed":True}

        if false_fault == "false_failure":
            # The effect committed, but the response channel reports failure.
            self._evidence[invocation_id].append({"type":"fault_injected","fault":"false_failure"})
            return {"status":"error","invocation_id":invocation_id,"lifecycle_state":"completed",
                    "effect_class":ec,"version":v,
                    "error":"Internal failure (response channel fault)",
                    "error_code":"INTERNAL_FAILURE"}
        
        if idem_key: self._idem[idem_key] = {"invocation_id":invocation_id,"effect_class":ec,"version":v,"data":payload}
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"completed","effect_class":ec,"version":v,"committed":True,"data":payload}
    def reconcile(self, invocation_id: str) -> dict:
        d = self._durable.get(invocation_id)
        if d is None: return {"status":"error","error":f"Invocation '{invocation_id}' not found."}
        d["reconciled"] = True
        self._evidence.setdefault(invocation_id,[]).append({"type":"reconciled"})
        return {"status":"success","invocation_id":invocation_id,"resolved_status":d.get("status","unknown"),"reconciled":True}
    def resume(self, invocation_id: str) -> dict:
        d = self._durable.get(invocation_id)
        inv = self._invocations.get(invocation_id)
        if d is None and inv is None: return {"status":"error","error":f"Invocation '{invocation_id}' not found."}
        # Re-drive the interrupted effect to completion.
        if d and d.get("effect"):
            effect = dict(d["effect"])
            effect.pop("interrupt_at", None)
            world = d.get("world")
            if world is not None:
                try:
                    result = world.apply_effect(effect)
                    if not result.get("success", True):
                        return {"status":"error","error":result.get("error","Backend error")}
                    if inv: inv["lifecycle_state"] = "completed"
                    d["status"] = "completed"
                    self._evidence.setdefault(invocation_id,[]).append({"type":"resumed"})
                    return {"status":"success","invocation_id":invocation_id,
                            "lifecycle_state":"completed","job_id":result.get("job_id"),
                            "progress":result.get("progress",1.0)}
                except Exception as exc:
                    return {"status":"error","error":str(exc)}
        if inv: inv["lifecycle_state"] = "resumed"
        if d: d["status"] = "resumed"
        self._evidence.setdefault(invocation_id,[]).append({"type":"resumed"})
        return {"status":"success","invocation_id":invocation_id,"lifecycle_state":"resumed"}
    def get_evidence(self, invocation_id: str) -> dict:
        ev = self._evidence.get(invocation_id)
        if ev is None: return {"status":"error","error":f"No evidence for '{invocation_id}'."}
        return {"status":"success","invocation_id":invocation_id,"evidence":ev}
