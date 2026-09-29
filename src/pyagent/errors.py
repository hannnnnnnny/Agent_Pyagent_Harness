"""Exception hierarchy for pyagent.

Every error raised by the harness derives from :class:`PyAgentError` so callers
can catch harness failures without swallowing unrelated exceptions.
"""

from __future__ import annotations


class PyAgentError(Exception):
    """Base class for all pyagent errors."""


class ConfigError(PyAgentError):
    """Raised when configuration is missing or invalid."""


class ToolError(PyAgentError):
    """Raised by a tool when it cannot complete; reported back to the model."""


class ToolInputError(ToolError):
    """Raised when tool input fails schema validation."""


class SafetyError(PyAgentError):
    """Base class for refusals made by the safety layer."""


class SandboxViolation(SafetyError):
    """Raised when an action would touch something outside the workspace."""


class PolicyViolation(SafetyError):
    """Raised when a command or action is blocked by policy."""


class ApprovalDenied(SafetyError):
    """Raised when a human (or approval policy) declines an action."""


class BudgetExceeded(PyAgentError):
    """Raised when a run exceeds its turn, token, or cost budget."""


class ProviderError(PyAgentError):
    """Raised when the model provider fails in a way the loop cannot recover from."""
