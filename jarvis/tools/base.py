"""Base types for JARVIS agent tools."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApprovalFlag(Enum):
    NONE = "none"         # auto-execute
    WARN = "warn"         # show diff/preview but auto-execute
    REQUIRED = "required" # must wait for user approval


@dataclass
class ToolResult:
    output: str
    error: bool = False
    approval_flag: ApprovalFlag = ApprovalFlag.NONE
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.output


@dataclass(slots=True)
class ToolInvocation:
    tool_name: str
    tool_input: dict[str, Any]
    tool_call_id: str = ""
    conversation_id: str = ""


@dataclass(slots=True)
class ToolPreflight:
    invocation: ToolInvocation
    approval_flag: ApprovalFlag = ApprovalFlag.NONE
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
