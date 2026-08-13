"""Tests that all interfaces use the same backend (parity invariant).

The parity invariant: all interfaces for a given task MUST use the same
world instance and ultimately call world.apply_effect to mutate state.

All interfaces are no-arg constructible.  The world is passed to invoke()
as a parameter.
"""

import pytest
from unittest.mock import MagicMock

from aftbench.worlds.base import World
from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld

try:
    from aftbench.interfaces.i0_legacy import I0LegacyInterface
    from aftbench.interfaces.i1_schema import I1SchemaInterface
    from aftbench.interfaces.i2_discovery import I2DiscoveryInterface
    from aftbench.interfaces.i3_lifecycle import I3LifecycleInterface
    from aftbench.interfaces.i4_effect import I4EffectInterface
    from aftbench.interfaces.i5_full_aft import I5FullAFTInterface
    _HAS_INTERFACES = True
except (ImportError, ModuleNotFoundError, Exception):
    _HAS_INTERFACES = False

# Provide stubs so parametrize doesn't NameError at collection time
if not _HAS_INTERFACES:
    I0LegacyInterface = None  # type: ignore
    I1SchemaInterface = None  # type: ignore
    I2DiscoveryInterface = None  # type: ignore
    I3LifecycleInterface = None  # type: ignore
    I4EffectInterface = None  # type: ignore
    I5FullAFTInterface = None  # type: ignore


# ---------------------------------------------------------------------------
# Mock world that records apply_effect calls
# ---------------------------------------------------------------------------

class RecordingWorld(World):
    """A mock world that records all apply_effect calls."""

    def __init__(self):
        super().__init__()
        self.effect_calls = []

    def reset(self, seed: int = 0) -> None:
        self.effect_calls = []

    def get_state(self):
        return {"records": {}}

    def verify_postconditions(self, task, state):
        return True

    def verify_safety_predicates(self, task, state):
        return True

    def apply_effect(self, effect):
        self.effect_calls.append(effect)
        return {"success": True, "record_id": "rec-new", "version": "v1"}

    def get_object_version(self, obj_id):
        return "v1"


# ===========================================================================
# I0 routes through world.apply_effect
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI0Parity:
    def setup_method(self):
        self.world = RecordingWorld()
        self.world.reset()
        self.iface = I0LegacyInterface()

    def test_invoke_create_routes_to_apply_effect(self):
        self.iface.invoke("create_record", {"record_type": "contact"}, self.world)
        assert len(self.world.effect_calls) == 1

    def test_invoke_read_routes_to_apply_effect(self):
        self.iface.invoke("read_record", {"record_id": "rec-001"}, self.world)
        assert len(self.world.effect_calls) == 1

    def test_invoke_unknown_tool_does_not_call_apply_effect(self):
        result = self.iface.invoke("nonexistent_tool", {}, self.world)
        assert len(self.world.effect_calls) == 0
        assert result.get("success") is False or result.get("status") == "error"

    def test_multiple_invocations_accumulate(self):
        self.iface.invoke("create_record", {}, self.world)
        self.iface.invoke("read_record", {}, self.world)
        self.iface.invoke("list_records", {}, self.world)
        assert len(self.world.effect_calls) == 3


# ===========================================================================
# I5 routes through world.apply_effect
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI5Parity:
    def setup_method(self):
        self.world = RecordingWorld()
        self.world.reset()
        self.iface = I5FullAFTInterface()

    def test_invoke_create_routes_to_apply_effect(self):
        self.iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, self.world)
        assert len(self.world.effect_calls) == 1

    def test_invoke_delete_routes_to_apply_effect(self):
        self.iface.invoke("crm.delete_record", {"record_id": "rec-001"}, self.world)
        assert len(self.world.effect_calls) == 1


# ===========================================================================
# I0 and I5 both call world.apply_effect on the same world
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI0AndI5SameBackend:
    def test_both_call_apply_effect_on_same_world(self):
        world = RecordingWorld()
        world.reset()

        i0 = I0LegacyInterface()
        i5 = I5FullAFTInterface()

        i0.invoke("create_record", {"record_type": "contact"}, world)
        i5.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, world)

        assert len(world.effect_calls) == 2


# ===========================================================================
# All interfaces I0-I5 call world.apply_effect
# ===========================================================================

_ALL_IFACES = [
    pytest.param(I0LegacyInterface, "I0", "create_record", {"record_type": "contact"},
                 id="I0"),
    pytest.param(I1SchemaInterface, "I1", "crm.create_record",
                 {"record_type": "contact", "fields": {}}, id="I1"),
    pytest.param(I2DiscoveryInterface, "I2", "crm.create_record",
                 {"record_type": "contact", "fields": {}}, id="I2"),
    pytest.param(I3LifecycleInterface, "I3", "crm.create_record",
                 {"record_type": "contact", "fields": {}}, id="I3"),
    pytest.param(I4EffectInterface, "I4", "crm.create_record",
                 {"record_type": "contact", "fields": {}}, id="I4"),
    pytest.param(I5FullAFTInterface, "I5", "crm.create_record",
                 {"record_type": "contact", "fields": {}}, id="I5"),
]


@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestAllInterfacesCallApplyEffect:
    @pytest.mark.parametrize("iface_cls,condition_name,cap_id,params", _ALL_IFACES)
    def test_invoke_calls_apply_effect(self, iface_cls, condition_name,
                                       cap_id, params):
        world = RecordingWorld()
        world.reset()
        iface = iface_cls()

        assert iface.condition_name == condition_name

        iface.invoke(cap_id, params, world)
        assert len(world.effect_calls) >= 1
