"""Add your own tool to pyagent.

Tools declare a JSON schema (validated before every call), a risk level (which
drives approvals), and a ``run`` method. Raise ``ToolError`` for failures the
model should see and recover from.

    python examples/custom_tool.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

from pyagent import AgentOptions, build_agent
from pyagent.cli.render import ConsoleRenderer, format_result
from pyagent.errors import ToolError
from pyagent.providers.scripted import ScriptedProvider, text_turn, tool_turn
from pyagent.tools import Risk, Tool, ToolContext


class WordCount(Tool):
    name = "word_count"
    description = "Count the words in a workspace text file."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "File to count."}},
        "required": ["path"],
        "additionalProperties": False,
    }
    risk = Risk.READ

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        # resolve_for_read applies the sandbox and protected-path rules.
        path = ctx.workspace.resolve_for_read(args["path"])
        if not path.is_file():
            raise ToolError(f"{args['path']} is not a file")
        return str(len(path.read_text(encoding="utf-8").split()))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "essay.txt").write_text("the quick brown fox jumps over the lazy dog")
        provider = ScriptedProvider(
            [tool_turn(("word_count", {"path": "essay.txt"})), text_turn("It has 9 words.")]
        )
        options = AgentOptions(extra_tools=[WordCount()], audit=False)
        options.events.subscribe(ConsoleRenderer(sys.stdout))
        result = build_agent(root, provider, options).run("How long is essay.txt?")
        print(format_result(result))
        return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
