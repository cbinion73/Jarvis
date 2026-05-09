from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .models import MemoryEntry, MemoryProposal, UserProfile


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalCipher:
    def __init__(self, key_path: Path) -> None:
        try:
            from cryptography.fernet import Fernet
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("cryptography is required for the memory subsystem.") from exc

        self._fernet_cls = Fernet
        self.key_path = key_path
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.key_path.exists():
            self.key_path.write_bytes(Fernet.generate_key())
        self._fernet = Fernet(self.key_path.read_bytes())

    def encrypt_json(self, payload: dict) -> str:
        return self._fernet.encrypt(json.dumps(payload).encode("utf-8")).decode("utf-8")

    def decrypt_json(self, token: str) -> dict:
        raw = self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        return json.loads(raw)


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.entries_path = self.root / "entries.json"
        self.proposals_path = self.root / "proposals.json"

    def _load_json(self, path: Path, default: object) -> object:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _entries(self) -> list[dict]:
        payload = self._load_json(self.entries_path, [])
        return payload if isinstance(payload, list) else []

    def _save_entries(self, records: list[dict]) -> None:
        self._save_json(self.entries_path, records)

    def add_entry(self, entry: MemoryEntry) -> dict:
        records = self._entries()
        payload = asdict(entry)
        records.append(payload)
        self._save_entries(records)
        return payload

    def list_entries(self) -> list[dict]:
        return self._entries()

    def remove_entry(self, entry_id: str) -> dict | None:
        records = self._entries()
        remaining = []
        removed = None
        for item in records:
            if item["entry_id"] == entry_id:
                removed = item
            else:
                remaining.append(item)
        if removed is not None:
            self._save_entries(remaining)
        return removed

    def _proposals(self) -> list[dict]:
        payload = self._load_json(self.proposals_path, [])
        return payload if isinstance(payload, list) else []

    def _save_proposals(self, records: list[dict]) -> None:
        self._save_json(self.proposals_path, records)

    def add_proposal(self, proposal: MemoryProposal) -> dict:
        records = self._proposals()
        payload = asdict(proposal)
        records.append(payload)
        self._save_proposals(records)
        return payload

    def list_proposals(self) -> list[dict]:
        return self._proposals()

    def update_proposal_status(self, proposal_id: str, status: str) -> dict | None:
        records = self._proposals()
        updated = None
        for item in records:
            if item["proposal_id"] == proposal_id:
                item["status"] = status
                updated = item
                break
        if updated is not None:
            self._save_proposals(records)
        return updated


class MemorySupport:
    def __init__(self, config: AppConfig, store: MemoryStore) -> None:
        self.config = config
        self.store = store
        self.profile = config.load_json_profile(
            config.memory_profile_path,
            {
                "schemas": {},
                "boundaries": {},
                "sensitiveApprovalRules": {
                    "typesRequiringApproval": [],
                    "keywordsRequiringApproval": [],
                },
                "cloudExclusion": {
                    "excludeSensitive": True,
                    "excludedTags": [],
                    "notes": [],
                },
                "encryption": {
                    "algorithm": "fernet",
                    "keyPath": "data/memory/fernet.key",
                },
                "reviewNotes": [],
            },
        )
        key_path = Path(self.profile.get("encryption", {}).get("keyPath", "data/memory/fernet.key"))
        self.cipher = LocalCipher(key_path)

    def schemas(self) -> dict:
        return self.profile.get("schemas", {})

    def _normalize_tags(self, tags: list[str], memory_type: str) -> list[str]:
        defaults = self.schemas().get(memory_type, {}).get("defaultTags", [])
        merged = []
        for tag in [*defaults, *tags]:
            normalized = tag.strip().lower().replace(" ", "-")
            if normalized and normalized not in merged:
                merged.append(normalized)
        return merged

    def _requires_approval(self, memory_type: str, summary: str, detail: str, tags: list[str]) -> tuple[bool, str]:
        rules = self.profile.get("sensitiveApprovalRules", {})
        types = set(rules.get("typesRequiringApproval", []))
        keywords = [item.lower() for item in rules.get("keywordsRequiringApproval", [])]
        haystack = " ".join([summary, detail, " ".join(tags)]).lower()
        if memory_type in types:
            return True, f"Memory type '{memory_type}' requires approval before storage."
        for keyword in keywords:
            if keyword and keyword in haystack:
                return True, f"Sensitive keyword '{keyword}' triggered approval before storage."
        return False, ""

    def _cloud_excluded(self, sensitivity: str, tags: list[str]) -> bool:
        policy = self.profile.get("cloudExclusion", {})
        excluded_tags = {item.lower() for item in policy.get("excludedTags", [])}
        return (policy.get("excludeSensitive", True) and sensitivity == "sensitive") or bool(excluded_tags.intersection(set(tags)))

    def _title_from_summary(self, summary: str) -> str:
        cleaned = summary.strip().split(".")[0].strip()
        return cleaned[:80] or "Untitled memory"

    def remember(
        self,
        actor: UserProfile,
        memory_type: str,
        scope: str,
        summary: str,
        detail: str,
        owner: str = "",
        project: str = "",
        tags: list[str] | None = None,
        sensitivity: str = "normal",
    ) -> dict:
        tag_list = self._normalize_tags(tags or [], memory_type)
        resolved_owner = owner or actor.display_name
        title = self._title_from_summary(summary)
        needs_approval, rationale = self._requires_approval(memory_type, summary, detail, tag_list)
        payload = {
            "detail": detail,
            "owner": resolved_owner,
            "project": project,
            "captured_by": actor.display_name,
            "scope": scope,
            "memory_type": memory_type,
            "hash": hashlib.sha256(detail.encode("utf-8")).hexdigest(),
        }
        if needs_approval or sensitivity == "sensitive":
            proposal = MemoryProposal(
                proposal_id=str(uuid.uuid4()),
                actor=actor.display_name,
                memory_type=memory_type,
                scope=scope,
                owner=resolved_owner,
                project=project,
                title=title,
                summary=summary,
                tags=tag_list,
                sensitivity="sensitive",
                payload=payload,
                status="pending",
                rationale=rationale or "Sensitive memory requires explicit review before storage.",
                created_at=_now_iso(),
            )
            return {"stored": False, "proposal": self.store.add_proposal(proposal), "needs_approval": True}

        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            memory_type=memory_type,
            scope=scope,
            owner=resolved_owner,
            project=project,
            title=title,
            summary=summary,
            tags=tag_list,
            sensitivity=sensitivity,
            approval_status="approved",
            cloud_excluded=self._cloud_excluded(sensitivity, tag_list),
            encrypted_payload=self.cipher.encrypt_json(payload),
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        return {"stored": True, "entry": self.store.add_entry(entry), "needs_approval": False}

    def _viewer_allowed(self, viewer: UserProfile, entry: dict) -> bool:
        if viewer.permissions == "adult":
            return True
        boundaries = self.profile.get("boundaries", {})
        scope = entry.get("scope", "")
        memory_type = entry.get("memory_type", "")
        owner = entry.get("owner", "")
        if memory_type == "personal" and boundaries.get("childCanViewOwnPersonal", True):
            return owner == viewer.display_name
        if memory_type == "household":
            return bool(boundaries.get("childCanViewHousehold", False))
        if memory_type == "project":
            return bool(boundaries.get("childCanViewProject", False))
        if memory_type == "safety":
            return bool(boundaries.get("childCanViewSafety", False))
        if scope == "personal":
            return owner == viewer.display_name
        return False

    def review(
        self,
        viewer: UserProfile,
        memory_type: str = "",
        owner: str = "",
        project: str = "",
        include_payload: bool = False,
    ) -> list[dict]:
        results = []
        for item in self.store.list_entries():
            if memory_type and item.get("memory_type") != memory_type:
                continue
            if owner and item.get("owner") != owner:
                continue
            if project and item.get("project") != project:
                continue
            if not self._viewer_allowed(viewer, item):
                continue
            payload = None
            if include_payload:
                payload = self.cipher.decrypt_json(item["encrypted_payload"])
            results.append(
                {
                    "entry_id": item["entry_id"],
                    "memory_type": item["memory_type"],
                    "scope": item["scope"],
                    "owner": item["owner"],
                    "project": item["project"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "tags": item["tags"],
                    "sensitivity": item["sensitivity"],
                    "approval_status": item["approval_status"],
                    "cloud_excluded": item["cloud_excluded"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "payload": payload,
                }
            )
        return list(reversed(results))

    def forget(self, viewer: UserProfile, entry_id: str) -> dict:
        removed = None
        for item in self.store.list_entries():
            if item["entry_id"] == entry_id:
                if not self._viewer_allowed(viewer, item):
                    raise PermissionError("Viewer is not allowed to forget this memory entry.")
                removed = item
                break
        if removed is None:
            raise KeyError(f"Unknown memory entry: {entry_id}")
        self.store.remove_entry(entry_id)
        return {
            "forgotten": True,
            "entry_id": entry_id,
            "title": removed["title"],
            "owner": removed["owner"],
        }

    def export(self, viewer: UserProfile, memory_type: str = "", owner: str = "", project: str = "") -> dict:
        entries = self.review(viewer, memory_type=memory_type, owner=owner, project=project, include_payload=True)
        return {
            "exported_at": _now_iso(),
            "viewer": viewer.display_name,
            "count": len(entries),
            "entries": entries,
            "cloud_exclusion_notes": self.profile.get("cloudExclusion", {}).get("notes", []),
        }

    def proposals(self, status: str = "") -> list[dict]:
        items = self.store.list_proposals()
        if status:
            items = [item for item in items if item.get("status") == status]
        return list(reversed(items))

    def resolve_proposal(self, proposal_id: str, decision: str) -> dict:
        proposal = None
        for item in self.store.list_proposals():
            if item["proposal_id"] == proposal_id:
                proposal = item
                break
        if proposal is None:
            raise KeyError(f"Unknown memory proposal: {proposal_id}")
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        self.store.update_proposal_status(proposal_id, decision)
        if decision == "rejected":
            return {"proposal_id": proposal_id, "status": "rejected"}
        payload = proposal["payload"]
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            memory_type=proposal["memory_type"],
            scope=proposal["scope"],
            owner=proposal["owner"],
            project=proposal["project"],
            title=proposal["title"],
            summary=proposal["summary"],
            tags=proposal["tags"],
            sensitivity=proposal["sensitivity"],
            approval_status="approved",
            cloud_excluded=self._cloud_excluded(proposal["sensitivity"], proposal["tags"]),
            encrypted_payload=self.cipher.encrypt_json(payload),
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        stored = self.store.add_entry(entry)
        return {"proposal_id": proposal_id, "status": "approved", "entry": stored}

    def overview(self, viewer: UserProfile) -> dict:
        visible = self.review(viewer, include_payload=False)
        by_type: dict[str, int] = {}
        by_owner: dict[str, int] = {}
        cloud_excluded = 0
        for item in visible:
            by_type[item["memory_type"]] = by_type.get(item["memory_type"], 0) + 1
            by_owner[item["owner"]] = by_owner.get(item["owner"], 0) + 1
            if item["cloud_excluded"]:
                cloud_excluded += 1
        return {
            "viewer": viewer.display_name,
            "schemas": self.schemas(),
            "review_notes": self.profile.get("reviewNotes", []),
            "counts": {
                "visible_entries": len(visible),
                "cloud_excluded_entries": cloud_excluded,
                "pending_proposals": len([item for item in self.store.list_proposals() if item.get("status") == "pending"]),
            },
            "by_type": by_type,
            "by_owner": by_owner,
            "recent_entries": visible[:8],
            "pending_proposals": self.proposals(status="pending")[:8],
            "encryption": {
                "algorithm": self.profile.get("encryption", {}).get("algorithm", "fernet"),
                "key_path": self.profile.get("encryption", {}).get("keyPath", ""),
            },
            "cloud_exclusion": self.profile.get("cloudExclusion", {}),
        }
