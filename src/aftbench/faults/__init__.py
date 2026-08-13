"""AFTBench faults — fault injection implementations."""

from .model import FaultSpec, FaultType, FaultOccurrence, FaultOracle
from .injector import FaultInjector

__all__ = [
    "FaultSpec",
    "FaultType",
    "FaultOccurrence",
    "FaultOracle",
    "FaultInjector",
]
