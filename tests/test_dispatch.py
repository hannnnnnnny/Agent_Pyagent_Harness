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


def test_limit_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make(tmp_path, max_calls_per_turn=0)
