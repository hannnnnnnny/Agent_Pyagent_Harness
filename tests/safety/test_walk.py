from pathlib import Path

import pytest

from pyagent.safety.walk import walk_files
from pyagent.safety.workspace import Workspace


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "root"
    for rel in ["b.txt", "a/x.py", "a/y.py", ".env", "node_modules/pkg/i.js", ".git/HEAD"]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel)
    (tmp_path / "outside.txt").write_text("secret")
    return Workspace(root)


def _names(ws: Workspace) -> list[str]:
    return [ws.relative(p.resolve()) for p in walk_files(ws, ws.root)]


def test_walk_is_sorted_and_skips_noise_and_secrets(ws: Workspace) -> None:
    assert _names(ws) == ["b.txt", "a/x.py", "a/y.py"]


def test_walk_skips_symlinks_leaving_workspace(ws: Workspace, tmp_path: Path) -> None:
    try:
        (ws.root / "leak.txt").symlink_to(tmp_path / "outside.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted on this platform")
    assert "leak.txt" not in " ".join(_names(ws))


def test_walk_can_start_in_subdirectory(ws: Workspace) -> None:
    assert [p.name for p in walk_files(ws, ws.root / "a")] == ["x.py", "y.py"]
