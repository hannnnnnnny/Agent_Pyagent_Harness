"""Lexical checks on model-supplied paths, applied before touching the filesystem."""

from __future__ import annotations

import re

from pyagent.errors import SandboxViolation

MAX_PATH_LENGTH = 4096

# Windows reserved device names resolve to devices, not files, in any directory.
_WINDOWS_DEVICES = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.IGNORECASE)


def check_path_text(path: str) -> None:
    """Reject path strings that are malformed or tricky regardless of the OS."""
    if not path or not path.strip():
        raise SandboxViolation("path must not be empty")
    if len(path) > MAX_PATH_LENGTH:
        raise SandboxViolation("path is too long")
    if "\x00" in path:
        raise SandboxViolation("path contains a NUL byte")
    if path.startswith(("\\\\", "//")):
        raise SandboxViolation("UNC and network paths are not allowed")
    if path.startswith("~"):
        raise SandboxViolation("home-relative paths are not allowed")
    for part in re.split(r"[\\/]", path):
        if _WINDOWS_DEVICES.match(part.rstrip(" .")):
            raise SandboxViolation(f"reserved device name {part!r} is not allowed")
    # A colon after the drive letter selects an NTFS alternate data stream.
    if ":" in path[2:]:
        raise SandboxViolation("alternate data streams are not allowed")
