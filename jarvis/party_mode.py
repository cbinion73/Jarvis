from __future__ import annotations

"""
JARVIS Party Mode — Overnight Research Orchestrator
Agents work all night building fully-formed dossiers.
No cost (Ollama + free web search).
Every morning: Chris wakes up to fully-researched investment memos.
"""

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.party_mode")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _time_label() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


# ---------------------------------------------------------------------------
# PartySession dataclass
# ---------------------------------------------------------------------------

@dataclass
class PartySession:
    session_id: str
    started_at: str
    ended_at: str = ""
    status: str = "running"             # "running" | "completed" | "idle"
    dossiers_built: list[str] = field(default_factory=list)   # work_ids
    dossiers_attempted: int = 0
    items_dreamed: int = 0
    items_researched: int = 0
    agent_log: list[str] = field(default_factory=list)
    triggered_by: str = "schedule"     # "schedule" | "manual"


# ---------------------------------------------------------------------------
# PartyModeController
# ---------------------------------------------------------------------------

OVERNIGHT_START_HOUR = 22   # 10 PM
OVERNIGHT_END_HOUR   = 6    # 6 AM
MAX_DOSSIERS_PER_SESSION = 8
DREAM_BATCH_SIZE = 3


class PartyModeController:
    """
    Orchestrates overnight deep-research sessions.
    Agents dream new ideas, then build fully-formed dossiers.
    """

    def __init__(self, runtime: Any = None) -> None:
        self.runtime = runtime
        self._session: PartySession | None = None
        self._stop_flag = False
        self._lock = threading.Lock()
        self._sessions_path = Path.home() / ".jarvis" / "party_sessions.jsonl"
        self._sessions_path.parent.mkdir(parents=True, exist_ok=True)
        self._manual_trigger = False

    # ------------------------------------------------------------------
    # Time window
    # ------------------------------------------------------------------

    def is_overnight_window(self) -> bool:
        hour = datetime.now().hour
        return hour >= OVERNIGHT_START_HOUR or hour < OVERNIGHT_END_HOUR

    def should_run(self) -> bool:
        return self._manual_trigger or self.is_overnight_window()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            if self._session is None:
                return {"status": "idle", "dossiers_built": [], "last_log": None}
            s = self._session
            last_log = s.agent_log[-1] if s.agent_log else None
            return {
                "status": s.status,
                "session_id": s.session_id,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "dossiers_built": list(s.dossiers_built),
                "dossiers_attempted": s.dossiers_attempted,
                "items_dreamed": s.items_dreamed,
                "items_researched": s.items_researched,
                "triggered_by": s.triggered_by,
                "last_log": last_log,
                "agent_log": list(s.agent_log[-20:]),  # last 20 entries
            }

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def start(self, manual: bool = False) -> None:
        """Spawn background thread to run a session."""
        with self._lock:
            if self._session and self._session.status == "running":
                logger.info("[party_mode] Session already running — ignoring start()")
                return
            self._manual_trigger = manual
            self._stop_flag = False
            session = PartySession(
                session_id=str(uuid.uuid4()),
                started_at=_now_iso(),
                triggered_by="manual" if manual else "schedule",
            )
            self._session = session

        t = threading.Thread(target=self._run_session, daemon=True)
        t.start()
        logger.info("[party_mode] Session started (manual=%s)", manual)

    def stop(self) -> None:
        """Signal the running session to stop gracefully."""
        self._stop_flag = True
        logger.info("[party_mode] Stop requested")

    # ------------------------------------------------------------------
    # Morning Brief
    # ------------------------------------------------------------------

    def morning_brief(self) -> str:
        with self._lock:
            if self._session is None:
                return "No overnight session ran."
            s = self._session
            n = len(s.dossiers_built)
            if n == 0:
                return "Your agents ran overnight but could not complete any dossiers. Check logs for details."
            parts = [
                f"Tonight your agents built {n} dossier{'s' if n != 1 else ''}. Here's what they found:",
                "",
            ]
            for log_entry in s.agent_log:
                if "Dossier complete" in log_entry or "dossier:" in log_entry.lower():
                    parts.append(f"  • {log_entry}")
            if len(parts) == 2:
                # No specific dossier entries — show last few log lines
                for entry in s.agent_log[-5:]:
                    parts.append(f"  • {entry}")
            return "\n".join(parts)

    # ------------------------------------------------------------------
    # Internal session runner
    # ------------------------------------------------------------------

    def _run_session(self) -> None:
        with self._lock:
            session = self._session

        def _log(msg: str) -> None:
            entry = f"{_time_label()} — {msg}"
            with self._lock:
                session.agent_log.append(entry)
            logger.info("[party_mode] %s", msg)

        _log("Party mode started. Scanning for work...")

        try:
            # ------------------------------------------------------------------
            # Get gateway
            # ------------------------------------------------------------------
            gateway = None
            try:
                from .llm_gateway import get_gateway
                gateway = get_gateway()
                if gateway is None:
                    _log("WARNING: Ollama gateway is None — dossier building will produce empty sections")
                else:
                    _log("Gateway connected")
            except Exception as gw_exc:
                _log(f"Gateway import failed: {gw_exc}")

            # ------------------------------------------------------------------
            # Dream phase: generate new ideas if fewer than 3 today
            # ------------------------------------------------------------------
            try:
                import json as _json_dream
                from .agent_work import get_work_store, STATUS_DREAMED
                pi_store = get_work_store("catalyst-personal")
                todays_dreams = pi_store.get_todays_dreams()
                pi_today = [d for d in todays_dreams if d.domain == "passive-income"]
                _log(f"Dream phase: {len(pi_today)} passive-income items created today")

                if len(pi_today) < DREAM_BATCH_SIZE and gateway is not None:
                    needed = DREAM_BATCH_SIZE - len(pi_today)
                    dream_prompt = (
                        "You are Mantis, JARVIS's Catalyst agent for Chris Binion. "
                        "Chris wants autonomous agents to dream up, research, propose, "
                        "and (once approved) implement passive income streams. "
                        f"Dream up exactly {needed} fresh, realistic passive income ideas "
                        "that Chris could realistically pursue as a software developer / entrepreneur. "
                        "Focus on digital products, content, licensing, or small automated services. "
                        "Return a JSON array of objects: "
                        '[{"title": "...", "idea": "1-3 sentence explanation of the opportunity, '
                        'why it fits Chris, rough effort/return estimate"}]'
                    )
                    try:
                        raw_ideas = gateway.simple_complete(dream_prompt, max_tokens=600, task_type="converse")
                        raw_ideas = raw_ideas.strip()
                        if raw_ideas.startswith("```"):
                            lines_raw = raw_ideas.split("\n")
                            raw_ideas = "\n".join(
                                lines_raw[1:-1] if lines_raw[-1].strip() == "```" else lines_raw[1:]
                            )
                        start_i = raw_ideas.find("[")
                        end_i = raw_ideas.rfind("]") + 1
                        if start_i >= 0 and end_i > start_i:
                            idea_list = _json_dream.loads(raw_ideas[start_i:end_i])
                            for idea_obj in idea_list[:needed]:
                                idea_title = idea_obj.get("title", "Unnamed idea").strip()
                                idea_text = idea_obj.get("idea", "").strip()
                                if not idea_title:
                                    continue
                                wi = pi_store.dream_idea(
                                    title=idea_title,
                                    idea=idea_text,
                                    domain="passive-income",
                                )
                                with self._lock:
                                    session.items_dreamed += 1
                                _log(f"Dreamed: {idea_title}")
                    except Exception as dream_exc:
                        _log(f"Dream generation failed: {dream_exc}")
                else:
                    _log("Sufficient ideas exist or no gateway — skipping dream phase")
            except Exception as dream_phase_exc:
                _log(f"Dream phase error: {dream_phase_exc}")

            if self._stop_flag:
                _log("Stop requested — aborting before dossier phase")
                self._finalize_session(session)
                return

            # ------------------------------------------------------------------
            # Dossier phase: build dossiers for undocumented work items
            # ------------------------------------------------------------------
            try:
                from .agent_work import get_work_store, get_all_stores
                from .dossier import get_dossier_store, DossierBuilder

                dossier_store = get_dossier_store()
                all_stores = get_all_stores()

                # Collect work items that need dossiers
                candidates = []
                for store in all_stores.values():
                    for item in store.all_items():
                        if item.status not in ("dreamed", "researching", "proposed"):
                            continue
                        # Check if already has a dossier
                        existing = dossier_store.get_by_work_id(item.work_id)
                        if existing is not None:
                            continue
                        candidates.append((store, item))

                _log(f"Dossier phase: {len(candidates)} work items need dossiers")

                builder = DossierBuilder(gateway)

                for store, work_item in candidates:
                    if self._stop_flag:
                        _log("Stop requested — ending dossier phase")
                        break
                    with self._lock:
                        if len(session.dossiers_built) >= MAX_DOSSIERS_PER_SESSION:
                            _log(f"Reached max dossiers per session ({MAX_DOSSIERS_PER_SESSION}) — stopping")
                            break

                    with self._lock:
                        session.dossiers_attempted += 1

                    _log(f"Building dossier: {work_item.title}")
                    try:
                        dossier = builder.build(work_item, session_id=session.session_id)
                        dossier_store.save(dossier)

                        # Advance work item to PROPOSED if still dreamed/researching
                        if work_item.status in ("dreamed", "researching"):
                            try:
                                if work_item.status == "dreamed":
                                    store.advance_to_research(
                                        work_item.work_id,
                                        research_notes="Auto-researched by party mode overnight session.",
                                    )
                                store.submit_proposal(
                                    work_item.work_id,
                                    proposal_text=dossier.executive_summary or "Dossier ready for review.",
                                )
                            except Exception as adv_exc:
                                logger.debug("[party_mode] Could not advance work item: %s", adv_exc)

                        with self._lock:
                            session.dossiers_built.append(work_item.work_id)
                            session.items_researched += 1

                        low = dossier.revenue_estimate_low
                        high = dossier.revenue_estimate_high
                        conf = dossier.confidence_score
                        rev_str = f"${low:,}–${high:,}/mo" if (low or high) else "TBD"
                        _log(
                            f"Dossier complete: {work_item.title} | "
                            f"Revenue: {rev_str} | "
                            f"Confidence: {conf:.1f}/10"
                        )
                    except Exception as build_exc:
                        _log(f"Failed to build dossier for '{work_item.title}': {build_exc}")

            except Exception as dossier_phase_exc:
                _log(f"Dossier phase error: {dossier_phase_exc}")

        except Exception as session_exc:
            logger.exception("[party_mode] Session error: %s", session_exc)
            with self._lock:
                session.agent_log.append(f"{_time_label()} — Session error: {session_exc}")

        self._finalize_session(session)

    def _finalize_session(self, session: PartySession) -> None:
        with self._lock:
            session.status = "completed"
            session.ended_at = _now_iso()
            n = len(session.dossiers_built)
            session.agent_log.append(
                f"{_time_label()} — Party mode complete. "
                f"{n} dossier{'s' if n != 1 else ''} built, "
                f"{session.items_dreamed} ideas dreamed."
            )
            self._manual_trigger = False

        # Persist session
        try:
            self._sessions_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._sessions_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(session)) + "\n")
        except OSError as exc:
            logger.warning("[party_mode] Could not save session: %s", exc)

        logger.info(
            "[party_mode] Session finalized — %d dossiers built, %d dreamed",
            len(session.dossiers_built),
            session.items_dreamed,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_controller: PartyModeController | None = None
_controller_lock = threading.Lock()


def get_party_controller(runtime: Any = None) -> PartyModeController:
    global _controller
    with _controller_lock:
        if _controller is None:
            _controller = PartyModeController(runtime)
    return _controller
