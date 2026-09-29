"""Add a project-specific safety rule with a custom gate.

A gate sees every tool call after the built-in SafetyGate has allowed it and
can refuse it by raising ``PolicyViolation``. Here: generated files under
``migrations/`` must never be edited by hand.

    python examples/custom_policy.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from pyagent import AgentOptions, ApprovalMode, build_agent
from pyagent.cli.render import ConsoleRenderer, format_result
from pyagent.errors import PolicyViolation
from pyagent.messages import ToolCall
from pyagent.providers.scripted import ScriptedProvider, text_turn, tool_turn
from pyagent.tools import Risk, Tool


def protect_migrations(tool: Tool, call: ToolCall) -> None:
    path = str(call.input.get("path", "")).replace("\\", "/")
    if tool.risk is Risk.WRITE and path.startswith("migrations/"):
        raise PolicyViolation("migrations are generated; change the models and regenerate")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "migrations").mkdir()
        (root / "migrations" / "0001_initial.py").write_text("# generated\n")
        provider = ScriptedProvider(
            [
                tool_turn(
                    (
                        "edit_file",
                        {
                            "path": "migrations/0001_initial.py",
                            "old_string": "# generated",
                            "new_string": "# hand edited",
                        },
                    )
                ),
                tool_turn(("write_file", {"path": "models.py", "content": "class User: ...\n"})),
                text_turn("Updated the model instead of the migration."),
            ]
        )
        options = AgentOptions(
            mode=ApprovalMode.AUTO_EDIT, extra_gates=[protect_migrations], audit=False
        )
        options.events.subscribe(ConsoleRenderer(sys.stdout))
        result = build_agent(root, provider, options).run("Add a User model")
        print(format_result(result))
        untouched = (root / "migrations" / "0001_initial.py").read_text() == "# generated\n"
        return 0 if result.ok and untouched else 1


if __name__ == "__main__":
    raise SystemExit(main())
