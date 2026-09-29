"""Registry of tools available to an agent."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import Any

from pyagent.tools.base import Tool
from pyagent.tools.schema import check_schema

_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class ToolRegistry:
    """Holds tools by name and validates their definitions on registration."""

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if not _NAME.match(tool.name):
            raise ValueError(f"invalid tool name {tool.name!r}")
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} is already registered")
        if not tool.description.strip():
            raise ValueError(f"tool {tool.name!r} needs a description")
        if tool.input_schema.get("type") != "object":
            raise ValueError(f"tool {tool.name!r} input_schema must be an object schema")
        check_schema(tool.input_schema, tool.name)
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def specs(self) -> list[dict[str, Any]]:
        """Tool definitions in a stable (sorted) order to keep the prompt cacheable."""
        return [self._tools[name].spec() for name in sorted(self._tools)]
