"""Dispatching one turn's tool calls: limits, loop guards, and events."""

from __future__ import annotations

from pyagent.events import EventBus
from pyagent.messages import ToolCall, ToolResult
from pyagent.tools.executor import ToolExecutor

DEFAULT_MAX_CALLS_PER_TURN = 25


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
    ) -> None:
        if max_calls_per_turn < 1:
            raise ValueError("max_calls_per_turn must be at least 1")
        self.executor = executor
        self.events = events
        self.max_calls_per_turn = max_calls_per_turn

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

    def _execute(self, call: ToolCall) -> ToolResult:
        self.events.emit("tool_started", tool=call.name, input=call.input)
        result = self.executor.execute(call)
        self.events.emit(
            "tool_finished", tool=call.name, is_error=result.is_error, output=result.content
        )
        return result
