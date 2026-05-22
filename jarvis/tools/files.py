"""
JARVIS Tool: file_ops
=====================
Read, write, surgically edit, or list files and directories on the filesystem.
"""
from __future__ import annotations

import os
import pathlib
from difflib import unified_diff

from .base import ApprovalFlag, ToolResult

# ---------------------------------------------------------------------------
# Anthropic tool schema
# ---------------------------------------------------------------------------

DEFINITION: dict = {
    "name": "file_ops",
    "description": (
        "Read, write, or surgically edit files on the filesystem. "
        "Also supports listing directory contents. "
        "Edits require an exact match of old_string; if the string appears "
        "multiple times you must make old_string longer/more specific."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "edit", "list_dir"],
                "description": "The file operation to perform.",
            },
            "path": {
                "type": "string",
                "description": "Absolute path to the file or directory.",
            },
            "content": {
                "type": "string",
                "description": "Full new content to write (used with 'write').",
            },
            "old_string": {
                "type": "string",
                "description": "Exact string to find and replace (used with 'edit').",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement string (used with 'edit').",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to return for 'read'. Default 500.",
                "default": 500,
            },
        },
        "required": ["operation", "path"],
    },
}


# ---------------------------------------------------------------------------
# Approval logic
# ---------------------------------------------------------------------------

def needs_approval(inputs: dict) -> ApprovalFlag:
    """Return the approval level required for this file operation."""
    operation: str = inputs.get("operation", "")
    path: str = inputs.get("path", "")

    if operation in ("read", "list_dir"):
        return ApprovalFlag.NONE

    # .env files are sensitive — require explicit approval
    filename = pathlib.Path(path).name
    if filename.startswith(".env") or filename.endswith(".env"):
        return ApprovalFlag.REQUIRED

    if operation in ("write", "edit"):
        return ApprovalFlag.WARN

    return ApprovalFlag.NONE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _number_lines(text: str, max_lines: int) -> str:
    """Return text with line numbers in cat -n style, limited to max_lines."""
    lines = text.splitlines(keepends=True)
    total = len(lines)
    truncated = lines[:max_lines]
    numbered = "".join(f"{i + 1:6}\t{line}" for i, line in enumerate(truncated))
    if total > max_lines:
        numbered += f"\n[... {total - max_lines} more lines not shown (max_lines={max_lines}) ...]"
    return numbered


def _context_diff(original: str, modified: str, path: str) -> str:
    """Produce a unified diff string between original and modified content."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff_lines = list(
        unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )
    return "".join(diff_lines) if diff_lines else "(no differences)"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

async def run(
    operation: str,
    path: str,
    content: str = "",
    old_string: str = "",
    new_string: str = "",
    max_lines: int = 500,
) -> ToolResult:
    """Perform the requested file operation and return a ToolResult."""

    p = pathlib.Path(path)

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    if operation == "read":
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            numbered = _number_lines(text, max_lines)
            return ToolResult(
                output=f"File: {path}\n\n{numbered}",
                error=False,
                metadata={"path": path, "size": p.stat().st_size},
            )
        except FileNotFoundError:
            return ToolResult(
                output=f"File not found: {path}",
                error=True,
            )
        except IsADirectoryError:
            return ToolResult(
                output=f"Path is a directory, not a file: {path}. Use 'list_dir' instead.",
                error=True,
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output=f"Error reading file: {exc}", error=True)

    # ------------------------------------------------------------------
    # LIST_DIR
    # ------------------------------------------------------------------
    if operation == "list_dir":
        try:
            if not p.exists():
                return ToolResult(output=f"Directory not found: {path}", error=True)
            if not p.is_dir():
                return ToolResult(output=f"Path is not a directory: {path}", error=True)

            entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            lines: list[str] = [f"Directory: {path}\n"]
            for entry in entries:
                try:
                    size = entry.stat().st_size if entry.is_file() else 0
                    kind = "file" if entry.is_file() else "dir "
                    size_str = f"{size:>10,} B" if entry.is_file() else "          -"
                    lines.append(f"  [{kind}]  {size_str}  {entry.name}")
                except OSError:
                    lines.append(f"  [????]            ?  {entry.name}")

            lines.append(f"\n{len(entries)} entries")
            return ToolResult(output="\n".join(lines), error=False)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output=f"Error listing directory: {exc}", error=True)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------
    if operation == "write":
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            byte_count = len(content.encode("utf-8"))
            return ToolResult(
                output=f"Written {byte_count:,} bytes to {path}",
                error=False,
                metadata={"path": path, "bytes": byte_count},
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output=f"Error writing file: {exc}", error=True)

    # ------------------------------------------------------------------
    # EDIT
    # ------------------------------------------------------------------
    if operation == "edit":
        try:
            if not p.exists():
                return ToolResult(output=f"File not found: {path}", error=True)

            original = p.read_text(encoding="utf-8", errors="replace")

            occurrences = original.count(old_string)
            if occurrences == 0:
                return ToolResult(
                    output=(
                        f"old_string not found in {path}.\n"
                        "Make sure the string matches exactly (including whitespace and newlines)."
                    ),
                    error=True,
                )
            if occurrences > 1:
                return ToolResult(
                    output=(
                        f"old_string found {occurrences} times in {path} — must be unique. "
                        "Expand old_string with more surrounding context to make it unique, "
                        "or use replace_all=true context if you intend to replace every occurrence."
                    ),
                    error=True,
                )

            modified = original.replace(old_string, new_string, 1)
            p.write_text(modified, encoding="utf-8")

            diff = _context_diff(original, modified, path)
            return ToolResult(
                output=f"Edit applied to {path}:\n\n{diff}",
                error=False,
                metadata={"path": path, "occurrences_replaced": 1},
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output=f"Error editing file: {exc}", error=True)

    # ------------------------------------------------------------------
    # Unknown operation
    # ------------------------------------------------------------------
    return ToolResult(
        output=f"Unknown operation: '{operation}'. Must be one of: read, write, edit, list_dir.",
        error=True,
    )
