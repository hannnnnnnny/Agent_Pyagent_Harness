"""Dispatching one turn's tool calls: limits, loop guards, and events."""

from __future__ import annotations

import json

from pyagent.events import EventBus
from pyagent.messages import ToolCall, ToolResult
from pyagent.tools.executor import ToolExecutor

DEFAULT_MAX_CALLS_PER_TURN = 25
# The same call (tool and input) this many times in a row is treated as a loop.
DEFAULT_MAX_IDENTICAL_CALLS = 3


def _signature(call: ToolCall) -> str:
    return f"{call.name}:{json.dumps(call.input, sort_keys=True)}"


class Dispatcher:
    """Runs the tool calls from one assistant turn.

    Results always line up one-to-one with the calls, because the API requires
    a result for every ``tool_use`` block, including ones that were not run.
    """

    def __init__(
        self,
        executor: ToolExecutor,
        events: EventBus,
        *,
        max_calls_per_turn: int = DEFAULT_MAX_CALLS_PER_TURN,
        max_identical_calls: int = DEFAULT_MAX_IDENTICAL_CALLS,
    ) -> None:
        if max_calls_per_turn < 1 or max_identical_calls < 1:
            raise ValueError("dispatch limits must be at least 1")
        self.executor = executor
        self.events = events
        self.max_calls_per_turn = max_calls_per_turn
        self.max_identical_calls = max_identical_calls
        self._last_signature = ""
        self._repeats = 0

    def run(self, calls: list[ToolCall]) -> list[ToolResult]:
        allowed = calls[: self.max_calls_per_turn]
        results = [self._execute(call) for call in allowed]
        for call in calls[self.max_calls_per_turn :]:
            message = (
                f"not run: at most {self.max_calls_per_turn} tool calls are allowed per "
                "turn. Re-issue this call in a later turn if it is still needed."
            )
            results.append(ToolResult(call.id, message, is_error=True))
        return results

    def _is_repeat_loop(self, call: ToolCall) -> bool:
        signature = _signature(call)
        self._repeats = self._repeats + 1 if signature == self._last_signature else 1
        self._last_signature = signature
        return self._repeats > self.max_identical_calls

    def _execute(self, call: ToolCall) -> ToolResult:
        if self._is_repeat_loop(call):
            message = (
                f"not run: this exact call was already made {self.max_identical_calls} times "
                "in a row with nothing else in between. Try a different approach."
            )
            return ToolResult(call.id, message, is_error=True)
        self.events.emit("tool_started", tool=call.name, input=call.input)
        result = self.executor.execute(call)
        self.events.emit(
            "tool_finished", tool=call.name, is_error=result.is_error, output=result.content
        )
        return result
