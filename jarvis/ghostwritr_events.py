"""
ghostwritr_events.py — Ghostwritr Live Event Poller
====================================================
Polls Ghostwritr for stage/status changes and automatically triggers
JARVIS actions (book launch pipeline, notifications, etc.).

Runs as a background asyncio task inside the JARVIS FastAPI service.
Poll interval: 60 seconds.

Events handled:
    • Book stage → READY_FOR_REVIEW     → create approval in JARVIS
    • Book stage → COMMITTED (all done) → trigger pre-launch prep
    • Book status → PUBLISHED           → trigger full launch assets
    • New book created                  → add to JARVIS idea inbox as 'queued'
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

logger = logging.getLogger("jarvis.ghostwritr_events")

_STATE_PATH = Path.home() / ".jarvis" / "ghostwritr_events_state.json"
_STATE_LOG_PATH = _STATE_PATH.with_name("ghostwritr_events_state_log.jsonl")
_STATE_STATE_LOG_PATH = _STATE_PATH.with_name("ghostwritr_events_state_state_log.jsonl")
_POLL_INTERVAL = 60  # seconds


def _load_state() -> dict:
    try:
        if _STATE_PATH.exists():
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Ghostwritr events snapshot unreadable; replaying state log")
    if _STATE_STATE_LOG_PATH.exists():
        try:
            last: dict[str, Any] | None = None
            for line in _STATE_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    last = payload
            if last is not None:
                atomic_write_json(_STATE_PATH, last)
                return last
        except Exception:
            logger.warning("Ghostwritr events state log unreadable", exc_info=True)
    if _STATE_LOG_PATH.exists():
        try:
            last: dict[str, Any] | None = None
            for line in _STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    last = payload
            if last is not None:
                atomic_write_json(_STATE_PATH, last)
                return last
        except Exception:
            logger.warning("Ghostwritr events append log unreadable", exc_info=True)
    return {"seen_stages": {}, "seen_books": [], "last_poll": ""}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(_STATE_LOG_PATH, state)
    append_jsonl(_STATE_STATE_LOG_PATH, state)
    atomic_write_json(_STATE_PATH, state)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _handle_stage_change(bridge: Any, book_row: dict, stage: dict, event_key: str) -> None:
    """Called when a stage status changes to something interesting."""
    slug = book_row.get("slug", "")
    stage_key = stage.get("stageKey") or stage.get("stage_key", "?")
    stage_status = stage.get("status", "")
    title = book_row.get("titleWorking") or book_row.get("title") or slug

    logger.info("GhostwritrEvents: stage change — %s / %s → %s", slug, stage_key, stage_status)

    if stage_status == "READY_FOR_REVIEW":
        # This is handled by the existing review-checker; skip here to avoid duplicates
        pass

    elif stage_status == "COMMITTED":
        # Check if ALL stages are now committed → trigger pre-launch
        try:
            pairs = bridge._list_books_with_stages()
            for br, stages in pairs:
                if br.get("slug") == slug:
                    all_committed = all(
                        s.get("status") in ("COMMITTED", "SKIPPED")
                        for s in stages
                        if s.get("status") not in ("PENDING",)
                    )
                    committed_count = sum(1 for s in stages if s.get("status") == "COMMITTED")
                    total = len(stages)
                    logger.info("GhostwritrEvents: %s committed %d/%d stages", slug, committed_count, total)
                    # Trigger pre-launch if ≥75% of stages committed
                    if total > 0 and committed_count / total >= 0.75:
                        await _trigger_launch(slug, "pre_launch", title)
        except Exception as exc:
            logger.warning("GhostwritrEvents: stage check failed: %s", exc)


async def _trigger_launch(slug: str, trigger: str, title: str) -> None:
    """Trigger the JARVIS launch pipeline via HTTP."""
    import httpx
    base = "http://127.0.0.1:8787"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{base}/api/publishing/launch/{slug}/generate",
                json={"force": False, "trigger": trigger},
            )
            if resp.status_code in (200, 202, 409):
                logger.info("GhostwritrEvents: launch triggered for '%s' (%s)", slug, trigger)
            else:
                logger.warning("GhostwritrEvents: launch trigger returned %d for '%s'", resp.status_code, slug)
    except Exception as exc:
        logger.warning("GhostwritrEvents: could not trigger launch for '%s': %s", slug, exc)


async def _handle_book_published(book_row: dict) -> None:
    """Trigger full launch pipeline when a book is marked PUBLISHED."""
    slug = book_row.get("slug", "")
    title = book_row.get("titleWorking") or book_row.get("title") or slug
    logger.info("GhostwritrEvents: book PUBLISHED — '%s', triggering post-publish launch", slug)
    await _trigger_launch(slug, "post_publish", title)


async def _handle_new_book(book_row: dict) -> None:
    """Add newly created book as a JARVIS idea."""
    slug = book_row.get("slug", "")
    title = book_row.get("titleWorking") or book_row.get("title") or slug
    logger.info("GhostwritrEvents: new book detected — '%s', adding to idea inbox", slug)
    try:
        try:
            from .ideas import add_idea
        except ImportError:
            from ideas import add_idea
        add_idea(
            text=title,
            source="ghostwritr",
            notes=f"Book imported from Ghostwritr (slug: {slug})",
            domain="books",
            tags=["ghostwritr", "book", slug],
        )
    except Exception as exc:
        logger.warning("GhostwritrEvents: could not add idea for '%s': %s", slug, exc)


async def poll_once(bridge: Any) -> None:
    """Run one poll cycle — check for changes and fire handlers."""
    state = _load_state()
    seen_stages: dict = state.get("seen_stages", {})
    seen_books: list = state.get("seen_books", [])
    changed = False

    try:
        pairs = await asyncio.to_thread(bridge._list_books_with_stages)
    except Exception as exc:
        logger.debug("GhostwritrEvents: poll failed: %s", exc)
        return

    current_slugs = []
    for book_row, stages in pairs:
        slug = book_row.get("slug", "")
        if not slug:
            continue
        current_slugs.append(slug)
        book_status = book_row.get("status", "")

        # New book detection
        if slug not in seen_books:
            if seen_books:  # only fire if we've seen books before (not first run)
                await _handle_new_book(book_row)
            seen_books.append(slug)
            changed = True

        # Book published
        pub_key = f"{slug}:PUBLISHED"
        if book_status == "PUBLISHED" and pub_key not in seen_stages:
            await _handle_book_published(book_row)
            seen_stages[pub_key] = _now()
            changed = True

        # Stage changes
        for stage in stages:
            stage_id = stage.get("id") or f"{slug}:{stage.get('stageKey','?')}"
            event_key = f"{stage_id}:{stage.get('status','')}"
            if event_key not in seen_stages:
                if seen_stages:  # skip on very first poll
                    await _handle_stage_change(bridge, book_row, stage, event_key)
                seen_stages[event_key] = _now()
                changed = True

    if changed:
        state["seen_stages"] = seen_stages
        state["seen_books"] = seen_books
        state["last_poll"] = _now()
        await asyncio.to_thread(_save_state, state)
    else:
        # Update last_poll timestamp
        state["last_poll"] = _now()
        await asyncio.to_thread(_save_state, state)


async def run_event_loop(bridge: Any) -> None:
    """
    Continuous poll loop. Call this as an asyncio task from service.py.
    Runs until cancelled.
    """
    logger.info("GhostwritrEvents: starting poll loop (interval=%ds)", _POLL_INTERVAL)
    while True:
        try:
            await poll_once(bridge)
        except asyncio.CancelledError:
            logger.info("GhostwritrEvents: poll loop cancelled")
            raise
        except Exception as exc:
            logger.warning("GhostwritrEvents: unhandled error in poll loop: %s", exc)
        await asyncio.sleep(_POLL_INTERVAL)
