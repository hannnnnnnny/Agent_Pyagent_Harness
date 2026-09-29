"""Bounded file I/O used by file tools."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pyagent.errors import ToolError

DEFAULT_MAX_READ_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_WRITE_BYTES = 2 * 1024 * 1024
_SNIFF_BYTES = 8192


def is_binary(data: bytes) -> bool:
    """Heuristic used by git: a NUL byte in the first block means binary."""
    return b"\x00" in data[:_SNIFF_BYTES]


def read_text(path: Path, max_bytes: int = DEFAULT_MAX_READ_BYTES) -> str:
    """Read a UTF-8 text file, refusing binaries and files over ``max_bytes``."""
    if not path.exists():
        raise ToolError(f"file not found: {path.name}")
    if not path.is_file():
        raise ToolError(f"not a regular file: {path.name}")
    size = path.stat().st_size
    if size > max_bytes:
        raise ToolError(f"file is {size} bytes, over the {max_bytes} byte read limit")
    data = path.read_bytes()
    if is_binary(data):
        raise ToolError(f"{path.name} looks like a binary file")
    return data.decode("utf-8", errors="replace")


def write_text(path: Path, content: str, max_bytes: int = DEFAULT_MAX_WRITE_BYTES) -> int:
    """Atomically write ``content``; returns bytes written.

    Writing to a temp file and renaming means a crash or a concurrent reader
    never observes a half-written file.
    """
    data = content.encode("utf-8")
    if len(data) > max_bytes:
        raise ToolError(f"content is {len(data)} bytes, over the {max_bytes} byte write limit")
    if path.exists() and not path.is_file():
        raise ToolError(f"not a regular file: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return len(data)
