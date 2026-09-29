"""list_dir: show the entries of one directory."""

from __future__ import annotations

from typing import Any

from pyagent.errors import SafetyError, ToolError
from pyagent.tools.base import Risk, Tool, ToolContext

MAX_ENTRIES = 1000


class ListDir(Tool):
    name = "list_dir"
    description = (
        "List the files and subdirectories of a workspace directory (not recursive). "
        "Directories end with '/'."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory relative to the workspace root. Defaults to '.'.",
            },
        },
        "additionalProperties": False,
    }
    risk = Risk.READ

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        ws = ctx.workspace
        directory = ws.resolve_for_read(args.get("path", "."))
        if not directory.is_dir():
            raise ToolError(f"not a directory: {ws.relative(directory)}")
        entries: list[str] = []
        for child in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            real = child.resolve()
            if not ws.contains(real):
                continue
            try:
                ws.protected.check_read(ws.relative(real))
            except SafetyError:
                continue
            entries.append(child.name + ("/" if child.is_dir() else ""))
        if not entries:
            return "(empty directory)"
        if len(entries) > MAX_ENTRIES:
            hidden = len(entries) - MAX_ENTRIES
            entries = [*entries[:MAX_ENTRIES], f"... and {hidden} more entries"]
        return "\n".join(entries)
