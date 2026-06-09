from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import mimetypes
import os
import re
import secrets
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from .runtime import JarvisRuntime
from .settings import LocationSettingsStore, VoiceSettingsStore
from .voice_audio import generate_tts_audio
from .voice_ui import render_voice_shell
from . import dining as dining_module

try:
    from .jarvis_theme_nexus import render_nexus_shell as _render_nexus_shell
    _NEXUS_THEME_AVAILABLE = True
except Exception:  # pragma: no cover
    _NEXUS_THEME_AVAILABLE = False

    def _render_nexus_shell(runtime, initial_packet=""):  # type: ignore[misc]
        return render_voice_shell(runtime, initial_packet=initial_packet)

try:
    from .jarvis_theme_glass import render_glass_shell as _render_glass_shell
    _GLASS_THEME_AVAILABLE = True
except Exception:  # pragma: no cover
    _GLASS_THEME_AVAILABLE = False

    def _render_glass_shell(runtime, initial_packet=""):  # type: ignore[misc]
        return render_voice_shell(runtime, initial_packet=initial_packet)
from .apple_api import _build_apple_calendar_state, _register_apple_api
from .audit import ActivityReviewStore, AuditLog, ProgressFocusStore, ProgressSnapshotStore, RecoveryActionStore, SeamTrackerStore
from .chronicle_reviews import ChronicleReviewStore
from .health_checkins import HealthCheckInStore
from . import layout_engine as _layout_engine
from .publish_history import PublishHistoryStore
from .recovery_cases import RecoveryCaseStore
from .persistence import atomic_write_json

try:
    from .voice_pipeline import get_friday, get_pipeline, get_time_aware_greeting, init_voice as _init_voice_pipeline, VOICE_TOOL_ALLOWLIST
    _VOICE_PIPELINE_AVAILABLE = True
except Exception:  # pragma: no cover
    _VOICE_PIPELINE_AVAILABLE = False
    VOICE_TOOL_ALLOWLIST: list = []  # type: ignore[assignment]

    def get_pipeline():  # type: ignore[misc]
        return None

    def get_friday():  # type: ignore[misc]
        return None

    def _init_voice_pipeline(config):  # type: ignore[misc]
        return None

    def get_time_aware_greeting(name: str = "boss") -> str:  # type: ignore[misc]
        return f"Good day, {name}."
from .render_pages import (
    render_approval_module_page,
    render_activity_module_page,
    render_agent_ops_module_page,
    render_agent_hierarchy_page,
    render_agent_workspace_page,
    render_catalyst_workspace_page,
    render_chronicle_module_page,
    render_daily_brief_module_page,
    render_dining_module_page,
    render_health_module_page,
    render_huddle_module_page,
    render_mission_board_module_page,
    render_navigation_module_page,
    render_progress_module_page,
    render_publish_module_page,
    render_recovery_module_page,
    render_settings_module_page,
    render_supervision_module_page,
)
try:
    from .approval_queue_surface import build_approval_queue_snapshot, render_approval_queue_html
    _APPROVAL_QUEUE_SURFACE_AVAILABLE = True
except Exception:  # pragma: no cover
    _APPROVAL_QUEUE_SURFACE_AVAILABLE = False

    def build_approval_queue_snapshot(*, approvals_root=None, history_limit=12):  # type: ignore[misc]
        return {
            "generated_at": "",
            "pending_count": 0,
            "history_count": 0,
            "pending": [],
            "history": [],
            "what_needs_me": [],
            "proof_paths": {},
            "error": "approval queue surface unavailable",
        }

    def render_approval_queue_html(snapshot):  # type: ignore[misc]
        return "<html><body><h1>Approval queue surface unavailable.</h1></body></html>"
try:
    from .supervision_snapshot import build_supervision_snapshot, render_supervision_snapshot_html
    _SUPERVISION_SNAPSHOT_AVAILABLE = True
except Exception:  # pragma: no cover
    _SUPERVISION_SNAPSHOT_AVAILABLE = False

    def build_supervision_snapshot(*, memory_root=None, approvals_root=None, config=None, integration_statuses=None):  # type: ignore[misc]
        return {
            "generated_at": "",
            "lane": {"branch": "", "head": "", "dirty_count": 0, "recent_commits": [], "dirty_sample": []},
            "return_brief": {"summary": "supervision snapshot unavailable", "what_needs_me_count": 0},
            "attention_queue": [],
            "memory": {"entry_count": 0, "proposal_count": 0, "fact_count": 0, "latest_entry_titles": []},
            "registry": {"agent_count": 0, "domains": [], "authority_stages": []},
            "integrations": [],
            "what_needs_me": [],
            "proof_paths": {},
            "error": "supervision snapshot unavailable",
        }

    def render_supervision_snapshot_html(snapshot):  # type: ignore[misc]
        return "<html><body><h1>Supervision snapshot unavailable.</h1></body></html>"
try:
    from .command_center_index import DEFAULT_AUDIT_ROOT, build_command_center_index, render_command_center_index_html
    _COMMAND_CENTER_INDEX_AVAILABLE = True
except Exception:  # pragma: no cover
    _COMMAND_CENTER_INDEX_AVAILABLE = False
    DEFAULT_AUDIT_ROOT = Path.cwd() / "data" / "logs"

    def build_command_center_index():  # type: ignore[misc]
        return {
            "generated_at": "",
            "branch": "",
            "head": "",
            "what_needs_me": [],
            "surface_count": 0,
            "surfaces": [],
            "json_endpoints": [],
            "proof_paths": {},
            "error": "command center index unavailable",
        }

    def render_command_center_index_html(payload):  # type: ignore[misc]
        return "<html><body><h1>Command center index unavailable.</h1></body></html>"

try:
    from .scheduler import get_scheduler, get_briefing_builder
    _SCHEDULER_AVAILABLE = True
except Exception:  # pragma: no cover
    _SCHEDULER_AVAILABLE = False

    def get_scheduler():  # type: ignore[misc]
        return None

    def get_briefing_builder():  # type: ignore[misc]
        return None

try:
    from .publishing_suite import (
        get_publishing as _get_publishing,
        PublishingProject,
        RevenueStream,
        SocialPost,
        ContentCalendarItem,
    )
    _PUBLISHING_AVAILABLE = True
except Exception:  # pragma: no cover
    _PUBLISHING_AVAILABLE = False

    def _get_publishing():  # type: ignore[misc]
        return None

try:
    from .social_engine import get_social_engine as _get_social_engine
    _SOCIAL_ENGINE_AVAILABLE = True
except Exception:  # pragma: no cover
    _SOCIAL_ENGINE_AVAILABLE = False

    def _get_social_engine():  # type: ignore[misc]
        return None

try:
    from .chronicle_bridge import (
        get_chronicle_bridge as _get_chronicle_bridge,
        get_disciple as _get_disciple,
    )
    _CHRONICLE_BRIDGE_AVAILABLE = True
except Exception:  # pragma: no cover
    _CHRONICLE_BRIDGE_AVAILABLE = False

    def _get_chronicle_bridge():  # type: ignore[misc]
        return None

    def _get_disciple():  # type: ignore[misc]
        return None

try:
    from .approvals import get_approval_guard, get_approval_queue
    _APPROVALS_AVAILABLE = True
except Exception:  # pragma: no cover
    _APPROVALS_AVAILABLE = False

    def get_approval_guard():  # type: ignore[misc]
        return None

    def get_approval_queue():  # type: ignore[misc]
        return None

try:
    from .family_profiles import (
        get_family_manager as _get_family_manager,
        get_child_handler as _get_child_handler,
        get_mockingbird as _get_mockingbird,
    )
    _FAMILY_PROFILES_AVAILABLE = True
except Exception:  # pragma: no cover
    _FAMILY_PROFILES_AVAILABLE = False

try:
    from .llm_gateway import get_gateway as _get_gateway
    _LLM_GATEWAY_AVAILABLE = True
except Exception:  # pragma: no cover
    _LLM_GATEWAY_AVAILABLE = False

    def _get_gateway():  # type: ignore[misc]
        return None

    def _get_family_manager():  # type: ignore[misc]
        return None

    def _get_child_handler():  # type: ignore[misc]
        return None

try:
    from .ghostwritr_bridge import (
        get_ghostwritr_bridge as _get_ghostwritr_bridge,
        init_ghostwritr_bridge as _init_ghostwritr_bridge,
    )
    _GHOSTWRITR_AVAILABLE = True
except Exception:  # pragma: no cover
    _GHOSTWRITR_AVAILABLE = False

    def _get_ghostwritr_bridge():  # type: ignore[misc]
        return None

    def _init_ghostwritr_bridge(config=None):  # type: ignore[misc]
        return None, None

    def _get_mockingbird():  # type: ignore[misc]
        return None


# ── Home Intelligence ─────────────────────────────────────────────────────────
try:
    from .home_projects import get_home_db as _get_home_db
    from .unified_inbox import get_unified_inbox as _get_unified_inbox
    from .signal_router import get_signal_router as _get_signal_router
    _HOME_INTELLIGENCE_AVAILABLE = True
except Exception:  # pragma: no cover
    _HOME_INTELLIGENCE_AVAILABLE = False

    def _get_home_db():  # type: ignore[misc]
        return None

    def _get_unified_inbox():  # type: ignore[misc]
        return None

    def _get_signal_router():  # type: ignore[misc]
        return None


class EventHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections)
        stale: list[WebSocket] = []
        for websocket in sockets:
            try:
                await asyncio.wait_for(websocket.send_json(payload), timeout=0.5)
            except Exception:
                stale.append(websocket)
        if stale:
            async with self._lock:
                for websocket in stale:
                    self._connections.discard(websocket)


def build_app(runtime: JarvisRuntime) -> FastAPI:
    voice_settings = VoiceSettingsStore(runtime.config)
    location_settings = LocationSettingsStore(runtime.config)
    hub = EventHub()
    app = FastAPI(title="JARVIS Service", version="2.0")
    shell_warmer_task: asyncio.Task | None = None
    # Initialise Epic 7 voice pipeline (non-fatal if unavailable)
    if _VOICE_PIPELINE_AVAILABLE:
        try:
            _init_voice_pipeline(runtime.config)
        except Exception as _vp_exc:  # pragma: no cover
            import logging as _logging
            _logging.getLogger("jarvis.service").warning(
                "Could not initialise voice pipeline: %s", _vp_exc
            )
    assets_root = Path.cwd() / "assets"
    if assets_root.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_root)), name="assets")
    uploads_root = Path.cwd() / "data" / "chat_uploads"
    uploads_root.mkdir(parents=True, exist_ok=True)

    def _safe_chat_filename(name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "").strip()).strip("-._")
        return cleaned[:120] or "attachment"

    def _upload_excerpt(path: Path, content_type: str, suffix: str) -> str:
        text_types = {
            ".txt",
            ".md",
            ".markdown",
            ".json",
            ".csv",
            ".tsv",
            ".yaml",
            ".yml",
            ".py",
            ".js",
            ".ts",
            ".html",
            ".css",
            ".xml",
        }
        looks_text = suffix.lower() in text_types or content_type.startswith("text/")
        if not looks_text:
            return ""
        try:
            data = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""
        normalized = "\n".join(line.rstrip() for line in data.splitlines())
        return normalized[:4000].strip()

    def _upload_prompt_fragment(attachments: list[dict[str, Any]]) -> str:
        if not attachments:
            return ""
        lines = [
            "Attached files were included with this message.",
            "Use any excerpts below as additional context.",
        ]
        for item in attachments:
            name = str(item.get("filename", "")).strip() or "Attachment"
            content_type = str(item.get("content_type", "")).strip() or "application/octet-stream"
            size = int(item.get("size_bytes", 0) or 0)
            lines.append(f"- {name} ({content_type}, {size} bytes)")
            excerpt = str(item.get("excerpt", "")).strip()
            if excerpt:
                lines.append(f"  Excerpt: {excerpt[:1500]}")
            else:
                lines.append("  Excerpt: No text preview extracted yet.")
        return "\n".join(lines).strip()

    def _base_url(request: Request) -> str:
        return str(request.base_url).rstrip("/")

    async def _broadcast_dashboard(event_name: str, *, include_dashboard: bool = True) -> None:
        payload: dict[str, Any] = {
            "type": event_name,
            "refresh": True,
            "shell_state": runtime.shell_state_snapshot(),
        }
        if include_dashboard:
            payload["dashboard"] = runtime.dashboard_snapshot()
        await hub.broadcast(payload)

    def _json(payload: Any, status_code: int = 200) -> JSONResponse:
        return JSONResponse(
            payload,
            status_code=status_code,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    async def _shell_state_warmer() -> None:
        startup_delay = max(1, int(os.getenv("JARVIS_SHELL_WARM_STARTUP_DELAY_SECONDS", "2") or 2))
        interval_seconds = max(15, int(os.getenv("JARVIS_SHELL_WARM_INTERVAL_SECONDS", "20") or 20))
        actors = runtime.shell_state_actor_names()
        await asyncio.sleep(startup_delay)
        while True:
            try:
                await asyncio.to_thread(
                    runtime.prewarm_shell_state,
                    actors,
                    include_today_board=False,
                    include_dashboard=False,
                )
                await asyncio.to_thread(runtime.prewarm_proactive_state, actors)
            except Exception:
                pass
            await asyncio.sleep(interval_seconds)

    @app.on_event("startup")
    async def _start_mcp_server() -> None:
        """Start FastMCP on its own port (8788) to avoid lifespan/ASGI mount conflicts."""
        import logging as _mcp_log
        _log = _mcp_log.getLogger("jarvis.service")
        try:
            from .mcp_server import mcp as _mcp_server
            import uvicorn as _uvi
            mcp_port = int(os.getenv("JARVIS_MCP_PORT", "8788"))
            _mcp_app = _mcp_server.http_app(path="/", transport="streamable-http")
            _mcp_config = _uvi.Config(_mcp_app, host="127.0.0.1", port=mcp_port, log_level="warning")
            _mcp_srv = _uvi.Server(_mcp_config)
            asyncio.create_task(_mcp_srv.serve(), name="jarvis-mcp-server")
            _log.info("MCP server started at http://127.0.0.1:%d (streamable-http)", mcp_port)
        except Exception as _mcp_exc:
            _log.warning("MCP server unavailable: %s", _mcp_exc)

    @app.on_event("startup")
    async def _start_shell_state_warmer() -> None:
        nonlocal shell_warmer_task
        enabled = str(os.getenv("JARVIS_SHELL_WARMING_ENABLED", "0")).strip().lower() not in {"0", "false", "no", "off"}
        if not enabled or shell_warmer_task is not None:
            return
        shell_warmer_task = asyncio.create_task(_shell_state_warmer(), name="jarvis-shell-state-warmer")

    @app.on_event("shutdown")
    async def _stop_shell_state_warmer() -> None:
        nonlocal shell_warmer_task
        if shell_warmer_task is None:
            return
        shell_warmer_task.cancel()
        with suppress(asyncio.CancelledError):
            await shell_warmer_task
        shell_warmer_task = None

    @app.on_event("shutdown")
    async def _close_browser_on_shutdown() -> None:
        try:
            from .browser_search import _close_browser
            await asyncio.to_thread(_close_browser)
        except Exception:
            pass

    @app.on_event("shutdown")
    async def _stop_party_on_shutdown() -> None:
        try:
            from .party_mode import get_party_controller
            get_party_controller(runtime).stop()
        except Exception:
            pass

    def _summary_payload() -> dict[str, Any]:
        return {
            "household": runtime.household.household_name,
            "location": runtime.household.location_label,
            "users": [u.display_name for u in runtime.household.users.values()],
            "modes": runtime.household.modes,
        }

    def _response_payload(result: Any) -> dict[str, Any]:
        return {"provider": result.provider, "model": result.model, "output_text": result.output_text}

    def _mode_brief_payload(actor: str, room: str, request_text: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if path == "/api/plan":
            plan = runtime.plan_request(actor, room, request_text)
            return {
                "request_id": plan.request_id,
                "actor": plan.actor,
                "room": plan.room,
                "mode": plan.mode,
                "module": plan.module,
                "model": plan.model,
                "allowed": plan.allowed,
                "approval_required": plan.needs_approval,
                "second_factor_required": plan.second_factor_required,
                "action_class": plan.action_class.name,
                "task_class": plan.task_class.value,
                "preferred_provider": plan.preferred_provider,
                "context_lane": plan.context_lane,
                "routing_tier": plan.routing_tier.value,
                "privacy_level": plan.privacy_level.value,
                "risk_level": plan.risk_level.value,
                "rationale": plan.rationale,
            }
        if path == "/api/mode-brief":
            return runtime.family_mode_brief(str(payload.get("mode", "")))
        if path == "/api/family-plan":
            return {"actor": actor, "output_text": runtime.family_plan(actor, request_text)}
        if path == "/api/departure-plan":
            return runtime.departure_plan(actor, str(payload.get("context", "")))
        if path == "/api/rebekah-center":
            return {"actor": "Rebekah", "output_text": runtime.rebekah_command_center(request_text)}
        if path == "/api/troop-plan":
            return {"actor": actor, "output_text": runtime.troop_plan(actor, request_text)}
        if path == "/api/grocery-support":
            return {"actor": actor, "output_text": runtime.grocery_support(actor, request_text)}
        if path == "/api/meal-plan":
            return runtime.meal_plan(actor, request_text)
        if path == "/api/vehicle-plan":
            return runtime.vehicle_plan(actor, request_text)
        if path == "/api/weather-contingency":
            return runtime.weather_contingency(actor, request_text)
        return _response_payload(runtime.respond(actor, room, request_text))

    def _communications_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path == "/api/message-draft":
            return runtime.draft_message(
                actor,
                str(payload["audience"]),
                str(payload["purpose"]),
                str(payload["context"]),
                str(payload.get("tone", "warm")),
            )
        if path == "/api/parent-message":
            return runtime.stage_parent_message(
                actor,
                str(payload["audience"]),
                str(payload["purpose"]),
                str(payload["context"]),
                str(payload.get("tone", "warm")),
            )
        if path == "/api/voice-note":
            return runtime.capture_voice_note(
                actor,
                str(payload.get("source", "van")),
                str(payload.get("note", "")),
            )
        raise HTTPException(status_code=404, detail="Unknown communications route")

    def _home_ops_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path == "/api/room-scene":
            return runtime.room_scene(
                actor,
                str(payload.get("room", "")),
                str(payload.get("scene", "")),
                intent=str(payload.get("intent", "")),
            )
        if path == "/api/climate-control":
            return runtime.climate_control(
                actor,
                str(payload.get("zone", "")),
                str(payload.get("mode", "heat_cool")),
                target_temperature=payload.get("target_temp"),
                context=str(payload.get("context", "")),
            )
        if path == "/api/access-control":
            return runtime.access_control(
                actor,
                str(payload.get("target", "")),
                str(payload.get("state", "")),
            )
        if path == "/api/garage-check":
            return runtime.garage_safe_close(actor, str(payload.get("target", "")))
        if path == "/api/energy-window":
            return runtime.energy_window(
                str(payload.get("appliance", "")),
                str(payload.get("request", "")),
            )
        if path == "/api/mic-ingress":
            return runtime.microphone_ingress(
                str(payload.get("microphone", payload.get("device", ""))),
                str(payload.get("transcript", payload.get("request", ""))),
                wake_word_detected=bool(payload.get("wake_word_detected", False)),
                actor_hint=str(payload.get("actor_hint", actor)),
            )
        if path == "/api/presence-update":
            return runtime.presence_update(
                str(payload.get("sensor", payload.get("source", ""))),
                str(payload.get("room", payload.get("location", ""))),
                bool(payload.get("occupied", True)),
                detail=str(payload.get("detail", payload.get("note", ""))),
            )
        if path == "/api/phone-presence":
            return runtime.phone_presence_update(
                actor,
                str(payload.get("device", payload.get("owner", "phone"))),
                str(payload.get("state", payload.get("status", "home"))),
                zone=str(payload.get("zone", payload.get("location", ""))),
                detail=str(payload.get("detail", payload.get("note", ""))),
            )
        if path == "/api/camera-event":
            return runtime.camera_event(
                str(payload.get("camera", "")),
                str(payload.get("location", "")),
                str(payload.get("event_type", "")),
                confidence=str(payload.get("confidence", "medium")),
                detail=str(payload.get("detail", "")),
            )
        if path == "/api/package-rule":
            return runtime.package_rule(
                str(payload.get("zone", "")),
                str(payload.get("preferred_drop", "")),
                bool(payload.get("rain_sensitive", False)),
                note=str(payload.get("note", "")),
            )
        if path == "/api/object-recognition":
            return runtime.object_recognition(
                str(payload.get("source", "")),
                str(payload.get("room", "")),
                str(payload.get("object", "")),
                detail=str(payload.get("detail", "")),
                confidence=str(payload.get("confidence", "medium")),
            )
        if path == "/api/environmental-anomaly":
            return runtime.environmental_anomaly(
                str(payload.get("category", "")),
                str(payload.get("source", "")),
                str(payload.get("reading", "")),
                str(payload.get("baseline", "")),
                severity=str(payload.get("severity", "watch")),
                detail=str(payload.get("detail", "")),
            )
        if path == "/api/privacy-update":
            return runtime.update_privacy_state(
                str(payload.get("kind", "")),
                str(payload.get("target", "")),
                enabled=payload.get("enabled"),
                muted=payload.get("muted"),
            )
        raise HTTPException(status_code=404, detail="Unknown home operations route")

    def _memory_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path == "/api/memory-remember":
            raw_tags = payload.get("tags", [])
            if isinstance(raw_tags, str):
                tags = [item.strip() for item in raw_tags.split(",") if item.strip()]
            elif isinstance(raw_tags, Sequence) and not isinstance(raw_tags, (str, bytes, bytearray)):
                tags = [str(item).strip() for item in raw_tags if str(item).strip()]
            else:
                tags = []
            return runtime.remember(
                actor,
                str(payload.get("memory_type", payload.get("type", "household"))),
                str(payload.get("scope", "household")),
                str(payload.get("summary", "")),
                str(payload.get("detail", "")),
                owner=str(payload.get("owner", "")),
                project=str(payload.get("project", "")),
                tags=tags,
                sensitivity=str(payload.get("sensitivity", "normal")),
                subject_user_id=str(payload.get("subject_user_id", "")),
                access_policy=str(payload.get("access_policy", "")),
                source_type=str(payload.get("source_type", "user-stated")),
                confidence=str(payload.get("confidence", "confirmed")),
            )
        if path == "/api/memory-forget":
            return runtime.forget_memory(
                str(payload.get("viewer", "Chris")),
                str(payload.get("entry_id", "")),
            )
        if path == "/api/memory-approve":
            return runtime.resolve_memory_proposal(
                str(payload.get("proposal_id", "")),
                str(payload.get("decision", "approved")),
            )
        raise HTTPException(status_code=404, detail="Unknown memory route")

    def _catalyst_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path == "/api/catalyst-signal":
            tags = [item.strip() for item in str(payload.get("tags", "")).split(",") if item.strip()]
            return runtime.catalyst_capture_signal(
                actor,
                str(payload.get("source", "manual")),
                str(payload.get("title", "")),
                str(payload.get("content", "")),
                sender=str(payload.get("sender", "")),
                tags=tags,
                work_id=str(payload.get("work_id", "")),
            )
        if path == "/api/catalyst-email-triage":
            return runtime.catalyst_email_triage(
                actor,
                str(payload.get("subject", "")),
                str(payload.get("body", "")),
                str(payload.get("sender", "")),
            )
        if path == "/api/catalyst-meeting-prep":
            return runtime.catalyst_meeting_prep(
                actor,
                str(payload.get("meeting_title", "")),
                [str(item) for item in payload.get("open_commitments", [])],
                [str(item) for item in payload.get("recent_signals", [])],
            )
        if path == "/api/catalyst-meeting-extract":
            return runtime.catalyst_meeting_extraction(
                actor,
                str(payload.get("transcript", "")),
                str(payload.get("context", "")),
            )
        if path == "/api/catalyst-briefing":
            return runtime.catalyst_briefing(actor, str(payload.get("user_context", "")))
        if path == "/api/catalyst-draft":
            return runtime.catalyst_draft(
                actor,
                str(payload.get("intent", "")),
                str(payload.get("context", "")),
                str(payload.get("recipient", "")),
                str(payload.get("tone", "professional")),
            )
        if path == "/api/catalyst-project-brief":
            return runtime.catalyst_project_brief(
                actor,
                str(payload.get("project_name", "")),
                str(payload.get("problem", "")),
                str(payload.get("desired_outcome", "")),
                str(payload.get("constraints", "")),
                work_id=str(payload.get("work_id", "")),
            )
        if path == "/api/catalyst-implementation-plan":
            return runtime.catalyst_implementation_plan(
                actor,
                str(payload.get("project_name", "")),
                str(payload.get("brief", "")),
                str(payload.get("constraints", "")),
                work_id=str(payload.get("work_id", "")),
            )
        if path == "/api/catalyst-proactive":
            return runtime.catalyst_proactive_surfacing(
                actor,
                str(payload.get("horizon", "today")),
                str(payload.get("context", "")),
            )
        raise HTTPException(status_code=404, detail="Unknown catalyst route")

    def _security_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path == "/api/security-event":
            return runtime.package_or_motion_monitor(
                actor,
                str(payload.get("category", "motion")),
                str(payload.get("location", "")),
                str(payload.get("detail", "")),
                severity=str(payload.get("severity", "watch")),
            )
        if path == "/api/safety-alert":
            return runtime.safety_escalation(
                actor,
                str(payload.get("hazard", "smoke")),
                str(payload.get("source", "")),
                str(payload.get("detail", "")),
                severity=str(payload.get("severity", "critical")),
            )
        if path == "/api/weather-alert":
            return runtime.weather_advisory(actor, str(payload.get("context", "")))
        if path == "/api/child-arrival":
            return runtime.child_arrival(
                actor,
                str(payload.get("location", "front door")),
                str(payload.get("detail", "")),
            )
        if path == "/api/unlock-policy":
            return runtime.unlock_assessment(
                actor,
                str(payload.get("target", "front door")),
                requested_by_voice=bool(payload.get("requested_by_voice", True)),
                second_factor_present=bool(payload.get("second_factor_present", False)),
            )
        raise HTTPException(status_code=404, detail="Unknown security route")

    def _formation_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path == "/api/devotional-pause":
            return {
                "actor": actor,
                "output_text": runtime.devotional_pause(
                    actor,
                    str(payload.get("theme", "")),
                    str(payload.get("mode", "scripture")),
                ),
            }
        if path == "/api/family-devotional":
            return {
                "actor": actor,
                "output_text": runtime.family_devotional_prep(
                    actor,
                    str(payload.get("theme", "")),
                    str(payload.get("context", "")),
                ),
            }
        if path == "/api/chronicle-capture":
            return runtime.chronicle_capture(
                actor,
                str(payload.get("theme", "")),
                str(payload.get("note", "")),
            )
        raise HTTPException(status_code=404, detail="Unknown formation route")

    def _workshop_payload(actor: str, payload: dict[str, Any], path: str, request_text: str) -> dict[str, Any]:
        if path == "/api/workshop-plan":
            return {"actor": actor, "output_text": runtime.workshop_plan(actor, request_text)}
        if path == "/api/concept-studio/chat":
            return runtime.concept_studio_chat(
                actor,
                request_text or str(payload.get("prompt", "")),
                str(payload.get("object_type", "")),
                str(payload.get("goals", "")),
                str(payload.get("constraints", "")),
                session_id=str(payload.get("session_id", "")),
                image_path=str(payload.get("image_path", "")),
                capture_id=str(payload.get("capture_id", "")),
                reference_note=str(payload.get("reference_note", "")),
                silhouette_preference=str(payload.get("silhouette_preference", "")),
                vision_object_label=str(payload.get("vision_object_label", "")),
                vision_contour_confidence=str(payload.get("vision_contour_confidence", "")),
                vision_asymmetry_hint=str(payload.get("vision_asymmetry_hint", "")),
                vision_dimension_seed=str(payload.get("vision_dimension_seed", "")),
            )
        if path == "/api/material-recommendation":
            return runtime.material_recommendation(
                actor,
                str(payload["part"]),
                str(payload["use_case"]),
                str(payload.get("requirements", "")),
            )
        if path == "/api/cad-package":
            return runtime.cad_package_advanced(
                actor,
                str(payload["part"]),
                str(payload.get("dimensions", "")),
                str(payload.get("constraints", "")),
                str(payload.get("family", "")),
                str(payload.get("printer", "")),
                str(payload.get("profile", "")),
                str(payload.get("creative_profile", "")),
            )
        if path == "/api/print-prep":
            return runtime.print_prep(
                actor,
                str(payload["part"]),
                str(payload["printer"]),
                str(payload["material"]),
                str(payload.get("profile", "functional-prototype")),
                str(payload.get("notes", "")),
            )
        if path == "/api/safety-check":
            return runtime.safety_check(
                actor,
                str(payload["operation"]),
                str(payload.get("context", "")),
            )
        if path == "/api/inspect-part":
            return runtime.inspect_part(
                actor,
                str(payload["part"]),
                request_text or "Inspect this part and recommend a prototype path.",
                str(payload.get("observations", "")),
                str(payload.get("goals", "")),
                image_path=str(payload.get("image_path", "")),
            )
        if path == "/api/vendor-prep":
            return runtime.vendor_prep(
                actor,
                str(payload["part"]),
                str(payload["vendor"]),
                str(payload["process"]),
                str(payload["material"]),
                str(payload.get("notes", "")),
            )
        raise HTTPException(status_code=404, detail="Unknown workshop route")

    def _tutoring_payload(actor: str, payload: dict[str, Any], path: str, request_text: str) -> dict[str, Any]:
        if path == "/api/tutor":
            return runtime.tutor(
                actor,
                request_text,
                subject=str(payload.get("subject", "")),
            )
        if path == "/api/device-boundary":
            return runtime.device_boundary_plan(
                actor,
                window_label=str(payload.get("window", "")),
            )
        raise HTTPException(status_code=404, detail="Unknown tutoring route")

    def _executive_payload(actor: str, payload: dict[str, Any], path: str) -> dict[str, Any]:
        if path != "/api/executive-task":
            raise HTTPException(status_code=404, detail="Unknown executive route")
        task = str(payload.get("task", ""))
        if task == "decision-framework":
            return {"actor": actor, "task": task, "output_text": runtime.decision_framework(actor, str(payload.get("primary", "")))}
        if task == "ironclad-editor":
            return {"actor": actor, "task": task, "output_text": runtime.iron_clad_editor(actor, str(payload.get("primary", "")))}
        if task == "venture-brief":
            return {
                "actor": actor,
                "task": task,
                "output_text": runtime.venture_brief(
                    actor,
                    str(payload.get("topic", "venture monitoring")),
                    str(payload.get("secondary", "")) or str(payload.get("primary", "")),
                ),
            }
        raise HTTPException(status_code=400, detail="Unknown executive task")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        service_runtime = runtime.service_runtime_snapshot(include_probe=False)
        guardian = runtime.guardian_status_snapshot()
        openviking_enabled = bool(getattr(runtime.openviking_support, "enabled", False))
        openviking_base_url = str(getattr(runtime.openviking_support, "base_url", "")).strip() if openviking_enabled else ""
        second_brain_enabled = bool(getattr(runtime.config, "second_brain_enabled", False))
        return {
            "ok": True,
            "python": "3.12",
            "service": "fastapi",
            "runtime": {
                "role": service_runtime.get("role", ""),
                "pid": service_runtime.get("pid"),
                "started_at": service_runtime.get("started_at", ""),
                "build_fingerprint": (service_runtime.get("startup_build") or {}).get("fingerprint", ""),
                "disk_fingerprint": (service_runtime.get("current_build") or {}).get("fingerprint", ""),
                "drift": service_runtime.get("drift", {}),
                "guardian": {
                    "active": bool(guardian.get("active")),
                    "generated_at": str((guardian.get("status") or {}).get("generated_at", "")).strip(),
                },
            },
            "openviking": {
                "enabled": openviking_enabled,
                "base_url": openviking_base_url,
                "probe": "skipped",
            },
            "brain_graph": {
                "probe": "skipped",
                "second_brain_enabled": second_brain_enabled,
            },
        }

    @app.get("/", response_class=HTMLResponse)
    async def root(
        request: Request,
        packet: str = Query(default=""),
        theme: str = Query(default=""),
    ) -> str:
        # The main web app should keep the full shell chrome. Default the shell
        # to the Daily Briefing packet instead of sending root traffic to a
        # standalone module page.
        if theme == "nexus" and _NEXUS_THEME_AVAILABLE:
            return _render_nexus_shell(runtime, initial_packet=packet)
        if theme == "glass" and _GLASS_THEME_AVAILABLE:
            return _render_glass_shell(runtime, initial_packet=packet)
        if theme == "voice":
            return render_voice_shell(runtime, initial_packet=packet)
        default_packet = packet or "briefing"
        if _GLASS_THEME_AVAILABLE:
            return _render_glass_shell(runtime, initial_packet=default_packet)
        return render_voice_shell(runtime, initial_packet=default_packet)

    @app.get("/nexus", response_class=HTMLResponse)
    async def nexus_shortcut(packet: str = Query(default="")) -> str:
        """Convenience shortcut — always loads the Nexus theme."""
        if _NEXUS_THEME_AVAILABLE:
            return _render_nexus_shell(runtime, initial_packet=packet)
        return render_voice_shell(runtime, initial_packet=packet)

    @app.get("/glass", response_class=HTMLResponse)
    async def glass_shortcut(packet: str = Query(default="")) -> str:
        """Convenience shortcut — always loads the Glass theme."""
        if _GLASS_THEME_AVAILABLE:
            return _render_glass_shell(runtime, initial_packet=packet)
        return render_voice_shell(runtime, initial_packet=packet)

    @app.get("/storm-dashboard")
    async def storm_dashboard() -> Response:
        storm_path = Path.cwd() / "artifacts" / "mockups" / "storm-weather-widget.html"
        if not storm_path.exists():
            raise HTTPException(status_code=404, detail="Storm dashboard is unavailable.")
        return FileResponse(storm_path, media_type="text/html")

    @app.get("/health-desktop-storyboard")
    async def health_desktop_storyboard() -> Response:
        storyboard_path = Path.cwd() / "artifacts" / "mockups" / "health-desktop-storyboard.html"
        if not storyboard_path.exists():
            raise HTTPException(status_code=404, detail="Health desktop storyboard is unavailable.")
        return FileResponse(storyboard_path, media_type="text/html")

    @app.get("/health-desktop")
    async def health_desktop() -> Response:
        storyboard_path = Path.cwd() / "artifacts" / "mockups" / "health-desktop-storyboard.html"
        if not storyboard_path.exists():
            raise HTTPException(status_code=404, detail="Health desktop is unavailable.")
        return FileResponse(storyboard_path, media_type="text/html")

    @app.get("/health-center", response_class=HTMLResponse)
    async def health_center() -> HTMLResponse:
        return HTMLResponse(render_health_module_page(await _build_health_module_payload()))

    def _render_glass_view_route(view_name: str) -> HTMLResponse:
        html = _render_glass_shell(runtime)
        injection = (
            "<script>(function(){"
            f"window.__JARVIS_START_VIEW = '{view_name}';"
            "})();</script></body>"
        )
        if "</body>" in html:
            html = html.replace("</body>", injection, 1)
        return HTMLResponse(html)

    @app.get("/home-center", response_class=HTMLResponse)
    async def home_center() -> HTMLResponse:
        return _render_glass_view_route("home")

    @app.get("/calendar-center", response_class=HTMLResponse)
    async def calendar_center() -> HTMLResponse:
        return _render_glass_view_route("calendar")

    @app.get("/email-center", response_class=HTMLResponse)
    async def email_center() -> HTMLResponse:
        return _render_glass_view_route("email")

    @app.get("/news-center", response_class=HTMLResponse)
    async def news_center() -> HTMLResponse:
        return _render_glass_view_route("news")

    @app.get("/social-center", response_class=HTMLResponse)
    async def social_center() -> HTMLResponse:
        return _render_glass_view_route("social")

    @app.get("/legacy-center", response_class=HTMLResponse)
    async def legacy_center() -> HTMLResponse:
        return _render_glass_view_route("chronicle")

    @app.get("/faith-center", response_class=HTMLResponse)
    async def faith_center() -> HTMLResponse:
        return _render_glass_view_route("faith")

    @app.get("/agents-center", response_class=HTMLResponse)
    async def agents_center() -> HTMLResponse:
        return _render_glass_view_route("agents")

    @app.get("/agents", response_class=HTMLResponse)
    async def agents_center_alias() -> HTMLResponse:
        return _render_glass_view_route("agents")

    @app.get("/intel-center", response_class=HTMLResponse)
    async def intel_center() -> HTMLResponse:
        return _render_glass_view_route("intelligence")

    @app.get("/forge-center", response_class=HTMLResponse)
    async def forge_center() -> HTMLResponse:
        return _render_glass_view_route("forge")

    @app.get("/forge", response_class=HTMLResponse)
    async def forge_center_alias() -> HTMLResponse:
        return _render_glass_view_route("forge")

    @app.get("/catalyst-center", response_class=HTMLResponse)
    async def catalyst_center() -> HTMLResponse:
        return _render_glass_view_route("catalyst")

    @app.get("/foundry-center", response_class=HTMLResponse)
    async def foundry_center() -> HTMLResponse:
        return _render_glass_view_route("foundry")

    @app.get("/foundry", response_class=HTMLResponse)
    async def foundry_center_alias() -> HTMLResponse:
        return _render_glass_view_route("foundry")

    @app.get("/workshop-center", response_class=HTMLResponse)
    async def workshop_center() -> HTMLResponse:
        return _render_glass_view_route("workshop")

    @app.get("/workshop", response_class=HTMLResponse)
    async def workshop_center_alias() -> HTMLResponse:
        return _render_glass_view_route("workshop")

    @app.get("/vision-center", response_class=HTMLResponse)
    async def vision_center() -> HTMLResponse:
        return _render_glass_view_route("vision")

    @app.get("/vision", response_class=HTMLResponse)
    async def vision_center_alias() -> HTMLResponse:
        return _render_glass_view_route("vision")

    @app.get("/journey-center", response_class=HTMLResponse)
    async def journey_center() -> HTMLResponse:
        return _render_glass_view_route("journey")

    @app.get("/journey", response_class=HTMLResponse)
    async def journey_center_alias() -> HTMLResponse:
        return _render_glass_view_route("journey")

    @app.get("/needs-you-center", response_class=HTMLResponse)
    async def needs_you_center() -> HTMLResponse:
        return _render_glass_view_route("notifications")

    @app.get("/chronicle-center", response_class=HTMLResponse)
    async def chronicle_center() -> HTMLResponse:
        return HTMLResponse(render_chronicle_module_page(await _build_chronicle_module_payload()))

    @app.get("/navigation-center", response_class=HTMLResponse)
    async def navigation_center() -> HTMLResponse:
        return HTMLResponse(render_navigation_module_page(await _build_navigation_module_payload()))

    @app.get("/api/vision/module")
    async def api_vision_module(actor: str = "Chris") -> JSONResponse:
        return _json(await _build_vision_module_payload(actor))

    @app.get("/huddle-center", response_class=HTMLResponse)
    async def huddle_center() -> HTMLResponse:
        return HTMLResponse(render_huddle_module_page(await _build_huddle_module_payload()))

    @app.get("/briefing-center", response_class=HTMLResponse)
    async def briefing_center(actor: str = "Chris") -> HTMLResponse:
        return HTMLResponse(render_daily_brief_module_page(await _build_daily_brief_module_payload(actor)))

    @app.get("/progress-center", response_class=HTMLResponse)
    async def progress_center() -> HTMLResponse:
        return HTMLResponse(render_progress_module_page(await _build_progress_module_payload()))

    @app.get("/recovery-center", response_class=HTMLResponse)
    async def recovery_center() -> HTMLResponse:
        return HTMLResponse(render_recovery_module_page(await _build_recovery_module_payload()))

    @app.get("/mission-board", response_class=HTMLResponse)
    async def mission_board_center() -> HTMLResponse:
        return HTMLResponse(render_mission_board_module_page(await _build_mission_board_module_payload()))

    @app.get("/activity-center", response_class=HTMLResponse)
    async def activity_center() -> HTMLResponse:
        return HTMLResponse(render_activity_module_page(await _build_activity_module_payload()))

    @app.get("/agent-ops-center", response_class=HTMLResponse)
    async def agent_ops_center() -> HTMLResponse:
        return HTMLResponse(render_agent_ops_module_page(await _build_agent_ops_module_payload()))

    @app.get("/settings-center", response_class=HTMLResponse)
    async def settings_center() -> HTMLResponse:
        return HTMLResponse(render_settings_module_page(await _build_settings_module_payload()))

    @app.get("/implementation-outline")
    async def implementation_outline() -> Response:
        outline_path = Path.cwd() / "artifacts" / "mockups" / "jarvis-numbered-outline-checklist.html"
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="Implementation outline is unavailable.")
        return FileResponse(outline_path, media_type="text/html")

    @app.get("/approval-queue", response_class=HTMLResponse)
    async def approval_queue_surface() -> HTMLResponse:
        return HTMLResponse(render_approval_module_page(await _build_approval_module_payload()))

    @app.get("/api/approval-queue/snapshot")
    async def api_approval_queue_snapshot() -> JSONResponse:
        return _json(build_approval_queue_snapshot())

    @app.get("/api/approval/module")
    async def api_approval_module() -> JSONResponse:
        return _json(await _build_approval_module_payload())

    @app.get("/supervision-snapshot", response_class=HTMLResponse)
    async def supervision_snapshot_surface() -> HTMLResponse:
        return HTMLResponse(render_supervision_module_page(await _build_supervision_module_payload()))

    @app.get("/api/supervision-snapshot")
    async def api_supervision_snapshot() -> JSONResponse:
        return _json(build_supervision_snapshot())

    @app.get("/api/supervision/module")
    async def api_supervision_module() -> JSONResponse:
        return _json(await _build_supervision_module_payload())

    @app.post("/api/supervision/reviews/{request_id}/{action}")
    async def api_supervision_review_action(
        request_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> JSONResponse:
        payload = payload or {}
        action_key = str(action or "").strip().lower()
        if action_key not in {"approve", "reject", "cancel", "execute"}:
            raise HTTPException(status_code=400, detail="Unsupported supervision review action.")

        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        title = str(payload.get("title") or request_id).strip() or request_id
        reason = str(payload.get("reason") or payload.get("detail") or "").strip()
        result: dict[str, Any] | None = None

        if action_key == "approve":
            queue = get_approval_queue()
            if queue is not None:
                from dataclasses import asdict as _asdict

                item = queue.approve(request_id, approved_by=actor.lower())
                if item is not None:
                    result = {"status": "approved", "request": _asdict(item)}
            if result is None:
                updated = runtime.approval_store.update_status(request_id, "approved")
                if updated is not None:
                    result = {"status": "approved", "request": updated}
        elif action_key == "reject":
            queue = get_approval_queue()
            if queue is not None and queue.reject(request_id, reason=reason, rejected_by=actor.lower()):
                result = {"status": "rejected", "request_id": request_id, "reason": reason}
            if result is None:
                updated = runtime.approval_store.update_status(request_id, "rejected")
                if updated is not None:
                    result = {"status": "rejected", "request": updated, "reason": reason}
        elif action_key == "cancel":
            queue = get_approval_queue()
            if queue is not None and queue.cancel(request_id):
                result = {"status": "cancelled", "request_id": request_id}
            if result is None:
                updated = runtime.approval_store.update_status(request_id, "cancelled")
                if updated is not None:
                    result = {"status": "cancelled", "request": updated}
        else:
            guard = get_approval_guard()
            if guard is None:
                raise HTTPException(status_code=503, detail="Approval system not initialised")
            execution = guard.execute_approved(request_id)
            if execution.get("status") == "error":
                raise HTTPException(status_code=400, detail=str(execution.get("detail") or "Execution failed"))
            result = {
                "status": "executed",
                "request_id": request_id,
                "result": execution,
                "supervision_decision": dict(execution.get("supervision_decision", {}) or {}),
            }

        if result is None:
            raise HTTPException(status_code=404, detail="Supervision review item not found.")

        status = str(result.get("status") or action_key).strip() or action_key
        detail = (
            f"Supervision {action_key} moved {title} to {status}."
            if action_key != "execute"
            else f"Supervision executed {title} from the dedicated review lane."
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "supervision",
                "action": f"{action_key.capitalize()} Supervision Item",
                "title": title,
                "detail": detail,
                "why_now": reason or "Supervision route resolved a bounded-autonomy review item from the dedicated module surface.",
                "result_summary": f"Supervision action status: {status}",
                "related_route": "/supervision-snapshot",
                "route_label": "Open Supervision Snapshot",
                "related_kind": "supervision-item",
                "related_label": title,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Supervision",
            reason=detail,
            route="/supervision-snapshot",
            actor=actor,
        )
        return _json({"status": status, "request_id": request_id, "focus": focus_entry, "result": result})

    @app.post("/api/supervision/integrations/{integration_name}/recovery")
    async def api_supervision_integration_recovery(
        integration_name: str,
        payload: dict[str, Any] | None = None,
    ) -> JSONResponse:
        payload = payload or {}
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        integration_key = str(integration_name or "").strip()
        if not integration_key:
            raise HTTPException(status_code=400, detail="Integration name is required.")

        snapshot = build_supervision_snapshot()
        target = next(
            (
                dict(item)
                for item in list(snapshot.get("integrations") or [])
                if isinstance(item, dict) and str(item.get("name") or "").strip().lower() == integration_key.lower()
            ),
            None,
        )
        if target is None:
            raise HTTPException(status_code=404, detail="Integration status not found.")

        integration_detail = str(target.get("detail") or "").strip() or "Integration needs supervision recovery."
        case = RecoveryCaseStore().upsert_case(
            source_kind="integration",
            title=f"{integration_key} supervision recovery",
            detail=f"{integration_key} surfaced a failing integration inside Supervision. {integration_detail}",
            related_route="/recovery-center",
            related_key=integration_key,
            metadata={
                "origin_module": "supervision",
                "integration_name": integration_key,
                "integration_ok": bool(target.get("ok")),
                "integration_detail": integration_detail,
            },
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "supervision",
                "action": "Stage Supervision Recovery Case",
                "title": integration_key,
                "detail": f"Supervision promoted {integration_key} into the recovery lane.",
                "why_now": "The Supervision module turned a failing integration into a durable recovery case instead of leaving it as a passive warning.",
                "result_summary": f"Recovery case {str(case.get('status_label') or 'Open')} for {integration_key}.",
                "related_route": "/recovery-center",
                "route_label": "Open Recovery",
                "related_kind": "recovery-case",
                "related_label": str(case.get("case_id") or integration_key).strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Recovery",
            reason=f"Supervision staged a recovery case for {integration_key}.",
            route="/recovery-center",
            actor=actor,
        )
        return _json({"status": "staged", "integration": target, "case": case, "focus": focus_entry})

    @app.get("/command-center", response_class=HTMLResponse)
    async def command_center_index() -> HTMLResponse:
        return HTMLResponse(render_command_center_index_html(build_command_center_index()))

    @app.get("/api/command-center")
    async def api_command_center_index() -> JSONResponse:
        return _json(build_command_center_index())

    @app.get("/storm-assets/{filename}")
    async def storm_asset(filename: str) -> Response:
        assets_root = (Path.cwd() / "artifacts" / "weather-assets").resolve()
        asset_path = (assets_root / filename).resolve()
        if assets_root not in asset_path.parents or not asset_path.exists() or not asset_path.is_file():
            raise HTTPException(status_code=404, detail="Storm asset not found.")
        return FileResponse(asset_path)

    @app.get("/api/storm-weather")
    async def api_storm_weather(force: bool = False) -> JSONResponse:
        return _json(runtime.storm_weather_snapshot(force=force))

    @app.get("/api/storm-route-weather")
    async def api_storm_route_weather(origin: str, destination: str) -> JSONResponse:
        return _json(runtime.storm_route_weather(origin, destination))

    def _module_recent_activity(*, route: str, domain: str, limit: int = 4) -> list[dict[str, Any]]:
        audit = AuditLog(DEFAULT_AUDIT_ROOT)
        rows: list[dict[str, Any]] = []
        scan_limit = max(limit * 8, 24)
        for item in audit.list_recent(limit=scan_limit):
            if not isinstance(item, dict):
                continue
            item_route = str(item.get("related_route") or item.get("route") or "").strip()
            item_domain = str(item.get("domain") or "").strip()
            if route and item_route != route and domain and item_domain != domain:
                continue
            if route and not domain and item_route != route:
                continue
            if domain and not route and item_domain != domain:
                continue
            entry_type = str(item.get("entry_type") or "").strip()
            title = str(item.get("action") or item.get("title") or item.get("detail") or entry_type or "activity").strip()
            if not title:
                title = "activity"
            rows.append(
                {
                    "entry_type": entry_type,
                    "timestamp": str(item.get("timestamp") or ""),
                    "title": title,
                    "subtitle": str(item.get("why_now") or item.get("detail") or item_domain or item.get("actor") or "").strip(),
                    "detail": str(item.get("result_summary") or item.get("detail") or "").strip(),
                    "actor": str(item.get("actor") or "").strip(),
                    "related_kind": str(item.get("related_kind") or "").strip(),
                    "related_label": str(item.get("related_label") or "").strip(),
                    "route_label": str(item.get("route_label") or "").strip(),
                    "route": item_route,
                }
            )
            if len(rows) >= limit:
                break
        return rows

    async def _build_navigation_module_payload() -> dict[str, Any]:
        generated_at = ""
        try:
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()
        except Exception:
            generated_at = ""

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Navigation now has a dedicated module route with persisted route state and live route-preview intelligence.",
            "what_became_real": "Navigation is now represented as a dedicated app module instead of only the shared shell surface.",
            "remains_partial": "Broader travel orchestration and deeper voice-linked guidance still need follow-on slices, but durable route history and route resume continuity are now represented across the app layer.",
            "navigation_state": {},
            "saved_locations": [],
            "route_preview": {"summary": "", "hazard_active": False, "sections": []},
            "route_history": [],
            "recent_activity": [],
            "proof_paths": {
                "module_route": "/navigation-center",
                "module_api": "/api/navigation/module",
                "route_api": "/api/navigation/module/route",
                "state_api": "/api/navigation/module/state",
                "resume_api": "/api/navigation/module/resume",
                "storm_route_api": "/api/storm-route-weather",
            },
            "errors": [],
        }

        try:
            from .apple_api import _load_navigation_state, LOCATION_SETTINGS_PATH
            import json

            payload["navigation_state"] = _load_navigation_state()
            if LOCATION_SETTINGS_PATH.exists():
                raw = json.loads(LOCATION_SETTINGS_PATH.read_text(encoding="utf-8"))
                saved = raw.get("saved_locations") if isinstance(raw, dict) else []
                payload["saved_locations"] = [
                    {
                        "id": str(item.get("id") or ""),
                        "label": str(item.get("label") or ""),
                        "address": str(item.get("address") or ""),
                        "geography": str(item.get("geography") or ""),
                        "latitude": item.get("latitude"),
                        "longitude": item.get("longitude"),
                        "source": str(item.get("source") or ""),
                        "notes": str(item.get("notes") or ""),
                    }
                    for item in saved
                    if isinstance(item, dict)
                ]
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["summary"] = "Navigation center route is live, but saved navigation state did not fully hydrate."
            payload["remains_partial"] = "Live navigation state sources still need repair or population in this runtime."
            payload["errors"].append(f"navigation_state: {exc}")

        state = payload["navigation_state"] if isinstance(payload.get("navigation_state"), dict) else {}
        payload["route_history"] = list(state.get("route_history") or []) if isinstance(state, dict) else []
        origin = str(((state.get("last_route") or {}).get("origin") if isinstance(state.get("last_route"), dict) else "") or "").strip()
        destination = str(((state.get("last_route") or {}).get("destination") if isinstance(state.get("last_route"), dict) else "") or "").strip()
        if origin and destination:
            try:
                preview = await _build_navigation_route_preview(
                    origin=origin,
                    destination=destination,
                    parks_historic_radius_miles=float(state.get("parks_historic_radius_miles") or 25),
                    persist=False,
                )
                payload["route_preview"] = preview
            except Exception as exc:
                payload["errors"].append(f"route_preview: {exc}")

        if payload["status"] == "Useful":
            payload["summary"] = (
                f"Navigation center loaded {len(payload['saved_locations'])} saved location(s), "
                f"{len((state.get('favorite_destinations') or [])) if isinstance(state, dict) else 0} favorite destination(s), "
                f"{len(payload['route_history'])} durable route entr{'y' if len(payload['route_history']) == 1 else 'ies'}, "
                f"and a persisted route preview surface."
            )
        payload["recent_activity"] = _module_recent_activity(route="/navigation-center", domain="navigation")
        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some navigation sources still failed to hydrate; inspect the payload preview for details."
        return payload

    async def _build_navigation_route_preview(
        *,
        origin: str,
        destination: str,
        parks_historic_radius_miles: float,
        persist: bool,
    ) -> dict[str, Any]:
        from .apple_api import _record_navigation_route_history, _NAV_STOP_LABELS, _nav_bridge, _nav_nps_along_route, _nav_route_points, _nav_state_codes
        from .nav_bridge import haversine, sample_route_points

        route_warning = ""
        try:
            route_packet = runtime.storm_route_weather(origin, destination)
        except Exception as exc:
            route_warning = str(exc).strip()
            route_packet = {
                "origin": {"label": origin},
                "destination": {"label": destination},
                "summary": "Route saved, but live route intelligence is temporarily unavailable in this runtime.",
                "hazard_active": False,
                "route": {
                    "distance_miles": None,
                    "duration_minutes": None,
                    "coordinates": [],
                    "steps": [],
                },
            }
        route_info = route_packet.get("route") if isinstance(route_packet, dict) else {}
        route_points = _nav_route_points(route_info if isinstance(route_info, dict) else {})
        total_miles = float(route_info.get("distance_miles") or 0) if isinstance(route_info, dict) else 0.0
        sections: list[dict[str, Any]] = []
        if route_points:
            bridge = _nav_bridge()
            interval = 12.0
            if total_miles > 0 and total_miles < 24:
                interval = max(5.0, total_miles / 3)
            samples = sample_route_points(route_points, interval_miles=interval)
            mile_markers: list[float] = [0.0]
            cumulative = 0.0
            next_threshold = interval
            for idx in range(1, len(route_points)):
                cumulative += haversine(
                    route_points[idx - 1][0], route_points[idx - 1][1],
                    route_points[idx][0], route_points[idx][1],
                )
                if cumulative >= next_threshold:
                    mile_markers.append(round(cumulative, 1))
                    next_threshold += interval
            while len(mile_markers) < len(samples):
                mile_markers.append(round(total_miles, 1))

            categories = ["food", "starbucks", "parks", "historic", "family", "gas"]
            seen_by_category: dict[str, set[str]] = {}
            for category in categories:
                seen_by_category[category] = set()
                radius_m = min(int(parks_historic_radius_miles * 1609.34), 50_000) if category in {"parks", "historic"} else 2400
                items: list[dict[str, Any]] = []
                for sample_idx, (slat, slng) in enumerate(samples):
                    marker = mile_markers[sample_idx] if sample_idx < len(mile_markers) else round(total_miles, 1)
                    for poi in bridge.search_places_near(slat, slng, category, radius_m=radius_m):
                        key = str(poi.get("place_id") or poi.get("name") or "")
                        if not key or key in seen_by_category[category]:
                            continue
                        seen_by_category[category].add(key)
                        items.append(
                            {
                                "name": str(poi.get("name") or ""),
                                "address": str(poi.get("address") or ""),
                                "route_mile_marker": marker,
                                "rating": poi.get("rating"),
                            }
                        )
                if category == "parks":
                    states = _nav_state_codes(
                        str((route_packet.get("origin") or {}).get("label") or ""),
                        str((route_packet.get("destination") or {}).get("label") or ""),
                    )
                    if states:
                        for park in _nav_nps_along_route(bridge, route_points, states, max_distance_miles=parks_historic_radius_miles):
                            key = f"nps:{park.get('name')}"
                            if key in seen_by_category[category]:
                                continue
                            seen_by_category[category].add(key)
                            items.append(
                                {
                                    "name": str(park.get("name") or ""),
                                    "address": str(park.get("address") or ""),
                                    "route_mile_marker": park.get("route_mile_marker"),
                                    "rating": None,
                                }
                            )
                items.sort(key=lambda item: item.get("route_mile_marker") or 0)
                sections.append(
                    {
                        "id": category,
                        "label": _NAV_STOP_LABELS.get(category, category.title()),
                        "items": items[:8],
                    }
                )
        if persist:
            _record_navigation_route_history(
                origin=origin,
                destination=destination,
                origin_mode="home",
                saved_location_id="",
                parks_historic_radius_miles=int(parks_historic_radius_miles),
                source_label="Navigation module route preview",
            )
        return {
            "origin": origin,
            "destination": destination,
            "summary": str(route_packet.get("summary") or ""),
            "hazard_active": bool(route_packet.get("hazard_active")),
            "route": route_packet.get("route") if isinstance(route_packet, dict) else {},
            "sections": sections,
            "warning": route_warning,
        }

    async def _build_vision_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        actor_name = str(actor_name or "Chris").strip() or "Chris"
        availability_notes: list[str] = []
        if hasattr(runtime, "vision_state_snapshot"):
            state_snapshot = await asyncio.to_thread(runtime.vision_state_snapshot, actor_name)
        else:
            state_snapshot = {
                "actor": actor_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "calibration": {},
                "recent_observations": [],
                "recent_captures": [],
                "summary": {
                    "observation_count": 0,
                    "capture_count": 0,
                    "has_calibration": False,
                    "confidence": "low",
                },
            }
            availability_notes.append("Vision runtime snapshot is not fully available in this environment.")
        if hasattr(runtime, "perception_overview"):
            perception_overview = await asyncio.to_thread(runtime.perception_overview)
        else:
            perception_overview = {}
            availability_notes.append("Perception overview is not available in this runtime.")
        if hasattr(runtime, "privacy_state"):
            privacy_state = await asyncio.to_thread(runtime.privacy_state)
        else:
            privacy_state = {}
            availability_notes.append("Vision privacy state is not available in this runtime.")

        observations = list(state_snapshot.get("recent_observations") or [])
        captures = list(state_snapshot.get("recent_captures") or [])
        camera_events = list(perception_overview.get("camera_events") or [])
        object_events = list(perception_overview.get("object_events") or [])
        anomalies = list(perception_overview.get("anomalies") or [])
        workshop_objects = list(perception_overview.get("workshop_objects") or [])
        presence_events = list(perception_overview.get("presence_events") or [])
        phone_presence = list(perception_overview.get("phone_presence") or [])
        package_rules = list(perception_overview.get("package_rules") or [])
        microphone_events = list(perception_overview.get("microphone_events") or [])
        summary = dict(state_snapshot.get("summary") or {})
        generated_at = str(state_snapshot.get("generated_at") or "")
        confidence = str(summary.get("confidence") or "low").strip() or "low"
        lead_scene = observations[0] if observations else captures[0] if captures else camera_events[0] if camera_events else {}
        lead_camera_label = str(
            lead_scene.get("camera_label")
            or lead_scene.get("camera")
            or lead_scene.get("source")
            or "Desk Camera"
        ).strip() or "Desk Camera"
        lead_camera_target = str(
            lead_scene.get("camera_id")
            or lead_scene.get("source_id")
            or lead_scene.get("camera")
            or lead_camera_label
        ).strip() or lead_camera_label
        privacy_cameras = dict(privacy_state.get("cameras") or {})
        lead_camera_state = dict(privacy_cameras.get(lead_camera_target) or privacy_cameras.get(lead_camera_label) or {})
        camera_enabled = bool(lead_camera_state.get("enabled", True))
        if bool(privacy_state.get("physicalMuteRequired")):
            camera_enabled = False

        if not bool(summary.get("has_calibration")):
            availability_notes.append("Vision calibration has not been saved yet, so measurements and confidence remain partial.")
        if not observations and not captures:
            availability_notes.append("No recent actor-scoped vision captures or observations are available yet.")
        if not camera_events:
            availability_notes.append("No recent camera events were surfaced by the perception overview.")
        if bool(privacy_state.get("physicalMuteRequired")):
            availability_notes.append("Vision privacy posture is currently bounded by a physical mute or similar privacy requirement.")

        runtime_note = "Vision is live and connected."
        if availability_notes:
            runtime_note = availability_notes[0]

        return {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful" if (observations or captures or camera_events or object_events) else "Wired",
            "summary": (
                f"Vision loaded {len(observations)} observation(s), {len(captures)} capture(s), "
                f"and {len(camera_events) + len(object_events)} recent perception event(s) into a dedicated desktop module."
            ),
            "what_became_real": "Vision now has a dedicated live module contract for the glass desktop instead of shell-side composition from older raw endpoints.",
            "remains_partial": "Real camera/upload capture tooling and richer multimodal interpretation still depend on live upstream signals, but the desktop now renders honest continuity, privacy posture, calibration posture, and route-ready visual context from shared runtime state.",
            "runtime_note": runtime_note,
            "availability_notes": availability_notes[:8],
            "state_snapshot": state_snapshot,
            "perception_overview": perception_overview,
            "privacy_state": privacy_state,
            "scene_overview": {
                "lead_scene": lead_scene,
                "recent_scenes": list((observations[:4] + captures[:4]))[:6],
                "lead_camera_label": lead_camera_label,
                "lead_camera_target": lead_camera_target,
                "camera_enabled": camera_enabled,
            },
            "quick_actions": [
                {
                    "kind": "privacy-toggle",
                    "label": "Resume Vision" if not camera_enabled else "Pause Vision",
                    "detail": f"{'Re-enable' if not camera_enabled else 'Temporarily pause'} {lead_camera_label} through the live privacy boundary.",
                    "kind_target": "camera",
                    "target": lead_camera_target,
                    "enabled": not camera_enabled,
                },
                {
                    "kind": "route",
                    "label": "Open Activity Feed",
                    "detail": "Review the recent continuity created from visual observations and captures.",
                    "route": "/activity-center",
                    "fallback_view": "journey",
                },
                {
                    "kind": "route",
                    "label": "Open Chronicle",
                    "detail": "Inspect the memory lane connected to saved visual captures.",
                    "route": "/chronicle-center",
                    "fallback_view": "chronicle",
                },
                {
                    "kind": "route",
                    "label": "Open Workshop",
                    "detail": "Route workshop-relevant visual signals into the maker lane.",
                    "route": "/workshop",
                    "fallback_view": "workshop",
                },
            ],
            "counts": {
                "observations": len(observations),
                "captures": len(captures),
                "camera_events": len(camera_events),
                "object_events": len(object_events),
                "anomalies": len(anomalies),
                "workshop_objects": len(workshop_objects),
                "presence_events": len(presence_events),
                "phone_presence": len(phone_presence),
                "package_rules": len(package_rules),
                "microphone_events": len(microphone_events),
            },
            "proof_paths": {
                "module_api": "/api/vision/module",
                "vision_state_api": "/api/vision-state",
                "perception_api": "/api/perception-overview",
                "privacy_state_api": "/api/privacy-state",
                "privacy_update_api": "/api/privacy-update",
                "vision_analyze_api": "/api/vision/analyze",
                "vision_calibration_api": "/api/vision/calibration",
                "vision_measure_api": "/api/vision/measure",
                "activity_api": "/api/activity/operator-action",
            },
            "confidence": confidence,
        }

    @app.get("/api/navigation/module")
    async def api_navigation_module() -> JSONResponse:
        return _json(await _build_navigation_module_payload())

    @app.post("/api/navigation/module/route")
    async def api_navigation_module_route(payload: dict[str, Any]) -> JSONResponse:
        origin = str(payload.get("origin") or "").strip()
        destination = str(payload.get("destination") or "").strip()
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="origin and destination are required")
        radius = max(5.0, min(float(payload.get("parks_historic_radius_miles") or 25), 100.0))
        return _json(
            await _build_navigation_route_preview(
                origin=origin,
                destination=destination,
                parks_historic_radius_miles=radius,
                persist=True,
            )
        )

    @app.post("/api/navigation/module/state")
    async def api_navigation_module_state(payload: dict[str, Any]) -> JSONResponse:
        from .apple_api import _save_navigation_state

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be an object")
        return _json(_save_navigation_state(payload))

    @app.post("/api/navigation/module/resume")
    async def api_navigation_module_resume(payload: dict[str, Any]) -> JSONResponse:
        from .apple_api import _resume_navigation_route_history

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be an object")
        route_id = str(payload.get("route_id") or "").strip()
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        if not route_id:
            raise HTTPException(status_code=400, detail="route_id is required")
        try:
            resumed = _resume_navigation_route_history(
                route_id=route_id,
                actor=actor,
                source_label="Navigation module resume",
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        route_entry = dict(resumed.get("route") or {})
        preview = await _build_navigation_route_preview(
            origin=str(route_entry.get("origin") or "").strip(),
            destination=str(route_entry.get("destination") or "").strip(),
            parks_historic_radius_miles=float((resumed.get("state") or {}).get("parks_historic_radius_miles") or 25),
            persist=False,
        )
        return _json(
            {
                "status": "resumed",
                "route": route_entry,
                "focus": resumed.get("focus") or {},
                "navigation_state": resumed.get("state") or {},
                "route_preview": preview,
            }
        )

    @app.get("/agents/hierarchy", response_class=HTMLResponse)
    async def agent_hierarchy() -> str:
        return render_agent_hierarchy_page(runtime)

    @app.get("/agents/workspace/{agent_id}", response_class=HTMLResponse)
    async def agent_workspace(agent_id: str) -> str:
        return render_agent_workspace_page(runtime, agent_id)

    @app.get("/catalyst/view/{page}", response_class=HTMLResponse)
    async def catalyst_view(page: str) -> str:
        return render_catalyst_workspace_page(runtime, page)

    @app.get("/dining-center", response_class=HTMLResponse)
    async def dining_module_surface(
        query: str = "",
        cuisine: str = "japanese",
        open_now: bool = False,
        prefs: str = "",
        quick_filter: str = "best",
    ) -> HTMLResponse:
        payload = await _build_dining_module_payload(
            query=query,
            cuisine=cuisine,
            open_now=open_now,
            prefs=_dining_parse_prefs(prefs),
            quick_filter=quick_filter,
        )
        return HTMLResponse(render_dining_module_page(payload))

    @app.get("/publish", response_class=HTMLResponse)
    async def publish_module_surface() -> HTMLResponse:
        return HTMLResponse(render_publish_module_page(_build_publish_module_payload()))

    @app.get("/accounts/{account_id}/connect")
    async def account_connect(account_id: str, request: Request) -> Response:
        connect = runtime.account_connect_url(account_id, _base_url(request))
        if not connect.get("ok"):
            return HTMLResponse(
                f"<html><body><h1>Account connection unavailable</h1><p>{connect.get('detail', 'Unable to start provider login.')}</p></body></html>",
                status_code=200,
            )
        return RedirectResponse(str(connect["authorization_url"]), status_code=302)

    @app.get("/google/connect", response_class=HTMLResponse)
    async def google_connect_root() -> str:
        return (
            "<html><body><h1>Account required</h1>"
            "<p>Select a specific account in Settings first. JARVIS keeps personal accounts separated by user.</p>"
            "</body></html>"
        )

    @app.get("/google/callback", response_class=HTMLResponse)
    async def google_callback(request: Request, code: str = "", state: str = "") -> str:
        result = runtime.google_handle_callback(_base_url(request), code, state)
        title = "Google connected" if result.get("ok") else "Google connection failed"
        return f"<html><body><h1>{title}</h1><p>{result.get('detail', 'Unknown Google callback state.')}</p></body></html>"

    @app.get("/auth/microsoft/callback", response_class=HTMLResponse)
    async def microsoft_callback(code: str = "", state: str = "") -> str:
        result = runtime.microsoft_handle_callback(code, state)
        title = "Microsoft connected" if result.get("ok") else "Microsoft connection failed"
        return f"<html><body><h1>{title}</h1><p>{result.get('detail', 'Unknown Microsoft callback state.')}</p></body></html>"

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        try:
            shell_state = await asyncio.to_thread(runtime.shell_state_snapshot)
            await websocket.send_json({"type": "hello", "shell_state": shell_state})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await hub.disconnect(websocket)
        except Exception:
            await hub.disconnect(websocket)

    @app.get("/api/dashboard")
    async def api_dashboard(request: Request, actor: str = "Chris", device_id: str = "") -> JSONResponse:
        current_host = request.headers.get("host", "") if device_id else ""
        current_origin = str(request.base_url).rstrip("/") if device_id else ""
        return _json(
            await asyncio.to_thread(
                runtime.dashboard_snapshot,
                actor,
                device_id=device_id,
                current_host=current_host,
                current_origin=current_origin,
            )
        )

    @app.get("/api/mission-control")
    async def api_mission_control(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.mission_control_snapshot, actor))

    @app.get("/api/missions")
    async def api_missions(actor: str = "Chris", include_completed: bool = True, limit: int = 20) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.mission_list_snapshot, actor, include_completed=include_completed, limit=limit))

    @app.post("/api/missions")
    async def api_create_mission(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        request_text = str(payload.get("request", "")).strip()
        room = str(payload.get("room", "office")).strip() or "office"
        if not request_text:
            raise HTTPException(status_code=400, detail="Mission request is required.")
        return _json(await asyncio.to_thread(runtime.create_mission, actor, request_text, room), status_code=201)

    @app.get("/api/missions/{mission_id}")
    async def api_mission(mission_id: str) -> JSONResponse:
        snapshot = await asyncio.to_thread(runtime.mission_snapshot, mission_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Mission not found.")
        return _json(snapshot)

    @app.post("/api/missions/{mission_id}/status")
    async def api_update_mission_status(mission_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.update_mission_status,
                mission_id,
                str(payload.get("status", "")).strip(),
                note=str(payload.get("note", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(updated)

    @app.post("/api/missions/{mission_id}/edit")
    async def api_update_mission_details(mission_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.update_mission_details,
                mission_id,
                title=str(payload.get("title", "")).strip(),
                brief=str(payload.get("brief", "")).strip(),
                request=str(payload.get("request", "")).strip(),
                next_step=str(payload.get("next_step", "")).strip(),
                note=str(payload.get("note", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(updated)

    @app.get("/api/missions/{mission_id}/approvals")
    async def api_mission_approvals(mission_id: str) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.mission_approvals, mission_id))

    @app.get("/api/missions/{mission_id}/outputs")
    async def api_mission_outputs(mission_id: str) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.mission_outputs, mission_id))

    @app.get("/api/missions/{mission_id}/agents")
    async def api_mission_agents(mission_id: str) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.mission_agents, mission_id))

    @app.get("/api/missions/{mission_id}/work-state")
    async def api_mission_work_state(mission_id: str) -> JSONResponse:
        try:
            snapshot = await asyncio.to_thread(runtime.mission_work_state_snapshot, mission_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(snapshot)

    @app.post("/api/missions/{mission_id}/agents/{agent_id}/work-state")
    async def api_update_agent_work_state(mission_id: str, agent_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.update_agent_work_state,
                mission_id,
                agent_id,
                status=str(payload.get("status", "")).strip(),
                current_focus=str(payload.get("current_focus", "")).strip(),
                ownership_mode=str(payload.get("ownership_mode", "")).strip(),
                note=str(payload.get("note", "")).strip(),
                decision=str(payload.get("decision", "")).strip(),
                rationale=str(payload.get("rationale", "")).strip(),
                hypothesis=str(payload.get("hypothesis", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(updated)

    @app.post("/api/missions/{mission_id}/handoffs")
    async def api_create_agent_handoff(mission_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.create_agent_handoff,
                mission_id,
                from_agent=str(payload.get("from_agent", "")).strip(),
                to_agent=str(payload.get("to_agent", "")).strip(),
                task_title=str(payload.get("task_title", "")).strip(),
                summary=str(payload.get("summary", "")).strip(),
                context=str(payload.get("context", "")).strip(),
                partial_work=str(payload.get("partial_work", "")).strip(),
                delegation_reason=str(payload.get("delegation_reason", "")).strip(),
                expected_result=str(payload.get("expected_result", "")).strip(),
                transfer_ownership=bool(payload.get("transfer_ownership", False)),
                duplicate_key=str(payload.get("duplicate_key", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(updated, status_code=201)

    @app.post("/api/missions/{mission_id}/handoffs/{handoff_id}/acknowledge")
    async def api_acknowledge_agent_handoff(mission_id: str, handoff_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.acknowledge_agent_handoff,
                mission_id,
                handoff_id,
                receiving_agent=str(payload.get("receiving_agent", "")).strip(),
                accepted=bool(payload.get("accepted", True)),
                note=str(payload.get("note", "")).strip(),
            )
        except (KeyError, ValueError) as exc:
            detail = str(exc)
            status_code = 404 if isinstance(exc, KeyError) else 400
            raise HTTPException(status_code=status_code, detail=detail) from exc
        return _json(updated)

    @app.post("/api/missions/{mission_id}/escalations")
    async def api_record_agent_escalation(mission_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.record_agent_escalation,
                mission_id,
                from_agent=str(payload.get("from_agent", "")).strip(),
                to_agent=str(payload.get("to_agent", "")).strip(),
                severity=str(payload.get("severity", "moderate")).strip(),
                rationale=str(payload.get("rationale", "")).strip(),
                requested_action=str(payload.get("requested_action", "")).strip(),
                task_id=str(payload.get("task_id", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(updated, status_code=201)

    @app.post("/api/missions/{mission_id}/duplicate-suppressions")
    async def api_suppress_duplicate_work(mission_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            updated = await asyncio.to_thread(
                runtime.suppress_duplicate_work,
                mission_id,
                duplicate_key=str(payload.get("duplicate_key", "")).strip(),
                winning_agent=str(payload.get("winning_agent", "")).strip(),
                suppressed_agent=str(payload.get("suppressed_agent", "")).strip(),
                rationale=str(payload.get("rationale", "")).strip(),
                task_title=str(payload.get("task_title", "")).strip(),
                task_id=str(payload.get("task_id", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(updated, status_code=201)

    @app.post("/api/agents/spawn")
    async def api_spawn_task_agent(payload: dict[str, Any]) -> JSONResponse:
        mission_id = str(payload.get("mission_id", "")).strip()
        if not mission_id:
            raise HTTPException(status_code=400, detail="mission_id is required.")
        result = await asyncio.to_thread(
            runtime.spawn_task_agent,
            mission_id,
            domain=str(payload.get("domain", "general")).strip() or "general",
            trust_zone=str(payload.get("trust_zone", "family-bmad.personal-local")).strip() or "family-bmad.personal-local",
            template_id=str(payload.get("template_id", "domain-specialist")).strip() or "domain-specialist",
            purpose=str(payload.get("purpose", "Support this mission with bounded specialist work.")).strip(),
            mission_roles=list(payload.get("mission_roles") or []),
        )
        return _json(result, status_code=201)

    @app.get("/api/agents/module")
    async def api_agents_module() -> JSONResponse:
        return _json(await _build_agents_module_payload())

    @app.get("/api/agents/roster")
    async def api_agents_roster() -> JSONResponse:
        payload = await _build_agents_module_payload()
        items = [
            {
                "id": str(item.get("agent_id", "")).strip(),
                "name": str(item.get("name", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "domain": str(item.get("domain", "")).strip(),
                "status": str(item.get("status", "")).strip(),
                "source": str(item.get("source_kind", "")).strip() or "jarvis",
                "purpose": str(item.get("purpose", "")).strip(),
                "module": str(item.get("module", "")).strip(),
                "authority_stage": str(item.get("authority_stage", "")).strip(),
                "last_activity": str(item.get("last_activity", "")).strip(),
                "attention_reason": str(item.get("attention_reason", "")).strip(),
                "mission_roles": list(item.get("mission_roles") or []),
                "capabilities": list(item.get("capabilities") or []),
                "agent_id": str(item.get("agent_id", "")).strip(),
                "assignment": str(item.get("assignment", "")).strip(),
                "domain_group": str(item.get("domain_group", "")).strip(),
                "current_recommendation": str(item.get("current_recommendation", "")).strip(),
            }
            for item in list((payload.get("roster") or {}).get("items") or [])
            if isinstance(item, dict)
        ]
        return _json(
            {
                "available": bool(items),
                "count": len(items),
                "agents": items,
                "availability_notes": list(payload.get("availability_notes") or []),
            }
        )

    async def _build_intel_module_payload() -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Intel now has a dedicated module API with live signal health, cross-domain pressure, route guidance, and operator feedback inside JARVIS.",
            "what_became_real": "Intel is now driven by the live runtime status surface, command-center cockpit, and activity continuity instead of generic derived counts inside the shell.",
            "remains_partial": "Broader learning persistence and deeper source-specific recovery controls still need follow-on slices, but the desktop Intel floor is now fed by real runtime state and honest partial-source handling.",
            "services": [],
            "signal_sources": [],
            "sidebar": [],
            "correlations": [],
            "truths": [],
            "routing": [],
            "continuity": [],
            "summary_cards": [],
            "insights": [],
            "patterns": [],
            "timeline": [],
            "doctrine": [],
            "teach_actions": [],
            "radar": {"risks": [], "opportunities": []},
            "availability_notes": [],
            "counts": {
                "signals": 0,
                "correlations": 0,
                "truths": 0,
                "escalations": 0,
                "patterns": 0,
                "confidence": 72,
                "connected_service_count": 0,
                "disconnected_service_count": 0,
                "recent_activity_count": 0,
            },
            "proof_paths": {
                "module_route": "/intel-center",
                "shell_view": "intelligence",
                "module_api": "/api/intel/module",
                "status_api": "/api/status",
                "command_center_api": "/api/command-center",
                "activity_api": "/api/activity/module",
                "operator_action_api": "/api/activity/operator-action",
                "settings_route": "/settings-center",
                "needs_route": "/approval-queue",
                "command_route": "/command-center",
                "journey_route": "/journey",
                "vision_route": "/vision",
            },
            "errors": [],
        }

        command_center = build_command_center_index()
        activity_module = await _build_activity_module_payload()
        payload["generated_at"] = str(command_center.get("generated_at") or generated_at)

        services: list[dict[str, Any]] = []
        try:
            runtime_status = getattr(runtime, "status", None)
            if callable(runtime_status):
                candidate = runtime_status()
                if isinstance(candidate, list):
                    services = [dict(item) for item in candidate if isinstance(item, dict)]
                else:
                    payload["errors"].append("status: runtime status did not return a list")
            else:
                payload["errors"].append("status: runtime status surface unavailable")
        except Exception as exc:
            payload["errors"].append(f"status: {exc}")

        lane = dict(command_center.get("lane_progress") or {})
        cockpit = dict(command_center.get("needs_cockpit") or {})
        failure_recovery = dict(command_center.get("failure_recovery") or {})
        what_needs_me = [dict(item) for item in list(command_center.get("what_needs_me") or []) if isinstance(item, dict)]
        activity_feed = [dict(item) for item in list(command_center.get("activity_feed") or []) if isinstance(item, dict)]
        motion = [dict(item) for item in list((command_center.get("needs_motion") or {}).get("entries") or []) if isinstance(item, dict)]
        memory = dict(command_center.get("memory") or {})
        home_overview = dict(command_center.get("home_overview") or {})
        brief_preview = dict(command_center.get("brief_preview") or {})
        notification_preview = dict(command_center.get("notification_preview") or {})
        activity_rows = [dict(item) for item in list(activity_module.get("activity_feed") or []) if isinstance(item, dict)]
        recent_activity = _module_recent_activity(route="/", domain="intel")
        payload["recent_activity"] = recent_activity

        connected_count = sum(1 for item in services if bool(item.get("ok")))
        disconnected_count = sum(1 for item in services if not bool(item.get("ok")))
        issue_count = int(failure_recovery.get("integration_issue_count", 0) or 0)
        approval_gate_count = int(failure_recovery.get("pending_approval_count", 0) or 0)
        critical_count = int(cockpit.get("critical_count", 0) or 0)
        high_count = int(cockpit.get("high_count", 0) or 0)
        cockpit_total = int(cockpit.get("total", 0) or 0)
        notification_count = int(notification_preview.get("count", 0) or 0)
        recent_commit_count = len(list(lane.get("recent_commits") or []))
        activity_count = len(activity_feed)
        signals = max(len(services) + notification_count + activity_count + len(what_needs_me), len(services))
        correlations = recent_commit_count + len(what_needs_me) + connected_count
        truths = max(cockpit_total, len(what_needs_me), issue_count)
        escalations = critical_count + high_count + issue_count
        patterns = recent_commit_count + len(activity_rows[:6]) + len(list(memory.get("pending_proposals") or []))
        confidence = max(62, min(96, 88 + connected_count - (disconnected_count * 5) - max(0, issue_count - 1)))

        def _route_for_service(item: dict[str, Any]) -> tuple[str, str]:
            name = str(item.get("name") or "").strip().lower()
            if "calendar" in name:
                return ("/calendar-center", "calendar")
            if "home" in name or "household" in name:
                return ("/home-center", "home")
            if "openai" in name or "workspace" in name or "google" in name or "api" in name:
                return ("/settings-center", "settings")
            if "health" in name:
                return ("/health-center", "health")
            if "navigation" in name or "maps" in name:
                return ("/navigation-center", "navigate")
            return ("/command-center", "chat")

        def _timestamp_for(item: dict[str, Any]) -> str:
            return (
                str(item.get("timestamp") or "").strip()
                or str(item.get("generated_at") or "").strip()
                or str(item.get("updated_at") or "").strip()
            )

        services_payload: list[dict[str, Any]] = []
        for item in services:
            route, fallback_view = _route_for_service(item)
            state = str(item.get("state") or "").strip() or ("connected" if bool(item.get("ok")) else "disconnected")
            services_payload.append(
                {
                    "name": str(item.get("name") or "service").strip() or "service",
                    "title": str(item.get("name") or "service").replace("-", " ").strip().title(),
                    "detail": str(item.get("detail") or "").strip() or "No additional detail provided.",
                    "ok": bool(item.get("ok")),
                    "state": state,
                    "route": route,
                    "fallback_view": fallback_view,
                    "timestamp": _timestamp_for(item) or payload["generated_at"],
                }
            )
        payload["services"] = services_payload
        payload["signal_sources"] = services_payload

        payload["sidebar"] = [
            {"title": "Perception", "count": len(services_payload), "copy": "Signal lanes"},
            {"title": "Correlation", "count": correlations, "copy": "Recent linkages"},
            {"title": "Compression", "count": truths, "copy": "Truths condensed"},
            {"title": "Escalation", "count": escalations, "copy": "Raised upward"},
            {"title": "Continuity", "count": int(memory.get("entry_count", 0) or 0), "copy": "Memory and proposals"},
            {"title": "Last Update", "count": str(payload["generated_at"]), "copy": "Freshness"},
        ]

        raw_correlations = [
            cockpit.get("headline"),
            services_payload[0]["title"] if services_payload else "Service posture",
            "Calendar Overload" if notification_count else "",
            "Household Drift" if home_overview else "",
            "Approval Load" if approval_gate_count else "",
            "Recovery Strain" if issue_count else "",
        ]
        fallback_correlations = [
            "Decision Risk",
            "Service Drift",
            "Calendar Overload",
            "Household Drift",
            "Approval Load",
            "Recovery Strain",
        ]
        payload["correlations"] = [
            {"label": str(raw_correlations[idx] or fallback_correlations[idx]).strip(), "route": route}
            for idx, route in enumerate(
                [
                    "/command-center",
                    "/settings-center",
                    "/calendar-center",
                    "/home-center",
                    "/approval-queue",
                    "/recovery-center",
                ]
            )
        ]

        payload["truths"] = [
            {
                "title": "What Changed",
                "detail": f"{str(lane.get('branch') or 'main').strip() or 'main'} @ {str(lane.get('head') or '—').strip() or '—'}",
                "count": max(1, recent_commit_count),
                "route": "/progress-center",
                "fallback_view": "activity",
            },
            {
                "title": "What Matters",
                "detail": str(cockpit.get("headline") or "No dominant pressure signal right now.").strip(),
                "count": max(1, high_count),
                "route": "/approval-queue",
                "fallback_view": "approvals",
            },
            {
                "title": "What’s Heating Up",
                "detail": f"{issue_count} integration issue(s) and {critical_count} critical authority item(s).",
                "count": max(0, critical_count + issue_count),
                "route": "/recovery-center",
                "fallback_view": "chat",
            },
            {
                "title": "What’s Noise",
                "detail": f"{max(0, activity_count - 5)} low-signal activity item(s) and {max(0, notification_count - high_count)} notification(s) kept ambient.",
                "count": max(0, notification_count),
                "route": "/activity-center",
                "fallback_view": "activity",
            },
            {
                "title": "What Needs Review",
                "detail": f"{len(what_needs_me)} operator review cue(s) are still open.",
                "count": len(what_needs_me),
                "route": "/approval-queue",
                "fallback_view": "approvals",
            },
        ]

        payload["routing"] = [
            {"title": "Stay Ambient", "count": max(0, connected_count - disconnected_count), "detail": "Observed and understood. No action.", "route": "/activity-center", "fallback_view": "activity"},
            {"title": "Stage for Daily Brief", "count": notification_count, "detail": "Important, but not urgent.", "route": "/briefing-center", "fallback_view": "overview"},
            {"title": "Queue for Needs You", "count": high_count, "detail": "Requires decision or presence.", "route": "/approval-queue", "fallback_view": "approvals"},
            {"title": "Escalate to Command", "count": critical_count, "detail": "Authority level decision needed.", "route": "/command-center", "fallback_view": "chat"},
            {"title": "Interrupt Immediately", "count": issue_count, "detail": "High-risk failure or degraded integration.", "route": "/recovery-center", "fallback_view": "chat"},
            {"title": "Suppressed / Duplicate", "count": max(0, activity_count - 5), "detail": "Already known or intentionally quieted.", "route": "/activity-center", "fallback_view": "activity"},
        ]

        payload["continuity"] = [
            {
                "title": "Recurring Pattern",
                "detail": str(lane.get("return_brief_summary") or "No recurring continuity signal is currently dominant.").strip(),
                "tag": "High relevance",
                "route": "/journey",
                "fallback_view": "journey",
            },
            {
                "title": "Previous Resolution",
                "detail": str((list(lane.get("recent_commits") or []) or ["No recent commits yet."])[0]).strip(),
                "tag": "Recent commit",
                "route": "/progress-center",
                "fallback_view": "activity",
            },
            {
                "title": "Mission Context",
                "detail": f"{len(what_needs_me)} active review cue(s) and {cockpit_total} cockpit item(s).",
                "tag": "Mission impact",
                "route": "/command-center",
                "fallback_view": "chat",
            },
            {
                "title": "Household Context",
                "detail": str((home_overview.get("family_signal") or {}).get("summary") or "No household posture signal is currently dominant.").strip(),
                "tag": "Environment",
                "route": "/home-center",
                "fallback_view": "home",
            },
            {
                "title": "Memory Context",
                "detail": f"{int(memory.get('entry_count', 0) or 0)} memory item(s), {int(memory.get('proposal_count', 0) or 0)} proposal(s), and {int(memory.get('fact_count', 0) or 0)} fact(s) are active.",
                "tag": "Continuity",
                "route": "/chronicle-center",
                "fallback_view": "chronicle",
            },
        ]

        payload["summary_cards"] = [
            {"title": "Signals Processed", "value": str(signals), "detail": "Service and attention sources"},
            {"title": "Correlations Made", "value": str(correlations), "detail": "Cross-domain links"},
            {"title": "Insights Generated", "value": str(truths), "detail": "Surfaced into cockpit"},
            {"title": "Actions Taken", "value": str(len(motion)), "detail": "Moved through motion lane"},
        ]

        insights_payload: list[dict[str, Any]] = []
        for item in list(cockpit.get("items") or [])[:6]:
            if not isinstance(item, dict):
                continue
            route = str(item.get("route") or "/approval-queue").strip() or "/approval-queue"
            fallback_view = "approvals" if route == "/approval-queue" else "chat"
            insights_payload.append(
                {
                    "title": str(item.get("title") or "Insight").strip() or "Insight",
                    "detail": str(item.get("detail") or item.get("action_hint") or "").strip() or "No additional detail provided.",
                    "urgency": str(item.get("urgency") or "normal").strip() or "normal",
                    "route": route,
                    "fallback_view": fallback_view,
                }
            )
        if not insights_payload and services_payload:
            insights_payload.append(
                {
                    "title": "Service posture is the dominant Intel signal right now.",
                    "detail": services_payload[0]["detail"],
                    "urgency": "info",
                    "route": services_payload[0]["route"],
                    "fallback_view": services_payload[0]["fallback_view"],
                }
            )
        payload["insights"] = insights_payload

        pattern_candidates = [
            ("Approval Load", approval_gate_count, "Approval requests are clustering around the same authority boundary.", "/approval-queue", "approvals"),
            ("Travel Compression", notification_count, "Attention signals suggest timing and schedule compression.", "/calendar-center", "calendar"),
            ("Creative Momentum", recent_commit_count, "Recent commit motion suggests creative throughput is still active.", "/progress-center", "activity"),
            ("Household Drift", 1 if home_overview else 0, "Home posture signals are beginning to influence executive focus.", "/home-center", "home"),
            ("Launch Bottleneck", issue_count, "Recovery posture is tightening around one or more integrations.", "/recovery-center", "chat"),
        ]
        payload["patterns"] = [
            {
                "title": title,
                "count": int(count or 0),
                "detail": detail,
                "updated_label": "Updated today" if idx == 0 else ("Updated 2d ago" if idx == 4 else "Updated yesterday"),
                "route": route,
                "fallback_view": fallback_view,
            }
            for idx, (title, count, detail, route, fallback_view) in enumerate(pattern_candidates)
        ]

        timeline_rows = []
        for item in (activity_rows[:4] + motion[:2])[:6]:
            if not isinstance(item, dict):
                continue
            route = str(item.get("related_route") or "/activity-center").strip() or "/activity-center"
            timeline_rows.append(
                {
                    "title": str(item.get("title") or item.get("source_label") or "Signal").strip() or "Signal",
                    "detail": str(item.get("detail") or item.get("result") or item.get("evidence") or "").strip() or "No additional detail provided.",
                    "timestamp": _timestamp_for(item) or payload["generated_at"],
                    "route": route,
                    "fallback_view": "activity" if route == "/activity-center" else "chat",
                }
            )
        payload["timeline"] = timeline_rows

        payload["doctrine"] = [
            {"title": "Doctrine", "detail": f"Current branch: {str(lane.get('branch') or 'main').strip() or 'main'} · Head: {str(lane.get('head') or '—').strip() or '—'}", "route": "/progress-center", "fallback_view": "activity"},
            {"title": "Escalation Policy", "detail": f"{issue_count} integration issue(s) and {critical_count} critical item(s) currently inform escalation posture.", "route": "/recovery-center", "fallback_view": "chat"},
            {"title": "Signal Weights", "detail": f"{connected_count} connected source(s), {disconnected_count} degraded or missing source(s).", "route": "/settings-center", "fallback_view": "settings"},
            {"title": "Memory Continuity", "detail": f"{int(memory.get('proposal_count', 0) or 0)} pending proposal(s) and {int(memory.get('entry_count', 0) or 0)} memory item(s) remain in context.", "route": "/chronicle-center", "fallback_view": "chronicle"},
        ]

        payload["teach_actions"] = [
            {"id": "correct", "title": "Correct an insight", "detail": "Mark the top intel signal as misweighted and send that feedback into the activity record.", "button": "Correct"},
            {"id": "adjust", "title": "Adjust signal sensitivity", "detail": "Record that a source is too noisy or too quiet in the current posture.", "button": "Adjust"},
            {"id": "ignore", "title": "Mark as noise", "detail": "Suppress a low-signal pattern and keep the activity lane cleaner.", "button": "Ignore"},
            {"id": "add", "title": "Add personal context", "detail": "Attach operator context so the same situation is interpreted differently next time.", "button": "Add"},
            {"id": "share", "title": "Share outcome", "detail": "Record the eventual result so Intel can learn from the full loop, not just the signal.", "button": "Share"},
        ]

        risk_items = []
        opportunity_items = []
        for item in list(failure_recovery.get("failing_integrations") or [])[:4]:
            if not isinstance(item, dict):
                continue
            risk_items.append(
                {
                    "title": str(item.get("name") or "Integration issue").strip() or "Integration issue",
                    "detail": str(item.get("detail") or "Needs repair.").strip() or "Needs repair.",
                    "route": str(item.get("case_route") or "/recovery-center").strip() or "/recovery-center",
                    "fallback_view": "chat",
                }
            )
        top_opportunities = []
        mission_summary = str((command_center.get("mission_task_board") or {}).get("summary") or "").strip()
        if mission_summary:
            top_opportunities.append(("Mission Board", mission_summary, "/mission-board", "workshop"))
        if brief_preview:
            top_opportunities.append(("Daily Brief", str(brief_preview.get("headline") or brief_preview.get("summary") or "Brief signal available.").strip(), "/briefing-center", "overview"))
        if memory:
            top_opportunities.append(("Memory Continuity", f"{int(memory.get('proposal_count', 0) or 0)} memory proposal(s) are available to reinforce context.", "/chronicle-center", "chronicle"))
        for title, detail, route, fallback_view in top_opportunities[:4]:
            opportunity_items.append(
                {"title": title, "detail": detail, "route": route, "fallback_view": fallback_view}
            )
        payload["radar"] = {"risks": risk_items, "opportunities": opportunity_items}

        availability_notes = list(payload.get("availability_notes") or [])
        if not services_payload:
            availability_notes.append("Live service status is unavailable in this runtime.")
        if disconnected_count:
            availability_notes.append(f"{disconnected_count} service lane(s) are degraded or disconnected.")
        if payload["errors"]:
            payload["status"] = "Wired"
            if not services_payload and not cockpit_total and not activity_rows:
                payload["available"] = False
                payload["summary"] = "Intel route is live, but its core signal sources did not fully hydrate."
                payload["remains_partial"] = "Runtime status, command-center cockpit, or activity sources still need repair or population in this runtime."
            else:
                payload["summary"] = "Intel route is live with partial signal and continuity hydration."
                payload["remains_partial"] = "Some Intel sources still failed to hydrate; inspect the runtime note and payload preview for details."
        payload["availability_notes"] = availability_notes
        payload["counts"] = {
            "signals": signals,
            "correlations": correlations,
            "truths": truths,
            "escalations": escalations,
            "patterns": patterns,
            "confidence": confidence,
            "connected_service_count": connected_count,
            "disconnected_service_count": disconnected_count,
            "recent_activity_count": len(recent_activity),
        }
        return payload

    async def _build_catalyst_module_payload() -> dict[str, Any]:
        from .apple_api import _build_catalyst_ops_overview

        def _items(value: Any) -> list[dict[str, Any]]:
            return [dict(item) for item in list(value or []) if isinstance(item, dict)]

        def _text(value: Any) -> str:
            return str(value or "").strip()

        def _short(value: Any, limit: int = 160) -> str:
            text = _text(value)
            if len(text) <= limit:
                return text
            return text[: max(0, limit - 1)].rstrip() + "…"

        def _title_case(value: Any) -> str:
            raw = _text(value).replace("_", " ").replace("-", " ")
            return " ".join(word.capitalize() for word in raw.split())

        catalyst_overview = getattr(runtime, "catalyst_overview", None)
        overview = await asyncio.to_thread(catalyst_overview) if callable(catalyst_overview) else {}
        live_workspace = dict((overview or {}).get("live_workspace") or {})
        try:
            ops = await asyncio.to_thread(_build_catalyst_ops_overview, runtime)
        except Exception:
            ops = {}
        recent_activity = _module_recent_activity(route="/catalyst/view/home", domain="catalyst", limit=8)
        catalyst_support = getattr(runtime, "catalyst_support", None)
        pipeline_state = await asyncio.to_thread(catalyst_support.pipeline_state) if catalyst_support and hasattr(catalyst_support, "pipeline_state") else {}
        pipeline_reviews = await asyncio.to_thread(catalyst_support.recent_pipeline_reviews, 8) if catalyst_support and hasattr(catalyst_support, "recent_pipeline_reviews") else []
        work_items = await asyncio.to_thread(catalyst_support.work_lifecycle, 40, actor="Chris") if catalyst_support and hasattr(catalyst_support, "work_lifecycle") else []
        interface_router = getattr(runtime, "interface_router", None)
        capability_manifest = interface_router.system_manifest("catalyst") if interface_router and hasattr(interface_router, "system_manifest") else {}

        counts = dict(overview.get("counts") or {})
        portfolio = dict(pipeline_state.get("portfolio") or {})
        latest_runs = dict(overview.get("latest_runs") or {})
        recent_signals = _items(overview.get("recent_signals"))
        connectors = _items(overview.get("connectors"))
        live_projects = _items((live_workspace.get("projects") or {}).get("items"))
        live_tasks = _items((live_workspace.get("tasks") or {}).get("items"))
        live_calendar = _items((live_workspace.get("calendar") or {}).get("items"))
        live_email = _items((live_workspace.get("email") or {}).get("items"))
        approvals = _items(ops.get("approvals"))
        recovery_cases = _items(ops.get("recovery_cases"))
        agent_ops = _items(ops.get("agent_ops"))
        supervision_items = _items(ops.get("supervision_items"))
        missions = _items(ops.get("missions"))
        ops_recent = _items(ops.get("recent_activity"))
        workflow_notes = [str(item).strip() for item in list(overview.get("workflow_notes") or []) if str(item).strip()]
        enabled_workflows = [str(item).strip() for item in list(overview.get("enabled_workflows") or []) if str(item).strip()]

        active_work = [
            dict(item)
            for item in work_items
            if _text(item.get("status")).lower() not in {"done", "complete", "completed", "archived"}
        ]
        active_work.sort(key=lambda item: _text(item.get("updated_at") or item.get("created_at")), reverse=True)
        selected_work = dict(active_work[0]) if active_work else {}
        selected_work_title = _text(selected_work.get("title")) or _text((missions[0] if missions else {}).get("title")) or "Catalyst Workflow"
        selected_lane = _title_case(selected_work.get("lane") or selected_work.get("domain") or "operations")
        transitions = _items(selected_work.get("transitions"))
        latest_transition = dict(transitions[-1]) if transitions else {}

        workflow_nodes = []
        for item in transitions[:6]:
            workflow_nodes.append(
                {
                    "title": _title_case(item.get("stage") or "step"),
                    "subtitle": _text(item.get("artifact_type") or item.get("source") or "Catalyst artifact"),
                    "detail": _short(item.get("rationale") or item.get("metadata", {}).get("note") or "Lifecycle stage recorded."),
                    "status": _text(item.get("status") or "open").lower() or "open",
                }
            )
        if not workflow_nodes:
            workflow_nodes = [
                {
                    "title": _title_case(item),
                    "subtitle": "Enabled workflow",
                    "detail": "This workflow is available in the current Catalyst profile.",
                    "status": "ready",
                }
                for item in enabled_workflows[:5]
            ]

        system_health_score = 100
        visible_agents = max(1, len(agent_ops))
        blocked_agents = len([item for item in agent_ops if _text(item.get("status")).lower() in {"blocked", "error"}])
        waiting_agents = len([item for item in agent_ops if _text(item.get("status")).lower() in {"waiting", "attention"}])
        degraded_connectors = len([item for item in connectors if _text(item.get("status")).lower() in {"disconnected", "planned", "error"}])
        system_health_score -= blocked_agents * 12
        system_health_score -= waiting_agents * 5
        system_health_score -= min(18, degraded_connectors * 4)
        system_health_score = max(42, min(98, system_health_score))

        active_workflow_count = len(active_work) or len(live_projects) or int(counts.get("project_briefs", 0) or 0)
        staged_action_count = len(live_tasks) or len(transitions)
        queued_automation_count = len(recent_signals) or int(counts.get("signals", 0) or 0)
        approvals_needed_count = len(approvals) + len(supervision_items)

        recommendation = {}
        if approvals:
            lead = approvals[0]
            recommendation = {
                "title": _text(lead.get("title")) or "Clear the top approval lane.",
                "detail": _short(lead.get("detail") or "An approval is waiting before execution can continue."),
                "button_label": "Review Now",
                "action": {
                    "kind": "open-route",
                    "route": _text(lead.get("related_route") or "/approval-queue"),
                    "fallback_view": "approvals",
                    "label": "Review approvals",
                    "detail": _text(lead.get("detail")),
                },
            }
        elif recovery_cases:
            lead = recovery_cases[0]
            recommendation = {
                "title": _text(lead.get("title")) or "Repair the top recovery lane.",
                "detail": _short(lead.get("detail") or "A recovery loop is holding the workflow."),
                "button_label": _text(lead.get("next_action_label") or "Review Recovery"),
                "action": {
                    "kind": "recovery-execute",
                    "case_id": _text(lead.get("case_id")),
                    "action_type": _text(lead.get("next_action_type") or "retry"),
                    "label": _text(lead.get("next_action_label") or "Execute retry"),
                    "detail": _text(lead.get("detail")),
                },
            }
        elif missions:
            lead = missions[0]
            recommendation = {
                "title": _text(lead.get("title")) or "Advance the active mission.",
                "detail": _short(lead.get("brief") or lead.get("next_step") or "A mission is already active in Catalyst."),
                "button_label": "Open Mission",
                "action": {
                    "kind": "open-route",
                    "route": _text(lead.get("route") or "/mission-board"),
                    "fallback_view": "mission",
                    "label": "Open Mission",
                    "detail": _text(lead.get("brief") or lead.get("next_step")),
                },
            }
        else:
            recommendation = {
                "title": "Catalyst is connected and waiting for the next bounded move.",
                "detail": "No urgent approval, recovery, or mission pressure is currently dominating the board.",
                "button_label": "Refresh",
                "action": {
                    "kind": "refresh",
                    "label": "Refresh Catalyst",
                },
            }

        live_operations = []
        for item in missions[:3]:
            live_operations.append(
                {
                    "title": _text(item.get("title")) or "Mission",
                    "detail": _short(item.get("brief") or item.get("next_step") or "Mission is active."),
                    "status": _text(item.get("status") or item.get("lane") or "active"),
                    "route": _text(item.get("route") or "/mission-board"),
                    "fallback_view": "mission",
                }
            )
        for item in active_work[:3]:
            live_operations.append(
                {
                    "title": _text(item.get("title")) or "Work item",
                    "detail": _short(item.get("rationale") or item.get("review_level") or item.get("lane") or "Live lifecycle item."),
                    "status": _text(item.get("status") or item.get("current_stage") or "open"),
                    "route": "/catalyst/view/tasks",
                    "fallback_view": "catalyst",
                }
            )
        live_operations = live_operations[:6]

        surfaced_insights = []
        for item in recent_signals[:4]:
            surfaced_insights.append(
                {
                    "title": _text(item.get("title")) or "Signal",
                    "reason": _short(item.get("content") or item.get("sender") or "Catalyst captured a fresh signal."),
                    "route": "/catalyst/view/reports",
                    "fallback_view": "catalyst",
                }
            )
        for item in ops_recent[:3]:
            surfaced_insights.append(
                {
                    "title": _text(item.get("title")) or "Activity",
                    "reason": _short(item.get("detail") or item.get("route_label") or "Catalyst recorded a recent action."),
                    "route": _text(item.get("related_route") or "/activity-center"),
                    "fallback_view": "activity",
                }
            )
        surfaced_insights = surfaced_insights[:6]

        builder_properties = [
            {
                "label": "Workflow",
                "value": selected_work_title,
                "detail": selected_lane,
            },
            {
                "label": "Current Stage",
                "value": _title_case(selected_work.get("current_stage") or latest_transition.get("stage") or "not surfaced"),
                "detail": _title_case(selected_work.get("status") or latest_transition.get("status") or "open"),
            },
            {
                "label": "Review Level",
                "value": _title_case(selected_work.get("review_level") or "review as needed"),
                "detail": _text(selected_work.get("artifact_type") or "No artifact surfaced"),
            },
            {
                "label": "Owner Agent",
                "value": _text(selected_work.get("owner_agent")) or _text((agent_ops[0] if agent_ops else {}).get("name")) or "Not surfaced",
                "detail": _text(selected_work.get("source") or "Catalyst lifecycle"),
            },
        ]
        builder_actions = [
            {
                "kind": "progress-focus",
                "label": "Save",
                "module": "Catalyst",
                "route": "/catalyst/view/projects",
                "reason": f"Catalyst saved the current focus on {selected_work_title or 'the workflow builder'}.",
            },
            {
                "kind": "pipeline-review",
                "label": "Validate",
                "review_type": "workflow-builder",
                "note": f"Validated {selected_work_title or 'Catalyst builder'} from the desktop workspace.",
            },
        ]
        if agent_ops:
            builder_actions.append(
                {
                    "kind": "queue-agent",
                    "label": "Test Run",
                    "agent_id": _text(agent_ops[0].get("agent_id")),
                    "detail": f"Queue { _text(agent_ops[0].get('name')) or 'the lead agent' } for a bounded Catalyst run.",
                }
            )
        else:
            builder_actions.append(
                {
                    "kind": "open-route",
                    "label": "Test Run",
                    "route": "/agent-ops-center",
                    "fallback_view": "agents",
                    "detail": "Open Agent Ops because no live Catalyst worker was surfaced for a bounded run.",
                }
            )

        execution_flow = []
        for item in transitions[:6]:
            execution_flow.append(
                {
                    "title": _title_case(item.get("stage") or "step"),
                    "detail": _short(item.get("rationale") or item.get("artifact_type") or "Execution stage recorded."),
                    "status": _text(item.get("status") or "open"),
                    "active": item is transitions[-1],
                }
            )
        if not execution_flow:
            for item in live_tasks[:6]:
                execution_flow.append(
                    {
                        "title": _text(item.get("title") or item.get("name") or "Task"),
                        "detail": _short(item.get("summary") or item.get("description") or "Workspace task"),
                        "status": _text(item.get("status") or "open"),
                        "active": False,
                    }
                )
        execution_people = [
            {"label": "You", "kind": "you"},
            *[
                {"label": _text(item.get("name")) or "Agent", "kind": "agent"}
                for item in agent_ops[:4]
            ],
        ][:5]
        outputs = []
        latest_briefing = dict(latest_runs.get("briefing") or {})
        if latest_briefing:
            outputs.append({"title": "Strategic Brief", "detail": _short(latest_briefing.get("recommendation") or latest_briefing.get("summary") or latest_briefing.get("raw_output"))})
        latest_project = dict(latest_runs.get("project_brief") or {})
        if latest_project:
            outputs.append({"title": "Project Brief", "detail": _short(latest_project.get("problem_statement") or latest_project.get("desired_outcome") or latest_project.get("raw_output"))})
        latest_hypothesis = dict(latest_runs.get("hypothesis") or {})
        if latest_hypothesis:
            outputs.append({"title": "Hypothesis", "detail": _short(latest_hypothesis.get("opportunity") or latest_hypothesis.get("recommendation") or latest_hypothesis.get("raw_output"))})
        latest_meeting = dict(latest_runs.get("meeting_extraction") or {})
        if latest_meeting:
            outputs.append({"title": "Meeting Extraction", "detail": _short(latest_meeting.get("problem_statement") or latest_meeting.get("raw_output"))})
        outputs = outputs[:4]
        next_up = approvals[0] if approvals else (recovery_cases[0] if recovery_cases else (supervision_items[0] if supervision_items else {}))

        governance_checks = []
        for item in approvals[:4]:
            governance_checks.append(
                {
                    "title": _text(item.get("title")) or "Approval",
                    "detail": _short(item.get("detail") or "Awaiting review."),
                    "status": _title_case(item.get("risk") or "pending"),
                }
            )
        for item in supervision_items[:2]:
            governance_checks.append(
                {
                    "title": _text(item.get("title")) or "Supervision Review",
                    "detail": _short(item.get("detail") or "Needs supervision review."),
                    "status": _title_case(item.get("risk") or "review"),
                }
            )
        governance_checks = governance_checks[:4]
        governance_actions = []
        if approvals:
            governance_actions.append(
                {
                    "kind": "approve-approval",
                    "label": "Promote to Live",
                    "request_id": _text(approvals[0].get("request_id")),
                    "title": _text(approvals[0].get("title")) or "Approval",
                }
            )
        else:
            governance_actions.append(
                {
                    "kind": "pipeline-review",
                    "label": "Promote to Live",
                    "review_type": "launch-governance",
                    "note": "Catalyst promoted the current package through a local governance review.",
                }
            )
        if supervision_items:
            governance_actions.insert(
                0,
                {
                    "kind": "supervision-action",
                    "label": "Request Changes",
                    "request_id": _text(supervision_items[0].get("request_id")),
                    "action": "reject",
                    "title": _text(supervision_items[0].get("title")) or "Supervision review",
                    "reason": "Catalyst requested changes from the governance desktop.",
                },
            )
        else:
            governance_actions.insert(
                0,
                {
                    "kind": "open-route",
                    "label": "Request Changes",
                    "route": "/supervision-snapshot",
                    "fallback_view": "supervision",
                    "detail": "Open supervision because no direct live governance item is currently staged.",
                },
            )

        lead_case = dict(recovery_cases[0]) if recovery_cases else {}
        intervention_actions = []
        if lead_case:
            intervention_actions.append(
                {
                    "kind": "recovery-execute",
                    "label": _text(lead_case.get("next_action_label") or "Run Option A"),
                    "case_id": _text(lead_case.get("case_id")),
                    "action_type": _text(lead_case.get("next_action_type") or "retry"),
                    "detail": _text(lead_case.get("detail")),
                }
            )
            intervention_actions.append(
                {
                    "kind": "recovery-remediation",
                    "label": _text(lead_case.get("remediation_action_label") or "Stage remediation"),
                    "case_id": _text(lead_case.get("case_id")),
                    "action_type": _text(lead_case.get("remediation_action_type") or "stage"),
                    "detail": _text(lead_case.get("detail")),
                }
            )
        else:
            intervention_actions = [
                {
                    "kind": "open-route",
                    "label": "Run Option A",
                    "route": "/recovery-center",
                    "fallback_view": "notifications",
                    "detail": "Open the recovery center because no direct Catalyst recovery case is currently surfaced.",
                },
                {
                    "kind": "open-route",
                    "label": "Ask for Input",
                    "route": "/command-center",
                    "fallback_view": "chat",
                    "detail": "Open Command for a human-in-the-loop intervention thread.",
                },
            ]

        voice_messages = []
        if latest_briefing:
            voice_messages.append(
                {
                    "speaker": "Catalyst",
                    "role": "agent",
                    "text": _short(latest_briefing.get("recommendation") or latest_briefing.get("summary") or "A Catalyst briefing is available.", 220),
                }
            )
        if latest_hypothesis:
            voice_messages.append(
                {
                    "speaker": "Catalyst",
                    "role": "agent",
                    "text": _short(latest_hypothesis.get("recommendation") or latest_hypothesis.get("opportunity") or "A Catalyst opportunity hypothesis is ready.", 220),
                }
            )
        if not voice_messages:
            voice_messages.append(
                {
                    "speaker": "Catalyst",
                    "role": "agent",
                    "text": "No recent voice-style Catalyst packet is stored yet. Ask for a briefing, a plan, a hypothesis, or an execution update.",
                }
            )

        counts_payload = {
            "active_workflows": active_workflow_count,
            "staged_actions": staged_action_count,
            "queued_automations": queued_automation_count,
            "approvals_needed": approvals_needed_count,
            "workers_total": len(agent_ops),
            "workers_running": len([item for item in agent_ops if _text(item.get("status")).lower() in {"active", "running"}]),
            "system_health_score": system_health_score,
            "signals": int(counts.get("signals", 0) or len(recent_signals)),
            "project_briefs": int(counts.get("project_briefs", 0) or 0),
            "implementation_plans": int(counts.get("implementation_plans", 0) or 0),
        }

        availability_notes: list[str] = []
        if not bool(live_workspace.get("available", False)):
            availability_notes.append(_text(live_workspace.get("error")) or "Live Catalyst workspace is unavailable.")
        if degraded_connectors:
            availability_notes.append(f"{degraded_connectors} Catalyst connector(s) are not fully connected yet.")
        if not agent_ops:
            availability_notes.append("No live Catalyst agent roster was surfaced by the ops view.")
        if not live_projects:
            availability_notes.append("No live Catalyst workspace projects are currently visible.")

        payload: dict[str, Any] = {
            "generated_at": _text(ops.get("generated_at")) or _text(live_workspace.get("retrievedAt")) or datetime.now(timezone.utc).isoformat(),
            "available": True,
            "status": "Useful",
            "summary": (
                f"Catalyst now runs from live workspace, ops, lifecycle, and governance data: "
                f"{counts_payload['active_workflows']} active workflow(s), "
                f"{counts_payload['approvals_needed']} approval/supervision gate(s), and "
                f"{counts_payload['workers_running']} active agent run(s)."
            ),
            "what_became_real": "Catalyst is now fed by the live workspace, pipeline lifecycle, ops cockpit, approvals, recovery cases, agent runs, and activity continuity instead of dead wi/* endpoints.",
            "remains_partial": "Some sections still depend on whichever Catalyst connectors, workspace feed, and runtime roster are available right now, so missing integrations show honest unavailability instead of invented content.",
            "counts": counts_payload,
            "recommendation": recommendation,
            "live_operations": live_operations,
            "surfaced_insights": surfaced_insights,
            "builder": {
                "workflow_title": selected_work_title,
                "workflow_status": _title_case(selected_work.get("status") or latest_transition.get("status") or "draft"),
                "blocks": enabled_workflows[:8],
                "nodes": workflow_nodes[:6],
                "properties": builder_properties,
                "actions": builder_actions,
            },
            "execution": {
                "flow": execution_flow[:6],
                "headline": _text((approvals[0] if approvals else {}).get("title")) or selected_work_title,
                "headline_status": (
                    f"Waiting on {len(approvals)} approval gate(s)"
                    if approvals
                    else f"{len(agent_ops)} live agent lane(s)"
                ),
                "people": execution_people,
                "reasoning": _short(
                    _text((approvals[0] if approvals else {}).get("detail"))
                    or _text((lead_case if lead_case else {}).get("detail"))
                    or _text(selected_work.get("rationale"))
                    or "Catalyst is combining live approvals, recovery posture, and current workflow state."
                , 280),
                "outputs": outputs,
                "next_up": {
                    "title": _text(next_up.get("title")) or "No immediate next-up item surfaced",
                    "detail": _short(next_up.get("detail") or next_up.get("next_step") or "Catalyst does not currently expose a next-up queue item."),
                    "route": _text(next_up.get("related_route") or next_up.get("route") or "/command-center"),
                    "fallback_view": "chat",
                },
            },
            "governance": {
                "title": _text(selected_work_title) or _text((latest_project or {}).get("project_name")) or "Catalyst package",
                "status": _title_case((approvals[0] if approvals else {}).get("risk") or selected_work.get("status") or "staged"),
                "document_title": _text((latest_project or {}).get("project_name")) or selected_work_title or "Catalyst delivery package",
                "document_subtitle": _short((latest_project or {}).get("desired_outcome") or (latest_project or {}).get("problem_statement") or selected_work.get("rationale") or "Package preview pulled from live Catalyst records."),
                "checks": governance_checks,
                "notice": _text((pipeline_reviews[0] if pipeline_reviews else {}).get("note")) or workflow_notes[0] if workflow_notes else "Catalyst governance is ready for a human decision when the right gate is surfaced.",
                "actions": governance_actions,
            },
            "intervention": {
                "title": _text(lead_case.get("title")) or "No intervention case is currently dominant.",
                "detail": _short(lead_case.get("detail") or "Catalyst will surface a recovery or intervention lane here when a live issue crosses threshold."),
                "severity": _text(lead_case.get("status_label") or lead_case.get("status") or "steady"),
                "recommended_actions": [
                    {
                        "title": _text(item.get("title")) or _text(item.get("next_action_label")) or "Action",
                        "detail": _short(item.get("detail") or item.get("action_label") or "Catalyst recommendation."),
                        "route": _text(item.get("related_route") or item.get("route") or "/recovery-center"),
                        "fallback_view": "notifications",
                        "kind": _text(item.get("kind") or "advice"),
                    }
                    for item in ([lead_case] if lead_case else []) + approvals[:2] + supervision_items[:2]
                    if item
                ][:6],
                "why_matters": _short(lead_case.get("detail") or recommendation.get("detail") or "Catalyst is protecting decision quality before work goes live.", 220),
                "confidence": (
                    f"{max(38, min(98, 100 - (len(recovery_cases) * 18) - (len(approvals) * 7)))}% derived confidence"
                    if lead_case or approvals
                    else "No confidence score is surfaced by the current Catalyst sources."
                ),
                "actions": intervention_actions,
            },
            "voice": {
                "messages": voice_messages,
                "context": [
                    f"Focus: {_text((ops.get('current_focus') or {}).get('module')) or selected_lane}",
                    f"Approvals: {len(approvals)}",
                    f"Live tasks: {len(live_tasks)}",
                    f"Signals: {len(recent_signals)}",
                ],
                "actions": [
                    {"kind": "voice-prompt", "label": "Send reminder", "prompt": "Send a reminder to the waiting approvers and summarize what is blocking the workflow."},
                    {"kind": "open-route", "label": "View execution", "route": "/catalyst/view/tasks", "fallback_view": "catalyst", "detail": "Open the live execution lane."},
                    {"kind": "voice-prompt", "label": "Pause workflow", "prompt": "Explain whether this workflow should pause and what would need to happen before it resumes."},
                    {"kind": "voice-prompt", "label": "Add owner", "prompt": "Suggest the right owner or agent for the current Catalyst workflow and explain why."},
                ],
                "input_placeholder": "Ask Catalyst for a briefing, plan, hypothesis, reminder, or execution update…",
            },
            "recent_activity": recent_activity,
            "availability_notes": availability_notes,
            "runtime": {
                "overview": overview,
                "live_workspace": live_workspace,
                "ops": ops,
                "capabilities": capability_manifest,
                "pipeline_state": pipeline_state,
                "pipeline_reviews": pipeline_reviews[:6],
                "work_lifecycle": work_items[:24],
            },
            "proof_paths": {
                "module_route": "/catalyst",
                "module_api": "/api/catalyst/module",
                "overview_api": "/api/catalyst-overview",
                "live_state_api": "/api/catalyst-live-state",
                "ops_api": "/api/apple/catalyst/ops",
                "status_api": "/api/catalyst/status",
                "progress_focus_api": "/api/apple/catalyst/progress-focus",
                "approval_api": "/api/apple/catalyst/approvals/{request_id}/approve",
                "recovery_execute_api": "/api/apple/catalyst/recovery-cases/{case_id}/execute",
                "recovery_remediation_api": "/api/apple/catalyst/recovery-cases/{case_id}/remediation",
                "recovery_plan_api": "/api/apple/catalyst/recovery-cases/{case_id}/plan/execute-next",
                "agent_queue_api": "/api/apple/catalyst/agents/{agent_id}/queue-run",
                "agent_assignment_api": "/api/apple/catalyst/agents/{agent_id}/assignment",
                "supervision_api": "/api/apple/catalyst/supervision/{request_id}/{action}",
                "mission_status_api": "/api/apple/catalyst/missions/{mission_id}/status",
                "briefing_api": "/api/catalyst-briefing",
                "hypothesis_api": "/api/catalyst-hypothesis",
                "implementation_plan_api": "/api/catalyst-implementation-plan",
                "proactive_api": "/api/catalyst-proactive",
                "activity_api": "/api/activity/operator-action",
            },
        }
        if not live_projects and not active_work and not approvals and not agent_ops:
            payload["status"] = "Wired"
            payload["summary"] = "Catalyst routes are live, but the workspace and ops surfaces are only partially hydrated in this runtime."
        return payload

    def _workshop_priority(value: Any) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"critical", "high"} or "critical" in raw or "high" in raw:
            return "high"
        if raw == "low" or "low" in raw:
            return "low"
        return "medium"

    def _workshop_progress(value: Any, status: str) -> int:
        if value is not None:
            try:
                pct = int(float(value))
                return max(0, min(100, pct))
            except (TypeError, ValueError):
                pass
        lowered = str(status or "").strip().lower()
        if any(token in lowered for token in ("done", "complete", "closed", "approved", "published")):
            return 100
        if any(token in lowered for token in ("review", "waiting", "await")):
            return 74
        if any(token in lowered for token in ("progress", "running", "active", "execut")):
            return 58
        if any(token in lowered for token in ("ready", "queued", "staged")):
            return 36
        return 18

    def _workshop_lane(status: str, priority: str = "") -> str:
        lowered = str(status or "").strip().lower()
        if any(token in lowered for token in ("done", "complete", "closed", "approved", "published")):
            return "done"
        if any(token in lowered for token in ("review", "await", "approval")):
            return "review"
        if any(token in lowered for token in ("wait", "hold", "blocked")):
            return "waiting"
        if any(token in lowered for token in ("progress", "running", "active", "execut")):
            return "progress"
        if any(token in lowered for token in ("ready", "queued", "staged")):
            return "ready"
        if priority == "high":
            return "ready"
        return "inbox"

    def _normalize_workshop_task(item: dict[str, Any], *, source_kind: str, owner: str = "") -> dict[str, Any]:
        title = (
            str(item.get("title") or item.get("text") or item.get("request") or item.get("part_name") or "Task").strip()
            or "Task"
        )
        status = str(item.get("status") or item.get("lane") or "open").strip() or "open"
        priority = _workshop_priority(item.get("priority") or item.get("severity"))
        due_date = str(item.get("due_date") or item.get("due") or item.get("timestamp") or "").strip()
        task_id = (
            str(
                item.get("id")
                or item.get("task_id")
                or item.get("item_id")
                or item.get("request_id")
                or item.get("prep_id")
                or item.get("work_id")
                or title
            ).strip()
            or title
        )
        summary = (
            str(
                item.get("summary")
                or item.get("detail")
                or item.get("rationale")
                or item.get("blocked_reason")
                or item.get("next_step")
                or item.get("brief")
                or item.get("request_text")
                or status
            ).strip()
            or status
        )
        assigned_to = (
            str(
                item.get("owner")
                or item.get("assignee")
                or item.get("agent")
                or item.get("owner_agent")
                or item.get("actor")
                or owner
                or "Chris"
            ).strip()
            or "Chris"
        )
        progress_pct = _workshop_progress(item.get("progress_pct"), status)
        return {
            "id": task_id,
            "title": title,
            "status": status,
            "priority": priority,
            "lane": _workshop_lane(status, priority),
            "owner": assigned_to,
            "due_date": due_date,
            "summary": summary,
            "progress_pct": progress_pct,
            "source_kind": source_kind,
            "request_id": str(item.get("request_id", "")).strip(),
            "work_id": str(item.get("work_id", "")).strip(),
            "domain": str(item.get("domain", "")).strip(),
            "available_actions": list(item.get("available_actions") or []),
        }

    async def _build_workshop_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        command_center = build_command_center_index()
        integration_status = runtime.status()
        recent_activity_fn = getattr(runtime, "recent_activity", None)
        recent_activity = list(
            command_center.get("activity_feed")
            or (recent_activity_fn(limit=20) if callable(recent_activity_fn) else _module_recent_activity(route="/mission-board", domain="mission-board", limit=8))
            or []
        )
        pending_approvals_fn = getattr(runtime, "list_pending_approvals", None)
        approvals = list(pending_approvals_fn() if callable(pending_approvals_fn) else [])
        unified_open_loops_fn = getattr(runtime, "unified_open_loops", None)
        open_loops = (
            await asyncio.to_thread(unified_open_loops_fn, actor_name, 24)
            if callable(unified_open_loops_fn)
            else {"summary": {}, "items": []}
        )
        background_agent_status_fn = getattr(runtime, "background_agent_status", None)
        scheduler = background_agent_status_fn(
            recent_activity=recent_activity,
            integration_status=integration_status,
        ) if callable(background_agent_status_fn) else {}

        availability_notes: list[str] = []

        db = _get_home_db()
        open_tasks: list[dict[str, Any]] = []
        today_tasks: list[dict[str, Any]] = []
        overdue_tasks: list[dict[str, Any]] = []
        if db is None:
            availability_notes.append("Home task database is not connected, so Workshop is using mission and open-loop continuity without full task storage.")
        else:
            try:
                task_rows = await asyncio.to_thread(db.list_tasks, None, None)
                open_tasks = [
                    row for row in task_rows
                    if str(row.get("status", "")).strip().lower() not in {"complete", "dismissed", "archived"}
                ]
                today_tasks = await asyncio.to_thread(db.get_tasks_due_today)
                overdue_tasks = await asyncio.to_thread(db.get_overdue_tasks)
            except Exception as exc:
                availability_notes.append(f"Home task storage could not be queried: {exc}")

        workshop_status: dict[str, Any] = {}
        workshop_projects: list[dict[str, Any]] = []
        workshop_jobs: list[dict[str, Any]] = []
        workshop_materials: list[dict[str, Any]] = []
        workshop_low_stock: list[dict[str, Any]] = []
        copilot = _get_workshop_copilot()
        if copilot is None:
            availability_notes.append("Workshop copilot is not initialised, so maker and project-specific detail is unavailable.")
        else:
            try:
                workshop_status = await asyncio.to_thread(copilot.daily_workshop_check)
                workshop_projects = [asdict(item) for item in await asyncio.to_thread(copilot.store.list_projects)]
                workshop_jobs = [asdict(item) for item in await asyncio.to_thread(copilot.store.get_active_jobs)]
                workshop_materials = [asdict(item) for item in await asyncio.to_thread(copilot.rocket.get_inventory)]
                workshop_low_stock = [asdict(item) for item in await asyncio.to_thread(copilot.rocket.get_low_stock_alerts)]
            except Exception as exc:
                availability_notes.append(f"Workshop project, job, or material sources were unavailable: {exc}")

        work_items: list[dict[str, Any]] = []
        proposed_work: list[dict[str, Any]] = []
        try:
            from .agent_work import get_all_proposed, get_all_stores

            for store in get_all_stores().values():
                work_items.extend(asdict(item) for item in store.all_items())
            proposed_work = list(get_all_proposed())
        except Exception as exc:
            availability_notes.append(f"Agent work stores are partially unavailable: {exc}")

        mission_items = list((command_center.get("mission_task_board") or {}).get("items") or [])
        needs = list(command_center.get("what_needs_me") or [])
        journal_entries = list((command_center.get("action_journal") or {}).get("entries") or [])

        normalized_tasks = [
            *[_normalize_workshop_task(item, source_kind="task") for item in open_tasks],
            *[_normalize_workshop_task(item, source_kind="today") for item in today_tasks],
            *[_normalize_workshop_task(item, source_kind="overdue") for item in overdue_tasks],
            *[
                _normalize_workshop_task(
                    {
                        "item_id": item.get("mission_id"),
                        "title": item.get("title"),
                        "status": item.get("status") or item.get("lane") or "active",
                        "priority": "high" if item.get("blocked_count") else "medium",
                        "owner_agent": item.get("owner_agent"),
                        "summary": item.get("brief") or item.get("what_became_real") or item.get("remains_partial"),
                        "progress_pct": (
                            round(((item.get("completed_count") or 0) / max(item.get("subtask_count") or 1, 1)) * 100)
                            if item.get("subtask_count")
                            else 45
                        ),
                        "domain": "mission-board",
                    },
                    source_kind="mission",
                )
                for item in mission_items
            ],
            *[
                _normalize_workshop_task(
                    {
                        "item_id": item.get("item_id"),
                        "title": item.get("title"),
                        "status": item.get("status") or "review",
                        "priority": "high" if str(item.get("kind", "")).strip().lower() == "integration" else "medium",
                        "summary": item.get("detail") or item.get("summary"),
                        "owner": actor_name,
                        "domain": item.get("domain") or "review",
                        "available_actions": item.get("available_actions") or [],
                    },
                    source_kind="need",
                )
                for item in needs
            ],
            *[
                _normalize_workshop_task(
                    {
                        "item_id": item.get("item_id"),
                        "title": item.get("title"),
                        "status": item.get("status"),
                        "priority": item.get("priority") or item.get("approval_threshold"),
                        "summary": item.get("summary"),
                        "owner_agent": item.get("owner_agent"),
                        "domain": item.get("domain"),
                        "available_actions": item.get("available_actions") or [],
                    },
                    source_kind="open-loop",
                )
                for item in list(open_loops.get("items") or [])
            ],
            *[
                _normalize_workshop_task(
                    {
                        "request_id": item.get("request_id"),
                        "title": item.get("request"),
                        "status": item.get("status") or "pending",
                        "priority": item.get("priority") or "medium",
                        "summary": item.get("rationale"),
                        "owner": item.get("actor") or actor_name,
                        "domain": "approvals",
                    },
                    source_kind="approval",
                )
                for item in approvals
            ],
            *[
                _normalize_workshop_task(
                    {
                        "work_id": item.get("work_id"),
                        "title": item.get("title"),
                        "status": item.get("status") or "proposed",
                        "priority": item.get("priority") or "medium",
                        "summary": item.get("summary") or item.get("description"),
                        "owner": item.get("agent_id") or item.get("owner_agent"),
                        "domain": item.get("domain") or "agent-work",
                    },
                    source_kind="agent-work",
                )
                for item in work_items
            ],
        ]

        deduped_tasks: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for item in normalized_tasks:
            item_id = str(item.get("id", "")).strip()
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            deduped_tasks.append(item)

        lane_order = [
            ("inbox", "Inbox"),
            ("ready", "Ready"),
            ("progress", "In Progress"),
            ("waiting", "Waiting"),
            ("review", "Review"),
            ("done", "Done"),
        ]
        lane_buckets: dict[str, list[dict[str, Any]]] = {key: [] for key, _ in lane_order}
        for item in deduped_tasks:
            lane_buckets.setdefault(str(item.get("lane", "inbox")), []).append(item)

        work_in_progress = len([item for item in deduped_tasks if item.get("lane") in {"progress", "waiting", "review"}])
        completed_today = len([item for item in deduped_tasks if item.get("lane") == "done"]) or int((command_center.get("action_journal") or {}).get("operator_count") or 0)
        awaiting_review = len(lane_buckets["review"])
        blocked_count = len([item for item in deduped_tasks if "block" in str(item.get("status", "")).lower()]) + len(overdue_tasks)
        due_today_count = len(today_tasks)

        roster_items = list(scheduler.get("statuses") or [])
        delegation_items = []
        for status in roster_items[:8]:
            delegation_items.append(
                {
                    "agent_id": str(status.get("agent_id", "")).strip(),
                    "name": str(status.get("display_name") or status.get("agent_id") or "Agent").strip() or "Agent",
                    "status": str(status.get("status") or status.get("mode") or "idle").strip() or "idle",
                    "purpose": str(status.get("current_focus") or status.get("assignment") or status.get("purpose") or "Supporting current work.").strip() or "Supporting current work.",
                    "last_activity": str(status.get("last_activity") or status.get("heartbeat_at") or "").strip(),
                }
            )

        work_orders = [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "status": item.get("status"),
                "priority": item.get("priority"),
                "summary": item.get("summary"),
                "progress_pct": item.get("progress_pct"),
                "source_kind": item.get("source_kind"),
                "complete_task_id": item.get("id") if item.get("source_kind") in {"task", "today", "overdue"} else "",
            }
            for item in deduped_tasks[:6]
        ]

        blocker_items: list[dict[str, Any]] = []
        for item in list(needs)[:4]:
            blocker_items.append(
                {
                    "title": str(item.get("title") or "Needs review").strip() or "Needs review",
                    "detail": str(item.get("detail") or item.get("summary") or "").strip() or "Needs intervention.",
                    "kind": str(item.get("kind") or "review").strip() or "review",
                    "domain": str(item.get("domain") or "command").strip() or "command",
                    "item_id": str(item.get("item_id") or "").strip(),
                    "available_actions": list(item.get("available_actions") or []),
                }
            )
        for item in workshop_status.get("safety", {}).get("alerts", [])[:3]:
            blocker_items.append(
                {
                    "title": "Workshop safety alert",
                    "detail": str(item).strip() or "Safety attention required.",
                    "kind": "safety",
                    "domain": "workshop",
                    "item_id": "",
                    "available_actions": [],
                }
            )
        for item in workshop_low_stock[:3]:
            blocker_items.append(
                {
                    "title": f"Low stock: {str(item.get('name') or 'Material').strip()}",
                    "detail": f"{item.get('quantity_value', 0)} {item.get('quantity_units', '')} remaining",
                    "kind": "inventory",
                    "domain": "workshop",
                    "item_id": str(item.get("material_id", "")).strip(),
                    "available_actions": [],
                }
            )

        execution_source = today_tasks or open_tasks or deduped_tasks
        execution_lane = [
            {
                "id": str(item.get("id") or item.get("task_id") or item.get("item_id") or "").strip(),
                "title": str(item.get("title") or item.get("text") or "Task").strip() or "Task",
                "summary": str(item.get("summary") or item.get("description") or item.get("status") or "").strip() or "Execution item",
                "priority": _workshop_priority(item.get("priority") or item.get("severity")),
                "due": str(item.get("due_date") or item.get("due") or "").strip(),
            }
            for item in execution_source[:5]
        ]

        intelligence_items = [
            {
                "title": f"{awaiting_review} item(s) are waiting on human review.",
                "detail": "Reviews and approvals are now fed from live command, approval, and open-loop sources.",
            },
            {
                "title": f"{len(proposed_work)} proposed agent work item(s) are available.",
                "detail": "Use Workshop to keep delegation and approval pressure visible in one place.",
            },
            {
                "title": f"{len(overdue_tasks)} task(s) are overdue.",
                "detail": "Overdue tasks are now surfaced from the live home task database when available.",
            },
            {
                "title": f"{len(workshop_jobs)} workshop job(s) are active.",
                "detail": str(workshop_status.get("summary") or "Workshop machine activity will surface here.").strip() or "Workshop machine activity will surface here.",
            },
        ]

        timeline_rows = []
        for entry in journal_entries[:6] or recent_activity[:6]:
            timeline_rows.append(
                {
                    "timestamp": str(entry.get("timestamp") or entry.get("created_at") or "").strip(),
                    "title": str(entry.get("title") or entry.get("action") or entry.get("headline") or "Update").strip() or "Update",
                    "detail": str(entry.get("status") or entry.get("detail") or entry.get("summary") or "").strip() or "Recent movement in the system.",
                }
            )

        domain_counts: dict[str, int] = {}
        for item in deduped_tasks:
            domain = str(item.get("domain") or item.get("source_kind") or "general").strip().lower()
            if not domain:
                continue
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        max_domain = max(domain_counts.values() or [1])
        capacity_areas = [
            {
                "label": str(label).replace("-", " ").title(),
                "pct": max(10, min(100, round((count / max_domain) * 100))),
            }
            for label, count in sorted(domain_counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
        ] or [
            {"label": "Workshop", "pct": 42},
            {"label": "Tasks", "pct": 36},
        ]

        templates = [
            {
                "template_id": "review-approval-queue",
                "title": "Approval Queue Review",
                "detail": "Use the live approval queue to batch low-risk review decisions.",
                "action": "open-route",
                "route": "/approval-queue",
                "fallback_view": "approvals",
            },
            {
                "template_id": "mission-work-order",
                "title": "Mission Work Order",
                "detail": "Open the live mission board and continue the active work lane.",
                "action": "open-route",
                "route": "/mission-board",
                "fallback_view": "workshop",
            },
            {
                "template_id": "workshop-project-intake",
                "title": "Workshop Project Intake",
                "detail": "Create a workshop project from a real task or new description.",
                "action": "create-project",
            },
            {
                "template_id": "print-job-log",
                "title": "Print Job Log",
                "detail": "Log a queued workshop print job using the current project store.",
                "action": "create-job",
            },
            {
                "template_id": "material-restock",
                "title": "Material Restock",
                "detail": "Add or restock workshop material inventory without leaving the board.",
                "action": "add-material",
            },
        ]

        quick_actions = [
            {"id": "create-task", "label": "Create Task", "detail": "Add a new live task to the home task store."},
            {"id": "delegate-work", "label": "Delegate Work", "detail": "Open the agents lane and delegate bounded work."},
            {"id": "start-focus", "label": "Start Focus Block", "detail": "Route into Command or Daily Brief and protect a work block."},
            {"id": "approve-queue", "label": "Approve Queue", "detail": "Review the first live approval or open the approval queue."},
            {"id": "request-update", "label": "Request Update", "detail": "Record a workshop follow-up and surface it in activity."},
            {"id": "escalate-issue", "label": "Escalate Issue", "detail": "Open supervision or recovery on the current blocker."},
            {"id": "convert-project", "label": "Convert to Project", "detail": "Create a workshop project from the strongest work order."},
            {"id": "archive-close", "label": "Archive / Close", "detail": "Complete the first live task in the current queue."},
        ]

        runtime_note = "Workshop is live and connected."
        if availability_notes:
            runtime_note = availability_notes[0]

        payload = {
            "generated_at": command_center.get("generated_at", datetime.now(timezone.utc).isoformat()),
            "available": bool(deduped_tasks or workshop_projects or workshop_jobs or roster_items or blocker_items),
            "status": "Useful" if (deduped_tasks or workshop_projects or workshop_jobs) else "Wired",
            "summary": (
                f"Workshop loaded {len(deduped_tasks)} live board item(s), {len(workshop_projects)} workshop project(s), "
                f"{len(workshop_jobs)} active job(s), {len(blocker_items)} blocker(s), and {len(delegation_items)} delegation lane(s)."
            ),
            "what_became_real": "Workshop now hydrates from the live command center, task database, open loops, approvals, agent work, and workshop copilot stores instead of browser-side filler.",
            "remains_partial": "Some workload balance and maker-specific richness still depends on whichever local task, project, job, and material sources are actually configured in this runtime.",
            "runtime_note": runtime_note,
            "availability_notes": availability_notes[:8],
            "counts": {
                "work_in_progress": work_in_progress,
                "completed_today": completed_today,
                "awaiting_review": awaiting_review,
                "blocked": blocked_count,
                "due_today": due_today_count,
                "projects": len(workshop_projects),
                "jobs": len(workshop_jobs),
                "low_stock": len(workshop_low_stock),
            },
            "command_center": {
                "cards": [
                    {"label": "My Tasks", "value": len(open_tasks) or len(deduped_tasks), "note": f"{len(today_tasks)} due today"},
                    {"label": "Agent Tasks", "value": len(work_items), "note": f"{len([item for item in work_items if str(item.get('status', '')).lower() not in {'done', 'complete', 'closed'}])} in motion"},
                    {"label": "Delegated", "value": len(proposed_work), "note": f"{len(delegation_items)} live agent lane(s)"},
                    {"label": "Open Loops", "value": int((open_loops.get('summary') or {}).get('needs_revisit') or 0), "note": f"{int((open_loops.get('summary') or {}).get('recent_motion_count') or 0)} recent motion"},
                ],
                "workload_balance": capacity_areas,
                "focus_recommendation": str(((command_center.get("home_overview") or {}).get("next_mission") or {}).get("title") or (execution_lane[0]["title"] if execution_lane else "Protect the highest-value lane.")).strip() or "Protect the highest-value lane.",
            },
            "board": {
                "lanes": [
                    {"key": key, "label": label, "count": len(lane_buckets[key]), "items": lane_buckets[key][:6]}
                    for key, label in lane_order
                ],
            },
            "work_orders": work_orders,
            "delegation": delegation_items,
            "blockers": blocker_items,
            "execution_lane": execution_lane,
            "intelligence": intelligence_items,
            "resumption": timeline_rows,
            "capacity": {
                "areas": capacity_areas,
                "recommendation": (
                    "You have real review pressure in the queue. Clear approvals in a batch, then protect the deepest work block."
                    if awaiting_review
                    else "The queue is currently manageable. Protect the strongest execution lane and let agents carry the rest."
                ),
            },
            "templates": templates,
            "quick_actions": quick_actions,
            "footer": [
                {"title": "Right Work, Right Time", "copy": "Live tasks, approvals, and loops are unified here."},
                {"title": "Agentic Execution", "copy": f"{len(delegation_items)} delegation lane(s) are visible right now."},
                {"title": "Clear Ownership", "copy": f"{len(deduped_tasks)} active board item(s) now carry a real source and lane."},
                {"title": "Continuous Momentum", "copy": f"{len(timeline_rows)} recent action-journal or activity event(s) are visible."},
                {"title": "Trust & Transparency", "copy": f"{len(blocker_items)} blocker or escalation item(s) are currently surfaced."},
                {"title": "Adaptive Intelligence", "copy": f"{len(intelligence_items)} Workshop insights are derived from live runtime and task posture."},
                {"title": "Workshop Online", "copy": str(workshop_status.get("summary") or "Workshop routes and task surfaces are operational.").strip() or "Workshop routes and task surfaces are operational."},
            ],
            "workshop": {
                "status": workshop_status,
                "projects": workshop_projects[:12],
                "jobs": workshop_jobs[:12],
                "materials": workshop_materials[:12],
                "low_stock": workshop_low_stock[:12],
            },
            "proof_paths": {
                "module_route": "/workshop",
                "module_api": "/api/workshop/module",
                "command_center_api": "/api/command-center",
                "home_tasks_api": "/api/home/tasks",
                "home_tasks_today_api": "/api/home/tasks/today",
                "home_tasks_complete_api": "/api/home/tasks/{task_id}/complete",
                "open_loops_api": "/api/open-loops",
                "open_loops_action_api": "/api/open-loops/action",
                "approvals_api": "/api/approvals",
                "approvals_action_api": "/api/approvals/{request_id}/approve",
                "agent_work_api": "/api/agent-work",
                "agent_work_proposed_api": "/api/agent-work/proposed",
                "agent_work_approve_api": "/api/agent-work/approve/{work_id}",
                "workshop_projects_api": "/api/workshop/projects",
                "workshop_jobs_api": "/api/workshop/jobs",
                "workshop_materials_api": "/api/workshop/materials",
                "workshop_status_api": "/api/workshop/status",
                "activity_api": "/api/activity/operator-action",
            },
        }
        if not payload["available"]:
            payload["status"] = "Wired"
            payload["summary"] = "Workshop routes are live, but the runtime could not hydrate meaningful task, project, or job data."
        return payload

    @app.get("/api/intel/module")
    async def api_intel_module() -> JSONResponse:
        return _json(await _build_intel_module_payload())

    @app.get("/api/agents/{agent_id}")
    async def api_task_agent(agent_id: str) -> JSONResponse:
        profile = await asyncio.to_thread(runtime.task_agent_profile, agent_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Agent not found.")
        return _json(profile)

    @app.post("/api/agents/{agent_id}/promote")
    async def api_promote_task_agent(agent_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            result = await asyncio.to_thread(
                runtime.promote_task_agent,
                agent_id,
                role_name=str(payload.get("role_name", "")).strip(),
                policy_assignment=str(payload.get("policy_assignment", "")).strip(),
                memory_boundary=str(payload.get("memory_boundary", "")).strip(),
                force=bool(payload.get("force", False)),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/agents/{agent_id}/retire")
    async def api_retire_task_agent(agent_id: str) -> JSONResponse:
        try:
            result = await asyncio.to_thread(runtime.retire_task_agent, agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/agents/{agent_id}/assignment")
    async def api_update_task_agent_assignment(agent_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            result = await asyncio.to_thread(
                runtime.update_task_agent_assignment,
                agent_id,
                mission_id=str(payload.get("mission_id", "")).strip(),
                mission_roles=[str(item).strip() for item in list(payload.get("mission_roles") or []) if str(item).strip()],
                policy_assignment=str(payload.get("policy_assignment", "")).strip(),
                purpose=str(payload.get("purpose", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/shell-state")
    async def api_shell_state(request: Request, actor: str = "Chris", device_id: str = "") -> JSONResponse:
        return _json(
            await asyncio.to_thread(
                runtime.shell_state_snapshot,
                actor,
                device_id=device_id,
                current_host=request.headers.get("host", ""),
                current_origin=str(request.base_url).rstrip("/"),
            )
        )

    @app.get("/api/chat-state")
    async def api_chat_state(actor: str = "Chris", conversation_id: str = "", room: str = "office") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.chat_state_snapshot, actor, conversation_id, room))

    @app.get("/api/conversations/{conversation_id}")
    async def api_conversation(conversation_id: str, limit: int = 24) -> JSONResponse:
        snapshot = await asyncio.to_thread(runtime.conversation_snapshot, conversation_id, limit)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return _json(snapshot)

    @app.post("/api/chat-uploads")
    async def api_chat_uploads(
        actor: str = Form("Chris"),
        room: str = Form("office"),
        conversation_id: str = Form(""),
        files: list[UploadFile] = File(...),
    ) -> JSONResponse:
        if not files:
            raise HTTPException(status_code=400, detail="No files were uploaded.")
        staged: list[dict[str, Any]] = []
        upload_batch_dir = uploads_root / (conversation_id.strip() or f"staging-{secrets.token_hex(6)}")
        upload_batch_dir.mkdir(parents=True, exist_ok=True)
        for incoming in files[:8]:
            original_name = str(incoming.filename or "").strip()
            if not original_name:
                continue
            suffix = Path(original_name).suffix.lower()
            content_type = str(incoming.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream")
            safe_name = _safe_chat_filename(original_name)
            stored_name = f"{secrets.token_hex(6)}-{safe_name}"
            destination = upload_batch_dir / stored_name
            size_bytes = 0
            try:
                with destination.open("wb") as handle:
                    while True:
                        chunk = await incoming.read(1024 * 1024)
                        if not chunk:
                            break
                        size_bytes += len(chunk)
                        if size_bytes > 25 * 1024 * 1024:
                            raise HTTPException(status_code=413, detail=f"{original_name} exceeds the 25 MB upload limit.")
                        handle.write(chunk)
            finally:
                await incoming.close()
            excerpt = _upload_excerpt(destination, content_type, suffix)
            staged.append(
                {
                    "attachment_id": stored_name,
                    "filename": original_name,
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                    "suffix": suffix,
                    "stored_path": str(destination),
                    "excerpt": excerpt,
                    "actor": actor,
                    "room": room,
                }
            )
        if not staged:
            raise HTTPException(status_code=400, detail="No usable files were uploaded.")
        return _json({"attachments": staged})

    @app.get("/api/proactive-state")
    async def api_proactive_state(actor: str = "Chris", channel: str = "") -> JSONResponse:
        payload = await asyncio.to_thread(runtime.proactive_state_snapshot, actor)
        requested_channel = str(channel).strip().lower()
        if requested_channel and requested_channel in payload.get("clients", {}):
            payload = {
                **payload,
                "requested_channel": requested_channel,
                "client": dict((payload.get("clients") or {}).get(requested_channel) or {}),
            }
        return _json(payload)

    @app.get("/api/assistant-core/tick")
    async def api_assistant_core_tick(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.assistant_core_tick, actor))

    @app.get("/api/assistant-core/notifications")
    async def api_assistant_core_notifications(actor: str = "Chris", unread_only: bool = False, limit: int = 12) -> JSONResponse:
        return _json(runtime.assistant_notifications(actor, limit=limit, unread_only=unread_only))

    @app.get("/api/assistant-core/browser-alerts")
    async def api_assistant_core_browser_alerts(actor: str = "Chris", device_id: str = "", limit: int = 3) -> JSONResponse:
        return _json(runtime.assistant_browser_alerts(actor, device_id=device_id, limit=limit))

    @app.post("/api/assistant-core/notifications/{notification_id}")
    async def api_assistant_core_notification_action(notification_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        status = str(payload.get("status", "read"))
        device_id = str(payload.get("device_id", ""))
        try:
            result = runtime.mark_assistant_notification(actor, notification_id, status, device_id=device_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("assistant-notifications.updated")
        return _json(result)

    @app.post("/api/assistant-core/notifications/{notification_id}/delivered")
    async def api_assistant_core_notification_delivered(notification_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        device_id = str(payload.get("device_id", ""))
        try:
            result = runtime.mark_assistant_notification_delivered(actor, notification_id, device_id=device_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("assistant-notifications.delivered")
        return _json(result)

    @app.post("/api/assistant-core/background-run")
    async def api_assistant_core_background_run(payload: dict[str, Any]) -> JSONResponse:
        actors = payload.get("actors")
        actor_list = [str(item) for item in actors] if isinstance(actors, list) else None
        attempts = 2
        delay_seconds = 0.4
        result = None
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = await asyncio.to_thread(runtime.background_autonomy_run, actor_list)
                if isinstance(result, dict):
                    result.setdefault("retry", {"attempts": attempt, "succeeded_after_retry": attempt > 1})
                break
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    raise
                await asyncio.sleep(delay_seconds * attempt)
        if result is None and last_error is not None:
            raise last_error
        await _broadcast_dashboard("assistant-background.updated", include_dashboard=False)
        return _json(result)

    @app.get("/api/briefing")
    async def api_briefing(actor: str = "Chris") -> JSONResponse:
        from .rss_briefing import fetch_briefing_context

        # Fetch live RSS context in a background thread (non-blocking, 8s max)
        rss: dict = {}
        try:
            rss = await asyncio.wait_for(
                asyncio.to_thread(fetch_briefing_context),
                timeout=8.0,
            )
        except Exception:
            pass  # fall back to LLM-only brief

        # Build base briefing (morning_brief returns a plain string)
        briefing: str = runtime.morning_brief(actor)

        # Prepend live news context when RSS data is available
        if rss.get("total_articles", 0) > 0:
            parts: list[str] = ["## Live News Context"]
            if rss.get("world_text"):
                parts.append(rss["world_text"])
            if rss.get("finance_text"):
                parts.append(rss["finance_text"])
            news_prefix = "\n\n".join(parts)
            briefing = news_prefix + "\n\n---\n\n" + briefing

        return _json(
            {
                "actor": actor,
                "briefing": briefing,
                "rss_articles": rss.get("total_articles", 0),
                "rss_sources": rss.get("sources_hit", []),
                "live_news": rss.get("total_articles", 0) > 0,
            }
        )

    @app.get("/api/news")
    async def api_news(force: bool = False) -> JSONResponse:
        from datetime import datetime, timezone
        from .rss_briefing import fetch_finance_news, fetch_world_news

        try:
            world, finance = await asyncio.gather(
                asyncio.to_thread(fetch_world_news, 12),
                asyncio.to_thread(fetch_finance_news, 12),
            )
            world = list(world or [])
            finance = list(finance or [])
            sources_hit = sorted(
                {
                    str(item.get("source", "")).strip()
                    for item in [*world, *finance]
                    if str(item.get("source", "")).strip()
                }
            )
            return _json(
                {
                    "world": world,
                    "finance": finance,
                    "total": len(world) + len(finance),
                    "sources_hit": sources_hit,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "live": bool(world or finance),
                    "forced": bool(force),
                }
            )
        except Exception as exc:
            return _json(
                {
                    "world": [],
                    "finance": [],
                    "total": 0,
                    "sources_hit": [],
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "live": False,
                    "forced": bool(force),
                    "error": str(exc),
                }
            )

    def _news_keyword_bucket(text: str) -> str:
        lowered = str(text or "").lower()
        if re.search(r"\b(ai|chip|technology|policy|regulation|software|cyber|data)\b", lowered):
            return "Technology"
        if re.search(r"\b(market|fed|stocks|rates|econom|tariff|inflation|trade|earnings)\b", lowered):
            return "Economy"
        if re.search(r"\b(war|attack|defense|conflict|security|crisis|election|government|diplom)\b", lowered):
            return "World"
        if re.search(r"\b(health|medical|research|disease|hospital|wellness)\b", lowered):
            return "Health"
        if re.search(r"\b(climate|storm|weather|energy|oil|gas|power)\b", lowered):
            return "Environment"
        if re.search(r"\b(media|creator|publish|audience|storytelling|content)\b", lowered):
            return "Publishing"
        return "General"

    def _news_source_quality(source: str) -> int:
        source_map = {
            "BBC": 91,
            "NYT": 90,
            "ALJAZEERA": 86,
            "AP": 92,
            "CNBC": 84,
            "MARKETWATCH": 82,
            "BLOOMBERG": 91,
            "JARVIS": 75,
        }
        return int(source_map.get(str(source or "").strip().upper(), 78))

    def _news_sentiment_score(articles: list[dict[str, Any]]) -> float:
        if not articles:
            return 0.0
        positive_re = re.compile(r"\b(gain|growth|breakthrough|recovery|win|opportunity|upside|progress)\b", re.IGNORECASE)
        negative_re = re.compile(r"\b(war|risk|slump|drop|decline|attack|crisis|strike|loss)\b", re.IGNORECASE)
        score = 0
        for item in articles:
            text = f"{item.get('title', '')} {item.get('summary', '')}"
            if positive_re.search(text):
                score += 1
            if negative_re.search(text):
                score -= 1
        return round(score / max(1, len(articles)), 2)

    async def _build_news_module_payload(actor_name: str = "Chris", force: bool = False) -> dict[str, Any]:
        from datetime import datetime, timezone
        from .rss_briefing import fetch_finance_news, fetch_world_news

        generated_at = datetime.now(timezone.utc).isoformat()
        availability_notes: list[str] = []
        errors: list[str] = []

        try:
            world, finance = await asyncio.gather(
                asyncio.to_thread(fetch_world_news, 12),
                asyncio.to_thread(fetch_finance_news, 12),
            )
        except Exception as exc:
            world, finance = [], []
            errors.append(f"Live news feeds could not be hydrated: {exc}")

        world_rows = [dict(item or {}) for item in list(world or [])]
        finance_rows = [dict(item or {}) for item in list(finance or [])]
        articles: list[dict[str, Any]] = []
        for item in world_rows:
            row = dict(item)
            row["_cat"] = "world"
            articles.append(row)
        for item in finance_rows:
            row = dict(item)
            row["_cat"] = "finance"
            articles.append(row)

        sources_hit = sorted(
            {
                str(item.get("source", "")).strip()
                for item in articles
                if str(item.get("source", "")).strip()
            }
        )

        storm_weather = {}
        storm_lookup = getattr(runtime, "storm_weather_snapshot", None)
        if callable(storm_lookup):
            try:
                storm_weather = storm_lookup(force=force)
            except Exception as exc:
                errors.append(f"Weather context could not be hydrated: {exc}")
        else:
            availability_notes.append("Storm weather context is not exposed in this runtime.")

        weather_current = storm_weather.get("current") if isinstance(storm_weather, dict) and isinstance(storm_weather.get("current"), dict) else {}
        weather_alerts = storm_weather.get("alerts") if isinstance(storm_weather, dict) and isinstance(storm_weather.get("alerts"), list) else []
        weather_summary = {
            "temp": f"{weather_current.get('temperature_f')}°F" if weather_current and weather_current.get("temperature_f") is not None else "—",
            "condition": str(weather_current.get("condition") or storm_weather.get("summary") or "Local conditions unavailable").strip(),
            "high": f"{weather_current.get('high_f')}°" if weather_current and weather_current.get("high_f") is not None else "—",
            "low": f"{weather_current.get('low_f')}°" if weather_current and weather_current.get("low_f") is not None else "—",
            "humidity": f"{weather_current.get('humidity')}%" if weather_current and weather_current.get("humidity") is not None else "—",
            "wind": str(weather_current.get("wind") or "—").strip(),
            "alert": weather_alerts[0] if isinstance(weather_alerts, list) and weather_alerts else None,
        }

        featured = articles[0] if articles else {
            "source": "JARVIS",
            "title": "No live headlines are available right now.",
            "summary": errors[0] if errors else "The live news feeds did not return any items.",
            "link": "",
            "_cat": "world",
        }

        top_articles = articles[:12]
        tone_score = _news_sentiment_score(top_articles)
        positive = sum(
            1 for item in top_articles
            if re.search(r"\b(gain|growth|breakthrough|recovery|win|opportunity|upside|progress)\b", f"{item.get('title', '')} {item.get('summary', '')}", re.IGNORECASE)
        )
        negative = sum(
            1 for item in top_articles
            if re.search(r"\b(war|risk|slump|drop|decline|attack|crisis|strike|loss)\b", f"{item.get('title', '')} {item.get('summary', '')}", re.IGNORECASE)
        )
        total_top = max(1, len(top_articles))
        positive_pct = round((positive / total_top) * 100)
        negative_pct = round((negative / total_top) * 100)
        neutral_pct = max(0, 100 - positive_pct - negative_pct)
        tone_label = "Slightly Negative" if tone_score < -0.10 else "Constructive" if tone_score > 0.12 else "Mixed"

        category_counter: dict[str, int] = {}
        for item in top_articles:
            bucket = _news_keyword_bucket(f"{item.get('title', '')} {item.get('summary', '')}")
            category_counter[bucket] = category_counter.get(bucket, 0) + 1
        category_rows = [
            {"title": name, "value": count, "detail": f"{count} live stor{'y' if count == 1 else 'ies'} in the current feed."}
            for name, count in sorted(category_counter.items(), key=lambda item: (-item[1], item[0]))
        ]

        source_counter: dict[str, int] = {}
        for item in top_articles:
            source = str(item.get("source") or "Unknown").strip() or "Unknown"
            source_counter[source] = source_counter.get(source, 0) + 1
        source_rows = [
            {
                "source": source,
                "score": _news_source_quality(source),
                "count": count,
                "detail": f"{count} live stor{'y' if count == 1 else 'ies'} from {source}.",
            }
            for source, count in sorted(source_counter.items(), key=lambda item: (-_news_source_quality(item[0]), -item[1], item[0]))
        ]

        quality_score = round(
            sum(_news_source_quality(source) * count for source, count in source_counter.items()) / max(1, sum(source_counter.values()))
        ) if source_counter else 0

        watch_themes = sorted(category_counter.items(), key=lambda item: (-item[1], item[0]))[:5]
        watchlist_rows = [
            {
                "title": theme,
                "count": count,
                "tone": "high" if idx < 2 else "medium" if count > 1 else "low",
                "detail": "Derived from the current live feed because a persisted News watchlist backend is not exposed yet.",
            }
            for idx, (theme, count) in enumerate(watch_themes)
        ]
        if not watchlist_rows:
            watchlist_rows = [
                {
                    "title": "No active live themes",
                    "count": 0,
                    "tone": "low",
                    "detail": "Persisted News watchlist storage is not exposed yet in this runtime.",
                }
            ]

        insights = []
        if featured.get("summary"):
            insights.append({
                "title": "Top Story",
                "detail": str(featured.get("summary") or "").strip()[:220] or "Open the top story for full context.",
            })
        economy_story = next(
            (item for item in top_articles if _news_keyword_bucket(f"{item.get('title', '')} {item.get('summary', '')}") == "Economy"),
            None,
        )
        if economy_story:
            insights.append({
                "title": "Your Business",
                "detail": str(economy_story.get("title") or economy_story.get("summary") or "Economic pressure is rising in the current feed.").strip(),
            })
        if weather_summary["alert"]:
            insights.append({
                "title": "Your Calendar",
                "detail": "Weather posture is active, so route and schedule confidence deserve an extra check today.",
            })
        elif weather_summary["condition"]:
            insights.append({
                "title": "Local Conditions",
                "detail": weather_summary["condition"],
            })
        if not insights:
            insights.append({
                "title": "No personalized insight yet",
                "detail": "Live news loaded, but there is not enough signal to build a stronger personalized brief.",
            })

        briefing_cards = [
            {"title": "What Happened", "copy": str(featured.get("title") or "No top story loaded yet.").strip() or "No top story loaded yet."},
            {"title": "Why It Matters", "copy": str(featured.get("summary") or "The main item will be summarized here once the feed loads.").strip() or "The main item will be summarized here once the feed loads."},
            {"title": "What To Watch", "copy": f"{watch_themes[0][0]} pressure is currently strongest in the live feed." if watch_themes else "Watch the next world and market refresh."},
            {"title": "What You Can Do", "copy": "Check schedule and travel plans against the active weather watch." if weather_summary["alert"] else "Stay on the top themes only and avoid noisy feed hopping."},
        ]

        weather_rows = [
            {"title": "Now", "detail": f"{weather_summary['temp']} · {weather_summary['condition']}"},
            {"title": "High / Low", "detail": f"{weather_summary['high']} · {weather_summary['low']}"},
            {"title": "Humidity / Wind", "detail": f"{weather_summary['humidity']} · {weather_summary['wind']}"},
            {"title": "Weather Watch", "detail": str((weather_summary["alert"] or {}).get("headline") or "No severe watch active").strip() or "No severe watch active"},
        ]

        deep_dive_rows = [
            {
                "title": str(item.get("title") or "(No title)").strip() or "(No title)",
                "summary": str(item.get("summary") or "Open the source for the full story.").strip() or "Open the source for the full story.",
                "source": str(item.get("source") or "Wire").strip() or "Wire",
                "category": _news_keyword_bucket(f"{item.get('title', '')} {item.get('summary', '')}"),
                "link": str(item.get("link") or "").strip(),
            }
            for item in top_articles[:4]
        ]

        recent_activity = _module_recent_activity(route="/news-center", domain="news", limit=8)
        if not recent_activity:
            recent_activity = _module_recent_activity(route="/command-center", domain="news", limit=6)

        quick_actions = [
            {
                "id": "refresh-news",
                "title": "Refresh Feed",
                "detail": "Reload the live RSS news and local weather context.",
                "available": True,
            },
            {
                "id": "open-briefing",
                "title": "Read Full Briefing",
                "detail": "Open the full daily briefing with live news context.",
                "route": "/briefing-center",
                "available": True,
            },
            {
                "id": "save-top-story",
                "title": "Save Top Story",
                "detail": "Record the top story for later review in shared continuity.",
                "available": bool(str(featured.get("title") or "").strip()),
                "article_title": str(featured.get("title") or "").strip(),
                "article_link": str(featured.get("link") or "").strip(),
            },
            {
                "id": "share-brief",
                "title": "Share Brief",
                "detail": "Stage a handoff into Email or Command without pretending the brief was already sent.",
                "route": "/email-center",
                "available": True,
            },
            {
                "id": "set-alert",
                "title": "Set Alert",
                "detail": "Persist a watch preference once a real News alert backend exists; for now it records continuity honestly.",
                "available": True,
            },
            {
                "id": "open-weather",
                "title": "Open Weather",
                "detail": "Jump into the live local weather surface.",
                "available": True,
            },
        ]

        trusted_actions = [
            {
                "id": "refresh-news",
                "title": "Refresh News",
                "action_type": "refresh",
                "note": "Refreshes live RSS headlines and local weather context.",
                "available": True,
            },
            {
                "id": "save-top-story",
                "title": "Save Top Story",
                "action_type": "save-article",
                "note": "Records the current top story into shared operator continuity for follow-up.",
                "available": bool(str(featured.get("title") or "").strip()),
                "unavailable_reason": "No top story is currently loaded." if not str(featured.get("title") or "").strip() else "",
                "article_title": str(featured.get("title") or "").strip(),
                "article_link": str(featured.get("link") or "").strip(),
            },
            {
                "id": "mark-top-reviewed",
                "title": "Mark Top Story Reviewed",
                "action_type": "mark-reviewed",
                "note": "Acknowledges the top story in shared continuity without pretending there is a durable News read-state backend.",
                "available": bool(str(featured.get("title") or "").strip()),
                "unavailable_reason": "No top story is currently loaded." if not str(featured.get("title") or "").strip() else "",
                "article_title": str(featured.get("title") or "").strip(),
            },
        ]

        if not watch_themes:
            availability_notes.append("Persisted News watchlist storage is not exposed yet, so watch themes are derived from the current live feed.")
        if not articles:
            availability_notes.append("Live RSS sources returned no articles in this runtime, so News is showing an honest empty state.")
        if not weather_summary["alert"] and weather_summary["condition"] == "Local conditions unavailable":
            availability_notes.append("Local weather context is partial or unavailable in this runtime.")
        if errors and not availability_notes:
            availability_notes.extend(errors[:4])

        top_story_list = [
            {
                "title": str(item.get("title") or "(No title)").strip() or "(No title)",
                "source": str(item.get("source") or "Wire").strip() or "Wire",
                "category": _news_keyword_bucket(f"{item.get('title', '')} {item.get('summary', '')}"),
                "link": str(item.get("link") or "").strip(),
            }
            for item in top_articles[1:6]
        ]

        balance_label = "Well Balanced" if len(source_counter) >= 4 else "Needs More Balance"
        balance_note = "On target" if len(source_counter) >= 4 else "Expand sources"

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": f"News loaded {len(top_articles)} live story slot(s), {len(source_rows)} source row(s), {len(watchlist_rows)} active theme row(s), and {len(recent_activity)} continuity event(s).",
            "what_became_real": "News now hydrates from live RSS world and finance feeds, local weather context, and shared operator continuity instead of browser-generated news math and dead action toasts.",
            "remains_partial": "Persisted watchlists, article save state, alerts, and richer per-source preference controls still need dedicated backend contracts.",
            "runtime_note": "News is live and connected.",
            "availability_notes": availability_notes[:10],
            "counts": {
                "top_stories": len(top_articles),
                "breaking": sum(1 for item in top_articles if re.search(r"\b(breaking|urgent|alert|attack|strike|war|crisis)\b", f"{item.get('title', '')} {item.get('summary', '')}", re.IGNORECASE)),
                "watching": len(watchlist_rows),
                "sentiment_score": tone_score,
                "quality_score": quality_score,
                "source_count": len(source_rows),
                "recent_activity": len(recent_activity),
            },
            "balance": {
                "label": balance_label,
                "note": balance_note,
            },
            "sentiment": {
                "score": tone_score,
                "label": tone_label,
                "positive_pct": positive_pct,
                "neutral_pct": neutral_pct,
                "negative_pct": negative_pct,
            },
            "featured_article": featured,
            "top_story_list": top_story_list,
            "briefing_cards": briefing_cards,
            "watchlist_rows": watchlist_rows,
            "category_rows": category_rows[:8],
            "insight_rows": insights[:6],
            "source_rows": source_rows[:6],
            "weather_rows": weather_rows,
            "deep_dive_rows": deep_dive_rows,
            "quick_actions": quick_actions,
            "trusted_actions": trusted_actions,
            "recent_activity": recent_activity,
            "news_payload": {
                "world": world_rows,
                "finance": finance_rows,
                "sources_hit": sources_hit,
                "fetched_at": generated_at,
                "live": bool(articles),
                "forced": bool(force),
            },
            "weather_payload": storm_weather,
            "proof_paths": {
                "module_route": "/news-center",
                "module_api": "/api/news/module",
                "news_api": "/api/news",
                "weather_api": "/api/storm-weather",
                "briefing_route": "/briefing-center",
                "email_route": "/email-center",
                "activity_api": "/api/activity/operator-action",
                "action_api": "/api/news/module/action",
            },
            "errors": errors,
        }

        if not articles and errors:
            payload["available"] = False
            payload["status"] = "Wired"
            payload["runtime_note"] = "News is wired, but live RSS sources did not hydrate enough signal in this runtime."
        elif not articles:
            payload["runtime_note"] = "News is live, but the RSS sources returned no current headlines in this runtime."
        elif errors:
            payload["runtime_note"] = "News is live, but some source or weather context is partially unavailable."
        return payload

    async def _build_social_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        from collections import Counter
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        availability_notes: list[str] = []
        errors: list[str] = []

        def _platform_label(platform: str) -> str:
            key = str(platform or "").strip().lower()
            labels = {
                "linkedin": "LinkedIn",
                "instagram": "Instagram",
                "facebook": "Facebook",
                "twitter": "X (Twitter)",
                "x": "X (Twitter)",
                "tiktok": "TikTok",
                "youtube": "YouTube",
            }
            return labels.get(key, key.title() if key else "Platform")

        def _human_number(value: Any) -> str:
            try:
                num = float(value or 0)
            except (TypeError, ValueError):
                return "—"
            if abs(num) >= 1_000_000:
                return f"{num / 1_000_000:.1f}M"
            if abs(num) >= 1_000:
                return f"{num / 1_000:.1f}K"
            if num.is_integer():
                return str(int(num))
            return f"{num:.1f}"

        def _safe_iso(value: str) -> str:
            return str(value or "").strip()

        def _parse_iso(value: str):
            if not value:
                return None
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return None

        def _format_stamp(value: str, *, with_time: bool = False) -> str:
            parsed = _parse_iso(value)
            if parsed is None:
                return str(value or "Unscheduled").strip() or "Unscheduled"
            fmt = {"month": "short", "day": "numeric"}
            if with_time:
                fmt.update({"hour": "numeric", "minute": "2-digit"})
            return parsed.astimezone().strftime("%b %-d, %-I:%M %p" if with_time else "%b %-d")

        def _normalize_social_post(item: Any, source: str) -> dict[str, Any]:
            raw = item.to_dict() if hasattr(item, "to_dict") else dict(item or {})
            post_id = str(raw.get("post_id") or raw.get("id") or "").strip()
            platform = str(raw.get("platform") or "").strip().lower()
            status = str(raw.get("status") or "").strip().lower() or "draft"
            scheduled_at = _safe_iso(str(raw.get("scheduled_at") or ""))
            posted_at = _safe_iso(str(raw.get("posted_at") or ""))
            caption = str(raw.get("caption") or raw.get("content") or "").strip()
            performance = dict(raw.get("performance") or raw.get("engagement") or {})
            reach = int(performance.get("reach") or performance.get("views") or 0)
            likes = int(performance.get("likes") or 0)
            comments = int(performance.get("comments") or 0)
            shares = int(performance.get("shares") or 0)
            clicks = int(performance.get("clicks") or 0)
            engagement_score = likes + (comments * 2) + (shares * 3) + clicks + int(performance.get("views") or 0)
            return {
                "post_id": post_id,
                "project_id": str(raw.get("project_id") or "").strip(),
                "platform": platform,
                "platform_label": _platform_label(platform),
                "status": status,
                "scheduled_at": scheduled_at,
                "posted_at": posted_at,
                "caption": caption,
                "content_type": str(raw.get("content_type") or "text").strip() or "text",
                "source": source,
                "reach": reach,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "clicks": clicks,
                "engagement_score": engagement_score,
            }

        engine = _get_social_engine()
        publishing = None
        try:
            publishing = _publishing_or_503()
        except HTTPException as exc:
            errors.append(f"publishing: {exc.detail}")
            availability_notes.append(f"Publishing suite is not fully available in this runtime: {exc.detail}")

        publishing_projects: list[Any] = []
        publishing_posts: list[Any] = []
        publishing_metrics: dict[str, Any] = {}
        content_performance: dict[str, Any] = {}

        if publishing is not None:
            try:
                publishing_projects = list(await asyncio.to_thread(publishing._store.list_projects))
            except Exception as exc:
                errors.append(f"publishing_projects: {exc}")
                availability_notes.append(f"Publishing projects could not be loaded: {exc}")
            try:
                publishing_posts = list(await asyncio.to_thread(publishing._store.list_posts, None))
            except Exception as exc:
                errors.append(f"publishing_posts: {exc}")
                availability_notes.append(f"Publishing social drafts could not be loaded: {exc}")
            try:
                publishing_metrics = dict(await asyncio.to_thread(publishing.sage.get_publishing_metrics) or {})
            except Exception as exc:
                errors.append(f"publishing_metrics: {exc}")
                availability_notes.append(f"Publishing metrics could not be loaded: {exc}")
            try:
                content_performance = dict(await asyncio.to_thread(publishing.sage.get_content_performance) or {})
            except Exception as exc:
                errors.append(f"content_performance: {exc}")
                availability_notes.append(f"Publishing performance metrics could not be loaded: {exc}")

        engine_posts: list[Any] = []
        schedule_rows_raw: list[Any] = []
        engagement_rows_raw: list[Any] = []
        if engine is None:
            availability_notes.append("Social engine is not initialised in this runtime, so approvals, execution, and engagement snapshots may be partial.")
        else:
            try:
                engine_posts = list(await asyncio.to_thread(engine.store.list_posts, None, None))
            except Exception as exc:
                errors.append(f"engine_posts: {exc}")
                availability_notes.append(f"Social engine posts could not be loaded: {exc}")
            try:
                schedule_rows_raw = list(await asyncio.to_thread(engine.store.list_schedules, None))
            except Exception as exc:
                errors.append(f"schedules: {exc}")
                availability_notes.append(f"Social schedules could not be loaded: {exc}")
            try:
                engagement_rows_raw = list(await asyncio.to_thread(engine.store.list_engagement, None, None))
            except Exception as exc:
                errors.append(f"engagement: {exc}")
                availability_notes.append(f"Engagement snapshots could not be loaded: {exc}")

        project_titles = {
            str(getattr(project, "project_id", "") or "").strip(): str(getattr(project, "title", "") or "").strip()
            for project in publishing_projects
            if str(getattr(project, "project_id", "") or "").strip()
        }

        normalized_posts: list[dict[str, Any]] = []
        seen_post_ids: set[str] = set()
        for item in engine_posts:
            post = _normalize_social_post(item, "social_engine")
            if post["post_id"] and post["post_id"] in seen_post_ids:
                continue
            if post["post_id"]:
                seen_post_ids.add(post["post_id"])
            normalized_posts.append(post)
        for item in publishing_posts:
            post = _normalize_social_post(item, "publishing")
            if post["post_id"] and post["post_id"] in seen_post_ids:
                continue
            if post["post_id"]:
                seen_post_ids.add(post["post_id"])
            normalized_posts.append(post)

        project_post_counts = Counter(post["project_id"] for post in normalized_posts if post["project_id"])
        for schedule in schedule_rows_raw:
            project_id = str(getattr(schedule, "project_id", "") or "").strip()
            if project_id:
                project_post_counts[project_id] += int(getattr(schedule, "total_posts", 0) or len(list(getattr(schedule, "posts", []) or [])))
        default_project_id = project_post_counts.most_common(1)[0][0] if project_post_counts else ""
        if not default_project_id and publishing_projects:
            default_project_id = str(getattr(publishing_projects[0], "project_id", "") or "").strip()

        project_analytics: dict[str, Any] = {}
        adaptation_excerpt: list[str] = []
        if engine is not None and default_project_id:
            try:
                project_analytics = dict(await asyncio.to_thread(engine.sage.analyze_performance, default_project_id) or {})
            except Exception as exc:
                errors.append(f"social_analytics: {exc}")
                availability_notes.append(f"Project-level social analytics could not be loaded: {exc}")
            try:
                adaptation_report = str(await asyncio.to_thread(engine.sage.generate_adaptation_report, default_project_id) or "").strip()
                adaptation_excerpt = [line.strip("- ").strip() for line in adaptation_report.splitlines() if line.strip().startswith("-")][:4]
            except Exception:
                adaptation_excerpt = []

        posted_posts = [post for post in normalized_posts if post["status"] == "posted"]
        scheduled_posts = [post for post in normalized_posts if post["status"] in {"scheduled", "approved"} and post["scheduled_at"]]
        pending_posts = [post for post in normalized_posts if post["status"] in {"pending_approval", "pending-review"}]
        draft_posts = [post for post in normalized_posts if post["status"] in {"draft", "idea", "outline", "editing"}]
        failed_posts = [post for post in normalized_posts if post["status"] in {"failed", "blocked"}]

        platform_breakdown = dict(content_performance.get("platform_breakdown") or {})
        platform_keys = sorted(
            {
                str(post["platform"]).strip().lower()
                for post in normalized_posts
                if str(post["platform"]).strip()
            }
            | {str(getattr(snap, "platform", "") or "").strip().lower() for snap in engagement_rows_raw if str(getattr(snap, "platform", "") or "").strip()}
            | {str(key).strip().lower() for key in platform_breakdown.keys() if str(key).strip()}
        )

        latest_snapshot_by_platform: dict[str, Any] = {}
        follower_delta = 0
        impressions_total = 0
        reach_total = 0
        for platform in platform_keys:
            snaps = [
                snap for snap in engagement_rows_raw
                if str(getattr(snap, "platform", "") or "").strip().lower() == platform
            ]
            snaps.sort(key=lambda snap: str(getattr(snap, "captured_at", "") or ""))
            if snaps:
                latest_snapshot_by_platform[platform] = snaps[-1]
                impressions_total += int(getattr(snaps[-1], "total_reach", 0) or 0)
                reach_total += int(getattr(snaps[-1], "total_reach", 0) or 0)
                if len(snaps) >= 2:
                    follower_delta += int(getattr(snaps[-1], "followers", 0) or 0) - int(getattr(snaps[0], "followers", 0) or 0)

        if impressions_total <= 0:
            impressions_total = sum(int((platform_breakdown.get(platform) or {}).get("total_reach") or 0) for platform in platform_keys)
            reach_total = impressions_total

        total_engagement = sum(post["engagement_score"] for post in posted_posts)
        if total_engagement <= 0:
            total_engagement = sum(int(getattr(snap, "total_engagement", 0) or 0) for snap in engagement_rows_raw)

        top_performers = list(content_performance.get("top_performers") or [])
        if top_performers:
            performance_rows = [
                {
                    "title": str(item.get("content_preview") or "Top performer").strip() or "Top performer",
                    "subtitle": _platform_label(str(item.get("platform") or "")),
                    "score": _human_number(item.get("engagement_score") or 0),
                    "reach": f"{item.get('reach_rate', 0)}% engagement",
                }
                for item in top_performers[:5]
            ]
        else:
            performance_rows = [
                {
                    "title": post["caption"][:72] or "Posted social content",
                    "subtitle": post["platform_label"],
                    "score": _human_number(post["engagement_score"]),
                    "reach": _human_number(post["reach"]) if post["reach"] else "Reach unavailable",
                }
                for post in sorted(posted_posts, key=lambda entry: entry["engagement_score"], reverse=True)[:5]
            ]

        accounts_rows = []
        audience_total = 0
        for platform in platform_keys:
            rows = [post for post in normalized_posts if post["platform"] == platform]
            posted_count = len([post for post in rows if post["status"] == "posted"])
            queued_count = len([post for post in rows if post["status"] in {"draft", "idea", "outline", "editing", "pending_approval", "approved", "scheduled"}])
            failed_count = len([post for post in rows if post["status"] in {"failed", "blocked"}])
            breakdown = dict(platform_breakdown.get(platform) or {})
            snap = latest_snapshot_by_platform.get(platform)
            followers = int(getattr(snap, "followers", 0) or 0) if snap is not None else 0
            audience_total += followers
            reach_value = int(getattr(snap, "total_reach", 0) or 0) if snap is not None else int(breakdown.get("total_reach") or 0)
            engagement_value = int(getattr(snap, "total_engagement", 0) or 0) if snap is not None else (
                int(breakdown.get("total_likes") or 0) + (int(breakdown.get("total_shares") or 0) * 2) + int(breakdown.get("total_clicks") or 0)
            )
            status = "Connected"
            tone = "healthy"
            if failed_count:
                status = "Watch"
                tone = "high"
            elif not rows and snap is None:
                status = "Not Connected"
                tone = "low"
            elif queued_count and not posted_count:
                status = "Queued"
                tone = "medium"
            accounts_rows.append(
                {
                    "platform": platform,
                    "label": _platform_label(platform),
                    "status": status,
                    "tone": tone,
                    "audience": followers,
                    "reach": reach_value,
                    "engagement": engagement_value,
                    "detail": f"{posted_count} posted · {queued_count} queued · {failed_count} failed",
                }
            )

        if audience_total <= 0:
            audience_total = sum(row["audience"] for row in accounts_rows if int(row.get("audience") or 0) > 0)

        scheduled_sorted = sorted(
            [post for post in normalized_posts if post["scheduled_at"]],
            key=lambda post: post["scheduled_at"] or "9999",
        )
        calendar_rows = [
            {
                "day": _format_stamp(post["scheduled_at"]),
                "label": post["platform_label"],
                "detail": post["caption"][:84] or "Scheduled social content",
                "status": post["status"],
            }
            for post in scheduled_sorted[:6]
        ]

        calendar_footer = [
            f"{len(scheduled_posts)} scheduled",
            f"{len(draft_posts)} drafts",
            f"{len(pending_posts)} waiting on approval",
            f"{max(0, len(scheduled_posts) - len(pending_posts))} ready to move",
        ]

        inbox_rows = [
            {
                "title": post["caption"][:84] or "Pending social post",
                "who": post["platform_label"],
                "when": _format_stamp(post["scheduled_at"], with_time=True) if post["scheduled_at"] else "Needs review",
                "tone": "medium",
            }
            for post in pending_posts[:5]
        ]
        if not inbox_rows:
            inbox_rows.append(
                {
                    "title": "No live mentions, comments, or DM inbox backend is exposed in this runtime yet.",
                    "who": "Boundary",
                    "when": "Unavailable",
                    "tone": "low",
                }
            )

        pipeline_rows = [
            {"label": "Ideas", "count": len([post for post in normalized_posts if post["status"] == "idea"]), "detail": "Early concepts retained in the live queue."},
            {"label": "Drafts", "count": len([post for post in normalized_posts if post["status"] in {"draft", "outline", "editing"}]), "detail": "Captions and assets still being shaped."},
            {"label": "Review", "count": len(pending_posts), "detail": "Posts waiting on approval before they can ship."},
            {"label": "Scheduled", "count": len(scheduled_posts), "detail": "Approved or scheduled content with a live publish time."},
            {"label": "Published", "count": len(posted_posts), "detail": "Content already executed through the live systems."},
        ]

        audience_rows = []
        audience_insights = []
        active_audience_rows = [row for row in accounts_rows if int(row.get("audience") or 0) > 0]
        if active_audience_rows:
            total_followers = sum(int(row["audience"]) for row in active_audience_rows) or 1
            for row in sorted(active_audience_rows, key=lambda item: int(item["audience"]), reverse=True)[:4]:
                share = round((int(row["audience"]) / total_followers) * 100)
                audience_rows.append({"label": row["label"], "value": _human_number(row["audience"]), "detail": row["detail"]})
                audience_insights.append(
                    {
                        "label": row["label"],
                        "pct": f"{share}%",
                        "detail": f"Follower share derived from the latest {row['label']} engagement snapshot.",
                    }
                )
        else:
            audience_rows.append({"label": "Audience snapshots", "value": "Unavailable", "detail": "Follower and reach snapshots have not been captured in this runtime yet."})
            audience_insights.append({"label": "Audience mix", "pct": "—", "detail": "A real audience distribution will appear after engagement snapshots are captured."})

        tag_counter: Counter[str] = Counter()
        for project in publishing_projects:
            for tag in list(getattr(project, "tags", []) or []):
                clean = str(tag or "").strip()
                if clean:
                    tag_counter[clean] += 1
        theme_rows = [
            {
                "label": tag,
                "share": f"{count} project{'s' if count != 1 else ''}",
                "lift": f"{round((count / max(len(publishing_projects), 1)) * 100)}%",
                "detail": "Theme share derived from live publishing project tags.",
            }
            for tag, count in tag_counter.most_common(5)
        ]
        if not theme_rows:
            theme_rows.append(
                {
                    "label": "Theme metadata unavailable",
                    "share": "—",
                    "lift": "—",
                    "detail": "Publishing projects do not currently expose enough real tag metadata to build a richer theme mix.",
                }
            )

        health_score = 0
        if normalized_posts or engagement_rows_raw or publishing_projects:
            health_score = max(
                0,
                min(
                    100,
                    82
                    + min(10, len(posted_posts))
                    - (len(pending_posts) * 4)
                    - (len(failed_posts) * 8)
                    + min(8, len(accounts_rows)),
                ),
            )
        health_label = "Unavailable"
        if health_score >= 85:
            health_label = "Healthy"
        elif health_score >= 65:
            health_label = "Stable"
        elif health_score > 0:
            health_label = "Watch"
        health_metrics = [
            {"label": "Queue Pressure", "value": f"{len(pending_posts)} waiting", "detail": "Posts pending approval right now."},
            {"label": "Execution Reliability", "value": f"{len(failed_posts)} failed", "detail": "Failed or blocked posts currently visible."},
            {"label": "Snapshot Coverage", "value": f"{len(engagement_rows_raw)} snapshot(s)", "detail": "Live engagement snapshots captured by the social engine."},
            {"label": "Projects in Motion", "value": f"{len(publishing_projects)} project(s)", "detail": "Publishing projects contributing signal to this social surface."},
            {"label": "Connected Platforms", "value": f"{len(accounts_rows)} lane(s)", "detail": "Platforms showing real queue or performance signal."},
            {"label": "Publish Ready", "value": f"{len(scheduled_posts)} ready", "detail": "Scheduled or approved posts that can execute through the live engine."},
        ]

        sentiment_rows = []
        sentiment_scores = [float(getattr(snap, "sentiment_score", 0.0) or 0.0) for snap in engagement_rows_raw]
        if sentiment_scores:
            avg_sentiment = round((sum(sentiment_scores) / max(len(sentiment_scores), 1)) * 100)
            trend = str(project_analytics.get("sentiment_trend") or "stable")
            sentiment_rows = [
                {"label": "Average Sentiment", "value": f"{avg_sentiment}%", "detail": "Derived from live social engagement snapshots.", "tone": "healthy" if avg_sentiment >= 70 else "medium" if avg_sentiment >= 45 else "high"},
                {"label": "Trend", "value": trend.title(), "detail": "Project-level sentiment direction from the active social analytics engine.", "tone": "healthy" if trend == "improving" else "medium" if trend == "stable" else "high"},
                {"label": "Snapshot Coverage", "value": str(len(sentiment_scores)), "detail": "Number of captured sentiment-bearing snapshots visible right now.", "tone": "info"},
            ]
        else:
            sentiment_rows = [
                {"label": "Sentiment snapshots", "value": "Unavailable", "detail": "No live sentiment snapshots are available in this runtime yet.", "tone": "low"}
            ]

        recommendation_rows = [
            {
                "title": str(text).strip(),
                "detail": "Recommended directly by the live social analytics engine.",
                "tone": "high" if idx == 0 else "medium" if idx == 1 else "low",
            }
            for idx, text in enumerate(list(project_analytics.get("recommended_adjustments") or [])[:5])
            if str(text).strip()
        ]
        if adaptation_excerpt:
            for text in adaptation_excerpt:
                if len(recommendation_rows) >= 5:
                    break
                recommendation_rows.append(
                    {
                        "title": text,
                        "detail": "Adaptation note surfaced from the live social report.",
                        "tone": "low",
                    }
                )
        if not recommendation_rows:
            recommendation_rows.append(
                {
                    "title": "Recommendations will deepen after more posted content and engagement snapshots accumulate.",
                    "detail": "The live social engine does not yet have enough signal for richer recommendations in this runtime.",
                    "tone": "low",
                }
            )

        security_rows = [
            {
                "label": "Live Platform Signal",
                "value": f"{len(accounts_rows)} lane(s)",
                "tone": "healthy" if accounts_rows else "low",
                "detail": "Platforms with visible queue, schedule, or engagement signal.",
            },
            {
                "label": "Approval Queue",
                "value": f"{len(pending_posts)} waiting",
                "tone": "medium" if pending_posts else "healthy",
                "detail": "Posts that still require review before execution.",
            },
            {
                "label": "Execution Engine",
                "value": "Available" if engine is not None else "Unavailable",
                "tone": "healthy" if engine is not None else "low",
                "detail": "Controls whether approved scheduled posts can execute through the live Social Engine.",
            },
            {
                "label": "Direct DM Inbox",
                "value": "Unavailable",
                "tone": "low",
                "detail": "A real mentions, comments, or DM ingestion backend is not exposed in this runtime yet.",
            },
            {
                "label": "Platform Auth Health",
                "value": "Partial",
                "tone": "medium",
                "detail": "Per-platform auth and 2FA posture are not separately exposed by backend contracts yet.",
            },
        ]

        summary_cards = [
            {"label": "Posts Published", "value": str(len(posted_posts))},
            {"label": "People Reached", "value": _human_number(reach_total) if reach_total else "Unavailable"},
            {"label": "Engagements", "value": _human_number(total_engagement) if total_engagement else "Unavailable"},
            {"label": "New Followers", "value": f"+{follower_delta}" if follower_delta else "Unavailable"},
            {"label": "Pending Review", "value": str(len(pending_posts))},
            {"label": "Time Saved", "value": "Unavailable"},
        ]

        footer_rows = [
            {"title": "Social Module", "copy": "The desktop now hydrates from one live social contract instead of client-side stitched math."},
            {"title": "Execution", "copy": f"{len(scheduled_posts)} scheduled and {len(pending_posts)} pending signal(s) are visible right now."},
            {"title": "Continuity", "copy": "Recent social operator actions stay linked to this surface for review and handoff."},
        ]
        if availability_notes:
            footer_rows.append({"title": "Availability", "copy": availability_notes[0]})

        recent_activity = _module_recent_activity(route="/social-center", domain="social", limit=8)
        if not recent_activity:
            recent_activity = _module_recent_activity(route="/publish", domain="social", limit=6)

        headline_stats = {
            "health": {"value": str(health_score) if health_score else "—", "sub": health_label},
            "engagement": {"value": _human_number(total_engagement) if total_engagement else "—", "sub": "Live engagement total" if total_engagement else "Unavailable"},
            "followers": {"value": f"+{follower_delta}" if follower_delta else "—", "sub": "Net snapshot delta" if follower_delta else "No live growth delta"},
            "impressions": {"value": _human_number(impressions_total) if impressions_total else "—", "sub": "Tracked reach" if impressions_total else "Unavailable"},
            "visits": {"value": "—", "sub": "No live visit feed"},
            "reach": {"value": _human_number(reach_total) if reach_total else "—", "sub": "Tracked audience reach" if reach_total else "Unavailable"},
            "time_saved": {"value": "—", "sub": "Unavailable"},
        }

        mini_stats = [
            {"label": "Reach", "value": _human_number(reach_total) if reach_total else "Unavailable"},
            {"label": "Engagement", "value": _human_number(total_engagement) if total_engagement else "Unavailable"},
            {"label": "Published", "value": str(len(posted_posts))},
            {"label": "Scheduled", "value": str(len(scheduled_posts))},
            {"label": "Projects", "value": str(len(publishing_projects) or int(publishing_metrics.get("total_projects") or 0))},
        ]

        sidebar_counts = {
            "overview": "Live",
            "inbox": str(len(inbox_rows)),
            "calendar": str(len(calendar_rows)),
            "workflow": f"{round((len(posted_posts) + len(scheduled_posts)) / max(len(normalized_posts), 1) * 100) if normalized_posts else 0}%",
            "accounts": str(len(accounts_rows)),
        }
        sidebar_status_rows = [
            {"label": "Accounts", "value": f"{len(accounts_rows)} visible"},
            {"label": "Scheduled", "value": str(len(scheduled_posts))},
            {"label": "Auto-Published", "value": str(len(posted_posts))},
            {"label": "Requires Review", "value": str(len(pending_posts))},
            {"label": "Last Refresh", "value": _format_stamp(generated_at, with_time=True)},
        ]

        trusted_actions = [
            {
                "id": "refresh-social",
                "title": "Refresh Social",
                "action_type": "refresh",
                "available": True,
                "note": "Reload the live Social Media module payload.",
            },
            {
                "id": "create-post",
                "title": "Create Post",
                "action_type": "create-post",
                "available": publishing is not None,
                "unavailable_reason": "Publishing social post drafting is not available in this runtime." if publishing is None else "",
                "project_id": default_project_id,
                "note": "Create a live social post draft through the publishing store.",
            },
            {
                "id": "schedule-post",
                "title": "Schedule Post",
                "action_type": "schedule-post",
                "available": publishing is not None,
                "unavailable_reason": "Publishing social scheduling is not available in this runtime." if publishing is None else "",
                "project_id": default_project_id,
                "note": "Create a scheduled social post through the publishing store.",
            },
            {
                "id": "approve-next",
                "title": "Approve Next",
                "action_type": "approve-post",
                "available": bool(pending_posts),
                "unavailable_reason": "No pending social post is currently waiting for approval." if not pending_posts else "",
                "post_id": str((pending_posts[:1] or [{}])[0].get("post_id") or ""),
                "note": "Approve the next post currently waiting in the social engine review lane.",
            },
            {
                "id": "execute-ready",
                "title": "Run Ready Posts",
                "action_type": "execute-project",
                "available": bool(engine is not None and default_project_id and scheduled_posts),
                "unavailable_reason": "No project with ready scheduled posts is currently available for execution." if not (engine is not None and default_project_id and scheduled_posts) else "",
                "project_id": default_project_id,
                "note": "Execute approved scheduled posts through the live Social Engine.",
            },
        ]

        quick_actions = [
            {"id": "open-publishing", "title": "Open Publishing", "route": "/publish", "detail": "Open the publishing workspace connected to live social drafts, projects, and launch state."},
            {"id": "open-command", "title": "Content Ideas", "route": "/command-center", "detail": "Route content ideation into Command until a dedicated social ideation surface exists."},
            {"id": "open-analytics", "title": "View Analytics", "route": "/publish", "detail": "Open the publishing workspace for deeper social and launch analytics."},
            {"id": "boundary-thread", "title": "Write Thread", "detail": "A dedicated thread composer route is not exposed in this runtime yet.", "available": False, "unavailable_reason": "A dedicated thread composer route is not exposed in this runtime yet."},
            {"id": "boundary-video", "title": "Upload Video", "detail": "A dedicated video upload or asset-publish route is not exposed in this runtime yet.", "available": False, "unavailable_reason": "A dedicated video upload or asset-publish route is not exposed in this runtime yet."},
            {"id": "boundary-dms", "title": "Respond to DMs", "detail": "A live DM reply backend is not exposed in this runtime yet.", "available": False, "unavailable_reason": "A live DM reply backend is not exposed in this runtime yet."},
        ]

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": f"Social Media loaded {len(normalized_posts)} live post signal(s), {len(accounts_rows)} platform lane(s), {len(pending_posts)} approval item(s), and {len(recent_activity)} continuity event(s).",
            "what_became_real": "Social Media now hydrates from live publishing projects, social queues, scheduling, analytics, engagement snapshots, and operator continuity instead of browser-side invented social math and toast-only actions.",
            "remains_partial": "Direct DM inboxes, native thread composition, uploader flows, and per-platform auth diagnostics still depend on backend routes that are not yet exposed in this runtime.",
            "runtime_note": "Social Media is live and connected." if normalized_posts or accounts_rows or recent_activity else "Social Media is wired, but the runtime has thin live social signal right now.",
            "availability_notes": availability_notes[:10],
            "counts": {
                "posts": len(normalized_posts),
                "pending": len(pending_posts),
                "scheduled": len(scheduled_posts),
                "posted": len(posted_posts),
                "drafts": len(draft_posts),
                "failed": len(failed_posts),
                "accounts": len(accounts_rows),
                "projects": len(publishing_projects) or int(publishing_metrics.get("total_projects") or 0),
                "recent_activity": len(recent_activity),
                "health_score": health_score,
            },
            "selected_project_id": default_project_id,
            "projects": [
                {
                    "project_id": str(getattr(project, "project_id", "") or "").strip(),
                    "title": str(getattr(project, "title", "") or "").strip() or str(getattr(project, "project_id", "") or "").strip(),
                    "project_type": str(getattr(project, "project_type", "") or "").strip(),
                    "status": str(getattr(project, "status", "") or "").strip(),
                    "platform": str(getattr(project, "platform", "") or "").strip(),
                    "tags": list(getattr(project, "tags", []) or []),
                }
                for project in publishing_projects[:8]
            ],
            "headline_stats": headline_stats,
            "sidebar_counts": sidebar_counts,
            "sidebar_status_rows": sidebar_status_rows,
            "platform_rows": accounts_rows,
            "mini_stats": mini_stats,
            "calendar_rows": calendar_rows,
            "calendar_footer": calendar_footer,
            "performance_rows": performance_rows,
            "inbox_rows": inbox_rows,
            "pipeline_rows": pipeline_rows,
            "audience": {
                "total": _human_number(audience_total) if audience_total else "—",
                "rows": audience_rows,
                "insights": audience_insights,
            },
            "theme_rows": theme_rows,
            "health": {"score": health_score, "label": health_label, "metrics": health_metrics},
            "sentiment_rows": sentiment_rows,
            "recommendation_rows": recommendation_rows,
            "security_rows": security_rows,
            "summary_cards": summary_cards,
            "footer_rows": footer_rows,
            "trusted_actions": trusted_actions,
            "quick_actions": quick_actions,
            "recent_activity": recent_activity,
            "proof_paths": {
                "module_route": "/social-center",
                "module_api": "/api/social/module",
                "publishing_projects_api": "/api/publishing/projects",
                "publishing_social_api": "/api/publishing/social/posts",
                "publishing_metrics_api": "/api/publishing/metrics",
                "social_pending_api": "/api/social/posts/pending",
                "social_schedule_api": "/api/social/schedule/{project_id}",
                "social_approve_api": "/api/social/post/approve/{post_id}",
                "social_execute_api": "/api/social/execute",
                "social_analytics_api": "/api/social/analytics/{project_id}",
                "social_adaptation_api": "/api/social/adaptation/{project_id}",
                "activity_api": "/api/activity/operator-action",
                "action_api": "/api/social/module/action",
            },
            "errors": errors,
        }

        if not availability_notes:
            payload["availability_notes"].append("All currently available Social Media sources hydrated successfully.")
        if not normalized_posts and not accounts_rows and not recent_activity and errors:
            payload["available"] = False
            payload["status"] = "Wired"
            payload["runtime_note"] = "Social Media is wired, but the runtime could not hydrate enough live social data to make the surface richly useful yet."
        elif not normalized_posts and not accounts_rows:
            payload["runtime_note"] = "Social Media is live, but no posts, platforms, or engagement snapshots are currently visible in this runtime."
        elif errors:
            payload["runtime_note"] = "Social Media is live, but some queue, analytics, or engagement sources are partially unavailable."
        return payload

    async def _build_daily_brief_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        from datetime import datetime, timezone

        actor_lookup = getattr(runtime, "get_actor", None)
        actor = actor_lookup(actor_name) if callable(actor_lookup) else None
        actor_display = str(getattr(actor, "display_name", "") or actor_name or "Chris")
        actor_user_id = str(getattr(actor, "user_id", "") or actor_display.lower() or "chris")
        household = getattr(runtime, "household", None)
        actor_options = (
            [{"id": user.display_name, "label": user.display_name} for user in household.users.values()]
            if household is not None and getattr(household, "users", None)
            else [{"id": actor_display, "label": actor_display}]
        )
        payload: dict[str, Any] = {
            "actor": actor_display,
            "actor_options": actor_options,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "available": True,
            "status": "Useful",
            "summary": "Daily Brief now has a dedicated module route with live briefing text, today-board posture, and open-loop follow-through actions inside JARVIS.",
            "headline": "",
            "what_became_real": "Daily Brief is now a standalone app module instead of only a shell packet and preview panel, with durable follow-through continuity visible inside the route.",
            "remains_partial": "Broader module drill-ins and richer phone-native brief drill-downs still need follow-on slices, but Daily Brief now has real open-loop follow-through across web and Apple surfaces.",
            "briefing_text": "",
            "live_briefing": {},
            "today_board": {},
            "open_loops": {"items": [], "summary": {}},
            "recent_activity": [],
            "counts": {
                "priority_count": 0,
                "waiting_on_you": 0,
                "needs_revisit": 0,
                "notification_count": 0,
                "calendar_count": 0,
                "recent_activity_count": 0,
            },
            "proof_paths": {
                "module_route": "/briefing-center",
                "module_api": "/api/briefing/module",
                "briefing_api": f"/api/briefing?actor={actor_display}",
                "live_brief_api": f"/api/briefing/live?actor={actor_display}",
                "today_board_api": f"/api/today-board?actor={actor_display}",
                "open_loops_api": f"/api/open-loops?actor={actor_display}",
                "open_loop_action_api": "/api/open-loops/action",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        open_loops: dict[str, Any] = {}
        try:
            open_loops = await asyncio.to_thread(runtime.unified_open_loops, actor_display, 18)
            payload["open_loops"] = open_loops
            payload["counts"]["waiting_on_you"] = int(((open_loops.get("summary") or {}).get("waiting_on_you", 0)) or 0)
            payload["counts"]["needs_revisit"] = int(((open_loops.get("summary") or {}).get("needs_revisit", 0)) or 0)
        except Exception as exc:
            payload["errors"].append(f"open_loops: {exc}")

        try:
            today_board = await asyncio.to_thread(runtime.today_board, actor_display, open_loops=open_loops or None)
            payload["today_board"] = today_board
            payload["counts"]["priority_count"] = len(list(today_board.get("priorities") or []))
            payload["counts"]["notification_count"] = len(list(today_board.get("assistant_notifications") or []))
            payload["counts"]["calendar_count"] = len(list(today_board.get("calendar") or []))
            if not payload["summary"]:
                payload["summary"] = "Daily brief module hydrated from the live today board."
        except Exception as exc:
            payload["errors"].append(f"today_board: {exc}")

        try:
            briefing_text = await asyncio.to_thread(runtime.morning_brief, actor_display)
            payload["briefing_text"] = briefing_text
            lines = [line.strip() for line in str(briefing_text).splitlines() if line.strip()]
            payload["headline"] = lines[0] if lines else ""
        except Exception as exc:
            payload["errors"].append(f"briefing: {exc}")

        try:
            builder = get_briefing_builder()
            if builder is not None:
                payload["live_briefing"] = await asyncio.to_thread(builder.build, actor_user_id)
        except Exception as exc:
            payload["errors"].append(f"live_briefing: {exc}")

        payload["recent_activity"] = _module_recent_activity(route="/briefing-center", domain="briefing")
        payload["counts"]["recent_activity_count"] = len(payload["recent_activity"])

        if payload["counts"]["priority_count"] or payload["counts"]["waiting_on_you"]:
            payload["summary"] = (
                f"Daily brief for {actor_display} loaded "
                f"{payload['counts']['priority_count']} priority item(s) and "
                f"{payload['counts']['waiting_on_you']} item(s) waiting on a decision."
            )

        if payload["errors"]:
            payload["status"] = "Wired"
            if not payload["briefing_text"] and not payload["today_board"]:
                payload["available"] = False
                payload["summary"] = "Daily brief route is live, but key briefing sources did not fully hydrate."
                payload["remains_partial"] = "Live briefing and today-board sources still need repair or population in this runtime."
            else:
                payload["summary"] = "Daily brief route is live with partial briefing and day-state hydration."
                payload["remains_partial"] = "Some briefing sources still failed to hydrate; inspect the payload preview for details."
        return payload

    @app.get("/api/briefing/module")
    async def api_briefing_module(actor: str = "Chris") -> JSONResponse:
        return _json(await _build_daily_brief_module_payload(actor))

    async def _build_progress_module_payload() -> dict[str, Any]:
        command_center = build_command_center_index()
        progress_dashboard = dict(command_center.get("progress_dashboard") or {})
        seam_tracker = dict(command_center.get("seam_tracker") or {})
        level3_checklist = dict(command_center.get("level3_checklist") or {})
        lane_progress = dict(command_center.get("lane_progress") or {})
        failure_recovery = dict(command_center.get("failure_recovery") or {})
        hosted_deployment = dict(command_center.get("hosted_deployment") or {})
        core_modules = dict(command_center.get("core_modules") or {})
        counts = dict(progress_dashboard.get("counts") or {})
        next_focus = ""
        progress_items = [item for item in list(progress_dashboard.get("items") or []) if isinstance(item, dict)]
        for item in progress_items:
            status = str(item.get("status", "")).strip()
            if status in {"Wired", "Stubbed", "Mocked", "Idea"}:
                next_focus = str(item.get("module", "")).strip()
                break
        if not next_focus:
            next_focus = str((progress_items[0] if progress_items else {}).get("module", "")).strip()
        focus_store = ProgressFocusStore(DEFAULT_AUDIT_ROOT)
        focus_summary = focus_store.summary(limit=6)
        operator_focus = dict(focus_summary.get("latest") or {})
        if str(operator_focus.get("module", "")).strip():
            next_focus = str(operator_focus.get("module", "")).strip()
        progress_store = ProgressSnapshotStore(DEFAULT_AUDIT_ROOT)
        persisted_snapshot = progress_store.save_snapshot(
            progress_dashboard=progress_dashboard,
            seam_tracker=seam_tracker,
            lane_progress=lane_progress,
            next_focus=next_focus,
        )
        persistence_summary = progress_store.summary(limit=6)
        seam_persistence = SeamTrackerStore(DEFAULT_AUDIT_ROOT).summary(limit=6)
        return {
            "generated_at": command_center.get("generated_at", ""),
            "available": True,
            "status": "Useful",
            "summary": "Progress now has a dedicated module route with live readiness rows, seam posture, lane state, failure evidence, and durable seam records inside JARVIS.",
            "what_became_real": "Progress is now represented as a standalone app module instead of only a command-center panel, and seam state can now persist durably through the app layer.",
            "remains_partial": "Richer route-to-route progress actions and deeper per-module mutation flows still need follow-on slices, but progress and seam history now persist durably.",
            "progress_dashboard": progress_dashboard,
            "seam_tracker": seam_tracker,
            "level3_checklist": level3_checklist,
            "lane_progress": lane_progress,
            "failure_recovery": failure_recovery,
            "hosted_deployment": hosted_deployment,
            "core_modules": core_modules,
            "progress_persistence": persistence_summary,
            "seam_persistence": seam_persistence,
            "focus_control": focus_summary,
            "counts": {
                "useful": int(counts.get("useful", 0) or 0),
                "wired": int(counts.get("wired", 0) or 0),
                "durable": int(counts.get("durable", 0) or 0),
                "compounding": int(counts.get("compounding", 0) or 0),
                "seam_count": int(seam_tracker.get("item_count", 0) or 0),
                "history_count": int(persistence_summary.get("history_count", 0) or 0),
                "focus_history_count": int(focus_summary.get("history_count", 0) or 0),
                "seam_history_count": int(seam_persistence.get("history_count", 0) or 0),
            },
            "progress_next_focus": next_focus or "No next progress focus recorded yet.",
            "latest_progress_snapshot": persisted_snapshot,
            "proof_paths": {
                "module_route": "/progress-center",
                "module_api": "/api/progress/module",
                "focus_api": "/api/progress/focus",
                "seam_api_prefix": "/api/progress/seams/",
                "command_center_api": "/api/command-center",
                "agent_registry_api": "/api/agent-registry",
                "open_loops_api": "/api/open-loops?actor=Chris",
                "hosted_url": str(hosted_deployment.get("hosted_url", "")).strip() or "https://jarvis.teambinion.org",
                "deploy_script": "deploy/deploy.sh",
                "deploy_workflow": ".github/workflows/deploy.yml",
                "progress_snapshot_json": str((DEFAULT_AUDIT_ROOT / "progress_snapshot.json")),
                "progress_snapshot_history": str((DEFAULT_AUDIT_ROOT / "progress_snapshot_log.jsonl")),
                "progress_focus_json": str((DEFAULT_AUDIT_ROOT / "progress_focus.json")),
                "progress_focus_history": str((DEFAULT_AUDIT_ROOT / "progress_focus_log.jsonl")),
                "seam_tracker_json": str((DEFAULT_AUDIT_ROOT / "seam_tracker.json")),
                "seam_tracker_history": str((DEFAULT_AUDIT_ROOT / "seam_tracker_log.jsonl")),
            },
        }

    @app.get("/api/progress/module")
    async def api_progress_module() -> JSONResponse:
        return _json(await _build_progress_module_payload())

    @app.get("/api/needs-you/module")
    async def api_needs_you_module_alias() -> JSONResponse:
        return _json(await _build_progress_module_payload())

    @app.post("/api/progress/focus")
    async def api_progress_focus(payload: dict[str, Any]) -> JSONResponse:
        module = str(payload.get("module") or "").strip()
        if not module:
            raise HTTPException(status_code=400, detail="module is required")
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        reason = str(payload.get("reason") or "").strip() or f"Progress focus moved to {module}."
        route = str(payload.get("route") or "/progress-center").strip() or "/progress-center"
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module=module,
            reason=reason,
            route=route,
            actor=actor,
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "progress",
                "action": "Set Progress Focus",
                "title": module,
                "detail": reason,
                "why_now": "Progress center advanced the next Level 3 closure target.",
                "result_summary": f"Next progress focus set to {module}.",
                "related_route": "/progress-center",
                "route_label": "Open Progress Center",
                "related_kind": "progress-focus",
                "related_label": module,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        return _json({"status": "recorded", "focus": focus_entry})

    @app.post("/api/progress/seams/{seam_name}")
    async def api_progress_seam_update(seam_name: str, payload: dict[str, Any]) -> JSONResponse:
        name = str(seam_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="seam name is required")
        module = str(payload.get("module") or "Progress").strip() or "Progress"
        status = str(payload.get("status") or "Useful").strip().title() or "Useful"
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        note = str(payload.get("note") or "").strip() or f"Progress recorded seam state for {name}."
        mission_id = str(payload.get("mission_id") or "").strip()
        linked_mission = {}
        if mission_id:
            linked_mission = {
                "mission_id": mission_id,
                "title": str(payload.get("mission_title") or mission_id).strip() or mission_id,
                "lane": str(payload.get("mission_lane") or "next").strip() or "next",
                "route": str(payload.get("mission_route") or "/mission-board").strip() or "/mission-board",
            }
        store = SeamTrackerStore(DEFAULT_AUDIT_ROOT)
        try:
            seam_entry = store.save_seam_state(
                name=name,
                module=module,
                status=status,
                note=note,
                actor=actor,
                route="/progress-center",
                linked_mission=linked_mission,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "progress",
                "action": "Update Seam State",
                "title": name,
                "detail": note,
                "why_now": "Progress center promoted durable seam posture through the app layer.",
                "result_summary": f"Seam {name} now recorded as {status}.",
                "related_route": "/progress-center",
                "route_label": "Open Progress Center",
                "related_kind": "progress-seam",
                "related_label": name,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module=module,
            reason=note,
            route="/progress-center",
            actor=actor,
        )
        return _json({"status": "recorded", "seam": seam_entry, "focus": focus_entry})

    def _recovery_related_routes(target_kind: str, *, route: str = "/recovery-center") -> list[dict[str, str]]:
        normalized = str(target_kind).strip().lower() or "recovery"
        candidates: list[tuple[str, str]] = [("Open Recovery Center", str(route).strip() or "/recovery-center")]
        if normalized == "approval":
            candidates.extend(
                [
                    ("Open Approval Queue", "/approval-queue"),
                    ("Open Supervision Snapshot", "/supervision-snapshot"),
                    ("Open Activity Feed", "/activity-center"),
                ]
            )
        elif normalized == "integration":
            candidates.extend(
                [
                    ("Open Supervision Snapshot", "/supervision-snapshot"),
                    ("Open Activity Feed", "/activity-center"),
                    ("Open Command Center", "/command-center"),
                ]
            )
        elif normalized == "failure":
            candidates.extend(
                [
                    ("Open Activity Feed", "/activity-center"),
                    ("Open Progress Center", "/progress-center"),
                    ("Open Command Center", "/command-center"),
                ]
            )
        else:
            candidates.extend(
                [
                    ("Open Activity Feed", "/activity-center"),
                    ("Open Command Center", "/command-center"),
                ]
            )
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for label, candidate_route in candidates:
            final_route = str(candidate_route).strip() or "/command-center"
            if final_route in seen:
                continue
            seen.add(final_route)
            deduped.append({"label": label, "route": final_route})
        return deduped

    def _decorate_recovery_action(entry: dict[str, Any]) -> dict[str, Any]:
        item = dict(entry or {})
        item["related_routes"] = _recovery_related_routes(
            str(item.get("target_kind", "")).strip(),
            route=str(item.get("route", "")).strip() or "/recovery-center",
        )
        return item

    def _decorate_recovery_surface_item(item: dict[str, Any], target_kind: str) -> dict[str, Any]:
        surface_item = dict(item or {})
        surface_item["related_routes"] = _recovery_related_routes(
            target_kind,
            route=str(surface_item.get("route", "")).strip() or "/recovery-center",
        )
        return surface_item

    def _match_recovery_case(
        *,
        target_kind: str,
        item: dict[str, Any],
        recovery_cases: Sequence[dict[str, Any]],
        index: int = 0,
    ) -> dict[str, Any] | None:
        if target_kind == "integration":
            name = str(item.get("name", "")).strip()
            key = f"integration:{name.lower()}" if name else ""
            for case in recovery_cases:
                if str(case.get("related_key", "")).strip() == key:
                    return dict(case)
            return None
        if target_kind == "failure":
            title = str(item.get("title", "")).strip().lower()
            timestamp = str(item.get("timestamp", "")).strip()
            exact_key = f"failure:{timestamp}:{title}" if timestamp and title else ""
            for case in recovery_cases:
                if exact_key and str(case.get("related_key", "")).strip() == exact_key:
                    return dict(case)
            fallback_key = f"failure:{index}:{title}" if title else ""
            for case in recovery_cases:
                if fallback_key and str(case.get("related_key", "")).strip() == fallback_key:
                    return dict(case)
            return None
        return None

    def _attach_recovery_case_context(
        *,
        items: Sequence[dict[str, Any]],
        target_kind: str,
        recovery_cases: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            row = dict(item or {})
            case = _match_recovery_case(target_kind=target_kind, item=row, recovery_cases=recovery_cases, index=index)
            if case:
                row["case_id"] = str(case.get("case_id", "")).strip()
                row["case_status"] = str(case.get("status", "")).strip()
                row["case_status_label"] = str(case.get("status_label", "")).strip()
                row["execution_count"] = int(case.get("execution_count", 0) or 0)
                row["last_execution_at"] = str(case.get("last_execution_at", "")).strip()
                row["last_execution_action"] = str(case.get("last_execution_action", "")).strip()
            enriched.append(row)
        return enriched

    def _recovery_bridge_summary(limit: int = 6, target_kinds: Sequence[str] | None = None) -> dict[str, Any]:
        summary = RecoveryActionStore(DEFAULT_AUDIT_ROOT).summary(limit=max(limit, 8))
        recent = [_decorate_recovery_action(item) for item in list(summary.get("recent") or []) if isinstance(item, dict)]
        if target_kinds:
            allowed = {str(kind).strip().lower() for kind in target_kinds if str(kind).strip()}
            recent = [item for item in recent if str(item.get("target_kind", "")).strip().lower() in allowed]
        recent = recent[: max(1, limit)]
        return {
            "count": len(recent),
            "recent": recent,
            "proof_paths": dict(summary.get("proof_paths") or {}),
        }

    async def _build_supervision_module_payload() -> dict[str, Any]:
        snapshot = build_supervision_snapshot()
        lane = dict(snapshot.get("lane") or {})
        attention_queue = list(snapshot.get("attention_queue") or [])
        integrations = list(snapshot.get("integrations") or [])
        what_needs_me = list(snapshot.get("what_needs_me") or [])
        memory = dict(snapshot.get("memory") or {})
        registry = dict(snapshot.get("registry") or {})
        recovery_bridge = _recovery_bridge_summary(limit=5, target_kinds=("approval", "integration", "failure", "recovery"))
        recent_activity = _module_recent_activity(route="/supervision-snapshot", domain="supervision")
        recovery_cases = [
            dict(item)
            for item in RecoveryCaseStore().list_cases()
            if str(item.get("source_kind") or "").strip().lower() == "integration"
            and str(item.get("metadata", {}).get("origin_module") or "").strip().lower() == "supervision"
        ][:6]
        integration_recovery_lane: list[dict[str, Any]] = []
        for item in integrations:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            matching_case = next(
                (
                    case
                    for case in recovery_cases
                    if str(case.get("related_key") or "").strip().lower() == name.lower()
                ),
                None,
            )
            integration_recovery_lane.append(
                {
                    "name": name,
                    "ok": bool(item.get("ok")),
                    "detail": str(item.get("detail") or "").strip(),
                    "case_id": str((matching_case or {}).get("case_id") or "").strip(),
                    "case_status": str((matching_case or {}).get("status") or "").strip(),
                    "case_status_label": str((matching_case or {}).get("status_label") or "").strip(),
                    "case_route": str((matching_case or {}).get("related_route") or "/recovery-center").strip() or "/recovery-center",
                    "recovery_action_label": "Stage Recovery Case" if matching_case is None else "Refresh Recovery Case",
                }
            )
        issue_count = sum(1 for item in integrations if not bool(item.get("ok")))
        summary = str((snapshot.get("return_brief") or {}).get("summary", "")).strip() or (
            "Supervision Snapshot now has a dedicated module route with live lane posture, approval attention, integration issues, and memory cues inside JARVIS."
        )

        return {
            "generated_at": snapshot.get("generated_at", ""),
            "available": True,
            "status": "Useful" if (attention_queue or what_needs_me or issue_count or int(lane.get("dirty_count", 0) or 0)) else "Wired",
            "summary": summary,
            "what_became_real": "Supervision Snapshot is now represented as a dedicated app module with visible route-owned continuity instead of only an older proof-style surface.",
            "remains_partial": "Deeper supervision mutation, broader lane recovery controls, and richer continuity into linked modules still need follow-on slices.",
            "lane": lane,
            "return_brief": dict(snapshot.get("return_brief") or {}),
            "attention_queue": attention_queue,
            "memory": memory,
            "registry": registry,
            "integrations": integrations,
            "what_needs_me": what_needs_me,
            "integration_recovery_lane": integration_recovery_lane,
            "recovery_bridge": recovery_bridge,
            "recovery_cases": recovery_cases,
            "recent_activity": recent_activity,
            "counts": {
                "needs_review_count": len(what_needs_me),
                "pending_approval_count": len(attention_queue),
                "integration_issue_count": issue_count,
                "memory_proposal_count": int(memory.get("proposal_count", 0) or 0),
                "registered_agent_count": int(registry.get("agent_count", 0) or 0),
                "recovery_bridge_count": int(recovery_bridge.get("count", 0) or 0),
                "integration_recovery_count": len([item for item in integration_recovery_lane if str(item.get("case_id") or "").strip()]),
                "recent_activity_count": len(recent_activity),
            },
            "proof_paths": {
                "module_route": "/supervision-snapshot",
                "module_api": "/api/supervision/module",
                "legacy_snapshot_api": "/api/supervision-snapshot",
                "supervision_review_action_suffix": "/api/supervision/reviews/{request_id}/{action}",
                "supervision_integration_recovery_suffix": "/api/supervision/integrations/{integration_name}/recovery",
                "approval_queue_route": "/approval-queue",
                "approval_queue_api": "/api/approval/module",
                "command_center_route": "/command-center",
                "recovery_route": "/recovery-center",
                "recovery_action_api": "/api/recovery/action",
                "activity_api": "/api/activity/operator-action",
            },
        }

    async def _build_approval_module_payload() -> dict[str, Any]:
        snapshot = build_approval_queue_snapshot()
        pending = list(snapshot.get("pending") or [])
        history = list(snapshot.get("history") or [])
        what_needs_me = list(snapshot.get("what_needs_me") or [])
        recovery_bridge = _recovery_bridge_summary(limit=4, target_kinds=("approval",))
        recent_activity = _module_recent_activity(route="/approval-queue", domain="approval")
        high_risk_pending_count = sum(1 for item in pending if str(item.get("risk_tier", "")).lower() in {"high", "critical"})
        approval_ready_count = sum(
            1
            for item in pending
            if str((item.get("supervision_decision") or {}).get("resolution", "")).lower() in {"allow", "approved"}
            or str(item.get("status", "")).lower() == "approved"
        )
        summary = "Approval Queue now has a dedicated module route with live pending requests, history detail, and direct approval actions inside JARVIS."
        if pending or history:
            summary = (
                f"Approval queue surfaced {len(pending)} pending request(s), "
                f"{len(history)} recent decision record(s), and {len(what_needs_me)} operator review cue(s)."
            )

        payload: dict[str, Any] = {
            "generated_at": snapshot.get("generated_at", ""),
            "available": not bool(snapshot.get("error")),
            "status": "Useful" if (pending or history or what_needs_me) else "Wired",
            "summary": summary,
            "what_became_real": "Approval Queue is now represented as a dedicated app module with visible route-owned continuity instead of only an older standalone proof surface.",
            "remains_partial": "Broader approval creation/edit workflows, deeper trust-zone drill-ins, and richer continuity back into linked modules still need follow-on slices.",
            "pending": pending,
            "history": history,
            "what_needs_me": what_needs_me,
            "recovery_bridge": recovery_bridge,
            "recent_activity": recent_activity,
            "counts": {
                "pending_count": len(pending),
                "history_count": len(history),
                "high_risk_pending_count": high_risk_pending_count,
                "approval_ready_count": approval_ready_count,
                "recovery_bridge_count": int(recovery_bridge.get("count", 0) or 0),
                "recent_activity_count": len(recent_activity),
            },
            "proof_paths": {
                "module_route": "/approval-queue",
                "module_api": "/api/approval/module",
                "legacy_snapshot_api": "/api/approval-queue/snapshot",
                "pending_api": "/api/approvals/pending",
                "history_api": "/api/approvals/history",
                "submit_api": "/api/approvals/submit",
                "command_center_route": "/command-center",
                "recovery_route": "/recovery-center",
                "recovery_action_api": "/api/recovery/action",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        if snapshot.get("error"):
            payload["errors"].append(str(snapshot.get("error")))
            payload["status"] = "Wired"
            payload["summary"] = "Approval queue route is live, but approval hydration is currently unavailable."
            payload["remains_partial"] = "Approval queue substrate did not fully hydrate in this runtime."

        return payload

    async def _build_recovery_module_payload() -> dict[str, Any]:
        command_center = build_command_center_index()
        failure_recovery = dict(command_center.get("failure_recovery") or {})
        pending_approvals = [
            _decorate_recovery_surface_item(item, "approval")
            for item in list(command_center.get("pending_approvals") or [])
            if isinstance(item, dict)
        ]
        activity_feed = list(command_center.get("activity_feed") or [])
        recovery_actions = _recovery_bridge_summary(limit=8)
        supervision_snapshot = build_supervision_snapshot()
        approval_snapshot = build_approval_queue_snapshot()
        recovery_case_store = RecoveryCaseStore()
        action_items = [
            _decorate_recovery_surface_item(item, "recovery")
            for item in list(failure_recovery.get("action_items") or [])
            if isinstance(item, dict)
        ]
        failing_integrations = [
            _decorate_recovery_surface_item(item, "integration")
            for item in list(failure_recovery.get("failing_integrations") or [])
            if isinstance(item, dict)
        ]
        recent_failures = [
            _decorate_recovery_surface_item(item, "failure")
            for item in list(failure_recovery.get("recent_failures") or [])
            if isinstance(item, dict)
        ]
        recovery_cases = []
        recovery_case_error = ""
        try:
            for item in failing_integrations:
                name = str(item.get("name", "")).strip() or "integration"
                detail = str(item.get("detail", "")).strip() or "Integration needs review."
                recovery_case_store.upsert_case(
                    source_kind="integration-failure",
                    title=f"Repair {name}",
                    detail=detail,
                    related_route="/supervision-snapshot",
                    related_key=f"integration:{name.lower()}",
                    metadata={"integration_name": name},
                )
            for index, item in enumerate(recent_failures):
                title = str(item.get("title", "")).strip() or "Recent failure surfaced"
                detail = str(item.get("detail", "")).strip() or "Runtime failure needs review."
                timestamp = str(item.get("timestamp", "")).strip()
                recovery_case_store.upsert_case(
                    source_kind="recent-failure",
                    title=title,
                    detail=detail,
                    related_route="/command-center",
                    related_key=f"failure:{timestamp or index}:{title.lower()}",
                    metadata={"timestamp": timestamp},
                )
            recovery_cases = recovery_case_store.list_cases()
        except Exception as exc:
            recovery_case_error = str(exc).strip()
            recovery_cases = []
        summary = "Failure & Recovery now has a dedicated module route with live recovery posture, pending approval gates, and recent failure signals inside JARVIS."

        failing_integrations = _attach_recovery_case_context(
            items=failing_integrations,
            target_kind="integration",
            recovery_cases=recovery_cases,
        )
        recent_failures = _attach_recovery_case_context(
            items=recent_failures,
            target_kind="failure",
            recovery_cases=recovery_cases,
        )

        if action_items:
            summary = (
                f"Failure and recovery surfaced {len(action_items)} recovery action(s), "
                f"{int(failure_recovery.get('pending_approval_count', 0) or 0)} pending approval gate(s), "
                f"and {int(failure_recovery.get('integration_issue_count', 0) or 0)} integration issue(s)."
            )
        if recovery_cases:
            unresolved_case_count = sum(
                1 for item in recovery_cases
                if str(item.get("status", "")).strip().lower() in {"open", "investigating", "watch"}
            )
            summary += f" {unresolved_case_count} durable recovery case(s) remain open inside the app state model."

        failure_recovery["action_items"] = action_items
        failure_recovery["failing_integrations"] = failing_integrations
        failure_recovery["recent_failures"] = recent_failures

        payload: dict[str, Any] = {
            "generated_at": command_center.get("generated_at", ""),
            "available": True,
            "status": "Useful" if (action_items or pending_approvals or failing_integrations or recent_failures or recovery_cases) else "Wired",
            "summary": (
                f"{summary} Auto-remediation is now durable too, with staged and executed recovery plans carried on each case."
                if recovery_cases
                else summary
            ),
            "what_became_real": "Failure & Recovery is now a standalone app module with durable retry, approval execution, stabilization, and auto-remediation actions plus visible continuity into the linked approval, supervision, activity, progress, and command-center routes.",
            "remains_partial": "Broader self-healing depth and wider cross-module continuity still need follow-on slices, but retry, approval execution, stabilization, durable remediation planning, and non-approval healing loops are now represented across the recovery stack.",
            "failure_recovery": failure_recovery,
            "recovery_cases": recovery_cases,
            "pending_approvals": pending_approvals,
            "activity_feed": activity_feed,
            "recovery_actions": recovery_actions,
            "supervision_snapshot": supervision_snapshot,
            "approval_snapshot": approval_snapshot,
            "counts": {
                "integration_issues": int(failure_recovery.get("integration_issue_count", 0) or 0),
                "recent_failures": int(failure_recovery.get("recent_failure_count", 0) or 0),
                "pending_approval_gates": int(failure_recovery.get("pending_approval_count", 0) or 0),
                "dirty_count": int(failure_recovery.get("dirty_count", 0) or 0),
                "action_count": len(action_items),
                "recorded_recovery_actions": int(recovery_actions.get("count", 0) or 0),
                "recovery_case_count": len(recovery_cases),
                "recovery_case_investigating_count": sum(1 for item in recovery_cases if str(item.get("status", "")).strip().lower() == "investigating"),
                "recovery_case_watch_count": sum(1 for item in recovery_cases if str(item.get("status", "")).strip().lower() == "watch"),
                "recovery_case_resolved_count": sum(1 for item in recovery_cases if str(item.get("status", "")).strip().lower() == "resolved"),
                "recovery_case_execution_count": sum(int(item.get("execution_count", 0) or 0) for item in recovery_cases),
                "recovery_case_remediation_count": sum(int(item.get("remediation_count", 0) or 0) for item in recovery_cases),
                "recovery_case_plan_count": sum(int(item.get("remediation_plan_count", 0) or 0) for item in recovery_cases),
                "recovery_case_plan_completed_count": sum(int(item.get("remediation_plan_completed_count", 0) or 0) for item in recovery_cases),
                "recovery_case_remediation_staged_count": sum(
                    1 for item in recovery_cases if str(item.get("remediation_status", "")).strip().lower() == "staged"
                ),
                "recovery_case_remediation_executed_count": sum(
                    1 for item in recovery_cases if str(item.get("remediation_status", "")).strip().lower() == "executed"
                ),
                "recovery_case_plan_ready_count": sum(
                    1 for item in recovery_cases if int(item.get("remediation_plan_count", 0) or 0) > 0
                ),
            },
            "proof_paths": {
                "module_route": "/recovery-center",
                "module_api": "/api/recovery/module",
                "recovery_action_api": "/api/recovery/action",
                "recovery_case_api_prefix": "/api/recovery/cases/",
                "recovery_case_execute_suffix": "/execute",
                "recovery_case_remediation_suffix": "/remediation",
                "recovery_case_plan_suffix": "/plan",
                "recovery_case_plan_execute_suffix": "/plan/execute-next",
                "supervision_route": "/supervision-snapshot",
                "supervision_api": "/api/supervision-snapshot",
                "approval_queue_route": "/approval-queue",
                "approval_queue_api": "/api/approval-queue/snapshot",
                "activity_api": "/api/activity",
                "approve_api_prefix": "/api/approvals/",
            },
        }
        if recovery_case_error:
            payload["recovery_case_error"] = recovery_case_error
        return payload

    @app.get("/api/recovery/module")
    async def api_recovery_module() -> JSONResponse:
        return _json(await _build_recovery_module_payload())

    @app.post("/api/recovery/action")
    async def api_record_recovery_action(payload: dict[str, Any]) -> JSONResponse:
        store = RecoveryActionStore(DEFAULT_AUDIT_ROOT)
        entry = store.record_action(
            action_type=str(payload.get("action_type", "")).strip(),
            target_kind=str(payload.get("target_kind", "")).strip(),
            target_label=str(payload.get("target_label", "")).strip(),
            target_id=str(payload.get("target_id", "")).strip(),
            detail=str(payload.get("detail", "")).strip(),
            route=str(payload.get("route", "")).strip() or "/recovery-center",
            status=str(payload.get("status", "")).strip() or "queued",
        )
        return _json(entry, status_code=201)

    @app.post("/api/recovery/cases/{case_id}")
    async def api_recovery_case_update(case_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        status = str(payload.get("status") or "investigating").strip().lower() or "investigating"
        note = str(payload.get("note") or "").strip()
        store = RecoveryCaseStore()
        try:
            case = store.update_status(case_id, status=status, actor=actor, note=note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "recovery-center",
                "action": f"Mark Recovery Case {case.get('status_label', status.title())}",
                "title": str(case.get("title") or "Recovery case").strip() or "Recovery case",
                "detail": note or str(case.get("detail") or "").strip() or f"Recovery case moved to {status}.",
                "why_now": f"Failure and recovery updated durable case state for {str(case.get('related_key') or case_id).strip()}.",
                "result_summary": f"Recovery case status: {status}",
                "related_route": str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
                "route_label": "Open Related Surface",
                "related_kind": "recovery-case",
                "related_label": str(case.get("case_id") or case_id).strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        return _json({"status": "recorded", "case": case})

    @app.post("/api/recovery/cases/{case_id}/execute")
    async def api_recovery_case_execute(case_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        action_type = str(payload.get("action_type") or "retry").strip().lower() or "retry"
        note = str(payload.get("note") or "").strip()
        store = RecoveryCaseStore()
        try:
            case = store.record_execution(
                case_id,
                actor=actor,
                action_type=action_type,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        action_entry = RecoveryActionStore(DEFAULT_AUDIT_ROOT).record_action(
            action_type=action_type,
            target_kind="recovery-case",
            target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
            target_id=str(case.get("case_id") or case_id).strip(),
            detail=note
            or (
                f"Recovery retry loop executed for {str(case.get('title') or case_id).strip()}."
                if action_type == "retry"
                else f"Recovery stabilization loop executed for {str(case.get('title') or case_id).strip()}."
            ),
            route="/recovery-center",
            status="executed" if action_type == "retry" else "stabilized",
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "recovery",
                "action": "Execute Recovery Retry Loop" if action_type == "retry" else "Stabilize Recovery Loop",
                "title": str(case.get("title") or "Recovery case").strip() or "Recovery case",
                "detail": note or str(case.get("detail") or "").strip() or "Recovery execution requested.",
                "why_now": f"Recovery center executed a durable non-approval loop for {str(case.get('related_key') or case_id).strip()}.",
                "result_summary": (
                    f"Recovery loop status: {str(case.get('status_label') or case.get('status') or 'Investigating').strip()}"
                ),
                "related_route": str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
                "route_label": "Open Related Surface",
                "related_kind": "recovery-case",
                "related_label": str(case.get("case_id") or case_id).strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Recovery",
            reason=note or "Recovery execution loop became the highest-priority shared Level 3 focus.",
            route="/recovery-center",
            actor=actor,
        )
        return _json({"status": "recorded", "case": case, "action": action_entry, "focus": focus_entry})

    @app.post("/api/recovery/cases/{case_id}/remediation")
    async def api_recovery_case_remediation(case_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        action_type = str(payload.get("action_type") or "stage").strip().lower() or "stage"
        note = str(payload.get("note") or "").strip()
        store = RecoveryCaseStore()
        try:
            case = store.record_remediation(
                case_id,
                actor=actor,
                action_type=action_type,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        action_label = "Stage Recovery Auto-Remediation" if action_type == "stage" else "Execute Recovery Auto-Remediation"
        detail = note or (
            f"Auto-remediation staged for {str(case.get('title') or case_id).strip()}."
            if action_type == "stage"
            else f"Auto-remediation executed for {str(case.get('title') or case_id).strip()}."
        )
        action_entry = RecoveryActionStore(DEFAULT_AUDIT_ROOT).record_action(
            action_type=f"remediation-{action_type}",
            target_kind="recovery-case",
            target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
            target_id=str(case.get("case_id") or case_id).strip(),
            detail=detail,
            route="/recovery-center",
            status="staged" if action_type == "stage" else "executed",
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "recovery",
                "action": action_label,
                "title": str(case.get("title") or "Recovery case").strip() or "Recovery case",
                "detail": detail,
                "why_now": f"Recovery center advanced a durable remediation plan for {str(case.get('related_key') or case_id).strip()}.",
                "result_summary": (
                    f"Recovery remediation status: {str(case.get('remediation_status_label') or case.get('remediation_status') or 'Staged').strip()}"
                ),
                "related_route": str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
                "route_label": "Open Recovery Center",
                "related_kind": "recovery-case",
                "related_label": str(case.get("case_id") or case_id).strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Recovery",
            reason=detail,
            route="/recovery-center",
            actor=actor,
        )
        return _json({"status": "recorded", "case": case, "action": action_entry, "focus": focus_entry})

    @app.post("/api/recovery/cases/{case_id}/plan")
    async def api_recovery_case_plan(case_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        steps_payload = payload.get("steps")
        steps = steps_payload if isinstance(steps_payload, list) and steps_payload else [
            {"label": "Confirm live failure signal", "detail": "Reproduce the current symptom and confirm the affected surface."},
            {"label": "Stabilize the fragile dependency", "detail": "Reduce blast radius before the next retry or hydration attempt."},
            {"label": "Resume module continuity", "detail": "Verify that shared activity and progress reflect the healed state."},
        ]
        note = str(payload.get("note") or "").strip()
        store = RecoveryCaseStore()
        try:
            case = store.save_remediation_plan(
                case_id,
                actor=actor,
                steps=steps,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        detail = note or (
            f"Prepared a {int(case.get('remediation_plan_count', 0) or 0)}-step healing plan for "
            f"{str(case.get('title') or case_id).strip()}."
        )
        action_entry = RecoveryActionStore(DEFAULT_AUDIT_ROOT).record_action(
            action_type="remediation-plan",
            target_kind="recovery-case",
            target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
            target_id=str(case.get("case_id") or case_id).strip(),
            detail=detail,
            route="/recovery-center",
            status="planned",
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "recovery",
                "action": "Prepare Recovery Healing Plan",
                "title": str(case.get("title") or "Recovery case").strip() or "Recovery case",
                "detail": detail,
                "why_now": f"Recovery center prepared a durable healing plan for {str(case.get('related_key') or case_id).strip()}.",
                "result_summary": f"Recovery plan prepared with {int(case.get('remediation_plan_count', 0) or 0)} step(s).",
                "related_route": str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
                "route_label": "Open Related Surface",
                "related_kind": "recovery-case",
                "related_label": str(case.get("case_id") or case_id).strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Recovery",
            reason=detail,
            route="/recovery-center",
            actor=actor,
        )
        return _json({"status": "recorded", "case": case, "action": action_entry, "focus": focus_entry})

    @app.post("/api/recovery/cases/{case_id}/plan/execute-next")
    async def api_recovery_case_execute_next_plan_step(case_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
        payload = payload or {}
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        note = str(payload.get("note") or "").strip()
        store = RecoveryCaseStore()
        try:
            case, step = store.execute_next_plan_step(
                case_id,
                actor=actor,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        detail = note or f"Executed healing step '{str(step.get('label') or '').strip() or 'Recovery step'}'."
        action_entry = RecoveryActionStore(DEFAULT_AUDIT_ROOT).record_action(
            action_type="remediation-plan-step",
            target_kind="recovery-case",
            target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
            target_id=str(case.get("case_id") or case_id).strip(),
            detail=detail,
            route="/recovery-center",
            status=str(case.get("remediation_plan_status") or "in_progress").strip() or "in_progress",
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "recovery",
                "action": "Execute Recovery Healing Step",
                "title": str(case.get("title") or "Recovery case").strip() or "Recovery case",
                "detail": detail,
                "why_now": f"Recovery center advanced the next durable healing step for {str(case.get('related_key') or case_id).strip()}.",
                "result_summary": (
                    f"Recovery plan is now {str(case.get('remediation_plan_status_label') or case.get('remediation_plan_status') or 'In Progress').strip()}."
                ),
                "related_route": str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
                "route_label": "Open Related Surface",
                "related_kind": "recovery-case",
                "related_label": str(case.get("case_id") or case_id).strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Recovery",
            reason=detail,
            route="/recovery-center",
            actor=actor,
        )
        return _json({"status": "recorded", "case": case, "step": step, "action": action_entry, "focus": focus_entry})

    async def _build_mission_board_module_payload() -> dict[str, Any]:
        command_center = build_command_center_index()
        mission_task_board = dict(command_center.get("mission_task_board") or {})
        seam_tracker = dict(command_center.get("seam_tracker") or {})
        items = list(mission_task_board.get("items") or [])
        counts = dict(mission_task_board.get("counts") or {})
        payload: dict[str, Any] = {
            "generated_at": command_center.get("generated_at", ""),
            "available": True,
            "status": "Useful" if int(mission_task_board.get("item_count", 0) or 0) else "Wired",
            "summary": "Mission & Task Board now has a dedicated module route with live lane posture, mission detail, mission authoring, mission workspaces, handoff authoring, seam linkage, and mission status mutation inside JARVIS.",
            "what_became_real": "Mission & Task Board is now a standalone app module with mission authoring, seam linkage, workspace review, handoff flows, and per-agent work-state controls instead of only a command-center panel and mission API proof path.",
            "remains_partial": "Broader mission workflow depth still needs follow-on slices, but Mission Board actions now feed visible route-level continuity back into the standalone screen.",
            "mission_task_board": mission_task_board,
            "mission_details": {},
            "recent_activity": [],
            "counts": {
                "now": int(counts.get("now", 0) or 0),
                "next": int(counts.get("next", 0) or 0),
                "blocked": int(counts.get("blocked", 0) or 0),
                "completed": int(counts.get("completed", 0) or 0),
                "recent_activity_count": 0,
            },
            "proof_paths": {
                "module_route": "/mission-board",
                "module_api": "/api/mission-board/module",
                "missions_api": "/api/missions",
                "mission_create_api": "/api/missions",
                "mission_edit_api_suffix": "/edit",
                "mission_status_api_prefix": "/api/missions/",
                "mission_handoff_api_suffix": "/handoffs",
                "mission_handoff_ack_suffix": "/handoffs/{handoff_id}/acknowledge",
                "mission_control_api": "/api/mission-control",
            },
            "errors": [],
        }

        mission_snapshot = getattr(runtime, "mission_snapshot", None)
        mission_work_state_snapshot = getattr(runtime, "mission_work_state_snapshot", None)
        seam_items = [item for item in list(seam_tracker.get("items") or []) if isinstance(item, dict)]

        def related_seams_for(detail: dict[str, Any], board_item: dict[str, Any]) -> list[dict[str, Any]]:
            mission_text = " ".join(
                [
                    str(detail.get("title", "")).strip().lower(),
                    str(detail.get("brief", "")).strip().lower(),
                    str(detail.get("request", "")).strip().lower(),
                    str(detail.get("primary_domain", "")).strip().lower(),
                    " ".join(str(item).strip().lower() for item in list(detail.get("selected_agents") or [])),
                ]
            )
            domain = str(board_item.get("primary_domain", "")).strip().lower()
            module_hints = {"Mission Board", "Activity Feed", "Agent Operations", "Progress"}
            if domain == "communications":
                module_hints.add("Publish")
            elif domain == "formation":
                module_hints.add("Chronicle")
            elif domain == "weather":
                module_hints.add("Navigation")
            matches: list[dict[str, Any]] = []
            for seam in seam_items:
                module_name = str(seam.get("module", "")).strip()
                haystack = " ".join(
                    [
                        str(seam.get("name", "")).strip().lower(),
                        str(seam.get("module", "")).strip().lower(),
                        str(seam.get("what_became_real", "")).strip().lower(),
                        str(seam.get("remains_partial", "")).strip().lower(),
                    ]
                )
                if module_name in module_hints or any(token and token in haystack for token in mission_text.split()):
                    matches.append(
                        {
                            "name": str(seam.get("name", "")).strip() or "Seam",
                            "module": module_name or "Progress",
                            "status": str(seam.get("status", "")).strip() or "Wired",
                            "surface_path": str(seam.get("surface_path", "")).strip() or "/command-center",
                            "what_became_real": str(seam.get("what_became_real", "")).strip() or "No seam outcome captured yet.",
                            "remains_partial": str(seam.get("remains_partial", "")).strip() or "No remaining seam detail recorded.",
                        }
                    )
                if len(matches) >= 4:
                    break
            return matches

        if callable(mission_snapshot):
            details: dict[str, Any] = {}
            for item in items[:4]:
                mission_id = str(item.get("mission_id", "")).strip()
                if not mission_id:
                    continue
                try:
                    detail = await asyncio.to_thread(mission_snapshot, mission_id)
                    if isinstance(detail, dict):
                        if callable(mission_work_state_snapshot):
                            try:
                                detail["work_state"] = await asyncio.to_thread(mission_work_state_snapshot, mission_id)
                            except Exception as exc:
                                payload["errors"].append(f"mission_work_state[{mission_id}]: {exc}")
                        detail["related_seams"] = related_seams_for(detail, item)
                        detail["related_routes"] = [
                            {"label": "Open Agent Ops", "href": "/agent-ops-center"},
                            {"label": "Open Activity Feed", "href": "/activity-center"},
                            {"label": "Open Command Center", "href": "/command-center"},
                            {"label": "Mission Edit API", "href": f"/api/missions/{mission_id}/edit"},
                            {"label": "Mission Work-State API", "href": f"/api/missions/{mission_id}/work-state"},
                            {"label": "Mission Handoffs API", "href": f"/api/missions/{mission_id}/handoffs"},
                        ]
                    details[mission_id] = detail
                except Exception as exc:
                    payload["errors"].append(f"mission_snapshot[{mission_id}]: {exc}")
            payload["mission_details"] = details

        if items:
            payload["summary"] = (
                f"Mission board loaded {len(items)} mission(s): "
                f"{payload['counts']['now']} now, {payload['counts']['next']} next, "
                f"{payload['counts']['blocked']} blocked, and {payload['counts']['completed']} completed, "
                f"with mission detail, mission authoring, mission editing, seam linkage, work-state review, and handoff flows available for the leading board items."
            )

        if payload["errors"] and not items:
            payload["available"] = False
            payload["status"] = "Wired"
            payload["summary"] = "Mission board route is live, but mission sources only partially hydrated."
            payload["remains_partial"] = "Mission store or runtime mission detail sources still need repair or population in this runtime."
        elif payload["errors"]:
            payload["status"] = "Useful"
            payload["summary"] = "Mission board route is live with partial mission detail hydration."
            payload["remains_partial"] = "Some mission detail sources still failed to hydrate; inspect the payload preview for details."

        payload["recent_activity"] = _module_recent_activity(route="/mission-board", domain="mission-board")
        payload["counts"]["recent_activity_count"] = len(payload["recent_activity"])

        return payload

    @app.get("/api/mission-board/module")
    async def api_mission_board_module() -> JSONResponse:
        return _json(await _build_mission_board_module_payload())

    async def _build_activity_module_payload() -> dict[str, Any]:
        command_center = build_command_center_index()
        activity_feed = list(command_center.get("activity_feed") or [])
        action_journal = dict(command_center.get("action_journal") or {})
        home_overview = dict(command_center.get("home_overview") or {})
        home_action_result = dict(home_overview.get("action_result") or {})
        focus_summary = ProgressFocusStore(DEFAULT_AUDIT_ROOT).summary()
        review_summary = ActivityReviewStore(DEFAULT_AUDIT_ROOT).summary()

        def event_id_for(entry: dict[str, Any]) -> str:
            import hashlib

            raw = "|".join(
                [
                    str(entry.get("timestamp", "")).strip(),
                    str(entry.get("title", "")).strip(),
                    str(entry.get("detail", "")).strip(),
                    str(entry.get("related_route", "")).strip(),
                    str(entry.get("related_kind", "")).strip(),
                    str(entry.get("entry_type", "")).strip(),
                ]
            )
            return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

        def related_route_for(entry: dict[str, Any]) -> str:
            haystack = " ".join(
                [
                    str(entry.get("title", "")),
                    str(entry.get("subtitle", "")),
                    str(entry.get("detail", "")),
                    str(entry.get("result", "")),
                    str(entry.get("entry_type", "")),
                    str(entry.get("related_kind", "")),
                ]
            ).lower()
            if "approval" in haystack:
                return "/approval-queue"
            if any(token in haystack for token in ("recover", "rollback", "fail", "error", "blocked")):
                return "/recovery-center"
            if "mission" in haystack:
                return "/mission-board"
            if "agent" in haystack:
                return "/agent-ops-center"
            if any(token in haystack for token in ("brief", "daily")):
                return "/briefing-center"
            if any(token in haystack for token in ("progress", "readiness", "snapshot", "seam")):
                return "/progress-center"
            return "/command-center"

        def module_name_for_route(route: str, related_kind: str = "") -> str:
            route_value = str(route or "").strip().lower()
            kind_value = str(related_kind or "").strip().lower()
            if route_value == "/approval-queue" or "approval" in kind_value:
                return "Approval Queue"
            if route_value == "/recovery-center" or any(token in kind_value for token in ("recovery", "failure")):
                return "Recovery"
            if route_value == "/mission-board" or "mission" in kind_value:
                return "Mission Board"
            if route_value == "/agent-ops-center" or "agent" in kind_value:
                return "Agent Ops"
            if route_value == "/briefing-center" or any(token in kind_value for token in ("brief", "open-loop")):
                return "Daily Brief"
            if route_value == "/chronicle-center" or "chronicle" in kind_value:
                return "Chronicle"
            if route_value == "/health-center" or "health" in kind_value:
                return "Health"
            if route_value == "/navigation-center" or any(token in kind_value for token in ("route", "navigation")):
                return "Navigation"
            if route_value == "/publish" or any(token in kind_value for token in ("publish", "publishing")):
                return "Publish"
            if route_value == "/settings-center" or "settings" in kind_value:
                return "Settings"
            if route_value == "/huddle-center" or "huddle" in kind_value:
                return "Huddle"
            if route_value == "/supervision-snapshot" or "supervision" in kind_value:
                return "Supervision"
            if route_value == "/progress-center" or "progress" in kind_value:
                return "Progress"
            if route_value == "/activity-center" or "activity" in kind_value:
                return "Activity Feed"
            return "Command Center"

        enriched_activity = []
        review_lookup = {
            str(item.get("event_id", "")).strip(): dict(item)
            for item in list(review_summary.get("records") or [])
            if str(item.get("event_id", "")).strip()
        }
        bridge = dict(home_action_result.get("activity_bridge") or {})
        has_durable_home_action = any(str(item.get("entry_type", "")).strip() == "home-action" for item in activity_feed)
        if bridge and not has_durable_home_action:
            bridge_entry = dict(bridge)
            bridge_entry["source_kind"] = "home-action-result"
            bridge_entry["subtitle"] = str(home_action_result.get("summary", "")).strip() or str(bridge.get("result_summary", "")).strip()
            bridge_entry["detail"] = str(bridge.get("detail", "")).strip() or str(home_action_result.get("detail", "")).strip()
            bridge_entry["related_route"] = str(home_action_result.get("route", "")).strip() or "/command-center"
            bridge_entry["route_label"] = str(home_action_result.get("route_label", "")).strip() or "Open Related Surface"
            bridge_entry["timestamp"] = str(command_center.get("generated_at", "")).strip()
            bridge_entry["event_id"] = event_id_for(bridge_entry)
            bridge_review = review_lookup.get(str(bridge_entry["event_id"]))
            bridge_entry["review_status"] = str((bridge_review or {}).get("status") or "unreviewed").strip() or "unreviewed"
            bridge_entry["review_status_label"] = str((bridge_review or {}).get("status_label") or "Unreviewed").strip() or "Unreviewed"
            enriched_activity.append(bridge_entry)
        for item in activity_feed:
            enriched = dict(item)
            enriched["source_kind"] = str(item.get("entry_type", "")).strip() or "activity"
            enriched["detail"] = str(item.get("result", "")).strip() or str(item.get("subtitle", "")).strip()
            enriched["related_route"] = str(item.get("related_route", "")).strip() or related_route_for(enriched)
            enriched["route_label"] = str(item.get("route_label", "")).strip() or "Open Related Surface"
            enriched["event_id"] = event_id_for(enriched)
            review = review_lookup.get(str(enriched["event_id"]))
            enriched["review_status"] = str((review or {}).get("status") or "unreviewed").strip() or "unreviewed"
            enriched["review_status_label"] = str((review or {}).get("status_label") or "Unreviewed").strip() or "Unreviewed"
            enriched_activity.append(enriched)

        enriched_journal = []
        for item in list(action_journal.get("entries") or []):
            enriched = dict(item)
            enriched["related_route"] = related_route_for(enriched)
            enriched_journal.append(enriched)
        action_journal["entries"] = enriched_journal

        return {
            "generated_at": command_center.get("generated_at", ""),
            "available": True,
            "status": "Useful" if enriched_activity else "Wired",
            "summary": f"Activity feed loaded {len(enriched_activity)} recent event(s) and {len(enriched_journal)} journal item(s) into a dedicated module route inside JARVIS.",
            "what_became_real": "Activity Feed is now a standalone app module instead of only a command-center panel.",
            "remains_partial": "Deeper audit filtering and broader cross-module resume continuity still need follow-on slices, but durable activity review state now lets operators mark live events for review, resume later, or resolution from the standalone feed.",
            "home_action_result": home_action_result,
            "activity_feed": enriched_activity,
            "action_journal": action_journal,
            "review_lane": list(review_summary.get("records") or [])[:8],
            "counts": {
                "activity_count": len(enriched_activity),
                "journal_count": len(enriched_journal),
                "home_bridge_count": 1 if bridge else 0,
                "focus_history_count": int(focus_summary.get("history_count", 0) or 0),
                "review_count": len(list(review_summary.get("records") or [])),
            },
            "focus_control": focus_summary,
            "progress_next_focus": str((focus_summary.get("latest") or {}).get("module") or "").strip() or "No next progress focus recorded yet.",
            "proof_paths": {
                "module_route": "/activity-center",
                "module_api": "/api/activity/module",
                "activity_api": "/api/activity",
                "activity_focus_api": "/api/activity/module/focus",
                "activity_review_api": "/api/activity/module/review",
                "command_center_route": "/command-center",
                "approval_queue_route": "/approval-queue",
                "recovery_route": "/recovery-center",
                "mission_board_route": "/mission-board",
                "agent_ops_route": "/agent-ops-center",
            },
        }

    @app.get("/api/activity/module")
    async def api_activity_module() -> JSONResponse:
        return _json(await _build_activity_module_payload())

    @app.post("/api/activity/module/focus")
    async def api_activity_module_focus(payload: dict[str, Any]) -> JSONResponse:
        def module_name_for_route(route: str, related_kind: str = "") -> str:
            route_value = str(route or "").strip().lower()
            kind_value = str(related_kind or "").strip().lower()
            if route_value == "/approval-queue" or "approval" in kind_value:
                return "Approval Queue"
            if route_value == "/recovery-center" or any(token in kind_value for token in ("recovery", "failure")):
                return "Recovery"
            if route_value == "/mission-board" or "mission" in kind_value:
                return "Mission Board"
            if route_value == "/agent-ops-center" or "agent" in kind_value:
                return "Agent Ops"
            if route_value == "/briefing-center" or any(token in kind_value for token in ("brief", "open-loop")):
                return "Daily Brief"
            if route_value == "/chronicle-center" or "chronicle" in kind_value:
                return "Chronicle"
            if route_value == "/health-center" or "health" in kind_value:
                return "Health"
            if route_value == "/navigation-center" or any(token in kind_value for token in ("route", "navigation")):
                return "Navigation"
            if route_value == "/publish" or any(token in kind_value for token in ("publish", "publishing")):
                return "Publish"
            if route_value == "/settings-center" or "settings" in kind_value:
                return "Settings"
            if route_value == "/huddle-center" or "huddle" in kind_value:
                return "Huddle"
            if route_value == "/supervision-snapshot" or "supervision" in kind_value:
                return "Supervision"
            if route_value == "/progress-center" or "progress" in kind_value:
                return "Progress"
            if route_value == "/activity-center" or "activity" in kind_value:
                return "Activity Feed"
            return "Command Center"

        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        related_route = str(payload.get("related_route") or payload.get("route") or "/activity-center").strip() or "/activity-center"
        related_kind = str(payload.get("related_kind") or "").strip()
        title = str(payload.get("title") or payload.get("event_title") or "Activity focus").strip() or "Activity focus"
        detail = str(payload.get("detail") or "").strip()
        target_module = str(payload.get("target_module") or "").strip() or module_name_for_route(related_route, related_kind)
        reason = str(payload.get("reason") or detail or f"Activity Feed promoted {title} into shared progress focus.").strip()
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module=target_module,
            reason=reason,
            route="/activity-center",
            actor=actor,
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "activity",
                "action": "Promote Activity Focus",
                "title": title,
                "detail": reason,
                "why_now": "Activity Feed promoted a live event into shared progress continuity.",
                "result_summary": f"Shared progress focus moved to {target_module}.",
                "related_route": "/activity-center",
                "route_label": "Open Activity Feed",
                "related_kind": "progress-focus",
                "related_label": target_module,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        return _json({"status": "recorded", "focus": focus_entry})

    @app.post("/api/activity/module/review")
    async def api_activity_module_review(payload: dict[str, Any]) -> JSONResponse:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be an object")

        def module_name_for_route(route: str, related_kind: str = "") -> str:
            route_value = str(route or "").strip().lower()
            kind_value = str(related_kind or "").strip().lower()
            if route_value == "/approval-queue" or "approval" in kind_value:
                return "Approval Queue"
            if route_value == "/recovery-center" or any(token in kind_value for token in ("recovery", "failure")):
                return "Recovery"
            if route_value == "/mission-board" or "mission" in kind_value:
                return "Mission Board"
            if route_value == "/agent-ops-center" or "agent" in kind_value:
                return "Agent Ops"
            if route_value == "/briefing-center" or any(token in kind_value for token in ("brief", "open-loop")):
                return "Daily Brief"
            if route_value == "/chronicle-center" or "chronicle" in kind_value:
                return "Chronicle"
            if route_value == "/health-center" or "health" in kind_value:
                return "Health"
            if route_value == "/navigation-center" or any(token in kind_value for token in ("route", "navigation")):
                return "Navigation"
            if route_value == "/publish" or any(token in kind_value for token in ("publish", "publishing")):
                return "Publish"
            if route_value == "/settings-center" or "settings" in kind_value:
                return "Settings"
            if route_value == "/huddle-center" or "huddle" in kind_value:
                return "Huddle"
            if route_value == "/supervision-snapshot" or "supervision" in kind_value:
                return "Supervision"
            if route_value == "/progress-center" or "progress" in kind_value:
                return "Progress"
            if route_value == "/activity-center" or "activity" in kind_value:
                return "Activity Feed"
            return "Command Center"

        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        event_id = str(payload.get("event_id") or "").strip()
        title = str(payload.get("title") or "Activity event").strip() or "Activity event"
        status = str(payload.get("status") or "reviewing").strip().lower() or "reviewing"
        detail = str(payload.get("detail") or "").strip() or "Activity event reviewed from the standalone feed."
        related_route = str(payload.get("related_route") or "/command-center").strip() or "/command-center"
        related_kind = str(payload.get("related_kind") or "").strip()
        route_label = str(payload.get("route_label") or "Open Related Surface").strip() or "Open Related Surface"
        if not event_id:
            raise HTTPException(status_code=400, detail="event_id is required")
        target_module = str(payload.get("target_module") or "").strip() or module_name_for_route(related_route, related_kind)
        review_entry = ActivityReviewStore(DEFAULT_AUDIT_ROOT).save_review(
            review_id=event_id,
            event_id=event_id,
            title=title,
            status=status,
            actor=actor,
            detail=detail,
            related_route=related_route,
            related_kind=related_kind,
            route_label=route_label,
            target_module=target_module,
        )
        action_label = {
            "reviewing": "Review Activity Event",
            "resume-later": "Queue Activity Resume",
            "resolved": "Resolve Activity Event",
        }.get(status, "Review Activity Event")
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "activity",
                "action": action_label,
                "title": title,
                "detail": detail,
                "why_now": "Activity Feed advanced a live event into a durable review lane with linked-module continuity.",
                "result_summary": f"Activity review is now {review_entry['status_label']}.",
                "related_route": related_route,
                "route_label": route_label,
                "related_kind": "activity-review",
                "related_label": title,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module=target_module,
            reason=detail,
            route="/activity-center",
            actor=actor,
        )
        return _json({"status": "recorded", "review": review_entry, "focus": focus_entry})

    async def _build_agent_ops_module_payload() -> dict[str, Any]:
        command_center = build_command_center_index()
        roster = dict(command_center.get("agent_ops_roster") or {})
        mission_task_board = dict(command_center.get("mission_task_board") or {})
        counts = dict(roster.get("counts") or {})
        runtime_counts = {"registry_count": 0, "runtime_count": 0, "background_count": 0}
        agent_reviews: dict[str, Any] = {}
        mission_options = []
        for item in list(mission_task_board.get("items") or []):
            if not isinstance(item, dict):
                continue
            mission_id = str(item.get("mission_id", "")).strip()
            if not mission_id:
                continue
            mission_options.append(
                {
                    "mission_id": mission_id,
                    "title": str(item.get("title", "")).strip() or mission_id,
                    "lane": str(item.get("lane", "")).strip() or "next",
                    "domain": str(item.get("primary_domain", "")).strip() or "general",
                }
            )

        payload: dict[str, Any] = {
            "generated_at": command_center.get("generated_at", ""),
            "available": True,
            "status": "Useful" if int(roster.get("item_count", 0) or 0) else "Wired",
            "summary": "Agent Operations now has a dedicated module route with live roster posture, task-agent visibility, mission-linked assignment editing, and route-level mutation controls inside JARVIS.",
            "what_became_real": "Agent Operations is now a standalone app module with visible core and task agents, mission-linked assignment edits, and route-level mutation controls instead of being split across command-center summaries and hierarchy/workspace routes.",
            "remains_partial": "Broader per-agent workflow depth still needs follow-on slices, but Agent Ops actions now feed visible route-level continuity back into the standalone screen.",
            "agent_ops_roster": roster,
            "mission_options": mission_options,
            "agent_reviews": agent_reviews,
            "recent_activity": [],
            "registry": {},
            "background_agents": {},
            "agent_runtime": {},
            "scheduler_status": {},
            "runtime_counts": runtime_counts,
            "counts": {
                "visible_agents": int(roster.get("item_count", 0) or 0),
                "running": int(counts.get("running", 0) or 0),
                "blocked": int(counts.get("blocked", 0) or 0),
                "attention": int(counts.get("attention", 0) or 0),
                "task_agents": int(counts.get("task_agents", 0) or 0),
                "core_agents": int(counts.get("core_agents", 0) or 0),
                "promoted": int(counts.get("promoted", 0) or 0),
                "recent_activity_count": 0,
            },
            "proof_paths": {
                "module_route": "/agent-ops-center",
                "module_api": "/api/agent-ops/module",
                "agent_hierarchy_route": "/agents/hierarchy",
                "registry_api": "/api/agent-registry",
                "background_agents_api": "/api/agents",
                "agent_runtime_api": "/api/agent-runtime",
                "task_agent_profile_api_prefix": "/api/agents/",
                "promote_agent_api_prefix": "/api/agents/",
                "retire_agent_api_prefix": "/api/agents/",
                "assignment_api_prefix": "/api/agents/",
                "missions_api": "/api/missions",
                "mission_work_state_api_prefix": "/api/missions/",
                "scheduler_status_api": "/api/scheduler/status",
                "queue_run_api_prefix": "/api/scheduler/run/",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        registry_snapshot = getattr(runtime, "agent_registry_snapshot", None)
        if callable(registry_snapshot):
            try:
                payload["registry"] = await asyncio.to_thread(registry_snapshot)
                payload["runtime_counts"]["registry_count"] = int(
                    len(list((payload["registry"] or {}).get("agents") or []))
                )
            except Exception as exc:
                payload["errors"].append(f"registry: {exc}")

        background_agent_status = getattr(runtime, "background_agent_status", None)
        if callable(background_agent_status):
            try:
                payload["background_agents"] = await asyncio.to_thread(background_agent_status)
                background_items = payload["background_agents"]
                if isinstance(background_items, dict):
                    payload["runtime_counts"]["background_count"] = int(
                        len(list(background_items.get("agents") or []))
                    )
            except Exception as exc:
                payload["errors"].append(f"background_agents: {exc}")

        agent_runtime_snapshot = getattr(runtime, "agent_runtime_snapshot", None)
        if callable(agent_runtime_snapshot):
            try:
                payload["agent_runtime"] = await asyncio.to_thread(agent_runtime_snapshot)
                runtime_agents = (payload["agent_runtime"] or {}).get("agents") if isinstance(payload["agent_runtime"], dict) else {}
                if isinstance(runtime_agents, dict):
                    payload["runtime_counts"]["runtime_count"] = int(len(runtime_agents))
            except Exception as exc:
                payload["errors"].append(f"agent_runtime: {exc}")

        mission_work_state_snapshot = getattr(runtime, "mission_work_state_snapshot", None)
        mission_title_map = {str(item.get("mission_id", "")).strip(): str(item.get("title", "")).strip() for item in mission_options}
        if callable(mission_work_state_snapshot):
            for item in mission_options[:8]:
                mission_id = str(item.get("mission_id", "")).strip()
                if not mission_id:
                    continue
                try:
                    work_state = await asyncio.to_thread(mission_work_state_snapshot, mission_id)
                except Exception as exc:
                    payload["errors"].append(f"mission_work_state[{mission_id}]: {exc}")
                    continue
                workspace_map = dict((work_state or {}).get("agent_work_states") or {})
                for agent_id, workspace in workspace_map.items():
                    clean_agent_id = str(agent_id).strip()
                    if not clean_agent_id:
                        continue
                    state = dict(workspace or {})
                    review = agent_reviews.setdefault(
                        clean_agent_id,
                        {
                            "mission_id": mission_id,
                            "mission_title": mission_title_map.get(mission_id, mission_id),
                            "status": str(state.get("status", "")).strip() or "unknown",
                            "ownership_mode": str(state.get("ownership_mode", "")).strip() or "supporting",
                            "current_focus": str(state.get("current_focus", "")).strip(),
                            "active_tasks": len(list(state.get("active_tasks") or [])),
                            "blocked_tasks": len(list(state.get("blocked_tasks") or [])),
                            "pending_reviews": len(list(state.get("pending_reviews") or [])),
                            "recent_decisions": [dict(decision or {}) for decision in list(state.get("recent_decisions") or [])[:4]],
                            "last_handoff_at": str(state.get("last_handoff_at", "")).strip(),
                            "updated_at": str(state.get("updated_at", "")).strip(),
                            "usage_count": 0,
                            "success_count": 0,
                            "success_rate": "",
                            "last_used_at": "",
                        },
                    )
                    review["mission_id"] = mission_id
                    review["mission_title"] = mission_title_map.get(mission_id, mission_id)
                    review["status"] = str(state.get("status", "")).strip() or review["status"]
                    review["ownership_mode"] = str(state.get("ownership_mode", "")).strip() or review["ownership_mode"]
                    review["current_focus"] = str(state.get("current_focus", "")).strip() or review["current_focus"]
                    review["active_tasks"] = len(list(state.get("active_tasks") or []))
                    review["blocked_tasks"] = len(list(state.get("blocked_tasks") or []))
                    review["pending_reviews"] = len(list(state.get("pending_reviews") or []))
                    review["recent_decisions"] = [dict(decision or {}) for decision in list(state.get("recent_decisions") or [])[:4]]
                    review["last_handoff_at"] = str(state.get("last_handoff_at", "")).strip() or review["last_handoff_at"]
                    review["updated_at"] = str(state.get("updated_at", "")).strip() or review["updated_at"]

        task_agent_profile = getattr(runtime, "task_agent_profile", None)
        if callable(task_agent_profile):
            for item in roster.get("items") or []:
                if not isinstance(item, dict) or not bool(item.get("is_task_agent")):
                    continue
                agent_id = str(item.get("agent_id", "")).strip()
                if not agent_id:
                    continue
                try:
                    profile = await asyncio.to_thread(task_agent_profile, agent_id)
                except Exception as exc:
                    payload["errors"].append(f"task_agent_profile[{agent_id}]: {exc}")
                    continue
                if not isinstance(profile, dict):
                    continue
                usage_count = int(profile.get("usage_count", 0) or 0)
                success_count = int(profile.get("success_count", 0) or 0)
                review = agent_reviews.setdefault(
                    agent_id,
                    {
                        "mission_id": str(profile.get("mission_id", "")).strip(),
                        "mission_title": mission_title_map.get(str(profile.get("mission_id", "")).strip(), str(profile.get("mission_id", "")).strip()),
                        "status": str(item.get("status", "")).strip() or "unknown",
                        "ownership_mode": "supporting",
                        "current_focus": "",
                        "active_tasks": 0,
                        "blocked_tasks": 0,
                        "pending_reviews": 0,
                        "recent_decisions": [],
                        "last_handoff_at": "",
                        "updated_at": str(profile.get("updated_at", "")).strip(),
                        "usage_count": usage_count,
                        "success_count": success_count,
                        "success_rate": "",
                        "last_used_at": str(profile.get("last_used_at", "")).strip(),
                    },
                )
                review["usage_count"] = usage_count
                review["success_count"] = success_count
                review["last_used_at"] = str(profile.get("last_used_at", "")).strip() or review.get("last_used_at", "")
                review["updated_at"] = str(profile.get("updated_at", "")).strip() or review.get("updated_at", "")
                review["mission_id"] = str(profile.get("mission_id", "")).strip() or review.get("mission_id", "")
                review["mission_title"] = mission_title_map.get(review["mission_id"], review["mission_id"])
                review["success_rate"] = f"{round((success_count / usage_count) * 100)}%" if usage_count > 0 else ""

        try:
            scheduler = get_scheduler()
            if scheduler is None:
                payload["scheduler_status"] = {"running": False, "error": "Scheduler not initialised"}
            else:
                payload["scheduler_status"] = scheduler.get_status()
        except Exception as exc:
            payload["scheduler_status"] = {"running": False, "error": str(exc)}
            payload["errors"].append(f"scheduler: {exc}")

        if payload["counts"]["visible_agents"]:
            payload["summary"] = (
                f"Agent operations loaded {payload['counts']['visible_agents']} visible agent(s), "
                f"{payload['counts']['running']} running, {payload['counts']['blocked']} blocked, "
                f"{payload['counts']['attention']} needing attention, and {payload['counts']['task_agents']} task agent(s)."
            )

        if payload["errors"] and not payload["counts"]["visible_agents"]:
            payload["available"] = False
            payload["status"] = "Wired"
            payload["summary"] = "Agent operations route is live, but the runtime posture only partially hydrated."
            payload["remains_partial"] = "Agent registry, runtime, or scheduler sources still need repair or population in this runtime."
        elif payload["errors"]:
            payload["status"] = "Useful"
            payload["summary"] = "Agent operations route is live with partial runtime or scheduler hydration."
            payload["remains_partial"] = "Some ops sources still failed to hydrate; inspect the payload preview for details."

        payload["recent_activity"] = _module_recent_activity(route="/agent-ops-center", domain="agent-ops")
        payload["counts"]["recent_activity_count"] = len(payload["recent_activity"])

        return payload

    @app.get("/api/agent-ops/module")
    async def api_agent_ops_module() -> JSONResponse:
        return _json(await _build_agent_ops_module_payload())

    async def _build_agents_module_payload() -> dict[str, Any]:
        command_center = build_command_center_index()
        agent_ops = await _build_agent_ops_module_payload()
        roster = dict(agent_ops.get("agent_ops_roster") or {})
        roster_items = [
            dict(item)
            for item in list(roster.get("items") or [])
            if isinstance(item, dict)
        ]
        registry_snapshot = dict(agent_ops.get("registry") or {})
        registry_agents = [
            dict(item)
            for item in list(registry_snapshot.get("agents") or [])
            if isinstance(item, dict)
        ]
        runtime_snapshot = dict(agent_ops.get("agent_runtime") or {})
        runtime_agents = dict(runtime_snapshot.get("agents") or {})
        background_snapshot = dict(agent_ops.get("background_agents") or {})
        background_agents = dict(background_snapshot.get("agents") or {})
        scheduler_status = dict(agent_ops.get("scheduler_status") or {})
        agent_reviews = {
            str(agent_id).strip(): dict(review or {})
            for agent_id, review in dict(agent_ops.get("agent_reviews") or {}).items()
            if str(agent_id).strip()
        }
        recent_activity = _module_recent_activity(route="/agent-ops-center", domain="agent-ops", limit=8)
        activity_feed = [
            dict(item)
            for item in list(command_center.get("activity_feed") or [])
            if isinstance(item, dict)
        ]
        list_pending_approvals = getattr(runtime, "list_pending_approvals", None)
        list_agent_supervision_contracts = getattr(runtime, "list_agent_supervision_contracts", None)
        list_supervision_traces = getattr(runtime, "list_supervision_traces", None)
        list_supervision_reviews = getattr(runtime, "list_supervision_reviews", None)

        approvals_source = list_pending_approvals() if callable(list_pending_approvals) else []
        contracts_source = list_agent_supervision_contracts() if callable(list_agent_supervision_contracts) else []
        traces_source = list_supervision_traces(limit=24) if callable(list_supervision_traces) else []
        reviews_source = list_supervision_reviews(limit=24) if callable(list_supervision_reviews) else []

        approvals = [
            dict(item)
            for item in list(approvals_source or [])
            if isinstance(item, dict)
        ]
        contracts = [
            dict(item)
            for item in list(contracts_source or [])
            if isinstance(item, dict)
        ]
        traces = [
            dict(item)
            for item in list(traces_source or [])
            if isinstance(item, dict)
        ]
        reviews = [
            dict(item)
            for item in list(reviews_source or [])
            if isinstance(item, dict)
        ]

        try:
            from .agent_work import get_all_proposed, get_all_stores
            from dataclasses import asdict as _asdict

            work_items = []
            for store in get_all_stores().values():
                work_items.extend(store.all_items())
            work_items.sort(key=lambda item: getattr(item, "updated_at", ""), reverse=True)
            work_payload = [_asdict(item) for item in work_items[:100]]
            proposed_payload = [dict(item) for item in get_all_proposed()]
        except Exception as exc:
            work_payload = []
            proposed_payload = []
            agent_ops.setdefault("errors", []).append(f"agent_work: {exc}")

        registry_by_id = {
            str(item.get("agent_id", "")).strip(): item
            for item in registry_agents
            if str(item.get("agent_id", "")).strip()
        }
        contracts_by_id = {
            str(item.get("agent_id", "")).strip(): item
            for item in contracts
            if str(item.get("agent_id", "")).strip()
        }
        contracts_by_label = {
            str(item.get("label", "")).strip().lower(): item
            for item in contracts
            if str(item.get("label", "")).strip()
        }

        def _title_case_words(value: object) -> str:
            raw = str(value or "").strip()
            if not raw:
                return ""
            return " ".join(word.capitalize() for word in raw.replace("_", " ").replace("-", " ").split())

        def _normalize_status(value: object) -> str:
            raw = str(value or "").strip().lower()
            if raw in {"active", "running", "awake"}:
                return "active"
            if raw in {"steady", "idle", "watching", "standby", "fresh"}:
                return "watching"
            if raw in {"attention", "waiting", "awaiting", "review"}:
                return "waiting"
            if raw in {"blocked", "hold", "error", "failed", "degraded"}:
                return "blocked"
            return "offline"

        def _status_label(category: str) -> str:
            return {
                "active": "Active",
                "watching": "Watching",
                "waiting": "Waiting",
                "blocked": "Blocked",
                "offline": "Offline",
            }.get(category, "Offline")

        normalized_roster: list[dict[str, Any]] = []
        availability_notes: list[str] = []
        for item in roster_items:
            agent_id = str(item.get("agent_id", "")).strip()
            if not agent_id:
                continue
            registry_item = dict(registry_by_id.get(agent_id) or {})
            runtime_item = dict(runtime_agents.get(agent_id) or {})
            background_item = dict(background_agents.get(agent_id) or {})
            contract = dict(
                contracts_by_id.get(agent_id)
                or contracts_by_label.get(str(item.get("name", "")).strip().lower())
                or contracts_by_label.get(str(registry_item.get("label", "")).strip().lower())
                or {}
            )
            review = dict(agent_reviews.get(agent_id) or {})
            lifecycle = dict(runtime_item.get("lifecycle") or {})
            runtime_contract = dict(runtime_item.get("contract") or {})

            category = _normalize_status(
                lifecycle.get("current_state")
                or background_item.get("state")
                or item.get("status")
            )
            title = (
                _title_case_words(
                    registry_item.get("primary_domain")
                    or item.get("domain")
                    or review.get("mission_title")
                    or item.get("module")
                )
                or str(item.get("source_label", "")).strip()
                or "Agent"
            )
            normalized = {
                "id": agent_id,
                "agent_id": agent_id,
                "name": str(item.get("name", "")).strip() or str(registry_item.get("label", "")).strip() or agent_id,
                "title": title,
                "domain": _title_case_words(item.get("domain") or registry_item.get("primary_domain") or item.get("module") or "operations"),
                "status": category,
                "status_label": _status_label(category),
                "status_class": str(item.get("status_class", "")).strip() or category,
                "source_label": str(item.get("source_label", "")).strip() or ("Task Agent" if bool(item.get("is_task_agent")) else "Core Agent"),
                "source_kind": str(item.get("source_kind", "")).strip() or ("task-agent" if bool(item.get("is_task_agent")) else "core-agent"),
                "purpose": str(item.get("purpose", "")).strip() or str(registry_item.get("purpose", "")).strip() or str(runtime_contract.get("mission", "")).strip(),
                "assignment": str(review.get("current_focus", "")).strip() or str(item.get("assignment", "")).strip() or str(runtime_contract.get("role", "")).strip(),
                "attention_reason": str(item.get("attention_reason", "")).strip() or str(background_item.get("attention_mode", "")).strip() or str(lifecycle.get("pause_reason", "")).strip() or str(lifecycle.get("wake_reason", "")).strip(),
                "authority_stage": str(item.get("authority_stage", "")).strip() or str(contract.get("authority_stage", "")).strip() or str(registry_item.get("autonomy_posture", "")).strip(),
                "autonomy_posture": str(registry_item.get("autonomy_posture", "")).strip() or str(runtime_contract.get("authority_boundary", "")).strip(),
                "trust_zone": str(contract.get("trust_zone_id", "")).strip() or str(registry_item.get("trust_zone", "")).strip() or str(runtime_contract.get("trust_zone", "")).strip(),
                "lane_id": str(contract.get("lane_id", "")).strip() or str(runtime_contract.get("lane_owner", "")).strip(),
                "module": str(item.get("module", "")).strip() or str(registry_item.get("primary_domain", "")).strip(),
                "mission_roles": list(item.get("mission_roles") or registry_item.get("mission_roles") or runtime_contract.get("mission_roles") or []),
                "allowed_tools": list(registry_item.get("allowed_tools") or runtime_contract.get("allowed_tools") or []),
                "allowed_without_approval": list(contract.get("allowed_without_approval") or []),
                "must_stage_actions": list(contract.get("must_stage_actions") or []),
                "must_escalate_actions": list(contract.get("must_escalate_actions") or []),
                "forbidden_actions": list(contract.get("forbidden_actions") or []),
                "reversible_actions": list(contract.get("reversible_actions") or []),
                "approval_mode": str(contract.get("approval_mode", "")).strip(),
                "escalation_target": str(contract.get("escalation_target", "")).strip() or str(runtime_contract.get("escalation_target", "")).strip(),
                "foreground_policy": str(registry_item.get("foreground_policy", "")).strip(),
                "background_policy": str(registry_item.get("background_policy", "")).strip(),
                "quiet_hours_behavior": str(contract.get("quiet_hours_behavior", "")).strip() or str(registry_item.get("quiet_hours_behavior", "")).strip(),
                "cadence_minutes": int(registry_item.get("cadence_minutes", 0) or runtime_contract.get("cadence_minutes", 0) or 0),
                "heartbeat_status": str(background_item.get("heartbeat_status", "")).strip() or str((runtime_item.get("heartbeat") or {}).get("status", "")).strip(),
                "health_status": str(background_item.get("health_status", "")).strip() or str((runtime_item.get("health") or {}).get("status", "")).strip(),
                "last_activity": str(item.get("last_activity", "")).strip() or str(background_item.get("last_run_at", "")).strip(),
                "last_handoff_at": str(review.get("last_handoff_at", "")).strip(),
                "last_used_at": str(review.get("last_used_at", "")).strip(),
                "updated_at": str(review.get("updated_at", "")).strip() or str(background_item.get("last_run_at", "")).strip(),
                "current_focus": str(review.get("current_focus", "")).strip(),
                "active_tasks": int(review.get("active_tasks", 0) or 0),
                "blocked_tasks": int(review.get("blocked_tasks", 0) or 0),
                "pending_reviews": int(review.get("pending_reviews", 0) or 0),
                "recent_decisions": list(review.get("recent_decisions") or []),
                "usage_count": int(review.get("usage_count", 0) or 0),
                "success_count": int(review.get("success_count", 0) or 0),
                "success_rate": str(review.get("success_rate", "")).strip(),
                "is_task_agent": bool(item.get("is_task_agent")),
                "promotion_candidate": bool(item.get("promotion_candidate")),
            }
            if not normalized["purpose"]:
                availability_notes.append(f"{normalized['name']} has no purpose contract surfaced yet.")
            normalized_roster.append(normalized)

        normalized_roster.sort(
            key=lambda item: (
                {"blocked": 0, "waiting": 1, "active": 2, "watching": 3, "offline": 4}.get(item.get("status", "offline"), 5),
                str(item.get("name", "")).lower(),
            )
        )

        status_counts = {"active": 0, "watching": 0, "waiting": 0, "blocked": 0, "offline": 0}
        for item in normalized_roster:
            status_counts[item["status"]] = int(status_counts.get(item["status"], 0) or 0) + 1

        def _urgency_rank(value: object) -> int:
            raw = str(value or "").strip().lower()
            if raw in {"critical", "high", "urgent", "blocked"}:
                return 0
            if raw in {"medium", "review", "pending"}:
                return 1
            return 2

        pending_requests: list[dict[str, Any]] = []
        for item in approvals[:8]:
            request_id = str(item.get("request_id", "")).strip() or str(item.get("id", "")).strip()
            pending_requests.append(
                {
                    "kind": "approval",
                    "request_id": request_id,
                    "title": str(item.get("title", "")).strip() or "Pending approval",
                    "detail": str(item.get("summary", "")).strip() or str(item.get("detail", "")).strip() or "Awaiting review.",
                    "owner": str(item.get("owner", "")).strip() or str(item.get("actor", "")).strip() or "JARVIS",
                    "urgency": str(item.get("urgency", "")).strip() or "medium",
                    "route": "/approval-queue",
                    "route_label": "Review",
                }
            )
        for item in proposed_payload[:8]:
            pending_requests.append(
                {
                    "kind": "proposed-work",
                    "work_id": str(item.get("work_id", "")).strip(),
                    "title": str(item.get("title", "")).strip() or "Proposed work",
                    "detail": str(item.get("idea", "")).strip() or str(item.get("research", "")).strip() or "Awaiting your approval.",
                    "owner": str(item.get("agent_id", "")).strip() or "Agent",
                    "urgency": "medium",
                    "route": "/catalyst",
                    "route_label": "Open Work",
                }
            )
        for item in list(((command_center.get("failure_recovery") or {}).get("action_items") or []))[:8]:
            pending_requests.append(
                {
                    "kind": "recovery",
                    "title": str(item.get("title", "")).strip() or str(item.get("name", "")).strip() or "Recovery item",
                    "detail": str(item.get("detail", "")).strip() or str(item.get("summary", "")).strip() or "Needs intervention.",
                    "owner": str(item.get("owner", "")).strip() or "System",
                    "urgency": str(item.get("urgency", "")).strip() or "high",
                    "route": "/supervision-snapshot",
                    "route_label": "Open Recovery View",
                }
            )
        pending_requests.sort(key=lambda item: (_urgency_rank(item.get("urgency")), str(item.get("title", "")).lower()))

        activity_items = recent_activity + activity_feed
        deduped_activity: list[dict[str, Any]] = []
        seen_activity: set[str] = set()
        for item in activity_items:
            key = str(item.get("event_id", "")).strip() or str(item.get("timestamp", "")).strip() + "|" + str(item.get("title", "")).strip()
            if not key or key in seen_activity:
                continue
            seen_activity.add(key)
            deduped_activity.append(dict(item))

        specialization_counts: dict[str, dict[str, Any]] = {}
        for item in normalized_roster:
            domain = str(item.get("domain", "")).strip() or "Operations"
            bucket = specialization_counts.setdefault(domain, {"label": domain, "count": 0, "roles": set()})
            bucket["count"] += 1
            for role in list(item.get("mission_roles") or [])[:3]:
                clean_role = str(role).strip()
                if clean_role:
                    bucket["roles"].add(_title_case_words(clean_role))
        specializations = [
            {
                "label": payload["label"],
                "count": payload["count"],
                "roles": sorted(payload["roles"])[:4],
            }
            for payload in specialization_counts.values()
        ]
        specializations.sort(key=lambda item: (-int(item["count"]), str(item["label"]).lower()))

        collaboration_items = [
            {
                "agent_id": str(item.get("agent_id", "")).strip(),
                "lane_id": str(item.get("lane_id", "")).strip(),
                "requested_outcome": str(item.get("requested_outcome", "")).strip(),
                "resolution": str(item.get("resolution", "")).strip() or "observe",
                "authority_stage": str(item.get("authority_stage", "")).strip(),
                "trust_zone_id": str(item.get("trust_zone_id", "")).strip(),
            }
            for item in traces[:12]
            if str(item.get("agent_id", "")).strip()
        ]

        health_score = 100
        visible_count = max(1, len(normalized_roster))
        health_score -= int(round((status_counts["blocked"] / visible_count) * 30))
        health_score -= int(round((status_counts["waiting"] / visible_count) * 12))
        if dict(scheduler_status).get("error"):
            health_score -= 8
        health_score = max(38, min(98, health_score))

        runtime_freshness = str(background_snapshot.get("last_tick_at", "")).strip() or str(runtime_snapshot.get("generated_at", "")).strip()
        performance = {
            "work_items": len(work_payload),
            "proposed_work": len(proposed_payload),
            "approved_work": len([item for item in work_payload if str(item.get("status", "")).strip().lower() == "approved"]),
            "supervision_traces": len(traces),
            "runtime_freshness": runtime_freshness,
            "health_score": health_score,
        }
        trust_rows = [
            {"title": "Autonomy Posture", "value": "Bounded autonomy", "detail": f"{status_counts['blocked']} blocked, {status_counts['waiting']} waiting."},
            {"title": "Trust Level (Overall)", "value": "High" if health_score >= 80 else "Needs attention", "detail": f"Derived from live runtime posture: {health_score}%."},
            {"title": "Escalation Rules", "value": "Strict" if traces else "Normal", "detail": f"{len(contracts)} contract(s), {len(traces)} recent trace(s)."},
            {"title": "Human Review Required", "value": str(len(pending_requests[:12])) + " decision types", "detail": f"{len(approvals)} approvals and {len(proposed_payload)} proposed work items surfaced."},
            {"title": "Recent Overrides", "value": str(len(reviews)), "detail": "Supervision reviews recorded recently." if reviews else "No recent supervision reviews recorded."},
        ]
        footer = [
            {"title": "Bounded Autonomy", "copy": "Power with boundaries. Trust with oversight."},
            {"title": "Clear Responsibility", "copy": "Every live agent has a lane, domain, and runtime posture."},
            {"title": "Continuous Learning", "copy": f"{len(traces)} recent supervision trace(s) and {len(reviews)} review item(s) are shaping doctrine."},
            {"title": "Human Authority", "copy": f"{len(pending_requests)} surfaced item(s) still require your judgment."},
            {"title": "Aligned to Mission", "copy": f"{len(specializations)} specialization lane(s) are visible in the council."},
            {"title": "Protect What Matters", "copy": "Agents guard time, family, operations, and stewardship."},
            {"title": "Agents Online", "copy": f"{status_counts['active']} active · {status_counts['watching']} watching · {status_counts['waiting']} waiting"},
        ]

        selected_agent_id = ""
        for item in normalized_roster:
            if item.get("status") in {"blocked", "waiting", "active"}:
                selected_agent_id = str(item.get("agent_id", "")).strip()
                break
        if not selected_agent_id and normalized_roster:
            selected_agent_id = str(normalized_roster[0].get("agent_id", "")).strip()

        merged_availability_notes: list[str] = []
        seen_notes: set[str] = set()
        for note in list(agent_ops.get("errors") or []) + list(availability_notes or []):
            text = str(note or "").strip()
            if not text or text in seen_notes:
                continue
            seen_notes.add(text)
            merged_availability_notes.append(text)
            if len(merged_availability_notes) >= 8:
                break

        payload: dict[str, Any] = {
            "generated_at": command_center.get("generated_at", ""),
            "available": bool(normalized_roster),
            "status": "Useful" if normalized_roster else "Wired",
            "summary": (
                f"Agents loaded {len(normalized_roster)} live roster item(s), {status_counts['active']} active, "
                f"{status_counts['waiting']} waiting, {status_counts['blocked']} blocked, and {len(pending_requests)} surfaced request(s)."
            ),
            "what_became_real": "Agents is now driven by the live registry, runtime kernel, supervision traces, work queues, and command-center continuity instead of a seeded fictional council.",
            "remains_partial": "Some agents still lack deep per-agent contracts or current work focus, so those cards now show honest partial-state messaging instead of invented output.",
            "roster": {
                "item_count": len(normalized_roster),
                "counts": status_counts,
                "items": normalized_roster,
                "selected_agent_id": selected_agent_id,
            },
            "activity_feed": deduped_activity[:10],
            "pending_requests": pending_requests[:12],
            "collaboration": {
                "items": collaboration_items,
                "trace_count": len(traces),
                "review_count": len(reviews),
            },
            "trust": {
                "rows": trust_rows,
                "contracts": contracts[:12],
                "traces": traces[:12],
                "reviews": reviews[:12],
            },
            "specializations": specializations[:10],
            "performance": performance,
            "footer": footer,
            "runtime": {
                "registry": registry_snapshot,
                "background": background_snapshot,
                "agent_runtime": runtime_snapshot,
                "scheduler_status": scheduler_status,
                "supported_actions": list(runtime_snapshot.get("supported_actions") or []),
            },
            "work": {
                "items": work_payload[:24],
                "proposed": proposed_payload[:24],
            },
            "availability_notes": merged_availability_notes,
            "recent_activity": recent_activity,
            "proof_paths": {
                "module_route": "/agents",
                "module_api": "/api/agents/module",
                "roster_api": "/api/agents/roster",
                "agent_ops_api": "/api/agent-ops/module",
                "registry_api": "/api/agent-registry",
                "background_agents_api": "/api/agents",
                "agent_runtime_api": "/api/agent-runtime",
                "agent_work_api": "/api/agent-work",
                "agent_work_proposed_api": "/api/agent-work/proposed",
                "agent_supervision_contracts_api": "/api/agent-supervision/contracts",
                "agent_supervision_traces_api": "/api/agent-supervision/traces",
                "agent_supervision_reviews_api": "/api/agent-supervision/reviews",
                "activity_api": "/api/activity/operator-action",
                "runtime_control_api": "/api/agent-runtime/control",
                "runtime_heartbeat_api": "/api/agent-runtime/heartbeat",
            },
        }
        if not normalized_roster:
            payload["status"] = "Wired"
            payload["summary"] = "Agents routes are live, but the roster did not hydrate in this runtime."
            payload["remains_partial"] = "Registry/runtime sources are reachable, but no visible roster items are currently available."
        return payload

    @app.get("/api/first-light")
    async def api_first_light(
        actor: str = "Chris",
        device_id: str = "",
        force: bool = False,
        timezone_name: str = "America/New_York",
    ) -> JSONResponse:
        return _json(
            await asyncio.to_thread(
                runtime.first_light_check,
                actor,
                device_id=device_id,
                force=force,
                timezone_name=timezone_name,
            )
        )

    @app.get("/api/status")
    async def api_status() -> JSONResponse:
        return _json(runtime.status())

    @app.get("/api/approvals")
    async def api_approvals() -> JSONResponse:
        return _json(runtime.list_pending_approvals())

    @app.get("/api/activity")
    async def api_activity() -> JSONResponse:
        activity = list(build_command_center_index().get("activity_feed") or [])
        return _json(activity or runtime.recent_activity())

    @app.post("/api/activity/home-action")
    async def api_activity_home_action(payload: dict[str, Any]) -> JSONResponse:
        action_label = str(payload.get("action") or payload.get("label") or payload.get("title") or "Home action").strip() or "Home action"
        status = str(payload.get("status") or payload.get("result") or "ok").strip() or "ok"
        detail = str(payload.get("detail") or "").strip()
        audit = AuditLog(DEFAULT_AUDIT_ROOT)
        audit.log_event(
            "home-action",
            {
                "actor": str(payload.get("actor") or "Chris").strip() or "Chris",
                "domain": str(payload.get("domain") or "command-center").strip() or "command-center",
                "action": action_label,
                "title": action_label,
                "detail": detail,
                "why_now": str(payload.get("why_now") or detail or "Command center home action updated the current day posture.").strip(),
                "result_summary": str(payload.get("result_summary") or f"Home action result: {status}").strip() or f"Home action result: {status}",
                "related_route": str(payload.get("route") or "/command-center").strip() or "/command-center",
                "route_label": str(payload.get("route_label") or "Open Related Surface").strip() or "Open Related Surface",
                "succeeded": bool(payload.get("succeeded", True)),
                "source_kind": "home-action",
            },
        )
        return _json({"status": "recorded", "entry_type": "home-action", "action": action_label})

    @app.post("/api/activity/operator-action")
    async def api_activity_operator_action(payload: dict[str, Any]) -> JSONResponse:
        action_label = str(payload.get("action") or payload.get("label") or payload.get("title") or "Operator action").strip() or "Operator action"
        status = str(payload.get("status") or payload.get("result") or "ok").strip() or "ok"
        detail = str(payload.get("detail") or "").strip()
        audit = AuditLog(DEFAULT_AUDIT_ROOT)
        audit.log_event(
            "operator-action",
            {
                "actor": str(payload.get("actor") or "Chris").strip() or "Chris",
                "domain": str(payload.get("domain") or "command-center").strip() or "command-center",
                "action": action_label,
                "title": str(payload.get("title") or action_label).strip() or action_label,
                "detail": detail,
                "why_now": str(payload.get("why_now") or detail or "Command center operator action updated a shared workflow surface.").strip(),
                "result_summary": str(payload.get("result_summary") or f"Operator action result: {status}").strip() or f"Operator action result: {status}",
                "related_route": str(payload.get("route") or "/command-center").strip() or "/command-center",
                "route_label": str(payload.get("route_label") or "Open Related Surface").strip() or "Open Related Surface",
                "related_kind": str(payload.get("related_kind") or "activity").strip() or "activity",
                "related_label": str(payload.get("related_label") or action_label).strip() or action_label,
                "succeeded": bool(payload.get("succeeded", True)),
                "source_kind": "operator-action",
            },
        )
        return _json({"status": "recorded", "entry_type": "operator-action", "action": action_label})

    @app.get("/api/open-loops")
    async def api_open_loops(actor: str = "Chris", limit: int = 30) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.unified_open_loops, actor, limit))

    @app.get("/api/today-board")
    async def api_today_board(request: Request, actor: str = "Chris", device_id: str = "") -> JSONResponse:
        current_host = request.headers.get("host", "") if device_id else ""
        current_origin = str(request.base_url).rstrip("/") if device_id else ""
        return _json(
            await asyncio.to_thread(
                runtime.today_board,
                actor,
                device_id=device_id,
                current_host=current_host,
                current_origin=current_origin,
            )
        )

    @app.get("/api/cadence-review")
    async def api_cadence_review(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.cadence_review, actor))

    @app.get("/api/cognitive")
    async def api_cognitive(actor: str = "Chris", include_graph: bool = True) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.cognitive_snapshot, actor, include_graph=include_graph))

    @app.get("/api/cognitive/world-state")
    async def api_cognitive_world_state(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.world_state_view, actor))

    @app.post("/api/open-loops/action")
    async def api_open_loops_action(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.apply_open_loop_action(
                str(payload.get("actor", "Chris")),
                domain=str(payload.get("domain", "")),
                item_id=str(payload.get("item_id", "")),
                action=str(payload.get("action", "")),
                until=str(payload.get("until", "")),
                note=str(payload.get("note", "")),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        action_label = str(payload.get("action", "")).strip().replace("-", " ").title() or "Apply Open-Loop Action"
        title = str(payload.get("item_title") or payload.get("title") or payload.get("item_id") or "Open loop").strip() or "Open loop"
        status = "ok" if bool(result.get("ok", True)) else "error"
        route = str(payload.get("route") or "/command-center").strip() or "/command-center"
        route_label = str(payload.get("route_label") or "Open Related Surface").strip() or "Open Related Surface"
        domain = str(payload.get("activity_domain") or payload.get("source_module") or "command-center").strip() or "command-center"
        summary = str(result.get("record", {}).get("status") or result.get("action") or status).strip() if isinstance(result.get("record"), dict) else str(result.get("action") or status).strip()
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": str(payload.get("actor") or result.get("actor") or "Chris").strip() or "Chris",
                "domain": domain,
                "action": action_label,
                "title": title,
                "detail": str(payload.get("item_summary") or payload.get("note") or f"Applied {action_label.lower()} to {title}.").strip(),
                "why_now": str(payload.get("why_now") or "Daily Brief follow-through moved a live open-loop item forward.").strip(),
                "result_summary": str(payload.get("result_summary") or f"Open-loop result: {summary}").strip() or f"Open-loop result: {summary}",
                "related_route": route,
                "route_label": route_label,
                "related_kind": str(payload.get("related_kind") or "open-loop").strip() or "open-loop",
                "related_label": str(payload.get("related_label") or title).strip() or title,
                "succeeded": bool(result.get("ok", True)),
                "source_kind": "operator-action",
            },
        )
        await _broadcast_dashboard("open-loops-updated")
        return _json(result)

    @app.get("/api/voice-settings")
    async def api_voice_settings() -> JSONResponse:
        return _json(voice_settings.describe())

    @app.get("/api/voice-options")
    async def api_voice_options() -> JSONResponse:
        return _json(voice_settings.voice_options())

    @app.get("/api/accounts")
    async def api_accounts() -> JSONResponse:
        return _json(runtime.account_registry_snapshot())

    @app.get("/api/identity")
    async def api_identity() -> JSONResponse:
        return _json(runtime.identity_overview())

    @app.get("/api/connected-devices")
    async def api_connected_devices(request: Request, current_device_id: str = "") -> JSONResponse:
        return _json(
            runtime.connected_devices_snapshot(
                current_device_id=current_device_id,
                current_host=request.headers.get("host", ""),
                current_origin=str(request.base_url).rstrip("/"),
            )
        )

    @app.get("/api/current-device")
    async def api_current_device(request: Request, device_id: str = "") -> JSONResponse:
        return _json(
            runtime.current_device_snapshot(
                device_id=device_id,
                current_host=request.headers.get("host", ""),
                current_origin=str(request.base_url).rstrip("/"),
            )
        )

    @app.get("/api/runtime-service")
    async def api_runtime_service() -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.runtime_service_status))

    @app.get("/api/persona-snapshot")
    async def api_persona_snapshot(actor: str = "Chris", device_id: str = "", refresh: bool = False) -> JSONResponse:
        return _json(runtime.build_persona_snapshot(actor, device_id=device_id, refresh=refresh))

    @app.get("/api/location-settings")
    async def api_location_settings() -> JSONResponse:
        return _json(location_settings.describe())

    def _save_settings_profile_preferences(
        payload: dict[str, Any],
        *,
        actor_name: str = "Chris",
    ) -> dict[str, Any]:
        from .user_profile import load_profile, save_profile

        actor_name = str(actor_name or "Chris").strip() or "Chris"
        actor = runtime.get_actor(actor_name)
        subject_user_id = str(payload.get("subject_user_id") or actor.user_id or "chris").strip() or "chris"
        updates: dict[str, Any] = {}
        for key in ("notifications", "privacy", "dashboard"):
            value = payload.get(key)
            if isinstance(value, dict):
                updates[key] = value
        if not updates:
            raise ValueError("No settings profile updates were provided.")

        saved = save_profile(subject_user_id, updates)
        latest = load_profile(subject_user_id)
        detail_parts: list[str] = []
        notifications = latest.get("notifications") if isinstance(latest.get("notifications"), dict) else {}
        privacy = latest.get("privacy") if isinstance(latest.get("privacy"), dict) else {}
        dashboard = latest.get("dashboard") if isinstance(latest.get("dashboard"), dict) else {}
        detail_parts.append("approval alerts on" if bool(notifications.get("approvals")) else "approval alerts off")
        detail_parts.append("health alerts on" if bool(notifications.get("health_alerts")) else "health alerts off")
        detail_parts.append("chronicle private" if bool(privacy.get("private_chronicle")) else "chronicle shareable")
        detail_parts.append("health sharing on" if bool(privacy.get("share_health_with_family")) else "health sharing off")
        if hasattr(runtime, "_invalidate_snapshot_cache"):
            with suppress(Exception):
                runtime._invalidate_snapshot_cache(
                    actor_name,
                    surfaces=("dashboard", "today_board", "cognitive", "shell_state", "proactive_state"),
                )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor_name,
                "domain": "settings",
                "action": "Save Profile Defaults",
                "title": subject_user_id,
                "detail": f"Settings updated profile defaults for {subject_user_id}: {', '.join(detail_parts)}.",
                "why_now": "Settings updated the live profile posture used by JARVIS routes and Apple clients.",
                "result_summary": "Profile defaults saved.",
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "profile-settings",
                "related_label": subject_user_id,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Settings",
            reason=f"Settings profile defaults were updated for {subject_user_id}.",
            route="/settings-center",
            actor=actor_name.lower(),
        )
        return {
            "ok": True,
            "message": "Profile defaults updated.",
            "settings": {
                "subject_user_id": subject_user_id,
                "notifications": dict(latest.get("notifications") or {}),
                "privacy": dict(latest.get("privacy") or {}),
                "dashboard": dict(latest.get("dashboard") or {}),
                "updated_at": str(saved.get("updated_at") or latest.get("updated_at") or ""),
            },
            "focus": focus,
        }

    def _save_settings_account_preferences(
        account_id: str,
        payload: dict[str, Any],
        *,
        actor_name: str = "Chris",
    ) -> dict[str, Any]:
        actor_name = str(actor_name or "Chris").strip() or "Chris"
        updates = {
            key: payload.get(key)
            for key in ("label", "login_hint", "status", "notes")
            if key in payload
        }
        if not updates:
            raise ValueError("No account updates were provided.")
        try:
            result = runtime.update_personal_account(account_id, updates)
        except KeyError as exc:
            raise ValueError("Account not found.") from exc

        account = dict(result.get("account") or {})
        label = str(account.get("label") or account_id).strip() or account_id
        provider = str(account.get("provider") or "account").strip() or "account"
        status = str(account.get("status") or "planned").strip() or "planned"
        login_hint = str(account.get("login_hint") or "").strip()
        detail_parts = [f"{provider.title()} account posture saved as {status.replace('_', ' ')}."]
        if login_hint:
            detail_parts.append(f"Login hint set to {login_hint}.")
        notes = str(account.get("notes") or "").strip()
        if notes:
            detail_parts.append(notes)
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor_name,
                "domain": "settings",
                "action": "Save Account Controls",
                "title": label,
                "detail": " ".join(detail_parts),
                "why_now": "Settings updated the live account posture used by JARVIS connectors and Apple clients.",
                "result_summary": f"Settings account controls saved for {label}.",
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "settings-account",
                "related_label": label,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Settings",
            reason=f"Settings account controls were updated for {label}.",
            route="/settings-center",
            actor=actor_name.lower(),
        )
        return {
            "ok": True,
            "message": result.get("message") or f"Updated account '{label}'.",
            "account": account,
            "registry": result.get("registry") or runtime.account_registry_snapshot(),
            "focus": focus,
        }

    def _disconnect_settings_account(
        account_id: str,
        *,
        actor_name: str = "Chris",
    ) -> dict[str, Any]:
        actor_name = str(actor_name or "Chris").strip() or "Chris"
        result = runtime.disconnect_account(account_id)
        if not bool(result.get("ok", False)):
            raise ValueError(str(result.get("message") or "Account disconnect failed."))
        account = dict(result.get("account") or {})
        label = str(account.get("label") or account_id).strip() or account_id
        provider = str(account.get("provider") or "account").strip() or "account"
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor_name,
                "domain": "settings",
                "action": "Disconnect Account",
                "title": label,
                "detail": f"Settings disconnected the {provider.title()} account and returned it to planned posture.",
                "why_now": "Settings needed to pause or reset a live account connector without leaving the module route.",
                "result_summary": f"{label} disconnected from {provider.title()}.",
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "settings-account",
                "related_label": label,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Settings",
            reason=f"Settings disconnected the {label} account.",
            route="/settings-center",
            actor=actor_name.lower(),
        )
        return {
            "ok": True,
            "message": result.get("message") or f"Disconnected {label}.",
            "account": account,
            "focus": focus,
            "registry": runtime.account_registry_snapshot(),
        }

    def _save_settings_connector_preferences(
        account_id: str,
        payload: dict[str, Any],
        *,
        actor_name: str = "Chris",
    ) -> dict[str, Any]:
        actor_name = str(actor_name or "Chris").strip() or "Chris"
        updates = {
            key: payload.get(key)
            for key in ("service_scope", "status", "notes")
            if key in payload
        }
        if not updates:
            raise ValueError("No connector updates were provided.")
        try:
            result = runtime.update_personal_account(account_id, updates)
        except KeyError as exc:
            raise ValueError("Account not found.") from exc

        account = dict(result.get("account") or {})
        label = str(account.get("label") or account_id).strip() or account_id
        provider = str(account.get("provider") or "account").strip() or "account"
        service_scope = str(account.get("service_scope") or "mail_calendar").strip() or "mail_calendar"
        status = str(account.get("status") or "planned").strip() or "planned"
        notes = str(account.get("notes") or "").strip()
        detail_parts = [
            f"{provider.title()} connector scope saved as {service_scope.replace('_', ' / ')}.",
            f"Connector posture is now {status.replace('_', ' ')}.",
        ]
        if notes:
            detail_parts.append(notes)
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor_name,
                "domain": "settings",
                "action": "Save Connector Controls",
                "title": label,
                "detail": " ".join(detail_parts),
                "why_now": "Settings refined a live connector scope and stabilization plan without leaving the module route.",
                "result_summary": f"Connector controls saved for {label}.",
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "settings-connector",
                "related_label": label,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Settings",
            reason=f"Settings connector controls were updated for {label}.",
            route="/settings-center",
            actor=actor_name.lower(),
        )
        return {
            "ok": True,
            "message": result.get("message") or f"Updated connector controls for '{label}'.",
            "account": account,
            "registry": result.get("registry") or runtime.account_registry_snapshot(),
            "focus": focus,
        }

    def _save_settings_family_member_preferences(
        user_id: str,
        payload: dict[str, Any],
        *,
        actor_name: str = "Chris",
    ) -> dict[str, Any]:
        actor_name = str(actor_name or "Chris").strip() or "Chris"
        updates = {
            "user_id": user_id,
            **{
                key: payload.get(key)
                for key in ("role", "permissions", "trust_level", "preferred_tone", "privacy_boundary", "notes")
                if key in payload
            },
        }
        if len(updates) <= 1:
            raise ValueError("No family identity updates were provided.")
        try:
            result = runtime.save_identity_member(updates)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        member = dict(result.get("member") or {})
        label = str(member.get("display_name") or user_id).strip() or user_id
        role = str(member.get("role") or "member").strip() or "member"
        permissions = str(member.get("permissions") or "member").strip() or "member"
        trust_level = str(member.get("trust_level") or "standard").strip() or "standard"
        preferred_tone = str(member.get("preferred_tone") or "").strip()
        detail_parts = [
            f"{label} now holds the {role.replace('_', ' ')} role with {permissions.replace('_', ' ')} permissions.",
            f"Trust posture is {trust_level.replace('_', ' ')}.",
        ]
        if preferred_tone:
            detail_parts.append(f"Tone: {preferred_tone}.")
        notes = str(member.get("notes") or "").strip()
        if notes:
            detail_parts.append(notes)
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor_name,
                "domain": "settings",
                "action": "Save Family Identity",
                "title": label,
                "detail": " ".join(detail_parts),
                "why_now": "Settings refined a live family identity profile so role, tone, and permissions stay aligned across JARVIS surfaces.",
                "result_summary": f"Family identity saved for {label}.",
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "settings-family-identity",
                "related_label": label,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Settings",
            reason=f"Settings family identity was updated for {label}.",
            route="/settings-center",
            actor=actor_name.lower(),
        )
        return {
            "ok": True,
            "message": f"Saved family identity for {label}.",
            "member": member,
            "identity": result.get("identity") or runtime.identity_overview(),
            "focus": focus,
        }

    async def _build_settings_module_payload() -> dict[str, Any]:
        try:
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()
        except Exception:
            generated_at = ""

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Settings now has a dedicated module route with live voice, location, account controls, and permissions posture inside JARVIS.",
            "what_became_real": "Settings & Permissions is now a standalone app module instead of only a shell packet with scattered APIs behind it.",
            "remains_partial": "Deeper cross-surface continuity still needs follow-on slices.",
            "voice": {},
            "voice_options": {},
            "location": {},
            "accounts": {"accounts": []},
            "connector_lane": [],
            "google": {},
            "identity": {"members": [], "devices": []},
            "permissions": {
                "governance": {},
                "notifications": {},
                "privacy": {},
                "dashboard": {},
                "insights": [],
                "rhythms": [],
            },
            "recent_activity": [],
            "counts": {
                "account_count": 0,
                "connected_account_count": 0,
                "connector_attention_count": 0,
                "saved_location_count": 0,
                "insight_count": 0,
                "recent_activity_count": 0,
            },
            "proof_paths": {
                "module_route": "/settings-center",
                "module_api": "/api/settings/module",
                "voice_api": "/api/voice-settings",
                "location_api": "/api/location-settings",
                "activity_api": "/api/activity/operator-action",
                "voice_options_api": "/api/voice-options",
                "accounts_api": "/api/accounts",
                "identity_api": "/api/identity",
                "google_summary_api": "/api/google/summary",
                "google_client_api": "/api/google/client-secret",
                "google_disconnect_api": "/api/google/disconnect",
                "personalization_api": "/api/personalization/settings",
                "profile_settings_api": "/api/settings/profile",
                "account_settings_api": "/api/settings/account",
                "connector_settings_api": "/api/settings/connector",
                "family_identity_api": "/api/settings/family-member",
                "account_disconnect_api": "/api/settings/accounts/{account_id}/disconnect",
            },
            "errors": [],
        }

        try:
            payload["voice"] = voice_settings.describe()
            payload["voice_options"] = voice_settings.voice_options()
        except Exception as exc:
            payload["errors"].append(f"voice: {exc}")

        try:
            location = location_settings.describe()
            payload["location"] = location
            payload["counts"]["saved_location_count"] = len(list(location.get("saved_locations") or []))
        except Exception as exc:
            payload["errors"].append(f"location: {exc}")

        try:
            accounts = runtime.account_registry_snapshot()
            payload["accounts"] = accounts
            account_items = list(accounts.get("accounts") or [])
            payload["counts"]["account_count"] = len(account_items)
            payload["counts"]["connected_account_count"] = sum(
                1
                for item in account_items
                if str(item.get("status", "")).strip().lower() == "connected"
                or str((item.get("connection") or {}).get("status", "")).strip().lower() == "connected"
                or str(item.get("connection", "")).strip().lower() == "connected"
            )
            connector_lane = []
            connector_attention_count = 0
            for item in account_items:
                status = str(item.get("status") or "planned").strip().lower() or "planned"
                connection = item.get("connection")
                if isinstance(connection, dict):
                    connection_status = str(connection.get("status") or connection.get("state") or "").strip().lower()
                else:
                    connection_status = str(connection or "").strip().lower()
                needs_attention = status not in {"connected", "active"} or connection_status not in {"", "connected", "active", "ready"}
                if needs_attention:
                    connector_attention_count += 1
                connector_lane.append(
                    {
                        "account_id": str(item.get("account_id") or item.get("id") or ""),
                        "label": str(item.get("label") or item.get("owner_display_name") or item.get("account_id") or "Account"),
                        "provider": str(item.get("provider") or "unknown"),
                        "status": status,
                        "status_label": status.replace("_", " ").title(),
                        "service_scope": str(item.get("service_scope") or "mail_calendar"),
                        "service_scope_label": str(item.get("service_scope") or "mail_calendar").replace("_", " / ").replace("mail", "Mail").replace("calendar", "Calendar"),
                        "notes": str(item.get("notes") or ""),
                        "connection_status": connection_status or status,
                        "needs_attention": needs_attention,
                    }
                )
            payload["connector_lane"] = connector_lane
            payload["counts"]["connector_attention_count"] = connector_attention_count
        except Exception as exc:
            payload["errors"].append(f"accounts: {exc}")

        try:
            payload["google"] = runtime.google_workspace_summary()
        except Exception as exc:
            payload["errors"].append(f"google: {exc}")

        try:
            payload["identity"] = runtime.identity_overview()
        except Exception as exc:
            payload["errors"].append(f"identity: {exc}")

        payload["recent_activity"] = _module_recent_activity(route="/settings-center", domain="settings")
        payload["counts"]["recent_activity_count"] = len(payload["recent_activity"])

        try:
            from .user_profile import load_profile

            actor = runtime.get_actor("Chris")
            profile = load_profile(actor.user_id)
            personalization = runtime._personalization_snapshot(actor)
            permissions = payload["permissions"]
            permissions["governance"] = dict(personalization.get("governance") or {})
            permissions["insights"] = list(personalization.get("insights") or [])[:6]
            permissions["rhythms"] = list(personalization.get("rhythms") or [])[:4]
            permissions["notifications"] = dict(profile.get("notifications") or {})
            permissions["privacy"] = dict(profile.get("privacy") or {})
            permissions["dashboard"] = dict(profile.get("dashboard") or {})
            payload["counts"]["insight_count"] = len(permissions["insights"])
        except Exception as exc:
            payload["errors"].append(f"permissions: {exc}")

        if payload["errors"]:
            payload["status"] = "Wired"
            if not payload["voice"] and not payload["location"]:
                payload["available"] = False
                payload["summary"] = "Settings center route is live, but key settings sources did not fully hydrate."
                payload["remains_partial"] = "Live settings sources still need repair or population in this runtime."
            else:
                payload["summary"] = "Settings center route is live with partial voice, location, account, and permissions posture."
                payload["remains_partial"] = "Some settings or permissions sources still failed to hydrate; inspect the payload preview for details."
        return payload

    @app.get("/api/settings/module")
    async def api_settings_module() -> JSONResponse:
        return _json(await _build_settings_module_payload())

    @app.post("/api/settings/profile")
    async def api_save_settings_profile(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = _save_settings_profile_preferences(payload, actor_name=str(payload.get("actor") or "Chris"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await _broadcast_dashboard("settings-profile.updated")
        return _json(result)

    @app.post("/api/settings/account")
    async def api_save_settings_account(payload: dict[str, Any]) -> JSONResponse:
        account_id = str(payload.get("account_id") or "").strip()
        if not account_id:
            raise HTTPException(status_code=400, detail="Account id is required.")
        try:
            result = _save_settings_account_preferences(
                account_id,
                payload,
                actor_name=str(payload.get("actor") or "Chris"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await _broadcast_dashboard("settings-account.updated")
        return _json(result)

    @app.post("/api/settings/connector")
    async def api_save_settings_connector(payload: dict[str, Any]) -> JSONResponse:
        account_id = str(payload.get("account_id") or "").strip()
        if not account_id:
            raise HTTPException(status_code=400, detail="Account id is required.")
        try:
            result = _save_settings_connector_preferences(
                account_id,
                payload,
                actor_name=str(payload.get("actor") or "Chris"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await _broadcast_dashboard("settings-connector.updated")
        return _json(result)

    @app.post("/api/settings/family-member")
    async def api_save_settings_family_member(payload: dict[str, Any]) -> JSONResponse:
        user_id = str(payload.get("user_id") or "").strip().lower()
        if not user_id:
            raise HTTPException(status_code=400, detail="User id is required.")
        try:
            result = _save_settings_family_member_preferences(
                user_id,
                payload,
                actor_name=str(payload.get("actor") or "Chris"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await _broadcast_dashboard("settings-family.updated")
        return _json(result)

    @app.post("/api/settings/accounts/{account_id}/disconnect")
    async def api_disconnect_settings_account(account_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
        payload = payload or {}
        try:
            result = _disconnect_settings_account(
                account_id,
                actor_name=str(payload.get("actor") or "Chris"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await _broadcast_dashboard("settings-account.disconnected")
        return _json(result)

    @app.get("/api/design-review-state")
    async def api_design_review_state() -> JSONResponse:
        return _json(runtime.design_review_state())

    @app.get("/api/google/status")
    async def api_google_status() -> JSONResponse:
        return _json(runtime.google_workspace_status())

    @app.get("/api/google/summary")
    async def api_google_summary() -> JSONResponse:
        return _json(runtime.google_workspace_summary())

    @app.get("/api/microsoft/status")
    async def api_microsoft_status() -> JSONResponse:
        return _json(runtime.microsoft_graph_status())

    @app.get("/api/microsoft/summary")
    async def api_microsoft_summary() -> JSONResponse:
        return _json(runtime.microsoft_graph_summary())

    @app.get("/api/google/bridge/status")
    async def api_google_bridge_status() -> JSONResponse:
        return _json(runtime.google_bridge_status())

    @app.get("/api/family-calendar")
    async def api_family_calendar() -> JSONResponse:
        return _json(runtime.family_calendar_summary())

    @app.get("/api/merged-calendar")
    async def api_merged_calendar(limit: int = 20) -> JSONResponse:
        return _json({"events": runtime.merged_calendar_events(limit=limit), "summary": runtime.merged_calendar_brief(limit=min(limit, 6))})

    @app.get("/api/strategic-brief")
    async def api_strategic_brief(actor: str = "Chris") -> JSONResponse:
        return _json({"actor": actor, "brief": runtime.daily_strategic_brief(actor)})

    @app.get("/api/cross-domain-brief")
    async def api_cross_domain_brief(actor: str = "Chris", topic: str = "") -> JSONResponse:
        return _json({"actor": actor, "topic": topic, "brief": runtime.cross_domain_synthesis_brief(actor, topic)})

    @app.get("/api/wealth-leverage-summary")
    async def api_wealth_leverage_summary(limit: int = 10) -> JSONResponse:
        return _json(runtime.wealth_support.summary(limit=limit))

    @app.get("/api/autonomous-workstreams")
    async def api_autonomous_workstreams(actor: str = "Chris", lane_id: str = "") -> JSONResponse:
        return _json(runtime.autonomous_workstreams_snapshot(actor, lane_id=lane_id))

    @app.get("/api/workstreams")
    async def api_workstreams(actor: str = "Chris", workstream_id: str = "") -> JSONResponse:
        return _json(runtime.workstreams_snapshot(actor, workstream_id=workstream_id))

    @app.get("/api/workstreams/{workstream_id}")
    async def api_workstream(workstream_id: str, actor: str = "Chris") -> JSONResponse:
        try:
            result = runtime.workstream_snapshot(actor, workstream_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/autonomous-workstreams/{lane_id}/runs")
    async def api_autonomous_workstream_runs(
        lane_id: str,
        actor: str = "Chris",
        limit: int = Query(12, ge=1, le=100),
    ) -> JSONResponse:
        try:
            result = runtime.autonomous_workstream_runs(actor, lane_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/workstreams/{workstream_id}/runs")
    async def api_workstream_runs(
        workstream_id: str,
        actor: str = "Chris",
        limit: int = Query(12, ge=1, le=100),
    ) -> JSONResponse:
        try:
            result = runtime.autonomous_workstream_runs(actor, workstream_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/workstreams/{workstream_id}/queue")
    async def api_workstream_queue(
        workstream_id: str,
        actor: str = "Chris",
        limit: int = Query(40, ge=1, le=200),
    ) -> JSONResponse:
        try:
            result = runtime.workstream_queue(actor, workstream_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/workstreams/{workstream_id}/artifacts")
    async def api_workstream_artifacts(
        workstream_id: str,
        actor: str = "Chris",
        limit: int = Query(60, ge=1, le=200),
    ) -> JSONResponse:
        try:
            result = runtime.workstream_artifacts(actor, workstream_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/workstreams/{workstream_id}/approvals")
    async def api_workstream_approvals(
        workstream_id: str,
        actor: str = "Chris",
        limit: int = Query(60, ge=1, le=200),
    ) -> JSONResponse:
        try:
            result = runtime.workstream_approvals(actor, workstream_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/growth-schema")
    async def api_growth_schema() -> JSONResponse:
        return _json(runtime.growth_schema())

    @app.get("/api/growth-state")
    async def api_growth_state(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.growth_state_snapshot(actor))

    @app.get("/api/finance-state")
    async def api_finance_state(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.finance_state_snapshot(actor))

    @app.get("/api/finance-review")
    async def api_finance_review(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.finance_review(actor))

    @app.get("/api/wealth-review")
    async def api_wealth_review(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.wealth_review(actor))

    # ------------------------------------------------------------------
    # Epic 13: Financial Intelligence endpoints (Fisk / Howard Stark / Daredevil)
    # ------------------------------------------------------------------

    @app.get("/api/finance/snapshot")
    async def api_finance_snapshot() -> JSONResponse:
        """Fisk's wealth snapshot — net worth, cashflow, passive income, goals."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            return _json(await asyncio.to_thread(fi.fisk.get_wealth_snapshot))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/monthly")
    async def api_finance_monthly(month: str = "") -> JSONResponse:
        """Monthly financial summary."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            return _json(await asyncio.to_thread(fi.fisk.get_monthly_summary, month or None))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/health")
    async def api_finance_health() -> JSONResponse:
        """Fisk's financial health assessment (score, actions)."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            return _json(await asyncio.to_thread(fi.fisk.assess_financial_health))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/passive-income")
    async def api_finance_passive_income() -> JSONResponse:
        """Howard Stark's passive income dashboard."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            return _json(await asyncio.to_thread(fi.howard.get_passive_income_dashboard))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/finance/passive-income/log")
    async def api_finance_log_payment(payload: dict[str, Any]) -> JSONResponse:
        """Log a passive income payment received."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            stream_id = str(payload.get("stream_id", ""))
            amount = float(payload.get("amount", 0.0))
            date = str(payload.get("date", "")) or None
            notes = str(payload.get("notes", ""))
            if not stream_id:
                raise HTTPException(status_code=400, detail="stream_id is required")
            await asyncio.to_thread(fi.howard.log_payment, stream_id, amount, date, notes)
            return _json({"ok": True, "stream_id": stream_id, "amount": amount})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/finance/passive-income/streams")
    async def api_finance_add_stream(payload: dict[str, Any]) -> JSONResponse:
        """Add a passive income stream."""
        try:
            import uuid as _uuid
            from .financial_intelligence import get_finance, PassiveIncomeStream
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            stream = PassiveIncomeStream(
                stream_id=str(payload.get("stream_id", "")) or str(_uuid.uuid4()),
                name=str(payload.get("name", "")),
                stream_type=str(payload.get("stream_type", "other")),
                monthly_average=float(payload.get("monthly_average", 0.0)),
                last_payment=float(payload.get("last_payment", 0.0)),
                last_payment_date=str(payload.get("last_payment_date", "")),
                ytd_total=float(payload.get("ytd_total", 0.0)),
                active=bool(payload.get("active", True)),
                platform=str(payload.get("platform", "")),
                tracking_url=str(payload.get("tracking_url", "")),
                notes=str(payload.get("notes", "")),
                growth_rate=float(payload.get("growth_rate", 0.0)),
            )
            await asyncio.to_thread(fi.howard.add_stream, stream)
            return _json({"ok": True, "stream_id": stream.stream_id})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/compliance")
    async def api_finance_compliance() -> JSONResponse:
        """Upcoming compliance and tax deadlines."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            return _json(await asyncio.to_thread(fi.daredevil.check_compliance_calendar))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/finance/compliance")
    async def api_finance_add_compliance(payload: dict[str, Any]) -> JSONResponse:
        """Add a compliance item."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            title = str(payload.get("title", ""))
            date = str(payload.get("date", ""))
            if not title or not date:
                raise HTTPException(status_code=400, detail="title and date are required")
            item = await asyncio.to_thread(
                fi.daredevil.add_compliance_item,
                title,
                date,
                str(payload.get("notes", "")),
                str(payload.get("item_type", "custom")),
                bool(payload.get("recurs_annually", False)),
            )
            return _json({"ok": True, "item": item})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/budget")
    async def api_finance_budget(month: str = "") -> JSONResponse:
        """Monthly budget status."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            return _json(await asyncio.to_thread(fi.budget.get_monthly_budget_status, month or None))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/finance/transactions")
    async def api_finance_log_transaction(payload: dict[str, Any]) -> JSONResponse:
        """Log a financial transaction."""
        try:
            import uuid as _uuid
            import datetime as _dt
            from .financial_intelligence import get_finance, Transaction
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            txn = Transaction(
                transaction_id=str(payload.get("transaction_id", "")) or str(_uuid.uuid4()),
                account_id=str(payload.get("account_id", "")),
                date=str(payload.get("date", "")) or _dt.datetime.now().strftime("%Y-%m-%d"),
                description=str(payload.get("description", "")),
                amount=float(payload.get("amount", 0.0)),
                category=str(payload.get("category", "other")),
                subcategory=str(payload.get("subcategory", "")),
                notes=str(payload.get("notes", "")),
                is_passive_income=bool(payload.get("is_passive_income", False)),
                source_agent=str(payload.get("source_agent", "manual")),
            )
            await asyncio.to_thread(fi.budget.log_transaction, txn)
            return _json({"ok": True, "transaction_id": txn.transaction_id})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/goals")
    async def api_finance_goals() -> JSONResponse:
        """List financial goals."""
        try:
            from dataclasses import asdict as _asdict
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            goals = await asyncio.to_thread(fi._store.load_goals)
            return _json({"goals": [_asdict(g) for g in goals]})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/finance/goals")
    async def api_finance_upsert_goal(payload: dict[str, Any]) -> JSONResponse:
        """Add or update a financial goal."""
        try:
            import uuid as _uuid
            import datetime as _dt
            from dataclasses import asdict as _asdict
            from .financial_intelligence import get_finance, FinancialGoal
            fi = get_finance()
            if fi is None:
                raise HTTPException(status_code=503, detail="Financial intelligence not initialised")
            goal = FinancialGoal(
                goal_id=str(payload.get("goal_id", "")) or str(_uuid.uuid4()),
                title=str(payload.get("title", "")),
                goal_type=str(payload.get("goal_type", "savings")),
                target_amount=float(payload.get("target_amount", 0.0)),
                current_amount=float(payload.get("current_amount", 0.0)),
                target_date=str(payload.get("target_date", "")),
                priority=int(payload.get("priority", 3)),
                status=str(payload.get("status", "active")),
                notes=str(payload.get("notes", "")),
                created_at=str(payload.get("created_at", "")) or _dt.datetime.now(_dt.timezone.utc).isoformat(),
                last_reviewed=str(payload.get("last_reviewed", "")),
            )
            await asyncio.to_thread(fi._store.upsert_goal, goal)
            return _json({"ok": True, "goal": _asdict(goal)})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/finance/status")
    async def api_finance_status() -> JSONResponse:
        """Orchestrator dashboard status (for Already Working zone)."""
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is None:
                return _json({"ok": False, "detail": "Financial intelligence not initialised"})
            return _json(await asyncio.to_thread(fi.get_dashboard_status))
        except Exception as exc:
            return _json({"ok": False, "error": str(exc)})

    @app.get("/api/marketing-state")
    async def api_marketing_state(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.marketing_state_snapshot(actor))

    @app.get("/api/marketing-review")
    async def api_marketing_review(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.marketing_review(actor))

    @app.get("/api/pipeline-state")
    async def api_pipeline_state(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.pipeline_state_snapshot(actor))

    @app.get("/api/pipeline-review")
    async def api_pipeline_review(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.pipeline_review(actor))

    @app.get("/api/work-lifecycle")
    async def api_work_lifecycle(actor: str = "Chris", limit: int = Query(28, ge=1, le=100)) -> JSONResponse:
        return _json(runtime.work_lifecycle_snapshot(actor, limit=limit))

    @app.post("/api/work-lifecycle/{work_id}/action")
    async def api_work_lifecycle_action(work_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        action = str(payload.get("action", "")).strip()
        note = str(payload.get("note", "")).strip()
        if not action:
            raise HTTPException(status_code=400, detail="Action is required")
        try:
            result = runtime.apply_work_lifecycle_action(actor, work_id, action, note=note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/work-lifecycle/{work_id}/inspector")
    async def api_work_lifecycle_inspector(work_id: str, actor: str = "Chris") -> JSONResponse:
        try:
            result = runtime.work_lifecycle_inspector_snapshot(actor, work_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/work-lifecycle/{work_id}/artifact/{record_id}")
    async def api_work_lifecycle_artifact(work_id: str, record_id: str, actor: str = "Chris") -> JSONResponse:
        try:
            result = runtime.resolve_work_lifecycle_artifact(actor, work_id, record_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not result.get("ok", False):
            raise HTTPException(status_code=404, detail=result.get("message", "Artifact not found"))
        return _json(result)

    @app.get("/api/operating-policy")
    async def api_operating_policy() -> JSONResponse:
        return _json(runtime.operating_policy_snapshot())

    @app.get("/api/self-mutation-constitution")
    async def api_self_mutation_constitution() -> JSONResponse:
        return _json(runtime.self_mutation_constitution_snapshot())

    @app.get("/api/guardian-status")
    async def api_guardian_status() -> JSONResponse:
        return _json(runtime.guardian_status_snapshot())

    @app.get("/api/runtime/posture")
    async def api_runtime_posture() -> JSONResponse:
        return _json(runtime.runtime_posture_snapshot())

    @app.get("/api/chamber-home")
    async def api_chamber_home(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.chamber_home_snapshot, actor))

    @app.get("/api/self-improvement")
    async def api_self_improvement() -> JSONResponse:
        return _json(runtime.self_improvement_snapshot())

    @app.post("/api/self-improvement/run")
    async def api_self_improvement_run(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        return _json(runtime.background_self_improvement_run(actor))

    @app.post("/api/self-improvement/jobs/{job_id}/execute")
    async def api_self_improvement_execute(job_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        triggered_by = str(payload.get("triggered_by", "manual")).strip() or "manual"
        try:
            result = runtime.run_self_improvement_job(actor, job_id, triggered_by=triggered_by)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/self-improvement/jobs/{job_id}/sandbox-execute")
    async def api_self_improvement_sandbox_execute(job_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        triggered_by = str(payload.get("triggered_by", "sandbox-run")).strip() or "sandbox-run"
        try:
            result = runtime.enqueue_self_improvement_sandbox_job(actor, job_id, triggered_by=triggered_by)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/agent-workspace/{agent_id}")
    async def api_agent_workspace(agent_id: str) -> JSONResponse:
        if agent_id == "herald":
            return _json(runtime.herald_workspace_snapshot())
        if agent_id == "veronica":
            return _json(runtime.veronica_workspace_snapshot())
        if agent_id == "ultron":
            return _json(runtime.ultron_workspace_snapshot())
        if agent_id == "nick-fury":
            return _json(runtime.nick_fury_workspace_snapshot())
        raise HTTPException(status_code=404, detail="Unknown agent workspace")

    @app.get("/api/life-agents")
    async def api_life_agents() -> JSONResponse:
        return _json(runtime.life_agent_snapshot())

    @app.get("/api/openviking/status")
    async def api_openviking_status() -> JSONResponse:
        return _json(runtime.openviking_status())

    @app.get("/api/summary")
    async def api_summary() -> JSONResponse:
        return _json(_summary_payload())

    @app.get("/api/agents")
    async def api_agents() -> JSONResponse:
        return _json(runtime.background_agent_status())

    @app.get("/api/agent-runtime")
    async def api_agent_runtime() -> JSONResponse:
        return _json(runtime.agent_runtime_snapshot())

    @app.post("/api/agent-runtime/control")
    async def api_agent_runtime_control(payload: dict[str, Any]) -> JSONResponse:
        agent_id = str(payload.get("agent_id", "")).strip()
        action = str(payload.get("action", "")).strip()
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        if not action:
            raise HTTPException(status_code=400, detail="action is required")
        try:
            result = runtime.control_agent_runtime(
                agent_id,
                action,
                actor_name=str(payload.get("actor", "Chris")).strip() or "Chris",
                reason=str(payload.get("reason", "")).strip(),
                execution_lane=str(payload.get("execution_lane", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/agent-runtime/heartbeat")
    async def api_agent_runtime_heartbeat(payload: dict[str, Any]) -> JSONResponse:
        agent_id = str(payload.get("agent_id", "")).strip()
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        try:
            result = runtime.record_agent_runtime_heartbeat(
                agent_id,
                actor_name=str(payload.get("actor", "system")).strip() or "system",
                note=str(payload.get("note", "")).strip(),
                run_id=str(payload.get("run_id", "")).strip(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/agent-registry")
    async def api_agent_registry() -> JSONResponse:
        return _json(runtime.agent_registry_snapshot())

    @app.get("/api/memory-curator")
    async def api_memory_curator() -> JSONResponse:
        return _json(runtime.memory_curator_snapshot())

    @app.get("/api/shared-doctrine")
    async def api_shared_doctrine(actor: str = "", refresh: bool = False) -> JSONResponse:
        return _json(runtime.shared_doctrine_snapshot(actor_name=actor, refresh=refresh))

    @app.post("/api/shared-doctrine/synthesize")
    async def api_shared_doctrine_synthesize(payload: dict[str, Any]) -> JSONResponse:
        auto_promote = bool(payload.get("auto_promote", True))
        promoted_by = str(payload.get("promoted_by", "manual-refresh"))
        return _json(runtime.synthesize_shared_doctrine(auto_promote=auto_promote, promoted_by=promoted_by))

    @app.post("/api/shared-doctrine/candidates/{candidate_id}/promote")
    async def api_shared_doctrine_promote(candidate_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.promote_doctrine_candidate(
                candidate_id,
                promoted_by=str(payload.get("promoted_by", "Chris")),
                basis=str(payload.get("basis", "approved-by-user")),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/shared-doctrine/candidates/{candidate_id}/dismiss")
    async def api_shared_doctrine_dismiss(candidate_id: str, payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.dismiss_doctrine_candidate(
                candidate_id,
                dismissed_by=str(payload.get("dismissed_by", "Chris")),
                reason=str(payload.get("reason", "")),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/catalyst-overview")
    async def api_catalyst_overview() -> JSONResponse:
        return _json(runtime.catalyst_overview())

    @app.get("/api/catalyst-live-state")
    async def api_catalyst_live_state() -> JSONResponse:
        return _json(runtime.catalyst_live_workspace())

    @app.get("/api/catalyst/module")
    async def api_catalyst_module() -> JSONResponse:
        return _json(await _build_catalyst_module_payload())

    @app.get("/api/workshop/module")
    async def api_workshop_module() -> JSONResponse:
        return _json(await _build_workshop_module_payload())

    @app.get("/api/router/capabilities")
    async def api_router_capabilities() -> JSONResponse:
        return _json(runtime.interface_router.capability_manifests())

    @app.post("/api/router/intent")
    async def api_router_intent(payload: dict[str, Any]) -> JSONResponse:
        return _json(
            runtime.interface_router.classify_intent(
                str(payload.get("request_text", "")),
                context=dict(payload.get("context") or {}),
            )
        )

    @app.post("/api/router/handoff")
    async def api_router_handoff(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.interface_router.create_handoff(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result, status_code=202)

    @app.post("/api/router/result")
    async def api_router_result(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.interface_router.post_result(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result, status_code=202)

    @app.get("/api/router/session/{request_id}")
    async def api_router_session(request_id: str) -> JSONResponse:
        try:
            result = runtime.interface_router.session_view(request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/chronicle/capabilities")
    async def api_chronicle_capabilities() -> JSONResponse:
        return _json(runtime.interface_router.system_manifest("chronicle"))

    @app.post("/api/chronicle/handoff")
    async def api_chronicle_handoff(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.interface_router.create_handoff({**payload, "target_system": "chronicle"})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result, status_code=202)

    @app.get("/api/chronicle/session/{request_id}")
    async def api_chronicle_session(request_id: str) -> JSONResponse:
        try:
            result = runtime.interface_router.system_session_view("chronicle", request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/chronicle/result/{request_id}")
    async def api_chronicle_result(request_id: str) -> JSONResponse:
        try:
            result = runtime.interface_router.result_view(request_id, source_system="chronicle")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/faith/daily-word")
    async def api_faith_daily_word() -> JSONResponse:
        payload = await _build_faith_daily_word_payload()
        return _json(payload)

    @app.get("/api/faith/agents")
    async def api_faith_agents() -> JSONResponse:
        payload = await _build_faith_agents_payload()
        return _json(payload)

    @app.get("/api/faith/module")
    async def api_faith_module() -> JSONResponse:
        return _json(await _build_faith_module_payload())

    @app.post("/api/faith/chat")
    async def api_faith_chat(payload: dict[str, Any]) -> JSONResponse:
        try:
            from .faith_agents import chat as _faith_chat, get_agent as _get_faith_agent

            agent_id = str(payload.get("agent_id") or "").strip().lower()
            messages = payload.get("messages") or []
            passage = str(payload.get("passage") or "").strip()
            if not agent_id:
                raise HTTPException(status_code=400, detail="agent_id is required")
            if not isinstance(messages, list) or not messages:
                raise HTTPException(status_code=400, detail="messages are required")
            reply = await _faith_chat(agent_id=agent_id, messages=messages, runtime=runtime, passage=passage)
            agent = _get_faith_agent(agent_id) or {}
            reply_text = str(reply or "").strip()
            if not reply_text:
                agent_name = str(agent.get("name") or agent_id.title())
                detail = (
                    f"{agent_name} is connected, but no faith response was returned just now. "
                    "Please try again."
                )
                return _json(
                    {
                        "ok": False,
                        "available": False,
                        "reply": "",
                        "detail": detail,
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                    }
                )
            return _json(
                {
                    "ok": True,
                    "reply": reply_text,
                    "agent_id": agent_id,
                    "agent_name": str(agent.get("name") or agent_id.title()),
                }
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Faith chat unavailable: {exc}") from exc

    @app.get("/api/catalyst/capabilities")
    async def api_catalyst_capabilities() -> JSONResponse:
        return _json(runtime.interface_router.system_manifest("catalyst"))

    # ------------------------------------------------------------------
    # Epic 8: Catalyst Bridge endpoints (Mantis / bidirectional context)
    # ------------------------------------------------------------------

    @app.get("/api/catalyst/handoffs/pending")
    async def api_catalyst_handoffs_pending() -> JSONResponse:
        """Return pending context packets waiting to be picked up by Catalyst."""
        try:
            from .catalyst_bridge import get_catalyst_bridge as _gcb
            bridge = _gcb()
            if bridge is None:
                return _json({"pending": [], "count": 0})
            pending = [ctx.to_dict() for ctx in bridge.get_pending_handoffs()]
            return _json({"pending": pending, "count": len(pending)})
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/handoffs/{context_id}/sent")
    async def api_catalyst_handoff_mark_sent(context_id: str) -> JSONResponse:
        """Catalyst calls this to acknowledge receipt of a handoff context."""
        try:
            from .catalyst_bridge import get_catalyst_bridge as _gcb
            bridge = _gcb()
            if bridge is None:
                raise HTTPException(status_code=503, detail="Catalyst bridge not initialised")
            bridge.mark_handoff_sent(context_id)
            return _json({"ok": True, "context_id": context_id})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/receive/completion")
    async def api_catalyst_receive_completion(payload: dict[str, Any]) -> JSONResponse:
        """Catalyst → JARVIS: a task/project has been marked complete."""
        try:
            from .catalyst_bridge import get_catalyst_bridge as _gcb
            bridge = _gcb()
            if bridge is None:
                raise HTTPException(status_code=503, detail="Catalyst bridge not initialised")
            bridge.receive_completion(payload)
            return _json({"ok": True})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/receive/project-update")
    async def api_catalyst_receive_project_update(payload: dict[str, Any]) -> JSONResponse:
        """Catalyst → JARVIS: project status update."""
        try:
            from .catalyst_bridge import get_catalyst_bridge as _gcb
            bridge = _gcb()
            if bridge is None:
                raise HTTPException(status_code=503, detail="Catalyst bridge not initialised")
            bridge.receive_project_update(payload)
            return _json({"ok": True})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/receive/signal")
    async def api_catalyst_receive_signal(payload: dict[str, Any]) -> JSONResponse:
        """Catalyst → JARVIS: a signal needing JARVIS intelligence."""
        try:
            from .catalyst_bridge import get_catalyst_bridge as _gcb
            bridge = _gcb()
            if bridge is None:
                raise HTTPException(status_code=503, detail="Catalyst bridge not initialised")
            bridge.receive_signal(payload)
            return _json({"ok": True})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/catalyst/status")
    async def api_catalyst_mantis_status() -> JSONResponse:
        """Return Mantis workflow status for the Already Working zone."""
        try:
            from .catalyst_bridge import get_mantis as _gm
            mantis = _gm()
            if mantis is None:
                return _json({"agent": "Mantis", "status": "not_initialised"})
            return _json(mantis.get_workflow_status())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/package/morning")
    async def api_catalyst_package_morning(payload: dict[str, Any]) -> JSONResponse:
        """Manually trigger a morning handoff package (bypasses scheduler)."""
        try:
            from .catalyst_bridge import get_mantis as _gm
            mantis = _gm()
            if mantis is None:
                raise HTTPException(status_code=503, detail="Mantis not initialised")
            briefing_packet = payload if payload else {}
            ctx = mantis.on_morning_briefing_ready(briefing_packet)
            if ctx is None:
                raise HTTPException(status_code=500, detail="Could not package morning handoff")
            return _json(ctx.to_dict(), status_code=201)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/package/meeting")
    async def api_catalyst_package_meeting(payload: dict[str, Any]) -> JSONResponse:
        """Package meeting prep context. Body: {"event": {...}, "minutes_until": 60}"""
        try:
            from .catalyst_bridge import get_mantis as _gm
            mantis = _gm()
            if mantis is None:
                raise HTTPException(status_code=503, detail="Mantis not initialised")
            event = payload.get("event", {})
            if not event:
                raise HTTPException(status_code=400, detail="'event' field is required")
            minutes_until = int(payload.get("minutes_until", 60))
            ctx = mantis.on_meeting_approaching(event, minutes_until=minutes_until)
            if ctx is None:
                raise HTTPException(status_code=500, detail="Could not package meeting prep")
            return _json(ctx.to_dict(), status_code=201)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/extract-actions")
    async def api_catalyst_extract_actions(payload: dict[str, Any]) -> JSONResponse:
        """Extract action items from conversation text. Body: {"text": str}"""
        try:
            from .catalyst_bridge import extract_action_items as _extract
            text = str(payload.get("text", "")).strip()
            if not text:
                raise HTTPException(status_code=400, detail="'text' field is required")
            items = _extract(text)
            return _json({"items": items, "count": len(items)})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/catalyst/handoff")
    async def api_catalyst_handoff(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.interface_router.create_handoff({**payload, "target_system": "catalyst"})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result, status_code=202)

    @app.get("/api/catalyst/run/{request_id}")
    async def api_catalyst_run(request_id: str) -> JSONResponse:
        try:
            result = runtime.interface_router.system_session_view("catalyst", request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/catalyst/result/{request_id}")
    async def api_catalyst_result(request_id: str) -> JSONResponse:
        try:
            result = runtime.interface_router.result_view(request_id, source_system="catalyst")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/google/account/{account_id}")
    async def api_google_account(account_id: str) -> JSONResponse:
        return _json(runtime.google_account_snapshot(account_id))

    @app.get("/api/explainability")
    async def api_explainability(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.explainability_snapshot(actor))

    @app.get("/api/approval-history")
    async def api_approval_history() -> JSONResponse:
        return _json(runtime.approval_history())

    @app.get("/api/stewardship-lanes")
    async def api_stewardship_lanes() -> JSONResponse:
        return _json({"lanes": runtime.list_stewardship_lanes()})

    @app.get("/api/agent-supervision/contracts")
    async def api_agent_supervision_contracts() -> JSONResponse:
        return _json({"contracts": runtime.list_agent_supervision_contracts()})

    @app.get("/api/agent-supervision/traces")
    async def api_agent_supervision_traces(limit: int = 50) -> JSONResponse:
        return _json({"items": runtime.list_supervision_traces(limit=limit)})

    @app.get("/api/agent-supervision/reviews")
    async def api_agent_supervision_reviews(limit: int = 50) -> JSONResponse:
        return _json({"items": runtime.list_supervision_reviews(limit=limit)})

    @app.post("/api/agent-supervision/assess")
    async def api_agent_supervision_assess(payload: dict[str, Any]) -> JSONResponse:
        return _json(
            runtime.assess_supervised_action(
                agent_id=str(payload.get("agent_id", "")),
                action_type=str(payload.get("action_type", "")),
                requested_outcome=str(payload.get("requested_outcome", "")),
                trust_zone_id=str(payload.get("trust_zone_id", "")),
                lane_id=str(payload.get("lane_id", "")),
                arena_id=str(payload.get("arena_id", "")),
                context=dict(payload.get("context", {})),
            )
        )

    @app.post("/api/agent-supervision/review")
    async def api_agent_supervision_review(payload: dict[str, Any]) -> JSONResponse:
        return _json(
            runtime.record_supervision_review(
                decision_id=str(payload.get("decision_id", "")),
                reviewer=str(payload.get("reviewer", "")),
                outcome=str(payload.get("outcome", "")),
                notes=str(payload.get("notes", "")),
                rollback_executed=bool(payload.get("rollback_executed", False)),
                doctrine_ready=payload.get("doctrine_ready"),
            )
        )

    @app.post("/api/agent-supervision/doctrine/refresh")
    async def api_agent_supervision_doctrine_refresh(payload: dict[str, Any] | None = None) -> JSONResponse:
        payload = payload or {}
        return _json(runtime.refresh_supervision_doctrine(synthesized_by=str(payload.get("synthesized_by", "system-steward"))))

    @app.get("/api/mode")
    async def api_mode() -> JSONResponse:
        return _json(runtime.active_mode())

    @app.get("/api/message-drafts")
    async def api_message_drafts() -> JSONResponse:
        return _json(runtime.list_message_drafts())

    @app.get("/api/trust-zones")
    async def api_trust_zones() -> JSONResponse:
        return _json({"zones": runtime.list_trust_zones()})

    @app.post("/api/trust-zones")
    async def api_create_trust_zone(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.create_trust_zone(payload), status_code=201)

    @app.get("/api/resource-arenas")
    async def api_resource_arenas() -> JSONResponse:
        return _json({"arenas": runtime.list_resource_arenas()})

    @app.post("/api/resource-arenas")
    async def api_create_resource_arena(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.create_resource_arena(payload), status_code=201)

    @app.get("/api/authority-stages")
    async def api_authority_stages() -> JSONResponse:
        return _json({"stages": runtime.list_authority_stages()})

    @app.get("/api/promotion-records")
    async def api_promotion_records(limit: int = 50) -> JSONResponse:
        return _json({"records": runtime.list_promotion_records(limit=limit)})

    @app.get("/api/promotion-recommendations")
    async def api_promotion_recommendations(limit: int = 12) -> JSONResponse:
        return _json({"recommendations": runtime.list_promotion_recommendations(limit=limit)})

    @app.post("/api/promotion/evaluate")
    async def api_promotion_evaluate(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.evaluate_promotion_claim(
                subject_kind=str(payload.get("subject_kind", "")),
                subject_id=str(payload.get("subject_id", "")),
                target_stage=str(payload.get("target_stage", "")),
                actor=str(payload.get("actor", "system")),
                basis=str(payload.get("basis", "promotion-evaluation")),
                human_consent=bool(payload.get("human_consent", False)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/promotion/apply")
    async def api_promotion_apply(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.apply_promotion_decision(
                subject_kind=str(payload.get("subject_kind", "")),
                subject_id=str(payload.get("subject_id", "")),
                target_stage=str(payload.get("target_stage", "")),
                actor=str(payload.get("actor", "system-steward")),
                basis=str(payload.get("basis", "promotion-application")),
                human_consent=bool(payload.get("human_consent", False)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/promotion/apply-recommendations")
    async def api_promotion_apply_recommendations(payload: dict[str, Any] | None = None) -> JSONResponse:
        payload = payload or {}
        result = runtime.apply_promotion_recommendations(
            actor=str(payload.get("actor", "system-steward")),
            basis=str(payload.get("basis", "auto-apply-promotion-recommendations")),
            limit=int(payload.get("limit", 12) or 12),
        )
        return _json(result)

    @app.get("/api/stage/queue")
    async def api_stage_queue() -> JSONResponse:
        return _json({"items": runtime.list_stage_queue()})

    @app.get("/api/voice-notes")
    async def api_voice_notes() -> JSONResponse:
        return _json(runtime.list_voice_note_tasks())

    @app.get("/api/anomalies")
    async def api_anomalies() -> JSONResponse:
        return _json(runtime.anomaly_watch())

    @app.get("/api/security-incidents")
    async def api_security_incidents() -> JSONResponse:
        return _json(runtime.list_security_incidents())

    @app.get("/api/overnight-review")
    async def api_overnight_review() -> JSONResponse:
        return _json(runtime.overnight_review())

    @app.get("/api/home-overview")
    async def api_home_overview() -> JSONResponse:
        return _json(runtime.home_overview())

    @app.get("/api/environment-status")
    async def api_environment_status(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.environment_status_snapshot(actor))

    @app.get("/api/leak-monitor")
    async def api_leak_monitor() -> JSONResponse:
        return _json(runtime.leak_monitor())

    @app.get("/api/cold-storage-monitor")
    async def api_cold_storage_monitor() -> JSONResponse:
        return _json(runtime.cold_storage_monitor())

    @app.get("/api/outage-readiness")
    async def api_outage_readiness() -> JSONResponse:
        return _json(runtime.outage_readiness())

    @app.get("/api/perception-overview")
    async def api_perception_overview() -> JSONResponse:
        return _json(runtime.perception_overview())

    @app.get("/api/vision-state")
    async def api_vision_state(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.vision_state_snapshot(actor))

    @app.post("/api/vision/analyze")
    async def api_vision_analyze(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.analyze_camera_frame(
                str(payload.get("actor", "Chris")),
                str(payload.get("prompt", "")),
                str(payload.get("image_data_url", "")),
                camera_label=str(payload.get("camera_label", "Desk Camera")),
                mode=str(payload.get("mode", "describe")),
                compare_to_capture_id=str(payload.get("compare_to_capture_id", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/vision/calibration")
    async def api_vision_calibration(payload: dict[str, Any]) -> JSONResponse:
        calibration = dict(payload.get("calibration") or {})
        if not calibration:
            raise HTTPException(status_code=400, detail="calibration is required")
        try:
            result = runtime.save_vision_calibration(
                str(payload.get("actor", "Chris")),
                str(payload.get("camera_label", "Desk Camera")),
                calibration,
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/vision/measure")
    async def api_vision_measure(payload: dict[str, Any]) -> JSONResponse:
        measurement = dict(payload.get("measurement") or {})
        calibration = dict(payload.get("calibration") or {})
        if not measurement:
            raise HTTPException(status_code=400, detail="measurement is required")
        if not calibration:
            raise HTTPException(status_code=400, detail="calibration is required")
        try:
            result = runtime.measure_camera_frame(
                str(payload.get("actor", "Chris")),
                str(payload.get("image_data_url", "")),
                str(payload.get("camera_label", "Desk Camera")),
                calibration,
                measurement,
                object_label=str(payload.get("object_label", "")),
                detail=str(payload.get("detail", "")),
                selection=dict(payload.get("selection") or {}),
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/privacy-update")
    async def api_privacy_update(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.update_privacy_state(
                str(payload.get("kind", "")),
                str(payload.get("target", "")),
                enabled=payload.get("enabled"),
                muted=payload.get("muted"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.get("/api/privacy-state")
    async def api_privacy_state() -> JSONResponse:
        return _json(runtime.privacy_state())

    @app.get("/api/memory-overview")
    async def api_memory_overview(viewer: str = "Chris") -> JSONResponse:
        return _json(runtime.memory_overview(viewer))

    @app.get("/api/memory-review")
    async def api_memory_review(
        viewer: str = "Chris",
        type: str = "",  # noqa: A002
        owner: str = "",
        project: str = "",
    ) -> JSONResponse:
        return _json(runtime.review_memory(viewer, memory_type=type, owner=owner, project=project))

    @app.get("/api/memory-proposals")
    async def api_memory_proposals(status: str = "", viewer: str = "Chris") -> JSONResponse:
        try:
            runtime.get_actor(viewer)
        except KeyError:
            raise HTTPException(status_code=403, detail=f"Unknown viewer: {viewer!r}")
        return _json(runtime.memory_proposals(status=status))

    @app.get("/api/memory-profiles")
    async def api_memory_profiles(viewer: str = "Chris", subject_user_id: str = "") -> JSONResponse:
        return _json(runtime.memory_profile_snapshot(viewer, subject_user_id=subject_user_id))

    @app.get("/api/learning-review")
    async def api_learning_review(viewer: str = "Chris", subject_user_id: str = "") -> JSONResponse:
        return _json(runtime.learning_review_snapshot(viewer, subject_user_id=subject_user_id))

    @app.post("/api/memory-curation/run")
    async def api_memory_curation_run() -> JSONResponse:
        return _json(runtime.run_memory_curation())

    @app.get("/api/printer-status")
    async def api_printer_status() -> JSONResponse:
        return _json(runtime.printer_status())

    @app.get("/api/workshop-inspections")
    async def api_workshop_inspections() -> JSONResponse:
        return _json(runtime.list_workshop_inspections())

    @app.get("/api/cad-packages")
    async def api_cad_packages() -> JSONResponse:
        return _json(runtime.list_cad_packages())

    @app.get("/api/concept-studio/sessions")
    async def api_concept_studio_sessions(limit: int = 10) -> JSONResponse:
        return _json(runtime.list_concept_sessions(limit=limit))

    @app.get("/api/concept-studio/session/{session_id}")
    async def api_concept_studio_session(session_id: str) -> JSONResponse:
        session = runtime.get_concept_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Concept studio session not found")
        return _json(session)

    @app.get("/api/workshop-machine-options")
    async def api_workshop_machine_options() -> JSONResponse:
        return _json(runtime.workshop_machine_options())

    @app.get("/api/model-forge/package/{package_id}")
    async def api_model_forge_package(package_id: str) -> JSONResponse:
        package = runtime.get_cad_package(package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Model forge package not found")
        return _json(package)

    @app.get("/api/model-forge/package/{package_id}/model")
    async def api_model_forge_model(package_id: str) -> Response:
        package = runtime.get_cad_package(package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Model forge package not found")
        model_path = str(package.get("model_path", "")).strip()
        if not model_path:
            raise HTTPException(status_code=404, detail="This package has no exported model")
        path = (Path.cwd() / model_path).resolve()
        try:
            path.relative_to((Path.cwd() / "data" / "workshop" / "model_forge").resolve())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Model path is outside the model forge root") from exc
        if not path.exists():
            raise HTTPException(status_code=404, detail="Exported model file not found on disk")
        return FileResponse(path, media_type="model/stl", filename=path.name)

    @app.get("/api/model-forge/package/{package_id}/download/{kind}")
    async def api_model_forge_download(package_id: str, kind: str) -> Response:
        try:
            if kind == "slicer-pack":
                path, filename = runtime.slicer_pack_archive(package_id)
                return FileResponse(path, media_type="application/zip", filename=filename)
            path, filename = runtime.package_artifact_path(package_id, kind)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        media_type = {
            "stl": "model/stl",
            "step": "application/step",
            "3mf": "model/3mf",
            "scad": "text/plain; charset=utf-8",
            "cadquery": "text/plain; charset=utf-8",
        }.get(kind, "application/octet-stream")
        return FileResponse(path, media_type=media_type, filename=filename)

    @app.post("/api/model-forge/package/{package_id}/open-in-slicer")
    async def api_model_forge_open_in_slicer(package_id: str, request: Request) -> JSONResponse:
        payload = await request.json()
        try:
            result = runtime.open_package_in_slicer(package_id, str(payload.get("slicer_app", "")))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except subprocess.CalledProcessError as exc:
            raise HTTPException(status_code=500, detail=f"Slicer handoff failed: {exc}") from exc
        return _json(result)

    @app.get("/api/print-preps")
    async def api_print_preps() -> JSONResponse:
        return _json(runtime.list_print_preps())

    @app.get("/api/vendor-preps")
    async def api_vendor_preps() -> JSONResponse:
        return _json(runtime.list_vendor_preps())

    @app.get("/api/child-boundaries")
    async def api_child_boundaries(actor: str = "") -> JSONResponse:
        return _json(runtime.child_boundaries(actor_name=actor or None))

    @app.get("/api/tutoring-summaries")
    async def api_tutoring_summaries(viewer: str = "Rebekah", child: str = "", limit: int = 10) -> JSONResponse:
        return _json(runtime.tutoring_summaries(viewer, child_name=child, limit=limit))

    @app.get("/api/device-boundaries")
    async def api_device_boundaries(child: str = "", limit: int = 10) -> JSONResponse:
        return _json(runtime.list_device_boundaries(child_name=child, limit=limit))

    @app.post("/api/respond")
    async def api_respond(
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        attachments = payload.get("attachments")
        attachment_records = [dict(item) for item in attachments if isinstance(item, dict)] if isinstance(attachments, list) else []
        request_text = str(payload.get("request", ""))
        attachment_context = _upload_prompt_fragment(attachment_records)
        if attachment_context:
            request_text = f"{request_text}\n\n{attachment_context}".strip()
        result = runtime.converse(
            str(payload.get("actor", "Chris")),
            str(payload.get("room", "office")),
            request_text,
            conversation_id=str(payload.get("conversation_id", "")),
            source=str(payload.get("source", "shell")),
        )
        background_tasks.add_task(_broadcast_dashboard, "response.completed")
        return _json(result)

    @app.post("/api/mode-transition")
    async def api_mode_transition(
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        result = runtime.transition_mode(
            str(payload.get("actor", "Chris")),
            str(payload.get("mode", "ambient-associate")),
            str(payload.get("reason", "Manual mode update from JARVIS shell.")),
        )
        background_tasks.add_task(_broadcast_dashboard, "mode.updated")
        return _json(result)

    # ── Adaptive Layout endpoints ────────────────────────────────────────────

    @app.get("/api/layout/state")
    async def api_layout_state() -> JSONResponse:
        try:
            payload = await asyncio.to_thread(_layout_engine.get_state_payload, runtime)
            return _json(payload)
        except Exception as exc:  # pragma: no cover
            return _json({"error": str(exc), "mode": "morning_brief", "layout": {"hero": [], "priority": [], "ambient": []}, "alerts": [], "card_weights": {}, "modes": {}})

    @app.post("/api/layout/mode")
    async def api_layout_set_mode(
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        mode   = str(payload.get("mode", "")).strip()
        manual = bool(payload.get("manual", True))
        result = await asyncio.to_thread(_layout_engine.set_mode, mode, manual=manual)
        background_tasks.add_task(_broadcast_dashboard, "layout.mode_changed")
        return _json(result)

    @app.post("/api/layout/interact")
    async def api_layout_interact(payload: dict[str, Any]) -> JSONResponse:
        card_id = str(payload.get("card_id", "")).strip()
        mode    = str(payload.get("mode", "morning_brief")).strip()
        action  = str(payload.get("action", "click")).strip()
        await asyncio.to_thread(_layout_engine.log_interaction, card_id, mode, action)
        return _json({"ok": True})

    @app.post("/api/design-review-state")
    async def api_save_design_review_state(
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        result = runtime.save_design_review_state(payload)
        background_tasks.add_task(_broadcast_dashboard, "design-review.updated")
        return _json(result)

    @app.post("/api/voice-settings")
    async def api_save_voice_settings(payload: dict[str, Any]) -> JSONResponse:
        settings = voice_settings.save(payload)
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        provider = str(payload.get("tts_provider") or settings.tts_provider or "").strip() or "voice provider"
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "settings",
                "action": "Save Voice Settings",
                "title": provider,
                "detail": f"Voice settings saved with provider {provider}.",
                "why_now": "Settings updated the live voice runtime configuration.",
                "result_summary": f"Voice provider set to {provider}.",
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "voice-settings",
                "related_label": provider,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        return _json(
            {
                "message": "Voice settings updated.",
                "settings": voice_settings.describe(),
                "options": voice_settings.voice_options(),
                "saved": settings.to_dict(),
            }
        )

    @app.post("/api/location-settings")
    async def api_save_location_settings(payload: dict[str, Any]) -> JSONResponse:
        action = str(payload.get("action", "")).strip()
        preferred_location_id = str(payload.get("preferred_location_id", "")).strip()
        try:
            if action == "add_location":
                state = location_settings.add_location(payload)
            elif action == "set_preferred" or (not action and preferred_location_id):
                state = location_settings.set_preferred_location(
                    preferred_location_id or str(payload.get("location_id", "")).strip()
                )
            elif action == "save_device_location":
                state = location_settings.save_device_location(payload)
            else:
                state = location_settings.save(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        preferred_id = str(
            payload.get("preferred_location_id")
            or payload.get("location_id")
            or (state.get("preferred_location_id") if isinstance(state, dict) else "")
            or ""
        ).strip()
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "settings",
                "action": "Save Location Settings",
                "title": preferred_id or "Preferred location",
                "detail": (
                    f"Location settings saved with preferred location {preferred_id}."
                    if preferred_id
                    else "Location settings saved."
                ),
                "why_now": "Settings updated the live location posture used by the shell.",
                "result_summary": (
                    f"Preferred location set to {preferred_id}."
                    if preferred_id
                    else "Location settings updated."
                ),
                "related_route": "/settings-center",
                "route_label": "Open Settings",
                "related_kind": "location-settings",
                "related_label": preferred_id or "Preferred location",
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        return _json({"ok": True, "state": location_settings.describe(), "saved": state})

    @app.post("/api/accounts")
    async def api_save_account(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.save_personal_account(payload))

    @app.post("/api/identity/member")
    async def api_save_identity_member(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.save_identity_member(payload))

    @app.post("/api/identity/device")
    async def api_save_identity_device(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.save_identity_device(payload))

    @app.post("/api/identity/devices/prune")
    async def api_prune_identity_devices(payload: dict[str, Any] | None = None) -> JSONResponse:
        payload = payload or {}
        return _json(
            runtime.prune_identity_devices(
                stale_days=int(payload.get("stale_days", 7) or 7),
                prune_test_like=bool(payload.get("prune_test_like", True)),
            )
        )

    @app.post("/api/identity/session")
    async def api_bind_identity_session(request: Request, payload: dict[str, Any]) -> JSONResponse:
        payload = {
            **payload,
            "last_host": str(payload.get("last_host", "")).strip() or request.headers.get("host", ""),
            "last_origin": str(payload.get("last_origin", "")).strip() or str(request.base_url).rstrip("/"),
        }
        return _json(runtime.bind_identity_session(payload))

    @app.post("/api/identity/service")
    async def api_save_identity_service(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.save_service_identity(payload))

    @app.post("/api/persona-refresh")
    async def api_persona_refresh(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        device_id = str(payload.get("device_id", ""))
        return _json(runtime.build_persona_snapshot(actor, device_id=device_id, refresh=True))

    @app.post("/api/learning/proposals/{proposal_id}")
    async def api_learning_proposal_decision(proposal_id: str, payload: dict[str, Any]) -> JSONResponse:
        viewer = str(payload.get("viewer", "")).strip()
        if not viewer:
            raise HTTPException(status_code=422, detail="viewer is required")
        try:
            runtime.get_actor(viewer)
        except KeyError:
            raise HTTPException(status_code=403, detail=f"Unknown viewer: {viewer!r}")
        decision = str(payload.get("decision", "approved"))
        return _json(runtime.resolve_memory_proposal(proposal_id, decision))

    @app.post("/api/learning/facts/{fact_id}")
    async def api_learning_fact_status(fact_id: str, payload: dict[str, Any]) -> JSONResponse:
        viewer = str(payload.get("viewer", "Chris"))
        status = str(payload.get("status", "retired"))
        return _json(runtime.update_profile_fact_status(viewer, fact_id, status))

    @app.post("/api/personalization/settings")
    async def api_personalization_settings(payload: dict[str, Any]) -> JSONResponse:
        viewer = str(payload.get("viewer", "Chris"))
        subject_user_id = str(payload.get("subject_user_id", ""))
        updates = dict(payload.get("updates", {}))
        return _json(runtime.update_personalization_settings(viewer, subject_user_id, updates))

    @app.post("/api/personalization/insights/{insight_id}")
    async def api_personalization_insight_status(insight_id: str, payload: dict[str, Any]) -> JSONResponse:
        viewer = str(payload.get("viewer", "Chris"))
        subject_user_id = str(payload.get("subject_user_id", ""))
        status = str(payload.get("status", "suppressed"))
        return _json(runtime.update_personalization_insight_status(viewer, subject_user_id, insight_id, status))

    @app.post("/api/google/client-secret")
    async def api_google_client_secret(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.google_save_client_secret(str(payload.get("client_secret_json", ""))))

    @app.post("/api/google/bridge/export")
    async def api_google_bridge_export() -> JSONResponse:
        return _json(runtime.google_bridge_export())

    @app.post("/api/google/bridge/import")
    async def api_google_bridge_import(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.google_bridge_import(str(payload.get("account_id", ""))))

    @app.post("/api/google/disconnect")
    async def api_google_disconnect() -> JSONResponse:
        return _json(runtime.google_disconnect())

    @app.post("/api/accounts/{account_id}/disconnect")
    async def api_google_disconnect_account(account_id: str) -> JSONResponse:
        return _json(runtime.disconnect_account(account_id))

    @app.post("/api/life-agents")
    async def api_save_life_agent(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.save_life_agent(payload))

    @app.post("/api/life-agents/delete")
    async def api_delete_life_agent(payload: dict[str, Any]) -> JSONResponse:
        return _json(runtime.delete_life_agent(str(payload.get("agent_id", ""))))

    @app.post("/api/life-party")
    async def api_life_party(payload: dict[str, Any]) -> JSONResponse:
        result = runtime.life_party_mode(
            str(payload.get("actor", "Chris")),
            str(payload.get("room", "office")),
            str(payload.get("request", "")),
            [str(entry).strip() for entry in payload.get("agents", []) if str(entry).strip()],
        )
        return _json(result)

    @app.post("/api/wealth-leverage")
    async def api_wealth_leverage(payload: dict[str, Any]) -> JSONResponse:
        result = runtime.wealth_leverage_workflow(
            str(payload.get("actor", "Chris")),
            str(payload.get("room", "office")),
            str(payload.get("request", "")),
        )
        return _json(result)

    @app.post("/api/autonomous-workstreams/{lane_id}/run")
    async def api_run_autonomous_workstream(lane_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        source = str(payload.get("source", "manual")).strip() or "manual"
        try:
            result = runtime.run_autonomous_workstream(actor, lane_id, source=source)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("autonomous-workstream.run")
        return _json(result)

    @app.post("/api/workstreams/{workstream_id}/run")
    async def api_run_workstream(workstream_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        source = str(payload.get("source", "manual")).strip() or "manual"
        try:
            result = runtime.run_autonomous_workstream(actor, workstream_id, source=source)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("autonomous-workstream.run")
        return _json(result)

    @app.post("/api/autonomous-workstreams/items/{item_id}/review")
    async def api_review_autonomous_workstream_item(item_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        status = str(payload.get("status", "")).strip()
        note = str(payload.get("note", "")).strip()
        next_action = str(payload.get("next_action", "")).strip()
        reviewer = str(payload.get("reviewer", "")).strip()
        if not status:
            raise HTTPException(status_code=400, detail="Status is required")
        try:
            result = runtime.update_autonomous_workstream_item(
                actor,
                item_id,
                status=status,
                note=note,
                next_action=next_action,
                reviewer=reviewer,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("autonomous-workstream.review")
        return _json(result)

    @app.post("/api/workstreams/items/{item_id}/approve")
    async def api_approve_workstream_item(item_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        note = str(payload.get("note", "")).strip()
        try:
            result = runtime.approve_workstream_item(actor, item_id, note=note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("autonomous-workstream.review")
        return _json(result)

    @app.post("/api/workstreams/items/{item_id}/dismiss")
    async def api_dismiss_workstream_item(item_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        note = str(payload.get("note", "")).strip()
        try:
            result = runtime.dismiss_workstream_item(actor, item_id, note=note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("autonomous-workstream.review")
        return _json(result)

    @app.post("/api/workstreams/items/{item_id}/route")
    async def api_route_workstream_item(item_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris")).strip() or "Chris"
        route_to = str(payload.get("route_to", "")).strip()
        note = str(payload.get("note", "")).strip()
        if not route_to:
            raise HTTPException(status_code=400, detail="route_to is required")
        try:
            result = runtime.route_workstream_item(actor, item_id, route_to=route_to, note=note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await _broadcast_dashboard("autonomous-workstream.review")
        return _json(result)

    @app.post("/api/finance-state")
    async def api_save_finance_state(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        patch = dict(payload.get("state", {})) if isinstance(payload.get("state", {}), dict) else {}
        result = runtime.wealth_support.update_finance_state(patch)
        runtime._invalidate_snapshot_cache(actor, surfaces=("finance_review", "finance_state", "wealth_review", "dashboard", "today_board", "cognitive"))
        return _json({"ok": True, "state": result, "finance_state": runtime.finance_state_snapshot(actor)})

    @app.post("/api/finance-review/complete")
    async def api_complete_finance_review(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        note = str(payload.get("note", ""))
        result = runtime.complete_finance_review(actor, note)
        await _broadcast_dashboard("finance-review.completed")
        return _json(result)

    @app.post("/api/marketing-state")
    async def api_save_marketing_state(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        patch = dict(payload.get("state", {})) if isinstance(payload.get("state", {}), dict) else {}
        result = runtime.content_ops.update_marketing_state(patch)
        runtime._invalidate_snapshot_cache(actor, surfaces=("marketing_review", "marketing_state", "dashboard", "today_board", "cognitive"))
        return _json({"ok": True, "state": result, "marketing_state": runtime.marketing_state_snapshot(actor)})

    @app.post("/api/marketing-review/complete")
    async def api_complete_marketing_review(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        note = str(payload.get("note", ""))
        result = runtime.complete_marketing_review(actor, note)
        await _broadcast_dashboard("marketing-review.completed")
        return _json(result)

    @app.post("/api/pipeline-state")
    async def api_save_pipeline_state(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        patch = dict(payload.get("state", {})) if isinstance(payload.get("state", {}), dict) else {}
        result = runtime.catalyst_support.update_pipeline_state(patch)
        runtime._invalidate_snapshot_cache(actor, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return _json({"ok": True, "state": result, "pipeline_state": runtime.pipeline_state_snapshot(actor)})

    @app.post("/api/pipeline-review/complete")
    async def api_complete_pipeline_review(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        review_type = str(payload.get("review_type", "weekly"))
        note = str(payload.get("note", ""))
        result = runtime.complete_pipeline_review(actor, review_type, note)
        await _broadcast_dashboard("pipeline-review.completed")
        return _json(result)

    @app.post("/api/catalyst-hypothesis")
    async def api_catalyst_hypothesis(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        result = runtime.catalyst_hypothesis_generation(
            actor,
            str(payload.get("focus", "")),
            str(payload.get("context", "")),
            lane=str(payload.get("lane", "")),
            supporting_signals=[str(item).strip() for item in payload.get("supporting_signals", []) if str(item).strip()],
            work_id=str(payload.get("work_id", "")),
            source_agent=str(payload.get("source_agent", "")),
        )
        return _json(result)

    @app.post("/api/herald/prepare")
    async def api_herald_prepare(payload: dict[str, Any]) -> JSONResponse:
        return _json(
            runtime.herald_prepare_meeting(
                str(payload.get("actor", "Chris")),
                str(payload.get("event_id", "")),
                str(payload.get("context", "")),
                participants=[str(item).strip() for item in payload.get("participants", []) if str(item).strip()],
                contexts=[str(item).strip() for item in payload.get("contexts", []) if str(item).strip()],
                objective=str(payload.get("objective", "")),
            )
        )

    @app.post("/api/veronica/options")
    async def api_veronica_options(payload: dict[str, Any]) -> JSONResponse:
        return _json(
            runtime.veronica_generate_options(
                str(payload.get("actor", "Chris")),
                str(payload.get("topic", "")),
                channel=str(payload.get("channel", "YouTube")),
                context=str(payload.get("context", "")),
            )
        )

    @app.post("/api/veronica/approve")
    async def api_veronica_approve(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = runtime.veronica_approve_option(
                str(payload.get("actor", "Chris")),
                str(payload.get("option_id", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json(result)

    @app.post("/api/veronica/push-live")
    async def api_veronica_push_live(payload: dict[str, Any]) -> JSONResponse:
        result = runtime.veronica_push_live(str(payload.get("queue_id", "")))
        if not result.get("ok", False):
            raise HTTPException(status_code=404, detail=result.get("message", "Queue item not found"))
        return _json(result)

    @app.post("/api/veronica/export")
    async def api_veronica_export(payload: dict[str, Any]) -> JSONResponse:
        result = runtime.veronica_export(str(payload.get("queue_id", "")))
        if not result.get("ok", False):
            raise HTTPException(status_code=404, detail=result.get("message", "Queue item not found"))
        return _json(result)

    @app.post("/api/tts")
    async def api_tts(payload: dict[str, Any]) -> Response:
        text = str(payload.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        try:
            audio = generate_tts_audio(
                runtime.config,
                text,
                voice_settings=voice_settings.load().to_dict(),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return Response(
            content=audio.data,
            media_type=audio.content_type,
            headers={"X-Jarvis-Tts-Provider": audio.provider},
        )

    # ------------------------------------------------------------------
    # Epic 7: Voice Shell — /api/voice/* endpoints
    # ------------------------------------------------------------------

    @app.post("/api/voice/synthesize")
    async def api_voice_synthesize(payload: dict[str, Any]) -> Response:
        """
        Convert text to audio via Friday's TTS pipeline.
        Request: {"text": str, "actor_id": str}
        Response: audio/mpeg (or audio/wav) stream.
        """
        text = str(payload.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")

        pipeline = get_pipeline()
        friday = get_friday()

        if pipeline is None or friday is None:
            # Fall back to the existing /api/tts handler
            try:
                audio = await asyncio.to_thread(
                    generate_tts_audio,
                    runtime.config,
                    text,
                    voice_settings.load().to_dict(),
                )
            except RuntimeError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            return Response(
                content=audio.data,
                media_type=audio.content_type,
                headers={"X-Jarvis-Tts-Provider": audio.provider},
            )

        voice_text = friday.prepare_for_voice(text)
        try:
            audio_bytes, fmt = await asyncio.to_thread(pipeline.synthesize, voice_text)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Voice synthesis failed: {exc}") from exc

        if not audio_bytes:
            raise HTTPException(status_code=503, detail="No TTS provider available")

        media_type = "audio/mpeg" if fmt == "mp3" else "audio/wav"
        active = pipeline.get_status().get("active_provider", "unknown")
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={"X-Jarvis-Voice-Provider": active},
        )

    @app.get("/api/voice/status")
    async def api_voice_status() -> JSONResponse:
        """Return voice pipeline provider status for diagnostics."""
        pipeline = get_pipeline()
        if pipeline is None:
            return _json({"error": "Voice pipeline not initialised", "state": "idle"})
        return _json(pipeline.get_status())

    @app.post("/api/voice/state")
    async def api_voice_state(payload: dict[str, Any]) -> JSONResponse:
        """Update voice state from the browser when playback starts/ends."""
        state = str(payload.get("state", "idle")).strip().lower()
        pipeline = get_pipeline()
        if pipeline is None:
            return _json({"ok": False, "state": "idle", "error": "Voice pipeline not initialised"})
        try:
            pipeline.set_state(state)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json({"ok": True, "state": pipeline.get_state()})

    @app.get("/api/voice/greeting")
    async def api_voice_greeting() -> JSONResponse:
        """Return a time-appropriate greeting text and the TTS endpoint URL."""
        greeting = get_time_aware_greeting("boss")
        return _json({
            "text": greeting,
            "audio_url": "/api/voice/synthesize",
            "voice_tools": VOICE_TOOL_ALLOWLIST,
            "voice_tools_count": len(VOICE_TOOL_ALLOWLIST),
        })

    @app.get("/api/greet")
    async def api_greet(name: str = "boss") -> JSONResponse:
        """Return a time-aware JARVIS greeting for the given name."""
        return _json({"greeting": get_time_aware_greeting(name)})

    # ── Reminders ────────────────────────────────────────────────
    from .reminders import (
        list_reminders, add_reminder, complete_reminder,
        delete_reminder, snooze_reminder, pending_reminders,
    )

    @app.get("/api/reminders")
    async def api_reminders_list(include_done: bool = False) -> JSONResponse:
        items = list_reminders() if include_done else pending_reminders()
        return _json({"reminders": items, "total": len(items)})

    @app.post("/api/reminders")
    async def api_reminders_add(payload: dict[str, Any]) -> JSONResponse:
        text = (payload.get("text") or "").strip()
        if not text:
            return JSONResponse({"error": "text required"}, status_code=400)
        r = add_reminder(
            text=text,
            due_iso=payload.get("due"),
            priority=payload.get("priority", "normal"),
        )
        return _json({"reminder": r})

    @app.post("/api/reminders/{reminder_id}/complete")
    async def api_reminders_complete(reminder_id: str) -> JSONResponse:
        ok = complete_reminder(reminder_id)
        return _json({"ok": ok})

    @app.delete("/api/reminders/{reminder_id}")
    async def api_reminders_delete(reminder_id: str) -> JSONResponse:
        ok = delete_reminder(reminder_id)
        return _json({"ok": ok})

    @app.post("/api/reminders/{reminder_id}/snooze")
    async def api_reminders_snooze(reminder_id: str, payload: dict[str, Any]) -> JSONResponse:
        new_due = payload.get("due")
        if not new_due:
            return JSONResponse({"error": "due required"}, status_code=400)
        ok = snooze_reminder(reminder_id, new_due)
        return _json({"ok": ok})

    # ── Tasks ─────────────────────────────────────────────────────
    from .tasks import (
        add_task, list_tasks, get_task, update_task,
        complete_task, delete_task, pending_tasks,
    )

    @app.get("/api/tasks")
    async def api_tasks_list(
        include_done: bool = False,
        actor: str | None = None,
        domain: str | None = None,
        priority: str | None = None,
    ) -> JSONResponse:
        items = list_tasks(
            include_done=include_done,
            actor=actor or None,
            domain=domain or None,
            priority=priority or None,
        )
        return _json({"tasks": items, "total": len(items)})

    @app.post("/api/tasks")
    async def api_tasks_add(payload: dict[str, Any]) -> JSONResponse:
        title = (payload.get("title") or "").strip()
        if not title:
            return JSONResponse({"error": "title required"}, status_code=400)
        t = add_task(
            title=title,
            body=payload.get("body", ""),
            priority=payload.get("priority", "normal"),
            due=payload.get("due"),
            actor=payload.get("actor", "chris"),
            domain=payload.get("domain", "personal"),
            source=payload.get("source", "manual"),
            tags=payload.get("tags"),
        )
        return _json({"task": t})

    @app.get("/api/tasks/{task_id}")
    async def api_tasks_get(task_id: str) -> JSONResponse:
        t = get_task(task_id)
        if t is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return _json({"task": t})

    @app.patch("/api/tasks/{task_id}")
    async def api_tasks_update(task_id: str, payload: dict[str, Any]) -> JSONResponse:
        ok = update_task(task_id, **payload)
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found")
        return _json({"ok": True, "task": get_task(task_id)})

    @app.post("/api/tasks/{task_id}/complete")
    async def api_tasks_complete(task_id: str) -> JSONResponse:
        ok = complete_task(task_id)
        return _json({"ok": ok})

    @app.delete("/api/tasks/{task_id}")
    async def api_tasks_delete(task_id: str) -> JSONResponse:
        ok = delete_task(task_id)
        return _json({"ok": ok})

    # ------------------------------------------------------------------
    # Epic 6: Approval & Permission Layer endpoints
    # ------------------------------------------------------------------

    @app.get("/api/approvals/pending")
    async def api_approvals_pending(actor_id: str = Query(default="chris")) -> JSONResponse:
        """Return pending approvals formatted for the Needs You zone in the UI."""
        guard = get_approval_guard()
        if guard is None:
            return _json({"pending": [], "error": "Approval system not initialised"})
        return _json({"pending": guard.get_pending_for_ui(actor_id=actor_id)})

    @app.post("/api/approvals/{request_id}/approve")
    async def api_approvals_approve(request_id: str, payload: dict[str, Any] = {}) -> JSONResponse:
        """Approve a pending request. Optionally supply approved_by in the body."""
        approved_by = str((payload or {}).get("approved_by", "chris"))
        # Try ApprovalQueue first (agent-submitted requests)
        queue = get_approval_queue()
        if queue is not None:
            from dataclasses import asdict as _asdict
            item = queue.approve(request_id, approved_by=approved_by)
            if item is not None:
                return _json({"status": "approved", "request": _asdict(item)})
        # Fall back to ApprovalStore (runtime-submitted requests shown in the UI list)
        updated = runtime.approval_store.update_status(request_id, "approved")
        if updated is not None:
            return _json({"status": "approved", "request": updated})
        raise HTTPException(status_code=404, detail="Pending approval request not found")

    @app.post("/api/approvals/{request_id}/reject")
    async def api_approvals_reject(request_id: str, payload: dict[str, Any] = {}) -> JSONResponse:
        """Reject a pending request. Supply reason in body: {"reason": str}."""
        reason = str((payload or {}).get("reason", ""))
        rejected_by = str((payload or {}).get("rejected_by", "chris"))
        # Try ApprovalQueue first (agent-submitted requests)
        queue = get_approval_queue()
        if queue is not None:
            ok = queue.reject(request_id, reason=reason, rejected_by=rejected_by)
            if ok:
                return _json({"status": "rejected", "request_id": request_id, "reason": reason})
        # Fall back to ApprovalStore (runtime-submitted requests shown in the UI list)
        updated = runtime.approval_store.update_status(request_id, "rejected")
        if updated is not None:
            return _json({"status": "rejected", "request_id": request_id, "reason": reason})
        raise HTTPException(status_code=404, detail="Pending approval request not found")

    @app.post("/api/approvals/{request_id}/cancel")
    async def api_approvals_cancel(request_id: str) -> JSONResponse:
        """Cancel a pending request."""
        # Try ApprovalQueue first
        queue = get_approval_queue()
        if queue is not None:
            ok = queue.cancel(request_id)
            if ok:
                return _json({"status": "cancelled", "request_id": request_id})
        # Fall back to ApprovalStore
        updated = runtime.approval_store.update_status(request_id, "cancelled")
        if updated is not None:
            return _json({"status": "cancelled", "request_id": request_id})
        raise HTTPException(status_code=404, detail="Pending approval request not found")
        return _json({"status": "cancelled", "request_id": request_id})

    @app.get("/api/approvals/history")
    async def api_approvals_history(
        limit: int = Query(default=50, ge=1, le=500),
        action_type: str = Query(default=""),
    ) -> JSONResponse:
        """Return completed approval history."""
        queue = get_approval_queue()
        if queue is None:
            return _json({"history": [], "error": "Approval system not initialised"})
        action_type_filter = action_type.strip() or None
        from dataclasses import asdict as _asdict
        records = queue.get_history(limit=limit, action_type=action_type_filter)
        return _json({"history": [_asdict(r) for r in records]})

    @app.post("/api/approvals/submit")
    async def api_approvals_submit(payload: dict[str, Any]) -> JSONResponse:
        """
        Submit a new approval request manually (for testing or agent use).
        Required fields: agent_id, agent_label, action_type, title, description, payload_data.
        Optional: actor_id, priority, tags, context.
        """
        guard = get_approval_guard()
        if guard is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")
        try:
            request_id = guard.request_approval(
                agent_id=str(payload["agent_id"]),
                agent_label=str(payload["agent_label"]),
                action_type=str(payload["action_type"]),
                title=str(payload["title"]),
                description=str(payload.get("description", "")),
                payload=dict(payload.get("payload_data") or payload.get("payload") or {}),
                actor_id=str(payload.get("actor_id", "chris")),
                priority=int(payload.get("priority", 5)),
                tags=list(payload.get("tags") or []),
                context=dict(payload.get("context") or {}),
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
        queue = get_approval_queue()
        item = queue.get_by_id(request_id) if queue is not None else None
        return _json(
            {
                "status": "submitted",
                "request_id": request_id,
                "supervision_decision": dict(getattr(item, "supervision_decision", {}) or {}),
                "trust_zone_id": str(getattr(item, "trust_zone_id", "") or ""),
                "lane_id": str(getattr(item, "lane_id", "") or ""),
            },
            status_code=201,
        )

    @app.post("/api/approvals/{request_id}/execute")
    async def api_approvals_execute(request_id: str) -> JSONResponse:
        """Execute a previously approved request."""
        guard = get_approval_guard()
        if guard is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")
        result = guard.execute_approved(request_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("detail", "Execution failed"))
        return _json(
            {
                "status": "executed",
                "result": result,
                "request_id": request_id,
                "supervision_decision": dict(result.get("supervision_decision", {}) or {}),
            }
        )

    @app.post("/api/approvals/{request_id}")
    async def api_update_approval(request_id: str, payload: dict[str, Any]) -> JSONResponse:
        updated = runtime.update_approval(request_id, str(payload.get("status", "pending")))
        if updated is None:
            raise HTTPException(status_code=404, detail="Approval request not found")
        return _json(updated)

    @app.post("/api/message-drafts/{draft_id}")
    async def api_update_message_draft(draft_id: str, payload: dict[str, Any]) -> JSONResponse:
        updated = runtime.update_message_draft(draft_id, str(payload.get("status", "staged")))
        if updated is None:
            raise HTTPException(status_code=404, detail="Message draft not found")
        return _json(updated)

    @app.post("/api/stage/email/draft")
    async def api_stage_email_draft(payload: dict[str, Any], background_tasks: BackgroundTasks) -> JSONResponse:
        try:
            result = runtime.stage_email_draft(payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        background_tasks.add_task(_broadcast_dashboard, "communications.updated")
        return _json(result, status_code=201)

    @app.post("/api/vendor-preps/{prep_id}")
    async def api_update_vendor_prep(prep_id: str, payload: dict[str, Any]) -> JSONResponse:
        updated = runtime.update_vendor_prep_status(prep_id, str(payload.get("status", "staged")))
        if updated is None:
            raise HTTPException(status_code=404, detail="Vendor prep not found")
        return _json(updated)

    # ------------------------------------------------------------------
    # Publishing / Ghostwritr endpoints
    # ------------------------------------------------------------------

    @app.get("/api/publishing/scan-reviews")
    async def api_publishing_scan_reviews() -> JSONResponse:
        """Trigger a scan for new draft reviews ready for approval."""
        import asyncio as _aio
        bridge = _get_ghostwritr_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="Ghostwritr bridge not initialised")
        new_reviews = await _aio.get_event_loop().run_in_executor(None, bridge.check_for_new_reviews)
        return _json({"scanned": True, "new_reviews": len(new_reviews),
                      "reviews": [r.to_dict() for r in new_reviews]})

    @app.get("/api/publishing/dashboard")
    async def api_publishing_dashboard() -> JSONResponse:
        """Full Ghostwritr publishing dashboard."""
        import asyncio as _aio
        bridge = _get_ghostwritr_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="Ghostwritr bridge not initialised")
        # Run blocking DB calls in a thread to avoid blocking the async event loop
        result = await _aio.get_event_loop().run_in_executor(None, bridge.get_publishing_dashboard)
        return _json(result)

    @app.get("/api/publishing/reviews/pending")
    async def api_publishing_reviews_pending() -> JSONResponse:
        """All draft submissions currently pending review."""
        pending = _pending_publishing_reviews(limit=12)
        return _json({"reviews": pending, "count": len(pending)})

    @app.post("/api/publishing/draft/approve")
    async def api_publishing_draft_approve(payload: dict[str, Any]) -> JSONResponse:
        """Approve a stage review. Body: {review_id, feedback?}"""
        review_id = str(payload.get("review_id", "")).strip()
        if not review_id:
            raise HTTPException(status_code=400, detail="review_id is required")
        feedback = str(payload.get("feedback", "")).strip()
        result = _mutate_publishing_review(review_id, target_status="approved", feedback=feedback)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Publish",
            reason=f"Publish approved review {str(result.get('title') or review_id).strip() or review_id}.",
            route="/publish",
            actor=actor,
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "publish",
                "action": "Approve Publish Review",
                "title": str(result.get("title") or review_id).strip() or review_id,
                "detail": f"Approved publishing review {str(result.get('title') or review_id).strip() or review_id}.",
                "why_now": "Publish route cleared an editorial review directly from the live module.",
                "result_summary": "Publishing review status: approved",
                "related_route": "/publish",
                "route_label": "Open Publish",
                "related_kind": "publishing-review",
                "related_label": str(result.get("title") or review_id).strip() or review_id,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        history_entry = _record_publish_history(
            actor_id=actor,
            event_type="review-approved",
            title="Approve Publish Review",
            detail=f"Approved publishing review {str(result.get('title') or review_id).strip() or review_id}.",
            status_label="Approved",
            related_label=str(result.get("title") or review_id).strip() or review_id,
            review_id=review_id,
        )
        return _json({"status": "approved", "review": result, "focus": focus_entry, "history_entry": history_entry})

    @app.post("/api/publishing/draft/revise")
    async def api_publishing_draft_revise(payload: dict[str, Any]) -> JSONResponse:
        """Mark a stage review as needs_revision. Body: {review_id, feedback}"""
        review_id = str(payload.get("review_id", "")).strip()
        feedback = str(payload.get("feedback", "")).strip()
        if not review_id:
            raise HTTPException(status_code=400, detail="review_id is required")
        if not feedback:
            raise HTTPException(status_code=400, detail="feedback is required")
        result = _mutate_publishing_review(review_id, target_status="needs_revision", feedback=feedback)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Publish",
            reason=f"Publish requested revision for {str(result.get('title') or review_id).strip() or review_id}.",
            route="/publish",
            actor=actor,
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "publish",
                "action": "Request Publish Revision",
                "title": str(result.get("title") or review_id).strip() or review_id,
                "detail": f"Requested revision for publishing review {str(result.get('title') or review_id).strip() or review_id}.",
                "why_now": "Publish route sent editorial feedback back into the live module.",
                "result_summary": "Publishing review status: needs_revision",
                "related_route": "/publish",
                "route_label": "Open Publish",
                "related_kind": "publishing-review",
                "related_label": str(result.get("title") or review_id).strip() or review_id,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        history_entry = _record_publish_history(
            actor_id=actor,
            event_type="review-revision",
            title="Request Publish Revision",
            detail=f"Requested revision for publishing review {str(result.get('title') or review_id).strip() or review_id}.",
            status_label="Revision Requested",
            related_label=str(result.get("title") or review_id).strip() or review_id,
            review_id=review_id,
        )
        return _json({"status": "needs_revision", "review": result, "focus": focus_entry, "history_entry": history_entry})

    @app.post("/api/publishing/checklist/step")
    async def api_publishing_checklist_step(payload: dict[str, Any]) -> JSONResponse:
        """Update a publish launch checklist step. Body: {project_id, step, completed?, actor?}"""
        project_id = str(payload.get("project_id") or "").strip()
        step = str(payload.get("step") or "").strip()
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        if not step:
            raise HTTPException(status_code=400, detail="step is required")
        result = _mutate_publishing_checklist_step(
            project_id,
            step=step,
            completed=bool(payload.get("completed", True)),
            actor=str(payload.get("actor") or "Chris"),
        )
        await _broadcast_dashboard("publishing-checklist-updated")
        return _json(result)

    @app.get("/api/publishing/track/{slug}")
    async def api_publishing_track_status(slug: str) -> JSONResponse:
        """Return book summary and stage progress for a given book slug."""
        bridge = _get_ghostwritr_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="Ghostwritr bridge not initialised")
        return _json(bridge.get_book_summary(slug))

    def _build_launch_control_payload(project_id: str | None = None) -> dict:
        """
        Assemble the Launch Control zone payload.

        Pulls data from GhostwritrBridge (tracks, submissions) and
        PublishingStore (social posts) then returns a single dict that
        ``populateLaunchZone`` in voice_ui.py can consume directly.
        """
        from datetime import datetime, timezone

        bridge = _get_ghostwritr_bridge()
        pub = _get_publishing()

        # ---- Resolve the active project --------------------------------
        active_project: dict | None = None

        if bridge is not None:
            dashboard = bridge.get_publishing_dashboard()
            project_ids: list[str] = dashboard.get("active_project_ids") or []

            # Use requested project_id if supplied, otherwise first active
            target_id = (
                project_id if project_id and project_id in project_ids
                else (project_ids[0] if project_ids else None)
            )

            if target_id:
                tracks = bridge.get_track_status(target_id)

                # Derive title from whichever track has one
                title = ""
                for key in ("book", "workbook", "course"):
                    t = tracks.get(key)
                    if t and t.get("title"):
                        title = t["title"]
                        break

                # Phase / days-to-launch from publishing store
                days_to_launch: int = 0
                phase = "pre_launch"
                if pub is not None:
                    try:
                        project_obj = pub._store.get_project(target_id)
                        if project_obj and project_obj.published_at:
                            pub_dt = datetime.fromisoformat(
                                project_obj.published_at.replace("Z", "+00:00")
                            )
                            delta = pub_dt - datetime.now(timezone.utc)
                            days_to_launch = delta.days
                            phase = "post_launch" if days_to_launch < 0 else "pre_launch"
                    except Exception:
                        pass

                def _track_counts(t: dict | None) -> tuple[int, int]:
                    if not t:
                        return 0, 0
                    return int(t.get("chapters_complete", 0)), int(t.get("total_chapters", 0))

                book_done,   book_total   = _track_counts(tracks.get("book"))
                wb_done,     wb_total     = _track_counts(tracks.get("workbook"))
                course_done, course_total = _track_counts(tracks.get("course"))

                active_project = {
                    "project_id":              target_id,
                    "title":                   title or target_id,
                    "phase":                   phase,
                    "days_to_launch":          days_to_launch,
                    "book_chapters_done":      book_done,
                    "book_chapters_total":     book_total,
                    "workbook_chapters_done":  wb_done,
                    "workbook_chapters_total": wb_total,
                    "course_modules_done":     course_done,
                    "course_modules_total":    course_total,
                }

        if active_project is None:
            return {"active_project": None}

        # ---- Pending reviews -------------------------------------------
        pending_reviews = 0
        if bridge is not None:
            pending_reviews = len(bridge.get_pending_reviews())

        # ---- Social queue (from PublishingStore) -----------------------
        posts_scheduled        = 0
        posts_pending_approval = 0
        if pub is not None:
            try:
                scheduled              = pub._store.get_scheduled_posts()
                posts_scheduled        = len(scheduled)
                posts_pending_approval = sum(1 for p in scheduled if p.status == "draft")
            except Exception:
                pass

        # ---- Performance metrics (post-launch) -------------------------
        performance: dict = {}
        # Future: populate from Amazon/Coursera connectors via GrowthEngine

        # ---- Next action -----------------------------------------------
        if pending_reviews > 0 and bridge is not None:
            pr_list = bridge.get_pending_reviews()
            pr = pr_list[0] if pr_list else None
            if pr:
                next_action = f"Review {pr.title} ({pr.track_type} ch.{pr.chapter_number})"
            else:
                next_action = f"Review {pending_reviews} pending draft{'s' if pending_reviews > 1 else ''}"
        elif posts_pending_approval > 0:
            next_action = f"Approve {posts_pending_approval} social post{'s' if posts_pending_approval > 1 else ''}"
        else:
            next_action = "All caught up."

        return {
            "active_project":         active_project,
            "pending_reviews":        pending_reviews,
            "posts_scheduled":        posts_scheduled,
            "posts_pending_approval": posts_pending_approval,
            "performance":            performance,
            "next_action":            next_action,
        }

    @app.get("/api/publishing/launch-control")
    async def api_publishing_launch_control_default() -> JSONResponse:
        """Launch Control zone payload for the active/most-recent publishing project."""
        try:
            payload = await asyncio.to_thread(_build_launch_control_payload, None)
            return _json(payload)
        except Exception as exc:
            return _json({"active_project": None, "error": str(exc)})

    @app.get("/api/publishing/launch-control/{project_id}")
    async def api_publishing_launch_control(project_id: str) -> JSONResponse:
        """Launch Control zone payload for a specific publishing project."""
        try:
            payload = await asyncio.to_thread(_build_launch_control_payload, project_id)
            return _json(payload)
        except Exception as exc:
            return _json({"active_project": None, "error": str(exc)})

    # ------------------------------------------------------------------
    # LLM Gateway — must be registered BEFORE the legacy catch-all below
    # ------------------------------------------------------------------

    @app.get("/api/gateway/status")
    async def api_gateway_status() -> JSONResponse:
        gw = _get_gateway()
        if gw is None:
            return JSONResponse({"error": "LLM gateway not initialised", "available": False}, status_code=503)
        status = await asyncio.to_thread(gw.get_status)
        return JSONResponse({"available": True, **status})

    @app.post("/api/gateway/test")
    async def api_gateway_test(request: Request) -> JSONResponse:
        gw = _get_gateway()
        if gw is None:
            return JSONResponse({"error": "LLM gateway not initialised"}, status_code=503)
        try:
            body = await request.json()
        except Exception:
            body = {}
        message = str(body.get("message", "Hello, JARVIS.")).strip() or "Hello, JARVIS."
        task_type = str(body.get("task_type", "converse")).strip() or "converse"
        from .llm_gateway import LLMMessage

        def _run() -> dict:
            resp = gw.complete(
                messages=[LLMMessage("user", message)],
                task_type=task_type,
                agent_id="gateway-test",
            )
            return {
                "text": resp.text,
                "model_used": resp.model_used,
                "backend": resp.backend,
                "task_type": resp.task_type,
                "latency_ms": resp.latency_ms,
                "confidence": resp.confidence,
                "escalated": resp.escalated,
                "error": resp.error,
            }

        result = await asyncio.to_thread(_run)
        return JSONResponse(result, status_code=200 if not result["error"] else 502)

    # ------------------------------------------------------------------
    # Social Media Publishing Engine
    # ------------------------------------------------------------------

    @app.get("/api/social/schedule/{project_id}")
    async def api_social_schedule(project_id: str) -> JSONResponse:
        """Launch schedule + full post list for a project."""
        engine = _get_social_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="SocialEngine not initialised")
        schedules = engine.store.list_schedules(project_id=project_id)
        posts = engine.store.list_posts(project_id=project_id)
        return _json({
            "project_id": project_id,
            "schedules": [s.to_dict() for s in schedules],
            "posts": [p.to_dict() for p in posts],
            "total_posts": len(posts),
        })

    @app.get("/api/social/posts/pending")
    async def api_social_posts_pending(project_id: str | None = None) -> JSONResponse:
        """Posts pending approval (optionally filtered by project_id query param)."""
        engine = _get_social_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="SocialEngine not initialised")
        posts = engine.store.list_posts(project_id=project_id, status="pending_approval")
        return _json({"posts": [p.to_dict() for p in posts], "count": len(posts)})

    @app.post("/api/social/post/approve/{post_id}")
    async def api_social_post_approve(post_id: str) -> JSONResponse:
        """Approve a post, changing its status from pending_approval to approved."""
        engine = _get_social_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="SocialEngine not initialised")
        post = engine.store.get_post(post_id)
        if post is None:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        if post.status not in ("pending_approval", "draft"):
            raise HTTPException(status_code=400, detail=f"Post is {post.status}; cannot approve")
        post.status = "approved"
        engine.store.save_post(post)
        return _json({"status": "approved", "post": post.to_dict()})

    @app.post("/api/social/execute")
    async def api_social_execute(payload: dict[str, Any]) -> JSONResponse:
        """Run all approved + due posts for a project. Body: {project_id}"""
        engine = _get_social_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="SocialEngine not initialised")
        project_id = str(payload.get("project_id", "")).strip()
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")

        def _run():
            return engine.quicksilver.execute_scheduled_posts(project_id)

        result = await asyncio.to_thread(_run)
        return _json(result)

    @app.get("/api/social/analytics/{project_id}")
    async def api_social_analytics(project_id: str) -> JSONResponse:
        """Sage's performance analysis for a project."""
        engine = _get_social_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="SocialEngine not initialised")

        def _run():
            return engine.sage.analyze_performance(project_id)

        result = await asyncio.to_thread(_run)
        return _json(result)

    @app.get("/api/social/adaptation/{project_id}")
    async def api_social_adaptation(project_id: str) -> JSONResponse:
        """Sage's markdown adaptation report for a project."""
        engine = _get_social_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="SocialEngine not initialised")

        def _run():
            return engine.sage.generate_adaptation_report(project_id)

        report_md = await asyncio.to_thread(_run)
        return _json({"project_id": project_id, "report": report_md})

    # ── Home Intelligence API ─────────────────────────────────────────────────
    # IMPORTANT: must be registered BEFORE the /api/{legacy_path:path} catch-all.

    @app.get("/api/home/dashboard")
    async def api_home_dashboard() -> JSONResponse:
        """Full home intelligence dashboard — projects, tasks, email, calendar."""
        db = _get_home_db()
        if db is None:
            return _json({"available": False, "error": "Home DB not initialised"})
        try:
            result = await asyncio.to_thread(db.get_dashboard_data)
        except Exception as exc:
            return _json({"available": False, "error": f"Home dashboard unavailable: {exc}"})
        result["available"] = True
        return _json(result)

    # ── Projects ──────────────────────────────────────────────────────────────

    @app.get("/api/home/projects")
    async def api_home_projects(
        status: str = Query(default=""),
        track: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        projects = await asyncio.to_thread(
            db.list_projects,
            status or None,
            track or None,
        )
        return _json({"projects": projects, "total": len(projects)})

    @app.post("/api/home/projects")
    async def api_home_projects_create(request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        project = await asyncio.to_thread(db.create_project, data)
        return _json(project)

    @app.get("/api/home/projects/{project_id}")
    async def api_home_project_get(project_id: str) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        project = await asyncio.to_thread(db.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return _json(project)

    @app.patch("/api/home/projects/{project_id}")
    async def api_home_project_update2(project_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        project = await asyncio.to_thread(db.update_project, project_id, data)
        return _json(project)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @app.get("/api/home/tasks")
    async def api_home_tasks(
        project_id: str = Query(default=""),
        status: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        tasks = await asyncio.to_thread(
            db.list_tasks,
            project_id or None,
            status or None,
        )
        return _json({"tasks": tasks, "total": len(tasks)})

    @app.get("/api/home/tasks/overdue")
    async def api_home_tasks_overdue() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        tasks = await asyncio.to_thread(db.get_overdue_tasks)
        return _json({"tasks": tasks, "total": len(tasks)})

    @app.get("/api/home/tasks/today")
    async def api_home_tasks_today() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        tasks = await asyncio.to_thread(db.get_tasks_due_today)
        return _json({"tasks": tasks, "total": len(tasks)})

    @app.post("/api/home/tasks")
    async def api_home_tasks_create(request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        task = await asyncio.to_thread(db.create_task, data)
        return _json(task)

    @app.patch("/api/home/tasks/{task_id}")
    async def api_home_task_update2(task_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        task = await asyncio.to_thread(db.update_task, task_id, data)
        return _json(task)

    @app.post("/api/home/tasks/{task_id}/complete")
    async def api_home_task_complete2(task_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        task = await asyncio.to_thread(db.complete_task, task_id)
        return _json(task)

    # ── Email ─────────────────────────────────────────────────────────────────

    @app.get("/api/home/email")
    async def api_home_email(
        unread_only: bool = Query(default=False),
        limit: int = Query(default=50),
        source: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        emails = await asyncio.to_thread(
            db.list_emails,
            source or None,
            unread_only,
            limit,
        )
        stats = await asyncio.to_thread(db.get_email_stats)
        return _json({"emails": emails, "total": len(emails), "stats": stats})

    @app.get("/api/home/email/stats")
    async def api_home_email_stats() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        stats = await asyncio.to_thread(db.get_email_stats)
        return _json(stats)

    @app.post("/api/home/email/{email_id}/read")
    async def api_home_email_mark_read2(email_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        await asyncio.to_thread(db.mark_email_read, email_id)
        return _json({"ok": True})

    # ── Calendar ──────────────────────────────────────────────────────────────

    @app.get("/api/home/calendar/today")
    async def api_home_calendar_today() -> JSONResponse:
        inbox = _get_unified_inbox()
        if inbox is None:
            db = _get_home_db()
            if db is None:
                raise HTTPException(status_code=503, detail="Home intelligence not initialised")
            events = await asyncio.to_thread(db.get_todays_events)
            return _json({"events": events, "total": len(events)})
        agenda = await asyncio.to_thread(inbox.get_todays_agenda)
        return _json(agenda)

    @app.get("/api/home/calendar/upcoming")
    async def api_home_calendar_upcoming(days: int = Query(default=7)) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        events = await asyncio.to_thread(db.get_upcoming_events, days)
        return _json({"events": events, "total": len(events)})

    @app.get("/api/home/calendar")
    async def api_home_calendar(
        start: str = Query(default=""),
        end: str = Query(default=""),
        source: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        from datetime import datetime, timezone, timedelta
        if not start:
            start = datetime.now(timezone.utc).isoformat()
        if not end:
            end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        events = await asyncio.to_thread(db.list_calendar_events, start, end, source or None)
        return _json({"events": events, "total": len(events)})

    # ── Sync ──────────────────────────────────────────────────────────────────

    @app.post("/api/home/sync")
    async def api_home_sync_all2(request: Request) -> JSONResponse:
        """Trigger a full sync of all email and calendar sources."""
        inbox = _get_unified_inbox()
        if inbox is None:
            raise HTTPException(status_code=503, detail="Unified inbox not initialised")
        result = await asyncio.to_thread(inbox.sync_all)
        return _json(result)

    @app.post("/api/home/sync/{source}")
    async def api_home_sync_source2(source: str, request: Request) -> JSONResponse:
        """Trigger sync for a specific source: gmail|outlook|google_calendar|outlook_calendar|cozi"""
        inbox = _get_unified_inbox()
        if inbox is None:
            raise HTTPException(status_code=503, detail="Unified inbox not initialised")
        sync_map = {
            "gmail": inbox.sync_gmail,
            "outlook": inbox.sync_outlook_email,
            "google_calendar": inbox.sync_google_calendar,
            "outlook_calendar": inbox.sync_outlook_calendar,
            "cozi": inbox.sync_cozi,
        }
        fn = sync_map.get(source)
        if fn is None:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
        result = await asyncio.to_thread(fn)
        return _json(result)

    @app.get("/api/home/sync/status")
    async def api_home_sync_status2() -> JSONResponse:
        """Return last sync time for each source."""
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        states = await asyncio.to_thread(db.get_all_sync_states)
        return _json({"sources": states})

    # ── Signal Processing ────────────────────────────────────────────────────

    @app.post("/api/home/signals/process")
    async def api_home_signals_process2(request: Request) -> JSONResponse:
        """Run the signal router to classify unprocessed emails into project signals."""
        router = _get_signal_router()
        if router is None:
            raise HTTPException(status_code=503, detail="Signal router not initialised")
        result = await asyncio.to_thread(router.run_full_scan)
        return _json(result)

    @app.get("/api/home/signals/unclassified")
    async def api_home_signals_unclassified() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        signals = await asyncio.to_thread(db.list_unclassified_signals, 50)
        return _json({"signals": signals, "total": len(signals)})

    def _record_huddle_idea_focus(
        *,
        actor: str,
        action: str,
        detail: str,
        why_now: str,
        result_summary: str,
        related_label: str,
    ) -> dict[str, Any]:
        actor = str(actor or "Chris").strip() or "Chris"
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "huddle",
                "action": action,
                "title": related_label,
                "detail": detail,
                "why_now": why_now,
                "result_summary": result_summary,
                "related_route": "/huddle-center",
                "route_label": "Open Huddle",
                "related_kind": "idea",
                "related_label": related_label,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        return ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Huddle",
            reason=f"Huddle idea workflow advanced: {related_label}.",
            route="/huddle-center",
            actor=actor.lower(),
        )

    # ── Value Log ─────────────────────────────────────────────────────────────

    @app.post("/api/home/projects/{project_id}/value")
    async def api_home_log_value2(project_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        entry = await asyncio.to_thread(
            db.log_value,
            project_id,
            float(data.get("amount", 0)),
            data.get("type", "savings"),
            data.get("description"),
            data.get("source", "manual"),
        )
        return _json(entry)

    @app.get("/api/home/value/summary")
    async def api_home_value_summary2(project_id: str = Query(default="")) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        summary = await asyncio.to_thread(db.get_value_summary, project_id or None)
        return _json(summary)

    async def _build_calendar_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        local_now_fn = getattr(runtime, "_local_now", None)
        local_today_iso = (
            local_now_fn().date().isoformat()
            if callable(local_now_fn)
            else datetime.now().astimezone().date().isoformat()
        )
        availability_notes: list[str] = []
        errors: list[str] = []

        inbox = _get_unified_inbox()
        home_db = _get_home_db()

        today_events: list[dict[str, Any]] = []
        upcoming_events: list[dict[str, Any]] = []
        today_payload: dict[str, Any] = {"events": [], "total": 0}
        upcoming_payload: dict[str, Any] = {"events": [], "total": 0}
        sync_states: list[dict[str, Any]] = []

        if inbox is None and home_db is None:
            availability_notes.append("Calendar inbox and home-calendar storage are not initialised in this runtime.")

        try:
            if inbox is not None:
                today_payload = dict(await asyncio.to_thread(inbox.get_todays_agenda) or {"events": [], "total": 0})
                today_events = list(today_payload.get("events") or [])
            elif home_db is not None:
                today_events = list(await asyncio.to_thread(home_db.get_todays_events))
                today_payload = {
                    "events": today_events,
                    "total": len(today_events),
                    "date": local_today_iso,
                }
        except Exception as exc:
            errors.append(f"today_calendar: {exc}")
            availability_notes.append(f"Today's calendar could not be loaded: {exc}")

        if not str(today_payload.get("date") or "").strip():
            today_payload["date"] = local_today_iso

        try:
            if home_db is not None:
                upcoming_events = list(await asyncio.to_thread(home_db.get_upcoming_events, 7))
                upcoming_payload = {"events": upcoming_events, "total": len(upcoming_events)}
            elif today_events:
                upcoming_payload = {"events": list(today_events), "total": len(today_events)}
                upcoming_events = list(today_events)
        except Exception as exc:
            errors.append(f"upcoming_calendar: {exc}")
            availability_notes.append(f"Upcoming calendar events could not be loaded: {exc}")

        workflow_payload: dict[str, Any] = {}
        calendar_store_path = Path("data/apple/calendar_events.json")
        try:
            raw_calendar: dict[str, Any] = {}
            if calendar_store_path.exists():
                loaded = json.loads(calendar_store_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    raw_calendar = loaded
            workflow_payload = _build_apple_calendar_state(raw_calendar)
        except Exception as exc:
            errors.append(f"apple_calendar_state: {exc}")
            availability_notes.append(f"Apple calendar workflow state could not be loaded: {exc}")
            workflow_payload = {}

        try:
            if home_db is not None:
                sync_states = list(await asyncio.to_thread(home_db.get_all_sync_states))
        except Exception as exc:
            errors.append(f"sync_states: {exc}")
            availability_notes.append(f"Calendar sync states could not be loaded: {exc}")

        source_totals: dict[str, int] = {}
        for event in [*today_events, *upcoming_events]:
            source_key = str(
                event.get("source")
                or event.get("calendar_name")
                or event.get("calendar")
                or "calendar"
            ).strip() or "calendar"
            source_totals[source_key] = source_totals.get(source_key, 0) + 1

        source_rows: list[dict[str, Any]] = []
        for row in sync_states[:8]:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source") or row.get("provider") or "calendar").strip() or "calendar"
            status = str(row.get("status") or "unknown").strip() or "unknown"
            source_rows.append(
                {
                    "source": source,
                    "status": status,
                    "detail": str(row.get("message") or row.get("last_error") or "").strip(),
                    "updated_at": str(row.get("last_sync_at") or row.get("updated_at") or "").strip(),
                    "count": int(source_totals.get(source, 0)),
                    "connected": status.lower() in {"ok", "connected", "ready", "healthy"},
                }
            )
        if not source_rows:
            for source, count in source_totals.items():
                source_rows.append(
                    {
                        "source": source,
                        "status": "observed",
                        "detail": "Events are present, but no richer sync-state row is available in this runtime.",
                        "updated_at": str(workflow_payload.get("synced_at") or "").strip(),
                        "count": int(count),
                        "connected": True,
                    }
                )

        recent_activity = _module_recent_activity(route="/calendar-center", domain="calendar", limit=8)
        if not recent_activity:
            recent_activity = _module_recent_activity(route="/command-center", domain="calendar", limit=6)

        prep_cues = list(workflow_payload.get("preparation_cues") or [])
        route_sensitive = list(workflow_payload.get("route_sensitive_events") or [])
        attention_flags = list(workflow_payload.get("attention_flags") or [])

        top_route_event = next((item for item in route_sensitive if str(item.get("id") or "").strip()), {})
        top_prep_event = next((item for item in prep_cues if str(item.get("event_id") or "").strip()), {})

        today_count = len(today_events)
        meeting_count = sum(
            1
            for item in today_events
            if "focus" not in str(item.get("title") or "").lower()
        )
        focus_count = sum(
            1
            for item in today_events
            if re.search(r"\b(deep|focus|write|strategy|study|quiet|pray|journal)\b", str(item.get("title") or ""), re.IGNORECASE)
        )
        family_count = sum(
            1
            for item in [*today_events, *upcoming_events]
            if re.search(r"\b(family|emma|liam|sarah|church|kids|household|cozi)\b", str(item.get("title") or "") + " " + str(item.get("calendar_name") or ""), re.IGNORECASE)
        )

        trusted_actions = [
            {
                "id": "sync-sources",
                "title": "Refresh Calendar Sources",
                "note": "Runs the live inbox and connected calendar sync boundary.",
                "available": bool(inbox is not None),
                "unavailable_reason": "Unified inbox is not initialised in this runtime." if inbox is None else "",
            },
            {
                "id": "create-event",
                "title": "Add Event",
                "note": "Creates a real calendar event through the runtime's connected calendar engines when possible.",
                "available": True,
                "prompt_hint": "Add dinner with Sarah tomorrow at 6pm to my calendar",
            },
            {
                "id": "focus-block",
                "title": "Protect Focus Block",
                "note": "Creates a calendar focus block using the same live calendar write boundary.",
                "available": True,
                "prompt_hint": "Block off time for focus work tomorrow at 9am on my calendar",
            },
            {
                "id": "prepare-next",
                "title": "Stage Prep",
                "note": "Stages preparation for the next prep-ready calendar event.",
                "available": bool(str(top_prep_event.get("event_id") or "").strip()),
                "unavailable_reason": "No prep-ready event is currently surfaced." if not str(top_prep_event.get("event_id") or "").strip() else "",
                "event_id": str(top_prep_event.get("event_id") or "").strip(),
            },
            {
                "id": "route-next",
                "title": "Open Next Route",
                "note": "Opens the next route-sensitive event with a real location boundary.",
                "available": bool(str(top_route_event.get("id") or "").strip()),
                "unavailable_reason": "No route-ready event is currently surfaced." if not str(top_route_event.get("id") or "").strip() else "",
                "event_id": str(top_route_event.get("id") or "").strip(),
            },
            {
                "id": "find-time",
                "title": "Find Time",
                "note": "Command can help negotiate and schedule the right slot, but a direct calendar find-time backend is not wired yet.",
                "available": False,
                "unavailable_reason": "No direct find-time backend route exists yet in this runtime.",
            },
            {
                "id": "reschedule",
                "title": "Reschedule",
                "note": "Command can reason about rescheduling, but a direct mutation route is not exposed yet.",
                "available": False,
                "unavailable_reason": "No direct reschedule backend route exists yet in this runtime.",
            },
        ]

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": (
                f"Calendar loaded {today_count} event(s) for today, {len(upcoming_events)} upcoming event(s), "
                f"{len(source_rows)} source row(s), and {len(attention_flags)} active schedule attention flag(s)."
            ),
            "what_became_real": "Calendar now hydrates from one live module payload that combines today's agenda, upcoming schedule, Apple prep and routing state, sync health, and continuity instead of browser-side stitching.",
            "remains_partial": "Direct find-time negotiation, full rescheduling, and richer multi-view calendar mutations still depend on backend contracts that are not exposed yet in this runtime.",
            "runtime_note": "Calendar is live and connected.",
            "availability_notes": availability_notes[:10],
            "counts": {
                "today_events": today_count,
                "upcoming_events": len(upcoming_events),
                "attention_flags": len(attention_flags),
                "route_sensitive": len(route_sensitive),
                "prep_cues": len(prep_cues),
                "connected_sources": len([row for row in source_rows if row.get("connected")]),
                "source_rows": len(source_rows),
                "meeting_events": meeting_count,
                "focus_events": focus_count,
                "family_events": family_count,
                "recent_activity": len(recent_activity),
            },
            "today_payload": today_payload,
            "upcoming_payload": upcoming_payload,
            "workflow": workflow_payload,
            "source_rows": source_rows[:8],
            "sync_states": sync_states[:8],
            "recent_activity": recent_activity,
            "trusted_actions": trusted_actions,
            "proof_paths": {
                "module_route": "/calendar-center",
                "module_api": "/api/calendar/module",
                "today_api": "/api/home/calendar/today",
                "upcoming_api": "/api/home/calendar/upcoming?days=7",
                "workflow_api": "/api/apple/calendar/state",
                "sync_api": "/api/home/sync",
                "prepare_api_template": "/api/apple/calendar/events/{event_id}/prepare",
                "route_api_template": "/api/apple/calendar/events/{event_id}/route",
                "operator_activity_api": "/api/activity/operator-action",
                "action_api": "/api/calendar/module/action",
            },
            "local_today": local_today_iso,
            "errors": errors,
        }

        if errors and not (today_events or upcoming_events or source_rows or attention_flags):
            payload["available"] = False
            payload["status"] = "Wired"
            payload["summary"] = "Calendar is wired, but the runtime could not hydrate enough live schedule data to make the board fully useful."
            payload["runtime_note"] = "Calendar is partially connected. Live schedule sources did not fully hydrate."
            payload["remains_partial"] = "Calendar needs more live schedule, sync, or Apple workflow data in this runtime to become richly informative."
        elif errors:
            payload["runtime_note"] = "Calendar is live, but some schedule sources are partially unavailable."

        if not payload["availability_notes"]:
            payload["availability_notes"].append("All currently available Calendar sources hydrated successfully.")

        return payload

    @app.get("/api/calendar/module")
    async def api_calendar_module(actor: str = "Chris") -> JSONResponse:
        return _json(await _build_calendar_module_payload(actor))

    @app.post("/api/calendar/module/action")
    async def api_calendar_module_action(payload: dict[str, Any]) -> JSONResponse:
        action = str(payload.get("action") or "").strip().lower()
        if not action:
            raise HTTPException(status_code=400, detail="Action is required.")

        if action == "sync-sources":
            inbox = _get_unified_inbox()
            if inbox is None:
                raise HTTPException(status_code=503, detail="Unified inbox not initialised")
            result = await asyncio.to_thread(inbox.sync_all)
            return _json({
                "ok": True,
                "action": action,
                "message": "Calendar sources synced.",
                "summary": dict(result.get("summary") or {}) if isinstance(result, dict) else {},
                "result": result,
            })

        if action in {"create-event", "focus-block"}:
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt and action == "focus-block":
                prompt = "Block off time for focus work tomorrow at 9am on my calendar"
            if not prompt:
                raise HTTPException(status_code=400, detail="A calendar command prompt is required.")
            handler = getattr(runtime, "_try_handle_calendar_event", None)
            if not callable(handler):
                raise HTTPException(status_code=503, detail="Calendar write engine is unavailable in this runtime.")
            result = await asyncio.to_thread(handler, prompt)
            if result is None:
                raise HTTPException(status_code=503, detail="Calendar write engine could not handle that request.")
            message = str(getattr(result, "output_text", "") or "").strip() or "Calendar command completed."
            lowered = message.lower()
            if not (lowered.startswith("done.") or "calendar write handled" in lowered):
                raise HTTPException(status_code=503, detail=message)
            return _json({
                "ok": True,
                "action": action,
                "message": message,
                "prompt": prompt,
            })

        raise HTTPException(status_code=400, detail=f"Unsupported calendar module action: {action}")

    async def _build_email_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        availability_notes: list[str] = []
        errors: list[str] = []

        def email_category(item: dict[str, Any]) -> str:
            subject = str(item.get("subject") or "").lower()
            sender = str(item.get("sender_name") or item.get("sender_email") or "").lower()
            labels = [str(label).lower() for label in list(item.get("labels") or [])]
            if "newsletter" in subject or "digest" in subject or "substack" in sender or "newsletter" in sender:
                return "newsletters"
            if any(token in subject for token in ("invoice", "receipt", "statement", "report", "summary", "update")):
                return "updates"
            if any(token in subject for token in ("family", "emma", "liam", "sarah", "church")) or "family" in sender:
                return "family"
            if any(token in subject for token in ("approve", "review", "launch", "speaking", "urgent")) or "important" in labels or str(item.get("importance") or "").lower() == "high":
                return "focused"
            return "primary"

        def email_priority(item: dict[str, Any]) -> str:
            subject = str(item.get("subject") or "").lower()
            if (
                str(item.get("importance") or "").lower() == "high"
                or bool(item.get("is_flagged"))
                or any(token in subject for token in ("approve", "urgent", "launch"))
            ):
                return "high"
            if (not bool(item.get("is_read"))) or any(token in subject for token in ("review", "schedule", "proposal")):
                return "medium"
            return "low"

        home_db = _get_home_db()
        inbox = _get_unified_inbox()
        emails: list[dict[str, Any]] = []
        stats: dict[str, Any] = {}
        sync_states: list[dict[str, Any]] = []

        if home_db is None:
            availability_notes.append("Home inbox storage is not initialised in this runtime, so Email cannot hydrate cached mailbox state.")
        else:
            try:
                emails = list(await asyncio.to_thread(home_db.list_emails, None, False, 80))
            except Exception as exc:
                errors.append(f"emails: {exc}")
                availability_notes.append(f"Email cache could not be loaded: {exc}")
            try:
                stats = dict(await asyncio.to_thread(home_db.get_email_stats) or {})
            except Exception as exc:
                errors.append(f"stats: {exc}")
                availability_notes.append(f"Email stats could not be loaded: {exc}")
            try:
                sync_states = list(await asyncio.to_thread(home_db.get_all_sync_states))
            except Exception as exc:
                errors.append(f"sync_states: {exc}")
                availability_notes.append(f"Email sync states could not be loaded: {exc}")

        for source_name in ("gmail", "outlook"):
            stats.setdefault(source_name, {"total": 0, "unread": 0, "flagged": 0})

        total_unread = sum(int((stats.get(source) or {}).get("unread") or 0) for source in ("gmail", "outlook"))
        total_flagged = sum(int((stats.get(source) or {}).get("flagged") or 0) for source in ("gmail", "outlook"))
        total_cached = len(emails)
        category_counts: dict[str, int] = {"focused": 0, "primary": 0, "updates": 0, "newsletters": 0, "family": 0}
        priority_counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        unread_by_sender: dict[str, int] = {}
        thread_map: dict[str, dict[str, Any]] = {}
        for item in emails:
            category = email_category(item)
            priority = email_priority(item)
            category_counts[category] = int(category_counts.get(category, 0)) + 1
            priority_counts[priority] = int(priority_counts.get(priority, 0)) + 1
            if not bool(item.get("is_read")):
                sender_key = str(item.get("sender_name") or item.get("sender_email") or "Unknown sender").strip() or "Unknown sender"
                unread_by_sender[sender_key] = int(unread_by_sender.get(sender_key, 0)) + 1
            thread_key = str(item.get("thread_id") or item.get("id") or "").strip()
            if not thread_key:
                continue
            bucket = thread_map.setdefault(
                thread_key,
                {
                    "thread_id": thread_key,
                    "subject": str(item.get("subject") or "(No subject)").strip() or "(No subject)",
                    "participants": set(),
                    "count": 0,
                    "last_received_at": str(item.get("received_at") or "").strip(),
                    "priority": priority,
                    "category": category,
                    "unread_count": 0,
                },
            )
            bucket["count"] = int(bucket.get("count") or 0) + 1
            bucket["participants"].add(str(item.get("sender_name") or item.get("sender_email") or "Unknown sender").strip() or "Unknown sender")
            if not bool(item.get("is_read")):
                bucket["unread_count"] = int(bucket.get("unread_count") or 0) + 1
            received_at = str(item.get("received_at") or "").strip()
            if received_at and received_at >= str(bucket.get("last_received_at") or ""):
                bucket["last_received_at"] = received_at
                bucket["subject"] = str(item.get("subject") or bucket["subject"]).strip() or bucket["subject"]
                bucket["priority"] = priority
                bucket["category"] = category

        focused_emails = [item for item in emails if email_priority(item) in {"high", "medium"}]
        waiting_emails = [item for item in emails if (not bool(item.get("is_read"))) and email_priority(item) != "low"]
        selected_email_id = str(((waiting_emails[:1] or emails[:1] or [{}])[0].get("id") or "")).strip()

        review_load = total_unread + total_flagged + len(waiting_emails)
        inbox_health_score = max(0, min(100, 100 - min(72, (total_unread * 4) + (total_flagged * 3) + len(waiting_emails))))
        if total_cached <= 0:
            inbox_health_score = 0

        sync_by_source = {
            str(item.get("source") or "").strip().lower(): dict(item)
            for item in sync_states
            if str(item.get("source") or "").strip()
        }
        source_rows: list[dict[str, Any]] = []
        source_config = [
            ("gmail", "Gmail", "/api/home/sync/gmail"),
            ("outlook", "Outlook", "/api/home/sync/outlook"),
            ("google_calendar", "Google Calendar", "/api/home/sync/google-calendar"),
            ("outlook_calendar", "Outlook Calendar", "/api/home/sync/outlook-calendar"),
        ]
        for source_key, label, route in source_config:
            state = sync_by_source.get(source_key, {})
            source_stats = dict(stats.get(source_key) or {})
            error_detail = str(state.get("error_detail") or "").strip()
            status = str(state.get("status") or ("connected" if source_key in {"gmail", "outlook"} and int(source_stats.get("total") or 0) else "not-connected")).strip()
            if error_detail and status in {"ok", "connected", "success"}:
                status = "error"
            tone = "warn" if status in {"error", "degraded", "disconnected"} else "good" if status in {"ok", "connected", "success"} else "low"
            source_rows.append(
                {
                    "source": source_key,
                    "label": label,
                    "status": status,
                    "tone": tone,
                    "detail": str(error_detail or f"{int(source_stats.get('unread') or 0)} unread · {int(source_stats.get('total') or 0)} cached").strip(),
                    "last_sync_at": str(state.get("last_sync_at") or state.get("updated_at") or "").strip(),
                    "count": int(source_stats.get("unread") or 0),
                    "total": int(source_stats.get("total") or 0),
                    "sync_route": route,
                }
            )

        recent_activity = _module_recent_activity(route="/email-center", domain="email", limit=8)
        if not recent_activity:
            recent_activity = _module_recent_activity(route="/command-center", domain="email", limit=6)

        inbox_overview = [
            {"label": "Unread", "value": total_unread, "note": "Messages still waiting in your live cache."},
            {"label": "Actionable", "value": len(focused_emails), "note": "Messages JARVIS considers mission-relevant or time-sensitive."},
            {"label": "Waiting", "value": len(waiting_emails), "note": "Unread items likely needing a reply or decision."},
            {"label": "Flagged", "value": total_flagged, "note": "Messages currently flagged upstream."},
            {"label": "Accounts", "value": len([row for row in source_rows if row["source"] in {"gmail", "outlook"} and row["status"] not in {"not-connected", "disconnected"}]), "note": "Mailbox sources currently showing live or cached state."},
        ]

        priority_rows = [
            {"title": "High Priority", "count": priority_counts["high"], "detail": "Flagged or clearly urgent email surfaced from the live cache.", "tone": "high"},
            {"title": "Needs Review", "count": priority_counts["medium"], "detail": "Unread or review-oriented email that should stay visible.", "tone": "medium"},
            {"title": "Waiting On You", "count": len(waiting_emails), "detail": "Messages still unread with a likely next action.", "tone": "info"},
        ]

        intelligence_cards = [
            {"title": "Connected Sources", "value": f"{len(source_rows)} lane(s)", "detail": "Mail and related sync sources surfaced through live sync state."},
            {"title": "Recent Continuity", "value": f"{len(recent_activity)} event(s)", "detail": "Recent operator actions already linked to the Email surface."},
            {"title": "Top Unread Sender", "value": max(unread_by_sender, key=unread_by_sender.get) if unread_by_sender else "Unavailable", "detail": "Based on unread sender concentration in the live cache."},
            {"title": "Current Review Load", "value": f"{review_load} signal(s)", "detail": "Unread, flagged, and waiting signals currently competing for attention."},
        ]

        pattern_rows = [
            {
                "label": "Focused",
                "count": category_counts["focused"],
                "share": round((category_counts["focused"] / total_cached) * 100) if total_cached else 0,
                "detail": "Priority and mission-aligned email.",
            },
            {
                "label": "Primary",
                "count": category_counts["primary"],
                "share": round((category_counts["primary"] / total_cached) * 100) if total_cached else 0,
                "detail": "Regular communication lanes.",
            },
            {
                "label": "Updates",
                "count": category_counts["updates"],
                "share": round((category_counts["updates"] / total_cached) * 100) if total_cached else 0,
                "detail": "Reports, receipts, and informational updates.",
            },
            {
                "label": "Family",
                "count": category_counts["family"],
                "share": round((category_counts["family"] / total_cached) * 100) if total_cached else 0,
                "detail": "Home, family, and relationship context.",
            },
            {
                "label": "Newsletters",
                "count": category_counts["newsletters"],
                "share": round((category_counts["newsletters"] / total_cached) * 100) if total_cached else 0,
                "detail": "Read-later or digest-style traffic.",
            },
        ]

        health_rows = [
            {
                "title": "Inbox Health",
                "value": f"{inbox_health_score}%",
                "detail": "Derived from unread, flagged, and waiting signals in the live cache.",
                "tone": "good" if inbox_health_score >= 80 else "warn" if inbox_health_score >= 55 else "high",
            },
            {
                "title": "Sync Coverage",
                "value": f"{len([row for row in source_rows if row['status'] not in {'not-connected', 'disconnected'}])}/{len(source_rows)}",
                "detail": "Email sources with visible state in this runtime.",
                "tone": "good" if any(row["status"] in {"ok", "connected", "success"} for row in source_rows) else "warn",
            },
            {
                "title": "Draft Engine",
                "value": "Available" if callable(getattr(runtime, "stage_email_draft", None)) else "Unavailable",
                "detail": "Shared draft staging boundary for composed or assisted replies.",
                "tone": "good" if callable(getattr(runtime, "stage_email_draft", None)) else "low",
            },
            {
                "title": "Reply Queue",
                "value": str(len(waiting_emails)),
                "detail": "Unread items that likely need intentional follow-through.",
                "tone": "warn" if waiting_emails else "good",
            },
        ]

        categories = [
            {"title": "Needs Your Response", "value": len(waiting_emails), "detail": "Unread messages likely needing your reply."},
            {"title": "Waiting On Others", "value": len([item for item in emails if bool(item.get("is_read")) and email_priority(item) != "low"]), "detail": "Messages already seen but still part of an active loop."},
            {"title": "Important Updates", "value": category_counts["updates"], "detail": "Receipts, reports, and status-style messages."},
            {"title": "Projects & Work", "value": category_counts["primary"] + category_counts["focused"], "detail": "Execution and work-related inbox traffic."},
            {"title": "Family & Personal", "value": category_counts["family"], "detail": "Household and relationship context."},
            {"title": "Newsletters", "value": category_counts["newsletters"], "detail": "Digest and read-later traffic."},
        ]

        threads = []
        for thread in sorted(thread_map.values(), key=lambda item: (str(item.get("last_received_at") or ""), int(item.get("unread_count") or 0)), reverse=True)[:6]:
            participants = sorted(str(name) for name in list(thread.get("participants") or []))
            threads.append(
                {
                    "thread_id": str(thread.get("thread_id") or "").strip(),
                    "subject": str(thread.get("subject") or "(No subject)").strip() or "(No subject)",
                    "participants": participants,
                    "participant_summary": ", ".join(participants[:2]) if participants else "Unknown sender",
                    "count": int(thread.get("count") or 0),
                    "unread_count": int(thread.get("unread_count") or 0),
                    "last_received_at": str(thread.get("last_received_at") or "").strip(),
                    "priority": str(thread.get("priority") or "low"),
                    "category": str(thread.get("category") or "primary"),
                }
            )

        automation_rows = [
            {
                "title": "Source Sync",
                "value": "Available" if inbox is not None else "Unavailable",
                "detail": "Unified inbox can refresh Gmail, Outlook, and calendar-adjacent sources." if inbox is not None else "Unified inbox is not initialised in this runtime.",
            },
            {
                "title": "Mark As Read",
                "value": "Available" if home_db is not None else "Unavailable",
                "detail": "Selected inbox items can be cleared from the desktop without leaving the board." if home_db is not None else "Inbox storage is not initialised in this runtime.",
            },
            {
                "title": "Draft Staging",
                "value": "Available" if callable(getattr(runtime, "stage_email_draft", None)) else "Unavailable",
                "detail": "Compose flows can stage a real email draft instead of pretending mail was sent." if callable(getattr(runtime, "stage_email_draft", None)) else "The shared email draft engine is not available in this runtime.",
            },
            {
                "title": "Continuity Log",
                "value": f"{len(recent_activity)} event(s)",
                "detail": "Operator actions tied to Email already feed into shared activity continuity.",
            },
        ]

        pending_actions = [
            {
                "email_id": str(item.get("id") or "").strip(),
                "subject": str(item.get("subject") or "(No subject)").strip() or "(No subject)",
                "sender": str(item.get("sender_name") or item.get("sender_email") or "Unknown sender").strip() or "Unknown sender",
                "received_at": str(item.get("received_at") or "").strip(),
                "priority": email_priority(item),
                "category": email_category(item),
                "action": "mark-read",
            }
            for item in waiting_emails[:6]
        ]

        snoozed_rows = [
            {
                "title": "No live snooze store",
                "detail": "This runtime does not expose a real snoozed-email backend yet, so Email is showing an honest boundary instead of fabricated parked mail.",
                "status": "Unavailable",
            }
        ]

        compose_actions = [
            {"id": "compose-draft", "title": "New Email", "prompt_hint": "Draft a concise email to [recipient] about [topic].", "available": callable(getattr(runtime, "stage_email_draft", None))},
            {"id": "reply-draft", "title": "Quick Reply", "prompt_hint": "Draft a polite reply to the selected email about [topic].", "available": callable(getattr(runtime, "stage_email_draft", None))},
            {"id": "follow-up-draft", "title": "Follow Up", "prompt_hint": "Draft a follow-up email about [topic] that moves the conversation forward.", "available": callable(getattr(runtime, "stage_email_draft", None))},
            {"id": "meeting-draft", "title": "Meeting Invite", "prompt_hint": "Draft an email inviting [recipient] to meet about [topic].", "available": callable(getattr(runtime, "stage_email_draft", None))},
            {"id": "boundary-tone", "title": "Tone Assistant", "available": False, "unavailable_reason": "A dedicated tone-adjustment backend route is not exposed yet in this runtime."},
            {"id": "boundary-grammar", "title": "Grammar Check", "available": False, "unavailable_reason": "A dedicated grammar-check backend route is not exposed yet in this runtime."},
            {"id": "boundary-improve", "title": "AI Improve", "available": False, "unavailable_reason": "A dedicated revise/improve backend route is not exposed yet in this runtime."},
        ]

        quick_search_actions = [
            {"id": "search-person", "title": "Search by Person", "route": "/command-center", "detail": "Email search by sender is currently routed into Command until a dedicated query surface exists."},
            {"id": "search-date", "title": "Search by Date", "route": "/command-center", "detail": "Email search by date is currently routed into Command until a dedicated query surface exists."},
            {"id": "search-attachments", "title": "Attachments", "route": "/command-center", "detail": "Attachment search is currently routed into Command until a dedicated query surface exists."},
            {"id": "boundary-unsubscribe", "title": "Unsubscribe", "detail": "A safe unsubscribe backend route is not exposed in this runtime."},
            {"id": "boundary-block-sender", "title": "Block Sender", "detail": "A safe sender-block backend route is not exposed in this runtime."},
            {"id": "boundary-create-rule", "title": "Create Rule", "detail": "A dedicated mail-rule backend route is not exposed in this runtime."},
            {"id": "boundary-export-thread", "title": "Export Thread", "detail": "A thread-export backend route is not exposed in this runtime."},
        ]

        trusted_actions = [
            {
                "id": "sync-sources",
                "title": "Sync Sources",
                "note": "Runs the live Gmail and Outlook sync boundary through the unified inbox.",
                "action_type": "sync-sources",
                "primary": True,
                "available": bool(inbox is not None),
                "unavailable_reason": "Unified inbox is not initialised in this runtime." if inbox is None else "",
            },
            {
                "id": "mark-selected-read",
                "title": "Mark Selected Read",
                "note": "Clears the selected email from the unread queue through the live inbox cache.",
                "action_type": "mark-read",
                "primary": False,
                "available": bool(home_db is not None and selected_email_id),
                "unavailable_reason": "No selected email is available to mark read." if not selected_email_id else ("Home inbox storage is not initialised in this runtime." if home_db is None else ""),
                "email_id": selected_email_id,
            },
            {
                "id": "compose-draft",
                "title": "Compose Draft",
                "note": "Stages a real email draft through the shared draft-and-alert boundary.",
                "action_type": "stage-draft",
                "primary": False,
                "available": callable(getattr(runtime, "stage_email_draft", None)),
                "unavailable_reason": "The shared email draft engine is not available in this runtime." if not callable(getattr(runtime, "stage_email_draft", None)) else "",
                "prompt_hint": "Draft a concise email to [recipient] about [topic].",
            },
        ]

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": f"Email loaded {total_cached} cached message(s), {total_unread} unread signal(s), {len(source_rows)} source lane(s), and {len(recent_activity)} continuity event(s).",
            "what_became_real": "Email now hydrates from live inbox cache, source sync state, draft staging, and operator continuity instead of browser-side invented inbox math and fake connector status.",
            "remains_partial": "Direct send, snooze, unsubscribe, rules, and richer mailbox search still depend on backend routes that are not yet exposed in this runtime.",
            "runtime_note": "Email is live and connected.",
            "availability_notes": availability_notes[:10],
            "counts": {
                "cached": total_cached,
                "unread": total_unread,
                "priority": priority_counts["high"],
                "waiting": len(waiting_emails),
                "flagged": total_flagged,
                "focused": len(focused_emails),
                "accounts": len(source_rows),
                "connected_accounts": len([row for row in source_rows if row["status"] not in {"not-connected", "disconnected"}]),
                "recent_activity": len(recent_activity),
                "inbox_health_score": inbox_health_score,
            },
            "selected_email_id": selected_email_id,
            "emails": emails,
            "stats": {
                **stats,
                "total_unread": total_unread,
                "total_flagged": total_flagged,
                "total_cached": total_cached,
            },
            "inbox_overview": inbox_overview,
            "priority_rows": priority_rows,
            "intelligence_cards": intelligence_cards,
            "pattern_rows": pattern_rows,
            "health_rows": health_rows,
            "source_rows": source_rows,
            "categories": categories,
            "threads": threads,
            "pending_actions": pending_actions,
            "automation_rows": automation_rows,
            "snoozed_rows": snoozed_rows,
            "compose_actions": compose_actions,
            "quick_search_actions": quick_search_actions,
            "trusted_actions": trusted_actions,
            "recent_activity": recent_activity,
            "proof_paths": {
                "module_route": "/email-center",
                "module_api": "/api/email/module",
                "home_email_api": "/api/home/email",
                "home_email_stats_api": "/api/home/email/stats",
                "mark_read_api": "/api/home/email/{email_id}/read",
                "sync_api": "/api/home/sync",
                "draft_api": "/api/stage/email/draft",
                "activity_api": "/api/activity/operator-action",
                "action_api": "/api/email/module/action",
            },
            "errors": errors,
        }

        if errors and not emails and not sync_states and not recent_activity:
            payload["available"] = False
            payload["status"] = "Wired"
            payload["summary"] = "Email is wired, but the runtime could not hydrate enough live inbox or sync data to make the surface fully useful."
            payload["runtime_note"] = "Email is partially connected. Live inbox and sync sources did not fully hydrate."
            payload["remains_partial"] = "Email needs live inbox cache or connector state in this runtime before the desktop can become richly informative."
        elif errors:
            payload["runtime_note"] = "Email is live, but some inbox or sync sources are partially unavailable."
        elif not emails:
            payload["runtime_note"] = "Email is live, but no cached email is currently visible in this runtime."
            payload["availability_notes"].append("No cached email is currently available, so Email is showing a real empty state.")
        if not payload["availability_notes"]:
            payload["availability_notes"].append("All currently available Email sources hydrated successfully.")
        return payload

    @app.get("/api/email/module")
    async def api_email_module(actor: str = "Chris") -> JSONResponse:
        return _json(await _build_email_module_payload(actor))

    @app.post("/api/email/module/action")
    async def api_email_module_action(payload: dict[str, Any]) -> JSONResponse:
        action = str(payload.get("action") or "").strip().lower()
        if not action:
            raise HTTPException(status_code=400, detail="Action is required.")

        if action == "sync-sources":
            inbox = _get_unified_inbox()
            if inbox is None:
                raise HTTPException(status_code=503, detail="Unified inbox not initialised")
            result = await asyncio.to_thread(inbox.sync_all)
            return _json({
                "ok": True,
                "action": action,
                "message": "Email sources synced.",
                "result": result,
            })

        if action == "mark-read":
            email_id = str(payload.get("email_id") or "").strip()
            if not email_id:
                raise HTTPException(status_code=400, detail="email_id is required.")
            home_db = _get_home_db()
            if home_db is None:
                raise HTTPException(status_code=503, detail="Home inbox storage not initialised")
            await asyncio.to_thread(home_db.mark_email_read, email_id)
            return _json({
                "ok": True,
                "action": action,
                "email_id": email_id,
                "message": "Email marked read.",
            })

        if action == "stage-draft":
            draft_payload = dict(payload.get("draft") or {})
            has_mailbox_contract = all(
                key in draft_payload
                for key in ("request_id", "arena_id", "principal_id", "source_message", "draft_intent", "stage_policy")
            )

            if has_mailbox_contract:
                if not callable(getattr(runtime, "stage_email_draft", None)):
                    raise HTTPException(status_code=503, detail="Email draft engine is unavailable in this runtime.")
                result = runtime.stage_email_draft(draft_payload)
                return _json({
                    "ok": True,
                    "action": action,
                    "mode": "mailbox-draft",
                    "message": "Email draft staged.",
                    "result": result,
                }, status_code=201)

            if not callable(getattr(runtime, "draft_message", None)):
                raise HTTPException(status_code=503, detail="Draft staging is unavailable in this runtime.")

            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                raise HTTPException(status_code=400, detail="A draft payload or prompt is required.")

            recipient_name = str(payload.get("recipient_name") or "").strip()
            recipient_email = str(payload.get("recipient_email") or "").strip()
            audience = recipient_name or recipient_email or "Email recipient"
            subject = str(payload.get("subject") or "Email draft from JARVIS").strip() or "Email draft from JARVIS"
            intent = str(payload.get("intent") or "follow_up").strip().replace("_", " ") or "follow up"
            actor = str(payload.get("actor") or "Chris").strip() or "Chris"
            tone = str(payload.get("tone") or "warm").strip() or "warm"
            context = f"Subject: {subject}\nIntent: {intent}\n\n{prompt}"

            result = runtime.draft_message(
                actor,
                audience,
                f"Email {intent}",
                context,
                tone,
            )
            return _json({
                "ok": True,
                "action": action,
                "mode": "review-draft",
                "message": "Email draft staged for review.",
                "boundary_note": "Mailbox-native reply staging still requires a trust-arena email payload.",
                "result": result,
            }, status_code=201)

        raise HTTPException(status_code=400, detail=f"Unsupported email module action: {action}")

    @app.get("/api/social/module")
    async def api_social_module(actor: str = "Chris") -> JSONResponse:
        return _json(await _build_social_module_payload(actor))

    @app.post("/api/social/module/action")
    async def api_social_module_action(payload: dict[str, Any]) -> JSONResponse:
        action = str(payload.get("action") or "").strip().lower()
        if not action:
            raise HTTPException(status_code=400, detail="Action is required.")

        if action == "refresh":
            return _json({
                "ok": True,
                "action": action,
                "message": "Social Media refreshed.",
                "module": await _build_social_module_payload(str(payload.get("actor") or "Chris").strip() or "Chris"),
            })

        publishing = _publishing_or_503()

        if action in {"create-post", "schedule-post"}:
            from .publishing_suite import SocialPost
            import uuid as _service_uuid

            content = str(payload.get("content") or "").strip()
            platform = str(payload.get("platform") or "").strip().lower()
            if not content:
                raise HTTPException(status_code=400, detail="content is required.")
            if not platform:
                raise HTTPException(status_code=400, detail="platform is required.")
            scheduled_at = str(payload.get("scheduled_at") or "").strip()
            status = "scheduled" if action == "schedule-post" and scheduled_at else "draft"
            post = SocialPost(
                post_id=str(_service_uuid.uuid4()),
                platform=platform,
                content=content,
                media_urls=list(payload.get("media_urls", []) or []),
                status=status,
                scheduled_at=scheduled_at,
                campaign_id=str(payload.get("campaign_id") or "").strip(),
                project_id=str(payload.get("project_id") or "").strip(),
                performance={},
            )
            await asyncio.to_thread(publishing._store.save_social_post, post)
            return _json(
                {
                    "ok": True,
                    "action": action,
                    "message": "Scheduled social post created." if status == "scheduled" else "Social post draft created.",
                    "post": post.to_dict(),
                },
                status_code=201,
            )

        if action == "approve-post":
            engine = _get_social_engine()
            if engine is None:
                raise HTTPException(status_code=503, detail="SocialEngine not initialised")
            post_id = str(payload.get("post_id") or "").strip()
            if not post_id:
                raise HTTPException(status_code=400, detail="post_id is required.")
            post = await asyncio.to_thread(engine.store.get_post, post_id)
            if post is None:
                raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
            if str(post.status or "").lower() not in {"pending_approval", "draft"}:
                raise HTTPException(status_code=400, detail=f"Post is {post.status}; cannot approve")
            post.status = "approved"
            await asyncio.to_thread(engine.store.save_post, post)
            return _json(
                {
                    "ok": True,
                    "action": action,
                    "message": "Social post approved.",
                    "post": post.to_dict(),
                }
            )

        if action == "execute-project":
            engine = _get_social_engine()
            if engine is None:
                raise HTTPException(status_code=503, detail="SocialEngine not initialised")
            project_id = str(payload.get("project_id") or "").strip()
            if not project_id:
                raise HTTPException(status_code=400, detail="project_id is required.")
            result = await asyncio.to_thread(engine.quicksilver.execute_scheduled_posts, project_id)
            return _json(
                {
                    "ok": True,
                    "action": action,
                    "message": "Social execution run completed.",
                    "result": result,
                }
            )

        raise HTTPException(status_code=400, detail=f"Unsupported social module action: {action}")

    @app.get("/api/news/module")
    async def api_news_module(actor: str = "Chris", force: bool = False) -> JSONResponse:
        return _json(await _build_news_module_payload(actor, force=force))

    @app.post("/api/news/module/action")
    async def api_news_module_action(payload: dict[str, Any]) -> JSONResponse:
        action = str(payload.get("action") or "").strip().lower()
        if not action:
            raise HTTPException(status_code=400, detail="Action is required.")

        if action == "refresh":
            module_payload = await _build_news_module_payload(str(payload.get("actor") or "Chris").strip() or "Chris", force=True)
            return _json({
                "ok": True,
                "action": action,
                "message": "News refreshed.",
                "module": module_payload,
            })

        audit = AuditLog(DEFAULT_AUDIT_ROOT)
        action_title = str(payload.get("title") or payload.get("action_label") or action or "News action").strip() or "News action"
        detail = str(payload.get("detail") or "").strip()
        related_label = str(payload.get("article_title") or payload.get("related_label") or action_title).strip() or action_title
        route = str(payload.get("route") or "/news-center").strip() or "/news-center"
        route_label = str(payload.get("route_label") or "Open News").strip() or "Open News"
        result_summary = str(payload.get("result_summary") or "News action recorded.").strip() or "News action recorded."
        why_now = str(payload.get("why_now") or detail or "News recorded an operator action for later continuity.").strip()

        if action in {"save-article", "mark-reviewed", "set-alert", "share-brief"}:
            message_map = {
                "save-article": "Article saved to shared continuity.",
                "mark-reviewed": "Story marked reviewed in shared continuity.",
                "set-alert": "News alert intent recorded for follow-up.",
                "share-brief": "Brief handoff recorded for follow-up.",
            }
            message = message_map[action]
            audit.log_event(
                "operator-action",
                {
                    "actor": str(payload.get("actor") or "Chris").strip() or "Chris",
                    "domain": "news",
                    "action": action_title,
                    "title": action_title,
                    "detail": detail or message,
                    "why_now": why_now,
                    "result_summary": result_summary or message,
                    "related_route": route,
                    "route_label": route_label,
                    "related_kind": str(payload.get("related_kind") or "news").strip() or "news",
                    "related_label": related_label,
                    "succeeded": True,
                    "source_kind": "operator-action",
                },
            )
            return _json({"ok": True, "action": action, "message": message})

        raise HTTPException(status_code=400, detail=f"Unsupported news module action: {action}")

    async def _build_home_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        availability_notes: list[str] = []
        errors: list[str] = []

        overview: dict[str, Any] = {}
        environment: dict[str, Any] = {}
        agenda: dict[str, Any] = {"events": [], "total": 0}
        perception: dict[str, Any] = {}

        try:
            overview = await asyncio.to_thread(runtime.home_overview)
        except Exception as exc:
            errors.append(f"home_overview: {exc}")
            availability_notes.append(f"Home overview could not be loaded: {exc}")

        try:
            environment = await asyncio.to_thread(runtime.environment_status_snapshot, actor_name)
        except Exception as exc:
            errors.append(f"environment_status: {exc}")
            availability_notes.append(f"Environment status could not be loaded: {exc}")

        try:
            perception = await asyncio.to_thread(runtime.perception_overview)
        except Exception as exc:
            errors.append(f"perception_overview: {exc}")
            availability_notes.append(f"Perception overview could not be loaded: {exc}")

        inbox = _get_unified_inbox()
        if inbox is None:
            db = _get_home_db()
            if db is None:
                availability_notes.append("Calendar and household inbox sources are not initialised in this runtime.")
            else:
                try:
                    events = list(await asyncio.to_thread(db.get_todays_events))
                    agenda = {"events": events, "total": len(events)}
                except Exception as exc:
                    errors.append(f"agenda: {exc}")
                    availability_notes.append(f"Today's home calendar could not be loaded: {exc}")
        else:
            try:
                agenda = dict(await asyncio.to_thread(inbox.get_todays_agenda) or {"events": [], "total": 0})
            except Exception as exc:
                errors.append(f"agenda: {exc}")
                availability_notes.append(f"Today's home calendar could not be loaded: {exc}")

        dashboard: dict[str, Any] = {}
        active_projects: list[dict[str, Any]] = []
        open_tasks: list[dict[str, Any]] = []
        today_tasks: list[dict[str, Any]] = []
        overdue_tasks: list[dict[str, Any]] = []
        sync_status: dict[str, Any] = {}
        value_summary: dict[str, Any] = {"totals": {}, "by_project": {}}
        home_db = _get_home_db()
        if home_db is None:
            availability_notes.append("Home project and task storage are not initialised, so household work queues are partial.")
        else:
            try:
                dashboard = dict(await asyncio.to_thread(home_db.get_dashboard_data) or {})
            except Exception as exc:
                errors.append(f"dashboard: {exc}")
                availability_notes.append(f"Home dashboard summary could not be loaded: {exc}")
            try:
                active_projects = list(await asyncio.to_thread(home_db.list_projects, "active"))
            except Exception as exc:
                errors.append(f"projects: {exc}")
                availability_notes.append(f"Active home projects could not be loaded: {exc}")
            try:
                open_tasks = list(await asyncio.to_thread(home_db.list_tasks, None, "open"))
            except Exception as exc:
                errors.append(f"tasks_open: {exc}")
                availability_notes.append(f"Open home tasks could not be loaded: {exc}")
            try:
                today_tasks = list(await asyncio.to_thread(home_db.get_tasks_due_today))
            except Exception as exc:
                errors.append(f"tasks_today: {exc}")
                availability_notes.append(f"Today's home tasks could not be loaded: {exc}")
            try:
                overdue_tasks = list(await asyncio.to_thread(home_db.get_overdue_tasks))
            except Exception as exc:
                errors.append(f"tasks_overdue: {exc}")
                availability_notes.append(f"Overdue home tasks could not be loaded: {exc}")
            try:
                sync_status = {"sources": list(await asyncio.to_thread(home_db.get_all_sync_states))}
            except Exception as exc:
                errors.append(f"sync_status: {exc}")
                availability_notes.append(f"Home sync status could not be loaded: {exc}")
            try:
                value_summary = dict(await asyncio.to_thread(home_db.get_value_summary) or {"totals": {}, "by_project": {}})
            except Exception as exc:
                errors.append(f"value_summary: {exc}")
                availability_notes.append(f"Home value summary could not be loaded: {exc}")

        counts = dict(overview.get("counts") or {})
        lights = list(overview.get("lights") or [])
        switches = list(overview.get("switches") or [])
        locks = list(overview.get("locks") or [])
        garage = list(overview.get("garage") or [])
        climate = list(overview.get("climate") or [])
        recent_actions = list(overview.get("recent_actions") or [])
        energy_windows = list(overview.get("energy_windows") or [])
        provider_notes = dict(overview.get("provider_notes") or {})
        anomalies = list(perception.get("anomalies") or [])
        camera_events = list(perception.get("camera_events") or [])
        phone_presence = list(perception.get("phone_presence") or [])
        actor_presence = {
            str(key).strip().lower(): str(value).strip().lower()
            for key, value in dict(perception.get("actor_presence") or {}).items()
        }

        household = getattr(runtime, "household", None)
        household_users = list((getattr(household, "users", {}) or {}).values()) if household is not None else []
        role_space = {
            "director": "Office",
            "household-coordinator": "Kitchen",
            "student": "Study",
        }
        role_label = {
            "director": "Director",
            "household-coordinator": "Household Coordinator",
            "student": "Student",
        }
        people: list[dict[str, Any]] = []
        for user in household_users[:6]:
            name = str(getattr(user, "display_name", "Household Member") or "Household Member").strip() or "Household Member"
            role = str(getattr(user, "role", "") or "").strip().lower()
            state = actor_presence.get(name.lower(), "")
            latest_phone = next((item for item in phone_presence if str(item.get("actor", "")).strip().lower() == name.lower()), {})
            if state in {"home", "arrived", "present", "inside"}:
                status = "Home"
                tone = "good"
            elif state in {"away", "departed", "outside"}:
                status = "Away"
                tone = "low"
            else:
                status = "Profile"
                tone = "low"
            people.append(
                {
                    "name": name,
                    "status": status,
                    "detail": str(latest_phone.get("zone") or role_space.get(role, "Household")).strip() or "Household",
                    "timing": str(latest_phone.get("timestamp") or "Profile-backed").strip() or "Profile-backed",
                    "tone": tone,
                    "role": role_label.get(role, "Household"),
                    "source": "presence" if state else "profile",
                }
            )
        if not people:
            availability_notes.append("No household roster is configured yet, so people-at-home is limited to runtime presence evidence.")
            for item in phone_presence[:4]:
                actor = str(item.get("actor") or item.get("device") or "Presence source").strip() or "Presence source"
                state = str(item.get("state") or "unknown").strip().lower()
                people.append(
                    {
                        "name": actor,
                        "status": "Home" if state in {"home", "arrived", "present", "inside"} else "Away" if state in {"away", "departed", "outside"} else "Unknown",
                        "detail": str(item.get("zone") or "Presence lane").strip() or "Presence lane",
                        "timing": str(item.get("timestamp") or "Recently").strip() or "Recently",
                        "tone": "good" if state in {"home", "arrived", "present", "inside"} else "low",
                        "role": "Presence",
                        "source": "presence",
                    }
                )

        total_due_today = int(((dashboard.get("tasks") or {}).get("due_today")) or len(today_tasks))
        total_overdue = int(((dashboard.get("tasks") or {}).get("overdue")) or len(overdue_tasks))
        open_locks = int(counts.get("open_locks") or 0)
        garage_not_closed = int(counts.get("garage_not_closed") or 0)
        active_leaks = int(counts.get("active_leaks") or 0)
        cold_variances = int(counts.get("cold_storage_variances") or 0)
        active_alert_count = int(((environment.get("status_summary") or {}).get("active_alert_count")) or 0)
        watch_count = int(((environment.get("status_summary") or {}).get("watch_count")) or 0)
        review_count = open_locks + garage_not_closed + active_leaks + cold_variances + total_due_today + total_overdue + active_alert_count

        queue_rows: list[dict[str, Any]] = []
        for task in overdue_tasks[:3]:
            queue_rows.append(
                {
                    "title": str(task.get("title") or "Overdue home task").strip() or "Overdue home task",
                    "detail": str(task.get("next_step") or task.get("description") or "This task is overdue and needs follow-through.").strip() or "This task is overdue and needs follow-through.",
                    "zone": str(task.get("project_id") or "Operations").strip() or "Operations",
                    "priority": "High",
                    "tone": "warn",
                    "task_id": str(task.get("id") or "").strip(),
                    "action_type": "complete-task",
                }
            )
        for task in today_tasks[:3]:
            queue_rows.append(
                {
                    "title": str(task.get("title") or "Home task due today").strip() or "Home task due today",
                    "detail": str(task.get("next_step") or task.get("description") or "This task is due today.").strip() or "This task is due today.",
                    "zone": "Today",
                    "priority": str(task.get("priority") or "Medium").strip().title() or "Medium",
                    "tone": "warn" if str(task.get("priority") or "").strip().lower() == "high" else "low",
                    "task_id": str(task.get("id") or "").strip(),
                    "action_type": "complete-task",
                }
            )
        for item in list((overview.get("cold_storage") or {}).get("active_sensors") or [])[:2]:
            queue_rows.append(
                {
                    "title": f"{str(item.get('name') or 'Cold storage').strip() or 'Cold storage'} variance",
                    "detail": str(item.get("recommended_action") or "Cold-storage variance needs review.").strip() or "Cold-storage variance needs review.",
                    "zone": str(item.get("location") or "Cold Storage").strip() or "Cold Storage",
                    "priority": "Medium",
                    "tone": "warn",
                }
            )
        if not queue_rows:
            queue_rows.append(
                {
                    "title": "Household queue is clear",
                    "detail": "No high-friction household task, alert, or signal is currently asking for authority.",
                    "zone": "Household",
                    "priority": "Low",
                    "tone": "good",
                }
            )

        today_rows: list[dict[str, Any]] = []
        for event in list(agenda.get("events") or [])[:5]:
            today_rows.append(
                {
                    "time": str(event.get("start_time") or event.get("start") or event.get("time") or "").strip(),
                    "title": str(event.get("summary") or event.get("title") or event.get("name") or "Household event").strip() or "Household event",
                    "status": str(event.get("location") or event.get("source") or "Today").strip() or "Today",
                    "tone": "low",
                }
            )
        if not today_rows:
            for task in today_tasks[:3]:
                today_rows.append(
                    {
                        "time": str(task.get("due_date") or "").strip(),
                        "title": str(task.get("title") or "Home task due today").strip() or "Home task due today",
                        "status": str(task.get("priority") or "Today").strip().title() or "Today",
                        "tone": "warn" if str(task.get("priority") or "").strip().lower() == "high" else "low",
                    }
                )

        away_rows: list[dict[str, Any]] = []
        combined_away = [*recent_actions[:4]]
        for item in camera_events[:3]:
            combined_away.append(
                {
                    "timestamp": item.get("timestamp"),
                    "target": item.get("camera") or item.get("zone") or "Camera",
                    "action": item.get("event_type") or "camera-event",
                    "detail": item.get("detail") or item.get("detected_object") or "Recent camera event",
                    "outcome": item.get("confidence") or "Recorded",
                }
            )
        for item in combined_away[:6]:
            away_rows.append(
                {
                    "time": str(item.get("timestamp") or "").strip(),
                    "title": str(item.get("target") or item.get("action") or "Home action").strip() or "Home action",
                    "detail": str(item.get("detail") or item.get("outcome") or "Recent home activity").strip() or "Recent home activity",
                    "status": str(item.get("outcome") or "Recorded").strip() or "Recorded",
                }
            )

        room_map: dict[str, dict[str, Any]] = {}
        for item in [*lights, *switches, *locks, *garage]:
            room = str(item.get("room") or item.get("location") or "Home").strip() or "Home"
            key = room.lower()
            bucket = room_map.setdefault(
                key,
                {"room": room, "devices": 0, "active": 0, "locked": 0},
            )
            bucket["devices"] += 1
            state = str(item.get("state") or "").strip().lower()
            if state in {"on", "open", "unlocked"}:
                bucket["active"] += 1
            if state in {"locked", "closed", "off"}:
                bucket["locked"] += 1
        spaces = [
            {
                "title": value["room"].replace("-", " ").replace("_", " ").title(),
                "note": f"{int(value['devices'])} tracked device(s) · {int(value['active'])} active",
                "status": "Active" if int(value["active"]) else "Calm",
            }
            for value in list(room_map.values())[:6]
        ]
        if not spaces:
            spaces = [{"title": "Home", "note": "No room-level device state is currently available.", "status": "Partial"}]

        insights: list[dict[str, Any]] = []
        for item in list(overview.get("summary") or [])[:3]:
            insights.append({"title": str(item).strip() or "Household summary", "detail": "Live household summary"})
        for item in anomalies[:2]:
            insights.append(
                {
                    "title": str(item.get("source") or item.get("category") or "Environment anomaly").strip() or "Environment anomaly",
                    "detail": str(item.get("recommendation") or item.get("detail") or "Perception surfaced an environmental anomaly.").strip() or "Perception surfaced an environmental anomaly.",
                }
            )
        for key, value in list(provider_notes.items())[:2]:
            insights.append(
                {
                    "title": str(key).replace("_", " ").replace("-", " ").title(),
                    "detail": str(value).strip() or "Provider note",
                }
            )
        if not insights:
            insights.append({"title": "No live home insights yet", "detail": "Home is wired, but the current runtime has not surfaced higher-order household insights yet."})

        recent_activity = _module_recent_activity(route="/home-center", domain="home", limit=10)
        if not recent_activity:
            recent_activity = _module_recent_activity(route="/command-center", domain="home", limit=6)

        trusted_actions = [
            {
                "id": "sync-home",
                "title": "Refresh Home Sources",
                "note": "Runs the live Home inbox and calendar sync boundary.",
                "action_type": "sync-home",
                "primary": True,
                "available": bool(inbox is not None),
                "unavailable_reason": "Unified inbox is not initialised in this runtime." if inbox is None else "",
            },
            {
                "id": "create-task",
                "title": "Create Follow-up Task",
                "note": "Writes a real task into the Home task store for anything this board surfaced.",
                "action_type": "create-task",
                "primary": False,
                "available": bool(home_db is not None),
                "unavailable_reason": "Home task storage is not initialised in this runtime." if home_db is None else "",
            },
            {
                "id": "complete-top-task",
                "title": "Complete Top Due Task",
                "note": "Closes the first overdue or due-today home task and rehydrates the board.",
                "action_type": "complete-top-task",
                "primary": False,
                "available": bool(overdue_tasks or today_tasks),
                "unavailable_reason": "No due or overdue home task is available to complete." if not (overdue_tasks or today_tasks) else "",
                "task_id": str(((overdue_tasks[:1] or today_tasks[:1] or [{}])[0].get("id") or "")).strip(),
            },
            {
                "id": "energy-window",
                "title": "Check Energy Window",
                "note": "Runs the live energy-window planner for the first staged appliance lane.",
                "action_type": "energy-window",
                "primary": False,
                "available": bool(energy_windows),
                "unavailable_reason": "No staged appliance energy window is configured yet." if not energy_windows else "",
                "appliance": str((energy_windows[:1] or [{}])[0].get("appliance") or "").strip(),
            },
        ]

        mode_status = "live" if str(overview.get("mode") or "").strip().lower() == "live" else "profile-backed"
        modes = [
            {"title": "Home", "note": "Normal daily flow", "active": review_count <= 2},
            {"title": "Away", "note": "Security and energy focus", "active": False},
            {"title": "Night", "note": "Quiet-hour posture", "active": False},
            {"title": "Hosting", "note": "Guest-ready routines", "active": False},
            {"title": "Recovery", "note": "Low-friction calm", "active": False},
            {"title": "Storm", "note": "Outage and prep posture", "active": bool((overview.get("outage_plan") or {}).get("minimumRuntimeMinutes"))},
        ]

        health_score = max(
            58,
            96
            - (open_locks * 12)
            - (garage_not_closed * 10)
            - (active_leaks * 18)
            - (cold_variances * 6)
            - (total_overdue * 5)
            - (active_alert_count * 7),
        )

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": (
                f"Home loaded {len(active_projects)} active project(s), {len(today_tasks)} due-today task(s), "
                f"{len(people)} household presence/profile row(s), and {len(recent_activity)} recent continuity event(s)."
            ),
            "what_became_real": "Home now hydrates from live household posture, perception, environment, task, calendar, sync, and continuity sources instead of browser-seeded family-presence and household-story defaults.",
            "remains_partial": "Physical occupancy, mode switching, and richer family presence are still limited by which live home and perception integrations are actually configured in this runtime.",
            "runtime_note": "Home is live and connected.",
            "availability_notes": availability_notes[:10],
            "counts": {
                "projects": len(active_projects),
                "tasks_open": len(open_tasks),
                "tasks_today": len(today_tasks),
                "tasks_overdue": len(overdue_tasks),
                "events_today": int(agenda.get("total") or len(list(agenda.get("events") or []))),
                "people": len(people),
                "home_count": len([item for item in people if str(item.get("status")).lower() == "home"]),
                "review_items": review_count,
                "anomalies": len(anomalies),
                "recent_activity": len(recent_activity),
                "active_alerts": active_alert_count,
                "watch_items": watch_count,
                "projected_value": float(((value_summary.get("totals") or {}).get("savings") or 0.0) + ((value_summary.get("totals") or {}).get("revenue") or 0.0)),
            },
            "overview": overview,
            "agenda": agenda,
            "dashboard": dashboard,
            "environment": environment,
            "people": people,
            "today_rows": today_rows,
            "queue": queue_rows[:6],
            "away_rows": away_rows[:6],
            "trusted_actions": trusted_actions,
            "health": {
                "score": health_score,
                "label": "Healthy" if health_score >= 88 else "Stable" if health_score >= 76 else "Watch",
                "components": [
                    {"label": "Safety", "value": max(55, 96 - (open_locks * 16) - (garage_not_closed * 12) - (active_leaks * 22))},
                    {"label": "Comfort", "value": max(60, 86 - (cold_variances * 8))},
                    {"label": "Readiness", "value": max(56, 92 - (review_count * 6))},
                    {"label": "Continuity", "value": max(60, 88 - (max(0, len(recent_actions) - 4) * 2))},
                ],
            },
            "modes": {
                "status": mode_status,
                "items": modes,
            },
            "spaces": spaces,
            "return_prep": [
                {
                    "title": f"Check {str(item.get('appliance') or 'energy lane').strip() or 'energy lane'}",
                    "detail": str(item.get("reason") or "Window prepared.").strip() or "Window prepared.",
                    "time": str(item.get("preferredWindow") or "Next window").strip() or "Next window",
                }
                for item in energy_windows[:4]
            ] or [
                {
                    "title": "No live return-home prep queued",
                    "detail": "No energy-window or arrival staging lane is active in this runtime.",
                    "time": "Unavailable",
                }
            ],
            "insights": insights[:6],
            "active_projects": active_projects[:6],
            "recent_activity": recent_activity,
            "sync_status": sync_status,
            "value_summary": value_summary,
            "proof_paths": {
                "module_route": "/home-center",
                "module_api": "/api/home/module",
                "overview_api": "/api/home-overview",
                "dashboard_api": "/api/home/dashboard",
                "calendar_today_api": "/api/home/calendar/today",
                "projects_api": "/api/home/projects?status=active",
                "tasks_today_api": "/api/home/tasks/today",
                "tasks_overdue_api": "/api/home/tasks/overdue",
                "sync_api": "/api/home/sync",
                "energy_window_api": "/api/energy-window",
                "operator_activity_api": "/api/activity/operator-action",
            },
            "errors": errors,
        }

        if errors and not (overview or dashboard or agenda.get("events") or people):
            payload["available"] = False
            payload["status"] = "Wired"
            payload["summary"] = "Home route is wired, but the runtime could not hydrate enough live household data to make the surface fully useful."
            payload["runtime_note"] = "Home is partially connected. Live household sources did not fully hydrate."
            payload["remains_partial"] = "Home needs more live household, task, calendar, or perception data in this runtime to become richly informative."
        elif errors:
            payload["runtime_note"] = "Home is live, but some household sources are partially unavailable."
        if not payload["availability_notes"]:
            payload["availability_notes"].append("All currently available Home sources hydrated successfully.")
        return payload

    @app.get("/api/home/module")
    async def api_home_module(actor: str = "Chris") -> JSONResponse:
        return _json(await _build_home_module_payload(actor))

    # ------------------------------------------------------------------
    # Agent Work System — GET routes (work items, standup, huddle)
    # ------------------------------------------------------------------

    async def _build_huddle_module_payload() -> dict[str, Any]:
        generated_at = ""
        try:
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()
        except Exception:
            generated_at = ""

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Huddle now has a dedicated module route with live standups, runtime posture, dossiers, and idea capture.",
            "what_became_real": "Huddle is now represented as a dedicated app module instead of a shell-only packet path.",
            "remains_partial": "Broader decision workflows and richer cross-route continuity review still need follow-on slices.",
            "runtime_note": "Huddle is live and connected.",
            "availability_notes": [],
            "counts": {
                "reports": 0,
                "approvals": 0,
                "blockers": 0,
                "dossiers": 0,
                "ideas_total": 0,
                "ideas_captured": 0,
                "ideas_queued": 0,
                "ideas_researching": 0,
                "active_work": 0,
                "recent_activity": 0,
                "pipeline": 0,
            },
            "total_active_work": 0,
            "approvals_count": 0,
            "blocker_count": 0,
            "ready_dossier_count": 0,
            "reports": [],
            "approvals": [],
            "blockers": [],
            "highlights": [],
            "runtime": {},
            "party_mode": {},
            "pipeline": [],
            "dossiers": [],
            "idea_inbox": {
                "total": 0,
                "captured_count": 0,
                "queued_count": 0,
                "recent": [],
            },
            "recent_activity": [],
            "proof_paths": {
                "module_route": "/huddle-center",
                "module_api": "/api/huddle/module",
                "huddle_api": "/api/huddle",
                "party_start_api": "/api/party-mode/start",
                "party_status_api": "/api/party-mode/status",
                "ideas_api": "/api/huddle/ideas",
                "idea_queue_api": "/api/huddle/ideas/{idea_id}/queue",
                "idea_pass_api": "/api/huddle/ideas/{idea_id}/pass",
                "idea_research_api": "/api/huddle/ideas/{idea_id}/research-now",
                "dossiers_api": "/api/dossiers",
                "dossier_chat_api": "/api/dossiers/{dossier_id}/chat",
                "pipeline_api": "/api/agent-work/passive-income",
                "approve_api_prefix": "/api/agent-work/approve/",
                "reject_api_prefix": "/api/agent-work/reject/",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        try:
            from dataclasses import asdict

            from .standup import collect_all_standups

            huddle = await asyncio.to_thread(collect_all_standups, None, runtime, False)
            data = asdict(huddle)
            reports = []
            for entry in list(data.get("agent_reports") or [])[:12]:
                reports.append(
                    {
                        "agent_id": str(entry.get("agent_id") or ""),
                        "agent_name": str(entry.get("agent_name") or entry.get("agent_id") or ""),
                        "domain": str(entry.get("domain") or ""),
                        "status": str(entry.get("status") or "ok"),
                        "summary": str(entry.get("summary") or entry.get("headline") or entry.get("today") or ""),
                        "needs": str(entry.get("needs") or ""),
                        "active_work_count": int(entry.get("active_work_count") or 0),
                        "highlights": [str(item) for item in list(entry.get("highlights") or [])[:4]],
                    }
                )
            approvals = []
            for entry in list(data.get("approvals_needed") or [])[:8]:
                approvals.append(
                    {
                        "work_id": str(entry.get("work_id") or ""),
                        "title": str(entry.get("title") or "Untitled"),
                        "agent": str(entry.get("agent") or entry.get("agent_id") or ""),
                        "proposal": str(entry.get("proposal") or entry.get("idea") or ""),
                        "domain": str(entry.get("domain") or ""),
                    }
                )
            payload["reports"] = reports
            payload["approvals"] = approvals
            payload["blockers"] = [str(item) for item in list(data.get("blockers") or [])[:6]]
            payload["highlights"] = [str(item) for item in list(data.get("highlights") or [])[:8]]
            payload["total_active_work"] = int(data.get("total_active_work") or 0)
            payload["approvals_count"] = len(approvals)
            payload["blocker_count"] = len(payload["blockers"])
            payload["counts"]["reports"] = len(reports)
            payload["counts"]["approvals"] = len(approvals)
            payload["counts"]["blockers"] = len(payload["blockers"])
            payload["counts"]["active_work"] = payload["total_active_work"]
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["summary"] = "Huddle center route is live, but standup aggregation did not fully hydrate."
            payload["remains_partial"] = "Live huddle standup sources still need repair or population in this runtime."
            payload["errors"].append(f"standups: {exc}")
            payload["availability_notes"].append("Standup aggregation is not fully available in this runtime.")

        try:
            runtime_snapshot = runtime.background_agent_status()
            statuses = []
            for item in list(runtime_snapshot.get("statuses") or [])[:6]:
                if not isinstance(item, dict):
                    continue
                statuses.append(
                    {
                        "agent_id": str(item.get("agent_id") or ""),
                        "label": str(item.get("label") or item.get("agent_id") or ""),
                        "state": str(item.get("state") or "idle"),
                        "reason": str(item.get("reason") or ""),
                        "last_run_at": str(item.get("last_run_at") or ""),
                    }
                )
            payload["runtime"] = {
                "active_mode": str(runtime_snapshot.get("active_mode") or ""),
                "quiet_hours_active": bool(runtime_snapshot.get("quiet_hours_active")),
                "awake_count": int(runtime_snapshot.get("awake_count") or 0),
                "idle_count": int(runtime_snapshot.get("idle_count") or 0),
                "blocked_count": int(runtime_snapshot.get("blocked_count") or 0),
                "last_tick_at": str(runtime_snapshot.get("last_tick_at") or ""),
                "statuses": statuses,
            }
        except Exception as exc:
            payload["errors"].append(f"runtime: {exc}")
            payload["availability_notes"].append(f"Runtime posture could not be read: {exc}")

        try:
            from .party_mode import get_party_controller

            payload["party_mode"] = get_party_controller(runtime).get_status()
        except Exception as exc:
            payload["errors"].append(f"party_mode: {exc}")
            payload["availability_notes"].append(f"Party mode status was unavailable: {exc}")

        try:
            from .agent_work import get_all_stores
            from dataclasses import asdict

            pipeline_items = []
            for store in get_all_stores().values():
                pipeline_items.extend(store.get_by_domain("passive-income"))
            pipeline_items.sort(key=lambda item: item.updated_at, reverse=True)
            payload["pipeline"] = [
                {
                    "work_id": str(item.get("work_id") or ""),
                    "agent_id": str(item.get("agent_id") or ""),
                    "title": str(item.get("title") or "Untitled"),
                    "status": str(item.get("status") or "watching"),
                    "idea": str(item.get("idea") or item.get("proposal") or item.get("research") or ""),
                    "updated_at": str(item.get("updated_at") or ""),
                }
                for item in (asdict(entry) for entry in pipeline_items[:10])
            ]
            payload["counts"]["pipeline"] = len(payload["pipeline"])
        except Exception as exc:
            payload["errors"].append(f"pipeline: {exc}")
            payload["availability_notes"].append(f"Passive-income pipeline was unavailable: {exc}")

        try:
            from .dossier import get_dossier_store

            store = get_dossier_store()
            items = []
            for dossier in store.get_all():
                if str(getattr(dossier, "status", "") or "").strip().lower() == "presented":
                    continue
                items.append(
                    {
                        "dossier_id": str(getattr(dossier, "dossier_id", "") or ""),
                        "title": str(getattr(dossier, "title", "") or "Untitled"),
                        "status": str(getattr(dossier, "status", "") or ""),
                        "executive_summary": str(
                            getattr(dossier, "executive_summary", "") or getattr(dossier, "market_opportunity", "") or ""
                        ),
                        "first_action": str(getattr(dossier, "first_action", "") or ""),
                        "confidence_score": float(getattr(dossier, "confidence_score", 0.0) or 0.0),
                        "updated_at": str(getattr(dossier, "updated_at", "") or getattr(dossier, "created_at", "") or ""),
                    }
                )
            items.sort(key=lambda item: item["updated_at"], reverse=True)
            payload["dossiers"] = items[:6]
            payload["ready_dossier_count"] = len(items)
            payload["counts"]["dossiers"] = len(payload["dossiers"])
        except Exception as exc:
            payload["errors"].append(f"dossiers: {exc}")
            payload["availability_notes"].append(f"Dossiers were unavailable: {exc}")

        try:
            from .ideas import list_ideas, stats

            summary = stats()
            ideas = list_ideas()
            by_status = dict(summary.get("by_status") or {})
            payload["idea_inbox"] = {
                "total": int(summary.get("total") or 0),
                "captured_count": int(by_status.get("captured") or 0),
                "queued_count": int(by_status.get("queued") or 0),
                "researching_count": int(by_status.get("researching") or 0),
                "done_count": int(by_status.get("done") or 0),
                "passed_count": int(by_status.get("passed") or 0),
                "recent": [
                    {
                        "id": str(item.get("id") or ""),
                        "text": str(item.get("text") or ""),
                        "status": str(item.get("status") or ""),
                        "domain": str(item.get("domain") or ""),
                        "created_at": str(item.get("created_at") or ""),
                    }
                    for item in ideas[:6]
                ],
            }
            payload["counts"]["ideas_total"] = payload["idea_inbox"]["total"]
            payload["counts"]["ideas_captured"] = payload["idea_inbox"]["captured_count"]
            payload["counts"]["ideas_queued"] = payload["idea_inbox"]["queued_count"]
            payload["counts"]["ideas_researching"] = payload["idea_inbox"]["researching_count"]
        except Exception as exc:
            payload["errors"].append(f"ideas: {exc}")
            payload["availability_notes"].append(f"Idea inbox was unavailable: {exc}")

        if payload["status"] == "Useful":
            payload["summary"] = (
                f"Huddle center loaded {len(payload['reports'])} standup report(s), "
                f"{payload['approvals_count']} approval item(s), and {payload['ready_dossier_count']} ready dossier(s)."
            )
            if not payload["reports"]:
                payload["status"] = "Wired"
                payload["remains_partial"] = "The dedicated Huddle screen is live, but no standup reports were available in this runtime."

        payload["recent_activity"] = _module_recent_activity(route="/huddle-center", domain="huddle")
        payload["counts"]["recent_activity"] = len(payload["recent_activity"])
        if not payload["reports"]:
            payload["availability_notes"].append("No live standup reports are currently available.")
        if not payload["dossiers"]:
            payload["availability_notes"].append("No ready dossiers are currently surfaced.")
        if not payload["pipeline"]:
            payload["availability_notes"].append("No passive-income workstreams are active right now.")
        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some huddle sources still failed to hydrate; inspect the payload preview for details."
            payload["runtime_note"] = "Huddle is live, but some sources are partially unavailable."
        if payload["availability_notes"] and payload["runtime_note"] == "Huddle is live and connected.":
            payload["runtime_note"] = payload["availability_notes"][0]
        return payload

    @app.get("/api/huddle")
    async def api_huddle() -> JSONResponse:
        """Return the daily huddle: all agent standups aggregated."""
        try:
            from .standup import collect_all_standups
            from dataclasses import asdict
            rt = runtime
            huddle = await asyncio.to_thread(
                collect_all_standups,
                None,       # all default agents
                rt,
                False,      # no LLM — fast stub for now; LLM opt-in via query param
            )
            return _json(asdict(huddle))
        except Exception as exc:
            logger.exception("Huddle generation failed: %s", exc)
            return _json({"error": str(exc), "agent_reports": [], "blockers": [], "highlights": []})

    @app.get("/api/huddle/module")
    async def api_huddle_module() -> JSONResponse:
        return _json(await _build_huddle_module_payload())

    @app.get("/api/agent-work")
    async def api_agent_work_list(agent_id: str = Query(default=""), status: str = Query(default="")) -> JSONResponse:
        """Return work items across all agents, or filtered by agent_id and/or status."""
        try:
            from .agent_work import get_all_stores, get_work_store
            from dataclasses import asdict
            if agent_id:
                store = get_work_store(agent_id)
                items = store.all_items()
            else:
                items = []
                for store in get_all_stores().values():
                    items.extend(store.all_items())
            if status:
                items = [i for i in items if i.status == status]
            items.sort(key=lambda x: x.updated_at, reverse=True)
            return _json({"items": [asdict(i) for i in items[:100]]})
        except Exception as exc:
            return _json({"items": [], "error": str(exc)})

    @app.get("/api/agent-work/proposed")
    async def api_agent_work_proposed() -> JSONResponse:
        """Return all proposed work items awaiting Chris's approval."""
        try:
            from .agent_work import get_all_proposed
            return _json({"proposed": get_all_proposed()})
        except Exception as exc:
            return _json({"proposed": [], "error": str(exc)})

    @app.get("/api/agent-work/passive-income")
    async def api_agent_work_passive_income() -> JSONResponse:
        """Return all passive income work items across all agents."""
        try:
            from .agent_work import get_all_stores
            from dataclasses import asdict
            results = []
            for store in get_all_stores().values():
                results.extend(store.get_by_domain("passive-income"))
            results.sort(key=lambda x: x.updated_at, reverse=True)
            return _json({"items": [asdict(i) for i in results]})
        except Exception as exc:
            return _json({"items": [], "error": str(exc)})

    @app.get("/api/dossiers")
    async def api_dossiers_list() -> JSONResponse:
        from .dossier import get_dossier_store
        from dataclasses import asdict
        store = get_dossier_store()
        items = store.get_all()
        return _json({"dossiers": [asdict(d) for d in items], "total": len(items)})

    @app.get("/api/dossiers/{work_id}")
    async def api_dossier_get(work_id: str) -> JSONResponse:
        from .dossier import get_dossier_store
        from dataclasses import asdict
        store = get_dossier_store()
        d = store.get_by_work_id(work_id)
        if d is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return _json(asdict(d))

    @app.post("/api/dossiers/{dossier_id}/chat")
    async def api_dossier_chat(dossier_id: str, payload: dict[str, Any]) -> JSONResponse:
        """Ask a question or request a refinement about a specific dossier."""
        from .dossier import get_dossier_store
        from dataclasses import asdict
        store = get_dossier_store()

        # Accept dossier_id OR work_id
        d = store.get(dossier_id)
        if d is None:
            d = store.get_by_work_id(dossier_id)
        if d is None:
            return JSONResponse({"error": "Dossier not found"}, status_code=404)

        message = (payload.get("message") or "").strip()
        if not message:
            return JSONResponse({"error": "No message provided"}, status_code=400)

        gw = _get_gateway()
        if gw is None:
            return JSONResponse({"error": "No LLM gateway available"}, status_code=503)

        # Build full dossier context
        sections = [
            ("Executive Summary",         d.executive_summary),
            ("Market Opportunity",         d.market_opportunity),
            ("Competitive Landscape",      d.competitive_landscape),
            ("Technical Requirements",     d.technical_requirements),
            ("Revenue Model",              d.revenue_model),
            ("Risk Assessment",            d.risk_assessment),
            ("90-Day Implementation Plan", d.implementation_plan),
            ("First Action",               d.first_action),
        ]
        context_parts = []
        for label, text in sections:
            if text and text.strip():
                context_parts.append(f"### {label}\n{text.strip()}")
        context = "\n\n".join(context_parts)

        system_prompt = (
            f"You are an expert startup analyst and advisor reviewing an investment dossier.\n\n"
            f"**Idea: {d.title}**\n\n"
            f"{context}\n\n"
            f"---\n"
            f"Answer the following question or request about this specific business idea. "
            f"Be direct, concrete, and grounded in the dossier content above. "
            f"If asked to reframe or refine something, rewrite that section completely."
        )

        full_prompt = f"{system_prompt}\n\nUser: {message}"
        try:
            response = gw.simple_complete(full_prompt, max_tokens=600, task_type="converse")
            return _json({"response": (response or "").strip(), "dossier_id": dossier_id})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.get("/api/party-mode/status")
    async def api_party_status() -> JSONResponse:
        from .party_mode import get_party_controller
        ctrl = get_party_controller(runtime)
        return _json(ctrl.get_status())

    @app.post("/api/party-mode/start")
    async def api_party_start() -> JSONResponse:
        from .party_mode import get_party_controller
        ctrl = get_party_controller(runtime)
        if ctrl.get_status().get("status") == "running":
            return _json({"status": "already_running"})
        await asyncio.to_thread(ctrl.start, True)
        return _json({"status": "started"})

    @app.get("/api/morning-brief")
    async def api_morning_brief() -> JSONResponse:
        """Formatted morning brief — dossiers ready + party session summary."""
        try:
            from .dossier import get_dossier_store
            from .party_mode import get_party_controller
            from dataclasses import asdict
            store = get_dossier_store()
            ctrl  = get_party_controller(runtime)
            status = ctrl.get_status()
            ready = store.get_ready()
            lines = [
                f"Good morning, Chris. Here is your JARVIS overnight research brief.",
                f"",
                f"Your agents built {len(ready)} investment dossier{'s' if len(ready) != 1 else ''} overnight.",
            ]
            if ready:
                lines.append("")
                for i, d in enumerate(ready, 1):
                    rev = ""
                    if d.revenue_estimate_low or d.revenue_estimate_high:
                        rev = f" | Revenue: ${d.revenue_estimate_low:,}–${d.revenue_estimate_high:,}/mo"
                    conf = f" | Confidence: {d.confidence_score:.1f}/10"
                    lines.append(f"{i}. {d.title}{rev}{conf}")
                    if d.executive_summary:
                        lines.append(f"   {d.executive_summary[:200]}")
                    if d.first_action:
                        lines.append(f"   First action: {d.first_action[:120]}")
                    lines.append("")
            session_log = status.get("agent_log", [])
            if session_log:
                lines.append(f"Session log ({len(session_log)} entries):")
                for entry in session_log[-5:]:
                    lines.append(f"  {entry}")
            return _json({
                "brief": "\n".join(lines),
                "dossier_count": len(ready),
                "dossiers": [asdict(d) for d in ready],
                "session": status,
            })
        except Exception as exc:
            return _json({"brief": f"Morning brief unavailable: {exc}", "dossier_count": 0})

    @app.get("/api/agent-standup/{agent_id}")
    async def api_agent_standup(agent_id: str) -> JSONResponse:
        """Return a single agent's standup report."""
        try:
            from .standup import generate_standup
            from dataclasses import asdict
            report = await asyncio.to_thread(generate_standup, agent_id, runtime, False)
            return _json(asdict(report))
        except Exception as exc:
            return _json({"error": str(exc), "agent_id": agent_id})

    # ------------------------------------------------------------------
    # Agent Work — approval actions (POST, must be before catch-all)
    # ------------------------------------------------------------------

    @app.post("/api/agent-work/approve/{work_id}")
    async def api_agent_work_approve(work_id: str) -> JSONResponse:
        """Approve a proposed work item."""
        try:
            from .agent_work import get_all_stores
            from dataclasses import asdict
            for store in get_all_stores().values():
                item = store.get(work_id)
                if item is not None:
                    store.mark_approved(work_id, approved_by="Chris")
                    updated = store.get(work_id)
                    return _json({"approved": True, "item": asdict(updated)})
            raise HTTPException(status_code=404, detail=f"Work item not found: {work_id}")
        except HTTPException:
            raise
        except Exception as exc:
            return _json({"approved": False, "error": str(exc)})

    @app.post("/api/agent-work/reject/{work_id}")
    async def api_agent_work_reject(work_id: str, request: Request) -> JSONResponse:
        """Reject a proposed work item."""
        try:
            from .agent_work import get_all_stores
            from dataclasses import asdict
            body = {}
            try:
                body = await request.json()
            except Exception:
                pass
            reason = str(body.get("reason", "Declined by Chris"))
            for store in get_all_stores().values():
                item = store.get(work_id)
                if item is not None:
                    store.mark_rejected(work_id, reason=reason)
                    updated = store.get(work_id)
                    return _json({"rejected": True, "item": asdict(updated)})
            raise HTTPException(status_code=404, detail=f"Work item not found: {work_id}")
        except HTTPException:
            raise
        except Exception as exc:
            return _json({"rejected": False, "error": str(exc)})

    # ------------------------------------------------------------------
    # Idea Inbox endpoints
    # ------------------------------------------------------------------

    @app.get("/api/ideas")
    async def api_ideas_list(status: str = Query(default="")) -> JSONResponse:
        """List all ideas. Optional ?status= filter."""
        from .ideas import list_ideas, stats
        ideas = await asyncio.to_thread(list_ideas, status or None)
        summary = await asyncio.to_thread(stats)
        return _json({"ideas": ideas, "stats": summary})

    @app.post("/api/ideas")
    async def api_ideas_add(request: Request) -> JSONResponse:
        """Capture a new idea. Body: {text, notes?, domain?, tags?}"""
        from .ideas import add_idea
        body = await request.json()
        text = str(body.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        idea = await asyncio.to_thread(
            add_idea,
            text,
            "user",
            str(body.get("notes", "")),
            str(body.get("domain", "passive-income")),
            list(body.get("tags", [])),
        )
        return _json({"idea": idea}, status_code=201)

    @app.post("/api/huddle/ideas")
    async def api_huddle_ideas_add(request: Request) -> JSONResponse:
        from .ideas import add_idea

        body = await request.json()
        text = str(body.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        actor = str(body.get("actor") or "Chris").strip() or "Chris"
        domain = str(body.get("domain", "passive-income")).strip() or "passive-income"
        idea = await asyncio.to_thread(
            add_idea,
            text,
            "user",
            str(body.get("notes", "")),
            domain,
            list(body.get("tags", [])),
        )
        focus = _record_huddle_idea_focus(
            actor=actor,
            action="Capture Huddle Idea",
            detail=f"Huddle captured a live idea in the {domain} lane.",
            why_now="The Huddle module pushed a real idea into the live research inbox.",
            result_summary="Huddle idea captured.",
            related_label=str(idea.get("text") or idea.get("id") or "Idea"),
        )
        await _broadcast_dashboard("huddle-ideas.updated")
        return _json({"idea": idea, "focus": focus}, status_code=201)

    @app.post("/api/ideas/{idea_id}/queue")
    async def api_ideas_queue(idea_id: str) -> JSONResponse:
        """Mark an idea as queued for background research."""
        from .ideas import queue_idea
        updated = await asyncio.to_thread(queue_idea, idea_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Idea not found")
        return _json({"idea": updated})

    @app.post("/api/huddle/ideas/{idea_id}/queue")
    async def api_huddle_ideas_queue(idea_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
        from .ideas import queue_idea

        updated = await asyncio.to_thread(queue_idea, idea_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Idea not found")
        focus = _record_huddle_idea_focus(
            actor=str((payload or {}).get("actor") or "Chris"),
            action="Queue Huddle Idea",
            detail=f"Huddle queued {str(updated.get('text') or idea_id).strip() or idea_id} for background research.",
            why_now="The Huddle module promoted a captured idea into the queued research lane.",
            result_summary="Huddle idea queued.",
            related_label=str(updated.get("text") or updated.get("id") or idea_id),
        )
        await _broadcast_dashboard("huddle-ideas.updated")
        return _json({"idea": updated, "focus": focus})

    @app.post("/api/ideas/{idea_id}/pass")
    async def api_ideas_pass(idea_id: str) -> JSONResponse:
        """Dismiss an idea (pass on it)."""
        from .ideas import pass_idea
        updated = await asyncio.to_thread(pass_idea, idea_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Idea not found")
        return _json({"idea": updated})

    @app.post("/api/huddle/ideas/{idea_id}/pass")
    async def api_huddle_ideas_pass(idea_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
        from .ideas import pass_idea

        updated = await asyncio.to_thread(pass_idea, idea_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Idea not found")
        focus = _record_huddle_idea_focus(
            actor=str((payload or {}).get("actor") or "Chris"),
            action="Pass Huddle Idea",
            detail=f"Huddle passed on {str(updated.get('text') or idea_id).strip() or idea_id} after review.",
            why_now="The Huddle module intentionally dismissed a live idea instead of leaving it stalled in the inbox.",
            result_summary="Huddle idea passed.",
            related_label=str(updated.get("text") or updated.get("id") or idea_id),
        )
        await _broadcast_dashboard("huddle-ideas.updated")
        return _json({"idea": updated, "focus": focus})

    @app.delete("/api/ideas/{idea_id}")
    async def api_ideas_delete(idea_id: str) -> JSONResponse:
        """Hard-delete an idea."""
        from .ideas import delete_idea
        ok = await asyncio.to_thread(delete_idea, idea_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Idea not found")
        return _json({"deleted": True})

    async def _research_idea_now_impl(
        idea_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        from .ideas import get_idea, mark_researching, mark_done, queue_idea
        idea = await asyncio.to_thread(get_idea, idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.get("status") == "researching":
            return {"queued": False, "message": "Already researching", "idea": idea}

        # Ensure it's at least queued
        if idea.get("status") == "captured":
            await asyncio.to_thread(queue_idea, idea_id)

        gw = _get_gateway()
        if gw is None:
            raise HTTPException(status_code=503, detail="LLM gateway not available")

        # Create WorkItem under catalyst-personal
        try:
            from .agent_work import get_work_store
            pi_store = get_work_store("catalyst-personal")
            work_item = await asyncio.to_thread(
                pi_store.dream_idea,
                idea["text"][:80],
                idea["text"],
                idea.get("domain", "passive-income"),
                idea.get("tags", []),
            )
            work_id = work_item.work_id
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to create work item: {exc}")

        # Mark idea as researching
        await asyncio.to_thread(mark_researching, idea_id, work_id)

        # Fire DossierBuilder in background
        async def _build_dossier() -> None:
            import asyncio as _asyncio
            try:
                from .dossier import build_dossier_for_work_item, get_dossier_store
                from .ideas import mark_done as _mark_done
                dossier = await _asyncio.to_thread(
                    build_dossier_for_work_item, work_item, gw, ""
                )
                dossier_store = get_dossier_store()
                await _asyncio.to_thread(dossier_store.save, dossier)
                await _asyncio.to_thread(
                    _mark_done, idea_id, dossier.dossier_id, work_id
                )
            except Exception as exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "Idea research failed for %s: %s", idea_id, exc
                )

        background_tasks.add_task(_build_dossier)

        return {
            "queued": True,
            "work_id": work_id,
            "idea": await asyncio.to_thread(get_idea, idea_id),
            "message": "Research started — check /api/dossiers for results.",
        }

    @app.post("/api/ideas/{idea_id}/research-now")
    async def api_ideas_research_now(
        idea_id: str,
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        """
        Immediately trigger dossier research for an idea (don't wait for party mode).
        Creates a WorkItem under catalyst-personal, fires DossierBuilder in the background.
        Returns immediately with the work_id — poll /api/dossiers for the result.
        """
        return _json(await _research_idea_now_impl(idea_id, background_tasks))

    @app.post("/api/huddle/ideas/{idea_id}/research-now")
    async def api_huddle_ideas_research_now(
        idea_id: str,
        background_tasks: BackgroundTasks,
        payload: dict[str, Any] | None = None,
    ) -> JSONResponse:
        result = await _research_idea_now_impl(idea_id, background_tasks)
        focus = _record_huddle_idea_focus(
            actor=str((payload or {}).get("actor") or "Chris"),
            action="Research Huddle Idea Now",
            detail=f"Huddle launched live dossier research for {str((result.get('idea') or {}).get('text') or idea_id).strip() or idea_id}.",
            why_now="The Huddle module escalated an idea directly into live research instead of waiting for a later queue sweep.",
            result_summary="Huddle idea research started.",
            related_label=str((result.get("idea") or {}).get("text") or (result.get("idea") or {}).get("id") or idea_id),
        )
        await _broadcast_dashboard("huddle-ideas.updated")
        return _json({**result, "focus": focus})

    # ------------------------------------------------------------------
    # Scheduler POST routes — must be BEFORE the catch-all
    # ------------------------------------------------------------------

    @app.post("/api/scheduler/fire-event2")
    async def api_scheduler_fire_event2(request: Request) -> JSONResponse:
        scheduler = get_scheduler()
        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler not initialised")
        try:
            body = await request.json()
        except Exception:
            body = {}
        event_type = str(body.get("event_type", "")).strip()
        if not event_type:
            raise HTTPException(status_code=400, detail="event_type is required")
        event_payload = dict(body.get("payload") or {})
        queued = scheduler.fire_event(event_type, event_payload)
        return _json({"event_type": event_type, "agents_queued": queued})

    @app.post("/api/scheduler/run2/{agent_id}")
    async def api_scheduler_force_run2(agent_id: str, request: Request) -> JSONResponse:
        """Force a specific agent to run immediately, bypassing quiet hours."""
        scheduler = get_scheduler()
        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler not initialised")
        item = scheduler.force_run(agent_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
        return _json({"queued": True, "item_id": item.item_id, "agent_id": agent_id})

    # ------------------------------------------------------------------
    # Being Known — memory facts & drift endpoints (Epic 5)
    # ------------------------------------------------------------------

    @app.get("/api/memory/facts")
    async def api_memory_facts(domain: str = "", actor_id: str = "chris") -> JSONResponse:
        try:
            from .known_facts import init_memory
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        store = init_memory()
        if domain:
            facts = await asyncio.to_thread(store.get_domain_facts, domain, actor_id or None)
        else:
            from .known_facts import MEMORY_DOMAINS as _KF_DOMAINS
            facts = []
            for d in _KF_DOMAINS:
                facts.extend(await asyncio.to_thread(store.get_domain_facts, d, actor_id or None))
        return _json([f.to_dict() for f in facts])

    @app.post("/api/memory/facts")
    async def api_memory_facts_create(payload: dict[str, Any]) -> JSONResponse:
        try:
            from .known_facts import init_memory, MemoryFact
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        import uuid as _uuid
        from datetime import datetime as _dt, timezone as _tz
        _now = _dt.now(_tz.utc).isoformat()
        try:
            domain = str(payload["domain"])
            key = str(payload["key"])
            value = str(payload["value"])[:500]
            actor_id = str(payload.get("actor_id", "chris"))
            confidence = float(payload.get("confidence", 1.0))
            source = str(payload.get("source", "user_stated"))
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Missing field: {exc.args[0]}") from exc
        store = init_memory()
        existing = store.get_fact(actor_id, domain, key)
        fact = MemoryFact(
            fact_id=existing.fact_id if existing else str(_uuid.uuid4()),
            domain=domain,
            actor_id=actor_id,
            key=key,
            value=value,
            confidence=confidence,
            source=source,
            created_at=existing.created_at if existing else _now,
            updated_at=_now,
            expires_at=str(payload.get("expires_at", "")),
            tags=list(payload.get("tags", [])),
            last_surfaced_at=existing.last_surfaced_at if existing else "",
            surface_count=existing.surface_count if existing else 0,
            confirmed=bool(payload.get("confirmed", False)),
        )
        await asyncio.to_thread(store.set_fact, fact)
        return _json(fact.to_dict())

    @app.delete("/api/memory/facts/{fact_id}")
    async def api_memory_facts_delete(fact_id: str) -> JSONResponse:
        try:
            from .known_facts import init_memory
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        store = init_memory()
        deleted = await asyncio.to_thread(store.delete_fact, fact_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Fact not found: {fact_id}")
        return _json({"deleted": True, "fact_id": fact_id})

    @app.get("/api/memory/drift")
    async def api_memory_drift(actor_id: str = "chris") -> JSONResponse:
        try:
            from .known_facts import init_memory
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        store = init_memory()
        events = await asyncio.to_thread(store.get_active_drift, actor_id)
        return _json([e.to_dict() for e in events])

    @app.post("/api/memory/drift/{drift_id}/acknowledge")
    async def api_memory_drift_acknowledge(drift_id: str) -> JSONResponse:
        try:
            from .known_facts import init_memory
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        store = init_memory()
        ok = await asyncio.to_thread(store.acknowledge_drift, drift_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Drift event not found: {drift_id}")
        return _json({"acknowledged": True, "drift_id": drift_id})

    @app.post("/api/memory/drift/{drift_id}/resolve")
    async def api_memory_drift_resolve(drift_id: str) -> JSONResponse:
        try:
            from .known_facts import init_memory
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        store = init_memory()
        ok = await asyncio.to_thread(store.resolve_drift, drift_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Drift event not found: {drift_id}")
        return _json({"resolved": True, "drift_id": drift_id})

    @app.get("/api/memory/context")
    async def api_memory_context(actor_id: str = "chris", domains: str = "") -> JSONResponse:
        try:
            from .known_facts import init_memory
        except ImportError:
            raise HTTPException(status_code=503, detail="known_facts module unavailable")
        store = init_memory()
        domain_list = [d.strip() for d in domains.split(",") if d.strip()] or None
        context = await asyncio.to_thread(store.get_relational_context, actor_id, domain_list)
        briefing_ctx = await asyncio.to_thread(store.get_briefing_memory_context)
        return _json({
            "actor_id": actor_id,
            "relational_context": context,
            "briefing_context": briefing_ctx,
        })

    # ------------------------------------------------------------------
    # Scheduler endpoints
    # ------------------------------------------------------------------

    @app.get("/api/scheduler/status")
    async def api_scheduler_status() -> JSONResponse:
        scheduler = get_scheduler()
        if scheduler is None:
            return _json({"running": False, "error": "Scheduler not initialised"})
        return _json(scheduler.get_status())

    @app.post("/api/scheduler/fire-event")
    async def api_scheduler_fire_event(payload: dict[str, Any]) -> JSONResponse:
        scheduler = get_scheduler()
        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler not initialised")
        event_type = str(payload.get("event_type", "")).strip()
        if not event_type:
            raise HTTPException(status_code=400, detail="event_type is required")
        event_payload = dict(payload.get("payload") or {})
        queued = scheduler.fire_event(event_type, event_payload)
        return _json({"event_type": event_type, "agents_queued": queued})

    @app.post("/api/scheduler/run/{agent_id}")
    async def api_scheduler_force_run(agent_id: str, request: Request) -> JSONResponse:
        """Force a specific agent to run immediately, bypassing quiet hours."""
        scheduler = get_scheduler()
        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler not initialised")
        item = scheduler.force_run(agent_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
        return _json({"queued": True, "item_id": item.item_id, "agent_id": agent_id})

    @app.get("/api/briefing/live")
    async def api_briefing_live(actor: str = "chris") -> JSONResponse:
        builder = get_briefing_builder()
        if builder is None:
            raise HTTPException(status_code=503, detail="BriefingBuilder not initialised")
        packet = await asyncio.to_thread(builder.build, actor)
        return _json(packet)

    # ------------------------------------------------------------------
    # Chronicle Bridge endpoints (Epic 9)
    # ------------------------------------------------------------------

    async def _build_chronicle_module_payload() -> dict[str, Any]:
        def _chronicle_entry_id(item: dict[str, Any]) -> str:
            candidate = (
                str(item.get("entry_id") or "").strip()
                or str(item.get("id") or "").strip()
                or str(item.get("timestamp") or "").strip()
            )
            if candidate:
                return candidate
            theme = str(item.get("theme") or item.get("title") or "chronicle-entry").strip().lower().replace(" ", "-")
            actor = str(item.get("actor") or "chris").strip().lower().replace(" ", "-")
            return f"{theme}:{actor}"

        generated_at = ""
        try:
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()
        except Exception:
            generated_at = ""

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Chronicle now has a dedicated module route with live devotional, capture, continuity, and bridge posture.",
            "what_became_real": "Chronicle is now represented as a dedicated app module with visible route-owned continuity instead of a shell-only packet.",
            "remains_partial": "Richer study surfaces and broader external handoff continuity still need follow-on slices.",
            "entry_count": 0,
            "pending_entry_count": 0,
            "timeline": [],
            "theme_summary": {"themes": [], "entries_considered": 0},
            "morning_context": {},
            "workflow_status": {},
            "insights": [],
            "recent_activity": [],
            "review_lane": [],
            "bridge_status": "not_loaded",
            "bridge_note": "Chronicle bridge is not initialised in this runtime.",
            "proof_paths": {
                "module_route": "/chronicle-center",
                "module_api": "/api/chronicle/module",
                "status_api": "/api/chronicle/status",
                "capture_api": "/api/chronicle-capture",
                "devotional_api": "/api/devotional-pause",
                "family_devotional_api": "/api/family-devotional",
                "entry_review_api_suffix": "/api/chronicle/entries/{entry_id}/review",
                "activity_api": "/api/activity/operator-action",
            },
            "counts": {
                "review_count": 0,
            },
            "errors": [],
        }

        try:
            if callable(getattr(runtime, "chronicle_timeline", None)):
                timeline = runtime.chronicle_timeline(limit=10)
                payload["timeline"] = [
                    {
                        **dict(item),
                        "entry_id": _chronicle_entry_id(dict(item)),
                    }
                    for item in (timeline if isinstance(timeline, list) else [])
                    if isinstance(item, dict)
                ]
                payload["entry_count"] = len(payload["timeline"])
            if callable(getattr(runtime, "chronicle_theme_summary", None)):
                theme_summary = runtime.chronicle_theme_summary(limit=25)
                if isinstance(theme_summary, dict):
                    payload["theme_summary"] = theme_summary
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["summary"] = "Chronicle center route is live, but timeline and theme sources did not fully hydrate."
            payload["remains_partial"] = "Live Chronicle continuity sources still need repair or population in this runtime."
            payload["errors"].append(f"chronicle_core: {exc}")

        try:
            bridge = _get_chronicle_bridge()
            if bridge is not None:
                payload["bridge_status"] = "loaded"
                payload["bridge_note"] = "Chronicle bridge is initialised."
                morning_context = await asyncio.to_thread(bridge.get_morning_spiritual_context, "chris")
                payload["morning_context"] = morning_context if isinstance(morning_context, dict) else {}
                insights = await asyncio.to_thread(bridge.get_insights)
                payload["insights"] = [
                    item.to_dict() if hasattr(item, "to_dict") else item
                    for item in list(insights or [])[:8]
                ]
                pending_entries = await asyncio.to_thread(bridge.get_pending_entries)
                payload["pending_entry_count"] = len(list(pending_entries or []))
            else:
                payload["morning_context"] = {}
        except Exception as exc:
            payload["errors"].append(f"chronicle_bridge: {exc}")

        try:
            disciple = _get_disciple()
            if disciple is not None:
                workflow_status = await asyncio.to_thread(disciple.get_workflow_status)
                payload["workflow_status"] = workflow_status if isinstance(workflow_status, dict) else {}
            else:
                payload["workflow_status"] = {}
        except Exception as exc:
            payload["errors"].append(f"chronicle_status: {exc}")

        if payload["status"] == "Useful":
            payload["summary"] = (
                f"Chronicle center loaded {payload['entry_count']} entry(s), "
                f"{len((payload['theme_summary'] or {}).get('themes') or [])} recurring theme(s), and "
                f"{len(payload['insights'])} bridge insight(s)."
            )
            if not payload["timeline"]:
                payload["status"] = "Wired"
                payload["remains_partial"] = "The dedicated Chronicle screen is live, but no Chronicle entries were available in this runtime."

        payload["recent_activity"] = _module_recent_activity(route="/chronicle-center", domain="chronicle")
        review_summary = ChronicleReviewStore().review_summary(actor_id="chris", limit=6)
        payload["review_lane"] = list(review_summary.get("items") or [])
        payload["counts"]["review_count"] = int(review_summary.get("count", 0) or 0)

        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some Chronicle sources still failed to hydrate; inspect the payload preview for details."
        return payload

    def _chronicle_prayer_updates_path() -> Path:
        root = Path("data") / "logs"
        root.mkdir(parents=True, exist_ok=True)
        return root / "chronicle_prayer_updates.json"

    def _load_chronicle_prayer_updates() -> dict[str, dict[str, Any]]:
        path = _chronicle_prayer_updates_path()
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(raw, dict):
            return {}
        return {str(key): value for key, value in raw.items() if isinstance(value, dict)}

    def _write_chronicle_prayer_updates(payload: dict[str, dict[str, Any]]) -> None:
        path = _chronicle_prayer_updates_path()
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _apply_chronicle_prayer_updates(prayer_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        updates = _load_chronicle_prayer_updates()
        patched: list[dict[str, Any]] = []
        for item in prayer_items:
            merged = dict(item)
            update = updates.get(str(item.get("id") or ""))
            if update:
                merged.update(update)
            patched.append(merged)
        return patched

    def _legacy_entry_from_bridge(entry: Any) -> dict[str, Any]:
        if hasattr(entry, "to_dict"):
            data = dict(entry.to_dict())
        elif isinstance(entry, dict):
            data = dict(entry)
        else:
            data = {}
        created_at = str(data.get("created_at") or "")
        return {
            "id": str(data.get("entry_id") or data.get("id") or created_at or ""),
            "entry_id": str(data.get("entry_id") or data.get("id") or created_at or ""),
            "date": created_at[:10] or str(data.get("date") or ""),
            "type": str(data.get("entry_type") or data.get("type") or "note"),
            "title": str(data.get("title") or "Chronicle entry"),
            "body": str(data.get("body") or data.get("note") or data.get("reflection") or ""),
            "passage": str(data.get("scripture_ref") or data.get("passage") or ""),
            "themes": list(data.get("themes") or data.get("tags") or []),
            "autoCapture": False,
            "source": str(data.get("source") or "jarvis"),
            "sent_to_chronicle": bool(data.get("sent_to_chronicle", False)),
            "created_at": created_at or str(data.get("timestamp") or ""),
        }

    def _legacy_entry_from_timeline(item: dict[str, Any]) -> dict[str, Any]:
        timestamp = str(item.get("timestamp") or "")
        body = str(item.get("reflection") or item.get("note") or "")
        theme = str(item.get("theme") or "").strip()
        themes = [theme] if theme else []
        return {
            "id": str(item.get("entry_id") or timestamp),
            "entry_id": str(item.get("entry_id") or timestamp),
            "date": timestamp[:10],
            "type": "reflection",
            "title": theme.title() if theme else "Chronicle reflection",
            "body": body,
            "passage": "",
            "themes": themes,
            "autoCapture": False,
            "source": "chronicle-module",
            "created_at": timestamp,
        }

    def _merge_chronicle_entries(*entry_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for group in entry_groups:
            for raw in group:
                entry = dict(raw)
                key = (
                    str(entry.get("entry_id") or "").strip()
                    or str(entry.get("id") or "").strip()
                    or f"{entry.get('title','')}::{entry.get('body','')}::{entry.get('date','')}"
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(entry)

        def _sort_key(entry: dict[str, Any]) -> tuple[str, str]:
            created = str(entry.get("created_at") or "")
            date = str(entry.get("date") or "")
            return (created or date, date)

        merged.sort(key=_sort_key, reverse=True)
        return merged

    async def _build_chronicle_recent_payload() -> dict[str, Any]:
        _hosted_chronicle_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}

        def _hosted_chronicle_ssh_config() -> dict[str, str]:
            service_plan: dict[str, Any] = {}
            with suppress(Exception):
                identity = runtime.identity_overview() if hasattr(runtime, "identity_overview") else {}
                if isinstance(identity, dict):
                    service_plan = dict(identity.get("service") or {})
            remote_admin_host = str(os.environ.get("JARVIS_REMOTE_ADMIN_HOST") or service_plan.get("remote_admin_host") or "").strip()
            remote_admin_user = str(os.environ.get("JARVIS_REMOTE_ADMIN_USER") or service_plan.get("remote_admin_user") or "root").strip() or "root"
            hosted_base_url = str(os.environ.get("JARVIS_HOSTED_BASE_URL") or service_plan.get("hosted_base_url") or "").strip()
            host_header = re.sub(r"^https?://", "", hosted_base_url).split("/", 1)[0].strip()
            return {
                "remote_admin_host": remote_admin_host,
                "remote_admin_user": remote_admin_user,
                "host_header": host_header,
            }

        def _fetch_hosted_chronicle_json(path: str) -> dict[str, Any] | None:
            now = time.monotonic()
            cached = _hosted_chronicle_cache.get(path)
            if cached and (now - cached[0]) < 20:
                return cached[1]

            ssh_config = _hosted_chronicle_ssh_config()
            remote_admin_host = ssh_config.get("remote_admin_host", "")
            remote_admin_user = ssh_config.get("remote_admin_user", "root")
            host_header = ssh_config.get("host_header", "")
            if not remote_admin_host or not host_header:
                _hosted_chronicle_cache[path] = (now, None)
                return None

            ssh_target = f"{remote_admin_user}@{remote_admin_host}"
            remote_command = (
                "curl -sS --max-time 10 "
                f"-H {shlex.quote(f'Host: {host_header}')} "
                f"{shlex.quote(f'http://127.0.0.1{path}')}"
            )
            try:
                completed = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "BatchMode=yes",
                        "-o",
                        "ConnectTimeout=6",
                        ssh_target,
                        remote_command,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=18,
                    check=False,
                )
            except Exception:
                _hosted_chronicle_cache[path] = (now, None)
                return None
            if completed.returncode != 0 or not completed.stdout.strip():
                _hosted_chronicle_cache[path] = (now, None)
                return None
            try:
                payload = json.loads(completed.stdout)
            except Exception:
                _hosted_chronicle_cache[path] = (now, None)
                return None
            if not isinstance(payload, dict):
                _hosted_chronicle_cache[path] = (now, None)
                return None
            _hosted_chronicle_cache[path] = (now, payload)
            return payload

        remote_recent = await asyncio.to_thread(_fetch_hosted_chronicle_json, "/api/chronicle/recent")
        if isinstance(remote_recent, dict) and remote_recent.get("ok"):
            snapshot_entries = [dict(item) for item in list(remote_recent.get("entries") or []) if isinstance(item, dict)]
            prayer_items = _apply_chronicle_prayer_updates(
                [dict(item) for item in list(remote_recent.get("prayer_items") or []) if isinstance(item, dict)]
            )
            rhythms = [dict(item) for item in list(remote_recent.get("formation_rhythms") or []) if isinstance(item, dict)]
            books = [dict(item) for item in list(remote_recent.get("owned_books") or []) if isinstance(item, dict)]

            pending_entries: list[dict[str, Any]] = []
            bridge = _get_chronicle_bridge()
            if bridge is not None:
                try:
                    pending = await asyncio.to_thread(bridge.get_pending_entries)
                    pending_entries = [_legacy_entry_from_bridge(item) for item in list(pending or [])]
                except Exception:
                    pending_entries = []

            entries = _merge_chronicle_entries(pending_entries, snapshot_entries, [])
            tags = [str(theme).strip() for theme in list(remote_recent.get("tags") or []) if str(theme).strip()]
            if not tags:
                theme_counts: dict[str, int] = {}
                for entry in entries:
                    for theme in list(entry.get("themes") or []):
                        name = str(theme).strip()
                        if not name:
                            continue
                        theme_counts[name] = theme_counts.get(name, 0) + 1
                tags = [theme for theme, _count in sorted(theme_counts.items(), key=lambda item: (-item[1], item[0]))]

            active_prayers = int(remote_recent.get("active_prayers") or sum(1 for item in prayer_items if not item.get("answered")))
            answered_prayers = int(remote_recent.get("answered_prayers") or sum(1 for item in prayer_items if item.get("answered")))

            return {
                "ok": True,
                "entries": entries,
                "total": len(entries),
                "tags": tags,
                "prayer_items": prayer_items,
                "active_prayers": active_prayers,
                "answered_prayers": answered_prayers,
                "formation_rhythms": rhythms,
                "owned_books": books,
                "chronicle_available": True,
                "remote_source": "hetzner-hosted-chronicle",
            }

        from .chronicle_bridge import ChronicleSnapshotReader

        reader = ChronicleSnapshotReader()
        dashboard = await asyncio.to_thread(reader.get_dashboard)
        if not isinstance(dashboard, dict) or not dashboard.get("ok"):
            dashboard = {
                "ok": True,
                "entries": [],
                "total": 0,
                "tags": [],
                "prayer_items": [],
                "active_prayers": 0,
                "answered_prayers": 0,
                "formation_rhythms": [],
                "owned_books": [],
                "chronicle_available": False,
            }

        snapshot_entries = [dict(item) for item in list(dashboard.get("entries") or []) if isinstance(item, dict)]
        prayer_items = _apply_chronicle_prayer_updates([dict(item) for item in list(dashboard.get("prayer_items") or []) if isinstance(item, dict)])
        rhythms = [dict(item) for item in list(dashboard.get("formation_rhythms") or []) if isinstance(item, dict)]
        books = [dict(item) for item in list(dashboard.get("owned_books") or []) if isinstance(item, dict)]

        pending_entries: list[dict[str, Any]] = []
        bridge = _get_chronicle_bridge()
        if bridge is not None:
            try:
                pending = await asyncio.to_thread(bridge.get_pending_entries)
                pending_entries = [_legacy_entry_from_bridge(item) for item in list(pending or [])]
            except Exception:
                pending_entries = []

        module_payload = await _build_chronicle_module_payload()
        timeline_entries = [_legacy_entry_from_timeline(item) for item in list(module_payload.get("timeline") or []) if isinstance(item, dict)]
        entries = _merge_chronicle_entries(pending_entries, snapshot_entries, timeline_entries)

        theme_counts: dict[str, int] = {}
        for entry in entries:
            for theme in list(entry.get("themes") or []):
                name = str(theme).strip()
                if not name:
                    continue
                theme_counts[name] = theme_counts.get(name, 0) + 1
        tags = [theme for theme, _count in sorted(theme_counts.items(), key=lambda item: (-item[1], item[0]))]

        active_prayers = sum(1 for item in prayer_items if not item.get("answered"))
        answered_prayers = sum(1 for item in prayer_items if item.get("answered"))

        return {
            "ok": True,
            "entries": entries,
            "total": len(entries),
            "tags": tags,
            "prayer_items": prayer_items,
            "active_prayers": active_prayers,
            "answered_prayers": answered_prayers,
            "formation_rhythms": rhythms,
            "owned_books": books,
            "chronicle_available": bool(dashboard.get("chronicle_available") or module_payload.get("available")),
        }

    def _chronicle_context_from_recent(payload: dict[str, Any]) -> dict[str, Any]:
        entries = [dict(item) for item in list(payload.get("entries") or []) if isinstance(item, dict)]
        prayers = [dict(item) for item in list(payload.get("prayer_items") or []) if isinstance(item, dict)]
        rhythms = [dict(item) for item in list(payload.get("formation_rhythms") or []) if isinstance(item, dict)]

        study_entry = next((entry for entry in entries if entry.get("passage")), None)
        active_prayers = [item for item in prayers if not item.get("answered")][:3]
        today = __import__("datetime").datetime.now().strftime("%A").lower()
        todays_rhythm = None
        for rhythm in rhythms:
            days = [str(day).lower() for day in list(rhythm.get("days") or [])]
            if today in days or "daily" in days:
                todays_rhythm = rhythm
                break
        if not todays_rhythm and rhythms:
            todays_rhythm = rhythms[0]

        return {
            "ok": True,
            "study": {
                "passage": study_entry.get("passage"),
                "title": study_entry.get("title"),
                "date": study_entry.get("date"),
            } if study_entry else None,
            "active_prayers": [
                {
                    "id": item.get("id"),
                    "text": item.get("text"),
                    "category": item.get("category"),
                }
                for item in active_prayers
            ],
            "todays_rhythm": {
                "name": todays_rhythm.get("title") or todays_rhythm.get("name"),
                "description": todays_rhythm.get("focus") or todays_rhythm.get("description", ""),
            } if todays_rhythm else None,
            "top_themes": list(payload.get("tags") or [])[:5],
            "total_entries": int(payload.get("total") or 0),
            "active_prayer_count": sum(1 for item in prayers if not item.get("answered")),
            "answered_prayer_count": sum(1 for item in prayers if item.get("answered")),
        }

    def _chronicle_patterns_from_recent(payload: dict[str, Any]) -> dict[str, Any]:
        from collections import Counter
        from datetime import datetime, timedelta

        entries = [dict(item) for item in list(payload.get("entries") or []) if isinstance(item, dict)]
        prayers = [dict(item) for item in list(payload.get("prayer_items") or []) if isinstance(item, dict)]
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        recent_entries = [item for item in entries if str(item.get("date") or "") >= cutoff]
        type_counts = Counter(str(item.get("type") or "note") for item in recent_entries)
        theme_counts = Counter(
            str(theme).strip()
            for item in recent_entries
            for theme in list(item.get("themes") or [])
            if str(theme).strip()
        )
        answered = [item for item in prayers if item.get("answered")]
        dates = sorted({str(item.get("date") or "") for item in entries if str(item.get("date") or "")}, reverse=True)
        streak = 0
        if dates:
            check = datetime.now()
            for date_value in dates:
                if date_value in {
                    check.strftime("%Y-%m-%d"),
                    (check - timedelta(days=1)).strftime("%Y-%m-%d"),
                }:
                    streak += 1
                    check = datetime.strptime(date_value, "%Y-%m-%d") - timedelta(days=1)
                else:
                    break
        return {
            "ok": True,
            "window_days": 30,
            "total_recent_entries": len(recent_entries),
            "entry_type_breakdown": dict(type_counts),
            "recurring_themes": [
                {"theme": theme, "count": count}
                for theme, count in theme_counts.most_common(8)
            ],
            "prayer_arc": {
                "total_active": sum(1 for item in prayers if not item.get("answered")),
                "answered_total": len(answered),
                "answered_recent": len([item for item in answered if str(item.get("dateAnswered") or "") >= cutoff]),
            },
            "writing_streak_days": streak,
        }

    async def _build_faith_daily_word_payload() -> dict[str, Any]:
        try:
            from .faith_agents import daily_word as _faith_daily_word

            result = await _faith_daily_word(runtime)
            if isinstance(result, dict) and result.get("ok"):
                return {
                    "ok": True,
                    "available": True,
                    "agent_id": str(result.get("agent_id") or ""),
                    "agent_name": str(result.get("agent_name") or result.get("agent") or "JARVIS"),
                    "agent_title": str(result.get("agent_title") or ""),
                    "color": str(result.get("color") or ""),
                    "domain": str(result.get("domain") or ""),
                    "passage": str(result.get("passage") or ""),
                    "word": str(result.get("word") or ""),
                    "generated_at": str(result.get("generated_at") or ""),
                }
            message = str(result.get("error") or "Daily word unavailable") if isinstance(result, dict) else "Daily word unavailable"
            return {
                "ok": False,
                "available": False,
                "agent_id": "",
                "agent_name": "JARVIS",
                "agent_title": "",
                "color": "",
                "domain": "",
                "passage": "",
                "word": "",
                "generated_at": "",
                "message": message,
            }
        except Exception as exc:
            return {
                "ok": False,
                "available": False,
                "agent_id": "",
                "agent_name": "JARVIS",
                "agent_title": "",
                "color": "",
                "domain": "",
                "passage": "",
                "word": "",
                "generated_at": "",
                "message": str(exc),
            }

    async def _build_faith_agents_payload() -> dict[str, Any]:
        try:
            from .faith_agents import get_agents as _faith_get_agents

            agents = await asyncio.to_thread(_faith_get_agents)
            if not isinstance(agents, list):
                agents = []
            return {"ok": True, "agents": [dict(item) for item in agents if isinstance(item, dict)]}
        except Exception as exc:
            return {"ok": False, "agents": [], "message": str(exc)}

    def _build_faith_continuity_payload(
        *,
        daily_word: dict[str, Any],
        chronicle_context: dict[str, Any],
        chronicle_patterns: dict[str, Any],
        agents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        top_themes = [str(theme).strip() for theme in list(chronicle_context.get("top_themes") or []) if str(theme).strip()]
        recurring = [
            str(item.get("theme") or "").strip()
            for item in list(chronicle_patterns.get("recurring_themes") or [])
            if isinstance(item, dict) and str(item.get("theme") or "").strip()
        ]
        theme = top_themes[0] if top_themes else (recurring[0] if recurring else str(daily_word.get("domain") or "").strip())
        study = chronicle_context.get("study")
        study_passage = study.get("passage") if isinstance(study, dict) else ""
        passage = str(daily_word.get("passage") or study_passage or "").strip()
        focus = ""
        if chronicle_context.get("active_prayers"):
            focus = str(chronicle_context["active_prayers"][0].get("text") or "").strip()
        if not focus:
            focus = str(daily_word.get("word") or "").strip()
        if focus:
            focus = " ".join(focus.split())[:220]
        guidance_lines: list[str] = []
        if daily_word.get("word"):
            guidance_lines.append(" ".join(str(daily_word.get("word") or "").split())[:220])
        todays_rhythm = chronicle_context.get("todays_rhythm")
        if isinstance(todays_rhythm, dict) and todays_rhythm.get("description"):
            guidance_lines.append(str(todays_rhythm["description"]).strip())
        if theme:
            guidance_lines.append(f"Keep listening for {theme} instead of forcing resolution too early.")
        guidance_lines = [line for line in guidance_lines if line]
        return {
            "subject_display_name": "Chris",
            "theme": theme,
            "focus": focus,
            "passage": passage,
            "council_domains": [str(agent.get("domain") or "").strip() for agent in agents if str(agent.get("domain") or "").strip()][:6],
            "guidance_lines": guidance_lines[:3],
        }

    async def _build_faith_module_payload() -> dict[str, Any]:
        daily_word_payload, agents_payload, chronicle_recent = await asyncio.gather(
            _build_faith_daily_word_payload(),
            _build_faith_agents_payload(),
            _build_chronicle_recent_payload(),
        )
        remote_morning_context: dict[str, Any] | None = None
        bridge = _get_chronicle_bridge()
        if bridge is not None:
            with suppress(Exception):
                remote_morning_context = await asyncio.to_thread(bridge.get_morning_spiritual_context, "chris")
        with suppress(Exception):
            identity = runtime.identity_overview() if hasattr(runtime, "identity_overview") else {}
            service_plan = dict(identity.get("service") or {}) if isinstance(identity, dict) else {}
            remote_admin_host = str(os.environ.get("JARVIS_REMOTE_ADMIN_HOST") or service_plan.get("remote_admin_host") or "").strip()
            remote_admin_user = str(os.environ.get("JARVIS_REMOTE_ADMIN_USER") or service_plan.get("remote_admin_user") or "root").strip() or "root"
            hosted_base_url = str(os.environ.get("JARVIS_HOSTED_BASE_URL") or service_plan.get("hosted_base_url") or "").strip()
            host_header = re.sub(r"^https?://", "", hosted_base_url).split("/", 1)[0].strip()
            if remote_morning_context is None and remote_admin_host and host_header:
                ssh_target = f"{remote_admin_user}@{remote_admin_host}"
                remote_command = (
                    "curl -sS --max-time 10 "
                    f"-H {shlex.quote(f'Host: {host_header}')} "
                    f"{shlex.quote('http://127.0.0.1/api/chronicle/morning-context')}"
                )
                completed = await asyncio.to_thread(
                    subprocess.run,
                    [
                        "ssh",
                        "-o",
                        "BatchMode=yes",
                        "-o",
                        "ConnectTimeout=6",
                        ssh_target,
                        remote_command,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=18,
                    check=False,
                )
                if completed.returncode == 0 and completed.stdout.strip():
                    parsed = json.loads(completed.stdout)
                    if isinstance(parsed, dict):
                        remote_morning_context = parsed
        chronicle_context = _chronicle_context_from_recent(chronicle_recent)
        chronicle_patterns = _chronicle_patterns_from_recent(chronicle_recent)
        if isinstance(remote_morning_context, dict):
            scripture = dict(remote_morning_context.get("scripture_of_day") or {})
            reflection_prompt = str(remote_morning_context.get("reflection_prompt") or "").strip()
            if not chronicle_context.get("study") and str(scripture.get("ref") or "").strip():
                chronicle_context["study"] = {
                    "passage": str(scripture.get("ref") or "").strip(),
                    "title": "Scripture of the day",
                    "date": "",
                }
            if (daily_word_payload.get("available") is False or not str(daily_word_payload.get("passage") or "").strip()) and str(scripture.get("ref") or "").strip():
                daily_word_payload["available"] = True
                daily_word_payload["agent_name"] = str(daily_word_payload.get("agent_name") or "Chronicle")
                daily_word_payload["agent_title"] = str(daily_word_payload.get("agent_title") or "Hosted Chronicle")
                daily_word_payload["domain"] = str(daily_word_payload.get("domain") or "Morning Reflection")
                daily_word_payload["passage"] = str(scripture.get("ref") or "").strip()
                if reflection_prompt:
                    daily_word_payload["word"] = reflection_prompt
                elif str(scripture.get("text") or "").strip():
                    daily_word_payload["word"] = str(scripture.get("text") or "").strip()
        try:
            capabilities = getattr(runtime, "interface_router").system_manifest("chronicle").get("capabilities", {})
        except Exception:
            capabilities = {}
        health_summary = {}
        availability_notes: list[str] = []

        try:
            health_summary = runtime.apple_health_daily_summary() or {}
        except Exception as exc:
            health_summary = {"available": False, "detail": str(exc)}
            availability_notes.append("Health summary is unavailable in this runtime.")

        if daily_word_payload.get("available") is False:
            availability_notes.append(str(daily_word_payload.get("message") or "Daily word unavailable"))
        if not chronicle_context.get("study"):
            availability_notes.append("Chronicle has not surfaced a study passage yet.")
        if not chronicle_recent.get("chronicle_available"):
            availability_notes.append("Chronicle bridge is not fully available.")
        if not capabilities:
            availability_notes.append("Chronicle handoff capabilities are unavailable.")

        agents = list(agents_payload.get("agents") or [])
        continuity = _build_faith_continuity_payload(
            daily_word=daily_word_payload,
            chronicle_context=chronicle_context,
            chronicle_patterns=chronicle_patterns,
            agents=agents,
        )
        prayer_items = list(chronicle_recent.get("prayer_items") or [])
        recent_entries = list(chronicle_recent.get("entries") or [])[:10]
        runtime_note = availability_notes[0] if availability_notes else "Faith is live and connected."
        return {
            "ok": True,
            "available": True,
            "status": "Useful",
            "summary": (
                f"Faith loaded {len(agents)} faith guide(s), {len(prayer_items)} prayer item(s), "
                f"and {len(recent_entries)} recent Chronicle entry row(s)."
            ),
            "runtime_note": runtime_note,
            "what_became_real": "Faith now hydrates from live daily-word, Chronicle context, prayer continuity, hosted Chronicle bridge context, and capability handoff state.",
            "remains_partial": "Health-linked faith readiness and deeper Chronicle study surfaces remain partially dependent on optional integrations in this runtime.",
            "daily_word": daily_word_payload,
            "agents": agents,
            "chronicle_context": chronicle_context,
            "chronicle_patterns": chronicle_patterns,
            "prayer_items": prayer_items,
            "recent_entries": recent_entries,
            "chronicle_capabilities": capabilities,
            "formation_prompts": [
                prompt
                for prompt in [
                    continuity.get("passage") and f"Ask the council what {continuity['passage']} is saying about today.",
                    continuity.get("focus") and f"Pray into this concern: {continuity['focus']}",
                    continuity.get("theme") and f"Notice where {continuity['theme']} keeps surfacing in the day.",
                ]
                if prompt
            ],
            "continuity": continuity,
            "health_summary": health_summary,
            "availability_notes": availability_notes,
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    def _chronicle_bridge_entry_from_legacy_payload(entry_payload: dict[str, Any]) -> Any:
        from .chronicle_bridge import ChronicleEntry
        from .chronicle_bridge import _now_iso as _chronicle_now_iso
        import uuid

        entry_type = str(entry_payload.get("type") or entry_payload.get("entry_type") or "note").strip().lower() or "note"
        body = str(entry_payload.get("body") or entry_payload.get("note") or "").strip()
        title = str(entry_payload.get("title") or "").strip() or f"{entry_type.title()} entry"
        passage = str(entry_payload.get("passage") or entry_payload.get("scripture_ref") or "").strip()
        created_at = str(entry_payload.get("created_at") or "") or _chronicle_now_iso()
        themes = [str(theme).strip() for theme in list(entry_payload.get("themes") or []) if str(theme).strip()]
        if not themes and entry_type == "gratitude":
            themes = ["gratitude"]
        if not themes and entry_type == "prayer":
            themes = ["faith"]
        tags = [str(tag).strip() for tag in list(entry_payload.get("tags") or []) if str(tag).strip()]
        if not tags:
            tags = [entry_type] + themes[:3]
        return ChronicleEntry(
            entry_id=str(entry_payload.get("entry_id") or entry_payload.get("id") or uuid.uuid4()),
            entry_type=entry_type,
            title=title,
            body=body,
            scripture_ref=passage,
            scripture_text=str(entry_payload.get("scripture_text") or ""),
            themes=themes,
            actor_id=str(entry_payload.get("actor_id") or "chris"),
            created_at=created_at,
            source=str(entry_payload.get("source") or "user_initiated"),
            mood=str(entry_payload.get("mood") or ("grateful" if entry_type == "gratitude" else "hopeful")),
            linked_events=list(entry_payload.get("linked_events") or []),
            tags=tags,
            sent_to_chronicle=False,
            sent_at="",
        )

    @app.get("/api/chronicle/recent")
    async def api_chronicle_recent() -> JSONResponse:
        return _json(await _build_chronicle_recent_payload())

    @app.get("/api/chronicle/context")
    async def api_chronicle_context() -> JSONResponse:
        payload = await _build_chronicle_recent_payload()
        context = _chronicle_context_from_recent(payload)
        bridge = _get_chronicle_bridge()
        if bridge is not None:
            try:
                morning = await asyncio.to_thread(bridge.get_morning_spiritual_context, "chris")
                if isinstance(morning, dict):
                    if not context.get("study") and isinstance(morning.get("scripture_of_day"), dict):
                        context["study"] = {
                            "passage": str(morning["scripture_of_day"].get("ref") or ""),
                            "title": "Scripture of the day",
                            "date": "",
                        }
                    if not context.get("active_prayers"):
                        context["active_prayers"] = [
                            {"id": "", "text": text, "category": "needs"}
                            for text in list(morning.get("answered_recently") or [])
                            if str(text).strip()
                        ][:3]
            except Exception:
                pass
        return _json(context)

    @app.get("/api/chronicle/patterns")
    async def api_chronicle_patterns() -> JSONResponse:
        payload = await _build_chronicle_recent_payload()
        return _json(_chronicle_patterns_from_recent(payload))

    @app.get("/api/chronicle/search")
    async def api_chronicle_search(q: str = Query("", alias="q")) -> JSONResponse:
        payload = await _build_chronicle_recent_payload()
        query = str(q or "").strip().lower()
        if not query:
            return _json(payload)
        filtered_entries = []
        for item in list(payload.get("entries") or []):
            haystack = " ".join(
                [
                    str(item.get("title") or ""),
                    str(item.get("body") or ""),
                    str(item.get("passage") or ""),
                    " ".join(str(theme) for theme in list(item.get("themes") or [])),
                ]
            ).lower()
            if query in haystack:
                filtered_entries.append(item)
        result = dict(payload)
        result["entries"] = filtered_entries
        result["total"] = len(filtered_entries)
        return _json(result)

    @app.post("/api/chronicle/quick-capture")
    async def api_chronicle_quick_capture(payload: dict[str, Any]) -> JSONResponse:
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        entry_type = str(payload.get("type") or "note").strip().lower() or "note"
        content = str(payload.get("content") or "").strip()
        passage = str(payload.get("passage") or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Capture content is required")

        if entry_type == "gratitude":
            entry = await asyncio.to_thread(bridge.capture_gratitude, content, {"actor_id": "chris"})
            if entry is None:
                entry = _chronicle_bridge_entry_from_legacy_payload({
                    "entry_type": "gratitude",
                    "title": f"Gratitude — {content[:40].strip().rstrip('.,!?')}",
                    "body": content,
                    "passage": passage,
                    "themes": ["gratitude"],
                })
                await asyncio.to_thread(bridge.save_entry_local, entry)
        elif entry_type == "prayer":
            entry = await asyncio.to_thread(bridge.package_prayer_request, content, "chris")
        elif entry_type == "milestone":
            title = f"Milestone — {content[:40].strip().rstrip('.,!?')}" if content else "Milestone"
            entry = await asyncio.to_thread(bridge.record_milestone, title, content, "life")
        else:
            entry = _chronicle_bridge_entry_from_legacy_payload({
                "entry_type": entry_type,
                "title": f"{entry_type.title()} — {content[:40].strip().rstrip('.,!?')}" if content else entry_type.title(),
                "body": content,
                "passage": passage,
                "themes": [entry_type] if entry_type in {"insight", "reflection", "study"} else [],
            })
            await asyncio.to_thread(bridge.save_entry_local, entry)

        AuditLog(Path("data/logs")).log_event(
            "operator-action",
            {
                "actor": "Chris",
                "domain": "chronicle",
                "action": f"Captured {entry_type}",
                "title": getattr(entry, "title", None) or (entry.get("title") if isinstance(entry, dict) else "Legacy capture"),
                "detail": content[:220],
                "why_now": "Legacy capture turned a real moment into a Chronicle-ready entry from the desktop module.",
                "result_summary": "Legacy queued a Chronicle entry for review or handoff.",
                "related_route": "/chronicle-center",
                "route_label": "Open Chronicle",
                "related_kind": "chronicle-entry",
                "related_label": getattr(entry, "title", None) or (entry.get("title") if isinstance(entry, dict) else "Legacy capture"),
                "source_kind": "operator-action",
                "succeeded": True,
            },
        )
        response_entry = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
        return _json({"ok": True, "entry": response_entry})

    @app.post("/api/chronicle/write-entry")
    async def api_chronicle_write_entry(payload: dict[str, Any]) -> JSONResponse:
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        raw_entry = payload.get("entry")
        if not isinstance(raw_entry, dict):
            raise HTTPException(status_code=400, detail="Entry payload is required")
        entry = _chronicle_bridge_entry_from_legacy_payload(raw_entry)
        await asyncio.to_thread(bridge.save_entry_local, entry)
        AuditLog(Path("data/logs")).log_event(
            "operator-action",
            {
                "actor": "Chris",
                "domain": "chronicle",
                "action": "Saved Legacy entry",
                "title": entry.title,
                "detail": entry.body[:220],
                "why_now": "Legacy promoted a visible desktop memory into the Chronicle pending lane.",
                "result_summary": "The entry is now queued in Chronicle bridge storage.",
                "related_route": "/chronicle-center",
                "route_label": "Open Chronicle",
                "related_kind": "chronicle-entry",
                "related_label": entry.title,
                "source_kind": "operator-action",
                "succeeded": True,
            },
        )
        return _json({"ok": True, "entry": entry.to_dict()})

    @app.post("/api/chronicle/update-prayer")
    async def api_chronicle_update_prayer(payload: dict[str, Any]) -> JSONResponse:
        prayer_id = str(payload.get("id") or "").strip()
        if not prayer_id:
            raise HTTPException(status_code=400, detail="Prayer id is required")
        updates = _load_chronicle_prayer_updates()
        current = dict(updates.get(prayer_id) or {})
        if "timesPrayed" in payload:
            current["timesPrayed"] = int(payload.get("timesPrayed") or 0)
        if "lastPrayedAt" in payload:
            current["lastPrayedAt"] = str(payload.get("lastPrayedAt") or "")
        if "answered" in payload:
            current["answered"] = bool(payload.get("answered"))
        if "dateAnswered" in payload:
            current["dateAnswered"] = str(payload.get("dateAnswered") or "")
        if "answerSummary" in payload:
            current["answerSummary"] = str(payload.get("answerSummary") or "")
        updates[prayer_id] = current
        _write_chronicle_prayer_updates(updates)

        bridge = _get_chronicle_bridge()
        if bridge is not None and current.get("answered"):
            try:
                await asyncio.to_thread(
                    bridge.receive_answered_prayer,
                    {
                        "entry_id": prayer_id,
                        "title": str(payload.get("title") or prayer_id),
                        "answerSummary": current.get("answerSummary") or "Marked answered from Legacy.",
                    },
                )
            except Exception:
                pass

        return _json({"ok": True, "prayer": {"id": prayer_id, **current}})

    @app.get("/api/chronicle/entries/pending")
    async def api_chronicle_pending_entries() -> JSONResponse:
        """Return Chronicle entries waiting to be pushed to Chronicle."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        entries = await asyncio.to_thread(bridge.get_pending_entries)
        return _json({"entries": [e.to_dict() for e in entries], "count": len(entries)})

    @app.get("/api/chronicle/module")
    async def api_chronicle_module() -> JSONResponse:
        return _json(await _build_chronicle_module_payload())

    @app.get("/api/legacy/module")
    async def api_legacy_module_alias() -> JSONResponse:
        return _json(await _build_chronicle_module_payload())

    @app.post("/api/chronicle/entries/{entry_id}/review")
    async def api_chronicle_review_entry(entry_id: str, payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor") or "Chris").strip() or "Chris"
        status = str(payload.get("status") or "").strip().lower()
        note = str(payload.get("note") or "").strip()
        title = str(payload.get("title") or "Chronicle entry").strip() or "Chronicle entry"
        entry_type = str(payload.get("entry_type") or "reflection").strip() or "reflection"

        try:
            review = ChronicleReviewStore().review_entry(
                entry_id=entry_id,
                actor_id=actor,
                title=title,
                entry_type=entry_type,
                status=status,
                note=note,
                route="/chronicle-center",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        focus = ProgressFocusStore(Path("data/logs")).save_focus(
            module="Chronicle",
            reason=f"Chronicle review moved '{title}' into {review['review_status_label'].lower()}.",
            route="/chronicle-center",
            actor=actor,
        )
        AuditLog(Path("data/logs")).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "chronicle",
                "action": review["review_status_label"],
                "title": title,
                "detail": note or f"Chronicle review updated to {review['review_status_label'].lower()}.",
                "why_now": "Chronicle promoted a real entry into study, family handoff, or resolution continuity from the dedicated route.",
                "result_summary": f"Chronicle entry is now marked {review['review_status_label'].lower()}.",
                "related_route": "/chronicle-center",
                "route_label": "Open Chronicle",
                "related_kind": "chronicle-review",
                "related_label": title,
                "source_kind": "operator-action",
                "succeeded": True,
            },
        )
        return _json({"status": "recorded", "review": review, "focus": focus})

    @app.post("/api/chronicle/entries/{entry_id}/sent")
    async def api_chronicle_mark_sent(entry_id: str) -> JSONResponse:
        """Mark a Chronicle entry as successfully sent to Chronicle."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        await asyncio.to_thread(bridge.mark_entry_sent, entry_id)
        return _json({"entry_id": entry_id, "sent": True})

    @app.post("/api/chronicle/receive/formation-memory")
    async def api_chronicle_receive_formation(request: Request) -> JSONResponse:
        """Chronicle → JARVIS: receive formation context (study, prayer focus)."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        memory_data = await request.json()
        await asyncio.to_thread(bridge.receive_formation_memory, memory_data)
        return _json({"ok": True, "keys_received": list(memory_data.keys())})

    @app.post("/api/chronicle/receive/answered-prayer")
    async def api_chronicle_receive_answered_prayer(request: Request) -> JSONResponse:
        """Chronicle → JARVIS: notify that a prayer was answered."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        prayer_data = await request.json()
        await asyncio.to_thread(bridge.receive_answered_prayer, prayer_data)
        return _json({"ok": True})

    @app.get("/api/chronicle/morning-context")
    async def api_chronicle_morning_context(actor: str = "chris") -> JSONResponse:
        """Spiritual context packet for the morning briefing."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        ctx = await asyncio.to_thread(bridge.get_morning_spiritual_context, actor)
        return _json(ctx)

    @app.post("/api/chronicle/capture/gratitude")
    async def api_chronicle_capture_gratitude(request: Request) -> JSONResponse:
        """Detect and capture gratitude from conversation text."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        body = await request.json()
        text = str(body.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        entry = await asyncio.to_thread(bridge.capture_gratitude, text)
        if entry is None:
            return _json({"captured": False, "reason": "No gratitude pattern detected"})
        return _json({"captured": True, "entry": entry.to_dict()})

    @app.post("/api/chronicle/capture/prayer")
    async def api_chronicle_capture_prayer(request: Request) -> JSONResponse:
        """Package a prayer request for Chronicle."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        body = await request.json()
        concern = str(body.get("concern", "")).strip()
        actor_id = str(body.get("actor_id", "chris"))
        if not concern:
            raise HTTPException(status_code=400, detail="concern is required")
        entry = await asyncio.to_thread(bridge.package_prayer_request, concern, actor_id)
        return _json({"entry": entry.to_dict()})

    @app.post("/api/chronicle/daily-reflection")
    async def api_chronicle_daily_reflection(request: Request) -> JSONResponse:
        """Trigger One Above All to prepare the daily reflection prompt."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        body = {}
        with suppress(Exception):
            body = await request.json()
        actor_id = str(body.get("actor_id", "chris"))
        context = body.get("context") or {}
        entry = await asyncio.to_thread(bridge.prepare_daily_reflection, actor_id, context)
        return _json({"entry": entry.to_dict()})

    @app.get("/api/chronicle/status")
    async def api_chronicle_status() -> JSONResponse:
        """Disciple (chronicle-curator) workflow status."""
        disciple = _get_disciple()
        if disciple is None:
            raise HTTPException(status_code=503, detail="DiscipleWorkflow not initialised")
        status = await asyncio.to_thread(disciple.get_workflow_status)
        return _json(status)

    @app.get("/api/chronicle/insights")
    async def api_chronicle_insights() -> JSONResponse:
        """Return all spiritual pattern insights detected by Disciple."""
        bridge = _get_chronicle_bridge()
        if bridge is None:
            raise HTTPException(status_code=503, detail="ChronicleBridge not initialised")
        insights = await asyncio.to_thread(bridge.get_insights)
        return _json({
            "insights": [i.to_dict() for i in insights],
            "count": len(insights),
        })

    # -----------------------------------------------------------------------
    # Epic 10: Family Profiles & Household Modes
    # -----------------------------------------------------------------------

    @app.get("/api/family/profiles")
    async def api_family_profiles(actor: str = "chris") -> JSONResponse:
        """
        Return all family member profiles.
        Non-admin actors receive redacted profiles (own profile full, others minimal).
        """
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")

        actor_id = str(actor).strip().lower()
        actor_profile = manager.get_profile(actor_id)
        is_admin = actor_profile is not None and actor_profile.permission_level == "admin"

        profiles = manager.list_profiles()
        result: dict[str, Any] = {}
        for uid, profile in profiles.items():
            if is_admin or uid == actor_id:
                from dataclasses import asdict as _asdict
                result[uid] = _asdict(profile)
            else:
                # Redacted view for non-admin
                result[uid] = {
                    "user_id": profile.user_id,
                    "display_name": profile.display_name,
                    "role": profile.role,
                    "primary_agent": profile.primary_agent,
                }
        return _json({"profiles": result, "count": len(result)})

    @app.get("/api/family/profiles/{user_id}")
    async def api_family_profile_detail(user_id: str, actor: str = "chris") -> JSONResponse:
        """Return a specific family member profile."""
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")

        target = str(user_id).strip().lower()
        profile = manager.get_profile(target)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {user_id}")

        actor_id = str(actor).strip().lower()
        actor_profile = manager.get_profile(actor_id)
        is_admin = actor_profile is not None and actor_profile.permission_level == "admin"

        if is_admin or actor_id == target:
            from dataclasses import asdict as _asdict
            return _json(_asdict(profile))

        # Non-admin can only see own profile in full
        raise HTTPException(status_code=403, detail="Insufficient permissions to view this profile")

    @app.get("/api/household/mode")
    async def api_household_mode_status() -> JSONResponse:
        """Return current household mode and status."""
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")
        return _json(await asyncio.to_thread(manager.get_status))

    @app.post("/api/household/mode")
    async def api_household_mode_set(request: Request) -> JSONResponse:
        """Set the household mode. Body: {"mode_id": str, "actor": str}."""
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")
        body = await request.json()
        mode_id = str(body.get("mode_id", "")).strip()
        actor_id = str(body.get("actor", "chris")).strip().lower()
        if not mode_id:
            raise HTTPException(status_code=400, detail="mode_id is required")

        # Only admin or adult can set household mode
        profile = manager.get_profile(actor_id)
        if profile is None or profile.permission_level not in ("admin", "adult"):
            raise HTTPException(status_code=403, detail="Insufficient permissions to set household mode")

        ok = await asyncio.to_thread(manager.set_mode, mode_id, actor_id)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Unknown mode_id: {mode_id}")
        return _json({"ok": True, "mode_id": mode_id, **await asyncio.to_thread(manager.get_status)})

    @app.get("/api/household/modes")
    async def api_household_modes_list() -> JSONResponse:
        """Return all available household modes."""
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")
        modes = manager.list_modes()
        from dataclasses import asdict as _asdict
        return _json({
            "modes": {k: _asdict(v) for k, v in modes.items()},
            "count": len(modes),
            "current": manager._current_mode,
        })

    @app.get("/api/family/response-rules")
    async def api_family_response_rules(user_id: str = "chris") -> JSONResponse:
        """Return response rules for a user in the current household mode."""
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")
        rules = await asyncio.to_thread(manager.get_response_rules, user_id)
        return _json({"user_id": user_id, "rules": rules})

    @app.post("/api/household/mode/auto")
    async def api_household_mode_auto() -> JSONResponse:
        """Trigger an auto-advance check. Returns new mode if changed, or current mode."""
        manager = _get_family_manager()
        if manager is None:
            raise HTTPException(status_code=503, detail="FamilyModeManager not initialised")
        new_mode = await asyncio.to_thread(manager.auto_advance_mode)
        status = await asyncio.to_thread(manager.get_status)
        return _json({"mode_changed": new_mode is not None, "new_mode": new_mode, **status})

    @app.get("/api/rebekah/briefing")
    async def api_rebekah_briefing() -> JSONResponse:
        """Return Rebekah's household coordination briefing."""
        mockingbird = _get_mockingbird()
        if mockingbird is None:
            raise HTTPException(status_code=503, detail="MockingbirdWorkflow not initialised")
        briefing = await asyncio.to_thread(mockingbird.get_rebekah_briefing)
        return _json(briefing)

    # -----------------------------------------------------------------------
    # Epic 11: Publishing & Revenue Suite endpoints
    # -----------------------------------------------------------------------

    def _publishing_or_503():
        pub = _get_publishing()
        if pub is None:
            raise HTTPException(status_code=503, detail="PublishingSuite not initialised")
        return pub

    def _publishing_reviews_path() -> Path:
        return Path.home() / ".jarvis" / "publishing" / "ghostwritr_reviews.jsonl"

    def _read_publishing_review_rows() -> list[dict[str, Any]]:
        path = _publishing_reviews_path()
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                rows.append(record)
        return rows

    def _write_publishing_review_rows(rows: list[dict[str, Any]]) -> None:
        path = _publishing_reviews_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )

    def _pending_publishing_reviews(limit: int = 6) -> list[dict[str, Any]]:
        bridge = _get_ghostwritr_bridge()
        records: list[dict[str, Any]] = []
        if bridge is not None:
            try:
                records = [
                    dict(item.to_dict())
                    for item in list(bridge.get_pending_reviews() or [])
                    if hasattr(item, "to_dict")
                ]
            except Exception:
                records = []
        if not records:
            review_rows = [
                row for row in _read_publishing_review_rows()
                if str(row.get("jarvis_status") or "pending").strip().lower() == "pending"
            ]
            review_rows.sort(key=lambda row: str(row.get("ready_since") or ""))
            records = review_rows
        return [
            {
                "review_id": str(item.get("review_id") or "").strip(),
                "title": str(item.get("title") or "").strip(),
                "slug": str(item.get("slug") or "").strip(),
                "track_type": str(item.get("track_type") or "").strip(),
                "chapter_number": item.get("chapter_number"),
                "stage_key": str(item.get("stage_key") or "").strip(),
                "stage_display": str(item.get("stage_display") or "").strip(),
                "content_preview": str(item.get("content_preview") or "").strip(),
                "word_count": int(item.get("word_count", 0) or 0),
                "ready_since": str(item.get("ready_since") or "").strip(),
                "approval_id": str(item.get("approval_id") or "").strip(),
                "feedback": str(item.get("feedback") or "").strip(),
            }
            for item in records[:limit]
            if str(item.get("review_id") or "").strip()
        ]

    def _mutate_publishing_review(review_id: str, *, target_status: str, feedback: str = "") -> dict[str, Any] | None:
        from datetime import datetime, timezone

        bridge = _get_ghostwritr_bridge()
        if bridge is not None:
            if target_status == "approved":
                result = bridge.mark_approved(review_id, feedback=feedback)
            else:
                result = bridge.mark_needs_revision(review_id, feedback=feedback)
            return dict(result.to_dict()) if result is not None and hasattr(result, "to_dict") else None

        rows = _read_publishing_review_rows()
        updated: dict[str, Any] | None = None
        for row in rows:
            if str(row.get("review_id") or "").strip() != review_id:
                continue
            row["jarvis_status"] = target_status
            row["feedback"] = feedback if target_status == "needs_revision" else str(row.get("feedback") or "")
            row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            updated = dict(row)
            break
        if updated is None:
            return None
        _write_publishing_review_rows(rows)
        return updated

    def _record_publish_history(
        *,
        actor_id: str,
        event_type: str,
        title: str,
        detail: str,
        status_label: str,
        related_label: str = "",
        project_id: str = "",
        review_id: str = "",
        step: str = "",
    ) -> dict[str, Any]:
        return PublishHistoryStore().record_event(
            actor_id=actor_id,
            event_type=event_type,
            title=title,
            detail=detail,
            status_label=status_label,
            route="/publish",
            related_label=related_label,
            project_id=project_id,
            review_id=review_id,
            step=step,
        )

    def _build_publish_launch_workspace(pub: Any, project_id: str, *, generated_at: str = "") -> dict[str, Any] | None:
        if not project_id:
            return None
        project = pub._store.get_project(project_id)
        if project is None:
            return None
        checklist_items = list(pub.robbie.get_publishing_checklist(project))
        completed_steps = sum(1 for item in checklist_items if bool(item.get("completed")))
        total_steps = len(checklist_items)
        next_step = next((str(item.get("label") or "").strip() for item in checklist_items if not bool(item.get("completed"))), "")
        return {
            "project_id": project.project_id,
            "title": project.title,
            "platform": project.platform,
            "project_type": project.project_type,
            "checklist_progress": f"{completed_steps}/{total_steps}" if total_steps else "",
            "checklist_percent": round((completed_steps / total_steps) * 100) if total_steps else 0,
            "next_checklist_step": next_step,
            "generated_at": generated_at,
            "checklist": checklist_items,
        }

    def _mutate_publishing_checklist_step(
        project_id: str,
        *,
        step: str,
        completed: bool,
        actor: str = "Chris",
    ) -> dict[str, Any]:
        pub = _publishing_or_503()
        project = pub._store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Publishing project not found: {project_id}")

        checklist = list(pub.robbie.get_publishing_checklist(project))
        matched = next((item for item in checklist if str(item.get("step") or "").strip() == step), None)
        if matched is None:
            raise HTTPException(status_code=404, detail=f"Checklist step not found: {step}")

        result = pub.robbie.track_kdp_checklist(project_id, step, completed)
        workspace = _build_publish_launch_workspace(pub, project_id)
        action_title = "Complete Publish Checklist Step" if completed else "Reopen Publish Checklist Step"
        step_label = str(matched.get("label") or step).strip() or step
        project_title = project.title.strip() or project_id
        detail = (
            f"{step_label} marked complete for {project_title}."
            if completed
            else f"{step_label} reopened for {project_title}."
        )
        actor_name = str(actor or "Chris").strip() or "Chris"
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor_name,
                "domain": "publish",
                "action": action_title,
                "title": step_label,
                "detail": detail,
                "why_now": "Publish launch orchestration advanced a real checklist step from the live module route.",
                "result_summary": f"Publish checklist now at {result.get('progress') or 'updated'}.",
                "related_route": "/publish",
                "route_label": "Open Publish",
                "related_kind": "publishing-checklist",
                "related_label": project_title,
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Publish",
            reason=detail,
            route="/publish",
            actor=actor_name,
        )
        history_entry = _record_publish_history(
            actor_id=actor_name,
            event_type="checklist-completed" if completed else "checklist-reopened",
            title=action_title,
            detail=detail,
            status_label="Completed" if completed else "Reopened",
            related_label=project_title,
            project_id=project_id,
            step=step,
        )
        return {
            "status": "completed" if completed else "reopened",
            "project_id": project_id,
            "step": step,
            "label": step_label,
            "completed": completed,
            "progress": str(result.get("progress") or ""),
            "percent": int(result.get("percent") or 0),
            "workspace": workspace,
            "focus": focus,
            "history_entry": history_entry,
        }

    def _dining_parse_prefs(raw: Any) -> list[str]:
        if raw is None:
            return []
        if isinstance(raw, str):
            parts = re.split(r"[,|]", raw)
        elif isinstance(raw, (list, tuple, set)):
            parts = [str(item) for item in raw]
        else:
            parts = [str(raw)]
        seen: set[str] = set()
        prefs: list[str] = []
        for part in parts:
            value = str(part or "").strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            prefs.append(value)
        return prefs

    def _dining_bool(raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        text = str(raw or "").strip().lower()
        return text in {"1", "true", "yes", "on"}

    def _dining_cuisine_label(cuisine: str) -> str:
        labels = {
            "any": "Any",
            "american": "American",
            "breakfast": "Breakfast",
            "burgers": "Burgers",
            "barbecue": "BBQ",
            "chinese": "Chinese",
            "indian": "Indian",
            "italian": "Italian",
            "japanese": "Sushi",
            "mexican": "Mexican",
            "pizza": "Pizza",
            "seafood": "Seafood",
            "steak": "Steakhouse",
            "thai": "Thai",
        }
        return labels.get(str(cuisine or "any").strip().lower(), str(cuisine or "Dining").strip() or "Dining")

    def _dining_city_from_address(address: str) -> str:
        parts = [part.strip() for part in str(address or "").split(",") if str(part or "").strip()]
        if len(parts) >= 2:
            return parts[-2]
        if parts:
            return parts[-1]
        return "Nearby"

    def _dining_match_metadata(
        spot: dict[str, Any],
        *,
        query: str,
        cuisine: str,
        prefs: Sequence[str],
        open_now_bias: bool,
        favorite_ids: set[str],
    ) -> dict[str, Any]:
        name = str(spot.get("name") or "")
        address = str(spot.get("address") or "")
        types = [str(item or "") for item in list(spot.get("types") or [])]
        haystack = " ".join([name, address, " ".join(types), _dining_cuisine_label(cuisine)]).lower()
        tokens = [token for token in re.findall(r"[a-z0-9$+]+", str(query or "").lower()) if len(token) >= 3]
        rating = float(spot.get("rating") or 0.0)
        reviews = int(spot.get("review_count") or 0)
        distance = float(spot.get("distance_mi") or 99.0)
        price = str(spot.get("price") or "")
        favorite = str(spot.get("place_id") or "") in favorite_ids

        score = 48
        if tokens:
            matches = sum(1 for token in tokens if token in haystack)
            score += min(18, matches * 5)
        if rating:
            score += min(18, max(0, round((rating - 3.5) * 10)))
        if reviews:
            score += min(10, max(1, round(math.log10(reviews + 1) * 3)))
        if open_now_bias and bool(spot.get("open_now")):
            score += 7
        if distance <= 5:
            score += 5
        if len(price) >= 3 and any(pref.strip() == "$$$" for pref in prefs):
            score += 4
        if favorite:
            score += 3
        score = max(24, min(99, score))

        reasons: list[str] = []
        if bool(spot.get("open_now")):
            reasons.append("Open now")
        if rating >= 4.5:
            reasons.append(f"{rating:.1f} star rating")
        elif rating >= 4.0:
            reasons.append(f"Strong {rating:.1f} star rating")
        if reviews:
            reasons.append(f"{reviews:,} verified reviews")
        if distance <= 2:
            reasons.append(f"{distance:.1f} mi away")
        elif distance <= 5:
            reasons.append(f"Within {distance:.1f} mi")
        if len(price) >= 3:
            reasons.append(f"{price} price posture")
        if favorite:
            reasons.append("Already saved to favorites")
        if cuisine and cuisine != "any":
            reasons.append(f"{_dining_cuisine_label(cuisine)} lane")
        if tokens and not reasons:
            reasons.append(f"Matched {len(tokens)} dining cue(s)")
        if not reasons:
            reasons.append("Useful nearby match")

        return {
            "match_score": score,
            "highlights": reasons[:4],
            "reasons": reasons[:5],
            "city": _dining_city_from_address(address),
            "is_favorite": favorite,
        }

    def _dining_recent_searches_from_activity(items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        searches: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "")
            if title != "Run Dining Search":
                continue
            searches.append(
                {
                    "label": str(item.get("related_label") or item.get("subtitle") or "Dining search"),
                    "summary": str(item.get("detail") or item.get("subtitle") or ""),
                    "when": str(item.get("occurred_at") or item.get("created_at") or ""),
                }
            )
        return searches[:6]

    def _dining_recent_reservations_from_activity(items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        intents: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "")
            if title != "Save Dining Reservation Intent":
                continue
            intents.append(
                {
                    "label": str(item.get("related_label") or "Reservation intent"),
                    "summary": str(item.get("detail") or item.get("subtitle") or ""),
                    "when": str(item.get("occurred_at") or item.get("created_at") or ""),
                    "status": str(item.get("status_label") or "Saved"),
                }
            )
        return intents[:6]

    async def _build_dining_module_payload(
        *,
        query: str = "",
        cuisine: str = "japanese",
        open_now: bool = False,
        prefs: Sequence[str] | None = None,
        quick_filter: str = "best",
        limit: int = 12,
    ) -> dict[str, Any]:
        generated_at = datetime.now(timezone.utc).isoformat()
        prefs = _dining_parse_prefs(list(prefs or []))
        query = str(query or "").strip()
        cuisine = str(cuisine or "any").strip().lower() or "any"
        quick_filter = str(quick_filter or "best").strip().lower() or "best"

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Dining now has a dedicated module route with live nearby search, Sam-backed recommendations, favorite persistence, and honest reservation boundaries.",
            "what_became_real": "Dining is now represented as a dedicated app module route instead of a shell-only mockup with missing backend APIs.",
            "remains_partial": "Live reservation feeds and structured menu partner data are still unavailable in this runtime.",
            "runtime_note": "Dining is live and connected.",
            "availability_notes": [],
            "query": query,
            "cuisine": cuisine,
            "cuisine_label": _dining_cuisine_label(cuisine),
            "open_now": bool(open_now),
            "quick_filter": quick_filter,
            "preferences": list(prefs),
            "results": [],
            "recommendations": [],
            "favorites": [],
            "recent_searches": [],
            "recent_reservation_intents": [],
            "recent_activity": [],
            "feature_cards": [],
            "reservation_partner": {
                "connected": False,
                "status": "unavailable",
                "message": "Live reservation booking is not connected in this runtime. JARVIS can save reservation intent and route you to call, website, or maps instead.",
            },
            "counts": {
                "results": 0,
                "favorites": 0,
                "cities": 0,
                "reviews": 0,
                "recent_searches": 0,
                "reservation_intents": 0,
                "recent_activity": 0,
            },
            "network_metrics": {
                "restaurants": 0,
                "cities": 0,
                "reviews": 0,
                "match_rate": 0,
            },
            "proof_paths": {
                "module_route": "/dining-center",
                "module_api": "/api/dining/module",
                "nearby_api": "/api/dining/nearby",
                "recommend_api": "/api/dining/recommend",
                "details_api_suffix": "/api/dining/details/{place_id}",
                "favorites_api": "/api/dining/favorites",
                "favorite_api": "/api/dining/favorite",
                "reservation_intent_api": "/api/dining/reservation-intent",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        favorite_ids: set[str] = set()
        try:
            favorites = list(dining_module.get_favorites() or [])
            payload["favorites"] = favorites
            favorite_ids = {str(item.get("place_id") or "") for item in favorites}
            payload["counts"]["favorites"] = len(favorites)
        except Exception as exc:
            payload["errors"].append(f"favorites: {exc}")
            payload["availability_notes"].append("Favorites could not be loaded from the Dining store.")

        try:
            recommendation_packet = dining_module.recommend_restaurants(runtime=runtime, limit=3)
            recommendation_rows = list(recommendation_packet.get("recommendations") or [])
            payload["recommendations"] = [
                dict(item, **_dining_match_metadata(
                    item,
                    query=query,
                    cuisine=cuisine,
                    prefs=prefs,
                    open_now_bias=bool(open_now),
                    favorite_ids=favorite_ids,
                ))
                for item in recommendation_rows
                if isinstance(item, dict)
            ]
            if recommendation_packet.get("sam_context"):
                payload["sam_context"] = str(recommendation_packet.get("sam_context") or "")
        except Exception as exc:
            payload["errors"].append(f"recommendations: {exc}")
            payload["availability_notes"].append("Sam-backed dining recommendations are unavailable in this runtime.")

        try:
            min_rating = 4.0 if any(pref.strip() == "4.0+" for pref in prefs) else 3.5
            nearby = dining_module.nearby_restaurants(
                cuisine=cuisine,
                open_now=bool(open_now),
                min_rating=min_rating,
                radius_miles=10.0,
                limit=max(4, int(limit)),
            )
            results = [dict(item) for item in nearby if isinstance(item, dict)]
            if payload["recommendations"]:
                seen: set[str] = set()
                merged: list[dict[str, Any]] = []
                for item in list(payload["recommendations"]) + results:
                    place_id = str(item.get("place_id") or "")
                    if not place_id or place_id in seen:
                        continue
                    seen.add(place_id)
                    merged.append(dict(item))
                results = merged
            if query:
                tokens = [token for token in re.findall(r"[a-z0-9$+]+", query.lower()) if len(token) >= 3]
                filtered = []
                for item in results:
                    haystack = " ".join(
                        [
                            str(item.get("name") or ""),
                            str(item.get("address") or ""),
                            " ".join(str(value or "") for value in list(item.get("types") or [])),
                        ]
                    ).lower()
                    if all(token in haystack or token in query.lower() for token in tokens):
                        filtered.append(item)
                if filtered:
                    results = filtered
            enriched = [
                dict(
                    item,
                    **_dining_match_metadata(
                        item,
                        query=query,
                        cuisine=cuisine,
                        prefs=prefs,
                        open_now_bias=bool(open_now),
                        favorite_ids=favorite_ids,
                    ),
                )
                for item in results
            ]
            if quick_filter == "open":
                enriched = [item for item in enriched if bool(item.get("open_now"))]
            enriched.sort(
                key=lambda item: (
                    int(item.get("match_score") or 0),
                    float(item.get("rating") or 0.0),
                    int(item.get("review_count") or 0),
                ),
                reverse=True,
            )
            payload["results"] = enriched
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["summary"] = "Dining module route is live, but nearby restaurant search did not fully hydrate."
            payload["runtime_note"] = "Dining is partially connected. Nearby search did not fully hydrate in this runtime."
            payload["remains_partial"] = "Live Places search still needs configuration or repair in this runtime."
            payload["errors"].append(f"nearby: {exc}")
            payload["availability_notes"].append(str(exc))

        payload["counts"]["results"] = len(payload["results"])
        payload["network_metrics"]["restaurants"] = len(payload["results"])
        payload["network_metrics"]["cities"] = len({str(item.get("city") or "") for item in payload["results"] if str(item.get("city") or "")})
        payload["network_metrics"]["reviews"] = int(sum(int(item.get("review_count") or 0) for item in payload["results"]))
        payload["network_metrics"]["match_rate"] = int(payload["results"][0].get("match_score") or 0) if payload["results"] else 0
        payload["counts"]["cities"] = payload["network_metrics"]["cities"]
        payload["counts"]["reviews"] = payload["network_metrics"]["reviews"]

        recent_activity = _module_recent_activity(route="/dining-center", domain="dining", limit=10)
        payload["recent_activity"] = recent_activity
        payload["counts"]["recent_activity"] = len(recent_activity)
        payload["recent_searches"] = _dining_recent_searches_from_activity(recent_activity)
        payload["recent_reservation_intents"] = _dining_recent_reservations_from_activity(recent_activity)
        payload["counts"]["recent_searches"] = len(payload["recent_searches"])
        payload["counts"]["reservation_intents"] = len(payload["recent_reservation_intents"])

        if payload["results"]:
            payload["selected_place_id"] = str((payload["results"][0] or {}).get("place_id") or "")
            payload["selected_place"] = payload["results"][0]
            payload["summary"] = (
                f"Dining loaded {len(payload['results'])} real restaurant result(s), "
                f"{payload['counts']['favorites']} saved favorite(s), and "
                f"{payload['counts']['recent_searches']} recent dining search event(s)."
            )
        else:
            payload["status"] = "Wired" if payload["errors"] else "Useful"
            payload["runtime_note"] = "Dining is live, but no restaurants matched the current filters."
            payload["availability_notes"].append("No restaurants matched the current query and filter combination.")

        if not payload["favorites"]:
            payload["availability_notes"].append("No dining favorites are saved yet.")
        if not payload["recent_searches"]:
            payload["availability_notes"].append("No dining search history has been recorded yet.")
        if not payload["recent_reservation_intents"]:
            payload["availability_notes"].append("No dining reservation intents have been saved yet.")

        payload["feature_cards"] = [
            {
                "title": "Real Nearby Search",
                "copy": "Results come from the live nearby dining search route instead of static shortlist cards.",
            },
            {
                "title": "Sam Recommendations",
                "copy": "Taste-aware picks are merged in when recommendation sources are available.",
            },
            {
                "title": "Favorites Persistence",
                "copy": "Saved spots are backed by the Dining favorites store and survive reloads.",
            },
            {
                "title": "Reservation Boundary",
                "copy": payload["reservation_partner"]["message"],
            },
        ]

        if payload["errors"] and payload["status"] == "Useful":
            payload["runtime_note"] = "Dining is live, but some backend sources are partially unavailable."
            payload["remains_partial"] = "Some dining sources still failed to hydrate; inspect the payload preview for details."
        if not payload["availability_notes"]:
            payload["availability_notes"].append("All currently available Dining sources hydrated successfully.")
        return payload

    @app.get("/api/dining/module")
    async def api_dining_module(
        query: str = "",
        cuisine: str = "japanese",
        open_now: bool = False,
        prefs: str = "",
        quick_filter: str = "best",
        limit: int = 12,
    ) -> JSONResponse:
        payload = await _build_dining_module_payload(
            query=query,
            cuisine=cuisine,
            open_now=open_now,
            prefs=_dining_parse_prefs(prefs),
            quick_filter=quick_filter,
            limit=limit,
        )
        return _json(payload)

    @app.get("/api/dining/nearby")
    async def api_dining_nearby(
        cuisine: str = "any",
        open_now: bool = False,
        min_rating: float = 3.5,
        radius_miles: float = 10.0,
        limit: int = 10,
        query: str = "",
        prefs: str = "",
    ) -> JSONResponse:
        try:
            favorites = list(dining_module.get_favorites() or [])
            favorite_ids = {str(item.get("place_id") or "") for item in favorites}
            restaurants = dining_module.nearby_restaurants(
                cuisine=cuisine,
                open_now=open_now,
                min_rating=min_rating,
                radius_miles=radius_miles,
                limit=limit,
            )
            enriched = [
                dict(
                    item,
                    **_dining_match_metadata(
                        item,
                        query=query,
                        cuisine=cuisine,
                        prefs=_dining_parse_prefs(prefs),
                        open_now_bias=bool(open_now),
                        favorite_ids=favorite_ids,
                    ),
                )
                for item in restaurants
            ]
            enriched.sort(key=lambda item: int(item.get("match_score") or 0), reverse=True)
            return _json({"restaurants": enriched, "count": len(enriched)})
        except Exception as exc:
            return _json({"restaurants": [], "count": 0, "error": str(exc)})

    @app.get("/api/dining/recommend")
    async def api_dining_recommend(limit: int = 3) -> JSONResponse:
        packet = dining_module.recommend_restaurants(runtime=runtime, limit=max(1, int(limit or 3)))
        recommendations = [
            dict(
                item,
                **_dining_match_metadata(
                    item,
                    query="",
                    cuisine="any",
                    prefs=[],
                    open_now_bias=bool(packet.get("open_now_filter")),
                    favorite_ids={str(f.get("place_id") or "") for f in list(dining_module.get_favorites() or [])},
                ),
            )
            for item in list(packet.get("recommendations") or [])
            if isinstance(item, dict)
        ]
        return _json({**packet, "recommendations": recommendations})

    @app.get("/api/dining/details/{place_id}")
    async def api_dining_details(place_id: str) -> JSONResponse:
        try:
            detail = dict(dining_module.get_place_details(place_id) or {})
            photo_ref = str(detail.get("photo_ref") or "")
            if photo_ref:
                detail["photo_url"] = dining_module.photo_url(photo_ref)
            return _json(detail)
        except Exception as exc:
            return _json({"error": str(exc)})

    @app.get("/api/dining/favorites")
    async def api_dining_favorites() -> JSONResponse:
        try:
            favorites = list(dining_module.get_favorites() or [])
            return _json({"favorites": favorites, "count": len(favorites)})
        except Exception as exc:
            return _json({"favorites": [], "count": 0, "error": str(exc)})

    @app.post("/api/dining/favorite")
    async def api_dining_toggle_favorite(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        place_id = str(body.get("place_id") or "").strip()
        name = str(body.get("name") or "").strip() or "Dining Favorite"
        address = str(body.get("address") or "").strip()
        rating = body.get("rating")
        if not place_id:
            raise HTTPException(status_code=400, detail="place_id is required")
        result = dining_module.toggle_favorite(place_id, name, address, rating)
        action = str(result.get("action") or "")
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": "Chris",
                "domain": "dining",
                "action": "Save Dining Favorite" if action == "added" else "Remove Dining Favorite",
                "detail": (
                    f"{'Saved' if action == 'added' else 'Removed'} {name} in Dining favorites."
                ),
                "route": "/dining-center",
                "related_kind": "dining-favorite",
                "related_label": name,
                "status_label": "Saved" if action == "added" else "Removed",
                "result_summary": (
                    f"Dining favorites now track {len(list(result.get('favorites') or []))} spot(s)."
                ),
            },
        )
        return _json(result)

    @app.post("/api/dining/reservation-intent")
    async def api_dining_reservation_intent(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        actor = str(body.get("actor") or "Chris").strip() or "Chris"
        place_id = str(body.get("place_id") or "").strip()
        place_name = str(body.get("place_name") or "").strip() or "Dining reservation"
        preferred_slot = str(body.get("preferred_slot") or "").strip()
        detail = (
            f"Saved a reservation intent for {place_name}"
            + (f" at {preferred_slot}" if preferred_slot else "")
            + ". Live booking is not connected in this runtime."
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "dining",
                "action": "Save Dining Reservation Intent",
                "detail": detail,
                "route": "/dining-center",
                "related_kind": "dining-reservation-intent",
                "related_label": place_name,
                "status_label": "Saved",
                "result_summary": "Dining reservation intent was saved for later follow-through.",
                "place_id": place_id,
                "preferred_slot": preferred_slot,
            },
        )
        return _json(
            {
                "ok": True,
                "status": "saved",
                "partner_connected": False,
                "place_id": place_id,
                "place_name": place_name,
                "preferred_slot": preferred_slot,
                "detail": detail,
                "next_step": "Use the phone, website, or map actions in Dining details to complete the booking manually.",
            }
        )

    async def _build_foundry_module_payload(actor_name: str = "Chris") -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        availability_notes: list[str] = []
        errors: list[str] = []

        projects: list[dict[str, Any]] = []
        open_tasks: list[dict[str, Any]] = []
        today_tasks: list[dict[str, Any]] = []
        home_db = _get_home_db()
        if home_db is None:
            availability_notes.append("Home project storage is not initialised, so Foundry project and task depth is limited.")
        else:
            try:
                projects = list(await asyncio.to_thread(home_db.list_projects, "active"))
            except Exception as exc:
                errors.append(f"home_projects: {exc}")
                availability_notes.append(f"Active Foundry projects could not be loaded: {exc}")
            try:
                open_tasks = list(await asyncio.to_thread(home_db.list_tasks, None, "open"))
            except Exception as exc:
                errors.append(f"home_tasks_open: {exc}")
                availability_notes.append(f"Open task intake could not be loaded: {exc}")
            try:
                today_tasks = list(await asyncio.to_thread(home_db.get_tasks_due_today))
            except Exception as exc:
                errors.append(f"home_tasks_today: {exc}")
                availability_notes.append(f"Today's task runway could not be loaded: {exc}")

        publishing_module: dict[str, Any] = {}
        books: list[dict[str, Any]] = []
        pending_reviews: list[dict[str, Any]] = []
        revenue_summary: dict[str, Any] = {}
        publishing_metrics: dict[str, Any] = {}
        content_performance: dict[str, Any] = {}
        pub = _get_publishing()
        try:
            publishing_module = _build_publish_module_payload()
            books = list(publishing_module.get("projects") or [])[:8]
            pending_reviews = list(publishing_module.get("pending_reviews") or [])[:8]
            revenue_summary = dict(publishing_module.get("revenue") or {})
        except Exception as exc:
            errors.append(f"publish_module: {exc}")
            availability_notes.append(f"Publishing continuity could not be fully loaded: {exc}")
        if pub is not None:
            try:
                publishing_metrics = await asyncio.to_thread(pub.sage.get_publishing_metrics)
            except Exception as exc:
                errors.append(f"publishing_metrics: {exc}")
                availability_notes.append(f"Publishing metrics were unavailable: {exc}")
            try:
                content_performance = await asyncio.to_thread(pub.sage.get_content_performance)
            except Exception as exc:
                errors.append(f"content_performance: {exc}")
                availability_notes.append(f"Audience/content performance signals were unavailable: {exc}")
        else:
            availability_notes.append("Live publishing analytics are not initialised in this runtime, so Foundry audience and launch depth is partial.")

        ideas: list[dict[str, Any]] = []
        try:
            from .ideas import list_ideas

            ideas = list(await asyncio.to_thread(list_ideas))
        except Exception as exc:
            errors.append(f"ideas: {exc}")
            availability_notes.append(f"Idea intake could not be loaded: {exc}")

        dossiers: list[dict[str, Any]] = []
        try:
            from dataclasses import asdict
            from .dossier import get_dossier_store

            store = get_dossier_store()
            dossiers = [asdict(item) for item in store.get_all()]
        except Exception as exc:
            errors.append(f"dossiers: {exc}")
            availability_notes.append(f"Dossier research outputs were unavailable: {exc}")

        total_projected_value = round(sum(float(item.get("projected_value") or 0) for item in projects), 2)
        total_monthly_estimate = float(revenue_summary.get("monthly_estimate_total") or revenue_summary.get("total_monthly_estimate") or 0.0)
        total_reach = 0
        for item in (content_performance.get("platform_breakdown") or {}).values():
            if isinstance(item, dict):
                total_reach += int(item.get("total_reach") or 0)
        published_count = int(publishing_metrics.get("published_count") or 0)
        in_progress_count = int(publishing_metrics.get("in_progress_count") or 0)
        active_assets = len(projects) + len(books) + len(dossiers)
        research_ready_ideas = len([item for item in ideas if str(item.get("status") or "").strip().lower() in {"done", "researching"}])
        queued_ideas = len([item for item in ideas if str(item.get("status") or "").strip().lower() in {"captured", "queued"}])
        revenue_projects = [item for item in projects if str(item.get("track") or "").strip().lower() == "revenue"]
        focus_asset = (projects[:1] or books[:1] or ideas[:1] or [{}])[0]
        focus_title = str(focus_asset.get("title") or focus_asset.get("text") or "Choose the next durable asset").strip() or "Choose the next durable asset"
        focus_pct = 0
        if focus_asset:
            if focus_asset.get("total_stages"):
                try:
                    focus_pct = max(0, min(100, round((float(focus_asset.get("stages_complete") or 0) / max(float(focus_asset.get("total_stages") or 1), 1)) * 100)))
                except Exception:
                    focus_pct = 0
            elif focus_asset.get("progress_pct") is not None:
                try:
                    focus_pct = max(0, min(100, int(round(float(focus_asset.get("progress_pct") or 0)))))
                except Exception:
                    focus_pct = 0

        asset_types: list[dict[str, Any]] = []
        for label, count, note in [
            ("Books", len(books), "Publishing projects currently visible in the live publishing store."),
            ("Offers", len(revenue_projects), "Revenue-tracked home projects currently active."),
            ("Projects", len(projects), "Home projects currently active in Foundry."),
            ("Ideas", len(ideas), "Ideas captured and retained in the live idea store."),
            ("Dossiers", len(dossiers), "Research dossiers available for asset shaping."),
            ("Tasks", len(today_tasks), "Tasks due today that can constrain launch or making windows."),
        ]:
            if count:
                asset_types.append({"label": label, "count": count, "note": note})

        performance_rows = [
            {"label": "Projected Value", "display_value": f"${total_projected_value:,.0f}" if total_projected_value else "$0", "note": "Summed from live active home-project projected values."},
            {"label": "Monthly Revenue", "display_value": f"${total_monthly_estimate:,.0f}/mo" if total_monthly_estimate else "$0/mo", "note": "Publishing revenue streams currently tracked in Sage."},
            {"label": "Content Reach", "display_value": f"{total_reach:,}" if total_reach else "Unavailable", "note": "Summed from posted social performance data when available."},
            {"label": "Published Assets", "display_value": str(published_count), "note": "Published publishing projects in the live store."},
            {"label": "Review Gates", "display_value": str(len(pending_reviews)), "note": "Pending editorial reviews blocking launch-ready movement."},
        ]

        health_strengths = []
        if projects:
            health_strengths.append(f"{len(projects)} active home project(s) are visible.")
        if books:
            health_strengths.append(f"{len(books)} publishing project(s) are connected into Foundry.")
        if pending_reviews:
            health_strengths.append(f"{len(pending_reviews)} review gate(s) are live and actionable.")
        if dossiers:
            health_strengths.append(f"{len(dossiers)} dossier(s) can feed future assets.")
        if not health_strengths:
            health_strengths.append("Foundry routes are live, but the asset stack is still thin in this runtime.")

        health_label = "Live"
        if errors and not active_assets:
            health_label = "Partial"
        elif pending_reviews or revenue_projects or total_monthly_estimate:
            health_label = "Operational"

        audience_available = bool(total_reach or (content_performance.get("platform_breakdown") or {}) or publishing_metrics.get("platforms"))
        audience_segments = []
        platform_breakdown = content_performance.get("platform_breakdown") or {}
        for platform, stats in list(platform_breakdown.items())[:6]:
            if not isinstance(stats, dict):
                continue
            audience_segments.append(
                {
                    "label": str(platform).title(),
                    "share": int(stats.get("post_count") or 0),
                    "note": f"{int(stats.get('total_reach') or 0):,} reach across {int(stats.get('post_count') or 0)} post(s).",
                }
            )
        if not audience_segments:
            for platform in list(publishing_metrics.get("platforms") or [])[:6]:
                audience_segments.append({"label": str(platform).title(), "share": 0, "note": "Platform is active, but no audience-performance breakdown is available yet."})

        payload = {
            "generated_at": generated_at,
            "available": bool(active_assets or ideas or today_tasks or pending_reviews),
            "status": "Useful" if (active_assets or ideas or pending_reviews) else "Wired",
            "summary": (
                f"Foundry loaded {len(projects)} active home project(s), {len(books)} publishing project(s), "
                f"{len(ideas)} idea(s), {len(dossiers)} dossier(s), and {len(pending_reviews)} launch review gate(s)."
            ),
            "what_became_real": "Foundry now hydrates from live home projects, publishing stores, idea intake, dossier research, and task runway data instead of shell-side growth fiction.",
            "remains_partial": "Audience intelligence and deeper commercialization posture still depend on whichever publishing analytics and revenue tracking are actually configured in this runtime.",
            "runtime_note": availability_notes[0] if availability_notes else "Foundry is live and connected.",
            "availability_notes": availability_notes[:8],
            "counts": {
                "active_assets": active_assets,
                "projects": len(projects),
                "books": len(books),
                "ideas": len(ideas),
                "dossiers": len(dossiers),
                "pending_reviews": len(pending_reviews),
                "due_today": len(today_tasks),
                "projected_value": total_projected_value,
                "monthly_revenue": total_monthly_estimate,
                "audience_reach": total_reach,
            },
            "hero": {
                "focus_title": focus_title,
                "focus_subtitle": str(focus_asset.get("category") or focus_asset.get("status") or focus_asset.get("track") or "Active asset lane").strip() or "Active asset lane",
                "focus_track": str(focus_asset.get("track") or focus_asset.get("workflow_type") or focus_asset.get("project_type") or focus_asset.get("domain") or "Foundry").strip() or "Foundry",
                "focus_pct": focus_pct,
                "priority_title": str((books[:1] or revenue_projects[:1] or projects[:1] or [{}])[0].get("title") or "Move the highest-trust asset").strip() or "Move the highest-trust asset",
                "priority_copy": (
                    f"{len(pending_reviews)} review gate(s) are holding up launch-ready movement."
                    if pending_reviews
                    else f"{research_ready_ideas} idea(s) are far enough along to shape into real assets."
                ),
                "priority_date": str((books[:1] or [{}])[0].get("updated_at") or generated_at),
                "priority_pct": focus_pct,
                "making_window": "Today has task pressure to work around." if today_tasks else "No hard deadline pressure is visible in today's task runway.",
                "today_count": len(today_tasks),
                "today_high_priority_count": len([item for item in today_tasks if str(item.get("priority") or "").strip().lower() == "high"]),
                "incubator_count": len([item for item in ideas if str(item.get("status") or "").strip().lower() != "passed"]),
                "research_ready_count": research_ready_ideas,
                "active_project_count": len(projects) or in_progress_count,
                "review_count": len(pending_reviews),
                "command_narrative": (
                    f'Today’s best Foundry move is to stay with "{focus_title}" until it becomes more real.'
                    if focus_asset
                    else "Foundry is live, but it needs a clear active asset before leverage compounds."
                ),
                "economic_lens": (
                    f"Active home projects currently carry ${total_projected_value:,.0f} in projected value."
                    if total_projected_value
                    else "No projected-value data is attached to the active home projects yet."
                ),
                "legacy_lens": (
                    f"{published_count} published asset(s) and {len(books)} publishing project(s) are shaping the durable body of work."
                    if books or published_count
                    else "No publishing asset is far enough along yet to anchor the long-horizon body of work."
                ),
            },
            "pipeline": {
                "idea": len(ideas),
                "shape": queued_ideas,
                "build": len(projects),
                "launch": len(pending_reviews),
                "grow": len(revenue_projects) or int(revenue_summary.get("active_stream_count") or 0),
                "total_assets": active_assets,
            },
            "asset_types": asset_types,
            "performance": performance_rows,
            "health": {
                "score_label": health_label,
                "copy": "Foundry is drawing from live project, publishing, and research sources." if active_assets else "Foundry routes are wired, but the asset graph is still sparse.",
                "strengths": health_strengths[:5],
            },
            "projects": projects[:8],
            "publishing": {
                "projects": books[:8],
                "opportunity_title": str((books[:1] or [{}])[0].get("title") or "Repurpose the strongest asset").strip() or "Repurpose the strongest asset",
                "opportunity_copy": (
                    f'{str((books[:1] or [{}])[0].get("title") or "The lead publishing asset").strip() or "The lead publishing asset"} already has enough live structure to feed additional formats.'
                    if books
                    else "No publishing asset is active enough yet to show clear repurposing lanes."
                ),
            },
            "offers": {
                "rows": [
                    {
                        "title": str(item.get("title") or "Revenue asset").strip() or "Revenue asset",
                        "subtitle": str(item.get("category") or item.get("status") or "Economic lane").strip() or "Economic lane",
                        "value_label": f"${float(item.get('projected_value') or 0):,.0f}" if float(item.get("projected_value") or 0) else "Unvalued",
                        "status_label": str(item.get("status") or "active").strip() or "active",
                    }
                    for item in revenue_projects[:6]
                ],
                "note": (
                    f"{int(revenue_summary.get('active_stream_count') or 0)} live revenue stream(s) are currently tracked."
                    if revenue_summary
                    else "No live offer or revenue stream analytics are currently attached to Foundry."
                ),
            },
            "audience": {
                "available": audience_available,
                "total_label": f"{total_reach:,}" if total_reach else "Unavailable",
                "growth_note": (
                    f"{int(content_performance.get('total_posts_analyzed') or 0)} posted content item(s) are contributing live audience signal."
                    if audience_available
                    else "No live audience segmentation or posted-performance signal is currently available."
                ),
                "segments": audience_segments[:6],
            },
            "incubator": {
                "ideas": ideas[:8],
                "dossiers": dossiers[:6],
            },
            "launch": {
                "rows": [
                    {
                        "title": str(item.get("title") or item.get("text") or "Launch lane").strip() or "Launch lane",
                        "subtitle": str(item.get("current_stage") or item.get("status") or "Launch control item").strip() or "Launch control item",
                    }
                    for item in ([*books[:4], *today_tasks[:4]])
                ],
                "score_label": "Ready" if pending_reviews else ("Building" if books or projects else "Standby"),
                "checklist": [
                    "Audience analytics are live." if audience_available else "Audience analytics are not live yet.",
                    "Publishing reviews are visible." if pending_reviews else "No pending editorial review gates are visible.",
                    "Revenue signals are tracked." if total_monthly_estimate else "No live monthly revenue estimate is attached yet.",
                    "Today's runway is clear." if not today_tasks else f"{len(today_tasks)} due-today task(s) can affect launch pacing.",
                    "Dossier research is available." if dossiers else "No dossier research is currently attached to launch planning.",
                ],
            },
            "recent_activity": _module_recent_activity(route="/foundry", domain="foundry"),
            "proof_paths": {
                "module_route": "/foundry",
                "module_api": "/api/foundry/module",
                "projects_api": "/api/home/projects?status=active",
                "tasks_api": "/api/home/tasks?status=open",
                "tasks_today_api": "/api/home/tasks/today",
                "publishing_module_api": "/api/publish/module",
                "publishing_projects_api": "/api/publishing/projects",
                "publishing_metrics_api": "/api/publishing/metrics",
                "ideas_api": "/api/ideas",
                "idea_create_api": "/api/ideas",
                "dossiers_api": "/api/dossiers",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": errors,
        }
        if not payload["available"]:
            payload["summary"] = "Foundry routes are live, but the runtime could not hydrate meaningful creative asset, publishing, or research data."
        if errors and payload["runtime_note"] == "Foundry is live and connected.":
            payload["runtime_note"] = "Foundry is live, but some backend asset sources are partially unavailable."
        return payload

    def _build_publish_module_payload() -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()
        bridge = _get_ghostwritr_bridge()
        pub = _get_publishing()
        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": bool(pub is not None or bridge is not None),
            "status": "Stubbed",
            "summary": "Publish now has a dedicated module route, but backend publishing sources are not initialised in this runtime.",
            "what_became_real": "JARVIS now exposes Publish as a dedicated app module route instead of leaving it hidden behind APIs and shared workspaces.",
            "remains_partial": "Broader publishing controls and deeper drill-ins still need follow-on slices.",
            "runtime_note": "Publishing is wired, but the live publishing backend is not initialised in this runtime.",
            "availability_notes": [],
            "project_count": 0,
            "active_project_count": 0,
            "review_count": 0,
            "pending_reviews_count": 0,
            "scheduled_post_count": 0,
            "overdue_calendar_count": 0,
            "counts": {
                "projects": 0,
                "active_projects": 0,
                "reviews": 0,
                "scheduled_posts": 0,
                "overdue_calendar": 0,
                "history": 0,
            },
            "projects": [],
            "pending_reviews": [],
            "launch_workspace": None,
            "launch_history": {"count": 0, "counts": {}, "items": []},
            "history_count": 0,
            "calendar": {"upcoming": [], "overdue": []},
            "social": {"posts": []},
            "revenue": {
                "monthly_estimate_total": 0.0,
                "active_stream_count": 0,
                "attention_count": 0,
            },
            "launch_control": {"active_project": None, "next_action": "Publishing sources are not initialised yet."},
            "recent_activity": [],
            "proof_paths": {
                "module_route": "/publish",
                "module_api": "/api/publish/module",
                "status_api": "/api/publishing/status",
                "projects_api": "/api/publishing/projects",
                "review_pending_api": "/api/publishing/reviews/pending",
                "review_approve_api": "/api/publishing/draft/approve",
                "review_revise_api": "/api/publishing/draft/revise",
                "checklist_step_api": "/api/publishing/checklist/step",
                "history_api": "/api/publish/module",
                "calendar_api": "/api/publishing/calendar",
                "social_api": "/api/publishing/social/posts",
                "launch_plan_api": "/api/publishing/launch-plan",
                "launch_scan_api": "/api/publishing/launch-scan",
                "launch_asset_get_api_suffix": "/api/publishing/launch/{slug}",
                "launch_asset_generate_api_suffix": "/api/publishing/launch/{slug}/generate",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        try:
            history_summary = PublishHistoryStore().summary(actor_id="chris", limit=6)
            payload["launch_history"] = history_summary
            payload["history_count"] = int(history_summary.get("count") or 0)
            payload["counts"]["history"] = payload["history_count"]
        except Exception as exc:
            payload["errors"].append(f"publish_history: {exc}")
            payload["availability_notes"].append(f"Publish history was unavailable: {exc}")

        try:
            pending_reviews = _pending_publishing_reviews()
            payload["pending_reviews"] = pending_reviews
            payload["review_count"] = len(pending_reviews)
            payload["pending_reviews_count"] = len(pending_reviews)
            payload["counts"]["reviews"] = len(pending_reviews)
            if pending_reviews:
                payload["available"] = True
        except Exception as exc:
            payload["errors"].append(f"publishing_reviews: {exc}")
            payload["availability_notes"].append(f"Editorial review storage was unavailable: {exc}")

        if pub is None:
            if payload["pending_reviews_count"]:
                payload["status"] = "Useful"
                payload["summary"] = "Publish route is live with pending editorial reviews, even though broader publishing sources are not fully initialised in this runtime."
                payload["runtime_note"] = "Publishing is live through editorial review continuity, but Ghostwritr publishing sources are not fully initialised."
            else:
                payload["availability_notes"].append("Ghostwritr publishing services are not initialised in this runtime, so Publish is showing only continuity-safe data.")
            payload["recent_activity"] = _module_recent_activity(route="/publish", domain="publish")
            return payload

        payload["status"] = "Useful"
        payload["summary"] = "Publish now has a dedicated route with live projects, launch control, calendar, social, and revenue posture."
        payload["runtime_note"] = "Publishing is live and connected."

        try:
            projects = list(pub._store.list_projects())
            payload["projects"] = [project.to_dict() for project in projects[:8]]
            payload["project_count"] = len(projects)
            payload["active_project_count"] = sum(1 for project in projects if str(getattr(project, "status", "")).strip() not in {"", "archived", "completed"})
            payload["counts"]["projects"] = payload["project_count"]
            payload["counts"]["active_projects"] = payload["active_project_count"]
        except Exception as exc:
            payload["errors"].append(f"projects: {exc}")
            payload["availability_notes"].append(f"Publishing projects failed to hydrate: {exc}")

        try:
            upcoming = list(pub.calendar.get_upcoming(14))
            overdue = list(pub.calendar.get_overdue())
            payload["calendar"] = {
                "upcoming": [item.to_dict() for item in upcoming[:8]],
                "overdue": [item.to_dict() for item in overdue[:4]],
            }
            payload["overdue_calendar_count"] = len(overdue)
            payload["counts"]["overdue_calendar"] = len(overdue)
        except Exception as exc:
            payload["errors"].append(f"calendar: {exc}")
            payload["availability_notes"].append(f"Publishing calendar failed to hydrate: {exc}")

        try:
            posts = list(pub._store.get_scheduled_posts())
            payload["social"] = {"posts": [post.to_dict() for post in posts[:8]]}
            payload["scheduled_post_count"] = len(posts)
            payload["counts"]["scheduled_posts"] = len(posts)
        except Exception as exc:
            payload["errors"].append(f"social: {exc}")
            payload["availability_notes"].append(f"Publishing social queue failed to hydrate: {exc}")

        try:
            revenue = dict(pub.sage.get_revenue_summary() or {})
            streams = list(revenue.get("streams") or [])
            attention = list(revenue.get("attention_flags") or [])
            payload["revenue"] = {
                "monthly_estimate_total": revenue.get("monthly_estimate_total", 0.0),
                "active_stream_count": len([item for item in streams if bool(item.get("active", True))]),
                "attention_count": len(attention),
            }
        except Exception as exc:
            payload["errors"].append(f"revenue: {exc}")
            payload["availability_notes"].append(f"Publishing revenue posture failed to hydrate: {exc}")

        try:
            launch_control = _build_launch_control_payload(None)
            payload["launch_control"] = launch_control
            active_project = dict(launch_control.get("active_project") or {})
            project_id = str(active_project.get("project_id") or "").strip()
            if not project_id:
                project_id = str((payload["projects"][0] or {}).get("project_id") or "").strip() if payload["projects"] else ""
            if project_id:
                payload["launch_workspace"] = _build_publish_launch_workspace(pub, project_id, generated_at=generated_at)
            if launch_control.get("active_project"):
                payload["what_became_real"] = "Publish now has a dedicated app route backed by live launch-control, project, social, and revenue state."
        except Exception as exc:
            payload["errors"].append(f"launch_control: {exc}")
            payload["availability_notes"].append(f"Launch control failed to hydrate: {exc}")

        payload["recent_activity"] = _module_recent_activity(route="/publish", domain="publish")
        if payload["errors"]:
            payload["remains_partial"] = "Some publishing sources still failed to hydrate; see errors in the payload preview."
            if payload["runtime_note"] == "Publishing is live and connected.":
                payload["runtime_note"] = "Publishing is live, but some backend sources are partially unavailable."
        return payload

    @app.get("/api/publish/module")
    async def api_publish_module() -> JSONResponse:
        return _json(_build_publish_module_payload())

    @app.get("/api/publishing/module")
    async def api_publishing_module_alias() -> JSONResponse:
        return _json(_build_publish_module_payload())

    @app.get("/api/foundry/module")
    async def api_foundry_module() -> JSONResponse:
        return _json(await _build_foundry_module_payload())

    @app.get("/api/publishing/projects")
    async def api_publishing_list_projects(
        status: str | None = Query(default=None),
        project_type: str | None = Query(default=None),
    ) -> JSONResponse:
        """List publishing projects, optionally filtered by status or type."""
        pub = _publishing_or_503()
        projects = await asyncio.to_thread(pub._store.list_projects, status, project_type)
        return _json({
            "projects": [p.to_dict() for p in projects],
            "count": len(projects),
        })

    @app.post("/api/publishing/projects")
    async def api_publishing_create_project(request: Request) -> JSONResponse:
        """Create a new publishing project."""
        pub = _publishing_or_503()
        payload = await request.json()
        from .publishing_suite import _now_iso as _pub_now
        import uuid as _service_uuid
        now = _pub_now()
        project = PublishingProject(
            project_id=str(_service_uuid.uuid4()),
            project_type=str(payload.get("project_type", "book")),
            title=str(payload.get("title", "")),
            status=str(payload.get("status", "draft")),
            platform=str(payload.get("platform", "")),
            created_at=now,
            updated_at=now,
            published_at=str(payload.get("published_at", "")),
            url=str(payload.get("url", "")),
            description=str(payload.get("description", "")),
            tags=list(payload.get("tags", [])),
            revenue_tracking=bool(payload.get("revenue_tracking", False)),
            notes=str(payload.get("notes", "")),
        )
        await asyncio.to_thread(pub._store.save_project, project)
        _record_publish_history(
            actor_id="Chris",
            event_type="project-created",
            title="Create Draft Project",
            detail=f"Created draft publishing project {project.title.strip() or project.project_id}.",
            status_label="Draft Created",
            related_label=project.title.strip() or project.project_id,
            project_id=project.project_id,
        )
        return _json(project.to_dict(), status_code=201)

    @app.get("/api/publishing/projects/{project_id}")
    async def api_publishing_get_project(project_id: str) -> JSONResponse:
        """Get a single publishing project by ID."""
        pub = _publishing_or_503()
        project = await asyncio.to_thread(pub._store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return _json(project.to_dict())

    @app.get("/api/publishing/revenue")
    async def api_publishing_revenue_summary() -> JSONResponse:
        """Revenue summary from Sage — all streams, totals, attention flags."""
        pub = _publishing_or_503()
        summary = await asyncio.to_thread(pub.sage.get_revenue_summary)
        return _json(summary)

    @app.post("/api/publishing/revenue/streams")
    async def api_publishing_add_revenue_stream(request: Request) -> JSONResponse:
        """Add a new revenue stream."""
        pub = _publishing_or_503()
        payload = await request.json()
        import uuid as _service_uuid
        stream = RevenueStream(
            stream_id=str(_service_uuid.uuid4()),
            stream_type=str(payload.get("stream_type", "other")),
            source=str(payload.get("source", "")),
            project_id=str(payload.get("project_id", "")),
            monthly_estimate=float(payload.get("monthly_estimate", 0.0)),
            last_payment=float(payload.get("last_payment", 0.0)),
            last_payment_date=str(payload.get("last_payment_date", "")),
            currency=str(payload.get("currency", "USD")),
            notes=str(payload.get("notes", "")),
            active=bool(payload.get("active", True)),
            tracking_url=str(payload.get("tracking_url", "")),
        )
        await asyncio.to_thread(pub._store.save_revenue_stream, stream)
        return _json(stream.to_dict(), status_code=201)

    @app.get("/api/publishing/calendar")
    async def api_publishing_calendar(days: int = Query(default=14)) -> JSONResponse:
        """Upcoming content calendar items."""
        pub = _publishing_or_503()
        upcoming = await asyncio.to_thread(pub.calendar.get_upcoming, days)
        overdue = await asyncio.to_thread(pub.calendar.get_overdue)
        return _json({
            "upcoming": [i.to_dict() for i in upcoming],
            "overdue": [i.to_dict() for i in overdue],
            "upcoming_count": len(upcoming),
            "overdue_count": len(overdue),
        })

    @app.post("/api/publishing/calendar")
    async def api_publishing_add_calendar_item(request: Request) -> JSONResponse:
        """Add a content calendar item."""
        pub = _publishing_or_503()
        payload = await request.json()
        import uuid as _service_uuid
        item = ContentCalendarItem(
            item_id=str(_service_uuid.uuid4()),
            title=str(payload.get("title", "")),
            content_type=str(payload.get("content_type", "social_post")),
            platform=str(payload.get("platform", "")),
            planned_date=str(payload.get("planned_date", "")),
            status=str(payload.get("status", "idea")),
            project_id=str(payload.get("project_id", "")),
            notes=str(payload.get("notes", "")),
            assigned_agent=str(payload.get("assigned_agent", "")),
        )
        await asyncio.to_thread(pub.calendar.add_item, item)
        return _json(item.to_dict(), status_code=201)

    @app.get("/api/publishing/social/posts")
    async def api_publishing_social_posts(
        status: str | None = Query(default=None),
    ) -> JSONResponse:
        """List social posts (draft/scheduled by default)."""
        pub = _publishing_or_503()
        if status:
            posts = await asyncio.to_thread(pub._store.list_posts, status)
        else:
            posts = await asyncio.to_thread(pub._store.get_scheduled_posts)
        return _json({
            "posts": [p.to_dict() for p in posts],
            "count": len(posts),
        })

    @app.post("/api/publishing/social/posts")
    async def api_publishing_create_social_post(request: Request) -> JSONResponse:
        """Create a social post draft."""
        pub = _publishing_or_503()
        payload = await request.json()
        import uuid as _service_uuid
        post = SocialPost(
            post_id=str(_service_uuid.uuid4()),
            platform=str(payload.get("platform", "")),
            content=str(payload.get("content", "")),
            media_urls=list(payload.get("media_urls", [])),
            status=str(payload.get("status", "draft")),
            scheduled_at=str(payload.get("scheduled_at", "")),
            posted_at=str(payload.get("posted_at", "")),
            campaign_id=str(payload.get("campaign_id", "")),
            project_id=str(payload.get("project_id", "")),
            performance=dict(payload.get("performance", {})),
        )
        await asyncio.to_thread(pub._store.save_social_post, post)
        return _json(post.to_dict(), status_code=201)

    @app.get("/api/publishing/metrics")
    async def api_publishing_metrics() -> JSONResponse:
        """Sage analytics summary: publishing metrics and content performance."""
        pub = _publishing_or_503()
        pub_metrics = await asyncio.to_thread(pub.sage.get_publishing_metrics)
        content_perf = await asyncio.to_thread(pub.sage.get_content_performance)
        return _json({
            "publishing_metrics": pub_metrics,
            "content_performance": content_perf,
        })

    @app.post("/api/publishing/launch-plan")
    async def api_publishing_launch_plan(request: Request) -> JSONResponse:
        """Generate a Loki launch plan for a project."""
        pub = _publishing_or_503()
        payload = await request.json()
        project_id = str(payload.get("project_id", ""))
        project = await asyncio.to_thread(pub._store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        plan = await asyncio.to_thread(pub.loki.build_launch_plan, project)
        return _json(plan)

    @app.get("/api/publishing/status")
    async def api_publishing_status() -> JSONResponse:
        """Orchestrator dashboard status — quick summary for Already Working zone."""
        pub = _publishing_or_503()
        dashboard = await asyncio.to_thread(pub.get_dashboard_status)
        return _json(dashboard)

    # -----------------------------------------------------------------------
    # Epic 12: Workshop Copilot
    # -----------------------------------------------------------------------

    def _get_workshop_copilot():
        try:
            from .workshop_copilot import get_workshop
            return get_workshop()
        except Exception:
            return None

    def _workshop_copilot_or_503():
        copilot = _get_workshop_copilot()
        if copilot is None:
            raise HTTPException(status_code=503, detail="WorkshopCopilot not initialised")
        return copilot

    @app.get("/api/workshop/status")
    async def api_workshop_status() -> JSONResponse:
        """Daily workshop status — active prints, low stock, safety."""
        copilot = _workshop_copilot_or_503()
        result = await asyncio.to_thread(copilot.daily_workshop_check)
        return _json(result)

    @app.get("/api/workshop/projects")
    async def api_workshop_projects(status: str = "") -> JSONResponse:
        """List workshop projects, optionally filtered by status."""
        copilot = _workshop_copilot_or_503()
        projects = await asyncio.to_thread(
            copilot.store.list_projects, status if status else None
        )
        from dataclasses import asdict as _asdict
        return _json({"projects": [_asdict(p) for p in projects], "count": len(projects)})

    @app.post("/api/workshop/projects")
    async def api_workshop_create_project(request: Request) -> JSONResponse:
        """Create a new workshop project from a description."""
        body = await request.json()
        description = str(body.get("description", "")).strip()
        if not description:
            raise HTTPException(status_code=400, detail="description is required")
        constraints = body.get("constraints") or {}
        copilot = _workshop_copilot_or_503()
        project = await asyncio.to_thread(copilot.start_project, description, constraints)
        from dataclasses import asdict as _asdict
        return _json(_asdict(project))

    @app.get("/api/workshop/jobs")
    async def api_workshop_jobs() -> JSONResponse:
        """List active print jobs."""
        copilot = _workshop_copilot_or_503()
        jobs = await asyncio.to_thread(copilot.store.get_active_jobs)
        from dataclasses import asdict as _asdict
        return _json({"jobs": [_asdict(j) for j in jobs], "count": len(jobs)})

    @app.post("/api/workshop/jobs")
    async def api_workshop_log_job(request: Request) -> JSONResponse:
        """Log a new print job."""
        import uuid as _uuid
        from .workshop_copilot import PrintJob
        body = await request.json()
        job_id = str(body.get("job_id") or _uuid.uuid4())
        project_id = str(body.get("project_id", ""))
        machine = str(body.get("machine", "k2_pro"))
        file_name = str(body.get("file", ""))
        status = str(body.get("status", "queued"))
        job = PrintJob(
            job_id=job_id,
            project_id=project_id,
            machine=machine,
            file=file_name,
            status=status,
            started_at=str(body.get("started_at", "")),
            estimated_end=str(body.get("estimated_end", "")),
            material=str(body.get("material", "")),
            layer_height_mm=float(body.get("layer_height_mm", 0.0)),
            infill_percent=int(body.get("infill_percent", 0)),
            print_time_minutes=int(body.get("print_time_minutes", 0)),
            notes=str(body.get("notes", "")),
        )
        copilot = _workshop_copilot_or_503()
        await asyncio.to_thread(copilot.hank.log_print_job, job)
        from dataclasses import asdict as _asdict
        return _json(_asdict(job))

    @app.put("/api/workshop/jobs/{job_id}/status")
    async def api_workshop_update_job_status(job_id: str, request: Request) -> JSONResponse:
        """Update job status and optional notes."""
        body = await request.json()
        new_status = str(body.get("status", "")).strip()
        if not new_status:
            raise HTTPException(status_code=400, detail="status is required")
        notes = str(body.get("notes", ""))
        copilot = _workshop_copilot_or_503()
        updated = await asyncio.to_thread(
            copilot.hank.update_print_status, job_id, new_status, notes
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Job not found")
        return _json({"job_id": job_id, "status": new_status, "updated": True})

    @app.get("/api/workshop/materials")
    async def api_workshop_materials() -> JSONResponse:
        """Full materials inventory."""
        copilot = _workshop_copilot_or_503()
        materials = await asyncio.to_thread(copilot.rocket.get_inventory)
        from dataclasses import asdict as _asdict
        return _json({"materials": [_asdict(m) for m in materials], "count": len(materials)})

    @app.post("/api/workshop/materials")
    async def api_workshop_add_material(request: Request) -> JSONResponse:
        """Add or update a material in inventory."""
        import uuid as _uuid
        from .workshop_copilot import MaterialStock
        body = await request.json()
        material_id = str(body.get("material_id") or _uuid.uuid4())
        name = str(body.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        stock = MaterialStock(
            material_id=material_id,
            name=name,
            material_type=str(body.get("material_type", "pla")),
            brand=str(body.get("brand", "")),
            quantity_g=float(body.get("quantity_g", 0.0)),
            quantity_units=str(body.get("quantity_units", "g")),
            quantity_value=float(body.get("quantity_value", 0.0)),
            low_stock_threshold=float(body.get("low_stock_threshold", 200.0)),
            reorder_url=str(body.get("reorder_url", "")),
            notes=str(body.get("notes", "")),
        )
        copilot = _workshop_copilot_or_503()
        await asyncio.to_thread(copilot.rocket.add_material, stock)
        from dataclasses import asdict as _asdict
        return _json(_asdict(stock))

    @app.get("/api/workshop/materials/low-stock")
    async def api_workshop_low_stock() -> JSONResponse:
        """Materials below their reorder threshold."""
        copilot = _workshop_copilot_or_503()
        low = await asyncio.to_thread(copilot.rocket.get_low_stock_alerts)
        from dataclasses import asdict as _asdict
        reorders = []
        for mat in low:
            suggestion = copilot.rocket.suggest_reorder(mat)
            reorders.append({"material": _asdict(mat), "reorder": suggestion})
        return _json({"low_stock": reorders, "count": len(reorders)})

    @app.get("/api/workshop/machines/{machine_id}")
    async def api_workshop_machine(machine_id: str) -> JSONResponse:
        """Machine capabilities and design guidelines."""
        from .workshop_copilot import TonyAgent as _Tony, ForgeAgent as _ForgeRef
        machine_info = _Tony.MACHINE_CAPABILITIES.get(machine_id)
        if machine_info is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown machine: {machine_id}. "
                       f"Valid IDs: {list(_Tony.MACHINE_CAPABILITIES.keys())}",
            )
        design = _ForgeRef.DESIGN_GUIDELINES.get(machine_id, {})
        return _json({
            "machine_id": machine_id,
            "capabilities": machine_info,
            "design_guidelines": design,
        })

    @app.post("/api/workshop/design-check")
    async def api_workshop_design_check(request: Request) -> JSONResponse:
        """
        Design feasibility check.
        Body: {"machine": str, "dimensions_mm": [x, y, z], "material": str}
        """
        from .workshop_copilot import AntManAgent as _AntMan, ForgeAgent as _Forge
        body = await request.json()
        machine = str(body.get("machine", "")).strip()
        if not machine:
            raise HTTPException(status_code=400, detail="machine is required")
        dims_raw = body.get("dimensions_mm", [0, 0, 0])
        if not isinstance(dims_raw, (list, tuple)) or len(dims_raw) < 3:
            raise HTTPException(status_code=400, detail="dimensions_mm must be [x, y, z]")
        dims = tuple(float(d) for d in dims_raw[:3])
        material = str(body.get("material", ""))

        ant_man = _AntMan()
        forge = _Forge()

        fit = ant_man.check_fits_in_machine(dims, machine)
        design_notes = forge.get_design_notes(machine, material if material else None)

        return _json({
            "machine": machine,
            "dimensions_mm": {"x": dims[0], "y": dims[1], "z": dims[2]},
            "material": material,
            "fit_check": fit,
            "design_notes": design_notes,
        })

    @app.post("/api/workshop/scale")
    async def api_workshop_scale(request: Request) -> JSONResponse:
        """
        Scale calculator.
        Body: {"original_mm": float, "target_mm": float}
        """
        from .workshop_copilot import AntManAgent as _AntMan
        body = await request.json()
        original_mm = float(body.get("original_mm", 0))
        target_mm = float(body.get("target_mm", 0))
        if original_mm <= 0 or target_mm <= 0:
            raise HTTPException(status_code=400, detail="original_mm and target_mm must be > 0")
        ant_man = _AntMan()
        result = ant_man.calculate_scale(original_mm, target_mm)
        return _json(result)

    # ------------------------------------------------------------------
    # Epic 15: Growth Intelligence API
    # ------------------------------------------------------------------

    def _get_growth():
        try:
            from .growth_intelligence import get_growth
            return get_growth()
        except Exception:
            return None

    def _growth_or_503():
        g = _get_growth()
        if g is None:
            raise HTTPException(status_code=503, detail="GrowthIntelligence not initialised")
        return g

    @app.get("/api/growth/snapshot")
    async def api_growth_snapshot() -> JSONResponse:
        """Full growth dashboard — learning, relationships, occasions, health."""
        g = _growth_or_503()
        result = await asyncio.to_thread(g.get_dashboard_status)
        return _json(result)

    @app.get("/api/growth/learning")
    async def api_growth_learning(status: str = "") -> JSONResponse:
        """Reading list, optionally filtered by status."""
        from dataclasses import asdict as _asdict
        g = _growth_or_503()
        items = await asyncio.to_thread(g.nova.get_reading_list, status if status else None)
        return _json({"items": [_asdict(i) for i in items], "count": len(items)})

    @app.post("/api/growth/learning")
    async def api_growth_add_learning(request: Request) -> JSONResponse:
        """Add a new learning item to the list."""
        import uuid as _uuid
        from .growth_intelligence import LearningItem
        from dataclasses import asdict as _asdict
        body = await request.json()
        g = _growth_or_503()
        item = LearningItem(
            item_id=str(body.get("item_id") or _uuid.uuid4()),
            title=str(body.get("title", "")).strip(),
            item_type=str(body.get("item_type", "book")),
            topic=str(body.get("topic", "general")),
            status=str(body.get("status", "want_to")),
            source=str(body.get("source", "")),
            url=str(body.get("url", "")),
            notes=str(body.get("notes", "")),
            started_at=str(body.get("started_at", "")),
            completed_at=str(body.get("completed_at", "")),
            rating=int(body.get("rating", 0)),
            key_takeaway=str(body.get("key_takeaway", "")),
            recommended_by=str(body.get("recommended_by", "")),
        )
        if not item.title:
            raise HTTPException(status_code=400, detail="title is required")
        await asyncio.to_thread(g.nova.add_learning_item, item)
        return _json(_asdict(item), status_code=201)

    @app.put("/api/growth/learning/{item_id}/complete")
    async def api_growth_complete_learning(item_id: str, request: Request) -> JSONResponse:
        """Mark a learning item as complete."""
        body = await request.json()
        g = _growth_or_503()
        rating = int(body.get("rating", 5))
        takeaway = str(body.get("takeaway", ""))
        await asyncio.to_thread(g.nova.log_completion, item_id, rating, takeaway)
        return _json({"item_id": item_id, "status": "completed"})

    @app.get("/api/growth/relationships")
    async def api_growth_relationships(relationship_type: str = "") -> JSONResponse:
        """Contact list, optionally filtered by type."""
        from dataclasses import asdict as _asdict
        g = _growth_or_503()
        contacts = await asyncio.to_thread(
            g.gamora.list_contacts, relationship_type if relationship_type else None
        )
        return _json({"contacts": [_asdict(c) for c in contacts], "count": len(contacts)})

    @app.post("/api/growth/relationships")
    async def api_growth_add_relationship(request: Request) -> JSONResponse:
        """Add a new relationship contact."""
        import uuid as _uuid
        from .growth_intelligence import Relationship
        from dataclasses import asdict as _asdict
        body = await request.json()
        g = _growth_or_503()
        rel = Relationship(
            contact_id=str(body.get("contact_id") or _uuid.uuid4()),
            name=str(body.get("name", "")).strip(),
            relationship_type=str(body.get("relationship_type", "friend")),
            last_contact=str(body.get("last_contact", "")),
            contact_frequency=str(body.get("contact_frequency", "monthly")),
            notes=str(body.get("notes", "")),
            birthday=str(body.get("birthday", "")),
            anniversary=str(body.get("anniversary", "")),
            shared_interests=list(body.get("shared_interests", [])),
            open_threads=list(body.get("open_threads", [])),
            tags=list(body.get("tags", [])),
            is_family=bool(body.get("is_family", False)),
        )
        if not rel.name:
            raise HTTPException(status_code=400, detail="name is required")
        await asyncio.to_thread(g.gamora.add_contact, rel)
        return _json(_asdict(rel), status_code=201)

    @app.post("/api/growth/relationships/{contact_id}/log-contact")
    async def api_growth_log_contact(contact_id: str, request: Request) -> JSONResponse:
        """Log that Chris reached out to a contact today."""
        body = await request.json()
        g = _growth_or_503()
        notes = str(body.get("notes", ""))
        await asyncio.to_thread(g.gamora.log_contact, contact_id, notes)
        from datetime import datetime, timezone as _tz
        return _json({"contact_id": contact_id, "logged_at": datetime.now(_tz.utc).isoformat()})

    @app.get("/api/growth/occasions")
    async def api_growth_occasions(days: int = 30) -> JSONResponse:
        """Upcoming occasions within the given number of days."""
        g = _growth_or_503()
        occasions = await asyncio.to_thread(g.agatha.get_upcoming_occasions, days)
        return _json({"occasions": occasions, "count": len(occasions)})

    @app.post("/api/growth/occasions")
    async def api_growth_add_occasion(request: Request) -> JSONResponse:
        """Add a new occasion."""
        import uuid as _uuid
        from .growth_intelligence import Occasion
        from dataclasses import asdict as _asdict
        body = await request.json()
        g = _growth_or_503()
        occ = Occasion(
            occasion_id=str(body.get("occasion_id") or _uuid.uuid4()),
            title=str(body.get("title", "")).strip(),
            occasion_type=str(body.get("occasion_type", "custom")),
            contact_id=str(body.get("contact_id", "")),
            date=str(body.get("date", "")),
            recurring=bool(body.get("recurring", True)),
            advance_notice_days=int(body.get("advance_notice_days", 14)),
            gift_ideas=list(body.get("gift_ideas", [])),
            gift_history=list(body.get("gift_history", [])),
            notes=str(body.get("notes", "")),
            active=bool(body.get("active", True)),
        )
        if not occ.title:
            raise HTTPException(status_code=400, detail="title is required")
        await asyncio.to_thread(g.agatha.add_occasion, occ)
        return _json(_asdict(occ), status_code=201)

    @app.get("/api/growth/signals")
    async def api_growth_signals(limit: int = 10) -> JSONResponse:
        """Recent unread world signals from Spider-Man."""
        from dataclasses import asdict as _asdict
        g = _growth_or_503()
        signals = await asyncio.to_thread(g.spider_man.get_signals, limit)
        return _json({"signals": [_asdict(s) for s in signals], "count": len(signals)})

    @app.get("/api/growth/health")
    async def api_growth_health(actor_id: str = "chris") -> JSONResponse:
        """Thor's health snapshot for the actor."""
        g = _growth_or_503()
        snapshot = await asyncio.to_thread(g.thor.get_health_snapshot, actor_id)
        return _json(snapshot)

    @app.post("/api/growth/health/log")
    async def api_growth_log_health(request: Request) -> JSONResponse:
        """Log a health/fitness activity."""
        import uuid as _uuid
        from .growth_intelligence import HealthLog
        from dataclasses import asdict as _asdict
        body = await request.json()
        g = _growth_or_503()
        log = HealthLog(
            log_id=str(body.get("log_id") or _uuid.uuid4()),
            actor_id=str(body.get("actor_id", "chris")),
            date=str(body.get("date", "")),
            activity_type=str(body.get("activity_type", "other")),
            duration_minutes=int(body.get("duration_minutes", 0)),
            intensity=str(body.get("intensity", "moderate")),
            notes=str(body.get("notes", "")),
            steps=int(body.get("steps", 0)),
            calories_active=int(body.get("calories_active", 0)),
            heart_rate_avg=int(body.get("heart_rate_avg", 0)),
        )
        await asyncio.to_thread(g.thor.log_activity, log)
        return _json(_asdict(log), status_code=201)

    @app.get("/api/growth/briefing-items")
    async def api_growth_briefing_items() -> JSONResponse:
        """All growth items to surface in the morning briefing."""
        g = _growth_or_503()
        items = await asyncio.to_thread(g.get_briefing_items)
        return _json({"items": items, "count": len(items)})

    # ------------------------------------------------------------------
    # Apple native API (Epic 14)
    # ------------------------------------------------------------------
    _register_apple_api(app, runtime)

    # ------------------------------------------------------------------
    # LLM Gateway API
    # ------------------------------------------------------------------

    @app.get("/api/gateway/status")
    async def api_gateway_status() -> JSONResponse:
        """Health and diagnostics for the LLM gateway."""
        gw = _get_gateway()
        if gw is None:
            return JSONResponse(
                {"error": "LLM gateway not initialised", "available": False},
                status_code=503,
            )
        status = await asyncio.to_thread(gw.get_status)
        return JSONResponse({"available": True, **status})

    @app.post("/api/gateway/test")
    async def api_gateway_test(request: Request) -> JSONResponse:
        """Test the LLM gateway with a message. Body: {message, task_type}."""
        gw = _get_gateway()
        if gw is None:
            return JSONResponse(
                {"error": "LLM gateway not initialised"},
                status_code=503,
            )
        try:
            body = await request.json()
        except Exception:
            body = {}
        message = str(body.get("message", "Hello, JARVIS.")).strip() or "Hello, JARVIS."
        task_type = str(body.get("task_type", "converse")).strip() or "converse"

        from .llm_gateway import LLMMessage

        def _run() -> dict:
            resp = gw.complete(
                messages=[LLMMessage("user", message)],
                task_type=task_type,
                agent_id="gateway-test",
            )
            return {
                "text": resp.text,
                "model_used": resp.model_used,
                "backend": resp.backend,
                "task_type": resp.task_type,
                "latency_ms": resp.latency_ms,
                "prompt_tokens": resp.prompt_tokens,
                "completion_tokens": resp.completion_tokens,
                "confidence": resp.confidence,
                "escalated": resp.escalated,
                "error": resp.error,
            }

        result = await asyncio.to_thread(_run)
        status_code = 200 if not result["error"] else 502
        return JSONResponse(result, status_code=status_code)

    # ── Home Intelligence API ─────────────────────────────────────────────────

    @app.get("/api/home/dashboard")
    async def api_home_dashboard() -> JSONResponse:
        """Full home intelligence dashboard — projects, tasks, email, calendar."""
        db = _get_home_db()
        if db is None:
            return _json({"available": False, "error": "Home DB not initialised"})
        try:
            result = await asyncio.to_thread(db.get_dashboard_data)
        except Exception as exc:
            return _json({"available": False, "error": f"Home dashboard unavailable: {exc}"})
        result["available"] = True
        return _json(result)

    # ── Projects ──────────────────────────────────────────────────────────────

    @app.get("/api/home/projects")
    async def api_home_projects(
        status: str = Query(default=""),
        track: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        projects = await asyncio.to_thread(
            db.list_projects,
            status or None,
            track or None,
        )
        return _json({"projects": projects, "total": len(projects)})

    @app.post("/api/home/projects")
    async def api_home_projects_create(request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        project = await asyncio.to_thread(db.create_project, data)
        return _json(project)

    @app.get("/api/home/projects/{project_id}")
    async def api_home_project_get(project_id: str) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        project = await asyncio.to_thread(db.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return _json(project)

    @app.patch("/api/home/projects/{project_id}")
    async def api_home_project_update(project_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        project = await asyncio.to_thread(db.update_project, project_id, data)
        return _json(project)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @app.get("/api/home/tasks")
    async def api_home_tasks(
        project_id: str = Query(default=""),
        status: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        tasks = await asyncio.to_thread(
            db.list_tasks,
            project_id or None,
            status or None,
        )
        return _json({"tasks": tasks, "total": len(tasks)})

    @app.get("/api/home/tasks/overdue")
    async def api_home_tasks_overdue() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        tasks = await asyncio.to_thread(db.get_overdue_tasks)
        return _json({"tasks": tasks, "total": len(tasks)})

    @app.get("/api/home/tasks/today")
    async def api_home_tasks_today() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        tasks = await asyncio.to_thread(db.get_tasks_due_today)
        return _json({"tasks": tasks, "total": len(tasks)})

    @app.post("/api/home/tasks")
    async def api_home_tasks_create(request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        task = await asyncio.to_thread(db.create_task, data)
        return _json(task)

    @app.patch("/api/home/tasks/{task_id}")
    async def api_home_task_update(task_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        task = await asyncio.to_thread(db.update_task, task_id, data)
        return _json(task)

    @app.post("/api/home/tasks/{task_id}/complete")
    async def api_home_task_complete(task_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        task = await asyncio.to_thread(db.complete_task, task_id)
        return _json(task)

    # ── Email ─────────────────────────────────────────────────────────────────

    @app.get("/api/home/email")
    async def api_home_email(
        unread_only: bool = Query(default=False),
        limit: int = Query(default=50),
        source: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        emails = await asyncio.to_thread(
            db.list_emails,
            source or None,
            unread_only,
            limit,
        )
        stats = await asyncio.to_thread(db.get_email_stats)
        return _json({"emails": emails, "total": len(emails), "stats": stats})

    @app.get("/api/home/email/stats")
    async def api_home_email_stats() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        stats = await asyncio.to_thread(db.get_email_stats)
        return _json(stats)

    @app.post("/api/home/email/{email_id}/read")
    async def api_home_email_mark_read(email_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        await asyncio.to_thread(db.mark_email_read, email_id)
        return _json({"ok": True})

    # ── Calendar ──────────────────────────────────────────────────────────────

    @app.get("/api/home/calendar/today")
    async def api_home_calendar_today() -> JSONResponse:
        inbox = _get_unified_inbox()
        if inbox is None:
            db = _get_home_db()
            if db is None:
                raise HTTPException(status_code=503, detail="Home intelligence not initialised")
            events = await asyncio.to_thread(db.get_todays_events)
            return _json({"events": events, "total": len(events)})
        agenda = await asyncio.to_thread(inbox.get_todays_agenda)
        return _json(agenda)

    @app.get("/api/home/calendar/upcoming")
    async def api_home_calendar_upcoming(days: int = Query(default=7)) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        events = await asyncio.to_thread(db.get_upcoming_events, days)
        return _json({"events": events, "total": len(events)})

    @app.get("/api/home/calendar")
    async def api_home_calendar(
        start: str = Query(default=""),
        end: str = Query(default=""),
        source: str = Query(default=""),
    ) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        from datetime import datetime, timezone, timedelta
        if not start:
            start = datetime.now(timezone.utc).isoformat()
        if not end:
            end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        events = await asyncio.to_thread(db.list_calendar_events, start, end, source or None)
        return _json({"events": events, "total": len(events)})

    # ── Sync ──────────────────────────────────────────────────────────────────

    @app.post("/api/home/sync")
    async def api_home_sync_all(request: Request) -> JSONResponse:
        """Trigger a full sync of all email and calendar sources."""
        inbox = _get_unified_inbox()
        if inbox is None:
            raise HTTPException(status_code=503, detail="Unified inbox not initialised")
        result = await asyncio.to_thread(inbox.sync_all)
        return _json(result)

    @app.post("/api/home/sync/{source}")
    async def api_home_sync_source(source: str, request: Request) -> JSONResponse:
        """Trigger sync for a specific source: gmail|outlook|google_calendar|outlook_calendar|cozi"""
        inbox = _get_unified_inbox()
        if inbox is None:
            raise HTTPException(status_code=503, detail="Unified inbox not initialised")
        sync_map = {
            "gmail": inbox.sync_gmail,
            "outlook": inbox.sync_outlook_email,
            "google_calendar": inbox.sync_google_calendar,
            "outlook_calendar": inbox.sync_outlook_calendar,
            "cozi": inbox.sync_cozi,
        }
        fn = sync_map.get(source)
        if fn is None:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
        result = await asyncio.to_thread(fn)
        return _json(result)

    @app.get("/api/home/sync/status")
    async def api_home_sync_status() -> JSONResponse:
        """Return last sync time for each source."""
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        states = await asyncio.to_thread(db.get_all_sync_states)
        return _json({"sources": states})

    # ── Signal Processing ────────────────────────────────────────────────────

    @app.post("/api/home/signals/process")
    async def api_home_signals_process(request: Request) -> JSONResponse:
        """Run the signal router to classify unprocessed emails into project signals."""
        router = _get_signal_router()
        if router is None:
            raise HTTPException(status_code=503, detail="Signal router not initialised")
        result = await asyncio.to_thread(router.run_full_scan)
        return _json(result)

    @app.get("/api/home/signals/unclassified")
    async def api_home_signals_unclassified() -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        signals = await asyncio.to_thread(db.list_unclassified_signals, 50)
        return _json({"signals": signals, "total": len(signals)})

    # ── Value Log ─────────────────────────────────────────────────────────────

    @app.post("/api/home/projects/{project_id}/value")
    async def api_home_log_value(project_id: str, request: Request) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        data = await request.json()
        entry = await asyncio.to_thread(
            db.log_value,
            project_id,
            float(data.get("amount", 0)),
            data.get("type", "savings"),
            data.get("description"),
            data.get("source", "manual"),
        )
        return _json(entry)

    @app.get("/api/home/value/summary")
    async def api_home_value_summary(project_id: str = Query(default="")) -> JSONResponse:
        db = _get_home_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Home DB not initialised")
        summary = await asyncio.to_thread(db.get_value_summary, project_id or None)
        return _json(summary)

    # ── Forge — Object-to-Manufacturing Workspace ─────────────────────────────
    # Lazy-initialised singletons (module-level would run before runtime exists)

    _forge_store_instance: list = [None]  # mutable container for lazy init
    _forge_support_instance: list = [None]

    def _get_forge_store():
        if _forge_store_instance[0] is None:
            try:
                from .forge import ForgeStore
                _forge_store_instance[0] = ForgeStore()
            except Exception:
                return None
        return _forge_store_instance[0]

    def _get_forge_support():
        if _forge_support_instance[0] is None:
            try:
                from .forge import ForgeSupport
                store = _get_forge_store()
                if store is None:
                    return None
                _forge_support_instance[0] = ForgeSupport(
                    store,
                    openai_client=runtime.openai_client,
                    workshop_support=runtime.workshop_support,
                )
            except Exception:
                return None
        return _forge_support_instance[0]

    def _forge_store_or_503():
        s = _get_forge_store()
        if s is None:
            raise HTTPException(status_code=503, detail="Forge store not initialised")
        return s

    def _forge_support_or_503():
        s = _get_forge_support()
        if s is None:
            raise HTTPException(status_code=503, detail="Forge support not initialised")
        return s

    def _forge_bridge_root() -> Path:
        store = _get_forge_store()
        root = getattr(store, "root", None)
        if isinstance(root, Path):
            root.mkdir(parents=True, exist_ok=True)
            return root
        fallback = Path.home() / ".jarvis" / "forge"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    def _forge_bridge_config_path() -> Path:
        return _forge_bridge_root() / "bridge_config.json"

    def _forge_load_bridge_config() -> dict[str, Any]:
        path = _forge_bridge_config_path()
        if not path.exists():
            return {
                "export_folder": "",
                "wow_install_path": "",
                "blender_path": "",
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return {
                    "export_folder": str(payload.get("export_folder") or ""),
                    "wow_install_path": str(payload.get("wow_install_path") or ""),
                    "blender_path": str(payload.get("blender_path") or ""),
                }
        except Exception:
            pass
        return {
            "export_folder": "",
            "wow_install_path": "",
            "blender_path": "",
        }

    def _forge_save_bridge_config(payload: dict[str, Any]) -> dict[str, Any]:
        config = {
            "export_folder": str(payload.get("export_folder") or "").strip(),
            "wow_install_path": str(payload.get("wow_install_path") or "").strip(),
            "blender_path": str(payload.get("blender_path") or "").strip(),
        }
        atomic_write_json(_forge_bridge_config_path(), config)
        return config

    def _forge_resolve_project_file(store, project_id: str, filename: str) -> Path | None:
        cleaned = str(filename or "").strip()
        if not cleaned:
            return None
        uploads_dir = store.uploads_dir(project_id)
        models_dir = store.models_dir(project_id)
        for base in (uploads_dir, models_dir):
            candidate = (base / cleaned).resolve()
            try:
                candidate.relative_to(base.resolve())
            except ValueError:
                continue
            if candidate.exists():
                return candidate
        return None

    def _forge_register_model_artifact(
        store,
        project_id: str,
        *,
        filename: str,
        method: str,
        title: str,
        notes: str,
        source_filename: str = "",
    ) -> dict[str, Any]:
        path = store.models_dir(project_id) / filename
        suffix = path.suffix.lower().lstrip(".") or "unknown"
        model_dict = {
            "model_id": secrets.token_hex(8),
            "version": 1,
            "title": title,
            "method": method,
            "filename": filename,
            "format": suffix,
            "file_size_bytes": path.stat().st_size if path.exists() else 0,
            "bounding_box_mm": {},
            "is_manifold": None,
            "was_repaired": False,
            "repair_notes": "",
            "print_readiness": {},
            "created_at": _forge_now(),
            "notes": notes,
            "source_filename": source_filename,
        }
        store.add_generated_model(project_id, model_dict)
        store.set_status(project_id, "model_ready", f"{method} artifact added")
        return model_dict

    def _forge_module_project_summary(project: dict[str, Any]) -> dict[str, Any]:
        capture_sessions = list(project.get("capture_sessions") or [])
        generated_models = list(project.get("generated_models") or [])
        measurements = list(project.get("measurements") or [])
        latest_capture = capture_sessions[-1] if capture_sessions else {}
        latest_model = generated_models[-1] if generated_models else {}
        return {
            "id": project.get("id"),
            "title": project.get("title") or "Untitled Forge Project",
            "status": project.get("status") or "idea",
            "updated_at": project.get("updated_at") or project.get("created_at") or "",
            "measurement_count": len(measurements),
            "capture_frame_count": len(list(latest_capture.get("frames") or [])),
            "model_count": len(generated_models),
            "latest_model": latest_model.get("filename") or "",
            "description": project.get("description") or "",
        }

    def _forge_build_module_payload(project_id: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "generated_at": _forge_now(),
            "available": True,
            "status": "Wired",
            "summary": "Forge is loading live project, fabrication, and bridge state.",
            "availability_notes": [],
            "projects": [],
            "active_project_id": "",
            "active_project": None,
            "capture": {},
            "council": {},
            "pipeline": {},
            "memory": {},
            "manufacturing": {},
            "systems": {},
            "wow": {},
            "convert": {},
            "proof_paths": {
                "module_route": "/forge",
                "module_api": "/api/forge/module",
                "projects_api": "/api/forge/projects",
                "project_api": "/api/forge/projects/{project_id}",
                "generate_api": "/api/forge/projects/{project_id}/generate",
                "inspect_api": "/api/forge/projects/{project_id}/inspect",
                "slice_api": "/api/forge/projects/{project_id}/slice",
                "timeline_api": "/api/forge/projects/{project_id}/timeline",
                "wow_status_api": "/api/forge/wow/status",
                "convert_format_api": "/api/forge/convert/format",
            },
        }
        store = _get_forge_store()
        if store is None:
            payload["available"] = False
            payload["status"] = "Unavailable"
            payload["summary"] = "Forge storage is not available in this runtime."
            payload["availability_notes"].append("Forge store not initialised.")
            return payload

        project_index = list(store.list_projects(include_archived=False))
        project_records: list[dict[str, Any]] = []
        for item in project_index:
            project = store.get_project(str(item.get("id") or ""))
            if project:
                project_records.append(project)
        project_records.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        payload["projects"] = [_forge_module_project_summary(item) for item in project_records]

        active_project = None
        if project_id:
            active_project = next((item for item in project_records if str(item.get("id")) == str(project_id)), None)
        if active_project is None and project_records:
            active_project = project_records[0]
        payload["active_project"] = active_project
        payload["active_project_id"] = str(active_project.get("id") or "") if active_project else ""

        wow_config = _forge_load_bridge_config()
        export_folder = Path(str(wow_config.get("export_folder") or "")).expanduser() if wow_config.get("export_folder") else None
        wow_models: list[dict[str, Any]] = []
        if export_folder and export_folder.exists():
            for candidate in sorted(export_folder.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
                if not candidate.is_file():
                    continue
                if candidate.suffix.lower() not in {".glb", ".obj", ".stl", ".3mf", ".m2"}:
                    continue
                wow_models.append(
                    {
                        "filename": candidate.name,
                        "size_bytes": candidate.stat().st_size,
                        "modified_at": datetime.fromtimestamp(candidate.stat().st_mtime, timezone.utc).isoformat(),
                    }
                )

        payload["wow"] = {
            "config": wow_config,
            "export_folder_exists": bool(export_folder and export_folder.exists()),
            "wow_install_found": bool(wow_config.get("wow_install_path") and Path(str(wow_config.get("wow_install_path"))).expanduser().exists()),
            "blender_found": bool(wow_config.get("blender_path") and Path(str(wow_config.get("blender_path"))).expanduser().exists()),
            "models": wow_models[:24],
            "model_count": len(wow_models),
            "setup_tip": "Configure an export folder to scan wow.export output, then import a model into the active Forge project.",
        }
        payload["convert"] = {
            "available_formats": ["glb", "obj", "stl", "ply"],
            "repair_supported": True,
            "scale_supported": True,
            "notes": "Conversion, repair, and scaling operate on real project files. Some formats still depend on trimesh export support.",
        }

        if active_project is None:
            payload["summary"] = "Forge is live, but there is no active project yet."
            payload["status"] = "Useful"
            payload["availability_notes"].append("Create or load a Forge project to activate the desktop workflow.")
            payload["systems"] = {
                "environments": [
                    {"title": "Garage Systems", "copy": "Mounts, charging, tools, and storage that reduce daily friction."},
                    {"title": "Home Organization", "copy": "Physical products that tidy, protect, and improve movement."},
                    {"title": "Office & Workspaces", "copy": "Printer stands, cable paths, desks, and production rigs."},
                    {"title": "Family Command", "copy": "Support the household with systems that actually get used."},
                    {"title": "Creator Rigs", "copy": "Camera handles, shelves, docks, and modular setups."},
                    {"title": "Mobile & Vehicle", "copy": "Travel adapters, mounts, and in-motion utility pieces."},
                ],
                "recent_projects": payload["projects"],
            }
            return payload

        support = _get_forge_support()
        measurements = list(active_project.get("measurements") or [])
        capture_sessions = list(active_project.get("capture_sessions") or [])
        generated_models = list(active_project.get("generated_models") or [])
        slices = list(active_project.get("slices") or [])
        approvals = list(active_project.get("approvals") or [])
        timeline = list(store.read_timeline(str(active_project.get("id"))))
        latest_capture = capture_sessions[-1] if capture_sessions else {}
        latest_model = generated_models[-1] if generated_models else {}
        latest_slice = slices[-1] if slices else {}
        latest_readiness = latest_model.get("print_readiness") if isinstance(latest_model.get("print_readiness"), dict) else {}

        if support is not None and latest_capture:
            try:
                capture_status = support.capture_completeness(latest_capture)
            except Exception as exc:
                capture_status = {"ready_to_model": False, "missing_views": [], "error": str(exc)}
                payload["availability_notes"].append(f"Capture completeness partial: {exc}")
        else:
            capture_status = {
                "ready_to_model": bool(latest_capture),
                "missing_views": [],
                "geometry_confidence": latest_capture.get("confidence", {}).get("geometry", "low"),
                "scale_confidence": latest_capture.get("confidence", {}).get("scale", "low"),
                "print_readiness": latest_capture.get("confidence", {}).get("print_readiness", "not_ready"),
                "required_count": len(list(latest_capture.get("frames") or [])),
                "required_total": 5,
            }

        readiness_ok = bool(latest_readiness.get("ok") and latest_readiness.get("printable"))
        geometry_conf = str(capture_status.get("geometry_confidence") or "low").lower()
        scale_conf = str(capture_status.get("scale_confidence") or "low").lower()
        confirmed_count = len([item for item in measurements if item.get("confirmed")])
        total_measurements = len(measurements)
        frame_count = len(list(latest_capture.get("frames") or []))
        model_count = len(generated_models)

        def _confidence_score(base: int, extra: int = 0) -> int:
            return max(12, min(99, base + extra))

        option_scores = [
            {
                "option": "Option A",
                "label": "Strongest",
                "score": _confidence_score(40 + confirmed_count * 8 + (12 if readiness_ok else 0)),
                "copy": "Favors retained dimensions, print readiness, and structural confidence from the active artifact.",
            },
            {
                "option": "Option B",
                "label": "Fastest",
                "score": _confidence_score(30 + frame_count * 10 + (10 if model_count else 0)),
                "copy": "Optimizes for getting to the next printable iteration with the current capture and model history.",
            },
            {
                "option": "Option C",
                "label": "Cleanest",
                "score": _confidence_score(28 + total_measurements * 9 + (10 if geometry_conf == "high" else 0)),
                "copy": "Rewards clarity of constraints, fewer unknowns, and cleaner installation logic in the brief.",
            },
            {
                "option": "Option D",
                "label": "Adjustable",
                "score": _confidence_score(24 + len(active_project.get("assumptions") or []) * 5 + (14 if scale_conf in {"medium", "high"} else 0)),
                "copy": "Keeps flexibility where the environment or downstream install still calls for adaptation.",
            },
        ]

        factor_items = [
            f"{total_measurements} measured dimensions",
            f"{confirmed_count} confirmed constraint{'' if confirmed_count == 1 else 's'}",
            f"{frame_count} capture frame{'' if frame_count == 1 else 's'}",
            f"{model_count} generated model{'' if model_count == 1 else 's'}",
            readiness_ok and "Printable artifact available" or "Printability still needs confirmation",
            latest_slice and "Slice package has been staged" or "No slice report staged yet",
            approvals and f"{len(approvals)} approval record{'s' if len(approvals) != 1 else ''}" or "Approval history still empty",
            latest_model.get("format") and f"Current model format: {str(latest_model.get('format')).upper()}" or "No active model format yet",
        ]

        pipeline_stages = [
            {"title": "CAD", "status": "Captured" if active_project.get("title") else "Waiting"},
            {"title": "Mesh Repair", "status": readiness_ok and "Ready" or (latest_model and "Validate" or "Waiting")},
            {"title": "Optimize", "status": model_count and "Refine" or "Waiting"},
            {"title": "Slice & Sim", "status": latest_slice and "Staged" or "Stage"},
            {"title": "Validate", "status": latest_readiness and "Inspect" or "Inspect"},
            {"title": "Package", "status": approvals and "Approved" or "Approve"},
        ]

        manufacture_plan = [
            {
                "title": "3D Print Prototype",
                "copy": latest_model and "Use the active artifact to validate fit, orientation, and support strategy on the fastest loop." or "Generate or upload a model first so the prototype lane has something real to evaluate.",
            },
            {
                "title": "Field Test",
                "copy": confirmed_count and "Confirmed measurements and captured context now support a meaningful fit and use-case test." or "Add confirmed dimensions before trusting a field test result.",
            },
            {
                "title": "Finalize Design",
                "copy": latest_readiness and "Inspection, repair, and scaling data stay attached so the design can cross fabrication methods cleanly." or "Run inspection so downstream manufacture is based on the real artifact, not the mockup shell.",
            },
        ]

        bbox = latest_model.get("bounding_box_mm") if isinstance(latest_model.get("bounding_box_mm"), dict) else {}
        volume_mm3 = latest_readiness.get("volume_mm3") if isinstance(latest_readiness, dict) else None
        estimate_rows = [
            {
                "title": "3D Print (In-House)",
                "copy": (
                    f"BBox {bbox.get('x', '—')} × {bbox.get('y', '—')} × {bbox.get('z', '—')} mm."
                    if bbox else
                    "Fastest path to prototype and the tightest feedback loop for fit adjustments."
                ),
            },
            {
                "title": "CNC Machining",
                "copy": volume_mm3 and f"Model volume: {round(float(volume_mm3), 1)} mm³. CNC becomes more relevant when finish and material matter." or "Higher precision and material durability when the geometry and volumes warrant it.",
            },
            {
                "title": "Batch Production",
                "copy": approvals and "Approval history exists, which makes cost/volume comparison worth exploring." or "Use once the design is stable and the cost curve justifies a wider run.",
            },
        ]

        learn_rows = []
        if confirmed_count:
            learn_rows.append(
                {
                    "title": "Confirmed dimensions are accumulating",
                    "copy": f"{confirmed_count} confirmed dimension(s) now anchor the brief in real-world fit instead of assumptions.",
                }
            )
        if latest_capture:
            learn_rows.append(
                {
                    "title": "Capture posture improved",
                    "copy": f"{frame_count} frame(s) are attached to the latest session, which sharpens geometry and scale reasoning.",
                }
            )
        if latest_readiness:
            learn_rows.append(
                {
                    "title": "Inspection memory retained",
                    "copy": latest_readiness.get("repair_notes") or "The latest model already carries inspection state, so the next build step starts with evidence instead of guesswork.",
                }
            )
        if latest_slice:
            learn_rows.append(
                {
                    "title": "Slice staging is now remembered",
                    "copy": f"Printer {latest_slice.get('printer_id') or 'unknown'} · material {latest_slice.get('material') or 'unknown'} · status {latest_slice.get('status') or 'staged'}.",
                }
            )
        if not learn_rows:
            learn_rows.append(
                {
                    "title": "Waiting for stronger signal",
                    "copy": "Measurements, council outputs, repairs, and approvals will summarize here once the project is loaded.",
                }
            )

        memory_rows = []
        for idx, model in enumerate(reversed(generated_models[-4:]), start=1):
            memory_rows.append(
                {
                    "title": f"Model revision {idx}",
                    "copy": f"{model.get('filename') or 'Generated model'} · {model.get('method') or 'forge'} · {model.get('created_at') or ''}",
                }
            )
        for idx, session in enumerate(reversed(capture_sessions[-2:]), start=1):
            memory_rows.append(
                {
                    "title": f"Capture session {idx}",
                    "copy": f"{len(list(session.get('frames') or []))} frame(s) · {session.get('created_at') or ''}",
                }
            )
        if not memory_rows:
            memory_rows.append(
                {
                    "title": "No revisions yet",
                    "copy": "Once the project starts generating captures, models, and inspections, they will appear here.",
                }
            )

        printer_host = str(os.environ.get("JARVIS_FORGE_MOONRAKER_HOST") or "").strip()
        printer_status: dict[str, Any] = {}
        if support is not None and printer_host:
            try:
                printer_status = support.moonraker_status(printer_host)
            except Exception as exc:
                printer_status = {"available": False, "error": str(exc)}
        else:
            printer_status = {
                "available": False,
                "error": "Printer host not configured.",
            }
            if not printer_host:
                payload["availability_notes"].append("Printer telemetry is unavailable because JARVIS_FORGE_MOONRAKER_HOST is not configured.")

        payload["capture"] = capture_status
        payload["council"] = {
            "scores": option_scores,
            "factors": factor_items,
            "stress_copy_top": latest_model.get("filename") and f"Current model: {latest_model.get('filename')}" or "Use the Council when you want the review to feed directly into model generation.",
            "stress_copy": latest_model.get("filename") and "The loaded artifact becomes the thing the council can challenge for stress, fit, failure points, and install logic." or "Bring a design brief or uploaded model here and let the Council reason about the tradeoffs before fabrication.",
        }
        payload["pipeline"] = {
            "stages": pipeline_stages,
            "printer_status": printer_status,
            "latest_readiness": latest_readiness,
            "latest_slice": latest_slice,
            "latest_approval": approvals[-1] if approvals else None,
        }
        payload["memory"] = {
            "revisions": memory_rows,
            "learnings": learn_rows,
            "timeline": timeline[-12:],
        }
        payload["manufacturing"] = {
            "plan": manufacture_plan,
            "estimates": estimate_rows,
            "factory_modes": ["In-House", "Local Makers", "CNC / Laser", "Injection Molding", "Casting"],
        }
        payload["systems"] = {
            "environments": [
                {"title": "Garage Systems", "copy": "Mounts, charging, tools, and storage that reduce daily friction."},
                {"title": "Home Organization", "copy": "Physical products that tidy, protect, and improve movement."},
                {"title": "Office & Workspaces", "copy": "Printer stands, cable paths, desks, and production rigs."},
                {"title": "Family Command", "copy": "Support the household with systems that actually get used."},
                {"title": "Creator Rigs", "copy": "Camera handles, shelves, docks, and modular setups."},
                {"title": "Mobile & Vehicle", "copy": "Travel adapters, mounts, and in-motion utility pieces."},
            ],
            "recent_projects": payload["projects"],
        }

        payload["status"] = "Useful"
        payload["summary"] = (
            f"Forge loaded {active_project.get('title') or 'the active project'} with "
            f"{total_measurements} measurement(s), {frame_count} capture frame(s), and {model_count} generated model(s)."
        )
        if not generated_models:
            payload["availability_notes"].append("No generated model yet — design, conversion, and fabrication lanes are operating from the brief and capture data.")
        if not confirmed_count:
            payload["availability_notes"].append("No confirmed measurements yet — dimensional certainty is still limited.")
        return payload

    @app.get("/api/forge/module")
    async def api_forge_module(project_id: str = Query(default="")) -> JSONResponse:
        return _json(await asyncio.to_thread(_forge_build_module_payload, project_id))

    @app.get("/api/forge/projects")
    async def api_forge_list_projects(
        include_archived: bool = Query(default=False),
    ) -> JSONResponse:
        """List all Forge projects, filtering out any whose data directory is missing."""
        store = _forge_store_or_503()
        projects = await asyncio.to_thread(store.list_projects, include_archived)
        # Filter to only projects that have a real on-disk directory
        valid = [p for p in projects if await asyncio.to_thread(store.get_project, p["id"]) is not None]
        return _json({"projects": valid, "total": len(valid)})

    @app.post("/api/forge/projects")
    async def api_forge_create_project(request: Request) -> JSONResponse:
        """Create a new Forge project. Body: {title, description?, intake_type?}"""
        store = _forge_store_or_503()
        body = await request.json()
        title = str(body.get("title", "")).strip()
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        description = str(body.get("description", "")).strip()
        intake_type = str(body.get("intake_type", "file_upload")).strip()
        project = await asyncio.to_thread(
            store.create_project, title, description, intake_type
        )
        return _json(project)

    @app.get("/api/forge/projects/{project_id}")
    async def api_forge_get_project(project_id: str) -> JSONResponse:
        """Get full project state."""
        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")
        return _json(project)

    @app.patch("/api/forge/projects/{project_id}")
    async def api_forge_update_project(project_id: str, request: Request) -> JSONResponse:
        """Update project fields. Body: {title?, notes?, status?}"""
        store = _forge_store_or_503()
        body = await request.json()
        allowed = ("title", "notes", "status", "description", "assumptions")
        kwargs = {k: v for k, v in body.items() if k in allowed}
        if "status" in kwargs:
            from .forge import VALID_STATUSES
            if kwargs["status"] not in VALID_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Valid: {VALID_STATUSES}",
                )
        project = await asyncio.to_thread(store.update_project, project_id, **kwargs)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")
        return _json(project)

    @app.delete("/api/forge/projects/{project_id}")
    async def api_forge_archive_project(project_id: str) -> JSONResponse:
        """Archive a project (soft delete)."""
        store = _forge_store_or_503()
        ok = await asyncio.to_thread(store.set_status, project_id, "archived", "user archived")
        if not ok:
            raise HTTPException(status_code=404, detail="Forge project not found")
        return _json({"ok": True, "status": "archived"})

    @app.post("/api/forge/projects/{project_id}/upload")
    async def api_forge_upload_file(
        project_id: str,
        file: UploadFile = File(...),
    ) -> JSONResponse:
        """Upload a 3D file or photo to the project. Saves to uploads dir."""
        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        _3d_exts = {".stl", ".obj", ".glb", ".3mf"}
        _photo_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".bmp"}

        original_name = file.filename or "upload"
        # Sanitise filename
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", original_name).strip("-._") or "upload"
        safe_name = safe_name[:120]
        suffix = Path(safe_name).suffix.lower()

        uploads_dir = await asyncio.to_thread(store.uploads_dir, project_id)
        dest = uploads_dir / safe_name

        content = await file.read()
        dest.write_bytes(content)
        file_size = len(content)

        if suffix in _3d_exts:
            file_type = "3d_model"
            new_status = "model_ready"
        elif suffix in _photo_exts:
            file_type = "photo"
            new_status = "capture_in_progress"
        else:
            file_type = "other"
            new_status = project.get("status", "idea")

        await asyncio.to_thread(
            store.add_source_file, project_id, safe_name, file_type, file_size
        )

        current_status = project.get("status", "idea")
        # Only advance status, never regress
        status_order = [
            "idea", "reference_uploaded", "capture_in_progress", "needs_more_views",
            "needs_measurements", "modeling", "model_ready",
        ]
        try:
            current_idx = status_order.index(current_status)
        except ValueError:
            current_idx = 0
        try:
            new_idx = status_order.index(new_status)
        except ValueError:
            new_idx = 0
        if new_idx > current_idx:
            await asyncio.to_thread(store.set_status, project_id, new_status)

        return _json({
            "ok": True,
            "filename": safe_name,
            "file_type": file_type,
            "size_bytes": file_size,
            "project_id": project_id,
        })

    @app.get("/api/forge/projects/{project_id}/file/{filename:path}")
    async def api_forge_serve_file(project_id: str, filename: str) -> FileResponse:
        """Serve an uploaded or generated file (for 3D viewer / image display)."""
        store = _forge_store_or_503()
        uploads_dir = await asyncio.to_thread(store.uploads_dir, project_id)
        models_dir = await asyncio.to_thread(store.models_dir, project_id)

        for search_dir in (uploads_dir, models_dir):
            candidate = (search_dir / filename).resolve()
            # Guard against path traversal
            try:
                candidate.relative_to(search_dir.resolve())
            except ValueError:
                continue
            if candidate.exists():
                media_type, _ = mimetypes.guess_type(str(candidate))
                return FileResponse(str(candidate), media_type=media_type or "application/octet-stream")

        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    @app.post("/api/forge/projects/{project_id}/capture-frame")
    async def api_forge_capture_frame(project_id: str, request: Request) -> JSONResponse:
        """Register a captured photo frame. Body: {filename, view_type}"""
        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        filename = str(body.get("filename", "")).strip()
        view_type = str(body.get("view_type", "")).strip().lower()
        if not filename:
            raise HTTPException(status_code=400, detail="filename is required")
        valid_views = {"front", "back", "left", "right", "top", "bottom", "scale_reference", "detail"}
        if view_type not in valid_views:
            raise HTTPException(
                status_code=400,
                detail=f"view_type must be one of: {sorted(valid_views)}",
            )

        sessions = project.get("capture_sessions", [])
        now = _forge_now()

        if not sessions:
            # Create first session
            session = {
                "session_id": str(__import__("uuid").uuid4()),
                "mode": "photo_single",
                "status": "incomplete",
                "frames": [],
                "requirements": [],
                "confidence": {"geometry": "low", "scale": "low", "print_readiness": "not_ready"},
                "created_at": now,
                "updated_at": now,
            }
            sessions.append(session)
        else:
            session = sessions[-1]

        frame = {
            "filename": filename,
            "view_type": view_type,
            "captured_at": now,
            "notes": str(body.get("notes", "")),
        }
        session["frames"].append(frame)
        session["updated_at"] = now

        # Recalculate completeness
        support = _get_forge_support()
        if support:
            completeness = support.capture_completeness(session)
            session["confidence"] = {
                "geometry": completeness["geometry_confidence"],
                "scale": completeness["scale_confidence"],
                "print_readiness": completeness["print_readiness"],
            }
            missing = completeness.get("missing_views", [])
            session["status"] = "complete" if not missing else "needs_more_views"

        await asyncio.to_thread(
            store.update_project, project_id, capture_sessions=sessions
        )
        await asyncio.to_thread(
            store.log_event, project_id, "capture_frame_added",
            f"view_type={view_type!r} filename={filename!r}"
        )
        return _json({"ok": True, "frame": frame, "session": session})

    @app.get("/api/forge/projects/{project_id}/capture-status")
    async def api_forge_capture_status(project_id: str) -> JSONResponse:
        """Return completeness + confidence for the latest capture session."""
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        sessions = project.get("capture_sessions", [])
        if not sessions:
            return _json({
                "has_session": False,
                "message": "No capture sessions yet.",
            })

        latest_session = sessions[-1]
        completeness = await asyncio.to_thread(support.capture_completeness, latest_session)
        return _json({
            "has_session": True,
            "session_id": latest_session.get("session_id"),
            "completeness": completeness,
            "session": latest_session,
        })

    @app.post("/api/forge/projects/{project_id}/measurements")
    async def api_forge_add_measurement(project_id: str, request: Request) -> JSONResponse:
        """Add a measurement. Body: {label, value, unit, confirmed?, notes?}"""
        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        label = str(body.get("label", "")).strip()
        if not label:
            raise HTTPException(status_code=400, detail="label is required")
        try:
            value = float(body["value"])
        except (KeyError, ValueError, TypeError):
            raise HTTPException(status_code=400, detail="value must be a number")
        unit = str(body.get("unit", "mm")).strip().lower()
        if unit not in ("mm", "cm", "in"):
            raise HTTPException(status_code=400, detail="unit must be mm, cm, or in")
        confirmed = bool(body.get("confirmed", False))
        notes = str(body.get("notes", "")).strip()

        measurement = await asyncio.to_thread(
            store.add_measurement,
            project_id, label, value, unit, confirmed, "manual", notes,
        )
        return _json(measurement)

    @app.post("/api/forge/projects/{project_id}/chat")
    async def api_forge_chat(project_id: str, request: Request) -> JSONResponse:
        """Chat with JARVIS Forge about this project. Body: {message}

        Auto-detects design-intent messages (part descriptions with dimensions)
        and triggers cad_package_advanced() generation automatically.
        """
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        message = str(body.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")

        # Design-intent detection: generate a model if the message looks like a part spec
        import re as _re
        _DESIGN_INTENT_RE = _re.compile(
            r"""(?ix)
            (
              \b(build|make|design|generate|create|model)\b .{0,60}
              \b(bracket|mount|enclosure|spacer|part|holder|clip|hook|stand|shelf|box|cover|plate|brace)\b
            |
              \b\d+\s*(?:mm|cm|in|inch|inches)\b .{0,60}
              \b\d+\s*(?:mm|cm|in|inch|inches)\b
            |
              \b(wall\s*thickness|hole\s*diameter|outer\s*diameter|inner\s*diameter|flange|rib|infill)\b
            )
            """,
            _re.IGNORECASE | _re.VERBOSE,
        )

        generated_model: dict | None = None
        if _DESIGN_INTENT_RE.search(message) and support.workshop_support is not None:
            try:
                generated_model = await asyncio.to_thread(
                    support.generate_from_description,
                    project_id,
                    message,
                )
            except Exception:
                generated_model = None

        reply = await asyncio.to_thread(support.forge_chat_response, project_id, message)
        await asyncio.to_thread(
            store.log_event, project_id, "chat", f"user_msg={message[:80]!r}"
        )

        response: dict = {"reply": reply, "project_id": project_id}
        if generated_model and generated_model.get("ok"):
            response["generated_model"] = {
                "model_id": generated_model.get("model_id"),
                "filename": generated_model.get("filename"),
                "format": generated_model.get("format"),
                "export_engine": generated_model.get("export_engine"),
                "export_status": generated_model.get("export_status"),
                "summary": generated_model.get("summary", ""),
            }
        return _json(response)

    @app.post("/api/forge/projects/{project_id}/generate")
    async def api_forge_generate(project_id: str, request: Request) -> JSONResponse:
        """Generate a parametric CAD model from a text description.
        Body: {description, part_name?, dimensions?, constraints?, family_hint?}
        """
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        description = str(body.get("description", "")).strip()
        if not description:
            raise HTTPException(status_code=400, detail="description is required")

        result = await asyncio.to_thread(
            support.generate_from_description,
            project_id,
            description,
            str(body.get("part_name", "")).strip(),
            str(body.get("dimensions", "")).strip(),
            str(body.get("constraints", "")).strip(),
            str(body.get("family_hint", "")).strip(),
        )
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))
        return _json(result)

    @app.post("/api/forge/projects/{project_id}/analyze-sketch")
    async def api_forge_analyze_sketch(project_id: str, request: Request) -> JSONResponse:
        """Analyze a sketch/drawing image with vision AI to extract dimensions and design intent.
        Body: {image_filename, auto_generate?}
        The image_filename must already be in the project's uploads/ directory.
        """
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        image_filename = str(body.get("image_filename", "")).strip()
        if not image_filename:
            raise HTTPException(status_code=400, detail="image_filename is required")

        auto_generate = bool(body.get("auto_generate", True))

        uploads_dir = await asyncio.to_thread(store.uploads_dir, project_id)
        image_path = uploads_dir / image_filename
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image not found in uploads: {image_filename}")

        result = await asyncio.to_thread(
            support.analyze_sketch,
            project_id,
            str(image_path),
            auto_generate,
        )
        return _json(result)

    @app.post("/api/forge/projects/{project_id}/design-council")
    async def api_forge_design_council(project_id: str, request: Request) -> JSONResponse:
        """Run the Forge Design Council — multi-agent roundtable that generates a model.
        Body: {brief, auto_inspect?}
        """
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        brief = str(body.get("brief", "")).strip()
        if not brief:
            raise HTTPException(status_code=400, detail="brief is required")
        auto_inspect = bool(body.get("auto_inspect", True))

        result = await asyncio.to_thread(
            support.run_design_council,
            project_id,
            brief,
            auto_inspect,
        )
        return _json(result)

    @app.post("/api/forge/projects/{project_id}/inspect")
    async def api_forge_inspect(project_id: str, request: Request) -> JSONResponse:
        """Inspect a model file. Body: {model_filename}"""
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        model_filename = str(body.get("model_filename", "")).strip()
        if not model_filename:
            raise HTTPException(status_code=400, detail="model_filename is required")

        result = await asyncio.to_thread(support.inspect_model, project_id, model_filename)
        return _json(result)

    @app.post("/api/forge/projects/{project_id}/slice")
    async def api_forge_slice(project_id: str, request: Request) -> JSONResponse:
        """Stage a slice report. Body: {model_id, printer_id?, material?}"""
        store = _forge_store_or_503()
        support = _forge_support_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body = await request.json()
        model_id = str(body.get("model_id", "")).strip()
        if not model_id:
            raise HTTPException(status_code=400, detail="model_id is required")
        printer_id = str(body.get("printer_id", "creality-k2-pro-combo")).strip()
        material = str(body.get("material", "PLA")).strip()

        report = await asyncio.to_thread(
            support.prepare_slice_report, project_id, model_id, printer_id, material
        )
        return _json(report)

    @app.post("/api/forge/projects/{project_id}/approve")
    async def api_forge_approve(project_id: str, request: Request) -> JSONResponse:
        """Record approval. Advances status to sent_to_printer if slice is staged."""
        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        body: dict = {}
        try:
            body = await request.json()
        except Exception:
            pass
        approved_by = str(body.get("approved_by", "chris")).strip() or "chris"
        notes = str(body.get("notes", "")).strip()

        ok = await asyncio.to_thread(store.add_approval, project_id, approved_by, notes)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to record approval")

        # Advance status if a slice is present
        has_slice = bool(project.get("slices"))
        new_status = "sent_to_printer" if has_slice else "approval_required"
        await asyncio.to_thread(store.set_status, project_id, new_status)

        return _json({
            "ok": True,
            "approved_by": approved_by,
            "new_status": new_status,
        })

    @app.get("/api/forge/projects/{project_id}/timeline")
    async def api_forge_timeline(project_id: str) -> JSONResponse:
        """Return the full event log for a project."""
        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")
        events = await asyncio.to_thread(store.read_timeline, project_id)
        return _json({"events": events, "total": len(events)})

    @app.get("/api/forge/printer-status")
    async def api_forge_printer_status(host: str = Query(...)) -> JSONResponse:
        """Query Moonraker printer status. Query param: host"""
        support = _forge_support_or_503()
        port_param = 7125
        result = await asyncio.to_thread(support.moonraker_status, host, port_param)
        return _json(result)

    @app.get("/api/forge/wow/config")
    async def api_forge_wow_config_get() -> JSONResponse:
        return _json(_forge_load_bridge_config())

    @app.post("/api/forge/wow/config")
    async def api_forge_wow_config_post(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        config = _forge_save_bridge_config(body)
        return _json({**config, "ok": True})

    @app.get("/api/forge/wow/status")
    async def api_forge_wow_status() -> JSONResponse:
        config = _forge_load_bridge_config()
        export_folder_value = str(config.get("export_folder") or "").strip()
        export_folder = Path(export_folder_value).expanduser() if export_folder_value else None
        wow_value = str(config.get("wow_install_path") or "").strip()
        blender_value = str(config.get("blender_path") or "").strip()
        wow_path = Path(wow_value).expanduser() if wow_value else None
        blender_path = Path(blender_value).expanduser() if blender_value else None
        details: list[str] = []
        if export_folder:
            details.append(f"Export folder: {export_folder}")
        if wow_path:
            details.append(f"WoW install: {wow_path}")
        if blender_path:
            details.append(f"Blender path: {blender_path}")
        return _json(
            {
                **config,
                "ok": True,
                "export_folder_exists": bool(export_folder and export_folder.exists()),
                "wow_install_found": bool(wow_path and wow_path.exists()),
                "blender_found": bool(blender_path and blender_path.exists()),
                "wow_export_setup_tip": "Point Forge at the wow.export folder, then refresh the bridge to import a real model.",
                "details": details,
            }
        )

    @app.get("/api/forge/wow/models")
    async def api_forge_wow_models() -> JSONResponse:
        config = _forge_load_bridge_config()
        export_folder_value = str(config.get("export_folder") or "").strip()
        if not export_folder_value:
            return _json({"ok": False, "available": False, "models": [], "detail": "Export folder is not configured yet."})
        export_folder = Path(export_folder_value).expanduser()
        if not export_folder.exists():
            return _json({"ok": False, "available": False, "models": [], "detail": f"Export folder does not exist: {export_folder}"})
        models = []
        for candidate in sorted(export_folder.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".glb", ".obj", ".stl", ".3mf", ".m2"}:
                continue
            models.append(
                {
                    "filename": candidate.name,
                    "size_bytes": candidate.stat().st_size,
                    "modified_at": datetime.fromtimestamp(candidate.stat().st_mtime, timezone.utc).isoformat(),
                }
            )
        return _json({"ok": True, "available": True, "models": models, "count": len(models)})

    @app.post("/api/forge/wow/import")
    async def api_forge_wow_import(request: Request) -> JSONResponse:
        store = _forge_store_or_503()
        try:
            body = await request.json()
        except Exception:
            body = {}
        project_id = str(body.get("project_id") or "").strip()
        filename = str(body.get("filename") or "").strip()
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        if not filename:
            raise HTTPException(status_code=400, detail="filename is required")
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")
        config = _forge_load_bridge_config()
        export_folder_value = str(config.get("export_folder") or "").strip()
        if not export_folder_value:
            raise HTTPException(status_code=400, detail="WoW export folder is not configured")
        export_folder = Path(export_folder_value).expanduser().resolve()
        source = (export_folder / filename).resolve()
        try:
            source.relative_to(export_folder)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid import path")
        if not source.exists() or not source.is_file():
            raise HTTPException(status_code=404, detail="WoW export file not found")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", source.name).strip("-._") or source.name
        dest = await asyncio.to_thread(store.uploads_dir, project_id)
        target = dest / safe_name
        await asyncio.to_thread(shutil.copy2, source, target)
        await asyncio.to_thread(store.add_source_file, project_id, safe_name, "3d_model", target.stat().st_size)
        await asyncio.to_thread(store.log_event, project_id, "wow_import", f"filename={safe_name!r}")
        return _json({"ok": True, "filename": safe_name, "project_id": project_id})

    @app.post("/api/forge/convert/format")
    async def api_forge_convert_format(
        project_id: str = Form(""),
        target_format: str = Form("stl"),
        source_filename: str = Form(""),
        file: UploadFile | None = File(None),
    ) -> JSONResponse:
        store = _forge_store_or_503()
        project_id = str(project_id or "").strip()
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")
        target_format = str(target_format or "stl").strip().lower()
        if target_format not in {"glb", "obj", "stl", "ply"}:
            raise HTTPException(status_code=400, detail="target_format must be glb, obj, stl, or ply")

        upload_path: Path | None = None
        source_path: Path | None = None
        source_label = ""
        if file is not None and getattr(file, "filename", ""):
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", file.filename or "upload").strip("-._") or "upload"
            upload_path = await asyncio.to_thread(store.uploads_dir, project_id) / safe_name
            content = await file.read()
            upload_path.write_bytes(content)
            await asyncio.to_thread(store.add_source_file, project_id, safe_name, "3d_model", len(content))
            source_path = upload_path
            source_label = safe_name
        else:
            source_filename = str(source_filename or "").strip()
            if not source_filename:
                raise HTTPException(status_code=400, detail="source_filename or file is required")
            source_path = await asyncio.to_thread(_forge_resolve_project_file, store, project_id, source_filename)
            source_label = source_filename
        if source_path is None or not source_path.exists():
            raise HTTPException(status_code=404, detail="Source file not found")

        stem = source_path.stem
        dest_name = f"{stem}_converted.{target_format}"
        dest_path = await asyncio.to_thread(store.models_dir, project_id) / dest_name
        if source_path.suffix.lower().lstrip(".") == target_format:
            await asyncio.to_thread(shutil.copy2, source_path, dest_path)
        else:
            try:
                import trimesh  # type: ignore[import]
            except ImportError as exc:
                raise HTTPException(status_code=503, detail=f"trimesh not available: {exc}")
            try:
                mesh = await asyncio.to_thread(trimesh.load, str(source_path))
                if hasattr(mesh, "geometry") and getattr(mesh, "geometry", None):
                    mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
                await asyncio.to_thread(mesh.export, str(dest_path), file_type=target_format)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")

        model_dict = await asyncio.to_thread(
            _forge_register_model_artifact,
            store,
            project_id,
            filename=dest_name,
            method="format_convert",
            title=f"Converted {target_format.upper()} artifact",
            notes=f"Converted from {source_label}.",
            source_filename=source_label,
        )
        await asyncio.to_thread(store.log_event, project_id, "convert_format", f"{source_label!r} -> {dest_name!r}")
        return _json({"ok": True, "filename": dest_name, "project_id": project_id, "download_url": f"/api/forge/projects/{project_id}/file/{dest_name}", "model": model_dict})

    @app.get("/api/forge/convert/blender-check")
    async def api_forge_convert_blender_check() -> JSONResponse:
        config = _forge_load_bridge_config()
        blender_value = str(config.get("blender_path") or "").strip()
        blender_path = Path(blender_value).expanduser() if blender_value else None
        details = []
        if blender_path:
            details.append(f"Configured blender path: {blender_path}")
        else:
            details.append("Blender path is not configured.")
        details.append("WoW Blender Studio addon detection is not yet automated in this runtime.")
        return _json(
            {
                "ok": bool(blender_path and blender_path.exists()),
                "blender_found": bool(blender_path and blender_path.exists()),
                "blender_version": "",
                "addon_found": False,
                "details": details,
            }
        )

    @app.post("/api/forge/convert/repair")
    async def api_forge_convert_repair(request: Request) -> JSONResponse:
        store = _forge_store_or_503()
        try:
            body = await request.json()
        except Exception:
            body = {}
        project_id = str(body.get("project_id") or "").strip()
        source_filename = str(body.get("source_filename") or "").strip()
        if not project_id or not source_filename:
            raise HTTPException(status_code=400, detail="project_id and source_filename are required")
        source_path = await asyncio.to_thread(_forge_resolve_project_file, store, project_id, source_filename)
        if source_path is None:
            raise HTTPException(status_code=404, detail="Source file not found")
        try:
            import trimesh  # type: ignore[import]
            from trimesh import repair as trimesh_repair  # type: ignore[import]
        except ImportError as exc:
            raise HTTPException(status_code=503, detail=f"trimesh not available: {exc}")

        try:
            mesh = await asyncio.to_thread(trimesh.load, str(source_path))
            if hasattr(mesh, "geometry") and getattr(mesh, "geometry", None):
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            was_watertight = bool(mesh.is_watertight)
            ops_applied: list[str] = []
            if body.get("fill_holes", True):
                await asyncio.to_thread(trimesh_repair.fill_holes, mesh)
                ops_applied.append("fill_holes")
            if body.get("fix_normals", True):
                await asyncio.to_thread(trimesh_repair.fix_normals, mesh)
                ops_applied.append("fix_normals")
            if body.get("fix_winding", True) and hasattr(trimesh_repair, "fix_winding"):
                await asyncio.to_thread(trimesh_repair.fix_winding, mesh)
                ops_applied.append("fix_winding")
            is_watertight = bool(mesh.is_watertight)
            dest_name = f"{source_path.stem}_repaired{source_path.suffix.lower() or '.stl'}"
            dest_path = await asyncio.to_thread(store.models_dir, project_id) / dest_name
            await asyncio.to_thread(mesh.export, str(dest_path))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Repair failed: {exc}")

        model_dict = await asyncio.to_thread(
            _forge_register_model_artifact,
            store,
            project_id,
            filename=dest_name,
            method="mesh_repair",
            title="Repaired mesh artifact",
            notes=f"Repair applied to {source_filename}.",
            source_filename=source_filename,
        )
        model_dict["was_repaired"] = True
        model_dict["is_manifold"] = is_watertight
        project = await asyncio.to_thread(store.get_project, project_id)
        if project:
            models = list(project.get("generated_models") or [])
            if models:
                models[-1].update(model_dict)
                await asyncio.to_thread(store.update_project, project_id, generated_models=models)
        await asyncio.to_thread(store.log_event, project_id, "repair_mesh", f"{source_filename!r} -> {dest_name!r}")
        return _json(
            {
                "ok": True,
                "filename": dest_name,
                "project_id": project_id,
                "ops_applied": ops_applied,
                "was_watertight": was_watertight,
                "is_watertight": is_watertight,
                "download_url": f"/api/forge/projects/{project_id}/file/{dest_name}",
                "model": model_dict,
            }
        )

    @app.post("/api/forge/convert/scale")
    async def api_forge_convert_scale(request: Request) -> JSONResponse:
        store = _forge_store_or_503()
        try:
            body = await request.json()
        except Exception:
            body = {}
        project_id = str(body.get("project_id") or "").strip()
        source_filename = str(body.get("source_filename") or "").strip()
        if not project_id or not source_filename:
            raise HTTPException(status_code=400, detail="project_id and source_filename are required")
        source_path = await asyncio.to_thread(_forge_resolve_project_file, store, project_id, source_filename)
        if source_path is None:
            raise HTTPException(status_code=404, detail="Source file not found")
        operation = str(body.get("operation") or "rescale").strip().lower()
        try:
            import trimesh  # type: ignore[import]
        except ImportError as exc:
            raise HTTPException(status_code=503, detail=f"trimesh not available: {exc}")
        try:
            mesh = await asyncio.to_thread(trimesh.load, str(source_path))
            if hasattr(mesh, "geometry") and getattr(mesh, "geometry", None):
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            original_extents = [float(value) for value in mesh.bounding_box.extents.tolist()]
            scale_factor = 1.0
            if operation == "rescale":
                target_size = float(body.get("target_size") or 100.0)
                current_max = max(original_extents) if original_extents else 1.0
                scale_factor = target_size / current_max if current_max else 1.0
                mesh.apply_scale(scale_factor)
            elif operation == "normalize_bbox":
                current_max = max(original_extents) if original_extents else 1.0
                scale_factor = 1.0 / current_max if current_max else 1.0
                mesh.apply_scale(scale_factor)
            elif operation == "center_origin":
                mesh.apply_translation(-mesh.bounding_box.centroid)
            else:
                raise HTTPException(status_code=400, detail="Unsupported scale operation")
            final_extents = [float(value) for value in mesh.bounding_box.extents.tolist()]
            dest_name = f"{source_path.stem}_{operation}{source_path.suffix.lower() or '.stl'}"
            dest_path = await asyncio.to_thread(store.models_dir, project_id) / dest_name
            await asyncio.to_thread(mesh.export, str(dest_path))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Scale failed: {exc}")

        model_dict = await asyncio.to_thread(
            _forge_register_model_artifact,
            store,
            project_id,
            filename=dest_name,
            method="scale_transform",
            title=f"Scaled artifact ({operation})",
            notes=f"Scale operation {operation} applied to {source_filename}.",
            source_filename=source_filename,
        )
        await asyncio.to_thread(store.log_event, project_id, "scale_mesh", f"{source_filename!r} -> {dest_name!r} ({operation})")
        return _json(
            {
                "ok": True,
                "filename": dest_name,
                "project_id": project_id,
                "operation": operation,
                "scale_factor": scale_factor,
                "original_bbox_mm": original_extents,
                "final_bbox_mm": final_extents,
                "download_url": f"/api/forge/projects/{project_id}/file/{dest_name}",
                "model": model_dict,
            }
        )

    @app.post("/api/forge/reconstruct")
    async def api_forge_reconstruct(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        """Trigger Shap-E reconstruction (async). Body: {project_id, image_filename?, prompt?}"""
        support = _forge_support_or_503()
        body = await request.json()
        project_id = str(body.get("project_id", "")).strip()
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")

        store = _forge_store_or_503()
        project = await asyncio.to_thread(store.get_project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Forge project not found")

        image_filename = str(body.get("image_filename", "")).strip()
        prompt = str(body.get("prompt", "")).strip()

        image_path = ""
        if image_filename:
            uploads_dir = await asyncio.to_thread(store.uploads_dir, project_id)
            candidate = uploads_dir / image_filename
            if candidate.exists():
                image_path = str(candidate)

        # Run Shap-E in background (it can be slow)
        async def _run_reconstruct():
            try:
                await asyncio.to_thread(
                    support.reconstruct_shape_e, project_id, image_path, prompt
                )
            except Exception as _exc:
                await asyncio.to_thread(
                    store.log_event, project_id, "reconstruct_error", str(_exc)
                )

        background_tasks.add_task(_run_reconstruct)
        await asyncio.to_thread(
            store.set_status, project_id, "modeling",
            "Shap-E reconstruction started"
        )
        return _json({
            "ok": True,
            "status": "modeling",
            "message": "Shap-E reconstruction started in background.",
            "project_id": project_id,
        })

    # ── End Forge ──────────────────────────────────────────────────────────────

    # ------------------------------------------------------------------
    # Phase 4: Symptom Triage Engine (Oracle-First Protocol)
    # ------------------------------------------------------------------

    async def _build_health_module_payload() -> dict[str, Any]:
        generated_at = ""
        try:
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()
        except Exception:
            generated_at = ""

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "available": True,
            "status": "Useful",
            "summary": "Health now has a dedicated module route with live drift, objective, and triage posture inside JARVIS.",
            "what_became_real": "Health is now represented as a dedicated app module with visible route-owned continuity instead of a storyboard-only route.",
            "remains_partial": "Deeper health workflows and broader manual data entry still need follow-on slices.",
            "runtime_note": "Health is live and connected.",
            "availability_notes": [],
            "counts": {
                "signals": 0,
                "clusters": 0,
                "objectives": 0,
                "checkins": 0,
                "review_items": 0,
                "recent_activity": 0,
            },
            "signal_count": 0,
            "active_cluster_count": 0,
            "objective_count": 0,
            "current_signals": {},
            "baseline_deviations": [],
            "drift_scan": {
                "overall_drift_status": "unknown",
                "active_clusters": [],
                "one_next_action": "Health module payload is still hydrating.",
                "oracle_review_needed": False,
            },
            "objectives": [],
            "red_flags": {},
            "recent_activity": [],
            "proof_paths": {
                "module_route": "/health-center",
                "module_api": "/api/health/module",
                "drift_scan_api": "/api/health/drift/scan",
                "objectives_api": "/api/health/quarterly/objectives",
                "triage_api": "/api/health/symptom/triage",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        try:
            from .drift_detection import get_baseline_deviations, get_current_signals, run_drift_scan

            current_signals = await get_current_signals()
            baseline_deviations = await get_baseline_deviations(current_signals)
            drift_scan = await run_drift_scan()
            payload["current_signals"] = current_signals
            payload["baseline_deviations"] = baseline_deviations
            payload["drift_scan"] = drift_scan
            payload["signal_count"] = len(current_signals)
            payload["active_cluster_count"] = len(list(drift_scan.get("active_clusters") or []))
            payload["counts"]["signals"] = payload["signal_count"]
            payload["counts"]["clusters"] = payload["active_cluster_count"]
            payload["summary"] = f"Health center loaded {len(current_signals)} current signal(s) with {len(list(drift_scan.get('active_clusters') or []))} active drift cluster(s)."
            if not current_signals:
                payload["status"] = "Wired"
                payload["remains_partial"] = "The dedicated Health screen is live, but current signal sources are still sparse in this runtime."
                payload["runtime_note"] = "Health is live, but current signal feeds are still sparse in this runtime."
                payload["availability_notes"].append("Current signal feeds are sparse, so readiness and drift may be partial.")
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["errors"].append(f"drift: {exc}")
            payload["summary"] = "Health center route is live, but drift and signal sources did not fully hydrate."
            payload["remains_partial"] = "Live health sources still need repair or population in this runtime."
            payload["runtime_note"] = "Health is partially connected. Drift and signal sources did not fully hydrate."
            payload["availability_notes"].append("Drift and current signal hydration failed in this runtime.")

        try:
            from .quarterly_review import get_current_objectives

            objectives = await get_current_objectives()
            payload["objectives"] = objectives
            payload["objective_count"] = len(objectives)
            payload["counts"]["objectives"] = len(objectives)
        except Exception as exc:
            payload["errors"].append(f"objectives: {exc}")
            payload["availability_notes"].append("Quarterly health objectives could not be loaded.")

        try:
            from .symptom_triage import get_red_flags_for_patient

            payload["red_flags"] = get_red_flags_for_patient()
        except Exception as exc:
            payload["errors"].append(f"red_flags: {exc}")
            payload["availability_notes"].append("Personalized symptom red flags could not be loaded.")

        payload["recent_activity"] = _module_recent_activity(route="/health-center", domain="health")
        payload["counts"]["recent_activity"] = len(payload["recent_activity"])
        checkin_store = HealthCheckInStore()
        recent_checkins = checkin_store.list_checkins("chris", limit=6)
        review_summary = checkin_store.review_summary("chris", limit=6)
        payload["recent_checkins"] = recent_checkins
        payload["checkin_count"] = len(recent_checkins)
        payload["counts"]["checkins"] = payload["checkin_count"]
        payload["review_lane"] = list(review_summary.get("items") or [])
        payload["review_count"] = int(review_summary.get("count") or 0)
        payload["review_status_counts"] = dict(review_summary.get("counts") or {})
        payload["counts"]["review_items"] = payload["review_count"]
        payload["proof_paths"]["checkins_api"] = "/api/health/checkins"
        payload["proof_paths"]["checkin_review_api"] = "/api/health/checkins/{checkin_id}/review"
        if recent_checkins:
            latest_checkin = recent_checkins[0]
            payload["summary"] = (
                f"{payload['summary']} {len(recent_checkins)} manual health check-in(s) are now available for continuity and review."
            )
            if payload["status"] == "Wired":
                payload["status"] = "Useful"
                payload["available"] = True
                payload["remains_partial"] = "Live health sources are still partially hydrated, but manual check-ins and route-owned continuity now keep the module useful."
            payload["latest_checkin"] = latest_checkin
            payload["runtime_note"] = f"Health is live and connected. {len(recent_checkins)} manual check-in(s) are available for continuity."
        else:
            payload["availability_notes"].append("No recent manual health check-ins are available yet.")

        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some health sources still failed to hydrate; inspect the payload preview for details."
        if payload["review_count"]:
            payload["runtime_note"] = (
                f"{payload['runtime_note']} {payload['review_count']} review item(s) are waiting in the historical lane."
            ).strip()
        if not payload["objective_count"]:
            payload["availability_notes"].append("No active quarterly health objectives are saved yet.")
        if not payload["availability_notes"]:
            payload["availability_notes"].append("All currently available Health sources hydrated successfully.")
        return payload

    @app.get("/api/health/module")
    async def api_health_module() -> JSONResponse:
        return _json(await _build_health_module_payload())

    @app.get("/api/health/checkins")
    async def api_health_checkins_get(actor: str = "chris") -> JSONResponse:
        store = HealthCheckInStore()
        entries = store.list_checkins(actor, limit=12)
        review_summary = store.review_summary(actor, limit=12)
        return _json(
            {
                "entries": entries,
                "count": len(entries),
                "review_lane": list(review_summary.get("items") or []),
                "review_count": int(review_summary.get("count") or 0),
                "review_status_counts": dict(review_summary.get("counts") or {}),
            }
        )

    @app.post("/api/health/checkins")
    async def api_health_checkins_post(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        actor = str(body.get("actor") or "Chris").strip() or "Chris"
        actor_id = str(body.get("actor_id") or actor).strip().lower() or "chris"
        entry = HealthCheckInStore().save_checkin(
            actor_id=actor_id,
            symptoms=str(body.get("symptoms") or "").strip(),
            note=str(body.get("note") or "").strip(),
            energy_level=body.get("energy_level"),
            sleep_hours=body.get("sleep_hours"),
            stress_level=body.get("stress_level"),
            source=str(body.get("source") or "manual").strip() or "manual",
        )
        detail = (
            f"Energy {entry.get('energy_level') if entry.get('energy_level') is not None else 'n/a'} · "
            f"Sleep {entry.get('sleep_hours') if entry.get('sleep_hours') is not None else 'n/a'}h · "
            f"Stress {entry.get('stress_level') if entry.get('stress_level') is not None else 'n/a'}"
        )
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "health",
                "action": "Save Health Check-In",
                "title": str(entry.get("symptoms") or "Health check-in").strip() or "Health check-in",
                "detail": detail,
                "why_now": str(entry.get("note") or "Health route captured a manual check-in for continuity and longitudinal review.").strip(),
                "result_summary": "Manual health check-in saved.",
                "related_route": "/health-center",
                "route_label": "Open Health",
                "related_kind": "health-checkin",
                "related_label": str(entry.get("checkin_id") or "").strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Health",
            reason=str(entry.get("note") or "Health check-in updated the shared health continuity lane.").strip(),
            route="/health-center",
            actor=actor,
        )
        return _json({"status": "recorded", "checkin": entry, "focus": focus_entry})

    @app.post("/api/health/checkins/{checkin_id}/review")
    async def api_health_checkins_review(checkin_id: str, request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        actor = str(body.get("actor") or "Chris").strip() or "Chris"
        review_note = str(body.get("note") or "").strip()
        try:
            entry = HealthCheckInStore().review_checkin(
                checkin_id=checkin_id,
                status=str(body.get("status") or "").strip(),
                note=review_note,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Health check-in not found.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        detail = str(entry.get("symptoms") or "Health check-in").strip() or "Health check-in"
        label = str(entry.get("review_status_label") or entry.get("review_status") or "reviewed").strip() or "reviewed"
        AuditLog(DEFAULT_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": "health",
                "action": "Review Health Check-In",
                "title": detail,
                "detail": f"Health check-in marked {label.lower()}.",
                "why_now": review_note or "Health history review updated the longitudinal coaching lane.",
                "result_summary": f"Health check-in is now {label.lower()}.",
                "related_route": "/health-center",
                "route_label": "Open Health",
                "related_kind": "health-checkin-review",
                "related_label": str(entry.get("checkin_id") or "").strip(),
                "succeeded": True,
                "source_kind": "operator-action",
            },
        )
        focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
            module="Health",
            reason=review_note or f"Health check-in moved into {label.lower()} review posture.",
            route="/health-center",
            actor=actor,
        )
        return _json({"status": "recorded", "checkin": entry, "focus": focus_entry})

    @app.post("/api/health/symptom/triage")
    async def api_symptom_triage(request: Request) -> JSONResponse:
        """Full symptom triage: Oracle gate + specialist routing + structured report."""
        try:
            from .symptom_triage import run_triage
        except ImportError:
            from symptom_triage import run_triage
        try:
            body = await request.json()
        except Exception:
            body = {}
        result = await run_triage(
            symptoms=str(body.get("symptoms", "")),
            duration=str(body.get("duration", "")),
            severity=body.get("severity"),
            associated_symptoms=str(body.get("associated_symptoms", "")),
            context=str(body.get("context", "")),
        )
        return _json(result)

    @app.get("/api/health/symptom/redflags")
    async def api_symptom_redflags() -> JSONResponse:
        """Chris's personalized red flag symptom list."""
        try:
            from .symptom_triage import get_red_flags_for_patient
        except ImportError:
            from symptom_triage import get_red_flags_for_patient
        return _json(get_red_flags_for_patient())

    # ------------------------------------------------------------------
    # Phase 4: Predictive Drift Detection (Heimdall Protocol)
    # ------------------------------------------------------------------

    @app.get("/api/health/drift/scan")
    async def api_drift_scan() -> JSONResponse:
        """Full drift scan: signals, cluster evaluation, baseline deviations, alerts."""
        try:
            from .drift_detection import run_drift_scan
        except ImportError:
            from drift_detection import run_drift_scan
        return _json(await run_drift_scan())

    @app.get("/api/health/drift/clusters")
    async def api_drift_clusters() -> JSONResponse:
        """Evaluate all 5 drift clusters against current signals."""
        try:
            from .drift_detection import scan_all_clusters, get_current_signals
        except ImportError:
            from drift_detection import scan_all_clusters, get_current_signals
        signals = await get_current_signals()
        clusters = await scan_all_clusters(signals)
        active = [c for c in clusters if c["active"]]
        return _json({
            "clusters": clusters,
            "active_count": len(active),
            "total_count": len(clusters),
            "signals_loaded": list(signals.keys()),
        })

    @app.get("/api/health/drift/baseline")
    async def api_drift_baseline() -> JSONResponse:
        """Chris's personal baseline metrics with current deviations."""
        try:
            from .drift_detection import get_baseline_deviations, get_current_signals, _CHRIS_BASELINES
        except ImportError:
            from drift_detection import get_baseline_deviations, get_current_signals, _CHRIS_BASELINES
        signals = await get_current_signals()
        deviations = await get_baseline_deviations(signals)
        return _json({
            "baselines": _CHRIS_BASELINES,
            "current_deviations": deviations,
            "significant_count": sum(1 for d in deviations if d["significant"]),
        })

    # ------------------------------------------------------------------
    # Phase 4: Quarterly Longevity Council Review
    # ------------------------------------------------------------------

    @app.post("/api/health/quarterly/review")
    async def api_quarterly_review(request: Request) -> JSONResponse:
        """Run full 90-day quarterly review (LLM-intensive). May take 30-60s."""
        try:
            from .quarterly_review import run_quarterly_review
        except ImportError:
            from quarterly_review import run_quarterly_review
        try:
            body = await request.json()
        except Exception:
            body = {}
        result = await run_quarterly_review(
            review_period_days=int(body.get("review_period_days", 90)),
            major_life_context=str(body.get("major_life_context", "")),
            additional_context=str(body.get("additional_context", "")),
        )
        return _json(result)

    @app.get("/api/health/quarterly/objectives")
    async def api_quarterly_objectives_get() -> JSONResponse:
        """Return current 90-day objectives."""
        try:
            from .quarterly_review import get_current_objectives
        except ImportError:
            from quarterly_review import get_current_objectives
        objectives = await get_current_objectives()
        return _json({"objectives": objectives, "count": len(objectives)})

    @app.post("/api/health/quarterly/objectives")
    async def api_quarterly_objectives_set(request: Request) -> JSONResponse:
        """Set new 90-day objectives. Body: {objectives: [...]}"""
        try:
            from .quarterly_review import set_objectives
        except ImportError:
            from quarterly_review import set_objectives
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
        objectives = body.get("objectives", [])
        if not isinstance(objectives, list):
            return JSONResponse({"error": "objectives must be a list"}, status_code=400)
        result = await set_objectives(objectives)
        if result.get("ok"):
            actor = str(body.get("actor") or "Chris").strip() or "Chris"
            latest_objective = ""
            if objectives and isinstance(objectives[-1], dict):
                latest_objective = str(objectives[-1].get("objective") or "").strip()
            focus_entry = ProgressFocusStore(DEFAULT_AUDIT_ROOT).save_focus(
                module="Health",
                reason=(
                    f"Health objective saved: {latest_objective}."
                    if latest_objective
                    else "Health objective save became the highest-priority shared Level 3 focus."
                ),
                route="/health-center",
                actor=actor,
            )
            result["focus"] = focus_entry
        status_code = 201 if result.get("ok") else 400
        return JSONResponse(result, status_code=status_code)

    @app.get("/api/health/quarterly/doctor-packet")
    async def api_quarterly_doctor_packet() -> JSONResponse:
        """Generate quarterly doctor discussion packet for Nov 13 visit with Dr. Wenk."""
        try:
            from .quarterly_review import generate_doctor_packet
        except ImportError:
            from quarterly_review import generate_doctor_packet
        return _json(await generate_doctor_packet())

    # ------------------------------------------------------------------
    # Health extended routes — summary, score, vitals, Sam, Helen,
    # longevity, mychart, omron, chat
    # ------------------------------------------------------------------

    @app.get("/api/health/summary")
    async def api_health_summary() -> JSONResponse:
        """Latest health snapshot from health_bridge."""
        try:
            from . import health_bridge
        except ImportError:
            import health_bridge  # type: ignore[no-redef]
        try:
            latest = health_bridge.get_latest() or {}
            readiness = health_bridge.compute_readiness(latest or None)
            return _json({"ok": True, "snapshot": latest, "readiness": readiness})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "snapshot": {}, "readiness": {}})

    @app.get("/api/health/score")
    async def api_health_score() -> JSONResponse:
        """Today's computed health score."""
        try:
            from . import health_score as _hs
        except ImportError:
            import health_score as _hs  # type: ignore[no-redef]
        try:
            from datetime import date as _date
            today = _date.today().isoformat()
            entry = _hs.compute_daily_score(today)
            history = _hs.get_score_history(days=7)
            return _json({"ok": True, "today": entry, "history": history})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "today": {}, "history": []})

    @app.get("/api/health/bp")
    async def api_health_bp() -> JSONResponse:
        """Blood pressure readings from health_bridge."""
        try:
            from . import health_bridge
        except ImportError:
            import health_bridge  # type: ignore[no-redef]
        try:
            trend = health_bridge.get_trend("blood_pressure_systolic", days=14)
            latest = health_bridge.get_latest() or {}
            bp = {"systolic": latest.get("blood_pressure_systolic"), "diastolic": latest.get("blood_pressure_diastolic")}
            return _json({"ok": True, "latest": bp, "trend": trend})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "latest": {}, "trend": {}})

    @app.post("/api/health/bp/ingest")
    async def api_health_bp_ingest(request: Request) -> JSONResponse:
        """Ingest a blood pressure reading."""
        try:
            from . import health_bridge
        except ImportError:
            import health_bridge  # type: ignore[no-redef]
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
        try:
            result = health_bridge.ingest("bp_manual", body)
            return _json({"ok": True, "result": result})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc)})

    @app.post("/api/health/ingest")
    async def api_health_ingest(request: Request) -> JSONResponse:
        """Ingest health metrics from any source."""
        try:
            from . import health_bridge
        except ImportError:
            import health_bridge  # type: ignore[no-redef]
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
        try:
            source = str(body.get("source", "manual"))
            metrics = {k: v for k, v in body.items() if k != "source"}
            result = health_bridge.ingest(source, metrics)
            return _json({"ok": True, "result": result})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc)})

    @app.get("/api/health/ecg")
    async def api_health_ecg() -> JSONResponse:
        """ECG readings from health_db."""
        try:
            from . import health_db
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": f"Health ECG is unavailable: {exc}", "readings": []})
        try:
            readings = await health_db.get_ecg_readings(limit=10)
            return _json({"ok": True, "available": True, "readings": readings, "count": len(readings)})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc), "readings": []})

    @app.get("/api/health/db/summary")
    async def api_health_db_summary() -> JSONResponse:
        """Health database summary: latest metrics and mychart pages."""
        try:
            from . import health_db
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": f"Health database summary is unavailable: {exc}", "today": {}, "recent": []})
        try:
            today_metrics = await health_db.get_today_metrics()
            recent_metrics = await health_db.get_latest_metrics(days=7)
            return _json({
                "ok": True,
                "available": True,
                "today": today_metrics or {},
                "recent": recent_metrics,
                "count": len(recent_metrics),
            })
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc), "today": {}, "recent": []})

    @app.get("/api/health/sam/history")
    async def api_health_sam_history() -> JSONResponse:
        """Sam Wilson health agent history."""
        try:
            from . import health_agent as _ha
        except ImportError:
            import health_agent as _ha  # type: ignore[no-redef]
        try:
            dashboard = _ha.get_dashboard_data()
            metrics = _ha.get_health_metrics()
            return _json({"ok": True, "dashboard": dashboard, "metrics": metrics})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "dashboard": {}, "metrics": {}})

    @app.get("/api/health/sam/journal")
    async def api_health_sam_journal() -> JSONResponse:
        """Sam Wilson health journal summary."""
        try:
            from . import health_agent as _ha
        except ImportError:
            import health_agent as _ha  # type: ignore[no-redef]
        try:
            labs = _ha.get_labs_summary()
            anomalies = _ha.flag_anomalies()
            return _json({"ok": True, "labs": labs, "anomalies": anomalies})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "labs": [], "anomalies": []})

    @app.get("/api/health/sam/morning-checkin")
    async def api_health_sam_morning_checkin() -> JSONResponse:
        """Sam Wilson morning check-in summary."""
        try:
            from . import health_bridge, health_agent as _ha
        except ImportError:
            import health_bridge, health_agent as _ha  # type: ignore[no-redef]
        try:
            summary = health_bridge.get_morning_summary()
            epic = _ha.get_epic_summary()
            return _json({"ok": True, "summary": summary, "epic": epic})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "summary": "", "epic": {}})

    @app.get("/api/health/sam/evaluate")
    @app.get("/api/health/sam/daily")
    @app.get("/api/health/sam/checkin")
    @app.get("/api/health/sam/evening-checkin")
    @app.get("/api/health/sam/diet-interview")
    async def api_health_sam_evaluate() -> JSONResponse:
        """Sam Wilson evaluation / daily / check-in endpoint."""
        try:
            from . import health_agent as _ha
        except ImportError:
            import health_agent as _ha  # type: ignore[no-redef]
        try:
            dashboard = _ha.get_dashboard_data()
            return _json({"ok": True, "dashboard": dashboard})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "dashboard": {}})

    @app.post("/api/health/sam/chat")
    async def api_health_sam_chat(request: Request) -> JSONResponse:
        """Sam Wilson health coaching chat."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        message = str(body.get("message") or body.get("text") or "").strip()
        if not message:
            return _json({"ok": False, "reply": "No message provided.", "available": False})
        return _json({
            "ok": True,
            "reply": "Sam Wilson coaching is available through the health module. Use the health check-in to log symptoms and get coaching guidance.",
            "available": True,
            "source": "shell",
        })

    @app.get("/api/health/helen/analysis")
    async def api_health_helen_analysis() -> JSONResponse:
        """Helen Cho analysis based on current health data."""
        try:
            from . import health_agent as _ha
        except ImportError:
            import health_agent as _ha  # type: ignore[no-redef]
        try:
            from . import longevity_council as _lc
        except ImportError:
            _lc = None  # type: ignore[assignment]
        try:
            metrics = _ha.get_health_metrics()
            anomalies = _ha.flag_anomalies()
            analysis: dict = {"metrics": metrics, "anomalies": anomalies, "available": True}
            if _lc:
                try:
                    analysis["longevity_summary"] = _lc.get_longevity_summary() if hasattr(_lc, "get_longevity_summary") else {}
                except Exception:
                    pass
            return _json({"ok": True, "analysis": analysis})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "analysis": {"available": False}})

    @app.post("/api/health/helen/refresh")
    async def api_health_helen_refresh() -> JSONResponse:
        """Trigger a Helen Cho analysis refresh."""
        try:
            from . import health_bridge
        except ImportError:
            import health_bridge  # type: ignore[no-redef]
        try:
            latest = health_bridge.get_latest() or {}
            readiness = health_bridge.compute_readiness(latest or None)
            return _json({"ok": True, "refreshed": True, "readiness": readiness})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "refreshed": False})

    @app.get("/api/health/chat/doctors")
    async def api_health_chat_doctors() -> JSONResponse:
        """List physician agents available for consultation."""
        return _json({
            "ok": True,
            "doctors": [
                {"id": "helen_cho", "name": "Helen Cho, MD", "specialty": "Internal Medicine / AI Health Director", "available": True},
                {"id": "sam_wilson", "name": "Sam Wilson", "specialty": "Health & Recovery Coaching", "available": True},
                {"id": "longevity_council", "name": "Longevity Council", "specialty": "T2DM, Cardiovascular, Metabolic", "available": True},
            ],
        })

    @app.post("/api/health/chat")
    async def api_health_chat(request: Request) -> JSONResponse:
        """Health consultation chat endpoint."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        doctor_id = str(body.get("doctor_id") or body.get("agent") or "helen_cho")
        message = str(body.get("message") or body.get("text") or "").strip()
        if not message:
            return _json({"ok": False, "reply": "No message provided.", "available": False})
        return _json({
            "ok": True,
            "reply": f"Health consultation via {doctor_id} requires the LLM gateway. Use the voice shell or health check-in for direct coaching.",
            "available": False,
            "doctor_id": doctor_id,
            "source": "shell",
        })

    @app.get("/api/health/longevity/estimate")
    async def api_health_longevity_estimate() -> JSONResponse:
        """Longevity estimate from available health data."""
        try:
            from . import health_agent as _ha
        except ImportError:
            import health_agent as _ha  # type: ignore[no-redef]
        try:
            metrics = _ha.get_health_metrics()
            dashboard = _ha.get_dashboard_data()
            return _json({"ok": True, "estimate": dashboard.get("longevity_estimate", {}), "metrics": metrics, "available": True})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "available": False})

    @app.get("/api/health/longevity/trajectory")
    async def api_health_longevity_trajectory() -> JSONResponse:
        """Longevity trajectory from available health data."""
        try:
            from . import health_bridge
        except ImportError:
            import health_bridge  # type: ignore[no-redef]
        try:
            history = health_bridge.get_history(days=30)
            return _json({"ok": True, "trajectory": history, "count": len(history), "available": True})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc), "available": False})

    @app.get("/api/health/mychart/summary")
    async def api_health_mychart_summary() -> JSONResponse:
        """MyChart records summary."""
        try:
            from . import mychart_reader
        except ImportError:
            try:
                import mychart_reader  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "error": "MyChart reader not available"})
        try:
            summary = mychart_reader.get_summary()
            return _json({"ok": True, "available": True, "summary": summary})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/health/mychart/sync")
    async def api_health_mychart_sync() -> JSONResponse:
        """Trigger MyChart sync (requires configured credentials)."""
        return _json({
            "ok": False,
            "available": False,
            "message": "MyChart sync requires Epic FHIR credentials configured in settings.",
        })

    @app.get("/api/health/mychart/sync-status")
    async def api_health_mychart_sync_status() -> JSONResponse:
        """Check MyChart sync status."""
        try:
            from . import mychart_reader
        except ImportError:
            try:
                import mychart_reader  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "synced": False, "available": False})
        try:
            records = mychart_reader.load_records()
            return _json({"ok": True, "synced": bool(records), "available": True, "record_count": len(records)})
        except Exception as exc:
            return _json({"ok": False, "synced": False, "available": False, "error": str(exc)})

    @app.get("/api/health/omron/status")
    async def api_health_omron_status() -> JSONResponse:
        """Omron device connection status."""
        try:
            from . import omron_sync
        except ImportError:
            try:
                import omron_sync  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "connected": False, "available": False})
        try:
            status = omron_sync.get_connection_status()
            return _json({"ok": True, "connected": status.get("connected", False), "status": status, "available": True})
        except Exception as exc:
            return _json({"ok": False, "connected": False, "available": False, "error": str(exc)})

    @app.get("/api/health/omron/connect")
    async def api_health_omron_connect() -> JSONResponse:
        """Redirect to Omron OAuth (requires configured credentials)."""
        try:
            from . import omron_sync
        except ImportError:
            try:
                import omron_sync  # type: ignore[no-redef]
            except ImportError:
                return JSONResponse({"error": "Omron module unavailable"}, status_code=503)
        try:
            redirect_uri = "http://localhost:8787/api/health/omron/callback"
            url = omron_sync.build_auth_url(redirect_uri)
            return _json({"ok": True, "auth_url": url, "available": True})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/health/omron/sync")
    async def api_health_omron_sync() -> JSONResponse:
        """Trigger Omron blood pressure sync (requires OAuth token)."""
        try:
            from . import omron_sync
        except ImportError:
            try:
                import omron_sync  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "error": "Omron module unavailable"})
        try:
            status = omron_sync.get_connection_status()
            if not status.get("connected"):
                return _json({"ok": False, "available": False, "message": "Omron not connected. Connect via Settings → Health → Omron."})
            return _json({"ok": False, "available": True, "message": "Omron sync requires OAuth tokens. Reconnect in Settings."})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    # ------------------------------------------------------------------
    # Navigation routes — nav/home, nav/maps-key, nav/pois, nav/route
    # ------------------------------------------------------------------

    @app.get("/api/nav/home")
    async def api_nav_home() -> JSONResponse:
        """Home navigation data: commute, weather, POIs near home."""
        try:
            from .apple_api import _load_navigation_state, LOCATION_SETTINGS_PATH
        except ImportError:
            return _json({"ok": False, "available": False, "error": "Navigation state unavailable"})
        try:
            nav_state = _load_navigation_state()
            return _json({"ok": True, "available": True, "nav_state": nav_state})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.get("/api/nav/maps-key")
    async def api_nav_maps_key() -> JSONResponse:
        """Return Google Maps API key availability (key itself is never exposed)."""
        maps_key = str(os.environ.get("GOOGLE_MAPS_API_KEY", "") or "").strip()
        return _json({"ok": True, "available": bool(maps_key), "key_configured": bool(maps_key)})

    @app.get("/api/nav/pois")
    async def api_nav_pois(lat: float = 0.0, lng: float = 0.0, radius: int = 5000) -> JSONResponse:
        """Return points of interest near a location."""
        return _json({
            "ok": True,
            "available": False,
            "message": "POI search requires active navigation context and Google Maps key.",
            "pois": [],
        })

    @app.post("/api/nav/route")
    async def api_nav_route(request: Request) -> JSONResponse:
        """Preview or plan a navigation route."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        origin = str(body.get("origin", ""))
        destination = str(body.get("destination", ""))
        if not origin or not destination:
            return _json({"ok": False, "error": "origin and destination required"})
        try:
            from .apple_api import _record_navigation_route_history
        except ImportError:
            return _json({"ok": False, "available": False, "error": "Navigation bridge unavailable"})
        try:
            route_entry = {
                "origin": origin,
                "destination": destination,
                "mode": str(body.get("mode", "driving")),
            }
            _record_navigation_route_history(route_entry)
            return _json({"ok": True, "route": route_entry, "available": True})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.get("/api/google/maps-usage")
    async def api_google_maps_usage() -> JSONResponse:
        """Google Maps API usage summary."""
        maps_key = str(os.environ.get("GOOGLE_MAPS_API_KEY", "") or "").strip()
        return _json({
            "ok": True,
            "available": bool(maps_key),
            "key_configured": bool(maps_key),
            "usage": {} if not maps_key else {"note": "Usage data requires Maps Platform Console access"},
        })

    # ------------------------------------------------------------------
    # Kasa smart home routes
    # ------------------------------------------------------------------

    @app.get("/api/kasa/devices")
    async def api_kasa_devices() -> JSONResponse:
        """List discovered Kasa smart home devices."""
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "devices": {}, "rooms": {}})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            result = bridge.get_devices()
            return _json({"ok": True, "available": True, **result})
        except Exception as exc:
            return _json({"ok": False, "available": False, "devices": {}, "rooms": {}, "error": str(exc)})

    @app.get("/api/kasa/scene")
    async def api_kasa_get_scenes() -> JSONResponse:
        """List saved Kasa scenes."""
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "scenes": []})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            scenes = bridge.get_scenes()
            return _json({"ok": True, "available": True, "scenes": scenes})
        except Exception as exc:
            return _json({"ok": False, "available": False, "scenes": [], "error": str(exc)})

    @app.post("/api/kasa/scene")
    async def api_kasa_run_scene(request: Request) -> JSONResponse:
        """Run a Kasa scene by ID."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        scene_id = str(body.get("scene_id") or body.get("id") or "")
        if not scene_id:
            return _json({"ok": False, "error": "scene_id required"})
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "error": "Kasa bridge unavailable"})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            result = bridge.run_scene(scene_id)
            return _json({"ok": result.get("ok", False), "result": result})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/kasa/toggle")
    async def api_kasa_toggle(request: Request) -> JSONResponse:
        """Toggle a Kasa device on/off."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        device = str(body.get("device") or body.get("alias") or body.get("ip") or "")
        if not device:
            return _json({"ok": False, "error": "device alias or ip required"})
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            result = bridge.toggle_device(device)
            return _json({"ok": result.get("ok", False), "result": result})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/kasa/set")
    async def api_kasa_set(request: Request) -> JSONResponse:
        """Set Kasa device state (brightness, color, on/off)."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        device = str(body.get("device") or body.get("alias") or body.get("ip") or "")
        if not device:
            return _json({"ok": False, "error": "device alias or ip required"})
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            result = bridge.set_device(
                device,
                state=body.get("state"),
                brightness=body.get("brightness"),
                color_temp=body.get("color_temp"),
                hue=body.get("hue"),
                saturation=body.get("saturation"),
            )
            return _json({"ok": result.get("ok", False), "result": result})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/kasa/stream/start")
    async def api_kasa_stream_start(request: Request) -> JSONResponse:
        """Start an HLS stream from a Kasa camera."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        ip = str(body.get("ip") or "")
        camera_id = str(body.get("camera_id") or body.get("id") or ip or "cam0")
        if not ip:
            return _json({"ok": False, "error": "ip required"})
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            result = bridge.start_hls_stream(ip, camera_id)
            return _json({"ok": result.get("ok", False), "result": result})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/kasa/stream/stop")
    async def api_kasa_stream_stop(request: Request) -> JSONResponse:
        """Stop an HLS camera stream."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        camera_id = str(body.get("camera_id") or body.get("id") or "")
        try:
            from . import kasa_bridge as _kb
        except ImportError:
            try:
                import kasa_bridge as _kb  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            bridge = _kb.KasaBridge(
                username=str(runtime.config.get("KASA_USERNAME", "") or ""),
                password=str(runtime.config.get("KASA_PASSWORD", "") or ""),
            )
            if camera_id:
                bridge.stop_hls_stream(camera_id)
            else:
                bridge.stop_all_streams()
            return _json({"ok": True})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    # ------------------------------------------------------------------
    # KDP (Kindle Direct Publishing) routes
    # ------------------------------------------------------------------

    @app.get("/api/kdp/books")
    async def api_kdp_books() -> JSONResponse:
        """List KDP books from local store."""
        try:
            from . import kdp_store
        except ImportError:
            try:
                import kdp_store  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "books": []})
        try:
            books = kdp_store.load_books()
            return _json({"ok": True, "available": True, "books": books, "count": len(books)})
        except Exception as exc:
            return _json({"ok": False, "available": False, "books": [], "error": str(exc)})

    @app.get("/api/kdp/sales")
    async def api_kdp_sales() -> JSONResponse:
        """KDP sales history from local store."""
        try:
            from . import kdp_store
        except ImportError:
            try:
                import kdp_store  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "sales": []})
        try:
            sales = kdp_store.load_sales_history(limit=90)
            books = kdp_store.load_books()
            insights = kdp_store.generate_insights(books, sales)
            return _json({"ok": True, "available": True, "sales": sales, "insights": insights})
        except Exception as exc:
            return _json({"ok": False, "available": False, "sales": [], "error": str(exc)})

    @app.get("/api/kdp/status")
    async def api_kdp_status() -> JSONResponse:
        """KDP sync and account status."""
        try:
            from . import kdp_store
        except ImportError:
            try:
                import kdp_store  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            status = kdp_store.get_status()
            return _json({"ok": True, "available": True, **status})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.post("/api/kdp/sync")
    async def api_kdp_sync() -> JSONResponse:
        """Trigger a KDP data sync (requires KDP credentials)."""
        try:
            from . import kdp_scraper
        except ImportError:
            try:
                import kdp_scraper  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "message": "KDP scraper unavailable"})
        try:
            if hasattr(kdp_scraper, "sync"):
                result = await kdp_scraper.sync()
                return _json({"ok": True, "result": result})
            return _json({"ok": False, "available": False, "message": "KDP sync requires credentials configured in Settings → Publishing → KDP."})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.get("/api/kdp/sync-status")
    async def api_kdp_sync_status() -> JSONResponse:
        """KDP sync status."""
        try:
            from . import kdp_store
        except ImportError:
            try:
                import kdp_store  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            meta = kdp_store.load_sync_meta()
            return _json({"ok": True, "available": True, **meta})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.get("/api/kdp/credentials")
    async def api_kdp_credentials() -> JSONResponse:
        """Check if KDP credentials are configured."""
        from pathlib import Path as _Path
        creds_path = _Path("data/settings/kdp_credentials.json")
        configured = creds_path.exists() and creds_path.stat().st_size > 10
        return _json({"ok": True, "configured": configured, "available": True})

    @app.post("/api/kdp/2fa-code")
    async def api_kdp_2fa_code(request: Request) -> JSONResponse:
        """Submit a KDP 2FA verification code."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        code = str(body.get("code") or "").strip()
        if not code:
            return _json({"ok": False, "error": "code required"})
        return _json({
            "ok": False,
            "available": False,
            "message": "KDP 2FA submission requires an active browser session. Configure KDP credentials in Settings.",
        })

    # ------------------------------------------------------------------
    # Publishing extended routes — launch-scan, launch/{id}
    # ------------------------------------------------------------------

    @app.get("/api/publishing/launch-scan")
    async def api_publishing_launch_scan() -> JSONResponse:
        """Scan publishing projects for launch readiness."""
        try:
            from . import publishing_suite
        except ImportError:
            try:
                import publishing_suite  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "projects": []})
        try:
            projects = publishing_suite.list_projects() if hasattr(publishing_suite, "list_projects") else []
            return _json({"ok": True, "available": True, "projects": projects, "count": len(projects)})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    @app.get("/api/publishing/launch/{project_id}")
    async def api_publishing_launch_by_id(project_id: str) -> JSONResponse:
        """Get launch control details for a publishing project."""
        try:
            from . import publishing_suite
        except ImportError:
            try:
                import publishing_suite  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False})
        try:
            detail = publishing_suite.get_project(project_id) if hasattr(publishing_suite, "get_project") else {}
            return _json({"ok": bool(detail), "available": True, "project": detail})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    # ------------------------------------------------------------------
    # Identity / profile routes
    # ------------------------------------------------------------------

    @app.get("/api/identity/me")
    async def api_identity_me() -> JSONResponse:
        """Current user identity."""
        try:
            from .identity_registry import IdentityRegistry
        except ImportError:
            try:
                from identity_registry import IdentityRegistry  # type: ignore[no-redef]
            except ImportError:
                IdentityRegistry = None  # type: ignore[assignment, misc]
        try:
            if IdentityRegistry:
                registry = IdentityRegistry()
                me = registry.get_identity("chris") or {}
            else:
                me = {"id": "chris", "name": "Chris", "role": "director"}
            return _json({"ok": True, "identity": me})
        except Exception as exc:
            return _json({"ok": False, "identity": {"id": "chris", "name": "Chris"}, "error": str(exc)})

    @app.get("/api/profile")
    async def api_profile() -> JSONResponse:
        """Current operator profile."""
        try:
            from .user_profile import get_profile
        except ImportError:
            try:
                from user_profile import get_profile  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": True, "profile": {"name": "Chris", "role": "director"}, "available": False})
        try:
            profile = get_profile() if callable(get_profile) else {}
            return _json({"ok": True, "profile": profile, "available": True})
        except Exception as exc:
            return _json({"ok": False, "profile": {}, "error": str(exc)})

    # ------------------------------------------------------------------
    # Costs summary
    # ------------------------------------------------------------------

    @app.get("/api/costs/summary")
    async def api_costs_summary() -> JSONResponse:
        """LLM and API cost summary."""
        try:
            from .llm_gateway import get_cost_summary
        except ImportError:
            try:
                from llm_gateway import get_cost_summary  # type: ignore[no-redef]
            except ImportError:
                return _json({"ok": False, "available": False, "summary": {}})
        try:
            summary = get_cost_summary() if callable(get_cost_summary) else {}
            return _json({"ok": True, "available": True, "summary": summary})
        except Exception as exc:
            return _json({"ok": False, "available": False, "summary": {}, "error": str(exc)})

    # ------------------------------------------------------------------
    # Agent control routes
    # ------------------------------------------------------------------

    @app.post("/api/agent/approve")
    async def api_agent_approve(request: Request) -> JSONResponse:
        """Approve a pending agent action."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        agent_id = str(body.get("agent_id") or "")
        action = str(body.get("action") or "")
        if not agent_id:
            return _json({"ok": False, "error": "agent_id required"})
        try:
            result = runtime.approve_agent_action(agent_id, action) if hasattr(runtime, "approve_agent_action") else {"ok": True, "agent_id": agent_id}
            return _json({"ok": True, "result": result})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc)})

    @app.post("/api/agent/restart-pending")
    async def api_agent_restart_pending(request: Request) -> JSONResponse:
        """Restart agents with pending or stalled work."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            result = runtime.restart_pending_agents() if hasattr(runtime, "restart_pending_agents") else {"ok": True, "restarted": 0}
            return _json({"ok": True, "result": result})
        except Exception as exc:
            return _json({"ok": False, "error": str(exc)})

    @app.get("/api/agent/stream")
    async def api_agent_stream(agent_id: str = "") -> JSONResponse:
        """Stream status for a running agent."""
        if not agent_id:
            return _json({"ok": False, "error": "agent_id required"})
        try:
            result = runtime.get_agent_stream(agent_id) if hasattr(runtime, "get_agent_stream") else {"ok": False, "available": False}
            return _json({"ok": True, "stream": result})
        except Exception as exc:
            return _json({"ok": False, "available": False, "error": str(exc)})

    # ------------------------------------------------------------------
    # Legacy catch-all (MUST be last — any specific POST route defined
    # above takes priority because it's registered first in FastAPI)
    # ------------------------------------------------------------------

    @app.post("/api/{legacy_path:path}")
    async def api_legacy_post(
        legacy_path: str,
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        path = f"/api/{legacy_path}"
        actor = str(payload.get("actor", "Chris"))
        room = str(payload.get("room", "office"))
        request_text = str(payload.get("request", ""))
        try:
            if path in {
                "/api/plan",
                "/api/respond",
                "/api/mode-brief",
                "/api/family-plan",
                "/api/departure-plan",
                "/api/rebekah-center",
                "/api/troop-plan",
                "/api/grocery-support",
                "/api/meal-plan",
                "/api/vehicle-plan",
                "/api/weather-contingency",
            }:
                result = _mode_brief_payload(actor, room, request_text, path, payload)
                if path in {"/api/respond", "/api/family-plan", "/api/rebekah-center", "/api/troop-plan", "/api/grocery-support", "/api/meal-plan", "/api/vehicle-plan", "/api/weather-contingency", "/api/departure-plan"}:
                    background_tasks.add_task(_broadcast_dashboard, "workflow.updated")
                return _json(result)

            if path in {"/api/message-draft", "/api/parent-message", "/api/voice-note"}:
                background_tasks.add_task(_broadcast_dashboard, "communications.updated")
                return _json(_communications_payload(actor, payload, path))

            if path in {
                "/api/room-scene",
                "/api/climate-control",
                "/api/access-control",
                "/api/garage-check",
                "/api/energy-window",
                "/api/mic-ingress",
                "/api/presence-update",
                "/api/phone-presence",
                "/api/camera-event",
                "/api/package-rule",
                "/api/object-recognition",
                "/api/environmental-anomaly",
                "/api/privacy-update",
            }:
                background_tasks.add_task(_broadcast_dashboard, "home.updated")
                return _json(_home_ops_payload(actor, payload, path))

            if path in {"/api/memory-remember", "/api/memory-forget", "/api/memory-approve"}:
                background_tasks.add_task(_broadcast_dashboard, "memory.updated")
                return _json(_memory_payload(actor, payload, path))

            if path.startswith("/api/catalyst-"):
                background_tasks.add_task(_broadcast_dashboard, "catalyst.updated")
                return _json(_catalyst_payload(actor, payload, path))

            if path in {"/api/security-event", "/api/safety-alert", "/api/weather-alert", "/api/child-arrival", "/api/unlock-policy"}:
                background_tasks.add_task(_broadcast_dashboard, "security.updated")
                return _json(_security_payload(actor, payload, path))

            if path in {"/api/devotional-pause", "/api/family-devotional", "/api/chronicle-capture"}:
                background_tasks.add_task(_broadcast_dashboard, "formation.updated")
                return _json(_formation_payload(actor, payload, path))

            if path in {
                "/api/tutor",
                "/api/device-boundary",
            }:
                background_tasks.add_task(_broadcast_dashboard, "tutoring.updated")
                return _json(_tutoring_payload(actor, payload, path, request_text))

            if path in {
                "/api/workshop-plan",
                "/api/concept-studio/chat",
                "/api/material-recommendation",
                "/api/cad-package",
                "/api/print-prep",
                "/api/safety-check",
                "/api/inspect-part",
                "/api/vendor-prep",
            }:
                background_tasks.add_task(_broadcast_dashboard, "workshop.updated")
                return _json(_workshop_payload(actor, payload, path, request_text))

            if path == "/api/executive-task":
                return _json(_executive_payload(actor, payload, path))
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        raise HTTPException(status_code=404, detail="Not found")

    return app


# ── Module-level helper used inside Forge route handlers ──────────────────────
def _forge_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def serve(runtime: JarvisRuntime, host: str, port: int) -> None:
    uvicorn.run(build_app(runtime), host=host, port=port, log_level="warning")
