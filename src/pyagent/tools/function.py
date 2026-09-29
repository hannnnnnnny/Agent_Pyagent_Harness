"""Build tools from plain functions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyagent.tools.base import Risk, Tool, ToolContext

ToolFunction = Callable[[dict[str, Any], ToolContext], str]


def function_tool(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    risk: Risk = Risk.READ,
) -> Callable[[ToolFunction], Tool]:
    """Decorator turning ``fn(args, ctx) -> str`` into a :class:`Tool` instance.

    The schema is explicit rather than inferred from type hints so what the
    model sees is exactly what gets validated.
    """

    def decorate(fn: ToolFunction) -> Tool:
        attrs = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "risk": risk,
            "run": lambda self, args, ctx: fn(args, ctx),
            "__doc__": fn.__doc__,
        }
        cls = type(f"FunctionTool_{name}", (Tool,), attrs)
        tool: Tool = cls()
        return tool

    return decorate
