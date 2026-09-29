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
