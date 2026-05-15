#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / "data" / "system"
LOG_ROOT = REPO_ROOT / "data" / "logs"
STATE_PATH = DATA_ROOT / "guardian_state.json"
EVENTS_PATH = DATA_ROOT / "guardian_events.jsonl"
RUNTIME_HEALTH_URL = os.getenv("JARVIS_RUNTIME_HEALTH_URL", "http://127.0.0.1:8787/health").strip()
RUNTIME_LABEL = os.getenv("JARVIS_RUNTIME_LABEL", "com.jarvis.runtime").strip()
AUTONOMY_LABEL = os.getenv("JARVIS_AUTONOMY_LABEL", "com.jarvis.assistant-autonomy").strip()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dirs() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(payload: dict) -> None:
    ensure_dirs()
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def log_event(event_type: str, payload: dict) -> None:
    ensure_dirs()
    record = {"timestamp": now_iso(), "event_type": event_type, **payload}
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def run_command(args: list[str], *, timeout: int = 20) -> dict:
    try:
        completed = subprocess.run(
            args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "command": args, "returncode": None, "stdout": "", "stderr": str(exc).strip()}
    return {
        "ok": completed.returncode == 0,
        "command": args,
        "returncode": int(completed.returncode),
        "stdout": str(completed.stdout or "").strip(),
        "stderr": str(completed.stderr or "").strip(),
    }


def probe_runtime() -> dict:
    try:
        with urllib.request.urlopen(RUNTIME_HEALTH_URL, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"ok": True, "payload": payload, "detail": ""}
    except urllib.error.URLError as exc:
        return {"ok": False, "payload": {}, "detail": str(exc).strip()}
    except Exception as exc:
        return {"ok": False, "payload": {}, "detail": str(exc).strip()}


def compiled_python_report() -> dict:
    python_bin = str(REPO_ROOT / ".venv" / "bin" / "python")
    files = [
        REPO_ROOT / "jarvis" / "runtime.py",
        REPO_ROOT / "jarvis" / "service.py",
        REPO_ROOT / "jarvis" / "assistant_core.py",
        REPO_ROOT / "jarvis" / "voice_ui.py",
        REPO_ROOT / "jarvis" / "self_improvement.py",
        REPO_ROOT / "jarvis" / "main.py",
    ]
    args = [python_bin, "-m", "py_compile", *[str(path) for path in files if path.exists()]]
    result = run_command(args, timeout=90)
    result["files"] = [str(path.relative_to(REPO_ROOT)) for path in files if path.exists()]
    return result


def launchctl_kickstart(label: str) -> dict:
    if not label:
        return {"ok": False, "label": "", "detail": "Missing launchd label."}
    target = f"gui/{os.getuid()}/{label}"
    result = run_command(["launchctl", "kickstart", "-k", target], timeout=20)
    return {"ok": bool(result.get("ok")), "label": label, "detail": str(result.get("stderr") or result.get("stdout") or "").strip()}


def guardian_snapshot() -> dict:
    runtime_probe = probe_runtime()
    compile_report = compiled_python_report()
    state = load_state()
    previous_failures = int(state.get("consecutive_runtime_failures", 0) or 0)
    failures = 0 if runtime_probe.get("ok") else previous_failures + 1
    snapshot = {
        "generated_at": now_iso(),
        "guardian": {
            "label": "com.jarvis.guardian",
            "repo_root": str(REPO_ROOT),
            "python": sys.executable,
        },
        "runtime_health_url": RUNTIME_HEALTH_URL,
        "runtime": runtime_probe,
        "compile": compile_report,
        "consecutive_runtime_failures": failures,
        "services": {
            "runtime_label": RUNTIME_LABEL,
            "autonomy_label": AUTONOMY_LABEL,
        },
        "last_recovery": state.get("last_recovery", {}),
    }
    return snapshot


def run_guardian_cycle(*, allow_restarts: bool = True) -> dict:
    snapshot = guardian_snapshot()
    recovery_actions: list[dict] = []
    should_restart = allow_restarts and (
        not snapshot.get("runtime", {}).get("ok")
        or not snapshot.get("compile", {}).get("ok")
    )
    if should_restart:
        if RUNTIME_LABEL:
            recovery_actions.append(launchctl_kickstart(RUNTIME_LABEL))
        if AUTONOMY_LABEL:
            recovery_actions.append(launchctl_kickstart(AUTONOMY_LABEL))
        snapshot["last_recovery"] = {
            "triggered_at": now_iso(),
            "actions": recovery_actions,
            "reason": "runtime-unhealthy" if not snapshot.get("runtime", {}).get("ok") else "compile-regression",
        }
        log_event("guardian-recovery", snapshot["last_recovery"])
    save_state(snapshot)
    log_event(
        "guardian-cycle",
        {
            "runtime_ok": bool(snapshot.get("runtime", {}).get("ok")),
            "compile_ok": bool(snapshot.get("compile", {}).get("ok")),
            "consecutive_runtime_failures": int(snapshot.get("consecutive_runtime_failures", 0) or 0),
            "recovery_actions": recovery_actions,
        },
    )
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal guardian for JARVIS runtime recovery.")
    parser.add_argument("--interval-seconds", type=int, default=45)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    if args.once:
        print(json.dumps(run_guardian_cycle(allow_restarts=not args.no_restart), indent=2))
        return 0

    interval = max(15, int(args.interval_seconds))
    while True:
        print(json.dumps(run_guardian_cycle(allow_restarts=not args.no_restart)), flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
