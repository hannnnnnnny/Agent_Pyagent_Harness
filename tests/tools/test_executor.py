from pathlib import Path
from typing import Any

import pytest

from pyagent.errors import ApprovalDenied, ToolError
from pyagent.messages import ToolCall
from pyagent.tools.base import Tool, ToolContext
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.registry import ToolRegistry


class Echo(Tool):
    name = "echo"
    description = "Echo text."
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        text = str(args["text"])
        if text == "fail":
            raise ToolError("expected failure")
        if text == "crash":
            raise RuntimeError("secret internal detail")
        return text


@pytest.fixture
def executor(tmp_path: Path) -> ToolExecutor:
    return ToolExecutor(
        ToolRegistry([Echo()]), ToolContext.for_root(tmp_path), max_output_chars=200
    )


def test_successful_call(executor: ToolExecutor) -> None:
    result = executor.execute(ToolCall("1", "echo", {"text": "hi"}))
    assert (result.tool_use_id, result.content, result.is_error) == ("1", "hi", False)


def test_unknown_tool_is_an_error_result(executor: ToolExecutor) -> None:
    result = executor.execute(ToolCall("1", "nope", {}))
    assert result.is_error
    assert "unknown tool" in result.content


def test_invalid_input_never_reaches_tool(executor: ToolExecutor) -> None:
    result = executor.execute(ToolCall("1", "echo", {"text": 5}))
    assert result.is_error
    assert "invalid input" in result.content


def test_tool_error_message_is_reported(executor: ToolExecutor) -> None:
    result = executor.execute(ToolCall("1", "echo", {"text": "fail"}))
    assert result.is_error
    assert result.content == "expected failure"


def test_crash_does_not_leak_details(executor: ToolExecutor) -> None:
    result = executor.execute(ToolCall("1", "echo", {"text": "crash"}))
    assert result.is_error
    assert "secret" not in result.content


def test_gate_can_block_a_call(tmp_path: Path) -> None:
    ran: list[str] = []

    def deny(tool: Tool, call: ToolCall) -> None:
        ran.append(tool.name)
        raise ApprovalDenied("user said no")

    executor = ToolExecutor(ToolRegistry([Echo()]), ToolContext.for_root(tmp_path), gates=[deny])
    result = executor.execute(ToolCall("1", "echo", {"text": "hi"}))
    assert result.is_error
    assert "user said no" in result.content
    assert ran == ["echo"]


def test_gates_run_after_validation(tmp_path: Path) -> None:
    calls: list[str] = []
    executor = ToolExecutor(
        ToolRegistry([Echo()]),
        ToolContext.for_root(tmp_path),
        gates=[lambda tool, call: calls.append(call.id)],
    )
    executor.execute(ToolCall("bad", "echo", {}))
    assert calls == []


def test_long_output_is_truncated(executor: ToolExecutor) -> None:
    result = executor.execute(ToolCall("1", "echo", {"text": "z" * 1000}))
    assert len(result.content) <= 200


def test_execute_all_preserves_order(executor: ToolExecutor) -> None:
    calls = [ToolCall(str(i), "echo", {"text": str(i)}) for i in range(3)]
    assert [r.tool_use_id for r in executor.execute_all(calls)] == ["0", "1", "2"]
