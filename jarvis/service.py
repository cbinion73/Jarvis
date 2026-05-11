from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from .runtime import JarvisRuntime
from .settings import LocationSettingsStore, VoiceSettingsStore
from .voice_audio import generate_tts_audio
from .voice_ui import render_voice_shell
from .render_pages import render_agent_hierarchy_page, render_agent_workspace_page, render_catalyst_workspace_page


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
    assets_root = Path.cwd() / "assets"
    if assets_root.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_root)), name="assets")

    def _base_url(request: Request) -> str:
        return str(request.base_url).rstrip("/")

    async def _broadcast_dashboard(event_name: str, *, include_dashboard: bool = True) -> None:
        payload: dict[str, Any] = {
            "type": event_name,
            "refresh": True,
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
            tags = [item.strip() for item in str(payload.get("tags", "")).split(",") if item.strip()]
            return runtime.remember(
                actor,
                str(payload.get("type", "household")),
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
            )
        if path == "/api/catalyst-implementation-plan":
            return runtime.catalyst_implementation_plan(
                actor,
                str(payload.get("project_name", "")),
                str(payload.get("brief", "")),
                str(payload.get("constraints", "")),
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
            },
            "openviking": runtime.openviking_status(),
            "brain_graph": runtime.brain_graph_snapshot(),
        }

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        return render_voice_shell(runtime)

    @app.get("/agents/hierarchy", response_class=HTMLResponse)
    async def agent_hierarchy() -> str:
        return render_agent_hierarchy_page(runtime)

    @app.get("/agents/workspace/{agent_id}", response_class=HTMLResponse)
    async def agent_workspace(agent_id: str) -> str:
        return render_agent_workspace_page(runtime, agent_id)

    @app.get("/catalyst/view/{page}", response_class=HTMLResponse)
    async def catalyst_view(page: str) -> str:
        return render_catalyst_workspace_page(runtime, page)

    @app.get("/accounts/{account_id}/connect")
    async def account_connect(account_id: str, request: Request) -> Response:
        connect = runtime.google_connect_url(account_id, _base_url(request))
        if not connect.get("ok"):
            return HTMLResponse(
                f"<html><body><h1>Account connection unavailable</h1><p>{connect.get('detail', 'Unable to start provider login.')}</p></body></html>",
                status_code=400,
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

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        try:
            dashboard = await asyncio.to_thread(runtime.dashboard_snapshot)
            await websocket.send_json({"type": "hello", "dashboard": dashboard})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await hub.disconnect(websocket)
        except Exception:
            await hub.disconnect(websocket)

    @app.get("/api/dashboard")
    async def api_dashboard(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.dashboard_snapshot, actor))

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
        return _json({"actor": actor, "briefing": runtime.morning_brief(actor)})

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
        return _json(runtime.recent_activity())

    @app.get("/api/open-loops")
    async def api_open_loops(actor: str = "Chris", limit: int = 30) -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.unified_open_loops, actor, limit))

    @app.get("/api/today-board")
    async def api_today_board(actor: str = "Chris") -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.today_board, actor))

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
    async def api_connected_devices() -> JSONResponse:
        return _json(runtime.connected_devices_snapshot())

    @app.get("/api/runtime-service")
    async def api_runtime_service() -> JSONResponse:
        return _json(await asyncio.to_thread(runtime.runtime_service_status))

    @app.get("/api/persona-snapshot")
    async def api_persona_snapshot(actor: str = "Chris", device_id: str = "", refresh: bool = False) -> JSONResponse:
        return _json(runtime.build_persona_snapshot(actor, device_id=device_id, refresh=refresh))

    @app.get("/api/location-settings")
    async def api_location_settings() -> JSONResponse:
        return _json(location_settings.describe())

    @app.get("/api/design-review-state")
    async def api_design_review_state() -> JSONResponse:
        return _json(runtime.design_review_state())

    @app.get("/api/google/status")
    async def api_google_status() -> JSONResponse:
        return _json(runtime.google_workspace_status())

    @app.get("/api/google/summary")
    async def api_google_summary() -> JSONResponse:
        return _json(runtime.google_workspace_summary())

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

    @app.get("/api/agent-registry")
    async def api_agent_registry() -> JSONResponse:
        return _json(runtime.agent_registry_snapshot())

    @app.get("/api/memory-curator")
    async def api_memory_curator() -> JSONResponse:
        return _json(runtime.memory_curator_snapshot())

    @app.get("/api/catalyst-overview")
    async def api_catalyst_overview() -> JSONResponse:
        return _json(runtime.catalyst_overview())

    @app.get("/api/google/account/{account_id}")
    async def api_google_account(account_id: str) -> JSONResponse:
        return _json(runtime.google_account_snapshot(account_id))

    @app.get("/api/explainability")
    async def api_explainability(actor: str = "Chris") -> JSONResponse:
        return _json(runtime.explainability_snapshot(actor))

    @app.get("/api/approval-history")
    async def api_approval_history() -> JSONResponse:
        return _json(runtime.approval_history())

    @app.get("/api/mode")
    async def api_mode() -> JSONResponse:
        return _json(runtime.active_mode())

    @app.get("/api/message-drafts")
    async def api_message_drafts() -> JSONResponse:
        return _json(runtime.list_message_drafts())

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
        result = runtime.respond(
            str(payload.get("actor", "Chris")),
            str(payload.get("room", "office")),
            str(payload.get("request", "")),
        )
        background_tasks.add_task(_broadcast_dashboard, "response.completed")
        return _json({"provider": result.provider, "model": result.model, "output_text": result.output_text})

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
        try:
            if action == "add_location":
                state = location_settings.add_location(payload)
            elif action == "set_preferred":
                state = location_settings.set_preferred_location(str(payload.get("location_id", "")).strip())
            elif action == "save_device_location":
                state = location_settings.save_device_location(payload)
            else:
                state = location_settings.save(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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

    @app.post("/api/identity/session")
    async def api_bind_identity_session(payload: dict[str, Any]) -> JSONResponse:
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

    @app.post("/api/google/disconnect")
    async def api_google_disconnect() -> JSONResponse:
        return _json(runtime.google_disconnect())

    @app.post("/api/accounts/{account_id}/disconnect")
    async def api_google_disconnect_account(account_id: str) -> JSONResponse:
        return _json(runtime.google_disconnect_account(account_id))

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

    @app.post("/api/finance-state")
    async def api_save_finance_state(payload: dict[str, Any]) -> JSONResponse:
        actor = str(payload.get("actor", "Chris"))
        patch = dict(payload.get("state", {})) if isinstance(payload.get("state", {}), dict) else {}
        result = runtime.wealth_support.update_finance_state(patch)
        runtime._invalidate_snapshot_cache(actor, surfaces=("finance_review", "finance_state", "dashboard", "today_board", "cognitive"))
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

    @app.post("/api/vendor-preps/{prep_id}")
    async def api_update_vendor_prep(prep_id: str, payload: dict[str, Any]) -> JSONResponse:
        updated = runtime.update_vendor_prep_status(prep_id, str(payload.get("status", "staged")))
        if updated is None:
            raise HTTPException(status_code=404, detail="Vendor prep not found")
        return _json(updated)

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


def serve(runtime: JarvisRuntime, host: str, port: int) -> None:
    uvicorn.run(build_app(runtime), host=host, port=port, log_level="warning")
