"""
jarvis/context_builder.py — Build rich project context for the agent
=====================================================================
Called at the start of each agent session to build a system prompt
addition describing the JARVIS codebase, connected projects, running
services, and recent git activity.
"""

import asyncio
from typing import NamedTuple

# ── Service definitions ────────────────────────────────────────────────────

class _Service(NamedTuple):
    port: int
    label: str


_SERVICES: list[_Service] = [
    _Service(8787, "JARVIS API"),
    _Service(8788, "JARVIS MCP"),
    _Service(3000, "Ghostwritr Next.js"),
    _Service(5432, "PostgreSQL"),
]

_JARVIS_ROOT    = "/Users/chris/Desktop/CODE/JARVIS"
_GHOSTWRITR_ROOT = "/Users/chris/Desktop/CODE/GHOSTWRITR"
_PORT_TIMEOUT   = 0.5  # seconds


# ── Port probe ─────────────────────────────────────────────────────────────

async def _is_port_open(host: str, port: int) -> bool:
    """Return True if a TCP connection to host:port succeeds within the timeout."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=_PORT_TIMEOUT,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
        return True
    except Exception:  # noqa: BLE001
        return False


# ── Git log helper ─────────────────────────────────────────────────────────

async def _git_log(repo_path: str, n: int) -> str:
    """Return the last n one-line git commits for the repo at repo_path."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", repo_path, "log", "--oneline", f"-{n}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=10.0
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return "(git log timed out)"

        if proc.returncode != 0:
            err = stderr_bytes.decode(errors="replace").strip()
            return f"(git error: {err})"

        output = stdout_bytes.decode(errors="replace").strip()
        return output if output else "(no commits found)"

    except FileNotFoundError:
        return "(git not found in PATH)"
    except Exception as exc:  # noqa: BLE001
        return f"(git log failed: {exc})"


# ── Main context builder ────────────────────────────────────────────────────

async def build_context() -> str:
    """
    Build and return a rich multi-line context string describing the JARVIS
    project state: running services, recent git history, file map, and
    agent capabilities.

    This function never raises — all errors are embedded in the returned string.
    """

    # Run all async probes concurrently
    service_checks, jarvis_log, ghostwritr_log = await asyncio.gather(
        asyncio.gather(*[
            _is_port_open("localhost", svc.port)
            for svc in _SERVICES
        ]),
        _git_log(_JARVIS_ROOT, 8),
        _git_log(_GHOSTWRITR_ROOT, 5),
    )

    # Format service status lines
    service_lines: list[str] = []
    for svc, is_running in zip(_SERVICES, service_checks):
        if is_running:
            service_lines.append(f"  OK  {svc.label} :{svc.port}")
        else:
            service_lines.append(f"  --  {svc.label} :{svc.port} (not running)")
    services_block = "\n".join(service_lines)

    # Format git logs with consistent indentation
    def _indent(text: str, prefix: str = "  ") -> str:
        return "\n".join(prefix + line for line in text.splitlines())

    context = f"""\
=== JARVIS PROJECT CONTEXT ===

ROOT: {_JARVIS_ROOT}
STACK: Python, FastAPI, Anthropic Claude, FastMCP, Tkinter UI

KEY FILES:
  jarvis/service.py              — FastAPI app, all HTTP routes (~7400 lines)
  jarvis/agent.py                — Agentic loop (the one currently running)
  jarvis/tools/                  — Agent tool modules (bash, files, web, git, jarvis_api, memory)
  jarvis/book_launch.py          — Book launch asset generators (Marquee, Bureau, Dispatch, etc.)
  jarvis/ghostwritr_mcp.py       — Ghostwritr MCP stdio server
  jarvis/ghostwritr_events.py    — DB poller for Ghostwritr stage changes
  jarvis/mcp_server.py           — JARVIS MCP tools exposed on port 8788
  jarvis/jarvis_theme_glass.py   — Full JARVIS UI (9000+ lines HTML/CSS/JS in Python)
  jarvis/llm_gateway.py          — LLM abstraction layer (5-tier escalation)
  jarvis/runtime.py              — JarvisRuntime central object
  jarvis/context_builder.py      — This file

CONNECTED PROJECTS:
  Ghostwritr: {_GHOSTWRITR_ROOT}
    Stack:    Next.js 15, Prisma, PostgreSQL, Anthropic SDK
    API:      http://localhost:3000
    DB:       postgresql://chris@localhost:5432/book_platform_builder
    Key files: src/app/api/, src/lib/jarvis/client.ts, prisma/schema.prisma

RUNNING SERVICES:
{services_block}

RECENT JARVIS COMMITS:
{_indent(jarvis_log)}

RECENT GHOSTWRITR COMMITS:
{_indent(ghostwritr_log)}

AGENT CAPABILITIES:
  bash        — Run shell commands (approval required for destructive ops)
  file_ops    — Read, write, edit files
  web         — Search DuckDuckGo or fetch URLs
  jarvis_api  — Call JARVIS internal API endpoints
  git         — Git status, diff, commit (approval required for commit/push)
  memory      — Read/write persistent facts across sessions

=== END CONTEXT ==="""

    return context
