"""F4: Legacy archive — intergenerational memory bundles.

Provides browsable, exportable, permissioned, provenance-backed, correctable
bundles of:
- Stories (family narratives, memorable events)
- Milestones (births, graduations, significant achievements)
- Decisions (major family decisions with reasoning)
- Rituals (family practices, traditions, recurring ceremonies)
- Lessons (lessons learned, wisdom captured)
- Identity threads (who we are as a family, recurring themes)

All records are:
- Permissioned (who can read/edit/export)
- Provenance-backed (where did this come from, who recorded it)
- Correctable (dispute/correct/annotate flow)
- Exportable (structured JSON bundle for archival)
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_LEGACY_ROOT = Path("data/legacy")
_BUNDLES_PATH = _LEGACY_ROOT / "bundles.json"
_ENTRIES_PATH = _LEGACY_ROOT / "entries.json"
_AUDIT_PATH = _LEGACY_ROOT / "legacy_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Entry types and permission levels
# ---------------------------------------------------------------------------

ENTRY_TYPES = frozenset({
    "story",        # family narrative or memorable event
    "milestone",    # birth, graduation, achievement
    "decision",     # major family decision with reasoning
    "ritual",       # recurring practice or tradition
    "lesson",       # lesson learned or wisdom captured
    "identity",     # family identity thread
    "photo_ref",    # reference to a photo/media (no raw data stored)
})

PERMISSION_LEVELS = frozenset({"family", "adults_only", "chris_only", "archive"})

CORRECTION_STATUSES = frozenset({"active", "disputed", "corrected", "annotated", "archived"})


@dataclass(slots=True)
class LegacyEntry:
    """A single legacy archive entry."""
    entry_id: str
    entry_type: str                  # story/milestone/decision/ritual/lesson/identity/photo_ref
    title: str
    content: str
    date: str                        # YYYY-MM-DD (approximate date of the event)
    actor: str                       # who recorded this
    subjects: list[str]              # family members this involves
    permission_level: str            # family/adults_only/chris_only/archive
    provenance: str                  # how was this captured (conversation/manual/ritual/import)
    tags: list[str]
    status: str                      # active/disputed/corrected/annotated/archived
    created_at: str
    updated_at: str
    correction_note: str = ""
    annotation: str = ""
    bundle_ids: list[str] = field(default_factory=list)  # which bundles include this


@dataclass(slots=True)
class LegacyBundle:
    """A curated bundle of related legacy entries."""
    bundle_id: str
    title: str
    description: str
    theme: str                       # what connects these entries
    actor: str                       # who curated this bundle
    permission_level: str
    entry_ids: list[str]
    date_range_start: str
    date_range_end: str
    created_at: str
    updated_at: str
    exported_at: str = ""
    status: str = "active"           # active/archived/exported
    provenance: str = "curated"


class LegacyArchiveStore:
    """Manages legacy archive entries and bundles."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _LEGACY_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.entries_path = self.root / "entries.json"
        self.bundles_path = self.root / "bundles.json"
        self.audit_path = self.root / "legacy_audit.jsonl"

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, records)

    def _audit(self, event: str, entity_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {"ts": _ts(), "event": event, "entity_id": entity_id, "actor": actor}
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Entries
    # ------------------------------------------------------------------

    def add_entry(
        self,
        *,
        entry_type: str,
        title: str,
        content: str,
        date: str,
        actor: str,
        subjects: list[str] | None = None,
        permission_level: str = "family",
        provenance: str = "manual",
        tags: list[str] | None = None,
    ) -> LegacyEntry:
        if entry_type not in ENTRY_TYPES:
            raise ValueError(f"entry_type must be one of {sorted(ENTRY_TYPES)}")
        if permission_level not in PERMISSION_LEVELS:
            raise ValueError(f"permission_level must be one of {sorted(PERMISSION_LEVELS)}")
        if not title.strip():
            raise ValueError("title is required")

        entry = LegacyEntry(
            entry_id=str(uuid.uuid4()),
            entry_type=entry_type,
            title=title.strip(),
            content=content,
            date=date,
            actor=actor,
            subjects=subjects or [],
            permission_level=permission_level,
            provenance=provenance,
            tags=tags or [],
            status="active",
            created_at=_ts(),
            updated_at=_ts(),
        )
        records = self._load(self.entries_path)
        records.append(asdict(entry))
        self._save(self.entries_path, records)
        self._audit("entry_added", entry.entry_id, actor, {"type": entry_type, "title": title})
        return entry

    def get_entry(self, entry_id: str) -> dict | None:
        for r in self._load(self.entries_path):
            if r.get("entry_id") == entry_id:
                return r
        return None

    def list_entries(
        self,
        *,
        entry_type: str | None = None,
        permission_level: str | None = None,
        actor_permission: str = "family",
        status: str = "active",
    ) -> list[dict]:
        """List entries the requesting actor can see based on their permission level."""
        permission_order = ["family", "adults_only", "chris_only", "archive"]
        actor_idx = permission_order.index(actor_permission) if actor_permission in permission_order else 0

        records = self._load(self.entries_path)
        results = []
        for r in records:
            # Filter by status
            if status and r.get("status") != status:
                continue
            # Filter by type
            if entry_type and r.get("entry_type") != entry_type:
                continue
            # Permission gate
            entry_perm = r.get("permission_level", "family")
            entry_idx = permission_order.index(entry_perm) if entry_perm in permission_order else 0
            if entry_idx > actor_idx:
                continue  # actor can't see this
            results.append(r)
        return results

    def correct_entry(self, entry_id: str, actor: str, correction: str) -> dict | None:
        records = self._load(self.entries_path)
        updated = None
        for r in records:
            if r.get("entry_id") == entry_id:
                r["status"] = "corrected"
                r["correction_note"] = correction
                r["updated_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(self.entries_path, records)
            self._audit("entry_corrected", entry_id, actor, {"correction": correction[:100]})
        return updated

    def dispute_entry(self, entry_id: str, actor: str, dispute_note: str) -> dict | None:
        records = self._load(self.entries_path)
        updated = None
        for r in records:
            if r.get("entry_id") == entry_id:
                r["status"] = "disputed"
                r["correction_note"] = dispute_note
                r["updated_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(self.entries_path, records)
            self._audit("entry_disputed", entry_id, actor)
        return updated

    def annotate_entry(self, entry_id: str, actor: str, annotation: str) -> dict | None:
        records = self._load(self.entries_path)
        updated = None
        for r in records:
            if r.get("entry_id") == entry_id:
                r["annotation"] = annotation
                r["status"] = "annotated"
                r["updated_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(self.entries_path, records)
            self._audit("entry_annotated", entry_id, actor)
        return updated

    # ------------------------------------------------------------------
    # Bundles
    # ------------------------------------------------------------------

    def create_bundle(
        self,
        *,
        title: str,
        description: str,
        theme: str,
        actor: str,
        entry_ids: list[str],
        permission_level: str = "family",
        date_range_start: str = "",
        date_range_end: str = "",
        provenance: str = "curated",
    ) -> LegacyBundle:
        if not title.strip():
            raise ValueError("title is required")
        if permission_level not in PERMISSION_LEVELS:
            raise ValueError(f"permission_level must be one of {sorted(PERMISSION_LEVELS)}")

        bundle = LegacyBundle(
            bundle_id=str(uuid.uuid4()),
            title=title.strip(),
            description=description,
            theme=theme,
            actor=actor,
            permission_level=permission_level,
            entry_ids=entry_ids,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            created_at=_ts(),
            updated_at=_ts(),
            provenance=provenance,
        )
        # Update entries to reference this bundle
        entries = self._load(self.entries_path)
        for e in entries:
            if e.get("entry_id") in entry_ids:
                bids = list(e.get("bundle_ids") or [])
                if bundle.bundle_id not in bids:
                    bids.append(bundle.bundle_id)
                e["bundle_ids"] = bids
        self._save(self.entries_path, entries)

        bundles = self._load(self.bundles_path)
        bundles.append(asdict(bundle))
        self._save(self.bundles_path, bundles)
        self._audit("bundle_created", bundle.bundle_id, actor, {"title": title, "entries": len(entry_ids)})
        return bundle

    def get_bundle(self, bundle_id: str) -> dict | None:
        for r in self._load(self.bundles_path):
            if r.get("bundle_id") == bundle_id:
                return r
        return None

    def list_bundles(self, actor_permission: str = "family") -> list[dict]:
        permission_order = ["family", "adults_only", "chris_only", "archive"]
        actor_idx = permission_order.index(actor_permission) if actor_permission in permission_order else 0
        results = []
        for r in self._load(self.bundles_path):
            if r.get("status") == "archived":
                continue
            entry_perm = r.get("permission_level", "family")
            entry_idx = permission_order.index(entry_perm) if entry_perm in permission_order else 0
            if entry_idx > actor_idx:
                continue
            results.append(r)
        return results

    def export_bundle(self, bundle_id: str, actor: str) -> dict[str, Any]:
        """Export a bundle with its full entry contents for archival."""
        bundle = self.get_bundle(bundle_id)
        if not bundle:
            return {"error": "bundle not found", "bundle_id": bundle_id}

        entry_ids = bundle.get("entry_ids", [])
        entries = [
            e for e in self._load(self.entries_path)
            if e.get("entry_id") in entry_ids
        ]

        export = {
            "export_type": "legacy_bundle",
            "bundle": bundle,
            "entries": entries,
            "entry_count": len(entries),
            "exported_at": _ts(),
            "exported_by": actor,
            "format_version": "1.0",
        }
        self._audit("bundle_exported", bundle_id, actor, {"entry_count": len(entries)})

        # Mark as exported
        bundles = self._load(self.bundles_path)
        for b in bundles:
            if b.get("bundle_id") == bundle_id:
                b["exported_at"] = _ts()
                break
        self._save(self.bundles_path, bundles)

        return export
