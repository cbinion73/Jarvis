"""
JARVIS Agent Tools
==================
All agent tools in one registry. Each tool exposes:
  DEFINITION  — Anthropic tool_use schema dict
  needs_approval(input_dict) -> ApprovalFlag
  run(**kwargs) -> ToolResult   (async)
"""

from .base import ApprovalFlag, ToolResult  # noqa: F401
from . import bash, files, web, jarvis_api, git, memory  # noqa: F401

# Ordered list of all tools available to the agent
ALL_TOOLS = [bash, files, web, jarvis_api, git, memory]

# Anthropic-format tool definitions (for LLM tool_use)
TOOL_DEFINITIONS = [t.DEFINITION for t in ALL_TOOLS]

# Map tool name → module for dispatch
TOOL_REGISTRY: dict = {t.DEFINITION["name"]: t for t in ALL_TOOLS}
