"""Human-readable progress output for terminal runs."""

from __future__ import annotations

import dataclasses
import json
from typing import Any, TextIO

from pyagent.agent import RunResult
from pyagent.events import Event

PREVIEW_CHARS = 160


def _preview(value: Any, limit: int = PREVIEW_CHARS) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


class ConsoleRenderer:
    """Subscribes to agent events and prints a compact transcript."""

    def __init__(self, out: TextIO, verbose: bool = False) -> None:
        self.out = out
        self.verbose = verbose

    def __call__(self, event: Event) -> None:
        handler = getattr(self, f"_on_{event.kind}", None)
        if handler is not None:
            handler(event.data)

    def _write(self, line: str) -> None:
        self.out.write(line + "\n")
        self.out.flush()

    def _on_model_responded(self, data: dict[str, Any]) -> None:
        text = str(data.get("text", "")).strip()
        if text and data.get("tool_calls"):
            self._write(f"  {_preview(text)}")

    def _on_tool_started(self, data: dict[str, Any]) -> None:
        self._write(f"> {data['tool']} {_preview(data.get('input', {}))}")

    def _on_tool_finished(self, data: dict[str, Any]) -> None:
        status = "error" if data.get("is_error") else "ok"
        detail = _preview(data.get("output", ""), 1000 if self.verbose else 100)
        self._write(f"  [{status}] {detail}")

    def _on_action_blocked(self, data: dict[str, Any]) -> None:
        self._write(f"  [blocked] {data.get('reason', '')}")

    def _on_injection_suspected(self, data: dict[str, Any]) -> None:
        self._write(f"  [warning] possible prompt injection in tool output: {data.get('phrase')!r}")


def format_result(result: RunResult) -> str:
    """The final answer plus a one-line run summary."""
    lines = [result.text.strip()] if result.text.strip() else []
    cost = f", ~${result.cost_usd:.4f}" if result.cost_usd is not None else ""
    summary = f"[{result.stop}] {result.turns} turns, {result.usage.total_tokens} tokens{cost}"
    if result.detail:
        summary += f" - {result.detail}"
    lines.append(summary)
    return "\n".join(lines)


def result_to_dict(result: RunResult, session_id: str = "") -> dict[str, Any]:
    """A stable, JSON-serializable view of a run for scripts and CI."""
    return {
        "stop": result.stop,
        "ok": result.ok,
        "text": result.text,
        "turns": result.turns,
        "usage": dataclasses.asdict(result.usage),
        "cost_usd": result.cost_usd,
        "detail": result.detail,
        "session": session_id,
    }
