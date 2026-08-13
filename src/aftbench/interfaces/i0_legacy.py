"""I0 – Legacy interface."""
from __future__ import annotations
from typing import Any
from .base import Interface
from .i0_shared import CAPS, cap_to_effect, CAPS_BY_ID

# Map short names to full capability IDs for backward compatibility
SHORT_NAME_MAP = {
    "create_record": "crm.create_record",
    "read_record": "crm.get_record",
    "get_record": "crm.get_record",
    "update_record": "crm.update_record",
    "delete_record": "crm.delete_record",
    "list_records": "crm.list_records",
    "search_records": "catalog.search",
}

class I0LegacyInterface(Interface):
    @property
    def condition_name(self) -> str: return "I0"
    def discover(self, world_state: dict, task: dict) -> list[dict]:
        catalog = world_state.get("catalog", CAPS)
        return [{"capability_id":c["capability_id"],"name":c["capability_id"],"summary":c.get("description_short") or c.get("description",""),"description":c.get("description_short") or c.get("description","")} for c in catalog]
    def get_schema(self, capability_id: str, world_state: dict) -> dict:
        # Support both short names and full capability IDs
        full_id = SHORT_NAME_MAP.get(capability_id, capability_id)
        cap = CAPS_BY_ID.get(full_id)
        if cap is None: return {"status":"error","error":f"Unknown capability: {capability_id}"}
        return cap["input_schema"]
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        # Support both short names and full capability IDs
        full_id = SHORT_NAME_MAP.get(capability_id, capability_id)
        effect = cap_to_effect(full_id, params)
        if "error" in effect: return {"status":"error","success":False,"error":effect["error"]}
        try: result = world.apply_effect(effect)
        except Exception as exc: return {"status":"error","success":False,"error":str(exc)}
        if not result.get("success",True): return {"status":"error","success":False,"error":result.get("error","Backend error")}
        return {"status":"success","success":True,**{k:v for k,v in result.items() if k!="success"}}
