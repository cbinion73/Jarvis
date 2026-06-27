from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for cold systems
    def load_dotenv() -> None:
        return None

from .agent_registry_contract import contract_paths, load_contract_bundle
from .config import AppConfig
from .openclaw_bridge import build_openclaw_envelope, envelope_to_json
from .speech import voice_stack_status
from .fresh_start import FreshStartProtocol

if TYPE_CHECKING:
    from .runtime import JarvisRuntime

try:
    from .scheduler import init_scheduler as _init_scheduler
    _SCHEDULER_IMPORT_OK = True
except Exception:  # pragma: no cover
    _SCHEDULER_IMPORT_OK = False

    def _init_scheduler(runtime):  # type: ignore[misc]
        return None, None

try:
    from .approvals import init_approvals as _init_approvals
    _APPROVALS_IMPORT_OK = True
except Exception:  # pragma: no cover
    _APPROVALS_IMPORT_OK = False

    def _init_approvals(*args, **kwargs):  # type: ignore[misc]
        return None, None

try:
    from .data_connectors import init_connectors as _init_connectors
    _CONNECTORS_IMPORT_OK = True
except Exception:  # pragma: no cover
    _CONNECTORS_IMPORT_OK = False

    def _init_connectors(config):  # type: ignore[misc]
        return None

try:
    from .known_facts import init_memory as _init_memory
    _KNOWN_FACTS_IMPORT_OK = True
except Exception:  # pragma: no cover
    _KNOWN_FACTS_IMPORT_OK = False

    def _init_memory():  # type: ignore[misc]
        return None

try:
    from .chronicle_bridge import init_chronicle_bridge as _init_chronicle_bridge
    _CHRONICLE_BRIDGE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _CHRONICLE_BRIDGE_IMPORT_OK = False

    def _init_chronicle_bridge(chronicle_client=None, memory_store=None):  # type: ignore[misc]
        return None, None

try:
    from .catalyst_db import init_catalyst_db as _init_catalyst_db
    from .work_intelligence import init_work_intelligence as _init_work_intelligence
    from .agent_catalyst import ensure_all_agents_registered as _ensure_agents_catalyst
    _WORK_INTELLIGENCE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _WORK_INTELLIGENCE_IMPORT_OK = False

    def _init_catalyst_db(*a, **kw):  # type: ignore[misc]
        return None

    def _init_work_intelligence(*a, **kw):  # type: ignore[misc]
        return None

    def _ensure_agents_catalyst():  # type: ignore[misc]
        pass

try:
    from .voice import JarvisVoiceShell, build_voice_parser
    VOICE_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - optional dependency path
    JarvisVoiceShell = None  # type: ignore[assignment]
    VOICE_IMPORT_ERROR = exc

    def build_voice_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[misc]
        parser = subparsers.add_parser("voice", help="Run JARVIS voice and text conversation surfaces")
        parser.set_defaults(_voice_unavailable=True)

try:
    from .voice_pipeline import init_voice as _init_voice
    _VOICE_PIPELINE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _VOICE_PIPELINE_IMPORT_OK = False

    def _init_voice(config):  # type: ignore[misc]
        return None

try:
    from .publishing_suite import init_publishing as _init_publishing
    _PUBLISHING_IMPORT_OK = True
except Exception:  # pragma: no cover
    _PUBLISHING_IMPORT_OK = False

    def _init_publishing(runtime=None):  # type: ignore[misc]
        return None

try:
    from .family_profiles import init_family as _init_family, get_family_manager as _get_family_manager
    _FAMILY_PROFILES_IMPORT_OK = True
except Exception:  # pragma: no cover
    _FAMILY_PROFILES_IMPORT_OK = False

    def _init_family(runtime=None):  # type: ignore[misc]
        return None

    def _get_family_manager():  # type: ignore[misc]
        return None

try:
    from .workshop_copilot import init_workshop as _init_workshop
    _WORKSHOP_COPILOT_IMPORT_OK = True
except Exception:  # pragma: no cover
    _WORKSHOP_COPILOT_IMPORT_OK = False

    def _init_workshop(runtime=None):  # type: ignore[misc]
        return None

try:
    from .financial_intelligence import init_finance as _init_finance
    _FINANCIAL_INTELLIGENCE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _FINANCIAL_INTELLIGENCE_IMPORT_OK = False

    def _init_finance(runtime=None):  # type: ignore[misc]
        return None

try:
    from .growth_intelligence import init_growth as _init_growth
    _GROWTH_INTELLIGENCE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _GROWTH_INTELLIGENCE_IMPORT_OK = False

    def _init_growth(runtime=None):  # type: ignore[misc]
        return None

try:
    from .llm_gateway import init_gateway as _init_gateway
    _LLM_GATEWAY_IMPORT_OK = True
except Exception:  # pragma: no cover
    _LLM_GATEWAY_IMPORT_OK = False

    def _init_gateway(config=None):  # type: ignore[misc]
        return None

try:
    from .ghostwritr_bridge import init_ghostwritr_bridge as _init_ghostwritr_bridge
    _GHOSTWRITR_BRIDGE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _GHOSTWRITR_BRIDGE_IMPORT_OK = False

    def _init_ghostwritr_bridge():  # type: ignore[misc]
        return None

try:
    from .social_engine import init_social_engine as _init_social_engine
    _SOCIAL_ENGINE_IMPORT_OK = True
except Exception:  # pragma: no cover
    _SOCIAL_ENGINE_IMPORT_OK = False

    def _init_social_engine():  # type: ignore[misc]
        return None


# ── Home Intelligence (email, calendar, projects, tasks) ──────────────────────
try:
    from .home_projects import init_home_db as _init_home_db
    from .gmail_bridge import init_gmail_bridge as _init_gmail_bridge
    from .gcal_bridge import init_gcal_bridge as _init_gcal_bridge
    from .outlook_bridge import init_outlook_bridge as _init_outlook_bridge
    from .cozi_bridge import init_cozi_bridge as _init_cozi_bridge
    from .unified_inbox import init_unified_inbox as _init_unified_inbox
    from .signal_router import init_signal_router as _init_signal_router
    _HOME_INTELLIGENCE_IMPORT_OK = True
except Exception as _home_exc:  # pragma: no cover
    import logging as _log
    _log.getLogger("jarvis.main").warning("Home intelligence imports failed: %s", _home_exc)
    _HOME_INTELLIGENCE_IMPORT_OK = False

    def _init_home_db(db_url): return None  # type: ignore[misc]
    def _init_gmail_bridge(**kw): return None  # type: ignore[misc]
    def _init_gcal_bridge(**kw): return None  # type: ignore[misc]
    def _init_outlook_bridge(**kw): return None  # type: ignore[misc]
    def _init_cozi_bridge(**kw): return None  # type: ignore[misc]
    def _init_unified_inbox(**kw): return None  # type: ignore[misc]
    def _init_signal_router(**kw): return None  # type: ignore[misc]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS household runtime scaffold")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="Show configured household runtime summary")
    fresh_start = subparsers.add_parser("fresh-start", help="Preview or execute a fresh-start reset and rebuild protocol")
    fresh_start.add_argument("--execute", action="store_true", help="Actually wipe derived user state and rebuild from preserved sources.")
    fresh_start.add_argument("--no-backup", action="store_true", help="Skip the backup snapshot before deleting reset targets.")
    subparsers.add_parser("status", help="Check integration status")
    subparsers.add_parser("runtime-posture", help="Show always-on runtime posture and real-device integration truth")
    subparsers.add_parser("approvals", help="List pending approvals")
    subparsers.add_parser("voice-stack", help="Show configured STT/TTS provider order and readiness")
    subparsers.add_parser("brain-status", help="Show primary and second-brain status plus active graph state")
    subparsers.add_parser("agent-registry", help="Show the configured background agent registry")
    subparsers.add_parser("agent-registry-contract", help="Validate and show the canonical agent registry contract")
    subparsers.add_parser("agent-status", help="Show the current awake, idle, or blocked state of background agents")
    subparsers.add_parser("agent-runtime", help="Show the durable lifecycle and heartbeat state of the agent runtime kernel")
    agent_runtime_control = subparsers.add_parser("agent-runtime-control", help="Apply a lifecycle control action to a runtime agent")
    agent_runtime_control.add_argument("--agent-id", required=True)
    agent_runtime_control.add_argument("--action", required=True, choices=["wake", "pause", "resume", "interrupt", "escalate", "retire", "retire-now"])
    agent_runtime_control.add_argument("--actor", default="Chris")
    agent_runtime_control.add_argument("--reason", default="")
    agent_runtime_control.add_argument("--execution-lane", default="")
    subparsers.add_parser("memory-curator", help="Show memory curator rules and current curation candidates")
    assistant_notifications = subparsers.add_parser("assistant-notifications", help="Show assistant notifications for an actor")
    assistant_notifications.add_argument("--actor", default="Chris")
    assistant_notifications.add_argument("--unread-only", action="store_true")
    assistant_notifications.add_argument("--limit", type=int, default=12)
    assistant_autonomy = subparsers.add_parser("assistant-autonomy-run", help="Run a background assistant autonomy sweep")
    assistant_autonomy.add_argument("--actor", action="append", dest="actors")
    assistant_autonomy_daemon = subparsers.add_parser("assistant-autonomy-daemon", help="Run the assistant autonomy sweep in a persistent loop")
    assistant_autonomy_daemon.add_argument("--actor", action="append", dest="actors")
    assistant_autonomy_daemon.add_argument("--interval-seconds", type=int, default=600)
    subparsers.add_parser("openviking-status", help="Show OpenViking context backend readiness")
    subparsers.add_parser("catalyst-overview", help="Show the personal-safe Catalyst backend overview")
    subparsers.add_parser("google-status", help="Show Google Workspace connector readiness")
    subparsers.add_parser("google-summary", help="Show Gmail unread mail and upcoming calendar events")

    serve_parser = subparsers.add_parser("serve", help="Run the JARVIS local dashboard")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8787)

    briefing = subparsers.add_parser("briefing", help="Generate a morning briefing")
    briefing.add_argument("--actor", default="Chris")

    plan = subparsers.add_parser("plan", help="Plan a household request")
    plan.add_argument("--actor", default="Chris")
    plan.add_argument("--room", default="office")
    plan.add_argument("--request", required=True)

    respond = subparsers.add_parser("respond", help="Plan and answer with OpenAI")
    respond.add_argument("--actor", default="Chris")
    respond.add_argument("--room", default="office")
    respond.add_argument("--request", required=True)

    meeting_brief = subparsers.add_parser("meeting-brief", help="Build a meeting prep brief")
    meeting_brief.add_argument("--actor", default="Chris")
    meeting_brief.add_argument("--context")
    meeting_brief.add_argument("--context-file")

    meeting_followup = subparsers.add_parser("meeting-followup", help="Build a meeting follow-up matrix")
    meeting_followup.add_argument("--actor", default="Chris")
    meeting_followup.add_argument("--transcript")
    meeting_followup.add_argument("--transcript-file")

    decision_framework = subparsers.add_parser("decision-framework", help="Build decision criteria and framing for a drifting meeting")
    decision_framework.add_argument("--actor", default="Chris")
    decision_framework.add_argument("--context")
    decision_framework.add_argument("--context-file")

    research_summary = subparsers.add_parser("research-summary", help="Build an evidence-tiered research summary")
    research_summary.add_argument("--actor", default="Chris")
    research_summary.add_argument("--topic", required=True)
    research_summary.add_argument("--notes")
    research_summary.add_argument("--notes-file")

    confidentiality = subparsers.add_parser("confidentiality-review", help="Redact and flag sensitive work text")
    confidentiality.add_argument("--text")
    confidentiality.add_argument("--text-file")

    manuscript = subparsers.add_parser("manuscript-review", help="Review a manuscript excerpt")
    manuscript.add_argument("--actor", default="Chris")
    manuscript.add_argument("--excerpt")
    manuscript.add_argument("--excerpt-file")

    iron_clad = subparsers.add_parser("ironclad-editor", help="Run the Iron-Clad Executive Editor protocol")
    iron_clad.add_argument("--actor", default="Chris")
    iron_clad.add_argument("--excerpt")
    iron_clad.add_argument("--excerpt-file")

    venture_brief = subparsers.add_parser("venture-brief", help="Build a venture and market-monitoring brief")
    venture_brief.add_argument("--actor", default="Chris")
    venture_brief.add_argument("--topic", required=True)
    venture_brief.add_argument("--notes")
    venture_brief.add_argument("--notes-file")

    devotional = subparsers.add_parser("devotional-pause", help="Generate a Chronicle devotional pause")
    devotional.add_argument("--actor", default="Chris")
    devotional.add_argument("--theme", required=True)
    devotional.add_argument("--mode", default="scripture")

    family_devotional = subparsers.add_parser("family-devotional", help="Prepare a family devotional")
    family_devotional.add_argument("--actor", default="Chris")
    family_devotional.add_argument("--theme", required=True)
    family_devotional.add_argument("--context")
    family_devotional.add_argument("--context-file")

    chronicle_capture = subparsers.add_parser("chronicle-capture", help="Store a Chronicle reflection entry")
    chronicle_capture.add_argument("--actor", default="Chris")
    chronicle_capture.add_argument("--theme", required=True)
    chronicle_capture.add_argument("--note")
    chronicle_capture.add_argument("--note-file")

    chronicle_timeline = subparsers.add_parser("chronicle-timeline", help="Show recent Chronicle entries")
    chronicle_timeline.add_argument("--limit", type=int, default=10)

    chronicle_themes = subparsers.add_parser("chronicle-themes", help="Summarize recurring prayer and reflection themes")
    chronicle_themes.add_argument("--limit", type=int, default=25)

    mode_status = subparsers.add_parser("mode-status", help="Show the active household mode")

    mode_transition = subparsers.add_parser("mode-transition", help="Set the active household mode")
    mode_transition.add_argument("--actor", default="Chris")
    mode_transition.add_argument("--mode", required=True)
    mode_transition.add_argument("--reason", required=True)

    mode_brief = subparsers.add_parser("mode-brief", help="Show the current or requested household mode brief")
    mode_brief.add_argument("--mode", default="")

    family_plan = subparsers.add_parser("family-plan", help="Generate a family logistics plan")
    family_plan.add_argument("--actor", default="Rebekah")
    family_plan.add_argument("--request")
    family_plan.add_argument("--request-file")

    departure_plan = subparsers.add_parser("departure-plan", help="Build a leaving-the-house choreography plan")
    departure_plan.add_argument("--actor", default="Rebekah")
    departure_plan.add_argument("--context", default="")
    departure_plan.add_argument("--context-file")

    rebekah_center = subparsers.add_parser("rebekah-center", help="Build Rebekah's household coordination brief")
    rebekah_center.add_argument("--request")
    rebekah_center.add_argument("--request-file")

    troop_plan = subparsers.add_parser("troop-plan", help="Prepare a troop meeting plan")
    troop_plan.add_argument("--actor", default="Rebekah")
    troop_plan.add_argument("--request")
    troop_plan.add_argument("--request-file")

    grocery_support = subparsers.add_parser("grocery-support", help="Plan groceries and a low-complexity meal")
    grocery_support.add_argument("--actor", default="Rebekah")
    grocery_support.add_argument("--request")
    grocery_support.add_argument("--request-file")

    meal_plan = subparsers.add_parser("meal-plan", help="Create a structured meal and grocery grouping plan")
    meal_plan.add_argument("--actor", default="Rebekah")
    meal_plan.add_argument("--request")
    meal_plan.add_argument("--request-file")

    vehicle_plan = subparsers.add_parser("vehicle-plan", help="Assign a vehicle and route posture for household logistics")
    vehicle_plan.add_argument("--actor", default="Chris")
    vehicle_plan.add_argument("--request")
    vehicle_plan.add_argument("--request-file")

    weather_contingency = subparsers.add_parser("weather-contingency", help="Build a weather-aware household contingency plan")
    weather_contingency.add_argument("--actor", default="Rebekah")
    weather_contingency.add_argument("--request")
    weather_contingency.add_argument("--request-file")

    message_draft = subparsers.add_parser("message-draft", help="Stage an outbound family message draft")
    message_draft.add_argument("--actor", default="Rebekah")
    message_draft.add_argument("--audience", required=True)
    message_draft.add_argument("--purpose", required=True)
    message_draft.add_argument("--context")
    message_draft.add_argument("--context-file")
    message_draft.add_argument("--tone", default="warm")

    message_drafts = subparsers.add_parser("message-drafts", help="List staged family message drafts")
    message_drafts.add_argument("--limit", type=int, default=10)

    parent_message = subparsers.add_parser("parent-message", help="Stage a parent-facing message for approval")
    parent_message.add_argument("--actor", default="Rebekah")
    parent_message.add_argument("--audience", required=True)
    parent_message.add_argument("--purpose", required=True)
    parent_message.add_argument("--context")
    parent_message.add_argument("--context-file")
    parent_message.add_argument("--tone", default="warm")

    subparsers.add_parser("anomaly-watch", help="Show current household anomalies and watch items")

    security_event = subparsers.add_parser("security-event", help="Record package or unusual-motion monitoring")
    security_event.add_argument("--actor", default="Chris")
    security_event.add_argument("--category", choices=["package", "motion"], required=True)
    security_event.add_argument("--location", required=True)
    security_event.add_argument("--detail")
    security_event.add_argument("--detail-file")
    security_event.add_argument("--severity", default="watch")

    safety_alert = subparsers.add_parser("safety-alert", help="Escalate smoke, CO, or leak alerts")
    safety_alert.add_argument("--actor", default="Chris")
    safety_alert.add_argument("--hazard", choices=["smoke", "co", "leak"], required=True)
    safety_alert.add_argument("--source", required=True)
    safety_alert.add_argument("--detail")
    safety_alert.add_argument("--detail-file")
    safety_alert.add_argument("--severity", default="critical")

    weather_alert = subparsers.add_parser("weather-alert", help="Generate a weather timing advisory")
    weather_alert.add_argument("--actor", default="Chris")
    weather_alert.add_argument("--context")
    weather_alert.add_argument("--context-file")

    child_arrival = subparsers.add_parser("child-arrival", help="Record a child arrival or safe-home event")
    child_arrival.add_argument("--actor", required=True)
    child_arrival.add_argument("--location", default="front door")
    child_arrival.add_argument("--detail")
    child_arrival.add_argument("--detail-file")

    unlock_policy = subparsers.add_parser("unlock-policy", help="Evaluate no-unlock-with-voice-only enforcement")
    unlock_policy.add_argument("--actor", default="Chris")
    unlock_policy.add_argument("--target", required=True)
    unlock_policy.add_argument("--not-voice", action="store_true")
    unlock_policy.add_argument("--second-factor", action="store_true")

    overnight_review = subparsers.add_parser("overnight-review", help="Show the overnight watchtower review")

    security_incidents = subparsers.add_parser("security-incidents", help="List recent security incidents")
    security_incidents.add_argument("--limit", type=int, default=10)

    subparsers.add_parser("home-overview", help="Show the staged house nervous system overview")

    room_scene = subparsers.add_parser("room-scene", help="Apply a room scene or practical lighting intent")
    room_scene.add_argument("--actor", default="Chris")
    room_scene.add_argument("--room", required=True)
    room_scene.add_argument("--scene", required=True)
    room_scene.add_argument("--intent", default="")

    subparsers.add_parser("climate-status", help="Show climate entities and current state")

    climate_control = subparsers.add_parser("climate-control", help="Stage a climate mode or temperature change")
    climate_control.add_argument("--actor", default="Chris")
    climate_control.add_argument("--zone", required=True)
    climate_control.add_argument("--mode", required=True)
    climate_control.add_argument("--target-temp", type=float)
    climate_control.add_argument("--context", default="")

    subparsers.add_parser("access-overview", help="Show lock and monitored door state")

    access_control = subparsers.add_parser("access-control", help="Stage a lock or monitored-door state change")
    access_control.add_argument("--actor", default="Chris")
    access_control.add_argument("--target", required=True)
    access_control.add_argument("--state", required=True)

    subparsers.add_parser("garage-status", help="Show configured garage state and safety attributes")

    garage_check = subparsers.add_parser("garage-check", help="Run a garage safe-close check")
    garage_check.add_argument("--actor", default="Chris")
    garage_check.add_argument("--target", default="")

    subparsers.add_parser("leak-monitor", help="Show leak sensor summary")
    subparsers.add_parser("cold-storage-monitor", help="Show freezer and fridge variance status")

    energy_window = subparsers.add_parser("energy-window", help="Recommend an energy-aware appliance window")
    energy_window.add_argument("--appliance", required=True)
    energy_window.add_argument("--request", default="")

    subparsers.add_parser("outage-readiness", help="Show the outage resilience posture")

    subparsers.add_parser("perception-overview", help="Show the ambient sensing and perception overview")

    mic_ingress = subparsers.add_parser("mic-ingress", help="Record a far-field microphone ingress event")
    mic_ingress.add_argument("--microphone", required=True)
    mic_ingress.add_argument("--transcript", required=True)
    mic_ingress.add_argument("--wake-word", action="store_true")
    mic_ingress.add_argument("--actor-hint", default="")

    presence_update = subparsers.add_parser("presence-update", help="Record a room presence sensor update")
    presence_update.add_argument("--sensor", required=True)
    presence_update.add_argument("--room", required=True)
    presence_update.add_argument("--occupied", action="store_true")
    presence_update.add_argument("--detail", default="")

    phone_presence = subparsers.add_parser("phone-presence", help="Record a phone-based presence update")
    phone_presence.add_argument("--actor", required=True)
    phone_presence.add_argument("--device", default="")
    phone_presence.add_argument("--state", required=True)
    phone_presence.add_argument("--zone", default="")
    phone_presence.add_argument("--detail", default="")

    camera_event = subparsers.add_parser("camera-event", help="Record a camera event for workshop, porch, or garage")
    camera_event.add_argument("--camera", required=True)
    camera_event.add_argument("--event-type", required=True)
    camera_event.add_argument("--detail", required=True)
    camera_event.add_argument("--object", default="")
    camera_event.add_argument("--confidence", default="medium")

    package_rule = subparsers.add_parser("package-rule", help="Update a package-detection drop rule")
    package_rule.add_argument("--zone", required=True)
    package_rule.add_argument("--preferred-drop", required=True)
    package_rule.add_argument("--rain-sensitive", action="store_true")
    package_rule.add_argument("--note", default="")

    object_recognition = subparsers.add_parser("object-recognition", help="Record a workshop or room object recognition event")
    object_recognition.add_argument("--source", required=True)
    object_recognition.add_argument("--room", required=True)
    object_recognition.add_argument("--object", required=True)
    object_recognition.add_argument("--detail", default="")
    object_recognition.add_argument("--confidence", default="medium")

    anomaly = subparsers.add_parser("environmental-anomaly", help="Record an environmental or appliance anomaly")
    anomaly.add_argument("--category", required=True)
    anomaly.add_argument("--source", required=True)
    anomaly.add_argument("--reading", required=True)
    anomaly.add_argument("--baseline", required=True)
    anomaly.add_argument("--severity", default="watch")
    anomaly.add_argument("--detail", default="")

    subparsers.add_parser("privacy-state", help="Show current microphone and camera privacy state")

    privacy_update = subparsers.add_parser("privacy-update", help="Change camera enabled state or microphone mute state")
    privacy_update.add_argument("--kind", choices=["camera", "microphone"], required=True)
    privacy_update.add_argument("--target", required=True)
    privacy_update.add_argument("--enabled", choices=["true", "false"])
    privacy_update.add_argument("--muted", choices=["true", "false"])

    memory_overview = subparsers.add_parser("memory-overview", help="Show the memory-core overview and schema")
    memory_overview.add_argument("--viewer", default="Chris")

    memory_remember = subparsers.add_parser("memory-remember", help="Store a memory entry or create a sensitive proposal")
    memory_remember.add_argument("--actor", default="Chris")
    memory_remember.add_argument("--type", required=True, choices=["household", "personal", "project", "safety"])
    memory_remember.add_argument("--scope", required=True, choices=["household", "personal", "project", "safety"])
    memory_remember.add_argument("--summary", required=True)
    memory_remember.add_argument("--detail", required=True)
    memory_remember.add_argument("--owner", default="")
    memory_remember.add_argument("--project", default="")
    memory_remember.add_argument("--tags", default="")
    memory_remember.add_argument("--sensitivity", default="normal", choices=["normal", "sensitive"])

    memory_review = subparsers.add_parser("memory-review", help="Review visible memory entries")
    memory_review.add_argument("--viewer", default="Chris")
    memory_review.add_argument("--type", default="")
    memory_review.add_argument("--owner", default="")
    memory_review.add_argument("--project", default="")

    memory_forget = subparsers.add_parser("memory-forget", help="Forget a memory entry by id")
    memory_forget.add_argument("--viewer", default="Chris")
    memory_forget.add_argument("--entry-id", required=True)

    memory_export = subparsers.add_parser("memory-export", help="Export visible memory entries with decrypted payloads")
    memory_export.add_argument("--viewer", default="Chris")
    memory_export.add_argument("--type", default="")
    memory_export.add_argument("--owner", default="")
    memory_export.add_argument("--project", default="")

    memory_proposals = subparsers.add_parser("memory-proposals", help="List pending or resolved memory proposals")
    memory_proposals.add_argument("--status", default="")

    memory_approve = subparsers.add_parser("memory-approve", help="Approve or reject a memory proposal")
    memory_approve.add_argument("--proposal-id", required=True)
    memory_approve.add_argument("--decision", required=True, choices=["approved", "rejected"])

    subparsers.add_parser("openviking-sync-memory", help="Sync approved non-sensitive memory entries into OpenViking")

    catalyst_signal = subparsers.add_parser("catalyst-signal", help="Capture a Catalyst signal manually")
    catalyst_signal.add_argument("--actor", default="Chris")
    catalyst_signal.add_argument("--source", required=True)
    catalyst_signal.add_argument("--title", required=True)
    catalyst_signal.add_argument("--content")
    catalyst_signal.add_argument("--content-file")
    catalyst_signal.add_argument("--sender", default="")
    catalyst_signal.add_argument("--tags", default="")

    catalyst_email = subparsers.add_parser("catalyst-email-triage", help="Run Catalyst personal email triage")
    catalyst_email.add_argument("--actor", default="Chris")
    catalyst_email.add_argument("--subject", required=True)
    catalyst_email.add_argument("--body")
    catalyst_email.add_argument("--body-file")
    catalyst_email.add_argument("--sender", required=True)

    catalyst_meeting_prep = subparsers.add_parser("catalyst-meeting-prep", help="Prepare a Catalyst meeting brief")
    catalyst_meeting_prep.add_argument("--actor", default="Chris")
    catalyst_meeting_prep.add_argument("--meeting-title", required=True)
    catalyst_meeting_prep.add_argument("--open-commitment", action="append", default=[])
    catalyst_meeting_prep.add_argument("--recent-signal", action="append", default=[])

    catalyst_meeting_extract = subparsers.add_parser("catalyst-meeting-extract", help="Extract a Catalyst meeting workflow")
    catalyst_meeting_extract.add_argument("--actor", default="Chris")
    catalyst_meeting_extract.add_argument("--transcript")
    catalyst_meeting_extract.add_argument("--transcript-file")
    catalyst_meeting_extract.add_argument("--context", default="")

    catalyst_brief = subparsers.add_parser("catalyst-briefing", help="Generate a Catalyst recommendation brief")
    catalyst_brief.add_argument("--actor", default="Chris")
    catalyst_brief.add_argument("--context", default="")

    catalyst_draft = subparsers.add_parser("catalyst-draft", help="Compose a Catalyst draft")
    catalyst_draft.add_argument("--actor", default="Chris")
    catalyst_draft.add_argument("--intent", required=True)
    catalyst_draft.add_argument("--context")
    catalyst_draft.add_argument("--context-file")
    catalyst_draft.add_argument("--recipient", required=True)
    catalyst_draft.add_argument("--tone", default="professional")

    catalyst_project = subparsers.add_parser("catalyst-project-brief", help="Create a Catalyst personal project brief")
    catalyst_project.add_argument("--actor", default="Chris")
    catalyst_project.add_argument("--project-name", required=True)
    catalyst_project.add_argument("--problem", required=True)
    catalyst_project.add_argument("--desired-outcome", required=True)
    catalyst_project.add_argument("--constraints", default="")

    catalyst_impl = subparsers.add_parser("catalyst-implementation-plan", help="Create a Catalyst tactical implementation plan")
    catalyst_impl.add_argument("--actor", default="Chris")
    catalyst_impl.add_argument("--project-name", required=True)
    catalyst_impl.add_argument("--brief")
    catalyst_impl.add_argument("--brief-file")
    catalyst_impl.add_argument("--constraints", default="")

    catalyst_proactive = subparsers.add_parser("catalyst-proactive", help="Run Catalyst proactive surfacing")
    catalyst_proactive.add_argument("--actor", default="Chris")
    catalyst_proactive.add_argument("--horizon", default="today")
    catalyst_proactive.add_argument("--context", default="")

    voice_note = subparsers.add_parser("voice-note", help="Convert a quick family voice note into follow-up tasks")
    voice_note.add_argument("--actor", default="Rebekah")
    voice_note.add_argument("--source", default="van")
    voice_note.add_argument("--note")
    voice_note.add_argument("--note-file")

    voice_notes = subparsers.add_parser("voice-notes", help="List captured family voice-note follow-ups")
    voice_notes.add_argument("--limit", type=int, default=10)

    child_boundaries = subparsers.add_parser("child-boundaries", help="Show child tutoring and data boundary rules")
    child_boundaries.add_argument("--actor")

    tutor = subparsers.add_parser("tutor", help="Run a child-safe tutoring turn")
    tutor.add_argument("--actor", required=True)
    tutor.add_argument("--request")
    tutor.add_argument("--request-file")
    tutor.add_argument("--subject", default="")

    tutoring_summaries = subparsers.add_parser(
        "tutoring-summaries",
        help="Show parent-visible tutoring summaries",
    )
    tutoring_summaries.add_argument("--viewer", default="Rebekah")
    tutoring_summaries.add_argument("--child", default="")
    tutoring_summaries.add_argument("--limit", type=int, default=10)

    device_boundary = subparsers.add_parser("device-boundary", help="Open a device dock and study-boundary routine for a child")
    device_boundary.add_argument("--actor", required=True)
    device_boundary.add_argument("--window", default="")

    device_boundaries = subparsers.add_parser("device-boundaries", help="List device dock and study-boundary routines")
    device_boundaries.add_argument("--child", default="")
    device_boundaries.add_argument("--limit", type=int, default=10)

    workshop_plan = subparsers.add_parser("workshop-plan", help="Generate a workshop copilot plan")
    workshop_plan.add_argument("--actor", default="Chris")
    workshop_plan.add_argument("--request")
    workshop_plan.add_argument("--request-file")

    printer_status = subparsers.add_parser("printer-status", help="Show workshop printer seam status")

    inspect_part = subparsers.add_parser("inspect-part", help="Inspect a workshop part from observations")
    inspect_part.add_argument("--actor", default="Chris")
    inspect_part.add_argument("--part", required=True)
    inspect_part.add_argument("--request", default="Inspect this part and recommend a prototype path.")
    inspect_part.add_argument("--observations")
    inspect_part.add_argument("--observations-file")
    inspect_part.add_argument("--goals", default="Improve durability and validate fit before final fabrication.")
    inspect_part.add_argument("--goals-file")
    inspect_part.add_argument("--image-path", default="")

    cad_package = subparsers.add_parser("cad-package", help="Generate a rough CAD package for a workshop part")
    cad_package.add_argument("--actor", default="Chris")
    cad_package.add_argument("--part", required=True)
    cad_package.add_argument("--dimensions")
    cad_package.add_argument("--dimensions-file")
    cad_package.add_argument("--constraints")
    cad_package.add_argument("--constraints-file")

    material_recommendation = subparsers.add_parser("material-recommendation", help="Recommend materials for a workshop part")
    material_recommendation.add_argument("--actor", default="Chris")
    material_recommendation.add_argument("--part", required=True)
    material_recommendation.add_argument("--use-case", required=True)
    material_recommendation.add_argument("--requirements")
    material_recommendation.add_argument("--requirements-file")

    print_prep = subparsers.add_parser("print-prep", help="Stage a print-prep handoff")
    print_prep.add_argument("--actor", default="Chris")
    print_prep.add_argument("--part", required=True)
    print_prep.add_argument("--printer", required=True)
    print_prep.add_argument("--material", required=True)
    print_prep.add_argument("--profile", default="functional-prototype")
    print_prep.add_argument("--notes")
    print_prep.add_argument("--notes-file")

    safety_check = subparsers.add_parser("safety-check", help="Run a workshop safety and interlock check")
    safety_check.add_argument("--actor", default="Chris")
    safety_check.add_argument("--operation", required=True)
    safety_check.add_argument("--context")
    safety_check.add_argument("--context-file")

    inventory = subparsers.add_parser("inventory", help="Show workshop materials and consumables inventory")

    cad_packages = subparsers.add_parser("cad-packages", help="List generated workshop CAD packages")
    cad_packages.add_argument("--limit", type=int, default=10)

    print_preps = subparsers.add_parser("print-preps", help="List staged print-prep handoffs")
    print_preps.add_argument("--limit", type=int, default=10)

    vendor_prep = subparsers.add_parser("vendor-prep", help="Stage a vendor prep package for approval")
    vendor_prep.add_argument("--actor", default="Chris")
    vendor_prep.add_argument("--part", required=True)
    vendor_prep.add_argument("--vendor", required=True)
    vendor_prep.add_argument("--process", required=True)
    vendor_prep.add_argument("--material", required=True)
    vendor_prep.add_argument("--notes")
    vendor_prep.add_argument("--notes-file")

    vendor_preps = subparsers.add_parser("vendor-preps", help="List staged workshop vendor packages")
    vendor_preps.add_argument("--limit", type=int, default=10)

    bridge = subparsers.add_parser("openclaw-bridge", help="Emit a serializable OpenClaw bridge envelope")
    bridge.add_argument("--request", required=True)
    bridge.add_argument("--actor", default="Chris")
    bridge.add_argument("--room", default="office")
    bridge.add_argument("--device-name", default="")
    bridge.add_argument("--require-wake-word", action="store_true")

    build_voice_parser(subparsers)
    return parser


def command_summary(runtime: JarvisRuntime) -> int:
    print(f"Household: {runtime.household.household_name}")
    print(f"Location: {runtime.household.location_label}")
    print(
        "Models: "
        f"text={runtime.config.openai_text_model}, "
        f"router={runtime.config.openai_router_model}, "
        f"realtime={runtime.config.openai_realtime_model}"
    )
    print(f"OpenClaw gateway: {runtime.config.openclaw_gateway_url}")
    print("Users:")
    for user in runtime.household.users.values():
        print(f"  - {user.display_name} ({user.role})")
    print("Modes:")
    for mode in runtime.household.modes:
        print(f"  - {mode}")
    return 0


def command_fresh_start(runtime: JarvisRuntime, *, execute: bool, no_backup: bool) -> int:
    protocol = FreshStartProtocol(runtime.config)
    payload = protocol.execute(create_backup=not no_backup) if execute else protocol.preview()
    print(json.dumps(payload, indent=2))
    return 0


def _ensure_ollama_running(config: AppConfig) -> None:
    """
    Check whether Ollama is reachable at the configured base URL.
    If not, attempt to start it via `ollama serve` as a detached background process.
    Logs outcome but never raises — JARVIS degrades gracefully if Ollama can't start.
    """
    import logging
    import os
    import shutil
    import subprocess
    import time
    import urllib.request

    _log = logging.getLogger("jarvis.ollama-bootstrap")

    if not getattr(config, "ollama_enabled", True):
        _log.info(
            "Skipping Ollama auto-start because model mode '%s' has local models disabled.",
            getattr(config, "model_mode", "standard"),
        )
        return

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/v1").rstrip("/")
    health_url = f"{ollama_url}/api/tags"

    # 1 — Already running?
    try:
        with urllib.request.urlopen(health_url, timeout=2):
            _log.info("Ollama already running at %s", ollama_url)
            return
    except Exception:
        pass

    # 2 — Find the binary
    ollama_bin = shutil.which("ollama") or os.path.expanduser("~/.local/bin/ollama")
    if not ollama_bin or not os.path.isfile(ollama_bin):
        _log.warning("Ollama binary not found — skipping auto-start. Install from https://ollama.com")
        return

    # 3 — Launch detached
    try:
        log_path = os.path.expanduser("~/.jarvis/logs/ollama.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as log_fh:
            proc = subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,   # detach from JARVIS process group
            )
        _log.info("Ollama started (PID %d) — waiting for readiness…", proc.pid)
    except Exception as exc:
        _log.warning("Could not start Ollama: %s", exc)
        return

    # 4 — Wait up to 12 s for Ollama to be ready
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2):
                _log.info("Ollama ready after %.1f s", 12 - (deadline - time.monotonic()))
                return
        except Exception:
            time.sleep(1)

    _log.warning("Ollama did not become ready within 12 s — gateway will fall back to OpenAI")


def command_serve(runtime: JarvisRuntime, host: str, port: int) -> int:
    from .service import serve

    # Initialise Being Known memory layer before the HTTP server
    if _KNOWN_FACTS_IMPORT_OK:
        try:
            _init_memory()
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise known_facts memory layer: %s", exc
            )
    # Initialise data connectors (Epic 4) before the scheduler consumes them
    if _CONNECTORS_IMPORT_OK:
        try:
            _init_connectors(runtime.config)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise data connectors: %s", exc
            )
    # Initialise the Approval & Permission Layer (Epic 6) before the scheduler
    if _APPROVALS_IMPORT_OK:
        try:
            _init_approvals(runtime.supervision_support, runtime.execute_sandbox_job)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise approval layer: %s", exc
            )
    # Ensure Ollama is running (local inference backend)
    _ensure_ollama_running(runtime.config)
    # Initialise the LLM Gateway before the scheduler (agents need it)
    if _LLM_GATEWAY_IMPORT_OK:
        try:
            _init_gateway(runtime.config)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise LLM gateway: %s", exc
            )
    # Start the autonomous background scheduler before the HTTP server
    if _SCHEDULER_IMPORT_OK:
        try:
            _init_scheduler(runtime)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not start background scheduler: %s", exc
            )
    # Initialise the Chronicle bridge + Disciple workflow (Epic 9)
    if _CHRONICLE_BRIDGE_IMPORT_OK:
        try:
            _chronicle_client = getattr(runtime, "chronicle_support", None)
            _init_chronicle_bridge(chronicle_client=_chronicle_client)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise Chronicle bridge: %s", exc
            )
    # Initialise Work Intelligence DB + engine (Epic 8 — native Catalyst consolidation)
    if _WORK_INTELLIGENCE_IMPORT_OK:
        try:
            _wi_db = _init_catalyst_db()
            _init_work_intelligence(db=_wi_db, user_id="chris")
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise Work Intelligence engine: %s", exc
            )
    # Register all 56 agents with Catalyst — pre-warms AgentCatalyst singletons
    if _WORK_INTELLIGENCE_IMPORT_OK:
        try:
            _ensure_agents_catalyst()
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not register agents with Catalyst: %s", exc
            )
    # Initialise the Epic 7 Voice Shell pipeline
    if _VOICE_PIPELINE_IMPORT_OK:
        try:
            _init_voice(runtime.config)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise voice pipeline: %s", exc
            )
    # Initialise Epic 10 Family Profiles & Household Modes
    if _FAMILY_PROFILES_IMPORT_OK:
        try:
            _init_family(runtime)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise family profiles: %s", exc
            )
    # Initialise Epic 11 Publishing & Revenue Suite
    if _PUBLISHING_IMPORT_OK:
        try:
            _init_publishing(runtime)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise publishing suite: %s", exc
            )
    # Initialise Ghostwritr Bridge (Stan Lee — book authoring pipeline)
    if _GHOSTWRITR_BRIDGE_IMPORT_OK:
        try:
            import os as _os
            _init_ghostwritr_bridge(config={
                "base_url": _os.environ.get("GHOSTWRITR_BASE_URL", "http://localhost:3000"),
                "db_url": _os.environ.get("GHOSTWRITR_DB_URL", "postgresql://chris@127.0.0.1:5432/book_platform_builder"),
                "internal_token": _os.environ.get("GHOSTWRITR_INTERNAL_TOKEN", ""),
            })
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise Ghostwritr bridge: %s", exc
            )
    # Initialise Social Engine (JJJ / Quicksilver / Sage / Loki — launch + adapt)
    if _SOCIAL_ENGINE_IMPORT_OK:
        try:
            _init_social_engine()
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise social engine: %s", exc
            )
    # Initialise Epic 12 Workshop Copilot
    if _WORKSHOP_COPILOT_IMPORT_OK:
        try:
            _init_workshop(runtime)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise workshop copilot: %s", exc
            )
    # Initialise Epic 13 Financial Intelligence
    if _FINANCIAL_INTELLIGENCE_IMPORT_OK:
        try:
            _init_finance(runtime)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise financial intelligence: %s", exc
            )
    # Initialise Epic 15 Growth Intelligence
    if _GROWTH_INTELLIGENCE_IMPORT_OK:
        try:
            _init_growth(runtime)
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise growth intelligence: %s", exc
            )

    # ── Home Intelligence: email, calendar, projects, tasks ───────────────────
    if _HOME_INTELLIGENCE_IMPORT_OK:
        import logging as _log
        _hi_log = _log.getLogger("jarvis.main")
        try:
            import os as _os
            _home_db_url = _os.environ.get(
                "JARVIS_HOME_DB_URL",
                "postgresql://chris@127.0.0.1:5432/jarvis_home",
            )
            _home_db = _init_home_db(_home_db_url)
            _hi_log.info("Home DB connected at %s", _home_db_url)

            # Google bridges — resolve token from bridge directory
            _google_acct = _os.environ.get("JARVIS_GOOGLE_ACCOUNT_ID", "")
            _bridge_token_dir = _os.path.join(
                _os.path.dirname(__file__), "..", "data", "google", "bridge", "tokens"
            )
            _token_path = _os.path.join(_bridge_token_dir, f"{_google_acct}.json") if _google_acct else ""
            if _token_path and _os.path.exists(_token_path) and _os.path.getsize(_token_path) > 0:
                _gmail = _init_gmail_bridge(credentials_path=_token_path)
                _gcal  = _init_gcal_bridge(credentials_path=_token_path)
                _hi_log.info("Gmail + Google Calendar bridges initialised")
            else:
                _gmail = _gcal = None
                _hi_log.warning("Google token not found or empty — Gmail/GCal bridges skipped")

            # Outlook bridge — uses delegated OAuth token (authorisation-code flow)
            # Resolve token path: check JARVIS_MICROSOFT_TOKEN_PATH, then scan the
            # data/microsoft_graph/ directory for any account token file.
            _ms_token_path_raw = _os.environ.get(
                "JARVIS_MICROSOFT_TOKEN_PATH",
                _os.path.join(_os.path.dirname(__file__), "..", "data", "microsoft_graph", "token.json"),
            )
            _ms_token_path = Path(_ms_token_path_raw)
            if not _ms_token_path.exists() or _ms_token_path.stat().st_size == 0:
                # Scan sibling directory for any account-specific token file.
                _ms_token_dir = _ms_token_path.parent
                _candidates = sorted(
                    [
                        p for p in _ms_token_dir.glob("*.json")
                        if p.stem not in ("pending_oauth", "token")
                        and p.stat().st_size > 0
                    ],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if _candidates:
                    _ms_token_path = _candidates[0]
                    _hi_log.info("Resolved Outlook delegated token: %s", _ms_token_path)
                else:
                    _hi_log.warning("No Outlook delegated token found in %s", _ms_token_dir)
            _outlook = _init_outlook_bridge(
                token_path=_ms_token_path,
                client_id=_os.environ.get("JARVIS_MICROSOFT_CLIENT_ID", ""),
                client_secret=_os.environ.get("JARVIS_MICROSOFT_CLIENT_SECRET", ""),
                redirect_uri=_os.environ.get("JARVIS_MICROSOFT_REDIRECT_URI", ""),
                authority=_os.environ.get("JARVIS_MICROSOFT_AUTHORITY", "common"),
            )

            # Cozi bridge (ICS feed)
            _cozi = _init_cozi_bridge(
                username=_os.environ.get("COZI_USERNAME", ""),
                password=_os.environ.get("COZI_PASSWORD", ""),
            )

            # Unified inbox
            _init_unified_inbox(
                home_db=_home_db,
                gmail_bridge=_gmail,
                gcal_bridge=_gcal,
                outlook_bridge=_outlook,
                cozi_bridge=_cozi,
            )

            # Signal router
            _init_signal_router(
                home_db=_home_db,
                openai_api_key=_os.environ.get("OPENAI_API_KEY", ""),
            )
            _hi_log.info("Home intelligence layer initialised")
        except Exception as exc:
            import logging
            logging.getLogger("jarvis.main").warning(
                "Could not initialise home intelligence: %s", exc
            )

    serve(runtime, host, port)
    return 0


def command_briefing(runtime: JarvisRuntime, actor: str) -> int:
    print(runtime.morning_brief(actor))
    return 0


def command_status(runtime: JarvisRuntime) -> int:
    for item in runtime.status():
        state = "ok" if item["ok"] else "blocked"
        print(f"{item['name']}: {state} - {item['detail']}")
    return 0


def command_runtime_posture(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.runtime_posture_snapshot(), indent=2))
    return 0


def command_approvals(runtime: JarvisRuntime) -> int:
    records = runtime.list_pending_approvals()
    if not records:
        print("No pending approvals.")
        return 0
    for item in records:
        print(
            f"{item['request_id']} | actor={item['actor']} | class={item['action_class']} | request={item['request']}"
        )
    return 0


def command_voice_stack(runtime: JarvisRuntime) -> int:
    print(json.dumps(voice_stack_status(runtime.config), indent=2))
    return 0


def command_brain_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.brain_graph_snapshot(), indent=2))
    return 0


def command_agent_registry(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.agent_registry_snapshot(), indent=2))
    return 0


def command_agent_registry_contract() -> int:
    try:
        bundle = load_contract_bundle(validate=True)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "paths": contract_paths(),
                    "error": str(exc),
                },
                indent=2,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "paths": contract_paths(),
                "summary": bundle.snapshot(),
            },
            indent=2,
        )
    )
    return 0


def command_agent_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.background_agent_status(), indent=2))
    return 0


def command_agent_runtime(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.agent_runtime_snapshot(), indent=2))
    return 0


def command_agent_runtime_control(
    runtime: JarvisRuntime,
    agent_id: str,
    action: str,
    actor: str,
    reason: str,
    execution_lane: str,
) -> int:
    print(
        json.dumps(
            runtime.control_agent_runtime(
                agent_id,
                action,
                actor_name=actor,
                reason=reason,
                execution_lane=execution_lane,
            ),
            indent=2,
        )
    )
    return 0


def command_memory_curator(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.memory_curator_snapshot(), indent=2))
    return 0


def command_assistant_notifications(runtime: JarvisRuntime, actor: str, unread_only: bool, limit: int) -> int:
    print(json.dumps(runtime.assistant_notifications(actor, unread_only=unread_only, limit=limit), indent=2))
    return 0


def command_assistant_autonomy_run(runtime: JarvisRuntime, actors: list[str] | None) -> int:
    print(json.dumps(runtime.background_autonomy_run(actors), indent=2))
    return 0


def command_assistant_autonomy_daemon(runtime: JarvisRuntime, actors: list[str] | None, interval_seconds: int) -> int:
    interval = max(60, int(interval_seconds))
    while True:
        result = runtime.background_autonomy_run(actors)
        print(json.dumps(result), flush=True)
        time.sleep(interval)


def command_catalyst_overview(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.catalyst_overview(), indent=2))
    return 0


def command_google_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.google_workspace_status(), indent=2))
    return 0


def command_google_summary(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.google_workspace_summary(), indent=2))
    return 0


def command_catalyst_signal(
    runtime: JarvisRuntime,
    actor: str,
    source: str,
    title: str,
    content: str,
    sender: str,
    tags: list[str],
) -> int:
    print(json.dumps(runtime.catalyst_capture_signal(actor, source, title, content, sender=sender, tags=tags), indent=2))
    return 0


def command_catalyst_email_triage(runtime: JarvisRuntime, actor: str, subject: str, body: str, sender: str) -> int:
    print(json.dumps(runtime.catalyst_email_triage(actor, subject, body, sender), indent=2))
    return 0


def command_catalyst_meeting_prep(
    runtime: JarvisRuntime,
    actor: str,
    meeting_title: str,
    open_commitments: list[str],
    recent_signals: list[str],
) -> int:
    print(json.dumps(runtime.catalyst_meeting_prep(actor, meeting_title, open_commitments, recent_signals), indent=2))
    return 0


def command_catalyst_meeting_extract(runtime: JarvisRuntime, actor: str, transcript: str, context: str) -> int:
    print(json.dumps(runtime.catalyst_meeting_extraction(actor, transcript, context), indent=2))
    return 0


def command_catalyst_briefing(runtime: JarvisRuntime, actor: str, user_context: str) -> int:
    print(json.dumps(runtime.catalyst_briefing(actor, user_context), indent=2))
    return 0


def command_catalyst_draft(
    runtime: JarvisRuntime,
    actor: str,
    intent: str,
    context: str,
    recipient: str,
    tone: str,
) -> int:
    print(json.dumps(runtime.catalyst_draft(actor, intent, context, recipient, tone), indent=2))
    return 0


def command_catalyst_project_brief(
    runtime: JarvisRuntime,
    actor: str,
    project_name: str,
    problem: str,
    desired_outcome: str,
    constraints: str,
) -> int:
    print(json.dumps(runtime.catalyst_project_brief(actor, project_name, problem, desired_outcome, constraints), indent=2))
    return 0


def command_catalyst_implementation_plan(
    runtime: JarvisRuntime,
    actor: str,
    project_name: str,
    brief: str,
    constraints: str,
) -> int:
    print(json.dumps(runtime.catalyst_implementation_plan(actor, project_name, brief, constraints), indent=2))
    return 0


def command_catalyst_proactive(runtime: JarvisRuntime, actor: str, horizon: str, context: str) -> int:
    print(json.dumps(runtime.catalyst_proactive_surfacing(actor, horizon, context), indent=2))
    return 0


def command_plan(runtime: JarvisRuntime, actor: str, room: str, request: str) -> int:
    plan = runtime.plan_request(actor, room, request)
    print(f"Request ID: {plan.request_id}")
    print(f"Actor: {plan.actor}")
    print(f"Room: {plan.room}")
    print(f"Mode: {plan.mode}")
    print(f"Module: {plan.module}")
    print(f"Task class: {plan.task_class.value}")
    print(f"Preferred provider: {plan.preferred_provider}")
    print(f"Context lane: {plan.context_lane}")
    print(f"Model: {plan.model}")
    print(f"Allowed: {plan.allowed}")
    print(f"Approval required: {plan.needs_approval}")
    print(f"Second factor required: {plan.second_factor_required}")
    print(f"Action class: {plan.action_class.name}")
    print(f"Rationale: {plan.rationale}")
    return 0


def command_respond(runtime: JarvisRuntime, actor: str, room: str, request: str) -> int:
    result = runtime.respond(actor, room, request)
    print(f"Model: {result.model}")
    print(result.output_text)
    return 0


def read_inline_or_file(inline_value: str | None, file_value: str | None, label: str) -> str:
    if inline_value:
        return inline_value
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    raise ValueError(f"Provide --{label} or --{label}-file.")


def command_meeting_brief(runtime: JarvisRuntime, actor: str, context: str) -> int:
    print(runtime.meeting_brief(actor, context))
    return 0


def command_meeting_followup(runtime: JarvisRuntime, actor: str, transcript: str) -> int:
    print(runtime.meeting_followup(actor, transcript))
    return 0


def command_decision_framework(runtime: JarvisRuntime, actor: str, context: str) -> int:
    print(runtime.decision_framework(actor, context))
    return 0


def command_research_summary(runtime: JarvisRuntime, actor: str, topic: str, notes: str) -> int:
    print(runtime.research_summary(actor, topic, notes))
    return 0


def command_confidentiality_review(runtime: JarvisRuntime, text: str) -> int:
    print(json.dumps(runtime.confidentiality_review(text), indent=2))
    return 0


def command_manuscript_review(runtime: JarvisRuntime, actor: str, excerpt: str) -> int:
    print(runtime.manuscript_review(actor, excerpt))
    return 0


def command_iron_clad_editor(runtime: JarvisRuntime, actor: str, excerpt: str) -> int:
    print(runtime.iron_clad_editor(actor, excerpt))
    return 0


def command_venture_brief(runtime: JarvisRuntime, actor: str, topic: str, notes: str) -> int:
    print(runtime.venture_brief(actor, topic, notes))
    return 0


def command_devotional_pause(runtime: JarvisRuntime, actor: str, theme: str, mode: str) -> int:
    print(runtime.devotional_pause(actor, theme, mode))
    return 0


def command_family_devotional(runtime: JarvisRuntime, actor: str, theme: str, context: str) -> int:
    print(runtime.family_devotional_prep(actor, theme, context))
    return 0


def command_chronicle_capture(runtime: JarvisRuntime, actor: str, theme: str, note: str) -> int:
    print(json.dumps(runtime.chronicle_capture(actor, theme, note), indent=2))
    return 0


def command_chronicle_timeline(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.chronicle_timeline(limit=limit), indent=2))
    return 0


def command_chronicle_themes(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.chronicle_theme_summary(limit=limit), indent=2))
    return 0


def command_mode_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.active_mode(), indent=2))
    return 0


def command_mode_transition(runtime: JarvisRuntime, actor: str, mode: str, reason: str) -> int:
    print(json.dumps(runtime.transition_mode(actor, mode, reason), indent=2))
    return 0


def command_mode_brief(runtime: JarvisRuntime, mode: str) -> int:
    print(json.dumps(runtime.family_mode_brief(mode), indent=2))
    return 0


def command_family_plan(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(runtime.family_plan(actor, request))
    return 0


def command_departure_plan(runtime: JarvisRuntime, actor: str, context: str) -> int:
    print(json.dumps(runtime.departure_plan(actor, context), indent=2))
    return 0


def command_rebekah_center(runtime: JarvisRuntime, request: str) -> int:
    print(runtime.rebekah_command_center(request))
    return 0


def command_troop_plan(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(runtime.troop_plan(actor, request))
    return 0


def command_grocery_support(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(runtime.grocery_support(actor, request))
    return 0


def command_meal_plan(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(json.dumps(runtime.meal_plan(actor, request), indent=2))
    return 0


def command_vehicle_plan(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(json.dumps(runtime.vehicle_plan(actor, request), indent=2))
    return 0


def command_weather_contingency(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(json.dumps(runtime.weather_contingency(actor, request), indent=2))
    return 0


def command_message_draft(
    runtime: JarvisRuntime,
    actor: str,
    audience: str,
    purpose: str,
    context: str,
    tone: str,
) -> int:
    print(json.dumps(runtime.draft_message(actor, audience, purpose, context, tone), indent=2))
    return 0


def command_message_drafts(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.list_message_drafts(limit=limit), indent=2))
    return 0


def command_parent_message(
    runtime: JarvisRuntime,
    actor: str,
    audience: str,
    purpose: str,
    context: str,
    tone: str,
) -> int:
    print(json.dumps(runtime.stage_parent_message(actor, audience, purpose, context, tone), indent=2))
    return 0


def command_anomaly_watch(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.anomaly_watch(), indent=2))
    return 0


def command_security_event(
    runtime: JarvisRuntime,
    actor: str,
    category: str,
    location: str,
    detail: str,
    severity: str,
) -> int:
    print(json.dumps(runtime.package_or_motion_monitor(actor, category, location, detail, severity=severity), indent=2))
    return 0


def command_safety_alert(
    runtime: JarvisRuntime,
    actor: str,
    hazard: str,
    source: str,
    detail: str,
    severity: str,
) -> int:
    print(json.dumps(runtime.safety_escalation(actor, hazard, source, detail, severity=severity), indent=2))
    return 0


def command_weather_alert(runtime: JarvisRuntime, actor: str, context: str) -> int:
    print(json.dumps(runtime.weather_advisory(actor, context), indent=2))
    return 0


def command_child_arrival(runtime: JarvisRuntime, actor: str, location: str, detail: str) -> int:
    print(json.dumps(runtime.child_arrival(actor, location, detail), indent=2))
    return 0


def command_unlock_policy(
    runtime: JarvisRuntime,
    actor: str,
    target: str,
    requested_by_voice: bool,
    second_factor_present: bool,
) -> int:
    print(
        json.dumps(
            runtime.unlock_assessment(
                actor,
                target,
                requested_by_voice=requested_by_voice,
                second_factor_present=second_factor_present,
            ),
            indent=2,
        )
    )
    return 0


def command_overnight_review(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.overnight_review(), indent=2))
    return 0


def command_security_incidents(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.list_security_incidents(limit=limit), indent=2))
    return 0


def command_home_overview(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.home_overview(), indent=2))
    return 0


def command_room_scene(runtime: JarvisRuntime, actor: str, room: str, scene: str, intent: str) -> int:
    print(json.dumps(runtime.room_scene(actor, room, scene, intent=intent), indent=2))
    return 0


def command_climate_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.climate_status(), indent=2))
    return 0


def command_climate_control(
    runtime: JarvisRuntime,
    actor: str,
    zone: str,
    mode: str,
    target_temp: float | None,
    context: str,
) -> int:
    print(json.dumps(runtime.climate_control(actor, zone, mode, target_temperature=target_temp, context=context), indent=2))
    return 0


def command_access_overview(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.access_overview(), indent=2))
    return 0


def command_access_control(runtime: JarvisRuntime, actor: str, target: str, state: str) -> int:
    print(json.dumps(runtime.access_control(actor, target, state), indent=2))
    return 0


def command_garage_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.garage_status(), indent=2))
    return 0


def command_garage_check(runtime: JarvisRuntime, actor: str, target: str) -> int:
    print(json.dumps(runtime.garage_safe_close(actor, target), indent=2))
    return 0


def command_leak_monitor(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.leak_monitor(), indent=2))
    return 0


def command_cold_storage_monitor(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.cold_storage_monitor(), indent=2))
    return 0


def command_energy_window(runtime: JarvisRuntime, appliance: str, request_text: str) -> int:
    print(json.dumps(runtime.energy_window(appliance, request_text=request_text), indent=2))
    return 0


def command_outage_readiness(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.outage_readiness(), indent=2))
    return 0


def command_perception_overview(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.perception_overview(), indent=2))
    return 0


def command_mic_ingress(
    runtime: JarvisRuntime,
    microphone: str,
    transcript: str,
    wake_word_detected: bool,
    actor_hint: str,
) -> int:
    print(
        json.dumps(
            runtime.microphone_ingress(
                microphone,
                transcript,
                wake_word_detected=wake_word_detected,
                actor_hint=actor_hint,
            ),
            indent=2,
        )
    )
    return 0


def command_presence_update(runtime: JarvisRuntime, sensor: str, room: str, occupied: bool, detail: str) -> int:
    print(json.dumps(runtime.presence_update(sensor, room, occupied, detail=detail), indent=2))
    return 0


def command_phone_presence(
    runtime: JarvisRuntime,
    actor: str,
    device: str,
    state: str,
    zone: str,
    detail: str,
) -> int:
    print(json.dumps(runtime.phone_presence_update(actor, device, state, zone=zone, detail=detail), indent=2))
    return 0


def command_camera_event(
    runtime: JarvisRuntime,
    camera: str,
    event_type: str,
    detail: str,
    detected_object: str,
    confidence: str,
) -> int:
    print(
        json.dumps(
            runtime.camera_event(
                camera,
                event_type,
                detail,
                detected_object=detected_object,
                confidence=confidence,
            ),
            indent=2,
        )
    )
    return 0


def command_package_rule(
    runtime: JarvisRuntime,
    zone: str,
    preferred_drop: str,
    rain_sensitive: bool,
    note: str,
) -> int:
    print(json.dumps(runtime.package_rule(zone, preferred_drop, rain_sensitive, note=note), indent=2))
    return 0


def command_object_recognition(
    runtime: JarvisRuntime,
    source: str,
    room: str,
    observed_object: str,
    detail: str,
    confidence: str,
) -> int:
    print(
        json.dumps(
            runtime.object_recognition(source, room, observed_object, detail=detail, confidence=confidence),
            indent=2,
        )
    )
    return 0


def command_environmental_anomaly(
    runtime: JarvisRuntime,
    category: str,
    source: str,
    reading: str,
    baseline: str,
    severity: str,
    detail: str,
) -> int:
    print(
        json.dumps(
            runtime.environmental_anomaly(
                category,
                source,
                reading,
                baseline,
                severity=severity,
                detail=detail,
            ),
            indent=2,
        )
    )
    return 0


def command_privacy_state(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.privacy_state(), indent=2))
    return 0


def command_privacy_update(
    runtime: JarvisRuntime,
    kind: str,
    target: str,
    enabled_value: str | None,
    muted_value: str | None,
) -> int:
    enabled = None if enabled_value is None else enabled_value == "true"
    muted = None if muted_value is None else muted_value == "true"
    print(json.dumps(runtime.update_privacy_state(kind, target, enabled=enabled, muted=muted), indent=2))
    return 0


def command_memory_overview(runtime: JarvisRuntime, viewer: str) -> int:
    print(json.dumps(runtime.memory_overview(viewer), indent=2))
    return 0


def command_memory_remember(
    runtime: JarvisRuntime,
    actor: str,
    memory_type: str,
    scope: str,
    summary: str,
    detail: str,
    owner: str,
    project: str,
    tags: str,
    sensitivity: str,
) -> int:
    tag_list = [item.strip() for item in tags.split(",") if item.strip()]
    print(
        json.dumps(
            runtime.remember(
                actor,
                memory_type,
                scope,
                summary,
                detail,
                owner=owner,
                project=project,
                tags=tag_list,
                sensitivity=sensitivity,
            ),
            indent=2,
        )
    )
    return 0


def command_memory_review(
    runtime: JarvisRuntime,
    viewer: str,
    memory_type: str,
    owner: str,
    project: str,
) -> int:
    print(json.dumps(runtime.review_memory(viewer, memory_type=memory_type, owner=owner, project=project), indent=2))
    return 0


def command_memory_forget(runtime: JarvisRuntime, viewer: str, entry_id: str) -> int:
    print(json.dumps(runtime.forget_memory(viewer, entry_id), indent=2))
    return 0


def command_memory_export(
    runtime: JarvisRuntime,
    viewer: str,
    memory_type: str,
    owner: str,
    project: str,
) -> int:
    print(json.dumps(runtime.export_memory(viewer, memory_type=memory_type, owner=owner, project=project), indent=2))
    return 0


def command_memory_proposals(runtime: JarvisRuntime, status: str) -> int:
    print(json.dumps(runtime.memory_proposals(status=status), indent=2))
    return 0


def command_memory_approve(runtime: JarvisRuntime, proposal_id: str, decision: str) -> int:
    print(json.dumps(runtime.resolve_memory_proposal(proposal_id, decision), indent=2))
    return 0


def command_openviking_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.openviking_status(), indent=2))
    return 0


def command_openviking_sync_memory(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.sync_memory_to_openviking(), indent=2))
    return 0


def command_voice_note(runtime: JarvisRuntime, actor: str, source: str, note: str) -> int:
    print(json.dumps(runtime.capture_voice_note(actor, source, note), indent=2))
    return 0


def command_voice_notes(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.list_voice_note_tasks(limit=limit), indent=2))
    return 0


def command_child_boundaries(runtime: JarvisRuntime, actor: str | None) -> int:
    print(json.dumps(runtime.child_boundaries(actor_name=actor), indent=2))
    return 0


def command_tutor(runtime: JarvisRuntime, actor: str, request: str, subject: str) -> int:
    print(json.dumps(runtime.tutor(actor, request, subject=subject), indent=2))
    return 0


def command_tutoring_summaries(
    runtime: JarvisRuntime,
    viewer: str,
    child: str,
    limit: int,
) -> int:
    print(json.dumps(runtime.tutoring_summaries(viewer, child_name=child, limit=limit), indent=2))
    return 0


def command_device_boundary(runtime: JarvisRuntime, actor: str, window: str) -> int:
    print(json.dumps(runtime.device_boundary_plan(actor, window_label=window), indent=2))
    return 0


def command_device_boundaries(runtime: JarvisRuntime, child: str, limit: int) -> int:
    print(json.dumps(runtime.list_device_boundaries(child_name=child, limit=limit), indent=2))
    return 0


def command_workshop_plan(runtime: JarvisRuntime, actor: str, request: str) -> int:
    print(runtime.workshop_plan(actor, request))
    return 0


def command_printer_status(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.printer_status(), indent=2))
    return 0


def command_material_recommendation(
    runtime: JarvisRuntime,
    actor: str,
    part: str,
    use_case: str,
    requirements: str,
) -> int:
    print(json.dumps(runtime.material_recommendation(actor, part, use_case, requirements), indent=2))
    return 0


def command_cad_package(runtime: JarvisRuntime, actor: str, part: str, dimensions: str, constraints: str) -> int:
    print(json.dumps(runtime.cad_package(actor, part, dimensions, constraints), indent=2))
    return 0


def command_print_prep(
    runtime: JarvisRuntime,
    actor: str,
    part: str,
    printer: str,
    material: str,
    profile: str,
    notes: str,
) -> int:
    print(json.dumps(runtime.print_prep(actor, part, printer, material, profile, notes), indent=2))
    return 0


def command_safety_check(runtime: JarvisRuntime, actor: str, operation: str, context: str) -> int:
    print(json.dumps(runtime.safety_check(actor, operation, context), indent=2))
    return 0


def command_inventory(runtime: JarvisRuntime) -> int:
    print(json.dumps(runtime.inventory_summary(), indent=2))
    return 0


def command_cad_packages(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.list_cad_packages(limit=limit), indent=2))
    return 0


def command_print_preps(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.list_print_preps(limit=limit), indent=2))
    return 0


def command_inspect_part(
    runtime: JarvisRuntime,
    actor: str,
    part: str,
    request: str,
    observations: str,
    goals: str,
    image_path: str,
) -> int:
    print(
        json.dumps(
            runtime.inspect_part(
                actor,
                part,
                request,
                observations,
                goals,
                image_path=image_path,
            ),
            indent=2,
        )
    )
    return 0


def command_vendor_prep(
    runtime: JarvisRuntime,
    actor: str,
    part: str,
    vendor: str,
    process: str,
    material: str,
    notes: str,
) -> int:
    print(json.dumps(runtime.vendor_prep(actor, part, vendor, process, material, notes), indent=2))
    return 0


def command_vendor_preps(runtime: JarvisRuntime, limit: int) -> int:
    print(json.dumps(runtime.list_vendor_preps(limit=limit), indent=2))
    return 0


def command_openclaw_bridge(
    runtime: JarvisRuntime,
    actor: str,
    room: str,
    request_text: str,
    device_name: str,
    require_wake_word: bool,
) -> int:
    if VOICE_IMPORT_ERROR is not None or JarvisVoiceShell is None:
        raise RuntimeError(f"Voice subsystem is unavailable in this interpreter: {VOICE_IMPORT_ERROR}")
    voice_shell = JarvisVoiceShell(runtime)
    inferred = voice_shell.infer_context(
        raw_text=request_text,
        explicit_actor=actor,
        explicit_room=room,
        device_name=device_name,
        require_wake_word=require_wake_word,
    )
    plan = runtime.plan_request(inferred.actor, inferred.room, inferred.cleaned_request)
    result = runtime.openai_client.respond(plan)
    envelope = build_openclaw_envelope(runtime.config.openclaw_gateway_url, inferred, plan, result)
    print(envelope_to_json(envelope))
    return 0


def command_voice(runtime: JarvisRuntime, args: argparse.Namespace) -> int:
    if VOICE_IMPORT_ERROR is not None or JarvisVoiceShell is None:
        raise RuntimeError(f"Voice subsystem is unavailable in this interpreter: {VOICE_IMPORT_ERROR}")
    voice_shell = JarvisVoiceShell(runtime)
    require_wake_word = not args.no_wake_word

    if args.list_devices:
        return voice_shell.list_input_devices()
    if args.text:
        raw_text = args.text
        if args.whisper:
            if raw_text.lower().startswith("jarvis"):
                raw_text = raw_text.replace("Jarvis", "Jarvis, whisper mode", 1).replace("jarvis", "jarvis, whisper mode", 1)
            else:
                raw_text = f"whisper mode {raw_text}"
        elif args.quiet:
            if raw_text.lower().startswith("jarvis"):
                raw_text = raw_text.replace("Jarvis", "Jarvis, quiet mode", 1).replace("jarvis", "jarvis, quiet mode", 1)
            else:
                raw_text = f"quiet mode {raw_text}"
        handled = voice_shell.handle_text_turn(
            raw_text=raw_text,
            explicit_actor=args.actor,
            explicit_room=args.room,
            device_name=voice_shell._resolve_device_name(args.input_device),
            require_wake_word=require_wake_word,
            force_quiet=args.quiet,
            force_whisper=args.whisper,
        )
        if not handled:
            print(json.dumps({"wake_word_detected": False, "handled": False}, indent=2))
            return 0
        inferred, reply = handled
        print(
            json.dumps(
                {
                    "wake_word_detected": inferred.wake_word_detected,
                    "actor": inferred.actor,
                    "room": inferred.room,
                    "cleaned_request": inferred.cleaned_request,
                    "quiet_mode": inferred.quiet_mode,
                    "whisper_mode": inferred.whisper_mode,
                    "speaker_confidence": inferred.speaker_confidence,
                    "reply": reply,
                },
                indent=2,
            )
        )
        if not args.silent:
            voice_shell.speak(reply, quiet=inferred.quiet_mode, whisper=inferred.whisper_mode)
        return 0
    if args.text_loop:
        return voice_shell.run_text_loop(
            args.actor,
            args.room,
            args.silent,
            require_wake_word,
            force_quiet=args.quiet,
            force_whisper=args.whisper,
        )
    if args.listen:
        return voice_shell.run_continuous_listen_loop(
            actor=args.actor,
            room=args.room,
            record_duration=args.duration,
            input_device=args.input_device,
            silent=args.silent,
        )
    if args.loop:
        return voice_shell.run_push_to_talk_loop(
            duration=args.duration,
            actor=args.actor,
            room=args.room,
            input_device=args.input_device,
            silent=args.silent,
            require_wake_word=require_wake_word,
            force_quiet=args.quiet,
            force_whisper=args.whisper,
        )
    if args.realtime:
        return asyncio.run(
            voice_shell.run_realtime_transcription_loop(
                actor=args.actor,
                room=args.room,
                input_device=args.input_device,
                silent=args.silent,
                require_wake_word=require_wake_word,
                samplerate=args.samplerate,
                force_quiet=args.quiet,
                force_whisper=args.whisper,
            )
        )
    return voice_shell.run_text_loop(
        args.actor,
        args.room,
        args.silent,
        require_wake_word,
        force_quiet=args.quiet,
        force_whisper=args.whisper,
    )


def main() -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "agent-registry-contract":
        return command_agent_registry_contract()

    from .runtime import JarvisRuntime

    runtime = JarvisRuntime.from_env()

    if args.command == "summary":
        return command_summary(runtime)
    if args.command == "fresh-start":
        return command_fresh_start(runtime, execute=args.execute, no_backup=args.no_backup)
    if args.command == "serve":
        return command_serve(runtime, args.host, args.port)
    if args.command == "status":
        return command_status(runtime)
    if args.command == "runtime-posture":
        return command_runtime_posture(runtime)
    if args.command == "approvals":
        return command_approvals(runtime)
    if args.command == "voice-stack":
        return command_voice_stack(runtime)
    if args.command == "brain-status":
        return command_brain_status(runtime)
    if args.command == "agent-registry":
        return command_agent_registry(runtime)
    if args.command == "agent-status":
        return command_agent_status(runtime)
    if args.command == "agent-runtime":
        return command_agent_runtime(runtime)
    if args.command == "agent-runtime-control":
        return command_agent_runtime_control(runtime, args.agent_id, args.action, args.actor, args.reason, args.execution_lane)
    if args.command == "memory-curator":
        return command_memory_curator(runtime)
    if args.command == "assistant-notifications":
        return command_assistant_notifications(runtime, args.actor, args.unread_only, args.limit)
    if args.command == "assistant-autonomy-run":
        return command_assistant_autonomy_run(runtime, args.actors)
    if args.command == "assistant-autonomy-daemon":
        return command_assistant_autonomy_daemon(runtime, args.actors, args.interval_seconds)
    if args.command == "catalyst-overview":
        return command_catalyst_overview(runtime)
    if args.command == "google-status":
        return command_google_status(runtime)
    if args.command == "google-summary":
        return command_google_summary(runtime)
    if args.command == "briefing":
        return command_briefing(runtime, args.actor)
    if args.command == "plan":
        return command_plan(runtime, args.actor, args.room, args.request)
    if args.command == "respond":
        return command_respond(runtime, args.actor, args.room, args.request)
    if args.command == "meeting-brief":
        return command_meeting_brief(
            runtime,
            args.actor,
            read_inline_or_file(args.context, args.context_file, "context"),
        )
    if args.command == "meeting-followup":
        return command_meeting_followup(
            runtime,
            args.actor,
            read_inline_or_file(args.transcript, args.transcript_file, "transcript"),
        )
    if args.command == "decision-framework":
        return command_decision_framework(
            runtime,
            args.actor,
            read_inline_or_file(args.context, args.context_file, "context"),
        )
    if args.command == "research-summary":
        return command_research_summary(
            runtime,
            args.actor,
            args.topic,
            read_inline_or_file(args.notes, args.notes_file, "notes"),
        )
    if args.command == "confidentiality-review":
        return command_confidentiality_review(
            runtime,
            read_inline_or_file(args.text, args.text_file, "text"),
        )
    if args.command == "manuscript-review":
        return command_manuscript_review(
            runtime,
            args.actor,
            read_inline_or_file(args.excerpt, args.excerpt_file, "excerpt"),
        )
    if args.command == "ironclad-editor":
        return command_iron_clad_editor(
            runtime,
            args.actor,
            read_inline_or_file(args.excerpt, args.excerpt_file, "excerpt"),
        )
    if args.command == "venture-brief":
        return command_venture_brief(
            runtime,
            args.actor,
            args.topic,
            read_inline_or_file(args.notes, args.notes_file, "notes"),
        )
    if args.command == "devotional-pause":
        return command_devotional_pause(runtime, args.actor, args.theme, args.mode)
    if args.command == "family-devotional":
        return command_family_devotional(
            runtime,
            args.actor,
            args.theme,
            read_inline_or_file(args.context, args.context_file, "context")
            if (args.context or args.context_file)
            else "",
        )
    if args.command == "chronicle-capture":
        return command_chronicle_capture(
            runtime,
            args.actor,
            args.theme,
            read_inline_or_file(args.note, args.note_file, "note"),
        )
    if args.command == "chronicle-timeline":
        return command_chronicle_timeline(runtime, args.limit)
    if args.command == "chronicle-themes":
        return command_chronicle_themes(runtime, args.limit)
    if args.command == "mode-status":
        return command_mode_status(runtime)
    if args.command == "mode-transition":
        return command_mode_transition(runtime, args.actor, args.mode, args.reason)
    if args.command == "mode-brief":
        return command_mode_brief(runtime, args.mode)
    if args.command == "family-plan":
        return command_family_plan(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "departure-plan":
        return command_departure_plan(
            runtime,
            args.actor,
            read_inline_or_file(args.context, args.context_file, "context")
            if (args.context or args.context_file)
            else "",
        )
    if args.command == "rebekah-center":
        return command_rebekah_center(
            runtime,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "troop-plan":
        return command_troop_plan(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "grocery-support":
        return command_grocery_support(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "meal-plan":
        return command_meal_plan(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "vehicle-plan":
        return command_vehicle_plan(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "weather-contingency":
        return command_weather_contingency(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "message-draft":
        return command_message_draft(
            runtime,
            args.actor,
            args.audience,
            args.purpose,
            read_inline_or_file(args.context, args.context_file, "context"),
            args.tone,
        )
    if args.command == "message-drafts":
        return command_message_drafts(runtime, args.limit)
    if args.command == "parent-message":
        return command_parent_message(
            runtime,
            args.actor,
            args.audience,
            args.purpose,
            read_inline_or_file(args.context, args.context_file, "context"),
            args.tone,
        )
    if args.command == "anomaly-watch":
        return command_anomaly_watch(runtime)
    if args.command == "security-event":
        return command_security_event(
            runtime,
            args.actor,
            args.category,
            args.location,
            read_inline_or_file(args.detail, args.detail_file, "detail"),
            args.severity,
        )
    if args.command == "safety-alert":
        return command_safety_alert(
            runtime,
            args.actor,
            args.hazard,
            args.source,
            read_inline_or_file(args.detail, args.detail_file, "detail"),
            args.severity,
        )
    if args.command == "weather-alert":
        return command_weather_alert(
            runtime,
            args.actor,
            read_inline_or_file(args.context, args.context_file, "context"),
        )
    if args.command == "child-arrival":
        return command_child_arrival(
            runtime,
            args.actor,
            args.location,
            read_inline_or_file(args.detail, args.detail_file, "detail"),
        )
    if args.command == "unlock-policy":
        return command_unlock_policy(
            runtime,
            args.actor,
            args.target,
            requested_by_voice=not args.not_voice,
            second_factor_present=args.second_factor,
        )
    if args.command == "overnight-review":
        return command_overnight_review(runtime)
    if args.command == "security-incidents":
        return command_security_incidents(runtime, args.limit)
    if args.command == "home-overview":
        return command_home_overview(runtime)
    if args.command == "room-scene":
        return command_room_scene(runtime, args.actor, args.room, args.scene, args.intent)
    if args.command == "climate-status":
        return command_climate_status(runtime)
    if args.command == "climate-control":
        return command_climate_control(
            runtime,
            args.actor,
            args.zone,
            args.mode,
            args.target_temp,
            args.context,
        )
    if args.command == "access-overview":
        return command_access_overview(runtime)
    if args.command == "access-control":
        return command_access_control(runtime, args.actor, args.target, args.state)
    if args.command == "garage-status":
        return command_garage_status(runtime)
    if args.command == "garage-check":
        return command_garage_check(runtime, args.actor, args.target)
    if args.command == "leak-monitor":
        return command_leak_monitor(runtime)
    if args.command == "cold-storage-monitor":
        return command_cold_storage_monitor(runtime)
    if args.command == "energy-window":
        return command_energy_window(runtime, args.appliance, args.request)
    if args.command == "outage-readiness":
        return command_outage_readiness(runtime)
    if args.command == "perception-overview":
        return command_perception_overview(runtime)
    if args.command == "mic-ingress":
        return command_mic_ingress(runtime, args.microphone, args.transcript, args.wake_word, args.actor_hint)
    if args.command == "presence-update":
        return command_presence_update(runtime, args.sensor, args.room, args.occupied, args.detail)
    if args.command == "phone-presence":
        return command_phone_presence(runtime, args.actor, args.device, args.state, args.zone, args.detail)
    if args.command == "camera-event":
        return command_camera_event(
            runtime,
            args.camera,
            args.event_type,
            args.detail,
            args.object,
            args.confidence,
        )
    if args.command == "package-rule":
        return command_package_rule(runtime, args.zone, args.preferred_drop, args.rain_sensitive, args.note)
    if args.command == "object-recognition":
        return command_object_recognition(runtime, args.source, args.room, args.object, args.detail, args.confidence)
    if args.command == "environmental-anomaly":
        return command_environmental_anomaly(
            runtime,
            args.category,
            args.source,
            args.reading,
            args.baseline,
            args.severity,
            args.detail,
        )
    if args.command == "privacy-state":
        return command_privacy_state(runtime)
    if args.command == "privacy-update":
        return command_privacy_update(runtime, args.kind, args.target, args.enabled, args.muted)
    if args.command == "memory-overview":
        return command_memory_overview(runtime, args.viewer)
    if args.command == "memory-remember":
        return command_memory_remember(
            runtime,
            args.actor,
            args.type,
            args.scope,
            args.summary,
            args.detail,
            args.owner,
            args.project,
            args.tags,
            args.sensitivity,
        )
    if args.command == "memory-review":
        return command_memory_review(runtime, args.viewer, args.type, args.owner, args.project)
    if args.command == "memory-forget":
        return command_memory_forget(runtime, args.viewer, args.entry_id)
    if args.command == "memory-export":
        return command_memory_export(runtime, args.viewer, args.type, args.owner, args.project)
    if args.command == "memory-proposals":
        return command_memory_proposals(runtime, args.status)
    if args.command == "memory-approve":
        return command_memory_approve(runtime, args.proposal_id, args.decision)
    if args.command == "openviking-status":
        return command_openviking_status(runtime)
    if args.command == "openviking-sync-memory":
        return command_openviking_sync_memory(runtime)
    if args.command == "catalyst-signal":
        return command_catalyst_signal(
            runtime,
            args.actor,
            args.source,
            args.title,
            read_inline_or_file(args.content, args.content_file, "content"),
            args.sender,
            [item.strip() for item in args.tags.split(",") if item.strip()],
        )
    if args.command == "catalyst-email-triage":
        return command_catalyst_email_triage(
            runtime,
            args.actor,
            args.subject,
            read_inline_or_file(args.body, args.body_file, "body"),
            args.sender,
        )
    if args.command == "catalyst-meeting-prep":
        return command_catalyst_meeting_prep(
            runtime,
            args.actor,
            args.meeting_title,
            args.open_commitment,
            args.recent_signal,
        )
    if args.command == "catalyst-meeting-extract":
        return command_catalyst_meeting_extract(
            runtime,
            args.actor,
            read_inline_or_file(args.transcript, args.transcript_file, "transcript"),
            args.context,
        )
    if args.command == "catalyst-briefing":
        return command_catalyst_briefing(runtime, args.actor, args.context)
    if args.command == "catalyst-draft":
        return command_catalyst_draft(
            runtime,
            args.actor,
            args.intent,
            read_inline_or_file(args.context, args.context_file, "context"),
            args.recipient,
            args.tone,
        )
    if args.command == "catalyst-project-brief":
        return command_catalyst_project_brief(
            runtime,
            args.actor,
            args.project_name,
            args.problem,
            args.desired_outcome,
            args.constraints,
        )
    if args.command == "catalyst-implementation-plan":
        return command_catalyst_implementation_plan(
            runtime,
            args.actor,
            args.project_name,
            read_inline_or_file(args.brief, args.brief_file, "brief"),
            args.constraints,
        )
    if args.command == "catalyst-proactive":
        return command_catalyst_proactive(runtime, args.actor, args.horizon, args.context)
    if args.command == "voice-note":
        return command_voice_note(
            runtime,
            args.actor,
            args.source,
            read_inline_or_file(args.note, args.note_file, "note"),
        )
    if args.command == "voice-notes":
        return command_voice_notes(runtime, args.limit)
    if args.command == "child-boundaries":
        return command_child_boundaries(runtime, args.actor)
    if args.command == "tutor":
        return command_tutor(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
            args.subject,
        )
    if args.command == "tutoring-summaries":
        return command_tutoring_summaries(runtime, args.viewer, args.child, args.limit)
    if args.command == "device-boundary":
        return command_device_boundary(runtime, args.actor, args.window)
    if args.command == "device-boundaries":
        return command_device_boundaries(runtime, args.child, args.limit)
    if args.command == "workshop-plan":
        return command_workshop_plan(
            runtime,
            args.actor,
            read_inline_or_file(args.request, args.request_file, "request"),
        )
    if args.command == "printer-status":
        return command_printer_status(runtime)
    if args.command == "material-recommendation":
        return command_material_recommendation(
            runtime,
            args.actor,
            args.part,
            args.use_case,
            read_inline_or_file(args.requirements, args.requirements_file, "requirements"),
        )
    if args.command == "cad-package":
        return command_cad_package(
            runtime,
            args.actor,
            args.part,
            read_inline_or_file(args.dimensions, args.dimensions_file, "dimensions"),
            read_inline_or_file(args.constraints, args.constraints_file, "constraints"),
        )
    if args.command == "print-prep":
        return command_print_prep(
            runtime,
            args.actor,
            args.part,
            args.printer,
            args.material,
            args.profile,
            read_inline_or_file(args.notes, args.notes_file, "notes")
            if (args.notes or args.notes_file)
            else "",
        )
    if args.command == "safety-check":
        return command_safety_check(
            runtime,
            args.actor,
            args.operation,
            read_inline_or_file(args.context, args.context_file, "context")
            if (args.context or args.context_file)
            else "",
        )
    if args.command == "inventory":
        return command_inventory(runtime)
    if args.command == "cad-packages":
        return command_cad_packages(runtime, args.limit)
    if args.command == "print-preps":
        return command_print_preps(runtime, args.limit)
    if args.command == "inspect-part":
        return command_inspect_part(
            runtime,
            args.actor,
            args.part,
            args.request,
            read_inline_or_file(args.observations, args.observations_file, "observations"),
            read_inline_or_file(args.goals, args.goals_file, "goals"),
            args.image_path,
        )
    if args.command == "vendor-prep":
        return command_vendor_prep(
            runtime,
            args.actor,
            args.part,
            args.vendor,
            args.process,
            args.material,
            read_inline_or_file(args.notes, args.notes_file, "notes")
            if (args.notes or args.notes_file)
            else "",
        )
    if args.command == "vendor-preps":
        return command_vendor_preps(runtime, args.limit)
    if args.command == "openclaw-bridge":
        return command_openclaw_bridge(
            runtime,
            args.actor,
            args.room,
            args.request,
            args.device_name,
            args.require_wake_word,
        )
    if args.command == "voice":
        return command_voice(runtime, args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
