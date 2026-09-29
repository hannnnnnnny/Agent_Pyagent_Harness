"""Exact-replacement logic shared by edit_file and multi_edit."""

from __future__ import annotations

from pyagent.errors import ToolError


def match_line_endings(text: str, fragment: str) -> str:
    """Rewrite ``fragment``'s newlines to CRLF when ``text`` uses CRLF.

    Models write ``\\n``; files created on Windows often use ``\\r\\n``. Without
    this, multi-line replacements silently never match on those files.
    """
    if "\r\n" in text and "\n" in fragment and "\r\n" not in fragment:
        return fragment.replace("\n", "\r\n")
    return fragment


def replace_exact(
    text: str, old: str, new: str, *, replace_all: bool = False, label: str = ""
) -> tuple[str, int]:
    """Replace ``old`` with ``new``; returns the new text and the match count."""
    prefix = f"{label}: " if label else ""
    if old == new:
        raise ToolError(f"{prefix}old_string and new_string are identical")
    old, new = match_line_endings(text, old), match_line_endings(text, new)
    count = text.count(old)
    if count == 0:
        raise ToolError(f"{prefix}old_string was not found in the file")
    if count > 1 and not replace_all:
        raise ToolError(
            f"{prefix}old_string matches {count} times; add surrounding context "
            "to make it unique or set replace_all"
        )
    return text.replace(old, new), count
