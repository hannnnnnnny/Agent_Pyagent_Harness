from pathlib import Path
from typing import Any

from pyagent.messages import ToolCall
from pyagent.tools.base import Risk, Tool, ToolContext
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.function import function_tool
from pyagent.tools.registry import ToolRegistry

SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}


@function_tool("add", "Add two integers.", SCHEMA)
def add(args: dict[str, Any], ctx: ToolContext) -> str:
    """Adds numbers."""
    return str(args["a"] + args["b"])


def test_decorator_produces_a_tool() -> None:
    assert isinstance(add, Tool)
    assert add.spec()["name"] == "add"
    assert add.risk is Risk.READ
    assert add.__doc__ == "Adds numbers."


def test_function_tool_runs_through_executor(tmp_path: Path) -> None:
    executor = ToolExecutor(ToolRegistry([add]), ToolContext(root=tmp_path))
    assert executor.execute(ToolCall("1", "add", {"a": 2, "b": 3})).content == "5"


def test_risk_can_be_overridden() -> None:
    @function_tool("w", "Write.", {"type": "object", "properties": {}}, risk=Risk.WRITE)
    def w(args: dict[str, Any], ctx: ToolContext) -> str:
        return ""

    assert w.risk is Risk.WRITE
