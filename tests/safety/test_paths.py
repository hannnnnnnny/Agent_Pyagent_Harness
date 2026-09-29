import pytest

from pyagent.errors import SandboxViolation
from pyagent.safety.paths import check_path_text


@pytest.mark.parametrize("path", ["a.txt", "src/pkg/mod.py", "C:/work/a.txt", "./x", "dir\\f"])
def test_ordinary_paths_pass(path: str) -> None:
    check_path_text(path)


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("a\x00b", "NUL"),
        ("\\\\server\\share\\f", "UNC"),
        ("//server/share", "UNC"),
        ("~/.ssh/id_rsa", "home-relative"),
        ("CON", "device"),
        ("logs/nul.txt", "device"),
        ("dir/COM1", "device"),
        ("aux. ", "device"),
        ("file.txt:hidden", "alternate data"),
        ("x" * 5000, "too long"),
    ],
)
def test_tricky_paths_rejected(path: str, reason: str) -> None:
    with pytest.raises(SandboxViolation, match=reason):
        check_path_text(path)
