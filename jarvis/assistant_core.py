from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


ASSISTANT_CORE_PATH = Path.cwd() / "data" / "settings" / "assistant_core.json"
ACTIVE_NOTIFICATION_STATUSES = {"unseen", "surfaced", "opened"}
TERMINAL_NOTIFICATION_STATUSES = {"acted", "ignored", "expired"}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _parse_iso_datetime(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalized_label(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _is_low_signal_world_label(label: str, node_type: str) -> bool:
    normalized = _normalized_label(label)
    if not normalized:
        return True
    if node_type == "device":
        if "browser" in normalized or normalized in {"device", "unknown device", "macos"}:
            return True
    return False


def _select_signal_labels(ids: list[str], labels: dict[str, str], node_types: dict[str, str], *, limit: int = 8) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for item_id in ids:
        label = str(labels.get(item_id, item_id)).strip()
        node_type = str(node_types.get(item_id, "")).strip().lower()
        if _is_low_signal_world_label(label, node_type):
            continue
        normalized = _normalized_label(label)
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(label)
        if len(results) >= limit:
            break
    return results


def _merge_unique_labels(existing: list[str], incoming: list[str], *, limit: int = 8) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for raw in list(existing) + list(incoming):
        label = str(raw or "").strip()
        normalized = _normalized_label(label)
        if not label or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(label)
        if len(merged) >= limit:
            break
    return merged


def _world_count_event_allowed(scope: str, key: str, delta_value: int) -> bool:
    magnitude = abs(int(delta_value or 0))
    normalized_scope = str(scope or "").strip().lower()
    normalized_key = str(key or "").strip().lower()
    if magnitude <= 0:
        return False
    if normalized_scope == "summary" and normalized_key in {"devices", "notifications", "edges"} and magnitude <= 1:
        return False
    if normalized_scope == "entity_counts" and normalized_key in {"device", "notification"} and magnitude <= 1:
        return False
    if normalized_scope == "edge_counts" and normalized_key in {"owns", "located-in", "needs-attention"} and magnitude <= 1:
        return False
    return True


def _world_event_significance(scope: str, key: str, delta_value: int) -> str:
    magnitude = abs(int(delta_value or 0))
    normalized_scope = str(scope or "").strip().lower()
    normalized_key = str(key or "").strip().lower()
    if magnitude >= 4:
        return "high"
    if normalized_scope == "entity_counts" and normalized_key in {"risk", "lead", "asset", "approval"} and magnitude >= 1:
        return "high"
    if normalized_scope == "edge_counts" and normalized_key in {"at-risk-from", "must-decide", "belongs-to-lane"} and magnitude >= 1:
        return "high"
    if magnitude >= 2:
        return "medium"
    return "low"


def _world_event_title(scope: str, key: str, delta_value: int) -> str:
    direction = "up" if int(delta_value or 0) > 0 else "down"
    words = str(key or "").strip().replace("-", " ").replace("_", " ")
    if scope == "summary":
        return f"Summary {words} shifted {direction}"
    if scope == "entity_counts":
        return f"World graph {words} count shifted {direction}"
    if scope == "edge_counts":
        return f"World graph {words} relationship count shifted {direction}"
    return f"World graph {words} shifted {direction}"


def _world_event_detail(scope: str, key: str, delta_value: int) -> str:
    direction = "increased" if int(delta_value or 0) > 0 else "decreased"
    words = str(key or "").strip().replace("-", " ").replace("_", " ")
    return f"{scope.replace('_', ' ')} {words} {direction} by {abs(int(delta_value or 0))}."


def _world_event_signature(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type", "")).strip().lower()
    actor = str(event.get("actor", "")).strip().lower()
    scope = str(event.get("scope", "")).strip().lower()
    key = str(event.get("key", "")).strip().lower()
    direction = str(event.get("direction", "")).strip().lower()
    labels = [
        _normalized_label(label)
        for label in list(event.get("labels", []))
        if _normalized_label(label)
    ]
    if labels:
        return "|".join([actor, event_type, scope, key, direction, ",".join(sorted(labels))])
    return "|".join([actor, event_type, scope, key, direction, str(abs(int(event.get("delta_value", 0) or 0)))])


def _upsert_world_event(events: list[dict[str, Any]], candidate: dict[str, Any], *, dedupe_window_minutes: int = 180) -> None:
    now = _now_utc()
    signature = _world_event_signature(candidate)
    candidate["signature"] = signature
    candidate.setdefault("occurrence_count", 1)
    candidate.setdefault("first_seen_at", candidate.get("captured_at", now.isoformat()))
    candidate.setdefault("last_seen_at", candidate.get("captured_at", now.isoformat()))
    window_start = now - timedelta(minutes=max(int(dedupe_window_minutes or 0), 1))
    for item in reversed(events):
        if not isinstance(item, dict):
            continue
        if str(item.get("signature", "")).strip() != signature:
            continue
        last_seen = _parse_iso_datetime(str(item.get("last_seen_at", "")) or str(item.get("captured_at", "")))
        if last_seen is None or last_seen < window_start:
            break
        item["last_seen_at"] = candidate["last_seen_at"]
        item["captured_at"] = candidate["captured_at"]
        item["occurrence_count"] = int(item.get("occurrence_count", 1) or 1) + 1
        item["significance"] = candidate.get("significance", item.get("significance", "medium"))
        item["delta_value"] = candidate.get("delta_value", item.get("delta_value", 0))
        if "count_delta" in candidate:
            item["count_delta"] = dict(candidate.get("count_delta") or {})
        if candidate.get("labels"):
            item["labels"] = _merge_unique_labels(list(item.get("labels", [])), list(candidate.get("labels", [])))
        if candidate.get("added_labels"):
            item["added_labels"] = _merge_unique_labels(list(item.get("added_labels", [])), list(candidate.get("added_labels", [])))
        if candidate.get("removed_labels"):
            item["removed_labels"] = _merge_unique_labels(list(item.get("removed_labels", [])), list(candidate.get("removed_labels", [])))
        if candidate.get("summary"):
            item["summary"] = dict(candidate.get("summary") or {})
        return
    events.append(candidate)


def _normalize_world_event(item: dict[str, Any]) -> dict[str, Any]:
    event = dict(item)
    added_labels = [str(label).strip() for label in list(event.get("added_labels", [])) if str(label).strip()]
    removed_labels = [str(label).strip() for label in list(event.get("removed_labels", [])) if str(label).strip()]
    labels = [str(label).strip() for label in list(event.get("labels", [])) if str(label).strip()]
    if not labels:
        labels = _merge_unique_labels(added_labels, removed_labels)
    event_type = str(event.get("event_type", "")).strip()
    if not event_type:
        if added_labels:
            event_type = "world.signal.added"
        elif removed_labels:
            event_type = "world.signal.removed"
        else:
            event_type = "world.summary.changed"
    category = str(event.get("category", "")).strip()
    if not category:
        category = "signal" if added_labels or removed_labels else "count-change"
    scope = str(event.get("scope", "")).strip()
    if not scope:
        scope = "labels" if added_labels or removed_labels else "summary"
    key = str(event.get("key", "")).strip()
    if not key:
        key = "added" if added_labels else ("removed" if removed_labels else "summary")
    direction = str(event.get("direction", "")).strip()
    if not direction:
        direction = "up" if added_labels else ("down" if removed_labels else "changed")
    significance = str(event.get("significance", "")).strip()
    if not significance:
        if added_labels or removed_labels:
            significance = "medium"
        else:
            count_delta = dict(event.get("count_delta", {})) if isinstance(event.get("count_delta", {}), dict) else {}
            delta_value = next((int(value) for value in count_delta.values() if isinstance(value, (int, float))), 0)
            significance = _world_event_significance(scope, key, delta_value)
    event["labels"] = labels
    event["added_labels"] = added_labels
    event["removed_labels"] = removed_labels
    event["event_type"] = event_type
    event["category"] = category
    event["scope"] = scope
    event["key"] = key
    event["direction"] = direction
    event["significance"] = significance
    event["occurrence_count"] = int(event.get("occurrence_count", 1) or 1)
    event["first_seen_at"] = str(event.get("first_seen_at", "") or event.get("captured_at", "")).strip()
    event["last_seen_at"] = str(event.get("last_seen_at", "") or event.get("captured_at", "")).strip()
    if not str(event.get("title", "")).strip():
        event["title"] = "New world signals detected" if added_labels else (
            "World signals fell away" if removed_labels else _world_event_title(scope, key, 0)
        )
    if not str(event.get("detail", "")).strip():
        event["detail"] = "World-state delta captured from the latest graph snapshot."
    event["signature"] = str(event.get("signature", "")).strip() or _world_event_signature(event)
    return event


def _normalize_notification_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "unread": "unseen",
        "read": "opened",
        "delivered": "surfaced",
        "done": "acted",
        "dismissed": "ignored",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in ACTIVE_NOTIFICATION_STATUSES or normalized in TERMINAL_NOTIFICATION_STATUSES:
        return normalized
    return "opened"


@dataclass(slots=True)
class AssistantCoreStore:
    path: Path = ASSISTANT_CORE_PATH

    def load(self) -> dict[str, Any]:
        default = {
            "deferred": {},
            "history": [],
            "sweeps": {},
            "surface_history": [],
            "notifications": [],
            "outcomes": [],
            "world_graphs": {},
            "world_events": [],
            "surface_snapshots": {},
            "service_runtime": {},
            "service_runtime_history": [],
            "cadence_history": [],
        }
        if not self.path.exists():
            return default
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("deferred", {})
        payload.setdefault("history", [])
        payload.setdefault("sweeps", {})
        payload.setdefault("surface_history", [])
        payload.setdefault("notifications", [])
        payload.setdefault("outcomes", [])
        payload.setdefault("world_graphs", {})
        payload.setdefault("world_events", [])
        payload.setdefault("surface_snapshots", {})
        payload.setdefault("service_runtime", {})
        payload.setdefault("service_runtime_history", [])
        payload.setdefault("cadence_history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def deferred_record(self, item_key: str) -> dict[str, Any] | None:
        state = self.load()
        record = state.get("deferred", {}).get(item_key)
        return dict(record) if isinstance(record, dict) else None

    def set_deferred(self, item_key: str, *, until: str, actor: str, reason: str = "") -> dict[str, Any]:
        state = self.load()
        deferred = dict(state.get("deferred", {}))
        record = {
            "item_key": item_key,
            "until": until,
            "actor": actor,
            "reason": reason.strip(),
            "updated_at": _now_utc().isoformat(),
        }
        deferred[item_key] = record
        state["deferred"] = deferred
        history = list(state.get("history", []))
        history.append({"type": "deferred", **record})
        state["history"] = history[-80:]
        self.save(state)
        return record

    def clear_deferred(self, item_key: str) -> bool:
        state = self.load()
        deferred = dict(state.get("deferred", {}))
        if item_key not in deferred:
            return False
        record = deferred.pop(item_key)
        state["deferred"] = deferred
        history = list(state.get("history", []))
        history.append({"type": "cleared", **record, "cleared_at": _now_utc().isoformat()})
        state["history"] = history[-80:]
        self.save(state)
        return True

    def sweep_record(self, actor: str) -> dict[str, Any] | None:
        state = self.load()
        sweeps = state.get("sweeps", {})
        record = sweeps.get(actor.strip().lower(), {})
        return dict(record) if isinstance(record, dict) else None

    def world_graph_record(self, actor: str) -> dict[str, Any] | None:
        state = self.load()
        graphs = state.get("world_graphs", {})
        record = graphs.get(actor.strip().lower(), {})
        return dict(record) if isinstance(record, dict) else None

    def save_world_graph(self, actor: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        graphs = dict(state.get("world_graphs", {}))
        world_events = list(state.get("world_events", []))
        actor_key = actor.strip().lower()
        previous = dict(graphs.get(actor_key, {})) if isinstance(graphs.get(actor_key, {}), dict) else {}
        summary = dict(snapshot.get("summary", {}))
        nodes = list(snapshot.get("nodes", [])) if isinstance(snapshot.get("nodes", []), list) else []
        node_map = {
            str(item.get("id", "")).strip(): str(item.get("label", "") or item.get("type", "") or item.get("id", "")).strip()
            for item in nodes
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        }
        node_types = {
            str(item.get("id", "")).strip(): str(item.get("type", "")).strip().lower()
            for item in nodes
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        }
        node_ids = sorted(node_map.keys())
        previous_ids = set(previous.get("node_ids", [])) if isinstance(previous.get("node_ids", []), list) else set()
        current_ids = set(node_ids)
        added_ids = sorted(current_ids - previous_ids)
        removed_ids = sorted(previous_ids - current_ids)
        previous_summary = dict(previous.get("summary", {})) if isinstance(previous.get("summary", {}), dict) else {}
        current_entity_counts = dict(summary.get("entity_counts", {})) if isinstance(summary.get("entity_counts", {}), dict) else {}
        previous_entity_counts = dict(previous_summary.get("entity_counts", {})) if isinstance(previous_summary.get("entity_counts", {}), dict) else {}
        current_edge_counts = dict(summary.get("edge_counts", {})) if isinstance(summary.get("edge_counts", {}), dict) else {}
        previous_edge_counts = dict(previous_summary.get("edge_counts", {})) if isinstance(previous_summary.get("edge_counts", {}), dict) else {}
        def _summary_int(value: Any) -> int | None:
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            if value in ("", None):
                return 0
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        count_delta: dict[str, int] = {}
        for key in sorted(set(previous_summary) | set(summary)):
            current_value = _summary_int(summary.get(key, 0))
            previous_value = _summary_int(previous_summary.get(key, 0))
            if current_value is None or previous_value is None:
                continue
            delta = current_value - previous_value
            if delta:
                count_delta[key] = delta
        record = {
            "actor": actor.strip(),
            "captured_at": _now_utc().isoformat(),
            "summary": summary,
            "node_ids": node_ids,
            "node_labels": node_map,
            "node_types": node_types,
            "delta": {
                "added_ids": added_ids[:20],
                "removed_ids": removed_ids[:20],
                "added_labels": [],
                "removed_labels": [],
                "count_delta": count_delta,
            },
            "history": list(previous.get("history", []))[-11:],
        }
        previous_labels = previous.get("node_labels", {}) if isinstance(previous.get("node_labels", {}), dict) else {}
        previous_types = previous.get("node_types", {}) if isinstance(previous.get("node_types", {}), dict) else {}
        record["delta"]["added_labels"] = _select_signal_labels(added_ids, node_map, node_types, limit=8)
        record["delta"]["removed_labels"] = _select_signal_labels(removed_ids, previous_labels, previous_types, limit=8)
        record["history"].append(
            {
                "captured_at": record["captured_at"],
                "summary": summary,
                "count_delta": count_delta,
                "added_labels": record["delta"]["added_labels"],
                "removed_labels": record["delta"]["removed_labels"],
            }
        )
        if count_delta or record["delta"]["added_labels"] or record["delta"]["removed_labels"]:
            base_event = {
                "actor": actor.strip(),
                "captured_at": record["captured_at"],
                "summary": summary,
            }
            if record["delta"]["added_labels"]:
                _upsert_world_event(
                    world_events,
                    {
                        **base_event,
                        "event_id": f"world-signal-add-{_now_utc().timestamp()}-{actor_key}",
                        "event_type": "world.signal.added",
                        "category": "signal",
                        "scope": "labels",
                        "key": "added",
                        "direction": "up",
                        "title": "New world signals detected",
                        "detail": "New world-graph labels appeared in the latest snapshot.",
                        "significance": "medium",
                        "labels": list(record["delta"]["added_labels"]),
                        "added_labels": list(record["delta"]["added_labels"]),
                    },
                )
            if record["delta"]["removed_labels"]:
                _upsert_world_event(
                    world_events,
                    {
                        **base_event,
                        "event_id": f"world-signal-remove-{_now_utc().timestamp()}-{actor_key}",
                        "event_type": "world.signal.removed",
                        "category": "signal",
                        "scope": "labels",
                        "key": "removed",
                        "direction": "down",
                        "title": "World signals fell away",
                        "detail": "Previously visible world-graph labels disappeared from the latest snapshot.",
                        "significance": "medium",
                        "labels": list(record["delta"]["removed_labels"]),
                        "removed_labels": list(record["delta"]["removed_labels"]),
                    },
                )
            for scope, current_counts, previous_counts in (
                ("entity_counts", current_entity_counts, previous_entity_counts),
                ("edge_counts", current_edge_counts, previous_edge_counts),
            ):
                for key in sorted(set(current_counts) | set(previous_counts)):
                    current_value = _summary_int(current_counts.get(key, 0))
                    previous_value = _summary_int(previous_counts.get(key, 0))
                    if current_value is None or previous_value is None:
                        continue
                    delta_value = current_value - previous_value
                    if not _world_count_event_allowed(scope, key, delta_value):
                        continue
                    _upsert_world_event(
                        world_events,
                        {
                            **base_event,
                            "event_id": f"world-{scope}-{key}-{_now_utc().timestamp()}-{actor_key}",
                            "event_type": f"world.{scope}.changed",
                            "category": "count-change",
                            "scope": scope,
                            "key": str(key),
                            "direction": "up" if delta_value > 0 else "down",
                            "delta_value": delta_value,
                            "count_delta": {str(key): delta_value},
                            "title": _world_event_title(scope, str(key), delta_value),
                            "detail": _world_event_detail(scope, str(key), delta_value),
                            "significance": _world_event_significance(scope, str(key), delta_value),
                        },
                    )
            for key, delta_value in count_delta.items():
                if key in {"entity_counts", "edge_counts"}:
                    continue
                if not _world_count_event_allowed("summary", key, delta_value):
                    continue
                _upsert_world_event(
                    world_events,
                    {
                        **base_event,
                        "event_id": f"world-summary-{key}-{_now_utc().timestamp()}-{actor_key}",
                        "event_type": "world.summary.changed",
                        "category": "count-change",
                        "scope": "summary",
                        "key": str(key),
                        "direction": "up" if delta_value > 0 else "down",
                        "delta_value": delta_value,
                        "count_delta": {str(key): delta_value},
                        "title": _world_event_title("summary", str(key), delta_value),
                        "detail": _world_event_detail("summary", str(key), delta_value),
                        "significance": _world_event_significance("summary", str(key), delta_value),
                    },
                )
        graphs[actor_key] = record
        state["world_graphs"] = graphs
        state["world_events"] = world_events[-120:]
        self.save(state)
        return record

    def world_graph_history(self, actor: str, *, limit: int = 8) -> list[dict[str, Any]]:
        record = self.world_graph_record(actor) or {}
        history = list(record.get("history", [])) if isinstance(record.get("history", []), list) else []
        return history[-limit:]

    def list_world_events(self, actor: str = "", *, limit: int = 12) -> list[dict[str, Any]]:
        state = self.load()
        events = state.get("world_events", [])
        actor_key = actor.strip().lower()
        results: list[dict[str, Any]] = []
        for item in reversed(events if isinstance(events, list) else []):
            if not isinstance(item, dict):
                continue
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            results.append(_normalize_world_event(item))
            if len(results) >= limit:
                break
        return results

    def surface_snapshot(self, surface_key: str) -> dict[str, Any] | None:
        state = self.load()
        snapshots = state.get("surface_snapshots", {})
        record = snapshots.get(surface_key, {})
        return dict(record) if isinstance(record, dict) else None

    def save_surface_snapshot(self, surface_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        snapshots = dict(state.get("surface_snapshots", {}))
        record = {
            "surface_key": surface_key,
            "saved_at": _now_utc().isoformat(),
            "payload": payload,
        }
        snapshots[surface_key] = record
        if len(snapshots) > 80:
            ordered = sorted(
                (
                    (key, value)
                    for key, value in snapshots.items()
                    if isinstance(value, dict)
                ),
                key=lambda item: str(item[1].get("saved_at", "")),
                reverse=True,
            )[:80]
            snapshots = {key: value for key, value in ordered}
        state["surface_snapshots"] = snapshots
        self.save(state)
        return record

    def service_runtime_record(self, role: str) -> dict[str, Any] | None:
        state = self.load()
        records = state.get("service_runtime", {})
        record = records.get(role.strip().lower(), {})
        return dict(record) if isinstance(record, dict) else None

    def save_service_runtime(self, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        records = dict(state.get("service_runtime", {}))
        history = list(state.get("service_runtime_history", []))
        role_key = role.strip().lower()
        record = {
            "role": role.strip(),
            "updated_at": _now_utc().isoformat(),
            **payload,
        }
        records[role_key] = record
        history.append(record)
        state["service_runtime"] = records
        state["service_runtime_history"] = history[-120:]
        self.save(state)
        return record

    def list_cadence_history(self, actor: str = "", *, limit: int = 12) -> list[dict[str, Any]]:
        state = self.load()
        history = state.get("cadence_history", [])
        actor_key = actor.strip().lower()
        results: list[dict[str, Any]] = []
        for item in reversed(history if isinstance(history, list) else []):
            if not isinstance(item, dict):
                continue
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            results.append(dict(item))
            if len(results) >= limit:
                break
        return results

    def latest_cadence_record(self, actor: str, phase: str = "") -> dict[str, Any] | None:
        actor_key = actor.strip().lower()
        phase_key = phase.strip().lower()
        for item in self.list_cadence_history(actor, limit=40):
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            if phase_key and str(item.get("phase", "")).strip().lower() != phase_key:
                continue
            return dict(item)
        return None

    def save_cadence_record(
        self,
        actor: str,
        *,
        phase: str,
        loop_id: str,
        loop_label: str,
        title: str,
        digest: str,
        outcome_summary: str,
        completion_criteria: list[str],
        recommended_next_move: str,
        waiting_on_you: int,
        needs_revisit: int,
    ) -> dict[str, Any]:
        state = self.load()
        history = list(state.get("cadence_history", []))
        actor_key = actor.strip().lower()
        phase_key = phase.strip().lower()
        latest = self.latest_cadence_record(actor, phase)
        now = _now_utc()
        if latest:
            latest_at = latest.get("generated_at", "")
            try:
                latest_dt = datetime.fromisoformat(str(latest_at).replace("Z", "+00:00"))
            except ValueError:
                latest_dt = None
            same_content = (
                str(latest.get("digest", "")).strip() == digest.strip()
                and str(latest.get("outcome_summary", "")).strip() == outcome_summary.strip()
                and str(latest.get("recommended_next_move", "")).strip() == recommended_next_move.strip()
                and int(latest.get("waiting_on_you", 0) or 0) == int(waiting_on_you)
                and int(latest.get("needs_revisit", 0) or 0) == int(needs_revisit)
            )
            if same_content and latest_dt is not None and latest_dt >= now - timedelta(minutes=90):
                return latest
        record = {
            "cadence_id": f"cadence-{now.timestamp()}-{actor_key}-{phase_key}",
            "actor": actor.strip(),
            "phase": phase.strip(),
            "loop_id": loop_id.strip(),
            "loop_label": loop_label.strip(),
            "title": title.strip(),
            "digest": digest.strip(),
            "outcome_summary": outcome_summary.strip(),
            "completion_criteria": list(completion_criteria),
            "recommended_next_move": recommended_next_move.strip(),
            "waiting_on_you": int(waiting_on_you),
            "needs_revisit": int(needs_revisit),
            "generated_at": now.isoformat(),
        }
        history.append(record)
        state["cadence_history"] = history[-200:]
        self.save(state)
        return record

    def list_service_runtime_history(self, role: str = "", *, limit: int = 12) -> list[dict[str, Any]]:
        state = self.load()
        history = state.get("service_runtime_history", [])
        role_key = role.strip().lower()
        results: list[dict[str, Any]] = []
        for item in reversed(history if isinstance(history, list) else []):
            if not isinstance(item, dict):
                continue
            if role_key and str(item.get("role", "")).strip().lower() != role_key:
                continue
            results.append(dict(item))
            if len(results) >= limit:
                break
        return results

    def save_sweep(
        self,
        actor: str,
        *,
        surface_key: str,
        total_open_loops: int,
        waiting_on_you: int,
        needs_revisit: int,
        suggested_packet: str,
        cadence_phase: str = "",
        active_loop: str = "",
    ) -> dict[str, Any]:
        state = self.load()
        sweeps = dict(state.get("sweeps", {}))
        actor_key = actor.strip().lower()
        record = {
            "actor": actor.strip(),
            "surface_key": surface_key.strip(),
            "total_open_loops": int(total_open_loops),
            "waiting_on_you": int(waiting_on_you),
            "needs_revisit": int(needs_revisit),
            "suggested_packet": suggested_packet.strip(),
            "cadence_phase": cadence_phase.strip(),
            "active_loop": active_loop.strip(),
            "updated_at": _now_utc().isoformat(),
        }
        sweeps[actor_key] = record
        state["sweeps"] = sweeps
        history = list(state.get("surface_history", []))
        history.append(record)
        state["surface_history"] = history[-120:]
        self.save(state)
        return record

    def record_outcome(
        self,
        actor: str,
        *,
        source: str,
        initiator: str,
        status: str,
        domain: str = "",
        item_id: str = "",
        notification_id: str = "",
        action: str = "",
        action_class: str = "",
        surface_key: str = "",
        detail: str = "",
        device_id: str = "",
        timing_quality: str = "",
        succeeded: bool | None = None,
        caused_friction: bool | None = None,
        friction_reason: str = "",
    ) -> dict[str, Any]:
        state = self.load()
        outcomes = list(state.get("outcomes", []))
        now = _now_utc()
        record = {
            "outcome_id": f"outcome-{now.timestamp()}-{source.strip().lower() or 'event'}",
            "actor": actor.strip(),
            "source": source.strip() or "general",
            "initiator": initiator.strip() or "system",
            "status": status.strip() or "recorded",
            "domain": domain.strip(),
            "item_id": item_id.strip(),
            "notification_id": notification_id.strip(),
            "action": action.strip(),
            "action_class": action_class.strip(),
            "surface_key": surface_key.strip(),
            "detail": detail.strip(),
            "device_id": device_id.strip(),
            "timing_quality": timing_quality.strip(),
            "timestamp": now.isoformat(),
        }
        if succeeded is not None:
            record["succeeded"] = bool(succeeded)
        if caused_friction is not None:
            record["caused_friction"] = bool(caused_friction)
        if friction_reason.strip():
            record["friction_reason"] = friction_reason.strip()
        outcomes.append(record)
        state["outcomes"] = outcomes[-500:]
        self.save(state)
        return record

    def outcome_history(
        self,
        actor: str = "",
        *,
        limit: int = 25,
        source: str = "",
    ) -> list[dict[str, Any]]:
        state = self.load()
        actor_key = actor.strip().lower()
        source_key = source.strip().lower()
        results: list[dict[str, Any]] = []
        for item in reversed(list(state.get("outcomes", []))):
            if not isinstance(item, dict):
                continue
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            if source_key and str(item.get("source", "")).strip().lower() != source_key:
                continue
            results.append(dict(item))
            if len(results) >= limit:
                break
        return results

    def outcome_summary(self, actor: str = "", *, limit: int = 200) -> dict[str, Any]:
        outcomes = self.outcome_history(actor, limit=limit)
        summary = {
            "total": len(outcomes),
            "by_status": {},
            "by_source": {},
            "by_initiator": {},
            "by_timing_quality": {},
            "autonomous_successful": 0,
            "autonomous_failed": 0,
            "autonomous_friction": 0,
        }
        for item in outcomes:
            status = str(item.get("status", "recorded")).strip().lower() or "recorded"
            source = str(item.get("source", "general")).strip().lower() or "general"
            initiator = str(item.get("initiator", "system")).strip().lower() or "system"
            timing_quality = str(item.get("timing_quality", "")).strip().lower()
            summary["by_status"][status] = int(summary["by_status"].get(status, 0) or 0) + 1
            summary["by_source"][source] = int(summary["by_source"].get(source, 0) or 0) + 1
            summary["by_initiator"][initiator] = int(summary["by_initiator"].get(initiator, 0) or 0) + 1
            if timing_quality:
                summary["by_timing_quality"][timing_quality] = int(summary["by_timing_quality"].get(timing_quality, 0) or 0) + 1
            if source == "assistant-action":
                if item.get("succeeded") is True:
                    summary["autonomous_successful"] += 1
                if item.get("succeeded") is False:
                    summary["autonomous_failed"] += 1
                if item.get("caused_friction") is True:
                    summary["autonomous_friction"] += 1
        return summary

    def list_notifications(self, actor: str = "", *, unread_only: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        self.expire_notifications(actor or "")
        state = self.load()
        notifications = state.get("notifications", [])
        actor_key = actor.strip().lower()
        results: list[dict[str, Any]] = []
        for item in reversed(notifications if isinstance(notifications, list) else []):
            if not isinstance(item, dict):
                continue
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            status = _normalize_notification_status(str(item.get("status", "unseen")))
            if unread_only and status not in ACTIVE_NOTIFICATION_STATUSES:
                continue
            item["status"] = status
            results.append(dict(item))
            if len(results) >= limit:
                break
        return results

    def latest_notification(self, actor: str, surface_key: str, *, include_terminal: bool = True) -> dict[str, Any] | None:
        actor_key = actor.strip().lower()
        surface_key = surface_key.strip()
        if not actor_key or not surface_key:
            return None
        state = self.load()
        notifications = state.get("notifications", [])
        for item in reversed(notifications if isinstance(notifications, list) else []):
            if not isinstance(item, dict):
                continue
            if str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            if str(item.get("surface_key", "")).strip() != surface_key:
                continue
            status = _normalize_notification_status(str(item.get("status", "unseen")))
            if not include_terminal and status not in ACTIVE_NOTIFICATION_STATUSES:
                continue
            record = dict(item)
            record["status"] = status
            return record
        return None

    def notification_last_event_at(self, notification: dict[str, Any]) -> datetime | None:
        for key in (
            "opened_at",
            "surfaced_at",
            "browser_delivered_at",
            "ignored_at",
            "acted_at",
            "updated_at",
            "created_at",
        ):
            parsed = _parse_iso_datetime(str(notification.get(key, "")))
            if parsed is not None:
                return parsed
        return None

    def expire_notifications(self, actor: str = "") -> int:
        state = self.load()
        notifications = list(state.get("notifications", []))
        actor_key = actor.strip().lower()
        updated = 0
        now = _now_utc()
        for item in notifications:
            if not isinstance(item, dict):
                continue
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            status = _normalize_notification_status(str(item.get("status", "unseen")))
            expires_at = str(item.get("expires_at", "")).strip()
            if status not in ACTIVE_NOTIFICATION_STATUSES or not expires_at:
                item["status"] = status
                continue
            try:
                expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if expires_dt <= now:
                item["status"] = "expired"
                item["expired_at"] = now.isoformat()
                item["updated_at"] = now.isoformat()
                updated += 1
            else:
                item["status"] = status
        if updated:
            state["notifications"] = notifications
            self.save(state)
        return updated

    def mark_notifications_for_item(self, actor: str, *, domain: str, item_id: str, status: str) -> int:
        state = self.load()
        notifications = list(state.get("notifications", []))
        actor_key = actor.strip().lower()
        domain_key = domain.strip().lower()
        item_key = item_id.strip()
        normalized = _normalize_notification_status(status)
        updated = 0
        timestamp = _now_utc().isoformat()
        stamp_field = {
            "surfaced": "surfaced_at",
            "opened": "opened_at",
            "acted": "acted_at",
            "ignored": "ignored_at",
            "expired": "expired_at",
        }.get(normalized, "updated_at")
        for item in notifications:
            if not isinstance(item, dict):
                continue
            if actor_key and str(item.get("actor", "")).strip().lower() != actor_key:
                continue
            if str(item.get("domain", "")).strip().lower() != domain_key or str(item.get("item_id", "")).strip() != item_key:
                continue
            item["status"] = normalized
            item[stamp_field] = timestamp
            item["updated_at"] = timestamp
            updated += 1
        if updated:
            state["notifications"] = notifications
            self.save(state)
        return updated

    def push_notification(
        self,
        actor: str,
        *,
        surface_key: str,
        packet: str,
        title: str,
        detail: str,
        domain: str,
        item_id: str,
        severity: str = "normal",
        delivery_mode: str = "browser-eligible",
        interrupt_during_quiet_hours: bool = False,
        delivery_policy_summary: str = "",
        priority_class: str = "normal",
        why_this_surfaced: str = "",
        stale_after_hours: int = 48,
    ) -> dict[str, Any]:
        self.expire_notifications(actor)
        state = self.load()
        notifications = list(state.get("notifications", []))
        actor_key = actor.strip().lower()
        created_at = _now_utc()
        expires_at = (created_at + timedelta(hours=max(int(stale_after_hours or 0), 1))).isoformat()
        for item in notifications:
            if (
                isinstance(item, dict)
                and str(item.get("actor", "")).strip().lower() == actor_key
                and str(item.get("surface_key", "")).strip() == surface_key.strip()
                and _normalize_notification_status(str(item.get("status", "unseen"))) in ACTIVE_NOTIFICATION_STATUSES
            ):
                item["updated_at"] = created_at.isoformat()
                item["detail"] = detail.strip() or item.get("detail", "")
                item["title"] = title.strip() or item.get("title", "")
                item["severity"] = severity.strip() or item.get("severity", "normal")
                item["priority_class"] = priority_class.strip() or item.get("priority_class", "normal")
                item["delivery_mode"] = delivery_mode.strip() or item.get("delivery_mode", "browser-eligible")
                item["delivery_policy_summary"] = delivery_policy_summary.strip() or item.get("delivery_policy_summary", "")
                item["why_this_surfaced"] = why_this_surfaced.strip() or item.get("why_this_surfaced", "")
                item["stale_after_hours"] = max(int(stale_after_hours or 0), 1)
                item["expires_at"] = expires_at
                state["notifications"] = notifications[-200:]
                self.save(state)
                return dict(item)
        record = {
            "notification_id": f"assistant-{created_at.timestamp()}-{item_id or surface_key}",
            "actor": actor.strip(),
            "surface_key": surface_key.strip(),
            "packet": packet.strip(),
            "title": title.strip(),
            "detail": detail.strip(),
            "domain": domain.strip(),
            "item_id": item_id.strip(),
            "severity": severity.strip() or "normal",
            "priority_class": priority_class.strip() or "normal",
            "delivery_mode": delivery_mode.strip() or "browser-eligible",
            "interrupt_during_quiet_hours": bool(interrupt_during_quiet_hours),
            "delivery_policy_summary": delivery_policy_summary.strip(),
            "why_this_surfaced": why_this_surfaced.strip(),
            "stale_after_hours": max(int(stale_after_hours or 0), 1),
            "status": "unseen",
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "expires_at": expires_at,
        }
        notifications.append(record)
        state["notifications"] = notifications[-200:]
        self.save(state)
        return record

    def mark_notification(self, notification_id: str, *, status: str) -> dict[str, Any] | None:
        self.expire_notifications()
        state = self.load()
        notifications = list(state.get("notifications", []))
        normalized = _normalize_notification_status(status)
        stamp_field = {
            "surfaced": "surfaced_at",
            "opened": "opened_at",
            "acted": "acted_at",
            "ignored": "ignored_at",
            "expired": "expired_at",
        }.get(normalized, "updated_at")
        for item in notifications:
            if isinstance(item, dict) and str(item.get("notification_id", "")).strip() == notification_id.strip():
                item["status"] = normalized
                item[stamp_field] = _now_utc().isoformat()
                item["updated_at"] = _now_utc().isoformat()
                state["notifications"] = notifications
                self.save(state)
                return dict(item)
        return None

    def mark_notification_delivered(self, notification_id: str, *, device_id: str = "") -> dict[str, Any] | None:
        self.expire_notifications()
        state = self.load()
        notifications = list(state.get("notifications", []))
        for item in notifications:
            if isinstance(item, dict) and str(item.get("notification_id", "")).strip() == notification_id.strip():
                item["browser_delivered_at"] = _now_utc().isoformat()
                item["browser_delivery_count"] = int(item.get("browser_delivery_count", 0) or 0) + 1
                if device_id.strip():
                    item["browser_delivery_device_id"] = device_id.strip()
                current_status = _normalize_notification_status(str(item.get("status", "unseen")))
                if current_status == "unseen":
                    item["status"] = "surfaced"
                    item["surfaced_at"] = _now_utc().isoformat()
                item["updated_at"] = _now_utc().isoformat()
                state["notifications"] = notifications
                self.save(state)
                return dict(item)
        return None
