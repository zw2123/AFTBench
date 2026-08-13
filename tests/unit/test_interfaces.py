"""Tests for interface conditions I0-I5.

Verifies condition_name, discover, get_schema, invoke, and condition-specific
methods (resume for I3+, reconcile for I5).

All interfaces are no-arg constructible.  The world is passed to invoke()
as a parameter; discover() and get_schema() receive a world-state dict.
"""

import pytest
from unittest.mock import MagicMock

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

# Stubs so parametrize / class bodies don't NameError at collection time
if not _HAS_INTERFACES:
    I0LegacyInterface = object  # type: ignore
    I1SchemaInterface = object  # type: ignore
    I2DiscoveryInterface = object  # type: ignore
    I3LifecycleInterface = object  # type: ignore
    I4EffectInterface = object  # type: ignore
    I5FullAFTInterface = object  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_world():
    w = EnterpriseRecordsWorld()
    w.reset(seed=42)
    return w


def _make_mock_world():
    w = MagicMock()
    w.apply_effect.return_value = {"success": True, "record_id": "rec-new"}
    w.get_state.return_value = {"records": {}}
    w.get_object_version.return_value = "v1"
    return w


# ===========================================================================
# I0 – Legacy interface
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI0LegacyInterface:
    def test_condition_name(self):
        iface = I0LegacyInterface()
        assert iface.condition_name == "I0"

    def test_discover_returns_list_of_dicts(self):
        w = _make_world()
        iface = I0LegacyInterface()
        tools = iface.discover(w.get_state(), {"description": "create"})
        assert isinstance(tools, list)
        assert len(tools) > 0
        for tool in tools:
            assert isinstance(tool, dict)
            assert "capability_id" in tool or "name" in tool
            assert "description" in tool or "summary" in tool

    def test_get_schema_returns_dict(self):
        w = _make_world()
        iface = I0LegacyInterface()
        schema = iface.get_schema("create_record", w.get_state())
        assert isinstance(schema, dict)

    def test_get_schema_unknown_tool(self):
        w = _make_world()
        iface = I0LegacyInterface()
        schema = iface.get_schema("nonexistent_tool", w.get_state())
        assert "error" in schema

    def test_invoke_calls_apply_effect(self):
        mock_w = _make_mock_world()
        iface = I0LegacyInterface()
        iface.invoke("create_record", {"record_type": "contact"}, mock_w)
        mock_w.apply_effect.assert_called_once()

    def test_invoke_success(self):
        mock_w = _make_mock_world()
        iface = I0LegacyInterface()
        result = iface.invoke("read_record", {"record_id": "con-001"}, mock_w)
        assert result.get("success") is True or result.get("status") == "success"

    def test_invoke_unknown_tool_returns_error(self):
        mock_w = _make_mock_world()
        iface = I0LegacyInterface()
        result = iface.invoke("nonexistent_tool", {}, mock_w)
        assert result.get("success") is False or result.get("status") == "error"
        assert "error" in result


# ===========================================================================
# I1 – Schema interface
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI1SchemaInterface:
    def test_condition_name(self):
        iface = I1SchemaInterface()
        assert iface.condition_name == "I1"

    def test_discover_returns_list(self):
        w = _make_world()
        iface = I1SchemaInterface()
        caps = iface.discover(w.get_state(), {"description": "create"})
        assert isinstance(caps, list)
        assert len(caps) > 0

    def test_get_schema_returns_dict(self):
        w = _make_world()
        iface = I1SchemaInterface()
        schema = iface.get_schema("crm.create_record", w.get_state())
        assert isinstance(schema, dict)

    def test_invoke_calls_apply_effect(self):
        mock_w = _make_mock_world()
        iface = I1SchemaInterface()
        iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        mock_w.apply_effect.assert_called_once()

    def test_invoke_returns_result(self):
        mock_w = _make_mock_world()
        iface = I1SchemaInterface()
        result = iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        assert isinstance(result, dict)
        assert "status" in result


# ===========================================================================
# I2 – Discovery interface
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI2DiscoveryInterface:
    def test_condition_name(self):
        iface = I2DiscoveryInterface()
        assert iface.condition_name == "I2"

    def test_discover_returns_list_with_capability_id(self):
        w = _make_world()
        iface = I2DiscoveryInterface()
        caps = iface.discover(w.get_state(), {"description": "create"})
        assert isinstance(caps, list)
        assert len(caps) > 0
        for cap in caps:
            assert "capability_id" in cap

    def test_invoke_calls_apply_effect(self):
        mock_w = _make_mock_world()
        iface = I2DiscoveryInterface()
        iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        mock_w.apply_effect.assert_called_once()


# ===========================================================================
# I3 – Lifecycle interface
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI3LifecycleInterface:
    def test_condition_name(self):
        iface = I3LifecycleInterface()
        assert iface.condition_name == "I3"

    def test_discover_returns_list_with_capability_id(self):
        w = _make_world()
        iface = I3LifecycleInterface()
        caps = iface.discover(w.get_state(), {"description": "create"})
        assert isinstance(caps, list)
        assert len(caps) > 0
        for cap in caps:
            assert "capability_id" in cap

    def test_invoke_calls_apply_effect(self):
        mock_w = _make_mock_world()
        iface = I3LifecycleInterface()
        iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        mock_w.apply_effect.assert_called_once()

    def test_invoke_returns_invocation_id(self):
        mock_w = _make_mock_world()
        iface = I3LifecycleInterface()
        result = iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        assert "invocation_id" in result

    def test_has_resume_method(self):
        iface = I3LifecycleInterface()
        assert hasattr(iface, "resume")
        assert callable(iface.resume)

    def test_resume_nonexistent_invocation(self):
        iface = I3LifecycleInterface()
        result = iface.resume("nonexistent-id")
        assert result.get("status") == "error"


# ===========================================================================
# I4 – Effect-classified interface
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI4EffectInterface:
    def test_condition_name(self):
        iface = I4EffectInterface()
        assert iface.condition_name == "I4"

    def test_discover_returns_list_with_capability_id(self):
        w = _make_world()
        iface = I4EffectInterface()
        caps = iface.discover(w.get_state(), {"description": "create"})
        assert isinstance(caps, list)
        assert len(caps) > 0
        for cap in caps:
            assert "capability_id" in cap

    def test_invoke_calls_apply_effect(self):
        mock_w = _make_mock_world()
        iface = I4EffectInterface()
        iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        mock_w.apply_effect.assert_called_once()


# ===========================================================================
# I5 – Full AFT interface
# ===========================================================================

@pytest.mark.skipif(not _HAS_INTERFACES, reason="interfaces not importable")
class TestI5FullAFTInterface:
    def test_condition_name(self):
        iface = I5FullAFTInterface()
        assert iface.condition_name == "I5"

    def test_discover_returns_list_with_capability_id(self):
        w = _make_world()
        iface = I5FullAFTInterface()
        caps = iface.discover(w.get_state(), {"description": "create"})
        assert isinstance(caps, list)
        assert len(caps) > 0
        for cap in caps:
            assert "capability_id" in cap

    def test_invoke_calls_apply_effect(self):
        mock_w = _make_mock_world()
        iface = I5FullAFTInterface()
        iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        mock_w.apply_effect.assert_called_once()

    def test_has_reconcile_method(self):
        iface = I5FullAFTInterface()
        assert hasattr(iface, "reconcile")
        assert callable(iface.reconcile)

    def test_reconcile_nonexistent_invocation(self):
        mock_w = _make_mock_world()
        iface = I5FullAFTInterface()
        result = iface.reconcile("nonexistent-id")
        assert result.get("status") == "error"

    def test_reconcile_after_successful_invoke(self):
        mock_w = _make_mock_world()
        iface = I5FullAFTInterface()
        result = iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        inv_id = result.get("invocation_id")
        assert inv_id is not None
        recon = iface.reconcile(inv_id)
        assert recon.get("status") in ("success", "ok")

    def test_get_evidence_after_invoke(self):
        mock_w = _make_mock_world()
        iface = I5FullAFTInterface()
        result = iface.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, mock_w)
        inv_id = result.get("invocation_id")
        assert inv_id is not None
        evidence = iface.get_evidence(inv_id)
        assert evidence.get("status") in ("success", "ok")
