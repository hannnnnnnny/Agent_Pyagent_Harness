import pytest

from pyagent import errors


@pytest.mark.parametrize(
    "exc",
    [
        errors.ConfigError,
        errors.ToolError,
        errors.ToolInputError,
        errors.SandboxViolation,
        errors.PolicyViolation,
        errors.ApprovalDenied,
        errors.BudgetExceeded,
        errors.ProviderError,
    ],
)
def test_all_errors_derive_from_base(exc: type[Exception]) -> None:
    assert issubclass(exc, errors.PyAgentError)


def test_safety_errors_share_a_base() -> None:
    for exc in (errors.SandboxViolation, errors.PolicyViolation, errors.ApprovalDenied):
        assert issubclass(exc, errors.SafetyError)


def test_tool_input_error_is_a_tool_error() -> None:
    assert issubclass(errors.ToolInputError, errors.ToolError)
