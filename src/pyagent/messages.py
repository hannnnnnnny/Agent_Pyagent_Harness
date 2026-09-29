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
