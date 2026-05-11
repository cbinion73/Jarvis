from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from .config import AppConfig


@dataclass(slots=True)
class OpenVikingSupport:
    config: AppConfig

    @property
    def enabled(self) -> bool:
        return bool(
            self.config.openviking_enabled
            and self.config.openviking_base_url
            and self.config.openviking_api_key
            and self.config.openviking_memory_uri_root
        )

    @property
    def base_url(self) -> str:
        return self.config.openviking_base_url.rstrip("/")

    @property
    def memory_uri_root(self) -> str:
        root = self.config.openviking_memory_uri_root.strip()
        return root if root.endswith("/") else f"{root}/"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.openviking_api_key:
            headers["X-API-Key"] = self.config.openviking_api_key
        if self.config.openviking_account:
            headers["X-OpenViking-Account"] = self.config.openviking_account
        if self.config.openviking_user:
            headers["X-OpenViking-User"] = self.config.openviking_user
        if self.config.openviking_agent_id:
            headers["X-OpenViking-Agent"] = self.config.openviking_agent_id
        return headers

    def status(self) -> dict:
        if not self.config.openviking_enabled:
            return {"ok": False, "enabled": False, "detail": "OpenViking integration is disabled."}
        try:
            response = requests.get(f"{self.base_url}/health", headers=self._headers(), timeout=5)
            detail = response.text.strip()
            if response.headers.get("content-type", "").startswith("application/json"):
                try:
                    detail = json.dumps(response.json(), indent=2)
                except ValueError:
                    pass
            return {
                "ok": response.ok,
                "enabled": True,
                "base_url": self.base_url,
                "memory_uri_root": self.memory_uri_root,
                "detail": detail or f"http {response.status_code}",
            }
        except requests.RequestException as exc:
            return {
                "ok": False,
                "enabled": True,
                "base_url": self.base_url,
                "memory_uri_root": self.memory_uri_root,
                "detail": str(exc),
            }

    def sync_memory_entry(self, entry: dict) -> dict:
        if not self.enabled:
            return {"ok": False, "skipped": True, "detail": "OpenViking is not fully configured."}
        if entry.get("approval_status") != "approved":
            return {"ok": False, "skipped": True, "detail": "Entry is not approved for context sync."}
        if entry.get("cloud_excluded"):
            return {"ok": False, "skipped": True, "detail": "This memory lane is marked local-only."}
        if entry.get("memory_type") == "safety" or entry.get("sensitivity") == "sensitive":
            return {"ok": False, "skipped": True, "detail": "Safety and sensitive memories stay local-only for now."}

        entry_type = str(entry.get("memory_type", "unknown")).strip().lower() or "unknown"
        entry_id = str(entry.get("entry_id", "")).strip()
        uri = f"{self.memory_uri_root}{entry_type}-{entry_id}.md"
        content = self._render_memory_entry(entry)

        response = self._write(uri, content, mode="create")
        if response.status_code == 409:
            response = self._write(uri, content, mode="replace")

        if response.ok:
            payload = response.json()
            return {
                "ok": True,
                "entry_id": entry_id,
                "uri": uri,
                "detail": payload.get("result", {}),
            }
        if "resource is busy" in self._response_detail(response).lower():
            existing = self._read(uri)
            if existing.ok:
                return {
                    "ok": True,
                    "entry_id": entry_id,
                    "uri": uri,
                    "detail": {"status": "present", "mode": "read-after-busy"},
                }
        return {
            "ok": False,
            "entry_id": entry_id,
            "uri": uri,
            "detail": self._response_detail(response),
        }

    def sync_memory_entries(self, entries: list[dict]) -> dict:
        results = [self.sync_memory_entry(entry) for entry in entries]
        return {
            "ok": all(item.get("ok") or item.get("skipped") for item in results),
            "base_url": self.base_url,
            "memory_uri_root": self.memory_uri_root,
            "results": results,
            "synced": len([item for item in results if item.get("ok")]),
            "skipped": len([item for item in results if item.get("skipped")]),
            "failed": len([item for item in results if not item.get("ok") and not item.get("skipped")]),
        }

    def overview(self, uri: str) -> dict:
        if not self.enabled:
            return {"ok": False, "detail": "OpenViking is not fully configured."}
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/content/overview",
                headers=self._headers(),
                params={"uri": uri},
                timeout=15,
            )
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            return {
                "ok": response.ok,
                "uri": uri,
                "result": payload.get("result"),
                "detail": payload if payload else self._response_detail(response),
            }
        except requests.RequestException as exc:
            return {"ok": False, "uri": uri, "detail": str(exc)}

    def find(self, query: str, *, target_uri: str | None = None, limit: int = 5) -> dict:
        if not self.enabled:
            return {"ok": False, "detail": "OpenViking is not fully configured."}
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/search/find",
                headers=self._headers(),
                json={
                    "query": query,
                    "target_uri": target_uri or self.memory_uri_root.rstrip("/"),
                    "limit": limit,
                    "include_provenance": True,
                },
                timeout=20,
            )
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            return {
                "ok": response.ok,
                "query": query,
                "result": payload.get("result"),
                "detail": payload if payload else self._response_detail(response),
            }
        except requests.RequestException as exc:
            return {"ok": False, "query": query, "detail": str(exc)}

    def party_mode_context(self, prompt: str, *, limit: int = 4) -> str:
        result = self.find(prompt, limit=limit)
        if not result.get("ok"):
            return ""
        payload = result.get("result") or {}
        items = payload.get("items") or payload.get("hits") or payload.get("memories") or []
        lines: list[str] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("uri") or "context").strip()
            abstract = str(item.get("abstract") or item.get("overview") or item.get("content") or item.get("summary") or "").strip()
            if not abstract:
                continue
            lines.append(f"- {title}: {abstract[:400]}")
        return "\n".join(lines)

    def _write(self, uri: str, content: str, *, mode: str) -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/v1/content/write",
            headers=self._headers(),
            json={"uri": uri, "content": content, "mode": mode, "wait": True},
            timeout=30,
        )

    def _read(self, uri: str) -> requests.Response:
        return requests.get(
            f"{self.base_url}/api/v1/content/read",
            headers=self._headers(),
            params={"uri": uri},
            timeout=15,
        )

    def _response_detail(self, response: requests.Response) -> str:
        try:
            payload = response.json()
            return json.dumps(payload, indent=2)
        except ValueError:
            return response.text.strip() or f"http {response.status_code}"

    def _render_memory_entry(self, entry: dict) -> str:
        payload = entry.get("payload") or {}
        memory_fields = {
            "entry_id": entry.get("entry_id", ""),
            "memory_type": entry.get("memory_type", ""),
            "scope": entry.get("scope", ""),
            "owner": entry.get("owner", ""),
            "project": entry.get("project", ""),
            "tags": entry.get("tags", []),
            "created_at": entry.get("created_at", ""),
            "updated_at": entry.get("updated_at", ""),
            "captured_by": payload.get("captured_by", ""),
        }
        clean_fields = {key: value for key, value in memory_fields.items() if value not in ("", None, [], {})}
        meta_json = json.dumps(clean_fields, indent=2)
        detail = str(payload.get("detail", "")).strip()
        content = (
            f"# {entry.get('title', 'Untitled memory')}\n\n"
            f"## Summary\n{entry.get('summary', '').strip()}\n\n"
            f"## Detail\n{detail}\n"
        ).strip()
        return f"{content}\n\n<!-- MEMORY_FIELDS\n{meta_json}\n-->"
