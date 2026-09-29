"""Asking a human (or a stand-in) whether a risky action may proceed."""

from __future__ import annotations

import enum
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TextIO


class Choice(enum.Enum):
    APPROVE_ONCE = "once"
    APPROVE_SESSION = "session"
    DENY = "deny"


@dataclass(frozen=True)
class ApprovalRequest:
    tool_name: str
    args: dict[str, Any]
    reason: str

    def summary(self) -> str:
        if self.tool_name == "run_shell":
            return f"run: {self.args.get('command', '')}"
        if "path" in self.args:
            return f"{self.tool_name}: {self.args['path']}"
        return f"{self.tool_name}: {json.dumps(self.args, sort_keys=True)[:200]}"


@dataclass(frozen=True)
class ApprovalDecision:
    choice: Choice
    note: str = ""
    # False when no human was consulted (e.g. deny_all), so messages don't
    # misattribute an automatic denial to the user.
    by_user: bool = True

    @property
    def approved(self) -> bool:
        return self.choice is not Choice.DENY


class Approver(Protocol):
    def __call__(self, request: ApprovalRequest) -> ApprovalDecision: ...


def deny_all(request: ApprovalRequest) -> ApprovalDecision:
    """Default for non-interactive use: nothing risky runs without a human."""
    return ApprovalDecision(Choice.DENY, "no approver is configured", by_user=False)


@dataclass
class ScriptedApprover:
    """Replays a fixed list of choices; for tests and scripted runs."""

    choices: list[Choice]
    seen: list[ApprovalRequest] = field(default_factory=list)

    def __call__(self, request: ApprovalRequest) -> ApprovalDecision:
        self.seen.append(request)
        choice = self.choices.pop(0) if self.choices else Choice.DENY
        return ApprovalDecision(choice)


@dataclass
class ConsoleApprover:
    """Prompts on a terminal. Anything other than an explicit yes is a denial."""

    stdin: TextIO
    stdout: TextIO
    ask: Callable[[TextIO], str] = field(default=lambda stream: stream.readline())

    def __call__(self, request: ApprovalRequest) -> ApprovalDecision:
        self.stdout.write(
            f"\n[approval needed] {request.summary()}\n"
            f"  reason: {request.reason}\n"
            "  allow? [y]es once / [a]lways this session / [N]o (optionally: n <why>): "
        )
        self.stdout.flush()
        answer = self.ask(self.stdin).strip()
        head, _, note = answer.partition(" ")
        if head.lower() in {"y", "yes"}:
            return ApprovalDecision(Choice.APPROVE_ONCE)
        if head.lower() in {"a", "always"}:
            return ApprovalDecision(Choice.APPROVE_SESSION)
        return ApprovalDecision(Choice.DENY, note.strip())
