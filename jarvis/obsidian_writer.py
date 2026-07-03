"""Write learned knowledge back into the Obsidian vault — the other half of
the Obsidian loop. jarvis.obsidian_context reads the vault; this module lets
Jarvis propose new notes drawn from conversation or from what he has learned
about Chris, subject to explicit approval before anything touches disk.

Trust boundary (non-negotiable, per Chris's explicit direction):
  - Jarvis never writes a note silently. Every note is an ApprovalRequest
    (action_type="obsidian_note", risk_tier=MEDIUM — never auto-approves)
    until Chris approves it.
  - Every written note is unambiguously tagged as Jarvis-authored
    (frontmatter: source, created_by, proposal_id) so it is never confused
    with Chris's own writing.
  - Writes only happen in live-vault mode. On a machine that only carries
    the synced retrieval index (e.g. the production server), there is no
    real vault to write into — write_approved_note refuses rather than
    silently doing nothing or writing to the wrong place.
  - Path safety: the resolved destination must stay inside the vault root.
    No proposal-supplied path can escape it.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .obsidian_context import ObsidianVaultSupport

_DEFAULT_NOTE_FOLDER = "Jarvis Notes"

_DIRECT_SAVE_PATTERNS = [
    re.compile(r"^(?:save|write|add|put)\s+(?:this|that)\s+(?:to|in|into)\s+(?:my\s+)?obsidian(?:\s+vault)?\b(?:\s+about\s+(?P<topic>.+))?", re.IGNORECASE),
    re.compile(r"^(?:save|write|add|put)\s+(?:this|that)\s+(?:to|in|into)\s+(?:my\s+)?(?:notes|vault)\b(?:\s+about\s+(?P<topic>.+))?", re.IGNORECASE),
    re.compile(r"^(?:make|create)\s+an?\s+obsidian\s+note\b(?:\s+about\s+(?P<topic>.+))?", re.IGNORECASE),
]


def is_direct_obsidian_save_request(request: str) -> bool:
    cleaned = " ".join(str(request or "").strip().split())
    return any(pattern.match(cleaned) for pattern in _DIRECT_SAVE_PATTERNS)


def extract_obsidian_save_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_SAVE_PATTERNS:
        matched = pattern.match(cleaned)
        if matched:
            topic = str((matched.groupdict().get("topic") or "")).strip().rstrip(".?!")
            return topic
    return ""


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", str(title or "").strip()).strip()
    cleaned = re.sub(r"[\s_]+", " ", cleaned)
    return cleaned[:80].strip() or "Untitled Note"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_vault_relpath(rel_path: str, vault_path: Path, *, fallback_title: str) -> Path:
    """Resolve a proposal-supplied relative path safely inside the vault.

    Falls back to a folder+slug derived from the title if the supplied path
    is empty, absolute, or attempts to escape the vault root. Ensures the
    filename is unique (never overwrites an existing note).
    """
    vault_root = vault_path.resolve()
    candidate = str(rel_path or "").strip().strip("/")
    if not candidate:
        candidate = f"{_DEFAULT_NOTE_FOLDER}/{slugify_title(fallback_title)}.md"
    if not candidate.endswith(".md"):
        candidate = f"{candidate}.md"

    resolved = (vault_root / candidate).resolve()
    try:
        resolved.relative_to(vault_root)
    except ValueError:
        # Escaped the vault (e.g. "../../etc/passwd") — ignore it entirely
        # and use the safe default instead of trying to "fix" a hostile path.
        resolved = (vault_root / _DEFAULT_NOTE_FOLDER / f"{slugify_title(fallback_title)}.md").resolve()
        resolved.relative_to(vault_root)  # re-assert; raises if still unsafe

    base = resolved
    n = 2
    while resolved.exists():
        resolved = base.with_name(f"{base.stem} ({n}){base.suffix}")
        n += 1
    return resolved


def build_note_markdown(
    *,
    title: str,
    body: str,
    tags: list[str],
    proposal_id: str,
    created_at: str,
    source: str,
    source_detail: str,
) -> str:
    tags_yaml = "[" + ", ".join(str(t) for t in tags) + "]" if tags else "[]"
    frontmatter = (
        "---\n"
        f"source: jarvis\n"
        f"created_by: jarvis\n"
        f"proposal_id: {proposal_id}\n"
        f"created_at: {created_at}\n"
        f"origin: {source}\n"
        f"tags: {tags_yaml}\n"
        "---\n\n"
    )
    heading = f"# {title}\n\n"
    footer = f"\n\n---\n*Drafted by Jarvis from {source_detail}. Approved by Chris before being written here.*\n"
    return frontmatter + heading + body.strip() + footer


def propose_note(
    queue: Any,
    *,
    actor_id: str,
    agent_id: str,
    title: str,
    body: str,
    tags: list[str] | None = None,
    suggested_rel_path: str = "",
    source: str = "conversation",
    source_detail: str = "",
) -> dict[str, Any]:
    """Draft a note and submit it for approval. Nothing is written yet."""
    from .approvals import ApprovalRequest, RiskTier

    request_id = str(uuid.uuid4())
    now = _now_iso()
    payload = {
        "title": title,
        "body": body,
        "tags": list(tags or []),
        "suggested_rel_path": suggested_rel_path,
        "source": source,
        "source_detail": source_detail,
    }
    request = ApprovalRequest(
        request_id=request_id,
        agent_id=agent_id,
        agent_label="Jarvis",
        action_type="obsidian_note",
        title=f"Save note to Obsidian: {title}",
        description=(
            f"Jarvis drafted a note titled '{title}' from {source_detail or source}. "
            "Approving writes it into your Obsidian vault, clearly tagged as Jarvis-authored."
        ),
        payload=payload,
        risk_tier=RiskTier.MEDIUM,
        actor_id=actor_id,
        requested_at=now,
        expires_at=now,
        status="pending",
        priority=5,
        tags=["obsidian", "note"],
    )
    queue.submit(request)
    return {
        "proposal_id": request_id,
        "object_kind": "obsidian_note_proposal",
        "title": title,
        "summary": f"Drafted from {source_detail or source}. Waiting on your approval before it's written to Obsidian.",
        "body_preview": body.strip()[:600],
        "tags": list(tags or []),
        "status": "pending_approval",
        "created_at": now,
        "approval_endpoint": f"/api/obsidian/proposals/{request_id}/approve",
        "reject_endpoint": f"/api/approvals/{request_id}/reject",
    }


def write_approved_note(support: ObsidianVaultSupport, request: Any) -> dict[str, Any]:
    """Write an approved proposal's note to disk. Call only after approval.

    Returns {"written": True, "path": ...} on success, or
    {"written": False, "reason": ...} if the vault isn't writable here —
    never raises, never silently no-ops without explanation.
    """
    if support.mode != "live-vault":
        return {
            "written": False,
            "reason": (
                "The Obsidian vault is not writable from this machine "
                f"(mode={support.mode}). Notes can only be written on the Mac "
                "where the vault actually lives."
            ),
        }
    payload = dict(getattr(request, "payload", {}) or {})
    title = str(payload.get("title", "")).strip() or "Untitled Note"
    body = str(payload.get("body", ""))
    tags = list(payload.get("tags") or [])
    source = str(payload.get("source", "conversation"))
    source_detail = str(payload.get("source_detail", ""))
    proposal_id = str(getattr(request, "request_id", ""))
    created_at = _now_iso()

    try:
        dest = sanitize_vault_relpath(
            str(payload.get("suggested_rel_path", "")),
            support.vault_path,
            fallback_title=title,
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        markdown = build_note_markdown(
            title=title,
            body=body,
            tags=tags,
            proposal_id=proposal_id,
            created_at=created_at,
            source=source,
            source_detail=source_detail,
        )
        dest.write_text(markdown, encoding="utf-8")
    except Exception as exc:
        return {"written": False, "reason": f"Write failed: {exc}"}

    return {
        "written": True,
        "path": str(dest.relative_to(support.vault_path.resolve())),
        "absolute_path": str(dest),
        "written_at": created_at,
    }
