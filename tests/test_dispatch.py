from pathlib import Path

import pytest

from pyagent.dispatch import Dispatcher
from pyagent.events import Event, EventBus
from pyagent.messages import ToolCall
from pyagent.tools.base import ToolContext
from pyagent.tools.builtin import file_tools
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.registry import ToolRegistry


def make(root: Path, **kwargs: int) -> tuple[Dispatcher, list[Event]]:
    events: list[Event] = []
    bus = EventBus()
    bus.subscribe(events.append)
    executor = ToolExecutor(ToolRegistry(file_tools()), ToolContext.for_root(root))
    return Dispatcher(executor, bus, **kwargs), events


def calls(n: int, name: str = "list_dir") -> list[ToolCall]:
    return [ToolCall(f"c{i}", name, {}) for i in range(n)]


def test_results_line_up_with_calls(tmp_path: Path) -> None:
    dispatcher, _ = make(tmp_path)
    results = dispatcher.run(calls(3))
    assert [r.tool_use_id for r in results] == ["c0", "c1", "c2"]
    assert not any(r.is_error for r in results)


def test_calls_over_the_limit_are_not_run(tmp_path: Path) -> None:
    dispatcher, events = make(tmp_path, max_calls_per_turn=2)
    results = dispatcher.run(calls(4))
    assert [r.is_error for r in results] == [False, False, True, True]
    assert "at most 2 tool calls" in results[3].content
    assert [e.kind for e in events].count("tool_started") == 2


def test_events_wrap_each_call(tmp_path: Path) -> None:
    dispatcher, events = make(tmp_path)
    dispatcher.run(calls(1))
    assert [e.kind for e in events] == ["tool_started", "tool_finished"]


@pytest.mark.parametrize("limit", ["max_calls_per_turn", "max_identical_calls"])
def test_limits_must_be_positive(tmp_path: Path, limit: str) -> None:
    with pytest.raises(ValueError):
        make(tmp_path, **{limit: 0})


def test_identical_calls_in_a_row_are_cut_off(tmp_path: Path) -> None:
    dispatcher, _ = make(tmp_path, max_identical_calls=2)
    outcomes = [dispatcher.run(calls(1))[0].is_error for _ in range(4)]
    assert outcomes == [False, False, True, True]


def test_a_different_call_resets_the_repeat_count(tmp_path: Path) -> None:
    dispatcher, _ = make(tmp_path, max_identical_calls=2)
    dispatcher.run(calls(1))
    dispatcher.run(calls(1))
    dispatcher.run([ToolCall("x", "glob", {"pattern": "*"})])
    assert not dispatcher.run(calls(1))[0].is_error


def test_same_tool_with_different_input_is_not_a_repeat(tmp_path: Path) -> None:
    dispatcher, _ = make(tmp_path, max_identical_calls=1)
    first = dispatcher.run([ToolCall("a", "glob", {"pattern": "*.py"})])
    second = dispatcher.run([ToolCall("b", "glob", {"pattern": "*.md"})])
    assert not first[0].is_error
    assert not second[0].is_error
