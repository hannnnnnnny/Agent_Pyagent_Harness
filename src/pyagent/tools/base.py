"""Base types for tools the model can call."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


class Risk(enum.Enum):
    """How much damage a tool can do; drives approval decisions."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"


@dataclass
class ToolContext:
    """Per-run resources handed to every tool invocation."""

    root: Path
    extras: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """A capability exposed to the model.

    Subclasses declare their name, description, and input schema as class
    attributes and implement :meth:`run`. Inputs are validated against the
    schema before ``run`` is called.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]
    risk: ClassVar[Risk] = Risk.READ

    def spec(self) -> dict[str, Any]:
        """The tool definition sent to the Messages API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @abstractmethod
    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        """Execute the tool and return text for the model.

        Raise :class:`pyagent.errors.ToolError` for expected failures; the
        message is shown to the model so it can correct course.
        """
