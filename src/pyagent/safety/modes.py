"""Approval modes: how much the agent may do without asking."""

from __future__ import annotations

import enum

from pyagent.safety.verdict import Assessment, Verdict
from pyagent.tools.base import Risk


class ApprovalMode(enum.Enum):
    READ_ONLY = "read-only"
    """Only tools that cannot change anything may run."""

    ASK = "ask"
    """Reads run freely; every write, command, or network call needs approval."""

    AUTO_EDIT = "auto-edit"
    """Reads and file edits run freely; commands follow the command policy."""

    UNATTENDED = "unattended"
    """No human is present: policy-approved actions run, anything needing approval is denied."""


def mode_assessment(mode: ApprovalMode, risk: Risk) -> Assessment:
    """What ``mode`` alone says about a tool of the given ``risk``."""
    if risk is Risk.READ:
        return Assessment.allow()
    if mode is ApprovalMode.READ_ONLY:
        return Assessment.block(f"{risk.value} tools are disabled in read-only mode")
    if mode is ApprovalMode.ASK:
        return Assessment.ask(f"{risk.value} actions require approval in ask mode")
    if mode is ApprovalMode.AUTO_EDIT and risk is Risk.NETWORK:
        return Assessment.ask("network access requires approval")
    return Assessment.allow()


def effective_verdict(mode: ApprovalMode, assessment: Assessment) -> Assessment:
    """Apply mode-specific handling of a combined assessment.

    Unattended runs have nobody to ask, so an ASK must fail closed.
    """
    if mode is ApprovalMode.UNATTENDED and assessment.verdict is Verdict.ASK:
        return Assessment.block(f"needs approval but running unattended: {assessment.reason}")
    return assessment
