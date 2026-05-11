from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AppConfig
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CatalystStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.signals_path = self.root / "signals.json"
        self.email_triage_path = self.root / "email_triage_runs.json"
        self.meeting_prep_path = self.root / "meeting_prep_runs.json"
        self.meeting_extract_path = self.root / "meeting_extraction_runs.json"
        self.briefing_path = self.root / "briefing_runs.json"
        self.drafts_path = self.root / "draft_runs.json"
        self.project_briefs_path = self.root / "project_briefs.json"
        self.implementation_plans_path = self.root / "implementation_plans.json"
        self.proactive_path = self.root / "proactive_surfacing_runs.json"
        self.pipeline_state_path = self.root / "pipeline_state.json"
        self.pipeline_review_path = self.root / "pipeline_reviews.json"

    def _load_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_records(self, path: Path, records: list[dict]) -> None:
        path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def add_record(self, path: Path, record: dict) -> None:
        records = self._load_records(path)
        records.append(record)
        self._save_records(path, records)

    def list_records(self, path: Path, limit: int = 10) -> list[dict]:
        records = self._load_records(path)
        return list(reversed(records[-limit:]))

    def add_signal(self, record: dict) -> None:
        self.add_record(self.signals_path, record)

    def list_signals(self, limit: int = 20) -> list[dict]:
        return self.list_records(self.signals_path, limit=limit)

    def _load_json(self, path: Path, *, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        return payload

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def pipeline_state(self) -> dict[str, Any]:
        payload = self._load_json(self.pipeline_state_path, default={})
        return payload if isinstance(payload, dict) else {}

    def save_pipeline_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._save_json(self.pipeline_state_path, payload)
        return payload

    def update_pipeline_state(self, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.pipeline_state()

        def _merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
            merged = dict(base)
            for key, value in incoming.items():
                if isinstance(value, dict) and isinstance(base.get(key), dict):
                    merged[key] = _merge(dict(base.get(key) or {}), value)
                else:
                    merged[key] = value
            return merged

        updated = _merge(current, patch)
        self.save_pipeline_state(updated)
        return updated

    def recent_pipeline_reviews(self, limit: int = 12) -> list[dict[str, Any]]:
        payload = self._load_json(self.pipeline_review_path, default=[])
        records = payload if isinstance(payload, list) else []
        return list(reversed(records[-limit:]))

    def append_pipeline_review(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = self._load_json(self.pipeline_review_path, default=[])
        records = payload if isinstance(payload, list) else []
        records.append(record)
        self._save_json(self.pipeline_review_path, records)
        return record


class CatalystSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: CatalystStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        self.profile = config.load_json_profile(
            config.catalyst_profile_path,
            {
                "name": "Catalyst Personal",
                "connectors": [
                    {"id": "manual", "label": "Manual Capture", "status": "ready", "notes": "Text-first workflow capture is live."},
                    {"id": "gmail", "label": "Gmail", "status": "planned", "notes": "Personal Gmail wiring comes later."},
                    {"id": "google_calendar", "label": "Google Calendar", "status": "planned", "notes": "Personal calendar wiring comes later."},
                    {"id": "docs", "label": "Local Notes", "status": "ready", "notes": "JARVIS-side notes and memory are available now."},
                ],
                "enabledWorkflows": [
                    "email triage",
                    "meeting prep",
                    "meeting extraction",
                    "briefing generation",
                    "draft composition",
                    "project planning",
                    "proactive surfacing",
                ],
                "workflowNotes": [
                    "Keep the workflow personal, local-first, and honest about what is connected.",
                    "Do not imply Gmail or Calendar sync is live until those connectors are wired.",
                    "Use Catalyst as a specialist backend under JARVIS rather than as a separate persona.",
                ],
                "personalDataPolicy": [
                    "No legacy work database dependencies.",
                    "No Microsoft Graph assumptions.",
                    "No Databricks-specific logic.",
                    "Store only local workflow artifacts and user-provided signals.",
                ],
            },
        )

    def connector_status(self) -> list[dict]:
        return list(self.profile.get("connectors", []))

    def default_pipeline_state(self) -> dict[str, Any]:
        return {
            "updated_at": _now_iso(),
            "crm": {
                "active_opportunity_target": 3,
                "weekly_followup_target": 5,
                "average_deal_value": None,
            },
            "opportunities": [],
            "thresholds": {
                "stalled_after_days": 7,
                "hot_followup_within_days": 2,
                "minimum_active_opportunities": 3,
            },
            "notes": [
                "Pipeline state is currently inferred from Catalyst signals, project briefs, and implementation plans until a live CRM connector is wired.",
            ],
        }

    def pipeline_state(self) -> dict[str, Any]:
        saved = self.store.pipeline_state()
        defaults = self.default_pipeline_state()
        if not saved:
            self.store.save_pipeline_state(defaults)
            return defaults
        merged = dict(defaults)
        for key, value in saved.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**dict(merged.get(key) or {}), **value}
            else:
                merged[key] = value
        if merged != saved:
            self.store.save_pipeline_state(merged)
        return merged

    def update_pipeline_state(self, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.pipeline_state()
        current["updated_at"] = _now_iso()
        merged = self.store.update_pipeline_state({**patch, "updated_at": current["updated_at"]})
        return self.pipeline_state() if merged else current

    def recent_pipeline_reviews(self, limit: int = 12) -> list[dict[str, Any]]:
        return self.store.recent_pipeline_reviews(limit=limit)

    def complete_pipeline_review(self, actor: str, payload: dict[str, Any]) -> dict[str, Any]:
        review = {
            "review_id": str(uuid.uuid4()),
            "actor": actor,
            "review_type": str(payload.get("review_type", "weekly")).strip() or "weekly",
            "completed_at": _now_iso(),
            "summary": str(payload.get("summary", "")).strip(),
            "score": payload.get("score"),
            "band": str(payload.get("band", "")).strip(),
            "note": str(payload.get("note", "")).strip(),
        }
        self.store.append_pipeline_review(review)
        return review

    def capture_signal(
        self,
        actor: str,
        source: str,
        title: str,
        content: str,
        *,
        sender: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        record = {
            "signal_id": str(uuid.uuid4()),
            "actor": actor,
            "source": source,
            "title": title,
            "content": content,
            "sender": sender,
            "tags": tags or [],
            "timestamp": _now_iso(),
        }
        self.store.add_signal(record)
        return record

    def email_triage(self, actor: str, subject: str, body: str, sender: str) -> dict:
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal email triage",
                "Classify importance, extract actions, and draft the lightest useful reply.",
                extra_guidance=(
                    "Return labeled sections exactly as: Importance:, Score:, Signals:, Requires Action:, "
                    "Actions:, Suggested Reply:. Keep the answer compact and operational."
                ),
            ),
            f"Actor: {actor}\nSender: {sender}\nSubject: {subject}\nBody:\n{body}",
            max_output_tokens=380,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "subject": subject,
            "sender": sender,
            "importance": (self._extract_section(raw, "Importance") or "normal").lower(),
            "score": self._safe_float(self._extract_section(raw, "Score"), 0.68),
            "signals": self._split_lines(self._extract_section(raw, "Signals")),
            "requires_action": self._parse_bool(self._extract_section(raw, "Requires Action")),
            "actions": self._split_lines(self._extract_section(raw, "Actions")),
            "suggested_reply": self._extract_section(raw, "Suggested Reply"),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.email_triage_path, result)
        self.capture_signal(actor, "email", subject, body, sender=sender, tags=["catalyst", "email"])
        return result

    def meeting_prep(self, actor: str, meeting_title: str, open_commitments: list[str], recent_signals: list[str]) -> dict:
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal meeting prep",
                "Prepare a calm meeting brief with decision posture, watch points, and a usable agenda.",
                extra_guidance=(
                    "Return labeled sections exactly as: Brief Points:, Watch Points:, Suggested Agenda:. "
                    "Bias toward concise, pre-meeting usefulness."
                ),
            ),
            (
                f"Actor: {actor}\nMeeting Title: {meeting_title}\n"
                f"Open Commitments:\n{self._as_bullets(open_commitments)}\n\n"
                f"Recent Signals:\n{self._as_bullets(recent_signals)}"
            ),
            max_output_tokens=420,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "meeting_title": meeting_title,
            "brief_points": self._split_lines(self._extract_section(raw, "Brief Points")),
            "watch_points": self._split_lines(self._extract_section(raw, "Watch Points")),
            "suggested_agenda": self._split_lines(self._extract_section(raw, "Suggested Agenda")),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.meeting_prep_path, result)
        return result

    def meeting_extraction(self, actor: str, transcript: str, context: str = "") -> dict:
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal meeting extraction",
                "Extract commitments, decisions, risks, actions, and stakeholders from a transcript.",
                extra_guidance=(
                    "Return labeled sections exactly as: Problem Statement:, Commitments:, Decisions:, Risks:, "
                    "Action Items:, Stakeholders:, Confidence:."
                ),
            ),
            f"Actor: {actor}\nContext: {context}\nTranscript:\n{transcript}",
            max_output_tokens=900,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "problem_statement": self._extract_section(raw, "Problem Statement"),
            "commitments": self._split_lines(self._extract_section(raw, "Commitments")),
            "decisions": self._split_lines(self._extract_section(raw, "Decisions")),
            "risks": self._split_lines(self._extract_section(raw, "Risks")),
            "action_items": self._split_lines(self._extract_section(raw, "Action Items")),
            "stakeholders": self._split_lines(self._extract_section(raw, "Stakeholders")),
            "confidence": self._safe_float(self._extract_section(raw, "Confidence"), 0.7),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.meeting_extract_path, result)
        self.capture_signal(
            actor,
            "meeting_transcript",
            "Meeting transcript",
            transcript[:2000],
            tags=["catalyst", "meeting"],
        )
        return result

    def briefing_generation(self, actor: str, user_context: str = "") -> dict:
        signals = self.store.list_signals(limit=8)
        meeting_runs = self.store.list_records(self.store.meeting_extract_path, limit=5)
        open_commitments = sum(len(item.get("commitments", [])) for item in meeting_runs)
        overdue_count = sum(1 for item in meeting_runs for risk in item.get("risks", []) if "overdue" in risk.lower())
        signal_lines = [
            f"{item.get('source', 'signal')}: {item.get('title', '')} - {item.get('content', '')[:180]}"
            for item in signals
        ]
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal briefing generation",
                "Rank the current signals and produce one practical next recommendation.",
                extra_guidance=(
                    "Return labeled sections exactly as: Recommendation:, Reasoning:, Confidence:, Action Items:."
                ),
            ),
            (
                f"Actor: {actor}\nUser Context: {user_context or 'Personal executive and household operator'}\n"
                f"Signals:\n{self._as_bullets(signal_lines)}\n\n"
                f"Open Commitments Count: {open_commitments}\nOverdue Count: {overdue_count}"
            ),
            max_output_tokens=420,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "signal_count": len(signals),
            "open_commitments": open_commitments,
            "overdue_count": overdue_count,
            "recommendation": self._extract_section(raw, "Recommendation"),
            "reasoning": self._extract_section(raw, "Reasoning"),
            "confidence": self._safe_float(self._extract_section(raw, "Confidence"), 0.68),
            "action_items": self._split_lines(self._extract_section(raw, "Action Items")),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.briefing_path, result)
        return result

    def draft_composition(self, actor: str, intent: str, context: str, recipient: str, tone: str = "professional") -> dict:
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal draft composition",
                "Compose a draft with a clear subject, body, and key points.",
                extra_guidance=(
                    "Return labeled sections exactly as: Subject:, Body:, Tone:, Key Points:. "
                    "Keep the tone aligned with JARVIS and the stated audience."
                ),
            ),
            f"Actor: {actor}\nRecipient: {recipient}\nTone: {tone}\nIntent: {intent}\nContext:\n{context}",
            max_output_tokens=520,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "recipient": recipient,
            "intent": intent,
            "subject": self._extract_section(raw, "Subject"),
            "body": self._extract_section(raw, "Body"),
            "tone": self._extract_section(raw, "Tone") or tone,
            "key_points": self._split_lines(self._extract_section(raw, "Key Points")),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.drafts_path, result)
        return result

    def project_brief(self, actor: str, project_name: str, problem: str, desired_outcome: str, constraints: str = "") -> dict:
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal project planning",
                "Create an A3-style project brief for a personal initiative.",
                extra_guidance=(
                    "Return labeled sections exactly as: Situation:, Problem:, Goal:, In Scope:, Out Of Scope:, "
                    "First Release:, Risks:, Recommendation:."
                ),
            ),
            (
                f"Actor: {actor}\nProject: {project_name}\nProblem: {problem}\nDesired Outcome: {desired_outcome}\n"
                f"Constraints:\n{constraints}"
            ),
            max_output_tokens=950,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "project_name": project_name,
            "situation": self._extract_section(raw, "Situation"),
            "problem": self._extract_section(raw, "Problem") or problem,
            "goal": self._extract_section(raw, "Goal") or desired_outcome,
            "in_scope": self._split_lines(self._extract_section(raw, "In Scope")),
            "out_of_scope": self._split_lines(self._extract_section(raw, "Out Of Scope")),
            "first_release": self._split_lines(self._extract_section(raw, "First Release")),
            "risks": self._split_lines(self._extract_section(raw, "Risks")),
            "recommendation": self._extract_section(raw, "Recommendation"),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.project_briefs_path, result)
        return result

    def implementation_plan(self, actor: str, project_name: str, brief: str, constraints: str = "") -> dict:
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal implementation planning",
                "Turn a project brief into a tactical implementation plan.",
                extra_guidance=(
                    "Return labeled sections exactly as: Objective:, Workstreams:, Next Actions:, Dependencies:, Open Questions:."
                ),
            ),
            f"Actor: {actor}\nProject: {project_name}\nBrief:\n{brief}\n\nConstraints:\n{constraints}",
            max_output_tokens=900,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "project_name": project_name,
            "objective": self._extract_section(raw, "Objective"),
            "workstreams": self._split_lines(self._extract_section(raw, "Workstreams")),
            "next_actions": self._split_lines(self._extract_section(raw, "Next Actions")),
            "dependencies": self._split_lines(self._extract_section(raw, "Dependencies")),
            "open_questions": self._split_lines(self._extract_section(raw, "Open Questions")),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.implementation_plans_path, result)
        return result

    def proactive_surfacing(self, actor: str, horizon: str = "today", context: str = "") -> dict:
        signals = self.store.list_signals(limit=10)
        recent_briefs = self.store.list_records(self.store.briefing_path, limit=3)
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst proactive surfacing",
                "Surface the few next items that deserve attention without becoming noisy.",
                extra_guidance=(
                    "Return labeled sections exactly as: Opportunities:, Risks:, Recommended Focus:. "
                    "Keep it selective and human-manageable."
                ),
            ),
            (
                f"Actor: {actor}\nHorizon: {horizon}\nContext:\n{context}\n\n"
                f"Signals:\n{self._as_bullets([item.get('title', '') + ' - ' + item.get('content', '')[:160] for item in signals])}\n\n"
                f"Recent Brief Recommendations:\n{self._as_bullets([item.get('recommendation', '') for item in recent_briefs])}"
            ),
            max_output_tokens=460,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "horizon": horizon,
            "opportunities": self._split_lines(self._extract_section(raw, "Opportunities")),
            "risks": self._split_lines(self._extract_section(raw, "Risks")),
            "recommended_focus": self._split_lines(self._extract_section(raw, "Recommended Focus")),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.proactive_path, result)
        return result

    def overview(self) -> dict:
        latest_email = self.store.list_records(self.store.email_triage_path, limit=1)
        latest_meeting = self.store.list_records(self.store.meeting_extract_path, limit=1)
        latest_briefing = self.store.list_records(self.store.briefing_path, limit=1)
        latest_project = self.store.list_records(self.store.project_briefs_path, limit=1)
        return {
            "name": self.profile.get("name", "Catalyst Personal"),
            "connectors": self.connector_status(),
            "enabled_workflows": list(self.profile.get("enabledWorkflows", [])),
            "workflow_notes": list(self.profile.get("workflowNotes", [])),
            "personal_data_policy": list(self.profile.get("personalDataPolicy", [])),
            "recent_signals": self.store.list_signals(limit=6),
            "latest_runs": {
                "email_triage": latest_email[0] if latest_email else {},
                "meeting_extraction": latest_meeting[0] if latest_meeting else {},
                "briefing": latest_briefing[0] if latest_briefing else {},
                "project_brief": latest_project[0] if latest_project else {},
            },
            "counts": {
                "signals": len(self.store._load_records(self.store.signals_path)),
                "email_triage": len(self.store._load_records(self.store.email_triage_path)),
                "meeting_extractions": len(self.store._load_records(self.store.meeting_extract_path)),
                "briefings": len(self.store._load_records(self.store.briefing_path)),
                "drafts": len(self.store._load_records(self.store.drafts_path)),
                "project_briefs": len(self.store._load_records(self.store.project_briefs_path)),
                "implementation_plans": len(self.store._load_records(self.store.implementation_plans_path)),
            },
        }

    @staticmethod
    def _extract_section(text: str, heading: str) -> str:
        marker = f"{heading}:"
        if marker not in text:
            return ""
        tail = text.split(marker, 1)[1]
        lines = tail.splitlines()
        buffer: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped and buffer:
                break
            if ":" in stripped:
                candidate = stripped.split(":", 1)[0].strip()
                if candidate and candidate.replace(" ", "").replace("-", "").isalpha() and len(candidate) <= 32:
                    break
            if stripped.endswith(":") and stripped[:-1].replace(" ", "").isalpha():
                break
            buffer.append(line)
        return "\n".join(buffer).strip(" \n-")

    @staticmethod
    def _split_lines(text: str) -> list[str]:
        if not text:
            return []
        lines: list[str] = []
        for raw in text.splitlines():
            cleaned = raw.strip().lstrip("-").strip()
            if cleaned:
                lines.append(cleaned)
        if lines:
            return lines
        return [item.strip() for item in text.split(";") if item.strip()]

    @staticmethod
    def _safe_float(value: str, default: float) -> float:
        if not value:
            return default
        try:
            return float(value.strip().rstrip("%"))
        except ValueError:
            return default

    @staticmethod
    def _parse_bool(value: str) -> bool:
        if not value:
            return False
        lowered = value.strip().lower()
        if lowered in {"false", "no", "not required", "none"}:
            return False
        return True

    @staticmethod
    def _as_bullets(items: list[str]) -> str:
        if not items:
            return "- none"
        return "\n".join(f"- {item}" for item in items if item.strip())
