from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.audit import AuditLog
from jarvis.tools.base import ApprovalFlag, ToolInvocation, ToolResult
from jarvis.tools.middleware import (
    build_tool_invocation,
    execute_tool_call,
    preflight_tool_call,
    preflight_tool_invocation,
)


def _make_dummy_tool(*, approval_flag: ApprovalFlag = ApprovalFlag.NONE) -> SimpleNamespace:
    async def run(message: str) -> ToolResult:
        return ToolResult(output=f"ran:{message}", metadata={"runner": "dummy"})

    def needs_approval(inputs: dict) -> ApprovalFlag:  # noqa: ARG001
        return approval_flag

    return SimpleNamespace(
        DEFINITION={
            "name": "dummy_tool",
            "description": "Dummy tool used for middleware tests.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
        },
        run=run,
        needs_approval=needs_approval,
    )


class ToolMiddlewareTests(unittest.TestCase):
    def test_preflight_marks_warning_only_tools(self) -> None:
        registry = {"dummy_tool": _make_dummy_tool(approval_flag=ApprovalFlag.WARN)}

        preflight = preflight_tool_call("dummy_tool", {"message": "hello"}, tool_registry=registry)

        self.assertEqual(preflight.approval_flag, ApprovalFlag.WARN)
        self.assertTrue(preflight.metadata["warning_only"])
        self.assertFalse(preflight.metadata["approval_required"])
        self.assertEqual(preflight.metadata["tool_name"], "dummy_tool")

    def test_preflight_tracks_unknown_tools_without_crashing(self) -> None:
        preflight = preflight_tool_call("missing_tool", {"message": "hello"}, tool_registry={})

        self.assertEqual(preflight.approval_flag, ApprovalFlag.NONE)
        self.assertFalse(preflight.metadata["tool_known"])
        self.assertTrue(preflight.warnings)

    def test_execute_tool_call_merges_preflight_metadata_into_result(self) -> None:
        registry = {"dummy_tool": _make_dummy_tool(approval_flag=ApprovalFlag.WARN)}

        outcome = asyncio.run(
            execute_tool_call(
                "dummy_tool",
                {"message": "hello"},
                tool_call_id="call-1",
                conversation_id="conv-1",
                tool_registry=registry,
            )
        )

        self.assertEqual(outcome.result.output, "ran:hello")
        self.assertFalse(outcome.result.error)
        self.assertEqual(outcome.result.metadata["tool_name"], "dummy_tool")
        self.assertEqual(outcome.result.metadata["tool_call_id"], "call-1")
        self.assertEqual(outcome.result.metadata["conversation_id"], "conv-1")
        self.assertEqual(outcome.result.metadata["approval_flag"], "warn")
        self.assertEqual(outcome.result.metadata["runner"], "dummy")

    def test_execute_tool_call_returns_unknown_tool_error_result(self) -> None:
        outcome = asyncio.run(execute_tool_call("missing_tool", {"message": "hello"}, tool_registry={}))

        self.assertTrue(outcome.result.error)
        self.assertIn("Unknown tool", outcome.result.output)

    def test_invocation_builder_and_preflight_work_together(self) -> None:
        registry = {"dummy_tool": _make_dummy_tool(approval_flag=ApprovalFlag.REQUIRED)}
        invocation = build_tool_invocation(
            "dummy_tool",
            {"message": "hello"},
            tool_call_id="call-2",
            conversation_id="conv-2",
        )

        preflight = preflight_tool_invocation(invocation, tool_registry=registry)

        self.assertIsInstance(invocation, ToolInvocation)
        self.assertEqual(preflight.approval_flag, ApprovalFlag.REQUIRED)
        self.assertTrue(preflight.metadata["approval_required"])

    def test_preflight_adds_sandbox_metadata(self) -> None:
        registry = {"dummy_tool": _make_dummy_tool()}

        preflight = preflight_tool_call("dummy_tool", {"message": "hello"}, tool_registry=registry)

        self.assertEqual(preflight.metadata["sandbox_class"], "general.tool")
        self.assertFalse(preflight.metadata["sandbox_recommended"])

    def test_middleware_writes_preflight_and_execution_audit_events(self) -> None:
        registry = {"dummy_tool": _make_dummy_tool(approval_flag=ApprovalFlag.WARN)}
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditLog(Path(tmpdir))

            preflight = preflight_tool_call(
                "dummy_tool",
                {"message": "hello"},
                tool_registry=registry,
                audit_sink=audit,
            )
            outcome = asyncio.run(
                execute_tool_call(
                    "dummy_tool",
                    {"message": "hello"},
                    tool_registry=registry,
                    preflight=preflight,
                    audit_sink=audit,
                )
            )

            events = audit.list_recent(limit=4)
            event_types = [item.get("entry_type") for item in events]

            self.assertFalse(outcome.result.error)
            self.assertIn("tool-preflight", event_types)
            self.assertIn("tool-execution", event_types)


if __name__ == "__main__":
    unittest.main()
