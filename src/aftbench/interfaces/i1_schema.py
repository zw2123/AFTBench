"""I1 – Schema interface."""
from __future__ import annotations
from typing import Any
from .i0_legacy import I0LegacyInterface
from .i0_shared import CAPS_BY_ID, cap_to_effect
class I1SchemaInterface(I0LegacyInterface):
    @property
    def condition_name(self) -> str: return "I1"
    def get_schema(self, capability_id: str, world_state: dict) -> dict:
        cap = CAPS_BY_ID.get(capability_id)
        if cap is None: return {"status":"error","error":f"Unknown capability: {capability_id}"}
        return {"capability_id":capability_id,"summary":cap["summary"],"input_schema":cap["input_schema"]}
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        effect = cap_to_effect(capability_id, params)
        if "error" in effect: return {"status":"error","data":None,"resource_ref":None,"error":effect["error"]}
        try: result = world.apply_effect(effect)
        except Exception as exc: return {"status":"error","data":None,"resource_ref":None,"error":str(exc)}
        if not result.get("success",True): return {"status":"error","data":None,"resource_ref":None,"error":result.get("error","Backend error")}
        payload = {k:v for k,v in result.items() if k!="success"}
        ref = payload.get("record_id") or payload.get("job_id") or payload.get("ticket_id")
        return {"status":"success","data":payload,"resource_ref":ref,"error":None}
