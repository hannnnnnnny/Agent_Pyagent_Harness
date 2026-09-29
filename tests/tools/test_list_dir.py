from pyagent.tools.builtin.list_dir import ListDir
from tests.tools.conftest import Runner

tool = ListDir()


def test_lists_directories_first(run: Runner) -> None:
    (run.root / "src").mkdir()
    (run.root / "b.txt").write_text("")
    (run.root / "A.md").write_text("")
    assert run(tool).content == "src/\nA.md\nb.txt"


def test_hides_protected_entries(run: Runner) -> None:
    (run.root / ".env").write_text("SECRET=1")
    (run.root / "ok.txt").write_text("")
    assert run(tool, path=".").content == "ok.txt"


def test_empty_directory(run: Runner) -> None:
    (run.root / "empty").mkdir()
    assert run(tool, path="empty").content == "(empty directory)"


def test_file_is_not_a_directory(run: Runner) -> None:
    (run.root / "f.txt").write_text("")
    result = run(tool, path="f.txt")
    assert result.is_error
    assert "not a directory" in result.content


def test_cannot_list_outside(run: Runner) -> None:
    assert run(tool, path="..").is_error
