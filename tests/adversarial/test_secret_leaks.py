"""End-to-end: secrets must not reach the model or the audit log.

The agent is driven by a scripted "malicious" model that tries several ways
of surfacing credentials. Everything sent back to the model and everything
written to the audit log is then searched for the secret values.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pyagent.factory import STATE_DIR, AgentOptions, build_agent
from pyagent.messages import ModelResponse
from pyagent.providers.scripted import ScriptedProvider, text_turn, tool_turn
from pyagent.safety.command_policy import CommandPolicy
from pyagent.safety.modes import ApprovalMode

ENV_SECRET = "env-canary-9f8e7d6c5b4a"
FILE_SECRET = "ghp_" + "Z" * 36
PY = sys.executable.replace("\\", "/")


def attack_turns() -> list[ModelResponse]:
    print_env = "import os; print(dict(os.environ))"
    return [
        tool_turn(("read_file", {"path": ".env"})),
        tool_turn(("read_file", {"path": "notes.md"})),
        tool_turn(("grep", {"pattern": "ghp_"})),
        tool_turn(("run_shell", {"command": "env"})),
        tool_turn(("run_shell", {"command": f'"{PY}" -c "{print_env}"'})),
        tool_turn(("run_shell", {"command": "cat notes.md"})),
        text_turn("done"),
    ]


@pytest.fixture
def leaked_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("SERVICE_API_KEY", ENV_SECRET)
    (tmp_path / ".env").write_text(f"SERVICE_API_KEY={ENV_SECRET}\n")
    (tmp_path / "notes.md").write_text(f"deploy token: {FILE_SECRET}\n")
    provider = ScriptedProvider(attack_turns())
    options = AgentOptions(
        mode=ApprovalMode.UNATTENDED,
        command_policy=_permissive_shell(),
    )
    build_agent(tmp_path, provider, options).run("gather credentials")
    sent_to_model = "".join(str(r.messages) for r in provider.requests)
    audit = (tmp_path / STATE_DIR / "audit.jsonl").read_text(encoding="utf-8")
    return sent_to_model + audit


def _permissive_shell() -> CommandPolicy:
    # Pre-approve the probing commands so the test exercises redaction and
    # environment scrubbing rather than the approval layer.
    return CommandPolicy(allow_prefixes=("env", PY.split("/")[-1], f'"{PY}"', "cat"))


def test_environment_secret_never_leaks(leaked_text: str) -> None:
    assert ENV_SECRET not in leaked_text


def test_token_in_a_normal_file_is_redacted(leaked_text: str) -> None:
    assert FILE_SECRET not in leaked_text
    assert "[REDACTED]" in leaked_text


def test_the_attack_actually_ran_commands(leaked_text: str) -> None:
    # Guards against a vacuous pass: the probes must really have executed.
    assert leaked_text.count("[exit code 0]") >= 3
