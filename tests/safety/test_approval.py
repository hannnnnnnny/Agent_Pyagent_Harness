import io

import pytest

from pyagent.safety.approval import (
    ApprovalRequest,
    Choice,
    ConsoleApprover,
    ScriptedApprover,
    deny_all,
)

SHELL = ApprovalRequest("run_shell", {"command": "rm build.log"}, "rm can destroy data")


def test_summary_formats() -> None:
    assert SHELL.summary() == "run: rm build.log"
    assert ApprovalRequest("write_file", {"path": "a.py"}, "").summary() == "write_file: a.py"
    assert ApprovalRequest("x", {"b": 1}, "").summary() == 'x: {"b": 1}'


def test_deny_all() -> None:
    decision = deny_all(SHELL)
    assert not decision.approved
    assert decision.note


def test_scripted_approver_replays_then_denies() -> None:
    approver = ScriptedApprover([Choice.APPROVE_ONCE])
    assert approver(SHELL).approved
    assert not approver(SHELL).approved
    assert approver.seen == [SHELL, SHELL]


def _console(answer: str) -> tuple[ConsoleApprover, io.StringIO]:
    out = io.StringIO()
    return ConsoleApprover(stdin=io.StringIO(answer + "\n"), stdout=out), out


@pytest.mark.parametrize(
    ("answer", "choice"),
    [
        ("y", Choice.APPROVE_ONCE),
        ("YES", Choice.APPROVE_ONCE),
        ("a", Choice.APPROVE_SESSION),
        ("always", Choice.APPROVE_SESSION),
        ("n", Choice.DENY),
        ("", Choice.DENY),
        ("yep", Choice.DENY),
    ],
)
def test_console_answers(answer: str, choice: Choice) -> None:
    approver, out = _console(answer)
    assert approver(SHELL).choice is choice
    assert "run: rm build.log" in out.getvalue()
    assert "rm can destroy data" in out.getvalue()


def test_console_denial_note_is_captured() -> None:
    approver, _ = _console("n use git clean instead")
    decision = approver(SHELL)
    assert decision.note == "use git clean instead"
