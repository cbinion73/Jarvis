#!/usr/bin/env python3
"""
Fetch live /api/apple payloads and validate they decode through JarvisKit.

Usage examples:

  python3 scripts/verify_apple_contracts.py --base-url http://127.0.0.1:8787

  python3 scripts/verify_apple_contracts.py \
    --ssh-host root@5.78.212.15 \
    --container jarvis-family-jarvis-1
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
JARVIS_APPLE_DIR = REPO_ROOT / "JarvisApple"

ENDPOINTS: list[tuple[str, str]] = [
    ("/api/apple/status", "/api/apple/status"),
    ("/api/apple/app-state", "/api/apple/app-state"),
    ("/api/apple/weather", "/api/apple/weather"),
    ("/api/apple/navigation/locations", "/api/apple/navigation/locations"),
    (
        "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
        "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
    ),
    ("/api/apple/briefing?actor=chris", "/api/apple/briefing?actor=chris"),
    ("/api/apple/needs", "/api/apple/needs"),
    ("/api/apple/health/summary?actor=chris", "/api/apple/health/summary?actor=chris"),
    ("/api/apple/home/state", "/api/apple/home/state"),
    ("/api/apple/catalyst", "/api/apple/catalyst"),
    ("/api/apple/chronicle", "/api/apple/chronicle"),
    ("/api/apple/faith?actor=chris", "/api/apple/faith?actor=chris"),
    ("/api/apple/publishing", "/api/apple/publishing"),
    ("/api/apple/huddle", "/api/apple/huddle"),
    ("/api/apple/forge", "/api/apple/forge"),
]


def fetch_http(base_url: str, path: str) -> dict:
    with urlopen(f"{base_url.rstrip('/')}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_ssh(ssh_host: str, container: str, path: str, base_url: str) -> dict:
    full_url = f"{base_url.rstrip('/')}{path}"
    python_snippet = (
        "import json, sys, urllib.request; "
        "print(json.dumps(json.loads(urllib.request.urlopen(sys.argv[1]).read().decode('utf-8'))))"
    )
    remote = (
        f"docker exec {shlex.quote(container)} "
        f"python3 -c {shlex.quote(python_snippet)} {shlex.quote(full_url)}"
    )
    output = subprocess.check_output(["ssh", ssh_host, remote], text=True)
    return json.loads(output)


def fetch_with_retry(*, use_ssh: bool, path: str, base_url: str, ssh_host: str | None, container: str, attempts: int = 15, delay_s: float = 2.0) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if use_ssh:
                return fetch_ssh(ssh_host or "", container, path, base_url)
            return fetch_http(base_url, path)
        except Exception as exc:  # pragma: no cover - exercised in live use
            last_exc = exc
            if attempt == attempts:
                break
            time.sleep(delay_s)
    raise last_exc or RuntimeError(f"failed fetching {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--ssh-host", help="Optional SSH host for remote container probing.")
    parser.add_argument("--container", default="jarvis-family-jarvis-1")
    parser.add_argument("--keep-fixture", action="store_true")
    args = parser.parse_args()

    use_ssh = bool(args.ssh_host)

    payloads: dict[str, dict] = {}
    for key, path in ENDPOINTS:
        try:
            payloads[key] = fetch_with_retry(
                use_ssh=use_ssh,
                path=path,
                base_url=args.base_url,
                ssh_host=args.ssh_host,
                container=args.container,
            )
        except Exception as exc:  # pragma: no cover - exercised in live use
            print(f"failed fetching {path}: {exc}", file=sys.stderr)
            return 1

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        prefix="jarvis-apple-payloads-",
        delete=False,
    ) as fh:
        json.dump(payloads, fh)
        fixture_path = fh.name

    env = dict(os.environ)
    env["JARVIS_APPLE_PAYLOAD_FIXTURE"] = fixture_path
    try:
        subprocess.run(
            ["swift", "test"],
            cwd=JARVIS_APPLE_DIR,
            env=env,
            check=True,
        )
        print(f"apple contract decode passed using fixture {fixture_path}")
        return 0
    finally:
        if not args.keep_fixture:
            try:
                Path(fixture_path).unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
