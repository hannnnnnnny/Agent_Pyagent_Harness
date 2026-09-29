"""Provider-neutral message and content types.

Messages are stored in the Messages API wire shape (plain dicts) so assistant
turns can be echoed back byte-for-byte. Editing earlier turns would invalidate
preserved thinking blocks, so the conversation is append-only by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pyagent.usage import Usage

JSON = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation requested by the model."""

    id: str
    name: str
    input: JSON = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    """The outcome of executing a :class:`ToolCall`."""

    tool_use_id: str
    content: str
    is_error: bool = False

    def to_block(self) -> JSON:
        block: JSON = {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": self.content,
        }
        if self.is_error:
            block["is_error"] = True
        return block


@dataclass(frozen=True)
class ModelResponse:
    """One assistant turn returned by a provider.

    ``content`` holds the raw wire-shaped blocks, including opaque thinking
    blocks, so the turn can be appended to history unchanged.
    """

    content: list[JSON]
    stop_reason: str | None
    model: str = ""
    usage: Usage = field(default_factory=Usage)

    @property
    def text(self) -> str:
        return "".join(b.get("text", "") for b in self.content if b.get("type") == "text")

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [
            ToolCall(id=b["id"], name=b["name"], input=dict(b.get("input") or {}))
            for b in self.content
            if b.get("type") == "tool_use"
        ]


class Conversation:
    """Append-only message history in Messages API shape."""

    def __init__(self, messages: list[JSON] | None = None) -> None:
        self._messages: list[JSON] = list(messages or [])

    def __len__(self) -> int:
        return len(self._messages)

    @property
    def messages(self) -> list[JSON]:
        """A shallow copy; mutating it does not change the conversation."""
        return list(self._messages)

    def add_user_text(self, text: str) -> None:
        self._messages.append({"role": "user", "content": [{"type": "text", "text": text}]})

    def add_assistant(self, response: ModelResponse) -> None:
        self._messages.append({"role": "assistant", "content": list(response.content)})

    def add_tool_results(self, results: list[ToolResult]) -> None:
        # All results for one assistant turn go in a single user message; splitting
        # them discourages the model from making parallel tool calls.
        if not results:
            raise ValueError("at least one tool result is required")
        self._messages.append({"role": "user", "content": [r.to_block() for r in results]})
