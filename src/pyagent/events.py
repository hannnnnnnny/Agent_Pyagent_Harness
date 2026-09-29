"""Structured events emitted by the agent loop.

Frontends (CLI, logs, tests) subscribe to these instead of parsing output.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """A single observable step in an agent run."""

    kind: str
    data: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[Event], None]
