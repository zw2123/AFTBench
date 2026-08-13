"""I2 – Discovery interface."""
from __future__ import annotations
import json
from typing import Any
from .i1_schema import I1SchemaInterface
from .i0_shared import CAPS
class I2DiscoveryInterface(I1SchemaInterface):
    @property
    def condition_name(self) -> str: return "I2"
    def discover(self, world_state: dict, task: dict) -> list[dict]:
        task_text = json.dumps(task, default=str).lower()
        # Use world's catalog if available, otherwise fall back to static CAPS
        catalog = world_state.get("catalog", CAPS)
        scored = []
        for cap in catalog:
            # Handle both world catalog format and static CAPS format
            desc = cap.get("description_short") or cap.get("description", "")
            words = desc.lower().split()
            score = sum(1 for w in words if len(w)>2 and w in task_text)
            scored.append((score, cap))
        scored.sort(key=lambda x: (-x[0], x[1].get("capability_id","")))
        return [{"capability_id":cap.get("capability_id",""),"summary":cap.get("description_short") or cap.get("description","")} for _,cap in scored[:5]]
    def estimate_tokens(self, discovery_results: list[dict], schema: dict) -> tuple[int, int]:
        def _get_text(t):
            return t.get("summary", t.get("description", ""))
        return sum(len(_get_text(t).split())*2 for t in discovery_results), 0
