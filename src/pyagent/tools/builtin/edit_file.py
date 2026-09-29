"""edit_file: exact string replacement within a file."""

from __future__ import annotations

from typing import Any

from pyagent.diffs import unified_diff
from pyagent.errors import ToolError
from pyagent.safety.fileio import read_text, write_text
from pyagent.tools.base import Risk, Tool, ToolContext


class EditFile(Tool):
    name = "edit_file"
    description = (
        "Replace an exact string in a file. old_string must match exactly, including "
        "whitespace, and must be unique unless replace_all is true. Read the file first."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "old_string": {"type": "string", "minLength": 1, "description": "Text to replace."},
            "new_string": {"type": "string", "description": "Replacement text."},
            "replace_all": {
                "type": "boolean",
                "description": "Replace every occurrence instead of requiring a unique match.",
            },
        },
        "required": ["path", "old_string", "new_string"],
        "additionalProperties": False,
    }
    risk = Risk.WRITE

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = ctx.workspace.resolve_for_write(args["path"])
        ctx.workspace.protected.check_read(ctx.workspace.relative(path))
        old, new = args["old_string"], args["new_string"]
        if old == new:
            raise ToolError("old_string and new_string are identical")
        text = read_text(path)
        count = text.count(old)
        if count == 0:
            raise ToolError("old_string was not found in the file")
        if count > 1 and not args.get("replace_all", False):
            raise ToolError(
                f"old_string matches {count} times; add surrounding context "
                "to make it unique or set replace_all"
            )
        updated = text.replace(old, new)
        write_text(path, updated)
        noun = "occurrence" if count == 1 else "occurrences"
        rel = ctx.workspace.relative(path)
        return f"Replaced {count} {noun} in {rel}\n{unified_diff(text, updated, rel)}"
