"""Provider-neutral message and content types.

Messages are stored in the Messages API wire shape (plain dicts) so assistant
turns can be echoed back byte-for-byte. Editing earlier turns would invalidate
preserved thinking blocks, so the conversation is append-only by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
