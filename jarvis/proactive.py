"""D3: Proactive prompt builder.

Constructs why-now prompts with confidence, source_facts, suggested actions,
snooze/dismiss support, and an audit trail.  All prompts carry a truth label
and are never presented as live data if they are inferred or stale.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


PROMPT_STATES = frozenset({"pending", "delivered", "snoozed", "dismissed", "acted"})
SNOOZE_REASONS = frozenset({"not_now", "busy", "irrelevant", "already_handled"})
DISMISS_REASONS = frozenset({"not_useful", "wrong_time", "wrong_surface", "already_handled", "do_not_repeat"})


@dataclass(slots=True)
class ProactivePrompt:
    prompt_id: str
    actor: str
    title: str
    body: str
    why_now: str
    confidence: float           # 0.0–1.0
    source_facts: list[str]     # list of supporting fact_ids or description strings
    suggested_actions: list[dict]  # [{label, action_type, payload}]
    state: str                  # pending/delivered/snoozed/dismissed/acted
    created_at: str
    delivered_at: str = ""
    snoozed_until: str = ""
    dismissed_at: str = ""
    snooze_reason: str = ""
    dismiss_reason: str = ""
    domain: str = ""
    priority: int = 5           # 1=highest, 10=lowest
    source: str = "inferred"    # observed_fact / inferred / user-requested
    audit_events: list[dict] = field(default_factory=list)


class ProactivePromptStore:
    """Durable store for proactive prompts with JSONL audit trail."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.prompts_path = self.root / "proactive_prompts.json"
        self.audit_path = self.root / "proactive_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.prompts_path.exists():
            return []
        try:
            payload = json.loads(self.prompts_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        atomic_write_json(self.prompts_path, records)

    def _audit(self, event: str, prompt_id: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(),
            "event": event,
            "prompt_id": prompt_id,
        }
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def add(self, prompt: ProactivePrompt) -> dict:
        records = self._load()
        payload = asdict(prompt)
        records.append(payload)
        self._save(records)
        self._audit("created", prompt.prompt_id)
        return payload

    def list_pending(self, actor: str | None = None) -> list[dict]:
        records = self._load()
        out = []
        for r in records:
            if r.get("state") not in ("pending", "snoozed"):
                continue
            if actor and r.get("actor") != actor:
                continue
            # Exclude snoozed prompts whose snooze window hasn't expired
            if r.get("state") == "snoozed" and r.get("snoozed_until"):
                if r["snoozed_until"] > _ts():
                    continue
            out.append(r)
        out.sort(key=lambda x: (int(x.get("priority") or 5), x.get("created_at", "")))
        return out

    def mark_delivered(self, prompt_id: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "delivered"
                r["delivered_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("delivered", prompt_id)
        return updated

    def snooze(self, prompt_id: str, snooze_until: str, reason: str = "") -> dict | None:
        if reason and reason not in SNOOZE_REASONS:
            raise ValueError(f"snooze reason must be one of {sorted(SNOOZE_REASONS)}")
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "snoozed"
                r["snoozed_until"] = snooze_until
                r["snooze_reason"] = reason
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("snoozed", prompt_id, {"until": snooze_until, "reason": reason})
        return updated

    def dismiss(self, prompt_id: str, reason: str = "") -> dict | None:
        if reason and reason not in DISMISS_REASONS:
            raise ValueError(f"dismiss reason must be one of {sorted(DISMISS_REASONS)}")
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "dismissed"
                r["dismissed_at"] = _ts()
                r["dismiss_reason"] = reason
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("dismissed", prompt_id, {"reason": reason})
        return updated

    def mark_acted(self, prompt_id: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "acted"
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("acted", prompt_id)
        return updated


class ProactivePromptBuilder:
    """Construct well-formed ProactivePrompts with validated fields."""

    def build(
        self,
        *,
        actor: str,
        title: str,
        body: str,
        why_now: str,
        confidence: float = 0.7,
        source_facts: list[str] | None = None,
        suggested_actions: list[dict] | None = None,
        domain: str = "",
        priority: int = 5,
        source: str = "inferred",
    ) -> ProactivePrompt:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be 0.0–1.0")
        if priority not in range(1, 11):
            raise ValueError("priority must be 1–10")
        if source not in ("observed_fact", "inferred", "user-requested"):
            raise ValueError("source must be observed_fact, inferred, or user-requested")
        return ProactivePrompt(
            prompt_id=str(uuid.uuid4()),
            actor=actor,
            title=title,
            body=body,
            why_now=why_now,
            confidence=confidence,
            source_facts=source_facts or [],
            suggested_actions=suggested_actions or [],
            state="pending",
            created_at=_ts(),
            domain=domain,
            priority=priority,
            source=source,
        )
