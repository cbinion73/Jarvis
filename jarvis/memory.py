from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .data_hygiene import filter_records
from .identity import IdentityRegistry
from .models import MemoryEntry, MemoryProfileFact, MemoryProposal, UserProfile
from .persistence import append_jsonl, atomic_write_json
from .state_log_utils import read_jsonl_tail


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
        self.facts_path = self.root / "profile_facts.json"

    def _log_path(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}_log.jsonl")

    def _state_log_path(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}_state_log.jsonl")

    def _load_json(self, path: Path, default: object) -> object:
        if not path.exists():
            return self._load_json_from_state_log(path, default)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload not in ({}, [], ""):
                return payload
            return self._load_json_from_state_log(path, default)
        except (OSError, json.JSONDecodeError):
            return self._load_json_from_state_log(path, default)

    def _load_json_from_state_log(self, path: Path, default: object) -> object:
        try:
            state_log_path = self._state_log_path(path)
            if not state_log_path.exists():
                return self._load_json_from_log(path, default)
            latest: object = default
            for payload in read_jsonl_tail(state_log_path):
                if "payload" in payload:
                    latest = payload["payload"]
            return latest
        except (OSError, json.JSONDecodeError):
            return self._load_json_from_log(path, default)

    def _load_json_from_log(self, path: Path, default: object) -> object:
        try:
            log_path = self._log_path(path)
            if not log_path.exists():
                return default
            latest: object = default
            for payload in read_jsonl_tail(log_path):
                if "payload" in payload:
                    latest = payload["payload"]
            return latest
        except (OSError, json.JSONDecodeError):
            return default

    def _save_json(self, path: Path, payload: object) -> None:
        saved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_write_json(path, payload)
        append_jsonl(
            self._log_path(path),
            {
                "saved_at": saved_at,
                "payload": payload,
            },
        )
        append_jsonl(
            self._state_log_path(path),
            {
                "saved_at": saved_at,
                "payload": payload,
            },
        )

    def _entries(self) -> list[dict]:
        payload = self._load_json(self.entries_path, [])
        records = payload if isinstance(payload, list) else []
        cleaned = [self._coerce_entry_record(item) for item in records if isinstance(item, dict)]
        return filter_records(cleaned)

    def _save_entries(self, records: list[dict]) -> None:
        self._save_json(self.entries_path, records)

    def add_entry(self, entry: MemoryEntry) -> dict:
        # I5: Enforce Chronicle boundary at write time.
        # Faith-tagged content must not be stored in JARVIS memory; it belongs
        # to Chronicle.  Fail open (boundary check failure → allow write) so
        # legitimate entries are never silently dropped.
        try:
            from .chronicle_boundary import enforce_routing
            tags = list(entry.tags) if entry.tags else []
            domain = str(getattr(entry, "lane", "") or "")
            content = " ".join(filter(None, [
                str(getattr(entry, "title", "") or ""),
                str(getattr(entry, "summary", "") or ""),
            ]))
            routing = enforce_routing(
                actor=str(entry.owner or "system"),
                content_type="memory_entry",
                tags=tags,
                domain=domain,
                content=content,
            )
            if not routing.get("allowed", True):
                raise ValueError(
                    f"Chronicle boundary: this entry belongs to Chronicle, not JARVIS memory. "
                    f"Reason: {routing.get('reason', '')} "
                    f"Action: {routing.get('action_required', '')}"
                )
        except ValueError:
            raise  # re-raise boundary violations
        except Exception:
            pass  # fail open on unexpected errors

        # I2: Enforce provenance field at write time.
        # Entries with an unrecognised provenance value are rejected so garbage
        # data cannot enter the memory store silently.
        entry_provenance = str(getattr(entry, "provenance", "") or "").strip()
        if entry_provenance:
            try:
                from .models import MEMORY_PROVENANCE_VALUES
                if entry_provenance not in MEMORY_PROVENANCE_VALUES:
                    raise ValueError(
                        f"Provenance enforcement: '{entry_provenance}' is not a valid provenance value. "
                        f"Must be one of: {sorted(MEMORY_PROVENANCE_VALUES)}"
                    )
            except ValueError:
                raise
            except Exception:
                pass  # fail open if models import fails unexpectedly

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

    def get_entry(self, entry_id: str) -> dict | None:
        for item in self._entries():
            if item.get("entry_id") == entry_id:
                return item
        return None

    def correct_entry(self, entry_id: str, correction: str, actor: str) -> dict | None:
        """Mark an entry as corrected, excluding it from reasoning queries.

        Also cascades to any profile fact derived from this entry so the
        fact is immediately excluded from converse() context injection.
        """
        import time as _time
        records = self._entries()
        updated = None
        for item in records:
            if item.get("entry_id") == entry_id:
                item["approval_status"] = "corrected"
                item["correction_note"] = correction
                item["corrected_by"] = actor
                item["corrected_at"] = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
                item["updated_at"] = item["corrected_at"]
                updated = item
                break
        if updated is not None:
            self._save_entries(records)
            # Cascade: retire any profile fact that was promoted from this entry.
            # Profile facts store entry_id as their source_entry_id field.
            facts = self.list_profile_facts()
            changed = False
            for fact in facts:
                if fact.get("source_entry_id") == entry_id and fact.get("status", "active") == "active":
                    fact["status"] = "corrected"
                    fact["correction_note"] = correction
                    fact["updated_at"] = updated["corrected_at"]
                    changed = True
            if changed:
                self._save_json(self.facts_path, facts)
        return updated

    def _proposals(self) -> list[dict]:
        payload = self._load_json(self.proposals_path, [])
        records = payload if isinstance(payload, list) else []
        cleaned = [self._coerce_proposal_record(item) for item in records if isinstance(item, dict)]
        return filter_records(cleaned)

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

    def list_profile_facts(self) -> list[dict]:
        payload = self._load_json(self.facts_path, [])
        records = payload if isinstance(payload, list) else []
        cleaned = [self._coerce_fact_record(item) for item in records if isinstance(item, dict)]
        return filter_records(cleaned)

    def migrate_records(self) -> None:
        entries = self._entries()
        proposals = self._proposals()
        facts = self.list_profile_facts()
        self._save_entries(entries)
        self._save_proposals(proposals)
        self._save_json(self.facts_path, facts)

    def upsert_profile_fact(self, fact: MemoryProfileFact) -> dict:
        records = self.list_profile_facts()
        payload = asdict(fact)
        next_records: list[dict] = []
        replaced = False
        for item in records:
            if item.get("fact_id") == fact.fact_id:
                next_records.append(payload)
                replaced = True
            else:
                next_records.append(item)
        if not replaced:
            next_records.append(payload)
        self._save_json(self.facts_path, next_records)
        return payload

    def update_profile_fact_status(self, fact_id: str, status: str) -> dict | None:
        records = self.list_profile_facts()
        updated = None
        for item in records:
            if item.get("fact_id") == fact_id:
                item["status"] = status
                item["updated_at"] = _now_iso()
                updated = item
                break
        if updated is not None:
            self._save_json(self.facts_path, records)
        return updated

    def correct_profile_fact(self, fact_id: str, correction_note: str) -> dict | None:
        """Mark a fact as corrected; excluded from inference until re-approved."""
        records = self.list_profile_facts()
        updated = None
        for item in records:
            if item.get("fact_id") == fact_id:
                item["status"] = "corrected"
                item["correction_note"] = str(correction_note or "")
                item["updated_at"] = _now_iso()
                updated = item
                break
        if updated is not None:
            self._save_json(self.facts_path, records)
        return updated

    def dispute_profile_fact(self, fact_id: str, dispute_note: str) -> dict | None:
        """Mark a fact as disputed; not yet retired but flagged for review."""
        records = self.list_profile_facts()
        updated = None
        for item in records:
            if item.get("fact_id") == fact_id:
                item["status"] = "disputed"
                item["correction_note"] = str(dispute_note or "")
                item["updated_at"] = _now_iso()
                updated = item
                break
        if updated is not None:
            self._save_json(self.facts_path, records)
        return updated

    def retire_profile_fact(self, fact_id: str, reason: str = "") -> dict | None:
        """Permanently retire a fact; excluded from all reasoning."""
        records = self.list_profile_facts()
        updated = None
        for item in records:
            if item.get("fact_id") == fact_id:
                item["status"] = "retired"
                item["correction_note"] = str(reason or "")
                item["updated_at"] = _now_iso()
                updated = item
                break
        if updated is not None:
            self._save_json(self.facts_path, records)
        return updated

    def supersede_profile_fact(self, fact_id: str, new_fact_id: str, reason: str = "") -> dict | None:
        """Mark a fact as superseded by a newer fact."""
        records = self.list_profile_facts()
        updated = None
        for item in records:
            if item.get("fact_id") == fact_id:
                item["status"] = "superseded"
                item["superseded_by"] = str(new_fact_id or "")
                item["correction_note"] = str(reason or "")
                item["updated_at"] = _now_iso()
                updated = item
                break
        if updated is not None:
            self._save_json(self.facts_path, records)
        return updated

    def retrieve_by_situation(
        self,
        actor: str,
        situation_context: dict,
    ) -> list[dict]:
        """D8 / I1: Retrieve memory facts ranked by situational relevance.

        situation_context keys (all optional):
          person, domain, task, season, relationship  — original D8 dimensions
          unresolved_loop — keyword; matches facts whose title/summary indicates
                            an open loop or unresolved item
          lesson          — if truthy, boosts facts tagged lesson/learned/mistake
        Returns facts sorted by match score descending, each with a retrieval_reason.
        """
        facts = self.list_profile_facts()
        actor_lower = actor.strip().lower()
        person = str(situation_context.get("person") or "").strip().lower()
        domain = str(situation_context.get("domain") or "").strip().lower()
        task = str(situation_context.get("task") or "").strip().lower()
        season = str(situation_context.get("season") or "").strip().lower()
        relationship = str(situation_context.get("relationship") or "").strip().lower()
        # I1 additions
        unresolved_loop = str(situation_context.get("unresolved_loop") or "").strip().lower()
        lesson = bool(situation_context.get("lesson"))

        _UNRESOLVED_MARKERS = frozenset({"open", "unresolved", "pending", "blocked", "loop", "follow-up"})
        _LESSON_TAGS = frozenset({"lesson", "learned", "mistake", "retrospective", "post-mortem"})

        from .models import MEMORY_EXCLUDED_FROM_REASONING
        scored: list[tuple[int, str, dict]] = []
        for fact in facts:
            if fact.get("status") in MEMORY_EXCLUDED_FROM_REASONING:
                continue
            subject = str(fact.get("subject_user_id") or "").strip().lower()
            lane = str(fact.get("lane") or "").strip().lower()
            tags = [str(t).strip().lower() for t in (fact.get("tags") or [])]
            title_lower = str(fact.get("title") or "").strip().lower()
            summary_lower = str(fact.get("summary") or "").strip().lower()
            text_blob = title_lower + " " + summary_lower

            score = 0
            reasons: list[str] = []

            if person and (person == subject or person in title_lower or person in summary_lower):
                score += 4
                reasons.append(f"person:{person}")
            if actor_lower and actor_lower == subject:
                score += 2
                reasons.append(f"actor:{actor_lower}")
            if domain and (domain in lane or domain in tags or domain in title_lower):
                score += 3
                reasons.append(f"domain:{domain}")
            if task and (task in title_lower or task in summary_lower or task in tags):
                score += 3
                reasons.append(f"task:{task}")
            if relationship and (relationship in tags or relationship in lane):
                score += 2
                reasons.append(f"relationship:{relationship}")
            if season and (season in tags or season in summary_lower):
                score += 1
                reasons.append(f"season:{season}")

            # I1: unresolved_loop dimension — keyword match + structural open-loop markers
            if unresolved_loop and unresolved_loop in text_blob:
                score += 3
                reasons.append(f"unresolved_loop:{unresolved_loop}")
            elif unresolved_loop and any(m in text_blob for m in _UNRESOLVED_MARKERS):
                score += 2
                reasons.append("unresolved_loop:marker")
            elif any(t in tags for t in ("open", "unresolved", "pending", "loop")):
                # Even without context key, open-loop facts get a passive boost
                score += 1
                reasons.append("open_loop_tag")

            # I1: lesson dimension — facts about past mistakes or retrospectives
            if lesson and any(t in tags for t in _LESSON_TAGS):
                score += 3
                reasons.append("lesson:tag")
            elif lesson and any(kw in text_blob for kw in _LESSON_TAGS):
                score += 2
                reasons.append("lesson:text")

            if score == 0:
                continue
            retrieval_reason = ", ".join(reasons) if reasons else "general"
            enriched = dict(fact)
            enriched["retrieval_reason"] = retrieval_reason
            enriched["retrieval_score"] = score
            scored.append((score, fact.get("fact_id", ""), enriched))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [item for _, _, item in scored]

    def _coerce_entry_record(self, item: dict) -> dict:
        item = dict(item)
        if not str(item.get("subject_user_id", "")).strip() and str(item.get("memory_type", "")).strip().lower() == "personal":
            owner = str(item.get("owner", "")).strip()
            item["subject_user_id"] = owner.lower() if owner else ""
        item["access_policy"] = self._normalized_access_policy(item)
        item.setdefault("boundary_label", "")
        item.setdefault("source_type", "user-stated")
        item.setdefault("confidence", "confirmed")
        item.setdefault("provenance", "observed_fact")
        return item

    def _coerce_proposal_record(self, item: dict) -> dict:
        item = dict(item)
        if not str(item.get("subject_user_id", "")).strip() and str(item.get("memory_type", "")).strip().lower() == "personal":
            owner = str(item.get("owner", "")).strip()
            item["subject_user_id"] = owner.lower() if owner else ""
        item["access_policy"] = self._normalized_access_policy(item)
        item.setdefault("boundary_label", "")
        item.setdefault("source_type", "user-stated")
        item.setdefault("confidence", "confirmed")
        return item

    def _coerce_fact_record(self, item: dict) -> dict:
        item = dict(item)
        item.setdefault("source_entry_ids", [])
        item.setdefault("tags", [])
        item.setdefault("confidence", "confirmed")
        item.setdefault("status", "active")
        item.setdefault("source_type", "user-stated")
        item.setdefault("boundary_label", "")
        item.setdefault("provenance", "observed_fact")
        item.setdefault("correction_note", "")
        item.setdefault("superseded_by", "")
        return item

    def _legacy_access_policy(self, item: dict) -> str:
        memory_type = str(item.get("memory_type", "")).strip().lower()
        scope = str(item.get("scope", "")).strip().lower()
        if memory_type == "safety" or scope == "safety":
            return "restricted"
        if memory_type == "project" or scope == "project":
            return "shared"
        if memory_type == "household" or scope == "household":
            return "household"
        return "personal"

    def _normalized_access_policy(self, item: dict) -> str:
        access_policy = str(item.get("access_policy", "")).strip().lower()
        legacy_default = self._legacy_access_policy(item)
        if not access_policy or access_policy == "personal" and legacy_default != "personal":
            return legacy_default
        return access_policy


class MemorySupport:
    def __init__(self, config: AppConfig, store: MemoryStore, identity_registry: IdentityRegistry | None = None) -> None:
        self.config = config
        self.store = store
        self.identity_registry = identity_registry
        self.profile = config.load_json_profile(
            config.memory_profile_path,
            {
                "schemas": {},
                "boundaries": {},
                "partitionRules": {
                    "defaultPersonalAccess": "personal",
                    "defaultHouseholdAccess": "household",
                    "defaultProjectAccess": "shared",
                    "defaultSafetyAccess": "restricted",
                },
                "promotionRules": {
                    "promotePersonalToProfileFacts": True,
                    "promoteHouseholdPatterns": True,
                    "notes": [],
                },
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
        self.store.migrate_records()

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

    def _cloud_excluded(self, sensitivity: str, tags: list[str], access_policy: str = "", boundary_label: str = "") -> bool:
        policy = self.profile.get("cloudExclusion", {})
        excluded_tags = {item.lower() for item in policy.get("excludedTags", [])}
        if access_policy in {"personal", "restricted"}:
            return True
        if boundary_label in {"child", "child-private"}:
            return True
        return (policy.get("excludeSensitive", True) and sensitivity == "sensitive") or bool(excluded_tags.intersection(set(tags)))

    def _title_from_summary(self, summary: str) -> str:
        cleaned = summary.strip().split(".")[0].strip()
        return cleaned[:80] or "Untitled memory"

    def _member_record(self, user_ref: str) -> dict:
        if self.identity_registry is not None:
            member = self.identity_registry.member(user_ref)
            if member is not None:
                return member.to_dict()
        fallback = str(user_ref).strip()
        return {
            "user_id": fallback.lower(),
            "display_name": fallback,
            "permissions": "adult",
            "privacy_boundary": "personal",
            "trust_level": "trusted",
        }

    def _resolve_subject(self, actor: UserProfile, owner: str, subject_user_id: str, scope: str, memory_type: str) -> tuple[str, str]:
        explicit_subject = str(subject_user_id).strip()
        if explicit_subject:
            member = self._member_record(explicit_subject)
            return str(member.get("user_id", explicit_subject)).strip().lower(), str(member.get("display_name", owner or actor.display_name)).strip()
        owner_name = str(owner).strip()
        if owner_name:
            member = self._member_record(owner_name)
            return str(member.get("user_id", owner_name)).strip().lower(), str(member.get("display_name", owner_name)).strip()
        if scope == "personal" or memory_type == "personal":
            member = self._member_record(actor.user_id or actor.display_name)
            return str(member.get("user_id", actor.user_id)).strip().lower(), str(member.get("display_name", actor.display_name)).strip()
        return "", owner_name or actor.display_name

    def _default_access_policy(self, memory_type: str, scope: str) -> str:
        rules = self.profile.get("partitionRules", {})
        if memory_type == "safety" or scope == "safety":
            return str(rules.get("defaultSafetyAccess", "restricted"))
        if memory_type == "project" or scope == "project":
            return str(rules.get("defaultProjectAccess", "shared"))
        if memory_type == "household" or scope == "household":
            return str(rules.get("defaultHouseholdAccess", "household"))
        return str(rules.get("defaultPersonalAccess", "personal"))

    def _boundary_label_for(self, subject_user_id: str, access_policy: str) -> str:
        if access_policy == "restricted":
            return "restricted"
        if not subject_user_id:
            return "shared"
        member = self._member_record(subject_user_id)
        privacy_boundary = str(member.get("privacy_boundary", "personal")).strip().lower() or "personal"
        if privacy_boundary == "child" and access_policy == "personal":
            return "child-private"
        return privacy_boundary

    def _fact_id_for(self, subject_user_id: str, lane: str, summary: str) -> str:
        seed = f"{subject_user_id}|{lane}|{summary.strip().lower()}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]

    def _effective_subject_user_id(self, item: dict) -> str:
        subject_user_id = str(item.get("subject_user_id", "")).strip().lower()
        if subject_user_id:
            return subject_user_id
        if str(item.get("memory_type", "")).strip().lower() == "personal":
            owner = str(item.get("owner", "")).strip()
            member = self._member_record(owner)
            return str(member.get("user_id", "")).strip().lower()
        return ""

    def _effective_access_policy(self, item: dict) -> str:
        access_policy = str(item.get("access_policy", "")).strip().lower()
        if access_policy:
            return access_policy
        return self._default_access_policy(str(item.get("memory_type", "")), str(item.get("scope", "")))

    def _effective_boundary_label(self, item: dict) -> str:
        boundary_label = str(item.get("boundary_label", "")).strip()
        if boundary_label:
            return boundary_label
        return self._boundary_label_for(self._effective_subject_user_id(item), self._effective_access_policy(item))

    def _candidate_profile_fact(self, entry: dict, payload: dict) -> MemoryProfileFact | None:
        promote = self.profile.get("promotionRules", {})
        memory_type = str(entry.get("memory_type", "")).strip().lower()
        if memory_type == "personal" and not promote.get("promotePersonalToProfileFacts", True):
            return None
        if memory_type == "household" and not promote.get("promoteHouseholdPatterns", True):
            return None
        if memory_type not in {"personal", "household"}:
            return None
        subject_user_id = str(entry.get("subject_user_id", "")).strip().lower()
        if not subject_user_id and memory_type == "personal":
            return None
        member = self._member_record(subject_user_id) if subject_user_id else {"display_name": "Household"}
        title = str(entry.get("title", "")).strip() or self._title_from_summary(str(entry.get("summary", "")))
        return MemoryProfileFact(
            fact_id=self._fact_id_for(subject_user_id or "household", memory_type, str(entry.get("summary", ""))),
            subject_user_id=subject_user_id,
            subject_display_name=str(member.get("display_name", "Household")).strip() or "Household",
            lane=memory_type,
            title=title,
            summary=str(entry.get("summary", "")).strip(),
            tags=list(entry.get("tags", [])),
            source_entry_ids=[str(entry.get("entry_id", "")).strip()],
            confidence=str(payload.get("confidence") or entry.get("confidence") or "confirmed").strip() or "confirmed",
            status="active",
            source_type=str(payload.get("source_type") or entry.get("source_type") or "user-stated").strip() or "user-stated",
            boundary_label=str(entry.get("boundary_label", "")).strip(),
            created_at=_now_iso(),
            updated_at=_now_iso(),
            provenance=str(payload.get("provenance") or entry.get("provenance") or "observed_fact").strip() or "observed_fact",
        )

    def _promote_entry_to_profile_fact(self, entry: dict, payload: dict) -> dict | None:
        candidate = self._candidate_profile_fact(entry, payload)
        if candidate is None:
            return None
        existing = next((item for item in self.store.list_profile_facts() if item.get("fact_id") == candidate.fact_id), None)
        if existing:
            source_entry_ids = sorted(set([*existing.get("source_entry_ids", []), *candidate.source_entry_ids]))
            candidate = MemoryProfileFact(
                fact_id=candidate.fact_id,
                subject_user_id=candidate.subject_user_id,
                subject_display_name=candidate.subject_display_name,
                lane=candidate.lane,
                title=candidate.title,
                summary=candidate.summary,
                tags=sorted(set([*existing.get("tags", []), *candidate.tags])),
                source_entry_ids=source_entry_ids,
                confidence=candidate.confidence if candidate.confidence != "provisional" else str(existing.get("confidence", "confirmed")),
                status="active",
                source_type=candidate.source_type,
                boundary_label=candidate.boundary_label,
                created_at=str(existing.get("created_at", candidate.created_at)),
                updated_at=_now_iso(),
                provenance=str(existing.get("provenance", candidate.provenance)).strip() or candidate.provenance,
            )
        stored = self.store.upsert_profile_fact(candidate)
        return {"fact": stored, "status": "updated" if existing else "created"}

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
        subject_user_id: str = "",
        access_policy: str = "",
        source_type: str = "user-stated",
        confidence: str = "confirmed",
        provenance: str = "observed_fact",
    ) -> dict:
        tag_list = self._normalize_tags(tags or [], memory_type)
        resolved_subject_user_id, resolved_owner = self._resolve_subject(actor, owner, subject_user_id, scope, memory_type)
        resolved_access_policy = str(access_policy).strip().lower() or self._default_access_policy(memory_type, scope)
        boundary_label = self._boundary_label_for(resolved_subject_user_id, resolved_access_policy)
        title = self._title_from_summary(summary)
        needs_approval, rationale = self._requires_approval(memory_type, summary, detail, tag_list)
        payload = {
            "detail": detail,
            "owner": resolved_owner,
            "subject_user_id": resolved_subject_user_id,
            "project": project,
            "captured_by": actor.display_name,
            "scope": scope,
            "memory_type": memory_type,
            "source_type": source_type,
            "confidence": confidence,
            "provenance": provenance,
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
                subject_user_id=resolved_subject_user_id,
                access_policy=resolved_access_policy,
                boundary_label=boundary_label,
                source_type=source_type,
                confidence=confidence,
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
            cloud_excluded=self._cloud_excluded(sensitivity, tag_list, resolved_access_policy, boundary_label),
            encrypted_payload=self.cipher.encrypt_json(payload),
            created_at=_now_iso(),
            updated_at=_now_iso(),
            subject_user_id=resolved_subject_user_id,
            access_policy=resolved_access_policy,
            boundary_label=boundary_label,
            source_type=source_type,
            confidence=confidence,
            provenance=provenance,
        )
        stored = self.store.add_entry(entry)
        result = {"stored": True, "entry": stored, "needs_approval": False}
        promotion = self._promote_entry_to_profile_fact(stored, payload)
        if promotion:
            result["profile_promotion"] = promotion
        return result

    def _viewer_allowed(self, viewer: UserProfile, entry: dict) -> bool:
        boundaries = self.profile.get("boundaries", {})
        access_policy = self._effective_access_policy(entry)
        subject_user_id = self._effective_subject_user_id(entry)
        owner = str(entry.get("owner", "")).strip()
        viewer_matches_subject = bool(subject_user_id and subject_user_id == viewer.user_id)
        viewer_matches_owner = owner == viewer.display_name
        if viewer.permissions == "adult":
            if access_policy == "restricted":
                return bool(boundaries.get("adultCanViewAll", True)) or viewer_matches_subject or viewer_matches_owner
            return True
        boundaries = self.profile.get("boundaries", {})
        scope = entry.get("scope", "")
        memory_type = entry.get("memory_type", "")
        if access_policy == "restricted":
            return viewer_matches_subject or viewer_matches_owner
        if access_policy == "household":
            return bool(boundaries.get("childCanViewHousehold", False))
        if access_policy == "shared":
            return bool(boundaries.get("childCanViewProject", False))
        if memory_type == "personal" and boundaries.get("childCanViewOwnPersonal", True):
            return viewer_matches_subject or viewer_matches_owner
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
            effective_subject_user_id = self._effective_subject_user_id(item)
            effective_access_policy = self._effective_access_policy(item)
            effective_boundary_label = self._effective_boundary_label(item)
            effective_cloud_excluded = bool(item.get("cloud_excluded")) or self._cloud_excluded(
                str(item.get("sensitivity", "normal")),
                list(item.get("tags", [])),
                effective_access_policy,
                effective_boundary_label,
            )
            results.append(
                {
                    "entry_id": item["entry_id"],
                    "memory_type": item["memory_type"],
                    "scope": item["scope"],
                    "owner": item["owner"],
                    "subject_user_id": effective_subject_user_id,
                    "project": item["project"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "tags": item["tags"],
                    "sensitivity": item["sensitivity"],
                    "approval_status": item["approval_status"],
                    "cloud_excluded": effective_cloud_excluded,
                    "access_policy": effective_access_policy,
                    "boundary_label": effective_boundary_label,
                    "source_type": item.get("source_type", "user-stated"),
                    "confidence": item.get("confidence", "confirmed"),
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
            cloud_excluded=self._cloud_excluded(
                proposal["sensitivity"],
                proposal["tags"],
                str(proposal.get("access_policy", "")),
                str(proposal.get("boundary_label", "")),
            ),
            encrypted_payload=self.cipher.encrypt_json(payload),
            created_at=_now_iso(),
            updated_at=_now_iso(),
            subject_user_id=str(proposal.get("subject_user_id", "")).strip().lower(),
            access_policy=str(proposal.get("access_policy", "")).strip() or self._default_access_policy(proposal["memory_type"], proposal["scope"]),
            boundary_label=str(proposal.get("boundary_label", "")).strip(),
            source_type=str(proposal.get("source_type", "user-stated")).strip() or "user-stated",
            confidence=str(proposal.get("confidence", "confirmed")).strip() or "confirmed",
        )
        stored = self.store.add_entry(entry)
        result = {"proposal_id": proposal_id, "status": "approved", "entry": stored}
        promotion = self._promote_entry_to_profile_fact(stored, payload)
        if promotion:
            result["profile_promotion"] = promotion
        return result

    def overview(self, viewer: UserProfile) -> dict:
        visible = self.review(viewer, include_payload=False)
        by_type: dict[str, int] = {}
        by_owner: dict[str, int] = {}
        by_subject: dict[str, int] = {}
        cloud_excluded = 0
        for item in visible:
            by_type[item["memory_type"]] = by_type.get(item["memory_type"], 0) + 1
            by_owner[item["owner"]] = by_owner.get(item["owner"], 0) + 1
            subject_label = item.get("subject_user_id") or item["owner"]
            by_subject[subject_label] = by_subject.get(subject_label, 0) + 1
            if item["cloud_excluded"]:
                cloud_excluded += 1
        visible_facts = self.profile_facts(viewer)
        return {
            "viewer": viewer.display_name,
            "schemas": self.schemas(),
            "review_notes": self.profile.get("reviewNotes", []),
            "counts": {
                "visible_entries": len(visible),
                "cloud_excluded_entries": cloud_excluded,
                "pending_proposals": len([item for item in self.store.list_proposals() if item.get("status") == "pending"]),
                "visible_profile_facts": len(visible_facts),
            },
            "by_type": by_type,
            "by_owner": by_owner,
            "by_subject": by_subject,
            "recent_entries": visible[:8],
            "profile_facts": visible_facts[:8],
            "pending_proposals": self.proposals(status="pending")[:8],
            "encryption": {
                "algorithm": self.profile.get("encryption", {}).get("algorithm", "fernet"),
                "key_path": self.profile.get("encryption", {}).get("keyPath", ""),
            },
            "cloud_exclusion": self.profile.get("cloudExclusion", {}),
        }

    def approved_entries_for_context(self) -> list[dict]:
        entries: list[dict] = []
        for item in self.store.list_entries():
            payload = self.cipher.decrypt_json(item["encrypted_payload"])
            entries.append(
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
                    "cloud_excluded": bool(item.get("cloud_excluded")) or self._cloud_excluded(
                        str(item.get("sensitivity", "normal")),
                        list(item.get("tags", [])),
                        self._effective_access_policy(item),
                        self._effective_boundary_label(item),
                    ),
                    "subject_user_id": self._effective_subject_user_id(item),
                    "access_policy": self._effective_access_policy(item),
                    "boundary_label": self._effective_boundary_label(item),
                    "source_type": item.get("source_type", "user-stated"),
                    "confidence": item.get("confidence", "confirmed"),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "payload": payload,
                }
            )
        return list(reversed(entries))

    def profile_facts(self, viewer: UserProfile, subject_user_id: str = "") -> list[dict]:
        from .models import MEMORY_EXCLUDED_FROM_REASONING
        facts: list[dict] = []
        subject_filter = str(subject_user_id).strip().lower()
        for item in self.store.list_profile_facts():
            status = str(item.get("status", "active")).strip().lower()
            if status != "active":
                continue
            # Belt-and-suspenders: also check approval_status field for entries
            # that store it directly on the fact record.
            if str(item.get("approval_status", "")).strip().lower() in MEMORY_EXCLUDED_FROM_REASONING:
                continue
            candidate_entry = {
                "memory_type": item.get("lane", "personal"),
                "scope": "personal" if item.get("lane") == "personal" else "household",
                "owner": item.get("subject_display_name", ""),
                "subject_user_id": item.get("subject_user_id", ""),
                "access_policy": "personal" if item.get("lane") == "personal" else "household",
                "boundary_label": item.get("boundary_label", ""),
            }
            if subject_filter and item.get("subject_user_id", "").lower() != subject_filter:
                continue
            if not self._viewer_allowed(viewer, candidate_entry):
                continue
            facts.append(item)
        return list(reversed(facts))

    def update_profile_fact_status(self, viewer: UserProfile, fact_id: str, status: str) -> dict:
        if status not in {"active", "retired"}:
            raise ValueError("status must be active or retired")
        target = None
        for item in self.store.list_profile_facts():
            if item.get("fact_id") == fact_id:
                target = item
                break
        if target is None:
            raise KeyError(f"Unknown profile fact: {fact_id}")
        candidate_entry = {
            "memory_type": target.get("lane", "personal"),
            "scope": "personal" if target.get("lane") == "personal" else "household",
            "owner": target.get("subject_display_name", ""),
            "subject_user_id": target.get("subject_user_id", ""),
            "access_policy": "personal" if target.get("lane") == "personal" else "household",
            "boundary_label": target.get("boundary_label", ""),
        }
        if not self._viewer_allowed(viewer, candidate_entry):
            raise PermissionError("Viewer may not modify this profile fact")
        updated = self.store.update_profile_fact_status(fact_id, status)
        if updated is None:
            raise KeyError(f"Unknown profile fact: {fact_id}")
        return updated

    def nightly_curation(self) -> dict:
        promoted: list[dict] = []
        scanned = 0
        for item in self.store.list_entries():
            if item.get("approval_status") != "approved":
                continue
            scanned += 1
            payload = self.cipher.decrypt_json(item["encrypted_payload"])
            promotion = self._promote_entry_to_profile_fact(item, payload)
            if promotion:
                promoted.append(
                    {
                        "entry_id": item.get("entry_id", ""),
                        "summary": item.get("summary", ""),
                        "fact_id": promotion["fact"].get("fact_id", ""),
                        "status": promotion["status"],
                    }
                )
        return {
            "ran_at": _now_iso(),
            "scanned_entries": scanned,
            "promoted_count": len(promoted),
            "promotions": promoted[:24],
        }
