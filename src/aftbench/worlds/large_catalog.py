"""Large Catalog world: tool discovery from catalogs of varying sizes."""
from __future__ import annotations
import copy, hashlib, random
from typing import Any
from .base import World

DOMAINS = ["CRM","ticketing","storage","CI","reports","messaging","scheduling","publication"]
_TEMPLATES = {
    "CRM": [("create_contact","Create a new contact record",{"name":"string","email":"string"}),
            ("update_contact","Update fields on an existing contact",{"contact_id":"string","fields":"object"}),
            ("delete_contact","Permanently remove a contact record",{"contact_id":"string"}),
            ("search_contacts","Search contacts by name or email",{"query":"string","account_id":"string?"}),
            ("get_contact","Retrieve full details of a single contact",{"contact_id":"string"}),
            ("list_accounts","List all accounts with filtering",{"industry":"string?","region":"string?"}),
            ("create_account","Create a new account",{"name":"string","industry":"string"}),
            ("merge_contacts","Merge duplicate contact records",{"primary_id":"string","secondary_id":"string"}),
            ("assign_owner","Assign a record to a representative",{"record_id":"string","owner_id":"string"}),
            ("export_contacts","Export contacts to CSV",{"account_id":"string?","format":"string"})],
    "ticketing": [("create_ticket","Create a new support ticket",{"title":"string","description":"string"}),
                  ("update_ticket","Update ticket fields or status",{"ticket_id":"string","fields":"object"}),
                  ("close_ticket","Close a ticket with resolution",{"ticket_id":"string","resolution":"string"}),
                  ("assign_ticket","Assign ticket to an agent",{"ticket_id":"string","agent_id":"string"}),
                  ("escalate_ticket","Escalate to higher tier",{"ticket_id":"string","reason":"string"}),
                  ("search_tickets","Search tickets by keyword",{"query":"string","status":"string?"}),
                  ("add_comment","Add a comment to a ticket",{"ticket_id":"string","body":"string"}),
                  ("link_tickets","Link related tickets",{"source_id":"string","target_id":"string"}),
                  ("get_ticket_history","Retrieve ticket change history",{"ticket_id":"string"}),
                  ("bulk_update_tickets","Update multiple tickets",{"ticket_ids":"list","fields":"object"})],
    "storage": [("upload_file","Upload a file to cloud storage",{"path":"string","content":"bytes"}),
                ("download_file","Download a file from storage",{"path":"string"}),
                ("delete_file","Delete a file from storage",{"path":"string"}),
                ("list_files","List files in a directory",{"prefix":"string?","recursive":"bool?"}),
                ("copy_file","Copy a file to new location",{"source":"string","destination":"string"}),
                ("move_file","Move a file to new location",{"source":"string","destination":"string"}),
                ("get_file_metadata","Get metadata for a file",{"path":"string"}),
                ("set_permissions","Set access permissions",{"path":"string","permissions":"object"}),
                ("create_folder","Create a new folder",{"path":"string"}),
                ("generate_presigned_url","Generate temporary download URL",{"path":"string","expires_in":"int?"})],
    "CI": [("trigger_pipeline","Trigger a CI/CD pipeline",{"pipeline_id":"string","branch":"string?"}),
           ("get_pipeline_status","Get pipeline status",{"run_id":"string"}),
           ("cancel_pipeline","Cancel a running pipeline",{"run_id":"string"}),
           ("get_build_logs","Retrieve build logs",{"run_id":"string","step":"string?"}),
           ("list_pipelines","List available pipelines",{"project":"string?","status":"string?"}),
           ("retry_pipeline","Retry a failed pipeline",{"run_id":"string"}),
           ("deploy_artifact","Deploy artifact to environment",{"artifact_id":"string","environment":"string"}),
           ("rollback_deployment","Roll back deployment",{"environment":"string","version":"string?"}),
           ("get_test_results","Get test results",{"run_id":"string","suite":"string?"}),
           ("approve_deployment","Approve deployment gate",{"run_id":"string","gate":"string"})],
    "reports": [("generate_report","Generate report from template",{"template_id":"string","format":"string?"}),
                ("get_report","Retrieve a generated report",{"report_id":"string"}),
                ("list_reports","List available reports",{"category":"string?","owner":"string?"}),
                ("schedule_report","Schedule recurring report",{"template_id":"string","cron":"string"}),
                ("cancel_scheduled_report","Cancel scheduled report",{"schedule_id":"string"}),
                ("export_report","Export report in format",{"report_id":"string","format":"string"}),
                ("share_report","Share report with users",{"report_id":"string","recipients":"list"}),
                ("delete_report","Delete a report",{"report_id":"string"}),
                ("get_report_metadata","Get report metadata",{"report_id":"string"}),
                ("refresh_report","Refresh report with latest data",{"report_id":"string"})],
    "messaging": [("send_message","Send message to user or channel",{"recipient":"string","body":"string"}),
                  ("create_channel","Create messaging channel",{"name":"string","members":"list?"}),
                  ("list_channels","List messaging channels",{"type":"string?"}),
                  ("send_broadcast","Broadcast to channel members",{"channel_id":"string","body":"string"}),
                  ("get_message_history","Retrieve message history",{"channel_id":"string","limit":"int?"}),
                  ("pin_message","Pin a message",{"channel_id":"string","message_id":"string"}),
                  ("delete_message","Delete a message",{"channel_id":"string","message_id":"string"}),
                  ("add_reaction","React to a message",{"channel_id":"string","message_id":"string","emoji":"string"}),
                  ("create_thread","Start thread on message",{"channel_id":"string","message_id":"string","body":"string"}),
                  ("mute_channel","Mute channel notifications",{"channel_id":"string","duration":"string?"})],
    "scheduling": [("create_event","Create calendar event",{"title":"string","start":"datetime","end":"datetime"}),
                   ("update_event","Update calendar event",{"event_id":"string","fields":"object"}),
                   ("cancel_event","Cancel calendar event",{"event_id":"string","reason":"string?"}),
                   ("list_events","List events in time range",{"start":"datetime","end":"datetime"}),
                   ("find_availability","Find available time slots",{"attendees":"list","duration":"string"}),
                   ("send_invitation","Send meeting invitation",{"event_id":"string","recipients":"list"}),
                   ("rsvp","Respond to invitation",{"event_id":"string","response":"string"}),
                   ("create_recurring_event","Create recurring event",{"title":"string","recurrence":"string"}),
                   ("get_event_details","Get event details",{"event_id":"string"}),
                   ("move_event","Reschedule event",{"event_id":"string","new_start":"datetime"})],
    "publication": [("publish_article","Publish article to website",{"title":"string","content":"string"}),
                    ("update_article","Update published article",{"article_id":"string","fields":"object"}),
                    ("unpublish_article","Remove article from public view",{"article_id":"string"}),
                    ("list_articles","List published articles",{"category":"string?","status":"string?"}),
                    ("get_article","Get article content",{"article_id":"string"}),
                    ("schedule_publication","Schedule future publication",{"article_id":"string","publish_at":"datetime"}),
                    ("create_draft","Create draft article",{"title":"string","content":"string"}),
                    ("submit_for_review","Submit draft for review",{"article_id":"string","reviewer":"string"}),
                    ("approve_article","Approve for publication",{"article_id":"string"}),
                    ("delete_article","Permanently delete article",{"article_id":"string"})],
}
_NEAR_MISS = {
    "CRM": [("predict_revenue","Predict revenue using ML",{"account_id":"string"})],
    "ticketing": [("auto_triage","Auto-triage tickets with AI",{"ticket_ids":"list"})],
    "storage": [("scan_viruses","Scan files for viruses",{"path":"string"})],
    "CI": [("estimate_build_time","Estimate build duration",{"pipeline_id":"string"})],
    "reports": [("translate_report","Translate report",{"report_id":"string","lang":"string"})],
    "messaging": [("translate_message","Translate message",{"message_id":"string","lang":"string"})],
    "scheduling": [("book_room","Book conference room",{"room_id":"string","start":"datetime"})],
    "publication": [("translate_article","Translate article",{"article_id":"string","lang":"string"})],
}

def _gen(size, seed):
    rng = random.Random(seed); entries = []
    for dom, tmpls in _TEMPLATES.items():
        for n,d,inp in tmpls:
            entries.append({"capability_id":f"{dom}.{n}","name":n,"description":d,"input_schema":inp,"domain":dom})
    for dom, extras in _NEAR_MISS.items():
        for n,d,inp in extras:
            entries.append({"capability_id":f"{dom}.{n}","name":n,"description":d,"input_schema":inp,"domain":dom})
    while len(entries) < size:
        dom = rng.choice(DOMAINS); base = rng.choice(_TEMPLATES[dom])
        suf = rng.choice(["v2","batch","async","bulk","extended","advanced","lite","premium","internal"])
        cap_id = f"{dom}.{base[0]}_{suf}"
        if any(e["capability_id"]==cap_id for e in entries): continue
        entries.append({"capability_id":cap_id,"name":f"{base[0]}_{suf}","description":f"{base[1]} ({suf} variant)","input_schema":base[2],"domain":dom})
    rng.shuffle(entries); entries = entries[:size]
    for i,e in enumerate(entries): e["catalog_index"] = i
    return entries

class LargeCatalogWorld(World):
    SUPPORTED_SIZES = (10, 50, 200, 1000)
    def __init__(self, catalog_size: int = 50) -> None:
        super().__init__()
        if catalog_size not in self.SUPPORTED_SIZES: raise ValueError(f"catalog_size must be one of {self.SUPPORTED_SIZES}")
        self._catalog_size = catalog_size; self._catalog = []; self._catalog_version = ""
        self._target_capability_id = None
    def reset(self, seed: int = 0) -> None:
        self._catalog = _gen(self._catalog_size, seed)
        raw = str([(e["capability_id"],e["description"]) for e in self._catalog])
        self._catalog_version = hashlib.md5(raw.encode()).hexdigest()[:10]
        # Select a target capability based on seed
        rng = random.Random(seed)
        if self._catalog:
            self._target_capability_id = rng.choice(self._catalog)["capability_id"]
        self._initial_state = self.get_state()
    def get_state(self) -> dict:
        # Return catalog_sizes for all supported sizes
        catalog_sizes = {}
        for size in self.SUPPORTED_SIZES:
            catalog_sizes[size] = size
        return {
            "catalog":copy.deepcopy(self._catalog),
            "catalog_size":len(self._catalog),
            "catalog_version":self._catalog_version,
            "catalog_sizes": catalog_sizes,
            "target_capability_id": self._target_capability_id,
        }
    def verify_postconditions(self, task, state) -> bool:
        post = task.get("postconditions", []); catalog = state.get("catalog", [])
        # Check for selected_capability_id postcondition
        selected = task.get("selected_capability_id")
        target = state.get("target_capability_id")
        if selected and target:
            if selected != target:
                return False
        for cond in post:
            ct = cond.get("type")
            if ct == "capability_discovered":
                if not any(e["capability_id"]==cond["capability_id"] for e in catalog): return False
            elif ct == "correct_domain_selected":
                if cond.get("domain") not in [e.get("domain") for e in catalog]: return False
            elif ct == "distractor_rejected":
                if any(e["capability_id"]==cond["capability_id"] for e in catalog): return False
        return True
    def verify_safety_predicates(self, task, state) -> bool: return True
    def apply_effect(self, effect) -> dict:
        et = effect.get("type")
        if et == "get_catalog":
            size = effect.get("size", len(self._catalog))
            off=effect.get("offset",0); lim=min(size, len(self._catalog)); page=self._catalog[off:off+lim]
            return {"success":True,"catalog":copy.deepcopy(page),"entries":copy.deepcopy(page),"total":len(self._catalog),"offset":off,"returned":len(page),"catalog_version":self._catalog_version,"effect_class":"read_only"}
        elif et == "search_catalog":
            q=effect.get("query","").lower(); df=effect.get("domain"); lim=effect.get("limit",20); results=[]
            for e in self._catalog:
                t=f"{e['name']} {e['description']}".lower()
                if q in t or any(w in t for w in q.split()):
                    if df and e["domain"]!=df: continue
                    results.append(copy.deepcopy(e))
            return {"success":True,"results":results[:lim],"total_matches":len(results),"effect_class":"read_only"}
        elif et == "get_capability_details" or et == "get_schema":
            cid=effect.get("capability_id")
            for e in self._catalog:
                if e["capability_id"]==cid: return {"success":True,"capability":copy.deepcopy(e),"schema":copy.deepcopy(e.get("input_schema",{})),"effect_class":"read_only"}
            return {"success":False,"error":f"Capability {cid} not found","error_code":"NOT_FOUND"}
        elif et == "select_capability":
            cid=effect.get("capability_id")
            # Support case-insensitive matching
            cid_lower = cid.lower()
            for e in self._catalog:
                if e["capability_id"].lower()==cid_lower: return {"success":True,"selected":e["capability_id"],"capability":copy.deepcopy(e),"effect_class":"read_only"}
            return {"success":False,"error":f"Capability {cid} not found","error_code":"NOT_FOUND"}
        elif et == "get_relevance":
            q=effect.get("query",""); tk=effect.get("top_k",5); or_ = self.get_relevance_oracle(q,tk)
            return {"success":True,"results":copy.deepcopy(or_),"query":q,"effect_class":"read_only"}
        elif et == "list_domains":
            dc={}
            for e in self._catalog: dc[e["domain"]]=dc.get(e["domain"],0)+1
            return {"success":True,"domains":dc,"effect_class":"read_only"}
        elif et == "get_catalog_metadata":
            return {"success":True,"catalog_version":self._catalog_version,"catalog_size":len(self._catalog),"domains":list(set(e["domain"] for e in self._catalog)),"effect_class":"read_only"}
        return {"success":False,"error":f"Unknown effect: {et}","error_code":"UNKNOWN_EFFECT"}
    def get_object_version(self, obj_id): return "v1"
    def get_relevance_oracle(self, query, top_k=5):
        ql=query.lower(); qw=set(ql.split()); scored=[]
        for e in self._catalog:
            t=f"{e['name']} {e['description']} {e['domain']}".lower(); tw=set(t.split())
            ov=len(qw&tw); db=1.0 if any(d.lower() in ql for d in [e["domain"]]) else 0.0; sc=ov+db
            if sc>0: scored.append((sc,e))
        scored.sort(key=lambda x:-x[0]); return [e for _,e in scored[:top_k]]
    def get_catalog(self, size=None):
        if size is None:
            return copy.deepcopy(self._catalog)
        return copy.deepcopy(self._catalog[:size])
