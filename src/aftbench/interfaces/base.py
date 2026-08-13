"""Abstract base class for all AFTBench interfaces."""
from __future__ import annotations
import abc
from typing import Any

class Interface(abc.ABC):
    def __init__(self) -> None:
        pass
    @property
    @abc.abstractmethod
    def condition_name(self) -> str: ...
    @abc.abstractmethod
    def discover(self, world_state: dict, task: dict) -> list[dict]: ...
    @abc.abstractmethod
    def get_schema(self, capability_id: str, world_state: dict) -> dict: ...
    @abc.abstractmethod
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict: ...
    def estimate_tokens(self, discovery_results: list[dict], schema: dict) -> tuple[int, int]:
        import json as _j
        return sum(len(t.get("summary",t.get("description","")).split())*2 for t in discovery_results)+len(_j.dumps(schema).split())*2, 0
    def get_status(self, invocation_id: str) -> dict: raise NotImplementedError
    def resume(self, invocation_id: str) -> dict: raise NotImplementedError
    def cancel(self, invocation_id: str) -> dict: raise NotImplementedError
    def reconcile(self, invocation_id: str) -> dict: raise NotImplementedError
    def get_evidence(self, invocation_id: str) -> dict: raise NotImplementedError

    def supports(self, capability: str) -> bool:
        """Whether the interface truly implements an optional capability.

        Base-class stubs raise NotImplementedError; only overridden methods
        count as supported.
        """
        method = getattr(type(self), capability, None)
        if method is None:
            return False
        base_method = getattr(Interface, capability, None)
        return method is not base_method
