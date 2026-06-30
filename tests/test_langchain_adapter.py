from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from jarvis.agent import get_langchain_tools
from jarvis.langchain_adapter import (
    ApprovalRequiredError,
    build_langchain_tool,
    build_langchain_tool_registry,
    build_langchain_tools,
    build_openai_tools_from_langchain,
    langchain_runtime_available,
)
from jarvis.tools.base import ApprovalFlag, ToolResult


def _make_dummy_tool() -> SimpleNamespace:
    async def run(message: str, danger: bool = False) -> ToolResult:
        return ToolResult(output=f"echo:{message}:{danger}", error=False)

    def needs_approval(inputs: dict) -> ApprovalFlag:
        return ApprovalFlag.REQUIRED if inputs.get("danger") else ApprovalFlag.NONE

    return SimpleNamespace(
        DEFINITION={
            "name": "dummy_echo",
            "description": "Echo a message and simulate approval-sensitive execution.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back.",
                    },
                    "danger": {
                        "type": "boolean",
                        "description": "Whether this call should require approval.",
                        "default": False,
                    },
                },
                "required": ["message"],
            },
        },
        run=run,
        needs_approval=needs_approval,
    )


class LangChainAdapterTests(unittest.TestCase):
    def test_build_langchain_tools_preserves_registry_names(self) -> None:
        registry = {"dummy_echo": _make_dummy_tool()}

        tools = build_langchain_tools(registry)

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "dummy_echo")
        self.assertIn("approval-sensitive", tools[0].description)

    def test_tool_registry_builder_returns_named_mapping(self) -> None:
        registry = {"dummy_echo": _make_dummy_tool()}

        tool_registry = build_langchain_tool_registry(registry)

        self.assertEqual(list(tool_registry.keys()), ["dummy_echo"])
        self.assertEqual(tool_registry["dummy_echo"].name, "dummy_echo")

    def test_langchain_tool_executes_without_approval_when_safe(self) -> None:
        registry = {"dummy_echo": _make_dummy_tool()}
        tool = build_langchain_tool("dummy_echo", tool_registry=registry)

        output = asyncio.run(tool.ainvoke({"message": "hello", "danger": False}))

        self.assertEqual(output, "echo:hello:False")

    def test_langchain_tool_blocks_execution_when_approval_required(self) -> None:
        registry = {"dummy_echo": _make_dummy_tool()}
        tool = build_langchain_tool("dummy_echo", tool_registry=registry)

        with self.assertRaises(ApprovalRequiredError):
            asyncio.run(tool.ainvoke({"message": "hello", "danger": True}))

    def test_real_agent_surface_exposes_langchain_compatible_tools(self) -> None:
        tools = get_langchain_tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("bash", tool_names)
        self.assertIn("web", tool_names)
        self.assertGreaterEqual(len(tool_names), 3)

    def test_openai_tool_surface_can_be_derived_from_langchain_adapter(self) -> None:
        registry = {"dummy_echo": _make_dummy_tool()}

        tools = build_openai_tools_from_langchain(registry)

        self.assertEqual(len(tools), 1)
        function = tools[0]["function"]
        self.assertEqual(function["name"], "dummy_echo")
        self.assertIn("properties", function["parameters"])
        self.assertIn("message", function["parameters"]["properties"])

    def test_runtime_flag_matches_import_state(self) -> None:
        self.assertIsInstance(langchain_runtime_available(), bool)


if __name__ == "__main__":
    unittest.main()
