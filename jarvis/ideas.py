"""
ideas.py — JARVIS Idea Inbox
============================
A lightweight capture store for raw ideas. Each idea can be:
  - captured (just text, no action yet)
  - queued (marked for research)
  - researching (DossierBuilder is running)
  - done (dossier ready, linked via dossier_id / work_id)
  - passed (user dismissed it)

Storage: ~/.jarvis/ideas.json  (thread-safe, JSON array)
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_IDEAS_PATH = Path.home() / ".jarvis" / "ideas.json"
_lock = threading.Lock()

VALID_STATUSES = ["captured", "queued", "researching", "done", "passed"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> list[dict]:
    try:
        if _IDEAS_PATH.exists():
            data = json.loads(_IDEAS_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save(ideas: list[dict]) -> None:
    _IDEAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _IDEAS_PATH.write_text(json.dumps(ideas, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_idea(
    text: str,
    source: str = "user",
    notes: str = "",
    domain: str = "passive-income",
    tags: list[str] | None = None,
) -> dict:
    """Capture a raw idea. Returns the new idea dict."""
    idea: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "source": source,          # "user" | "agent"
        "status": "captured",
        "domain": domain,
        "notes": notes.strip(),
        "tags": tags or [],
        "work_id": "",             # set when WorkItem is created
        "dossier_id": "",          # set when dossier is ready
        "created_at": _now(),
        "updated_at": _now(),
        "researched_at": "",
    }
    with _lock:
        ideas = _load()
        ideas.append(idea)
        _save(ideas)
    return idea


def list_ideas(status: str | None = None) -> list[dict]:
    """Return all ideas, optionally filtered by status."""
    with _lock:
        ideas = _load()
    if status:
        ideas = [i for i in ideas if i.get("status") == status]
    return sorted(ideas, key=lambda i: i.get("created_at", ""), reverse=True)


def get_idea(idea_id: str) -> dict | None:
    with _lock:
        for idea in _load():
            if idea.get("id") == idea_id:
                return idea
    return None


def update_idea(idea_id: str, **fields: Any) -> dict | None:
    """Update arbitrary fields on an idea. Returns updated dict or None."""
    with _lock:
        ideas = _load()
        for idea in ideas:
            if idea.get("id") == idea_id:
                for k, v in fields.items():
                    if k not in ("id", "created_at"):
                        idea[k] = v
                idea["updated_at"] = _now()
                _save(ideas)
                return idea
    return None


def delete_idea(idea_id: str) -> bool:
    """Hard-delete an idea. Returns True if found."""
    with _lock:
        ideas = _load()
        new = [i for i in ideas if i.get("id") != idea_id]
        if len(new) < len(ideas):
            _save(new)
            return True
    return False


def queue_idea(idea_id: str) -> dict | None:
    """Mark an idea as queued for research."""
    return update_idea(idea_id, status="queued")


def pass_idea(idea_id: str) -> dict | None:
    """Dismiss an idea (pass on it)."""
    return update_idea(idea_id, status="passed")


def mark_researching(idea_id: str, work_id: str) -> dict | None:
    """Mark research started; store the linked WorkItem ID."""
    return update_idea(idea_id, status="researching", work_id=work_id)


def mark_done(idea_id: str, dossier_id: str, work_id: str = "") -> dict | None:
    """Mark research complete; store dossier_id and researched_at."""
    return update_idea(
        idea_id,
        status="done",
        dossier_id=dossier_id,
        work_id=work_id or get_idea(idea_id or "")  # keep existing if blank
            and (get_idea(idea_id) or {}).get("work_id", ""),
        researched_at=_now(),
    )


def pending_count() -> int:
    """Number of captured + queued ideas (snapshot for overview widget)."""
    ideas = list_ideas()
    return sum(1 for i in ideas if i.get("status") in ("captured", "queued"))


def stats() -> dict:
    """Summary counts by status for the overview chip."""
    ideas = list_ideas()
    counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for i in ideas:
        s = i.get("status", "captured")
        counts[s] = counts.get(s, 0) + 1
    return {"total": len(ideas), "by_status": counts}
