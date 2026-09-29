from pyagent.tools.base import Risk
from pyagent.tools.builtin.todo import STATE_KEY, Todo
from tests.tools.conftest import Runner

tool = Todo()


def test_renders_the_list_with_progress(run: Runner) -> None:
    items = [
        {"content": "read the code", "status": "completed"},
        {"content": "write the fix", "status": "in_progress"},
        {"content": "run tests", "status": "pending"},
    ]
    result = run(tool, items=items)
    assert result.content == (
        "[x] read the code\n[>] write the fix\n[ ] run tests\n(1/3 completed)"
    )
    assert run.ctx.extras[STATE_KEY] == items


def test_each_call_replaces_the_list(run: Runner) -> None:
    run(tool, items=[{"content": "a", "status": "pending"}])
    run(tool, items=[{"content": "b", "status": "completed"}])
    assert [i["content"] for i in run.ctx.extras[STATE_KEY]] == ["b"]


def test_only_one_item_in_progress(run: Runner) -> None:
    items = [{"content": x, "status": "in_progress"} for x in "ab"]
    result = run(tool, items=items)
    assert result.is_error
    assert "keep at most one" in result.content


def test_clearing_the_list(run: Runner) -> None:
    assert run(tool, items=[]).content == "Task list cleared."


def test_invalid_status_is_rejected(run: Runner) -> None:
    assert "invalid input" in run(tool, items=[{"content": "a", "status": "done"}]).content


def test_is_side_effect_free() -> None:
    assert tool.risk is Risk.READ
