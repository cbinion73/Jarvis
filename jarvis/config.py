from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
import sys

from .models import (
    FamilyEvent,
    HouseholdProfile,
    HouseholdSnapshot,
    VoiceContextProfile,
    VoiceSatelliteProfile,
    RoomProfile,
    SnapshotCard,
    UserProfile,
)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(slots=True)
class AppConfig:
    openai_api_key: str
    elevenlabs_api_key: str
    openai_model: str
    openai_text_model: str
    openai_router_model: str
    openai_realtime_model: str
    elevenlabs_voice: str
    tts_provider: str
    tts_fallbacks: tuple[str, ...]
    stt_provider: str
    stt_fallbacks: tuple[str, ...]
    localai_base_url: str
    localai_api_key: str
    localai_tts_model: str
    localai_tts_backend: str
    localai_stt_model: str
    piper_binary: str
    piper_model_path: Path | None
    piper_speaker: str
    livekit_url: str
    model_mode: str
    ollama_enabled: bool
    skip_model_warmup: bool
    livekit_api_key: str
    livekit_api_secret: str
    second_brain_provider: str
    second_brain_model: str
    second_brain_enabled: bool
    ollama_base_url: str
    ollama_summarize_model: str
    ollama_background_model: str
    home_assistant_url: str
    home_assistant_token: str
    openclaw_gateway_url: str
    household_config_path: Path
    household_snapshot_path: Path
    voice_context_path: Path
    executive_profile_path: Path
    chronicle_profile_path: Path
    family_profile_path: Path
    tutoring_profile_path: Path
    workshop_profile_path: Path
    security_profile_path: Path
    home_profile_path: Path
    perception_profile_path: Path
    memory_profile_path: Path
    catalyst_profile_path: Path
    runtime_profile_path: Path
    google_client_secret_path: Path
    google_token_path: Path
    microsoft_client_id: str
    microsoft_tenant_id: str
    microsoft_client_secret: str
    microsoft_redirect_uri: str
    microsoft_token_path: Path
    microsoft_authority: str
    plaid_client_id: str
    plaid_secret: str
    plaid_env: str
    plaid_country_codes: str
    openviking_enabled: bool
    openviking_base_url: str
    openviking_api_key: str
    openviking_account: str
    openviking_user: str
    openviking_agent_id: str
    openviking_memory_uri_root: str
    autonomous_workstreams_enabled: bool
    autonomous_workstream_lanes: tuple[str, ...]
    default_trust_owner_principal: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_env_file(Path(".env"))
        load_env_file(Path.home() / ".openclaw" / ".env")
        household_path = Path(
            os.getenv(
                "JARVIS_HOUSEHOLD_CONFIG",
                "household/jarvis_household.example.json",
        model_mode = os.getenv("JARVIS_MODEL_MODE", "standard").strip().lower() or "standard"
        cloud_light_mode = model_mode == "cloud_light"
            )
        )
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            openai_text_model=os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4-mini"),
            openai_router_model=os.getenv("OPENAI_ROUTER_MODEL", "gpt-5.4-nano"),
            openai_realtime_model=os.getenv(
                "OPENAI_REALTIME_MODEL", "gpt-realtime-1.5"
            ),
            elevenlabs_voice=os.getenv("ELEVENLABS_VOICE", "Adam"),
            tts_provider=os.getenv("JARVIS_TTS_PROVIDER", "auto").strip().lower(),
            tts_fallbacks=_csv_env(
                "JARVIS_TTS_FALLBACKS",
                ("piper", "localai", "elevenlabs", "system"),
            ),
            stt_provider=os.getenv("JARVIS_STT_PROVIDER", "openai").strip().lower(),
            stt_fallbacks=_csv_env(
                "JARVIS_STT_FALLBACKS",
                ("localai",),
            ),
            localai_base_url=os.getenv("LOCALAI_BASE_URL", "http://127.0.0.1:8080"),
            localai_api_key=os.getenv("LOCALAI_API_KEY", ""),
            localai_tts_model=os.getenv("LOCALAI_TTS_MODEL", "jarvis-piper"),
            localai_tts_backend=os.getenv("LOCALAI_TTS_BACKEND", "piper"),
            localai_stt_model=os.getenv("LOCALAI_STT_MODEL", "whisper-1"),
            piper_binary=_default_piper_binary(os.getenv("PIPER_BINARY", "")),
            piper_model_path=_default_piper_model_path(os.getenv("PIPER_MODEL_PATH", "")),
            piper_speaker=os.getenv("PIPER_SPEAKER", ""),
            livekit_url=os.getenv("LIVEKIT_URL", ""),
            livekit_api_key=os.getenv("LIVEKIT_API_KEY", ""),
            model_mode=model_mode,
            ollama_enabled=_bool_env("JARVIS_ENABLE_OLLAMA", not cloud_light_mode),
            skip_model_warmup=_bool_env("JARVIS_SKIP_MODEL_WARMUP", cloud_light_mode),
            livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
            second_brain_provider=os.getenv("JARVIS_SECOND_BRAIN_PROVIDER", "ollama").strip().lower(),
            second_brain_model=os.getenv("JARVIS_SECOND_BRAIN_MODEL", "qwen2.5:7b"),
            second_brain_enabled=_bool_env("JARVIS_SECOND_BRAIN_ENABLED", not cloud_light_mode),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_summarize_model=os.getenv("JARVIS_OLLAMA_SUMMARIZE_MODEL", "qwen2.5:7b"),
            ollama_background_model=os.getenv("JARVIS_OLLAMA_BACKGROUND_MODEL", "qwen2.5:7b"),
            home_assistant_url=os.getenv("HOME_ASSISTANT_URL", ""),
            home_assistant_token=os.getenv("HOME_ASSISTANT_TOKEN", ""),
            openclaw_gateway_url=os.getenv(
                "OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789"
            ),
            household_config_path=household_path,
            household_snapshot_path=Path(
                os.getenv(
                    "JARVIS_HOUSEHOLD_SNAPSHOT",
                    "household/jarvis_day_snapshot.example.json",
                )
            ),
            voice_context_path=Path(
                os.getenv(
                    "JARVIS_VOICE_CONTEXT",
                    "household/jarvis_voice_context.example.json",
                )
            ),
            executive_profile_path=Path(
                os.getenv(
                    "JARVIS_EXECUTIVE_PROFILE",
                    "household/jarvis_executive_profile.example.json",
                )
            ),
            chronicle_profile_path=Path(
                os.getenv(
                    "JARVIS_CHRONICLE_PROFILE",
                    "household/jarvis_chronicle_profile.example.json",
                )
            ),
            family_profile_path=Path(
                os.getenv(
                    "JARVIS_FAMILY_PROFILE",
                    "household/jarvis_family_profile.example.json",
                )
            ),
            tutoring_profile_path=Path(
                os.getenv(
                    "JARVIS_TUTORING_PROFILE",
                    "household/jarvis_tutoring_profile.example.json",
                )
            ),
            workshop_profile_path=Path(
                os.getenv(
                    "JARVIS_WORKSHOP_PROFILE",
                    "household/jarvis_workshop_profile.example.json",
                )
            ),
            security_profile_path=Path(
                os.getenv(
                    "JARVIS_SECURITY_PROFILE",
                    "household/jarvis_security_profile.example.json",
                )
            ),
            home_profile_path=Path(
                os.getenv(
                    "JARVIS_HOME_PROFILE",
                    "household/jarvis_home_assistant.example.json",
                )
            ),
            perception_profile_path=Path(
                os.getenv(
                    "JARVIS_PERCEPTION_PROFILE",
                    "household/jarvis_perception_profile.example.json",
                )
            ),
            memory_profile_path=Path(
                os.getenv(
                    "JARVIS_MEMORY_PROFILE",
                    "household/jarvis_memory_profile.example.json",
                )
            ),
            catalyst_profile_path=Path(
                os.getenv(
                    "JARVIS_CATALYST_PROFILE",
                    "household/jarvis_catalyst_profile.example.json",
                )
            ),
            runtime_profile_path=Path(
                os.getenv(
                    "JARVIS_RUNTIME_PROFILE",
                    "household/jarvis_runtime_profile.example.json",
                )
            ),
            google_client_secret_path=Path(
                os.getenv(
                    "JARVIS_GOOGLE_CLIENT_SECRET",
                    "config/google_client_secret.json",
                )
            ),
            google_token_path=Path(
                os.getenv(
                    "JARVIS_GOOGLE_TOKEN_PATH",
                    "data/google/google_token.json",
                )
            ),
            microsoft_client_id=os.getenv("JARVIS_MICROSOFT_CLIENT_ID", "").strip(),
            microsoft_tenant_id=os.getenv("JARVIS_MICROSOFT_TENANT_ID", "").strip(),
            microsoft_client_secret=os.getenv("JARVIS_MICROSOFT_CLIENT_SECRET", "").strip(),
            microsoft_redirect_uri=os.getenv(
                "JARVIS_MICROSOFT_REDIRECT_URI",
                "http://localhost:8787/auth/microsoft/callback",
            ).strip(),
            microsoft_token_path=Path(
                os.getenv(
                    "JARVIS_MICROSOFT_TOKEN_PATH",
                    "data/microsoft_graph/token.json",
                )
            ),
            microsoft_authority=os.getenv("JARVIS_MICROSOFT_AUTHORITY", "common").strip().lower() or "common",
            plaid_client_id=os.getenv("JARVIS_PLAID_CLIENT_ID", "").strip(),
            plaid_secret=os.getenv("JARVIS_PLAID_SECRET", "").strip(),
            plaid_env=os.getenv("JARVIS_PLAID_ENV", "sandbox").strip().lower() or "sandbox",
            plaid_country_codes=os.getenv("JARVIS_PLAID_COUNTRY_CODES", "US").strip() or "US",
            openviking_enabled=_bool_env("JARVIS_OPENVIKING_ENABLED", False),
            openviking_base_url=os.getenv("OPENVIKING_BASE_URL", "http://127.0.0.1:1933").rstrip("/"),
            openviking_api_key=os.getenv("OPENVIKING_API_KEY", "").strip(),
            openviking_account=os.getenv("OPENVIKING_ACCOUNT", "default").strip(),
            openviking_user=os.getenv("OPENVIKING_USER", "chris").strip(),
            openviking_agent_id=os.getenv("OPENVIKING_AGENT_ID", "jarvis").strip(),
            openviking_memory_uri_root=os.getenv(
                "JARVIS_OPENVIKING_MEMORY_URI_ROOT",
                "viking://user/chris/memories/",
            ).strip(),
            autonomous_workstreams_enabled=_bool_env("JARVIS_AUTONOMOUS_WORKSTREAMS_ENABLED", True),
            autonomous_workstream_lanes=_csv_env("JARVIS_AUTONOMOUS_WORKSTREAM_LANES", ("passive-income", "market-intelligence")),
            default_trust_owner_principal=os.getenv("JARVIS_DEFAULT_TRUST_OWNER_PRINCIPAL", "").strip().lower(),
        )

    def load_household(self) -> HouseholdProfile:
        payload = json.loads(self.household_config_path.read_text())
        users = {
            item["id"]: UserProfile(
                user_id=item["id"],
                display_name=item["displayName"],
                address_as=item["addressAs"],
                role=item["role"],
                permissions=item["permissions"],
                priorities=item.get("priorities", []),
            )
            for item in payload["users"]
        }
        rooms = {
            item["id"]: RoomProfile(
                room_id=item["id"],
                mode_bias=item["modeBias"],
            )
            for item in payload["rooms"]
        }
        return HouseholdProfile(
            household_name=payload["householdName"],
            location_label=payload["locationLabel"],
            quiet_start=payload["quietHours"]["start"],
            quiet_end=payload["quietHours"]["end"],
            users=users,
            rooms=rooms,
            modes=payload["modes"],
        )

    def load_snapshot(self) -> HouseholdSnapshot:
        payload = json.loads(self.household_snapshot_path.read_text())
        return HouseholdSnapshot(
            day_label=payload["dayLabel"],
            weather=payload["weather"],
            house_note=payload["houseNote"],
            body=SnapshotCard(**payload["cards"]["body"]),
            home=SnapshotCard(**payload["cards"]["home"]),
            mission=SnapshotCard(**payload["cards"]["mission"]),
            events=[FamilyEvent(**item) for item in payload["events"]],
            family_focus=payload["familyFocus"],
            watch_items=payload["watchItems"],
        )

    def load_voice_context(self) -> VoiceContextProfile:
        if not self.voice_context_path.exists():
            return VoiceContextProfile(wake_words=["jarvis"], satellites=[])
        payload = json.loads(self.voice_context_path.read_text())
        return VoiceContextProfile(
            wake_words=payload.get("wakeWords", ["jarvis"]),
            satellites=[
                VoiceSatelliteProfile(
                    satellite_id=item["id"],
                    device_name=item["deviceName"],
                    room=item["room"],
                    default_speaker=item.get("defaultSpeaker", ""),
                )
                for item in payload.get("satellites", [])
            ],
        )

    def load_json_profile(self, path: Path, default_payload: dict) -> dict:
        if not path.exists():
            return default_payload
        return json.loads(path.read_text())


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return default
    values = tuple(
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    )
    return values or default


def _optional_path(raw_value: str) -> Path | None:
    if not raw_value.strip():
        return None
    return Path(raw_value)


def _default_piper_binary(raw_value: str) -> str:
    if raw_value.strip():
        return raw_value.strip()
    sibling = Path(sys.executable).resolve().parent / "piper"
    if sibling.exists():
        return str(sibling)
    return "piper"


def _default_piper_model_path(raw_value: str) -> Path | None:
    explicit = _optional_path(raw_value)
    if explicit:
        return explicit
    bundled_root = Path.cwd() / "assets" / "piper" / "voices"
    if bundled_root.exists():
        models = sorted(bundled_root.rglob("*.onnx"))
        if models:
            return models[0]
    return None


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
