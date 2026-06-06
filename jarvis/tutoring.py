from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .models import DeviceBoundaryRoutine, RequestPlan, TutoringSession, UserProfile
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt
from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl


def _extract_section(text: str, heading: str) -> str:
    marker = f"{heading}:"
    if marker not in text:
        return ""
    fragment = text.split(marker, 1)[1]
    lines = []
    for line in fragment.splitlines():
        stripped = line.strip()
        if stripped and any(stripped.startswith(f"{name}:") for name in ("Reply", "Parent Summary", "Encouragement", "Follow Up")):
            if stripped.startswith(marker):
                continue
            break
        lines.append(line)
    return "\n".join(line.strip() for line in lines).strip()


class TutoringStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_path = self.root / "sessions.jsonl"
        self.sessions_log_path = self.root / "sessions_state_log.jsonl"
        self.boundaries_path = self.root / "device_boundaries.json"
        self.boundaries_log_path = self.root / "device_boundaries_log.jsonl"

    def add_session(self, session: TutoringSession) -> None:
        records = self._load_sessions()
        records.append(asdict(session))
        self._save_sessions(records)

    def list_sessions(self, child_name: str = "", limit: int = 20) -> list[dict]:
        records = self._load_sessions()
        if child_name:
            lowered = child_name.strip().lower()
            records = [item for item in records if item["actor"].strip().lower() == lowered]
        return list(reversed(records[-limit:]))

    def _load_sessions(self) -> list[dict]:
        if self.sessions_path.exists():
            try:
                records = [json.loads(line) for line in self.sessions_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                if records:
                    return records
            except Exception:
                pass
        return self._load_sessions_from_log()

    def _load_sessions_from_log(self) -> list[dict]:
        if not self.sessions_log_path.exists():
            return []
        try:
            latest: list[dict] = []
            for line in self.sessions_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
        except Exception:
            return []

    def _save_sessions(self, records: list[dict]) -> None:
        atomic_write_jsonl(self.sessions_path, records)
        append_jsonl(
            self.sessions_log_path,
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
        )

    def _load_boundaries(self) -> list[dict]:
        if not self.boundaries_path.exists():
            return self._load_boundaries_from_log()
        try:
            return json.loads(self.boundaries_path.read_text(encoding="utf-8"))
        except Exception:
            return self._load_boundaries_from_log()

    def _load_boundaries_from_log(self) -> list[dict]:
        if not self.boundaries_log_path.exists():
            return []
        try:
            latest: list[dict] = []
            for line in self.boundaries_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
        except Exception:
            return []

    def _save_boundaries(self, records: list[dict]) -> None:
        atomic_write_json(self.boundaries_path, records)
        append_jsonl(
            self.boundaries_log_path,
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
        )

    def add_boundary(self, routine: DeviceBoundaryRoutine) -> None:
        records = self._load_boundaries()
        records.append(asdict(routine))
        self._save_boundaries(records)

    def list_boundaries(self, child_name: str = "", limit: int = 20) -> list[dict]:
        records = self._load_boundaries()
        if child_name:
            lowered = child_name.strip().lower()
            records = [item for item in records if item["actor"].strip().lower() == lowered]
        return list(reversed(records[-limit:]))

    def update_boundary_status(self, routine_id: str, status: str) -> dict | None:
        records = self._load_boundaries()
        updated = None
        for item in records:
            if item["routine_id"] == routine_id:
                item["status"] = status
                updated = item
                break
        if updated:
            self._save_boundaries(records)
        return updated


class TutoringSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: TutoringStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        self.profile = config.load_json_profile(
            config.tutoring_profile_path,
            {
                "policyNotes": [],
                "parentViewNotes": [],
                "children": {},
                "adultKeywords": [
                    "thermo",
                    "confidential",
                    "manuscript",
                    "meeting notes",
                    "research brief",
                    "executive brief",
                    "parent message",
                    "adult calendar",
                ],
                "boundaryNotes": [],
            },
        )

    def apply_child_boundaries(self, actor: UserProfile, plan: RequestPlan) -> RequestPlan:
        if actor.permissions != "child":
            return plan

        lowered = plan.request.lower()
        profile = self._child_profile(actor.display_name)
        adult_keywords = [item.lower() for item in self.profile.get("adultKeywords", [])]
        blocked_topics = [item.lower() for item in profile.get("blockedTopics", [])]
        forbidden_modules = set(profile.get("forbiddenModules", ["executive-work", "workshop-copilot"]))

        boundary_hit = next(
            (
                token
                for token in [*adult_keywords, *blocked_topics]
                if token and token in lowered
            ),
            "",
        )

        if plan.module in forbidden_modules or boundary_hit:
            plan.module = "child-tutor"
            plan.workstream = "boundary-redirect"
            plan.allowed = False
            plan.needs_approval = False
            plan.second_factor_required = False
            plan.rationale = (
                "Child profile boundary blocked access to adult work data or restricted household tools."
            )
        return plan

    def child_boundaries(self, child: UserProfile | None = None) -> list[dict]:
        children = [child] if child is not None else []
        if not children:
            return []

        reports = []
        for profile in children:
            child_profile = self._child_profile(profile.display_name)
            reports.append(
                {
                    "actor": profile.display_name,
                    "permissions": profile.permissions,
                    "allowed_modules": child_profile.get(
                        "allowedModules",
                        ["child-tutor", "faith-and-formation", "family-logistics", "household-associate"],
                    ),
                    "forbidden_modules": child_profile.get(
                        "forbiddenModules",
                        ["executive-work", "workshop-copilot", "perception-mesh"],
                    ),
                    "blocked_topics": child_profile.get("blockedTopics", []),
                    "study_supports": child_profile.get("studySupports", []),
                    "parent_visibility": child_profile.get("parentVisibility", "summary-only"),
                }
            )
        return reports

    def tutoring_turn(self, actor: UserProfile, request: str, subject: str = "") -> dict:
        if actor.permissions != "child":
            raise PermissionError("Tutoring mode is reserved for child profiles.")

        profile = self._child_profile(actor.display_name)
        subject_label = subject or self._infer_subject(request, actor, profile)
        coaching_mode = self._infer_coaching_mode(request, subject_label)
        boundary_status = "allowed"
        lowered = request.lower()

        if any(phrase.lower() in lowered for phrase in profile.get("blockedTopics", [])):
            boundary_status = "redirected"

        system = build_specialist_prompt(
            "child tutoring",
            "Coach, quiz, rehearse, explain, and organize without doing deceptive schoolwork for the child.",
            extra_guidance=(
                "Use brief Socratic guidance, one step at a time. "
                "If the child asks you to do the work for them, redirect kindly and help them start their own thinking. "
                "Return labeled sections exactly as: Reply:, Parent Summary:, Encouragement:, Follow Up:. "
                f"Policy notes: {' '.join(self.profile.get('policyNotes', []))} "
                f"Child notes: {' '.join(profile.get('notes', []))} "
                f"Study supports: {', '.join(profile.get('studySupports', []))} "
                f"Coaching mode: {coaching_mode}. Subject: {subject_label}."
            ),
        )
        user = (
            f"Student: {actor.display_name}\n"
            f"Subject: {subject_label}\n"
            f"Request: {request}\n"
            "Remember that the child must provide their own answer or voice for final school output."
        )
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=420)
        response_text = _extract_section(raw, "Reply") or raw.strip()
        parent_summary = _extract_section(raw, "Parent Summary") or "Tutoring session completed."
        encouragement = _extract_section(raw, "Encouragement") or "Keep going one step at a time."
        follow_up = _extract_section(raw, "Follow Up") or "Ask the child to explain the next step in their own words."
        frustration_signal = self._infer_frustration(request, response_text)

        session = TutoringSession(
            session_id=str(uuid.uuid4()),
            actor=actor.display_name,
            subject=subject_label,
            request=request,
            coaching_mode=coaching_mode,
            response_text=response_text,
            parent_summary=parent_summary,
            boundary_status=boundary_status,
            encouragement=encouragement,
            follow_up=follow_up,
            frustration_signal=frustration_signal,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_session(session)
        return asdict(session)

    def parent_summaries(self, viewer: UserProfile, child_name: str = "", limit: int = 10) -> dict:
        if viewer.permissions != "adult":
            raise PermissionError("Only adult profiles may view tutoring summaries.")

        entries = self.store.list_sessions(child_name=child_name, limit=limit)
        by_child: dict[str, dict] = {}
        for entry in entries:
            bucket = by_child.setdefault(
                entry["actor"],
                {
                    "actor": entry["actor"],
                    "session_count": 0,
                    "subjects": [],
                    "recent_parent_summaries": [],
                    "frustration_signals": [],
                },
            )
            bucket["session_count"] += 1
            if entry["subject"] not in bucket["subjects"]:
                bucket["subjects"].append(entry["subject"])
            if len(bucket["recent_parent_summaries"]) < 3:
                bucket["recent_parent_summaries"].append(entry["parent_summary"])
            if entry["frustration_signal"] not in {"low", ""} and entry["frustration_signal"] not in bucket["frustration_signals"]:
                bucket["frustration_signals"].append(entry["frustration_signal"])

        return {
            "viewer": viewer.display_name,
            "notes": self.profile.get("parentViewNotes", []),
            "children": list(by_child.values()),
            "sessions": entries,
            "device_boundaries": self.store.list_boundaries(child_name=child_name, limit=limit),
        }

    def device_boundary_plan(self, actor: UserProfile, window_label: str = "") -> dict:
        if actor.permissions != "child":
            raise PermissionError("Device boundary routines are only defined for child profiles.")

        profile = self._child_profile(actor.display_name)
        boundary = profile.get("deviceBoundary", {})
        chosen_label = window_label or boundary.get("windowLabel", "Evening dock")
        routine = DeviceBoundaryRoutine(
            routine_id=str(uuid.uuid4()),
            actor=actor.display_name,
            window_label=chosen_label,
            checklist=list(boundary.get("studyChecklist", [])),
            device_expectation=boundary.get("deviceExpectation", "Dock the device and reset the study station."),
            reminder_text=boundary.get("reminderText", "Dock the device, reset the desk, and be ready for tomorrow."),
            status="open",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_boundary(routine)
        return asdict(routine)

    def list_device_boundaries(self, child_name: str = "", limit: int = 20) -> list[dict]:
        return self.store.list_boundaries(child_name=child_name, limit=limit)

    def update_device_boundary_status(self, routine_id: str, status: str) -> dict | None:
        return self.store.update_boundary_status(routine_id, status)

    def denial_response(self, actor: UserProfile, request: str, rationale: str) -> str:
        profile = self._child_profile(actor.display_name)
        redirect = profile.get("redirectPrompt", "Let us work on your assignment in a way that stays honest and actually helps you learn.")
        return (
            f"I cannot help with that request as asked. {rationale} "
            f"{redirect} Tell me the class, what part feels stuck, and what you have tried so far."
        )

    def _child_profile(self, actor_name: str) -> dict:
        children = self.profile.get("children", {})
        return children.get(
            actor_name,
            {
                "studySupports": [],
                "notes": [],
                "blockedTopics": [],
                "allowedModules": ["child-tutor", "faith-and-formation", "family-logistics", "household-associate"],
                "forbiddenModules": ["executive-work", "workshop-copilot", "perception-mesh"],
                "parentVisibility": "summary-only",
                "redirectPrompt": "I can still help you think it through honestly.",
                "deviceBoundary": {
                    "windowLabel": "Evening dock",
                    "studyChecklist": [],
                    "deviceExpectation": "Dock the device and reset the study station.",
                    "reminderText": "Dock the device, reset the desk, and be ready for tomorrow.",
                },
            },
        )

    def _infer_subject(self, request: str, actor: UserProfile, profile: dict) -> str:
        lowered = request.lower()
        if "math" in lowered or "equation" in lowered or "quiz" in lowered:
            return "math"
        if "read" in lowered or "book" in lowered or "essay" in lowered:
            return "reading"
        if "slide" in lowered or "presentation" in lowered or "project" in lowered:
            return "presentation"
        supports = profile.get("studySupports", [])
        if supports:
            return supports[0]
        return actor.priorities[0] if actor.priorities else "general study"

    def _infer_coaching_mode(self, request: str, subject: str) -> str:
        lowered = request.lower()
        if "quiz me" in lowered or "warmup" in lowered:
            return "quiz-practice"
        if "presentation" in lowered or "slide" in lowered or subject == "presentation":
            return "presentation-rehearsal"
        if "organize" in lowered or "outline" in lowered or "project" in lowered:
            return "project-organization"
        if "explain" in lowered or "understand" in lowered:
            return "guided-explanation"
        return "homework-coaching"

    def _infer_frustration(self, request: str, response_text: str) -> str:
        lowered = f"{request} {response_text}".lower()
        if any(token in lowered for token in ("frustrated", "stuck", "hate", "angry", "overwhelmed")):
            return "elevated"
        if any(token in lowered for token in ("unsure", "confused", "maybe")):
            return "watch"
        return "low"
