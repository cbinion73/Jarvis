from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .data_hygiene import filter_records
from .persistence import append_jsonl, atomic_write_json


SHARED_DOCTRINE_PATH = Path.cwd() / "data" / "settings" / "shared_doctrine.json"
SHARED_DOCTRINE_LOG_PATH = SHARED_DOCTRINE_PATH.with_name("shared_doctrine_log.jsonl")
SHARED_DOCTRINE_STATE_LOG_PATH = SHARED_DOCTRINE_PATH.with_name("shared_doctrine_state_log.jsonl")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SharedDoctrineStore:
    def __init__(self, path: Path = SHARED_DOCTRINE_PATH) -> None:
        self.path = path

    def _default_payload(self) -> dict[str, Any]:
        return {
            "generated_at": "",
            "candidates": [],
            "rules": [],
            "history": [],
            "last_synthesis": {},
        }

    def _log_path(self) -> Path:
        if self.path == SHARED_DOCTRINE_PATH:
            return SHARED_DOCTRINE_LOG_PATH
        return self.path.with_name(f"{self.path.stem}_log.jsonl")

    def _state_log_path(self) -> Path:
        if self.path == SHARED_DOCTRINE_PATH:
            return SHARED_DOCTRINE_STATE_LOG_PATH
        return self.path.with_name(f"{self.path.stem}_state_log.jsonl")

    def _load_from_log(self) -> dict[str, Any]:
        try:
            log_path = self._log_path()
            if log_path.exists():
                latest: dict[str, Any] | None = None
                for line in log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    state = payload.get("state")
                    if isinstance(state, dict):
                        latest = dict(state)
                if latest is not None:
                    return latest
        except (OSError, json.JSONDecodeError):
            pass
        return self._default_payload()

    def _load_from_state_log(self) -> dict[str, Any]:
        try:
            log_path = self._state_log_path()
            if log_path.exists():
                latest: dict[str, Any] | None = None
                for line in log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    state = payload.get("state")
                    if isinstance(state, dict):
                        latest = dict(state)
                if latest is not None:
                    return latest
        except (OSError, json.JSONDecodeError):
            pass
        return self._default_payload()

    def load(self) -> dict[str, Any]:
        default = self._default_payload()
        if not self.path.exists():
            payload = self._load_from_state_log()
            if payload == default:
                payload = self._load_from_log()
        else:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = self._load_from_state_log()
                if payload == default:
                    payload = self._load_from_log()
            else:
                if not isinstance(payload, dict) or not payload:
                    payload = self._load_from_state_log()
                    if payload == default:
                        payload = self._load_from_log()
        try:
            if not isinstance(payload, dict):
                return default
        except Exception:
            return default
        payload.setdefault("generated_at", "")
        payload.setdefault("candidates", [])
        payload.setdefault("rules", [])
        payload.setdefault("history", [])
        payload.setdefault("last_synthesis", {})
        payload["candidates"] = filter_records([dict(item) for item in list(payload.get("candidates", [])) if isinstance(item, dict)])
        payload["rules"] = filter_records([dict(item) for item in list(payload.get("rules", [])) if isinstance(item, dict)])
        payload["history"] = filter_records([dict(item) for item in list(payload.get("history", [])) if isinstance(item, dict)])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(payload)
        payload["generated_at"] = str(payload.get("generated_at", "")).strip() or _now_iso()
        atomic_write_json(self.path, payload)
        append_jsonl(
            self._log_path(),
            {
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "state": payload,
            },
        )
        append_jsonl(
            self._state_log_path(),
            {
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "state": payload,
            },
        )

    def replace_candidates(self, candidates: list[dict[str, Any]], *, synthesis_meta: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["generated_at"] = _now_iso()
        state["candidates"] = [dict(item) for item in candidates]
        state["last_synthesis"] = dict(synthesis_meta)
        history = list(state.get("history", []))
        history.append(
            {
                "timestamp": state["generated_at"],
                "event": "synthesized",
                "candidate_count": len(candidates),
                "rule_count": len(list(state.get("rules", []))),
                "meta": dict(synthesis_meta),
            }
        )
        state["history"] = history[-120:]
        self.save(state)
        return state

    def merge_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        synthesis_meta: dict[str, Any],
        source: str = "",
    ) -> dict[str, Any]:
        state = self.load()
        merged: list[dict[str, Any]] = []
        incoming = [dict(item) for item in candidates if isinstance(item, dict)]
        source_key = str(source).strip().lower()
        incoming_ids = {
            str(item.get("candidate_id", "")).strip()
            for item in incoming
            if str(item.get("candidate_id", "")).strip()
        }
        for item in list(state.get("candidates", [])):
            if not isinstance(item, dict):
                continue
            item_source = str(item.get("source", "")).strip().lower()
            item_id = str(item.get("candidate_id", "")).strip()
            if source_key and item_source == source_key:
                if item_id and item_id in incoming_ids:
                    continue
                if not item_id:
                    continue
            merged.append(dict(item))
        merged.extend(incoming)
        state["generated_at"] = _now_iso()
        state["candidates"] = merged[-240:]
        state["last_synthesis"] = dict(synthesis_meta)
        history = list(state.get("history", []))
        history.append(
            {
                "timestamp": state["generated_at"],
                "event": "merged_candidates",
                "candidate_count": len(incoming),
                "total_candidate_count": len(state["candidates"]),
                "source": source_key,
                "meta": dict(synthesis_meta),
            }
        )
        state["history"] = history[-120:]
        self.save(state)
        return state

    def list_candidates(self, *, status: str = "") -> list[dict[str, Any]]:
        candidates = list(self.load().get("candidates", []))
        normalized = str(status).strip().lower()
        if not normalized:
            return candidates
        return [item for item in candidates if str(item.get("status", "")).strip().lower() == normalized]

    def list_rules(self, *, active_only: bool = True) -> list[dict[str, Any]]:
        rules = list(self.load().get("rules", []))
        if not active_only:
            return rules
        return [item for item in rules if str(item.get("status", "active")).strip().lower() == "active"]

    def rules_for(
        self,
        *,
        actor: str = "",
        domain: str = "",
        agent_id: str = "",
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        actor_key = str(actor).strip().lower()
        domain_key = str(domain).strip().lower()
        agent_key = str(agent_id).strip().lower()
        matches: list[dict[str, Any]] = []
        for item in self.list_rules(active_only=active_only):
            actors = [str(entry).strip().lower() for entry in list(item.get("actors", [])) if str(entry).strip()]
            domains = [str(entry).strip().lower() for entry in list(item.get("domains", [])) if str(entry).strip()]
            agents = [str(entry).strip().lower() for entry in list(item.get("agent_ids", [])) if str(entry).strip()]
            if actor_key and actors and actor_key not in actors:
                continue
            if domain_key and domains and domain_key not in domains:
                continue
            if agent_key and agents and agent_key not in agents:
                continue
            matches.append(dict(item))
        return matches

    def promote_candidate(
        self,
        candidate_id: str,
        *,
        promoted_by: str = "",
        basis: str = "",
    ) -> dict[str, Any] | None:
        state = self.load()
        candidates = list(state.get("candidates", []))
        candidate = next((item for item in candidates if str(item.get("candidate_id", "")).strip() == candidate_id.strip()), None)
        if candidate is None:
            return None
        timestamp = _now_iso()
        candidate["status"] = "promoted"
        candidate["promoted_at"] = timestamp
        candidate["promoted_by"] = promoted_by.strip()
        rule_id = str(candidate.get("rule_id", "")).strip() or f"rule-{candidate_id.strip()}"
        rule = {
            "rule_id": rule_id,
            "source_candidate_id": candidate_id.strip(),
            "title": str(candidate.get("title", "")).strip(),
            "summary": str(candidate.get("summary", "")).strip(),
            "kind": str(candidate.get("kind", "heuristic")).strip() or "heuristic",
            "status": "active",
            "domains": list(candidate.get("domains", [])),
            "agent_ids": list(candidate.get("agent_ids", [])),
            "actors": list(candidate.get("actors", [])),
            "policy_effects": dict(candidate.get("policy_effects", {})),
            "evidence": dict(candidate.get("evidence", {})),
            "promotion_basis": basis.strip() or str(candidate.get("promotion_reason", "")).strip() or "promoted",
            "promoted_at": timestamp,
            "promoted_by": promoted_by.strip(),
        }
        rules = [item for item in list(state.get("rules", [])) if str(item.get("rule_id", "")).strip() != rule_id]
        rules.append(rule)
        state["rules"] = rules[-200:]
        state["candidates"] = candidates
        history = list(state.get("history", []))
        history.append(
            {
                "timestamp": timestamp,
                "event": "promoted",
                "candidate_id": candidate_id.strip(),
                "rule_id": rule_id,
                "promoted_by": promoted_by.strip(),
                "basis": rule["promotion_basis"],
            }
        )
        state["history"] = history[-120:]
        self.save(state)
        return rule

    def dismiss_candidate(self, candidate_id: str, *, dismissed_by: str = "", reason: str = "") -> dict[str, Any] | None:
        state = self.load()
        candidates = list(state.get("candidates", []))
        candidate = next((item for item in candidates if str(item.get("candidate_id", "")).strip() == candidate_id.strip()), None)
        if candidate is None:
            return None
        timestamp = _now_iso()
        candidate["status"] = "dismissed"
        candidate["dismissed_at"] = timestamp
        candidate["dismissed_by"] = dismissed_by.strip()
        if reason.strip():
            candidate["dismiss_reason"] = reason.strip()
        history = list(state.get("history", []))
        history.append(
            {
                "timestamp": timestamp,
                "event": "dismissed",
                "candidate_id": candidate_id.strip(),
                "dismissed_by": dismissed_by.strip(),
                "reason": reason.strip(),
            }
        )
        state["history"] = history[-120:]
        state["candidates"] = candidates
        self.save(state)
        return candidate
