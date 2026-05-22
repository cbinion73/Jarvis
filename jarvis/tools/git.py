"""
JARVIS Tool: git
================
Git operations — status, diff, log, add, commit, push, or any custom git command.
Delegates execution to the bash tool so output handling is consistent.
"""
from __future__ import annotations

import shlex

from . import bash
from .base import ApprovalFlag, ToolResult

# ---------------------------------------------------------------------------
# Anthropic tool schema
# ---------------------------------------------------------------------------

DEFINITION: dict = {
    "name": "git",
    "description": (
        "Run git operations on the JARVIS repository: "
        "status, diff, log, add, commit, push, or any arbitrary git command. "
        "Commit and push require explicit user approval. "
        "The default working directory is /Users/chris/Desktop/CODE/JARVIS."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["status", "diff", "log", "add", "commit", "push", "custom"],
                "description": "The git operation to perform.",
            },
            "message": {
                "type": "string",
                "description": "Commit message (used with 'commit').",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of files/paths to stage (used with 'add'). "
                    "Defaults to ['.'] (everything)."
                ),
            },
            "command": {
                "type": "string",
                "description": (
                    "Git arguments for 'custom' operation, e.g. 'branch -a' or 'stash list'."
                ),
            },
            "working_dir": {
                "type": "string",
                "description": (
                    "Directory in which to run git. "
                    "Defaults to /Users/chris/Desktop/CODE/JARVIS."
                ),
            },
        },
        "required": ["operation"],
    },
}

_DEFAULT_WORKING_DIR = "/Users/chris/Desktop/CODE/JARVIS"


# ---------------------------------------------------------------------------
# Approval logic
# ---------------------------------------------------------------------------

def needs_approval(inputs: dict) -> ApprovalFlag:
    """Commit and push are consequential — require approval."""
    operation: str = inputs.get("operation", "")
    if operation in ("push", "commit"):
        return ApprovalFlag.REQUIRED
    return ApprovalFlag.NONE


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

async def run(
    operation: str,
    message: str = "",
    files: list[str] | None = None,
    command: str = "",
    working_dir: str = "",
) -> ToolResult:
    """Execute the requested git operation and return its output."""
    cwd = working_dir.strip() or _DEFAULT_WORKING_DIR

    match operation:
        case "status":
            git_cmd = "git status"

        case "diff":
            git_cmd = "git diff --stat && git diff"

        case "log":
            git_cmd = "git log --oneline -20"

        case "add":
            targets = files if files else ["."]
            # Shell-quote each file path in case of spaces
            quoted = " ".join(shlex.quote(f) for f in targets)
            git_cmd = f"git add {quoted}"

        case "commit":
            if not message:
                return ToolResult(
                    output="A commit message is required for the 'commit' operation.",
                    error=True,
                )
            # Single-quote the body so most characters are safe;
            # escape any single quotes inside the message.
            safe_msg = message.replace("'", "'\\''")
            git_cmd = (
                f"git add -A && git commit -m "
                f"$'{safe_msg}\\n\\nCo-Authored-By: JARVIS Agent <jarvis@local>'"
            )

        case "push":
            git_cmd = "git push"

        case "custom":
            if not command.strip():
                return ToolResult(
                    output="The 'command' parameter is required for 'custom' git operations.",
                    error=True,
                )
            git_cmd = f"git {command}"

        case _:
            return ToolResult(
                output=(
                    f"Unknown operation: '{operation}'. "
                    "Must be one of: status, diff, log, add, commit, push, custom."
                ),
                error=True,
            )

    # Delegate to bash.run for consistent output handling / timeout
    result = await bash.run(command=git_cmd, timeout=60, working_dir=cwd)

    # Enrich metadata
    result.metadata["git_operation"] = operation
    result.metadata["working_dir"] = cwd
    return result
