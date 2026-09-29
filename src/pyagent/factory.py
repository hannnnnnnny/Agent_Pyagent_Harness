"""Assemble a fully wired, safe-by-default agent."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from pyagent.agent import Agent
from pyagent.budget import Budget
from pyagent.events import EventBus
from pyagent.prompts import build_system_prompt
from pyagent.providers.base import Provider
from pyagent.safety.approval import Approver, deny_all
from pyagent.safety.audit import AuditLog
from pyagent.safety.command_policy import CommandPolicy
from pyagent.safety.gate import SafetyGate
from pyagent.safety.injection import make_injection_filter
from pyagent.safety.modes import ApprovalMode
from pyagent.safety.protected import ProtectedPaths
from pyagent.safety.redact import Redactor
from pyagent.safety.workspace import Workspace
from pyagent.tools.base import Tool, ToolContext
from pyagent.tools.builtin import default_tools
from pyagent.tools.registry import ToolRegistry

STATE_DIR = ".pyagent"


@dataclass
class AgentOptions:
    """Everything configurable about an agent, with conservative defaults."""

    mode: ApprovalMode = ApprovalMode.ASK
    approver: Approver = deny_all
    budget: Budget = field(default_factory=Budget)
    command_policy: CommandPolicy = field(default_factory=CommandPolicy)
    protected: ProtectedPaths = field(default_factory=ProtectedPaths)
    extra_tools: list[Tool] = field(default_factory=list)
    instructions: str = ""
    audit: bool = True
    events: EventBus = field(default_factory=EventBus)


def build_agent(root: Path | str, provider: Provider, options: AgentOptions | None = None) -> Agent:
    """Wire tools, the safety gate, redaction, injection flagging, and auditing."""
    opts = options or AgentOptions()
    workspace = Workspace(root, opts.protected)
    ctx = ToolContext(workspace=workspace)
    redactor = Redactor.from_environment(os.environ)
    if opts.audit:
        run_id = uuid.uuid4().hex[:12]
        audit_path = workspace.root / STATE_DIR / "audit.jsonl"
        opts.events.subscribe(AuditLog(audit_path, redactor, run_id))
    injection_filter = make_injection_filter(
        lambda phrase: opts.events.emit("injection_suspected", phrase=phrase)
    )
    tools = ToolRegistry([*default_tools(opts.command_policy), *opts.extra_tools])
    gate = SafetyGate(ctx, opts.mode, opts.approver, opts.events)
    return Agent(
        provider,
        tools,
        ctx,
        gates=[gate],
        output_filters=[redactor.redact, injection_filter],
        system_prompt=build_system_prompt(opts.instructions),
        budget=opts.budget,
        events=opts.events,
    )
