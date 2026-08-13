"""Tests for capability-aware agent."""
import pytest
from aftbench.agents.capability_aware import CapabilityAwareAgent


class TestCapabilityAwareAgent:
    """Test capability detection and usage tracking."""

    def setup_method(self):
        self.agent = CapabilityAwareAgent()

    def test_capability_detection_status_query(self):
        """Verify status_query capability is detected."""
        response = {
            "status": "pending",
            "invocation_id": "inv-123",
        }
        caps = self.agent._detect_capabilities(response)
        assert caps["status_query"] is True

    def test_capability_detection_invocation_resume(self):
        """Verify invocation_resume capability is detected."""
        response = {
            "status": "partial",
            "lifecycle_token": "token-123",
        }
        caps = self.agent._detect_capabilities(response)
        assert caps["invocation_resume"] is True

    def test_capability_detection_reconciliation(self):
        """Verify reconciliation capability is detected."""
        response = {
            "status": "unknown_outcome",
            "reconciliation_available": True,
        }
        caps = self.agent._detect_capabilities(response)
        assert caps["reconciliation"] is True

    def test_capability_detection_idempotent_retry(self):
        """Verify idempotent_retry capability is detected."""
        response = {
            "status": "pending",
            "idempotency_key": "idem-123",
        }
        caps = self.agent._detect_capabilities(response)
        assert caps["idempotent_retry"] is True

    def test_capability_detection_version_refresh(self):
        """Verify version_refresh capability is detected."""
        response = {
            "status": "error",
            "error_code": "VERSION_CONFLICT",
            "current_version": "v2",
        }
        caps = self.agent._detect_capabilities(response)
        assert caps["version_refresh"] is True

    def test_capability_detection_authority_revalidation(self):
        """Verify authority_revalidation capability is detected."""
        response = {
            "status": "error",
            "error_code": "PERMISSION_DENIED",
        }
        caps = self.agent._detect_capabilities(response)
        assert caps["authority_revalidation"] is True

    def test_capability_usage_tracking(self):
        """Verify capability usage is recorded."""
        response = {
            "status": "unknown_outcome",
            "reconciliation_available": True,
            "invocation_id": "inv-123",
        }
        action = self.agent.handle_response(response, {})
        assert action == "reconcile"
        
        usage = self.agent.get_capability_usage()
        assert len(usage) > 0
        assert any(u["capability"] == "reconciliation" for u in usage)

    def test_invocation_resume_when_available(self):
        """Verify agent uses invocation_resume when available."""
        response = {
            "status": "partial",
            "lifecycle_token": "token-123",
        }
        action = self.agent.handle_response(response, {})
        assert action == "resume"
        
        usage = self.agent.get_capability_usage()
        assert any(u["capability"] == "invocation_resume" for u in usage)

    def test_reconciliation_for_unknown_outcome(self):
        """Verify agent uses reconciliation for unknown_outcome."""
        response = {
            "status": "unknown_outcome",
            "reconciliation_available": True,
            "invocation_id": "inv-123",
        }
        action = self.agent.handle_response(response, {})
        assert action == "reconcile"
        
        usage = self.agent.get_capability_usage()
        assert any(u["capability"] == "reconciliation" for u in usage)

    def test_version_refresh_on_conflict(self):
        """Verify agent uses version_refresh on VERSION_CONFLICT."""
        response = {
            "status": "error",
            "error_code": "VERSION_CONFLICT",
            "current_version": "v2",
        }
        action = self.agent.handle_response(response, {})
        assert action == "refresh_and_retry"
        
        usage = self.agent.get_capability_usage()
        assert any(u["capability"] == "version_refresh" for u in usage)

    def test_safe_refusal_on_permission_denied(self):
        """Verify agent safely refuses on PERMISSION_DENIED."""
        response = {
            "status": "error",
            "error_code": "PERMISSION_DENIED",
        }
        action = self.agent.handle_response(response, {})
        assert action == "abort"
        
        usage = self.agent.get_capability_usage()
        assert any(u["capability"] == "safe_refusal" or u["capability"] == "authority_revalidation" for u in usage)

    def test_discovery_fallback_on_empty(self):
        """Verify agent uses discovery_fallback on empty discovery."""
        task = {
            "allowed_capabilities": ["crm.create_record"],
        }
        cap = self.agent.select_tool([], task)
        assert cap == "crm.create_record"
        
        usage = self.agent.get_capability_usage()
        assert any(u["capability"] == "discovery_fallback" for u in usage)

    def test_idempotent_retry_on_pending(self):
        """Verify agent uses idempotent_retry on pending with idempotency."""
        response = {
            "status": "pending",
            "idempotency_key": "idem-123",
        }
        action = self.agent.handle_response(response, {})
        assert action == "retry"
        
        usage = self.agent.get_capability_usage()
        assert any(u["capability"] == "idempotent_retry" for u in usage)

    def test_no_capability_usage_when_not_available(self):
        """Verify no capability usage recorded when capabilities not available."""
        response = {
            "status": "error",
            "error": "Generic error",
        }
        action = self.agent.handle_response(response, {})
        assert action == "retry"  # Will retry
        
        # Should not have recorded special capability usage
        usage = self.agent.get_capability_usage()
        special_caps = [u for u in usage if u["capability"] not in ["discovery_fallback"]]
        assert len(special_caps) == 0  # No special capabilities used
