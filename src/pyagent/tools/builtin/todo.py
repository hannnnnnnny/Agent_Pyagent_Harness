"""todo: a task list the model keeps for itself during long tasks."""

from __future__ import annotations

from typing import Any

from pyagent.errors import ToolError
from pyagent.tools.base import Risk, Tool, ToolContext

MAX_ITEMS = 50
_MARKS = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
STATE_KEY = "todos"


class Todo(Tool):
    name = "todo"
    description = (
        "Maintain your task list for multi-step work. Send the complete list each time; "
        "it replaces the previous one. Keep exactly one item in_progress while working, "
        "and mark items completed as soon as they are done."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "maxItems": MAX_ITEMS,
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "minLength": 1, "maxLength": 300},
                        "status": {"type": "string", "enum": list(_MARKS)},
                    },
                    "required": ["content", "status"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    }
    # Only updates in-memory state, so it never needs approval.
    risk = Risk.READ

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        items = args["items"]
        in_progress = sum(item["status"] == "in_progress" for item in items)
        if in_progress > 1:
            raise ToolError(f"{in_progress} items are in_progress; keep at most one")
        ctx.extras[STATE_KEY] = [dict(item) for item in items]
        if not items:
            return "Task list cleared."
        lines = [f"{_MARKS[item['status']]} {item['content']}" for item in items]
        done = sum(item["status"] == "completed" for item in items)
        return "\n".join([*lines, f"({done}/{len(items)} completed)"])
