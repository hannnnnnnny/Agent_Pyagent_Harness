"""glob: find files by name pattern."""

from __future__ import annotations

import re
from typing import Any

from pyagent.safety.walk import walk_files
from pyagent.tools.base import Risk, Tool, ToolContext

MAX_RESULTS = 500


def compile_glob(pattern: str) -> re.Pattern[str]:
    """Translate a path glob into a regex.

    ``*`` and ``?`` never cross ``/``; ``**/`` matches zero or more directories.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


class Glob(Tool):
    name = "glob"
    description = (
        "Find workspace files whose path matches a glob pattern such as '**/*.py' or "
        "'src/*.ts'. Returns workspace-relative paths, one per line."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "minLength": 1, "maxLength": 500},
            "path": {
                "type": "string",
                "description": "Directory to search from. Defaults to the workspace root.",
            },
        },
        "required": ["pattern"],
        "additionalProperties": False,
    }
    risk = Risk.READ

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        ws = ctx.workspace
        start = ws.resolve_for_read(args.get("path", "."))
        regex = compile_glob(args["pattern"].replace("\\", "/"))
        matches: list[str] = []
        for path in walk_files(ws, start):
            if regex.match(path.relative_to(start).as_posix()):
                matches.append(ws.relative(path))
                if len(matches) > MAX_RESULTS:
                    break
        if not matches:
            return "(no matches)"
        if len(matches) > MAX_RESULTS:
            return "\n".join(matches[:MAX_RESULTS]) + f"\n(truncated at {MAX_RESULTS} results)"
        return "\n".join(matches)
