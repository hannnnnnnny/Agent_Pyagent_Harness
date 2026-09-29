"""Turns model tool calls into tool results, safely.

Nothing a tool does may crash the agent loop: every failure is converted into
an ``is_error`` result the model can read and react to.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from pyagent.errors import SafetyError, ToolError, ToolInputError
from pyagent.messages import ToolCall, ToolResult
from pyagent.text import truncate_middle
from pyagent.tools.base import Tool, ToolContext
from pyagent.tools.registry import ToolRegistry
from pyagent.tools.schema import validate

logger = logging.getLogger(__name__)

# Called after validation and before the tool runs. Raise SafetyError to block.
Gate = Callable[[Tool, ToolCall], None]
# Applied to every result (success or error) before it reaches the model.
OutputFilter = Callable[[str], str]

DEFAULT_MAX_OUTPUT_CHARS = 50_000


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        ctx: ToolContext,
        gates: list[Gate] | None = None,
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
        output_filters: list[OutputFilter] | None = None,
    ) -> None:
        self.registry = registry
        self.ctx = ctx
        self.gates = list(gates or [])
        self.max_output_chars = max_output_chars
        self.output_filters = list(output_filters or [])

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self.registry.get(call.name)
        if tool is None:
            return self._error(call, f"unknown tool {call.name!r}")
        try:
            validate(call.input, tool.input_schema)
            for gate in self.gates:
                gate(tool, call)
            output = tool.run(call.input, self.ctx)
        except ToolInputError as exc:
            return self._error(call, f"invalid input: {exc}")
        except SafetyError as exc:
            return self._error(call, f"blocked by safety policy: {exc}")
        except ToolError as exc:
            return self._error(call, str(exc))
        except Exception:
            # Unexpected bugs are logged in full locally, but only the exception
            # type reaches the model so internals and paths are not leaked.
            logger.exception("tool %s crashed", call.name)
            return self._error(call, "internal tool error; see local logs")
        return ToolResult(call.id, self._finish(output))

    def _error(self, call: ToolCall, message: str) -> ToolResult:
        return ToolResult(call.id, self._finish(message), is_error=True)

    def _finish(self, text: str) -> str:
        # Filter before truncating so a secret split by the elision marker still matches.
        for output_filter in self.output_filters:
            text = output_filter(text)
        return truncate_middle(text, self.max_output_chars)

    def execute_all(self, calls: list[ToolCall]) -> list[ToolResult]:
        """Run calls in order; results line up one-to-one with ``calls``."""
        return [self.execute(call) for call in calls]
