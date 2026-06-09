from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AuthorityStage, PromotionRecord, ResourceArena, StagedActionQueueItem, TrustZone
from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrustStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.trust_zones_path = self.root / "trust_zones.json"
        self.resource_arenas_path = self.root / "resource_arenas.json"
        self.authority_stages_path = self.root / "authority_stages.json"
        self.stage_queue_path = self.root / "stage_queue.json"
        self.promotion_records_path = self.root / "promotion_records.json"
        self._log_paths = {
            self.trust_zones_path: self.root / "trust_zones_log.jsonl",
            self.resource_arenas_path: self.root / "resource_arenas_log.jsonl",
            self.authority_stages_path: self.root / "authority_stages_log.jsonl",
            self.stage_queue_path: self.root / "stage_queue_log.jsonl",
            self.promotion_records_path: self.root / "promotion_records_log.jsonl",
        }

    def _load_records_from_log(self, path: Path) -> list[dict[str, Any]]:
        log_path = self._log_paths[path]
        if not log_path.exists():
            return []
        latest: list[dict[str, Any]] = []
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _load_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return self._load_records_from_log(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._load_records_from_log(path)
        if not isinstance(payload, list):
            return self._load_records_from_log(path)
        return [dict(item) for item in payload if isinstance(item, dict)]

    def _save_records(self, path: Path, records: list[dict]) -> None:
        atomic_write_json(path, records)
        append_jsonl(
            self._log_paths[path],
            {
                "saved_at": _now_iso(),
                "records": records,
            },
        )

    def list_trust_zones(self) -> list[dict]:
        return self._load_records(self.trust_zones_path)

    def save_trust_zones(self, records: list[dict]) -> None:
        self._save_records(self.trust_zones_path, records)

    def list_resource_arenas(self) -> list[dict]:
        return self._load_records(self.resource_arenas_path)

    def save_resource_arenas(self, records: list[dict]) -> None:
        self._save_records(self.resource_arenas_path, records)

    def list_authority_stages(self) -> list[dict]:
        return self._load_records(self.authority_stages_path)

    def save_authority_stages(self, records: list[dict]) -> None:
        self._save_records(self.authority_stages_path, records)

    def list_stage_queue(self) -> list[dict]:
        return self._load_records(self.stage_queue_path)

    def save_stage_queue(self, records: list[dict]) -> None:
        self._save_records(self.stage_queue_path, records)

    def list_promotion_records(self) -> list[dict]:
        return self._load_records(self.promotion_records_path)

    def save_promotion_records(self, records: list[dict]) -> None:
        self._save_records(self.promotion_records_path, records)


class TrustSupport:
    def __init__(self, store: TrustStore, default_owner_principal: str = "") -> None:
        self.store = store
        self.default_owner_principal = str(default_owner_principal or "").strip().lower() or "primary"
        self.bootstrap_defaults()

    def bootstrap_defaults(self) -> None:
        default_owner_principal = self.default_owner_principal
        if not self.store.list_authority_stages():
            stages = [
                AuthorityStage(
                    stage_id="observe",
                    name="Observe",
                    description="Read, analyze, and recommend without mutating external state.",
                    sequence=0,
                    allowed_action_types=["observe", "classify", "infer", "recommend"],
                    approval_requirements={"pre_action": "none", "boundary_crossing": "escalate"},
                    reporting_requirements={"summary_level": "minimal", "cadence": "on_request", "must_capture_outcomes": False},
                    promotion_criteria={"minimum_success_rate": 0.9, "minimum_review_count": 5, "maximum_boundary_violations": 0},
                    demotion_triggers=["boundary_violation", "false_confidence", "principal_override"],
                    status="active",
                ),
                AuthorityStage(
                    stage_id="draft",
                    name="Draft Only",
                    description="Prepare artifacts without finalizing or sending them.",
                    sequence=1,
                    allowed_action_types=["observe", "classify", "draft"],
                    approval_requirements={"pre_action": "draft_only", "boundary_crossing": "escalate"},
                    reporting_requirements={"summary_level": "standard", "cadence": "per_action", "must_capture_outcomes": True},
                    promotion_criteria={"minimum_success_rate": 0.95, "minimum_review_count": 25, "maximum_boundary_violations": 0},
                    demotion_triggers=["hidden_action", "error_rate_breach", "principal_override"],
                    status="active",
                ),
                AuthorityStage(
                    stage_id="stage_alert",
                    name="Stage and Alert",
                    description="Stage the action and notify the principal for review.",
                    sequence=2,
                    allowed_action_types=["observe", "classify", "draft", "stage", "alert"],
                    approval_requirements={"pre_action": "stage_and_alert", "boundary_crossing": "escalate"},
                    reporting_requirements={"summary_level": "standard", "cadence": "per_action", "must_capture_outcomes": True},
                    promotion_criteria={"minimum_success_rate": 0.97, "minimum_review_count": 40, "maximum_boundary_violations": 0},
                    demotion_triggers=["hidden_action", "error_rate_breach", "reporting_failure", "principal_override"],
                    status="active",
                ),
                AuthorityStage(
                    stage_id="sandbox_live",
                    name="Sandbox Live",
                    description="Execute directly inside a ring-fenced environment.",
                    sequence=3,
                    allowed_action_types=["observe", "infer", "simulate", "execute_in_zone"],
                    approval_requirements={"pre_action": "none", "boundary_crossing": "require_human_approval"},
                    reporting_requirements={"summary_level": "detailed", "cadence": "per_action", "must_capture_outcomes": True},
                    promotion_criteria={"minimum_success_rate": 0.98, "minimum_review_count": 50, "maximum_boundary_violations": 0},
                    demotion_triggers=["boundary_violation", "false_confidence", "error_rate_breach", "principal_override"],
                    status="active",
                ),
                AuthorityStage(
                    stage_id="mature_live",
                    name="Mature Delegated Live",
                    description="Operate with broader standing authority under explicit family policy.",
                    sequence=4,
                    allowed_action_types=["observe", "infer", "draft", "stage", "simulate", "execute_in_zone", "spawn_agent_in_zone"],
                    approval_requirements={"pre_action": "none", "boundary_crossing": "require_human_approval"},
                    reporting_requirements={"summary_level": "standard", "cadence": "daily", "must_capture_outcomes": True},
                    promotion_criteria={"minimum_success_rate": 0.99, "minimum_review_count": 100, "maximum_boundary_violations": 0},
                    demotion_triggers=["boundary_violation", "hidden_action", "error_rate_breach", "principal_override"],
                    status="active",
                ),
                AuthorityStage(
                    stage_id="suspended",
                    name="Suspended",
                    description="No autonomous actions allowed until re-enabled.",
                    sequence=99,
                    allowed_action_types=["observe"],
                    approval_requirements={"pre_action": "required", "boundary_crossing": "deny"},
                    reporting_requirements={"summary_level": "minimal", "cadence": "on_request", "must_capture_outcomes": False},
                    promotion_criteria={"minimum_success_rate": 1.0, "minimum_review_count": 0, "maximum_boundary_violations": 0},
                    demotion_triggers=["principal_override"],
                    status="active",
                ),
            ]
            self.store.save_authority_stages([asdict(item) for item in stages])
        if not self.store.list_trust_zones():
            now = _now_iso()
            zone = TrustZone(
                zone_id="shared-email.stage",
                name="Shared Email Draft Stage",
                description="Shared email draft-and-alert flow for household communication.",
                zone_type="draft_stage",
                authority_stage="draft",
                resource_scope={
                    "systems": ["gmail"],
                    "data_classes": ["shared_email", "relationship_memory"],
                    "account_ids": ["gmail_primary"],
                    "connector_ids": [],
                },
                allowed_actions=["observe", "classify", "draft", "stage", "alert", "store_memory"],
                approval_mode="stage_and_alert",
                audit_mode="standard",
                reporting_cadence="event_driven",
                promotion_rules={
                    "eligible_next_stages": ["stage_alert"],
                    "minimum_success_rate": 0.95,
                    "minimum_review_count": 25,
                    "required_signals": ["review_approved_rate", "low_edit_distance"],
                },
                demotion_rules={
                    "triggers": ["hidden_action", "error_rate_breach", "manual_override"],
                    "fallback_stage": "draft",
                },
                status="active",
                created_at=now,
                updated_at=now,
            )
            self.store.save_trust_zones([asdict(zone)])
        zone_records = self.store.list_trust_zones()
        zone_ids = {str(item.get("zone_id", "")).strip().lower() for item in zone_records}
        if "household_home" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_home",
                        name="Household Home Control",
                        description="Governed home-control lane for household service calls.",
                        zone_type="home_control",
                        authority_stage="draft",
                        resource_scope={
                            "systems": ["home_assistant"],
                            "data_classes": ["household_state", "device_control"],
                            "account_ids": [],
                            "connector_ids": ["home_assistant"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "home_control"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["stage_alert", "sandbox_live"],
                            "minimum_success_rate": 0.98,
                            "minimum_review_count": 20,
                            "required_signals": ["home_command_success_rate", "low_override_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "safety_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_schedule" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_schedule",
                        name="Household Schedule Routing",
                        description="Governed schedule-routing lane for calendar travel handoffs.",
                        zone_type="schedule_control",
                        authority_stage="sandbox_live",
                        resource_scope={
                            "systems": ["calendar", "maps"],
                            "data_classes": ["calendar_events", "travel_routes"],
                            "account_ids": [],
                            "connector_ids": ["eventkit", "maps"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "calendar_route"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["mature_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 12,
                            "required_signals": ["route_handoff_success_rate", "low_boundary_override_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "travel_boundary_violation", "principal_override"],
                            "fallback_stage": "stage_alert",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_safety" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_safety",
                        name="Household Safety Response",
                        description="Governed response lane for sound-triggered safety resolutions.",
                        zone_type="safety_response",
                        authority_stage="stage_alert",
                        resource_scope={
                            "systems": ["sound_alerts", "notifications"],
                            "data_classes": ["safety_signals", "resolution_history"],
                            "account_ids": [],
                            "connector_ids": ["sound_analysis"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "signal_resolution"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["sandbox_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 10,
                            "required_signals": ["sound_resolution_accuracy", "low_false_resolve_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "safety_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_perception" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_perception",
                        name="Household Perception Response",
                        description="Governed response lane for vision-triggered household scan resolutions.",
                        zone_type="perception_response",
                        authority_stage="sandbox_live",
                        resource_scope={
                            "systems": ["vision_scans", "notifications"],
                            "data_classes": ["perception_signals", "resolution_history"],
                            "account_ids": [],
                            "connector_ids": ["vision"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "signal_resolution"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["mature_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 10,
                            "required_signals": ["vision_resolution_accuracy", "low_false_resolve_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "perception_boundary_violation", "principal_override"],
                            "fallback_stage": "stage_alert",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_attention" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_attention",
                        name="Household Attention Workflow",
                        description="Governed workflow lane for mutating household notification state.",
                        zone_type="attention_workflow",
                        authority_stage="stage_alert",
                        resource_scope={
                            "systems": ["notifications"],
                            "data_classes": ["attention_objects", "notification_state"],
                            "account_ids": [],
                            "connector_ids": ["notification_center"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "notification_workflow"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["sandbox_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 10,
                            "required_signals": ["notification_action_accuracy", "low_reopen_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "attention_boundary_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_tasks" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_tasks",
                        name="Household Task Workflow",
                        description="Governed workflow lane for mutating household reminder and task state.",
                        zone_type="task_workflow",
                        authority_stage="stage_alert",
                        resource_scope={
                            "systems": ["reminders"],
                            "data_classes": ["task_objects", "reminder_state"],
                            "account_ids": [],
                            "connector_ids": ["eventkit_reminders"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "reminder_workflow"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["sandbox_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 10,
                            "required_signals": ["reminder_action_accuracy", "low_task_reopen_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "task_boundary_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_focus" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_focus",
                        name="Household Focus Workflow",
                        description="Governed workflow lane for mutating household focus posture and interruption rules.",
                        zone_type="focus_workflow",
                        authority_stage="stage_alert",
                        resource_scope={
                            "systems": ["focus_state", "notifications"],
                            "data_classes": ["focus_posture", "interruption_policy"],
                            "account_ids": [],
                            "connector_ids": ["focus_filters"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "focus_workflow"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["sandbox_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 10,
                            "required_signals": ["focus_action_accuracy", "low_interrupt_override_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "focus_boundary_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "household_huddle" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="household_huddle",
                        name="Household Huddle Workflow",
                        description="Governed workflow lane for waking agent councils and starting overnight huddle orchestration.",
                        zone_type="huddle_workflow",
                        authority_stage="stage_alert",
                        resource_scope={
                            "systems": ["huddle", "party_mode", "runtime"],
                            "data_classes": ["agent_orchestration", "party_mode_status"],
                            "account_ids": [],
                            "connector_ids": ["runtime"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "huddle_workflow"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["sandbox_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 8,
                            "required_signals": ["huddle_start_accuracy", "low_manual_abort_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "huddle_boundary_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if "publication_review" not in zone_ids:
            now = _now_iso()
            zone_records.append(
                asdict(
                    TrustZone(
                        zone_id="publication_review",
                        name="Publication Review Workflow",
                        description="Governed workflow lane for approving or sending publishing review items back for revision.",
                        zone_type="publishing_workflow",
                        authority_stage="stage_alert",
                        resource_scope={
                            "systems": ["publishing"],
                            "data_classes": ["review_objects", "publication_state"],
                            "account_ids": [],
                            "connector_ids": ["ghostwritr_publishing"],
                        },
                        allowed_actions=["observe", "classify", "draft", "stage", "alert", "publishing_review"],
                        approval_mode="stage_and_alert",
                        audit_mode="standard",
                        promotion_rules={
                            "eligible_next_stages": ["sandbox_live"],
                            "minimum_success_rate": 0.99,
                            "minimum_review_count": 8,
                            "required_signals": ["review_decision_accuracy", "low_revision_reopen_rate"],
                        },
                        demotion_rules={
                            "triggers": ["manual_override", "publication_boundary_violation", "principal_override"],
                            "fallback_stage": "draft",
                        },
                        status="active",
                        reporting_cadence="event_driven",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_trust_zones(zone_records)
        if not self.store.list_resource_arenas():
            now = _now_iso()
            arena = ResourceArena(
                arena_id="gmail.shared.drafts",
                name="Shared Gmail Draft Arena",
                description="Ring-fenced shared-email draft arena that saves to drafts and alerts the principal.",
                resource_type="email_draft_pipeline",
                linked_zone_id="shared-email.stage",
                owner_principal=default_owner_principal,
                risk_class="low",
                resource_refs={"mailbox_id": "gmail_primary", "folder_id": "drafts"},
                limits={
                    "action_budget": {"max_actions_per_day": 25, "max_drafts_per_day": 25},
                    "message_limits": {
                        "send_enabled": False,
                        "draft_folder_required": True,
                        "allowed_recipient_classes": ["known_contact", "manual_review"],
                    },
                },
                pause_conditions=["draft_save_failure", "principal_override"],
                promotion_eligibility={"enabled": True, "target_stage": "stage_alert"},
                status="active",
                created_at=now,
                updated_at=now,
            )
            self.store.save_resource_arenas([asdict(arena)])
        arena_records = self.store.list_resource_arenas()
        arena_ids = {str(item.get("arena_id", "")).strip().lower() for item in arena_records}
        if "household.home.manual" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.home.manual",
                        name="Household Home Command Arena",
                        description="Bounded arena for staged or live home-control commands.",
                        resource_type="home_control",
                        linked_zone_id="household_home",
                        owner_principal=default_owner_principal,
                        risk_class="medium",
                        resource_refs={"controller": "home_assistant"},
                        limits={
                            "action_budget": {"max_actions_per_day": 20, "max_high_risk_per_day": 4},
                            "command_limits": {"allowed_domains": ["light", "switch", "scene", "cover", "lock", "climate"]},
                        },
                        pause_conditions=["principal_override", "service_failure", "unexpected_device_response"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.schedule.routing" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.schedule.routing",
                        name="Household Schedule Routing Arena",
                        description="Bounded arena for calendar route handoffs and travel prep actions.",
                        resource_type="calendar_route",
                        linked_zone_id="household_schedule",
                        owner_principal=default_owner_principal,
                        risk_class="low",
                        resource_refs={"calendar_source": "eventkit", "maps_provider": "apple_maps"},
                        limits={
                            "action_budget": {"max_actions_per_day": 30, "max_live_route_handoffs_per_day": 20},
                            "route_limits": {"allow_external_send": False, "allowed_destinations": ["maps_preview", "device_handoff"]},
                        },
                        pause_conditions=["principal_override", "calendar_sync_failure", "route_resolution_failure"],
                        promotion_eligibility={"enabled": True, "target_stage": "mature_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.safety.signal-resolution" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.safety.signal-resolution",
                        name="Household Safety Signal Resolution Arena",
                        description="Bounded arena for resolving household safety sound alerts.",
                        resource_type="signal_resolution",
                        linked_zone_id="household_safety",
                        owner_principal=default_owner_principal,
                        risk_class="medium",
                        resource_refs={"signal_domain": "sound"},
                        limits={
                            "action_budget": {"max_actions_per_day": 25, "max_live_resolutions_per_day": 8},
                            "resolution_limits": {"allow_auto_resolution": False, "requires_reason_capture": True},
                        },
                        pause_conditions=["principal_override", "signal_resolution_failure", "unexpected_repeat_alert"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.perception.signal-resolution" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.perception.signal-resolution",
                        name="Household Perception Signal Resolution Arena",
                        description="Bounded arena for resolving household vision scans.",
                        resource_type="signal_resolution",
                        linked_zone_id="household_perception",
                        owner_principal=default_owner_principal,
                        risk_class="low",
                        resource_refs={"signal_domain": "vision"},
                        limits={
                            "action_budget": {"max_actions_per_day": 25, "max_live_resolutions_per_day": 15},
                            "resolution_limits": {"allow_auto_resolution": True, "requires_reason_capture": True},
                        },
                        pause_conditions=["principal_override", "signal_resolution_failure", "unexpected_repeat_alert"],
                        promotion_eligibility={"enabled": True, "target_stage": "mature_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.attention.workflow" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.attention.workflow",
                        name="Household Attention Workflow Arena",
                        description="Bounded arena for resolve and snooze mutations on household notifications.",
                        resource_type="notification_workflow",
                        linked_zone_id="household_attention",
                        owner_principal=default_owner_principal,
                        risk_class="low",
                        resource_refs={"notification_store": "shared_notification_center"},
                        limits={
                            "action_budget": {"max_actions_per_day": 40, "max_live_mutations_per_day": 15},
                            "workflow_limits": {"allow_delete": False, "allow_state_mutation": True},
                        },
                        pause_conditions=["principal_override", "notification_store_failure", "unexpected_reopen_rate"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.tasks.workflow" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.tasks.workflow",
                        name="Household Task Workflow Arena",
                        description="Bounded arena for complete and snooze mutations on household reminders.",
                        resource_type="reminder_workflow",
                        linked_zone_id="household_tasks",
                        owner_principal=default_owner_principal,
                        risk_class="low",
                        resource_refs={"task_store": "shared_reminder_center"},
                        limits={
                            "action_budget": {"max_actions_per_day": 50, "max_live_mutations_per_day": 20},
                            "workflow_limits": {"allow_delete": False, "allow_state_mutation": True},
                        },
                        pause_conditions=["principal_override", "task_store_failure", "unexpected_reopen_rate"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.focus.workflow" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.focus.workflow",
                        name="Household Focus Workflow Arena",
                        description="Bounded arena for applying household focus presets and interruption-policy mutations.",
                        resource_type="focus_workflow",
                        linked_zone_id="household_focus",
                        owner_principal=default_owner_principal,
                        risk_class="low",
                        resource_refs={"focus_store": "apple_focus_state"},
                        limits={
                            "action_budget": {"max_actions_per_day": 20, "max_live_mutations_per_day": 8},
                            "workflow_limits": {"allow_state_mutation": True, "allow_silent_override": False},
                        },
                        pause_conditions=["principal_override", "focus_store_failure", "unexpected_interrupt_spike"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "household.huddle.workflow" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="household.huddle.workflow",
                        name="Household Huddle Workflow Arena",
                        description="Bounded arena for starting overnight party-mode orchestration and other live huddle wake actions.",
                        resource_type="huddle_workflow",
                        linked_zone_id="household_huddle",
                        owner_principal=default_owner_principal,
                        risk_class="medium",
                        resource_refs={"controller": "party_mode"},
                        limits={
                            "action_budget": {"max_actions_per_day": 6, "max_live_starts_per_day": 2},
                            "workflow_limits": {"allow_background_start": True, "allow_silent_restart": False},
                        },
                        pause_conditions=["principal_override", "party_mode_failure", "unexpected_runtime_block"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "publication.review.workflow" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="publication.review.workflow",
                        name="Publication Review Workflow Arena",
                        description="Bounded arena for approve and revise mutations on publishing review items.",
                        resource_type="publishing_review",
                        linked_zone_id="publication_review",
                        owner_principal="chris",
                        risk_class="low",
                        resource_refs={"review_store": "ghostwritr_reviews"},
                        limits={
                            "action_budget": {"max_actions_per_day": 25, "max_live_mutations_per_day": 12},
                            "workflow_limits": {"allow_state_mutation": True, "allow_publish": False},
                        },
                        pause_conditions=["principal_override", "publishing_store_failure", "unexpected_review_reopen_rate"],
                        promotion_eligibility={"enabled": True, "target_stage": "sandbox_live"},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)
        if "system.agent-sandbox" not in arena_ids:
            now = _now_iso()
            arena_records.append(
                asdict(
                    ResourceArena(
                        arena_id="system.agent-sandbox",
                        name="Agent Self-Improvement Sandbox Arena",
                        description="Bounded arena for isolated worktree sandbox runs of self-improvement jobs.",
                        resource_type="self_improvement_sandbox",
                        linked_zone_id="system_agent",
                        owner_principal="chris",
                        risk_class="medium",
                        resource_refs={"executor": "sandbox_worktree_executor"},
                        limits={
                            "action_budget": {"max_jobs_per_day": 10, "max_concurrent_jobs": 2},
                        },
                        pause_conditions=["principal_override", "worktree_failure", "repeated_test_failure"],
                        promotion_eligibility={"enabled": False},
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
            self.store.save_resource_arenas(arena_records)

    def list_trust_zones(self) -> list[dict]:
        return self.store.list_trust_zones()

    def list_resource_arenas(self) -> list[dict]:
        return self.store.list_resource_arenas()

    def list_authority_stages(self) -> list[dict]:
        return self.store.list_authority_stages()

    def list_stage_queue(self, limit: int = 50) -> list[dict]:
        records = self.store.list_stage_queue()
        return list(reversed(records[-limit:]))

    def list_promotion_records(self, limit: int = 50) -> list[dict]:
        records = self.store.list_promotion_records()
        return list(reversed(records[-limit:]))

    def get_trust_zone(self, zone_id: str) -> dict | None:
        zone_key = zone_id.strip().lower()
        for zone in self.store.list_trust_zones():
            if str(zone.get("zone_id", "")).strip().lower() == zone_key:
                return dict(zone)
        return None

    def get_resource_arena(self, arena_id: str) -> dict | None:
        arena_key = arena_id.strip().lower()
        for arena in self.store.list_resource_arenas():
            if str(arena.get("arena_id", "")).strip().lower() == arena_key:
                return dict(arena)
        return None

    def get_authority_stage(self, stage_id: str) -> dict | None:
        stage_key = stage_id.strip().lower()
        for stage in self.store.list_authority_stages():
            if str(stage.get("stage_id", "")).strip().lower() == stage_key:
                return dict(stage)
        return None

    def upsert_trust_zone(self, zone: TrustZone) -> dict:
        records = self.store.list_trust_zones()
        payload = asdict(zone)
        replaced = False
        for index, item in enumerate(records):
            if str(item.get("zone_id", "")).strip().lower() == zone.zone_id.strip().lower():
                records[index] = payload
                replaced = True
                break
        if not replaced:
            records.append(payload)
        self.store.save_trust_zones(records)
        return payload

    def upsert_resource_arena(self, arena: ResourceArena) -> dict:
        records = self.store.list_resource_arenas()
        payload = asdict(arena)
        replaced = False
        for index, item in enumerate(records):
            if str(item.get("arena_id", "")).strip().lower() == arena.arena_id.strip().lower():
                records[index] = payload
                replaced = True
                break
        if not replaced:
            records.append(payload)
        self.store.save_resource_arenas(records)
        return payload

    def enqueue_stage_action(self, item: StagedActionQueueItem) -> dict:
        records = self.store.list_stage_queue()
        payload = asdict(item)
        records.append(payload)
        self.store.save_stage_queue(records)
        return payload

    def append_promotion_record(self, record: PromotionRecord) -> dict:
        records = self.store.list_promotion_records()
        payload = asdict(record)
        records.append(payload)
        self.store.save_promotion_records(records[-400:])
        return payload

    def update_trust_zone(self, zone_id: str, updates: dict[str, object]) -> dict | None:
        records = self.store.list_trust_zones()
        zone_key = zone_id.strip().lower()
        for index, item in enumerate(records):
            if str(item.get("zone_id", "")).strip().lower() != zone_key:
                continue
            merged = dict(item)
            merged.update(updates)
            records[index] = merged
            self.store.save_trust_zones(records)
            return merged
        return None

    def update_resource_arena(self, arena_id: str, updates: dict[str, object]) -> dict | None:
        records = self.store.list_resource_arenas()
        arena_key = arena_id.strip().lower()
        for index, item in enumerate(records):
            if str(item.get("arena_id", "")).strip().lower() != arena_key:
                continue
            merged = dict(item)
            merged.update(updates)
            records[index] = merged
            self.store.save_resource_arenas(records)
            return merged
