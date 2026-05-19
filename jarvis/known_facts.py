"""
known_facts.py — Being Known memory layer for JARVIS (Epic 5).

Persistent, domain-partitioned memory store that gives JARVIS relational
intelligence about Chris and his household.  Pure stdlib — no new deps.

Storage layout:
    ~/.jarvis/memory/{domain}/{fact_id}.json
    ~/.jarvis/memory/{domain}/_index.json   (key → fact_id mapping)
    ~/.jarvis/memory/drift/{drift_id}.json
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Memory domains
# ---------------------------------------------------------------------------

MEMORY_DOMAINS: list[str] = [
    "mission",       # Chris's stated priorities and life mission
    "household",     # family facts, routines, preferences
    "calendar",      # patterns from calendar (recurring events, travel rhythms)
    "comms",         # communication patterns, relationships
    "health",        # health/fitness patterns
    "faith",         # spiritual notes, prayer intentions
    "finance",       # financial goals and patterns
    "workshop",      # maker projects, equipment, preferences
    "projects",      # active projects and workstreams
    "priorities",    # ranked current priorities
    "briefings",     # history of past briefings
    "drift",         # logged drift events (when reality ≠ stated priorities)
    "growth",        # learning and personal development notes
    "relationships", # relationship intelligence facts
    "occasions",     # birthdays, anniversaries, gift history
]

# Domains surfaced first when building relational context
_PRIORITY_DOMAINS = ["mission", "priorities", "household", "projects", "health"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_expired(fact: "MemoryFact") -> bool:
    if not fact.expires_at:
        return False
    try:
        exp = datetime.fromisoformat(fact.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > exp
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MemoryFact:
    fact_id: str           # uuid4
    domain: str            # one of MEMORY_DOMAINS
    actor_id: str          # "chris" | "rebekah" | "caleb" | "anna" | "household"
    key: str               # short label e.g. "preferred_wake_time"
    value: str             # the fact itself (plain text, max 500 chars)
    confidence: float      # 0.0–1.0  (1.0 = explicitly stated by user)
    source: str            # "user_stated" | "inferred" | "observed" | "system"
    created_at: str        # ISO timestamp
    updated_at: str        # ISO timestamp
    expires_at: str        # ISO timestamp or "" (no expiry)
    tags: list[str]        # e.g. ["recurring", "time-sensitive"]
    last_surfaced_at: str  # when JARVIS last mentioned this fact
    surface_count: int     # how many times surfaced
    confirmed: bool        # user has confirmed this is still accurate

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryFact":
        return cls(
            fact_id=str(data.get("fact_id", "")),
            domain=str(data.get("domain", "")),
            actor_id=str(data.get("actor_id", "")),
            key=str(data.get("key", "")),
            value=str(data.get("value", ""))[:500],
            confidence=float(data.get("confidence", 1.0)),
            source=str(data.get("source", "user_stated")),
            created_at=str(data.get("created_at", _now_iso())),
            updated_at=str(data.get("updated_at", _now_iso())),
            expires_at=str(data.get("expires_at", "")),
            tags=list(data.get("tags", [])),
            last_surfaced_at=str(data.get("last_surfaced_at", "")),
            surface_count=int(data.get("surface_count", 0)),
            confirmed=bool(data.get("confirmed", False)),
        )


@dataclass
class DriftEvent:
    drift_id: str
    actor_id: str
    domain: str
    description: str       # human-readable description of the drift
    stated_priority: str   # what they said mattered
    observed_reality: str  # what JARVIS observed
    detected_at: str
    severity: str          # "gentle" | "moderate" | "significant"
    acknowledged: bool     # user has acknowledged this drift
    resolved: bool
    resolved_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DriftEvent":
        return cls(
            drift_id=str(data.get("drift_id", "")),
            actor_id=str(data.get("actor_id", "")),
            domain=str(data.get("domain", "")),
            description=str(data.get("description", "")),
            stated_priority=str(data.get("stated_priority", "")),
            observed_reality=str(data.get("observed_reality", "")),
            detected_at=str(data.get("detected_at", _now_iso())),
            severity=str(data.get("severity", "gentle")),
            acknowledged=bool(data.get("acknowledged", False)),
            resolved=bool(data.get("resolved", False)),
            resolved_at=str(data.get("resolved_at", "")),
        )


# ---------------------------------------------------------------------------
# KnownFactsStore
# ---------------------------------------------------------------------------

class KnownFactsStore:
    """
    Persistent memory store for JARVIS Being Known layer.

    Each fact → one JSON file:  ~/.jarvis/memory/{domain}/{fact_id}.json
    Per-domain index:            ~/.jarvis/memory/{domain}/_index.json
    Drift events:                ~/.jarvis/memory/drift_events/{drift_id}.json

    Per-domain locks prevent cross-domain contention while allowing concurrent
    reads from different domains.
    """

    ROOT = Path.home() / ".jarvis" / "memory"

    def __init__(self, root: Path | None = None) -> None:
        if root is not None:
            self.ROOT = root
        self._locks: dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()
        self._ensure_dirs()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        for domain in MEMORY_DOMAINS:
            (self.ROOT / domain).mkdir(parents=True, exist_ok=True)
        (self.ROOT / "drift_events").mkdir(parents=True, exist_ok=True)

    def _domain_lock(self, domain: str) -> threading.Lock:
        with self._meta_lock:
            if domain not in self._locks:
                self._locks[domain] = threading.Lock()
            return self._locks[domain]

    def _domain_dir(self, domain: str) -> Path:
        d = self.ROOT / domain
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _fact_path(self, domain: str, fact_id: str) -> Path:
        return self._domain_dir(domain) / f"{fact_id}.json"

    def _index_path(self, domain: str) -> Path:
        return self._domain_dir(domain) / "_index.json"

    def _load_index(self, domain: str) -> dict[str, str]:
        """Returns {composite_key → fact_id}."""
        path = self._index_path(domain)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_index(self, domain: str, index: dict[str, str]) -> None:
        path = self._index_path(domain)
        path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _composite_key(actor_id: str, domain: str, key: str) -> str:
        return f"{actor_id}|{domain}|{key}"

    def _write_fact(self, fact: MemoryFact) -> None:
        path = self._fact_path(fact.domain, fact.fact_id)
        path.write_text(json.dumps(fact.to_dict(), indent=2) + "\n", encoding="utf-8")

    def _read_fact_file(self, domain: str, fact_id: str) -> MemoryFact | None:
        path = self._fact_path(domain, fact_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return MemoryFact.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def _delete_fact_file(self, domain: str, fact_id: str) -> None:
        path = self._fact_path(domain, fact_id)
        if path.exists():
            path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Facts — public API
    # ------------------------------------------------------------------

    def set_fact(self, fact: MemoryFact) -> None:
        """Store or update a fact. Overwrites if same actor_id + domain + key."""
        lock = self._domain_lock(fact.domain)
        with lock:
            index = self._load_index(fact.domain)
            ck = self._composite_key(fact.actor_id, fact.domain, fact.key)
            old_id = index.get(ck)
            # If replacing a different fact_id, delete the old file
            if old_id and old_id != fact.fact_id:
                self._delete_fact_file(fact.domain, old_id)
            # If replacing same composite key with a new fact object, keep
            # the new fact_id
            index[ck] = fact.fact_id
            self._write_fact(fact)
            self._save_index(fact.domain, index)

    def get_fact(self, actor_id: str, domain: str, key: str) -> MemoryFact | None:
        """Get a specific fact by composite key (actor_id + domain + key)."""
        lock = self._domain_lock(domain)
        with lock:
            index = self._load_index(domain)
            ck = self._composite_key(actor_id, domain, key)
            fact_id = index.get(ck)
            if not fact_id:
                return None
            fact = self._read_fact_file(domain, fact_id)
            if fact is None:
                return None
            if _is_expired(fact):
                self._delete_fact_file(domain, fact_id)
                del index[ck]
                self._save_index(domain, index)
                return None
            return fact

    def get_domain_facts(self, domain: str, actor_id: str | None = None) -> list[MemoryFact]:
        """Get all non-expired facts for a domain, optionally filtered by actor."""
        lock = self._domain_lock(domain)
        with lock:
            index = self._load_index(domain)
            results: list[MemoryFact] = []
            expired_cks: list[str] = []
            for ck, fact_id in index.items():
                fact = self._read_fact_file(domain, fact_id)
                if fact is None:
                    expired_cks.append(ck)
                    continue
                if _is_expired(fact):
                    self._delete_fact_file(domain, fact_id)
                    expired_cks.append(ck)
                    continue
                if actor_id is not None and fact.actor_id != actor_id:
                    continue
                results.append(fact)
            if expired_cks:
                for ck in expired_cks:
                    index.pop(ck, None)
                self._save_index(domain, index)
            return results

    def search_facts(
        self,
        query: str,
        actor_id: str | None = None,
        domains: list[str] | None = None,
    ) -> list[MemoryFact]:
        """Simple case-insensitive keyword search across fact values and keys."""
        search_domains = domains if domains else MEMORY_DOMAINS
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        results: list[MemoryFact] = []
        for domain in search_domains:
            for fact in self.get_domain_facts(domain, actor_id=actor_id):
                haystack = f"{fact.key} {fact.value}".lower()
                if all(t in haystack for t in terms):
                    results.append(fact)
        return results

    def delete_fact(self, fact_id: str) -> bool:
        """Delete a fact by ID. Scans all domains."""
        for domain in MEMORY_DOMAINS:
            lock = self._domain_lock(domain)
            with lock:
                index = self._load_index(domain)
                to_remove = [ck for ck, fid in index.items() if fid == fact_id]
                if to_remove:
                    for ck in to_remove:
                        del index[ck]
                    self._delete_fact_file(domain, fact_id)
                    self._save_index(domain, index)
                    return True
        return False

    def expire_old_facts(self) -> int:
        """Delete all expired facts. Returns count deleted."""
        deleted = 0
        for domain in MEMORY_DOMAINS:
            lock = self._domain_lock(domain)
            with lock:
                index = self._load_index(domain)
                expired_cks: list[str] = []
                for ck, fact_id in index.items():
                    fact = self._read_fact_file(domain, fact_id)
                    if fact is None or _is_expired(fact):
                        self._delete_fact_file(domain, fact_id)
                        expired_cks.append(ck)
                        deleted += 1
                if expired_cks:
                    for ck in expired_cks:
                        del index[ck]
                    self._save_index(domain, index)
        return deleted

    def count_facts(self, actor_id: str | None = None) -> int:
        """Return total non-expired fact count, optionally filtered by actor."""
        total = 0
        for domain in MEMORY_DOMAINS:
            total += len(self.get_domain_facts(domain, actor_id=actor_id))
        return total

    # ------------------------------------------------------------------
    # Drift events — public API
    # ------------------------------------------------------------------

    def _drift_dir(self) -> Path:
        d = self.ROOT / "drift_events"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _drift_path(self, drift_id: str) -> Path:
        return self._drift_dir() / f"{drift_id}.json"

    def log_drift(self, drift: DriftEvent) -> None:
        """Persist a drift event."""
        path = self._drift_path(drift.drift_id)
        path.write_text(json.dumps(drift.to_dict(), indent=2) + "\n", encoding="utf-8")

    def _all_drift_events(self) -> list[DriftEvent]:
        events: list[DriftEvent] = []
        for path in sorted(self._drift_dir().glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                events.append(DriftEvent.from_dict(data))
            except (json.JSONDecodeError, OSError, KeyError):
                continue
        return events

    def get_active_drift(self, actor_id: str = "chris") -> list[DriftEvent]:
        """Return unresolved drift events for an actor, newest first."""
        return [
            e for e in reversed(self._all_drift_events())
            if e.actor_id == actor_id and not e.resolved
        ]

    def acknowledge_drift(self, drift_id: str) -> bool:
        path = self._drift_path(drift_id)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["acknowledged"] = True
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def resolve_drift(self, drift_id: str) -> bool:
        path = self._drift_path(drift_id)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["resolved"] = True
            data["acknowledged"] = True
            data["resolved_at"] = _now_iso()
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            return True
        except (json.JSONDecodeError, OSError):
            return False

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def get_relational_context(
        self,
        actor_id: str,
        domains: list[str] | None = None,
        max_chars: int = 2000,
    ) -> str:
        """
        Compact, bullet-style context string for prepending to system prompts.

        Format: "What I know about Chris: [mission: ...] [household: ...] ..."
        Prioritises mission and priorities, then other requested domains.
        """
        # Build domain order — priority domains first, then remaining
        if domains:
            ordered = [d for d in _PRIORITY_DOMAINS if d in domains]
            ordered += [d for d in domains if d not in _PRIORITY_DOMAINS]
        else:
            ordered = list(_PRIORITY_DOMAINS) + [
                d for d in MEMORY_DOMAINS if d not in _PRIORITY_DOMAINS
            ]

        label = actor_id.capitalize()
        lines: list[str] = [f"What I know about {label}:"]
        chars_used = len(lines[0])

        for domain in ordered:
            if domain == "drift":
                continue  # drift handled separately
            facts = self.get_domain_facts(domain, actor_id=actor_id)
            if not facts:
                continue
            domain_parts: list[str] = []
            for fact in sorted(facts, key=lambda f: -f.confidence):
                snippet = f"{fact.key}: {fact.value}"
                domain_parts.append(snippet)
            if not domain_parts:
                continue
            line = f"  [{domain}] " + " | ".join(domain_parts)
            if chars_used + len(line) + 1 > max_chars:
                # Truncate to fit
                available = max_chars - chars_used - len(f"  [{domain}] ") - 4
                if available > 30:
                    line = f"  [{domain}] " + " | ".join(domain_parts)[:available] + "..."
                else:
                    break
            lines.append(line)
            chars_used += len(line) + 1

        if len(lines) <= 1:
            return ""
        return "\n".join(lines)

    def get_briefing_memory_context(self) -> str:
        """
        Context string for the morning briefing agent:
        active drift, upcoming occasions, and current priorities.
        """
        parts: list[str] = []

        # Active drift
        drift_events = self.get_active_drift("chris")
        if drift_events:
            parts.append("Active drift alerts:")
            for event in drift_events[:3]:
                parts.append(f"  [{event.severity}] {event.description}")

        # Upcoming occasions
        occasions = self.get_domain_facts("occasions", actor_id="chris")
        occasions += self.get_domain_facts("occasions", actor_id="household")
        if occasions:
            parts.append("Occasions to remember:")
            for occ in occasions[:5]:
                parts.append(f"  {occ.key}: {occ.value}")

        # Priorities
        priorities = self.get_domain_facts("priorities", actor_id="chris")
        if priorities:
            parts.append("Current priorities:")
            for p in sorted(priorities, key=lambda f: -f.confidence)[:5]:
                parts.append(f"  {p.key}: {p.value}")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

def seed_initial_facts(store: KnownFactsStore) -> int:
    """
    Seed the store with facts from the project context.
    Only runs if the store has fewer than 5 facts for 'chris'.
    Returns number of facts seeded.
    """
    if store.count_facts(actor_id="chris") >= 5:
        return 0

    now = _now_iso()

    def _fact(
        domain: str,
        actor_id: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source: str = "user_stated",
        tags: list[str] | None = None,
    ) -> MemoryFact:
        return MemoryFact(
            fact_id=str(uuid.uuid4()),
            domain=domain,
            actor_id=actor_id,
            key=key,
            value=value[:500],
            confidence=confidence,
            source=source,
            created_at=now,
            updated_at=now,
            expires_at="",
            tags=tags or [],
            last_surfaced_at="",
            surface_count=0,
            confirmed=True,
        )

    seed_facts: list[MemoryFact] = [
        # Mission
        _fact("mission", "chris", "roles",
              "Strategist, writer, maker, Scout leader, Chronicle builder",
              tags=["identity"]),
        _fact("mission", "chris", "core_values",
              "Clarity, courage, wisdom, momentum. Faith-driven. Family-first.",
              tags=["identity", "foundation"]),
        _fact("mission", "chris", "emotional_target",
              "I am known, and I am not carrying this alone.",
              tags=["identity"]),

        # Household
        _fact("household", "chris", "family_members",
              "Wife: Rebekah. Kids: Caleb and Anna.",
              tags=["family"]),
        _fact("household", "rebekah", "role",
              "Household coordinator, troop organizer, family logistics lead",
              tags=["family"]),
        _fact("household", "chris", "household_name",
              "Binion household — Forney, Texas area",
              tags=["location"]),

        # Workshop
        _fact("workshop", "chris", "equipment",
              "Creality K2 Pro (FDM), Creality HALOT-ONE (resin), "
              "Creality Falcon 5W (laser), Titoe 4540 (CNC), Cricut Joy Xtra (labels/masks)",
              tags=["maker", "equipment"]),
        _fact("workshop", "chris", "maker_identity",
              "Hands-on maker — fabrication, electronics, 3D printing, laser cutting, CNC",
              tags=["maker"]),

        # Projects
        _fact("projects", "chris", "active_systems",
              "JARVIS (household AI), Catalyst (personal workflow), "
              "Chronicle (faith journal), Ghostwritr (book writing, future)",
              tags=["active"]),
        _fact("projects", "chris", "jarvis_purpose",
              "JARVIS is the household brain — ambient intelligence, daily briefings, "
              "agent network, memory and being known",
              tags=["active", "ai"]),

        # Priorities
        _fact("priorities", "chris", "top_priorities",
              "Faith, family health, JARVIS build-out, writing/Chronicle, "
              "financial stability, Scout leadership",
              tags=["ranked"]),

        # Scout leadership
        _fact("household", "chris", "scout_role",
              "Scout leader — runs troop activities alongside Rebekah",
              tags=["family", "community"]),

        # Health
        _fact("health", "chris", "health_intention",
              "Fitness is a stated priority — needs consistent logging and accountability",
              confidence=0.9, source="inferred", tags=["wellness"]),

        # Faith
        _fact("faith", "chris", "faith_framework",
              "Christian faith is foundational — Chronicle journal tracks spiritual growth "
              "and prayer intentions",
              tags=["faith", "chronicle"]),

        # Growth
        _fact("growth", "chris", "learning_posture",
              "Builder-learner mindset — prefers systems thinking, deep dives, "
              "practical application over theory",
              tags=["learning"]),
    ]

    seeded = 0
    for fact in seed_facts:
        existing = store.get_fact(fact.actor_id, fact.domain, fact.key)
        if not existing:
            store.set_fact(fact)
            seeded += 1

    return seeded


# ---------------------------------------------------------------------------
# DriftDetector
# ---------------------------------------------------------------------------

class DriftDetector:
    """
    Detects drift between stated priorities and observed reality.
    Designed to be called by the scheduler (typically every 24 h).

    Current checks:
    - Health: no logged health activity recently
    - Mission: project-related tasks not touched recently
    - Communication: important relationships not contacted in 30+ days
    """

    DEFAULT_HEALTH_DRIFT_DAYS = 5
    DEFAULT_MISSION_DRIFT_DAYS = 7
    DEFAULT_COMMS_DRIFT_DAYS = 30

    def __init__(self, store: KnownFactsStore, scheduler: Any = None) -> None:
        self._store = store
        self._scheduler = scheduler  # reserved for future scheduler integration

    def run_checks(self, actor_id: str = "chris") -> list[DriftEvent]:
        """Run all drift checks. Log new events. Return list of new events."""
        new_events: list[DriftEvent] = []

        checks = [
            self._check_health_drift,
            self._check_mission_drift,
            self._check_comms_drift,
        ]

        for check in checks:
            try:
                event = check(actor_id)
                if event is not None:
                    # Only log if no identical unresolved drift already exists
                    existing = self._store.get_active_drift(actor_id)
                    duplicate = any(
                        e.domain == event.domain and e.description == event.description
                        for e in existing
                    )
                    if not duplicate:
                        self._store.log_drift(event)
                        new_events.append(event)
            except Exception:  # never let a check crash the scheduler
                pass

        return new_events

    def _check_health_drift(self, actor_id: str) -> DriftEvent | None:
        """
        Health drift: if the health domain has a 'last_activity_date' fact
        that is older than DEFAULT_HEALTH_DRIFT_DAYS, flag drift.
        """
        health_priority = self._store.get_fact(actor_id, "priorities", "top_priorities")
        if not health_priority or "health" not in health_priority.value.lower():
            return None  # health not a stated priority, skip

        last_activity = self._store.get_fact(actor_id, "health", "last_activity_date")
        if last_activity and last_activity.value:
            try:
                last_date = datetime.fromisoformat(
                    last_activity.value.replace("Z", "+00:00")
                )
                delta = datetime.now(timezone.utc) - last_date
                if delta.days < self.DEFAULT_HEALTH_DRIFT_DAYS:
                    return None
                desc = (
                    f"{actor_id.capitalize()} stated fitness as a priority "
                    f"but no activity has been logged in {delta.days} days."
                )
            except ValueError:
                desc = (
                    f"{actor_id.capitalize()} stated fitness as a priority "
                    f"but last activity date is unreadable."
                )
        else:
            desc = (
                f"{actor_id.capitalize()} stated fitness as a priority "
                f"but no activity has been logged in JARVIS."
            )

        return DriftEvent(
            drift_id=str(uuid.uuid4()),
            actor_id=actor_id,
            domain="health",
            description=desc,
            stated_priority="Fitness / health is a top priority",
            observed_reality="No recent health activity logged",
            detected_at=_now_iso(),
            severity="gentle",
            acknowledged=False,
            resolved=False,
            resolved_at="",
        )

    def _check_mission_drift(self, actor_id: str) -> DriftEvent | None:
        """
        Mission drift: if 'last_project_touch' fact is older than
        DEFAULT_MISSION_DRIFT_DAYS, flag drift.
        """
        last_touch = self._store.get_fact(actor_id, "projects", "last_project_touch")
        if not last_touch or not last_touch.value:
            return None  # no tracking fact yet — can't determine drift

        try:
            last_date = datetime.fromisoformat(
                last_touch.value.replace("Z", "+00:00")
            )
            delta = datetime.now(timezone.utc) - last_date
            if delta.days < self.DEFAULT_MISSION_DRIFT_DAYS:
                return None
        except ValueError:
            return None

        return DriftEvent(
            drift_id=str(uuid.uuid4()),
            actor_id=actor_id,
            domain="projects",
            description=(
                f"{actor_id.capitalize()}'s active projects haven't been touched "
                f"in {delta.days} days — mission momentum may be stalling."
            ),
            stated_priority="Active project momentum",
            observed_reality=f"No project activity in {delta.days} days",
            detected_at=_now_iso(),
            severity="moderate",
            acknowledged=False,
            resolved=False,
            resolved_at="",
        )

    def _check_comms_drift(self, actor_id: str) -> DriftEvent | None:
        """
        Communication drift: check if any 'last_contact' relationship facts are
        older than DEFAULT_COMMS_DRIFT_DAYS and marked as important.
        """
        rel_facts = self._store.get_domain_facts("relationships", actor_id=actor_id)
        overdue: list[str] = []
        now = datetime.now(timezone.utc)

        for fact in rel_facts:
            if fact.key.startswith("last_contact_") and "important" in fact.tags:
                try:
                    last_contact = datetime.fromisoformat(
                        fact.value.replace("Z", "+00:00")
                    )
                    delta = now - last_contact
                    if delta.days >= self.DEFAULT_COMMS_DRIFT_DAYS:
                        name = fact.key.replace("last_contact_", "").replace("_", " ")
                        overdue.append(f"{name} ({delta.days}d)")
                except ValueError:
                    continue

        if not overdue:
            return None

        names = ", ".join(overdue[:5])
        return DriftEvent(
            drift_id=str(uuid.uuid4()),
            actor_id=actor_id,
            domain="relationships",
            description=f"Important relationships without recent contact: {names}.",
            stated_priority="Maintaining key relationships",
            observed_reality=f"No contact logged for: {names}",
            detected_at=_now_iso(),
            severity="gentle",
            acknowledged=False,
            resolved=False,
            resolved_at="",
        )


# ---------------------------------------------------------------------------
# MemoryContextInjector
# ---------------------------------------------------------------------------

class MemoryContextInjector:
    """
    Wraps LLM system prompt construction to inject relevant memory context.
    Call inject() before sending to the model.
    """

    def __init__(self, store: KnownFactsStore) -> None:
        self._store = store

    def inject(
        self,
        base_system_prompt: str,
        actor_id: str,
        domains: list[str] | None = None,
        max_tokens: int = 400,
    ) -> str:
        """
        Prepend relevant memory context to the system prompt.
        Respects max_tokens (estimated at 4 chars/token) to avoid bloating context.
        Always surfaces mission and priorities first, then other domains.
        """
        # Prioritise mission + priorities always, then requested
        ordered_domains: list[str] = ["mission", "priorities"]
        if domains:
            ordered_domains += [d for d in domains if d not in ordered_domains]

        max_chars = max_tokens * 4
        context = self._store.get_relational_context(
            actor_id,
            domains=ordered_domains,
            max_chars=max_chars,
        )
        if not context:
            return base_system_prompt
        return f"{base_system_prompt}\n\n[KNOWN CONTEXT]\n{context}"


# ---------------------------------------------------------------------------
# Singleton management
# ---------------------------------------------------------------------------

_store_singleton: KnownFactsStore | None = None
_store_lock = threading.Lock()


def init_memory(store_root: Path | None = None) -> KnownFactsStore:
    """
    Return the module-level KnownFactsStore singleton.
    Creates and seeds it on first call. Thread-safe.
    """
    global _store_singleton
    with _store_lock:
        if _store_singleton is not None:
            return _store_singleton

        store = KnownFactsStore(root=store_root)
        seeded = seed_initial_facts(store)
        if seeded:
            import logging
            logging.getLogger("jarvis.known_facts").info(
                "Seeded %d initial facts into KnownFactsStore", seeded
            )

        _store_singleton = store
        return _store_singleton


def get_memory() -> KnownFactsStore | None:
    """Return the singleton if initialised, else None."""
    return _store_singleton
