from pyagent.tools.base import Risk
from pyagent.tools.builtin import file_tools, read_only_tools
from pyagent.tools.registry import ToolRegistry


def test_read_only_set_never_writes() -> None:
    assert all(tool.risk is Risk.READ for tool in read_only_tools())


def test_file_tools_register_cleanly() -> None:
    registry = ToolRegistry(file_tools())
    assert sorted(t.name for t in registry) == [
        "edit_file",
        "glob",
        "grep",
        "list_dir",
        "read_file",
        "write_file",
    ]
