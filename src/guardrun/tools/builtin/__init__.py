"""Built-in tools shipped with guardrun."""

from guardrun.safety.command_policy import CommandPolicy
from guardrun.tools.base import Tool
from guardrun.tools.builtin.edit_file import EditFile
from guardrun.tools.builtin.glob import Glob
from guardrun.tools.builtin.grep import Grep
from guardrun.tools.builtin.list_dir import ListDir
from guardrun.tools.builtin.multi_edit import MultiEdit
from guardrun.tools.builtin.read_file import ReadFile
from guardrun.tools.builtin.run_shell import RunShell
from guardrun.tools.builtin.todo import Todo
from guardrun.tools.builtin.write_file import WriteFile


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
