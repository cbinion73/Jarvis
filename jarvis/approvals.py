from __future__ import annotations

"""
JARVIS Approval & Permission Layer — Epic 6
============================================
Unified approval gate ensuring JARVIS never takes consequential actions
without Chris's explicit sign-off.

Design:
- ApprovalRequest dataclass — single record per staged action
- ApprovalQueue — thread-safe store persisted to ~/.jarvis/approvals/
- ApprovalGuard — primary agent-facing interface
- ActionExecutors — stub dispatchers per action type (real wiring added per integration)
- GUARDRAIL_OVERRIDES — hard rules that elevate risk tiers for sensitive contexts

Persistence:
- ~/.jarvis/approvals/queue.jsonl   — active (pending/running) requests
- ~/.jarvis/approvals/history.jsonl — completed records, capped at 500
"""

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_jsonl

logger = logging.getLogger("jarvis.approvals")


# ---------------------------------------------------------------------------
# Risk tier enum
# ---------------------------------------------------------------------------

class RiskTier(str, Enum):
    SAFE = "safe"          # No approval needed: weather lookups, calendar reads
    LOW = "low"            # Soft approval (auto-approves after 30 min if no response)
    MEDIUM = "medium"      # Explicit approval required — never auto-approves
    HIGH = "high"          # Explicit approval + confirmation (2-step)
    CRITICAL = "critical"  # Blocks until approved; push notification immediately


# ---------------------------------------------------------------------------
# Risk classification tables
# ---------------------------------------------------------------------------

ACTION_RISK_MAP: dict[str, str] = {
    "send_message":     RiskTier.MEDIUM,
    "calendar_change":  RiskTier.MEDIUM,
    "purchase":         RiskTier.HIGH,
    "home_control":     RiskTier.MEDIUM,
    "social_post":      RiskTier.MEDIUM,
    "deploy":           RiskTier.HIGH,
    "document_send":    RiskTier.MEDIUM,
    "document_review":  RiskTier.MEDIUM,
    "external_api":     RiskTier.LOW,
    "file_write":       RiskTier.LOW,
    "other":            RiskTier.MEDIUM,
}

# Auto-approve timeouts by tier in seconds; None = never auto-approve
AUTO_APPROVE_TIMEOUTS: dict[str, int | None] = {
    RiskTier.SAFE:     0,
    RiskTier.LOW:      1800,   # 30 minutes
    RiskTier.MEDIUM:   None,
    RiskTier.HIGH:     None,
    RiskTier.CRITICAL: None,
}

# Expiry windows — how long a request stays open before it expires
EXPIRY_WINDOWS: dict[str, int] = {
    RiskTier.SAFE:     300,      # 5 min (academic; SAFE is immediate)
    RiskTier.LOW:      7200,     # 2 h
    RiskTier.MEDIUM:   86400,    # 24 h
    RiskTier.HIGH:     43200,    # 12 h
    RiskTier.CRITICAL: 3600,     # 1 h (push sent; must be acted on fast)
}

# Guardrail overrides: (action_type, context_key, context_value) → minimum tier
# These can only elevate, never lower.
GUARDRAIL_OVERRIDES: list[dict] = [
    # External messaging is always MEDIUM minimum
    {
        "action_types": ["send_message", "document_send", "social_post"],
        "context_key": None,
        "context_value": None,
        "minimum_tier": RiskTier.MEDIUM,
        "reason": "No automatic external messaging allowed",
    },
    # Any action flagged as child-related → elevate one tier
    {
        "action_types": None,   # all action types
        "context_key": "involves_children",
        "context_value": True,
        "minimum_tier": None,   # special: elevate_one
        "elevate_one": True,
        "reason": "Child-related external actions require elevated caution",
    },
    # Home unlock from outside network → CRITICAL
    {
        "action_types": ["home_control"],
        "context_key": "remote_unlock",
        "context_value": True,
        "minimum_tier": RiskTier.CRITICAL,
        "reason": "Remote door unlock requires CRITICAL approval",
    },
    # Voice-only unlock → CRITICAL + typed confirmation
    {
        "action_types": ["home_control"],
        "context_key": "voice_only_unlock",
        "context_value": True,
        "minimum_tier": RiskTier.CRITICAL,
        "reason": "Voice-only unlock is prohibited; requires typed second factor",
    },
    # Bedroom / bathroom camera commands → CRITICAL
    {
        "action_types": ["home_control"],
        "context_key": "camera_zone",
        "context_value": "private",
        "minimum_tier": RiskTier.CRITICAL,
        "reason": "Bedroom/bathroom camera commands require CRITICAL approval",
    },
    # Purchase > $500 → CRITICAL
    {
        "action_types": ["purchase"],
        "context_key": "amount_usd",
        "context_value": 500,   # ≥ this value
        "context_comparison": "gte",
        "minimum_tier": RiskTier.CRITICAL,
        "reason": "Purchases above $500 require CRITICAL approval",
    },
    # Purchase > $100 → HIGH minimum
    {
        "action_types": ["purchase"],
        "context_key": "amount_usd",
        "context_value": 100,
        "context_comparison": "gte",
        "minimum_tier": RiskTier.HIGH,
        "reason": "Purchases above $100 require HIGH approval",
    },
]

_TIER_ORDER = [
    RiskTier.SAFE,
    RiskTier.LOW,
    RiskTier.MEDIUM,
    RiskTier.HIGH,
    RiskTier.CRITICAL,
]


def _tier_index(tier: str) -> int:
    try:
        return _TIER_ORDER.index(RiskTier(tier))
    except (ValueError, AttributeError):
        return 2  # default to MEDIUM


def _elevate_tier(current: str) -> str:
    idx = _tier_index(current)
    if idx < len(_TIER_ORDER) - 1:
        return _TIER_ORDER[idx + 1].value
    return current


def classify_action(
    action_type: str,
    payload: dict | None = None,
    context: dict | None = None,
) -> str:
    """
    Determine risk tier for an action. Applies guardrail overrides that can
    only elevate the base tier — never lower it.
    """
    payload = payload or {}
    context = context or {}

    base_tier = ACTION_RISK_MAP.get(action_type, RiskTier.MEDIUM)
    current_idx = _tier_index(base_tier)

    for rule in GUARDRAIL_OVERRIDES:
        # Check action type match
        rule_types = rule.get("action_types")
        if rule_types is not None and action_type not in rule_types:
            continue

        # Check context condition
        ctx_key = rule.get("context_key")
        if ctx_key is not None:
            ctx_val_required = rule.get("context_value")
            ctx_actual = context.get(ctx_key) if ctx_key in context else payload.get(ctx_key)
            comparison = rule.get("context_comparison", "eq")

            if ctx_actual is None:
                continue

            if comparison == "gte":
                try:
                    if float(ctx_actual) < float(ctx_val_required):
                        continue
                except (TypeError, ValueError):
                    continue
            else:  # eq
                if ctx_actual != ctx_val_required:
                    continue

        # Apply elevation
        if rule.get("elevate_one"):
            elevated = _elevate_tier(base_tier)
            new_idx = _tier_index(elevated)
            if new_idx > current_idx:
                current_idx = new_idx
        else:
            min_tier = rule.get("minimum_tier")
            if min_tier is not None:
                min_idx = _tier_index(min_tier)
                if min_idx > current_idx:
                    current_idx = min_idx

    return _TIER_ORDER[current_idx].value


# ---------------------------------------------------------------------------
# Confirmation phrase generator
# ---------------------------------------------------------------------------

_CONFIRMATION_PHRASES: dict[str, str] = {
    "purchase":     "confirm purchase",
    "home_control": "confirm action",
    "deploy":       "confirm deploy",
    "social_post":  "confirm post",
    "send_message": "confirm send",
    "other":        "confirm",
}


def _make_confirmation_phrase(action_type: str, title: str) -> str:
    base = _CONFIRMATION_PHRASES.get(action_type, "confirm")
    # Use first 3 words of title for uniqueness
    words = title.lower().split()[:3]
    return f"{base}: {' '.join(words)}" if words else base


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_plus_seconds(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _expires_in_human(expires_at: str) -> str:
    """Return a human-readable 'expires in X min' string."""
    if not expires_at:
        return ""
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        delta = exp - datetime.now(timezone.utc)
        total_secs = int(delta.total_seconds())
        if total_secs <= 0:
            return "expired"
        if total_secs < 3600:
            mins = (total_secs + 59) // 60
            return f"expires in {mins} min"
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60
        if mins:
            return f"expires in {hours}h {mins}m"
        return f"expires in {hours}h"
    except (ValueError, AttributeError):
        return ""


# ---------------------------------------------------------------------------
# ApprovalRequest dataclass
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    request_id: str
    agent_id: str
    agent_label: str
    action_type: str       # see ACTION_RISK_MAP keys
    title: str             # short label shown in UI
    description: str       # what exactly will happen
    payload: dict          # staged action data
    risk_tier: str         # RiskTier value
    actor_id: str          # who this affects ("chris", "rebekah", …)
    requested_at: str      # ISO timestamp
    expires_at: str        # ISO timestamp
    status: str            # pending | approved | rejected | expired | executed | cancelled
    approved_by: str = ""
    approved_at: str = ""
    executed_at: str = ""
    rejection_reason: str = ""
    auto_approve_at: str = ""   # set for LOW risk tier
    priority: int = 5           # 1=urgent, 5=normal, 10=low
    tags: list = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_phrase: str = ""
    trust_zone_id: str = ""
    lane_id: str = ""
    arena_id: str = ""
    requested_outcome: str = ""
    supervision_context: dict = field(default_factory=dict)
    supervision_decision: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ApprovalQueue
# ---------------------------------------------------------------------------

class ApprovalQueue:
    """
    Thread-safe approval request store.

    Persistence:
    - queue.jsonl   — all active (pending) records
    - history.jsonl — completed records (approved/rejected/expired/cancelled/executed)
                      capped at HISTORY_LIMIT entries
    """

    ROOT = Path.home() / ".jarvis" / "approvals"
    HISTORY_LIMIT = 500

    def __init__(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)
        self._queue_path = self.ROOT / "queue.jsonl"
        self._history_path = self.ROOT / "history.jsonl"
        self._queue_state_log_path = self.ROOT / "queue_state_log.jsonl"
        self._history_state_log_path = self.ROOT / "history_state_log.jsonl"
        self._lock = threading.Lock()
        self._items: list[ApprovalRequest] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, request: ApprovalRequest) -> str:
        """Submit a new approval request. Returns request_id."""
        with self._lock:
            self._items.append(request)
            self._save()
        logger.info(
            "Approval submitted: %s agent=%s action=%s tier=%s",
            request.request_id,
            request.agent_id,
            request.action_type,
            request.risk_tier,
        )
        return request.request_id

    def approve(self, request_id: str, approved_by: str = "chris") -> ApprovalRequest | None:
        """Mark a pending request as approved. Returns the request for execution."""
        with self._lock:
            for item in self._items:
                if item.request_id == request_id and item.status == "pending":
                    item.status = "approved"
                    item.approved_by = approved_by
                    item.approved_at = _now_iso()
                    self._save()
                    logger.info("Approved: %s by=%s", request_id, approved_by)
                    return item
        return None

    def reject(self, request_id: str, reason: str = "", rejected_by: str = "chris") -> bool:
        """Mark a pending request as rejected. Returns True if found."""
        with self._lock:
            for item in self._items:
                if item.request_id == request_id and item.status == "pending":
                    item.status = "rejected"
                    item.rejection_reason = reason
                    item.approved_by = rejected_by
                    item.approved_at = _now_iso()
                    self._archive_completed(item)
                    self._save()
                    logger.info("Rejected: %s reason=%s", request_id, reason)
                    return True
        return False

    def cancel(self, request_id: str) -> bool:
        """Cancel a pending request. Returns True if found."""
        with self._lock:
            for item in self._items:
                if item.request_id == request_id and item.status == "pending":
                    item.status = "cancelled"
                    self._archive_completed(item)
                    self._save()
                    logger.info("Cancelled: %s", request_id)
                    return True
        return False

    def mark_executed(self, request_id: str) -> bool:
        """Mark an approved request as executed."""
        with self._lock:
            for item in self._items:
                if item.request_id == request_id and item.status == "approved":
                    item.status = "executed"
                    item.executed_at = _now_iso()
                    self._archive_completed(item)
                    self._save()
                    logger.info("Executed: %s", request_id)
                    return True
        return False

    def get_pending(self, actor_id: str | None = None) -> list[ApprovalRequest]:
        """Return pending requests, expiring stale ones first."""
        with self._lock:
            self._expire_old_unlocked()
            pending = [
                item for item in self._items
                if item.status == "pending"
                and (actor_id is None or item.actor_id.lower() == actor_id.lower())
            ]
        # Sort: priority asc, then requested_at asc
        pending.sort(key=lambda x: (x.priority, x.requested_at))
        return pending

    def get_by_id(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            for item in self._items:
                if item.request_id == request_id:
                    return item
        return None

    def get_history(self, limit: int = 50, action_type: str | None = None) -> list[ApprovalRequest]:
        """Return completed records from history file, newest first."""
        records = self._load_history()
        if action_type:
            records = [r for r in records if r.action_type == action_type]
        return list(reversed(records[-max(1, limit):]))

    def process_auto_approvals(self) -> int:
        """
        Check LOW risk items that have passed their auto_approve_at time.
        Auto-approve them and return the count auto-approved.
        """
        now = datetime.now(timezone.utc)
        count = 0
        with self._lock:
            for item in self._items:
                if item.status != "pending" or item.risk_tier != RiskTier.LOW:
                    continue
                if not item.auto_approve_at:
                    continue
                try:
                    auto_at = datetime.fromisoformat(item.auto_approve_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue
                if now >= auto_at:
                    item.status = "approved"
                    item.approved_by = "system_auto"
                    item.approved_at = _now_iso()
                    count += 1
                    logger.info("Auto-approved LOW risk request: %s", item.request_id)
            if count:
                self._save()
        return count

    def pending_count(self, actor_id: str | None = None) -> int:
        return len(self.get_pending(actor_id))

    def get_document_reviews_pending(self) -> list[ApprovalRequest]:
        """
        Return all pending approval requests where action_type == 'document_review',
        sorted by submitted_at (requested_at) ascending.
        """
        pending = self.get_pending()
        doc_reviews = [r for r in pending if r.action_type == "document_review"]
        doc_reviews.sort(key=lambda r: r.requested_at)
        return doc_reviews

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _expire_old_unlocked(self) -> int:
        """Must be called while holding self._lock. Marks expired items."""
        now = datetime.now(timezone.utc)
        count = 0
        for item in self._items:
            if item.status != "pending" or not item.expires_at:
                continue
            try:
                exp = datetime.fromisoformat(item.expires_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if now >= exp:
                item.status = "expired"
                self._archive_completed_unlocked(item)
                count += 1
                logger.debug("Expired: %s", item.request_id)
        if count:
            self._save_unlocked()
        return count

    def _archive_completed(self, item: ApprovalRequest) -> None:
        """Caller must hold lock."""
        self._archive_completed_unlocked(item)

    def _archive_completed_unlocked(self, item: ApprovalRequest) -> None:
        history = self._load_history()
        history.append(item)
        # Cap at HISTORY_LIMIT
        if len(history) > self.HISTORY_LIMIT:
            history = history[-self.HISTORY_LIMIT:]
        try:
            atomic_write_jsonl(self._history_path, [asdict(r) for r in history])
            append_jsonl(
                self._history_state_log_path,
                {
                    "saved_at": _now_iso(),
                    "records": [asdict(r) for r in history],
                },
            )
        except OSError as exc:
            logger.warning("Failed to write history: %s", exc)
        # Remove from active items
        self._items = [i for i in self._items if i.request_id != item.request_id]

    def _save(self) -> None:
        """Caller must hold lock."""
        self._save_unlocked()

    def _save_unlocked(self) -> None:
        try:
            active = [i for i in self._items if i.status in ("pending", "approved")]
            atomic_write_jsonl(self._queue_path, [asdict(i) for i in active])
            append_jsonl(
                self._queue_state_log_path,
                {
                    "saved_at": _now_iso(),
                    "records": [asdict(i) for i in active],
                },
            )
        except OSError as exc:
            logger.warning("Failed to persist queue: %s", exc)

    def _load(self) -> None:
        self._items = []
        if not self._queue_path.exists():
            self._items = self._load_queue_from_state_log()
            return
        try:
            for line in self._queue_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Ensure list fields are lists
                    data.setdefault("tags", [])
                    self._items.append(ApprovalRequest(**data))
                except Exception:
                    logger.debug("Skipping corrupt queue line", exc_info=True)
        except (OSError, json.JSONDecodeError):
            self._items = self._load_queue_from_state_log()
            return
        if not self._items:
            self._items = self._load_queue_from_state_log()

    def _load_queue_from_state_log(self) -> list[ApprovalRequest]:
        if not self._queue_state_log_path.exists():
            return []
        try:
            latest: list[ApprovalRequest] = []
            for line in self._queue_state_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if not isinstance(records, list):
                    continue
                candidate: list[ApprovalRequest] = []
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    item.setdefault("tags", [])
                    candidate.append(ApprovalRequest(**item))
                latest = candidate
            return latest
        except Exception:
            return []

    def _load_history(self) -> list[ApprovalRequest]:
        if not self._history_path.exists():
            return self._load_history_from_state_log()
        records: list[ApprovalRequest] = []
        try:
            for line in self._history_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    data.setdefault("tags", [])
                    records.append(ApprovalRequest(**data))
                except Exception:
                    pass
        except (OSError, json.JSONDecodeError):
            return self._load_history_from_state_log()
        return records or self._load_history_from_state_log()

    def _load_history_from_state_log(self) -> list[ApprovalRequest]:
        if not self._history_state_log_path.exists():
            return []
        try:
            latest: list[ApprovalRequest] = []
            for line in self._history_state_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if not isinstance(records, list):
                    continue
                candidate: list[ApprovalRequest] = []
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    item.setdefault("tags", [])
                    candidate.append(ApprovalRequest(**item))
                latest = candidate
            return latest
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------

class ActionExecutors:
    """
    Dispatches approved actions. Currently stubs for integrations not yet
    wired. The home_control executor is live via HomeAssistantConnector.
    """

    @staticmethod
    def send_message(payload: dict) -> dict:
        """Send email / SMS / Slack. Stub pending Gmail/Twilio integration."""
        channel = payload.get("channel", "email")
        recipient = payload.get("to", payload.get("recipient", "unknown"))
        logger.info("STUB send_message: channel=%s to=%s", channel, recipient)
        return {
            "status": "staged",
            "channel": channel,
            "recipient": recipient,
            "note": "Gmail / messaging integration pending",
        }

    @staticmethod
    def calendar_change(payload: dict) -> dict:
        """Create / update a calendar event via Google Calendar or Outlook."""
        event_title = payload.get("title", payload.get("event_title", ""))
        start       = payload.get("start", payload.get("start_time", ""))
        end         = payload.get("end",   payload.get("end_time", ""))
        description = payload.get("description", payload.get("body", ""))
        location    = payload.get("location", "")

        if not start:
            return {"status": "error", "error": "Missing start time for calendar event."}

        # ── Try Google Calendar first ─────────────────────────────────────────
        try:
            from .gcal_bridge import get_gcal_bridge
            gcal = get_gcal_bridge()
            if gcal is not None:
                result = gcal.create_event(
                    title=event_title,
                    start=start,
                    end=end or start,
                    description=description or None,
                    location=location or None,
                )
                if result.get("error"):
                    logger.warning("calendar_change: gcal error: %s", result["error"])
                else:
                    logger.info("calendar_change: gcal created '%s'", event_title)
                    return {"status": "ok", "backend": "google", "event": result}
        except Exception as exc:
            logger.warning("calendar_change: gcal unavailable: %s", exc)

        # ── Fall back to Outlook ──────────────────────────────────────────────
        try:
            from .outlook_bridge import get_outlook_bridge
            outlook = get_outlook_bridge()
            if outlook is not None:
                result = outlook.create_calendar_event(
                    title=event_title,
                    start=start,
                    end=end or None,
                    description=description,
                    location=location,
                )
                if result.get("error"):
                    logger.warning("calendar_change: outlook error: %s", result["error"])
                    return {"status": "error", "error": result["error"]}
                logger.info("calendar_change: outlook created '%s'", event_title)
                return {"status": "ok", "backend": "outlook", "event": result}
        except Exception as exc:
            logger.warning("calendar_change: outlook unavailable: %s", exc)

        return {
            "status": "error",
            "error": "No calendar backend available. Please connect Google Calendar or Outlook in Settings.",
        }

    @staticmethod
    def home_control(payload: dict) -> dict:
        """
        Call a Home Assistant service. Live via HomeAssistantConnector when
        the data aggregator is available; otherwise stubs gracefully.
        """
        try:
            from .data_connectors import get_aggregator
            agg = get_aggregator()
            if agg and hasattr(agg, "ha") and agg.ha is not None:
                domain = str(payload.get("ha_domain", "light"))
                service = str(payload.get("ha_service", "turn_on"))
                entity_id = str(payload.get("entity_id", ""))
                success = agg.ha.call_service(domain, service, entity_id)
                return {
                    "status": "executed" if success else "failed",
                    "entity": entity_id,
                    "domain": domain,
                    "service": service,
                }
        except Exception as exc:
            logger.debug("home_control live dispatch failed: %s", exc)
        entity_id = payload.get("entity_id", "")
        logger.info("STUB home_control: entity=%s", entity_id)
        return {
            "status": "staged",
            "entity": entity_id,
            "note": "Home Assistant not configured or connector unavailable",
        }

    @staticmethod
    def social_post(payload: dict) -> dict:
        """Post to a social platform. Stub pending social integration."""
        platform = payload.get("platform", "unknown")
        logger.info("STUB social_post: platform=%s", platform)
        return {
            "status": "staged",
            "platform": platform,
            "note": "Social media integration pending",
        }

    @staticmethod
    def purchase(payload: dict) -> dict:
        """Execute a purchase. Stub — always requires HIGH/CRITICAL approval."""
        vendor = payload.get("vendor", "unknown")
        amount = payload.get("amount_usd", "unknown")
        logger.info("STUB purchase: vendor=%s amount=%s", vendor, amount)
        return {
            "status": "staged",
            "vendor": vendor,
            "amount_usd": amount,
            "note": "Purchase integration pending; manual completion required",
        }

    @staticmethod
    def deploy(payload: dict) -> dict:
        """Deploy content or code. Stub pending deploy integration."""
        target = payload.get("target", "unknown")
        logger.info("STUB deploy: target=%s", target)
        return {
            "status": "staged",
            "target": target,
            "note": "Deploy integration pending",
        }

    @staticmethod
    def document_send(payload: dict) -> dict:
        """Send a document to a recipient. Stub."""
        recipient = payload.get("to", payload.get("recipient", "unknown"))
        doc = payload.get("document_title", payload.get("filename", "document"))
        logger.info("STUB document_send: to=%s doc=%s", recipient, doc)
        return {
            "status": "staged",
            "recipient": recipient,
            "document": doc,
            "note": "Document send integration pending",
        }

    @staticmethod
    def external_api(payload: dict) -> dict:
        """Call an external API endpoint. Stub."""
        url = payload.get("url", "unknown")
        logger.info("STUB external_api: url=%s", url)
        return {
            "status": "staged",
            "url": url,
            "note": "External API integration pending",
        }

    @staticmethod
    def file_write(payload: dict) -> dict:
        """Write a file to disk. Stub."""
        path = payload.get("path", "unknown")
        logger.info("STUB file_write: path=%s", path)
        return {
            "status": "staged",
            "path": path,
            "note": "File write integration pending",
        }

    @staticmethod
    def other(payload: dict) -> dict:
        logger.info("STUB other action: payload keys=%s", list(payload.keys()))
        return {"status": "staged", "note": "Action type 'other' — manual completion required"}

    _DISPATCH: dict[str, Any] = {}  # populated after class definition


# Populate dispatch table after class body
ActionExecutors._DISPATCH = {
    "send_message":    ActionExecutors.send_message,
    "calendar_change": ActionExecutors.calendar_change,
    "home_control":    ActionExecutors.home_control,
    "social_post":     ActionExecutors.social_post,
    "purchase":        ActionExecutors.purchase,
    "deploy":          ActionExecutors.deploy,
    "document_send":   ActionExecutors.document_send,
    "external_api":    ActionExecutors.external_api,
    "file_write":      ActionExecutors.file_write,
    "other":           ActionExecutors.other,
}


# ---------------------------------------------------------------------------
# ApprovalGuard
# ---------------------------------------------------------------------------

class ApprovalGuard:
    """
    Primary agent-facing interface for requesting approval before acting.

    Usage pattern:

        guard = get_approval_guard()

        if guard.can_execute(action_type="file_write", payload={"path": "..."}):
            # SAFE tier — act immediately
            ...
        else:
            request_id = guard.request_approval(
                agent_id="natasha",
                agent_label="Natasha",
                action_type="send_message",
                title="Send follow-up to John Smith",
                description="Reply to John's email about the Q3 proposal.",
                payload={"to": "john@example.com", "subject": "Re: Q3 Proposal", "body": "..."},
            )
            # Execution happens when approved via approve() + execute_approved()
    """

    def __init__(
        self,
        queue: ApprovalQueue,
        supervision_support: Any | None = None,
        sandbox_router: Any | None = None,
    ) -> None:
        self._queue = queue
        self._supervision_support = supervision_support
        self._sandbox_router = sandbox_router

    def set_supervision_support(self, supervision_support: Any | None) -> None:
        self._supervision_support = supervision_support

    def set_sandbox_router(self, sandbox_router: Any | None) -> None:
        self._sandbox_router = sandbox_router

    # ------------------------------------------------------------------
    # Agent-facing API
    # ------------------------------------------------------------------

    def can_execute(
        self,
        action_type: str,
        payload: dict | None = None,
        context: dict | None = None,
    ) -> bool:
        """Returns True only for SAFE tier actions (no approval needed)."""
        tier = classify_action(action_type, payload, context)
        return tier == RiskTier.SAFE

    def request_approval(
        self,
        agent_id: str,
        agent_label: str,
        action_type: str,
        title: str,
        description: str,
        payload: dict,
        actor_id: str = "chris",
        priority: int = 5,
        tags: list[str] | None = None,
        context: dict | None = None,
    ) -> str:
        """
        Build and submit an ApprovalRequest. Returns the request_id.
        Agents call this instead of acting directly for non-SAFE actions.
        """
        context = context or {}
        tier = classify_action(action_type, payload, context)
        now = _now_iso()
        expiry_secs = EXPIRY_WINDOWS.get(tier, 86400)
        expires_at = _iso_plus_seconds(expiry_secs)

        auto_approve_at = ""
        auto_timeout = AUTO_APPROVE_TIMEOUTS.get(tier)
        if auto_timeout is not None and auto_timeout > 0:
            auto_approve_at = _iso_plus_seconds(auto_timeout)

        requires_confirmation = tier in (RiskTier.HIGH, RiskTier.CRITICAL)
        confirmation_phrase = ""
        if requires_confirmation:
            confirmation_phrase = _make_confirmation_phrase(action_type, title)

        trust_zone_id = str(context.get("trust_zone_id", "")).strip()
        lane_id = str(context.get("lane_id", "")).strip()
        arena_id = str(context.get("arena_id", "")).strip()
        requested_outcome = str(context.get("requested_outcome", "")).strip() or description.strip() or title.strip()
        supervision_context = {
            key: value
            for key, value in context.items()
            if key not in {"trust_zone_id", "lane_id", "arena_id", "requested_outcome"}
        }
        supervision_decision: dict[str, Any] = {}
        if self._supervision_support is not None and (trust_zone_id or lane_id):
            try:
                supervision_decision = self._supervision_support.evaluate_action(
                    agent_id=agent_id,
                    action_type=action_type,
                    requested_outcome=requested_outcome or title,
                    trust_zone_id=trust_zone_id,
                    lane_id=lane_id,
                    arena_id=arena_id,
                    context=supervision_context,
                )
            except Exception:
                logger.warning("Supervision decision evaluation failed during request staging", exc_info=True)
                # Fail-closed: if supervision is required but unavailable, block staging
                # rather than queue the request without a ruling (Article III.7 Safe Degradation).
                raise RuntimeError(
                    "Supervision evaluation failed; action cannot be staged without a ruling. "
                    "Resolve the supervision engine fault before retrying."
                ) from None

        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            agent_id=agent_id,
            agent_label=agent_label,
            action_type=action_type,
            title=title,
            description=description,
            payload=payload,
            risk_tier=tier,
            actor_id=actor_id,
            requested_at=now,
            expires_at=expires_at,
            status="pending",
            auto_approve_at=auto_approve_at,
            priority=priority,
            tags=list(tags or []),
            requires_confirmation=requires_confirmation,
            confirmation_phrase=confirmation_phrase,
            trust_zone_id=trust_zone_id,
            lane_id=lane_id,
            arena_id=arena_id,
            requested_outcome=requested_outcome,
            supervision_context=supervision_context,
            supervision_decision=supervision_decision,
        )
        return self._queue.submit(request)

    def execute_approved(self, request_id: str) -> dict:
        """
        Execute an approved action by dispatching to the appropriate executor.
        Logs execution to the audit trail (if audit log available).
        Returns result dict.
        """
        item = self._queue.get_by_id(request_id)
        if item is None:
            return {"status": "error", "detail": "Request not found"}
        if item.status != "approved":
            return {"status": "error", "detail": f"Request status is '{item.status}', not 'approved'"}

        decision = self._resolve_supervision_decision(item)
        if decision:
            resolution = str(decision.get("resolution", "")).strip().lower()
            if resolution == "forbidden":
                return {
                    "status": "error",
                    "detail": "Execution blocked by supervision policy",
                    "supervision_decision": decision,
                }
            if bool(decision.get("sandbox_required")) and not bool(item.payload.get("_sandbox_execution")):
                sandbox_job_id = str(item.payload.get("_sandbox_job_id", "")).strip()
                if self._sandbox_router is not None and sandbox_job_id:
                    try:
                        routed = self._sandbox_router(
                            actor_name=item.approved_by or item.actor_id or "chris",
                            job_id=sandbox_job_id,
                            triggered_by="approval-guard",
                        )
                    except Exception as exc:
                        logger.warning("Sandbox routing failed for %s: %s", request_id, exc, exc_info=True)
                        return {
                            "status": "error",
                            "detail": f"Sandbox routing failed: {exc}",
                            "supervision_decision": decision,
                        }
                    return {
                        "status": "sandbox_routed",
                        "detail": "Execution was routed into the governed sandbox lane",
                        "supervision_decision": decision,
                        "sandbox_job_id": sandbox_job_id,
                        "sandbox_result": routed,
                    }
                return {
                    "status": "error",
                    "detail": "Execution requires sandbox routing before live dispatch",
                    "supervision_decision": decision,
                }

        executor = ActionExecutors._DISPATCH.get(
            item.action_type, ActionExecutors.other
        )
        try:
            result = executor(item.payload)
        except Exception as exc:
            logger.error("Executor failed for %s: %s", request_id, exc)
            result = {"status": "failed", "error": str(exc)}

        self._queue.mark_executed(request_id)

        # Best-effort audit log
        self._write_audit(item, result)

        logger.info(
            "Executed approved action: %s agent=%s action=%s result_status=%s",
            request_id,
            item.agent_id,
            item.action_type,
            result.get("status"),
        )
        return result

    def _resolve_supervision_decision(self, item: ApprovalRequest) -> dict[str, Any]:
        stored = dict(item.supervision_decision or {})
        if self._supervision_support is None:
            return stored
        if not any((item.trust_zone_id, item.lane_id, stored)):
            return {}
        try:
            return self._supervision_support.evaluate_action(
                agent_id=item.agent_id,
                action_type=item.action_type,
                requested_outcome=item.requested_outcome or item.description or item.title,
                trust_zone_id=item.trust_zone_id,
                lane_id=item.lane_id,
                arena_id=item.arena_id,
                context=dict(item.supervision_context or {}),
            )
        except Exception:
            logger.warning("Supervision decision evaluation failed during execution", exc_info=True)
            # Use the stored staging decision only if it contains an explicit resolution.
            # An empty stored dict means staging also failed — fall through to degraded-block
            # rather than proceeding without any ruling (Article III.7 Safe Degradation).
            if str(stored.get("resolution", "")).strip():
                return stored
            return {
                "resolution": "forbidden",
                "approval_required": True,
                "sandbox_required": False,
                "escalation_required": True,
                "rollback_posture": "manual-only",
                "authority_stage": "degraded",
                "reasons": ["Supervision evaluation failed at both staging and execution; execution blocked."],
                "degraded": True,
            }

    def get_pending_for_ui(self, actor_id: str = "chris") -> list[dict]:
        """
        Returns pending approvals formatted for the Needs You zone in the UI.

        Format matches the Chamber's needs_items schema:
          [{"id": str, "text": str, "agent": str, "risk": str, "expires_in": str,
            "action_type": str, "requires_confirmation": bool, "confirmation_phrase": str}]
        """
        pending = self._queue.get_pending(actor_id=actor_id)
        result = []
        for item in pending:
            expires_in = _expires_in_human(item.expires_at)
            result.append({
                "id": item.request_id,
                "text": item.title,
                "sub": item.description,
                "agent": item.agent_label,
                "risk": item.risk_tier,
                "expires_in": expires_in,
                "action_type": item.action_type,
                "priority": item.priority,
                "tags": item.tags,
                "requires_confirmation": item.requires_confirmation,
                "confirmation_phrase": item.confirmation_phrase,
                "requested_at": item.requested_at,
                "auto_approve_at": item.auto_approve_at,
                "payload": item.payload,
            })
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write_audit(self, item: ApprovalRequest, result: dict) -> None:
        try:
            from .audit import AuditLog
            audit_root = Path.home() / ".jarvis" / "audit"
            audit = AuditLog(audit_root)
            audit.log_assistant_action(
                actor=item.agent_id,
                domain="approvals",
                item_id=item.request_id,
                action=item.action_type,
                detail=item.title,
                mode="approved",
                action_class=item.risk_tier,
                policy_basis="approval_gate",
                result_summary=str(result.get("status", "")),
                succeeded=result.get("status") not in ("failed", "error"),
            )
        except Exception:
            logger.debug("Audit log write failed (non-fatal)", exc_info=True)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_guard_singleton: ApprovalGuard | None = None
_queue_singleton: ApprovalQueue | None = None


def get_approval_guard() -> ApprovalGuard | None:
    return _guard_singleton


def get_approval_queue() -> ApprovalQueue | None:
    return _queue_singleton


def configure_approval_guard(
    supervision_support: Any | None = None,
    sandbox_router: Any | None = None,
) -> ApprovalGuard | None:
    if _guard_singleton is None:
        return None
    _guard_singleton.set_supervision_support(supervision_support)
    _guard_singleton.set_sandbox_router(sandbox_router)
    return _guard_singleton


def init_approvals(
    supervision_support: Any | None = None,
    sandbox_router: Any | None = None,
) -> tuple[ApprovalQueue, ApprovalGuard]:
    """
    Initialize the module-level ApprovalQueue and ApprovalGuard singletons.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _guard_singleton, _queue_singleton

    if _guard_singleton is not None:
        _guard_singleton.set_supervision_support(supervision_support)
        _guard_singleton.set_sandbox_router(sandbox_router)
        assert _queue_singleton is not None
        return _queue_singleton, _guard_singleton

    queue = ApprovalQueue()
    guard = ApprovalGuard(
        queue,
        supervision_support=supervision_support,
        sandbox_router=sandbox_router,
    )

    _queue_singleton = queue
    _guard_singleton = guard

    # Process any auto-approvals that accumulated while offline
    auto_count = queue.process_auto_approvals()
    if auto_count:
        logger.info("init_approvals: auto-approved %d LOW risk requests on startup", auto_count)

    logger.info("ApprovalQueue and ApprovalGuard initialised (root=%s)", ApprovalQueue.ROOT)
    return queue, guard


def request_document_review(
    title: str,
    preview: str,
    submission_id: str,
    track_type: str,
    project_id: str = "",
    chapter_number: int | None = None,
    ghostwritr_url: str = "",
) -> str | None:
    """
    Convenience function: submit a document_review ApprovalRequest to the
    module-level queue. Returns the request_id, or None if the queue is not
    initialised.

    All fields are pre-filled for the Ghostwritr / Stan Lee use case.
    """
    guard = get_approval_guard()
    if guard is not None:
        return guard.request_approval(
            agent_id="stan-lee",
            agent_label="Stan Lee",
            action_type="document_review",
            title=f"Review draft: {title}",
            description=(
                f"Draft review for {track_type}: {title}\n\n"
                f"Preview: {preview[:300]}{'...' if len(preview) > 300 else ''}"
            ),
            payload={
                "submission_id": submission_id,
                "project_id": project_id,
                "track_type": track_type,
                "chapter_number": chapter_number,
                "ghostwritr_url": ghostwritr_url,
            },
            actor_id="chris",
            priority=5,
            tags=["writing", "ghostwritr", track_type],
            context={
                "trust_zone_id": "publication_review",
                "lane_id": "wealth-opportunity",
                "requested_outcome": f"Review and stage publishing feedback for '{title}'",
                "touches_external_state": False,
                "reversible": True,
            },
        )

    queue = get_approval_queue()
    if queue is None:
        logger.warning("request_document_review: ApprovalQueue not initialised")
        return None

    description = (
        f"Draft review for {track_type}: {title}\n\n"
        f"Preview: {preview[:300]}{'...' if len(preview) > 300 else ''}"
    )
    expiry_secs = EXPIRY_WINDOWS.get(RiskTier.MEDIUM, 86400)
    request = ApprovalRequest(
        request_id=str(uuid.uuid4()),
        agent_id="stan-lee",
        agent_label="Stan Lee",
        action_type="document_review",
        title=f"Review draft: {title}",
        description=description,
        payload={
            "submission_id": submission_id,
            "project_id": project_id,
            "track_type": track_type,
            "chapter_number": chapter_number,
            "ghostwritr_url": ghostwritr_url,
        },
        risk_tier=RiskTier.MEDIUM,
        actor_id="chris",
        requested_at=_now_iso(),
        expires_at=_iso_plus_seconds(expiry_secs),
        status="pending",
        priority=5,
        tags=["writing", "ghostwritr", track_type],
    )
    return queue.submit(request)
