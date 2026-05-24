"""
wi_workers.py — Work Intelligence Background Workers
=====================================================
Four async worker loops that keep the Work Intelligence layer continuously
updated without any user action.

Workers:
  1. email_triage_sweep      — every 15 min: pull unread emails, triage,
                               ingest signals + contacts into CatalystDB
  2. calendar_sync           — every 30 min: check upcoming events,
                               generate pre-meeting preps for events < 60 min out
  3. daily_briefing          — once per day at a configured hour: pull signals,
                               run briefing generation, persist ONE Recommendation
  4. commitment_monitor      — every 6 hours: monitor open commitments vs recent
                               signals, update statuses in DB

All workers:
  - Are async coroutines suitable for asyncio.create_task()
  - Use asyncio.to_thread() for sync DB / AI calls
  - Degrade gracefully when data sources are unavailable
  - Log clearly at INFO for normal operation, WARNING for errors
  - Broadcast SSE events via the hub when they complete a meaningful cycle
  - Are individually enable/disable-able via env vars

Env vars:
  WI_WORKERS_ENABLED           1 / 0  (master switch, default 1)
  WI_EMAIL_SWEEP_ENABLED       1 / 0  (default 1)
  WI_CALENDAR_SYNC_ENABLED     1 / 0  (default 1)
  WI_DAILY_BRIEFING_ENABLED    1 / 0  (default 1)
  WI_COMMITMENT_MONITOR_ENABLED 1/0   (default 1)
  WI_EMAIL_SWEEP_INTERVAL      seconds (default 900  = 15 min)
  WI_CALENDAR_SYNC_INTERVAL    seconds (default 1800 = 30 min)
  WI_COMMITMENT_MONITOR_INTERVAL seconds (default 21600 = 6 h)
  WI_BRIEFING_HOUR             0-23  local hour to generate daily brief (default 7)
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Any, Callable, Awaitable

log = logging.getLogger("jarvis.wi_workers")

# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def _flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in {"0", "false", "no", "off"}

def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)) or str(default))
    except (ValueError, TypeError):
        return default

# Master / per-worker switches
_MASTER_ENABLED              = _flag("WI_WORKERS_ENABLED", "1")
_EMAIL_SWEEP_ENABLED         = _flag("WI_EMAIL_SWEEP_ENABLED", "1")
_CALENDAR_SYNC_ENABLED       = _flag("WI_CALENDAR_SYNC_ENABLED", "1")
_DAILY_BRIEFING_ENABLED      = _flag("WI_DAILY_BRIEFING_ENABLED", "1")
_COMMITMENT_MONITOR_ENABLED  = _flag("WI_COMMITMENT_MONITOR_ENABLED", "1")

# Intervals
_EMAIL_SWEEP_INTERVAL        = _int("WI_EMAIL_SWEEP_INTERVAL",        900)
_CALENDAR_SYNC_INTERVAL      = _int("WI_CALENDAR_SYNC_INTERVAL",      1800)
_COMMITMENT_MONITOR_INTERVAL = _int("WI_COMMITMENT_MONITOR_INTERVAL", 21600)
_BRIEFING_HOUR               = _int("WI_BRIEFING_HOUR",               7)

# Initial startup delay so workers don't all fire simultaneously at boot
_STARTUP_DELAY_SECONDS       = _int("WI_STARTUP_DELAY", 30)

# ---------------------------------------------------------------------------
# Type alias for broadcast callable
# ---------------------------------------------------------------------------
BroadcastFn = Callable[[str, dict[str, Any]], Awaitable[None]] | None


# ---------------------------------------------------------------------------
# WORKER 1 — Email Triage Sweep
# ---------------------------------------------------------------------------

async def email_triage_sweep(runtime: Any, broadcast: BroadcastFn = None) -> None:
    """
    Periodically pull unread Gmail emails via the runtime's google_workspace,
    run the email_triage workflow, and ingest results into CatalystDB.

    Tracks processed message_ids in CatalystDB raw_emails to avoid re-triaging.
    """
    log.info("WI:email_sweep starting (interval=%ds)", _EMAIL_SWEEP_INTERVAL)
    await asyncio.sleep(_STARTUP_DELAY_SECONDS)

    while True:
        try:
            await _run_email_sweep(runtime, broadcast)
        except asyncio.CancelledError:
            log.info("WI:email_sweep cancelled")
            return
        except Exception as exc:
            log.warning("WI:email_sweep unhandled error: %s", exc)
        await asyncio.sleep(_EMAIL_SWEEP_INTERVAL)


async def _run_email_sweep(runtime: Any, broadcast: BroadcastFn) -> None:
    from .catalyst_db import get_catalyst_db
    from .work_intelligence import get_work_intelligence

    db = get_catalyst_db()
    engine = get_work_intelligence()

    if not db.is_available():
        log.debug("WI:email_sweep: DB not available, skipping")
        return

    # Pull unread emails from Google Workspace
    emails: list[dict] = []
    try:
        workspace_summary = await asyncio.to_thread(runtime.google_workspace_summary)
        for account_entry in workspace_summary.get("accounts", []):
            for msg in account_entry.get("emails", []):
                emails.append(msg)
    except Exception as exc:
        log.debug("WI:email_sweep: could not fetch Google emails: %s", exc)

    if not emails:
        log.debug("WI:email_sweep: no emails to process this cycle")
        return

    new_count = 0
    triaged_count = 0

    for msg in emails:
        message_id = str(msg.get("message_id") or msg.get("id") or "")
        if not message_id:
            continue

        # Skip if already in DB
        existing = db._q1(
            "SELECT id FROM raw_emails WHERE message_id = %s", (message_id,)
        )
        if existing:
            continue

        new_count += 1
        subject    = str(msg.get("subject") or "(no subject)")
        sender     = str(msg.get("from") or msg.get("sender") or "")
        snippet    = str(msg.get("snippet") or msg.get("body") or "")
        received   = str(msg.get("date") or msg.get("received_at") or "")

        # Run triage
        triage = await asyncio.to_thread(engine.email_triage, subject, snippet, sender)
        if not triage:
            continue
        triaged_count += 1

        # Ingest into CatalystDB
        await asyncio.to_thread(
            db.ingest_email_signal,
            "chris",
            message_id,
            subject,
            sender,
            snippet,
            received_at=received or None,
        )

        # Upsert contact
        if sender:
            await asyncio.to_thread(
                db.upsert_contact,
                "chris",
                sender,
            )

        # If high importance — create a signal for downstream workflows
        if triage.get("importance") == "high" or triage.get("requiresAction"):
            await asyncio.to_thread(
                db.ingest_signal,
                "chris",
                "email",
                f"Subject: {subject}\nFrom: {sender}\n\n{snippet[:600]}",
                external_id=message_id,
                source_metadata={
                    "importance": triage.get("importance"),
                    "score": triage.get("score"),
                    "actions": triage.get("actions", []),
                },
                criticality="CRITICAL" if triage.get("importance") == "high" else "STANDARD",
            )

    if triaged_count > 0:
        log.info("WI:email_sweep: processed %d new emails (%d triaged)", new_count, triaged_count)
        if broadcast:
            await broadcast("wi.email_sweep.completed", {
                "new_emails": new_count,
                "triaged": triaged_count,
                "timestamp": datetime.datetime.now().isoformat(),
            })
    else:
        log.debug("WI:email_sweep: no new emails this cycle")


# ---------------------------------------------------------------------------
# WORKER 2 — Calendar Sync
# ---------------------------------------------------------------------------

async def calendar_sync(runtime: Any, broadcast: BroadcastFn = None) -> None:
    """
    Periodically pull upcoming calendar events. For any event starting within
    60 minutes that hasn't been prepped yet, run pre_meeting_prep and persist
    the brief as a raw signal in CatalystDB.
    """
    log.info("WI:calendar_sync starting (interval=%ds)", _CALENDAR_SYNC_INTERVAL)
    await asyncio.sleep(_STARTUP_DELAY_SECONDS + 10)  # slight offset from email sweep

    while True:
        try:
            await _run_calendar_sync(runtime, broadcast)
        except asyncio.CancelledError:
            log.info("WI:calendar_sync cancelled")
            return
        except Exception as exc:
            log.warning("WI:calendar_sync unhandled error: %s", exc)
        await asyncio.sleep(_CALENDAR_SYNC_INTERVAL)


async def _run_calendar_sync(runtime: Any, broadcast: BroadcastFn) -> None:
    from .catalyst_db import get_catalyst_db
    from .work_intelligence import get_work_intelligence

    db = get_catalyst_db()
    engine = get_work_intelligence()

    if not db.is_available():
        return

    # Pull upcoming events
    events: list[dict] = []
    try:
        events = await asyncio.to_thread(runtime.merged_calendar_events, 15)
    except Exception as exc:
        log.debug("WI:calendar_sync: could not fetch events: %s", exc)
        return

    if not events:
        log.debug("WI:calendar_sync: no upcoming events this cycle")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    prepped_count = 0

    for event in events:
        title = str(event.get("summary") or event.get("title") or "Meeting")
        start_str = str(event.get("start") or "")
        if not start_str:
            continue

        # Parse start time
        try:
            # Handle both ISO datetime and date-only formats
            if "T" in start_str:
                start_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            else:
                start_date = datetime.date.fromisoformat(start_str[:10])
                start_dt = datetime.datetime.combine(
                    start_date, datetime.time(9, 0),
                    tzinfo=datetime.timezone.utc
                )
        except (ValueError, TypeError):
            continue

        # Only prep for events starting in the next 60 minutes
        minutes_until = (start_dt - now).total_seconds() / 60
        if not (0 <= minutes_until <= 60):
            continue

        # Check if we've already prepped this event (external_id = title+date)
        event_key = f"meeting-prep::{title[:80]}::{start_str[:10]}"
        already_prepped = db._q1(
            "SELECT id FROM raw_signals WHERE external_id = %s AND user_id = %s",
            (event_key, "chris"),
        )
        if already_prepped:
            continue

        # Pull context: open commitments + recent signals as text
        commitments = await asyncio.to_thread(db.list_open_commitments, "chris")
        commit_texts = [c.get("description", "") for c in commitments[:5]]

        recent_signals = await asyncio.to_thread(db.get_recent_signals, "chris", 10)
        signal_texts = [s.get("content", "")[:200] for s in recent_signals]

        # Run pre-meeting prep
        prep = await asyncio.to_thread(
            engine.pre_meeting_prep, title, commit_texts, signal_texts
        )
        if not prep:
            continue

        # Build a concise brief text
        brief_points = prep.get("briefPoints", [])
        watch_points = prep.get("watchPoints", [])
        agenda       = prep.get("suggestedAgenda", [])

        brief_text = f"PRE-MEETING BRIEF: {title}\n"
        brief_text += f"Starting in ~{int(minutes_until)} minutes\n\n"
        if brief_points:
            brief_text += "Key context:\n" + "\n".join(f"- {b}" for b in brief_points) + "\n\n"
        if watch_points:
            brief_text += "Watch for:\n" + "\n".join(f"- {w}" for w in watch_points) + "\n\n"
        if agenda:
            brief_text += "Suggested agenda:\n" + "\n".join(f"- {a}" for a in agenda)

        # Persist as signal with CRITICAL criticality so it surfaces immediately
        await asyncio.to_thread(
            db.ingest_signal,
            "chris",
            "calendar_event",
            brief_text.strip(),
            external_id=event_key,
            source_metadata={
                "event_title": title,
                "start": start_str,
                "minutes_until": int(minutes_until),
                "brief_points": brief_points,
                "watch_points": watch_points,
                "suggested_agenda": agenda,
            },
            criticality="CRITICAL",
        )
        prepped_count += 1
        log.info("WI:calendar_sync: prepped '%s' (T-%d min)", title, int(minutes_until))

    if prepped_count > 0 and broadcast:
        await broadcast("wi.meeting_prep.ready", {
            "prepped_count": prepped_count,
            "timestamp": datetime.datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# WORKER 3 — Daily Briefing
# ---------------------------------------------------------------------------

async def daily_briefing(runtime: Any, broadcast: BroadcastFn = None) -> None:
    """
    Once per day at WI_BRIEFING_HOUR (default 7am), pull the last 48h of signals,
    run briefing generation, and persist the ONE Recommendation to briefing_items.

    Checks every 5 minutes but only acts once per calendar day.
    """
    log.info("WI:daily_briefing starting (target hour=%d)", _BRIEFING_HOUR)
    await asyncio.sleep(_STARTUP_DELAY_SECONDS + 20)

    last_generated_date: str | None = None

    while True:
        try:
            today = datetime.date.today().isoformat()
            now_hour = datetime.datetime.now().hour

            if today != last_generated_date and now_hour >= _BRIEFING_HOUR:
                generated = await _run_daily_briefing(runtime, broadcast)
                if generated:
                    last_generated_date = today
        except asyncio.CancelledError:
            log.info("WI:daily_briefing cancelled")
            return
        except Exception as exc:
            log.warning("WI:daily_briefing unhandled error: %s", exc)

        await asyncio.sleep(300)  # check every 5 minutes


async def _run_daily_briefing(runtime: Any, broadcast: BroadcastFn) -> bool:
    """Generate and persist the ONE Recommendation. Returns True if successful."""
    from .catalyst_db import get_catalyst_db
    from .work_intelligence import get_work_intelligence

    db = get_catalyst_db()
    engine = get_work_intelligence()

    if not db.is_available():
        return False

    today = datetime.date.today().isoformat()

    # Check if already generated today
    existing = db.get_briefing_items("chris", today)
    if any(item.get("source_type") == "wi_daily_briefing" for item in existing):
        log.debug("WI:daily_briefing: already generated for %s", today)
        return False

    # Pull the last 48h of signals
    recent_signals_raw = await asyncio.to_thread(db.get_recent_signals, "chris", 50)
    signals = [
        {
            "id": s["id"],
            "type": s["signal_type"],
            "content": s["content"],
            "dueDate": None,
        }
        for s in recent_signals_raw
    ]

    # Pull commitment counts
    open_commits = await asyncio.to_thread(db.list_open_commitments, "chris")
    overdue = [c for c in open_commits if c.get("status") == "overdue"]

    # Try to enrich with live calendar events from runtime
    try:
        events = await asyncio.to_thread(runtime.merged_calendar_events, 8)
        for event in events:
            title = str(event.get("summary") or "(untitled)")
            start = str(event.get("start", ""))
            signals.insert(0, {
                "id": f"cal::{title[:40]}",
                "type": "calendar_event",
                "content": f"Upcoming: {title} at {start}",
                "dueDate": start or None,
            })
    except Exception:
        pass

    if not signals:
        log.debug("WI:daily_briefing: no signals available for %s, deferring", today)
        return False

    # Run briefing generation
    briefing = await asyncio.to_thread(
        engine.briefing_generation,
        signals,
        len(open_commits),
        len(overdue),
    )
    if not briefing:
        return False

    recommendation = str(briefing.get("recommendation", "")).strip()
    reasoning      = str(briefing.get("reasoning", "")).strip()
    confidence     = float(briefing.get("confidence", 0.5))
    action_items   = briefing.get("actionItems", [])

    if not recommendation:
        return False

    # Persist as briefing item
    full_text = recommendation
    if action_items:
        full_text += "\n\nSuggested actions:\n" + "\n".join(f"- {a}" for a in action_items)

    await asyncio.to_thread(
        db.save_briefing_item,
        "chris",
        full_text,
        today,
        source_type="wi_daily_briefing",
        confidence=confidence,
        reasoning_chain=reasoning,
    )

    log.info(
        "WI:daily_briefing: generated for %s (confidence=%.2f): %s",
        today, confidence, recommendation[:80],
    )

    if broadcast:
        await broadcast("wi.daily_briefing.ready", {
            "date": today,
            "recommendation": recommendation,
            "confidence": confidence,
            "action_items": action_items,
        })

    return True


# ---------------------------------------------------------------------------
# WORKER 4 — Commitment Monitor
# ---------------------------------------------------------------------------

async def commitment_monitor(runtime: Any, broadcast: BroadcastFn = None) -> None:
    """
    Every 6 hours: pull all open commitments, run the commitment-tracking
    workflow, and update statuses in CatalystDB.

    Surfaces at_risk and overdue commitments in the log and via SSE.
    """
    log.info("WI:commitment_monitor starting (interval=%ds)", _COMMITMENT_MONITOR_INTERVAL)
    await asyncio.sleep(_STARTUP_DELAY_SECONDS + 45)  # largest offset to spread startup load

    while True:
        try:
            await _run_commitment_monitor(runtime, broadcast)
        except asyncio.CancelledError:
            log.info("WI:commitment_monitor cancelled")
            return
        except Exception as exc:
            log.warning("WI:commitment_monitor unhandled error: %s", exc)
        await asyncio.sleep(_COMMITMENT_MONITOR_INTERVAL)


async def _run_commitment_monitor(runtime: Any, broadcast: BroadcastFn) -> None:
    from .catalyst_db import get_catalyst_db
    from .work_intelligence import get_work_intelligence

    db = get_catalyst_db()
    engine = get_work_intelligence()

    if not db.is_available():
        return

    # Pull open commitments
    commitments = await asyncio.to_thread(db.list_open_commitments, "chris")
    if not commitments:
        log.debug("WI:commitment_monitor: no open commitments, skipping")
        return

    # Build recent signals context
    recent_signals_raw = await asyncio.to_thread(db.get_recent_signals, "chris", 20)
    recent_signal_texts = [
        s.get("content", "")[:200] for s in recent_signals_raw
    ]

    # Run commitment tracking (parallel per commitment)
    results = await asyncio.to_thread(
        engine.commitment_tracking, commitments, recent_signal_texts
    )
    if not results:
        return

    updated = 0
    alerts: list[dict] = []

    for result in results:
        commitment_id = str(result.get("commitmentId", ""))
        new_status    = str(result.get("status", "on_track"))
        confidence    = float(result.get("confidence", 0.5))

        if not commitment_id:
            continue

        # Find the original commitment
        original = next((c for c in commitments if c.get("id") == commitment_id), None)
        old_status = str((original or {}).get("status", "open")) if original else "open"

        # Map workflow status back to DB status
        db_status_map = {
            "on_track":  "open",
            "at_risk":   "open",
            "overdue":   "overdue",
            "completed": "completed",
        }
        db_status = db_status_map.get(new_status, "open")

        # Only write back if status changed or newly overdue
        if db_status != old_status or new_status in ("at_risk", "overdue"):
            await asyncio.to_thread(db.update_commitment_status, commitment_id, db_status)
            updated += 1

        # Surface high-urgency alerts
        if new_status in ("at_risk", "overdue"):
            desc = str((original or {}).get("description", ""))[:120] if original else ""
            alerts.append({
                "commitment_id": commitment_id,
                "description":   desc,
                "status":        new_status,
                "confidence":    confidence,
                "suggested_action": result.get("suggestedAction"),
                "evidence":       result.get("evidence", ""),
            })
            log.info(
                "WI:commitment_monitor: %s commitment — %s (conf=%.2f)",
                new_status, desc[:60], confidence,
            )

    if updated > 0 or alerts:
        log.info(
            "WI:commitment_monitor: cycle complete — %d updated, %d alerts",
            updated, len(alerts),
        )
        if broadcast:
            await broadcast("wi.commitments.updated", {
                "updated":   updated,
                "alerts":    alerts,
                "total":     len(commitments),
                "timestamp": datetime.datetime.now().isoformat(),
            })


# ---------------------------------------------------------------------------
# Public API — start all workers
# ---------------------------------------------------------------------------

def should_run() -> bool:
    return _MASTER_ENABLED


async def start_all_workers(
    runtime: Any,
    broadcast: BroadcastFn = None,
) -> list[asyncio.Task]:
    """
    Create and return asyncio Tasks for all enabled workers.
    Call from the FastAPI startup event.

    Example:
        _wi_tasks = await wi_workers.start_all_workers(runtime, _broadcast)
    """
    if not _MASTER_ENABLED:
        log.info("WI workers disabled (WI_WORKERS_ENABLED=0)")
        return []

    tasks: list[asyncio.Task] = []

    if _EMAIL_SWEEP_ENABLED:
        tasks.append(
            asyncio.create_task(
                email_triage_sweep(runtime, broadcast),
                name="wi-email-sweep",
            )
        )
        log.info("WI: email_triage_sweep task started")

    if _CALENDAR_SYNC_ENABLED:
        tasks.append(
            asyncio.create_task(
                calendar_sync(runtime, broadcast),
                name="wi-calendar-sync",
            )
        )
        log.info("WI: calendar_sync task started")

    if _DAILY_BRIEFING_ENABLED:
        tasks.append(
            asyncio.create_task(
                daily_briefing(runtime, broadcast),
                name="wi-daily-briefing",
            )
        )
        log.info("WI: daily_briefing task started")

    if _COMMITMENT_MONITOR_ENABLED:
        tasks.append(
            asyncio.create_task(
                commitment_monitor(runtime, broadcast),
                name="wi-commitment-monitor",
            )
        )
        log.info("WI: commitment_monitor task started")

    log.info("WI workers: %d tasks started", len(tasks))
    return tasks


async def stop_all_workers(tasks: list[asyncio.Task]) -> None:
    """Cancel all worker tasks gracefully. Call from FastAPI shutdown event."""
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    log.info("WI workers: all %d tasks stopped", len(tasks))
