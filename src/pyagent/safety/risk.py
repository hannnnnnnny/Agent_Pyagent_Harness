"""Risk levels shared by tools and the safety layer."""

from __future__ import annotations

import enum


class Risk(enum.Enum):
    """How much damage a tool can do; drives approval decisions."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
