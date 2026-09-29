"""Project instructions loaded from a file such as ``AGENTS.md``."""

from __future__ import annotations

from pathlib import Path

from pyagent.errors import ConfigError, PyAgentError
from pyagent.safety.fileio import read_text
from pyagent.safety.workspace import Workspace

MAX_INSTRUCTIONS_BYTES = 32 * 1024


def load_instructions_file(root: Path, relative_path: str) -> str:
    """Read an instructions file through the workspace sandbox.

    The file goes into the system prompt, so it gets the same containment and
    protected-path rules as any tool read, plus a tighter size cap.
    """
    workspace = Workspace(root)
    try:
        path = workspace.resolve_for_read(relative_path)
        return read_text(path, max_bytes=MAX_INSTRUCTIONS_BYTES).strip()
    except PyAgentError as exc:
        raise ConfigError(f"cannot use instructions_file {relative_path!r}: {exc}") from exc


def combine_instructions(inline: str, from_file: str) -> str:
    parts = [part.strip() for part in (inline, from_file) if part.strip()]
    return "\n\n".join(parts)
