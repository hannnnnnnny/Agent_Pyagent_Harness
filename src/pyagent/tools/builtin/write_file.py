"""write_file: create or overwrite a text file."""

from __future__ import annotations

from typing import Any

from pyagent.safety.fileio import write_text
from pyagent.tools.base import Risk, Tool, ToolContext


class WriteFile(Tool):
    name = "write_file"
    description = (
        "Create a new text file or completely replace an existing one. Parent "
        "directories are created as needed. Prefer edit_file for small changes."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "content": {"type": "string", "description": "The full new file content."},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    }
    risk = Risk.WRITE

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = ctx.workspace.resolve_for_write(args["path"])
        existed = path.exists()
        size = write_text(path, args["content"])
        verb = "Overwrote" if existed else "Created"
        return f"{verb} {ctx.workspace.relative(path)} ({size} bytes)"
