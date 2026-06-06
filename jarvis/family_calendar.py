from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from .persistence import append_jsonl, atomic_write_json


FAMILY_CALENDAR_SETTINGS_PATH = Path.cwd() / "data" / "settings" / "family_calendar.json"
FAMILY_CALENDAR_SETTINGS_LOG_PATH = FAMILY_CALENDAR_SETTINGS_PATH.with_name("family_calendar_log.jsonl")
FAMILY_CALENDAR_SETTINGS_STATE_LOG_PATH = FAMILY_CALENDAR_SETTINGS_PATH.with_name("family_calendar_state_log.jsonl")


def _unfold_ics_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw.rstrip("\r"))
    return lines


def _parse_ics_datetime(raw: str, *, all_day: bool = False) -> str:
    value = raw.strip()
    if not value:
        return ""
    if all_day or len(value) == 8:
        try:
            return date.fromisoformat(f"{value[0:4]}-{value[4:6]}-{value[6:8]}").isoformat()
        except ValueError:
            return ""
    if value.endswith("Z"):
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return ""
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%S").isoformat()
    except ValueError:
        return ""


def _sort_key(value: str) -> tuple[int, str]:
    return (0, value or "")


@dataclass(slots=True)
class FamilyCalendarSupport:
    path: Path = FAMILY_CALENDAR_SETTINGS_PATH

    def _log_path(self) -> Path:
        if self.path == FAMILY_CALENDAR_SETTINGS_PATH:
            return FAMILY_CALENDAR_SETTINGS_LOG_PATH
        return self.path.with_name(f"{self.path.stem}_log.jsonl")

    def _state_log_path(self) -> Path:
        if self.path == FAMILY_CALENDAR_SETTINGS_PATH:
            return FAMILY_CALENDAR_SETTINGS_STATE_LOG_PATH
        return self.path.with_name(f"{self.path.stem}_state_log.jsonl")

    def load_settings(self) -> dict[str, Any]:
        default = {"label": "Family Shared Calendar", "source": "cozi", "ics_url": ""}
        if not self.path.exists():
            return self._load_from_state_log(default)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._load_from_state_log(default)
        if not isinstance(payload, dict) or not payload:
            return self._load_from_state_log(default)
        return {
            "label": str(payload.get("label", default["label"])).strip() or default["label"],
            "source": str(payload.get("source", default["source"])).strip() or default["source"],
            "ics_url": str(payload.get("ics_url", default["ics_url"])).strip(),
        }

    def _load_from_state_log(self, default: dict[str, Any]) -> dict[str, Any]:
        try:
            log_path = self._state_log_path()
            if not log_path.exists():
                return self._load_from_log(default)
            latest: dict[str, Any] | None = None
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                settings = payload.get("settings")
                if isinstance(settings, dict):
                    latest = dict(settings)
            if not latest:
                return self._load_from_log(default)
            return {
                "label": str(latest.get("label", default["label"])).strip() or default["label"],
                "source": str(latest.get("source", default["source"])).strip() or default["source"],
                "ics_url": str(latest.get("ics_url", default["ics_url"])).strip(),
            }
        except (OSError, json.JSONDecodeError):
            return self._load_from_log(default)

    def _load_from_log(self, default: dict[str, Any]) -> dict[str, Any]:
        try:
            log_path = self._log_path()
            if not log_path.exists():
                return default
            latest: dict[str, Any] | None = None
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                settings = payload.get("settings")
                if isinstance(settings, dict):
                    latest = dict(settings)
            if not latest:
                return default
            return {
                "label": str(latest.get("label", default["label"])).strip() or default["label"],
                "source": str(latest.get("source", default["source"])).strip() or default["source"],
                "ics_url": str(latest.get("ics_url", default["ics_url"])).strip(),
            }
        except (OSError, json.JSONDecodeError):
            return default

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_settings()
        current.update(
            {
                "label": str(payload.get("label", current["label"])).strip() or current["label"],
                "source": str(payload.get("source", current["source"])).strip() or current["source"],
                "ics_url": str(payload.get("ics_url", current["ics_url"])).strip(),
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        saved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_write_json(self.path, current)
        append_jsonl(
            self._log_path(),
            {
                "saved_at": saved_at,
                "settings": current,
            },
        )
        append_jsonl(
            self._state_log_path(),
            {
                "saved_at": saved_at,
                "settings": current,
            },
        )
        return current

    def summary(self, *, event_limit: int = 12, horizon_days: int = 30) -> dict[str, Any]:
        settings = self.load_settings()
        summary: dict[str, Any] = {
            "calendar": {
                "label": settings["label"],
                "source": settings["source"],
            },
            "configured": bool(settings["ics_url"]),
            "events": [],
            "counts": {"upcoming_events": 0},
        }
        if not settings["ics_url"]:
            summary["detail"] = "Family shared calendar feed is not configured yet."
            return summary
        try:
            response = requests.get(settings["ics_url"], timeout=20)
            response.raise_for_status()
            events = self._parse_ics_events(response.text, event_limit=event_limit, horizon_days=horizon_days)
            summary["events"] = events
            summary["counts"]["upcoming_events"] = len(events)
            summary["detail"] = "Family shared calendar is connected."
            return summary
        except Exception as exc:
            summary["detail"] = str(exc)
            summary["error"] = str(exc)
            return summary

    def _parse_ics_events(self, text: str, *, event_limit: int, horizon_days: int) -> list[dict[str, Any]]:
        lines = _unfold_ics_lines(text)
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=horizon_days)
        today = now.date()
        events: list[dict[str, Any]] = []
        current: dict[str, str] | None = None
        current_all_day = False

        for line in lines:
            if line == "BEGIN:VEVENT":
                current = {}
                current_all_day = False
                continue
            if line == "END:VEVENT":
                if current:
                    start = current.get("DTSTART", "")
                    end = current.get("DTEND", "")
                    summary = current.get("SUMMARY", "").strip() or "(Untitled event)"
                    start_iso = _parse_ics_datetime(start, all_day=current_all_day)
                    end_iso = _parse_ics_datetime(end, all_day=current_all_day)
                    if start_iso and self._event_in_horizon(start_iso, end_iso, today=today, now=now, horizon=horizon):
                        events.append(
                            {
                                "id": current.get("UID", ""),
                                "summary": summary,
                                "start": start_iso,
                                "end": end_iso,
                                "location": current.get("LOCATION", "").strip(),
                                "description": current.get("DESCRIPTION", "").strip(),
                                "all_day": current_all_day,
                            }
                        )
                current = None
                continue
            if current is None or ":" not in line:
                continue
            key_part, value = line.split(":", 1)
            key_bits = key_part.split(";")
            key = key_bits[0].upper()
            if key == "DTSTART" and any(bit.upper() == "VALUE=DATE" for bit in key_bits[1:]):
                current_all_day = True
            current[key] = value

        events.sort(key=lambda item: _sort_key(str(item.get("start", ""))))
        return events[:event_limit]

    @staticmethod
    def _event_in_horizon(start_iso: str, end_iso: str, *, today: date, now: datetime, horizon: datetime) -> bool:
        if "T" not in start_iso:
            try:
                start_date = date.fromisoformat(start_iso)
            except ValueError:
                return False
            if start_date < today:
                return False
            return start_date <= horizon.date()
        try:
            start_dt = datetime.fromisoformat(start_iso)
        except ValueError:
            return False
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if start_dt > horizon:
            return False
        if end_iso:
            try:
                end_dt = datetime.fromisoformat(end_iso) if "T" in end_iso else datetime.fromisoformat(end_iso + "T23:59:59+00:00")
            except ValueError:
                end_dt = start_dt
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            return end_dt >= now
        return start_dt >= now
