from __future__ import annotations

from .config import AppConfig
from .integrations import (
    IntegrationStatus,
    check_google_workspace,
    check_home_assistant,
    check_home_profile,
    check_memory_profile,
    check_openclaw,
    check_perception_profile,
    check_workshop_adapter,
)


def collect_status(config: AppConfig) -> list[IntegrationStatus]:
    return [
        check_openclaw(config),
        check_google_workspace(config),
        check_home_assistant(config),
        check_home_profile(config),
        check_memory_profile(config),
        check_perception_profile(config),
        check_workshop_adapter(config),
    ]
