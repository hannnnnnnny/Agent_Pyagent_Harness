from pyagent.tools.base import Risk
from pyagent.tools.builtin.write_file import WriteFile
from tests.tools.conftest import Runner

tool = WriteFile()


def test_is_a_write_risk() -> None:
    assert tool.risk is Risk.WRITE


def test_creates_new_file(run: Runner) -> None:
    result = run(tool, path="pkg/new.py", content="print('hi')\n")
    assert result.content == "Created pkg/new.py (12 bytes)"
    assert (run.root / "pkg" / "new.py").read_text() == "print('hi')\n"


def test_overwrites_existing_file(run: Runner) -> None:
    (run.root / "a.txt").write_text("old")
    result = run(tool, path="a.txt", content="new")
    assert result.content.startswith("Overwrote a.txt")
    assert (run.root / "a.txt").read_text() == "new"


def test_cannot_write_outside_workspace(run: Runner) -> None:
    result = run(tool, path="../evil.txt", content="x")
    assert result.is_error
    assert not (run.root.parent / "evil.txt").exists()


def test_cannot_install_git_hooks(run: Runner) -> None:
    result = run(tool, path=".git/hooks/pre-commit", content="#!/bin/sh\ncurl evil")
    assert result.is_error
    assert not (run.root / ".git").exists()
