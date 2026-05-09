from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import AppConfig
from .speech import voice_stack_status


VOICE_SETTINGS_PATH = Path.cwd() / "data" / "settings" / "voice.json"
LOCATION_SETTINGS_PATH = Path.cwd() / "data" / "settings" / "locations.json"
PIPER_VOICE_ROOT = Path.cwd() / "assets" / "piper" / "voices"
VALID_TTS_PROVIDERS = {"auto", "piper", "localai", "elevenlabs", "system"}


@dataclass(slots=True)
class VoiceSettings:
    tts_provider: str
    elevenlabs_voice: str
    piper_model_path: str
    piper_speaker: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class VoiceSettingsStore:
    def __init__(self, config: AppConfig, path: Path = VOICE_SETTINGS_PATH) -> None:
        self.config = config
        self.path = path

    def load(self) -> VoiceSettings:
        defaults = self.defaults()
        if not self.path.exists():
            return defaults
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        return self._coerce(payload, defaults=defaults)

    def save(self, payload: dict) -> VoiceSettings:
        settings = self._coerce(payload, defaults=self.load())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(settings.to_dict(), indent=2),
            encoding="utf-8",
        )
        return settings

    def defaults(self) -> VoiceSettings:
        default_piper = ""
        if self.config.piper_model_path and self.config.piper_model_path.exists():
            default_piper = str(self.config.piper_model_path.resolve())
        else:
            piper_voices = self.list_piper_voices()
            if piper_voices:
                default_piper = piper_voices[0]["id"]
        return VoiceSettings(
            tts_provider=self.config.tts_provider if self.config.tts_provider in VALID_TTS_PROVIDERS else "auto",
            elevenlabs_voice=self.config.elevenlabs_voice,
            piper_model_path=default_piper,
            piper_speaker=self.config.piper_speaker,
        )

    def describe(self) -> dict:
        settings = self.load()
        options = self.voice_options()
        return {
            **settings.to_dict(),
            "selected_provider_label": self._provider_label(settings.tts_provider),
            "selected_elevenlabs_label": self._selected_label(options["elevenlabs"], settings.elevenlabs_voice),
            "selected_piper_label": self._selected_label(options["piper"], settings.piper_model_path),
            "stack_status": voice_stack_status(self.config, settings.to_dict()),
        }

    def voice_options(self) -> dict:
        return {
            "providers": [
                {"id": "auto", "label": "Auto"},
                {"id": "elevenlabs", "label": "ElevenLabs"},
                {"id": "piper", "label": "Piper"},
                {"id": "localai", "label": "LocalAI"},
                {"id": "system", "label": "Browser/System Fallback"},
            ],
            "elevenlabs": self.list_elevenlabs_voices(),
            "piper": self.list_piper_voices(),
            "stack_status": voice_stack_status(self.config, self.load().to_dict()),
        }

    def list_piper_voices(self) -> list[dict]:
        voices: list[dict] = []
        if not PIPER_VOICE_ROOT.exists():
            return voices
        for model_path in sorted(PIPER_VOICE_ROOT.rglob("*.onnx")):
            metadata_path = model_path.with_suffix(model_path.suffix + ".json")
            label = model_path.stem.replace("_", " ").replace("-", " ").title()
            detail_bits: list[str] = []
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    metadata = {}
                dataset = str(metadata.get("dataset", "")).strip()
                if dataset:
                    dataset_label = dataset.split("_", 1)[1] if "_" in dataset else dataset
                    label = dataset_label.replace("_", " ").replace("-", " ").title()
                language = metadata.get("language", {})
                if isinstance(language, dict):
                    english = str(language.get("name_english", "")).strip()
                    country = str(language.get("country_english", "")).strip()
                    if english:
                        detail_bits.append(english if not country else f"{english} · {country}")
                quality = metadata.get("audio", {}).get("quality", "")
                if quality:
                    detail_bits.append(str(quality).title())
            relative_path = model_path.relative_to(Path.cwd())
            voices.append(
                {
                    "id": str(model_path.resolve()),
                    "label": label,
                    "detail": " · ".join(detail_bits),
                    "provider": "piper",
                    "available": model_path.exists(),
                    "path": str(relative_path),
                }
            )
        return voices

    def list_elevenlabs_voices(self) -> list[dict]:
        api_key = self.config.elevenlabs_api_key.strip()
        if not api_key:
            return []
        try:
            from elevenlabs.client import ElevenLabs
        except ModuleNotFoundError:
            return []

        client = ElevenLabs(api_key=api_key)
        try:
            payload = client.voices.get_all()
        except Exception:
            return []

        voices: list[dict] = []
        for item in getattr(payload, "voices", []):
            voice_id = str(getattr(item, "voice_id", "")).strip()
            name = str(getattr(item, "name", "")).strip()
            if not voice_id or not name:
                continue
            voices.append(
                {
                    "id": voice_id,
                    "label": name,
                    "detail": "",
                    "provider": "elevenlabs",
                    "available": True,
                }
            )
        return voices

    def _coerce(self, payload: dict, defaults: VoiceSettings) -> VoiceSettings:
        provider = str(payload.get("tts_provider", defaults.tts_provider)).strip().lower()
        if provider not in VALID_TTS_PROVIDERS:
            provider = defaults.tts_provider

        elevenlabs_voice = str(
            payload.get("elevenlabs_voice", defaults.elevenlabs_voice)
        ).strip() or defaults.elevenlabs_voice

        piper_model_path = str(
            payload.get("piper_model_path", defaults.piper_model_path)
        ).strip() or defaults.piper_model_path

        piper_speaker = str(
            payload.get("piper_speaker", defaults.piper_speaker)
        ).strip()

        if piper_model_path and not Path(piper_model_path).exists():
            piper_model_path = defaults.piper_model_path

        return VoiceSettings(
            tts_provider=provider,
            elevenlabs_voice=elevenlabs_voice,
            piper_model_path=piper_model_path,
            piper_speaker=piper_speaker,
        )

    @staticmethod
    def _provider_label(provider: str) -> str:
        mapping = {
            "auto": "Auto",
            "elevenlabs": "ElevenLabs",
            "piper": "Piper",
            "localai": "LocalAI",
            "system": "Browser/System Fallback",
        }
        return mapping.get(provider, provider.title())

    @staticmethod
    def _selected_label(options: list[dict], selected_id: str) -> str:
        for option in options:
            if option.get("id") == selected_id:
                label = str(option.get("label", selected_id))
                detail = str(option.get("detail", "")).strip()
                return label if not detail else f"{label} · {detail}"
        return selected_id or "--"


class LocationSettingsStore:
    def __init__(self, config: AppConfig, path: Path = LOCATION_SETTINGS_PATH) -> None:
        self.config = config
        self.path = path

    def defaults(self) -> dict:
        home_id = "household-home"
        return {
            "preferred_location_id": home_id,
            "saved_locations": [
                {
                    "id": home_id,
                    "label": self.config.load_household().location_label,
                    "geography": self.config.load_household().location_label,
                    "latitude": None,
                    "longitude": None,
                    "source": "household-profile",
                    "notes": "Default household location.",
                }
            ],
            "device_location": None,
        }

    def load(self) -> dict:
        defaults = self.defaults()
        if not self.path.exists():
            return defaults
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        return self._coerce(payload, defaults)

    def save(self, payload: dict) -> dict:
        state = self._coerce(payload, self.load())
        self._write(state)
        return state

    def add_location(self, payload: dict) -> dict:
        state = self.load()
        saved = list(state.get("saved_locations", []))
        label = str(payload.get("label", "")).strip()
        geography = str(payload.get("geography", "")).strip() or label
        if not label:
            raise ValueError("Location label is required.")
        location_id = str(payload.get("id", "")).strip() or _slugify_location(label)
        entry = {
            "id": location_id,
            "label": label,
            "geography": geography,
            "latitude": _float_or_none(payload.get("latitude")),
            "longitude": _float_or_none(payload.get("longitude")),
            "source": str(payload.get("source", "manual")).strip() or "manual",
            "notes": str(payload.get("notes", "")).strip(),
        }
        saved = [item for item in saved if item.get("id") != location_id]
        saved.append(entry)
        state["saved_locations"] = saved
        if payload.get("make_preferred"):
            state["preferred_location_id"] = location_id
        self._write(state)
        return state

    def save_device_location(self, payload: dict) -> dict:
        state = self.load()
        label = str(payload.get("label", "")).strip() or "Current Device Location"
        geography = str(payload.get("geography", "")).strip() or label
        device_location = {
            "label": label,
            "geography": geography,
            "latitude": _float_or_none(payload.get("latitude")),
            "longitude": _float_or_none(payload.get("longitude")),
            "source": "device-location-services",
            "timestamp": str(payload.get("timestamp", "")).strip(),
        }
        state["device_location"] = device_location
        if payload.get("save_as_location"):
            state = self.add_location(
                {
                    "id": "device-current",
                    "label": label,
                    "geography": geography,
                    "latitude": device_location["latitude"],
                    "longitude": device_location["longitude"],
                    "source": "device-location-services",
                    "notes": "Captured from browser location services.",
                    "make_preferred": bool(payload.get("make_preferred")),
                }
            )
            state["device_location"] = device_location
            self._write(state)
            return state
        if payload.get("make_preferred"):
            saved = list(state.get("saved_locations", []))
            existing = next((item for item in saved if item.get("id") == "device-current"), None)
            if existing:
                state["preferred_location_id"] = "device-current"
        self._write(state)
        return state

    def set_preferred_location(self, location_id: str) -> dict:
        state = self.load()
        candidate_ids = {item.get("id") for item in state.get("saved_locations", [])}
        if location_id not in candidate_ids:
            raise ValueError("Unknown location id.")
        state["preferred_location_id"] = location_id
        self._write(state)
        return state

    def describe(self) -> dict:
        state = self.load()
        active = next(
            (item for item in state.get("saved_locations", []) if item.get("id") == state.get("preferred_location_id")),
            None,
        )
        if not active:
            active = state.get("device_location") or {}
        return {
            **state,
            "active_location": active,
        }

    def _write(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _coerce(self, payload: dict, defaults: dict) -> dict:
        saved_raw = payload.get("saved_locations", defaults.get("saved_locations", []))
        saved: list[dict] = []
        for item in saved_raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            geography = str(item.get("geography", "")).strip() or label
            location_id = str(item.get("id", "")).strip() or _slugify_location(label or geography or "location")
            if not label and not geography:
                continue
            saved.append(
                {
                    "id": location_id,
                    "label": label or geography,
                    "geography": geography or label,
                    "latitude": _float_or_none(item.get("latitude")),
                    "longitude": _float_or_none(item.get("longitude")),
                    "source": str(item.get("source", "manual")).strip() or "manual",
                    "notes": str(item.get("notes", "")).strip(),
                }
            )
        if not saved:
            saved = defaults["saved_locations"]
        preferred = str(payload.get("preferred_location_id", defaults.get("preferred_location_id", ""))).strip()
        if preferred not in {item.get("id") for item in saved}:
            preferred = saved[0]["id"]
        device_raw = payload.get("device_location")
        device = None
        if isinstance(device_raw, dict):
            device = {
                "label": str(device_raw.get("label", "")).strip() or "Current Device Location",
                "geography": str(device_raw.get("geography", "")).strip() or str(device_raw.get("label", "")).strip() or "Current Device Location",
                "latitude": _float_or_none(device_raw.get("latitude")),
                "longitude": _float_or_none(device_raw.get("longitude")),
                "source": str(device_raw.get("source", "device-location-services")).strip() or "device-location-services",
                "timestamp": str(device_raw.get("timestamp", "")).strip(),
            }
        return {
            "preferred_location_id": preferred,
            "saved_locations": saved,
            "device_location": device,
        }


def _float_or_none(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _slugify_location(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "location"
