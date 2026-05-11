from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AppConfig
from .openai_tasks import JarvisOpenAIClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ContentOpsStore:
    root: Path
    idea_runs_path: Path = field(init=False)
    queue_path: Path = field(init=False)
    exports_root: Path = field(init=False)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.idea_runs_path = self.root / "veronica_idea_runs.json"
        self.queue_path = self.root / "veronica_queue.json"
        self.exports_root = self.root / "exports"
        self.exports_root.mkdir(parents=True, exist_ok=True)

    def _load(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _save(self, path: Path, records: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def add_record(self, path: Path, record: dict[str, Any]) -> dict[str, Any]:
        records = self._load(path)
        records.append(record)
        self._save(path, records)
        return record

    def list_records(self, path: Path, limit: int = 10) -> list[dict[str, Any]]:
        records = self._load(path)
        return list(reversed(records[-limit:]))

    def update_queue_item(self, queue_id: str, **updates: Any) -> dict[str, Any] | None:
        records = self._load(self.queue_path)
        for item in records:
            if str(item.get("queue_id", "")) == queue_id:
                item.update(updates)
                self._save(self.queue_path, records)
                return item
        return None


class ContentOpsSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: ContentOpsStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store

    def snapshot(self) -> dict[str, Any]:
        idea_runs = self.store.list_records(self.store.idea_runs_path, limit=6)
        queue = self.store.list_records(self.store.queue_path, limit=12)
        live_count = sum(1 for item in queue if str(item.get("status", "")).lower() == "live")
        return {
            "idea_runs": idea_runs,
            "queue": queue,
            "stats": {
                "idea_runs": len(self.store._load(self.store.idea_runs_path)),
                "queued": sum(1 for item in queue if str(item.get("status", "")).lower() == "queued"),
                "scripted": sum(1 for item in queue if str(item.get("status", "")).lower() == "scripted"),
                "live": live_count,
            },
        }

    def generate_options(self, actor: str, topic: str, channel: str = "YouTube", context: str = "") -> dict[str, Any]:
        prompt = (
            "You are Veronica, content head inside JARVIS. Generate exactly 4 sharply different short-form content options. "
            "Return strict JSON with key 'options', an array of objects with keys: title, hook, angle, notes. "
            "Make them publishable, specific, and high-signal."
        )
        payload = json.dumps(
            {
                "actor": actor,
                "topic": topic,
                "channel": channel,
                "context": context,
            },
            indent=2,
        )
        raw = self.openai_client.prompt_text(prompt, payload, max_output_tokens=700)
        options = self._parse_options(raw, topic, channel)
        run = {
            "run_id": str(uuid.uuid4()),
            "actor": actor,
            "topic": topic,
            "channel": channel,
            "context": context,
            "options": options,
            "raw_output": raw,
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.idea_runs_path, run)
        return run

    def approve_option(self, actor: str, option_id: str) -> dict[str, Any]:
        option = self._find_option(option_id)
        if not option:
            raise ValueError("Selected content option was not found.")
        prompt = (
            "You are Veronica, content head inside JARVIS. Turn the approved option into a short YouTube-ready script package. "
            "Return strict JSON with keys: title, cold_open, script, visual_notes, publish_notes."
        )
        payload = json.dumps({"actor": actor, "option": option}, indent=2)
        raw = self.openai_client.prompt_text(prompt, payload, max_output_tokens=1000)
        package = self._parse_script(raw, option)
        record = {
            "queue_id": str(uuid.uuid4()),
            "actor": actor,
            "source_option_id": option_id,
            "channel": option.get("channel", "YouTube"),
            "topic": option.get("topic", ""),
            "title": package["title"],
            "hook": package["cold_open"],
            "script": package["script"],
            "visual_notes": package["visual_notes"],
            "publish_notes": package["publish_notes"],
            "status": "queued",
            "timestamp": _now_iso(),
        }
        self.store.add_record(self.store.queue_path, record)
        return record

    def push_live(self, queue_id: str) -> dict[str, Any] | None:
        return self.store.update_queue_item(queue_id, status="live", published_at=_now_iso())

    def export_queue_item(self, queue_id: str) -> dict[str, Any]:
        record = self._find_queue_item(queue_id)
        if not record:
            raise ValueError("Queue item was not found.")
        export_root = self.store.exports_root / queue_id
        export_root.mkdir(parents=True, exist_ok=True)
        metadata_path = export_root / "metadata.json"
        package_path = export_root / "youtube_package.md"
        script_path = export_root / "script.txt"
        visuals_path = export_root / "visual_notes.txt"
        publish_path = export_root / "publish_notes.txt"

        metadata = {
            "queue_id": queue_id,
            "title": record.get("title", ""),
            "topic": record.get("topic", ""),
            "channel": record.get("channel", "YouTube"),
            "status": record.get("status", "queued"),
            "exported_at": _now_iso(),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        script_path.write_text(str(record.get("script", "")).strip() + "\n", encoding="utf-8")
        visuals_path.write_text(str(record.get("visual_notes", "")).strip() + "\n", encoding="utf-8")
        publish_path.write_text(str(record.get("publish_notes", "")).strip() + "\n", encoding="utf-8")
        package_path.write_text(
            (
                f"# {record.get('title', 'Untitled')}\n\n"
                f"## Hook\n{record.get('hook', '')}\n\n"
                f"## Script\n{record.get('script', '')}\n\n"
                f"## Visual Notes\n{record.get('visual_notes', '')}\n\n"
                f"## Publish Notes\n{record.get('publish_notes', '')}\n"
            ),
            encoding="utf-8",
        )
        updated = self.store.update_queue_item(
            queue_id,
            status="exported" if str(record.get("status", "")).lower() != "live" else str(record.get("status", "live")).lower(),
            exported_at=_now_iso(),
            export_manifest={
                "root": str(export_root),
                "files": [
                    {"label": "Metadata", "name": metadata_path.name},
                    {"label": "YouTube Package", "name": package_path.name},
                    {"label": "Script", "name": script_path.name},
                    {"label": "Visual Notes", "name": visuals_path.name},
                    {"label": "Publish Notes", "name": publish_path.name},
                ],
            },
        )
        return updated or record

    def _find_queue_item(self, queue_id: str) -> dict[str, Any] | None:
        for item in self.store.list_records(self.store.queue_path, limit=50):
            if str(item.get("queue_id", "")) == queue_id:
                return item
        return None

    def _find_option(self, option_id: str) -> dict[str, Any] | None:
        for run in self.store.list_records(self.store.idea_runs_path, limit=25):
            for option in run.get("options", []):
                if str(option.get("option_id", "")) == option_id:
                    return option
        return None

    def _parse_options(self, raw: str, topic: str, channel: str) -> list[dict[str, Any]]:
        try:
            payload = json.loads(raw)
            options = payload.get("options", [])
        except json.JSONDecodeError:
            options = []
        parsed: list[dict[str, Any]] = []
        for index, item in enumerate(options[:4], start=1):
            parsed.append(
                {
                    "option_id": str(uuid.uuid4()),
                    "topic": topic,
                    "channel": channel,
                    "title": str(item.get("title", "")).strip(),
                    "hook": str(item.get("hook", "")).strip(),
                    "angle": str(item.get("angle", "")).strip(),
                    "notes": str(item.get("notes", "")).strip(),
                }
            )
        if parsed:
            return parsed
        seeds = [
            ("Tight insight", f"Why {topic} matters more than most people think right now."),
            ("Sharp contrarian", f"The lazy consensus on {topic} is probably wrong."),
            ("Actionable breakdown", f"Three things to watch inside {topic} this week."),
            ("Signal over noise", f"What actually matters inside {topic}, without the fluff."),
        ]
        return [
            {
                "option_id": str(uuid.uuid4()),
                "topic": topic,
                "channel": channel,
                "title": title,
                "hook": hook,
                "angle": "Fallback structured option generated locally.",
                "notes": "Validate this with a stronger channel-specific prompt later.",
            }
            for title, hook in seeds
        ]

    def _parse_script(self, raw: str, option: dict[str, Any]) -> dict[str, str]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        return {
            "title": str(payload.get("title", option.get("title", "Approved draft"))).strip(),
            "cold_open": str(payload.get("cold_open", option.get("hook", ""))).strip(),
            "script": str(payload.get("script", option.get("angle", ""))).strip() or option.get("angle", ""),
            "visual_notes": str(payload.get("visual_notes", option.get("notes", ""))).strip(),
            "publish_notes": str(payload.get("publish_notes", "Queue for manual review before publishing.")).strip(),
        }
