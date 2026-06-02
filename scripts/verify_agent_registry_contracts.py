#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jarvis.agent_registry_contract import contract_paths, load_contract_bundle  # noqa: E402


def main() -> int:
    bundle = load_contract_bundle(validate=True)
    print(
        json.dumps(
            {
                "ok": True,
                "paths": contract_paths(),
                "summary": bundle.snapshot(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
