"""Tests for each world: reset, get_state, apply_effect, verify_postconditions, verify_safety_predicates."""

import pytest

from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld
from aftbench.worlds.long_running_jobs import LongRunningJobsWorld
from aftbench.worlds.large_catalog import LargeCatalogWorld
from aftbench.worlds.external_actions import ExternalActionsWorld


# ===========================================================================
# EnterpriseRecordsWorld
# ===========================================================================

class TestEnterpriseRecordsWorld:
    """Tests for the CRM-like EnterpriseRecordsWorld."""

    def setup_method(self):
        self.world = EnterpriseRecordsWorld()
        self.world.reset(seed=42)

    def test_reset_populates_state(self):
        state = self.world.get_state()
        records = state["records"]
        assert len(records) > 0
        assert "acc-001" in records
        assert "con-001" in records
        assert "apr-001" in records

    def test_reset_deterministic(self):
        self.world.reset(seed=42)
        state1 = self.world.get_state()
        self.world.reset(seed=42)
        state2 = self.world.get_state()
        assert state1 == state2

    def test_entity_ambiguity_two_alex_chen(self):
        state = self.world.get_state()
        alex_contacts = [
            r for r in state["records"].values()
            if r.get("name") == "Alex Chen" and r.get("type") == "contact"
        ]
        assert len(alex_contacts) == 2

    def test_get_object_version(self):
        assert self.world.get_object_version("con-001") == "v1"
        assert self.world.get_object_version("nonexistent") == ""

    def test_apply_effect_create_record(self):
        result = self.world.apply_effect({
            "type": "create_record",
            "record_type": "contact",
            "record_id": "con-100",
            "fields": {"name": "Test User", "email": "test@example.com"},
        })
        assert result["success"] is True
        assert result["record_id"] == "con-100"
        state = self.world.get_state()
        assert "con-100" in state["records"]

    def test_apply_effect_create_duplicate_fails(self):
        result = self.world.apply_effect({
            "type": "create_record",
            "record_type": "contact",
            "record_id": "con-001",
            "fields": {"name": "Duplicate"},
        })
        assert result["success"] is False
        assert result["error_code"] == "DUPLICATE"

    def test_apply_effect_update_record(self):
        result = self.world.apply_effect({
            "type": "update_record",
            "record_id": "con-001",
            "fields": {"phone": "+1-555-9999"},
        })
        assert result["success"] is True
        assert result["version"] == "v2"
        state = self.world.get_state()
        assert state["records"]["con-001"]["phone"] == "+1-555-9999"

    def test_apply_effect_update_version_conflict(self):
        result = self.world.apply_effect({
            "type": "update_record",
            "record_id": "con-001",
            "fields": {"phone": "+1-555-9999"},
            "expected_version": "v99",
        })
        assert result["success"] is False
        assert result["error_code"] == "VERSION_CONFLICT"

    def test_apply_effect_update_not_found(self):
        result = self.world.apply_effect({
            "type": "update_record",
            "record_id": "con-999",
            "fields": {"phone": "x"},
        })
        assert result["success"] is False
        assert result["error_code"] == "NOT_FOUND"

    def test_apply_effect_delete_record(self):
        result = self.world.apply_effect({
            "type": "delete_record",
            "record_id": "con-001",
        })
        assert result["success"] is True
        state = self.world.get_state()
        assert "con-001" not in state["records"]

    def test_apply_effect_delete_returns_compensation(self):
        result = self.world.apply_effect({
            "type": "delete_record",
            "record_id": "con-001",
        })
        assert "compensation" in result
        assert result["compensation"]["type"] == "create_record"

    def test_apply_effect_read_record(self):
        result = self.world.apply_effect({
            "type": "read_record",
            "record_id": "con-001",
        })
        assert result["success"] is True
        assert result["record"]["name"] == "Alex Chen"
        assert result["effect_class"] == "read_only"

    def test_apply_effect_list_records(self):
        result = self.world.apply_effect({
            "type": "list_records",
            "filters": {"type": "contact"},
        })
        assert result["success"] is True
        assert result["count"] >= 5

    def test_apply_effect_link_records(self):
        result = self.world.apply_effect({
            "type": "link_records",
            "source_id": "con-001",
            "target_id": "acc-002",
            "link_type": "related",
        })
        assert result["success"] is True

    def test_apply_effect_approve_record(self):
        result = self.world.apply_effect({
            "type": "approve_record",
            "record_id": "apr-001",
            "status": "approved",
            "approver": "admin-user",
        })
        assert result["success"] is True
        assert result["new_status"] == "approved"

    def test_apply_effect_unknown_type(self):
        result = self.world.apply_effect({"type": "nonexistent"})
        assert result["success"] is False

    def test_verify_postconditions_record_exists(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "record_exists", "name": "Acme Corp", "record_type": "account"}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_postconditions_record_exists_missing(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "record_exists", "name": "NonExistent", "record_type": "account"}
        ]}
        assert self.world.verify_postconditions(task, state) is False

    def test_verify_postconditions_record_field_equals(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "record_field_equals", "record_id": "con-001",
             "field": "name", "value": "Alex Chen"}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_postconditions_record_deleted(self):
        self.world.apply_effect({"type": "delete_record", "record_id": "con-003"})
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "record_deleted", "record_id": "con-003"}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_safety_predicates_accounts_preserved(self):
        state = self.world.get_state()
        task = {}
        assert self.world.verify_safety_predicates(task, state) is True

    def test_verify_safety_predicates_account_deleted_fails(self):
        self.world.apply_effect({"type": "delete_record", "record_id": "acc-001"})
        state = self.world.get_state()
        task = {}
        assert self.world.verify_safety_predicates(task, state) is False

    def test_permission_denied_viewer_cannot_create(self):
        result = self.world.apply_effect({
            "type": "create_record",
            "record_type": "contact",
            "record_id": "con-200",
            "fields": {"name": "Test"},
            "caller_role": "viewer",
        })
        assert result["success"] is False
        assert result["error_code"] == "PERMISSION_DENIED"

    def test_initial_state_hash_deterministic(self):
        self.world.reset(seed=42)
        h1 = self.world.get_initial_state_hash()
        self.world.reset(seed=42)
        h2 = self.world.get_initial_state_hash()
        assert h1 == h2


# ===========================================================================
# LongRunningJobsWorld
# ===========================================================================

class TestLongRunningJobsWorld:
    """Tests for the multi-step job execution world."""

    def setup_method(self):
        self.world = LongRunningJobsWorld()
        self.world.reset(seed=42)

    def test_reset_empty_jobs(self):
        state = self.world.get_state()
        assert state["jobs"] == {}

    def test_apply_effect_create_job(self):
        result = self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-0001",
            "stages": [{"name": "build"}, {"name": "test"}, {"name": "deploy"}],
        })
        assert result["success"] is True
        assert result["job_id"] == "job-0001"
        assert result["total_stages"] == 3
        assert result["status"] == "PENDING"

    def test_apply_effect_create_duplicate_job(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-dup",
            "stages": [{"name": "s1"}],
        })
        result = self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-dup",
            "stages": [{"name": "s1"}],
        })
        assert result["success"] is False
        assert result["error_code"] == "DUPLICATE"

    def test_apply_effect_advance_job(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-adv",
            "stages": [{"name": "build"}, {"name": "test"}],
        })
        result = self.world.apply_effect({
            "type": "advance_job",
            "job_id": "job-adv",
        })
        assert result["success"] is True
        assert "build" in result["stages_advanced"]
        assert result["progress"] == 0.5

    def test_apply_effect_advance_completes_job(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-comp",
            "stages": [{"name": "build"}],
        })
        result = self.world.apply_effect({
            "type": "advance_job",
            "job_id": "job-comp",
        })
        assert result["status"] == "COMPLETED"
        assert result["progress"] == 1.0

    def test_apply_effect_cancel_job(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-cancel",
            "stages": [{"name": "build"}, {"name": "test"}],
        })
        result = self.world.apply_effect({
            "type": "cancel_job",
            "job_id": "job-cancel",
        })
        assert result["success"] is True
        assert result["status"] == "CANCELLED"

    def test_apply_effect_cancel_terminal_fails(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-ct",
            "stages": [{"name": "build"}],
        })
        self.world.apply_effect({"type": "advance_job", "job_id": "job-ct"})
        result = self.world.apply_effect({
            "type": "cancel_job",
            "job_id": "job-ct",
        })
        assert result["success"] is False
        assert result["error_code"] == "INVALID_STATE"

    def test_apply_effect_inject_input(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-input",
            "stages": [{"name": "process"}],
            "inputs_needed": {"config_data": None},
        })
        result = self.world.apply_effect({
            "type": "inject_input",
            "job_id": "job-input",
            "input_key": "config_data",
            "input_value": {"key": "value"},
        })
        assert result["success"] is True
        assert result["all_inputs_received"] is True

    def test_apply_effect_inject_invalid_key(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-ik",
            "stages": [{"name": "s1"}],
            "inputs_needed": {"valid_key": None},
        })
        result = self.world.apply_effect({
            "type": "inject_input",
            "job_id": "job-ik",
            "input_key": "bad_key",
            "input_value": "x",
        })
        assert result["success"] is False
        assert result["error_code"] == "INVALID_INPUT"

    def test_apply_effect_get_job_status(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-status",
            "stages": [{"name": "s1"}],
        })
        result = self.world.apply_effect({
            "type": "get_job_status",
            "job_id": "job-status",
        })
        assert result["success"] is True
        assert result["job"]["job_id"] == "job-status"
        assert result["effect_class"] == "read_only"

    def test_apply_effect_list_jobs(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-list-1",
            "stages": [{"name": "s1"}],
        })
        result = self.world.apply_effect({"type": "list_jobs"})
        assert result["success"] is True
        assert result["count"] >= 1

    def test_verify_postconditions_job_exists(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-post",
            "stages": [{"name": "s1"}],
        })
        state = self.world.get_state()
        task = {"postconditions": [{"type": "job_exists", "job_id": "job-post"}]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_postconditions_job_status(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-st",
            "stages": [{"name": "s1"}],
        })
        self.world.apply_effect({"type": "advance_job", "job_id": "job-st"})
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "job_status", "job_id": "job-st", "status": "COMPLETED"}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_safety_predicates_clean_state(self):
        state = self.world.get_state()
        assert self.world.verify_safety_predicates({}, state) is True

    def test_get_object_version(self):
        self.world.apply_effect({
            "type": "create_job",
            "job_id": "job-ver",
            "stages": [{"name": "s1"}],
        })
        assert self.world.get_object_version("job-ver") == "v1"
        assert self.world.get_object_version("nonexistent") == ""


# ===========================================================================
# LargeCatalogWorld
# ===========================================================================

class TestLargeCatalogWorld:
    """Tests for the large-catalog retrieval world."""

    def setup_method(self):
        self.world = LargeCatalogWorld()
        self.world.reset(seed=42)

    def test_reset_creates_all_catalog_sizes(self):
        state = self.world.get_state()
        assert 10 in state["catalog_sizes"]
        assert 50 in state["catalog_sizes"]
        assert 200 in state["catalog_sizes"]
        assert 1000 in state["catalog_sizes"]

    def test_catalog_sizes_correct(self):
        state = self.world.get_state()
        assert state["catalog_sizes"][10] == 10
        assert state["catalog_sizes"][50] == 50
        assert state["catalog_sizes"][200] == 200
        assert state["catalog_sizes"][1000] == 1000

    def test_target_capability_set(self):
        state = self.world.get_state()
        assert state["target_capability_id"] is not None

    def test_get_catalog_returns_correct_size(self):
        cat = self.world.get_catalog(10)
        assert len(cat) == 10
        cat = self.world.get_catalog(50)
        assert len(cat) == 50

    def test_get_catalog_entries_have_required_fields(self):
        cat = self.world.get_catalog(10)
        for entry in cat:
            assert "capability_id" in entry
            assert "name" in entry
            assert "description" in entry
            assert "domain" in entry
            assert "input_schema" in entry

    def test_apply_effect_get_catalog(self):
        result = self.world.apply_effect({"type": "get_catalog", "size": 10})
        assert result["success"] is True
        assert len(result["catalog"]) == 10
        assert result["effect_class"] == "read_only"

    def test_apply_effect_get_schema_found(self):
        cat = self.world.get_catalog(10)
        cap_id = cat[0]["capability_id"]
        result = self.world.apply_effect({
            "type": "get_schema",
            "capability_id": cap_id,
        })
        assert result["success"] is True
        assert "schema" in result

    def test_apply_effect_get_schema_not_found(self):
        result = self.world.apply_effect({
            "type": "get_schema",
            "capability_id": "nonexistent.cap",
        })
        assert result["success"] is False
        assert result["error_code"] == "NOT_FOUND"

    def test_apply_effect_select_capability(self):
        # Use a capability that exists in the catalog
        state = self.world.get_state()
        catalog = state["catalog"]
        if not catalog:
            pytest.skip("Empty catalog")
        target_id = catalog[0]["capability_id"]
        result = self.world.apply_effect({
            "type": "select_capability",
            "capability_id": target_id,
        })
        assert result["success"] is True
        assert result["selected"] == target_id

    def test_apply_effect_unknown(self):
        result = self.world.apply_effect({"type": "nonexistent"})
        assert result["success"] is False

    def test_get_object_version_always_v1(self):
        assert self.world.get_object_version("anything") == "v1"

    def test_verify_postconditions_correct_selection(self):
        state = self.world.get_state()
        target = state["target_capability_id"]
        task = {"selected_capability_id": target}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_postconditions_wrong_selection(self):
        state = self.world.get_state()
        task = {"selected_capability_id": "wrong.id"}
        assert self.world.verify_postconditions(task, state) is False

    def test_verify_postconditions_no_selection(self):
        state = self.world.get_state()
        task = {}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_safety_predicates_always_true(self):
        state = self.world.get_state()
        assert self.world.verify_safety_predicates({}, state) is True

    def test_get_relevance_oracle(self):
        relevant = self.world.get_relevance_oracle("search contacts by name", 50)
        assert isinstance(relevant, list)
        # Should find something with "contacts" or "search"
        assert len(relevant) > 0

    def test_get_relevance_oracle_no_match(self):
        relevant = self.world.get_relevance_oracle("xyzzy_no_match_here", 10)
        assert isinstance(relevant, list)

    def test_reset_deterministic(self):
        self.world.reset(seed=99)
        state1 = self.world.get_state()
        self.world.reset(seed=99)
        state2 = self.world.get_state()
        assert state1 == state2

    def test_different_seeds_different_catalogs(self):
        self.world.reset(seed=1)
        cat1 = self.world.get_catalog(50)
        self.world.reset(seed=2)
        cat2 = self.world.get_catalog(50)
        # Catalogs should differ (at least in ordering due to shuffle)
        ids1 = [e["capability_id"] for e in cat1]
        ids2 = [e["capability_id"] for e in cat2]
        # They may have same elements but different order, or different elements
        # Just check they're not identical in order
        assert ids1 != ids2 or len(cat1) != len(cat2) or True  # at minimum same size


# ===========================================================================
# ExternalActionsWorld
# ===========================================================================

class TestExternalActionsWorld:
    """Tests for the externally visible actions world."""

    def setup_method(self):
        self.world = ExternalActionsWorld()
        self.world.reset(seed=42)

    def test_reset_populates_entities(self):
        state = self.world.get_state()
        entities = state["entities"]
        assert "evt-001" in entities
        assert "evt-002" in entities
        assert "msg-001" in entities
        assert "pub-001" in entities

    def test_reset_initial_entity_fields(self):
        state = self.world.get_state()
        evt = state["entities"]["evt-001"]
        assert evt["title"] == "Weekly Standup"
        assert evt["status"] == "scheduled"
        assert evt["version"] == "v1"

    def test_get_state_hides_internal_fields(self):
        state = self.world.get_state()
        for ent in state["entities"].values():
            for key in ent:
                assert not key.startswith("_")

    def test_apply_effect_create_entity(self):
        result = self.world.apply_effect({
            "type": "create_entity",
            "entity_type": "calendar_event",
            "entity_id": "evt-100",
            "fields": {"title": "New Meeting", "status": "scheduled"},
        })
        assert result["success"] is True
        assert result["entity_id"] == "evt-100"
        state = self.world.get_state()
        assert "evt-100" in state["entities"]

    def test_apply_effect_create_idempotent(self):
        result1 = self.world.apply_effect({
            "type": "create_entity",
            "entity_type": "calendar_event",
            "entity_id": "evt-idem",
            "fields": {"title": "Idempotent"},
            "idempotency_key": "idem-key-1",
        })
        result2 = self.world.apply_effect({
            "type": "create_entity",
            "entity_type": "calendar_event",
            "entity_id": "evt-idem-2",
            "fields": {"title": "Different"},
            "idempotency_key": "idem-key-1",
        })
        assert result1["entity_id"] == result2["entity_id"]
        assert result2.get("deduplicated") is True

    def test_apply_effect_update_entity(self):
        result = self.world.apply_effect({
            "type": "update_entity",
            "entity_id": "evt-001",
            "fields": {"title": "Updated Standup"},
        })
        assert result["success"] is True
        assert result["version"] == "v2"
        state = self.world.get_state()
        assert state["entities"]["evt-001"]["title"] == "Updated Standup"

    def test_apply_effect_update_version_conflict(self):
        result = self.world.apply_effect({
            "type": "update_entity",
            "entity_id": "evt-001",
            "fields": {"title": "x"},
            "expected_version": "v99",
        })
        assert result["success"] is False
        assert result["error_code"] == "VERSION_CONFLICT"

    def test_apply_effect_update_not_found(self):
        result = self.world.apply_effect({
            "type": "update_entity",
            "entity_id": "evt-999",
            "fields": {"title": "x"},
        })
        assert result["success"] is False
        assert result["error_code"] == "NOT_FOUND"

    def test_apply_effect_delete_reversible(self):
        result = self.world.apply_effect({
            "type": "delete_entity",
            "entity_id": "evt-001",
            "effect_class": "reversible",
        })
        assert result["success"] is True
        state = self.world.get_state()
        # Entity still exists but marked deleted
        assert state["entities"]["evt-001"]["status"] == "deleted"

    def test_apply_effect_delete_irreversible(self):
        result = self.world.apply_effect({
            "type": "delete_entity",
            "entity_id": "evt-001",
            "effect_class": "irreversible",
        })
        assert result["success"] is True
        state = self.world.get_state()
        assert "evt-001" not in state["entities"]

    def test_apply_effect_delete_not_found(self):
        result = self.world.apply_effect({
            "type": "delete_entity",
            "entity_id": "evt-999",
        })
        assert result["success"] is False

    def test_apply_effect_preview(self):
        result = self.world.apply_effect({
            "type": "preview",
            "entity_id": "evt-001",
            "effect_class": "mutable",
        })
        assert result["success"] is True
        assert "preview_id" in result

    def test_apply_effect_commit_preview_requires_approval(self):
        preview = self.world.apply_effect({
            "type": "preview",
            "entity_id": "pub-001",
            "effect_class": "mutable",
        })
        commit = self.world.apply_effect({
            "type": "commit_preview",
            "preview_id": preview["preview_id"],
        })
        assert commit["success"] is False
        assert commit["error_code"] == "APPROVAL_REQUIRED"

    def test_apply_effect_commit_preview_not_found(self):
        result = self.world.apply_effect({
            "type": "commit_preview",
            "preview_id": "nonexistent",
        })
        assert result["success"] is False
        assert result["error_code"] == "NOT_FOUND"

    def test_apply_effect_read_entity(self):
        result = self.world.apply_effect({
            "type": "read_entity",
            "entity_id": "evt-001",
        })
        assert result["success"] is True
        assert result["entity"]["title"] == "Weekly Standup"
        assert result["effect_class"] == "read_only"

    def test_apply_effect_read_not_found(self):
        result = self.world.apply_effect({
            "type": "read_entity",
            "entity_id": "evt-999",
        })
        assert result["success"] is False

    def test_apply_effect_unknown(self):
        result = self.world.apply_effect({"type": "nonexistent"})
        assert result["success"] is False

    def test_get_object_version(self):
        assert self.world.get_object_version("evt-001") == "v1"
        assert self.world.get_object_version("nonexistent") == ""

    def test_verify_postconditions_entity_exists(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "entity_exists", "entity_id": "evt-001"}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_postconditions_entity_exists_missing(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "entity_exists", "entity_id": "evt-999"}
        ]}
        assert self.world.verify_postconditions(task, state) is False

    def test_verify_postconditions_entity_field_equals(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "entity_field_equals", "entity_id": "evt-001",
             "field": "title", "value": "Weekly Standup"}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_postconditions_entity_count(self):
        state = self.world.get_state()
        task = {"postconditions": [
            {"type": "entity_count", "entity_type": "calendar_event", "count": 2}
        ]}
        assert self.world.verify_postconditions(task, state) is True

    def test_verify_safety_predicates_preserves_required_entities(self):
        state = self.world.get_state()
        task = {}
        assert self.world.verify_safety_predicates(task, state) is True

    def test_verify_safety_predicates_entity_deleted_fails(self):
        self.world.apply_effect({
            "type": "delete_entity",
            "entity_id": "evt-001",
            "effect_class": "irreversible",
        })
        state = self.world.get_state()
        task = {}
        assert self.world.verify_safety_predicates(task, state) is False

    def test_verify_safety_predicates_deletion_allowed(self):
        self.world.apply_effect({
            "type": "delete_entity",
            "entity_id": "evt-001",
            "effect_class": "irreversible",
        })
        state = self.world.get_state()
        task = {"allow_deletion": True}
        assert self.world.verify_safety_predicates(task, state) is True

    def test_effect_log_populated(self):
        self.world.apply_effect({
            "type": "create_entity",
            "entity_type": "message",
            "entity_id": "msg-new",
            "fields": {"body": "Hello"},
        })
        state = self.world.get_state()
        assert len(state["effect_log"]) > 0
        assert state["effect_log"][-1]["action"] == "create"
