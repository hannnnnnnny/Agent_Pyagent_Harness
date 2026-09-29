"""Built-in tools shipped with pyagent."""

from pyagent.safety.command_policy import CommandPolicy
from pyagent.tools.base import Tool
from pyagent.tools.builtin.edit_file import EditFile
from pyagent.tools.builtin.glob import Glob
from pyagent.tools.builtin.grep import Grep
from pyagent.tools.builtin.list_dir import ListDir
from pyagent.tools.builtin.multi_edit import MultiEdit
from pyagent.tools.builtin.read_file import ReadFile
from pyagent.tools.builtin.run_shell import RunShell
from pyagent.tools.builtin.todo import Todo
from pyagent.tools.builtin.write_file import WriteFile


def read_only_tools() -> list[Tool]:
    """Tools that can inspect but never modify the workspace."""
    return [ReadFile(), ListDir(), Glob(), Grep(), Todo()]


def file_tools() -> list[Tool]:
    """Every file tool, including ones that write."""
    return [*read_only_tools(), WriteFile(), EditFile(), MultiEdit()]


def default_tools(policy: CommandPolicy | None = None) -> list[Tool]:
    """File tools plus a policy-checked shell."""
    return [*file_tools(), RunShell(policy)]


__all__ = [
    "EditFile",
    "Glob",
    "Grep",
    "ListDir",
    "MultiEdit",
    "ReadFile",
    "RunShell",
    "Todo",
    "WriteFile",
    "default_tools",
    "file_tools",
    "read_only_tools",
]
