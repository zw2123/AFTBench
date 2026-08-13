"""AFTBench interface package."""
from .base import Interface
from .i0_legacy import I0LegacyInterface
from .i1_schema import I1SchemaInterface
from .i2_discovery import I2DiscoveryInterface
from .i3_lifecycle import I3LifecycleInterface
from .i4_effect import I4EffectInterface
from .i5_full_aft import I5FullAFTInterface
from .i5_ablations import (
    I5MinusSelectiveDiscovery,
    I5MinusResumableInvocation,
    I5MinusObservableExecution,
    I5MinusStructuredOutput,
    I5MinusSideEffectContract,
    I5MinusDurableState,
    I5MinusVerification,
    ABLATION_NAMES,
    create_ablation_interface,
)
INTERFACE_MAP = {"I0":I0LegacyInterface,"I1":I1SchemaInterface,"I2":I2DiscoveryInterface,"I3":I3LifecycleInterface,"I4":I4EffectInterface,"I5":I5FullAFTInterface}
ABLATION_MAP = {name: lambda n=name: create_ablation_interface(n) for name in ABLATION_NAMES}
def get_interface(condition: str) -> Interface:
    cls = INTERFACE_MAP.get(condition)
    if cls is not None:
        return cls()
    # Check if it's an ablation
    if condition in ABLATION_MAP:
        return ABLATION_MAP[condition]()
    raise KeyError(f"Unknown interface '{condition}'. Available: {sorted(INTERFACE_MAP)} + {sorted(ABLATION_MAP)}")
__all__ = ["Interface","I0LegacyInterface","I1SchemaInterface","I2DiscoveryInterface","I3LifecycleInterface","I4EffectInterface","I5FullAFTInterface","I5MinusSelectiveDiscovery","I5MinusResumableInvocation","I5MinusObservableExecution","I5MinusStructuredOutput","I5MinusSideEffectContract","I5MinusDurableState","I5MinusVerification","INTERFACE_MAP","ABLATION_MAP","ABLATION_NAMES","get_interface","create_ablation_interface"]
