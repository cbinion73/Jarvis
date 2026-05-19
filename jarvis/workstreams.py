from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

GENERIC_TRUTH_STATES = (
    "planned",
    "queued",
    "researched",
    "drafted",
    "staged",
    "approved",
    "executed",
    "verified",
    "blocked",
    "dismissed",
    "failed",
)

APPROVAL_STATUSES = ("pending", "approved", "dismissed", "expired", "blocked")

ARTIFACT_TYPES = (
    "report",
    "experiment-plan",
    "market-map",
    "guardrail-review",
    "blocked-action",
    "failure-record",
    "summary-brief",
)

BLOCKED_REASONS = (
    "policy-forbidden",
    "approval-required",
    "source-unavailable",
    "cadence-not-due",
    "precondition-missing",
    "trust-zone-blocked",
)


PASSIVE_INCOME_STATES = (
    "discovered",
    "screened",
    "rejected",
    "watching",
    "researching",
    "validated",
    "experiment_planned",
    "staged_for_approval",
    "in_progress",
    "paused",
    "scaled",
    "closed",
)

MARKET_INTELLIGENCE_STATES = (
    "screened",
    "watchlist",
    "researching",
    "thesis_built",
    "buy_candidate",
    "hold",
    "trim_candidate",
    "exit_candidate",
    "rejected",
    "staged_for_approval",
    "executed_under_rule",
)

FISK_REQUIRED_REVIEWERS = [
    {"agent_id": "nebula", "label": "Nebula", "role": "assumption-attack"},
    {"agent_id": "pepper", "label": "Pepper", "role": "family-reputation-fit"},
    {"agent_id": "watcher", "label": "Watcher", "role": "memory-pattern-fit"},
    {
        "agent_id": "legal-compliance-watcher",
        "label": "Legal/Compliance Watcher",
        "role": "tax-regulatory-professional-risk",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: object) -> str:
    return str(value or "").strip(" -\n\t")


def _clean_list(values: object, *, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _clean_text(value)
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
        if len(cleaned) >= limit:
            break
    return cleaned


def _market_report_template() -> dict[str, Any]:
    return {
        "ticker_or_asset": "",
        "sector": "",
        "time_horizon": "",
        "current_price_context": "",
        "thesis": "",
        "why_this_asset_matters": "",
        "market_belief": "",
        "what_fisk_may_be_missing": "",
        "fundamentals": {
            "revenue_trend": "",
            "earnings_trend": "",
            "margins": "",
            "debt": "",
            "cash_flow": "",
            "competitive_position": "",
        },
        "valuation": {
            "current_valuation": "",
            "historical_comparison": "",
            "peer_comparison": "",
            "valuation_risk": "",
        },
        "catalysts": {
            "near_term": [],
            "medium_term": [],
            "long_term": [],
        },
        "risks": {
            "business_risk": "",
            "market_risk": "",
            "valuation_risk": "",
            "regulatory_risk": "",
            "execution_risk": "",
        },
        "prediction": {
            "base_case": "",
            "bull_case": "",
            "bear_case": "",
            "confidence": "",
            "what_would_change_the_view": "",
        },
        "recommendation": "",
        "action_status": "No action taken",
        "approval_required": True,
    }


def _normalize_truth_value(value: object, *, default: str = "planned") -> str:
    cleaned = _clean_text(value).lower().replace(" ", "_")
    return cleaned if cleaned in GENERIC_TRUTH_STATES else default


def _normalize_approval_status(value: object, *, default: str = "pending") -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in APPROVAL_STATUSES else default


def _normalize_artifact_type(value: object, *, default: str = "report") -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in ARTIFACT_TYPES else default


def _normalize_blocked_reason(value: object) -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in BLOCKED_REASONS else ""


def _status_projection(status: object) -> dict[str, str]:
    normalized = _clean_text(status).lower()
    projection = {
        "item_status": "planned",
        "action_status": "planned",
        "verification_status": "planned",
    }
    if normalized in {"discovered"}:
        return projection
    if normalized in {"screened", "watching", "watchlist", "researching", "validated"}:
        projection["item_status"] = "researched"
        projection["action_status"] = "researched"
        return projection
    if normalized in {"experiment_planned", "thesis_built", "hold"}:
        projection["item_status"] = "drafted"
        projection["action_status"] = "drafted"
        return projection
    if normalized in {"staged_for_approval", "buy_candidate", "trim_candidate", "exit_candidate"}:
        projection["item_status"] = "staged"
        projection["action_status"] = "staged"
        return projection
    if normalized in {"approved"}:
        projection["item_status"] = "approved"
        projection["action_status"] = "approved"
        return projection
    if normalized in {"executed_under_rule", "scaled", "closed", "in_progress"}:
        projection["item_status"] = "executed"
        projection["action_status"] = "executed"
        return projection
    if normalized in {"rejected", "dismissed"}:
        projection["item_status"] = "dismissed"
        projection["action_status"] = "dismissed"
        return projection
    if normalized in {"blocked"}:
        projection["item_status"] = "blocked"
        projection["action_status"] = "blocked"
        return projection
    if normalized in {"failed"}:
        projection["item_status"] = "failed"
        projection["action_status"] = "failed"
        return projection
    return projection


class AutonomousWorkstreamStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"
        self.runs_path = self.root / "runs.json"
        self.items_path = self.root / "items.json"
        self.artifacts_path = self.root / "artifacts.json"
        self.approvals_path = self.root / "approvals.json"
        self.queue_path = self.root / "queue.json"

    def _load_json(self, path: Path, *, default: Any) -> Any:
        if not path.exists():
            return deepcopy(default)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return deepcopy(default)
        return payload

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def state(self) -> dict[str, Any]:
        payload = self._load_json(self.state_path, default={})
        return payload if isinstance(payload, dict) else {}

    def save_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._save_json(self.state_path, payload)
        return payload

    def runs(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.runs_path, default=[])
        return payload if isinstance(payload, list) else []

    def append_run(self, record: dict[str, Any]) -> dict[str, Any]:
        records = self.runs()
        records.append(record)
        self._save_json(self.runs_path, records)
        return record

    def items(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.items_path, default=[])
        return payload if isinstance(payload, list) else []

    def save_items(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._save_json(self.items_path, records)
        return records

    def upsert_item(self, record: dict[str, Any]) -> dict[str, Any]:
        item_id = _clean_text(record.get("item_id"))
        if not item_id:
            raise ValueError("item_id is required")
        records = self.items()
        for index, item in enumerate(records):
            if _clean_text(item.get("item_id")) == item_id:
                records[index] = record
                self.save_items(records)
                return record
        records.append(record)
        self.save_items(records)
        return record

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        needle = _clean_text(item_id)
        if not needle:
            return None
        for item in self.items():
            if _clean_text(item.get("item_id")) == needle:
                return dict(item)
        return None

    def artifacts(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.artifacts_path, default=[])
        return payload if isinstance(payload, list) else []

    def save_artifacts(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._save_json(self.artifacts_path, records)
        return records

    def upsert_artifact(self, record: dict[str, Any]) -> dict[str, Any]:
        artifact_id = _clean_text(record.get("artifact_id"))
        if not artifact_id:
            raise ValueError("artifact_id is required")
        records = self.artifacts()
        for index, artifact in enumerate(records):
            if _clean_text(artifact.get("artifact_id")) == artifact_id:
                records[index] = record
                self.save_artifacts(records)
                return record
        records.append(record)
        self.save_artifacts(records)
        return record

    def approvals(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.approvals_path, default=[])
        return payload if isinstance(payload, list) else []

    def save_approvals(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._save_json(self.approvals_path, records)
        return records

    def upsert_approval(self, record: dict[str, Any]) -> dict[str, Any]:
        approval_id = _clean_text(record.get("approval_id"))
        if not approval_id:
            raise ValueError("approval_id is required")
        records = self.approvals()
        for index, approval in enumerate(records):
            if _clean_text(approval.get("approval_id")) == approval_id:
                records[index] = record
                self.save_approvals(records)
                return record
        records.append(record)
        self.save_approvals(records)
        return record

    def queue_entries(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.queue_path, default=[])
        return payload if isinstance(payload, list) else []

    def save_queue_entries(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._save_json(self.queue_path, records)
        return records

    def upsert_queue_entry(self, record: dict[str, Any]) -> dict[str, Any]:
        queue_id = _clean_text(record.get("queue_id"))
        if not queue_id:
            raise ValueError("queue_id is required")
        records = self.queue_entries()
        for index, entry in enumerate(records):
            if _clean_text(entry.get("queue_id")) == queue_id:
                records[index] = record
                self.save_queue_entries(records)
                return record
        records.append(record)
        self.save_queue_entries(records)
        return record


class AutonomousWorkstreamSupport:
    def __init__(self, store: AutonomousWorkstreamStore) -> None:
        self.store = store
        self._migrated = False

    def default_state(self) -> dict[str, Any]:
        return {
            "updated_at": _now_iso(),
            "mission": "Run bounded autonomous wealth workstreams with truthful execution records, explicit guardrails, and reusable lane contracts.",
            "lanes": [
                {
                    "lane_id": "passive-income",
                    "label": "Passive Income",
                    "domain": "finance",
                    "owner_agent": "Fisk",
                    "owner_agent_id": "fisk",
                    "status": "active",
                    "proof_of_concept": True,
                    "summary": "Research, rank, and stage passive-income opportunities without pretending external execution already happened.",
                    "objective": "Discover compounding revenue ideas that fit Chris's skills, values, time constraints, and distribution reality.",
                    "cadence": "weekly + on demand",
                    "cadence_minutes": 10080,
                    "autonomy_mode": "staged",
                    "review_level": "human-review-required",
                    "report_type": "fisk-opportunity-report",
                    "required_reviewers": deepcopy(FISK_REQUIRED_REVIEWERS),
                    "allowed_actions": [
                        "research",
                        "summarize",
                        "score",
                        "rank",
                        "market-map",
                        "stage-review",
                        "propose-experiment",
                    ],
                    "forbidden_actions": [
                        "spend-money",
                        "open-accounts",
                        "post-publicly",
                        "contact-third-parties",
                        "execute-transactions",
                    ],
                    "state_model": list(PASSIVE_INCOME_STATES),
                    "item_types": ["opportunity", "experiment", "market-map", "validation-gap"],
                    "source_connectors": [
                        "wealth-summary",
                        "finance-state",
                        "pipeline-state",
                        "life-agent-fisk",
                    ],
                    "scoring_categories": [
                        "market_demand",
                        "revenue_potential",
                        "effort_required",
                        "capital_required",
                        "distribution_advantage",
                        "skill_fit",
                        "family_fit",
                        "reputation_fit",
                        "values_fit",
                        "durability",
                        "automation_potential",
                        "downside_risk",
                    ],
                },
                {
                    "lane_id": "market-intelligence",
                    "label": "Market Intelligence",
                    "domain": "finance",
                    "owner_agent": "Fisk",
                    "owner_agent_id": "fisk",
                    "status": "active",
                    "proof_of_concept": False,
                    "summary": "Track watchlists, theses, catalysts, and staged investment recommendations without pretending to trade.",
                    "objective": "Give Chris disciplined market awareness, probabilistic theses, and bounded approval-ready recommendations.",
                    "cadence": "daily + on demand",
                    "cadence_minutes": 1440,
                    "autonomy_mode": "staged",
                    "review_level": "human-review-required",
                    "report_type": "fisk-market-report",
                    "required_reviewers": deepcopy(FISK_REQUIRED_REVIEWERS),
                    "allowed_actions": [
                        "screen",
                        "summarize",
                        "build-thesis",
                        "track-catalysts",
                        "stage-review",
                        "update-watchlist",
                    ],
                    "forbidden_actions": [
                        "move-money",
                        "execute-trades",
                        "open-accounts",
                        "use-margin",
                        "trade-options",
                        "buy-crypto",
                    ],
                    "state_model": list(MARKET_INTELLIGENCE_STATES),
                    "item_types": [
                        "watchlist-candidate",
                        "thesis",
                        "catalyst-alert",
                        "buy-candidate",
                        "hold",
                        "trim-candidate",
                        "exit-candidate",
                    ],
                    "source_connectors": [
                        "finance-state",
                        "wealth-summary",
                        "manual-market-watchlists",
                    ],
                    "scoring_categories": [
                        "thesis_clarity",
                        "valuation_discipline",
                        "catalyst_quality",
                        "downside_risk",
                        "time_horizon_fit",
                        "portfolio_fit",
                    ],
                },
            ],
            "notes": [
                "Treat passive income as the first proof-of-concept lane, not the whole framework.",
                "Every lane must distinguish observed, inferred, prepared, recommended, requires approval, and not done.",
                "Background work can research and stage, but it must not imply external execution without evidence.",
            ],
        }

    def state(self) -> dict[str, Any]:
        saved = self.store.state()
        default = self.default_state()
        if not saved:
            self.store.save_state(default)
            self._migrate_persisted_records(default)
            return default
        merged = dict(default)
        merged.update(saved if isinstance(saved, dict) else {})
        saved_lanes = saved.get("lanes") if isinstance(saved, dict) else None
        mutated = False
        if isinstance(saved_lanes, list) and saved_lanes:
            merged["lanes"], mutated = self._merge_lane_defaults(saved_lanes)
        if mutated:
            merged["updated_at"] = _now_iso()
            self.store.save_state(merged)
        self._migrate_persisted_records(merged)
        return merged

    def _migrate_persisted_records(self, state: dict[str, Any] | None = None) -> None:
        if self._migrated:
            return
        state = state or self.store.state() or self.default_state()
        lanes = {
            _clean_text(lane.get("lane_id")): dict(lane)
            for lane in list(state.get("lanes", []))
            if isinstance(lane, dict) and _clean_text(lane.get("lane_id"))
        }
        runs = self.store.runs()
        runs_mutated = False
        migrated_runs: list[dict[str, Any]] = []
        for run in runs:
            record = dict(run)
            status = _clean_text(record.get("status")).lower() or "completed"
            items_staged = int(record.get("items_staged") or 0)
            if not _clean_text(record.get("run_status")):
                record["run_status"] = "blocked" if status == "skipped" else ("failed" if status == "failed" else "executed")
                runs_mutated = True
            if not _clean_text(record.get("action_status")):
                record["action_status"] = "blocked" if status == "skipped" else ("staged" if items_staged > 0 else "researched")
                runs_mutated = True
            if not _clean_text(record.get("verification_status")):
                record["verification_status"] = "planned"
                runs_mutated = True
            normalized_blocked = _normalize_blocked_reason(record.get("blocked_reason"))
            if record.get("blocked_reason", "") != normalized_blocked:
                record["blocked_reason"] = normalized_blocked
                runs_mutated = True
            desired_truth = record.get("action_status") or ("blocked" if status == "skipped" else ("staged" if items_staged > 0 else "researched"))
            desired_truth = _normalize_truth_value(desired_truth, default="researched")
            if _clean_text(record.get("truth_state")) != desired_truth:
                record["truth_state"] = desired_truth
                runs_mutated = True
            migrated_runs.append(record)
        if runs_mutated:
            self.store._save_json(self.store.runs_path, migrated_runs)

        items = self.store.items()
        items_mutated = False
        migrated_items: list[dict[str, Any]] = []
        for item in items:
            record = dict(item)
            lane = lanes.get(_clean_text(record.get("lane_id")), {})
            projection = _status_projection(record.get("status"))
            desired_truth = projection["action_status"]
            if not _clean_text(record.get("item_status")):
                record["item_status"] = projection["item_status"]
                items_mutated = True
            if not _clean_text(record.get("action_status")):
                record["action_status"] = desired_truth
                items_mutated = True
            if not _clean_text(record.get("verification_status")):
                record["verification_status"] = projection["verification_status"]
                items_mutated = True
            if _clean_text(record.get("truth_state")) != desired_truth:
                record["truth_state"] = desired_truth
                items_mutated = True
            normalized_blocked = _normalize_blocked_reason(record.get("blocked_reason"))
            if record.get("blocked_reason", "") != normalized_blocked:
                record["blocked_reason"] = normalized_blocked
                items_mutated = True
            approval_required = bool(record.get("approval_required"))
            desired_approval = _normalize_approval_status(
                record.get("approval_status"),
                default="pending" if approval_required and _clean_text(record.get("status")).lower() not in {"approved", "dismissed", "rejected", "closed"} else "",
            )
            if record.get("approval_status", "") != desired_approval:
                record["approval_status"] = desired_approval
                items_mutated = True
            if lane:
                if not _clean_text(record.get("report_type")) and _clean_text(lane.get("report_type")):
                    record["report_type"] = _clean_text(lane.get("report_type"))
                    items_mutated = True
                desired_reviewers = [dict(entry) for entry in list(lane.get("required_reviewers", [])) if isinstance(entry, dict)]
                if desired_reviewers and not list(record.get("required_reviewers", []) or []):
                    record["required_reviewers"] = desired_reviewers
                    items_mutated = True
                if not _clean_text(record.get("owner_agent")) and _clean_text(lane.get("owner_agent")):
                    record["owner_agent"] = _clean_text(lane.get("owner_agent"))
                    items_mutated = True
                if not _clean_text(record.get("owner_agent_id")) and _clean_text(lane.get("owner_agent_id")):
                    record["owner_agent_id"] = _clean_text(lane.get("owner_agent_id"))
                    items_mutated = True
            migrated_items.append(record)
        if items_mutated:
            self.store.save_items(migrated_items)

        artifacts_before = len(self.store.artifacts())
        approvals_before = len(self.store.approvals())
        queue_before = len(self.store.queue_entries())
        for item in self.store.items():
            lane = lanes.get(_clean_text(item.get("lane_id")), {})
            if not lane:
                continue
            item_id = str(item.get("item_id", "")).strip()
            if not item_id:
                continue
            if isinstance(item.get("opportunity_report"), dict):
                self._record_artifact(
                    actor=str(item.get("actor", "")).strip() or "Chris",
                    lane=lane,
                    item_id=item_id,
                    artifact_type="experiment-plan" if _clean_text(item.get("candidate_type")).lower() == "experiment" else "report",
                    title=str(item.get("title", "Workstream report")).strip(),
                    summary=str(item.get("summary", "")).strip(),
                    payload={"report_type": str(item.get("report_type", "")).strip(), "opportunity_report": dict(item.get("opportunity_report") or {})},
                )
            elif isinstance(item.get("market_report"), dict):
                self._record_artifact(
                    actor=str(item.get("actor", "")).strip() or "Chris",
                    lane=lane,
                    item_id=item_id,
                    artifact_type="report",
                    title=str(item.get("title", "Workstream report")).strip(),
                    summary=str(item.get("summary", "")).strip(),
                    payload={"report_type": str(item.get("report_type", "")).strip(), "market_report": dict(item.get("market_report") or {})},
                )
            if item.get("approval_required"):
                self._ensure_approval(actor=str(item.get("actor", "")).strip() or "Chris", lane=lane, item=item)
            self._ensure_queue_entry(actor=str(item.get("actor", "")).strip() or "Chris", lane=lane, item=item)

        if artifacts_before != len(self.store.artifacts()) or approvals_before != len(self.store.approvals()) or queue_before != len(self.store.queue_entries()):
            self.store.save_state({**state, "updated_at": _now_iso()})
        self._migrated = True

    def lanes(self) -> list[dict[str, Any]]:
        return [dict(item) for item in list(self.state().get("lanes", [])) if isinstance(item, dict)]

    def lane(self, lane_id: str) -> dict[str, Any] | None:
        needle = _clean_text(lane_id).lower()
        if not needle:
            return None
        for lane in self.lanes():
            if _clean_text(lane.get("lane_id")).lower() == needle:
                return lane
        return None

    def _merge_lane_defaults(self, saved_lanes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
        defaults = {str(lane.get("lane_id", "")).strip(): dict(lane) for lane in self.default_state().get("lanes", []) if isinstance(lane, dict)}
        merged_lanes: list[dict[str, Any]] = []
        seen: set[str] = set()
        mutated = False
        for lane in saved_lanes:
            if not isinstance(lane, dict):
                mutated = True
                continue
            lane_id = _clean_text(lane.get("lane_id"))
            if not lane_id:
                mutated = True
                continue
            seed = dict(defaults.get(lane_id, {}))
            combined = dict(seed)
            combined.update(lane)
            if lane_id in {"passive-income", "market-intelligence"}:
                combined["owner_agent"] = "Fisk"
                combined["owner_agent_id"] = "fisk"
                combined["required_reviewers"] = deepcopy(FISK_REQUIRED_REVIEWERS)
                if seed:
                    combined["cadence"] = seed.get("cadence", combined.get("cadence"))
                    combined["cadence_minutes"] = seed.get("cadence_minutes", combined.get("cadence_minutes"))
                    combined["report_type"] = seed.get("report_type", combined.get("report_type"))
            if lane_id == "passive-income" and _clean_text(combined.get("status")).lower() != "active":
                combined["status"] = "active"
            if lane_id == "market-intelligence":
                combined["status"] = "active"
            if combined != lane:
                mutated = True
            merged_lanes.append(combined)
            seen.add(lane_id)
        for lane_id, default_lane in defaults.items():
            if lane_id not in seen:
                merged_lanes.append(default_lane)
                mutated = True
        return merged_lanes, mutated

    def list_runs(self, *, lane_id: str = "", actor: str = "", limit: int = 12) -> list[dict[str, Any]]:
        lane_key = _clean_text(lane_id).lower()
        actor_key = _clean_text(actor).lower()
        records = []
        for item in self.store.runs():
            if lane_key and _clean_text(item.get("lane_id")).lower() != lane_key:
                continue
            if actor_key and _clean_text(item.get("actor")).lower() != actor_key:
                continue
            records.append(dict(item))
        records.sort(key=lambda item: _clean_text(item.get("started_at")), reverse=True)
        return records[:limit]

    def list_items(
        self,
        *,
        lane_id: str = "",
        actor: str = "",
        statuses: tuple[str, ...] = (),
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        lane_key = _clean_text(lane_id).lower()
        actor_key = _clean_text(actor).lower()
        status_keys = {_clean_text(item).lower() for item in statuses if _clean_text(item)}
        records = []
        for item in self.store.items():
            if lane_key and _clean_text(item.get("lane_id")).lower() != lane_key:
                continue
            if actor_key and _clean_text(item.get("actor")).lower() != actor_key:
                continue
            if status_keys and _clean_text(item.get("status")).lower() not in status_keys:
                continue
            records.append(dict(item))
        records.sort(key=lambda item: _clean_text(item.get("updated_at")), reverse=True)
        return records[:limit]

    def list_artifacts(
        self,
        *,
        lane_id: str = "",
        actor: str = "",
        item_id: str = "",
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        lane_key = _clean_text(lane_id).lower()
        actor_key = _clean_text(actor).lower()
        item_key = _clean_text(item_id).lower()
        records = []
        for artifact in self.store.artifacts():
            if lane_key and _clean_text(artifact.get("lane_id")).lower() != lane_key:
                continue
            if actor_key and _clean_text(artifact.get("actor")).lower() != actor_key:
                continue
            if item_key and _clean_text(artifact.get("item_id")).lower() != item_key:
                continue
            records.append(dict(artifact))
        records.sort(key=lambda item: _clean_text(item.get("created_at")), reverse=True)
        return records[:limit]

    def list_approvals(
        self,
        *,
        lane_id: str = "",
        actor: str = "",
        item_id: str = "",
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        lane_key = _clean_text(lane_id).lower()
        actor_key = _clean_text(actor).lower()
        item_key = _clean_text(item_id).lower()
        records = []
        for approval in self.store.approvals():
            if lane_key and _clean_text(approval.get("lane_id")).lower() != lane_key:
                continue
            if actor_key and _clean_text(approval.get("actor")).lower() != actor_key:
                continue
            if item_key and _clean_text(approval.get("item_id")).lower() != item_key:
                continue
            records.append(dict(approval))
        records.sort(key=lambda item: _clean_text(item.get("updated_at")), reverse=True)
        return records[:limit]

    def list_queue_entries(
        self,
        *,
        lane_id: str = "",
        actor: str = "",
        item_id: str = "",
        statuses: tuple[str, ...] = (),
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        lane_key = _clean_text(lane_id).lower()
        actor_key = _clean_text(actor).lower()
        item_key = _clean_text(item_id).lower()
        status_keys = {_clean_text(item).lower() for item in statuses if _clean_text(item)}
        records = []
        for entry in self.store.queue_entries():
            if lane_key and _clean_text(entry.get("lane_id")).lower() != lane_key:
                continue
            if actor_key and _clean_text(entry.get("actor")).lower() != actor_key:
                continue
            if item_key and _clean_text(entry.get("item_id")).lower() != item_key:
                continue
            if status_keys and _clean_text(entry.get("status")).lower() not in status_keys:
                continue
            records.append(dict(entry))
        records.sort(key=lambda item: _clean_text(item.get("updated_at")), reverse=True)
        return records[:limit]

    def _artifact_key(self, item_id: str, artifact_type: str) -> str:
        return f"{item_id}:{artifact_type}"

    def _approval_key(self, item_id: str) -> str:
        return f"approval:{item_id}"

    def _queue_key(self, item_id: str) -> str:
        return f"queue:{item_id}"

    def _queue_type_for_item(self, item: dict[str, Any]) -> str:
        status = _clean_text(item.get("status")).lower()
        if status in {"buy_candidate", "trim_candidate", "exit_candidate", "staged_for_approval"}:
            return "approve"
        if status in {"experiment_planned", "thesis_built"}:
            return "request-deeper-research"
        return "review"

    def _record_artifact(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        item_id: str,
        artifact_type: str,
        title: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        blocked_reason: str = "",
        artifact_id: str = "",
    ) -> dict[str, Any]:
        existing = {}
        normalized_artifact_id = _clean_text(artifact_id)
        if not normalized_artifact_id:
            existing = next(
                (
                    artifact
                    for artifact in self.list_artifacts(item_id=item_id, limit=24)
                    if _clean_text(artifact.get("artifact_type")) == _normalize_artifact_type(artifact_type)
                ),
                {},
            )
        now = _now_iso()
        record = {
            "artifact_id": normalized_artifact_id or _clean_text(existing.get("artifact_id")) or self._artifact_key(item_id, artifact_type),
            "item_id": item_id,
            "actor": actor,
            "lane_id": _clean_text(lane.get("lane_id")),
            "artifact_type": _normalize_artifact_type(artifact_type),
            "title": _clean_text(title) or "Workstream artifact",
            "summary": _clean_text(summary),
            "blocked_reason": _normalize_blocked_reason(blocked_reason),
            "created_at": _clean_text(existing.get("created_at")) or now,
            "updated_at": now,
            "payload": dict(payload or {}),
        }
        return self.store.upsert_artifact(record)

    def _ensure_approval(self, *, actor: str, lane: dict[str, Any], item: dict[str, Any]) -> dict[str, Any] | None:
        if not item.get("approval_required"):
            return None
        existing = next((entry for entry in self.list_approvals(item_id=str(item.get("item_id")), limit=8)), {})
        now = _now_iso()
        record = {
            "approval_id": _clean_text(existing.get("approval_id")) or self._approval_key(str(item.get("item_id"))),
            "item_id": str(item.get("item_id", "")).strip(),
            "actor": actor,
            "lane_id": _clean_text(lane.get("lane_id")),
            "status": _normalize_approval_status(existing.get("status"), default="pending"),
            "title": f"Approval needed · {str(item.get('title', 'Workstream item')).strip()}",
            "summary": _clean_list(item.get("requires_approval"), limit=4)[0] if _clean_list(item.get("requires_approval"), limit=4) else "Human approval is required before any external or financial action.",
            "required_reviewers": [dict(entry) for entry in list(item.get("required_reviewers", [])) if isinstance(entry, dict)],
            "created_at": _clean_text(existing.get("created_at")) or now,
            "updated_at": now,
        }
        return self.store.upsert_approval(record)

    def _ensure_queue_entry(self, *, actor: str, lane: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        existing = next((entry for entry in self.list_queue_entries(item_id=str(item.get("item_id")), limit=8)), {})
        now = _now_iso()
        queue_type = self._queue_type_for_item(item)
        status_value = _clean_text(item.get("status")).lower()
        approval_status = "pending" if item.get("approval_required") else ""
        queue_status = _clean_text(existing.get("status")) or "pending"
        if status_value in {"approved", "dismissed", "rejected", "closed"}:
            queue_status = "closed"
        record = {
            "queue_id": _clean_text(existing.get("queue_id")) or self._queue_key(str(item.get("item_id"))),
            "item_id": str(item.get("item_id", "")).strip(),
            "actor": actor,
            "lane_id": _clean_text(lane.get("lane_id")),
            "status": queue_status,
            "queue_type": queue_type,
            "title": str(item.get("title", "Workstream review item")).strip() or "Workstream review item",
            "summary": str(item.get("summary", "")).strip(),
            "recommended_action": str(item.get("recommended_action", "")).strip() or str(item.get("next_action", "")).strip() or "review",
            "required_reviewers": [dict(entry) for entry in list(item.get("required_reviewers", [])) if isinstance(entry, dict)],
            "approval_status": approval_status or _normalize_approval_status(existing.get("approval_status"), default="pending" if item.get("approval_required") else "approved"),
            "route_options": ["Nebula", "Pepper", "Watcher", "Legal/Compliance Watcher", "deeper-research"],
            "created_at": _clean_text(existing.get("created_at")) or now,
            "updated_at": now,
        }
        return self.store.upsert_queue_entry(record)

    def _attach_related_records(self, item: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(item)
        item_id = str(item.get("item_id", "")).strip()
        approvals = self.list_approvals(item_id=item_id, limit=8)
        queue_entries = self.list_queue_entries(item_id=item_id, limit=8)
        artifacts = self.list_artifacts(item_id=item_id, limit=24)
        if approvals:
            enriched["approval_status"] = _normalize_approval_status(approvals[0].get("status"))
        else:
            enriched["approval_status"] = "pending" if enriched.get("approval_required") else ""
        enriched["queue_entries"] = queue_entries
        enriched["artifacts"] = artifacts
        return enriched

    def _item_key(self, lane_id: str, actor: str, title: str) -> str:
        digest = hashlib.sha1(f"{lane_id}|{actor}|{title}".encode("utf-8")).hexdigest()
        return digest[:16]

    def _base_record(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        title: str,
        summary: str,
        candidate_type: str,
        status: str,
        confidence: str,
        next_action: str,
        evidence: list[dict[str, Any]],
        observed: list[str],
        inferred: list[str],
        prepared: list[str],
        recommended: list[str],
        requires_approval: list[str],
        not_done: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_title = _clean_text(title)
        item_id = f"{_clean_text(lane.get('lane_id'))}-{self._item_key(_clean_text(lane.get('lane_id')), actor, normalized_title)}"
        existing = self.store.get_item(item_id) or {}
        now = _now_iso()
        projection = _status_projection(status)
        record = {
            "item_id": item_id,
            "actor": actor,
            "lane_id": _clean_text(lane.get("lane_id")),
            "label": normalized_title,
            "title": normalized_title,
            "summary": _clean_text(summary),
            "candidate_type": _clean_text(candidate_type) or "opportunity",
            "status": _clean_text(status) or "researching",
            "truth_state": projection["action_status"],
            "item_status": projection["item_status"],
            "action_status": projection["action_status"],
            "verification_status": _normalize_truth_value(existing.get("verification_status"), default=projection["verification_status"]),
            "owner_agent": _clean_text(lane.get("owner_agent")) or "JARVIS",
            "owner_agent_id": _clean_text(lane.get("owner_agent_id")) or "jarvis-orchestrator",
            "domain": _clean_text(lane.get("domain")) or "general",
            "confidence": _clean_text(confidence) or "medium",
            "next_action": _clean_text(next_action) or "review",
            "created_at": _clean_text(existing.get("created_at")) or now,
            "updated_at": now,
            "last_reviewed_at": _clean_text(existing.get("last_reviewed_at")),
            "work_id": _clean_text(existing.get("work_id")),
            "report_type": _clean_text(lane.get("report_type")),
            "required_reviewers": [dict(entry) for entry in list(lane.get("required_reviewers", [])) if isinstance(entry, dict)],
            "approval_required": bool(requires_approval),
            "approval_status": _normalize_approval_status(existing.get("approval_status"), default="pending" if requires_approval else ""),
            "recommended_action": _clean_text(next_action) or "review",
            "blocked_reason": _normalize_blocked_reason(existing.get("blocked_reason")),
            "observed": _clean_list(observed, limit=12),
            "inferred": _clean_list(inferred, limit=12),
            "prepared": _clean_list(prepared, limit=12),
            "recommended": _clean_list(recommended, limit=12),
            "requires_approval": _clean_list(requires_approval, limit=12),
            "not_done": _clean_list(not_done, limit=12),
            "evidence": [dict(entry) for entry in evidence if isinstance(entry, dict)],
            "guardrail_reviews": [dict(entry) for entry in list(existing.get("guardrail_reviews", [])) if isinstance(entry, dict)],
            "metadata": dict(existing.get("metadata") or {}),
        }
        if metadata:
            record["metadata"].update(metadata)
        return record

    def _fisk_opportunity_report(
        self,
        *,
        title: str,
        category: str,
        summary: str,
        source: str,
        market_reality: str,
        who_pays: str,
        why_they_pay: str,
        current_alternatives: list[str],
        where_money_flows: str,
        who_controls_distribution: str,
        leverage_point: str,
        advantage: str,
        reusable_asset: str,
        ownable_channel: str,
        compounding_vector: str,
        revenue: str,
        startup_cost: str,
        operating_effort: str,
        time_to_first_dollar: str,
        time_to_meaningful_revenue: str,
        scalability: str,
        main_downside: str,
        hidden_labor: str,
        capital_risk: str,
        reputation_risk: str,
        family_time_cost: str,
        confidence: str,
        score: dict[str, Any],
        recommendation: str,
        next_action: str,
        approval_needed: bool,
    ) -> dict[str, Any]:
        return {
            "opportunity": _clean_text(title),
            "category": _clean_text(category),
            "source": _clean_text(source),
            "summary": _clean_text(summary),
            "market_reality": _clean_text(market_reality),
            "who_pays": _clean_text(who_pays),
            "why_they_pay": _clean_text(why_they_pay),
            "current_alternatives": _clean_list(current_alternatives, limit=8),
            "where_money_flows": _clean_text(where_money_flows),
            "who_controls_distribution": _clean_text(who_controls_distribution),
            "leverage_point": _clean_text(leverage_point),
            "advantage": _clean_text(advantage),
            "reusable_asset": _clean_text(reusable_asset),
            "ownable_channel": _clean_text(ownable_channel),
            "compounding_vector": _clean_text(compounding_vector),
            "economic_model": {
                "possible_revenue": _clean_text(revenue),
                "startup_cost": _clean_text(startup_cost),
                "operating_effort": _clean_text(operating_effort),
                "time_to_first_dollar": _clean_text(time_to_first_dollar),
                "time_to_meaningful_revenue": _clean_text(time_to_meaningful_revenue),
                "scalability": _clean_text(scalability),
            },
            "risk": {
                "main_downside": _clean_text(main_downside),
                "hidden_labor": _clean_text(hidden_labor),
                "capital_risk": _clean_text(capital_risk),
                "reputation_risk": _clean_text(reputation_risk),
                "family_time_cost": _clean_text(family_time_cost),
            },
            "confidence_level": _clean_text(confidence),
            "score": dict(score),
            "fisk_recommendation": _clean_text(recommendation),
            "next_action": _clean_text(next_action),
            "approval_needed": bool(approval_needed),
            "agents_to_route_to": [entry["label"] for entry in FISK_REQUIRED_REVIEWERS],
        }

    def _upsert_passive_income_candidate(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        title: str,
        summary: str,
        candidate_type: str,
        status: str,
        confidence: str,
        next_action: str,
        evidence: list[dict[str, Any]],
        observed: list[str],
        inferred: list[str],
        prepared: list[str],
        recommended: list[str],
        requires_approval: list[str],
        not_done: list[str],
        report: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._base_record(
            actor=actor,
            lane=lane,
            title=title,
            summary=summary,
            candidate_type=candidate_type,
            status=status,
            confidence=confidence,
            next_action=next_action,
            evidence=evidence,
            observed=observed,
            inferred=inferred,
            prepared=prepared,
            recommended=recommended,
            requires_approval=requires_approval,
            not_done=not_done,
            metadata=metadata,
        )
        record["opportunity_report"] = report
        stored = self.store.upsert_item(record)
        self._record_artifact(
            actor=actor,
            lane=lane,
            item_id=str(stored.get("item_id", "")).strip(),
            artifact_type="experiment-plan" if _clean_text(candidate_type).lower() == "experiment" else "report",
            title=str(stored.get("title", "Fisk opportunity report")).strip(),
            summary=str(stored.get("summary", "")).strip(),
            payload={"report_type": str(stored.get("report_type", "")).strip(), "opportunity_report": report},
        )
        self._ensure_approval(actor=actor, lane=lane, item=stored)
        self._ensure_queue_entry(actor=actor, lane=lane, item=stored)
        return self._attach_related_records(stored)

    def _upsert_market_candidate(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        title: str,
        summary: str,
        candidate_type: str,
        status: str,
        confidence: str,
        next_action: str,
        evidence: list[dict[str, Any]],
        observed: list[str],
        inferred: list[str],
        prepared: list[str],
        recommended: list[str],
        requires_approval: list[str],
        not_done: list[str],
        report: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._base_record(
            actor=actor,
            lane=lane,
            title=title,
            summary=summary,
            candidate_type=candidate_type,
            status=status,
            confidence=confidence,
            next_action=next_action,
            evidence=evidence,
            observed=observed,
            inferred=inferred,
            prepared=prepared,
            recommended=recommended,
            requires_approval=requires_approval,
            not_done=not_done,
            metadata=metadata,
        )
        template = _market_report_template()
        template.update(report)
        record["market_report"] = template
        stored = self.store.upsert_item(record)
        self._record_artifact(
            actor=actor,
            lane=lane,
            item_id=str(stored.get("item_id", "")).strip(),
            artifact_type="report",
            title=str(stored.get("title", "Fisk market report")).strip(),
            summary=str(stored.get("summary", "")).strip(),
            payload={"report_type": str(stored.get("report_type", "")).strip(), "market_report": template},
        )
        self._ensure_approval(actor=actor, lane=lane, item=stored)
        self._ensure_queue_entry(actor=actor, lane=lane, item=stored)
        return self._attach_related_records(stored)

    def lane_readiness(
        self,
        *,
        actor: str,
        lane_id: str,
        source: str,
        finance_state: dict[str, Any] | None = None,
        wealth_summary: dict[str, Any] | None = None,
        pipeline_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lane = self.lane(lane_id)
        if lane is None:
            raise KeyError("Workstream lane not found.")
        source_key = _clean_text(source).lower() or "manual"
        last_run = next(iter(self.list_runs(actor=actor, lane_id=lane_id, limit=1)), {})
        cadence_minutes = int(lane.get("cadence_minutes") or 0)
        should_run = True
        reason = ""
        next_run_at = ""
        if source_key == "background" and cadence_minutes > 0 and _clean_text(last_run.get("completed_at")):
            try:
                completed_dt = datetime.fromisoformat(str(last_run.get("completed_at")).replace("Z", "+00:00"))
                now_dt = datetime.now(timezone.utc)
                elapsed_minutes = (now_dt - completed_dt.astimezone(timezone.utc)).total_seconds() / 60
                if elapsed_minutes < cadence_minutes:
                    should_run = False
                    reason = "cadence-not-due"
                    next_run_at = (completed_dt.astimezone(timezone.utc) + timedelta(minutes=cadence_minutes)).isoformat()
            except ValueError:
                pass

        has_finance_state = finance_state is not None
        has_wealth_summary = wealth_summary is not None
        has_pipeline_state = pipeline_state is not None
        finance_state = finance_state or {}
        wealth_summary = wealth_summary or {}
        pipeline_state = pipeline_state or {}
        if should_run:
            if _clean_text(lane.get("lane_id")) == "passive-income":
                sources_available = True
                if has_wealth_summary or has_pipeline_state:
                    sources_available = any(
                        (
                            wealth_summary.get("recent_runs"),
                            wealth_summary.get("opportunity_theses"),
                            wealth_summary.get("experiments_in_flight"),
                            (pipeline_state.get("opportunities") or []),
                        )
                    )
                if not sources_available:
                    should_run = False
                    reason = "source-unavailable"
            elif _clean_text(lane.get("lane_id")) == "market-intelligence":
                sources_available = bool(finance_state) if has_finance_state else True
                if not sources_available:
                    should_run = False
                    reason = "source-unavailable"

        state = "can-run" if should_run else ("should-run-later" if reason == "cadence-not-due" else "cannot-run")
        return {
            "lane_id": _clean_text(lane.get("lane_id")),
            "state": state,
            "blocked_reason": _normalize_blocked_reason(reason),
            "last_run_at": _clean_text(last_run.get("completed_at")) or _clean_text(last_run.get("started_at")),
            "next_run_at": next_run_at,
            "cadence_minutes": cadence_minutes,
            "source": source_key,
        }

    def _blocked_run_record(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        source: str,
        blocked_reason: str,
        summary: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        run_record = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "lane_id": _clean_text(lane.get("lane_id")),
            "lane_label": _clean_text(lane.get("label")) or _clean_text(lane.get("lane_id")),
            "report_type": _clean_text(lane.get("report_type")),
            "status": "skipped",
            "run_status": "blocked",
            "truth_state": "blocked",
            "action_status": "blocked",
            "verification_status": "planned",
            "blocked_reason": _normalize_blocked_reason(blocked_reason),
            "source": _clean_text(source) or "manual",
            "started_at": now,
            "completed_at": now,
            "items_staged": 0,
            "staged_titles": [],
            "evidence_counts": {},
            "required_reviewers": [dict(entry) for entry in list(lane.get("required_reviewers", [])) if isinstance(entry, dict)],
            "summary": _clean_text(summary),
            "observed": [f"Lane {_clean_text(lane.get('lane_id'))} did not run."],
            "inferred": [],
            "prepared": [],
            "recommended": [],
            "requires_approval": [],
            "not_done": ["No external or financial action occurred."],
        }
        self.store.append_run(run_record)
        self._record_artifact(
            actor=actor,
            lane=lane,
            item_id=f"{_clean_text(lane.get('lane_id'))}:lane",
            artifact_type="blocked-action",
            title=f"{_clean_text(lane.get('label')) or _clean_text(lane.get('lane_id'))} blocked",
            summary=summary,
            payload={"run_id": run_record["run_id"], "blocked_reason": blocked_reason},
            blocked_reason=blocked_reason,
            artifact_id=f"{run_record['run_id']}:blocked-action",
        )
        return run_record

    def run_lane(
        self,
        *,
        actor: str,
        lane_id: str,
        source: str,
        wealth_summary: dict[str, Any] | None = None,
        finance_state: dict[str, Any] | None = None,
        pipeline_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lane = self.lane(lane_id)
        if lane is None:
            raise KeyError("Workstream lane not found.")
        readiness = self.lane_readiness(
            actor=actor,
            lane_id=lane_id,
            source=source,
            wealth_summary=wealth_summary,
            finance_state=finance_state,
            pipeline_state=pipeline_state,
        )
        if readiness.get("state") != "can-run":
            blocked_reason = str(readiness.get("blocked_reason", "")).strip() or "precondition-missing"
            summary = (
                f"{_clean_text(lane.get('label')) or lane_id} did not run because "
                f"{blocked_reason.replace('-', ' ')}."
            )
            run_record = self._blocked_run_record(
                actor=actor,
                lane=lane,
                source=source,
                blocked_reason=blocked_reason,
                summary=summary,
            )
            return {"ok": True, "run": run_record, "items": [], "lane": lane, "readiness": readiness}
        started_at = _now_iso()
        created_items: list[dict[str, Any]] = []
        staged_titles: list[str] = []
        evidence_counts: dict[str, int] = {}
        lane_key = _clean_text(lane.get("lane_id"))

        if lane_key == "passive-income":
            created_items, staged_titles, evidence_counts = self._run_passive_income_lane(
                actor=actor,
                lane=lane,
                wealth_summary=wealth_summary or {},
                finance_state=finance_state or {},
                pipeline_state=pipeline_state or {},
            )
        elif lane_key == "market-intelligence":
            created_items, staged_titles, evidence_counts = self._run_market_intelligence_lane(
                actor=actor,
                lane=lane,
                finance_state=finance_state or {},
            )

        run_record = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "lane_id": lane_key,
            "lane_label": _clean_text(lane.get("label")) or lane_key,
            "report_type": _clean_text(lane.get("report_type")),
            "status": "completed",
            "run_status": "executed",
            "truth_state": "staged" if created_items else "researched",
            "action_status": "staged" if created_items else "researched",
            "verification_status": "planned",
            "blocked_reason": "",
            "source": _clean_text(source) or "manual",
            "started_at": started_at,
            "completed_at": _now_iso(),
            "items_staged": len(created_items),
            "staged_titles": staged_titles[:8],
            "evidence_counts": evidence_counts,
            "required_reviewers": [dict(entry) for entry in list(lane.get("required_reviewers", [])) if isinstance(entry, dict)],
            "summary": (
                f"Reviewed {max(evidence_counts.values(), default=0)} source signal(s) and staged "
                f"{len(created_items)} reviewable item(s) for {_clean_text(lane.get('label')) or lane_key}."
            ),
            "observed": [f"Lane {lane_key} executed in bounded research mode."],
            "inferred": [f"{len(created_items)} item(s) were strong enough to keep under review."] if created_items else ["No sufficiently strong items were found."],
            "prepared": [f"Prepared {len(created_items)} structured report(s)."] if created_items else [],
            "recommended": [f"Route staged outputs through {', '.join(entry['label'] for entry in FISK_REQUIRED_REVIEWERS)}."] if created_items else [],
            "requires_approval": ["Any external action or financial commitment still requires Chris's approval."] if created_items else [],
            "not_done": [
                "No money was moved.",
                "No trades were executed.",
                "No external accounts were opened.",
                "No third parties were contacted.",
            ],
        }
        self.store.append_run(run_record)
        self._record_artifact(
            actor=actor,
            lane=lane,
            item_id=f"{lane_key}:lane",
            artifact_type="summary-brief",
            title=f"{_clean_text(lane.get('label')) or lane_key} summary",
            summary=str(run_record.get("summary", "")).strip(),
            payload={"run_id": run_record["run_id"], "staged_titles": staged_titles[:8]},
            artifact_id=f"{run_record['run_id']}:summary-brief",
        )
        state = self.state()
        state["updated_at"] = _now_iso()
        self.store.save_state(state)
        return {
            "ok": True,
            "run": run_record,
            "items": created_items,
            "lane": lane,
            "readiness": readiness,
        }

    def _run_passive_income_lane(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        wealth_summary: dict[str, Any],
        finance_state: dict[str, Any],
        pipeline_state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
        items: list[dict[str, Any]] = []
        staged_titles: list[str] = []
        evidence_counts = {
            "wealth_runs": len(list(wealth_summary.get("recent_runs", []))),
            "opportunity_theses": len([entry for entry in list(wealth_summary.get("opportunity_theses", [])) if _clean_text(entry)]),
            "experiments_in_flight": len([entry for entry in list(wealth_summary.get("experiments_in_flight", [])) if _clean_text(entry)]),
            "pipeline_opportunities": len([entry for entry in list((pipeline_state.get("opportunities") or [])) if isinstance(entry, dict)]),
        }
        theses = [_clean_text(item) for item in list(wealth_summary.get("opportunity_theses", [])) if _clean_text(item)]
        experiments = [_clean_text(item) for item in list(wealth_summary.get("experiments_in_flight", [])) if _clean_text(item)]
        recent_runs = [item for item in list(wealth_summary.get("recent_runs", [])) if isinstance(item, dict)]
        pipeline_opportunities = [item for item in list((pipeline_state.get("opportunities") or [])) if isinstance(item, dict)]

        for thesis in theses[:6]:
            score = {
                "market_demand": "medium",
                "revenue_potential": "medium",
                "effort_required": "unknown",
                "capital_required": "low",
                "distribution_advantage": "unknown",
                "skill_fit": "medium",
                "family_fit": "unknown",
                "reputation_fit": "unknown",
                "values_fit": "review",
                "durability": "medium",
                "automation_potential": "medium",
                "downside_risk": "moderate",
            }
            report = self._fisk_opportunity_report(
                title=thesis,
                category="passive-income",
                summary="Opportunity thesis preserved from prior wealth-and-leverage research and staged for explicit review.",
                source="wealth-summary",
                market_reality="The thesis exists, but market demand, channel ownership, and margin capture still need disciplined validation.",
                who_pays="Not yet validated.",
                why_they_pay="Not yet validated.",
                current_alternatives=["Generic side-hustle offerings", "Existing crowded digital-product markets"],
                where_money_flows="Money likely flows through buyers who pay for clarity, speed, or implementation help, but the exact payment path still needs market mapping.",
                who_controls_distribution="The distribution owner is not bounded yet.",
                leverage_point="The leverage may be packaging Chris's knowledge into something repeatable instead of inventing from scratch.",
                advantage="Existing frameworks, voice, and lived experience may create an advantage if paired with a real channel.",
                reusable_asset="Existing frameworks or prior writing",
                ownable_channel="Owned email/list or direct audience channel",
                compounding_vector="Reusable IP that can feed later products or training",
                revenue="Unknown until validation",
                startup_cost="Low",
                operating_effort="Unknown",
                time_to_first_dollar="Unknown",
                time_to_meaningful_revenue="Unknown",
                scalability="Potentially medium if distribution is solved",
                main_downside="Looks like passive income but may become disguised labor.",
                hidden_labor="Distribution and follow-up burden are not bounded yet.",
                capital_risk="Low",
                reputation_risk="Medium until positioning is clear",
                family_time_cost="Needs Pepper review",
                confidence="medium",
                score=score,
                recommendation="Research",
                next_action="promote-to-experiment",
                approval_needed=True,
            )
            record = self._upsert_passive_income_candidate(
                actor=actor,
                lane=lane,
                title=thesis,
                summary=report["summary"],
                candidate_type="opportunity",
                status="researching",
                confidence="medium",
                next_action="promote-to-experiment",
                evidence=[
                    {"source": "wealth-summary", "detail": thesis, "kind": "opportunity-thesis"},
                    {"source": "wealth-runs", "detail": f"{len(recent_runs)} prior wealth run(s) available for context.", "kind": "supporting-context"},
                ],
                observed=[f"Stored thesis: {thesis}", f"{len(recent_runs)} recent wealth run(s) available."],
                inferred=["The thesis may be viable, but the channel, buyer, and operating burden are still under-bounded."],
                prepared=["Prepared a Fisk opportunity report.", "Prepared guardrail routing metadata."],
                recommended=["Score and market-map the thesis before building.", "Push Nebula to attack the assumptions early."],
                requires_approval=["Any real capital commitment or public launch."],
                not_done=["Did not validate demand.", "Did not contact buyers.", "Did not build the offer."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])

        for experiment in experiments[:4]:
            score = {
                "market_demand": "observed",
                "revenue_potential": "unknown",
                "effort_required": "moderate",
                "capital_required": "low",
                "distribution_advantage": "unknown",
                "skill_fit": "medium",
                "family_fit": "review",
                "reputation_fit": "review",
                "values_fit": "review",
                "durability": "unknown",
                "automation_potential": "medium",
                "downside_risk": "moderate",
            }
            report = self._fisk_opportunity_report(
                title=experiment,
                category="experiment",
                summary="Existing experiment kept in the lane so JARVIS can track, revisit, and stage follow-up instead of claiming execution already happened.",
                source="wealth-summary",
                market_reality="The experiment exists in prior records, but its economics and operating burden still need clearer tracking.",
                who_pays="Under review.",
                why_they_pay="Under review.",
                current_alternatives=["Status quo job income", "Other low-margin side income attempts"],
                where_money_flows="Money only matters here if the experiment turns into a repeatable transaction path.",
                who_controls_distribution="Still unclear.",
                leverage_point="The experiment may reveal whether distribution or packaging is the constraint.",
                advantage="Existing familiarity from prior runs.",
                reusable_asset="Prior experiment notes and synthesis",
                ownable_channel="Still to be defined",
                compounding_vector="Possible if the experiment reveals a reusable funnel",
                revenue="Unknown",
                startup_cost="Low",
                operating_effort="Moderate",
                time_to_first_dollar="Unknown",
                time_to_meaningful_revenue="Unknown",
                scalability="Unknown",
                main_downside="A high-maintenance experiment can masquerade as passive income.",
                hidden_labor="Follow-up, ops, and distribution",
                capital_risk="Low",
                reputation_risk="Medium",
                family_time_cost="Needs Pepper review",
                confidence="medium",
                score=score,
                recommendation="Validate",
                next_action="review-experiment",
                approval_needed=True,
            )
            record = self._upsert_passive_income_candidate(
                actor=actor,
                lane=lane,
                title=experiment,
                summary=report["summary"],
                candidate_type="experiment",
                status="experiment_planned",
                confidence="medium",
                next_action="review-experiment",
                evidence=[{"source": "wealth-summary", "detail": experiment, "kind": "experiment"}],
                observed=[f"Stored experiment: {experiment}"],
                inferred=["The experiment may deserve another pass, but the operating burden is still unclear."],
                prepared=["Prepared a Fisk opportunity report.", "Prepared review-ready experiment framing."],
                recommended=["Review for repeatability before scaling.", "Decide whether this is a business system or just another job."],
                requires_approval=["Any spend, public launch, or third-party dependency."],
                not_done=["Did not execute the experiment.", "Did not prove repeatable distribution."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])

        for opportunity in pipeline_opportunities[:3]:
            title = _clean_text(opportunity.get("name") or opportunity.get("title") or opportunity.get("opportunity"))
            if not title:
                continue
            summary = _clean_text(opportunity.get("next_step") or opportunity.get("summary") or opportunity.get("note"))
            score = {
                "market_demand": "unknown",
                "revenue_potential": "unknown",
                "effort_required": "unknown",
                "capital_required": "unknown",
                "distribution_advantage": "unknown",
                "skill_fit": "review",
                "family_fit": "review",
                "reputation_fit": "review",
                "values_fit": "review",
                "durability": "unknown",
                "automation_potential": "unknown",
                "downside_risk": "unknown",
            }
            report = self._fisk_opportunity_report(
                title=title,
                category="pipeline-opportunity",
                summary=summary or "Pipeline opportunity bridged into the autonomous workstream for explicit review.",
                source="pipeline-state",
                market_reality="This came from the family portfolio pipeline, so the existence of the signal is real, but its passive-income quality is still unproven.",
                who_pays="Needs market mapping.",
                why_they_pay="Needs market mapping.",
                current_alternatives=["Current portfolio alternatives"],
                where_money_flows="Pipeline signal exists, but the cash capture point is not yet bounded.",
                who_controls_distribution="Unknown",
                leverage_point="May already have momentum if it came from the pipeline instead of a blank-sheet idea.",
                advantage="Existing internal interest or prior signal",
                reusable_asset="Prior catalyst or project notes",
                ownable_channel="Unknown",
                compounding_vector="Unknown",
                revenue="Unknown",
                startup_cost="Unknown",
                operating_effort="Unknown",
                time_to_first_dollar="Unknown",
                time_to_meaningful_revenue="Unknown",
                scalability="Unknown",
                main_downside="Can become portfolio noise without a clear demand path.",
                hidden_labor="Follow-through burden still unclear.",
                capital_risk="Unknown",
                reputation_risk="Unknown",
                family_time_cost="Needs Pepper review",
                confidence="low",
                score=score,
                recommendation="Watch",
                next_action="review-pipeline-fit",
                approval_needed=True,
            )
            record = self._upsert_passive_income_candidate(
                actor=actor,
                lane=lane,
                title=title,
                summary=report["summary"],
                candidate_type="market-map",
                status="screened",
                confidence="low",
                next_action="review-pipeline-fit",
                evidence=[{"source": "pipeline-state", "detail": title, "kind": "pipeline-opportunity"}],
                observed=[f"Pipeline opportunity observed: {title}"],
                inferred=["The signal is real, but its passive-income fit is not yet clear."],
                prepared=["Prepared a Fisk opportunity report for pipeline review."],
                recommended=["Map the buyers, margin path, and distribution control before committing attention."],
                requires_approval=["Any capital, public messaging, or external commitments."],
                not_done=["Did not validate the buyer.", "Did not prove passive-income economics."],
                report=report,
                metadata={"pipeline_status": _clean_text(opportunity.get("status"))},
            )
            items.append(record)
            staged_titles.append(record["title"])

        if not items:
            goals = dict(finance_state.get("goals") or {})
            target = goals.get("passive_income_target_monthly")
            current = goals.get("current_passive_income_monthly")
            summary = "No passive-income theses are staged yet. The first autonomous move is to build and rank an explicit shortlist."
            if target or current:
                summary += f" Current monthly passive income is {current or 'unknown'} against a target of {target or 'unknown'}."
            report = self._fisk_opportunity_report(
                title="Build the first passive-income shortlist",
                category="validation-gap",
                summary=summary,
                source="finance-state",
                market_reality="There is interest in passive income, but not enough specific opportunity evidence is staged yet.",
                who_pays="Unknown",
                why_they_pay="Unknown",
                current_alternatives=["Unstructured idea capture"],
                where_money_flows="Unknown",
                who_controls_distribution="Unknown",
                leverage_point="The first leverage is disciplined screening, not more idea generation.",
                advantage="A clear framework can prevent fantasy and wasted effort.",
                reusable_asset="Current frameworks and past notes",
                ownable_channel="Unknown",
                compounding_vector="Shortlist discipline improves future decisions.",
                revenue="Unknown",
                startup_cost="Low",
                operating_effort="Low",
                time_to_first_dollar="Unknown",
                time_to_meaningful_revenue="Unknown",
                scalability="Framework-level",
                main_downside="Staying abstract too long.",
                hidden_labor="No hidden labor yet because the offer does not exist.",
                capital_risk="Low",
                reputation_risk="Low",
                family_time_cost="Low",
                confidence="high",
                score={
                    "market_demand": "unknown",
                    "revenue_potential": "unknown",
                    "effort_required": "low",
                    "capital_required": "low",
                    "distribution_advantage": "unknown",
                    "skill_fit": "medium",
                    "family_fit": "high",
                    "reputation_fit": "high",
                    "values_fit": "high",
                    "durability": "high",
                    "automation_potential": "high",
                    "downside_risk": "low",
                },
                recommendation="Research",
                next_action="create-shortlist",
                approval_needed=True,
            )
            record = self._upsert_passive_income_candidate(
                actor=actor,
                lane=lane,
                title="Build the first passive-income shortlist",
                summary=summary,
                candidate_type="validation-gap",
                status="discovered",
                confidence="high",
                next_action="create-shortlist",
                evidence=[{"source": "finance-state", "detail": "Passive-income lane has goals but no staged theses yet.", "kind": "gap"}],
                observed=["No passive-income theses are currently staged in the lane."],
                inferred=["The highest-leverage move is to create a disciplined shortlist instead of chasing vague ideas."],
                prepared=["Prepared a framework-gap report."],
                recommended=["Build and rank the first shortlist."],
                requires_approval=["Any move beyond research and ranking."],
                not_done=["Did not validate an offer.", "Did not choose a channel."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])
        return items, staged_titles, evidence_counts

    def _run_market_intelligence_lane(
        self,
        *,
        actor: str,
        lane: dict[str, Any],
        finance_state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
        items: list[dict[str, Any]] = []
        staged_titles: list[str] = []
        market = dict(finance_state.get("market_intelligence") or {})
        watchlist = [item for item in list(market.get("watchlist", [])) if isinstance(item, dict)]
        theses = [item for item in list(market.get("theses", [])) if isinstance(item, dict)]
        catalysts = [item for item in list(market.get("catalysts", [])) if isinstance(item, dict)]
        evidence_counts = {
            "watchlist_items": len(watchlist),
            "theses": len(theses),
            "catalysts": len(catalysts),
        }

        for item in watchlist[:6]:
            ticker = _clean_text(item.get("ticker") or item.get("asset"))
            if not ticker:
                continue
            thesis = _clean_text(item.get("thesis"))
            recommendation = _clean_text(item.get("recommendation")) or "Watch"
            report = _market_report_template()
            report.update(
                {
                    "ticker_or_asset": ticker,
                    "sector": _clean_text(item.get("sector")),
                    "time_horizon": _clean_text(item.get("time_horizon")) or "6-12 months",
                    "current_price_context": _clean_text(item.get("price_context")) or "No live market feed is wired yet; current price context is manual or absent.",
                    "thesis": thesis or f"Watch {ticker} until the thesis is better bounded.",
                    "why_this_asset_matters": _clean_text(item.get("why_it_matters")) or f"{ticker} is on the watchlist because it may matter to Chris's capital growth goals.",
                    "market_belief": _clean_text(item.get("market_belief")) or "Market belief not yet written down.",
                    "what_fisk_may_be_missing": _clean_text(item.get("variant_view")) or "Fisk has not yet identified a strong variant perception.",
                    "catalysts": {
                        "near_term": _clean_list(item.get("near_term_catalysts", []), limit=6),
                        "medium_term": _clean_list(item.get("medium_term_catalysts", []), limit=6),
                        "long_term": _clean_list(item.get("long_term_catalysts", []), limit=6),
                    },
                    "prediction": {
                        "base_case": _clean_text(item.get("base_case")) or "Base case not yet written.",
                        "bull_case": _clean_text(item.get("bull_case")) or "Bull case not yet written.",
                        "bear_case": _clean_text(item.get("bear_case")) or "Bear case not yet written.",
                        "confidence": _clean_text(item.get("confidence")) or "low",
                        "what_would_change_the_view": _clean_text(item.get("invalidation")) or "Invalidation point not yet recorded.",
                    },
                    "recommendation": recommendation,
                    "action_status": "No action taken",
                    "approval_required": True,
                }
            )
            record = self._upsert_market_candidate(
                actor=actor,
                lane=lane,
                title=f"{ticker} watchlist",
                summary=f"Watchlist thesis for {ticker} staged for Fisk review without any trade execution.",
                candidate_type="watchlist-candidate",
                status="watchlist",
                confidence=_clean_text(item.get("confidence")) or "low",
                next_action="build-thesis",
                evidence=[{"source": "finance-state.market_intelligence.watchlist", "detail": ticker, "kind": "watchlist"}],
                observed=[f"Watchlist entry observed for {ticker}.", f"Sector: {_clean_text(item.get('sector')) or 'unknown'}"],
                inferred=["The asset is important enough to watch, but the thesis still needs discipline and explicit invalidation points."],
                prepared=["Prepared a Fisk market report.", "Prepared guardrail routing metadata."],
                recommended=[f"Keep {ticker} on watch, not in motion, until the thesis is written more sharply."],
                requires_approval=["Any position initiation or allocation decision."],
                not_done=["Did not execute a trade.", "Did not verify live price or brokerage state."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])

        for item in theses[:6]:
            ticker = _clean_text(item.get("ticker") or item.get("asset"))
            if not ticker:
                continue
            recommendation = _clean_text(item.get("recommendation")) or "Watch"
            report = _market_report_template()
            report.update(
                {
                    "ticker_or_asset": ticker,
                    "sector": _clean_text(item.get("sector")),
                    "time_horizon": _clean_text(item.get("time_horizon")) or "6-12 months",
                    "current_price_context": _clean_text(item.get("current_price_context")),
                    "thesis": _clean_text(item.get("thesis")) or f"Thesis for {ticker} has been staged, but not yet challenged enough.",
                    "why_this_asset_matters": _clean_text(item.get("why_this_asset_matters")) or f"{ticker} may matter because it intersects Chris's long-term capital growth lens.",
                    "market_belief": _clean_text(item.get("market_belief")),
                    "what_fisk_may_be_missing": _clean_text(item.get("what_fisk_may_be_missing")),
                    "fundamentals": {
                        "revenue_trend": _clean_text(item.get("revenue_trend")),
                        "earnings_trend": _clean_text(item.get("earnings_trend")),
                        "margins": _clean_text(item.get("margins")),
                        "debt": _clean_text(item.get("debt")),
                        "cash_flow": _clean_text(item.get("cash_flow")),
                        "competitive_position": _clean_text(item.get("competitive_position")),
                    },
                    "valuation": {
                        "current_valuation": _clean_text(item.get("current_valuation")),
                        "historical_comparison": _clean_text(item.get("historical_comparison")),
                        "peer_comparison": _clean_text(item.get("peer_comparison")),
                        "valuation_risk": _clean_text(item.get("valuation_risk")),
                    },
                    "catalysts": {
                        "near_term": _clean_list(item.get("near_term_catalysts", []), limit=6),
                        "medium_term": _clean_list(item.get("medium_term_catalysts", []), limit=6),
                        "long_term": _clean_list(item.get("long_term_catalysts", []), limit=6),
                    },
                    "risks": {
                        "business_risk": _clean_text(item.get("business_risk")),
                        "market_risk": _clean_text(item.get("market_risk")),
                        "valuation_risk": _clean_text(item.get("valuation_risk")),
                        "regulatory_risk": _clean_text(item.get("regulatory_risk")),
                        "execution_risk": _clean_text(item.get("execution_risk")),
                    },
                    "prediction": {
                        "base_case": _clean_text(item.get("base_case")) or "Base case not yet written.",
                        "bull_case": _clean_text(item.get("bull_case")) or "Bull case not yet written.",
                        "bear_case": _clean_text(item.get("bear_case")) or "Bear case not yet written.",
                        "confidence": _clean_text(item.get("confidence")) or "low",
                        "what_would_change_the_view": _clean_text(item.get("what_would_change_the_view")) or _clean_text(item.get("invalidation")),
                    },
                    "recommendation": recommendation,
                    "action_status": "Staged for approval" if recommendation.lower() in {"buy candidate", "buy-candidate", "trim candidate", "trim-candidate", "exit candidate", "exit-candidate"} else "No action taken",
                    "approval_required": True,
                }
            )
            status = "thesis_built"
            if recommendation.lower() in {"buy candidate", "buy-candidate"}:
                status = "buy_candidate"
            elif recommendation.lower() == "hold":
                status = "hold"
            elif recommendation.lower() in {"trim candidate", "trim-candidate"}:
                status = "trim_candidate"
            elif recommendation.lower() in {"exit candidate", "exit-candidate"}:
                status = "exit_candidate"
            record = self._upsert_market_candidate(
                actor=actor,
                lane=lane,
                title=f"{ticker} thesis",
                summary=f"Market thesis for {ticker} staged with probabilistic cases and explicit approval posture.",
                candidate_type="thesis",
                status=status,
                confidence=_clean_text(item.get("confidence")) or "low",
                next_action="review-thesis",
                evidence=[{"source": "finance-state.market_intelligence.theses", "detail": ticker, "kind": "thesis"}],
                observed=[f"Market thesis stored for {ticker}."],
                inferred=["The thesis may be useful, but it still needs Nebula, Pepper, Watcher, and compliance review before action."],
                prepared=["Prepared a Fisk market report.", "Prepared staged recommendation posture."],
                recommended=[f"Treat {ticker} as {recommendation or 'Watch'} until the thesis survives review."],
                requires_approval=["Any real position change or capital deployment."],
                not_done=["Did not move money.", "Did not place a trade.", "Did not verify brokerage exposure."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])

        for item in catalysts[:6]:
            ticker = _clean_text(item.get("ticker") or item.get("asset"))
            if not ticker:
                continue
            catalyst = _clean_text(item.get("catalyst")) or "Catalyst update"
            report = _market_report_template()
            report.update(
                {
                    "ticker_or_asset": ticker,
                    "sector": _clean_text(item.get("sector")),
                    "time_horizon": _clean_text(item.get("time_horizon")) or "near-term catalyst",
                    "thesis": _clean_text(item.get("thesis")) or f"{ticker} has a catalyst worth monitoring.",
                    "why_this_asset_matters": _clean_text(item.get("why_this_asset_matters")) or "Catalyst may change the quality of the watchlist thesis.",
                    "catalysts": {
                        "near_term": [catalyst],
                        "medium_term": [],
                        "long_term": [],
                    },
                    "prediction": {
                        "base_case": _clean_text(item.get("base_case")) or "Catalyst likely changes attention, not certainty.",
                        "bull_case": _clean_text(item.get("bull_case")),
                        "bear_case": _clean_text(item.get("bear_case")),
                        "confidence": _clean_text(item.get("confidence")) or "low",
                        "what_would_change_the_view": _clean_text(item.get("invalidation")),
                    },
                    "recommendation": _clean_text(item.get("recommendation")) or "Research",
                    "action_status": "No action taken",
                    "approval_required": True,
                }
            )
            record = self._upsert_market_candidate(
                actor=actor,
                lane=lane,
                title=f"{ticker} catalyst",
                summary=f"Catalyst alert for {ticker} staged for review instead of treated as a trading signal.",
                candidate_type="catalyst-alert",
                status="researching",
                confidence=_clean_text(item.get("confidence")) or "low",
                next_action="review-catalyst",
                evidence=[{"source": "finance-state.market_intelligence.catalysts", "detail": catalyst, "kind": "catalyst"}],
                observed=[f"Catalyst tracked for {ticker}: {catalyst}"],
                inferred=["The catalyst may matter, but catalysts are not trades by themselves."],
                prepared=["Prepared a catalyst-focused market report."],
                recommended=["Revisit the thesis around the catalyst rather than chasing it emotionally."],
                requires_approval=["Any action involving real capital."],
                not_done=["Did not act on momentum.", "Did not chase breaking news."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])

        if not items:
            report = _market_report_template()
            report.update(
                {
                    "ticker_or_asset": "No watchlist yet",
                    "time_horizon": "N/A",
                    "thesis": "The market-intelligence lane needs a first watchlist before it can stage disciplined theses.",
                    "why_this_asset_matters": "A disciplined watchlist is the first filter against hype and undirected market attention.",
                    "recommendation": "Research",
                    "action_status": "No action taken",
                    "approval_required": True,
                }
            )
            record = self._upsert_market_candidate(
                actor=actor,
                lane=lane,
                title="Build the first market watchlist",
                summary="No market-intelligence watchlist or thesis objects are staged yet. The first move is to create a bounded watchlist and thesis discipline.",
                candidate_type="watchlist-candidate",
                status="screened",
                confidence="high",
                next_action="build-watchlist",
                evidence=[{"source": "finance-state", "detail": "No market-intelligence records are currently staged.", "kind": "gap"}],
                observed=["No watchlist, thesis, or catalyst objects are currently staged."],
                inferred=["The right next move is bounded market structure, not random ticker fascination."],
                prepared=["Prepared a framework-gap market report."],
                recommended=["Create the first watchlist and thesis template before doing more forecasting."],
                requires_approval=["Any later position initiation."],
                not_done=["Did not create a trade.", "Did not assume live market data exists."],
                report=report,
            )
            items.append(record)
            staged_titles.append(record["title"])
        return items, staged_titles, evidence_counts

    def update_item_status(
        self,
        *,
        item_id: str,
        actor: str,
        status: str,
        note: str = "",
        next_action: str = "",
        reviewer: str = "",
    ) -> dict[str, Any]:
        existing = self.store.get_item(item_id)
        if existing is None:
            raise KeyError("Workstream item not found.")
        updated = dict(existing)
        lane = self.lane(str(updated.get("lane_id", "")).strip()) or {}
        updated["actor"] = actor
        updated["status"] = _clean_text(status) or updated.get("status", "reviewed")
        projection = _status_projection(updated["status"])
        updated["truth_state"] = projection["action_status"]
        updated["item_status"] = projection["item_status"]
        updated["action_status"] = projection["action_status"]
        updated["verification_status"] = _normalize_truth_value(updated.get("verification_status"), default=projection["verification_status"])
        updated["blocked_reason"] = _normalize_blocked_reason(updated.get("blocked_reason"))
        updated["updated_at"] = _now_iso()
        updated["last_reviewed_at"] = _now_iso()
        if _clean_text(note):
            updated.setdefault("metadata", {})
            updated["metadata"]["review_note"] = _clean_text(note)
        if _clean_text(next_action):
            updated["next_action"] = _clean_text(next_action)
            updated["recommended_action"] = _clean_text(next_action)
        if _clean_text(reviewer):
            reviews = [dict(entry) for entry in list(updated.get("guardrail_reviews", [])) if isinstance(entry, dict)]
            reviews.append(
                {
                    "reviewer": _clean_text(reviewer),
                    "status": updated["status"],
                    "note": _clean_text(note),
                    "timestamp": _now_iso(),
                }
            )
            updated["guardrail_reviews"] = reviews
            self._record_artifact(
                actor=actor,
                lane=lane,
                item_id=item_id,
                artifact_type="guardrail-review",
                title=f"{_clean_text(reviewer)} review",
                summary=_clean_text(note) or f"{_clean_text(reviewer)} updated {item_id}.",
                payload={"reviewer": _clean_text(reviewer), "status": updated["status"]},
            )
        if updated["status"] in {"approved", "dismissed"}:
            updated["approval_status"] = updated["status"]
        self.store.upsert_item(updated)
        self._ensure_approval(actor=actor, lane=lane, item=updated)
        queue = self._ensure_queue_entry(actor=actor, lane=lane, item=updated)
        queue["status"] = "closed" if updated["status"] in {"approved", "dismissed", "closed", "rejected"} else queue.get("status", "pending")
        queue["approval_status"] = updated.get("approval_status", queue.get("approval_status", ""))
        queue["updated_at"] = _now_iso()
        self.store.upsert_queue_entry(queue)
        approval = next((entry for entry in self.list_approvals(item_id=item_id, limit=1)), None)
        if approval:
            approval["status"] = _normalize_approval_status(updated.get("approval_status"), default=approval.get("status", "pending"))
            approval["updated_at"] = _now_iso()
            self.store.upsert_approval(approval)
        return self._attach_related_records(updated)

    def approve_item(self, *, item_id: str, actor: str, note: str = "") -> dict[str, Any]:
        return self.update_item_status(
            item_id=item_id,
            actor=actor,
            status="approved",
            note=note or "Approved for the next bounded step.",
            next_action="advance",
            reviewer="Chris",
        )

    def dismiss_item(self, *, item_id: str, actor: str, note: str = "") -> dict[str, Any]:
        return self.update_item_status(
            item_id=item_id,
            actor=actor,
            status="dismissed",
            note=note or "Dismissed from the current workstream queue.",
            next_action="archive",
            reviewer="Chris",
        )

    def route_item(self, *, item_id: str, actor: str, route_to: str, note: str = "") -> dict[str, Any]:
        existing = self.store.get_item(item_id)
        if existing is None:
            raise KeyError("Workstream item not found.")
        lane = self.lane(str(existing.get("lane_id", "")).strip()) or {}
        updated = self.update_item_status(
            item_id=item_id,
            actor=actor,
            status=str(existing.get("status", "researching")).strip() or "researching",
            note=note or f"Routed to {route_to} for deeper review.",
            next_action=f"route-to-{_clean_text(route_to).lower().replace(' ', '-')}",
            reviewer=route_to,
        )
        queue = next((entry for entry in self.list_queue_entries(item_id=item_id, limit=1)), {})
        if queue:
            queue["status"] = "pending"
            queue["queue_type"] = "route"
            queue["route_target"] = _clean_text(route_to)
            queue["updated_at"] = _now_iso()
            self.store.upsert_queue_entry(queue)
        self._record_artifact(
            actor=actor,
            lane=lane,
            item_id=item_id,
            artifact_type="summary-brief",
            title=f"Routed to {_clean_text(route_to)}",
            summary=note or f"Requested deeper review from {route_to}.",
            payload={"route_to": _clean_text(route_to)},
        )
        return self._attach_related_records(updated)

    def summary(self, *, actor: str, lane_id: str = "") -> dict[str, Any]:
        lanes = self.lanes()
        active_lane_ids = {_clean_text(lane.get("lane_id")) for lane in lanes}
        filtered_lanes = [lane for lane in lanes if not lane_id or _clean_text(lane.get("lane_id")) == _clean_text(lane_id)]
        items = [self._attach_related_records(item) for item in self.list_items(actor=actor, lane_id=lane_id, limit=120)]
        runs = self.list_runs(actor=actor, lane_id=lane_id, limit=20)
        artifacts = self.list_artifacts(actor=actor, lane_id=lane_id, limit=120)
        approvals = self.list_approvals(actor=actor, lane_id=lane_id, limit=120)
        queue_entries = self.list_queue_entries(actor=actor, lane_id=lane_id, limit=120)
        status_counts: dict[str, int] = {}
        for item in items:
            key = _clean_text(item.get("status")) or "unknown"
            status_counts[key] = status_counts.get(key, 0) + 1
        lane_readiness = [
            self.lane_readiness(actor=actor, lane_id=_clean_text(lane.get("lane_id")), source="manual")
            for lane in filtered_lanes
            if _clean_text(lane.get("lane_id"))
        ]
        return {
            "actor": actor,
            "generated_at": _now_iso(),
            "framework": {
                "lane_count": len(active_lane_ids),
                "proof_of_concept_lane": "passive-income",
                "mission": _clean_text(self.state().get("mission")),
            },
            "lanes": filtered_lanes,
            "summary": {
                "tracked_items": len(items),
                "recent_runs": len(runs),
                "staged_items": status_counts.get("staged_for_approval", 0) + status_counts.get("experiment_planned", 0),
                "researched_items": status_counts.get("researching", 0),
                "planned_items": status_counts.get("discovered", 0) + status_counts.get("screened", 0),
                "approved_items": status_counts.get("approved", 0),
                "queue_entries": len(queue_entries),
                "pending_approvals": len([entry for entry in approvals if _clean_text(entry.get("status")).lower() == "pending"]),
                "blocked_items": len([entry for entry in items if _clean_text(entry.get("item_status")).lower() == "blocked"]),
            },
            "status_counts": status_counts,
            "lane_readiness": lane_readiness,
            "recent_runs": runs,
            "artifacts": artifacts[:24],
            "approvals": approvals[:24],
            "queue": queue_entries[:24],
            "items": items[:24],
        }
