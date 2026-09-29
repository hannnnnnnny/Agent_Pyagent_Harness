"""The provider interface: one model call in, one assistant turn out."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pyagent.messages import JSON, ModelResponse


@dataclass(frozen=True)
class ModelRequest:
    """Everything needed for one model call, independent of vendor SDKs."""

    system: str
    messages: list[JSON]
    tools: list[JSON] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    """Anything that can turn a request into an assistant turn."""

    model: str

    def complete(self, request: ModelRequest) -> ModelResponse: ...
