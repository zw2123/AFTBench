"""I5 ablation interfaces - each removes exactly one primitive from full AFT."""
from __future__ import annotations
from typing import Any
from dataclasses import dataclass
from .i5_full_aft import I5FullAFTInterface


@dataclass
class AFTFeatureSet:
    """Feature flags for AFT interface ablations."""
    selective_discovery: bool = True
    resumable_invocation: bool = True
    observable_execution: bool = True
    structured_output: bool = True
    side_effect_contract: bool = True
    durable_state: bool = True
    verification: bool = True
    
    def to_dict(self) -> dict:
        return {
            "selective_discovery": self.selective_discovery,
            "resumable_invocation": self.resumable_invocation,
            "observable_execution": self.observable_execution,
            "structured_output": self.structured_output,
            "side_effect_contract": self.side_effect_contract,
            "durable_state": self.durable_state,
            "verification": self.verification,
        }


class I5AblationInterface(I5FullAFTInterface):
    """Base class for I5 ablations with configurable features."""
    
    def __init__(self, features: AFTFeatureSet):
        super().__init__()
        self.features = features
        self._ablation_name = "I5-unknown"
    
    @property
    def condition_name(self) -> str:
        return self._ablation_name
    
    def get_feature_flags(self) -> dict:
        """Return feature flags for manifest recording."""
        return self.features.to_dict()


class I5MinusSelectiveDiscovery(I5AblationInterface):
    """I5 without selective discovery - exposes full catalog."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(selective_discovery=False))
        self._ablation_name = "I5-minus-selective-discovery"
    
    def discover(self, world_state: dict, task: dict) -> list[dict]:
        # Return full catalog instead of selective discovery
        # Use world's catalog if available, otherwise fall back to static CAPS
        catalog = world_state.get("catalog", None)
        if catalog is not None:
            return [{"capability_id": c["capability_id"], "name": c["capability_id"],
                     "description": c.get("description", ""), "input_schema": c.get("input_schema", {})}
                    for c in catalog]
        from .i0_shared import CAPS
        return [{"capability_id": c["capability_id"], "name": c["capability_id"], 
                 "description": c["summary"], "input_schema": c["input_schema"]} 
                for c in CAPS]


class I5MinusResumableInvocation(I5AblationInterface):
    """I5 without resumable invocation - no resume capability."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(resumable_invocation=False))
        self._ablation_name = "I5-minus-resumable-invocation"
    
    def resume(self, invocation_id: str) -> dict:
        # Disable resume capability
        return {"status": "error", "error": "Resumable invocation not available"}


class I5MinusObservableExecution(I5AblationInterface):
    """I5 without observable execution - no status query."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(observable_execution=False))
        self._ablation_name = "I5-minus-observable-execution"
    
    def get_status(self, invocation_id: str) -> dict:
        # Disable status query
        return {"status": "error", "error": "Observable execution not available"}


class I5MinusStructuredOutput(I5AblationInterface):
    """I5 without structured output - returns free-form results."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(structured_output=False))
        self._ablation_name = "I5-minus-structured-output"
    
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        result = super().invoke(capability_id, params, world, context)
        # Remove structured fields, return free-form
        if "data" in result:
            return {"status": result.get("status"), "result": str(result.get("data"))}
        return result


class I5MinusSideEffectContract(I5AblationInterface):
    """I5 without side-effect contract - no preconditions/postconditions."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(side_effect_contract=False))
        self._ablation_name = "I5-minus-side-effect-contract"
    
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        # Without a side-effect contract there is no idempotency key either.
        params = {k: v for k, v in params.items() if k != "idempotency_key"}
        result = super().invoke(capability_id, params, world, context)
        # Remove effect contract fields, including version/error metadata
        # nested inside result payloads.
        for field in ["effect_class", "preconditions", "postconditions"]:
            result.pop(field, None)
        from .i0_shared import strip_version_metadata
        for key in list(result.keys()):
            val = result[key]
            if isinstance(val, dict):
                result[key] = strip_version_metadata(val)
        result.pop("version", None)
        result.pop("current_version", None)
        result.pop("error_code", None)
        return result


class I5MinusDurableState(I5AblationInterface):
    """I5 without durable state - process-local state only."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(durable_state=False))
        self._ablation_name = "I5-minus-durable-state"
        # Clear durable state storage — no persistence across process restarts
        self._durable: dict[str, dict[str, Any]] = {}
    
    def invoke(self, capability_id: str, params: dict, world: Any, context: dict | None = None) -> dict:
        # Call parent but strip _durable after each call
        result = super().invoke(capability_id, params, world, context)
        # Clear _durable to simulate no durable storage
        self._durable.clear()
        return result
    
    def resume(self, invocation_id: str) -> dict:
        # Without durable state, resume only works if _invocations has the entry
        inv = self._invocations.get(invocation_id)
        if inv is None:
            return {"status": "error", "error": f"Durable state not available: invocation '{invocation_id}' not found."}
        inv["lifecycle_state"] = "resumed"
        return {"status": "success", "invocation_id": invocation_id, "lifecycle_state": "resumed"}
    
    def reconcile(self, invocation_id: str) -> dict:
        # Disable reconciliation (requires durable state)
        return {"status": "error", "error": "Durable state not available"}
    
    def get_evidence(self, invocation_id: str) -> dict:
        # Disable evidence retrieval (requires durable state)
        return {"status": "error", "error": "Durable state not available"}


class I5MinusVerification(I5AblationInterface):
    """I5 without verification - no postcondition checking."""
    
    def __init__(self):
        super().__init__(AFTFeatureSet(verification=False))
        self._ablation_name = "I5-minus-verification"
    
    def verify(self, invocation_id: str, world: Any) -> dict:
        # Disable verification
        return {"status": "skipped", "verified": False, "reason": "Verification disabled"}


# Factory function to create ablation interfaces
def create_ablation_interface(ablation_name: str) -> I5AblationInterface:
    """Create an ablation interface by name."""
    ablation_map = {
        "I5-minus-selective-discovery": I5MinusSelectiveDiscovery,
        "I5-minus-resumable-invocation": I5MinusResumableInvocation,
        "I5-minus-observable-execution": I5MinusObservableExecution,
        "I5-minus-structured-output": I5MinusStructuredOutput,
        "I5-minus-side-effect-contract": I5MinusSideEffectContract,
        "I5-minus-durable-state": I5MinusDurableState,
        "I5-minus-verification": I5MinusVerification,
    }
    
    cls = ablation_map.get(ablation_name)
    if cls is None:
        raise ValueError(f"Unknown ablation: {ablation_name}")
    
    return cls()


# List of all ablation names
ABLATION_NAMES = [
    "I5-minus-selective-discovery",
    "I5-minus-resumable-invocation",
    "I5-minus-observable-execution",
    "I5-minus-structured-output",
    "I5-minus-side-effect-contract",
    "I5-minus-durable-state",
    "I5-minus-verification",
]
