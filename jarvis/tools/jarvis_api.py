"""
JARVIS Tool: jarvis_api
=======================
Call any JARVIS internal REST API endpoint.
Useful for reading status, querying data, or triggering subsystems
without shelling out to curl.
"""
from __future__ import annotations

import json
import os

import httpx

from .base import ApprovalFlag, ToolResult

# ---------------------------------------------------------------------------
# Anthropic tool schema
# ---------------------------------------------------------------------------

DEFINITION: dict = {
    "name": "jarvis_api",
    "description": (
        "Call any JARVIS internal API endpoint. Use this to check status, fetch data, "
        "or trigger JARVIS subsystems (ideas, forge, approvals, etc.). "
        "The base URL is read from the JARVIS_BASE_URL environment variable "
        "(default: http://127.0.0.1:8787)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "description": "HTTP method to use.",
            },
            "path": {
                "type": "string",
                "description": (
                    "API path relative to the base URL, e.g. '/api/status' or '/api/ideas'."
                ),
            },
            "body": {
                "type": "object",
                "description": "JSON body for POST requests. Omit for GET.",
            },
        },
        "required": ["method", "path"],
    },
}


# ---------------------------------------------------------------------------
# Approval logic
# ---------------------------------------------------------------------------

def needs_approval(inputs: dict) -> ApprovalFlag:  # noqa: ARG001
    """JARVIS API calls never require explicit approval."""
    return ApprovalFlag.NONE


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "http://127.0.0.1:8787"
_TIMEOUT = 10.0


async def run(
    method: str,
    path: str,
    body: dict | None = None,
) -> ToolResult:
    """Call a JARVIS internal API endpoint and return the response."""
    base_url = os.environ.get("JARVIS_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
    full_url = base_url + "/" + path.lstrip("/")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            if method.upper() == "GET":
                resp = await client.get(full_url)
            elif method.upper() == "POST":
                resp = await client.post(full_url, json=body or {})
            else:
                return ToolResult(
                    output=f"Unsupported method: {method}. Must be GET or POST.",
                    error=True,
                )

            # Try to decode as JSON, fall back to raw text
            try:
                data = resp.json()
                formatted = json.dumps(data, indent=2, default=str)
            except Exception:  # noqa: BLE001
                formatted = resp.text or "(empty response body)"

            is_error = resp.status_code >= 400
            status_line = f"HTTP {resp.status_code} {method.upper()} {full_url}"

            return ToolResult(
                output=f"{status_line}\n\n{formatted}",
                error=is_error,
                metadata={
                    "status_code": resp.status_code,
                    "url": full_url,
                    "method": method.upper(),
                },
            )

    except httpx.ConnectError:
        return ToolResult(
            output=(
                f"Could not connect to JARVIS at {base_url}. "
                "Is the JARVIS server running? "
                "Set JARVIS_BASE_URL if running on a non-default address."
            ),
            error=True,
            metadata={"url": full_url},
        )
    except httpx.TimeoutException:
        return ToolResult(
            output=f"Request timed out after {_TIMEOUT}s: {method.upper()} {full_url}",
            error=True,
            metadata={"url": full_url},
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            output=f"Unexpected error calling JARVIS API: {exc}",
            error=True,
            metadata={"url": full_url},
        )
