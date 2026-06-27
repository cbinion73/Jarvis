from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, root: Path, *, read_only: bool = False) -> None:
        self.root = root
        self.read_only = read_only
        if not self.read_only:
            self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._index_cache: list[dict] | None = None
        self._thread_cache: dict[str, dict] = {}

    def _load_json(self, path: Path, default: object) -> object:
        if not path.exists():
            payload = self._load_json_from_state_log(path, default)
            if payload != default:
                return payload
            return self._load_json_from_log(path, default)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = self._load_json_from_state_log(path, default)
            if payload != default:
                return payload
            return self._load_json_from_log(path, default)
        if payload == default:
            replayed = self._load_json_from_state_log(path, default)
            if replayed != default:
                return replayed
            return self._load_json_from_log(path, default)
        return payload

    def _save_json(self, path: Path, payload: object) -> None:
        if self.read_only:
            return
        atomic_write_json(path, payload)
        append_jsonl(
            self._log_path(path),
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )
        append_jsonl(
            self._state_log_path(path),
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def _log_path(self, path: Path) -> Path:
        if path == self.index_path:
            return self.root / "index_log.jsonl"
        return path.with_suffix(".log.jsonl")

    def _state_log_path(self, path: Path) -> Path:
        if path == self.index_path:
            return self.root / "index_state_log.jsonl"
        return path.with_suffix(".state_log.jsonl")

    def _load_json_from_log(self, path: Path, default: object) -> object:
        log_path = self._log_path(path)
        if not log_path.exists():
            return default
        latest: object = default
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                latest = payload.get("records", default)
        except (OSError, json.JSONDecodeError):
            return default
        if isinstance(default, dict):
            return dict(latest) if isinstance(latest, dict) else default
        if isinstance(default, list):
            if not isinstance(latest, list):
                return default
            return [dict(item) if isinstance(item, dict) else item for item in latest]
        return latest

    def _load_json_from_state_log(self, path: Path, default: object) -> object:
        log_path = self._state_log_path(path)
        if not log_path.exists():
            return default
        latest: object = default
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                latest = payload.get("records", default)
        except (OSError, json.JSONDecodeError):
            return default
        if isinstance(default, dict):
            return dict(latest) if isinstance(latest, dict) else default
        if isinstance(default, list):
            if not isinstance(latest, list):
                return default
            return [dict(item) if isinstance(item, dict) else item for item in latest]
        return latest

    def _index(self) -> list[dict]:
        if self._index_cache is None:
            payload = self._load_json(self.index_path, [])
            self._index_cache = [dict(item) for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []
        return deepcopy(self._index_cache)

    def _save_index(self, records: list[dict]) -> None:
        records = sorted(records, key=lambda item: str(item.get("updated_at", "")), reverse=True)
        self._index_cache = [dict(item) for item in records]
        self._save_json(self.index_path, records)

    def _thread_path(self, conversation_id: str) -> Path:
        return self.root / f"{conversation_id}.json"

    def _thread_record(self, conversation_id: str) -> dict | None:
        normalized = conversation_id.strip()
        if not normalized:
            return None
        cached = self._thread_cache.get(normalized)
        if cached is not None:
            return deepcopy(cached)
        path = self._thread_path(normalized)
        if not path.exists():
            return None
        payload = self._load_json(path, {})
        if not isinstance(payload, dict):
            return None
        record = dict(payload)
        self._thread_cache[normalized] = record
        return deepcopy(record)

    def _save_thread(self, record: dict) -> None:
        conversation_id = str(record.get("conversation_id", "")).strip()
        if not conversation_id:
            return
        self._thread_cache[conversation_id] = deepcopy(record)
        self._save_json(self._thread_path(conversation_id), record)

    def _title_from_text(self, text: str) -> str:
        cleaned = " ".join(str(text or "").strip().split())
        if not cleaned:
            return "New conversation"
        return cleaned[:72]

    def create(self, actor: str, room: str, source: str = "shell") -> dict:
        now = _now_iso()
        conversation_id = str(uuid.uuid4())
        record = {
            "conversation_id": conversation_id,
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "source": source.strip() or "shell",
            "title": "New conversation",
            "status": "active",
            "summary": "",
            "memory_signals": [],
            "created_at": now,
            "updated_at": now,
            "last_activity_at": now,
            "turn_count": 0,
            "latest_user_text": "",
            "latest_assistant_text": "",
            "turns": [],
        }
        self._save_thread(record)
        index = self._index()
        index = [item for item in index if item.get("conversation_id") != conversation_id]
        index.append(self._index_entry(record))
        self._save_index(index)
        return deepcopy(record)

    def _index_entry(self, record: dict) -> dict:
        return {
            "conversation_id": record.get("conversation_id", ""),
            "actor": record.get("actor", ""),
            "room": record.get("room", ""),
            "source": record.get("source", "shell"),
            "title": record.get("title", "New conversation"),
            "status": record.get("status", "active"),
            "summary": record.get("summary", ""),
            "memory_signals": list(record.get("memory_signals", []))[-8:],
            "created_at": record.get("created_at", ""),
            "updated_at": record.get("updated_at", ""),
            "last_activity_at": record.get("last_activity_at", ""),
            "turn_count": int(record.get("turn_count", 0) or 0),
            "latest_user_text": record.get("latest_user_text", ""),
            "latest_assistant_text": record.get("latest_assistant_text", ""),
        }

    def ensure(self, actor: str, room: str, conversation_id: str = "", source: str = "shell") -> dict:
        if conversation_id.strip():
            record = self.get(conversation_id)
            if record is not None:
                return record
        return self.create(actor, room, source=source)

    def get(self, conversation_id: str) -> dict | None:
        return self._thread_record(conversation_id)

    def list_recent(self, actor: str = "", limit: int = 8) -> list[dict]:
        actor_name = actor.strip().lower()
        records = self._index()
        if actor_name:
            records = [item for item in records if str(item.get("actor", "")).strip().lower() == actor_name]
        return records[: max(1, limit)]

    def update_thread(self, conversation_id: str, **updates: object) -> dict | None:
        record = self.get(conversation_id)
        if record is None:
            return None
        for key, value in updates.items():
            record[key] = value
        record["updated_at"] = _now_iso()
        self._save_thread(record)
        index = [item for item in self._index() if item.get("conversation_id") != conversation_id]
        index.append(self._index_entry(record))
        self._save_index(index)
        return deepcopy(record)

    def append_turn(
        self,
        conversation_id: str,
        *,
        role: str,
        text: str,
        actor: str = "",
        room: str = "",
        source: str = "shell",
        metadata: dict | None = None,
    ) -> dict | None:
        record = self.get(conversation_id)
        if record is None:
            return None
        turn_text = str(text or "").strip()
        if not turn_text:
            return record
        now = _now_iso()
        turns = list(record.get("turns", []))
        turns.append(
            {
                "turn_id": str(uuid.uuid4()),
                "role": role.strip() or "assistant",
                "text": turn_text,
                "actor": actor.strip() or record.get("actor", ""),
                "room": room.strip() or record.get("room", ""),
                "source": source.strip() or record.get("source", "shell"),
                "created_at": now,
                "metadata": dict(metadata or {}),
            }
        )
        record["turns"] = turns
        record["turn_count"] = len(turns)
        record["updated_at"] = now
        record["last_activity_at"] = now
        if actor.strip():
            record["actor"] = actor.strip()
        if room.strip():
            record["room"] = room.strip()
        if source.strip():
            record["source"] = source.strip()
        if role == "user":
            record["latest_user_text"] = turn_text
            if record.get("title") in {"", "New conversation"}:
                record["title"] = self._title_from_text(turn_text)
        else:
            record["latest_assistant_text"] = turn_text
        self._save_thread(record)
        index = [item for item in self._index() if item.get("conversation_id") != conversation_id]
        index.append(self._index_entry(record))
        self._save_index(index)
        return deepcopy(record)
