"""read_file: view a text file with line numbers."""

from __future__ import annotations

from typing import Any

from pyagent.safety.fileio import read_text
from pyagent.tools.base import Risk, Tool, ToolContext

DEFAULT_LINE_LIMIT = 2000


class ReadFile(Tool):
    name = "read_file"
    description = (
        "Read a UTF-8 text file from the workspace. Output lines are prefixed with "
        "their 1-based line number and a tab. Use offset/limit to page through large files."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "offset": {
                "type": "integer",
                "minimum": 1,
                "description": "First line to return (1-based). Defaults to 1.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
                "description": f"Maximum lines to return. Defaults to {DEFAULT_LINE_LIMIT}.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    risk = Risk.READ

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = ctx.workspace.resolve_for_read(args["path"])
        lines = read_text(path).splitlines()
        offset = int(args.get("offset", 1))
        limit = int(args.get("limit", DEFAULT_LINE_LIMIT))
        if not lines:
            return "(empty file)"
        if offset > len(lines):
            return f"(offset {offset} is past the end; file has {len(lines)} lines)"
        window = lines[offset - 1 : offset - 1 + limit]
        body = "\n".join(f"{offset + i}\t{line}" for i, line in enumerate(window))
        end = offset + len(window) - 1
        if end < len(lines):
            body += f"\n(showing lines {offset}-{end} of {len(lines)})"
        return body
