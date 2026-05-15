from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import AuthorityStage, ResourceArena, StagedActionQueueItem, TrustZone


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

    def _load_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _save_records(self, path: Path, records: list[dict]) -> None:
        path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

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


class TrustSupport:
    def __init__(self, store: TrustStore) -> None:
        self.store = store
        self.bootstrap_defaults()

    def bootstrap_defaults(self) -> None:
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
        if not self.store.list_resource_arenas():
            now = _now_iso()
            arena = ResourceArena(
                arena_id="gmail.shared.drafts",
                name="Shared Gmail Draft Arena",
                description="Ring-fenced shared-email draft arena that saves to drafts and alerts the principal.",
                resource_type="email_draft_pipeline",
                linked_zone_id="shared-email.stage",
                owner_principal="chris",
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

    def list_trust_zones(self) -> list[dict]:
        return self.store.list_trust_zones()

    def list_resource_arenas(self) -> list[dict]:
        return self.store.list_resource_arenas()

    def list_authority_stages(self) -> list[dict]:
        return self.store.list_authority_stages()

    def list_stage_queue(self, limit: int = 50) -> list[dict]:
        records = self.store.list_stage_queue()
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
