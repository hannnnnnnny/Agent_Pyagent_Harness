"""The safety gate: the single place a tool call is allowed, asked about, or blocked."""

from __future__ import annotations

import json

from pyagent.errors import ApprovalDenied, PolicyViolation
from pyagent.events import EventBus
from pyagent.messages import ToolCall
from pyagent.safety.approval import (
    ApprovalDecision,
    ApprovalRequest,
    Approver,
    Choice,
    deny_all,
)
from pyagent.safety.modes import ApprovalMode, effective_verdict, mode_assessment
from pyagent.safety.verdict import Verdict, strictest
from pyagent.tools.base import Tool, ToolContext


def _denial_message(decision: ApprovalDecision) -> str:
    if not decision.by_user:
        return f"this action needs approval, but none was available ({decision.note})"
    note = f" (user said: {decision.note})" if decision.note else ""
    return f"the user declined this action{note}"


def _session_key(tool: Tool, call: ToolCall) -> str:
    return f"{tool.name}:{json.dumps(call.input, sort_keys=True)}"


class SafetyGate:
    """An executor gate combining the approval mode, the tool's own assessment,
    and (when needed) a human decision.

    Session approvals are keyed by the exact tool input, so approving
    ``rm a.txt`` once "for the session" never approves ``rm -r src``.
    """

    def __init__(
        self,
        ctx: ToolContext,
        mode: ApprovalMode = ApprovalMode.ASK,
        approver: Approver = deny_all,
        events: EventBus | None = None,
    ) -> None:
        self.ctx = ctx
        self.mode = mode
        self.approver = approver
        self.events = events or EventBus()
        self._session_approved: set[str] = set()

    def __call__(self, tool: Tool, call: ToolCall) -> None:
        combined = strictest(
            [mode_assessment(self.mode, tool.risk), tool.assess(call.input, self.ctx)]
        )
        assessment = effective_verdict(self.mode, combined)
        if assessment.verdict is Verdict.BLOCK:
            self.events.emit("action_blocked", tool=tool.name, reason=assessment.reason)
            raise PolicyViolation(assessment.reason)
        if assessment.verdict is Verdict.ALLOW:
            return
        key = _session_key(tool, call)
        if key in self._session_approved:
            return
        request = ApprovalRequest(tool.name, call.input, assessment.reason)
        self.events.emit("approval_requested", tool=tool.name, reason=assessment.reason)
        decision = self.approver(request)
        self.events.emit("approval_decided", tool=tool.name, choice=decision.choice.value)
        if not decision.approved:
            raise ApprovalDenied(_denial_message(decision))
        if decision.choice is Choice.APPROVE_SESSION:
            self._session_approved.add(key)
