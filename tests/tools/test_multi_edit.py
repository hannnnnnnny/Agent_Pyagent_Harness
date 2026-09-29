import pytest

from pyagent.tools.builtin.multi_edit import MultiEdit
from tests.tools.conftest import Runner

tool = MultiEdit()
ORIGINAL = "def f():\n    return 1\n\n\ndef g():\n    return 1\n"


@pytest.fixture
def source(run: Runner) -> Runner:
    (run.root / "m.py").write_text(ORIGINAL)
    return run


def test_edits_apply_in_order(source: Runner) -> None:
    edits = [
        {"old_string": "def f():", "new_string": "def first():"},
        {"old_string": "def first():\n    return 1", "new_string": "def first():\n    return 2"},
    ]
    result = source(tool, path="m.py", edits=edits)
    assert result.content.startswith("Applied 2 edits to m.py")
    assert (source.root / "m.py").read_text() == ORIGINAL.replace(
        "def f():\n    return 1", "def first():\n    return 2"
    )


def test_any_failure_leaves_file_untouched(source: Runner) -> None:
    edits = [
        {"old_string": "def f():", "new_string": "def first():"},
        {"old_string": "missing", "new_string": "x"},
    ]
    result = source(tool, path="m.py", edits=edits)
    assert result.is_error
    assert "edit 2" in result.content
    assert (source.root / "m.py").read_text() == ORIGINAL


def test_ambiguous_edit_needs_replace_all(source: Runner) -> None:
    edits = [{"old_string": "return 1", "new_string": "return 0"}]
    assert "matches 2 times" in source(tool, path="m.py", edits=edits).content
    edits[0]["replace_all"] = True  # type: ignore[assignment]
    assert not source(tool, path="m.py", edits=edits).is_error


def test_empty_edit_list_is_rejected(source: Runner) -> None:
    assert source(tool, path="m.py", edits=[]).is_error


def test_schema_rejects_unknown_keys(source: Runner) -> None:
    edits = [{"old_string": "a", "new_string": "b", "regex": True}]
    assert "invalid input" in source(tool, path="m.py", edits=edits).content


def test_protected_files_are_refused(run: Runner) -> None:
    (run.root / ".env").write_text("A=1")
    result = run(tool, path=".env", edits=[{"old_string": "1", "new_string": "2"}])
    assert result.is_error
    assert (run.root / ".env").read_text() == "A=1"
