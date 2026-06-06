from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
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
from .apple_api import _register_apple_api
from .audit import AuditLog, ProgressFocusStore, ProgressSnapshotStore, RecoveryActionStore
from . import layout_engine as _layout_engine
from .recovery_cases import RecoveryCaseStore

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
        # Glass is the default. Only an explicit ?theme=nexus query param overrides it.
        if theme == "nexus" and _NEXUS_THEME_AVAILABLE:
            return _render_nexus_shell(runtime, initial_packet=packet)
        if _GLASS_THEME_AVAILABLE:
            return _render_glass_shell(runtime, initial_packet=packet)
        return render_voice_shell(runtime, initial_packet=packet)

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

    @app.get("/chronicle-center", response_class=HTMLResponse)
    async def chronicle_center() -> HTMLResponse:
        return HTMLResponse(render_chronicle_module_page(await _build_chronicle_module_payload()))

    @app.get("/navigation-center", response_class=HTMLResponse)
    async def navigation_center() -> HTMLResponse:
        return HTMLResponse(render_navigation_module_page(await _build_navigation_module_payload()))

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
            "remains_partial": "Cross-surface navigation continuity and stronger auditability still need follow-on slices.",
            "navigation_state": {},
            "saved_locations": [],
            "route_preview": {"summary": "", "hazard_active": False, "sections": []},
            "recent_activity": [],
            "proof_paths": {
                "module_route": "/navigation-center",
                "module_api": "/api/navigation/module",
                "route_api": "/api/navigation/module/route",
                "state_api": "/api/navigation/module/state",
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
        from .apple_api import _save_navigation_state, _NAV_STOP_LABELS, _nav_bridge, _nav_nps_along_route, _nav_route_points, _nav_state_codes
        from .nav_bridge import haversine, sample_route_points

        route_packet = runtime.storm_route_weather(origin, destination)
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
            _save_navigation_state(
                {
                    "parks_historic_radius_miles": parks_historic_radius_miles,
                    "last_route": {"origin": origin, "destination": destination},
                    "recent_destinations": [destination],
                }
            )
        return {
            "origin": origin,
            "destination": destination,
            "summary": str(route_packet.get("summary") or ""),
            "hazard_active": bool(route_packet.get("hazard_active")),
            "route": route_packet.get("route") if isinstance(route_packet, dict) else {},
            "sections": sections,
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

    @app.get("/agents/hierarchy", response_class=HTMLResponse)
    async def agent_hierarchy() -> str:
        return render_agent_hierarchy_page(runtime)

    @app.get("/agents/workspace/{agent_id}", response_class=HTMLResponse)
    async def agent_workspace(agent_id: str) -> str:
        return render_agent_workspace_page(runtime, agent_id)

    @app.get("/catalyst/view/{page}", response_class=HTMLResponse)
    async def catalyst_view(page: str) -> str:
        return render_catalyst_workspace_page(runtime, page)

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
            "remains_partial": "Deeper briefing-specific action loops and broader module drill-ins still need follow-on slices, but open-loop actions now feed shared continuity back into Daily Brief.",
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
        return {
            "generated_at": command_center.get("generated_at", ""),
            "available": True,
            "status": "Useful",
            "summary": "Progress now has a dedicated module route with live readiness rows, seam posture, lane state, and failure evidence inside JARVIS.",
            "what_became_real": "Progress is now represented as a standalone app module instead of only a command-center panel.",
            "remains_partial": "Richer route-to-route progress actions and deeper per-module mutation flows still need follow-on slices, but progress history now persists durably.",
            "progress_dashboard": progress_dashboard,
            "seam_tracker": seam_tracker,
            "level3_checklist": level3_checklist,
            "lane_progress": lane_progress,
            "failure_recovery": failure_recovery,
            "hosted_deployment": hosted_deployment,
            "core_modules": core_modules,
            "progress_persistence": persistence_summary,
            "focus_control": focus_summary,
            "counts": {
                "useful": int(counts.get("useful", 0) or 0),
                "wired": int(counts.get("wired", 0) or 0),
                "durable": int(counts.get("durable", 0) or 0),
                "compounding": int(counts.get("compounding", 0) or 0),
                "seam_count": int(seam_tracker.get("item_count", 0) or 0),
                "history_count": int(persistence_summary.get("history_count", 0) or 0),
                "focus_history_count": int(focus_summary.get("history_count", 0) or 0),
            },
            "progress_next_focus": next_focus or "No next progress focus recorded yet.",
            "latest_progress_snapshot": persisted_snapshot,
            "proof_paths": {
                "module_route": "/progress-center",
                "module_api": "/api/progress/module",
                "focus_api": "/api/progress/focus",
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
            },
        }

    @app.get("/api/progress/module")
    async def api_progress_module() -> JSONResponse:
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
            "recovery_bridge": recovery_bridge,
            "recent_activity": recent_activity,
            "counts": {
                "needs_review_count": len(what_needs_me),
                "pending_approval_count": len(attention_queue),
                "integration_issue_count": issue_count,
                "memory_proposal_count": int(memory.get("proposal_count", 0) or 0),
                "registered_agent_count": int(registry.get("agent_count", 0) or 0),
                "recovery_bridge_count": int(recovery_bridge.get("count", 0) or 0),
                "recent_activity_count": len(recent_activity),
            },
            "proof_paths": {
                "module_route": "/supervision-snapshot",
                "module_api": "/api/supervision/module",
                "legacy_snapshot_api": "/api/supervision-snapshot",
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
            "summary": summary,
            "what_became_real": "Failure & Recovery is now a standalone app module with durable retry, approval execution, and stabilization actions plus visible continuity into the linked approval, supervision, activity, and command-center routes.",
            "remains_partial": "Automated remediation still needs follow-on slices, but retry, approval execution, stabilization actions, and durable non-approval recovery cases are now represented across the recovery stack.",
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
            },
            "proof_paths": {
                "module_route": "/recovery-center",
                "module_api": "/api/recovery/module",
                "recovery_action_api": "/api/recovery/action",
                "recovery_case_api_prefix": "/api/recovery/cases/",
                "recovery_case_execute_suffix": "/execute",
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
            enriched_activity.append(bridge_entry)
        for item in activity_feed:
            enriched = dict(item)
            enriched["source_kind"] = str(item.get("entry_type", "")).strip() or "activity"
            enriched["detail"] = str(item.get("result", "")).strip() or str(item.get("subtitle", "")).strip()
            enriched["related_route"] = str(item.get("related_route", "")).strip() or related_route_for(enriched)
            enriched["route_label"] = str(item.get("route_label", "")).strip() or "Open Related Surface"
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
            "remains_partial": "Richer event mutation, deeper audit filtering, and broader cross-module resume continuity still need follow-on slices.",
            "home_action_result": home_action_result,
            "activity_feed": enriched_activity,
            "action_journal": action_journal,
            "counts": {
                "activity_count": len(enriched_activity),
                "journal_count": len(enriched_journal),
                "home_bridge_count": 1 if bridge else 0,
                "focus_history_count": int(focus_summary.get("history_count", 0) or 0),
            },
            "focus_control": focus_summary,
            "progress_next_focus": str((focus_summary.get("latest") or {}).get("module") or "").strip() or "No next progress focus recorded yet.",
            "proof_paths": {
                "module_route": "/activity-center",
                "module_api": "/api/activity/module",
                "activity_api": "/api/activity",
                "activity_focus_api": "/api/activity/module/focus",
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
            "summary": "Settings now has a dedicated module route with live voice, location, account, and permissions posture inside JARVIS.",
            "what_became_real": "Settings & Permissions is now a standalone app module instead of only a shell packet with scattered APIs behind it.",
            "remains_partial": "Broader connector actions, richer identity/account edits, and deeper cross-surface continuity still need follow-on slices.",
            "voice": {},
            "voice_options": {},
            "location": {},
            "accounts": {"accounts": []},
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
    async def api_memory_proposals(status: str = "") -> JSONResponse:
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

    @app.post("/api/approvals/{request_id}")
    async def api_update_approval(request_id: str, payload: dict[str, Any]) -> JSONResponse:
        updated = runtime.update_approval(request_id, str(payload.get("status", "pending")))
        if updated is None:
            raise HTTPException(status_code=404, detail="Approval request not found")
        return _json(updated)

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
        return _json({"status": "approved", "review": result, "focus": focus_entry})

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
        return _json({"status": "needs_revision", "review": result, "focus": focus_entry})

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
        result = await asyncio.to_thread(db.get_dashboard_data)
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
                "ideas_api": "/api/huddle/ideas",
                "idea_queue_api": "/api/huddle/ideas/{idea_id}/queue",
                "idea_pass_api": "/api/huddle/ideas/{idea_id}/pass",
                "idea_research_api": "/api/huddle/ideas/{idea_id}/research-now",
                "dossiers_api": "/api/dossiers",
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
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["summary"] = "Huddle center route is live, but standup aggregation did not fully hydrate."
            payload["remains_partial"] = "Live huddle standup sources still need repair or population in this runtime."
            payload["errors"].append(f"standups: {exc}")

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

        try:
            from .party_mode import get_party_controller

            payload["party_mode"] = get_party_controller(runtime).get_status()
        except Exception as exc:
            payload["errors"].append(f"party_mode: {exc}")

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
        except Exception as exc:
            payload["errors"].append(f"dossiers: {exc}")

        try:
            from .ideas import list_ideas, stats

            summary = stats()
            ideas = list_ideas()
            by_status = dict(summary.get("by_status") or {})
            payload["idea_inbox"] = {
                "total": int(summary.get("total") or 0),
                "captured_count": int(by_status.get("captured") or 0),
                "queued_count": int(by_status.get("queued") or 0),
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
        except Exception as exc:
            payload["errors"].append(f"ideas: {exc}")

        if payload["status"] == "Useful":
            payload["summary"] = (
                f"Huddle center loaded {len(payload['reports'])} standup report(s), "
                f"{payload['approvals_count']} approval item(s), and {payload['ready_dossier_count']} ready dossier(s)."
            )
            if not payload["reports"]:
                payload["status"] = "Wired"
                payload["remains_partial"] = "The dedicated Huddle screen is live, but no standup reports were available in this runtime."

        payload["recent_activity"] = _module_recent_activity(route="/huddle-center", domain="huddle")
        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some huddle sources still failed to hydrate; inspect the payload preview for details."
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
            "remains_partial": "Deeper Chronicle review workflows, richer study surfaces, and broader external handoff continuity still need follow-on slices.",
            "entry_count": 0,
            "pending_entry_count": 0,
            "timeline": [],
            "theme_summary": {"themes": [], "entries_considered": 0},
            "morning_context": {},
            "workflow_status": {},
            "insights": [],
            "recent_activity": [],
            "bridge_status": "not_loaded",
            "bridge_note": "Chronicle bridge is not initialised in this runtime.",
            "proof_paths": {
                "module_route": "/chronicle-center",
                "module_api": "/api/chronicle/module",
                "status_api": "/api/chronicle/status",
                "capture_api": "/api/chronicle-capture",
                "devotional_api": "/api/devotional-pause",
                "family_devotional_api": "/api/family-devotional",
                "activity_api": "/api/activity/operator-action",
            },
            "errors": [],
        }

        try:
            if callable(getattr(runtime, "chronicle_timeline", None)):
                timeline = runtime.chronicle_timeline(limit=10)
                payload["timeline"] = timeline if isinstance(timeline, list) else []
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

        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some Chronicle sources still failed to hydrate; inspect the payload preview for details."
        return payload

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
        }

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
            "remains_partial": "Cross-launch continuity, richer drill-ins, and broader publishing controls still need follow-on slices.",
            "project_count": 0,
            "active_project_count": 0,
            "review_count": 0,
            "pending_reviews_count": 0,
            "scheduled_post_count": 0,
            "overdue_calendar_count": 0,
            "projects": [],
            "pending_reviews": [],
            "launch_workspace": None,
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
                "calendar_api": "/api/publishing/calendar",
                "social_api": "/api/publishing/social/posts",
            },
            "errors": [],
        }

        try:
            pending_reviews = _pending_publishing_reviews()
            payload["pending_reviews"] = pending_reviews
            payload["review_count"] = len(pending_reviews)
            payload["pending_reviews_count"] = len(pending_reviews)
            if pending_reviews:
                payload["available"] = True
        except Exception as exc:
            payload["errors"].append(f"publishing_reviews: {exc}")

        if pub is None:
            if payload["pending_reviews_count"]:
                payload["status"] = "Useful"
                payload["summary"] = "Publish route is live with pending editorial reviews, even though broader publishing sources are not fully initialised in this runtime."
            payload["recent_activity"] = _module_recent_activity(route="/publish", domain="publish")
            return payload

        payload["status"] = "Useful"
        payload["summary"] = "Publish now has a dedicated route with live projects, launch control, calendar, social, and revenue posture."

        try:
            projects = list(pub._store.list_projects())
            payload["projects"] = [project.to_dict() for project in projects[:8]]
            payload["project_count"] = len(projects)
            payload["active_project_count"] = sum(1 for project in projects if str(getattr(project, "status", "")).strip() not in {"", "archived", "completed"})
        except Exception as exc:
            payload["errors"].append(f"projects: {exc}")

        try:
            upcoming = list(pub.calendar.get_upcoming(14))
            overdue = list(pub.calendar.get_overdue())
            payload["calendar"] = {
                "upcoming": [item.to_dict() for item in upcoming[:8]],
                "overdue": [item.to_dict() for item in overdue[:4]],
            }
            payload["overdue_calendar_count"] = len(overdue)
        except Exception as exc:
            payload["errors"].append(f"calendar: {exc}")

        try:
            posts = list(pub._store.get_scheduled_posts())
            payload["social"] = {"posts": [post.to_dict() for post in posts[:8]]}
            payload["scheduled_post_count"] = len(posts)
        except Exception as exc:
            payload["errors"].append(f"social: {exc}")

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

        payload["recent_activity"] = _module_recent_activity(route="/publish", domain="publish")
        if payload["errors"]:
            payload["remains_partial"] = "Some publishing sources still failed to hydrate; see errors in the payload preview."
        return payload

    @app.get("/api/publish/module")
    async def api_publish_module() -> JSONResponse:
        return _json(_build_publish_module_payload())

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
        result = await asyncio.to_thread(db.get_dashboard_data)
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
            "remains_partial": "Deeper health workflows, historical review, and broader manual data entry still need follow-on slices.",
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
            payload["summary"] = f"Health center loaded {len(current_signals)} current signal(s) with {len(list(drift_scan.get('active_clusters') or []))} active drift cluster(s)."
            if not current_signals:
                payload["status"] = "Wired"
                payload["remains_partial"] = "The dedicated Health screen is live, but current signal sources are still sparse in this runtime."
        except Exception as exc:
            payload["status"] = "Wired"
            payload["available"] = False
            payload["errors"].append(f"drift: {exc}")
            payload["summary"] = "Health center route is live, but drift and signal sources did not fully hydrate."
            payload["remains_partial"] = "Live health sources still need repair or population in this runtime."

        try:
            from .quarterly_review import get_current_objectives

            objectives = await get_current_objectives()
            payload["objectives"] = objectives
            payload["objective_count"] = len(objectives)
        except Exception as exc:
            payload["errors"].append(f"objectives: {exc}")

        try:
            from .symptom_triage import get_red_flags_for_patient

            payload["red_flags"] = get_red_flags_for_patient()
        except Exception as exc:
            payload["errors"].append(f"red_flags: {exc}")

        payload["recent_activity"] = _module_recent_activity(route="/health-center", domain="health")

        if payload["errors"] and payload["status"] == "Useful":
            payload["remains_partial"] = "Some health sources still failed to hydrate; inspect the payload preview for details."
        return payload

    @app.get("/api/health/module")
    async def api_health_module() -> JSONResponse:
        return _json(await _build_health_module_payload())

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

    return app


# ── Module-level helper used inside Forge route handlers ──────────────────────
def _forge_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def serve(runtime: JarvisRuntime, host: str, port: int) -> None:
    uvicorn.run(build_app(runtime), host=host, port=port, log_level="warning")
