from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .models import ArrivalEvent, SecurityIncident, UnlockAssessment, WeatherAdvisory
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SecurityStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.incidents_path = self.root / "security_incidents.json"
        self.weather_path = self.root / "weather_advisories.json"
        self.arrivals_path = self.root / "arrival_events.json"
        self.unlocks_path = self.root / "unlock_assessments.json"

    def _load_json(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, payload: list[dict]) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def add_incident(self, incident: SecurityIncident) -> None:
        records = self._load_json(self.incidents_path)
        records.append(asdict(incident))
        self._save_json(self.incidents_path, records)

    def list_incidents(self, limit: int = 20) -> list[dict]:
        records = self._load_json(self.incidents_path)
        return list(reversed(records[-limit:]))

    def add_weather(self, advisory: WeatherAdvisory) -> None:
        records = self._load_json(self.weather_path)
        records.append(asdict(advisory))
        self._save_json(self.weather_path, records)

    def list_weather(self, limit: int = 20) -> list[dict]:
        records = self._load_json(self.weather_path)
        return list(reversed(records[-limit:]))

    def add_arrival(self, event: ArrivalEvent) -> None:
        records = self._load_json(self.arrivals_path)
        records.append(asdict(event))
        self._save_json(self.arrivals_path, records)

    def list_arrivals(self, limit: int = 20) -> list[dict]:
        records = self._load_json(self.arrivals_path)
        return list(reversed(records[-limit:]))

    def add_unlock(self, assessment: UnlockAssessment) -> None:
        records = self._load_json(self.unlocks_path)
        records.append(asdict(assessment))
        self._save_json(self.unlocks_path, records)

    def list_unlocks(self, limit: int = 20) -> list[dict]:
        records = self._load_json(self.unlocks_path)
        return list(reversed(records[-limit:]))


class SecuritySupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: SecurityStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        self.profile = config.load_json_profile(
            config.security_profile_path,
            {
                "packageZones": [],
                "motionZones": [],
                "hazardContacts": [],
                "safeArrivalNotes": [],
                "weatherTimingNotes": [],
                "unlockPolicy": {
                    "voiceOnlyDenied": True,
                    "secondFactorOptions": [],
                    "highRiskTargets": [],
                },
                "overnightReviewNotes": [],
                "baselineIncidents": [],
            },
        )
        if not self.store.list_incidents(limit=1):
            for item in self.profile.get("baselineIncidents", []):
                self.store.add_incident(
                    SecurityIncident(
                        incident_id=str(uuid.uuid4()),
                        category=item["category"],
                        severity=item["severity"],
                        source=item["source"],
                        headline=item["headline"],
                        detail=item["detail"],
                        recommended_action=item["recommended_action"],
                        needs_ack=bool(item.get("needs_ack", False)),
                        timestamp=_now_iso(),
                    )
                )

    def package_or_motion_monitor(
        self,
        actor: str,
        category: str,
        location: str,
        detail: str,
        severity: str = "watch",
    ) -> dict:
        kind = category.strip().lower()
        if kind not in {"package", "motion"}:
            raise ValueError("category must be 'package' or 'motion'")
        headline = (
            f"Package activity noted at {location}"
            if kind == "package"
            else f"Unusual motion noted at {location}"
        )
        recommended_action = (
            "Check the delivery zone and confirm whether the drop location is acceptable."
            if kind == "package"
            else "Review the zone, timing, and whether this motion matches expected household activity."
        )
        incident = SecurityIncident(
            incident_id=str(uuid.uuid4()),
            category=kind,
            severity=severity,
            source=f"{location}-{kind}",
            headline=headline,
            detail=detail,
            recommended_action=recommended_action,
            needs_ack=severity in {"elevated", "critical"},
            timestamp=_now_iso(),
        )
        self.store.add_incident(incident)
        return asdict(incident)

    def safety_escalation(
        self,
        actor: str,
        hazard_type: str,
        source: str,
        detail: str,
        severity: str = "critical",
    ) -> dict:
        lowered = hazard_type.strip().lower()
        headline = f"{hazard_type.upper()} alert from {source}"
        recommended_action = {
            "smoke": "Confirm household safety, evacuate if needed, and verify the alarm source before re-entry.",
            "co": "Treat as immediate danger, move outside, and verify the detector source.",
            "leak": "Stop water flow if known and safe, then check damage risk and containment.",
        }.get(lowered, "Treat as a real alert until ruled out.")
        incident = SecurityIncident(
            incident_id=str(uuid.uuid4()),
            category=lowered or "hazard",
            severity=severity,
            source=source,
            headline=headline,
            detail=detail,
            recommended_action=recommended_action,
            needs_ack=True,
            timestamp=_now_iso(),
        )
        self.store.add_incident(incident)
        return asdict(incident)

    def weather_advisory(self, actor: str, context: str, current_weather: str) -> dict:
        notes = " ".join(self.profile.get("weatherTimingNotes", []))
        system = build_specialist_prompt(
            "weather timing",
            "Produce a concise operational advisory for departure timing, contingencies, and what can stay calm.",
            extra_guidance=(
                "Return four labeled lines exactly: Risk Level, Safe Timing, Recommendation, Follow Ups. "
                f"Notes: {notes}"
            ),
        )
        user = f"Actor: {actor}\nCurrent weather: {current_weather}\nContext: {context}"
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=220)
        parsed = {"risk level": "", "safe timing": "", "recommendation": "", "follow ups": ""}
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            lowered = key.strip().lower()
            if lowered in parsed:
                parsed[lowered] = value.strip()
        follow_ups = [item.strip() for item in parsed["follow ups"].split(";") if item.strip()]
        advisory = WeatherAdvisory(
            advisory_id=str(uuid.uuid4()),
            actor=actor,
            context=context,
            current_weather=current_weather,
            risk_level=parsed["risk level"] or "watch",
            safe_timing=parsed["safe timing"] or "Use the next calm window.",
            recommendation=parsed["recommendation"] or raw.strip(),
            follow_ups=follow_ups,
            timestamp=_now_iso(),
        )
        self.store.add_weather(advisory)
        return asdict(advisory)

    def child_arrival(self, actor: str, location: str, detail: str) -> dict:
        notes = " ".join(self.profile.get("safeArrivalNotes", []))
        next_steps = [
            "Confirm bag, shoes, and immediate needs.",
            "Keep the summary calm and factual for parents.",
        ]
        if "late" in detail.lower():
            next_steps.append("Check whether the delay was expected before escalating concern.")
        event = ArrivalEvent(
            event_id=str(uuid.uuid4()),
            actor=actor,
            location=location,
            status="home",
            detail=f"{detail} Notes: {notes}".strip(),
            next_steps=next_steps,
            timestamp=_now_iso(),
        )
        self.store.add_arrival(event)
        return asdict(event)

    def unlock_assessment(
        self,
        actor: str,
        target: str,
        requested_by_voice: bool,
        second_factor_present: bool,
    ) -> dict:
        policy = self.profile.get("unlockPolicy", {})
        voice_only_denied = bool(policy.get("voiceOnlyDenied", True))
        high_risk_targets = [item.lower() for item in policy.get("highRiskTargets", [])]
        sensitive_target = target.lower() in high_risk_targets or "door" in target.lower() or "garage" in target.lower()
        allowed = True
        rationale = "Unlock request is staged for review."
        next_step = "Manual approval required before any physical unlock."
        if requested_by_voice and sensitive_target and voice_only_denied and not second_factor_present:
            allowed = False
            rationale = "Voice-only unlock requests are denied until a second factor is confirmed."
            options = policy.get("secondFactorOptions", [])
            next_step = (
                f"Use one of the configured second factors: {', '.join(options)}."
                if options
                else "Use a trusted second factor before retrying."
            )
        elif requested_by_voice and sensitive_target and second_factor_present:
            rationale = "Voice request meets the second-factor gate, but still requires explicit approval."
            next_step = "Review the request in the dashboard approval queue before execution."
        assessment = UnlockAssessment(
            assessment_id=str(uuid.uuid4()),
            actor=actor,
            target=target,
            requested_by_voice=requested_by_voice,
            second_factor_present=second_factor_present,
            allowed=allowed,
            rationale=rationale,
            required_next_step=next_step,
            timestamp=_now_iso(),
        )
        self.store.add_unlock(assessment)
        return asdict(assessment)

    def overnight_review(self, watch_items: list[str]) -> dict:
        incidents = self.store.list_incidents(limit=20)
        notes = " ".join(self.profile.get("overnightReviewNotes", []))
        elevated = [item for item in incidents if item.get("severity") in {"elevated", "critical"}]
        packages = [item for item in incidents if item.get("category") == "package"]
        motion = [item for item in incidents if item.get("category") == "motion"]
        hazards = [item for item in incidents if item.get("category") in {"smoke", "co", "leak"}]
        summary_lines = [
            f"Open incidents: {len(incidents)}",
            f"Elevated incidents: {len(elevated)}",
            f"Package watch items: {len(packages)}",
            f"Motion watch items: {len(motion)}",
            f"Hazard alerts: {len(hazards)}",
        ]
        carry_forward = [item["headline"] for item in elevated[:5]]
        carry_forward.extend(watch_items[:5])
        return {
            "generated_at": _now_iso(),
            "summary": " | ".join(summary_lines),
            "carry_forward": carry_forward,
            "notes": notes,
            "incidents": incidents[:10],
        }

    def list_incidents(self, limit: int = 20) -> list[dict]:
        return self.store.list_incidents(limit=limit)

    def list_weather(self, limit: int = 20) -> list[dict]:
        return self.store.list_weather(limit=limit)

    def list_arrivals(self, limit: int = 20) -> list[dict]:
        return self.store.list_arrivals(limit=limit)

    def list_unlocks(self, limit: int = 20) -> list[dict]:
        return self.store.list_unlocks(limit=limit)
