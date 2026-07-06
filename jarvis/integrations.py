from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig


@dataclass(slots=True)
class IntegrationStatus:
    name: str
    ok: bool
    detail: str


def check_openclaw(config: AppConfig) -> IntegrationStatus:
    return IntegrationStatus(
        name="openclaw",
        ok=bool(config.openclaw_gateway_url),
        detail=f"configured gateway {config.openclaw_gateway_url}",
    )


def check_home_profile(config: AppConfig) -> IntegrationStatus:
    if not config.home_profile_path.exists():
        return IntegrationStatus(
            name="home-profile",
            ok=False,
            detail="Home automation profile is missing",
        )
    return IntegrationStatus(
        name="home-profile",
        ok=True,
        detail=f"loaded profile {config.home_profile_path}",
    )


def check_perception_profile(config: AppConfig) -> IntegrationStatus:
    if not config.perception_profile_path.exists():
        return IntegrationStatus(
            name="perception-profile",
            ok=False,
            detail="Perception profile is missing",
        )
    return IntegrationStatus(
        name="perception-profile",
        ok=True,
        detail=f"loaded profile {config.perception_profile_path}",
    )


def check_memory_profile(config: AppConfig) -> IntegrationStatus:
    if not config.memory_profile_path.exists():
        return IntegrationStatus(
            name="memory-profile",
            ok=False,
            detail="Memory profile is missing",
        )
    return IntegrationStatus(
        name="memory-profile",
        ok=True,
        detail=f"loaded profile {config.memory_profile_path}",
    )


def check_google_workspace(config: AppConfig) -> IntegrationStatus:
    if not config.google_client_secret_path.exists():
        return IntegrationStatus(
            name="google-workspace",
            ok=False,
            detail="Google client secret is missing",
        )
    if not config.google_token_path.exists():
        return IntegrationStatus(
            name="google-workspace",
            ok=False,
            detail="Google account is not connected yet",
        )
    return IntegrationStatus(
        name="google-workspace",
        ok=True,
        detail=f"token loaded from {config.google_token_path}",
    )


def check_workshop_adapter(config: AppConfig) -> IntegrationStatus:
    if not config.workshop_profile_path.exists():
        return IntegrationStatus(
            name="workshop-adapter",
            ok=False,
            detail="Workshop profile is missing",
        )
    return IntegrationStatus(
        name="workshop-adapter",
        ok=True,
        detail=f"loaded profile {config.workshop_profile_path}",
    )


def check_openai_api(config: AppConfig) -> IntegrationStatus:
    if not config.openai_api_key:
        return IntegrationStatus(
            name="openai-api",
            ok=False,
            detail="OPENAI_API_KEY is missing",
        )
    return IntegrationStatus(
        name="openai-api",
        ok=True,
        detail="OpenAI API key is configured",
    )
