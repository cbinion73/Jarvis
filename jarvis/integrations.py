from __future__ import annotations

from dataclasses import dataclass
from urllib import error, request

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


def check_home_assistant(config: AppConfig) -> IntegrationStatus:
    if not config.home_assistant_url or not config.home_assistant_token:
        return IntegrationStatus(
            name="home-assistant",
            ok=False,
            detail="HOME_ASSISTANT_URL or HOME_ASSISTANT_TOKEN is missing",
        )

    try:
        req = request.Request(
            f"{config.home_assistant_url}/api/",
            headers={"Authorization": f"Bearer {config.home_assistant_token}"},
        )
        with request.urlopen(req, timeout=5) as response:
            status_code = response.status
    except error.URLError as exc:
        return IntegrationStatus(
            name="home-assistant",
            ok=False,
            detail=str(exc),
        )

    return IntegrationStatus(
        name="home-assistant",
        ok=200 <= status_code < 300,
        detail=f"http {status_code}",
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
