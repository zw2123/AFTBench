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
        scored = []
        for cap in CAPS:
            words = cap["description_short"].lower().split()
            score = sum(1 for w in words if len(w)>2 and w in task_text)
            scored.append((score, cap))
        scored.sort(key=lambda x: (-x[0], x[1]["capability_id"]))
        return [{"capability_id":cap["capability_id"],"summary":cap["description_short"]} for _,cap in scored[:5]]
    def estimate_tokens(self, discovery_results: list[dict], schema: dict) -> tuple[int, int]:
        return sum(len(t.get("summary","").split())*2 for t in discovery_results), 0
