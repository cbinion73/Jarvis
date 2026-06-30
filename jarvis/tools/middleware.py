from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

from ..audit import AuditLog
from . import TOOL_REGISTRY
from .base import ApprovalFlag, ToolInvocation, ToolPreflight, ToolResult


@dataclass(slots=True)
class ToolExecutionOutcome:
    invocation: ToolInvocation
    preflight: ToolPreflight
    result: ToolResult


_DEFAULT_AUDIT_SINK: AuditLog | None = None


def _resolve_tool_registry(tool_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    return tool_registry or TOOL_REGISTRY


def _default_audit_sink() -> AuditLog:
    global _DEFAULT_AUDIT_SINK
    if _DEFAULT_AUDIT_SINK is None:
        root = Path(os.environ.get("JARVIS_TOOL_AUDIT_ROOT", "data/logs"))
        _DEFAULT_AUDIT_SINK = AuditLog(root)
    return _DEFAULT_AUDIT_SINK


def _classify_sandbox(tool_name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
    if tool_name == "bash":
        return "system.shell", True
    if tool_name == "git":
        return "repo.git", True
    if tool_name == "file_ops":
        operation = str(tool_input.get("operation", "")).strip().lower()
        if operation in {"read", "list_dir"}:
            return "filesystem.read", False
        return "filesystem.mutation", True
    if tool_name == "web":
        operation = str(tool_input.get("operation", "")).strip().lower()
        return ("network.fetch" if operation == "fetch" else "network.search"), False
    if tool_name == "jarvis_api":
        method = str(tool_input.get("method", "")).strip().upper()
        return "internal.api.mutation" if method == "POST" else "internal.api.read", method == "POST"
    if tool_name == "memory":
        return "memory.store", False
    return "general.tool", False


def _emit_audit_event(
    entry_type: str,
    payload: dict[str, Any],
    *,
    audit_sink: AuditLog | None = None,
) -> None:
    sink = audit_sink or _default_audit_sink()
    try:
        sink.log_event(entry_type, payload)
    except Exception:
        return


def resolve_tool_module(
    tool_name: str,
    *,
    tool_registry: dict[str, Any] | None = None,
) -> Any | None:
    registry = _resolve_tool_registry(tool_registry)
    return registry.get(tool_name)


def build_tool_invocation(
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
    *,
    tool_call_id: str = "",
    conversation_id: str = "",
) -> ToolInvocation:
    return ToolInvocation(
        tool_name=tool_name,
        tool_input=dict(tool_input or {}),
        tool_call_id=tool_call_id,
        conversation_id=conversation_id,
    )


def preflight_tool_invocation(
    invocation: ToolInvocation,
    *,
    tool_registry: dict[str, Any] | None = None,
    audit_sink: AuditLog | None = None,
) -> ToolPreflight:
    registry = _resolve_tool_registry(tool_registry)
    tool_module = registry.get(invocation.tool_name)
    sandbox_class, sandbox_recommended = _classify_sandbox(invocation.tool_name, invocation.tool_input)
    metadata = {
        "tool_name": invocation.tool_name,
        "input_keys": sorted(invocation.tool_input.keys()),
        "tool_call_id": invocation.tool_call_id,
        "conversation_id": invocation.conversation_id,
        "sandbox_class": sandbox_class,
        "sandbox_recommended": sandbox_recommended,
    }

    if tool_module is None:
        preflight = ToolPreflight(
            invocation=invocation,
            approval_flag=ApprovalFlag.NONE,
            warnings=[f"Unknown tool: '{invocation.tool_name}'."],
            metadata={**metadata, "tool_known": False},
        )
        _emit_audit_event(
            "tool-preflight",
            {
                "tool_name": invocation.tool_name,
                "tool_call_id": invocation.tool_call_id,
                "conversation_id": invocation.conversation_id,
                "approval_flag": preflight.approval_flag.value,
                "sandbox_class": sandbox_class,
                "sandbox_recommended": sandbox_recommended,
                "tool_known": False,
                "warnings": list(preflight.warnings),
            },
            audit_sink=audit_sink,
        )
        return preflight

    metadata["tool_known"] = True
    definition = dict(getattr(tool_module, "DEFINITION", {}) or {})
    metadata["tool_description"] = str(definition.get("description", "")).strip()

    approval_flag = ApprovalFlag.NONE
    needs_approval = getattr(tool_module, "needs_approval", None)
    if callable(needs_approval):
        try:
            approval_flag = needs_approval(dict(invocation.tool_input))
        except Exception as exc:  # noqa: BLE001
            return ToolPreflight(
                invocation=invocation,
                approval_flag=ApprovalFlag.NONE,
                warnings=[f"Approval preflight failed for '{invocation.tool_name}': {type(exc).__name__}: {exc}"],
                metadata={**metadata, "approval_preflight_error": type(exc).__name__},
            )

    metadata.update(
        {
            "approval_flag": approval_flag.value,
            "approval_required": approval_flag == ApprovalFlag.REQUIRED,
            "warning_only": approval_flag == ApprovalFlag.WARN,
        }
    )

    preflight = ToolPreflight(
        invocation=invocation,
        approval_flag=approval_flag,
        metadata=metadata,
    )
    _emit_audit_event(
        "tool-preflight",
        {
            "tool_name": invocation.tool_name,
            "tool_call_id": invocation.tool_call_id,
            "conversation_id": invocation.conversation_id,
            "approval_flag": preflight.approval_flag.value,
            "sandbox_class": sandbox_class,
            "sandbox_recommended": sandbox_recommended,
            "tool_known": True,
            "warnings": list(preflight.warnings),
        },
        audit_sink=audit_sink,
    )
    return preflight


def preflight_tool_call(
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
    *,
    tool_call_id: str = "",
    conversation_id: str = "",
    tool_registry: dict[str, Any] | None = None,
    audit_sink: AuditLog | None = None,
) -> ToolPreflight:
    invocation = build_tool_invocation(
        tool_name,
        tool_input,
        tool_call_id=tool_call_id,
        conversation_id=conversation_id,
    )
    return preflight_tool_invocation(invocation, tool_registry=tool_registry, audit_sink=audit_sink)


async def execute_tool_invocation(
    invocation: ToolInvocation,
    *,
    tool_registry: dict[str, Any] | None = None,
    preflight: ToolPreflight | None = None,
    audit_sink: AuditLog | None = None,
) -> ToolExecutionOutcome:
    registry = _resolve_tool_registry(tool_registry)
    tool_module = registry.get(invocation.tool_name)
    active_preflight = preflight or preflight_tool_invocation(invocation, tool_registry=registry, audit_sink=audit_sink)

    if tool_module is None:
        result = ToolResult(
            output=f"Unknown tool: '{invocation.tool_name}'. Available: {list(registry.keys())}",
            error=True,
            metadata=dict(active_preflight.metadata),
        )
        outcome = ToolExecutionOutcome(invocation=invocation, preflight=active_preflight, result=result)
        _emit_audit_event(
            "tool-execution",
            {
                "tool_name": invocation.tool_name,
                "tool_call_id": invocation.tool_call_id,
                "conversation_id": invocation.conversation_id,
                "approval_flag": active_preflight.approval_flag.value,
                "sandbox_class": active_preflight.metadata.get("sandbox_class", ""),
                "sandbox_recommended": bool(active_preflight.metadata.get("sandbox_recommended", False)),
                "status": "error",
                "error": True,
            },
            audit_sink=audit_sink,
        )
        return outcome

    try:
        result = await tool_module.run(**invocation.tool_input)
    except Exception as exc:  # noqa: BLE001
        result = ToolResult(
            output=f"Tool '{invocation.tool_name}' raised {type(exc).__name__}: {exc}",
            error=True,
        )

    merged_metadata = dict(active_preflight.metadata)
    merged_metadata.update(dict(result.metadata))
    result.metadata = merged_metadata
    outcome = ToolExecutionOutcome(invocation=invocation, preflight=active_preflight, result=result)
    _emit_audit_event(
        "tool-execution",
        {
            "tool_name": invocation.tool_name,
            "tool_call_id": invocation.tool_call_id,
            "conversation_id": invocation.conversation_id,
            "approval_flag": active_preflight.approval_flag.value,
            "sandbox_class": active_preflight.metadata.get("sandbox_class", ""),
            "sandbox_recommended": bool(active_preflight.metadata.get("sandbox_recommended", False)),
            "status": "error" if result.error else "ok",
            "error": bool(result.error),
            "result_metadata": dict(result.metadata),
        },
        audit_sink=audit_sink,
    )
    return outcome


async def execute_tool_call(
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
    *,
    tool_call_id: str = "",
    conversation_id: str = "",
    tool_registry: dict[str, Any] | None = None,
    preflight: ToolPreflight | None = None,
    audit_sink: AuditLog | None = None,
) -> ToolExecutionOutcome:
    invocation = build_tool_invocation(
        tool_name,
        tool_input,
        tool_call_id=tool_call_id,
        conversation_id=conversation_id,
    )
    return await execute_tool_invocation(
        invocation,
        tool_registry=tool_registry,
        preflight=preflight,
        audit_sink=audit_sink,
    )
