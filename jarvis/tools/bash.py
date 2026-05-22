"""
JARVIS Tool: bash
=================
Execute shell commands with timeout, working directory control,
and approval gating for destructive operations.
"""
from __future__ import annotations

import asyncio

from .base import ApprovalFlag, ToolResult

# ---------------------------------------------------------------------------
# Anthropic tool schema
# ---------------------------------------------------------------------------

DEFINITION: dict = {
    "name": "bash",
    "description": (
        "Execute a shell command and return its output (stdout + stderr combined). "
        "Use for running scripts, inspecting files, invoking CLI tools, or any "
        "system-level operation. Destructive commands require user approval; "
        "package installs show a warning before executing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum seconds to wait before killing the process. Default 30.",
                "default": 30,
            },
            "working_dir": {
                "type": "string",
                "description": "Directory to run the command in. Defaults to the current working directory.",
            },
        },
        "required": ["command"],
    },
}

# ---------------------------------------------------------------------------
# Pattern sets for approval gating
# ---------------------------------------------------------------------------

_DESTRUCTIVE_PATTERNS: tuple[str, ...] = (
    "rm ",
    "rmdir",
    "kill ",
    "pkill",
    "DROP ",
    "TRUNCATE ",
    "DELETE FROM",
    "format ",
    "mkfs",
    "dd if=",
)

_WARN_PATTERNS: tuple[str, ...] = (
    "pip install",
    "npm install",
    "brew install",
)


# ---------------------------------------------------------------------------
# Approval logic
# ---------------------------------------------------------------------------

def needs_approval(inputs: dict) -> ApprovalFlag:
    """Return the approval level required to execute this command."""
    command: str = inputs.get("command", "")
    for pattern in _DESTRUCTIVE_PATTERNS:
        if pattern in command:
            return ApprovalFlag.REQUIRED
    for pattern in _WARN_PATTERNS:
        if pattern in command:
            return ApprovalFlag.WARN
    return ApprovalFlag.NONE


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

_OUTPUT_LIMIT = 8_000
_TRUNCATION_NOTE = "\n\n[output truncated — showing first 8 000 chars]"


async def run(
    command: str,
    timeout: int = 30,
    working_dir: str | None = None,
) -> ToolResult:
    """Execute *command* in a subprocess and return the combined output."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir or None,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return ToolResult(
                output=f"Command timed out after {timeout} seconds: {command}",
                error=True,
                approval_flag=ApprovalFlag.NONE,
            )

        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")

        parts = [p for p in (stdout, stderr) if p.strip()]
        combined = "\n".join(parts) if parts else ""

        truncated = False
        if len(combined) > _OUTPUT_LIMIT:
            combined = combined[:_OUTPUT_LIMIT] + _TRUNCATION_NOTE
            truncated = True

        is_error = proc.returncode != 0

        return ToolResult(
            output=combined or "(no output)",
            error=is_error,
            approval_flag=ApprovalFlag.NONE,
            metadata={
                "returncode": proc.returncode,
                "truncated": truncated,
                "command": command,
            },
        )

    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            output=f"Failed to execute command: {exc}",
            error=True,
            approval_flag=ApprovalFlag.NONE,
            metadata={"command": command},
        )
