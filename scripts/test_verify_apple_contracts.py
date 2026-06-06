#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "JarvisApple" / "Tests" / "JarvisKitTests" / "Fixtures" / "apple_payload_fixture.json"


class FixtureHandler(BaseHTTPRequestHandler):
    fixture: dict[str, dict] = {}

    def do_GET(self) -> None:  # noqa: N802
        payload = self.fixture.get(self.path)
        if payload is None:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": f"missing fixture for {self.path}"}).encode("utf-8"))
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        payload = self.fixture.get(self.path)
        if payload is None:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": f"missing fixture for {self.path}"}).encode("utf-8"))
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> int:
    FixtureHandler.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        completed = subprocess.run(
            [sys.executable, "scripts/verify_apple_contracts.py", "--base-url", base_url, "--exercise-actions"],
            cwd=REPO_ROOT,
            check=False,
        )
        return completed.returncode
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
