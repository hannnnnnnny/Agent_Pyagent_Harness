import pytest

from pyagent.safety.modes import ApprovalMode, effective_verdict, mode_assessment
from pyagent.safety.verdict import Assessment, Verdict
from pyagent.tools.base import Risk

A, Q, B = Verdict.ALLOW, Verdict.ASK, Verdict.BLOCK


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (ApprovalMode.READ_ONLY, {Risk.READ: A, Risk.WRITE: B, Risk.EXECUTE: B, Risk.NETWORK: B}),
        (ApprovalMode.ASK, {Risk.READ: A, Risk.WRITE: Q, Risk.EXECUTE: Q, Risk.NETWORK: Q}),
        (ApprovalMode.AUTO_EDIT, {Risk.READ: A, Risk.WRITE: A, Risk.EXECUTE: A, Risk.NETWORK: Q}),
        (ApprovalMode.UNATTENDED, {Risk.READ: A, Risk.WRITE: A, Risk.EXECUTE: A, Risk.NETWORK: A}),
    ],
)
def test_mode_matrix(mode: ApprovalMode, expected: dict[Risk, Verdict]) -> None:
    assert {risk: mode_assessment(mode, risk).verdict for risk in Risk} == expected


def test_unattended_fails_closed_on_ask() -> None:
    result = effective_verdict(ApprovalMode.UNATTENDED, Assessment.ask("rm"))
    assert result.verdict is Verdict.BLOCK
    assert "unattended" in result.reason


@pytest.mark.parametrize("mode", [ApprovalMode.ASK, ApprovalMode.AUTO_EDIT])
def test_attended_modes_keep_ask(mode: ApprovalMode) -> None:
    assert effective_verdict(mode, Assessment.ask("rm")).verdict is Verdict.ASK


def test_modes_parse_from_config_strings() -> None:
    assert ApprovalMode("auto-edit") is ApprovalMode.AUTO_EDIT
