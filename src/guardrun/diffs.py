"""Compact unified diffs for reporting file changes."""

from __future__ import annotations

import difflib

MAX_DIFF_LINES = 60


def unified_diff(before: str, after: str, path: str, context: int = 2) -> str:
    """A unified diff of ``before`` -> ``after``, clipped to a readable length."""
    lines = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=context,
            lineterm="",
        )
    )
    if len(lines) > MAX_DIFF_LINES:
        hidden = len(lines) - MAX_DIFF_LINES
        lines = [*lines[:MAX_DIFF_LINES], f"... ({hidden} more diff lines)"]
    return "\n".join(lines)
