"""Saving and resuming conversations under ``.pyagent/sessions``."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyagent.errors import PyAgentError
from pyagent.messages import Conversation
from pyagent.safety.fileio import write_text

# Session ids become file names, so they are restricted to a safe alphabet.
_SESSION_ID = re.compile(r"^[a-f0-9]{12}$")
MAX_SESSION_BYTES = 50 * 1024 * 1024


class SessionError(PyAgentError):
    """Raised for unknown, malformed, or unreadable sessions."""


@dataclass(frozen=True)
class SessionInfo:
    id: str
    title: str
    model: str
    created: str
    updated: str
    messages: int


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SessionStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, session_id: str) -> Path:
        if not _SESSION_ID.match(session_id):
            raise SessionError(f"invalid session id {session_id!r}")
        return self.directory / f"{session_id}.json"

    def save(self, session_id: str, conversation: Conversation, *, title: str, model: str) -> None:
        path = self._path(session_id)
        created = _now()
        if path.exists():
            created = self._read(path).get("created", created)
        record = {
            "id": session_id,
            "title": title[:200],
            "model": model,
            "created": created,
            "updated": _now(),
            "messages": json.loads(conversation.to_json()),
        }
        write_text(path, json.dumps(record, ensure_ascii=False), max_bytes=MAX_SESSION_BYTES)

    def load(self, session_id: str) -> Conversation:
        path = self._path(session_id)
        if not path.exists():
            raise SessionError(f"no session named {session_id}")
        try:
            return Conversation.from_json(json.dumps(self._read(path)["messages"]))
        except (KeyError, ValueError) as exc:
            raise SessionError(f"session {session_id} is corrupt: {exc}") from exc

    def list_sessions(self) -> list[SessionInfo]:
        """All sessions, most recently updated first; unreadable files are skipped."""
        infos = []
        for path in self.directory.glob("*.json") if self.directory.is_dir() else []:
            try:
                data = self._read(path)
                infos.append(
                    SessionInfo(
                        id=data["id"],
                        title=data.get("title", ""),
                        model=data.get("model", ""),
                        created=data.get("created", ""),
                        updated=data.get("updated", ""),
                        messages=len(data.get("messages", [])),
                    )
                )
            except (KeyError, SessionError):
                continue
        return sorted(infos, key=lambda info: info.updated, reverse=True)

    def _read(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SessionError(f"cannot read {path.name}: {exc}") from exc
        if not isinstance(data, dict):
            raise SessionError(f"{path.name} is not a session record")
        return data


def session_summary(info: SessionInfo) -> str:
    return " | ".join(str(v) for v in asdict(info).values())
