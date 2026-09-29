from pyagent.tools.builtin.read_file import ReadFile
from tests.tools.conftest import Runner

tool = ReadFile()


def test_reads_with_line_numbers(run: Runner) -> None:
    (run.root / "a.txt").write_text("one\ntwo\n")
    result = run(tool, path="a.txt")
    assert not result.is_error
    assert result.content == "1\tone\n2\ttwo"


def test_offset_and_limit_page_through(run: Runner) -> None:
    (run.root / "a.txt").write_text("\n".join(f"l{i}" for i in range(1, 11)))
    result = run(tool, path="a.txt", offset=3, limit=2)
    assert result.content == "3\tl3\n4\tl4\n(showing lines 3-4 of 10)"


def test_offset_past_end(run: Runner) -> None:
    (run.root / "a.txt").write_text("x\n")
    assert "past the end" in run(tool, path="a.txt", offset=5).content


def test_empty_file(run: Runner) -> None:
    (run.root / "a.txt").write_text("")
    assert run(tool, path="a.txt").content == "(empty file)"


def test_missing_file_is_error(run: Runner) -> None:
    result = run(tool, path="missing.txt")
    assert result.is_error
    assert "not found" in result.content


def test_escape_is_blocked(run: Runner) -> None:
    result = run(tool, path="../../etc/passwd")
    assert result.is_error
    assert "blocked by safety policy" in result.content


def test_secret_file_is_blocked(run: Runner) -> None:
    (run.root / ".env").write_text("API_KEY=sk-live")
    result = run(tool, path=".env")
    assert result.is_error
    assert "sk-live" not in result.content
