from __future__ import annotations

from .config import AppConfig
from .integrations import (
    IntegrationStatus,
    check_google_workspace,
    check_home_profile,
    check_memory_profile,
    check_openai_api,
    check_openclaw,
    check_perception_profile,
    check_workshop_adapter,
)

# Home Assistant and OpenViking are not part of Chris's setup (2026-07-06 /
# 2026-07-08, his call) — their health checks were removed entirely so they
# can never resurface as "critical" repair items. OpenViking would need a
# Rust toolchain install and a from-source build of a third-party project
# that was never actually running here; not worth the risk for what it adds.


def collect_status(config: AppConfig) -> list[IntegrationStatus]:
    return [
        check_openai_api(config),
        check_openclaw(config),
        check_google_workspace(config),
        check_home_profile(config),
        check_memory_profile(config),
        check_perception_profile(config),
        check_workshop_adapter(config),
    ]
