"""Text helpers shared by tools and the agent loop."""

from __future__ import annotations


def _marker(omitted: int) -> str:
    return f"\n... [{omitted} characters truncated] ...\n"


def truncate_middle(text: str, limit: int) -> str:
    """Shorten ``text`` to at most ``limit`` characters, keeping both ends.

    Tool output often has the important parts at the start (headers) and the
    end (errors, exit status), so the middle is elided instead of the tail.
    """
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if len(text) <= limit:
        return text
    # Size the marker for the worst-case digit count so the result never exceeds limit.
    marker_len = len(_marker(len(text)))
    if marker_len >= limit:
        return text[:limit]
    keep = limit - marker_len
    marker = _marker(len(text) - keep)
    head = keep // 2
    tail = keep - head
    return text[:head] + marker + (text[-tail:] if tail else "")
