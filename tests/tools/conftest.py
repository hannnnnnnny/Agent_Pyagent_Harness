from pathlib import Path
from typing import Any

import pytest

from pyagent.messages import ToolCall, ToolResult
from pyagent.tools.base import Tool, ToolContext
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.registry import ToolRegistry


class Runner:
    """Runs a tool through the real executor, as the agent loop would."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.ctx = ToolContext.for_root(root)

    def __call__(self, tool: Tool, **args: Any) -> ToolResult:
        executor = ToolExecutor(ToolRegistry([tool]), self.ctx)
        return executor.execute(ToolCall("call", tool.name, args))


@pytest.fixture
def run(tmp_path: Path) -> Runner:
    return Runner(tmp_path)
