"""The workspace: the only directory tree tools may touch."""

from __future__ import annotations

from pathlib import Path

from pyagent.errors import SandboxViolation
from pyagent.safety.paths import check_path_text
from pyagent.safety.protected import ProtectedPaths


class Workspace:
    """A root directory that confines every file operation.

    Paths are resolved *after* following symlinks, so a link inside the
    workspace that points outside it is treated as outside.
    """

    def __init__(self, root: Path | str, protected: ProtectedPaths | None = None) -> None:
        resolved = Path(root).resolve()
        if not resolved.is_dir():
            raise ValueError(f"workspace root {resolved} is not a directory")
        self.root = resolved
        self.protected = protected or ProtectedPaths()

    def resolve(self, path: str) -> Path:
        """Map a model-supplied path to an absolute path inside the workspace."""
        check_path_text(path)
        candidate = (self.root / path).resolve()
        if not self.contains(candidate):
            raise SandboxViolation(f"{path!r} is outside the workspace")
        return candidate

    def resolve_for_read(self, path: str) -> Path:
        resolved = self.resolve(path)
        self.protected.check_read(self.relative(resolved))
        return resolved

    def resolve_for_write(self, path: str) -> Path:
        resolved = self.resolve(path)
        self.protected.check_write(self.relative(resolved))
        return resolved

    def contains(self, path: Path) -> bool:
        return path == self.root or path.is_relative_to(self.root)

    def relative(self, path: Path) -> str:
        """Display form of a workspace path, always with forward slashes."""
        rel = path.relative_to(self.root).as_posix()
        return rel or "."
