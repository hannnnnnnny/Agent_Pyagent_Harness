from typing import Any

import pytest

from pyagent.tools.base import Tool, ToolContext
from pyagent.tools.registry import ToolRegistry


def make_tool(name: str, schema: dict[str, Any] | None = None, description: str = "d") -> Tool:
    class _T(Tool):
        def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
            return ""

    _T.name = name
    _T.description = description
    _T.input_schema = schema or {"type": "object", "properties": {}}
    return _T()


def test_register_and_lookup() -> None:
    tool = make_tool("alpha")
    registry = ToolRegistry([tool])
    assert registry.get("alpha") is tool
    assert "alpha" in registry
    assert len(registry) == 1
    assert list(registry) == [tool]


def test_unknown_tool_lookup_returns_none() -> None:
    assert ToolRegistry().get("missing") is None


def test_duplicate_names_rejected() -> None:
    registry = ToolRegistry([make_tool("a")])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(make_tool("a"))


@pytest.mark.parametrize("name", ["", "has space", "x" * 65, "semi;colon"])
def test_invalid_names_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="invalid tool name"):
        ToolRegistry([make_tool(name)])


def test_blank_description_rejected() -> None:
    with pytest.raises(ValueError, match="description"):
        ToolRegistry([make_tool("a", description="  ")])


def test_non_object_schema_rejected() -> None:
    with pytest.raises(ValueError, match="object schema"):
        ToolRegistry([make_tool("a", {"type": "string"})])


def test_unsupported_schema_keyword_rejected() -> None:
    schema = {"type": "object", "properties": {"p": {"type": "string", "format": "uri"}}}
    with pytest.raises(ValueError, match="unsupported"):
        ToolRegistry([make_tool("a", schema)])


def test_specs_are_sorted_by_name() -> None:
    registry = ToolRegistry([make_tool("b"), make_tool("a")])
    assert [s["name"] for s in registry.specs()] == ["a", "b"]
