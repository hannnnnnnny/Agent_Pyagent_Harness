import threading
import time
from pathlib import Path
from typing import Any

import pytest

from pyagent.dispatch import Dispatcher
from pyagent.events import Event, EventBus
from pyagent.messages import ToolCall
from pyagent.safety.risk import Risk
from pyagent.tools.base import Tool, ToolContext
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


class Probe(Tool):
    """Records which thread ran it and how many calls overlapped."""

    name = "probe"
    description = "Test probe."
    input_schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
    risk = Risk.READ

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        with self.lock:
            self.active -= 1
        return str(args.get("n"))


class WriteProbe(Probe):
    name = "write_probe"
    risk = Risk.WRITE


def probe_dispatcher(root: Path, tool: Tool, **kwargs: bool) -> Dispatcher:
    executor = ToolExecutor(ToolRegistry([tool]), ToolContext.for_root(root))
    return Dispatcher(executor, EventBus(), **kwargs)


def probe_calls(name: str, n: int = 4) -> list[ToolCall]:
    return [ToolCall(f"p{i}", name, {"n": i}) for i in range(n)]


def test_read_only_calls_run_concurrently_in_order(tmp_path: Path) -> None:
    tool = Probe()
    results = probe_dispatcher(tmp_path, tool).run(probe_calls("probe"))
    assert [r.content for r in results] == ["0", "1", "2", "3"]
    assert tool.max_active > 1


def test_write_calls_never_run_concurrently(tmp_path: Path) -> None:
    tool = WriteProbe()
    probe_dispatcher(tmp_path, tool).run(probe_calls("write_probe"))
    assert tool.max_active == 1


def test_parallelism_can_be_disabled(tmp_path: Path) -> None:
    tool = Probe()
    probe_dispatcher(tmp_path, tool, parallel_reads=False).run(probe_calls("probe"))
    assert tool.max_active == 1


def test_mixed_turns_run_sequentially(tmp_path: Path) -> None:
    read, write = Probe(), WriteProbe()
    executor = ToolExecutor(ToolRegistry([read, write]), ToolContext.for_root(tmp_path))
    calls_ = [*probe_calls("probe", 2), ToolCall("w", "write_probe", {"n": 9})]
    results = Dispatcher(executor, EventBus()).run(calls_)
    assert [r.content for r in results] == ["0", "1", "9"]
    assert read.max_active == 1
