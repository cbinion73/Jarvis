from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen
import time
import uuid

from .persistence import append_jsonl, atomic_write_json

MANIFESTS_ROOT = Path(__file__).resolve().parent / "manifests"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InterfaceRouterStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_path = self.root / "sessions.json"
        self.results_path = self.root / "results.json"

    def _log_path(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}_log.jsonl")

    def _state_log_path(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}_state_log.jsonl")

    def _load_map(self, path: Path) -> dict[str, dict[str, Any]]:
        if not path.exists():
            payload = self._load_map_from_state_log(path)
            if payload:
                return payload
            return self._load_map_from_log(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = self._load_map_from_state_log(path)
            if payload:
                return payload
            return self._load_map_from_log(path)
        if not isinstance(payload, dict):
            payload = self._load_map_from_state_log(path)
            if payload:
                return payload
            return {}
        loaded = {str(key): value for key, value in payload.items() if isinstance(value, dict)}
        if loaded:
            return loaded
        replayed = self._load_map_from_state_log(path)
        if replayed:
            return replayed
        return loaded

    def _load_map_from_log(self, path: Path) -> dict[str, dict[str, Any]]:
        try:
            log_path = self._log_path(path)
            if not log_path.exists():
                return {}
            latest: dict[str, dict[str, Any]] = {}
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                state = payload.get("payload")
                if not isinstance(state, dict):
                    continue
                latest = {str(key): value for key, value in state.items() if isinstance(value, dict)}
            return latest
        except (OSError, json.JSONDecodeError):
            return {}

    def _load_map_from_state_log(self, path: Path) -> dict[str, dict[str, Any]]:
        try:
            log_path = self._state_log_path(path)
            if not log_path.exists():
                return {}
            latest: dict[str, dict[str, Any]] = {}
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                state = payload.get("payload")
                if not isinstance(state, dict):
                    continue
                latest = {str(key): value for key, value in state.items() if isinstance(value, dict)}
            return latest
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_map(self, path: Path, payload: dict[str, dict[str, Any]]) -> None:
        atomic_write_json(path, payload)
        append_jsonl(
            self._log_path(path),
            {
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": payload,
            },
        )
        append_jsonl(
            self._state_log_path(path),
            {
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": payload,
            },
        )

    def save_session(self, session: dict[str, Any]) -> dict[str, Any]:
        request_id = str(session.get("request_id", "")).strip()
        if not request_id:
            raise ValueError("request_id is required")
        sessions = self._load_map(self.sessions_path)
        sessions[request_id] = session
        self._save_map(self.sessions_path, sessions)
        return session

    def get_session(self, request_id: str) -> dict[str, Any] | None:
        return self._load_map(self.sessions_path).get(str(request_id).strip())

    def save_result(self, result: dict[str, Any]) -> dict[str, Any]:
        request_id = str(result.get("request_id", "")).strip()
        if not request_id:
            raise ValueError("request_id is required")
        results = self._load_map(self.results_path)
        results[request_id] = result
        self._save_map(self.results_path, results)
        return result

    def get_result(self, request_id: str) -> dict[str, Any] | None:
        return self._load_map(self.results_path).get(str(request_id).strip())


@dataclass(slots=True)
class IntentClassification:
    intent_family: str
    intent_subtype: str
    target_system: str
    mode: str
    confidence: str
    rationale: str
    handoff_required: bool
    suggested_capability: str = ""


class InterfaceRouterSupport:
    def __init__(self, store: InterfaceRouterStore) -> None:
        self.store = store
        self._manifests = {
            "chronicle": self._load_manifest("chronicle"),
            "catalyst": self._load_manifest("catalyst"),
        }

    def _load_manifest(self, system: str) -> dict[str, Any]:
        path = MANIFESTS_ROOT / f"{system}.capabilities.json"
        if not path.exists():
            raise FileNotFoundError(f"Capability manifest missing for {system}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Capability manifest for {system} is invalid")
        return payload

    def system_manifest(self, system: str) -> dict[str, Any]:
        key = str(system).strip().lower()
        manifest = self._manifests.get(key)
        if not manifest:
            raise KeyError(f"Unknown system: {system}")
        return manifest

    def capability_manifests(self) -> dict[str, Any]:
        return {
            "systems": {name: manifest for name, manifest in self._manifests.items()},
            "intent_taxonomy": self.intent_taxonomy(),
        }

    def intent_taxonomy(self) -> dict[str, Any]:
        return {
            "faith.study": {"target_system": "chronicle", "default_mode": "launch"},
            "faith.prayer": {"target_system": "chronicle", "default_mode": "launch"},
            "faith.formation": {"target_system": "chronicle", "default_mode": "launch"},
            "faith.lookup": {"target_system": "chronicle", "default_mode": "embed"},
            "faith.capture": {"target_system": "chronicle", "default_mode": "delegate"},
            "day.review": {"target_system": "jarvis", "default_mode": "native"},
            "day.communications": {"target_system": "jarvis", "default_mode": "embed"},
            "day.calendar": {"target_system": "jarvis", "default_mode": "embed"},
            "exec.prep": {"target_system": "catalyst", "default_mode": "delegate"},
            "exec.research": {"target_system": "catalyst", "default_mode": "delegate"},
            "exec.decision": {"target_system": "catalyst", "default_mode": "delegate"},
            "exec.packaging": {"target_system": "catalyst", "default_mode": "delegate"},
            "system.route": {"target_system": "jarvis", "default_mode": "native"},
            "system.control": {"target_system": "jarvis", "default_mode": "native"},
        }

    def classify_intent(self, request_text: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        text = str(request_text or "").strip()
        lowered = text.lower()
        context = context or {}
        classification = self._classify(lowered)
        return {
            "request_text": text,
            "context": context,
            "intent_family": classification.intent_family,
            "intent_subtype": classification.intent_subtype,
            "target_system": classification.target_system,
            "mode": classification.mode,
            "confidence": classification.confidence,
            "rationale": classification.rationale,
            "handoff_required": classification.handoff_required,
            "suggested_capability": classification.suggested_capability,
        }

    def _classify(self, lowered: str) -> IntentClassification:
        faith_words = ("bible", "scripture", "chronicle", "pray", "prayer", "devotional", "study", "theology", "gospel", "corinthians", "psalm", "formation", "reflection")
        exec_words = ("meeting", "brief", "briefing", "decision", "vendor", "research", "synthesis", "deck", "executive", "roadmap", "project")
        day_words = ("today", "calendar", "agenda", "email", "inbox", "message", "messages", "follow-up", "followup", "schedule", "priorities")

        if any(word in lowered for word in faith_words):
            if any(word in lowered for word in ("pray", "prayer")):
                return IntentClassification("faith.prayer", "guided_prayer", "chronicle", "launch", "high", "Faith-language matched prayer intent.", True, "prayer_session")
            if any(word in lowered for word in ("remember", "recall", "timeline", "pattern")):
                return IntentClassification("faith.lookup", "formation_lookup", "chronicle", "embed", "medium", "Faith-language matched retrieval intent.", True, "formation_memory_lookup")
            if any(word in lowered for word in ("save", "capture", "record", "journal")):
                return IntentClassification("faith.capture", "spiritual_capture", "chronicle", "delegate", "medium", "Faith-language matched capture intent.", True, "record_spiritual_event")
            return IntentClassification("faith.study", "passage_study", "chronicle", "launch", "high", "Faith-language matched study intent.", True, "study_passage")

        if any(word in lowered for word in exec_words):
            if any(word in lowered for word in ("decision", "choose", "tradeoff", "recommend")):
                return IntentClassification("exec.decision", "decision_support", "catalyst", "delegate", "high", "Executive-language matched decision framing.", True, "decision_support")
            if any(word in lowered for word in ("research", "vendor", "landscape", "scan")):
                return IntentClassification("exec.research", "research_synthesis", "catalyst", "delegate", "high", "Executive-language matched synthesis work.", True, "research_synthesis")
            if any(word in lowered for word in ("deck", "memo", "outline", "package")):
                return IntentClassification("exec.packaging", "action_packaging", "catalyst", "delegate", "medium", "Executive-language matched packaging work.", True, "action_packaging")
            return IntentClassification("exec.prep", "meeting_or_brief_prep", "catalyst", "delegate", "high", "Executive-language matched prep work.", True, "meeting_prep")

        if any(word in lowered for word in day_words):
            return IntentClassification("day.review", "daily_orchestration", "jarvis", "native", "medium", "Day-management language matched JARVIS-native orchestration.", False)

        return IntentClassification("system.route", "general_routing", "jarvis", "native", "low", "No strong specialist signal found; keep work in JARVIS.", False)

    def create_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        handoff = dict(payload or {})
        target_system = str(handoff.get("target_system", "")).strip().lower()
        if target_system == "jarvis":
            raise ValueError("Native JARVIS intents do not require a handoff.")
        manifest = self.system_manifest(target_system)
        capability = str(handoff.get("capability", "")).strip()
        if not capability:
            raise ValueError("capability is required")
        capability_record = dict((manifest.get("capabilities") or {}).get(capability) or {})
        if not capability_record:
            raise ValueError(f"Unknown capability '{capability}' for {target_system}")
        request_id = str(handoff.get("request_id", "")).strip() or str(uuid.uuid4())
        actor = dict(handoff.get("actor") or {})
        actor_id = str(actor.get("actor_id", handoff.get("actor_id", "Chris"))).strip() or "Chris"
        mode = str(handoff.get("mode", "")).strip() or str((capability_record.get("mode_support") or ["delegate"])[0])
        intent_family = str(handoff.get("intent_family", "")).strip() or str((capability_record.get("intent_families") or ["system.route"])[0])
        permissions = dict(handoff.get("permissions") or {})
        if target_system == "catalyst" and not permissions:
            permissions = {"autonomy_level": "propose_only", "allowed_actions": []}
        if target_system == "chronicle":
            permissions = {}
        timestamp = str(handoff.get("timestamp", "")).strip() or _now_iso()
        context = dict(handoff.get("context") or {})
        return_contract = dict(handoff.get("return_contract") or {})
        session = {
            "request_id": request_id,
            "timestamp": timestamp,
            "source_system": str(handoff.get("source_system", "jarvis")).strip() or "jarvis",
            "target_system": target_system,
            "intent_family": intent_family,
            "intent_subtype": str(handoff.get("intent_subtype", "")).strip(),
            "capability": capability,
            "mode": mode,
            "actor": {
                "actor_id": actor_id,
                "role": str(actor.get("role", "primary_user")).strip() or "primary_user",
            },
            "context": context,
            "permissions": permissions,
            "return_contract": return_contract,
            "status": "accepted",
            "stub": True,
            "deep_link": self.deep_link_for(target_system, capability, context),
            "accepted_at": _now_iso(),
        }
        self.store.save_session(session)
        dispatched = self._dispatch_handoff(session)
        if dispatched:
            merged = {**session, **dispatched}
            self.store.save_session(merged)
            return merged
        return session

    def post_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload or {})
        request_id = str(result.get("request_id", "")).strip()
        if not request_id:
            raise ValueError("request_id is required")
        source_system = str(result.get("source_system", "")).strip().lower()
        if source_system not in {"chronicle", "catalyst"}:
            raise ValueError("source_system must be chronicle or catalyst")
        status = str(result.get("status", "")).strip()
        summary = str(result.get("summary", "")).strip()
        if not status or not summary:
            raise ValueError("status and summary are required")
        session = self.store.get_session(request_id)
        stored = {
            "request_id": request_id,
            "source_system": source_system,
            "status": status,
            "summary": summary,
            "session_id": str(result.get("session_id", request_id)).strip(),
            "record_ids": list(result.get("record_ids") or []),
            "artifact_type": str(result.get("artifact_type", "")).strip(),
            "artifact_id": str(result.get("artifact_id", "")).strip(),
            "artifact_uri": str(result.get("artifact_uri", "")).strip(),
            "memory_updates": list(result.get("memory_updates") or []),
            "proposed_actions": list(result.get("proposed_actions") or []),
            "deep_link": result.get("deep_link"),
            "received_at": _now_iso(),
            "stub": True,
        }
        self.store.save_result(stored)
        if session:
            updated = dict(session)
            updated["status"] = status
            updated["latest_result_summary"] = summary
            updated["result_received_at"] = stored["received_at"]
            self.store.save_session(updated)
        return stored

    def session_view(self, request_id: str) -> dict[str, Any]:
        session = self.store.get_session(request_id)
        if not session:
            raise KeyError(f"Unknown session: {request_id}")
        result = self.store.get_result(request_id)
        return {
            "session": session,
            "result": result,
        }

    def system_session_view(self, system: str, request_id: str) -> dict[str, Any]:
        snapshot = self.session_view(request_id)
        session = dict(snapshot.get("session") or {})
        if str(session.get("target_system", "")).strip().lower() != str(system).strip().lower():
            raise KeyError(f"Session {request_id} is not owned by {system}")
        return snapshot

    def result_view(self, request_id: str, *, source_system: str | None = None) -> dict[str, Any]:
        result = self.store.get_result(request_id)
        if not result:
            raise KeyError(f"Unknown result: {request_id}")
        if source_system and str(result.get("source_system", "")).strip().lower() != str(source_system).strip().lower():
            raise KeyError(f"Result {request_id} is not owned by {source_system}")
        return result

    def deep_link_for(self, system: str, capability: str, context: dict[str, Any]) -> str | None:
        if system == "chronicle":
            if capability == "study_passage":
                return self._uri("chronicle://study", {"passage": context.get("passage") or context.get("prompt") or ""})
            if capability == "trace_theme":
                return self._uri("chronicle://themes/trace", {"theme": context.get("theme", "")})
            if capability == "prayer_session":
                return self._uri("chronicle://prayer/session", {"prompt": context.get("prompt", "")})
            if capability == "formation_memory_lookup":
                return self._uri("chronicle://memory", {"query": context.get("prompt") or context.get("theme") or ""})
            if capability == "record_spiritual_event":
                return self._uri("chronicle://capture", {"theme": context.get("theme", "")})
            if capability == "spiritual_timeline":
                return self._uri("chronicle://formation/timeline", {"range": context.get("range", "90d")})
        if system == "catalyst":
            if capability == "meeting_prep":
                return self._uri("catalyst://meeting-prep", {"event_id": context.get("calendar_event_id", ""), "title": context.get("meeting_title", "")})
            if capability == "briefing_build":
                return self._uri("catalyst://briefing", {"goal": context.get("goal", "")})
            if capability == "decision_support":
                return self._uri("catalyst://decision", {"goal": context.get("goal", "")})
            if capability == "research_synthesis":
                return self._uri("catalyst://research", {"goal": context.get("goal", "")})
            if capability == "action_packaging":
                return self._uri("catalyst://packaging", {"goal": context.get("goal", "")})
            if capability == "signal_triage":
                return self._uri("catalyst://signals", {"horizon": context.get("horizon", "today")})
        return None

    def _uri(self, base: str, params: dict[str, Any]) -> str:
        clean = {str(key): str(value) for key, value in params.items() if str(value).strip()}
        if not clean:
            return base
        return f"{base}?{urlencode(clean)}"

    def _target_base_url(self, system: str) -> str:
        if system == "chronicle":
            return str(os.getenv("CHRONICLE_API_BASE_URL", "http://127.0.0.1:5174")).strip()
        if system == "catalyst":
            return str(os.getenv("CATALYST_API_BASE_URL", "http://127.0.0.1:3001")).strip()
        return ""

    def _dispatch_handoff(self, session: dict[str, Any]) -> dict[str, Any] | None:
        target_system = str(session.get("target_system", "")).strip().lower()
        base_url = self._target_base_url(target_system).rstrip("/")
        if not base_url:
            return None
        endpoint = f"{base_url}/api/{target_system}/handoff"
        try:
            body = json.dumps(session).encode("utf-8")
            request = Request(
                endpoint,
                data=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return {
                    "dispatch": {
                        "attempted": True,
                        "target_url": endpoint,
                        "ok": True,
                    },
                    "status": str(payload.get("status", session.get("status", "accepted"))),
                    "deep_link": payload.get("deep_link", session.get("deep_link")),
                    "external_response": payload,
                }
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {
                "dispatch": {
                    "attempted": True,
                    "target_url": endpoint,
                    "ok": False,
                    "detail": str(exc),
                }
            }
        return None
