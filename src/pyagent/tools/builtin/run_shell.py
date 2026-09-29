"""run_shell: execute a vetted shell command inside the workspace."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from pyagent.safety.command_policy import CommandPolicy
from pyagent.safety.env import DEFAULT_PASSTHROUGH, scrub_env
from pyagent.safety.process import DEFAULT_TIMEOUT_SECONDS, run_command
from pyagent.safety.verdict import Assessment
from pyagent.tools.base import Risk, Tool, ToolContext

MAX_TIMEOUT_SECONDS = 600


class RunShell(Tool):
    name = "run_shell"
    description = (
        "Run a shell command (POSIX sh syntax) with the workspace root as the working "
        "directory. stdin is closed, secrets are removed from the environment, and "
        "commands are checked against a safety policy; risky ones need user approval. "
        "Returns the exit code and combined stdout/stderr."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "minLength": 1, "maxLength": 10000},
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_TIMEOUT_SECONDS,
                "description": f"Seconds before the command is killed. Default "
                f"{DEFAULT_TIMEOUT_SECONDS}.",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }
    risk = Risk.EXECUTE

    def __init__(
        self,
        policy: CommandPolicy | None = None,
        env_passthrough: Iterable[str] = DEFAULT_PASSTHROUGH,
    ) -> None:
        self.policy = policy or CommandPolicy()
        self.env_passthrough = frozenset(env_passthrough)

    def assess(self, args: dict[str, Any], ctx: ToolContext) -> Assessment:
        return self.policy.assess(args["command"], ctx.workspace)

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        env = scrub_env(os.environ, self.env_passthrough, extra={"PYAGENT": "1"})
        result = run_command(
            args["command"],
            ctx.workspace.root,
            env,
            timeout=args.get("timeout", DEFAULT_TIMEOUT_SECONDS),
        )
        status = "timed out and was killed" if result.timed_out else f"exit code {result.exit_code}"
        return f"[{status}]\n{result.output}".rstrip()
