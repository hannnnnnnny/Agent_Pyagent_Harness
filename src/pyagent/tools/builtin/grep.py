"""grep: search file contents with a regular expression."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pyagent.errors import ToolError
from pyagent.safety.fileio import is_binary
from pyagent.safety.walk import walk_files
from pyagent.tools.base import Risk, Tool, ToolContext
from pyagent.tools.builtin.glob import compile_glob

MAX_MATCHES = 200
MAX_FILE_BYTES = 1024 * 1024
# Python's re has no timeout, so long lines are clipped to bound the cost of a
# pathological (catastrophically backtracking) pattern.
MAX_LINE_CHARS = 2000


class Grep(Tool):
    name = "grep"
    description = (
        "Search workspace files for a regular expression (Python syntax). Returns "
        "'path:line: text' for each matching line. Binary and very large files are skipped."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "minLength": 1, "maxLength": 500},
            "path": {"type": "string", "description": "Directory to search. Defaults to '.'."},
            "include": {"type": "string", "description": "Only search files matching this glob."},
            "ignore_case": {"type": "boolean"},
            "fixed_string": {
                "type": "boolean",
                "description": "Treat pattern as literal text rather than a regex.",
            },
        },
        "required": ["pattern"],
        "additionalProperties": False,
    }
    risk = Risk.READ

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        ws = ctx.workspace
        start = ws.resolve_for_read(args.get("path", "."))
        regex = _compile(args)
        include = compile_glob(args["include"]) if args.get("include") else None
        results: list[str] = []
        for path in walk_files(ws, start):
            if include and not include.match(path.relative_to(start).as_posix()):
                continue
            for lineno, line in _search(path, regex):
                results.append(f"{ws.relative(path)}:{lineno}: {line}")
                if len(results) >= MAX_MATCHES:
                    return "\n".join(results) + f"\n(stopped at {MAX_MATCHES} matches)"
        return "\n".join(results) if results else "(no matches)"


def _compile(args: dict[str, Any]) -> re.Pattern[str]:
    pattern = re.escape(args["pattern"]) if args.get("fixed_string") else args["pattern"]
    flags = re.IGNORECASE if args.get("ignore_case") else 0
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ToolError(f"invalid regular expression: {exc}") from exc


def _search(path: Path, regex: re.Pattern[str]) -> list[tuple[int, str]]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return []
        data = path.read_bytes()
    except OSError:
        return []
    if is_binary(data):
        return []
    hits = []
    for lineno, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
        clipped = line[:MAX_LINE_CHARS]
        if regex.search(clipped):
            hits.append((lineno, clipped.strip()))
    return hits
