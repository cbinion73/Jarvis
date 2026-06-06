#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "## Backend Contract",
    "## Web Behavior",
    "## Phone Surface",
    "## Intentional Permission Flow",
    "## Device Verification",
    "## Rollout Notes",
]

REQUIRED_LINES = [
    "python3 scripts/verify_live_rollout_checklist.py",
    "python3 scripts/test_verify_apple_contracts.py",
    "swift test --package-path JarvisApple",
    "- Feature:",
    "- Branch:",
    "- Server / environment:",
    "- Proof artifacts:",
    "- Follow-up risks:",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 scripts/verify_live_rollout_checklist.py <markdown-file>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"missing checklist file: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")

    missing = [section for section in REQUIRED_SECTIONS if section not in text]
    missing += [line for line in REQUIRED_LINES if line not in text]

    if missing:
        print("checklist verification failed; missing required content:", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        return 1

    print(f"rollout checklist verified: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
