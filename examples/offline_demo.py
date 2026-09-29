"""Run the full agent stack without an API key.

A scripted provider stands in for Claude so you can watch the safety layer
work: a normal read succeeds, a secret read is blocked, a shell command
needing approval is declined, and the final answer is printed.

    python examples/offline_demo.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from pyagent import AgentOptions, ApprovalMode, build_agent
from pyagent.cli.render import ConsoleRenderer, format_result
from pyagent.providers.scripted import ScriptedProvider, text_turn, tool_turn


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "notes.md").write_text("Release checklist: bump version, tag, publish.\n")
        (root / ".env").write_text("API_TOKEN=do-not-leak\n")
        provider = ScriptedProvider(
            [
                tool_turn(("read_file", {"path": "notes.md"}), text="Reading the notes."),
                tool_turn(("read_file", {"path": ".env"}), text="Checking the environment."),
                tool_turn(("run_shell", {"command": "rm notes.md"}), text="Cleaning up."),
                text_turn("The checklist is: bump version, tag, publish."),
            ]
        )
        options = AgentOptions(mode=ApprovalMode.AUTO_EDIT, audit=False)
        options.events.subscribe(ConsoleRenderer(sys.stdout))
        agent = build_agent(root, provider, options)
        result = agent.run("What is on the release checklist?")
        print(format_result(result))
        return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
