from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import Field, create_model

from .tools import TOOL_REGISTRY
from .tools.base import ApprovalFlag
from .tools.middleware import execute_tool_call, preflight_tool_call

try:
    from langchain_core.tools import StructuredTool
except ModuleNotFoundError:  # pragma: no cover - exercised via fallback tests
    StructuredTool = None  # type: ignore[assignment]


def langchain_runtime_available() -> bool:
    return StructuredTool is not None


class ApprovalRequiredError(RuntimeError):
    def __init__(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        super().__init__(f"Approval required before executing tool '{tool_name}'.")
        self.tool_name = tool_name
        self.tool_input = dict(tool_input)


@dataclass(slots=True)
class LangChainCompatibleTool:
    name: str
    description: str
    args_schema: type[Any]
    coroutine: Any
    func: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    async def ainvoke(self, tool_input: dict[str, Any]) -> str:
        return await self.coroutine(**tool_input)

    def invoke(self, tool_input: dict[str, Any]) -> str:
        return self.func(**tool_input)


def _enum_literal(values: list[Any]) -> Any:
    unique = tuple(dict.fromkeys(values))
    if not unique:
        return str
    if all(isinstance(value, str) for value in unique):
        return Literal.__getitem__(unique)
    return str


def _schema_type(property_schema: dict[str, Any]) -> Any:
    enum_values = property_schema.get("enum")
    if isinstance(enum_values, list):
        return _enum_literal(enum_values)

    type_name = property_schema.get("type", "string")
    if type_name == "string":
        return str
    if type_name == "integer":
        return int
    if type_name == "number":
        return float
    if type_name == "boolean":
        return bool
    if type_name == "array":
        return list[Any]
    if type_name == "object":
        return dict[str, Any]
    return Any


def _build_args_schema(tool_name: str, input_schema: dict[str, Any]) -> type[Any]:
    properties = input_schema.get("properties", {}) or {}
    required = set(input_schema.get("required", []) or [])
    fields: dict[str, tuple[Any, Any]] = {}

    for property_name, property_schema in properties.items():
        schema = dict(property_schema or {})
        annotation = _schema_type(schema)
        description = str(schema.get("description", "")).strip() or None

        if property_name in required:
            default = Field(..., description=description)
        else:
            default_value = schema.get("default", None)
            default = Field(default_value, description=description)

        fields[property_name] = (annotation, default)

    model_name = "".join(part.capitalize() for part in tool_name.split("_")) + "Args"
    return create_model(model_name, **fields)


def _resolve_tool_registry(tool_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    return tool_registry or TOOL_REGISTRY

async def execute_langchain_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    tool_registry: dict[str, Any] | None = None,
) -> str:
    registry = _resolve_tool_registry(tool_registry)
    if registry.get(tool_name) is None:
        raise KeyError(f"Unknown tool: {tool_name}")

    preflight = preflight_tool_call(tool_name, tool_input, tool_registry=registry)
    if preflight.approval_flag == ApprovalFlag.REQUIRED:
        raise ApprovalRequiredError(tool_name, tool_input)

    outcome = await execute_tool_call(
        tool_name,
        tool_input,
        tool_registry=registry,
        preflight=preflight,
    )
    return outcome.result.output


def _make_sync_runner(tool_name: str, tool_registry: dict[str, Any] | None = None):
    def _run(**kwargs: Any) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                execute_langchain_tool(tool_name, kwargs, tool_registry=tool_registry)
            )
        raise RuntimeError(
            "Synchronous LangChain tool execution is unavailable inside an active event loop. "
            "Use 'ainvoke' instead."
        )

    return _run


def _make_async_runner(tool_name: str, tool_registry: dict[str, Any] | None = None):
    async def _arun(**kwargs: Any) -> str:
        return await execute_langchain_tool(tool_name, kwargs, tool_registry=tool_registry)

    return _arun


def build_langchain_tool(
    tool_name: str,
    *,
    tool_registry: dict[str, Any] | None = None,
) -> Any:
    registry = _resolve_tool_registry(tool_registry)
    module = registry[tool_name]
    definition = dict(getattr(module, "DEFINITION", {}) or {})
    input_schema = dict(definition.get("input_schema", {}) or {})
    description = str(definition.get("description", "")).strip()
    args_schema = _build_args_schema(tool_name, input_schema)
    metadata = {
        "jarvis_tool_name": tool_name,
        "approval_sensitive": True,
        "langchain_runtime_available": langchain_runtime_available(),
    }

    func = _make_sync_runner(tool_name, tool_registry=registry)
    coroutine = _make_async_runner(tool_name, tool_registry=registry)

    if StructuredTool is not None:
        return StructuredTool.from_function(
            func=func,
            coroutine=coroutine,
            name=tool_name,
            description=description,
            args_schema=args_schema,
        )

    return LangChainCompatibleTool(
        name=tool_name,
        description=description,
        args_schema=args_schema,
        coroutine=coroutine,
        func=func,
        metadata=metadata,
    )


def build_langchain_tools(
    tool_registry: dict[str, Any] | None = None,
) -> list[Any]:
    registry = _resolve_tool_registry(tool_registry)
    return [build_langchain_tool(tool_name, tool_registry=registry) for tool_name in registry]


def build_langchain_tool_registry(
    tool_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = _resolve_tool_registry(tool_registry)
    return {
        tool_name: build_langchain_tool(tool_name, tool_registry=registry)
        for tool_name in registry
    }


def _tool_args_schema(tool: Any) -> dict[str, Any]:
    schema_model = getattr(tool, "args_schema", None)
    if schema_model is None:
        return {"type": "object", "properties": {}}
    model_json_schema = getattr(schema_model, "model_json_schema", None)
    if callable(model_json_schema):
        return model_json_schema()
    schema = getattr(schema_model, "schema", None)
    if callable(schema):
        return schema()
    return {"type": "object", "properties": {}}


def build_openai_tool_from_langchain(tool: Any) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": str(getattr(tool, "name", "")).strip(),
            "description": str(getattr(tool, "description", "")).strip(),
            "parameters": _tool_args_schema(tool),
        },
    }


def build_openai_tools_from_langchain(
    tool_registry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        build_openai_tool_from_langchain(tool)
        for tool in build_langchain_tools(tool_registry)
    ]
