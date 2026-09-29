from pathlib import Path

import pytest

from pyagent.events import Event, EventBus
from pyagent.messages import ToolCall
from pyagent.safety.approval import Choice, ScriptedApprover
from pyagent.safety.gate import SafetyGate
from pyagent.safety.modes import ApprovalMode
from pyagent.tools.base import ToolContext
from pyagent.tools.builtin import default_tools
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.registry import ToolRegistry


class Harness:
    def __init__(self, root: Path, mode: ApprovalMode, choices: list[Choice]) -> None:
        self.ctx = ToolContext.for_root(root)
        self.approver = ScriptedApprover(list(choices))
        self.events: list[Event] = []
        bus = EventBus()
        bus.subscribe(self.events.append)
        self.gate = SafetyGate(self.ctx, mode, self.approver, bus)
        self.executor = ToolExecutor(ToolRegistry(default_tools()), self.ctx, gates=[self.gate])

    def call(self, name: str, **args: object) -> tuple[bool, str]:
        result = self.executor.execute(ToolCall("id", name, dict(args)))
        return (not result.is_error, result.content)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "a.txt").write_text("hello")
    return tmp_path


def test_reads_never_ask(root: Path) -> None:
    h = Harness(root, ApprovalMode.ASK, [])
    ok, _ = h.call("read_file", path="a.txt")
    assert ok
    assert h.approver.seen == []


def test_ask_mode_requests_approval_for_writes(root: Path) -> None:
    h = Harness(root, ApprovalMode.ASK, [Choice.APPROVE_ONCE])
    ok, _ = h.call("write_file", path="b.txt", content="x")
    assert ok
    assert h.approver.seen[0].tool_name == "write_file"


def test_denial_is_reported_to_the_model(root: Path) -> None:
    h = Harness(root, ApprovalMode.ASK, [Choice.DENY])
    ok, content = h.call("write_file", path="b.txt", content="x")
    assert not ok
    assert "declined" in content
    assert not (root / "b.txt").exists()


def test_read_only_mode_blocks_without_asking(root: Path) -> None:
    h = Harness(root, ApprovalMode.READ_ONLY, [Choice.APPROVE_ONCE])
    ok, content = h.call("write_file", path="b.txt", content="x")
    assert not ok
    assert "read-only" in content
    assert h.approver.seen == []


def test_auto_edit_allows_writes_but_asks_for_risky_commands(root: Path) -> None:
    h = Harness(root, ApprovalMode.AUTO_EDIT, [Choice.DENY])
    assert h.call("write_file", path="b.txt", content="x")[0]
    assert h.call("run_shell", command="ls")[0]
    ok, _ = h.call("run_shell", command="rm b.txt")
    assert not ok
    assert (root / "b.txt").exists()
    assert len(h.approver.seen) == 1


def test_policy_block_cannot_be_approved(root: Path) -> None:
    h = Harness(root, ApprovalMode.AUTO_EDIT, [Choice.APPROVE_SESSION])
    ok, content = h.call("run_shell", command="sudo id")
    assert not ok
    assert "privilege" in content
    assert h.approver.seen == []


def test_unattended_denies_anything_needing_approval(root: Path) -> None:
    h = Harness(root, ApprovalMode.UNATTENDED, [Choice.APPROVE_ONCE])
    ok, content = h.call("run_shell", command="rm a.txt")
    assert not ok
    assert "unattended" in content
    assert h.approver.seen == []


def test_session_approval_is_scoped_to_exact_input(root: Path) -> None:
    h = Harness(root, ApprovalMode.ASK, [Choice.APPROVE_SESSION, Choice.DENY])
    assert h.call("write_file", path="b.txt", content="x")[0]
    assert h.call("write_file", path="b.txt", content="x")[0]
    assert not h.call("write_file", path="b.txt", content="different")[0]
    assert len(h.approver.seen) == 2


def test_events_are_emitted(root: Path) -> None:
    h = Harness(root, ApprovalMode.ASK, [Choice.APPROVE_ONCE])
    h.call("write_file", path="b.txt", content="x")
    h.call("run_shell", command="sudo id")
    assert [e.kind for e in h.events] == [
        "approval_requested",
        "approval_decided",
        "action_blocked",
    ]
