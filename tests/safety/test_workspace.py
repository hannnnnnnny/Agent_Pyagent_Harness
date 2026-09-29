import os
from pathlib import Path

import pytest

from pyagent.errors import SandboxViolation
from pyagent.safety.workspace import Workspace


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    (tmp_path / "root" / "src").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    return Workspace(tmp_path / "root")


def test_root_must_be_a_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Workspace(tmp_path / "missing")


def test_relative_paths_resolve_inside(ws: Workspace) -> None:
    assert ws.resolve("src/a.py") == ws.root / "src" / "a.py"
    assert ws.resolve(".") == ws.root


def test_parent_traversal_is_blocked(ws: Workspace) -> None:
    with pytest.raises(SandboxViolation, match="outside the workspace"):
        ws.resolve("../outside/secret.txt")


def test_traversal_that_returns_inside_is_allowed(ws: Workspace) -> None:
    assert ws.resolve("src/../src/a.py") == ws.root / "src" / "a.py"


def test_absolute_path_outside_is_blocked(ws: Workspace, tmp_path: Path) -> None:
    with pytest.raises(SandboxViolation):
        ws.resolve(str(tmp_path / "outside" / "x"))


def test_absolute_path_inside_is_allowed(ws: Workspace) -> None:
    assert ws.resolve(str(ws.root / "src")) == ws.root / "src"


def test_sibling_with_common_prefix_is_blocked(ws: Workspace, tmp_path: Path) -> None:
    (tmp_path / "root-evil").mkdir()
    with pytest.raises(SandboxViolation):
        ws.resolve(str(tmp_path / "root-evil" / "x"))


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted on this platform")


def test_symlink_escape_is_blocked(ws: Workspace, tmp_path: Path) -> None:
    _symlink(ws.root / "link", tmp_path / "outside")
    with pytest.raises(SandboxViolation):
        ws.resolve("link/secret.txt")


def test_symlink_within_workspace_is_allowed(ws: Workspace) -> None:
    _symlink(ws.root / "alias", ws.root / "src")
    assert ws.resolve("alias") == ws.root / "src"


def test_relative_display_uses_forward_slashes(ws: Workspace) -> None:
    assert ws.relative(ws.root / "src" / "a.py") == "src/a.py"
    assert ws.relative(ws.root) == "."


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive filesystems only")
def test_case_variant_of_root_is_inside(ws: Workspace) -> None:
    upper = str(ws.root).upper()
    assert ws.resolve(upper) == ws.root
