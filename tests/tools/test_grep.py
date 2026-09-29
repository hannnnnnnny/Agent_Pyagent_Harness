import pytest

from pyagent.tools.builtin import grep as grep_module
from pyagent.tools.builtin.grep import Grep
from tests.tools.conftest import Runner

tool = Grep()


@pytest.fixture
def tree(run: Runner) -> Runner:
    files = {
        "src/a.py": "import os\ndef main():\n    return os.getcwd()\n",
        "src/b.txt": "Main entry\n",
        "docs/c.md": "call main() here\n",
        ".env": "MAIN_TOKEN=supersecret\n",
    }
    for rel, text in files.items():
        path = run.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (run.root / "blob.bin").write_bytes(b"main\x00\x01")
    return run


def test_regex_search_reports_path_and_line(tree: Runner) -> None:
    assert tree(tool, pattern=r"def \w+").content == "src/a.py:2: def main():"


def test_case_insensitive(tree: Runner) -> None:
    out = tree(tool, pattern="main", ignore_case=True).content
    assert "src/b.txt:1: Main entry" in out
    assert "blob.bin" not in out


def test_secrets_are_never_searched(tree: Runner) -> None:
    assert "supersecret" not in tree(tool, pattern="TOKEN", ignore_case=True).content


def test_include_filter(tree: Runner) -> None:
    assert tree(tool, pattern="main", include="**/*.md").content == "docs/c.md:1: call main() here"


def test_fixed_string(tree: Runner) -> None:
    assert tree(tool, pattern="n()", fixed_string=True).content == (
        "docs/c.md:1: call main() here\nsrc/a.py:2: def main():"
    )


def test_invalid_regex_is_error(tree: Runner) -> None:
    result = tree(tool, pattern="(unclosed")
    assert result.is_error
    assert "invalid regular expression" in result.content


def test_no_matches(tree: Runner) -> None:
    assert tree(tool, pattern="zzz").content == "(no matches)"


def test_match_cap(tree: Runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grep_module, "MAX_MATCHES", 1)
    assert "stopped at 1 matches" in tree(tool, pattern="main", ignore_case=True).content


def test_long_lines_are_clipped(run: Runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grep_module, "MAX_LINE_CHARS", 10)
    (run.root / "long.txt").write_text("a" * 50 + "needle")
    assert run(tool, pattern="needle").content == "(no matches)"
