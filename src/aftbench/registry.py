"""Simple decorator-based registry for AFTBench components.

Supports registration of: worlds, interfaces, agents, verifiers, faults.

Usage::

    from aftbench.registry import register_world, get_world

    @register_world("filesystem")
    class FilesystemWorld:
        ...

    world_cls = get_world("filesystem")
"""

from __future__ import annotations

from typing import Any, Callable, Dict, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Internal registries
# ---------------------------------------------------------------------------

_REGISTRIES: Dict[str, Dict[str, Any]] = {
    "world": {},
    "interface": {},
    "agent": {},
    "verifier": {},
    "fault": {},
}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _register(kind: str, name: str, obj: Any) -> Any:
    """Register *obj* under *name* in the *kind* registry."""
    registry = _REGISTRIES.get(kind)
    if registry is None:
        raise ValueError(f"Unknown registry kind: {kind!r}")
    if name in registry:
        raise ValueError(
            f"Duplicate registration: {kind} {name!r} is already registered"
        )
    registry[name] = obj
    return obj


def _get(kind: str, name: str) -> Any:
    """Look up *name* in the *kind* registry."""
    registry = _REGISTRIES.get(kind)
    if registry is None:
        raise ValueError(f"Unknown registry kind: {kind!r}")
    if name not in registry:
        available = ", ".join(sorted(registry)) or "(none)"
        raise KeyError(f"{kind} {name!r} not found.  Available: {available}")
    return registry[name]


def _list(kind: str) -> Dict[str, Any]:
    """Return a copy of the *kind* registry."""
    registry = _REGISTRIES.get(kind)
    if registry is None:
        raise ValueError(f"Unknown registry kind: {kind!r}")
    return dict(registry)


# ---------------------------------------------------------------------------
# Decorator factories
# ---------------------------------------------------------------------------

def register_world(name: str) -> Callable[[T], T]:
    """Decorator: register a world class or factory under *name*."""
    def decorator(obj: T) -> T:
        _register("world", name, obj)
        return obj
    return decorator


def register_interface(name: str) -> Callable[[T], T]:
    """Decorator: register an interface class or factory under *name*."""
    def decorator(obj: T) -> T:
        _register("interface", name, obj)
        return obj
    return decorator


def register_agent(name: str) -> Callable[[T], T]:
    """Decorator: register an agent class or factory under *name*."""
    def decorator(obj: T) -> T:
        _register("agent", name, obj)
        return obj
    return decorator


def register_verifier(name: str) -> Callable[[T], T]:
    """Decorator: register a verifier class or factory under *name*."""
    def decorator(obj: T) -> T:
        _register("verifier", name, obj)
        return obj
    return decorator


def register_fault(name: str) -> Callable[[T], T]:
    """Decorator: register a fault injector class or factory under *name*."""
    def decorator(obj: T) -> T:
        _register("fault", name, obj)
        return obj
    return decorator


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def get_world(name: str) -> Any:
    """Look up a registered world by name."""
    return _get("world", name)


def get_interface(name: str) -> Any:
    """Look up a registered interface by name."""
    return _get("interface", name)


def get_agent(name: str) -> Any:
    """Look up a registered agent by name."""
    return _get("agent", name)


def get_verifier(name: str) -> Any:
    """Look up a registered verifier by name."""
    return _get("verifier", name)


def get_fault(name: str) -> Any:
    """Look up a registered fault injector by name."""
    return _get("fault", name)


# ---------------------------------------------------------------------------
# Listing functions
# ---------------------------------------------------------------------------

def list_worlds() -> Dict[str, Any]:
    """Return all registered worlds."""
    return _list("world")


def list_interfaces() -> Dict[str, Any]:
    """Return all registered interfaces."""
    return _list("interface")


def list_agents() -> Dict[str, Any]:
    """Return all registered agents."""
    return _list("agent")


def list_verifiers() -> Dict[str, Any]:
    """Return all registered verifiers."""
    return _list("verifier")


def list_faults() -> Dict[str, Any]:
    """Return all registered fault injectors."""
    return _list("fault")


# ---------------------------------------------------------------------------
# Utility: clear all registries (useful for testing)
# ---------------------------------------------------------------------------

def clear_all() -> None:
    """Remove all registrations.  Intended for test teardown."""
    for registry in _REGISTRIES.values():
        registry.clear()


# Compatibility aliases
def register(kind: str, name: str) -> Callable:
    """Generic registration decorator."""
    def decorator(cls_or_fn: Any) -> Any:
        _register(kind, name, cls_or_fn)
        return cls_or_fn
    return decorator


def get_registered(kind: str, name: str) -> Any:
    """Generic lookup."""
    return _get(kind, name)


def list_registered(kind: str) -> list[str]:
    """List registered names for a kind."""
    return list(_REGISTRIES.get(kind, {}).keys())
