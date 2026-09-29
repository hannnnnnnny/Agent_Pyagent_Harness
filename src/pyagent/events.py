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


class EventBus:
    """Fan-out of events to registered handlers.

    A failing handler must not break the agent run, so handler errors are
    collected rather than raised.
    """

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self.handler_errors: list[BaseException] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def emit(self, kind: str, **data: Any) -> Event:
        event = Event(kind, data)
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as exc:  # isolate frontends from the loop
                self.handler_errors.append(exc)
        return event
