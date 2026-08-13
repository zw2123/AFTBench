"""Tests for ExternalActionsWorld high-level operations."""
import pytest
from aftbench.worlds.external_actions import ExternalActionsWorld


class TestExternalActionsHighLevel:
    """Tests for send_message, create_event, etc."""

    def setup_method(self):
        self.world = ExternalActionsWorld()
        self.world.reset(seed=42)

    def test_send_message_supported(self):
        """Verify send_message effect is supported."""
        result = self.world.apply_effect({
            "type": "send_message",
            "target": "alice",
            "body": "Hello"
        })
        assert result["success"] is True
        assert "message_id" in result
        assert result["target"] == "alice"
        assert "logical_effect_id" in result

    def test_exactly_once_message_effect(self):
        """Verify idempotency prevents duplicate messages."""
        idem_key = "msg-001"
        
        # First send
        result1 = self.world.apply_effect({
            "type": "send_message",
            "target": "bob",
            "body": "Test",
            "idempotency_key": idem_key
        })
        assert result1["success"] is True
        msg_id1 = result1["message_id"]
        
        # Second send with same idempotency key
        result2 = self.world.apply_effect({
            "type": "send_message",
            "target": "bob",
            "body": "Test",
            "idempotency_key": idem_key
        })
        assert result2["success"] is True
        assert result2.get("deduplicated") is True
        assert result2["message_id"] == msg_id1  # Same message ID

    def test_create_event_supported(self):
        """Verify create_event effect is supported."""
        result = self.world.apply_effect({
            "type": "create_event",
            "title": "Team Meeting",
            "participants": ["alice", "bob"],
            "start_time": "2026-01-01T10:00:00"
        })
        assert result["success"] is True
        assert "event_id" in result
        assert result["title"] == "Team Meeting"
        assert "logical_effect_id" in result

    def test_update_event_supported(self):
        """Verify update_event effect is supported."""
        # Create event first
        create_result = self.world.apply_effect({
            "type": "create_event",
            "title": "Original Title"
        })
        evt_id = create_result["event_id"]
        
        # Update event
        result = self.world.apply_effect({
            "type": "update_event",
            "event_id": evt_id,
            "fields": {"title": "Updated Title"}
        })
        assert result["success"] is True
        assert result["event_id"] == evt_id
        
        # Verify update
        state = self.world.get_state()
        evt = state["entities"][evt_id]
        assert evt["title"] == "Updated Title"

    def test_cancel_event_supported(self):
        """Verify cancel_event effect is supported."""
        # Create event first
        create_result = self.world.apply_effect({
            "type": "create_event",
            "title": "Meeting to Cancel"
        })
        evt_id = create_result["event_id"]
        
        # Cancel event
        result = self.world.apply_effect({
            "type": "cancel_event",
            "event_id": evt_id
        })
        assert result["success"] is True
        assert result["status"] == "cancelled"
        
        # Verify cancellation
        state = self.world.get_state()
        evt = state["entities"][evt_id]
        assert evt["status"] == "cancelled"

    def test_publish_article_requires_approval(self):
        """Verify publish_article requires approval when needed."""
        # pub-001 requires approval (set in reset)
        result = self.world.apply_effect({
            "type": "publish_article",
            "article_id": "pub-001"
        })
        assert result["success"] is False
        assert result["error_code"] == "APPROVAL_REQUIRED"

    def test_publish_article_with_approval(self):
        """Verify publish_article succeeds with approval."""
        # Grant approval
        self.world._approvals_granted.add("pub-001")
        
        result = self.world.apply_effect({
            "type": "publish_article",
            "article_id": "pub-001"
        })
        assert result["success"] is True
        assert result["status"] == "published"

    def test_logical_effect_id_in_effect_log(self):
        """Verify logical_effect_id is recorded in effect log."""
        result = self.world.apply_effect({
            "type": "send_message",
            "target": "charlie",
            "body": "Test message"
        })
        assert result["success"] is True
        
        # Check effect log
        state = self.world.get_state()
        effect_log = state["effect_log"]
        assert len(effect_log) > 0
        
        last_effect = effect_log[-1]
        assert "logical_effect_id" in last_effect
        assert last_effect["action"] == "send_message"

    def test_version_conflict_on_update_event(self):
        """Verify version conflict detection on update_event."""
        # Create event
        create_result = self.world.apply_effect({
            "type": "create_event",
            "title": "Test Event"
        })
        evt_id = create_result["event_id"]
        
        # Update with wrong version
        result = self.world.apply_effect({
            "type": "update_event",
            "event_id": evt_id,
            "expected_version": "v999",  # Wrong version
            "fields": {"title": "Updated"}
        })
        assert result["success"] is False
        assert result["error_code"] == "VERSION_CONFLICT"
