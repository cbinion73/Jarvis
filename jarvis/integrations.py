from __future__ import annotations

import json
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

    # The real connect flow (jarvis.google_workspace) is per-account: each
    # connected account's token lives at data/google/{account_id}.json, not
    # at the single legacy config.google_token_path this check used to look
    # at exclusively. That mismatch meant a successfully connected account
    # still reported "not connected" here forever. Check both: the legacy
    # path (older single-account setups) and every registered google
    # account's real per-account token file.
    if config.google_token_path.exists():
        return IntegrationStatus(
            name="google-workspace",
            ok=True,
            detail=f"token loaded from {config.google_token_path}",
        )

    from .accounts import ACCOUNTS_PATH

    try:
        accounts = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        accounts = []

    token_dir = config.google_token_path.parent
    for account in accounts if isinstance(accounts, list) else []:
        if not isinstance(account, dict) or account.get("provider") != "google":
            continue
        account_id = str(account.get("account_id", "")).strip()
        if account_id and (token_dir / f"{account_id}.json").exists():
            label = str(account.get("label", "")).strip() or account_id
            return IntegrationStatus(
                name="google-workspace",
                ok=True,
                detail=f"{label} connected",
            )

    return IntegrationStatus(
        name="google-workspace",
        ok=False,
        detail="Google account is not connected yet",
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
