"""Tests for ScriptedAgent tool selection, param building, response handling."""

import pytest

from aftbench.agents.scripted import ScriptedAgent


class TestScriptedAgentIdentity:
    """Test agent identity."""

    def test_default_agent_id(self):
        agent = ScriptedAgent()
        assert agent.agent_id() == "scripted-v1"

    def test_custom_agent_id(self):
        agent = ScriptedAgent(agent_id="custom-agent")
        assert agent.agent_id() == "custom-agent"


class TestScriptedAgentSelectTool:
    """Test keyword-based tool selection."""

    def setup_method(self):
        self.agent = ScriptedAgent()
        self.catalog = [
            {"capability_id": "do_create", "name": "do_create",
             "description": "Create a new record"},
            {"capability_id": "do_update", "name": "do_update",
             "description": "Update an existing record"},
            {"capability_id": "do_delete", "name": "do_delete",
             "description": "Delete a record"},
            {"capability_id": "do_read", "name": "do_read",
             "description": "Read a record by ID"},
        ]

    def test_select_create_tool(self):
        task = {"description": "Create a new contact"}
        result = self.agent.select_tool(self.catalog, task)
        assert result == "do_create"

    def test_select_delete_tool(self):
        task = {"description": "Delete the contact record"}
        result = self.agent.select_tool(self.catalog, task)
        assert result == "do_delete"

    def test_select_update_tool(self):
        task = {"description": "Update the phone number"}
        result = self.agent.select_tool(self.catalog, task)
        assert result == "do_update"

    def test_select_read_tool(self):
        # "read" keyword must appear in both task description and capability text
        task = {"description": "Read the contact record"}
        result = self.agent.select_tool(self.catalog, task)
        assert result == "do_read"

    def test_select_with_operation_field(self):
        task = {"description": "Something", "operation": "create a record"}
        result = self.agent.select_tool(self.catalog, task)
        assert result == "do_create"

    def test_empty_catalog_returns_none(self):
        task = {"description": "Create something"}
        result = self.agent.select_tool([], task)
        assert result is None

    def test_no_keyword_match_returns_first(self):
        task = {"description": "xyzzy unknown operation"}
        result = self.agent.select_tool(self.catalog, task)
        # Falls back to first capability
        assert result == "do_create"

    def test_select_list_tool(self):
        catalog = [
            {"capability_id": "do_list", "name": "do_list",
             "description": "List all records"},
            {"capability_id": "do_create", "name": "do_create",
             "description": "Create a new record"},
        ]
        task = {"description": "List all contacts"}
        result = self.agent.select_tool(catalog, task)
        assert result == "do_list"


class TestScriptedAgentBuildParams:
    """Test parameter building from task and schema."""

    def setup_method(self):
        self.agent = ScriptedAgent()

    def test_build_from_task_parameters(self):
        schema = {
            "properties": {
                "record_id": {"type": "string"},
                "fields": {"type": "object"},
            }
        }
        task = {
            "parameters": {
                "record_id": "con-001",
                "fields": {"phone": "555-1234"},
            }
        }
        params = self.agent.build_params("do_update", schema, task)
        assert params["record_id"] == "con-001"
        assert params["fields"] == {"phone": "555-1234"}

    def test_build_from_task_top_level(self):
        schema = {
            "properties": {
                "record_id": {"type": "string"},
            }
        }
        task = {"record_id": "con-001"}
        params = self.agent.build_params("do_read", schema, task)
        assert params["record_id"] == "con-001"

    def test_build_with_defaults(self):
        schema = {
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "name": {"type": "string"},
            }
        }
        task = {}
        params = self.agent.build_params("do_list", schema, task)
        assert params["limit"] == 10
        assert params["name"] == ""  # string default

    def test_build_with_type_defaults(self):
        schema = {
            "properties": {
                "count": {"type": "integer"},
                "flag": {"type": "boolean"},
                "label": {"type": "string"},
            }
        }
        task = {}
        params = self.agent.build_params("test", schema, task)
        assert params["count"] == 0
        assert params["flag"] is False
        assert params["label"] == ""

    def test_build_includes_idempotency_key(self):
        schema = {
            "properties": {
                "idempotency_key": {"type": "string"},
                "name": {"type": "string"},
            }
        }
        task = {"task_id": "task-42", "idempotency_key": "my-key-99"}
        params = self.agent.build_params("do_create", schema, task)
        assert "idempotency_key" in params
        # When task provides idempotency_key, it is used via task parameters path
        assert params["idempotency_key"] == "my-key-99"

    def test_build_idempotency_from_task(self):
        schema = {
            "properties": {
                "idempotency_key": {"type": "string"},
            }
        }
        task = {"idempotency_key": "my-key-123"}
        params = self.agent.build_params("do_create", schema, task)
        assert params["idempotency_key"] == "my-key-123"

    def test_build_empty_schema(self):
        schema = {"properties": {}}
        task = {"parameters": {"foo": "bar"}}
        params = self.agent.build_params("test", schema, task)
        assert params == {}


class TestScriptedAgentHandleResponse:
    """Test response handling and next-action decisions."""

    def setup_method(self):
        self.agent = ScriptedAgent()

    def test_success_returns_done(self):
        response = {"status": "success"}
        assert self.agent.handle_response(response, {}) == "done"

    def test_committed_returns_done(self):
        response = {"status": "committed"}
        assert self.agent.handle_response(response, {}) == "done"

    def test_partial_with_lifecycle_token_returns_resume(self):
        response = {"status": "partial", "lifecycle_token": "lc-123"}
        assert self.agent.handle_response(response, {}) == "resume"

    def test_partial_with_execution_handle_returns_resume(self):
        response = {"status": "partial", "execution_handle": "exec-456"}
        assert self.agent.handle_response(response, {}) == "resume"

    def test_partial_with_reconciliation_returns_reconcile(self):
        response = {"status": "partial", "reconciliation_available": True}
        assert self.agent.handle_response(response, {}) == "reconcile"

    def test_partial_no_recovery_returns_abort(self):
        response = {"status": "partial"}
        assert self.agent.handle_response(response, {}) == "abort"

    def test_pending_returns_retry(self):
        response = {"status": "pending"}
        assert self.agent.handle_response(response, {}) == "retry"

    def test_pending_max_retries_returns_abort(self):
        agent = ScriptedAgent()
        agent.handle_response({"status": "pending"}, {})  # retry 1
        agent.handle_response({"status": "pending"}, {})  # retry 2
        result = agent.handle_response({"status": "pending"}, {})  # abort
        assert result == "abort"

    def test_unknown_outcome_with_reconciliation(self):
        response = {"status": "unknown_outcome", "reconciliation_available": True}
        assert self.agent.handle_response(response, {}) == "reconcile"

    def test_unknown_outcome_no_reconciliation(self):
        response = {"status": "unknown_outcome"}
        assert self.agent.handle_response(response, {}) == "abort"

    def test_generic_failure_retries(self):
        response = {"status": "failure"}
        assert self.agent.handle_response(response, {}) == "retry"

    def test_generic_failure_max_retries_aborts(self):
        agent = ScriptedAgent()
        agent.handle_response({"status": "failure"}, {})
        agent.handle_response({"status": "failure"}, {})
        result = agent.handle_response({"status": "failure"}, {})
        assert result == "abort"

    def test_success_resets_retry_count(self):
        agent = ScriptedAgent()
        agent.handle_response({"status": "pending"}, {})  # retry 1
        agent.handle_response({"status": "success"}, {})  # done, resets
        result = agent.handle_response({"status": "pending"}, {})  # retry 1 again
        assert result == "retry"


class TestScriptedAgentHandleError:
    """Test error handling and next-action decisions."""

    def setup_method(self):
        self.agent = ScriptedAgent()

    def test_unstructured_error_retries(self):
        error = {"type": "unknown", "structured": False}
        assert self.agent.handle_error(error, {}) == "retry"

    def test_unstructured_error_max_retries_aborts(self):
        agent = ScriptedAgent()
        agent.handle_error({"structured": False}, {})
        agent.handle_error({"structured": False}, {})
        result = agent.handle_error({"structured": False}, {})
        assert result == "abort"

    def test_transient_error_retries(self):
        error = {"type": "TRANSIENT", "structured": True}
        assert self.agent.handle_error(error, {}) == "retry"

    def test_timeout_error_retries(self):
        error = {"type": "TIMEOUT", "structured": True}
        assert self.agent.handle_error(error, {}) == "retry"

    def test_transient_max_retries_aborts(self):
        agent = ScriptedAgent()
        agent.handle_error({"type": "TRANSIENT", "structured": True}, {})
        agent.handle_error({"type": "TRANSIENT", "structured": True}, {})
        result = agent.handle_error({"type": "TRANSIENT", "structured": True}, {})
        assert result == "abort"

    def test_partial_failure_with_lifecycle_returns_resume(self):
        error = {"type": "PARTIAL_FAILURE", "structured": True,
                 "lifecycle_token": "lc-abc"}
        assert self.agent.handle_error(error, {}) == "resume"

    def test_partial_failure_with_reconciliation(self):
        error = {"type": "PARTIAL_FAILURE", "structured": True,
                 "reconciliation_available": True}
        assert self.agent.handle_error(error, {}) == "reconcile"

    def test_partial_failure_no_recovery_aborts(self):
        error = {"type": "PARTIAL_FAILURE", "structured": True}
        assert self.agent.handle_error(error, {}) == "abort"

    def test_permission_denied_aborts(self):
        error = {"type": "PERMISSION_DENIED", "structured": True}
        assert self.agent.handle_error(error, {}) == "abort"

    def test_not_found_aborts(self):
        error = {"type": "NOT_FOUND", "structured": True}
        assert self.agent.handle_error(error, {}) == "abort"

    def test_invalid_state_aborts(self):
        error = {"type": "INVALID_STATE", "structured": True}
        assert self.agent.handle_error(error, {}) == "abort"

    def test_unknown_structured_error_retries(self):
        error = {"type": "SOMETHING_ELSE", "structured": True}
        assert self.agent.handle_error(error, {}) == "retry"
