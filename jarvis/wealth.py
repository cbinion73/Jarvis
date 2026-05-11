from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .openai_tasks import JarvisOpenAIClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe(values: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = str(value).strip(" -\n\t")
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
        if len(cleaned) >= limit:
            break
    return cleaned


def _extract_section_lines(text: str, headings: tuple[str, ...]) -> list[str]:
    lines = [line.strip() for line in str(text).splitlines()]
    active = False
    captured: list[str] = []
    for line in lines:
        normalized = line.strip().lstrip("-* ").lstrip("#").strip().lower().rstrip(":")
        if any(normalized == heading.lower().rstrip(":") for heading in headings):
            active = True
            continue
        if active and line.startswith("#"):
            break
        if active and line.lstrip("#").strip().endswith(":") and not line.startswith(("-", "*")):
            break
        if active and line:
            captured.append(line.lstrip("-* ").strip())
    return captured


def _extract_inline_sentence(text: str, anchor: str) -> str:
    pattern = re.compile(rf"{re.escape(anchor)}\s*[:\-]\s*(.+?)(?:\n|$)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(str(text))
    if not match:
        return ""
    return match.group(1).strip(" -*\n\t")


@dataclass(slots=True)
class WealthLeverageStore:
    root: Path
    path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "wealth_outcomes.json"

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def save(self, records: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        records = self.load()
        records.append(record)
        self.save(records)
        return record

    def recent(self, limit: int = 12) -> list[dict[str, Any]]:
        records = self.load()
        return list(reversed(records[-limit:]))


class WealthLeverageSupport:
    def __init__(self, store: WealthLeverageStore, openai_client: JarvisOpenAIClient) -> None:
        self.store = store
        self.openai_client = openai_client

    def record_workflow(self, workflow_result: dict[str, Any]) -> dict[str, Any]:
        structured = self._structure_outcome(workflow_result)
        record = {
            "entry_id": str(uuid.uuid4()),
            "timestamp": _now_iso(),
            "request": workflow_result.get("request", ""),
            "workflow": workflow_result.get("workflow", "wealth-and-leverage"),
            "agents": workflow_result.get("agents", []),
            "focus_areas": workflow_result.get("focus_areas", []),
            "opportunity_theses": structured.get("opportunity_theses", []),
            "experiments_in_flight": structured.get("experiments_in_flight", []),
            "rejected_ideas": structured.get("rejected_ideas", []),
            "roi_lessons": structured.get("roi_lessons", []),
            "synthesis": workflow_result.get("synthesis", ""),
            "participants": workflow_result.get("participants", []),
        }
        self.store.append(record)
        return record

    def summary(self, limit: int = 10) -> dict[str, Any]:
        records = self.store.recent(limit=limit)
        theses: list[str] = []
        experiments: list[str] = []
        rejected: list[str] = []
        roi_lessons: list[str] = []
        for item in records:
            theses.extend(item.get("opportunity_theses", []))
            experiments.extend(item.get("experiments_in_flight", []))
            rejected.extend(item.get("rejected_ideas", []))
            roi_lessons.extend(item.get("roi_lessons", []))
        return {
            "recent_runs": records,
            "opportunity_theses": theses[:12],
            "experiments_in_flight": experiments[:12],
            "rejected_ideas": rejected[:12],
            "roi_lessons": roi_lessons[:12],
        }

    def _structure_outcome(self, workflow_result: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "You are structuring a wealth-and-leverage planning outcome for durable memory. "
            "Return strict JSON with four keys: opportunity_theses, experiments_in_flight, rejected_ideas, roi_lessons. "
            "Each value must be an array of short strings. "
            "Use rejected_ideas only for ideas that should be avoided, deferred, or explicitly not pursued."
        )
        payload = json.dumps(
            {
                "request": workflow_result.get("request", ""),
                "synthesis": workflow_result.get("synthesis", ""),
                "participants": workflow_result.get("participants", []),
            },
            indent=2,
        )
        raw = self.openai_client.prompt_text(prompt, payload, max_output_tokens=260)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        structured = {
            "opportunity_theses": _dedupe(data.get("opportunity_theses", [])),
            "experiments_in_flight": _dedupe(data.get("experiments_in_flight", [])),
            "rejected_ideas": _dedupe(data.get("rejected_ideas", [])),
            "roi_lessons": _dedupe(data.get("roi_lessons", [])),
        }

        request = str(workflow_result.get("request", "")).strip()
        only_request_placeholder = (
            structured["opportunity_theses"] == [request]
            and not structured["experiments_in_flight"]
            and not structured["rejected_ideas"]
            and not structured["roi_lessons"]
        )

        if all(not values for values in structured.values()) or only_request_placeholder:
            synthesis = str(workflow_result.get("synthesis", "")).strip()
            recommendation_lines = _extract_section_lines(synthesis, ("Recommendation",))
            best_bets_lines = _extract_section_lines(synthesis, ("Best Bets",))
            risk_lines = _extract_section_lines(synthesis, ("Risks",))
            next_experiment_lines = _extract_section_lines(synthesis, ("Next Experiment",))

            structured["opportunity_theses"] = _dedupe(
                recommendation_lines + best_bets_lines + ([request] if request else []),
                limit=6,
            )
            structured["experiments_in_flight"] = _dedupe(next_experiment_lines, limit=4)
            structured["rejected_ideas"] = _dedupe(
                [
                    line
                    for line in risk_lines
                    if any(token in line.lower() for token in ("avoid", "defer", "not", "don't", "do not", "too much"))
                ],
                limit=4,
            )
            structured["roi_lessons"] = _dedupe(
                best_bets_lines[:2] + risk_lines[:2],
                limit=4,
            )

        if not structured["opportunity_theses"] and workflow_result.get("request"):
            structured["opportunity_theses"] = [str(workflow_result["request"]).strip()]

        participant_responses = [
            str(item.get("response", "")).strip()
            for item in workflow_result.get("participants", [])
            if str(item.get("response", "")).strip()
        ]
        if participant_responses:
            if not structured["experiments_in_flight"]:
                experiment_lines: list[str] = []
                for response in participant_responses:
                    experiment_lines.extend(_extract_section_lines(response, ("Next experiment", "Next experiment worth running")))
                    inline = _extract_inline_sentence(response, "next experiment")
                    if inline:
                        experiment_lines.append(inline)
                structured["experiments_in_flight"] = _dedupe(experiment_lines, limit=4)
            if not structured["roi_lessons"]:
                roi_lines: list[str] = []
                for response in participant_responses:
                    roi_lines.extend(_extract_section_lines(response, ("Best opportunity", "Best opportunity recommendation", "Main tradeoff/risk")))
                structured["roi_lessons"] = _dedupe(roi_lines, limit=4)

        return structured
