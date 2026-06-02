#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPO_ROOT / "household" / "jarvis_runtime_profile.example.json"
RUNBOOK_PATH = REPO_ROOT / "docs" / "operations-runbook.md"
POSTURE_DOC_PATH = REPO_ROOT / "docs" / "always-on-runtime-posture.md"

REQUIRED_PROFILE_KEYS = [
    "host",
    "runtime",
    "freshness",
    "durability",
    "push_path",
    "integrations",
    "devices",
]

REQUIRED_DOC_LINES = [
    "python3 -m jarvis runtime-posture",
    "python3 scripts/verify_runtime_posture.py",
    "/api/runtime/posture",
]


def _fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JARVIS always-on runtime posture artifacts.")
    parser.add_argument("--base-url", default="", help="Optional running JARVIS base URL, for example http://127.0.0.1:8787")
    args = parser.parse_args()

    failures: list[str] = []

    if not PROFILE_PATH.exists():
        failures.append(f"missing runtime profile: {PROFILE_PATH}")
    else:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        for key in REQUIRED_PROFILE_KEYS:
            if key not in profile:
                failures.append(f"runtime profile missing top-level key: {key}")
        runtime = profile.get("runtime") if isinstance(profile, dict) else {}
        services = runtime.get("services") if isinstance(runtime, dict) else []
        if not isinstance(services, list) or not services:
            failures.append("runtime profile must declare at least one service")

    for path in (RUNBOOK_PATH, POSTURE_DOC_PATH):
        if not path.exists():
            failures.append(f"missing doc: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        for line in REQUIRED_DOC_LINES:
            if line not in text:
                failures.append(f"{path.name} missing required line: {line}")

    if args.base_url:
        target = args.base_url.rstrip("/") + "/api/runtime/posture"
        try:
            payload = _fetch_json(target)
        except urllib.error.URLError as exc:
            failures.append(f"could not reach {target}: {exc}")
        else:
            if "state" not in payload:
                failures.append(f"{target} missing top-level state")
            if "launchd" not in payload:
                failures.append(f"{target} missing launchd section")
            if "integrations" not in payload:
                failures.append(f"{target} missing integrations section")

    if failures:
        print("runtime posture verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("runtime posture artifacts verified")
    if args.base_url:
        print(f"runtime posture endpoint verified at {args.base_url.rstrip('/')}/api/runtime/posture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
