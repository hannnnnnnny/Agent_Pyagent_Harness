import sys

import pytest

from pyagent.safety.command_policy import CommandPolicy
from pyagent.safety.verdict import Verdict
from pyagent.tools.base import Risk
from pyagent.tools.builtin.run_shell import RunShell
from tests.tools.conftest import Runner

PY = sys.executable.replace("\\", "/")
tool = RunShell()


def test_is_an_execute_risk() -> None:
    assert tool.risk is Risk.EXECUTE


def test_runs_in_workspace_and_reports_exit_code(run: Runner) -> None:
    (run.root / "hello.txt").write_text("hi")
    result = run(tool, command="ls")
    assert result.content.startswith("[exit code 0]")
    assert "hello.txt" in result.content


def test_failure_exit_code_is_reported(run: Runner) -> None:
    result = run(tool, command=f'"{PY}" -c "raise SystemExit(2)"')
    assert result.content.startswith("[exit code 2]")


def test_secrets_are_not_inherited(run: Runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-leak")
    code = "import os; print(os.environ.get('ANTHROPIC_API_KEY'), os.environ.get('PYAGENT'))"
    result = run(tool, command=f'"{PY}" -c "{code}"')
    assert "sk-ant-should-not-leak" not in result.content
    assert "None 1" in result.content


def test_timeout_is_reported(run: Runner) -> None:
    result = run(tool, command=f'"{PY}" -c "import time; time.sleep(20)"', timeout=1)
    assert "timed out" in result.content


def test_assess_delegates_to_policy(run: Runner) -> None:
    assert tool.assess({"command": "sudo id"}, run.ctx).verdict is Verdict.BLOCK
    assert tool.assess({"command": "git status"}, run.ctx).verdict is Verdict.ALLOW


def test_custom_policy(run: Runner) -> None:
    custom = RunShell(CommandPolicy(allow_prefixes=("make test",)))
    assert custom.assess({"command": "make test"}, run.ctx).verdict is Verdict.ALLOW


def test_timeout_bounds_enforced_by_schema(run: Runner) -> None:
    assert "invalid input" in run(tool, command="ls", timeout=100000).content
