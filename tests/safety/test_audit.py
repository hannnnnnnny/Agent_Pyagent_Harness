import os
import stat
import sys
from pathlib import Path

import pytest

from pyagent.events import EventBus
from pyagent.safety.audit import AuditLog, read_audit
from pyagent.safety.redact import Redactor


def test_records_are_appended_as_jsonl(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "logs" / "audit.jsonl", run_id="r1")
    log.record("tool_started", {"tool": "ls"})
    log.record("tool_finished", {"ok": True})
    records = read_audit(log.path)
    assert [r["kind"] for r in records] == ["tool_started", "tool_finished"]
    assert records[0]["run"] == "r1"
    assert records[0]["data"] == {"tool": "ls"}
    assert records[0]["ts"].endswith("+00:00")


def test_secrets_are_redacted_in_the_log(tmp_path: Path) -> None:
    redactor = Redactor()
    redactor.add_secrets(["super-secret-value"])
    log = AuditLog(tmp_path / "audit.jsonl", redactor=redactor)
    log.record("tool_finished", {"output": "token is super-secret-value"})
    assert "super-secret-value" not in log.path.read_text()


def test_subscribes_to_event_bus(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    bus = EventBus()
    bus.subscribe(log)
    bus.emit("approval_requested", tool="run_shell")
    assert read_audit(log.path)[0]["data"] == {"tool": "run_shell"}


def test_non_json_values_are_stringified(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record("x", {"path": Path("a"), "items": (1, 2)})
    data = read_audit(log.path)[0]["data"]
    assert data["items"] == [1, 2]
    assert "a" in data["path"]


def test_existing_log_is_appended_not_truncated(tmp_path: Path) -> None:
    AuditLog(tmp_path / "audit.jsonl").record("first", {})
    AuditLog(tmp_path / "audit.jsonl").record("second", {})
    assert len(read_audit(tmp_path / "audit.jsonl")) == 2


def test_missing_log_reads_as_empty(tmp_path: Path) -> None:
    assert read_audit(tmp_path / "none.jsonl") == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions only")
def test_log_is_private(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    assert stat.S_IMODE(os.stat(log.path).st_mode) == 0o600
