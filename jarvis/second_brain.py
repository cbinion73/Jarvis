from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request

from .config import AppConfig


@dataclass(slots=True)
class SecondBrainResult:
    provider: str
    model: str
    output_text: str


class OllamaBrainClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def enabled(self) -> bool:
        return self.config.second_brain_enabled and self.config.second_brain_provider == "ollama"

    def healthy(self) -> bool:
        if not self.enabled():
            return False
        try:
            with request.urlopen(f"{self.config.ollama_base_url.rstrip('/')}/api/tags", timeout=2) as response:
                return 200 <= response.status < 300
        except (error.URLError, TimeoutError, ValueError):
            return False

    def model_available(self) -> bool:
        return self._model_available(self.config.second_brain_model)

    def _model_available(self, model: str) -> bool:
        if not self.healthy():
            return False
        try:
            with request.urlopen(f"{self.config.ollama_base_url.rstrip('/')}/api/tags", timeout=4) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return False
        models = body.get("models", []) if isinstance(body, dict) else []
        target = model.strip()
        for item in models:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            model_name = str(item.get("model", "")).strip()
            if name == target or model_name == target:
                return True
        return False

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> SecondBrainResult:
        if not self.enabled():
            raise RuntimeError("Second brain is disabled.")
        selected_model = model or self.config.second_brain_model
        if not self._model_available(selected_model):
            raise RuntimeError(f"Second brain model '{selected_model}' is not available yet.")
        payload = json.dumps(
            {
                "model": selected_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {
                    "temperature": 0.4,
                },
            }
        ).encode("utf-8")
        req = request.Request(
            f"{self.config.ollama_base_url.rstrip('/')}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        message = body.get("message", {}) if isinstance(body, dict) else {}
        content = str(message.get("content", "")).strip()
        if not content:
            raise RuntimeError("Second brain response was empty.")
        return SecondBrainResult(
            provider="ollama",
            model=str(body.get("model") or selected_model),
            output_text=content,
        )
