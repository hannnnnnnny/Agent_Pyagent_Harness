"""Workspace traversal that respects the sandbox."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from pyagent.errors import SafetyError
from pyagent.safety.workspace import Workspace

# Noise directories skipped by default: large, generated, or version-control internals.
DEFAULT_SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
    }
)


def walk_files(
    workspace: Workspace,
    start: Path,
    skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS,
) -> Iterator[Path]:
    """Yield readable files under ``start``, top-down, sorted within each directory.

    Symlinked directories are not descended into, and files whose real path
    leaves the workspace or matches a protected rule are skipped silently.
    """
    for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            real = path.resolve()
            if not workspace.contains(real):
                continue
            try:
                workspace.protected.check_read(workspace.relative(real))
            except SafetyError:
                continue
            yield path
