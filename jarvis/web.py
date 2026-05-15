from __future__ import annotations

import json
import mimetypes
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .render_pages import render_agent_hierarchy_page, render_catalyst_workspace_page
from .runtime import JarvisRuntime
from .settings import LocationSettingsStore, VoiceSettingsStore
from .voice_audio import generate_tts_audio
from .voice_ui import render_voice_shell


def create_handler(runtime: JarvisRuntime) -> type[BaseHTTPRequestHandler]:
    asset_root = Path.cwd() / "assets"
    voice_settings = VoiceSettingsStore(runtime.config)
    location_settings = LocationSettingsStore(runtime.config)

    class JarvisHandler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path.startswith("/catalyst/view/"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path == "/agents/hierarchy":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path.startswith("/assets/"):
                candidate = (asset_root / parsed.path.removeprefix("/assets/")).resolve()
                try:
                    candidate.relative_to(asset_root.resolve())
                except ValueError:
                    self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                    return
                if not candidate.exists() or not candidate.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                    return
                content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(candidate.stat().st_size))
                self.end_headers()
                return
            if parsed.path.startswith("/accounts/") and parsed.path.endswith("/connect"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path == "/google/connect":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path.startswith("/api/"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(render_voice_shell(runtime))
                return
            if parsed.path.startswith("/catalyst/view/"):
                page = parsed.path.removeprefix("/catalyst/view/").strip("/") or "home"
                self._send_html(render_catalyst_workspace_page(runtime, page))
                return
            if parsed.path == "/agents/hierarchy":
                self._send_html(render_agent_hierarchy_page(runtime))
                return
            if parsed.path.startswith("/accounts/") and parsed.path.endswith("/connect"):
                account_id = parsed.path.split("/")[2]
                connect = runtime.google_connect_url(account_id, self._base_url())
                if not connect.get("ok"):
                    self._send_html(self._callback_page("Account connection unavailable", str(connect.get("detail", "Unable to start provider login.")), success=False))
                    return
                self._redirect(str(connect["authorization_url"]))
                return
            if parsed.path == "/google/connect":
                self._send_html(self._callback_page("Account required", "Select a specific account in Settings first. JARVIS now keeps personal accounts separated by user.", success=False))
                return
            if parsed.path == "/google/callback":
                params = parse_qs(parsed.query)
                code = params.get("code", [""])[0]
                state = params.get("state", [""])[0]
                result = runtime.google_handle_callback(self._base_url(), code, state)
                self._send_html(
                    self._callback_page(
                        "Google connected" if result.get("ok") else "Google connection failed",
                        str(result.get("detail", "Unknown Google callback state.")),
                        success=bool(result.get("ok")),
                    )
                )
                return
            if parsed.path.startswith("/assets/"):
                candidate = (asset_root / parsed.path.removeprefix("/assets/")).resolve()
                try:
                    candidate.relative_to(asset_root.resolve())
                except ValueError:
                    self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                    return
                if not candidate.exists() or not candidate.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                    return
                content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
                self._send_bytes(candidate.read_bytes(), content_type=content_type)
                return
            if parsed.path == "/api/summary":
                self._send_json(
                    {
                        "household": runtime.household.household_name,
                        "location": runtime.household.location_label,
                        "users": [u.display_name for u in runtime.household.users.values()],
                        "modes": runtime.household.modes,
                    }
                )
                return
            if parsed.path == "/api/dashboard":
                self._send_json(runtime.dashboard_snapshot())
                return
            if parsed.path == "/api/agents":
                self._send_json(runtime.background_agent_status())
                return
            if parsed.path == "/api/agent-registry":
                self._send_json(runtime.agent_registry_snapshot())
                return
            if parsed.path == "/api/life-agents":
                self._send_json(runtime.life_agent_snapshot())
                return
            if parsed.path == "/api/memory-curator":
                self._send_json(runtime.memory_curator_snapshot())
                return
            if parsed.path == "/api/catalyst-overview":
                self._send_json(runtime.catalyst_overview())
                return
            if parsed.path == "/api/accounts":
                self._send_json(runtime.account_registry_snapshot())
                return
            if parsed.path == "/api/design-review-state":
                self._send_json(runtime.design_review_state())
                return
            if parsed.path == "/api/google/status":
                self._send_json(runtime.google_workspace_status())
                return
            if parsed.path == "/api/google/summary":
                self._send_json(runtime.google_workspace_summary())
                return
            if parsed.path.startswith("/api/google/account/"):
                account_id = parsed.path.rsplit("/", 1)[-1]
                self._send_json(runtime.google_account_snapshot(account_id))
                return
            if parsed.path == "/api/explainability":
                self._send_json(runtime.explainability_snapshot())
                return
            if parsed.path == "/api/approval-history":
                self._send_json(runtime.approval_history())
                return
            if parsed.path == "/api/mode":
                self._send_json(runtime.active_mode())
                return
            if parsed.path == "/api/message-drafts":
                self._send_json(runtime.list_message_drafts())
                return
            if parsed.path == "/api/trust-zones":
                self._send_json({"zones": runtime.list_trust_zones()})
                return
            if parsed.path == "/api/resource-arenas":
                self._send_json({"arenas": runtime.list_resource_arenas()})
                return
            if parsed.path == "/api/authority-stages":
                self._send_json({"stages": runtime.list_authority_stages()})
                return
            if parsed.path == "/api/stage/queue":
                self._send_json({"items": runtime.list_stage_queue()})
                return
            if parsed.path == "/api/voice-notes":
                self._send_json(runtime.list_voice_note_tasks())
                return
            if parsed.path == "/api/anomalies":
                self._send_json(runtime.anomaly_watch())
                return
            if parsed.path == "/api/security-incidents":
                self._send_json(runtime.list_security_incidents())
                return
            if parsed.path == "/api/overnight-review":
                self._send_json(runtime.overnight_review())
                return
            if parsed.path == "/api/home-overview":
                self._send_json(runtime.home_overview())
                return
            if parsed.path == "/api/leak-monitor":
                self._send_json(runtime.leak_monitor())
                return
            if parsed.path == "/api/cold-storage-monitor":
                self._send_json(runtime.cold_storage_monitor())
                return
            if parsed.path == "/api/outage-readiness":
                self._send_json(runtime.outage_readiness())
                return
            if parsed.path == "/api/perception-overview":
                self._send_json(runtime.perception_overview())
                return
            if parsed.path == "/api/privacy-state":
                self._send_json(runtime.privacy_state())
                return
            if parsed.path == "/api/memory-overview":
                viewer = parse_qs(parsed.query).get("viewer", ["Chris"])[0]
                self._send_json(runtime.memory_overview(viewer))
                return
            if parsed.path == "/api/memory-review":
                params = parse_qs(parsed.query)
                self._send_json(
                    runtime.review_memory(
                        params.get("viewer", ["Chris"])[0],
                        memory_type=params.get("type", [""])[0],
                        owner=params.get("owner", [""])[0],
                        project=params.get("project", [""])[0],
                    )
                )
                return
            if parsed.path == "/api/memory-proposals":
                status = parse_qs(parsed.query).get("status", [""])[0]
                self._send_json(runtime.memory_proposals(status=status))
                return
            if parsed.path == "/api/printer-status":
                self._send_json(runtime.printer_status())
                return
            if parsed.path == "/api/workshop-inspections":
                self._send_json(runtime.list_workshop_inspections())
                return
            if parsed.path == "/api/cad-packages":
                self._send_json(runtime.list_cad_packages())
                return
            if parsed.path == "/api/print-preps":
                self._send_json(runtime.list_print_preps())
                return
            if parsed.path == "/api/vendor-preps":
                self._send_json(runtime.list_vendor_preps())
                return
            if parsed.path == "/api/child-boundaries":
                actor = parse_qs(parsed.query).get("actor", [""])[0]
                self._send_json(runtime.child_boundaries(actor_name=actor or None))
                return
            if parsed.path == "/api/tutoring-summaries":
                params = parse_qs(parsed.query)
                viewer = params.get("viewer", ["Rebekah"])[0]
                child = params.get("child", [""])[0]
                limit = int(params.get("limit", ["10"])[0])
                self._send_json(runtime.tutoring_summaries(viewer, child_name=child, limit=limit))
                return
            if parsed.path == "/api/device-boundaries":
                params = parse_qs(parsed.query)
                child = params.get("child", [""])[0]
                limit = int(params.get("limit", ["10"])[0])
                self._send_json(runtime.list_device_boundaries(child_name=child, limit=limit))
                return
            if parsed.path == "/api/status":
                self._send_json(runtime.status())
                return
            if parsed.path == "/api/approvals":
                self._send_json(runtime.list_pending_approvals())
                return
            if parsed.path == "/api/activity":
                self._send_json(runtime.recent_activity())
                return
            if parsed.path == "/api/briefing":
                actor = parse_qs(parsed.query).get("actor", ["Chris"])[0]
                self._send_json({"actor": actor, "briefing": runtime.morning_brief(actor)})
                return
            if parsed.path == "/api/voice-settings":
                self._send_json(voice_settings.describe())
                return
            if parsed.path == "/api/voice-options":
                self._send_json(voice_settings.voice_options())
                return
            if parsed.path == "/api/location-settings":
                self._send_json(location_settings.describe())
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/tts":
                payload = self._read_json()
                text = str(payload.get("text", "")).strip()
                if not text:
                    self.send_error(HTTPStatus.BAD_REQUEST, "Text is required")
                    return
                try:
                    audio = generate_tts_audio(
                        runtime.config,
                        text,
                        voice_settings=voice_settings.load().to_dict(),
                    )
                except RuntimeError as exc:
                    self.send_error(HTTPStatus.BAD_GATEWAY, str(exc))
                    return
                self._send_bytes(
                    audio.data,
                    content_type=audio.content_type,
                    extra_headers={"X-Jarvis-Tts-Provider": audio.provider},
                )
                return
            if parsed.path == "/api/voice-settings":
                payload = self._read_json()
                settings = voice_settings.save(payload)
                self._send_json(
                    {
                        "message": "Voice settings updated.",
                        "settings": voice_settings.describe(),
                        "options": voice_settings.voice_options(),
                        "saved": settings.to_dict(),
                    }
                )
                return
            if parsed.path == "/api/location-settings":
                payload = self._read_json()
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
                    self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                self._send_json({"ok": True, "state": location_settings.describe(), "saved": state})
                return
            if parsed.path == "/api/google/client-secret":
                payload = self._read_json()
                self._send_json(runtime.google_save_client_secret(str(payload.get("client_secret_json", ""))))
                return
            if parsed.path == "/api/accounts":
                payload = self._read_json()
                self._send_json(runtime.save_personal_account(payload))
                return
            if parsed.path == "/api/life-agents":
                payload = self._read_json()
                self._send_json(runtime.save_life_agent(payload))
                return
            if parsed.path == "/api/life-agents/delete":
                payload = self._read_json()
                self._send_json(runtime.delete_life_agent(str(payload.get("agent_id", ""))))
                return
            if parsed.path == "/api/life-party":
                payload = self._read_json()
                self._send_json(
                    runtime.life_party_mode(
                        str(payload.get("actor", "Chris")),
                        str(payload.get("room", "office")),
                        str(payload.get("request", "")),
                        [str(entry).strip() for entry in payload.get("agents", []) if str(entry).strip()],
                    )
                )
                return
            if parsed.path == "/api/design-review-state":
                payload = self._read_json()
                self._send_json(runtime.save_design_review_state(payload))
                return
            if parsed.path == "/api/mode-transition":
                payload = self._read_json()
                self._send_json(
                    runtime.transition_mode(
                        str(payload.get("actor", "Chris")),
                        str(payload.get("mode", "ambient-associate")),
                        str(payload.get("reason", "Manual mode update from JARVIS shell.")),
                    )
                )
                return
            if parsed.path == "/api/google/disconnect":
                self._send_json(runtime.google_disconnect())
                return
            if parsed.path.startswith("/api/accounts/") and parsed.path.endswith("/disconnect"):
                account_id = parsed.path.split("/")[3]
                self._send_json(runtime.google_disconnect_account(account_id))
                return
            if parsed.path in {"/api/plan", "/api/respond", "/api/mode-brief", "/api/family-plan", "/api/departure-plan", "/api/rebekah-center", "/api/troop-plan", "/api/grocery-support", "/api/meal-plan", "/api/vehicle-plan", "/api/weather-contingency", "/api/message-draft", "/api/parent-message", "/api/voice-note", "/api/security-event", "/api/safety-alert", "/api/weather-alert", "/api/child-arrival", "/api/unlock-policy", "/api/tutor", "/api/device-boundary", "/api/workshop-plan", "/api/material-recommendation", "/api/cad-package", "/api/print-prep", "/api/safety-check", "/api/inspect-part", "/api/vendor-prep", "/api/executive-task", "/api/devotional-pause", "/api/family-devotional", "/api/chronicle-capture", "/api/room-scene", "/api/climate-control", "/api/access-control", "/api/garage-check", "/api/energy-window", "/api/mic-ingress", "/api/presence-update", "/api/phone-presence", "/api/camera-event", "/api/package-rule", "/api/object-recognition", "/api/environmental-anomaly", "/api/privacy-update", "/api/memory-remember", "/api/memory-forget", "/api/memory-approve", "/api/catalyst-signal", "/api/catalyst-email-triage", "/api/catalyst-meeting-prep", "/api/catalyst-meeting-extract", "/api/catalyst-briefing", "/api/catalyst-draft", "/api/catalyst-project-brief", "/api/catalyst-hypothesis", "/api/catalyst-implementation-plan", "/api/catalyst-proactive"}:
                payload = self._read_json()
                actor = payload.get("actor", "Chris")
                room = payload.get("room", "office")
                request_text = payload.get("request", "")
                if parsed.path == "/api/plan":
                    plan = runtime.plan_request(actor, room, request_text)
                    self._send_json(
                        {
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
                            "rationale": plan.rationale,
                        }
                    )
                    return
                if parsed.path == "/api/mode-brief":
                    self._send_json(runtime.family_mode_brief(payload.get("mode", "")))
                    return
                if parsed.path == "/api/family-plan":
                    self._send_json({"actor": actor, "output_text": runtime.family_plan(actor, request_text)})
                    return
                if parsed.path == "/api/departure-plan":
                    self._send_json(runtime.departure_plan(actor, payload.get("context", "")))
                    return
                if parsed.path == "/api/rebekah-center":
                    self._send_json({"actor": "Rebekah", "output_text": runtime.rebekah_command_center(request_text)})
                    return
                if parsed.path == "/api/troop-plan":
                    self._send_json({"actor": actor, "output_text": runtime.troop_plan(actor, request_text)})
                    return
                if parsed.path == "/api/grocery-support":
                    self._send_json({"actor": actor, "output_text": runtime.grocery_support(actor, request_text)})
                    return
                if parsed.path == "/api/meal-plan":
                    self._send_json(runtime.meal_plan(actor, request_text))
                    return
                if parsed.path == "/api/vehicle-plan":
                    self._send_json(runtime.vehicle_plan(actor, request_text))
                    return
                if parsed.path == "/api/weather-contingency":
                    self._send_json(runtime.weather_contingency(actor, request_text))
                    return
                if parsed.path == "/api/message-draft":
                    self._send_json(
                        runtime.draft_message(
                            actor,
                            payload["audience"],
                            payload["purpose"],
                            payload["context"],
                            payload.get("tone", "warm"),
                        )
                    )
                    return
                if parsed.path == "/api/parent-message":
                    self._send_json(
                        runtime.stage_parent_message(
                            actor,
                            payload["audience"],
                            payload["purpose"],
                            payload["context"],
                            payload.get("tone", "warm"),
                        )
                    )
                    return
                if parsed.path == "/api/voice-note":
                    self._send_json(
                        runtime.capture_voice_note(
                            actor,
                            payload.get("source", "van"),
                            payload.get("note", ""),
                        )
                    )
                    return
                if parsed.path == "/api/room-scene":
                    self._send_json(
                        runtime.room_scene(
                            actor,
                            payload.get("room", ""),
                            payload.get("scene", ""),
                            intent=payload.get("intent", ""),
                        )
                    )
                    return
                if parsed.path == "/api/climate-control":
                    self._send_json(
                        runtime.climate_control(
                            actor,
                            payload.get("zone", ""),
                            payload.get("mode", "heat_cool"),
                            target_temperature=payload.get("target_temp"),
                            context=payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/access-control":
                    self._send_json(
                        runtime.access_control(
                            actor,
                            payload.get("target", ""),
                            payload.get("state", ""),
                        )
                    )
                    return
                if parsed.path == "/api/garage-check":
                    self._send_json(
                        runtime.garage_safe_close(
                            actor,
                            payload.get("target", ""),
                        )
                    )
                    return
                if parsed.path == "/api/energy-window":
                    self._send_json(
                        runtime.energy_window(
                            payload.get("appliance", ""),
                            request_text=payload.get("request", ""),
                        )
                    )
                    return
                if parsed.path == "/api/mic-ingress":
                    self._send_json(
                        runtime.microphone_ingress(
                            payload.get("microphone", ""),
                            payload.get("transcript", ""),
                            wake_word_detected=payload.get("wake_word", False),
                            actor_hint=payload.get("actor_hint", ""),
                        )
                    )
                    return
                if parsed.path == "/api/presence-update":
                    self._send_json(
                        runtime.presence_update(
                            payload.get("sensor", ""),
                            payload.get("room", ""),
                            bool(payload.get("occupied", False)),
                            detail=payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/phone-presence":
                    self._send_json(
                        runtime.phone_presence_update(
                            actor,
                            payload.get("device", ""),
                            payload.get("state", ""),
                            zone=payload.get("zone", ""),
                            detail=payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/camera-event":
                    self._send_json(
                        runtime.camera_event(
                            payload.get("camera", ""),
                            payload.get("event_type", ""),
                            payload.get("detail", ""),
                            detected_object=payload.get("object", ""),
                            confidence=payload.get("confidence", "medium"),
                        )
                    )
                    return
                if parsed.path == "/api/package-rule":
                    self._send_json(
                        runtime.package_rule(
                            payload.get("zone", ""),
                            payload.get("preferred_drop", ""),
                            bool(payload.get("rain_sensitive", False)),
                            note=payload.get("note", ""),
                        )
                    )
                    return
                if parsed.path == "/api/object-recognition":
                    self._send_json(
                        runtime.object_recognition(
                            payload.get("source", ""),
                            payload.get("room", ""),
                            payload.get("object", ""),
                            detail=payload.get("detail", ""),
                            confidence=payload.get("confidence", "medium"),
                        )
                    )
                    return
                if parsed.path == "/api/environmental-anomaly":
                    self._send_json(
                        runtime.environmental_anomaly(
                            payload.get("category", ""),
                            payload.get("source", ""),
                            payload.get("reading", ""),
                            payload.get("baseline", ""),
                            severity=payload.get("severity", "watch"),
                            detail=payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/privacy-update":
                    self._send_json(
                        runtime.update_privacy_state(
                            payload.get("kind", ""),
                            payload.get("target", ""),
                            enabled=payload.get("enabled"),
                            muted=payload.get("muted"),
                        )
                    )
                    return
                if parsed.path == "/api/memory-remember":
                    tags = [item.strip() for item in str(payload.get("tags", "")).split(",") if item.strip()]
                    self._send_json(
                        runtime.remember(
                            actor,
                            payload.get("type", "household"),
                            payload.get("scope", "household"),
                            payload.get("summary", ""),
                            payload.get("detail", ""),
                            owner=payload.get("owner", ""),
                            project=payload.get("project", ""),
                            tags=tags,
                            sensitivity=payload.get("sensitivity", "normal"),
                        )
                    )
                    return
                if parsed.path == "/api/memory-forget":
                    self._send_json(
                        runtime.forget_memory(
                            payload.get("viewer", "Chris"),
                            payload.get("entry_id", ""),
                        )
                    )
                    return
                if parsed.path == "/api/memory-approve":
                    self._send_json(
                        runtime.resolve_memory_proposal(
                            payload.get("proposal_id", ""),
                            payload.get("decision", "approved"),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-signal":
                    tags = [item.strip() for item in str(payload.get("tags", "")).split(",") if item.strip()]
                    self._send_json(
                        runtime.catalyst_capture_signal(
                            actor,
                            payload.get("source", "manual"),
                            payload.get("title", ""),
                            payload.get("content", ""),
                            sender=payload.get("sender", ""),
                            tags=tags,
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-email-triage":
                    self._send_json(
                        runtime.catalyst_email_triage(
                            actor,
                            payload.get("subject", ""),
                            payload.get("body", ""),
                            payload.get("sender", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-meeting-prep":
                    self._send_json(
                        runtime.catalyst_meeting_prep(
                            actor,
                            payload.get("meeting_title", ""),
                            payload.get("open_commitments", []),
                            payload.get("recent_signals", []),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-meeting-extract":
                    self._send_json(
                        runtime.catalyst_meeting_extraction(
                            actor,
                            payload.get("transcript", ""),
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-briefing":
                    self._send_json(
                        runtime.catalyst_briefing(
                            actor,
                            payload.get("user_context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-draft":
                    self._send_json(
                        runtime.catalyst_draft(
                            actor,
                            payload.get("intent", ""),
                            payload.get("context", ""),
                            payload.get("recipient", ""),
                            payload.get("tone", "professional"),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-project-brief":
                    self._send_json(
                        runtime.catalyst_project_brief(
                            actor,
                            payload.get("project_name", ""),
                            payload.get("problem", ""),
                            payload.get("desired_outcome", ""),
                            payload.get("constraints", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-hypothesis":
                    self._send_json(
                        runtime.catalyst_hypothesis_generation(
                            actor,
                            payload.get("focus", ""),
                            payload.get("context", ""),
                            payload.get("lane", ""),
                            payload.get("supporting_signals", []),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-implementation-plan":
                    self._send_json(
                        runtime.catalyst_implementation_plan(
                            actor,
                            payload.get("project_name", ""),
                            payload.get("brief", ""),
                            payload.get("constraints", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-proactive":
                    self._send_json(
                        runtime.catalyst_proactive_surfacing(
                            actor,
                            payload.get("horizon", "today"),
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/security-event":
                    self._send_json(
                        runtime.package_or_motion_monitor(
                            actor,
                            payload.get("category", "motion"),
                            payload.get("location", ""),
                            payload.get("detail", ""),
                            severity=payload.get("severity", "watch"),
                        )
                    )
                    return
                if parsed.path == "/api/safety-alert":
                    self._send_json(
                        runtime.safety_escalation(
                            actor,
                            payload.get("hazard", "smoke"),
                            payload.get("source", ""),
                            payload.get("detail", ""),
                            severity=payload.get("severity", "critical"),
                        )
                    )
                    return
                if parsed.path == "/api/weather-alert":
                    self._send_json(
                        runtime.weather_advisory(
                            actor,
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/child-arrival":
                    self._send_json(
                        runtime.child_arrival(
                            actor,
                            payload.get("location", "front door"),
                            payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/unlock-policy":
                    self._send_json(
                        runtime.unlock_assessment(
                            actor,
                            payload.get("target", "front door"),
                            requested_by_voice=payload.get("requested_by_voice", True),
                            second_factor_present=payload.get("second_factor_present", False),
                        )
                    )
                    return
                if parsed.path == "/api/devotional-pause":
                    self._send_json(
                        {
                            "actor": actor,
                            "output_text": runtime.devotional_pause(
                                actor,
                                payload.get("theme", ""),
                                payload.get("mode", "scripture"),
                            ),
                        }
                    )
                    return
                if parsed.path == "/api/family-devotional":
                    self._send_json(
                        {
                            "actor": actor,
                            "output_text": runtime.family_devotional_prep(
                                actor,
                                payload.get("theme", ""),
                                payload.get("context", ""),
                            ),
                        }
                    )
                    return
                if parsed.path == "/api/chronicle-capture":
                    self._send_json(
                        runtime.chronicle_capture(
                            actor,
                            payload.get("theme", ""),
                            payload.get("note", ""),
                        )
                    )
                    return
                if parsed.path == "/api/tutor":
                    self._send_json(
                        runtime.tutor(
                            actor,
                            request_text,
                            subject=payload.get("subject", ""),
                        )
                    )
                    return
                if parsed.path == "/api/device-boundary":
                    self._send_json(
                        runtime.device_boundary_plan(
                            actor,
                            window_label=payload.get("window", ""),
                        )
                    )
                    return
                if parsed.path == "/api/workshop-plan":
                    self._send_json({"actor": actor, "output_text": runtime.workshop_plan(actor, request_text)})
                    return
                if parsed.path == "/api/material-recommendation":
                    self._send_json(
                        runtime.material_recommendation(
                            actor,
                            payload["part"],
                            payload["use_case"],
                            payload.get("requirements", ""),
                        )
                    )
                    return
                if parsed.path == "/api/cad-package":
                    self._send_json(
                        runtime.cad_package(
                            actor,
                            payload["part"],
                            payload.get("dimensions", ""),
                            payload.get("constraints", ""),
                        )
                    )
                    return
                if parsed.path == "/api/print-prep":
                    self._send_json(
                        runtime.print_prep(
                            actor,
                            payload["part"],
                            payload["printer"],
                            payload["material"],
                            payload.get("profile", "functional-prototype"),
                            payload.get("notes", ""),
                        )
                    )
                    return
                if parsed.path == "/api/safety-check":
                    self._send_json(
                        runtime.safety_check(
                            actor,
                            payload["operation"],
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/inspect-part":
                    self._send_json(
                        runtime.inspect_part(
                            actor,
                            payload["part"],
                            request_text or "Inspect this part and recommend a prototype path.",
                            payload.get("observations", ""),
                            payload.get("goals", ""),
                            image_path=payload.get("image_path", ""),
                        )
                    )
                    return
                if parsed.path == "/api/vendor-prep":
                    self._send_json(
                        runtime.vendor_prep(
                            actor,
                            payload["part"],
                            payload["vendor"],
                            payload["process"],
                            payload["material"],
                            payload.get("notes", ""),
                        )
                    )
                    return
                if parsed.path == "/api/executive-task":
                    task = payload.get("task", "")
                    if task == "decision-framework":
                        self._send_json(
                            {
                                "actor": actor,
                                "task": task,
                                "output_text": runtime.decision_framework(actor, payload.get("primary", "")),
                            }
                        )
                        return
                    if task == "ironclad-editor":
                        self._send_json(
                            {
                                "actor": actor,
                                "task": task,
                                "output_text": runtime.iron_clad_editor(actor, payload.get("primary", "")),
                            }
                        )
                        return
                    if task == "venture-brief":
                        self._send_json(
                            {
                                "actor": actor,
                                "task": task,
                                "output_text": runtime.venture_brief(
                                    actor,
                                    payload.get("topic", "venture monitoring"),
                                    payload.get("secondary", "") or payload.get("primary", ""),
                                ),
                            }
                        )
                        return
                    self.send_error(HTTPStatus.BAD_REQUEST, "Unknown executive task")
                    return
                result = runtime.respond(actor, room, request_text)
                self._send_json({"provider": result.provider, "model": result.model, "output_text": result.output_text})
                return

            if parsed.path.startswith("/api/approvals/"):
                request_id = parsed.path.rsplit("/", 1)[-1]
                payload = self._read_json()
                updated = runtime.update_approval(request_id, payload.get("status", "pending"))
                if updated is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Approval request not found")
                    return
                self._send_json(updated)
                return

            if parsed.path.startswith("/api/message-drafts/"):
                draft_id = parsed.path.rsplit("/", 1)[-1]
                payload = self._read_json()
                updated = runtime.update_message_draft(draft_id, payload.get("status", "staged"))
                if updated is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Message draft not found")
                    return
                self._send_json(updated)
                return

            if parsed.path == "/api/stage/email/draft":
                payload = self._read_json()
                try:
                    result = runtime.stage_email_draft(payload)
                except KeyError:
                    self.send_error(HTTPStatus.NOT_FOUND, "Unknown trust-zone arena")
                    return
                except (TypeError, ValueError):
                    self.send_error(HTTPStatus.BAD_REQUEST, "Invalid email draft staging payload")
                    return
                self._send_json(result, status=201)
                return

            if parsed.path == "/api/trust-zones":
                payload = self._read_json()
                try:
                    result = runtime.create_trust_zone(payload)
                except (KeyError, TypeError, ValueError):
                    self.send_error(HTTPStatus.BAD_REQUEST, "Invalid trust zone payload")
                    return
                self._send_json(result, status=201)
                return

            if parsed.path == "/api/resource-arenas":
                payload = self._read_json()
                try:
                    result = runtime.create_resource_arena(payload)
                except (KeyError, TypeError, ValueError):
                    self.send_error(HTTPStatus.BAD_REQUEST, "Invalid resource arena payload")
                    return
                self._send_json(result, status=201)
                return

            if parsed.path.startswith("/api/vendor-preps/"):
                prep_id = parsed.path.rsplit("/", 1)[-1]
                payload = self._read_json()
                updated = runtime.update_vendor_prep_status(prep_id, payload.get("status", "staged"))
                if updated is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Vendor prep not found")
                    return
                self._send_json(updated)
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return None

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            return json.loads(body)

        def _send_json(self, payload: object, status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)

        def _send_html(self, html: str) -> None:
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)

        def _send_bytes(
            self,
            payload: bytes,
            content_type: str,
            status: int = 200,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def _redirect(self, location: str) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def _base_url(self) -> str:
            host = self.headers.get("Host", "127.0.0.1:8787")
            return f"http://{host}"

        def _callback_page(self, title: str, detail: str, *, success: bool) -> str:
            safe_title = escape(title)
            safe_detail = escape(detail)
            accent = "#6cffaf" if success else "#ffcc70"
            return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #07111a;
      color: #eef7ff;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
    }}
    .card {{
      width: min(560px, 92vw);
      padding: 28px;
      border: 1px solid rgba(111, 229, 255, 0.22);
      background: rgba(8, 18, 30, 0.92);
      box-shadow: 0 24px 72px rgba(0, 0, 0, 0.38);
      border-radius: 16px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 28px;
      color: {accent};
    }}
    p {{
      margin: 0;
      line-height: 1.55;
      color: #bfd2e4;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{safe_title}</h1>
    <p>{safe_detail}</p>
  </div>
</body>
</html>"""

    return JarvisHandler


def serve(runtime: JarvisRuntime, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), create_handler(runtime))
    print(f"JARVIS dashboard running on http://{host}:{port}")
    server.serve_forever()
