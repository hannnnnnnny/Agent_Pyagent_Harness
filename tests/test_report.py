from typing import Any

from pyagent.report import summarize_runs
from pyagent.usage import Usage


def rec(run: str, kind: str, **data: Any) -> dict[str, Any]:
    return {"ts": f"2026-09-29T00:00:0{len(data)}", "run": run, "kind": kind, "data": data}


def test_a_complete_run_is_summarized() -> None:
    records = [
        rec("r1", "run_started", task="fix the bug"),
        rec("r1", "tool_finished", tool="read_file", is_error=False),
        rec("r1", "tool_finished", tool="read_file", is_error=True),
        rec("r1", "action_blocked", tool="run_shell", reason="sudo"),
        rec(
            "r1",
            "run_finished",
            stop="completed",
            turns=3,
            usage={"input_tokens": 100, "output_tokens": 50},
            cost_usd=0.0012,
        ),
    ]
    (summary,) = summarize_runs(records)
    assert summary.task == "fix the bug"
    assert summary.stop == "completed"
    assert summary.turns == 3
    assert summary.usage == Usage(100, 50)
    assert summary.cost_usd == 0.0012
    assert summary.tools == {"read_file": 2}
    assert summary.tool_errors == 1
    assert summary.blocked == 1


def test_runs_sharing_an_id_are_split_on_run_started() -> None:
    records = [
        rec("chat", "run_started", task="one"),
        rec("chat", "run_finished", stop="completed"),
        rec("chat", "run_started", task="two"),
        rec("chat", "run_finished", stop="budget"),
    ]
    assert [(s.task, s.stop) for s in summarize_runs(records)] == [
        ("one", "completed"),
        ("two", "budget"),
    ]


def test_interrupted_runs_stay_unfinished() -> None:
    (summary,) = summarize_runs([rec("r", "run_started", task="t")])
    assert summary.stop == "unfinished"
    assert summary.cost_usd is None


def test_malformed_records_are_tolerated() -> None:
    records: list[dict[str, Any]] = [{"kind": "tool_finished"}, {"run": "x", "data": None}]
    summaries = summarize_runs(records)
    assert summaries[0].tools == {"?": 1}


def test_no_records() -> None:
    assert summarize_runs([]) == []
