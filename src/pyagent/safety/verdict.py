"""The shared vocabulary for safety decisions."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Verdict(enum.IntEnum):
    """Ordered so the strictest of several verdicts is simply ``max``."""

    ALLOW = 0
    ASK = 1
    BLOCK = 2


@dataclass(frozen=True)
class Assessment:
    """A verdict plus the human-readable reason behind it."""

    verdict: Verdict
    reason: str = ""

    @classmethod
    def allow(cls, reason: str = "") -> Assessment:
        return cls(Verdict.ALLOW, reason)

    @classmethod
    def ask(cls, reason: str) -> Assessment:
        return cls(Verdict.ASK, reason)

    @classmethod
    def block(cls, reason: str) -> Assessment:
        return cls(Verdict.BLOCK, reason)


def strictest(assessments: list[Assessment]) -> Assessment:
    """Combine assessments, keeping the most restrictive one."""
    if not assessments:
        return Assessment.allow()
    return max(assessments, key=lambda a: a.verdict)
