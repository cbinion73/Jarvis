from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

ALLOWED_RESEARCH_TASK_STATUSES = {
    "queued",
    "in_progress",
    "blocked",
    "completed",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    cleaned: list[str] = []
    for value in list(values or []):
        item = str(value or "").strip()
        if item:
            cleaned.append(item)
    return cleaned


def _looks_uncertain(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return any(
        token in lowered
        for token in (
            "prelim",
            "tentative",
            "uncertain",
            "unverified",
            "draft",
            "manual note",
            "partial",
            "rough",
        )
    )


@dataclass(slots=True)
class ResearchTaskStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "research_tasks.json"
        self.log_path = self.root / "research_tasks_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"research_tasks": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("research_tasks", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Research-task storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_task(
        self,
        *,
        actor: str,
        title: str,
        question: str,
        desired_scope: str = "",
        status: str = "queued",
        constraints: list[str] | None = None,
        source_expectations: list[str] | None = None,
    ) -> dict[str, Any]:
        cleaned_title = str(title or "").strip()
        cleaned_question = str(question or "").strip()
        cleaned_scope = str(desired_scope or "").strip()
        cleaned_status = str(status or "").strip().lower() or "queued"
        if not cleaned_title:
            raise ValueError("title is required")
        if not cleaned_question:
            raise ValueError("question is required")
        if cleaned_status not in ALLOWED_RESEARCH_TASK_STATUSES:
            raise ValueError("status must be one of: queued, in_progress, blocked, completed")
        now = _now_iso()
        task_id = str(uuid.uuid4())
        record = {
            "task_id": task_id,
            "object_kind": "research_task",
            "actor": str(actor or "").strip() or "Chris",
            "title": cleaned_title,
            "question": cleaned_question,
            "desired_scope": cleaned_scope,
            "status": cleaned_status,
            "constraints": _clean_list(constraints),
            "source_expectations": _clean_list(source_expectations),
            "created_at": now,
            "updated_at": now,
            "truth_mode": "explicit_intent_only",
            "research_performed": False,
            "source_discovery_performed": False,
            "autonomous_execution": False,
            "evidence_items": [],
            "evidence_refs": [],
            "synthesis": {},
        }
        payload = self.load()
        tasks = dict(payload.get("research_tasks", {}))
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        tasks[task_id] = record
        history.append(
            {
                "event": "research-task-created",
                "task_id": task_id,
                "title": cleaned_title,
                "status": cleaned_status,
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["research_tasks"] = tasks
        payload["history"] = history[-300:]
        self.save(payload)
        return record

    def update_task(
        self,
        task_id: str,
        *,
        title: str = "",
        question: str = "",
        desired_scope: str = "",
        status: str = "",
        constraints: list[str] | None = None,
        source_expectations: list[str] | None = None,
    ) -> dict[str, Any]:
        cleaned_task_id = str(task_id or "").strip()
        if not cleaned_task_id:
            raise ValueError("task_id is required")
        payload = self.load()
        tasks = dict(payload.get("research_tasks", {}))
        existing = tasks.get(cleaned_task_id)
        if not isinstance(existing, dict):
            raise KeyError(f"Unknown research task: {cleaned_task_id}")
        updated = dict(existing)
        if title.strip():
            updated["title"] = title.strip()
        if question.strip():
            updated["question"] = question.strip()
        if desired_scope.strip() or desired_scope == "":
            updated["desired_scope"] = desired_scope.strip()
        if status.strip():
            cleaned_status = status.strip().lower()
            if cleaned_status not in ALLOWED_RESEARCH_TASK_STATUSES:
                raise ValueError("status must be one of: queued, in_progress, blocked, completed")
            updated["status"] = cleaned_status
        if constraints is not None:
            updated["constraints"] = _clean_list(constraints)
        if source_expectations is not None:
            updated["source_expectations"] = _clean_list(source_expectations)
        if not str(updated.get("title", "")).strip():
            raise ValueError("title is required")
        if not str(updated.get("question", "")).strip():
            raise ValueError("question is required")
        updated["updated_at"] = _now_iso()
        tasks[cleaned_task_id] = updated
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        history.append(
            {
                "event": "research-task-updated",
                "task_id": cleaned_task_id,
                "title": str(updated.get("title", "")).strip(),
                "status": str(updated.get("status", "")).strip(),
                "updated_at": updated["updated_at"],
            }
        )
        payload["research_tasks"] = tasks
        payload["history"] = history[-300:]
        self.save(payload)
        return updated

    def add_evidence_item(
        self,
        task_id: str,
        *,
        source_label: str,
        source_locator: str = "",
        evidence_note: str = "",
        capture_status: str = "",
        confidence_label: str = "",
    ) -> dict[str, Any]:
        cleaned_task_id = str(task_id or "").strip()
        cleaned_source_label = str(source_label or "").strip()
        cleaned_source_locator = str(source_locator or "").strip()
        cleaned_evidence_note = str(evidence_note or "").strip()
        cleaned_capture_status = str(capture_status or "").strip() or "captured"
        cleaned_confidence_label = str(confidence_label or "").strip()
        if not cleaned_task_id:
            raise ValueError("task_id is required")
        if not cleaned_source_label:
            raise ValueError("source_label is required")
        if not cleaned_source_locator and not cleaned_evidence_note:
            raise ValueError("source_locator or evidence_note is required")
        payload = self.load()
        tasks = dict(payload.get("research_tasks", {}))
        existing = tasks.get(cleaned_task_id)
        if not isinstance(existing, dict):
            raise KeyError(f"Unknown research task: {cleaned_task_id}")
        updated = dict(existing)
        evidence_items = [dict(item) for item in list(updated.get("evidence_items") or []) if isinstance(item, dict)]
        now = _now_iso()
        created = {
            "evidence_id": str(uuid.uuid4()),
            "source_label": cleaned_source_label,
            "source_locator": cleaned_source_locator,
            "evidence_note": cleaned_evidence_note,
            "capture_status": cleaned_capture_status,
            "confidence_label": cleaned_confidence_label,
            "capture_mode": "manual_entry",
            "captured_at": now,
            "retrieval_used": False,
            "autonomous_discovery": False,
        }
        evidence_items.append(created)
        updated["evidence_items"] = evidence_items
        updated["updated_at"] = now
        tasks[cleaned_task_id] = updated
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        history.append(
            {
                "event": "research-task-evidence-added",
                "task_id": cleaned_task_id,
                "evidence_id": created["evidence_id"],
                "source_label": cleaned_source_label,
                "capture_mode": "manual_entry",
                "captured_at": now,
            }
        )
        payload["research_tasks"] = tasks
        payload["history"] = history[-300:]
        self.save(payload)
        return created

    def generate_synthesis(self, task_id: str) -> dict[str, Any]:
        cleaned_task_id = str(task_id or "").strip()
        if not cleaned_task_id:
            raise ValueError("task_id is required")
        payload = self.load()
        tasks = dict(payload.get("research_tasks", {}))
        existing = tasks.get(cleaned_task_id)
        if not isinstance(existing, dict):
            raise KeyError(f"Unknown research task: {cleaned_task_id}")
        updated = dict(existing)
        evidence_items = [dict(item) for item in list(updated.get("evidence_items") or []) if isinstance(item, dict)]
        if not evidence_items:
            raise ValueError("at least one attached evidence item is required before synthesis can be generated")

        now = _now_iso()
        evidence_ids_used = [str(item.get("evidence_id", "")).strip() for item in evidence_items if str(item.get("evidence_id", "")).strip()]
        supported_points: list[str] = []
        uncertainties: list[str] = []
        missing_information: list[str] = []

        for item in evidence_items:
            source_label = str(item.get("source_label", "")).strip() or "Attached evidence"
            source_locator = str(item.get("source_locator", "")).strip()
            evidence_note = str(item.get("evidence_note", "")).strip()
            confidence_label = str(item.get("confidence_label", "")).strip()
            capture_status = str(item.get("capture_status", "")).strip()
            if evidence_note:
                supported_points.append(f"{source_label}: {evidence_note}")
            elif source_locator:
                supported_points.append(f"{source_label}: Attached source at {source_locator}.")
            else:
                supported_points.append(f"{source_label}: Evidence item is attached, but the supporting note is still thin.")
            if _looks_uncertain(confidence_label) or _looks_uncertain(capture_status):
                uncertainties.append(f"{source_label} is marked with provisional or uncertain confidence.")
            if not source_locator:
                missing_information.append(f"{source_label} does not include a source locator or URL yet.")

        if len(evidence_items) < 2:
            uncertainties.append("The attached evidence set is still sparse, so this synthesis remains partial.")
            missing_information.append("More attached evidence items would be needed for a fuller synthesis.")
        if any(str(item.get("capture_mode", "")).strip() == "manual_entry" for item in evidence_items):
            uncertainties.append(
                "These evidence items were attached manually in this task; they were not autonomously discovered or externally validated in this runtime path."
            )
        expected_sources = [str(item).strip() for item in list(updated.get("source_expectations") or []) if str(item).strip()]
        if expected_sources and len(evidence_items) < len(expected_sources):
            missing_information.append(
                "Not all expected source types are represented yet: " + ", ".join(expected_sources)
            )

        supported_points = supported_points[:6]
        uncertainties = list(dict.fromkeys(item for item in uncertainties if item))[:6]
        missing_information = list(dict.fromkeys(item for item in missing_information if item))[:6]

        summary = (
            f"This synthesis uses {len(evidence_items)} attached evidence item"
            f"{'' if len(evidence_items) == 1 else 's'} for '{str(updated.get('title', '')).strip() or 'this research task'}'. "
            "It reflects only the evidence attached to this task in the current runtime path."
        )
        if uncertainties:
            summary += " Some parts remain uncertain or incomplete."

        synthesis = {
            "synthesis_id": str(uuid.uuid4()),
            "generated_at": now,
            "synthesis_mode": "attached_evidence_only",
            "evidence_ids_used": evidence_ids_used,
            "evidence_count": len(evidence_items),
            "summary": summary,
            "supported_points": supported_points,
            "uncertainties": uncertainties,
            "missing_information": missing_information,
            "externally_validated": False,
            "autonomous_discovery_used": False,
            "research_completed_inferred": False,
        }
        updated["synthesis"] = synthesis
        updated["updated_at"] = now
        tasks[cleaned_task_id] = updated
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        history.append(
            {
                "event": "research-task-synthesis-generated",
                "task_id": cleaned_task_id,
                "synthesis_id": synthesis["synthesis_id"],
                "evidence_count": len(evidence_items),
                "generated_at": now,
            }
        )
        payload["research_tasks"] = tasks
        payload["history"] = history[-300:]
        self.save(payload)
        return synthesis

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("research_tasks", {}).get(str(task_id or "").strip())
        return dict(record) if isinstance(record, dict) else None

    def list_tasks(self) -> list[dict[str, Any]]:
        payload = self.load()
        records = payload.get("research_tasks", {})
        if not isinstance(records, dict):
            return []
        items = [dict(item) for item in records.values() if isinstance(item, dict)]
        items.sort(key=lambda item: str(item.get("created_at", "")).strip(), reverse=True)
        return items
