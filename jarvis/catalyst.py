from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import WorkLifecycleStage

from .config import AppConfig
from .data_hygiene import filter_records
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
        self.hypotheses_path = self.root / "hypotheses.json"
        self.proactive_path = self.root / "proactive_surfacing_runs.json"
        self.pipeline_state_path = self.root / "pipeline_state.json"
        self.pipeline_review_path = self.root / "pipeline_reviews.json"
        self.work_lifecycle_path = self.root / "work_lifecycle.json"

    def _load_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        records = json.loads(path.read_text(encoding="utf-8"))
        return filter_records(records if isinstance(records, list) else [])

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

    def _find_record_by_id(self, path: Path, record_id: str, id_fields: tuple[str, ...]) -> dict[str, Any] | None:
        needle = str(record_id).strip()
        if not needle:
            return None
        for item in self._load_records(path):
            for field in id_fields:
                if str(item.get(field, "")).strip() == needle:
                    return dict(item)
        return None

    def resolve_artifact(self, artifact_type: str, record_id: str) -> dict[str, Any] | None:
        normalized_type = str(artifact_type).strip().lower()
        record_key = str(record_id).strip()
        if not normalized_type or not record_key:
            return None
        lookup: dict[str, tuple[Path, tuple[str, ...]]] = {
            "signal": (self.signals_path, ("signal_id",)),
            "hypothesis": (self.hypotheses_path, ("run_id",)),
            "project-brief": (self.project_briefs_path, ("run_id",)),
            "implementation-plan": (self.implementation_plans_path, ("run_id",)),
            "pipeline-review": (self.pipeline_review_path, ("review_id",)),
            "briefing": (self.briefing_path, ("run_id",)),
            "draft": (self.drafts_path, ("run_id",)),
            "meeting-extraction": (self.meeting_extract_path, ("run_id",)),
            "meeting-prep": (self.meeting_prep_path, ("run_id",)),
            "proactive-surfacing": (self.proactive_path, ("run_id",)),
        }
        config = lookup.get(normalized_type)
        if config is None:
            return None
        path, id_fields = config
        return self._find_record_by_id(path, record_key, id_fields)

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

    def work_lifecycle(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.work_lifecycle_path, default=[])
        return filter_records(payload if isinstance(payload, list) else [])

    def save_work_lifecycle(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._save_json(self.work_lifecycle_path, records)
        return records

    def get_work_item(self, work_id: str) -> dict[str, Any] | None:
        work_id = str(work_id).strip()
        if not work_id:
            return None
        for item in self.work_lifecycle():
            if str(item.get("work_id", "")).strip() == work_id:
                return dict(item)
        return None

    def upsert_work_item(self, record: dict[str, Any]) -> dict[str, Any]:
        work_id = str(record.get("work_id", "")).strip()
        if not work_id:
            raise ValueError("work_id is required")
        records = self.work_lifecycle()
        replaced = False
        for index, item in enumerate(records):
            if str(item.get("work_id", "")).strip() == work_id:
                records[index] = record
                replaced = True
                break
        if not replaced:
            records.append(record)
        self.save_work_lifecycle(records)
        return record


class CatalystSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: CatalystStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        default_profile = {
            "name": "Catalyst Personal",
            "mission": "Run the family's opportunity, savings, and project portfolio with JARVIS as one coordinated system.",
            "portfolioLanes": [
                {"id": "family-savings", "label": "Family Savings", "description": "Cost reduction, bill optimization, and household efficiency."},
                {"id": "revenue-growth", "label": "Revenue Growth", "description": "Consulting, side hustles, offers, and other income expansion."},
                {"id": "money-management", "label": "Money Management", "description": "Cash flow, capital allocation, debt, reserves, and stewardship."},
                {"id": "writing-and-ip", "label": "Writing and IP", "description": "Books, frameworks, courses, and durable intellectual property."},
                {"id": "social-and-media", "label": "Social and Media", "description": "Content, audience building, platform strategy, and distribution."},
                {"id": "family-operations", "label": "Family Operations", "description": "Projects that reduce friction, increase calm, or improve daily life."},
            ],
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
                "hypothesis generation",
                "proactive surfacing",
            ],
            "workflowNotes": [
                "Keep the workflow personal, local-first, and honest about what is connected.",
                "Do not imply Gmail or Calendar sync is live until those connectors are wired.",
                "Use Catalyst as a specialist backend under JARVIS rather than as a separate persona.",
                "Treat Catalyst as the family portfolio layer for savings, revenue, stewardship, and creative leverage.",
                "Let JARVIS agents contribute hypotheses, but keep major moves explicit and reviewable.",
            ],
            "personalDataPolicy": [
                "No legacy work database dependencies.",
                "No Microsoft Graph assumptions.",
                "No Databricks-specific logic.",
                "Store only local workflow artifacts and user-provided signals.",
            ],
        }
        loaded_profile = config.load_json_profile(config.catalyst_profile_path, default_profile)
        self.profile = dict(loaded_profile)
        self.profile["mission"] = str(self.profile.get("mission", "")).strip() or default_profile["mission"]
        self.profile["portfolioLanes"] = list(self.profile.get("portfolioLanes") or default_profile["portfolioLanes"])
        self.profile["enabledWorkflows"] = self._merge_profile_list(default_profile["enabledWorkflows"], self.profile.get("enabledWorkflows"))
        self.profile["workflowNotes"] = self._merge_profile_list(default_profile["workflowNotes"], self.profile.get("workflowNotes"))
        self.profile["personalDataPolicy"] = self._merge_profile_list(default_profile["personalDataPolicy"], self.profile.get("personalDataPolicy"))

    def work_lifecycle(self, limit: int = 40, *, actor: str = "") -> list[dict[str, Any]]:
        actor_key = actor.strip().lower()
        records = self.store.work_lifecycle()
        if actor_key:
            records = [item for item in records if not str(item.get("actor", "")).strip() or str(item.get("actor", "")).strip().lower() == actor_key]
        records.sort(key=lambda item: str(item.get("updated_at", "")).strip(), reverse=True)
        return records[:limit]

    def transition_work_item(
        self,
        *,
        actor: str,
        title: str,
        domain: str,
        lane: str,
        owner_agent: str,
        stage: WorkLifecycleStage | str,
        status: str,
        artifact_type: str,
        source: str,
        review_level: str,
        rationale: str,
        work_id: str = "",
        parent_work_id: str = "",
        record_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now_iso()
        normalized_stage = str(stage.value if isinstance(stage, WorkLifecycleStage) else stage).strip() or WorkLifecycleStage.SIGNAL.value
        resolved_work_id = work_id.strip() or parent_work_id.strip() or str(uuid.uuid4())
        existing = self.store.get_work_item(resolved_work_id) or {}
        transitions = [dict(item) for item in list(existing.get("transitions", [])) if isinstance(item, dict)]
        transition = {
            "transition_id": str(uuid.uuid4()),
            "stage": normalized_stage,
            "status": str(status).strip() or "open",
            "artifact_type": str(artifact_type).strip() or "artifact",
            "source": str(source).strip() or "manual",
            "owner_agent": str(owner_agent).strip() or "JARVIS",
            "lane": str(lane).strip() or "general-operations",
            "review_level": str(review_level).strip() or "review-as-needed",
            "rationale": str(rationale).strip(),
            "timestamp": now,
            "record_id": str(record_id).strip(),
            "metadata": dict(metadata or {}),
        }
        transitions.append(transition)
        artifact_refs = [dict(item) for item in list(existing.get("artifact_refs", [])) if isinstance(item, dict)]
        if transition["record_id"]:
            ref = {
                "record_id": transition["record_id"],
                "artifact_type": transition["artifact_type"],
                "stage": transition["stage"],
                "source": transition["source"],
                "timestamp": transition["timestamp"],
            }
            if ref not in artifact_refs:
                artifact_refs.append(ref)
        current = {
            "work_id": resolved_work_id,
            "actor": actor,
            "title": str(title).strip() or str(existing.get("title", "")).strip() or "Untitled work item",
            "domain": str(domain).strip() or str(existing.get("domain", "")).strip() or "general",
            "lane": str(lane).strip() or str(existing.get("lane", "")).strip() or "general-operations",
            "owner_agent": str(owner_agent).strip() or str(existing.get("owner_agent", "")).strip() or "JARVIS",
            "current_stage": normalized_stage,
            "status": transition["status"],
            "artifact_type": transition["artifact_type"],
            "source": transition["source"],
            "review_level": transition["review_level"],
            "rationale": transition["rationale"] or str(existing.get("rationale", "")).strip(),
            "created_at": str(existing.get("created_at", "")).strip() or now,
            "updated_at": now,
            "parent_work_id": str(existing.get("parent_work_id", "")).strip() or parent_work_id.strip(),
            "artifact_refs": artifact_refs,
            "transitions": transitions,
        }
        self.store.upsert_work_item(current)
        return current

    def connector_status(self) -> list[dict]:
        return list(self.profile.get("connectors", []))

    def default_pipeline_state(self) -> dict[str, Any]:
        return {
            "updated_at": _now_iso(),
            "portfolio": {
                "mission": "Coordinate family savings, revenue creation, stewardship, and compounding projects in one place.",
                "active_project_target": 6,
                "hypothesis_review_target": 5,
                "lanes": [dict(item) for item in self.profile.get("portfolioLanes", []) if isinstance(item, dict)],
            },
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
                "Catalyst portfolio state is currently inferred from signals, hypotheses, project briefs, and implementation plans until richer live connectors are wired.",
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
        work_id: str = "",
    ) -> dict:
        lane = self._infer_lane(f"{title}\n{content}", tags or [])
        record = {
            "signal_id": str(uuid.uuid4()),
            "actor": actor,
            "source": source,
            "title": title,
            "content": content,
            "sender": sender,
            "tags": tags or [],
            "lane": lane,
            "timestamp": _now_iso(),
        }
        self.store.add_signal(record)
        lifecycle = self.transition_work_item(
            actor=actor,
            title=title,
            domain="growth",
            lane=lane,
            owner_agent="Black Panther",
            stage=WorkLifecycleStage.SIGNAL,
            status="captured",
            artifact_type="signal",
            source=source,
            review_level="review-as-needed",
            rationale="A signal was captured and attached to the shared family portfolio lifecycle.",
            work_id=work_id,
            record_id=str(record.get("signal_id", "")).strip(),
            metadata={"tags": list(tags or []), "sender": sender},
        )
        record["work_id"] = lifecycle["work_id"]
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

    def project_brief(self, actor: str, project_name: str, problem: str, desired_outcome: str, constraints: str = "", *, work_id: str = "") -> dict:
        lane = self._infer_lane(f"{project_name}\n{problem}\n{desired_outcome}\n{constraints}")
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal project planning",
                "Create an A3-style project brief for a family-serving initiative inside Catalyst.",
                extra_guidance=(
                    "Return labeled sections exactly as: Lane:, Situation:, Problem:, Goal:, In Scope:, Out Of Scope:, "
                    "First Release:, Risks:, Recommendation:. Bias toward leverage, stewardship, and family usefulness."
                ),
            ),
            (
                f"Actor: {actor}\nProject: {project_name}\nProblem: {problem}\nDesired Outcome: {desired_outcome}\n"
                f"Constraints:\n{constraints}\nSuggested Lane: {lane}"
            ),
            max_output_tokens=950,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "project_name": project_name,
            "lane": self._extract_section(raw, "Lane") or lane,
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
        lifecycle = self.transition_work_item(
            actor=actor,
            title=project_name,
            domain="growth",
            lane=str(result.get("lane", lane)).strip() or lane,
            owner_agent="Black Panther",
            stage=WorkLifecycleStage.PROJECT_BRIEF,
            status="scoped",
            artifact_type="project-brief",
            source="catalyst-project-brief",
            review_level="review-before-commit",
            rationale="The work item was promoted from an idea into a scoped project brief.",
            work_id=work_id,
            record_id=str(result.get("run_id", "")).strip(),
            metadata={"problem": result.get("problem", ""), "goal": result.get("goal", "")},
        )
        result["work_id"] = lifecycle["work_id"]
        return result

    def implementation_plan(self, actor: str, project_name: str, brief: str, constraints: str = "", *, work_id: str = "") -> dict:
        lane = self._infer_lane(f"{project_name}\n{brief}\n{constraints}")
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst personal implementation planning",
                "Turn a project brief into a tactical implementation plan.",
                extra_guidance=(
                    "Return labeled sections exactly as: Lane:, Objective:, Workstreams:, Next Actions:, Dependencies:, Open Questions:."
                ),
            ),
            f"Actor: {actor}\nProject: {project_name}\nBrief:\n{brief}\n\nConstraints:\n{constraints}\nSuggested Lane: {lane}",
            max_output_tokens=900,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "project_name": project_name,
            "lane": self._extract_section(raw, "Lane") or lane,
            "objective": self._extract_section(raw, "Objective"),
            "workstreams": self._split_lines(self._extract_section(raw, "Workstreams")),
            "next_actions": self._split_lines(self._extract_section(raw, "Next Actions")),
            "dependencies": self._split_lines(self._extract_section(raw, "Dependencies")),
            "open_questions": self._split_lines(self._extract_section(raw, "Open Questions")),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.implementation_plans_path, result)
        lifecycle = self.transition_work_item(
            actor=actor,
            title=project_name,
            domain="growth",
            lane=str(result.get("lane", lane)).strip() or lane,
            owner_agent="Black Panther",
            stage=WorkLifecycleStage.IMPLEMENTATION_PLAN,
            status="ready",
            artifact_type="implementation-plan",
            source="catalyst-implementation-plan",
            review_level="review-before-commit",
            rationale="The work item now has explicit workstreams and next actions.",
            work_id=work_id,
            record_id=str(result.get("run_id", "")).strip(),
            metadata={"objective": result.get("objective", ""), "next_actions": list(result.get("next_actions", []))[:4]},
        )
        result["work_id"] = lifecycle["work_id"]
        return result

    def hypothesis_generation(
        self,
        actor: str,
        focus: str,
        context: str = "",
        lane: str = "",
        supporting_signals: list[str] | None = None,
        *,
        work_id: str = "",
        source_agent: str = "",
    ) -> dict:
        chosen_lane = lane.strip() or self._infer_lane(f"{focus}\n{context}\n{self._as_bullets(supporting_signals or [])}")
        supporting_signal_record = self.capture_signal(
            actor,
            "hypothesis",
            focus,
            context or focus,
            tags=["catalyst", "hypothesis", chosen_lane],
            work_id=work_id,
        )
        seeded_work_id = str(supporting_signal_record.get("work_id", "")).strip() or work_id
        raw = self.openai_client.prompt_text(
            build_specialist_prompt(
                "Catalyst family hypothesis generation",
                "Generate practical family-serving hypotheses that could create savings, revenue, leverage, or calmer operations.",
                extra_guidance=(
                    "Return labeled sections exactly as: Lane:, Opportunity:, Why Now:, Hypotheses:, First Bets:, Risks:, Support Needed:, Recommendation:. "
                    "Treat JARVIS agents as a team. Keep the ideas concrete, ethically sound, and reviewable."
                ),
            ),
            (
                f"Actor: {actor}\nFocus: {focus}\nLane: {chosen_lane}\nContext:\n{context}\n\n"
                f"Supporting Signals:\n{self._as_bullets(supporting_signals or [])}"
            ),
            max_output_tokens=820,
        )
        result = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "focus": focus,
            "lane": self._extract_section(raw, "Lane") or chosen_lane,
            "opportunity": self._extract_section(raw, "Opportunity"),
            "why_now": self._extract_section(raw, "Why Now"),
            "hypotheses": self._split_lines(self._extract_section(raw, "Hypotheses")),
            "first_bets": self._split_lines(self._extract_section(raw, "First Bets")),
            "risks": self._split_lines(self._extract_section(raw, "Risks")),
            "support_needed": self._split_lines(self._extract_section(raw, "Support Needed")),
            "recommendation": self._extract_section(raw, "Recommendation"),
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.hypotheses_path, result)
        lifecycle = self.transition_work_item(
            actor=actor,
            title=focus,
            domain="growth",
            lane=str(result.get("lane", chosen_lane)).strip() or chosen_lane,
            owner_agent=source_agent.strip() or "Black Panther",
            stage=WorkLifecycleStage.HYPOTHESIS,
            status="staged",
            artifact_type="hypothesis",
            source="catalyst-hypothesis",
            review_level="review-before-commit",
            rationale="A hypothesis was generated as a concrete, reviewable opportunity bet.",
            work_id=seeded_work_id,
            record_id=str(result.get("run_id", "")).strip(),
            metadata={"supporting_signals": list(supporting_signals or []), "source_agent": source_agent.strip()},
        )
        result["work_id"] = lifecycle["work_id"]
        return result

    def proactive_surfacing(self, actor: str, horizon: str = "today", context: str = "") -> dict:
        signals = self.store.list_signals(limit=10)
        recent_briefs = self.store.list_records(self.store.briefing_path, limit=3)
        recent_hypotheses = self.store.list_records(self.store.hypotheses_path, limit=4)
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
                f"Recent Brief Recommendations:\n{self._as_bullets([item.get('recommendation', '') for item in recent_briefs])}\n\n"
                f"Recent Hypotheses:\n{self._as_bullets([item.get('opportunity', '') or item.get('recommendation', '') for item in recent_hypotheses])}"
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
        latest_hypothesis = self.store.list_records(self.store.hypotheses_path, limit=1)
        return {
            "name": self.profile.get("name", "Catalyst Personal"),
            "mission": str(self.profile.get("mission", "")).strip(),
            "portfolio_lanes": list(self.profile.get("portfolioLanes", [])),
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
                "hypothesis": latest_hypothesis[0] if latest_hypothesis else {},
            },
            "counts": {
                "signals": len(self.store._load_records(self.store.signals_path)),
                "email_triage": len(self.store._load_records(self.store.email_triage_path)),
                "meeting_extractions": len(self.store._load_records(self.store.meeting_extract_path)),
                "briefings": len(self.store._load_records(self.store.briefing_path)),
                "drafts": len(self.store._load_records(self.store.drafts_path)),
                "project_briefs": len(self.store._load_records(self.store.project_briefs_path)),
                "implementation_plans": len(self.store._load_records(self.store.implementation_plans_path)),
                "hypotheses": len(self.store._load_records(self.store.hypotheses_path)),
            },
        }

    def _infer_lane(self, text: str, tags: list[str] | None = None) -> str:
        haystack = f"{text}\n{' '.join(tags or [])}".lower()
        rules = [
            ("family-savings", ("save", "savings", "cost", "bill", "expense", "subscription", "insurance", "utility")),
            ("revenue-growth", ("revenue", "income", "consulting", "client", "offer", "sales", "side hustle", "side-hustle")),
            ("money-management", ("budget", "cash flow", "cashflow", "debt", "invest", "stewardship", "finance", "money")),
            ("writing-and-ip", ("book", "write", "writing", "manuscript", "course", "framework", "intellectual property", "ip")),
            ("social-and-media", ("youtube", "social", "media", "content", "audience", "instagram", "linkedin", "podcast")),
            ("family-operations", ("family", "home", "household", "calendar", "routine", "operations", "friction", "peace")),
        ]
        for lane, needles in rules:
            if any(token in haystack for token in needles):
                return lane
        return "family-operations"

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
    def _merge_profile_list(defaults: list[str], configured: Any) -> list[str]:
        values = [str(item).strip() for item in (configured or []) if str(item).strip()]
        merged: list[str] = []
        for item in [*values, *defaults]:
            if item and item not in merged:
                merged.append(item)
        return merged

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
