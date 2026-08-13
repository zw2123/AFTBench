"""Shared capability catalogue. 23 capabilities across 8 domains."""
from __future__ import annotations
from typing import Any

# Capability catalogue — used by all interfaces
CAPS: list[dict[str, Any]] = [
    {"capability_id":"crm.create_record","summary":"Create a new CRM record","description_short":"Create record","domain":"crm","effect_type":"create_record","input_schema":{"type":"object","required":["record_type","fields"],"properties":{"record_type":{"type":"string"},"contact_id":{"type":"string"},"fields":{"type":"object"}}}},
    {"capability_id":"crm.update_record","summary":"Update an existing CRM record","description_short":"Update record","domain":"crm","effect_type":"update_record","input_schema":{"type":"object","required":["record_id","fields"],"properties":{"record_id":{"type":"string"},"fields":{"type":"object"},"expected_version":{"type":"string"}}}},
    {"capability_id":"crm.delete_record","summary":"Delete a CRM record by ID","description_short":"Delete record","domain":"crm","effect_type":"delete_record","input_schema":{"type":"object","required":["record_id"],"properties":{"record_id":{"type":"string"}}}},
    {"capability_id":"crm.get_record","summary":"Retrieve a CRM record by ID","description_short":"Get record","domain":"crm","effect_type":"read_record","input_schema":{"type":"object","required":["record_id"],"properties":{"record_id":{"type":"string"}}}},
    {"capability_id":"crm.list_records","summary":"List CRM records","description_short":"List records","domain":"crm","effect_type":"list_records","input_schema":{"type":"object","required":[],"properties":{}}},
    {"capability_id":"crm.search_contacts","summary":"Search contacts by name or account","description_short":"Search contacts","domain":"crm","effect_type":"search_contacts","input_schema":{"type":"object","required":["query"],"properties":{"query":{"type":"string"}}}},
    {"capability_id":"crm.get_contact","summary":"Get a contact by ID","description_short":"Get contact","domain":"crm","effect_type":"read_record","input_schema":{"type":"object","required":["record_id"],"properties":{"record_id":{"type":"string"}}}},
    {"capability_id":"crm.update_contact","summary":"Update a contact record","description_short":"Update contact","domain":"crm","effect_type":"update_record","input_schema":{"type":"object","required":["record_id","fields"],"properties":{"record_id":{"type":"string"},"fields":{"type":"object"},"expected_version":{"type":"string"}}}},
    # Calendar capabilities (aliased: cal.* = calendar.*)
    {"capability_id":"cal.create_event","summary":"Create a calendar event","description_short":"Create event","domain":"cal","effect_type":"create_event","input_schema":{"type":"object","required":["title","start_time","end_time"],"properties":{"title":{"type":"string"},"start_time":{"type":"string"},"end_time":{"type":"string"},"attendees":{"type":"array","items":{"type":"string"}},"event_id":{"type":"string"}}}},
    {"capability_id":"calendar.create_event","summary":"Create a calendar event","description_short":"Create event","domain":"cal","effect_type":"create_event","input_schema":{"type":"object","required":["title","start_time","end_time"],"properties":{"title":{"type":"string"},"start_time":{"type":"string"},"end_time":{"type":"string"},"attendees":{"type":"array","items":{"type":"string"}},"event_id":{"type":"string"}}}},
    {"capability_id":"cal.update_event","summary":"Update a calendar event","description_short":"Update event","domain":"cal","effect_type":"update_event","input_schema":{"type":"object","required":["event_id","fields"],"properties":{"event_id":{"type":"string"},"fields":{"type":"object"}}}},
    {"capability_id":"calendar.update_event","summary":"Update a calendar event","description_short":"Update event","domain":"cal","effect_type":"update_event","input_schema":{"type":"object","required":["event_id","fields"],"properties":{"event_id":{"type":"string"},"fields":{"type":"object"}}}},
    {"capability_id":"cal.cancel_event","summary":"Cancel a calendar event","description_short":"Cancel event","domain":"cal","effect_type":"cancel_event","input_schema":{"type":"object","required":["event_id"],"properties":{"event_id":{"type":"string"}}}},
    {"capability_id":"calendar.cancel_event","summary":"Cancel a calendar event","description_short":"Cancel event","domain":"cal","effect_type":"cancel_event","input_schema":{"type":"object","required":["event_id"],"properties":{"event_id":{"type":"string"}}}},
    {"capability_id":"cal.list_events","summary":"List calendar events","description_short":"List events","domain":"cal","effect_type":"list_events","input_schema":{"type":"object","required":[],"properties":{}}},
    {"capability_id":"calendar.list_events","summary":"List calendar events","description_short":"List events","domain":"cal","effect_type":"list_events","input_schema":{"type":"object","required":[],"properties":{}}},
    {"capability_id":"cal.get_event","summary":"Get a calendar event by ID","description_short":"Get event","domain":"cal","effect_type":"get_event","input_schema":{"type":"object","required":["event_id"],"properties":{"event_id":{"type":"string"}}}},
    {"capability_id":"calendar.get_event","summary":"Get a calendar event by ID","description_short":"Get event","domain":"cal","effect_type":"get_event","input_schema":{"type":"object","required":["event_id"],"properties":{"event_id":{"type":"string"}}}},
    # Messaging capabilities (aliased: msg.* = messaging.*)
    {"capability_id":"msg.send_message","summary":"Send a message to a target","description_short":"Send message","domain":"msg","effect_type":"send_message","input_schema":{"type":"object","required":["target","body"],"properties":{"target":{"type":"string"},"body":{"type":"string"},"message_id":{"type":"string"}}}},
    {"capability_id":"messaging.send_message","summary":"Send a message to a target","description_short":"Send message","domain":"msg","effect_type":"send_message","input_schema":{"type":"object","required":["target","body"],"properties":{"target":{"type":"string"},"body":{"type":"string"},"message_id":{"type":"string"}}}},
    {"capability_id":"msg.send_broadcast","summary":"Send a broadcast message","description_short":"Broadcast message","domain":"msg","effect_type":"send_broadcast","input_schema":{"type":"object","required":["targets","body"],"properties":{"targets":{"type":"array","items":{"type":"string"}},"body":{"type":"string"}}}},
    {"capability_id":"msg.schedule_message","summary":"Schedule a message for later delivery","description_short":"Schedule message","domain":"msg","effect_type":"schedule_message","input_schema":{"type":"object","required":["target","body","send_at"],"properties":{"target":{"type":"string"},"body":{"type":"string"},"send_at":{"type":"string"}}}},
    # Ticketing capabilities
    {"capability_id":"ticketing.create_ticket","summary":"Create a new support ticket","description_short":"Create ticket","domain":"ticketing","effect_type":"create_ticket","input_schema":{"type":"object","required":["title","priority"],"properties":{"title":{"type":"string"},"priority":{"type":"string"},"assignee":{"type":"string"}}}},
    {"capability_id":"ticketing.update_ticket","summary":"Update a support ticket","description_short":"Update ticket","domain":"ticketing","effect_type":"update_ticket","input_schema":{"type":"object","required":["ticket_id","fields"],"properties":{"ticket_id":{"type":"string"},"fields":{"type":"object"}}}},
    {"capability_id":"ticketing.close_ticket","summary":"Close a support ticket","description_short":"Close ticket","domain":"ticketing","effect_type":"close_ticket","input_schema":{"type":"object","required":["ticket_id"],"properties":{"ticket_id":{"type":"string"},"resolution":{"type":"string"}}}},
    # Reporting capabilities
    {"capability_id":"report.generate","summary":"Generate a report from data","description_short":"Generate report","domain":"report","effect_type":"generate_report","input_schema":{"type":"object","required":["report_type"],"properties":{"report_type":{"type":"string"},"filters":{"type":"object"}}}},
    {"capability_id":"report.export","summary":"Export a report to a file format","description_short":"Export report","domain":"report","effect_type":"export_report","input_schema":{"type":"object","required":["report_id","format"],"properties":{"report_id":{"type":"string"},"format":{"type":"string"}}}},
    {"capability_id":"report.schedule","summary":"Schedule recurring report generation","description_short":"Schedule report","domain":"report","effect_type":"schedule_report","input_schema":{"type":"object","required":["report_type","cron"],"properties":{"report_type":{"type":"string"},"cron":{"type":"string"},"recipients":{"type":"array","items":{"type":"string"}}}}},
    # Job capabilities
    {"capability_id":"job.start","summary":"Start a new multi-stage job","description_short":"Start job","domain":"job","effect_type":"start_job","input_schema":{"type":"object","required":["stages"],"properties":{"job_id":{"type":"string"},"stages":{"type":"array","items":{"type":"object","required":["name"],"properties":{"name":{"type":"string"}}}}}}},
    {"capability_id":"job.check_status","summary":"Check the status of a running job","description_short":"Check job","domain":"job","effect_type":"check_job","input_schema":{"type":"object","required":["job_id"],"properties":{"job_id":{"type":"string"}}}},
    {"capability_id":"job.advance","summary":"Advance a job to the next stage","description_short":"Advance job","domain":"job","effect_type":"advance_job","input_schema":{"type":"object","required":["job_id"],"properties":{"job_id":{"type":"string"},"steps":{"type":"integer"}}}},
    {"capability_id":"job.cancel","summary":"Cancel a running job","description_short":"Cancel job","domain":"job","effect_type":"cancel_job","input_schema":{"type":"object","required":["job_id"],"properties":{"job_id":{"type":"string"}}}},
    {"capability_id":"job.submit_partition","summary":"Submit a partition for processing","description_short":"Submit partition","domain":"job","effect_type":"submit_partition","input_schema":{"type":"object","required":["partition_id","dataset"],"properties":{"partition_id":{"type":"string"},"dataset":{"type":"string"}}}},
    # Catalog capabilities
    {"capability_id":"catalog.get_all","summary":"Retrieve the full capability catalog","description_short":"Get catalog","domain":"catalog","effect_type":"get_catalog","input_schema":{"type":"object","required":[],"properties":{}}},
    {"capability_id":"catalog.search","summary":"Search capabilities by keyword","description_short":"Search catalog","domain":"catalog","effect_type":"search_catalog","input_schema":{"type":"object","required":["query"],"properties":{"query":{"type":"string"}}}},
    # Publishing capabilities
    {"capability_id":"pub.publish_article","summary":"Publish an article","description_short":"Publish article","domain":"pub","effect_type":"publish_article","input_schema":{"type":"object","required":["title","content"],"properties":{"title":{"type":"string"},"content":{"type":"string"}}}},
    {"capability_id":"pub.notify_subscribers","summary":"Notify subscribers of new content","description_short":"Notify subscribers","domain":"pub","effect_type":"notify_subscribers","input_schema":{"type":"object","required":["article_id"],"properties":{"article_id":{"type":"string"},"channels":{"type":"array","items":{"type":"string"}}}}},
]
CAPS_BY_ID: dict[str, dict[str, Any]] = {c["capability_id"]: c for c in CAPS}
def cap_to_effect(capability_id: str, params: dict) -> dict[str, Any]:
    cap = CAPS_BY_ID.get(capability_id)
    if cap is None: return {"type":"unknown","error":f"Unknown capability: {capability_id}"}
    effect: dict[str, Any] = {"type": cap["effect_type"]}
    effect.update(params)
    return effect

def cap_to_effect_world(capability_id: str, params: dict, world: Any = None) -> dict[str, Any]:
    """Build an effect, falling back to world-defined catalogs.

    Some worlds (e.g. large_catalog) expose their own capability catalog that
    is not part of the static CAPS table.  For those, the world itself
    resolves the capability via its ``select_capability`` effect.
    """
    effect = cap_to_effect(capability_id, params)
    if "error" not in effect or world is None:
        return effect
    state = world.get_state() if hasattr(world, "get_state") else {}
    catalog = state.get("catalog", [])
    for entry in catalog:
        if entry.get("capability_id") == capability_id:
            return {"type": "select_capability", "capability_id": capability_id,
                    "args": params}
    return effect

_VERSION_KEYS = ("version", "current_version", "error_code", "previous_version")

def false_response_fault(context: dict | None) -> str | None:
    """Return 'false_success' / 'false_failure' / 'partial_success' if the
    context carries the fault.

    False-outcome faults simulate a lying response channel: the interface
    reports a terminal status that does not match the backend effect.
    """
    fault = (context or {}).get("fault")
    if fault is None:
        return None
    ft = getattr(fault, "fault_type", None)
    fv = ft.value if hasattr(ft, "value") else str(ft) if ft is not None else str(fault)
    if fv in ("false_success", "FALSE_SUCCESS"):
        return "false_success"
    if fv in ("false_failure", "FALSE_FAILURE"):
        return "false_failure"
    if fv in ("partial_success", "PARTIAL_SUCCESS"):
        return "partial_success"
    return None


def truncate_partial_effect(effect: dict) -> dict:
    """PARTIAL_SUCCESS fault: the backend applies only part of the effect.

    Every list-valued sub-effect (attendees, targets, recipients, ...) is
    truncated to its first half (min 1 element), deterministically.  A
    response channel under partial_success then reports full success.
    """
    for key, val in effect.items():
        if isinstance(val, list) and len(val) > 1:
            effect[key] = val[: max(1, len(val) // 2)]
    return effect

def strip_version_metadata(payload: dict) -> dict:
    """Remove version/error metadata from a payload, recursively.

    Legacy interfaces expose plain data only: no optimistic-concurrency
    versions, no structured error codes.
    """
    for key in list(payload.keys()):
        if key in _VERSION_KEYS:
            del payload[key]
        elif isinstance(payload[key], dict):
            strip_version_metadata(payload[key])
    return payload
