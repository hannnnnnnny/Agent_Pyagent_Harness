"""Summaries of past runs, computed from the audit log."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pyagent.usage import Usage


@dataclass
class RunSummary:
    run_id: str
    started: str = ""
    task: str = ""
    stop: str = "unfinished"
    turns: int = 0
    usage: Usage = field(default_factory=Usage)
    cost_usd: float | None = None
    tools: Counter[str] = field(default_factory=Counter)
    tool_errors: int = 0
    blocked: int = 0


def _usage_from(data: dict[str, Any]) -> Usage:
    raw = data.get("usage") or {}
    return Usage(
        input_tokens=int(raw.get("input_tokens", 0)),
        output_tokens=int(raw.get("output_tokens", 0)),
        cache_read_input_tokens=int(raw.get("cache_read_input_tokens", 0)),
        cache_creation_input_tokens=int(raw.get("cache_creation_input_tokens", 0)),
    )


def _apply(summary: RunSummary, record: dict[str, Any]) -> None:
    kind, data = record.get("kind"), record.get("data") or {}
    if kind == "run_started":
        summary.started = record.get("ts", "")
        summary.task = str(data.get("task", ""))
    elif kind == "tool_finished":
        summary.tools[str(data.get("tool", "?"))] += 1
        summary.tool_errors += bool(data.get("is_error"))
    elif kind == "action_blocked":
        summary.blocked += 1
    elif kind == "run_finished":
        summary.stop = str(data.get("stop", "unknown"))
        summary.turns = int(data.get("turns", 0))
        summary.usage = _usage_from(data)
        cost = data.get("cost_usd")
        summary.cost_usd = float(cost) if isinstance(cost, (int, float)) else None


def summarize_runs(records: list[dict[str, Any]]) -> list[RunSummary]:
    """Group audit records by run id, oldest run first.

    Several ``Agent.run`` calls can share one audit run id (e.g. a chat
    session), so a new ``run_started`` under the same id starts a new summary.
    """
    summaries: list[RunSummary] = []
    current: dict[str, RunSummary] = {}
    for record in records:
        run_id = str(record.get("run", ""))
        if record.get("kind") == "run_started" or run_id not in current:
            current[run_id] = RunSummary(run_id)
            summaries.append(current[run_id])
        _apply(current[run_id], record)
    return summaries
