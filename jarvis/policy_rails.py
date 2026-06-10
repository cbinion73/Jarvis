"""
JARVIS Policy Rails — canonical action taxonomy and hard policy enforcement.

This module defines:
1. CANONICAL_ACTION_TAXONOMY — every known action type mapped to family, risk tier,
   minimum authority stage, approval mode, and audit requirement.
2. HARD_BOUNDARY_FAMILIES — action families that require explicit authority,
   pre-approval, and audit record regardless of trust zone stage.
3. assess_action_policy() — the single authoritative function for classifying any
   action and determining whether it is allowed, staged, or denied.

Unknown action types fail CLOSED — they are denied until explicitly registered.

Constitutional basis: JARVIS-CONSTITUTION-FOR-SELF-IMPROVING-INTELLIGENCE.md
Articles III (Boundary Clarity), VI (Hard Escalation Lines).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Action family constants
# ---------------------------------------------------------------------------

FAMILY_OBSERVE = "observe"          # read-only, no side effects
FAMILY_DRAFT = "draft"              # produces output for human review; no send
FAMILY_COORDINATE = "coordinate"    # schedules, notifies, routes within approved scope
FAMILY_HOME = "home"                # physical home state changes (locks, climate, lights)
FAMILY_MEMORY = "memory"            # write/delete durable memory or profile facts
FAMILY_AGENT = "agent"             # create, retire, promote, or configure agents
FAMILY_GOVERNANCE = "governance"   # trust zone, arena, doctrine, approval mutations
FAMILY_MONEY = "money"             # spending, transactions, financial accounts
FAMILY_IDENTITY = "identity"       # account creation, credentials, public identity
FAMILY_LEGAL = "legal"             # contracts, legal filings, public representation
FAMILY_SECURITY = "security"       # physical security, unlock, surveillance actions
FAMILY_CHILDREN = "children"       # any action touching child-tagged data or users
FAMILY_REPUTATION = "reputation"   # public posting, publishing, external comms
FAMILY_SYSTEM = "system"           # self-modification, code changes, runtime mutations


# ---------------------------------------------------------------------------
# Risk tiers
# ---------------------------------------------------------------------------

RISK_LOW = 1        # reversible, bounded, non-consequential
RISK_MEDIUM = 2     # moderate consequence; review recommended
RISK_HIGH = 3       # significant consequence; pre-approval required
RISK_CRITICAL = 4   # irreversible or catastrophic risk; requires explicit human action


# ---------------------------------------------------------------------------
# Minimum authority stages
# ---------------------------------------------------------------------------

STAGE_OBSERVE = "observe"
STAGE_DRAFT = "draft"
STAGE_STAGE_ALERT = "stage_alert"
STAGE_SANDBOX_LIVE = "sandbox_live"
STAGE_MATURE_LIVE = "mature_live"


# ---------------------------------------------------------------------------
# Hard boundary families — require explicit authority and audit regardless of zone
# ---------------------------------------------------------------------------

HARD_BOUNDARY_FAMILIES: frozenset[str] = frozenset({
    FAMILY_MONEY,
    FAMILY_IDENTITY,
    FAMILY_LEGAL,
    FAMILY_SECURITY,
    FAMILY_CHILDREN,
    FAMILY_REPUTATION,
    FAMILY_SYSTEM,
})


@dataclass(frozen=True)
class ActionPolicy:
    """Policy specification for a single action type."""
    action_type: str
    family: str
    risk_tier: int                      # 1-4
    min_authority_stage: str            # minimum zone authority stage to allow
    approval_mode: str                  # "auto" | "stage" | "pre-approve" | "deny"
    audit_required: bool                # always write audit record
    description: str
    reversible: bool = True
    hard_boundary: bool = False         # forces pre-approval regardless of stage
    parent_review_required: bool = False  # requires parent actor acknowledgment


# ---------------------------------------------------------------------------
# Canonical action taxonomy
# ---------------------------------------------------------------------------

CANONICAL_ACTION_TAXONOMY: dict[str, ActionPolicy] = {
    # --- observe ---
    "read_state": ActionPolicy("read_state", FAMILY_OBSERVE, RISK_LOW, STAGE_OBSERVE, "auto", False, "Read system or household state."),
    "search_memory": ActionPolicy("search_memory", FAMILY_OBSERVE, RISK_LOW, STAGE_OBSERVE, "auto", False, "Search durable memory store."),
    "view_calendar": ActionPolicy("view_calendar", FAMILY_OBSERVE, RISK_LOW, STAGE_OBSERVE, "auto", False, "View calendar events."),
    "view_health": ActionPolicy("view_health", FAMILY_OBSERVE, RISK_LOW, STAGE_OBSERVE, "auto", False, "View health data."),
    "list_approvals": ActionPolicy("list_approvals", FAMILY_OBSERVE, RISK_LOW, STAGE_OBSERVE, "auto", False, "List pending approvals."),

    # --- draft ---
    "draft_email": ActionPolicy("draft_email", FAMILY_DRAFT, RISK_LOW, STAGE_DRAFT, "stage", True, "Draft email for human review before send."),
    "draft_document": ActionPolicy("draft_document", FAMILY_DRAFT, RISK_LOW, STAGE_DRAFT, "stage", True, "Draft document or text artifact."),
    "draft_schedule": ActionPolicy("draft_schedule", FAMILY_DRAFT, RISK_LOW, STAGE_DRAFT, "stage", True, "Propose schedule changes for review."),

    # --- coordinate ---
    "notification_workflow": ActionPolicy("notification_workflow", FAMILY_COORDINATE, RISK_LOW, STAGE_DRAFT, "auto", False, "Route notifications within approved policy."),
    "reminder_workflow": ActionPolicy("reminder_workflow", FAMILY_COORDINATE, RISK_LOW, STAGE_DRAFT, "auto", False, "Create or update reminders."),
    "focus_workflow": ActionPolicy("focus_workflow", FAMILY_COORDINATE, RISK_LOW, STAGE_DRAFT, "auto", False, "Manage focus/interrupt policy."),
    "calendar_route": ActionPolicy("calendar_route", FAMILY_COORDINATE, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Route calendar events or meeting prep."),
    "signal_resolution": ActionPolicy("signal_resolution", FAMILY_COORDINATE, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Resolve and route attention signals."),
    "huddle_workflow": ActionPolicy("huddle_workflow", FAMILY_COORDINATE, RISK_LOW, STAGE_DRAFT, "auto", False, "Prepare household huddle or briefing."),
    "stewardship_lane_review": ActionPolicy("stewardship_lane_review", FAMILY_COORDINATE, RISK_LOW, STAGE_DRAFT, "auto", False, "Review stewardship lane metadata."),

    # --- home ---
    "home_control": ActionPolicy("home_control", FAMILY_HOME, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Change physical home state (locks, climate, lights, garage).", reversible=True),
    "lock_action": ActionPolicy("lock_action", FAMILY_HOME, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Lock or unlock a door."),
    "climate_action": ActionPolicy("climate_action", FAMILY_HOME, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Adjust thermostat or climate setting."),
    "light_action": ActionPolicy("light_action", FAMILY_HOME, RISK_LOW, STAGE_STAGE_ALERT, "stage", False, "Control lights."),

    # --- memory ---
    "write_memory": ActionPolicy("write_memory", FAMILY_MEMORY, RISK_MEDIUM, STAGE_DRAFT, "stage", True, "Write a new durable memory entry."),
    "delete_memory": ActionPolicy("delete_memory", FAMILY_MEMORY, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Delete a durable memory entry.", reversible=False),
    "update_profile": ActionPolicy("update_profile", FAMILY_MEMORY, RISK_MEDIUM, STAGE_DRAFT, "stage", True, "Update a user profile fact."),

    # --- agent ---
    "spawn_agent": ActionPolicy("spawn_agent", FAMILY_AGENT, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Create a new agent in the registry."),
    "retire_agent": ActionPolicy("retire_agent", FAMILY_AGENT, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Retire an active agent.", reversible=False),
    "assign_agent": ActionPolicy("assign_agent", FAMILY_AGENT, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Assign an agent to a mission or task."),
    "foundry_proposal_review": ActionPolicy("foundry_proposal_review", FAMILY_AGENT, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Review and approve a foundry agent proposal."),

    # --- governance ---
    "promote_zone": ActionPolicy("promote_zone", FAMILY_GOVERNANCE, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Promote a trust zone to a higher authority stage.", hard_boundary=True),
    "suspend_zone": ActionPolicy("suspend_zone", FAMILY_GOVERNANCE, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Suspend a trust zone.", hard_boundary=True),
    "update_doctrine": ActionPolicy("update_doctrine", FAMILY_GOVERNANCE, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Update shared doctrine or policy."),
    "approve_action": ActionPolicy("approve_action", FAMILY_GOVERNANCE, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Approve a staged action."),
    "publishing_review": ActionPolicy("publishing_review", FAMILY_GOVERNANCE, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Review a publishing or outbound-content action."),

    # --- money (HARD BOUNDARY) ---
    "spend_money": ActionPolicy("spend_money", FAMILY_MONEY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Spend or commit money.", reversible=False, hard_boundary=True),
    "create_transaction": ActionPolicy("create_transaction", FAMILY_MONEY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Create a financial transaction.", reversible=False, hard_boundary=True),
    "transfer_funds": ActionPolicy("transfer_funds", FAMILY_MONEY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Transfer funds between accounts.", reversible=False, hard_boundary=True),
    "financial_commitment": ActionPolicy("financial_commitment", FAMILY_MONEY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Make a financial commitment or contract.", reversible=False, hard_boundary=True),

    # --- identity (HARD BOUNDARY) ---
    "create_account": ActionPolicy("create_account", FAMILY_IDENTITY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Create an external account or service.", reversible=False, hard_boundary=True),
    "change_credentials": ActionPolicy("change_credentials", FAMILY_IDENTITY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Change login credentials or API keys.", reversible=False, hard_boundary=True),
    "share_identity": ActionPolicy("share_identity", FAMILY_IDENTITY, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Share identity or personal information externally.", hard_boundary=True),

    # --- legal (HARD BOUNDARY) ---
    "sign_document": ActionPolicy("sign_document", FAMILY_LEGAL, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Sign or execute a legal document.", reversible=False, hard_boundary=True),
    "submit_filing": ActionPolicy("submit_filing", FAMILY_LEGAL, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Submit a legal or regulatory filing.", reversible=False, hard_boundary=True),
    "make_legal_representation": ActionPolicy("make_legal_representation", FAMILY_LEGAL, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Make a public legal representation.", reversible=False, hard_boundary=True),

    # --- security (HARD BOUNDARY) ---
    "remote_unlock": ActionPolicy("remote_unlock", FAMILY_SECURITY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Unlock door or gate remotely.", reversible=False, hard_boundary=True),
    "disable_alarm": ActionPolicy("disable_alarm", FAMILY_SECURITY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Disable a security alarm.", hard_boundary=True),
    "grant_physical_access": ActionPolicy("grant_physical_access", FAMILY_SECURITY, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Grant physical access to a location.", reversible=False, hard_boundary=True),
    "surveillance_action": ActionPolicy("surveillance_action", FAMILY_SECURITY, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Record or access camera/audio feed.", hard_boundary=True),

    # --- children (HARD BOUNDARY) ---
    "access_child_data": ActionPolicy("access_child_data", FAMILY_CHILDREN, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Access data tagged as belonging to a child.", hard_boundary=True, parent_review_required=True),
    "share_child_data": ActionPolicy("share_child_data", FAMILY_CHILDREN, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Share child data externally.", reversible=False, hard_boundary=True, parent_review_required=True),
    "override_child_guardrail": ActionPolicy("override_child_guardrail", FAMILY_CHILDREN, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Override a child safety guardrail.", reversible=False, hard_boundary=True, parent_review_required=True),
    "child_tutoring_action": ActionPolicy("child_tutoring_action", FAMILY_CHILDREN, RISK_MEDIUM, STAGE_STAGE_ALERT, "stage", True, "Tutoring or educational action for a child.", parent_review_required=True),

    # --- reputation (HARD BOUNDARY) ---
    "publish_external": ActionPolicy("publish_external", FAMILY_REPUTATION, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Publish content to an external audience.", hard_boundary=True),
    "post_social": ActionPolicy("post_social", FAMILY_REPUTATION, RISK_CRITICAL, STAGE_MATURE_LIVE, "deny", True, "Post to social media.", reversible=False, hard_boundary=True),
    "send_email": ActionPolicy("send_email", FAMILY_REPUTATION, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Send an email to an external party.", hard_boundary=True),

    # --- system (HARD BOUNDARY) ---
    "modify_codebase": ActionPolicy("modify_codebase", FAMILY_SYSTEM, RISK_HIGH, STAGE_SANDBOX_LIVE, "pre-approve", True, "Modify JARVIS source code.", hard_boundary=True),
    "update_config": ActionPolicy("update_config", FAMILY_SYSTEM, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Update system configuration.", hard_boundary=True),
    "restart_service": ActionPolicy("restart_service", FAMILY_SYSTEM, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Restart a JARVIS service."),
    "database_mutation": ActionPolicy("database_mutation", FAMILY_SYSTEM, RISK_HIGH, STAGE_STAGE_ALERT, "pre-approve", True, "Mutate the database schema or bulk data.", hard_boundary=True),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

UNKNOWN_ACTION_POLICY = ActionPolicy(
    action_type="_unknown",
    family="_unknown",
    risk_tier=RISK_CRITICAL,
    min_authority_stage=STAGE_MATURE_LIVE,
    approval_mode="deny",
    audit_required=True,
    description="Unknown/unregistered action type — fails closed by policy.",
    reversible=False,
    hard_boundary=True,
)


def get_action_policy(action_type: str) -> ActionPolicy:
    """Return the canonical policy for an action type.
    Unknown action types return UNKNOWN_ACTION_POLICY — they fail closed."""
    return CANONICAL_ACTION_TAXONOMY.get(str(action_type).strip(), UNKNOWN_ACTION_POLICY)


def is_hard_boundary(action_type: str) -> bool:
    """True if this action type is in a hard boundary family."""
    return get_action_policy(action_type).hard_boundary


def requires_parent_review(action_type: str) -> bool:
    """True if this action type involves child data and requires parent review."""
    return get_action_policy(action_type).parent_review_required


def action_family(action_type: str) -> str:
    """Return the action family for a given action type."""
    return get_action_policy(action_type).family


def action_risk_tier(action_type: str) -> int:
    """Return 1-4 risk tier for an action type."""
    return get_action_policy(action_type).risk_tier


def assess_action_policy(
    action_type: str,
    *,
    authority_stage: str,
    zone_id: str = "",
    actor: str = "",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Canonical policy assessment for any action type.

    Returns a structured verdict with:
    - decision: "allow" | "stage" | "deny"
    - policy_action_type: the action type assessed
    - family: action family
    - risk_tier: 1-4
    - hard_boundary: whether this is a hard policy boundary
    - min_authority_stage: minimum zone stage required
    - approval_mode: "auto" | "stage" | "pre-approve" | "deny"
    - reason: human-readable explanation
    - audit_required: bool
    - parent_review_required: bool (for child actions)
    """
    policy = get_action_policy(action_type)
    ctx = dict(context or {})

    # Unknown action type — always deny
    if policy.action_type == "_unknown":
        return {
            "decision": "deny",
            "policy_action_type": action_type,
            "registered": False,
            "family": "_unknown",
            "risk_tier": RISK_CRITICAL,
            "hard_boundary": True,
            "min_authority_stage": STAGE_MATURE_LIVE,
            "approval_mode": "deny",
            "reason": (
                f"Unknown action type '{action_type}' is not registered in the canonical "
                "action taxonomy. Unknown actions fail closed. Register the action type in "
                "jarvis/policy_rails.py to enable it."
            ),
            "audit_required": True,
            "parent_review_required": False,
            "zone_id": zone_id,
            "actor": actor,
        }

    # Hard boundary families always deny regardless of stage
    if policy.hard_boundary and policy.approval_mode == "deny":
        return {
            "decision": "deny",
            "policy_action_type": action_type,
            "registered": True,
            "family": policy.family,
            "risk_tier": policy.risk_tier,
            "hard_boundary": True,
            "min_authority_stage": policy.min_authority_stage,
            "approval_mode": "deny",
            "reason": (
                f"Action '{action_type}' is in the hard boundary family '{policy.family}'. "
                "This action requires explicit human initiation and cannot be performed by "
                "an automated agent under any zone stage."
            ),
            "audit_required": True,
            "parent_review_required": policy.parent_review_required,
            "zone_id": zone_id,
            "actor": actor,
        }

    # Sequence-based check: authority stage sufficiency
    stage_sequence = {
        STAGE_OBSERVE: 0,
        STAGE_DRAFT: 1,
        STAGE_STAGE_ALERT: 2,
        STAGE_SANDBOX_LIVE: 3,
        STAGE_MATURE_LIVE: 4,
    }
    current_seq = stage_sequence.get(authority_stage, 0)
    required_seq = stage_sequence.get(policy.min_authority_stage, 0)

    if current_seq < required_seq:
        return {
            "decision": "stage",
            "policy_action_type": action_type,
            "registered": True,
            "family": policy.family,
            "risk_tier": policy.risk_tier,
            "hard_boundary": policy.hard_boundary,
            "min_authority_stage": policy.min_authority_stage,
            "approval_mode": policy.approval_mode,
            "reason": (
                f"Zone '{zone_id}' is at stage '{authority_stage}' but action '{action_type}' "
                f"requires at least '{policy.min_authority_stage}'. Must promote before live execution."
            ),
            "audit_required": policy.audit_required,
            "parent_review_required": policy.parent_review_required,
            "zone_id": zone_id,
            "actor": actor,
        }

    # Hard boundary with pre-approve mode requires explicit pre-approval
    if policy.hard_boundary and policy.approval_mode == "pre-approve":
        pre_approved = bool(ctx.get("pre_approved"))
        approval_id = str(ctx.get("approval_id", "")).strip()
        if not pre_approved or not approval_id:
            return {
                "decision": "stage",
                "policy_action_type": action_type,
                "registered": True,
                "family": policy.family,
                "risk_tier": policy.risk_tier,
                "hard_boundary": True,
                "min_authority_stage": policy.min_authority_stage,
                "approval_mode": "pre-approve",
                "reason": (
                    f"Action '{action_type}' is a hard boundary action in family '{policy.family}'. "
                    "Explicit pre-approval is required. Submit for approval first and include "
                    "pre_approved=True and approval_id in the context."
                ),
                "audit_required": True,
                "parent_review_required": policy.parent_review_required,
                "zone_id": zone_id,
                "actor": actor,
            }

    # Parent review requirement for child actions
    if policy.parent_review_required:
        parent_acknowledged = bool(ctx.get("parent_acknowledged"))
        if not parent_acknowledged:
            return {
                "decision": "stage",
                "policy_action_type": action_type,
                "registered": True,
                "family": policy.family,
                "risk_tier": policy.risk_tier,
                "hard_boundary": policy.hard_boundary,
                "min_authority_stage": policy.min_authority_stage,
                "approval_mode": policy.approval_mode,
                "reason": (
                    f"Action '{action_type}' involves child data and requires parent acknowledgment. "
                    "Set parent_acknowledged=True in context after authorized parent review."
                ),
                "audit_required": True,
                "parent_review_required": True,
                "zone_id": zone_id,
                "actor": actor,
            }

    # Stage mode — route for review, don't execute live
    if policy.approval_mode == "stage":
        return {
            "decision": "stage",
            "policy_action_type": action_type,
            "registered": True,
            "family": policy.family,
            "risk_tier": policy.risk_tier,
            "hard_boundary": policy.hard_boundary,
            "min_authority_stage": policy.min_authority_stage,
            "approval_mode": "stage",
            "reason": (
                f"Action '{action_type}' in family '{policy.family}' must be staged for review "
                f"before execution. Risk tier: {policy.risk_tier}."
            ),
            "audit_required": policy.audit_required,
            "parent_review_required": policy.parent_review_required,
            "zone_id": zone_id,
            "actor": actor,
        }

    # Allow
    return {
        "decision": "allow",
        "policy_action_type": action_type,
        "registered": True,
        "family": policy.family,
        "risk_tier": policy.risk_tier,
        "hard_boundary": policy.hard_boundary,
        "min_authority_stage": policy.min_authority_stage,
        "approval_mode": policy.approval_mode,
        "reason": f"Action '{action_type}' is allowed at stage '{authority_stage}'.",
        "audit_required": policy.audit_required,
        "parent_review_required": policy.parent_review_required,
        "zone_id": zone_id,
        "actor": actor,
    }


def list_action_taxonomy() -> list[dict[str, Any]]:
    """Return the full action taxonomy as a list of dicts for API consumption."""
    rows = []
    for action_type, policy in sorted(CANONICAL_ACTION_TAXONOMY.items()):
        rows.append({
            "action_type": policy.action_type,
            "family": policy.family,
            "risk_tier": policy.risk_tier,
            "min_authority_stage": policy.min_authority_stage,
            "approval_mode": policy.approval_mode,
            "audit_required": policy.audit_required,
            "hard_boundary": policy.hard_boundary,
            "reversible": policy.reversible,
            "parent_review_required": policy.parent_review_required,
            "description": policy.description,
        })
    return rows


def governance_plain_language_summary(
    zones: list[dict],
    pending_approvals: list[dict],
    recent_promotions: list[dict],
    blocked_actions: list[dict],
) -> dict[str, Any]:
    """
    Produce a plain-language governance summary for household users.
    No JSON or code required to understand JARVIS's current authority posture.
    """
    active_zones = [z for z in zones if str(z.get("status", "")).lower() == "active"]
    inactive_zones = [z for z in zones if str(z.get("status", "")).lower() != "active"]

    zone_summaries = []
    for z in active_zones:
        stage = str(z.get("authority_stage", "observe"))
        stage_label = {
            "observe": "Read-only (can watch, not act)",
            "draft": "Draft mode (can prepare, not send)",
            "stage_alert": "Staged (can prepare live actions for your review)",
            "sandbox_live": "Sandbox live (can act in limited scope, pauses for big moves)",
            "mature_live": "Fully delegated (acts autonomously within this zone)",
        }.get(stage, stage)
        zone_summaries.append({
            "zone": str(z.get("zone_id", "")),
            "label": str(z.get("name") or z.get("zone_id", "")),
            "status": "Active",
            "authority": stage_label,
            "plain": f"{z.get('name', z.get('zone_id', ''))} — {stage_label}",
        })

    blocked_summaries = []
    for b in blocked_actions[:10]:
        blocked_summaries.append({
            "action": str(b.get("action_type", "")),
            "reason": str(b.get("reason", "")),
            "blocked_at": str(b.get("blocked_at", "")),
            "plain": f"Blocked: {b.get('action_type', '')} — {b.get('reason', '')}",
        })

    approval_summaries = []
    for a in pending_approvals[:10]:
        approval_summaries.append({
            "request_id": str(a.get("request_id", "")),
            "action": str(a.get("action_type", "")),
            "summary": str(a.get("summary") or a.get("detail", ""))[:120],
            "submitted_by": str(a.get("actor", "")),
            "plain": f"Needs your approval: {a.get('action_type', '')} — {(a.get('summary') or a.get('detail', ''))[:80]}",
        })

    promotion_summaries = []
    for p in recent_promotions[:5]:
        promotion_summaries.append({
            "zone": str(p.get("trust_zone", "")),
            "from_stage": str(p.get("current_stage", "")),
            "to_stage": str(p.get("target_stage", "")),
            "decision": str(p.get("decision", "")),
            "plain": f"{p.get('trust_zone', '')} moved from {p.get('current_stage', '')} to {p.get('target_stage', '')} — {p.get('decision', '')}",
        })

    return {
        "active_zone_count": len(active_zones),
        "inactive_zone_count": len(inactive_zones),
        "pending_approval_count": len(pending_approvals),
        "recent_blocked_count": len(blocked_actions),
        "zones": zone_summaries,
        "inactive_zones": [{"zone": z.get("zone_id", ""), "status": z.get("status", "")} for z in inactive_zones],
        "pending_approvals": approval_summaries,
        "recent_blocked_actions": blocked_summaries,
        "recent_promotions": promotion_summaries,
        "plain_summary": (
            f"JARVIS has {len(active_zones)} active operating zones. "
            f"{len(pending_approvals)} action(s) need your approval. "
            f"{len(blocked_actions)} action(s) were blocked recently. "
            f"All hard boundaries (money, legal, security, children) require explicit human action."
        ),
    }
