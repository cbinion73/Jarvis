"""Base types for JARVIS agent tools."""
from dataclasses import dataclass, field
from enum import Enum


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
