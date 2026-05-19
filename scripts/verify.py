#!/usr/bin/env python3
"""JARVIS verification script — checks all major subsystem endpoints.

Usage:
    python scripts/verify.py
    python scripts/verify.py --base-url http://localhost:9000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS_ICON = f"{GREEN}✓{RESET}"
FAIL_ICON = f"{RED}✗{RESET}"
WARN_ICON = f"{YELLOW}⚠{RESET}"


def _label(status: str) -> str:
    if status == "PASS":
        return f"{GREEN}{BOLD}PASS{RESET}"
    if status == "FAIL":
        return f"{RED}{BOLD}FAIL{RESET}"
    return f"{YELLOW}{BOLD}WARN{RESET}"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, timeout: int = 10) -> tuple[int, dict[str, Any]]:
    """Return (status_code, parsed_body). On network error returns (0, {})."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read()
            return exc.code, json.loads(raw) if raw else {}
        except Exception:
            return exc.code, {}
    except Exception:
        return 0, {}


def _post(url: str, payload: dict[str, Any], timeout: int = 30) -> tuple[int, dict[str, Any]]:
    """POST JSON payload. Returns (status_code, parsed_body)."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read()
            return exc.code, json.loads(raw) if raw else {}
        except Exception:
            return exc.code, {}
    except Exception:
        return 0, {}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_health(base: str) -> tuple[str, list[str]]:
    """GET /health  (falls back to /api/status)."""
    lines: list[str] = []

    code, body = _get(f"{base}/health")
    if code == 0:
        # try fallback
        code, body = _get(f"{base}/api/status")
        endpoint = "/api/status"
    else:
        endpoint = "/health"

    if code == 0:
        lines.append(f"  {FAIL_ICON} Could not connect to server at {base}")
        return "FAIL", lines

    ok = body.get("ok", body.get("status") == "ok" or code < 300)
    icon = PASS_ICON if ok else FAIL_ICON
    lines.append(f"  {icon} {endpoint} → HTTP {code}")
    if "python" in body:
        lines.append(f"      python={body['python']}  service={body.get('service', '?')}")
    return ("PASS" if ok else "FAIL"), lines


def check_gateway_status(base: str) -> tuple[str, list[str]]:
    """GET /api/gateway/status"""
    lines: list[str] = []
    code, body = _get(f"{base}/api/gateway/status")

    if code == 0:
        lines.append(f"  {FAIL_ICON} No response from /api/gateway/status")
        return "FAIL", lines

    if code == 405:
        lines.append(f"  {FAIL_ICON} /api/gateway/status → HTTP 405 (Method Not Allowed — check route registration)")
        return "FAIL", lines

    if code == 503 or not body.get("available", True):
        lines.append(f"  {WARN_ICON} Gateway not initialised (HTTP {code})")
        if "error" in body:
            lines.append(f"      {body['error']}")
        return "WARN", lines

    ollama   = body.get("ollama_available", body.get("local_available", False))
    openai   = body.get("openai_available", body.get("cloud_available", False))
    fast_m   = body.get("fast_model",      body.get("default_model", "?"))
    reason_m = body.get("reasoning_model", body.get("smart_model",   "?"))

    ol_icon = PASS_ICON if ollama  else WARN_ICON
    oi_icon = PASS_ICON if openai  else WARN_ICON

    lines.append(f"  {PASS_ICON} /api/gateway/status → HTTP {code}")
    lines.append(f"      {ol_icon} Ollama available : {ollama}")
    lines.append(f"      {oi_icon} OpenAI available : {openai}")
    lines.append(f"      fast model       : {fast_m}")
    lines.append(f"      reasoning model  : {reason_m}")
    return "PASS", lines


def check_gateway_roundtrip(base: str) -> tuple[str, list[str]]:
    """POST /api/gateway/test"""
    lines: list[str] = []
    payload = {
        "message": "Good morning. What's on my calendar today?",
        "task_type": "agent_work",
    }
    t0 = time.time()
    code, body = _post(f"{base}/api/gateway/test", payload, timeout=60)
    elapsed_ms = int((time.time() - t0) * 1000)

    if code == 0:
        lines.append(f"  {FAIL_ICON} No response from /api/gateway/test")
        return "FAIL", lines

    if code == 503:
        lines.append(f"  {WARN_ICON} Gateway not available for roundtrip (HTTP 503)")
        return "WARN", lines

    if code == 405:
        lines.append(f"  {FAIL_ICON} /api/gateway/test → HTTP 405 (Method Not Allowed — POST route not registered)")
        return "FAIL", lines

    if code >= 400:
        lines.append(f"  {FAIL_ICON} /api/gateway/test → HTTP {code}")
        return "FAIL", lines

    # Extract fields — gateway may return them at top level or nested
    response_text = body.get("response", body.get("content", body.get("text", "")))
    model_used    = body.get("model_used",  body.get("model", "?"))
    latency_ms    = body.get("latency_ms",  body.get("elapsed_ms", elapsed_ms))
    confidence    = body.get("confidence",  body.get("score", "?"))
    escalated     = body.get("escalated",   body.get("routed_up", "?"))

    snippet = str(response_text)[:120].replace("\n", " ")
    lines.append(f"  {PASS_ICON} /api/gateway/test → HTTP {code}  ({latency_ms} ms)")
    lines.append(f"      model      : {model_used}")
    lines.append(f"      latency_ms : {latency_ms}")
    lines.append(f"      confidence : {confidence}")
    lines.append(f"      escalated  : {escalated}")
    lines.append(f"      response   : {snippet!r}")
    return "PASS", lines


def check_briefing(base: str) -> tuple[str, list[str]]:
    """GET /api/briefing — checks 5 expected zones."""
    EXPECTED_ZONES = ["focus", "urgent", "calendar", "tasks", "open_loops"]
    lines: list[str] = []
    code, body = _get(f"{base}/api/briefing")

    if code == 0:
        lines.append(f"  {FAIL_ICON} No response from /api/briefing")
        return "FAIL", lines

    if code >= 400:
        lines.append(f"  {FAIL_ICON} /api/briefing → HTTP {code}")
        return "FAIL", lines

    briefing = body.get("briefing", body)
    if not isinstance(briefing, dict):
        briefing = {}

    lines.append(f"  {PASS_ICON} /api/briefing → HTTP {code}")
    populated = 0
    for zone in EXPECTED_ZONES:
        val = briefing.get(zone)
        filled = bool(val) if val is not None else False
        icon = PASS_ICON if filled else WARN_ICON
        lines.append(f"      {icon} {zone:<15}: {'populated' if filled else 'empty/missing'}")
        if filled:
            populated += 1

    status = "PASS" if populated >= 3 else ("WARN" if populated >= 1 else "WARN")
    return status, lines


def check_voice_stack(base: str) -> tuple[str, list[str]]:
    """GET /api/voice/status"""
    lines: list[str] = []
    code, body = _get(f"{base}/api/voice/status")

    if code == 0:
        lines.append(f"  {FAIL_ICON} No response from /api/voice/status")
        return "FAIL", lines

    if code == 405:
        lines.append(f"  {FAIL_ICON} /api/voice/status → HTTP 405 (Method Not Allowed — check route registration)")
        return "FAIL", lines

    if "error" in body or code >= 500:
        lines.append(f"  {WARN_ICON} /api/voice/status → HTTP {code}  (pipeline not initialised)")
        if "error" in body:
            lines.append(f"      {body['error']}")
        return "WARN", lines

    tts = body.get("tts",     body.get("tts_provider",     body.get("synthesis_provider", "?")))
    stt = body.get("stt",     body.get("stt_provider",     body.get("transcription_provider", "?")))
    state = body.get("state", body.get("pipeline_state",   "?"))

    lines.append(f"  {PASS_ICON} /api/voice/status → HTTP {code}")
    lines.append(f"      TTS provider : {tts}")
    lines.append(f"      STT provider : {stt}")
    lines.append(f"      pipeline     : {state}")
    return "PASS", lines


def check_approvals(base: str) -> tuple[str, list[str]]:
    """GET /api/approvals/pending"""
    lines: list[str] = []
    code, body = _get(f"{base}/api/approvals/pending")

    if code == 0:
        lines.append(f"  {FAIL_ICON} No response from /api/approvals/pending")
        return "FAIL", lines

    if code == 405:
        lines.append(f"  {FAIL_ICON} /api/approvals/pending → HTTP 405 (Method Not Allowed — check route registration)")
        return "FAIL", lines

    if code >= 400:
        lines.append(f"  {FAIL_ICON} /api/approvals/pending → HTTP {code}")
        return "FAIL", lines

    pending = body.get("pending", [])
    count = len(pending) if isinstance(pending, list) else "?"

    if "error" in body:
        lines.append(f"  {WARN_ICON} /api/approvals/pending → HTTP {code}  ({body['error']})")
        return "WARN", lines

    lines.append(f"  {PASS_ICON} /api/approvals/pending → HTTP {code}")
    lines.append(f"      pending count : {count}")
    return "PASS", lines


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary(results: list[tuple[str, str]]) -> None:
    width = max(len(name) for name, _ in results) + 4
    sep = "+" + "-" * (width + 2) + "+" + "-" * 8 + "+"
    print()
    print(f"{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}  JARVIS Verification Summary{RESET}")
    print(sep)
    print(f"| {'Check':<{width}} | Status |")
    print(sep)
    for name, status in results:
        label = _label(status)
        # pad with spaces (label includes ANSI codes so visual width is 4)
        print(f"| {name:<{width}} | {label}   |")
    print(sep)

    total  = len(results)
    passes = sum(1 for _, s in results if s == "PASS")
    warns  = sum(1 for _, s in results if s == "WARN")
    fails  = sum(1 for _, s in results if s == "FAIL")
    print(f"\n  {PASS_ICON} {passes}/{total} passed   {WARN_ICON} {warns} warn   {FAIL_ICON} {fails} failed\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify JARVIS endpoints.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8787",
        help="Base URL of the JARVIS server (default: http://localhost:8787)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"\n{BOLD}{CYAN}JARVIS Endpoint Verification{RESET}  →  {base}\n")

    checks = [
        ("Server Health",      check_health),
        ("Gateway Status",     check_gateway_status),
        ("Gateway Roundtrip",  check_gateway_roundtrip),
        ("Briefing Zones",     check_briefing),
        ("Voice Stack",        check_voice_stack),
        ("Approvals Queue",    check_approvals),
    ]

    summary: list[tuple[str, str]] = []
    for name, fn in checks:
        print(f"{BOLD}{name}{RESET}")
        try:
            status, lines = fn(base)
        except Exception as exc:
            status = "FAIL"
            lines = [f"  {FAIL_ICON} Unexpected error: {exc}"]
        for line in lines:
            print(line)
        print()
        summary.append((name, status))

    print_summary(summary)

    # Exit 1 if any hard failures
    return 1 if any(s == "FAIL" for _, s in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
