"""Known ways of escaping a workspace sandbox. Every one must stay blocked.

These go through the real tools and executor, so a regression anywhere in the
chain (validation, gate, workspace, protected paths) fails here.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyagent.messages import ToolCall
from pyagent.safety.gate import SafetyGate
from pyagent.safety.modes import ApprovalMode
from pyagent.tools.base import ToolContext
from pyagent.tools.builtin import file_tools
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.registry import ToolRegistry

# A canary string; seeing it in any tool output means a sandbox leak.
CANARY = "TOP-SECRET-CANARY"


@pytest.fixture
def setup(tmp_path: Path) -> tuple[ToolExecutor, Path]:
    root = tmp_path / "work"
    root.mkdir()
    (tmp_path / "outside.txt").write_text(CANARY)
    (root / ".env").write_text(f"KEY={CANARY}")
    (root / "keys").mkdir()
    (root / "keys" / "server.pem").write_text(CANARY)
    ctx = ToolContext.for_root(root)
    # Unattended: nothing can be approved, so only genuinely allowed calls run.
    gate = SafetyGate(ctx, ApprovalMode.UNATTENDED)
    return ToolExecutor(ToolRegistry(file_tools()), ctx, gates=[gate]), tmp_path


READ_ATTEMPTS = [
    "../outside.txt",
    "..\\outside.txt",
    "./../outside.txt",
    "keys/../../outside.txt",
    "%s/outside.txt",
    ".env",
    "./.env",
    "keys/../.env",
    ".ENV",
    "keys/server.pem",
    "KEYS/SERVER.PEM",
    ".env\x00.txt",
    "~/.ssh/id_rsa",
    ".env:$DATA",
]


@pytest.mark.parametrize("path", READ_ATTEMPTS)
def test_read_attempts_never_leak(setup: tuple[ToolExecutor, Path], path: str) -> None:
    executor, tmp = setup
    if "%s" in path:
        path = path % tmp.as_posix()
    result = executor.execute(ToolCall("x", "read_file", {"path": path}))
    assert result.is_error
    assert CANARY not in result.content


@pytest.mark.parametrize("pattern", ["**/*", "**/.env*", "**/*.pem", ".*"])
def test_discovery_tools_hide_secrets(setup: tuple[ToolExecutor, Path], pattern: str) -> None:
    executor, _ = setup
    result = executor.execute(ToolCall("x", "glob", {"pattern": pattern}))
    assert ".env" not in result.content
    assert "server.pem" not in result.content


def test_grep_cannot_read_secret_contents(setup: tuple[ToolExecutor, Path]) -> None:
    executor, _ = setup
    result = executor.execute(ToolCall("x", "grep", {"pattern": "SECRET", "ignore_case": True}))
    assert CANARY not in result.content


def test_grep_cannot_search_outside(setup: tuple[ToolExecutor, Path]) -> None:
    executor, _ = setup
    result = executor.execute(ToolCall("x", "grep", {"pattern": "CANARY", "path": ".."}))
    assert result.is_error
    assert CANARY not in result.content


@pytest.mark.parametrize(
    "path",
    ["../planted.txt", ".git/hooks/pre-commit", ".GIT/config", ".pyagent/audit.jsonl", ".env"],
)
def test_write_attempts_are_refused(setup: tuple[ToolExecutor, Path], path: str) -> None:
    executor, tmp = setup
    result = executor.execute(ToolCall("x", "write_file", {"path": path, "content": "pwned"}))
    assert result.is_error
    assert not (tmp / "planted.txt").exists()


def _try_symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted on this platform")


def test_symlinked_directory_escape(setup: tuple[ToolExecutor, Path]) -> None:
    executor, tmp = setup
    _try_symlink(tmp / "work" / "door", tmp)
    for path in ("door/outside.txt", "door"):
        result = executor.execute(ToolCall("x", "read_file", {"path": path}))
        assert CANARY not in result.content
    listing = executor.execute(ToolCall("x", "glob", {"pattern": "**/*"}))
    assert "outside.txt" not in listing.content


def test_symlink_to_secret_inside_workspace(setup: tuple[ToolExecutor, Path]) -> None:
    executor, tmp = setup
    _try_symlink(tmp / "work" / "readme.txt", tmp / "work" / ".env")
    result = executor.execute(ToolCall("x", "read_file", {"path": "readme.txt"}))
    assert CANARY not in result.content


@pytest.mark.skipif(os.name != "nt", reason="Windows path forms")
@pytest.mark.parametrize("path", ["\\\\?\\C:\\Windows\\win.ini", "C:..\\outside.txt", "NUL"])
def test_windows_specific_forms(setup: tuple[ToolExecutor, Path], path: str) -> None:
    executor, _ = setup
    result = executor.execute(ToolCall("x", "read_file", {"path": path}))
    assert result.is_error
