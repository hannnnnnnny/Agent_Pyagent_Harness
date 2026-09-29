import pytest

from pyagent.tools.builtin import glob as glob_module
from pyagent.tools.builtin.glob import Glob
from tests.tools.conftest import Runner

tool = Glob()


@pytest.fixture
def tree(run: Runner) -> Runner:
    for rel in ["setup.py", "src/a.py", "src/pkg/b.py", "src/c.txt", ".env", "keys/id_rsa"]:
        path = run.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    return run


def test_recursive_pattern_matches_all_depths(tree: Runner) -> None:
    assert tree(tool, pattern="**/*.py").content == "setup.py\nsrc/a.py\nsrc/pkg/b.py"


def test_single_level_pattern(tree: Runner) -> None:
    assert tree(tool, pattern="src/*.txt").content == "src/c.txt"


def test_star_does_not_cross_directories(tree: Runner) -> None:
    assert tree(tool, pattern="src/*.py").content == "src/a.py"


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("**/*.py", "a.py", True),
        ("**/*.py", "x/y/a.py", True),
        ("*.py", "x/a.py", False),
        ("a?.txt", "ab.txt", True),
        ("a?.txt", "a/.txt", False),
        ("src/**", "src/x/y", True),
        ("a+b.txt", "a+b.txt", True),
        ("a+b.txt", "aab.txt", False),
    ],
)
def test_compile_glob(pattern: str, path: str, expected: bool) -> None:
    assert bool(glob_module.compile_glob(pattern).match(path)) is expected


def test_search_from_subdirectory(tree: Runner) -> None:
    assert tree(tool, pattern="*.py", path="src/pkg").content == "src/pkg/b.py"


def test_protected_files_never_match(tree: Runner) -> None:
    assert tree(tool, pattern="**/*").content.count("\n") == 3
    assert tree(tool, pattern="**/id_rsa").content == "(no matches)"


def test_results_are_capped(tree: Runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(glob_module, "MAX_RESULTS", 2)
    assert "truncated at 2 results" in tree(tool, pattern="**/*").content
