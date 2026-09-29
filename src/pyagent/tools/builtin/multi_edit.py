"""multi_edit: several exact replacements in one file, applied atomically."""

from __future__ import annotations

from typing import Any

from pyagent.diffs import unified_diff
from pyagent.errors import ToolError
from pyagent.safety.fileio import read_text, write_text
from pyagent.tools.base import Risk, Tool, ToolContext
from pyagent.tools.builtin.editing import replace_exact

MAX_EDITS = 50


class MultiEdit(Tool):
    name = "multi_edit"
    description = (
        "Apply several exact string replacements to one file, in order. Each edit sees "
        "the result of the previous ones. If any edit fails, the file is left unchanged."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "edits": {
                "type": "array",
                "maxItems": MAX_EDITS,
                "items": {
                    "type": "object",
                    "properties": {
                        "old_string": {"type": "string", "minLength": 1},
                        "new_string": {"type": "string"},
                        "replace_all": {"type": "boolean"},
                    },
                    "required": ["old_string", "new_string"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["path", "edits"],
        "additionalProperties": False,
    }
    risk = Risk.WRITE

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = ctx.workspace.resolve_for_write(args["path"])
        ctx.workspace.protected.check_read(ctx.workspace.relative(path))
        if not args["edits"]:
            raise ToolError("no edits given")
        original = read_text(path)
        text = original
        for index, edit in enumerate(args["edits"], 1):
            text, _ = replace_exact(
                text,
                edit["old_string"],
                edit["new_string"],
                replace_all=edit.get("replace_all", False),
                label=f"edit {index}",
            )
        write_text(path, text)
        rel = ctx.workspace.relative(path)
        return f"Applied {len(args['edits'])} edits to {rel}\n{unified_diff(original, text, rel)}"
