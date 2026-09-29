"""Append-only JSONL audit trail of everything the agent does."""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyagent.events import Event
from pyagent.safety.redact import Redactor


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


class AuditLog:
    """Writes one redacted JSON object per event.

    Use as an :class:`~pyagent.events.EventBus` subscriber. Records are
    flushed immediately so a crash leaves a complete trail up to that point.
    """

    def __init__(self, path: Path, redactor: Redactor | None = None, run_id: str = "") -> None:
        self.path = path
        self.redactor = redactor or Redactor()
        self.run_id = run_id
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()
            if sys.platform != "win32":
                # The log can describe sensitive work; keep it private to the user.
                os.chmod(path, 0o600)

    def record(self, kind: str, data: dict[str, Any]) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "run": self.run_id,
            "kind": kind,
            "data": _jsonable(data),
        }
        line = self.redactor.redact(json.dumps(entry, ensure_ascii=False))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def __call__(self, event: Event) -> None:
        self.record(event.kind, event.data)


def read_audit(path: Path) -> list[dict[str, Any]]:
    """Load all records; used by tests and the ``pyagent audit`` command."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
