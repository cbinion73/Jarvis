from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .models import MessageDraft, ModeState, VoiceNoteTask
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt


def _parse_minutes(time_text: str) -> int:
    hours, minutes = time_text.split(":", 1)
    return int(hours) * 60 + int(minutes)


class FamilyStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.mode_state_path = self.root / "mode_state.json"
        self.mode_history_path = self.root / "mode_history.jsonl"
        self.message_drafts_path = self.root / "message_drafts.json"
        self.voice_notes_path = self.root / "voice_note_tasks.json"
        self.departure_runs_path = self.root / "departure_runs.json"
        self.meal_plans_path = self.root / "meal_plans.json"
        self.vehicle_plans_path = self.root / "vehicle_plans.json"
        self.weather_plans_path = self.root / "weather_plans.json"

    def load_mode_state(self) -> dict | None:
        if not self.mode_state_path.exists():
            return None
        return json.loads(self.mode_state_path.read_text(encoding="utf-8"))

    def save_mode_state(self, mode_state: ModeState) -> None:
        payload = asdict(mode_state)
        self.mode_state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        with self.mode_history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _load_drafts(self) -> list[dict]:
        if not self.message_drafts_path.exists():
            return []
        return json.loads(self.message_drafts_path.read_text(encoding="utf-8"))

    def _save_drafts(self, drafts: list[dict]) -> None:
        self.message_drafts_path.write_text(json.dumps(drafts, indent=2) + "\n", encoding="utf-8")

    def add_draft(self, draft: MessageDraft) -> None:
        drafts = self._load_drafts()
        drafts.append(asdict(draft))
        self._save_drafts(drafts)

    def list_drafts(self, limit: int = 20) -> list[dict]:
        drafts = self._load_drafts()
        return list(reversed(drafts[-limit:]))

    def update_draft_status(self, draft_id: str, status: str) -> dict | None:
        drafts = self._load_drafts()
        updated = None
        for draft in drafts:
            if draft["draft_id"] == draft_id:
                draft["status"] = status
                updated = draft
                break
        if updated:
            self._save_drafts(drafts)
        return updated

    def _load_voice_notes(self) -> list[dict]:
        if not self.voice_notes_path.exists():
            return []
        return json.loads(self.voice_notes_path.read_text(encoding="utf-8"))

    def _save_voice_notes(self, records: list[dict]) -> None:
        self.voice_notes_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def add_voice_note_task(self, task: VoiceNoteTask) -> None:
        records = self._load_voice_notes()
        records.append(asdict(task))
        self._save_voice_notes(records)

    def list_voice_note_tasks(self, limit: int = 20) -> list[dict]:
        records = self._load_voice_notes()
        return list(reversed(records[-limit:]))

    def update_voice_note_status(self, note_id: str, status: str) -> dict | None:
        records = self._load_voice_notes()
        updated = None
        for item in records:
            if item["note_id"] == note_id:
                item["status"] = status
                updated = item
                break
        if updated:
            self._save_voice_notes(records)
        return updated

    def _load_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_records(self, path: Path, records: list[dict]) -> None:
        path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def add_departure_run(self, record: dict) -> None:
        records = self._load_records(self.departure_runs_path)
        records.append(record)
        self._save_records(self.departure_runs_path, records)

    def list_departure_runs(self, limit: int = 10) -> list[dict]:
        records = self._load_records(self.departure_runs_path)
        return list(reversed(records[-limit:]))

    def add_meal_plan(self, record: dict) -> None:
        records = self._load_records(self.meal_plans_path)
        records.append(record)
        self._save_records(self.meal_plans_path, records)

    def list_meal_plans(self, limit: int = 10) -> list[dict]:
        records = self._load_records(self.meal_plans_path)
        return list(reversed(records[-limit:]))

    def add_vehicle_plan(self, record: dict) -> None:
        records = self._load_records(self.vehicle_plans_path)
        records.append(record)
        self._save_records(self.vehicle_plans_path, records)

    def list_vehicle_plans(self, limit: int = 10) -> list[dict]:
        records = self._load_records(self.vehicle_plans_path)
        return list(reversed(records[-limit:]))

    def add_weather_plan(self, record: dict) -> None:
        records = self._load_records(self.weather_plans_path)
        records.append(record)
        self._save_records(self.weather_plans_path, records)

    def list_weather_plans(self, limit: int = 10) -> list[dict]:
        records = self._load_records(self.weather_plans_path)
        return list(reversed(records[-limit:]))


class FamilySupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: FamilyStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        self.profile = config.load_json_profile(
            config.family_profile_path,
            {
                "modeSchedule": [],
                "departureChecklist": [],
                "messageStyleNotes": {},
                "familyPlanningNotes": [],
                "troopPlanningNotes": [],
                "groceryZones": {},
                "mealTemplates": [],
                "voiceNoteNotes": [],
                "modeDetails": {},
                "vehicleDefaults": {},
                "weatherPlanningNotes": [],
                "departureNotes": [],
            },
        )

    def infer_mode(self, at_time: datetime | None = None) -> ModeState:
        now = at_time or datetime.now()
        minutes = now.hour * 60 + now.minute
        for item in self.profile.get("modeSchedule", []):
            start = _parse_minutes(item["start"])
            end = _parse_minutes(item["end"])
            if start <= minutes <= end:
                return ModeState(
                    mode=item["mode"],
                    status="scheduled",
                    reason="Time-based household rhythm",
                    actor="system",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
        return ModeState(
            mode="ambient-associate",
            status="fallback",
            reason="No explicit scheduled mode matched",
            actor="system",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def active_mode(self) -> ModeState:
        stored = self.store.load_mode_state()
        if stored:
            return ModeState(**stored)
        inferred = self.infer_mode()
        self.store.save_mode_state(inferred)
        return inferred

    def transition_mode(self, actor: str, mode: str, reason: str) -> ModeState:
        mode_state = ModeState(
            mode=mode,
            status="manual",
            reason=reason,
            actor=actor,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save_mode_state(mode_state)
        return mode_state

    def _mode_config(self, mode: str) -> dict:
        return self.profile.get("modeDetails", {}).get(mode, {})

    def mode_brief(
        self,
        mode: str,
        weather: str = "",
        home_details: list[str] | None = None,
        watch_items: list[str] | None = None,
        event_titles: list[str] | None = None,
    ) -> dict:
        details = self._mode_config(mode)
        home_details = home_details or []
        watch_items = watch_items or []
        event_titles = event_titles or []
        title = details.get("title", mode.replace("-", " ").title())
        purpose = details.get("purpose", "Keep the household calm, prepared, and well-sequenced.")
        summary_parts = [purpose]
        if weather:
            summary_parts.append(f"Weather context: {weather}")
        if event_titles:
            summary_parts.append(f"Key events: {', '.join(event_titles[:3])}")
        if home_details:
            summary_parts.append(f"Home watch: {home_details[0]}")
        return {
            "mode": mode,
            "title": title,
            "purpose": purpose,
            "summary": " ".join(summary_parts),
            "actions": details.get("actions", []),
            "guardrails": details.get("guardrails", []),
            "signals": details.get("signals", []),
            "automation_targets": details.get("automationTargets", []),
            "watch_items": list(watch_items[:3]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def family_plan(self, actor: str, request: str, active_mode: str) -> str:
        notes = " ".join(self.profile.get("familyPlanningNotes", []))
        checklist = ", ".join(self.profile.get("departureChecklist", []))
        system = build_specialist_prompt(
            "family logistics",
            "Build a calm, low-friction household plan.",
            extra_guidance=(
                "Surface conflicts, ordering, reminders, and contingency notes. "
                f"Planning notes: {notes}. Departure checklist: {checklist}. "
                f"Current household mode: {active_mode}."
            ),
        )
        user = f"Actor: {actor}\nRequest: {request}"
        return self.openai_client.prompt_text(system, user, max_output_tokens=450)

    def rebekah_command_center(self, request: str, active_mode: str) -> str:
        planning_notes = " ".join(self.profile.get("familyPlanningNotes", []))
        troop_notes = " ".join(self.profile.get("troopPlanningNotes", []))
        meals = ", ".join(self.profile.get("mealTemplates", []))
        system = build_specialist_prompt(
            "Rebekah command center",
            "Build a practical household coordination brief with today's tensions, what can wait, and the next three useful moves.",
            extra_guidance=(
                "Be calm, low-fuss, and immediately useful. "
                f"Current household mode: {active_mode}. "
                f"Planning notes: {planning_notes}. "
                f"Troop notes: {troop_notes}. "
                f"Meal templates: {meals}."
            ),
        )
        user = f"Actor: Rebekah\nRequest: {request}"
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def troop_plan(self, actor: str, request: str) -> str:
        troop_notes = " ".join(self.profile.get("troopPlanningNotes", []))
        system = build_specialist_prompt(
            "troop meeting planning",
            "Prepare a practical troop plan with weather contingency, roster readiness, supplies, parent communication, and arrival timing.",
            extra_guidance=(
                "Return labeled sections: Weather, Backup Plan, Supplies, Parent Message, Follow Ups. "
                f"Troop planning notes: {troop_notes}."
            ),
        )
        user = f"Actor: {actor}\nRequest: {request}"
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def grocery_support(self, actor: str, request: str) -> str:
        zones = self.profile.get("groceryZones", {})
        templates = ", ".join(self.profile.get("mealTemplates", []))
        system = build_specialist_prompt(
            "grocery and meal support",
            "Group groceries by store zone or aisle when possible, recommend one low-complexity meal, and keep the plan quiet and practical.",
            extra_guidance=(
                "Return labeled sections: Grocery Groups, Meal Suggestion, Timing, Gaps. "
                f"Grocery zones: {json.dumps(zones)}. Meal templates: {templates}."
            ),
        )
        user = f"Actor: {actor}\nRequest: {request}"
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def draft_message(
        self,
        actor: str,
        audience: str,
        purpose: str,
        context: str,
        tone: str = "warm",
    ) -> dict:
        tone_note = self.profile.get("messageStyleNotes", {}).get(tone, "")
        system = build_specialist_prompt(
            "outbound message draft",
            "Write a message draft only.",
            extra_guidance=f"Do not imply it was sent. Tone guidance: {tone_note}",
        )
        user = (
            f"Actor: {actor}\nAudience: {audience}\nPurpose: {purpose}\n"
            f"Context:\n{context}\n\nWrite one polished draft."
        )
        body = self.openai_client.prompt_text(system, user, max_output_tokens=260)
        draft = MessageDraft(
            draft_id=str(uuid.uuid4()),
            actor=actor,
            audience=audience,
            purpose=purpose,
            tone=tone,
            context=context,
            body=body,
            status="staged",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_draft(draft)
        return asdict(draft)

    def stage_parent_message(
        self,
        actor: str,
        audience: str,
        purpose: str,
        context: str,
        tone: str = "warm",
    ) -> dict:
        draft = self.draft_message(actor, audience, purpose, context, tone)
        draft["status"] = "pending-approval"
        updated = self.store.update_draft_status(draft["draft_id"], "pending-approval")
        return updated or draft

    def list_drafts(self, limit: int = 20) -> list[dict]:
        return self.store.list_drafts(limit=limit)

    def update_draft_status(self, draft_id: str, status: str) -> dict | None:
        return self.store.update_draft_status(draft_id, status)

    def capture_voice_note(self, actor: str, source: str, note: str) -> dict:
        system = build_specialist_prompt(
            "voice-note follow-up capture",
            "Convert a quick voice note into concrete follow-up tasks only.",
            extra_guidance="Return 2 to 5 short lines, one task per line.",
        )
        user = (
            f"Actor: {actor}\n"
            f"Source: {source}\n"
            f"Voice note:\n{note}\n\n"
            f"Notes: {' '.join(self.profile.get('voiceNoteNotes', []))}"
        )
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=180)
        tasks = []
        for line in raw.splitlines():
            cleaned = line.strip().lstrip("-").strip()
            if cleaned:
                tasks.append(cleaned)
        task = VoiceNoteTask(
            note_id=str(uuid.uuid4()),
            actor=actor,
            source=source,
            note=note,
            tasks=tasks[:5],
            status="open",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_voice_note_task(task)
        return asdict(task)

    def list_voice_note_tasks(self, limit: int = 20) -> list[dict]:
        return self.store.list_voice_note_tasks(limit=limit)

    def update_voice_note_status(self, note_id: str, status: str) -> dict | None:
        return self.store.update_voice_note_status(note_id, status)

    def departure_checklist(self) -> list[str]:
        return self.profile.get("departureChecklist", [])

    def departure_orchestration(
        self,
        actor: str,
        context: str,
        weather: str,
        garage_state: str = "",
        family_focus: dict[str, list[str]] | None = None,
        persist: bool = True,
    ) -> dict:
        focus = family_focus or {}
        checklist = self.departure_checklist()
        notes = list(self.profile.get("departureNotes", []))
        focus_items = []
        for name, items in focus.items():
            if items:
                focus_items.append(f"{name}: {items[0]}")
        weather_hold = "Watch for rain timing before loading the car." if "rain" in weather.lower() else "No weather hold needed."
        garage_note = garage_state or "Confirm garage path is clear before departure."
        record = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "context": context,
            "headline": "Departure plan staged.",
            "weather_hold": weather_hold,
            "garage_note": garage_note,
            "focus_calls": focus_items[:4],
            "checklist": checklist,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if persist:
            self.store.add_departure_run(record)
        return record

    def meal_plan(self, actor: str, request: str, persist: bool = True) -> dict:
        lowered = request.lower()
        zones = self.profile.get("groceryZones", {})
        chosen_template = next(
            (template for template in self.profile.get("mealTemplates", []) if template.lower() in lowered),
            "",
        ) or (self.profile.get("mealTemplates", ["tacos"])[0])
        grocery_groups: dict[str, list[str]] = {}
        for zone, items in zones.items():
            matched = [item for item in items if item.lower() in lowered]
            if matched:
                grocery_groups[zone] = matched
        if not grocery_groups:
            grocery_groups = dict(list(zones.items())[:3])
        record = {
            "plan_id": str(uuid.uuid4()),
            "actor": actor,
            "request": request,
            "meal_suggestion": chosen_template,
            "grocery_groups": grocery_groups,
            "timing": [
                "Batch the pickup into one stop if possible.",
                "Stage ingredients before the after-school rush.",
                "Keep dinner to a low-complexity lane tonight.",
            ],
            "gaps": ["Confirm whether any missing produce or protein items need adding."],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if persist:
            self.store.add_meal_plan(record)
        return record

    def vehicle_assignment(self, actor: str, request: str, weather: str, persist: bool = True) -> dict:
        defaults = self.profile.get("vehicleDefaults", {})
        lowered = request.lower()
        if "troop" in lowered or "grocery" in lowered or "kids" in lowered:
            vehicle = defaults.get("familyLogisticsVehicle", "van")
        else:
            vehicle = defaults.get("defaultVehicle", "car")
        route_notes = [
            defaults.get("routePriority", "Favor fewer turns and lower-friction stops."),
        ]
        if "rain" in weather.lower():
            route_notes.append("Pad departure slightly to account for wet-weather loading.")
        record = {
            "plan_id": str(uuid.uuid4()),
            "actor": actor,
            "request": request,
            "vehicle": vehicle,
            "driver": actor,
            "route_notes": route_notes,
            "loadout": defaults.get("defaultLoadout", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if persist:
            self.store.add_vehicle_plan(record)
        return record

    def weather_contingency(
        self,
        actor: str,
        request: str,
        weather: str,
        active_mode: str,
        persist: bool = True,
    ) -> dict:
        notes = self.profile.get("weatherPlanningNotes", [])
        lowered = weather.lower()
        risk = "low"
        if "rain" in lowered:
            risk = "moderate"
        if "storm" in lowered or "severe" in lowered:
            risk = "high"
        record = {
            "plan_id": str(uuid.uuid4()),
            "actor": actor,
            "request": request,
            "active_mode": active_mode,
            "weather": weather,
            "risk_level": risk,
            "actions": [
                "Pull forward anything that needs a dry loading window.",
                "Keep one indoor fallback ready instead of rewriting the whole evening.",
                "Send only the parent update that changes the decision.",
            ],
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if persist:
            self.store.add_weather_plan(record)
        return record

    def list_departure_runs(self, limit: int = 10) -> list[dict]:
        return self.store.list_departure_runs(limit=limit)

    def list_meal_plans(self, limit: int = 10) -> list[dict]:
        return self.store.list_meal_plans(limit=limit)

    def list_vehicle_plans(self, limit: int = 10) -> list[dict]:
        return self.store.list_vehicle_plans(limit=limit)

    def list_weather_plans(self, limit: int = 10) -> list[dict]:
        return self.store.list_weather_plans(limit=limit)

    def anomaly_watch(self, home_details: list[str], watch_items: list[str]) -> list[dict]:
        results: list[dict] = []
        for detail in home_details:
            severity = "watch"
            lowered = detail.lower()
            if "warmer" in lowered or "intervention" in lowered:
                severity = "elevated"
            if "before" in lowered:
                severity = "timed"
            results.append({"source": "snapshot-home", "severity": severity, "detail": detail})
        for item in watch_items:
            results.append({"source": "watch-list", "severity": "watch", "detail": item})
        return results
