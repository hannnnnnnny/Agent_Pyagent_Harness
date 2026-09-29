import pytest

from pyagent.tools.builtin.edit_file import EditFile
from tests.tools.conftest import Runner

tool = EditFile()


@pytest.fixture
def source(run: Runner) -> Runner:
    (run.root / "m.py").write_text("x = 1\ny = 1\nz = 2\n")
    return run


def test_unique_replacement(source: Runner) -> None:
    result = source(tool, path="m.py", old_string="z = 2", new_string="z = 3")
    assert result.content.startswith("Replaced 1 occurrence in m.py\n--- a/m.py")
    assert "-z = 2" in result.content
    assert "+z = 3" in result.content
    assert (source.root / "m.py").read_text() == "x = 1\ny = 1\nz = 3\n"


def test_ambiguous_match_is_refused(source: Runner) -> None:
    result = source(tool, path="m.py", old_string="= 1", new_string="= 9")
    assert result.is_error
    assert "matches 2 times" in result.content
    assert (source.root / "m.py").read_text() == "x = 1\ny = 1\nz = 2\n"


def test_replace_all(source: Runner) -> None:
    result = source(tool, path="m.py", old_string="= 1", new_string="= 9", replace_all=True)
    assert result.content.startswith("Replaced 2 occurrences in m.py")


def test_missing_text_is_error(source: Runner) -> None:
    result = source(tool, path="m.py", old_string="nope", new_string="x")
    assert result.is_error
    assert "not found" in result.content


def test_identical_strings_rejected(source: Runner) -> None:
    assert source(tool, path="m.py", old_string="x", new_string="x").is_error


def test_empty_old_string_rejected_by_schema(source: Runner) -> None:
    result = source(tool, path="m.py", old_string="", new_string="x")
    assert "invalid input" in result.content


def test_cannot_edit_protected_file(run: Runner) -> None:
    (run.root / ".env").write_text("TOKEN=abc")
    result = run(tool, path=".env", old_string="abc", new_string="def")
    assert result.is_error
    assert (run.root / ".env").read_text() == "TOKEN=abc"
